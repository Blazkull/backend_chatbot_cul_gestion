from typing import Any, Generic, TypeVar
from pydantic import BaseModel

T = TypeVar("T")


class Meta(BaseModel):
    page: int = 1
    page_size: int = 20
    total: int = 0
    pages: int = 0


class APIResponse(BaseModel, Generic[T]):
    """Respuesta estandarizada del API."""
    success: bool
    data: T | None = None
    message: str = ""
    errors: list[dict] | None = None
    meta: Meta | None = None
