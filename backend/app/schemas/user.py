import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.models.base import UserRole


class UserCreate(BaseModel):
    username: str
    email: str
    full_name: str
    password: str
    role: UserRole = UserRole.agent


class UserUpdate(BaseModel):
    email: str | None = None
    full_name: str | None = None
    role: UserRole | None = None
    is_active: bool | None = None
    password: str | None = Field(None, min_length=5)


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(min_length=5)


class UserResponse(BaseModel):
    id: uuid.UUID
    username: str
    email: str
    full_name: str
    role: UserRole
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
