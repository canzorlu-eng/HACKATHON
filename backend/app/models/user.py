import uuid
from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class User(SQLModel, table=True):
    __tablename__ = "users"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)

    # Google identity (set by the auth dependency on first authenticated request)
    google_sub: str = Field(index=True, unique=True)  # stable Google account id
    email: str = Field(index=True)
    name: Optional[str] = Field(default=None)

    # Profile measurements — None until the user finishes onboarding.
    # Once set, these gate the analysis pipeline.
    height_cm: Optional[int] = Field(default=None, ge=50, le=300)
    weight_kg: Optional[int] = Field(default=None, ge=20, le=500)
    fit_preference: Optional[str] = Field(default=None)  # slim|regular|relaxed|oversize
    body_image_ref: Optional[str] = Field(default=None)

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = Field(default=None)
