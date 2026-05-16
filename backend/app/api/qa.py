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

from app.ai.client import AIClient, get_ai_client
from app.ai.qa_facts import collect_facts_for
from app.ai.qa_intent import route_intent
from app.ai.qa_narrative import maybe_compose_narrative
from app.api.auth import get_current_user
from app.config import get_settings
from app.db import get_session
from app.models.user import User
from app.repositories.analyses import AnalysisRepository
from app.schemas.qa import QAAnswerResponse

logger = logging.getLogger(__name__)
router = APIRouter()

_MAX_QUERY_LEN = 200


@router.post("/qa", response_model=QAAnswerResponse, status_code=200)
async def post_qa(
    analysis_id: UUID = Form(...),
    text: str = Form(..., min_length=1, max_length=_MAX_QUERY_LEN),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
    ai_client: AIClient = Depends(get_ai_client),
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
    deterministic_verdict = str(facts.get("verdict_tr", ""))

    # Optional Gemini polish — presentation-only. The validator inside
    # maybe_compose_narrative rejects any rewrite that invents numbers and
    # silently falls back to the deterministic verdict.
    settings = get_settings()
    answer_tr = await maybe_compose_narrative(
        facts=facts,
        deterministic_verdict_tr=deterministic_verdict,
        ai_client=ai_client,
        enabled=settings.enable_gemini_narrative,
    )

    logger.info(
        "qa user_id=%s analysis_id=%s intent=%s band=%s narrative_flag=%s "
        "rewritten=%s",
        current_user.id, analysis_id, intent, facts.get("confidence_band"),
        settings.enable_gemini_narrative,
        answer_tr != deterministic_verdict,
    )

    return QAAnswerResponse(
        intent=intent,
        answer_tr=answer_tr,
        confidence_band=facts.get("confidence_band", "low"),
        evidence_tr=list(facts.get("evidence_tr", [])),
        cohort_scope_tr=facts.get("cohort_scope_tr"),
    )
