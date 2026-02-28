import uuid
from datetime import datetime
from typing import Any
from pydantic import BaseModel, ConfigDict, Field

class AcademicRequestBase(BaseModel):
    request_type_id: uuid.UUID
    priority: int = 0
    form_data: dict[str, Any] = Field(default_factory=dict)
    notes: str | None = None

class AcademicRequestCreate(AcademicRequestBase):
    pass

class AcademicRequestUpdate(BaseModel):
    status_id: uuid.UUID | None = None
    current_approval_level: int | None = None
    priority: int | None = None
    notes: str | None = None
    form_data: dict[str, Any] | None = None

class AcademicRequestRead(AcademicRequestBase):
    id: uuid.UUID
    radicado_number: str
    user_id: uuid.UUID
    status_id: uuid.UUID
    current_approval_level: int
    created_at: datetime
    updated_at: datetime
    
    # Adicionales opcionales para devolver información anidada
    status_name: str | None = None
    type_name: str | None = None

    model_config = ConfigDict(from_attributes=True)
