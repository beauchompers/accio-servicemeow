import uuid
from datetime import datetime

from pydantic import BaseModel

class GroupCreate(BaseModel):
    name: str
    description: str = ""


class GroupUpdate(BaseModel):
    name: str | None = None
    description: str | None = None


class GroupMemberAdd(BaseModel):
    user_id: uuid.UUID
    is_lead: bool = False


class GroupMemberResponse(BaseModel):
    user_id: uuid.UUID
    username: str
    full_name: str
    is_lead: bool
    joined_at: datetime

    model_config = {"from_attributes": True}


class GroupResponse(BaseModel):
    id: uuid.UUID
    name: str
    description: str
    member_count: int = 0
    created_at: datetime
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}


class GroupDetailResponse(GroupResponse):
    members: list[GroupMemberResponse] = []
