import uuid
from datetime import datetime
from typing import Any, List, TYPE_CHECKING
from sqlmodel import Field, Relationship
if TYPE_CHECKING:
    from .message import Message
from sqlalchemy import Column, String, Integer, Boolean, Text, DateTime, JSON, text
from app.db.base import BaseDBModel


class ConversationStatus(BaseDBModel, table=True):
    __tablename__ = "conversation_statuses"

    name: str = Field(sa_column=Column(String(50), unique=True, nullable=False))
    slug: str = Field(sa_column=Column(String(50), unique=True, nullable=False))
    description: str | None = Field(default=None)
    is_active: bool = Field(default=True)


class Conversation(BaseDBModel, table=True):
    __tablename__ = "conversations"

    user_id: uuid.UUID | None = Field(default=None, foreign_key="users.id")
    status_id: uuid.UUID = Field(foreign_key="conversation_statuses.id", nullable=False)
    title: str | None = Field(default=None, max_length=255)

    # PNL fields
    summary: str | None = Field(default=None)
    sentiment_score: float | None = Field(default=None)
    sentiment_label: str | None = Field(default=None, max_length=20)
    keywords: Any = Field(default=[], sa_column=Column(JSON, server_default="'[]'"))
    language: str = Field(default="es", max_length=10)
    summary_generated: bool = Field(default=False)
    total_messages: int = Field(default=0)

    last_activity_at: datetime | None = Field(default=None)

    # Relationships
    messages: List["Message"] = Relationship(back_populates="conversation")
