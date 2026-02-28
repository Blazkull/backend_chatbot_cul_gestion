import uuid
from sqlmodel import Field
from sqlalchemy import Column, String, Integer, Boolean, Numeric, Text
from app.db.base import BaseDBModel


class RequestCategory(BaseDBModel, table=True):
    __tablename__ = "request_categories"

    name: str = Field(sa_column=Column(String(100), unique=True, nullable=False))
    description: str | None = Field(default=None)
    display_order: int = Field(default=0)
    is_active: bool = Field(default=True)


class RequestType(BaseDBModel, table=True):
    __tablename__ = "request_types"

    category_id: uuid.UUID = Field(foreign_key="request_categories.id", nullable=False)
    name: str = Field(sa_column=Column(String(150), unique=True, nullable=False))
    slug: str = Field(sa_column=Column(String(100), unique=True, nullable=False))
    description: str | None = Field(default=None)
    instructions: str | None = Field(default=None)
    notes: str | None = Field(default=None)
    cost: float = Field(default=0)
    processing_days: int = Field(default=5)
    max_per_semester: int | None = Field(default=None)
    requires_documents: bool = Field(default=False)
    display_order: int = Field(default=0)
    is_active: bool = Field(default=True)


class RequestStatus(BaseDBModel, table=True):
    __tablename__ = "request_statuses"

    name: str = Field(sa_column=Column(String(50), unique=True, nullable=False))
    slug: str = Field(sa_column=Column(String(50), unique=True, nullable=False))
    description: str | None = Field(default=None)
    color: str = Field(default="#6B7280", max_length=7)
    display_order: int = Field(default=0)
    is_final: bool = Field(default=False)
    is_active: bool = Field(default=True)
