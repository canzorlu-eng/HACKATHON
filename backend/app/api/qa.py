"""
POST /api/v1/qa — conversational follow-up anchored to an analysis.

Five supported intents (regex-routed, no Gemini classification):
  is_big | fabric_sweat | cut_wide | similar_users | return_reasons
Anything else routes to `unsupported` and returns a fixed Turkish refusal.

Honesty rail: every numeric claim in `answer_tr` is produced by a pure
fact collector (app.ai.qa_facts). No LLM is invoked here — the demo MUST
be reproducible and free of fabricated percentages. The fact collectors
themselves never invent numbers; they read from analysis.formatted_response,
the catalog, or the cohort aggregation.

Future enhancement: an optional Gemini narrative wrap can be added behind a
QA_USE_GEMINI feature flag, with verbatim-number validation against the
fact dict before serving the response. Out of scope for the hackathon cut.
"""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, Form, HTTPException
from sqlmodel import Session

from app.ai.qa_facts import collect_facts_for
from app.ai.qa_intent import route_intent
from app.api.auth import get_current_user
from app.db import get_session
from app.models.user import User
from app.repositories.analyses import AnalysisRepository
from app.schemas.qa import QAAnswerResponse

logger = logging.getLogger(__name__)
router = APIRouter()

_MAX_QUERY_LEN = 200


@router.post("/qa", response_model=QAAnswerResponse, status_code=200)
def post_qa(
    analysis_id: UUID = Form(...),
    text: str = Form(..., min_length=1, max_length=_MAX_QUERY_LEN),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> QAAnswerResponse:
    """Answer a follow-up question grounded in a recent analysis."""
    repo = AnalysisRepository(session)
    analysis = repo.get_by_id(analysis_id)

    if analysis is None or analysis.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Analiz bulunamadı.")

    if not analysis.formatted_response:
        raise HTTPException(
            status_code=409,
            detail="Bu analiz tamamlanmamış — önce yeniden analiz başlatın.",
        )

    intent = route_intent(text)
    facts = collect_facts_for(intent, analysis, current_user)

    logger.info(
        "qa user_id=%s analysis_id=%s intent=%s band=%s",
        current_user.id, analysis_id, intent, facts.get("confidence_band"),
    )

    return QAAnswerResponse(
        intent=intent,
        answer_tr=str(facts.get("verdict_tr", "")),
        confidence_band=facts.get("confidence_band", "low"),
        evidence_tr=list(facts.get("evidence_tr", [])),
        cohort_scope_tr=facts.get("cohort_scope_tr"),
    )
