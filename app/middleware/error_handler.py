from fastapi import Request, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
import traceback

from app.schemas.common import APIResponse


class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    """Global exception handler → APIResponse format."""

    async def dispatch(self, request: Request, call_next):
        try:
            response = await call_next(request)
            return response
        except Exception as exc:
            error_detail = str(exc)
            print(f"[ERROR] {request.method} {request.url.path}: {error_detail}")
            traceback.print_exc()
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content=APIResponse(
                    success=False,
                    message="Error interno del servidor.",
                    errors=[{"detail": error_detail}],
                ).model_dump(),
            )
