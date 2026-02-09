import uuid

from fastapi import HTTPException

from app.database import async_session
from app.mcp.auth import get_current_mcp_user
from app.mcp.resolvers import resolve_group, resolve_ticket_id, resolve_user
from app.mcp.server import mcp
from app.models.base import TicketPriority, TicketStatus
from app.schemas.ticket import TicketCreate, TicketUpdate
from app.services import note_service, ticket_service


@mcp.tool(description="Create a new support ticket")
async def create_ticket(
    title: str,
    description: str,
    priority: str,
    assigned_group: str,
    assigned_user: str | None = None,
) -> dict:
    """Create a new support ticket.

    Args:
        title: Ticket title
        description: Ticket description (HTML allowed, sanitized on save)
        priority: Priority level (critical, high, medium, low)
        assigned_group: Group to assign the ticket to -- name or UUID
        assigned_user: Optional user to assign -- username or UUID
    """
    try:
        async with async_session() as db:
            current_user = await get_current_mcp_user(db)
            group_id = await resolve_group(db, assigned_group)
            user_id = await resolve_user(db, assigned_user) if assigned_user else None
            data = TicketCreate(
                title=title,
                description=description,
                priority=TicketPriority(priority),
                assigned_group_id=group_id,
                assigned_user_id=user_id,
            )
            ticket = await ticket_service.create_ticket(db, current_user, data)
            await db.commit()
            return {
                "summary": f"Created ticket {ticket.ticket_number}: {ticket.title}",
                "data": {
                    "id": str(ticket.id),
                    "ticket_number": ticket.ticket_number,
                    "title": ticket.title,
                    "status": ticket.status.value,
                    "priority": ticket.priority.value,
                },
            }
    except ValueError as e:
        return {"summary": f"Error: {e}", "data": None}
    except Exception as e:
        return {"summary": f"Unexpected error: {e}", "data": None}


@mcp.tool(description="Get a ticket by ID or ticket number")
async def get_ticket(
    ticket_id_or_number: str,
) -> dict:
    """Get a ticket by ID (UUID) or ticket number (ASM-XXXX format).

    Returns full ticket details including assigned group/user names,
    SLA information, and all notes.

    Args:
        ticket_id_or_number: UUID or ticket number (e.g. ASM-0001)
    """
    try:
        async with async_session() as db:
            await get_current_mcp_user(db)
            tid = await resolve_ticket_id(db, ticket_id_or_number)
            ticket = await ticket_service.get_ticket(db, tid)
            return {
                "summary": f"Ticket {ticket.ticket_number}: {ticket.title} [{ticket.status.value}]",
                "data": {
                    "id": str(ticket.id),
                    "ticket_number": ticket.ticket_number,
                    "title": ticket.title,
                    "description": ticket.description,
                    "status": ticket.status.value,
                    "priority": ticket.priority.value,
                    "assigned_group_id": str(ticket.assigned_group_id) if ticket.assigned_group_id else None,
                    "assigned_group_name": ticket.assigned_group_name,
                    "assigned_user_id": str(ticket.assigned_user_id) if ticket.assigned_user_id else None,
                    "assigned_user_name": ticket.assigned_user_name,
                    "created_by_id": str(ticket.created_by_id),
                    "created_by_name": ticket.created_by_name,
                    "sla_target_minutes": ticket.sla_target_minutes,
                    "first_assigned_at": ticket.first_assigned_at.isoformat() if ticket.first_assigned_at else None,
                    "created_at": ticket.created_at.isoformat(),
                    "resolved_at": ticket.resolved_at.isoformat() if ticket.resolved_at else None,
                    "notes": [
                        {
                            "id": str(n.id),
                            "author_name": n.author_name,
                            "content": n.content,
                            "is_internal": n.is_internal,
                            "created_at": n.created_at.isoformat(),
                        }
                        for n in ticket.notes
                    ],
                },
            }
    except ValueError as e:
        return {"summary": f"Error: {e}", "data": None}
    except Exception as e:
        return {"summary": f"Unexpected error: {e}", "data": None}


