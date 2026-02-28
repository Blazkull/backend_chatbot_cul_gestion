from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.db.session import get_db
from app.dependencies.auth import get_current_user, require_role
from app.models.academic_request import AcademicRequest
from app.models.request_type import RequestType, RequestStatus
from app.schemas.auth import UserRead
from app.schemas.common import APIResponse

router = APIRouter(prefix="/admin", tags=["Admin CRM"])

@router.get("/dashboard", response_model=APIResponse[dict])
async def get_dashboard_metrics(
    current_user: UserRead = Depends(require_role(["superadmin", "admin"])),
    db: AsyncSession = Depends(get_db)
):
    """(Admin) Retorna métricas clave para popular gráficas en el CRM."""
    
    # 1. Total de solicitudes
    total_query = select(func.count()).select_from(AcademicRequest).where(AcademicRequest.is_deleted == False)
    total_requests = (await db.execute(total_query)).scalar_one()
    
    # En un caso real con PostgreSQL, harías un GROUP BY:
    # select(RequestStatus.name, func.count(AcademicRequest.id)) ... group_by(RequestStatus.name)
    # Para el MVP, recuperamos las solicitudes y las contamos en memoria para evitar errores de ORM en la vista rápida
    result = await db.execute(select(AcademicRequest.status_id, AcademicRequest.request_type_id).where(AcademicRequest.is_deleted == False))
    all_reqs = result.all()
    
    # Buscar mappings
    status_result = await db.execute(select(RequestStatus))
    statuses = {s.id: s.name for s in status_result.scalars().all()}
    
    type_result = await db.execute(select(RequestType))
    types = {t.id: t.name for t in type_result.scalars().all()}
    
    # 2. Agrupamiento por Estado
    status_counts = {}
    type_counts = {}
    
    for row in all_reqs:
        s_name = statuses.get(row.status_id, "Desconocido")
        t_name = types.get(row.request_type_id, "Desconocido")
        
        status_counts[s_name] = status_counts.get(s_name, 0) + 1
        type_counts[t_name] = type_counts.get(t_name, 0) + 1
        
    # Formato adaptado para Recharts: [{"name": "Aprobada", "value": 10}, ...]
    data_by_status = [{"name": k, "value": v} for k, v in status_counts.items()]
    data_by_type = [{"name": k, "value": v} for k, v in type_counts.items()]
    
    return APIResponse(
        success=True,
        data={
            "total_requests": total_requests,
            "requests_by_status": data_by_status,
            "requests_by_type": data_by_type,
            # Tokens are placeholder until token calculation is implemented in Chatbot LLM calls
            "total_tokens_used": 14500
        },
        message="Métricas del Dashboard obtenidas satisfactoriamente."
    )
