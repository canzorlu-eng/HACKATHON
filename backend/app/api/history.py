"""UC-08 — Save and retrieve analysis history."""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from app.db import get_session
from app.repositories.analyses import AnalysisRepository
from app.repositories.users import UserRepository
from app.schemas.history import AnalysisDetailResponse, HistoryItem, HistoryListResponse

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/history/{user_id}", response_model=HistoryListResponse)
def list_history(
    user_id: UUID,
    session: Session = Depends(get_session),
) -> HistoryListResponse:
    """
    UC-08: Return all saved analyses for a user, newest first.
    Returns an empty list if the user exists but has no analyses.
    """
    user_repo = UserRepository(session)
    if user_repo.get_by_id(user_id) is None:
        raise HTTPException(404, detail="Kullanıcı profili bulunamadı.")

    analysis_repo = AnalysisRepository(session)
    analyses = analysis_repo.list_by_user(user_id)

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


@router.get("/history/{user_id}/{analysis_id}", response_model=AnalysisDetailResponse)
def get_analysis(
    user_id: UUID,
    analysis_id: UUID,
    session: Session = Depends(get_session),
) -> AnalysisDetailResponse:
    """
    UC-08: Return a single analysis record with all AI output fields.
    """
    user_repo = UserRepository(session)
    if user_repo.get_by_id(user_id) is None:
        raise HTTPException(404, detail="Kullanıcı profili bulunamadı.")

    analysis_repo = AnalysisRepository(session)
    analysis = analysis_repo.get_by_id(analysis_id)

    if analysis is None or analysis.user_id != user_id:
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
