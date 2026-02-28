from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.dependencies.auth import get_current_user
from app.schemas.auth import (
    LoginRequest, RegisterRequest, ValidateCedulaRequest,
    ValidateCedulaResponse, TokenResponse, UserRead,
)
from app.schemas.common import APIResponse
from app.services.auth_service import (
    authenticate_user, authenticate_student, register_user, get_user_by_document,
    create_access_token,
)

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/login")
async def login(data: LoginRequest, db: AsyncSession = Depends(get_db)):
    """Login con número de documento o correo + password."""
    user, error = await authenticate_user(
        db, 
        data.password, 
        document_number=data.document_number, 
        email=data.email
    )
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=error)

    token = create_access_token({"sub": str(user.id), "email": user.email})
    return APIResponse(
        success=True,
        data=TokenResponse(
            access_token=token,
            user={
                "id": str(user.id),
                "first_name": user.first_name,
                "last_name": user.last_name,
                "email": user.email,
                "document_number": user.document_number,
            },
        ).model_dump(),
        message="Inicio de sesión exitoso.",
    )


@router.post("/login-student")
async def login_student(data: ValidateCedulaRequest, db: AsyncSession = Depends(get_db)):
    """Login para ESTUDIANTES usando solo el número de documento."""
    user, error = await authenticate_student(db, data.document_number)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=error)

    token = create_access_token({"sub": str(user.id), "email": user.email})
    return APIResponse(
        success=True,
        data=TokenResponse(
            access_token=token,
            user={
                "id": str(user.id),
                "first_name": user.first_name,
                "last_name": user.last_name,
                "email": user.email,
                "document_number": user.document_number,
            },
        ).model_dump(),
        message="Inicio de sesión de estudiante exitoso.",
    )


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(data: RegisterRequest, db: AsyncSession = Depends(get_db)):
    """Registro de usuario → Supabase Auth + BD local."""
    user, error = await register_user(db, data)
    if not user:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=error)

    token = create_access_token({"sub": str(user.id), "email": user.email})
    return APIResponse(
        success=True,
        data=TokenResponse(
            access_token=token,
            user={
                "id": str(user.id),
                "first_name": user.first_name,
                "last_name": user.last_name,
                "email": user.email,
                "document_number": user.document_number,
            },
        ).model_dump(),
        message="Usuario registrado exitosamente.",
    )


@router.post("/validate-cedula")
async def validate_cedula(data: ValidateCedulaRequest, db: AsyncSession = Depends(get_db)):
    """Verificar si un número de cédula existe en el sistema e iniciar sesión automática."""
    user = await get_user_by_document(db, data.document_number)
    if user:
        token = create_access_token({"sub": str(user.id), "email": user.email})
        return APIResponse(
            success=True,
            data=ValidateCedulaResponse(
                exists=True,
                user={"first_name": user.first_name, "last_name": user.last_name},
                access_token=token
            ).model_dump(),
        )
    return APIResponse(
        success=True,
        data=ValidateCedulaResponse(exists=False).model_dump(),
    )


@router.get("/me", response_model=APIResponse[UserRead])
async def get_me(current_user: UserRead = Depends(get_current_user)):
    """
    Obtener el perfil del usuario autenticado.
    (Activa el botón 'Authorize' en Swagger UI).
    """
    return APIResponse(
        success=True,
        data=current_user,
        message="Perfil obtenido exitosamente.",
    )
