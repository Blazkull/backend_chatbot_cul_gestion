from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException, status
import uuid

from app.models.academic_request import AcademicRequest
from app.models.request_type import RequestType, RequestStatus
from app.schemas.academic_request import AcademicRequestCreate, AcademicRequestRead, AcademicRequestUpdate


async def generate_radicado(db: AsyncSession) -> str:
    """
    Genera un número de radicado único. Formato: RAD-AAAA-0000X
    En una app real, podrías buscar el último de este año y sumar 1.
    """
    year = datetime.now().year
    
    # Buscar cuantos hay en el año (simple count)
    query = select(AcademicRequest).where(AcademicRequest.radicado_number.like(f"RAD-%"))
    result = await db.execute(query)
    count = len(result.scalars().all())
    
    secuencia = count + 1
    radicado = f"RAD-{year}-{secuencia:05d}"
    return radicado


async def create_request(
    db: AsyncSession, 
    user_id: uuid.UUID, 
    data: AcademicRequestCreate
) -> AcademicRequest:
    
    # 1. Verificar tipo de solicitud
    req_type = await db.get(RequestType, data.request_type_id)
    if not req_type:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="El tipo de solicitud especificado no existe."
        )

    # 2. Buscar estado inicial (default 'En Revisión' o 'Abierto')
    # Buscar el primer estado en la DB o asignar uno por defector. Aquí asumiremos
    # que existe un estado inicial.
    q_status = select(RequestStatus).limit(1)
    res_status = await db.execute(q_status)
    initial_status = res_status.scalar_one_or_none()
    
    if not initial_status:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error del sistema: No hay estados de solicitud configurados."
        )

    # 3. Generar radicado
    radicado = await generate_radicado(db)

    # 4. Crear registro
    new_request = AcademicRequest(
        radicado_number=radicado,
        user_id=user_id,
        request_type_id=req_type.id,
        status_id=initial_status.id,
        form_data=data.form_data,
        priority=data.priority,
        notes=data.notes,
        current_approval_level=0
    )
    
    db.add(new_request)
    await db.commit()
    await db.refresh(new_request)
    
    return new_request


from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

async def get_requests_for_user(
    db: AsyncSession, 
    user_id: uuid.UUID,
    page: int = 1,
    page_size: int = 20
):
    """Retorna solicitudes de un usuario con paginación."""
    query = select(AcademicRequest).where(
        AcademicRequest.user_id == user_id, 
        AcademicRequest.is_deleted == False
    ).order_by(AcademicRequest.created_at.desc())
    
    count_query = select(func.count()).select_from(AcademicRequest).where(
        AcademicRequest.user_id == user_id, 
        AcademicRequest.is_deleted == False
    )
    
    total = (await db.execute(count_query)).scalar_one()
    
    offset = (page - 1) * page_size
    query = query.limit(page_size).offset(offset)
    
    result = await db.execute(query)
    return result.scalars().all(), total


async def get_all_requests_paginated(
    db: AsyncSession,
    page: int = 1,
    page_size: int = 20,
    document_number: str | None = None,
    request_type_id: uuid.UUID | None = None,
    status_id: uuid.UUID | None = None
):
    """(Admin) Retorna todas las solicitudes con filtros dinámicos."""
    from app.models.user import User

    query = select(AcademicRequest).where(AcademicRequest.is_deleted == False).order_by(AcademicRequest.created_at.desc())
    count_query = select(func.count()).select_from(AcademicRequest).where(AcademicRequest.is_deleted == False)

    if document_number:
        query = query.join(User).where(User.document_number.ilike(f"%{document_number}%"))
        count_query = count_query.join(User).where(User.document_number.ilike(f"%{document_number}%"))
        
    if request_type_id:
        query = query.where(AcademicRequest.request_type_id == request_type_id)
        count_query = count_query.where(AcademicRequest.request_type_id == request_type_id)
        
    if status_id:
        query = query.where(AcademicRequest.status_id == status_id)
        count_query = count_query.where(AcademicRequest.status_id == status_id)

    total = (await db.execute(count_query)).scalar_one()
    
    offset = (page - 1) * page_size
    query = query.limit(page_size).offset(offset)
    
    # Eager load relationships for admin view if necessary:
    # query = query.options(selectinload(AcademicRequest.user))

    result = await db.execute(query)
    return result.scalars().all(), total



async def get_request_by_id(
    db: AsyncSession, 
    request_id: uuid.UUID, 
    user_id: uuid.UUID | None = None
):
    query = select(AcademicRequest).where(
        AcademicRequest.id == request_id, 
        AcademicRequest.is_deleted == False
    )
    
    if user_id:
        query = query.where(AcademicRequest.user_id == user_id)
        
    result = await db.execute(query)
    req = result.scalar_one_or_none()
    
    if not req:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Solicitud no encontrada o no tienes permisos."
        )
    return req

async def update_request_status(
    db: AsyncSession,
    request_id: uuid.UUID,
    new_status_id: uuid.UUID,
    admin_id: uuid.UUID
):
    req = await get_request_by_id(db, request_id)
    req.status_id = new_status_id
    req.updated_at = datetime.utcnow()
    # In a real app we would log this in Audit Logs
    db.add(req)
    await db.commit()
    await db.refresh(req)
    return req


async def update_request(
    db: AsyncSession,
    request_id: uuid.UUID,
    data: AcademicRequestUpdate,
    user_id: uuid.UUID | None = None
) -> AcademicRequest:
    req = await get_request_by_id(db, request_id, user_id)
    
    # User can update notes and form_data. Admin can update anything.
    if user_id:
        if data.notes is not None:
            req.notes = data.notes
        if data.form_data is not None:
            req.form_data = data.form_data
    else:
        if data.status_id is not None:
            req.status_id = data.status_id
        if data.current_approval_level is not None:
            req.current_approval_level = data.current_approval_level
        if data.priority is not None:
            req.priority = data.priority
        if data.notes is not None:
            req.notes = data.notes
        if data.form_data is not None:
            req.form_data = data.form_data

    req.updated_at = datetime.utcnow()
    db.add(req)
    await db.commit()
    await db.refresh(req)
    return req

async def delete_request(
    db: AsyncSession,
    request_id: uuid.UUID,
    user_id: uuid.UUID | None = None
):
    req = await get_request_by_id(db, request_id, user_id)
    req.is_deleted = True
    req.updated_at = datetime.utcnow()
    db.add(req)
    await db.commit()
    return True

