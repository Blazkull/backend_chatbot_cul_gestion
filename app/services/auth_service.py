"""Auth service — user registration via Supabase Auth + local DB sync."""

from datetime import datetime, timedelta
from jose import jwt, JWTError
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from supabase import create_client, Client

from app.config import get_settings
from app.models.user import User
from app.models.role import Role
from app.schemas.auth import RegisterRequest

settings = get_settings()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Supabase client (lazy-loaded — no crash if key is invalid)
_supabase_client: Client | None = None


def get_supabase() -> Client | None:
    global _supabase_client
    if _supabase_client is None and settings.SUPABASE_URL and settings.SUPABASE_SERVICE_KEY:
        try:
            _supabase_client = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)
        except Exception as e:
            print(f"[WARN] No se pudo conectar a Supabase Auth: {e}")
    return _supabase_client


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=settings.JWT_EXPIRATION_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    except JWTError:
        return None


async def get_user_by_document(db: AsyncSession, document_number: str) -> User | None:
    result = await db.execute(
        select(User).where(
            User.document_number == document_number,
            User.is_deleted == False,
        )
    )
    return result.scalar_one_or_none()


async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
    result = await db.execute(
        select(User).where(
            User.email == email,
            User.is_deleted == False,
        )
    )
    return result.scalar_one_or_none()


async def get_user_by_id(db: AsyncSession, user_id: str) -> User | None:
    result = await db.execute(
        select(User).where(
            User.id == user_id,
            User.is_deleted == False,
        )
    )
    return result.scalar_one_or_none()


async def get_default_role(db: AsyncSession, role_name: str = "estudiante") -> Role | None:
    result = await db.execute(
        select(Role).where(Role.name == role_name, Role.is_deleted == False)
    )
    return result.scalar_one_or_none()


async def register_user(db: AsyncSession, data: RegisterRequest) -> tuple[User | None, str]:
    """
    1. Create user in Supabase Auth
    2. Create user in local DB with supabase_auth_id
    Returns (user, error_message)
    """
    # Check if document already exists
    existing = await get_user_by_document(db, data.document_number)
    if existing:
        return None, "Ya existe un usuario con este número de documento."

    # Get default role
    role = await get_default_role(db)
    if not role:
        return None, "Rol por defecto 'estudiante' no encontrado. Contacte al administrador."

    # 1. Register in Supabase Auth
    supabase = get_supabase()
    supabase_uid = None
    if supabase:
        try:
            auth_response = supabase.auth.admin.create_user({
                "email": data.email,
                "password": data.password,
                "email_confirm": True,
                "user_metadata": {
                    "first_name": data.first_name,
                    "last_name": data.last_name,
                    "document_number": data.document_number,
                }
            })
            supabase_uid = str(auth_response.user.id)
        except Exception as e:
            error_msg = str(e)
            if "already registered" in error_msg.lower():
                return None, "Este correo ya está registrado en el sistema."
            print(f"[WARN] Supabase Auth error (continuing): {error_msg}")
    else:
        print("[WARN] Supabase no disponible, registrando solo en BD local.")

    # 2. Create in local DB
    new_user = User(
        role_id=role.id,
        document_type=data.document_type,
        document_number=data.document_number,
        first_name=data.first_name,
        last_name=data.last_name,
        email=data.email,
        phone=data.phone,
        birth_date=data.birth_date,
        gender=data.gender,
        program=data.program,
        semester=data.semester,
        schedule=data.schedule,
        password_hash=hash_password(data.password),
        supabase_auth_id=supabase_uid,
        data_processing_consent=data.data_processing_consent,
        is_active=True,
    )
    db.add(new_user)
    await db.flush()
    await db.refresh(new_user)

    return new_user, ""


async def authenticate_user(db: AsyncSession, password: str, document_number: str | None = None, email: str | None = None) -> tuple[User | None, str]:
    """
    1. Find user by document number or email
    2. Verify password locally (bcrypt)
    3. Also sign in via Supabase Auth for session
    """
    if email:
        user = await get_user_by_email(db, email)
    elif document_number:
        user = await get_user_by_document(db, document_number)
    else:
        return None, "Se requiere número de documento o correo."
    if not user:
        return None, "Credenciales inválidas."

    if not user.password_hash or not verify_password(password, user.password_hash):
        return None, "Credenciales inválidas."

    if not user.is_active:
        return None, "Tu cuenta está desactivada. Contacta al administrador."

    # Sign in via Supabase Auth for session tracking
    supabase = get_supabase()
    if supabase:
        try:
            supabase.auth.sign_in_with_password({
                "email": user.email,
                "password": password,
            })
        except Exception:
            pass  # Non-blocking

    # Update last login
    user.last_login_at = datetime.utcnow()
    db.add(user)

    return user, ""


async def authenticate_student(db: AsyncSession, document_number: str) -> tuple[User | None, str]:
    """
    1. Find user by document number.
    2. Check if user has the 'estudiante' role.
    3. Grant access without password (student flow).
    """
    user = await get_user_by_document(db, document_number)
    if not user:
        return None, "Estudiante no encontrado."

    if not user.is_active:
        return None, "Tu cuenta está desactivada. Contacta al administrador."

    # Prevent staff/admins from logging in without password
    from sqlalchemy.orm import selectinload
    result = await db.execute(select(Role).where(Role.id == user.role_id))
    role = result.scalar_one_or_none()
    
    if not role or role.name != "estudiante":
        return None, "Este método de inicio de sesión es exclusivo para estudiantes."

    # Update last login
    user.last_login_at = datetime.utcnow()
    db.add(user)

    return user, ""
