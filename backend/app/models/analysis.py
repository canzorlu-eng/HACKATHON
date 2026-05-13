import uuid
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import Column
from sqlalchemy import JSON
from sqlmodel import Field, SQLModel


class Analysis(SQLModel, table=True):
    __tablename__ = "analyses"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(foreign_key="users.id", index=True)
    garment_image_ref: str = Field(...)

    # Populated by LangGraph pipeline (Phase 6+)
    recommended_size: Optional[str] = Field(default=None)
    recommended_confidence: Optional[float] = Field(default=None)
    risk_level: Optional[str] = Field(default=None)
    formatted_response: Optional[Any] = Field(
        default=None, sa_column=Column(JSON, nullable=True)
    )

    created_at: datetime = Field(default_factory=datetime.utcnow)
