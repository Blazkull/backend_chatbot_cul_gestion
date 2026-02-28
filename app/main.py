from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.config import get_settings
from app.middleware.error_handler import ErrorHandlerMiddleware
from app.routers import health, auth, requests, chat, users, request_types, nlp, admin
from app.db.session import async_session

settings = get_settings()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    print(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    print(f"Environment: {settings.ENVIRONMENT}")
    
    # Validar conexión a la Base de Datos
    try:
        async with async_session() as session:
            await session.execute(text("SELECT 1"))
        print("✅ Conexión a Base de Datos (Supabase PostgreSQL): EXITOSA")
    except Exception as e:
        print(f"❌ Error conectando a BD: No se pudo verificar la conexión - {e}")

    yield
    print("Shutting down...")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    lifespan=lifespan,
)

# Middleware
app.add_middleware(ErrorHandlerMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers — all under /api/v1
API_PREFIX = "/api/v1"
app.include_router(health.router, prefix=API_PREFIX)
app.include_router(auth.router, prefix=API_PREFIX)
app.include_router(users.router, prefix=API_PREFIX)
app.include_router(requests.router, prefix=API_PREFIX)
app.include_router(request_types.router, prefix=API_PREFIX)
app.include_router(chat.router, prefix=API_PREFIX)
app.include_router(nlp.router, prefix=API_PREFIX)
app.include_router(admin.router, prefix=API_PREFIX)



@app.get("/")
async def root():
    return {"app": settings.APP_NAME, "version": settings.APP_VERSION}
