import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_db
from app.models.request_type import RequestType
from app.schemas.common import APIResponse

router = APIRouter(prefix="/request-types", tags=["Request Types & Dynamic Forms"])

@router.get("", response_model=APIResponse[list[dict]])
async def list_request_types(db: AsyncSession = Depends(get_db)):
    """Obtiene todos los tipos de solicitudes disponibles."""
    result = await db.execute(select(RequestType).where(RequestType.is_deleted == False))
    types = result.scalars().all()
    
    data = [{"id": str(t.id), "name": t.name, "description": t.description} for t in types]
    
    return APIResponse(
        success=True,
        data=data,
        message="Tipos de solicitud obtenidos."
    )

from app.models.request_type import RequestStatus

@router.get("/statuses", response_model=APIResponse[list[dict]])
async def list_request_statuses(db: AsyncSession = Depends(get_db)):
    """Obtiene todos los estados de solicitudes disponibles."""
    result = await db.execute(select(RequestStatus).where(RequestStatus.is_deleted == False))
    statuses = result.scalars().all()
    
    data = [{"id": str(s.id), "name": s.name, "description": s.description} for s in statuses]
    
    return APIResponse(
        success=True,
        data=data,
        message="Estados de solicitud obtenidos."
    )

@router.get("/{type_id}/form-schema", response_model=APIResponse[list[dict]])
async def get_form_schema(type_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """
    Retorna la estructura del formulario (Dynamic Form) requerida para un tipo de solicitud.
    En una base de datos más distribuida esto vendría de un campo JSON en RequestType 
    o una tabla FormFields, pero lo simulamos basado en el ID para el MVP.
    """
    req_type = await db.get(RequestType, type_id)
    if not req_type:
        raise HTTPException(status_code=404, detail="Tipo de solicitud no encontrado.")
        
    # Mocking form schema format compatible with frontend dynamic rendering rules
    # It would ideally be fetched from `req_type.form_schema` JSON column.
    
    schema = []
    
    if "omologaci" in req_type.name.lower():
        schema = [
            {"name": "asignatura", "label": "Asignatura a Homologar", "type": "text", "required": True},
            {"name": "institucion_origen", "label": "Institución de Origen", "type": "text", "required": True},
            {"name": "soporte_pago", "label": "Soporte de Pago (PDF)", "type": "file", "required": True}
        ]
    elif "reembolso" in req_type.name.lower() or "congelamiento" in req_type.name.lower():
        schema = [
            {"name": "motivo", "label": "Motivo de la solicitud", "type": "textarea", "required": True},
            {"name": "programa", "label": "Programa Académico", "type": "text", "required": True},
            {"name": "soporte_motivo", "label": "Soporte (PDF/Doc)", "type": "file", "required": True}
        ]
    else:
        # Default generic schema
        schema = [
            {"name": "asignatura", "label": "Asignatura", "type": "text", "required": True},
            {"name": "motivo", "label": "Motivo / Observación", "type": "textarea", "required": True}
        ]
        
    return APIResponse(
        success=True,
        data=schema,
        message=f"Esquema de formulario para {req_type.name} obtenido."
    )
