from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel


class HistoryItem(BaseModel):
    model_config = {"from_attributes": True}

    analysis_id: UUID
    created_at: datetime
    garment_image_ref: str
    recommended_size: Optional[str] = None
    risk_level: Optional[str] = None


class HistoryListResponse(BaseModel):
    items: list[HistoryItem]
    total: int


class AnalysisDetailResponse(BaseModel):
    model_config = {"from_attributes": True}

    analysis_id: UUID
    user_id: UUID
    garment_image_ref: str
    recommended_size: Optional[str] = None
    recommended_confidence: Optional[float] = None
    risk_level: Optional[str] = None
    formatted_response: Optional[Any] = None
    created_at: datetime
