"""UC-02 / UC-03–07 — Garment upload + LangGraph fit analysis pipeline."""

import asyncio
import logging
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlmodel import Session

from app.ai.client import AIClient, get_ai_client
from app.ai.graph import build_pipeline
from app.config import get_settings
from app.db import get_session
from app.models.analysis import Analysis
from app.repositories.analyses import AnalysisRepository
from app.repositories.users import UserRepository
from app.schemas.profile import GarmentUploadResponse
from app.services.image_store import ImageValidationError, delete_image, validate_and_store

_MAX_HISTORY_PER_USER = 5

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/analyze", response_model=GarmentUploadResponse, status_code=202)
async def start_analysis(
    user_id: str = Form(...),
    garment_image: UploadFile = File(...),
    session: Session = Depends(get_session),
    ai_client: AIClient = Depends(get_ai_client),
) -> GarmentUploadResponse:
    """
    UC-02: Upload garment image and run the full fit analysis pipeline.
    Returns 202 Accepted with the complete Turkish AI recommendation.
    """
    try:
        uid = UUID(user_id)
    except ValueError:
        raise HTTPException(422, detail="Geçersiz kullanıcı kimliği formatı.")

    user_repo = UserRepository(session)
    user = user_repo.get_by_id(uid)
    if user is None:
        raise HTTPException(404, detail="Kullanıcı profili bulunamadı.")

    settings = get_settings()
    try:
        garment_ref = await validate_and_store(
            garment_image,
            subfolder="garment",
            storage_dir=settings.image_storage_dir,
            max_upload_mb=settings.max_upload_mb,
        )
    except ImageValidationError as exc:
        raise HTTPException(422, detail=str(exc)) from exc

    analysis = Analysis(user_id=uid, garment_image_ref=garment_ref)
    analysis_repo = AnalysisRepository(session)
    analysis = analysis_repo.create(analysis)

    logger.info(
        "analysis_created analysis_id=%s user_id=%s garment_ref=%s",
        analysis.id,
        uid,
        garment_ref,
    )

    # ---- Run LangGraph pipeline ----
    pipeline = build_pipeline(ai_client)
    initial_state = {
        "analysis_id":     str(analysis.id),
        "user_id":         str(uid),
        "height_cm":       user.height_cm,
        "weight_kg":       user.weight_kg,
        "fit_preference":  user.fit_preference,
        "body_image_ref":  user.body_image_ref,
        "garment_image_ref": garment_ref,
        "storage_dir":     settings.image_storage_dir,
        # pipeline result fields — initialised so LangGraph state is complete
        "intent_valid":    False,
        "intent_error":    None,
        "body_analysis":   None,
        "garment_analysis": None,
        "review_insights": [],
        "recommendation":  None,
        "risk_evaluation": None,
        "final_response":  None,
        "pipeline_error":  None,
    }

    _PIPELINE_TIMEOUT = 30.0  # seconds

    final_response_dict = None
    try:
        final_state = await asyncio.wait_for(
            pipeline.ainvoke(initial_state),
            timeout=_PIPELINE_TIMEOUT,
        )
        final_response_dict = final_state.get("final_response")

        if final_response_dict:
            fr = final_response_dict
            analysis.recommended_size       = fr.get("recommended_size")
            analysis.recommended_confidence = fr.get("confidence_score")
            analysis.risk_level             = fr.get("risk_level")
            analysis.formatted_response     = fr
            session.add(analysis)
            session.commit()
            logger.info(
                "pipeline_complete analysis_id=%s size=%s risk=%s confidence=%.2f",
                analysis.id,
                analysis.recommended_size,
                analysis.risk_level,
                analysis.recommended_confidence or 0,
            )
        elif final_state.get("intent_error"):
            logger.warning(
                "pipeline_intent_rejected analysis_id=%s reason=%s",
                analysis.id,
                final_state["intent_error"],
            )
    except asyncio.TimeoutError:
        logger.warning("pipeline_timeout analysis_id=%s after %.0fs", analysis.id, _PIPELINE_TIMEOUT)
        session.rollback()
    except Exception:
        logger.exception("pipeline_failed analysis_id=%s", analysis.id)
        session.rollback()
        # Return partial response (image stored, AI result absent) rather than 500

    # ---- Prune to the user's most recent N analyses ----
    # The user wants the history capped at _MAX_HISTORY_PER_USER; whenever a
    # new one comes in, anything older than the last N is removed (record +
    # garment image on disk).
    try:
        overflow = analysis_repo.get_overflow(uid, keep=_MAX_HISTORY_PER_USER)
        for old in overflow:
            if old.garment_image_ref:
                delete_image(
                    old.garment_image_ref,
                    storage_dir=settings.image_storage_dir,
                )
            analysis_repo.delete(old)
        if overflow:
            logger.info(
                "history_pruned user_id=%s removed=%d keep=%d",
                uid, len(overflow), _MAX_HISTORY_PER_USER,
            )
    except Exception:
        # Pruning is best-effort — never block the user's primary response on it.
        logger.exception("history_prune_failed user_id=%s", uid)
        session.rollback()

    message = (
        "Görsel doğrulandı ve analiz tamamlandı."
        if final_response_dict
        else "Görsel doğrulandı. Analiz kısmen tamamlanamadı."
    )

    return GarmentUploadResponse(
        analysis_id=analysis.id,
        message=message,
        garment_image_ref=garment_ref,
        **(final_response_dict or {}),
    )
