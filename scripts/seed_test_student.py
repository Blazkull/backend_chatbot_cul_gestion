import asyncio
import os
import sys

# Append backend path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'backend')))

from app.db.session import SessionLocal
from app.models.user import User
from app.models.role import Role
from sqlalchemy import select

async def create_test_student():
    async with SessionLocal() as db:
        # Get 'estudiante' role
        result = await db.execute(select(Role).where(Role.name == "estudiante"))
        role = result.scalar_one_or_none()
        
        if not role:
            print("Role 'estudiante' no encontrado.")
            return

        # Check if user exists
        result = await db.execute(select(User).where(User.document_number == "123456789"))
        user = result.scalar_one_or_none()

        if not user:
            print("Creando usuario de prueba 123456789...")
            new_user = User(
                role_id=role.id,
                document_type="CC",
                document_number="123456789",
                first_name="Juan",
                last_name="Pérez",
                email="juan.perez@ul.edu.co",
                is_active=True,
                data_processing_consent=True
            )
            db.add(new_user)
            await db.commit()
            print("Usuario creado exitosamente.")
        else:
            print("El usuario de prueba 123456789 ya existe.")

if __name__ == "__main__":
    asyncio.run(create_test_student())
