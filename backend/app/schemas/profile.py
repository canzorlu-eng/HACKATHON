from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class FitPreference(str, Enum):
    slim = "slim"
    regular = "regular"
    relaxed = "relaxed"
    oversize = "oversize"


class ProfileResponse(BaseModel):
    model_config = {"from_attributes": True}

    user_id: UUID
    height_cm: int
    weight_kg: int
    fit_preference: FitPreference
    has_body_image: bool
    created_at: datetime


class GarmentUploadResponse(BaseModel):
    analysis_id: UUID
    message: str
    garment_image_ref: str
    # AI pipeline output — None only when pipeline is skipped (e.g. validation error)
    recommended_size: Optional[str] = None
    confidence_score: Optional[float] = None
    confidence_pct: Optional[str] = None
    explanation_tr: Optional[str] = None
    risk_level: Optional[str] = None
    risk_level_tr: Optional[str] = None
    risk_factors_tr: Optional[list[str]] = None
    uncertainty_tr: Optional[str] = None
    community_insights_tr: Optional[list[str]] = None
