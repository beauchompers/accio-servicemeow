import uuid

import nh3
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.dependencies import CurrentUser
from app.models.base import ActorType
from app.models.ticket import Ticket
from app.models.ticket_note import TicketNote
from app.services import audit_service


async def add_note(
    db: AsyncSession,
    current_user: CurrentUser,
    ticket_id: uuid.UUID,
    content: str,
    is_internal: bool = False,
) -> TicketNote:
    """Add a note to a ticket. Sanitizes HTML content."""
    # Verify ticket exists
    result = await db.execute(select(Ticket).where(Ticket.id == ticket_id))
    ticket = result.scalar_one_or_none()
    if not ticket:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found")

    clean_content = nh3.clean(content)

    note = TicketNote(
        ticket_id=ticket_id,
        author_id=current_user.user.id,
        content=clean_content,
        is_internal=is_internal,
    )
    db.add(note)
    await db.flush()

    # Log audit
    actor_type = ActorType.api_key if current_user.auth_type == "api_key" else ActorType.user
    await audit_service.log_action(
        db=db,
        ticket_id=ticket_id,
        actor_id=current_user.user.id,
        actor_type=actor_type,
        action="note_added",
        metadata={"note_id": str(note.id), "is_internal": is_internal},
    )

    return note


async def edit_note(
    db: AsyncSession,
    current_user: CurrentUser,
    note_id: uuid.UUID,
    content: str,
) -> TicketNote:
    """Edit an existing note. Sanitizes HTML content."""
    result = await db.execute(
        select(TicketNote).where(TicketNote.id == note_id)
        .options(selectinload(TicketNote.author))
    )
    note = result.scalar_one_or_none()
    if not note:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Note not found")

    clean_content = nh3.clean(content)
    note.content = clean_content
    await db.flush()
    return note


async def list_notes(
    db: AsyncSession,
    ticket_id: uuid.UUID,
) -> list[TicketNote]:
    """List all notes for a ticket, ordered by created_at asc."""
    result = await db.execute(
        select(TicketNote)
        .where(TicketNote.ticket_id == ticket_id)
        .order_by(TicketNote.created_at.asc())
        .options(selectinload(TicketNote.author))
    )
    return list(result.scalars().all())
