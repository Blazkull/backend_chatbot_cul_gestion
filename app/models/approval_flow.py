import uuid
from sqlmodel import Field
from sqlalchemy import Column, String, Integer, Boolean, Text, CheckConstraint
from app.db.base import BaseDBModel


class ApprovalFlow(BaseDBModel, table=True):
    __tablename__ = "approval_flows"

    request_type_id: uuid.UUID = Field(foreign_key="request_types.id", nullable=False)
    approver_role_id: uuid.UUID = Field(foreign_key="roles.id", nullable=False)
    step_level: int = Field(default=1)
    step_name: str = Field(sa_column=Column(String(100), nullable=False))
    is_active: bool = Field(default=True)


class ApprovalStep(BaseDBModel, table=True):
    __tablename__ = "approval_steps"
    __table_args__ = (
        CheckConstraint(
            "decision IN ('pendiente', 'aprobado', 'rechazado')",
            name="ck_approval_steps_decision"
        ),
    )

    request_id: uuid.UUID = Field(foreign_key="academic_requests.id", nullable=False)
    flow_id: uuid.UUID = Field(foreign_key="approval_flows.id", nullable=False)
    approver_id: uuid.UUID | None = Field(default=None, foreign_key="users.id")
    step_level: int = Field(nullable=False)
    decision: str | None = Field(default="pendiente", max_length=20)
    comments: str | None = Field(default=None)
    decided_at: str | None = Field(default=None)
