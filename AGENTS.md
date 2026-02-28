# ⚙️ AGENTS.md — Backend (FastAPI + SQLModel)

## Tech Stack
- **Runtime**: Python 3.11+
- **Framework**: FastAPI 0.115+
- **ORM**: SQLModel (individual file per model)
- **Validation**: Pydantic V2 (individual file per schema)
- **Auth**: JWT (PyJWT) + bcrypt (passlib)
- **DB**: PostgreSQL 17 via Supabase (RLS activo)
- **WebSocket**: FastAPI WebSocket
- **PDF**: reportlab
- **Email**: smtplib / aiosmtplib
- **IA**: httpx → HuggingFace Space API
- **Entorno virtual**: `.venv` (obligatorio)

## Estructura POO
```
apps/backend/
├── .venv/                    # Entorno virtual Python
├── requirements.txt          # Dependencias
├── .env                      # Variables de entorno (NO commitear)
├── .env.example              # Template de variables
└── app/
    ├── __init__.py
    ├── main.py               # FastAPI app + CORS + lifespan
    ├── config.py             # Pydantic Settings
    ├── db/
    │   ├── session.py        # Async engine + SessionLocal
    │   └── base.py           # SQLModel Base
    ├── models/               # SQLModel models (1 archivo = 1 modelo)
    │   ├── user.py
    │   ├── role.py
    │   ├── conversation.py
    │   ├── message.py
    │   ├── academic_request.py
    │   ├── request_type.py
    │   ├── request_status.py
    │   ├── approval_flow.py
    │   ├── approval_step.py
    │   └── ...
    ├── schemas/              # Pydantic V2 (1 archivo = 1 resource)
    │   ├── user.py
    │   ├── auth.py
    │   ├── conversation.py
    │   ├── academic_request.py
    │   └── ...
    ├── routers/              # Endpoints RESTful
    │   ├── auth.py           # POST /auth/login, /auth/register, /auth/validate-cedula
    │   ├── users.py          # CRUD /users/
    │   ├── solicitudes.py    # CRUD /solicitudes/
    │   ├── conversaciones.py # CRUD /conversations/
    │   ├── admin.py          # Dashboard data
    │   ├── chat.py           # WebSocket /ws/chat
    │   └── health.py         # GET /health
    ├── services/             # Lógica de negocio
    │   ├── auth_service.py
    │   ├── ai_service.py
    │   ├── pdf_service.py
    │   ├── email_service.py
    │   └── radicado_service.py
    ├── middleware/
    │   └── error_handler.py
    ├── dependencies/         # FastAPI DI
    │   ├── auth.py           # get_current_user, require_role
    │   └── database.py       # get_db session
    └── utils/
        └── logger.py
```

## Respuesta API Estandarizada
```python
class APIResponse(BaseModel):
    success: bool
    data: Any = None
    message: str = ""
    errors: list[dict] | None = None
    meta: dict | None = None  # paginación, etc.
```

## HTTP Status Codes
| Code | Uso |
|---|---|
| 200 | GET exitoso |
| 201 | POST/creación exitosa |
| 204 | DELETE exitoso |
| 400 | Solicitud inválida |
| 401 | No autenticado |
| 403 | No autorizado (rol insuficiente) |
| 404 | Recurso no encontrado |
| 409 | Conflicto (duplicado) |
| 422 | Error de validación |
| 500 | Error interno |

## Endpoints (v1)
```
/api/v1/auth/login           POST    # Login por cédula + password
/api/v1/auth/register        POST    # Registro de usuario
/api/v1/auth/validate-cedula POST    # Verificar si cédula existe
/api/v1/users/               GET     # Listar usuarios (admin)
/api/v1/users/{id}           GET     # Detalle usuario
/api/v1/users/{id}           PUT     # Actualizar usuario
/api/v1/solicitudes/         POST    # Crear solicitud
/api/v1/solicitudes/         GET     # Listar (filtros: cédula, tipo, estado)
/api/v1/solicitudes/{rad}    GET     # Detalle por radicado
/api/v1/solicitudes/{id}/approve  PUT  # Aprobar paso
/api/v1/solicitudes/{id}/reject   PUT  # Rechazar paso
/api/v1/conversations/       POST    # Nueva conversación
/api/v1/conversations/       GET     # Listar por cédula
/api/v1/conversations/{id}   PUT     # Cerrar conversación
/api/v1/conversations/{id}/messages GET  # Mensajes
/api/v1/admin/dashboard      GET     # Métricas dashboard
/api/v1/admin/token-usage    GET     # Uso de tokens IA
/ws/chat                     WS      # WebSocket chat
/api/v1/health               GET     # Health check
```

## Variables de Entorno
```
ENVIRONMENT=development
PORT=8000
JWT_SECRET_KEY=<super_secret_key>
JWT_EXPIRATION_MINUTES=1440
SUPABASE_URL=https://jursuxymhndqgzxpfpod.supabase.co
SUPABASE_SERVICE_KEY=...
SUPABASE_ANON_KEY=...
DATABASE_URL=postgresql+asyncpg://...
HF_TOKEN_READ=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
HF_SPACE_API_URL=https://jeacosta37-chatbot-ai-solicitudes.hf.space/generate
CORS_ORIGINS=http://localhost:5173
SMTP_HOST=smtp.yopmail.com
SMTP_PORT=587
```

## Reglas
- Siempre async/await
- SQLModel: 1 archivo por modelo en `models/`
- Pydantic: 1 archivo por schema en `schemas/`
- Passwords: bcrypt via passlib
- JWT: PyJWT con HS256
- Todo versionado en `/api/v1/`
- `.venv` obligatorio, `requirements.txt` actualizado

## Skills
api-design-principles, fastapi-pro, postgresql, supabase-postgres-best-practices, auth-implementation-patterns