@mcp.tool(description="Update a ticket's fields")
async def update_ticket(
    ticket_id_or_number: str,
    title: str | None = None,
    description: str | None = None,
    status: str | None = None,
    priority: str | None = None,
) -> dict:
    """Update a ticket's fields.

    Args:
        ticket_id_or_number: UUID or ticket number (e.g. ASM-0001)
        title: New title (optional)
        description: New description (HTML allowed, sanitized on save) (optional)
        status: New status: open, under_investigation, resolved (optional)
        priority: New priority: critical, high, medium, low (optional)
    """
    try:
        async with async_session() as db:
            current_user = await get_current_mcp_user(db)
            tid = await resolve_ticket_id(db, ticket_id_or_number)
            update_data = {}
            if title is not None:
                update_data["title"] = title
            if description is not None:
                update_data["description"] = description
            if status is not None:
                update_data["status"] = TicketStatus(status)
            if priority is not None:
                update_data["priority"] = TicketPriority(priority)

            data = TicketUpdate(**update_data)
            ticket = await ticket_service.update_ticket(
                db, current_user, tid, data
            )
            await db.commit()
            return {
                "summary": f"Updated ticket {ticket.ticket_number}",
                "data": {
                    "id": str(ticket.id),
                    "ticket_number": ticket.ticket_number,
                    "title": ticket.title,
                    "status": ticket.status.value,
                    "priority": ticket.priority.value,
                },
            }
    except ValueError as e:
        return {"summary": f"Error: {e}", "data": None}
    except Exception as e:
        return {"summary": f"Unexpected error: {e}", "data": None}


@mcp.tool(description="Assign or reassign a ticket to a group and/or user")
async def assign_ticket(
    ticket_id_or_number: str,
    group: str | None = None,
    user: str | None = None,
) -> dict:
    """Assign or reassign a ticket to a group and/or user.

    Args:
        ticket_id_or_number: UUID or ticket number (e.g. ASM-0001)
        group: Group to assign to -- name or UUID (optional)
        user: User to assign to -- username or UUID (optional)
    """
    try:
        async with async_session() as db:
            current_user = await get_current_mcp_user(db)
            tid = await resolve_ticket_id(db, ticket_id_or_number)
            update_data = {}
            if group is not None:
                update_data["assigned_group_id"] = await resolve_group(db, group)
            if user is not None:
                update_data["assigned_user_id"] = await resolve_user(db, user)

            data = TicketUpdate(**update_data)
            ticket = await ticket_service.update_ticket(
                db, current_user, tid, data
            )
            await db.commit()
            return {
                "summary": f"Assigned ticket {ticket.ticket_number}",
                "data": {
                    "id": str(ticket.id),
                    "ticket_number": ticket.ticket_number,
                    "assigned_group_id": str(ticket.assigned_group_id) if ticket.assigned_group_id else None,
                    "assigned_user_id": str(ticket.assigned_user_id) if ticket.assigned_user_id else None,
                },
            }
    except ValueError as e:
        return {"summary": f"Error: {e}", "data": None}
    except Exception as e:
        return {"summary": f"Unexpected error: {e}", "data": None}


@mcp.tool(description="List tickets with optional filters")
async def list_tickets(
    status: str | None = None,
    priority: str | None = None,
    group: str | None = None,
    user: str | None = None,
    search: str | None = None,
    sla_breached: bool | None = None,
    page: int = 1,
    page_size: int = 20,
) -> dict:
    """List tickets with optional filters.

    Args:
        status: Filter by status (open, under_investigation, resolved) -- comma-separated for multiple
        priority: Filter by priority (critical, high, medium, low)
        group: Filter by assigned group -- name or UUID
        user: Filter by assigned user -- username or UUID
        search: Full-text search query
        sla_breached: Filter for SLA-breached tickets (true/false)
        page: Page number (default 1)
        page_size: Results per page (default 20)
    """
    try:
        async with async_session() as db:
            await get_current_mcp_user(db)
            filters: dict = {}
            if status:
                filters["status"] = status
            if priority:
                filters["priority"] = priority
            if group:
                filters["assigned_group_id"] = await resolve_group(db, group)
            if user:
                filters["assigned_user_id"] = await resolve_user(db, user)
            if search:
                filters["search"] = search
            if sla_breached is not None:
                filters["sla_breached"] = sla_breached

            tickets, total = await ticket_service.list_tickets(
                db, filters=filters, page=page, page_size=page_size
            )
            return {
                "summary": f"Found {total} tickets (showing page {page})",
                "data": {
                    "total": total,
                    "page": page,
                    "tickets": [
                        {
                            "id": str(t.id),
                            "ticket_number": t.ticket_number,
                            "title": t.title,
                            "status": t.status.value,
                            "priority": t.priority.value,
                            "assigned_group_name": t.assigned_group_name,
                            "assigned_user_name": t.assigned_user_name,
                            "created_by_name": t.created_by_name,
                            "created_at": t.created_at.isoformat(),
                        }
                        for t in tickets
                    ],
                },
            }
    except ValueError as e:
        return {"summary": f"Error: {e}", "data": None}
    except Exception as e:
        return {"summary": f"Unexpected error: {e}", "data": None}


