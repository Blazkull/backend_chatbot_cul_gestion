from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Configuración centralizada del backend."""

    # --- App ---
    APP_NAME: str = "Chatbot Gestión Académica CUL"
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    PORT: int = 8000

    # --- JWT ---
    JWT_SECRET_KEY: str = "super_secret_change_me"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_MINUTES: int = 60  # 1h

    # --- Supabase ---
    SUPABASE_URL: str = ""
    SUPABASE_SERVICE_KEY: str = ""
    SUPABASE_ANON_KEY: str = ""

    # --- Database (asyncpg) ---
    DATABASE_URL: str = ""

    # --- HuggingFace AI ---
    HF_TOKEN_READ: str = ""
    HF_TOKEN_WRITE: str = ""
    HF_SPACE_API_URL: str = "https://jeacosta37-chatbot-ai-solicitudes.hf.space/generate"

    # --- CORS ---
    CORS_ORIGINS: str = "http://localhost:5173"

    # --- Resend (Email API — reemplaza SMTP) ---
    RESEND_API_KEY: str = ""
    EMAIL_FROM: str = "onboarding@resend.dev"

    # --- Logging ---
    LOG_LEVEL: str = "DEBUG"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",")]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
