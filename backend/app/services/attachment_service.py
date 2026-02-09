import os
import uuid

import aiofiles
import magic
from fastapi import HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import CurrentUser
from app.config import settings
from app.models.attachment import Attachment
from app.models.base import ActorType, UserRole
from app.models.ticket import Ticket
from app.services import audit_service

ALLOWED_CONTENT_TYPES = {
    # Images
    "image/png", "image/jpeg", "image/gif", "image/webp",
    # Documents
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "text/plain", "text/csv",
    "application/json", "application/xml", "text/yaml",
    # Archives
    "application/zip",
}


async def upload_file(
    db: AsyncSession,
    current_user: CurrentUser,
    ticket_id: uuid.UUID,
    file: UploadFile,
    note_id: uuid.UUID | None = None,
) -> Attachment:
    """Upload a file attachment to a ticket."""
    # Verify ticket exists
    result = await db.execute(select(Ticket).where(Ticket.id == ticket_id))
    ticket = result.scalar_one_or_none()
    if not ticket:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found")

    # Validate content type
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type {file.content_type} not allowed",
        )

    # Validate file size
    max_bytes = settings.max_upload_size_mb * 1024 * 1024
    content = await file.read()

    # Sniff actual content type — don't trust client header
    detected_type = magic.from_buffer(content, mime=True)
    if detected_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Detected file type {detected_type} not allowed",
        )

    if len(content) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File size exceeds {settings.max_upload_size_mb}MB limit",
        )

    # Generate storage path
    file_uuid = str(uuid.uuid4())
    original_filename = file.filename or "unnamed"
    storage_filename = f"{file_uuid}_{original_filename}"
    upload_dir = os.path.join(settings.upload_dir, str(ticket_id))
    os.makedirs(upload_dir, exist_ok=True)
    file_path = os.path.join(upload_dir, storage_filename)

    # Prevent path traversal via crafted original_filename
    if not os.path.realpath(file_path).startswith(os.path.realpath(settings.upload_dir) + os.sep):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid filename",
        )

    # Write to disk
    async with aiofiles.open(file_path, "wb") as f:
        await f.write(content)

    # Create DB record
    attachment = Attachment(
        ticket_id=ticket_id,
        note_id=note_id,
        filename=storage_filename,
        original_filename=original_filename,
        file_path=file_path,
        file_size=len(content),
        content_type=file.content_type or "application/octet-stream",
        uploaded_by_id=current_user.user.id,
    )
    db.add(attachment)
    await db.flush()

    # Log audit
    actor_type = ActorType.api_key if current_user.auth_type == "api_key" else ActorType.user
    await audit_service.log_action(
        db=db,
        ticket_id=ticket_id,
        actor_id=current_user.user.id,
        actor_type=actor_type,
        action="file_uploaded",
        metadata={"attachment_id": str(attachment.id), "filename": original_filename},
    )

    return attachment


async def list_attachments(
    db: AsyncSession,
    ticket_id: uuid.UUID,
) -> list[Attachment]:
    """List all attachments for a ticket."""
    result = await db.execute(
        select(Attachment)
        .where(Attachment.ticket_id == ticket_id)
        .order_by(Attachment.uploaded_at.asc())
    )
    return list(result.scalars().all())


async def get_attachment(
    db: AsyncSession,
    attachment_id: uuid.UUID,
) -> Attachment:
    """Get a single attachment by ID."""
    result = await db.execute(select(Attachment).where(Attachment.id == attachment_id))
    attachment = result.scalar_one_or_none()
    if not attachment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attachment not found")
    return attachment


async def delete_attachment(
    db: AsyncSession,
    current_user: CurrentUser,
    attachment_id: uuid.UUID,
) -> None:
    """Delete an attachment (removes file from disk and DB record)."""
    attachment = await get_attachment(db, attachment_id)

    # Only the uploader or an admin can delete
    if (
        current_user.user.id != attachment.uploaded_by_id
        and current_user.user.role != UserRole.admin
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the uploader or an admin can delete this attachment",
        )

    # Remove file from disk
    if os.path.exists(attachment.file_path):
        os.remove(attachment.file_path)

    # Log audit before deleting
    actor_type = ActorType.api_key if current_user.auth_type == "api_key" else ActorType.user
    await audit_service.log_action(
        db=db,
        ticket_id=attachment.ticket_id,
        actor_id=current_user.user.id,
        actor_type=actor_type,
        action="file_deleted",
        metadata={"attachment_id": str(attachment.id), "filename": attachment.original_filename},
    )

    await db.delete(attachment)
    await db.flush()