@mcp.tool(description="Add a note to a ticket")
async def add_ticket_note(
    ticket_id_or_number: str,
    content: str,
    is_internal: bool = False,
) -> dict:
    """Add a note to a ticket.

    Args:
        ticket_id_or_number: UUID or ticket number (e.g. ASM-0001)
        content: Note content (HTML allowed, sanitized on save)
        is_internal: Whether the note is internal-only (default false)
    """
    try:
        async with async_session() as db:
            current_user = await get_current_mcp_user(db)
            tid = await resolve_ticket_id(db, ticket_id_or_number)
            note = await note_service.add_note(
                db, current_user, tid, content, is_internal
            )
            await db.commit()
            return {
                "summary": "Added note to ticket",
                "data": {
                    "id": str(note.id),
                    "ticket_id": str(note.ticket_id),
                    "content": note.content,
                    "is_internal": note.is_internal,
                },
            }
    except ValueError as e:
        return {"summary": f"Error: {e}", "data": None}
    except Exception as e:
        return {"summary": f"Unexpected error: {e}", "data": None}


@mcp.tool(description="Get all notes for a ticket")
async def get_ticket_notes(
    ticket_id_or_number: str,
) -> dict:
    """Get all notes for a ticket.

    Args:
        ticket_id_or_number: UUID or ticket number (e.g. ASM-0001)
    """
    try:
        async with async_session() as db:
            await get_current_mcp_user(db)
            tid = await resolve_ticket_id(db, ticket_id_or_number)
            notes = await note_service.list_notes(db, tid)
            return {
                "summary": f"Found {len(notes)} {'note' if len(notes) == 1 else 'notes'}",
                "data": [
                    {
                        "id": str(n.id),
                        "author_name": n.author_name,
                        "content": n.content,
                        "is_internal": n.is_internal,
                        "created_at": n.created_at.isoformat(),
                    }
                    for n in notes
                ],
            }
    except ValueError as e:
        return {"summary": f"Error: {e}", "data": None}
    except Exception as e:
        return {"summary": f"Unexpected error: {e}", "data": None}


@mcp.tool(description="Resolve a ticket with optional resolution note")
async def resolve_ticket(
    ticket_id_or_number: str,
    resolution_note: str | None = None,
) -> dict:
    """Resolve a ticket, optionally adding a resolution note.

    Args:
        ticket_id_or_number: UUID or ticket number (e.g. ASM-0001)
        resolution_note: Optional note to add before resolving
    """
    try:
        async with async_session() as db:
            current_user = await get_current_mcp_user(db)
            tid = await resolve_ticket_id(db, ticket_id_or_number)
            if resolution_note:
                await note_service.add_note(db, current_user, tid, resolution_note, False)
            data = TicketUpdate(status=TicketStatus.resolved)
            ticket = await ticket_service.update_ticket(db, current_user, tid, data)
            await db.commit()
            return {
                "summary": f"Resolved ticket {ticket.ticket_number}",
                "data": {
                    "id": str(ticket.id),
                    "ticket_number": ticket.ticket_number,
                    "status": ticket.status.value,
                    "resolved_at": ticket.resolved_at.isoformat() if ticket.resolved_at else None,
                },
            }
    except ValueError as e:
        return {"summary": f"Error: {e}", "data": None}
    except Exception as e:
        return {"summary": f"Unexpected error: {e}", "data": None}


@mcp.tool(description="Batch-update multiple tickets at once")
async def bulk_update_tickets(
    ticket_ids: list[str],
    status: str | None = None,
    group: str | None = None,
    user: str | None = None,
) -> dict:
    """Batch-update multiple tickets at once.

    Args:
        ticket_ids: List of ticket UUIDs or ticket numbers (e.g. ASM-0001)
        status: New status to set (optional)
        group: Group to assign to -- name or UUID (optional)
        user: User to assign to -- username or UUID (optional)
    """
    try:
        async with async_session() as db:
            current_user = await get_current_mcp_user(db)
            update_data = {}
            if status is not None:
                update_data["status"] = TicketStatus(status)
            if group is not None:
                update_data["assigned_group_id"] = await resolve_group(db, group)
            if user is not None:
                update_data["assigned_user_id"] = await resolve_user(db, user)

            data = TicketUpdate(**update_data)
            results = []
            for tid_str in ticket_ids:
                tid = await resolve_ticket_id(db, tid_str)
                try:
                    ticket = await ticket_service.update_ticket(
                        db, current_user, tid, data
                    )
                except HTTPException as e:
                    raise ValueError(f"{tid_str}: {e.detail}") from e
                results.append({
                    "id": str(ticket.id),
                    "ticket_number": ticket.ticket_number,
                    "status": ticket.status.value,
                })
            await db.commit()
        return {
            "summary": f"Updated {len(results)} tickets",
            "data": {"updated": results},
        }
    except ValueError as e:
        return {"summary": f"Error: {e}", "data": None}
    except Exception as e:
        return {"summary": f"Unexpected error: {e}", "data": None}
