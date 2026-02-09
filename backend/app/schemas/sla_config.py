from pydantic import BaseModel

from app.models.base import TicketPriority


class SlaConfigItem(BaseModel):
    priority: TicketPriority
    target_assign_minutes: int
    target_resolve_minutes: int

    model_config = {"from_attributes": True}


class SlaConfigUpdate(BaseModel):
    configs: list[SlaConfigItem]
