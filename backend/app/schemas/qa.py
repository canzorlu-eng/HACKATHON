"""Schemas for /api/v1/qa — conversational follow-ups anchored to an analysis."""

from typing import Literal, Optional

from pydantic import BaseModel, Field


QAIntent = Literal[
    "is_big",
    "fabric_sweat",
    "cut_wide",
    "similar_users",
    "return_reasons",
    "unsupported",
]


class QAAnswerResponse(BaseModel):
    intent: QAIntent
    answer_tr: str                                          # 1-3 Turkish sentences
    confidence_band: Literal["high", "medium", "low"]
    evidence_tr: list[str] = Field(default_factory=list)    # 2-4 grounded bullets
    cohort_scope_tr: Optional[str] = None                   # only for cohort intents
