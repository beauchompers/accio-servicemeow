import uuid
from datetime import datetime

from pydantic import BaseModel


class NoteCreate(BaseModel):
    content: str
    is_internal: bool = False


class NoteUpdate(BaseModel):
    content: str


class NoteResponse(BaseModel):
    id: uuid.UUID
    ticket_id: uuid.UUID
    author_id: uuid.UUID
    author_name: str = ""
    content: str
    is_internal: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
