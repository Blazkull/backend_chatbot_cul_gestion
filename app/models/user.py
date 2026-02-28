import uuid
from datetime import date, datetime
from sqlmodel import Field, Relationship
from sqlalchemy import Column, String, Boolean, Integer, Date, DateTime, text
from app.db.base import BaseDBModel


class User(BaseDBModel, table=True):
    __tablename__ = "users"

    # FK → roles
    role_id: uuid.UUID = Field(foreign_key="roles.id", nullable=False)

    # Identification
    document_type: str | None = Field(default=None, max_length=30)
    document_number: str | None = Field(default=None, sa_column=Column(String(30), unique=True))
    first_name: str | None = Field(default=None, max_length=100)
    last_name: str | None = Field(default=None, max_length=100)
    email: str = Field(sa_column=Column(String(255), unique=True, nullable=False))
    phone: str | None = Field(default=None, max_length=30)
    birth_date: date | None = Field(default=None, sa_column=Column(Date, nullable=True))
    gender: str | None = Field(default=None, max_length=20)

    # Address
    address: str | None = Field(default=None)
    city: str | None = Field(default=None, max_length=100)
    neighborhood: str | None = Field(default=None, max_length=100)
    eps: str | None = Field(default=None, max_length=100)

    # Academic
    is_student: bool = Field(default=True)
    program: str | None = Field(default=None, max_length=255)
    semester: int | None = Field(default=None)
    schedule: str | None = Field(default=None, max_length=20)  # diurna/nocturna/mixta

    # Personal
    marital_status: str | None = Field(default=None, max_length=30)
    socioeconomic_stratum: int | None = Field(default=None)

    # Auth
    password_hash: str | None = Field(default=None, max_length=255)  # bcrypt
    supabase_auth_id: str | None = Field(default=None, max_length=255)  # Supabase Auth UID

    # Consent & Status
    data_processing_consent: bool = Field(default=False)
    is_active: bool = Field(default=True)
    last_login_at: datetime | None = Field(default=None)

    @property
    def full_name(self) -> str:
        return f"{self.first_name or ''} {self.last_name or ''}".strip()
