import uuid
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.db.session import get_db
from app.dependencies.auth import get_current_user, require_role
from app.schemas.auth import UserRead
from app.schemas.academic_request import AcademicRequestCreate, AcademicRequestRead
from app.schemas.common import APIResponse

from app.services.request_service import (
    create_request,
    get_requests_for_user,
    get_request_by_id,
    update_request,
    delete_request
)

router = APIRouter(prefix="/requests", tags=["Academic Requests"])

@router.post("", response_model=APIResponse[AcademicRequestRead], status_code=status.HTTP_201_CREATED)
async def create_new_request(
    data: AcademicRequestCreate,
    current_user: UserRead = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Crear una nueva solicitud académica. 
    Generará automáticamente el número de radicado y lo asignará al estado inicial.
    """
    new_req = await create_request(db, current_user.id, data)
    return APIResponse(
        success=True,
        data=new_req,
        message="Solicitud creada exitosamente."
    )


from fastapi import Query
from app.schemas.common import Meta

@router.get("", response_model=APIResponse[list[AcademicRequestRead]])
async def list_my_requests(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: UserRead = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Obtener todas las solicitudes del usuario autenticado."""
    reqs, total = await get_requests_for_user(db, current_user.id, page, page_size)
    pages = (total + page_size - 1) // page_size
    return APIResponse(
        success=True,
        data=reqs,
        meta=Meta(page=page, page_size=page_size, total=total, pages=pages),
        message=f"Se encontraron {len(reqs)} solicitudes."
    )

@router.get("/{request_id}", response_model=APIResponse[AcademicRequestRead])
async def get_request_detail(
    request_id: uuid.UUID,
    current_user: UserRead = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Obtener detalle de una solicitud específica."""
    # current_user.id is passed to prevent accessing other users' requests unless they are admin
    user_id_param = None if current_user.role_name in ["superadmin", "admin"] else current_user.id
    req = await get_request_by_id(db, request_id, user_id_param)
    return APIResponse(
        success=True,
        data=req,
        message="Solicitud obtenida exitosamente."
    )

from app.schemas.academic_request import AcademicRequestUpdate

@router.put("/{request_id}", response_model=APIResponse[AcademicRequestRead])
async def update_my_request(
    request_id: uuid.UUID,
    data: AcademicRequestUpdate,
    current_user: UserRead = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Actualizar una solicitud propia (o de cualquiera si es admin)."""
    user_id_param = None if current_user.role_name in ["superadmin", "admin"] else current_user.id
    updated_req = await update_request(db, request_id, data, user_id_param)
    return APIResponse(
        success=True,
        data=updated_req,
        message="Solicitud actualizada exitosamente."
    )

@router.delete("/{request_id}", response_model=APIResponse[bool])
async def delete_my_request(
    request_id: uuid.UUID,
    current_user: UserRead = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Eliminar (soft-delete) una solicitud."""
    user_id_param = None if current_user.role_name in ["superadmin", "admin"] else current_user.id
    await delete_request(db, request_id, user_id_param)
    return APIResponse(
        success=True,
        data=True,
        message="Solicitud eliminada exitosamente."
    )

from app.services.request_service import get_all_requests_paginated, update_request_status

@router.get("/admin/all", response_model=APIResponse[list[AcademicRequestRead]])
async def list_all_requests(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    document_number: str | None = None,
    request_type_id: uuid.UUID | None = None,
    status_id: uuid.UUID | None = None,
    current_user: UserRead = Depends(require_role(["superadmin", "admin"])),
    db: AsyncSession = Depends(get_db)
):
    """(Admin) Listar todas las solicitudes con filtros (Mínimo 3 filtros requeridos por rúbrica)."""
    reqs, total = await get_all_requests_paginated(
        db, page, page_size, document_number, request_type_id, status_id
    )
    pages = (total + page_size - 1) // page_size
    return APIResponse(
        success=True,
        data=reqs,
        meta=Meta(page=page, page_size=page_size, total=total, pages=pages),
        message="Operación exitosa"
    )

@router.put("/{request_id}/status", response_model=APIResponse[AcademicRequestRead])
async def change_request_status(
    request_id: uuid.UUID,
    new_status_id: uuid.UUID,
    current_user: UserRead = Depends(require_role(["superadmin", "admin"])),
    db: AsyncSession = Depends(get_db)
):
    """(Admin) Cambiar el estado de una solicitud (Flujo de Aprobación)."""
    updated_req = await update_request_status(db, request_id, new_status_id, current_user.id)
    return APIResponse(
        success=True,
        data=updated_req,
        message="Estado de la solicitud actualizado."
    )

