"""UC-08 — Save and retrieve analysis history (authenticated)."""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlmodel import Session

from app.api.auth import get_current_user
from app.config import get_settings
from app.db import get_session
from app.models.user import User
from app.repositories.analyses import AnalysisRepository
from app.schemas.history import AnalysisDetailResponse, HistoryItem, HistoryListResponse
from app.services.image_store import delete_image

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/history", response_model=HistoryListResponse)
def list_history(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> HistoryListResponse:
    """Return all saved analyses for the authenticated user, newest first."""
    analysis_repo = AnalysisRepository(session)
    analyses = analysis_repo.list_by_user(current_user.id)

    items = [
        HistoryItem(
            analysis_id=a.id,
            created_at=a.created_at,
            garment_image_ref=a.garment_image_ref,
            recommended_size=a.recommended_size,
            risk_level=a.risk_level,
        )
        for a in analyses
    ]
    return HistoryListResponse(items=items, total=len(items))


@router.get("/history/{analysis_id}", response_model=AnalysisDetailResponse)
def get_analysis(
    analysis_id: UUID,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> AnalysisDetailResponse:
    """Return a single analysis record; 404 if it belongs to a different user."""
    analysis_repo = AnalysisRepository(session)
    analysis = analysis_repo.get_by_id(analysis_id)

    if analysis is None or analysis.user_id != current_user.id:
        raise HTTPException(404, detail="Analiz kaydı bulunamadı.")

    return AnalysisDetailResponse(
        analysis_id=analysis.id,
        user_id=analysis.user_id,
        garment_image_ref=analysis.garment_image_ref,
        recommended_size=analysis.recommended_size,
        recommended_confidence=analysis.recommended_confidence,
        risk_level=analysis.risk_level,
        formatted_response=analysis.formatted_response,
        created_at=analysis.created_at,
    )


@router.delete("/history/{analysis_id}", status_code=204)
def delete_analysis(
    analysis_id: UUID,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> Response:
    """Delete a single analysis (record + garment image). Ownership-checked."""
    analysis_repo = AnalysisRepository(session)
    analysis = analysis_repo.get_by_id(analysis_id)
    if analysis is None or analysis.user_id != current_user.id:
        raise HTTPException(404, detail="Analiz kaydı bulunamadı.")

    settings = get_settings()
    if analysis.garment_image_ref:
        delete_image(
            analysis.garment_image_ref,
            storage_dir=settings.image_storage_dir,
        )
    analysis_repo.delete(analysis)
    logger.info("analysis_deleted analysis_id=%s user_id=%s", analysis_id, current_user.id)
    return Response(status_code=204)
