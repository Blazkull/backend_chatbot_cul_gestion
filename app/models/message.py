import uuid
from typing import Any, TYPE_CHECKING
from sqlmodel import Field, Relationship
if TYPE_CHECKING:
    from .conversation import Conversation
from sqlalchemy import Column, String, Integer, Text, CheckConstraint, JSON
from app.db.base import BaseDBModel


class Message(BaseDBModel, table=True):
    __tablename__ = "messages"
    __table_args__ = (
        CheckConstraint("role IN ('user', 'assistant', 'system')", name="ck_messages_role"),
    )

    conversation_id: uuid.UUID = Field(foreign_key="conversations.id", nullable=False)
    role: str = Field(sa_column=Column(String(20), nullable=False))  # user, assistant, system
    content: str = Field(sa_column=Column(Text, nullable=False))
    tokens_count: int = Field(default=0)

    # PNL
    sentiment: str | None = Field(default=None, max_length=20)
    sentiment_score: float | None = Field(default=None)

    metadata_extra: Any = Field(default={}, sa_column=Column("metadata", JSON, server_default="'{}'" ))

    # Relationships
    conversation: "Conversation" = Relationship(back_populates="messages")
