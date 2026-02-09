import math
import os
import uuid

from fastapi import APIRouter, Cookie, Depends, HTTPException, Query, Response, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import CurrentUser, get_current_user
from app.config import settings
from app.database import get_db
from app.services import auth_service
from app.schemas.attachment import AttachmentResponse
from app.schemas.audit_log import AuditLogResponse
from app.schemas.common import PaginatedResponse
from app.schemas.ticket import (
    TicketCreate,
    TicketDetailResponse,
    TicketListResponse,
    TicketResponse,
    TicketUpdate,
)
from app.schemas.ticket_note import NoteCreate, NoteResponse, NoteUpdate
from app.services import attachment_service, audit_service, note_service, sla_service, ticket_service

router = APIRouter()


# ---------------------------------------------------------------------------
# Standalone editor image upload — must be defined before {ticket_id} routes
# so that "images" is not captured as a ticket_id path param.
# ---------------------------------------------------------------------------

EDITOR_IMAGES_DIR = os.path.join(settings.upload_dir, "editor-images")


@router.post("/images")
async def upload_editor_image(
    file: UploadFile,
    current_user: CurrentUser = Depends(get_current_user),
):
    """Upload an image for use in the rich-text editor (not ticket-scoped)."""
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only image files are allowed.",
        )

    os.makedirs(EDITOR_IMAGES_DIR, exist_ok=True)
    safe_filename = f"{uuid.uuid4()}_{os.path.basename(file.filename or 'unnamed')}"
    file_path = os.path.join(EDITOR_IMAGES_DIR, safe_filename)
    # Prevent path traversal via crafted filename
    if not os.path.realpath(file_path).startswith(os.path.realpath(EDITOR_IMAGES_DIR) + os.sep):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid filename.",
        )

    contents = await file.read()
    with open(file_path, "wb") as f:
        f.write(contents)

    return {"url": f"/api/v1/tickets/images/{safe_filename}"}


@router.get("/images/{filename}")
async def serve_editor_image(
    filename: str,
    refresh_token: str | None = Cookie(None),
):
    """Serve an editor image file, authenticated via session cookie."""
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required.",
        )
    try:
        payload = auth_service.decode_token(refresh_token)
        if payload.get("type") != "refresh":
            raise ValueError("not a refresh token")
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session.",
        )

    file_path = os.path.join(EDITOR_IMAGES_DIR, filename)
    # Prevent path traversal
    if not os.path.realpath(file_path).startswith(os.path.realpath(EDITOR_IMAGES_DIR) + os.sep):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid filename.",
        )
    if not os.path.isfile(file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Image not found.",
        )
    return FileResponse(file_path)


# ---------------------------------------------------------------------------
# Attachment routes (non-ticket-scoped) — must be defined before {ticket_id}
# routes so that "attachments" is not captured as a ticket_id path param.
# ---------------------------------------------------------------------------


