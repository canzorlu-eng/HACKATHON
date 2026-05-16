"""
GET /api/v1/analyses/{analysis_id}/cohort

Lazy side-call powering the "Benzer kullanıcı deneyimi" panel on /analyze.
Reads the persisted Analysis (its garment_meta), pulls a cohort from the
review service via the two-stage relaxation, and returns aggregated
return-reason stats. Suppresses headline percentages when confidence_band
is "low" so the UI never publishes an unbacked number.
"""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from app.api.auth import get_current_user
from app.db import get_session
from app.models.user import User
from app.repositories.analyses import AnalysisRepository
from app.schemas.cohort import CohortResponse, ReasonStatOut
from app.services.cohort import (
    aggregate_return_reasons,
    find_similar_reviewers,
)

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/analyses/{analysis_id}/cohort", response_model=CohortResponse)
def get_cohort_for_analysis(
    analysis_id: UUID,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> CohortResponse:
    repo = AnalysisRepository(session)
    analysis = repo.get_by_id(analysis_id)

    if analysis is None or analysis.user_id != current_user.id:
        # Don't disclose the difference — both look the same to a stranger.
        raise HTTPException(status_code=404, detail="Analiz bulunamadı.")

    fr = analysis.formatted_response or {}
    garment_meta = fr.get("garment_meta") or {}
    category = str(garment_meta.get("category", ""))
    tendency = str(garment_meta.get("brand_sizing_tendency", "standart"))

    # Garment-invalid analyses lack a recommended_size — no useful cohort
    # can be derived. Return an empty low-confidence response so the panel
    # cleanly hides itself rather than firing meaningless aggregations.
    if (
        fr.get("recommended_size") is None
        or current_user.height_cm is None
        or current_user.weight_kg is None
        or not category
    ):
        return CohortResponse(
            scope_tr="Yeterli benzer kullanıcı verisi yok",
            total=0,
            returned_count=0,
            returned_pct=None,
            confidence_band="low",
            top_reasons=[],
            sample_quotes_tr=[],
        )

    cohort_rows, scope = find_similar_reviewers(
        category=category,
        brand_sizing_tendency=tendency,
        height_cm=int(current_user.height_cm),
        weight_kg=int(current_user.weight_kg),
    )
    stats = aggregate_return_reasons(cohort_rows)

    top_reasons = [
        ReasonStatOut(
            reason=r.reason,
            reason_tr=r.reason_tr,
            raw_count=r.raw_count,
            pct=r.pct,
        )
        for r in stats.top_reasons
    ]

    logger.info(
        "cohort_lookup analysis_id=%s user_id=%s category=%s tendency=%s "
        "stage=%s total=%d returned=%d band=%s",
        analysis_id, current_user.id, category, tendency,
        scope.stage, stats.total, stats.returned_count, stats.confidence_band,
    )

    return CohortResponse(
        scope_tr=scope.label_tr,
        total=stats.total,
        returned_count=stats.returned_count,
        returned_pct=stats.returned_pct,
        confidence_band=stats.confidence_band,
        top_reasons=top_reasons,
        sample_quotes_tr=stats.sample_quotes_tr,
    )
