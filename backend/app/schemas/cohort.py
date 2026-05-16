"""Schemas for /api/v1/analyses/{id}/cohort and the QA cohort-driven intents."""

from typing import Literal, Optional

from pydantic import BaseModel, Field


class ReasonStatOut(BaseModel):
    reason: str            # internal enum, e.g. "boy_uzunluk"
    reason_tr: str         # human label, e.g. "Boy / uzunluk"
    raw_count: int
    pct: int               # share of RETURNED cohort, not the full cohort


class CohortResponse(BaseModel):
    """Lazy side-call payload — drives the SimilarUsersPanel."""

    scope_tr: str                                           # badge text, e.g. "Benzer 18 alıcı (aynı kategori, ±5 cm boy)"
    total: int                                              # cohort size
    returned_count: int
    returned_pct: Optional[int] = None                      # None when confidence_band == "low"
    confidence_band: Literal["high", "medium", "low"]
    top_reasons: list[ReasonStatOut] = Field(default_factory=list)
    sample_quotes_tr: list[str] = Field(default_factory=list)
