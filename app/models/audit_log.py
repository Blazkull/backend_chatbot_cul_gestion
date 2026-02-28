import uuid
from typing import Any
from datetime import datetime
from sqlmodel import Field
from sqlalchemy import Column, String, Integer, Text, DateTime, JSON, text
from sqlmodel import SQLModel


class AuditLog(SQLModel, table=True):
    """Audit log — NO soft-delete, append-only."""
    __tablename__ = "audit_logs"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID | None = Field(default=None, foreign_key="users.id")
    action: str = Field(sa_column=Column(String(50), nullable=False))
    entity: str = Field(sa_column=Column(String(50), nullable=False))
    entity_id: uuid.UUID | None = Field(default=None)
    old_values: Any = Field(default=None, sa_column=Column(JSON, nullable=True))
    new_values: Any = Field(default=None, sa_column=Column(JSON, nullable=True))
    ip_address: str | None = Field(default=None, max_length=50)
    user_agent: str | None = Field(default=None)
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(DateTime(timezone=True), server_default=text("NOW()"), nullable=False),
    )
