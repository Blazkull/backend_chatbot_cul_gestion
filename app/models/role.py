from typing import Any
from sqlmodel import Field
from sqlalchemy import Column, String, Boolean, JSON
from app.db.base import BaseDBModel


class Role(BaseDBModel, table=True):
    __tablename__ = "roles"

    name: str = Field(sa_column=Column(String(50), unique=True, nullable=False))
    description: str | None = Field(default=None)
    permissions: Any = Field(default=[], sa_column=Column(JSON, server_default="'[]'"))
    is_active: bool = Field(default=True)
