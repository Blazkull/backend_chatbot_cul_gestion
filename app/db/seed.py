import asyncio
from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import engine
from app.models.request_type import RequestType
from app.models.conversation import ConversationStatus, Conversation
from app.models.message import Message

async def seed_data():
    async with AsyncSession(engine) as session:
        # Seed conversation statuses if not exist
        statuses = [
            {"name": "Activa", "slug": "active", "description": "Conversación en curso"},
            {"name": "Cerrada", "slug": "closed", "description": "Conversación finalizada"},
        ]
        
        for status_data in statuses:
            stmt = select(ConversationStatus).where(ConversationStatus.slug == status_data["slug"])
            result = await session.execute(stmt)
            status = result.scalar_one_or_none()
            if not status:
                new_status = ConversationStatus(**status_data)
                session.add(new_status)
                try:
                    await session.commit()
                    print(f"Added ConversationStatus: {status_data['name']}")
                except Exception as e:
                    await session.rollback()
                    print(f"Skipped ConversationStatus {status_data['name']}: already exists.")
        
        # Seed request types
        request_types = [
            {
                "name": "Homologación",
                "slug": "homologacion",
                "description": "Estudio de transferencia externa o interna",
                "requirements": [
                    "Certificados de notas de la institución de procedencia.",
                    "Diploma de carrera a homologar.",
                    "Documento de identidad ambas caras.",
                    "Contenido programático.",
                    "Resultados saber 11.",
                    "Foto 3x4.",
                ],
                "expected_response_days": 10,
                "needs_auth": True
            },
            {
                "name": "Retiro de asignatura",
                "slug": "retiro-asignatura",
                "description": "Retiro justificado de una asignatura",
                "requirements": [
                    "Justificación médica o laboral válida.",
                    "Diligenciar el formulario respectivo."
                ],
                "expected_response_days": 2,
                "needs_auth": True
            },
            {
                "name": "Habilitación",
                "slug": "habilitacion",
                "description": "Habilitación de asignaturas perdidas",
                "requirements": [
                    "Soporte de pago Original."
                ],
                "expected_response_days": 3,
                "needs_auth": True
            }
        ]

        for rt_data in request_types:
            stmt = select(RequestType).where(RequestType.slug == rt_data["slug"])
            result = await session.execute(stmt)
            rt = result.scalar_one_or_none()
            if not rt:
                new_rt = RequestType(
                    name=rt_data["name"],
                    slug=rt_data["slug"],
                    description=rt_data["description"],
                    requirements=rt_data["requirements"],
                    expected_response_days=rt_data["expected_response_days"],
                    needs_auth=rt_data["needs_auth"],
                    is_active=True
                )
                session.add(new_rt)
                try:
                    await session.commit()
                    print(f"Added RequestType: {rt_data['name']}")
                except Exception as e:
                    await session.rollback()
                    print(f"Skipped RequestType {rt_data['name']}: already exists.")

        print("Seeding completed successfully!")

if __name__ == "__main__":
    asyncio.run(seed_data())
