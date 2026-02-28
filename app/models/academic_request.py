import uuid
from typing import Any
from sqlmodel import Field
from sqlalchemy import Column, String, Integer, Text, JSON
from app.db.base import BaseDBModel


class AcademicRequest(BaseDBModel, table=True):
    __tablename__ = "academic_requests"

    radicado_number: str = Field(sa_column=Column(String(30), unique=True, nullable=False))
    user_id: uuid.UUID = Field(foreign_key="users.id", nullable=False)
    conversation_id: uuid.UUID | None = Field(default=None, foreign_key="conversations.id")
    request_type_id: uuid.UUID = Field(foreign_key="request_types.id", nullable=False)
    status_id: uuid.UUID = Field(foreign_key="request_statuses.id", nullable=False)
    current_approval_level: int = Field(default=0)
    form_data: Any = Field(default={}, sa_column=Column(JSON, server_default="'{}'"))
    summary_nlp: str | None = Field(default=None)
    notes: str | None = Field(default=None)
    priority: int = Field(default=0)
