"""Schemas for the /stylist endpoint."""

from typing import Optional

from pydantic import BaseModel, Field


class StylistSuggestion(BaseModel):
    garment_id: str
    name: str
    brand: str
    category: str
    fit_type: str
    fabric: str
    price_tl: int
    reason_tr: str
    fit_warning_tr: Optional[str] = None


class StylistResponse(BaseModel):
    suggestions: list[StylistSuggestion] = Field(default_factory=list)
    stylist_note_tr: str
    uncertainty_tr: Optional[str] = None
    query_echo: str
    max_price_tl: Optional[int] = None
    # True when Gemini rejected the request as not being a fashion query.
    # Frontend uses this to suppress the "no results" empty-state.
    off_topic: bool = False
