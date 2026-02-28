import uuid
from datetime import date
from pydantic import BaseModel, EmailStr


class LoginRequest(BaseModel):
    email: EmailStr | None = None
    document_number: str | None = None
    password: str


class RegisterRequest(BaseModel):
    document_type: str = "CC"
    document_number: str
    first_name: str
    last_name: str
    email: EmailStr
    phone: str | None = None
    password: str
    birth_date: date | None = None
    gender: str | None = None
    program: str | None = None
    semester: int | None = None
    schedule: str | None = None
    data_processing_consent: bool = False

class StudentRegisterRequest(BaseModel):
    document_type: str = "CC"
    document_number: str
    first_name: str
    last_name: str
    email: EmailStr
    phone: str | None = None
    program: str | None = None
    semester: int | None = None
    data_processing_consent: bool = True



class ValidateCedulaRequest(BaseModel):
    document_number: str


class ValidateCedulaResponse(BaseModel):
    exists: bool
    user: dict | None = None
    access_token: str | None = None


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict


class UserRead(BaseModel):
    id: uuid.UUID
    document_type: str | None
    document_number: str | None
    first_name: str | None
    last_name: str | None
    email: str
    phone: str | None
    program: str | None
    semester: int | None
    is_active: bool

    class Config:
        from_attributes = True

class UserUpdate(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    phone: str | None = None
    program: str | None = None
    semester: int | None = None
    schedule: str | None = None
    is_active: bool | None = None

class UserPasswordUpdate(BaseModel):
    password: str
