import uuid
from datetime import datetime
from sqlmodel import SQLModel, Field


class BaseDBModel(SQLModel):
    """Base model with shared audit fields for all tables."""

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        primary_key=True,
        nullable=False,
    )
    created_at: datetime | None = Field(
        default=None,
        sa_column_kwargs={"server_default": "NOW()", "nullable": False},
    )
    updated_at: datetime | None = Field(
        default=None,
        sa_column_kwargs={"server_default": "NOW()", "nullable": False},
    )
    deleted_at: datetime | None = Field(default=None)
    is_deleted: bool = Field(default=False)
