import uuid
from datetime import datetime

from pydantic import BaseModel, model_validator

from app.models.base import TicketPriority, TicketStatus
from app.schemas.user import UserResponse
from app.schemas.group import GroupResponse


class TicketCreate(BaseModel):
    title: str
    description: str
    priority: TicketPriority
    assigned_group_id: uuid.UUID
    assigned_user_id: uuid.UUID | None = None


class TicketUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    status: TicketStatus | None = None
    priority: TicketPriority | None = None
    assigned_group_id: uuid.UUID | None = None
    assigned_user_id: uuid.UUID | None = None

    @model_validator(mode="before")
    @classmethod
    def prevent_null_group(cls, values):
        if isinstance(values, dict) and "assigned_group_id" in values and values["assigned_group_id"] is None:
            raise ValueError("assigned_group_id cannot be null")
        return values


class SlaStatus(BaseModel):
    target_minutes: int | None
    elapsed_minutes: int
    percentage: float
    is_breached: bool
    is_at_risk: bool
    remaining_minutes: int | None
    is_resolved: bool = False
    outcome: str | None = None


class MttaStatus(BaseModel):
    target_minutes: int | None
    elapsed_minutes: int
    percentage: float
    is_breached: bool
    is_met: bool
    is_pending: bool


class TicketResponse(BaseModel):
    id: uuid.UUID
    ticket_number: str
    title: str
    description: str
    status: TicketStatus
    priority: TicketPriority
    assigned_group_id: uuid.UUID | None
    assigned_group_name: str | None = None
    assigned_user_id: uuid.UUID | None
    assigned_user_name: str | None = None
    created_by_id: uuid.UUID
    created_by_name: str | None = None
    created_at: datetime
    updated_at: datetime
    resolved_at: datetime | None
    first_assigned_at: datetime | None
    sla_target_minutes: int | None
    sla_target_assign_minutes: int | None = None

    model_config = {"from_attributes": True}


class TicketListResponse(BaseModel):
    id: uuid.UUID
    ticket_number: str
    title: str
    status: TicketStatus
    priority: TicketPriority
    assigned_group_id: uuid.UUID | None
    assigned_group_name: str | None = None
    assigned_user_id: uuid.UUID | None
    assigned_user_name: str | None = None
    created_by_id: uuid.UUID
    created_by_name: str | None = None
    created_at: datetime
    sla_target_minutes: int | None
    sla_target_assign_minutes: int | None = None

    model_config = {"from_attributes": True}


class TicketDetailResponse(TicketResponse):
    notes: list = []
    attachments: list = []
    audit_log: list = []
    sla_status: SlaStatus | None = None
    mtta_status: MttaStatus | None = None