@router.get(
    "/attachments/{attachment_id}/download",
    response_class=FileResponse,
)
async def download_attachment(
    attachment_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Download an attachment file by attachment ID."""
    attachment = await attachment_service.get_attachment(db, attachment_id)
    # Prevent path traversal via stored file_path
    if not os.path.realpath(attachment.file_path).startswith(os.path.realpath(settings.upload_dir) + os.sep):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file path.",
        )
    return FileResponse(
        path=attachment.file_path,
        filename=attachment.original_filename,
        media_type=attachment.content_type,
    )


@router.delete(
    "/attachments/{attachment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_attachment(
    attachment_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Delete an attachment by ID."""
    await attachment_service.delete_attachment(db, current_user, attachment_id)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ---------------------------------------------------------------------------
# Ticket CRUD
# ---------------------------------------------------------------------------


@router.post("/", response_model=TicketResponse, status_code=status.HTTP_201_CREATED)
async def create_ticket(
    data: TicketCreate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Create a new ticket."""
    ticket = await ticket_service.create_ticket(db, current_user, data)
    await db.commit()
    # Re-fetch with relationships loaded so serialization works after commit
    return await ticket_service.get_ticket(db, ticket.id)


@router.get("/", response_model=PaginatedResponse[TicketListResponse])
async def list_tickets(
    status_filter: str | None = Query(None, alias="status"),
    priority: str | None = Query(None),
    assigned_group_id: uuid.UUID | None = Query(None),
    assigned_user_id: uuid.UUID | None = Query(None),
    created_by_id: uuid.UUID | None = Query(None),
    search: str | None = Query(None),
    sla_breached: bool | None = Query(None),
    sort_by: str = Query("created_at"),
    sort_order: str = Query("desc"),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """List tickets with filtering, sorting, and pagination."""
    filters: dict = {}
    if status_filter is not None:
        filters["status"] = status_filter
    if priority is not None:
        filters["priority"] = priority
    if assigned_group_id is not None:
        filters["assigned_group_id"] = assigned_group_id
    if assigned_user_id is not None:
        filters["assigned_user_id"] = assigned_user_id
    if created_by_id is not None:
        filters["created_by_id"] = created_by_id
    if search is not None:
        filters["search"] = search
    if sla_breached is not None:
        filters["sla_breached"] = sla_breached
    filters["sort_by"] = sort_by
    filters["sort_order"] = sort_order

    tickets, total = await ticket_service.list_tickets(
        db, filters=filters, page=page, page_size=page_size
    )
    pages = math.ceil(total / page_size) if total > 0 else 0
    return PaginatedResponse(
        items=tickets,
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


@router.get("/{ticket_id}", response_model=TicketDetailResponse)
async def get_ticket(
    ticket_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Get a single ticket with notes, attachments, and audit log."""
    ticket = await ticket_service.get_ticket(db, ticket_id)

    notes = [NoteResponse.model_validate(n) for n in ticket.notes]
    attachments = [AttachmentResponse.model_validate(a) for a in ticket.attachments]
    audit_log = [
        AuditLogResponse(
            id=entry.id,
            ticket_id=entry.ticket_id,
            actor_id=entry.actor_id,
            actor_type=entry.actor_type,
            actor_name=entry.actor_name,
            action=entry.action,
            field_changed=entry.field_changed,
            old_value=entry.old_value,
            new_value=entry.new_value,
            metadata=entry.metadata_,
            created_at=entry.created_at,
        )
        for entry in ticket.audit_entries
    ]

    sla_status = sla_service.get_sla_status(ticket)
    mtta_status = sla_service.get_mtta_status(ticket)

    return TicketDetailResponse(
        id=ticket.id,
        ticket_number=ticket.ticket_number,
        title=ticket.title,
        description=ticket.description,
        status=ticket.status,
        priority=ticket.priority,
        assigned_group_id=ticket.assigned_group_id,
        assigned_group_name=ticket.assigned_group_name,
        assigned_user_id=ticket.assigned_user_id,
        assigned_user_name=ticket.assigned_user_name,
        created_by_id=ticket.created_by_id,
        created_by_name=ticket.created_by_name,
        created_at=ticket.created_at,
        updated_at=ticket.updated_at,
        resolved_at=ticket.resolved_at,
        first_assigned_at=ticket.first_assigned_at,
        sla_target_minutes=ticket.sla_target_minutes,
        sla_target_assign_minutes=ticket.sla_target_assign_minutes,
        notes=notes,
        attachments=attachments,
        audit_log=audit_log,
        sla_status=sla_status,
        mtta_status=mtta_status,
    )


@router.patch("/{ticket_id}", response_model=TicketResponse)
async def update_ticket(
    ticket_id: uuid.UUID,
    data: TicketUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Update a ticket."""
    ticket = await ticket_service.update_ticket(db, current_user, ticket_id, data)
    await db.commit()
    # Re-fetch with relationships loaded so serialization works after commit
    return await ticket_service.get_ticket(db, ticket.id)


@router.delete("/{ticket_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_ticket(
    ticket_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Soft-delete a ticket."""
    await ticket_service.soft_delete_ticket(db, current_user, ticket_id)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ---------------------------------------------------------------------------
# Notes (nested under ticket)
# ---------------------------------------------------------------------------


@router.post(
    "/{ticket_id}/notes",
    response_model=NoteResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_note(
    ticket_id: uuid.UUID,
    data: NoteCreate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Add a note to a ticket."""
    note = await note_service.add_note(
        db, current_user, ticket_id, data.content, data.is_internal
    )
    response = NoteResponse(
        id=note.id,
        ticket_id=note.ticket_id,
        author_id=note.author_id,
        author_name=current_user.user.full_name,
        content=note.content,
        is_internal=note.is_internal,
        created_at=note.created_at,
        updated_at=note.updated_at,
    )
    await db.commit()
    return response


@router.get("/{ticket_id}/notes", response_model=list[NoteResponse])
async def list_notes(
    ticket_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """List all notes for a ticket."""
    return await note_service.list_notes(db, ticket_id)


@router.patch(
    "/{ticket_id}/notes/{note_id}",
    response_model=NoteResponse,
)
async def edit_note(
    ticket_id: uuid.UUID,
    note_id: uuid.UUID,
    data: NoteUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Edit a note on a ticket."""
    note = await note_service.edit_note(db, current_user, note_id, data.content)
    author_name = note.author.full_name
    await db.refresh(note)
    response = NoteResponse(
        id=note.id,
        ticket_id=note.ticket_id,
        author_id=note.author_id,
        author_name=author_name,
        content=note.content,
        is_internal=note.is_internal,
        created_at=note.created_at,
        updated_at=note.updated_at,
    )
    await db.commit()
    return response


# ---------------------------------------------------------------------------
# Attachments (nested under ticket)
# ---------------------------------------------------------------------------


@router.post(
    "/{ticket_id}/attachments",
    response_model=AttachmentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_attachment(
    ticket_id: uuid.UUID,
    file: UploadFile,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Upload a file attachment to a ticket."""
    attachment = await attachment_service.upload_file(
        db, current_user, ticket_id, file
    )
    response = AttachmentResponse(
        id=attachment.id,
        ticket_id=attachment.ticket_id,
        note_id=attachment.note_id,
        filename=attachment.filename,
        original_filename=attachment.original_filename,
        file_size=attachment.file_size,
        content_type=attachment.content_type,
        uploaded_by_id=attachment.uploaded_by_id,
        uploaded_by_name=current_user.user.full_name,
        uploaded_at=attachment.uploaded_at,
    )
    await db.commit()
    return response


@router.get("/{ticket_id}/attachments", response_model=list[AttachmentResponse])
async def list_attachments(
    ticket_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """List all attachments for a ticket."""
    attachments = await attachment_service.list_attachments(db, ticket_id)
    return [
        AttachmentResponse(
            id=a.id,
            ticket_id=a.ticket_id,
            note_id=a.note_id,
            filename=a.filename,
            original_filename=a.original_filename,
            file_size=a.file_size,
            content_type=a.content_type,
            uploaded_by_id=a.uploaded_by_id,
            uploaded_at=a.uploaded_at,
        )
        for a in attachments
    ]


# ---------------------------------------------------------------------------
# Audit log (nested under ticket)
# ---------------------------------------------------------------------------


@router.get("/{ticket_id}/audit-log", response_model=list[AuditLogResponse])
async def get_audit_log(
    ticket_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Get the audit trail for a ticket."""
    entries = await audit_service.get_audit_log(db, ticket_id)
    return [
        AuditLogResponse(
            id=entry.id,
            ticket_id=entry.ticket_id,
            actor_id=entry.actor_id,
            actor_type=entry.actor_type,
            actor_name=entry.actor_name,
            action=entry.action,
            field_changed=entry.field_changed,
            old_value=entry.old_value,
            new_value=entry.new_value,
            metadata=entry.metadata_,
            created_at=entry.created_at,
        )
        for entry in entries
    ]
