from fastapi import APIRouter, Depends, HTTPException, status, Query
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func

from app.db.session import get_db
from app.dependencies.auth import get_current_user, require_role
from app.models.user import User
from app.models.role import Role
from app.schemas.auth import UserRead, StudentRegisterRequest, UserUpdate, UserPasswordUpdate
from app.schemas.common import APIResponse, Meta
from app.services.auth_service import hash_password

router = APIRouter(prefix="/users", tags=["Users"])

@router.post("/register-student", response_model=APIResponse[UserRead], status_code=status.HTTP_201_CREATED)
async def register_student_implicitly(
    data: StudentRegisterRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Registra un estudiante en PostgreSQL de forma directa sin requerir una cuenta en Supabase Auth,
    ya que los estudiantes acceden validando su cédula.
    """
    # Verify if exists
    result = await db.execute(select(User).where(User.document_number == data.document_number))
    existing_user = result.scalars().first()
    if existing_user:
        raise HTTPException(status_code=400, detail="El estudiante ya está registrado.")
    
    # Get student role
    role_result = await db.execute(select(Role).where(Role.name == "estudiante"))
    student_role = role_result.scalars().first()
    if not student_role:
        raise HTTPException(status_code=500, detail="Rol 'estudiante' no encontrado en la BD.")

    new_student = User(
        role_id=student_role.id,
        document_type=data.document_type,
        document_number=data.document_number,
        first_name=data.first_name,
        last_name=data.last_name,
        email=data.email,
        phone=data.phone,
        program=data.program,
        semester=data.semester,
        data_processing_consent=data.data_processing_consent,
        supabase_auth_id=None, # Explicitly null
        password_hash=None
    )
    
    db.add(new_student)
    await db.commit()
    await db.refresh(new_student)
    
    return APIResponse(
        success=True,
        data=new_student,
        message="Estudiante registrado exitosamente para el Chatbot."
    )

@router.get("", response_model=APIResponse[list[UserRead]])
async def list_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    role_name: str | None = None,
    document: str | None = None,
    current_user: UserRead = Depends(require_role(["superadmin", "admin"])),
    db: AsyncSession = Depends(get_db)
):
    """Listar usuarios con paginación y filtros (Solo Admin)."""
    query = select(User)
    count_query = select(func.count()).select_from(User)
    
    if document:
        query = query.where(User.document_number.ilike(f"%{document}%"))
        count_query = count_query.where(User.document_number.ilike(f"%{document}%"))
        
    if role_name:
        query = query.join(Role).where(Role.name == role_name)
        count_query = count_query.join(Role).where(Role.name == role_name)
        
    # Count total
    total_result = await db.execute(count_query)
    total = total_result.scalar_one()
    
    # Pagination
    offset = (page - 1) * page_size
    query = query.limit(page_size).offset(offset)
    
    # Execute query
    result = await db.execute(query)
    users = result.scalars().all()
    
    pages = (total + page_size - 1) // page_size
    
    return APIResponse(
        success=True,
        data=users,
        meta=Meta(page=page, page_size=page_size, total=total, pages=pages),
        message="Usuarios obtenidos correctamente."
    )

@router.get("/{user_id}", response_model=APIResponse[UserRead])
async def get_user(
    user_id: str,
    current_user: UserRead = Depends(require_role(["superadmin", "admin"])),
    db: AsyncSession = Depends(get_db)
):
    """Obtiene el detalle de un usuario específico."""
    result = await db.execute(select(User).where(User.id == user_id, User.is_deleted == False))
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado.")
        
    return APIResponse(success=True, data=user)

@router.put("/{user_id}", response_model=APIResponse[UserRead])
async def update_user(
    user_id: str,
    data: UserUpdate,
    current_user: UserRead = Depends(require_role(["superadmin", "admin"])),
    db: AsyncSession = Depends(get_db)
):
    """Actualiza la información de un usuario."""
    result = await db.execute(select(User).where(User.id == user_id, User.is_deleted == False))
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado.")
        
    update_data = data.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(user, key, value)
        
    await db.commit()
    await db.refresh(user)
    
    return APIResponse(success=True, data=user, message="Usuario actualizado exitosamente.")

@router.patch("/{user_id}/password", response_model=APIResponse[dict])
async def change_password(
    user_id: str,
    data: UserPasswordUpdate,
    current_user: UserRead = Depends(require_role(["superadmin", "admin"])),
    db: AsyncSession = Depends(get_db)
):
    """Cambia la contraseña de un usuario."""
    result = await db.execute(select(User).where(User.id == user_id, User.is_deleted == False))
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado.")
        
    user.password_hash = hash_password(data.password)
    await db.commit()
    
    return APIResponse(success=True, data={"user_id": user_id}, message="Contraseña actualizada exitosamente.")

@router.delete("/{user_id}", response_model=APIResponse[dict])
async def delete_user(
    user_id: str,
    current_user: UserRead = Depends(require_role(["superadmin", "admin"])),
    db: AsyncSession = Depends(get_db)
):
    """Realiza un borrado lógico (soft delete) del usuario."""
    result = await db.execute(select(User).where(User.id == user_id, User.is_deleted == False))
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado.")
        
    user.is_deleted = True
    user.is_active = False
    user.deleted_at = datetime.utcnow()
    
    await db.commit()
    
    return APIResponse(success=True, data={"user_id": user_id}, message="Usuario eliminado correctamente.")
