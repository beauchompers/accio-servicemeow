import uuid
from datetime import datetime

from pydantic import BaseModel


class AttachmentResponse(BaseModel):
    id: uuid.UUID
    ticket_id: uuid.UUID
    note_id: uuid.UUID | None
    filename: str
    original_filename: str
    file_size: int
    content_type: str
    uploaded_by_id: uuid.UUID
    uploaded_by_name: str = ""
    uploaded_at: datetime

    model_config = {"from_attributes": True}
