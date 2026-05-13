import uuid
from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class User(SQLModel, table=True):
    __tablename__ = "users"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    height_cm: int = Field(..., ge=50, le=300)
    weight_kg: int = Field(..., ge=20, le=500)
    fit_preference: str = Field(...)  # slim | regular | relaxed | oversize
    body_image_ref: Optional[str] = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = Field(default=None)
