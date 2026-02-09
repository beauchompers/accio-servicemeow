import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel

from app.models.base import ActorType


class AuditLogResponse(BaseModel):
    id: uuid.UUID
    ticket_id: uuid.UUID
    ticket_number: str | None = None
    actor_id: uuid.UUID | None
    actor_type: ActorType
    actor_name: str | None = None
    action: str
    field_changed: str | None
    old_value: str | None
    new_value: str | None
    metadata: dict[str, Any] | None = None
    created_at: datetime

    model_config = {"from_attributes": True}
