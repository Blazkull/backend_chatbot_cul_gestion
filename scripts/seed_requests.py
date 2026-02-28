import asyncio
import os
import sys
import uuid
import random
from datetime import datetime, timedelta

# Append backend path so we can import app modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'backend')))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.db.session import async_session
from app.models.role import Role
from app.models.user import User
from app.models.conversation import Conversation
from app.models.message import Message
from app.models.request_type import RequestType, RequestStatus
from app.models.academic_request import AcademicRequest
from app.models.approval_flow import ApprovalFlow
from app.models.audit_log import AuditLog
from sqlalchemy import select

async def seed_academic_requests():
    async with async_session() as db:
        print("Buscando usuarios, tipos de solicitud y estados...")
        
        # Obtener un usuario (estudiante)
        result_user = await db.execute(select(User).limit(10))
        users = result_user.scalars().all()
        if not users:
            print("No hay usuarios en la base de datos. Creando un estudiante de prueba...")
            # Get 'estudiante' role
            result_role = await db.execute(select(Role).where(Role.name == "estudiante"))
            role = result_role.scalar_one_or_none()
            if not role:
                print("Error: Role 'estudiante' no encontrado.")
                return
            student = User(
                role_id=role.id,
                document_type="CC",
                document_number="1140810234",
                first_name="Test",
                last_name="Student",
                email="test.student@ul.edu.co",
                is_active=True,
                data_processing_consent=True
            )
            db.add(student)
            await db.commit()
            await db.refresh(student)
            users = [student]

        # Obtener tipos de solicitud
        result_types = await db.execute(select(RequestType))
        req_types = result_types.scalars().all()
        if not req_types:
            print("Error: No hay RequestTypes en la bd. Ejecuta el seed base primero.")
            return

        # Obtener estados
        result_statuses = await db.execute(select(RequestStatus))
        req_statuses = result_statuses.scalars().all()
        if not req_statuses:
            print("Error: No hay RequestStatus en la bd. Ejecuta el seed base primero.")
            return

        print(f"Encontrados {len(req_types)} tipos y {len(req_statuses)} estados.")

        # Generar solicitudes dummy
        mock_data = [
            {"notes": "Solicita reintegro al programa. Motivo: Viaje finalizado.", "priority": 1},
            {"notes": "Frustración por cruce de horarios. Pide cambio urgente.", "priority": 2},
            {"notes": "Pide constancia de matrícula activa actual para la empresa.", "priority": 0},
            {"notes": "Queja sobre plataforma caída durante parcial. Solicita reapertura.", "priority": 3},
            {"notes": "Retoma estudios. Todo fluyó bien.", "priority": 1}
        ]

        # Verificar cuantas hay para no duplicar si ya exiten
        result_exist = await db.execute(select(AcademicRequest).limit(1))
        exist = result_exist.scalar_one_or_none()
        if exist:
            print("Ya existen AcademicRequests en la base de datos. Saltando seeding para evitar duplicados.")
            return

        print("Generando 5 solicitudes de prueba...")
        for i, data in enumerate(mock_data):
            radicado = f"RAD-2026-0000{i+1}"
            r_type = random.choice(req_types)
            r_status = random.choice(req_statuses)
            user = random.choice(users)

            new_req = AcademicRequest(
                radicado_number=radicado,
                user_id=user.id,
                request_type_id=r_type.id,
                status_id=r_status.id,
                form_data={"motivo": f"Dato de prueba {i}", "adicional": "Extra"},
                priority=data["priority"],
                notes=data["notes"],
                current_approval_level=0,
                created_at=datetime.utcnow() - timedelta(days=random.randint(0, 5))
            )
            db.add(new_req)

        await db.commit()
        print("Solicitudes generadas y guardadas exitosamente en la base de datos.")

if __name__ == "__main__":
    asyncio.run(seed_academic_requests())
