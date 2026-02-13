import uuid
from typing import Annotated

from fastapi import HTTPException
from pydantic import BaseModel, Field

from app.database import async_session
from app.mcp.auth import get_current_mcp_user
from app.mcp.resolvers import resolve_group, resolve_ticket_id, resolve_user
from app.mcp.server import mcp
from app.models.base import TicketPriority, TicketStatus
from app.schemas.ticket import TicketCreate, TicketUpdate
from app.services import note_service, ticket_service

try:
    from mcp.types import ToolAnnotations
except ImportError:
    ToolAnnotations = None  # type: ignore[assignment,misc]


# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------

# -- Shared inner models --


class TicketSummaryData(BaseModel):
    id: str = Field(description="Ticket UUID")
    ticket_number: str = Field(description="Ticket number (e.g. ASM-0001)")
    title: str = Field(description="Ticket title")
    status: str = Field(description="Current status")
    priority: str = Field(description="Priority level")


class NoteData(BaseModel):
    id: str = Field(description="Note UUID")
    author_name: str = Field(description="Display name of the note author")
    content: str = Field(description="Note content")
    is_internal: bool = Field(description="Whether the note is internal-only")
    created_at: str = Field(description="ISO 8601 timestamp")


class TicketListItemData(BaseModel):
    id: str = Field(description="Ticket UUID")
    ticket_number: str = Field(description="Ticket number (e.g. ASM-0001)")
    title: str = Field(description="Ticket title")
    status: str = Field(description="Current status")
    priority: str = Field(description="Priority level")
    assigned_group_name: str | None = Field(description="Assigned group name")
    assigned_user_name: str | None = Field(description="Assigned user name")
    created_by_name: str | None = Field(description="Creator's display name")
    created_at: str = Field(description="ISO 8601 timestamp")


# -- Per-tool inner models --


class TicketDetailData(BaseModel):
    id: str = Field(description="Ticket UUID")
    ticket_number: str = Field(description="Ticket number (e.g. ASM-0001)")
    title: str = Field(description="Ticket title")
    description: str = Field(description="Ticket description")
    status: str = Field(description="Current status")
    priority: str = Field(description="Priority level")
    assigned_group_id: str | None = Field(description="Assigned group UUID")
    assigned_group_name: str | None = Field(description="Assigned group name")
    assigned_user_id: str | None = Field(description="Assigned user UUID")
    assigned_user_name: str | None = Field(description="Assigned user name")
    created_by_id: str = Field(description="Creator's UUID")
    created_by_name: str | None = Field(description="Creator's display name")
    sla_target_minutes: int | None = Field(description="SLA target in minutes")
    first_assigned_at: str | None = Field(description="ISO 8601 timestamp of first assignment")
    created_at: str = Field(description="ISO 8601 timestamp")
    resolved_at: str | None = Field(description="ISO 8601 resolution timestamp")
    notes: list[NoteData] = Field(description="Ticket notes")


class TicketAssignmentData(BaseModel):
    id: str = Field(description="Ticket UUID")
    ticket_number: str = Field(description="Ticket number (e.g. ASM-0001)")
    assigned_group_id: str | None = Field(description="Assigned group UUID")
    assigned_user_id: str | None = Field(description="Assigned user UUID")


class NoteCreatedData(BaseModel):
    id: str = Field(description="Note UUID")
    ticket_id: str = Field(description="Parent ticket UUID")
    content: str = Field(description="Note content")
    is_internal: bool = Field(description="Whether the note is internal-only")


class TicketResolvedData(BaseModel):
    id: str = Field(description="Ticket UUID")
    ticket_number: str = Field(description="Ticket number (e.g. ASM-0001)")
    status: str = Field(description="Current status (resolved)")
    resolved_at: str | None = Field(description="ISO 8601 resolution timestamp")


class BulkUpdateItemData(BaseModel):
    id: str = Field(description="Ticket UUID")
    ticket_number: str = Field(description="Ticket number (e.g. ASM-0001)")
    status: str = Field(description="Current status after update")


# -- Container models --


class TicketListData(BaseModel):
    total: int = Field(description="Total number of matching tickets")
    page: int = Field(description="Current page number")
    tickets: list[TicketListItemData] = Field(description="Tickets on this page")


class BulkUpdateData(BaseModel):
    updated: list[BulkUpdateItemData] = Field(description="Updated tickets")


# -- Wrapper (result) models --


class CreateTicketResult(BaseModel):
    summary: str = Field(description="Human-readable result message")
    data: TicketSummaryData | None = Field(description="Created ticket, or null on error")


class GetTicketResult(BaseModel):
    summary: str = Field(description="Human-readable result message")
    data: TicketDetailData | None = Field(description="Full ticket details, or null on error")


class UpdateTicketResult(BaseModel):
    summary: str = Field(description="Human-readable result message")
    data: TicketSummaryData | None = Field(description="Updated ticket, or null on error")


class AssignTicketResult(BaseModel):
    summary: str = Field(description="Human-readable result message")
    data: TicketAssignmentData | None = Field(description="Assignment details, or null on error")


class ListTicketsResult(BaseModel):
    summary: str = Field(description="Human-readable result message")
    data: TicketListData | None = Field(description="Paginated ticket list, or null on error")


class AddNoteResult(BaseModel):
    summary: str = Field(description="Human-readable result message")
    data: NoteCreatedData | None = Field(description="Created note, or null on error")


class GetNotesResult(BaseModel):
    summary: str = Field(description="Human-readable result message")
    data: list[NoteData] | None = Field(description="List of notes, or null on error")


class ResolveTicketResult(BaseModel):
    summary: str = Field(description="Human-readable result message")
    data: TicketResolvedData | None = Field(description="Resolved ticket, or null on error")


class BulkUpdateResult(BaseModel):
    summary: str = Field(description="Human-readable result message")
    data: BulkUpdateData | None = Field(description="Update results, or null on error")


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------


@mcp.tool(
    description="Create a new support ticket",
    annotations=ToolAnnotations(openWorldHint=False),
)
async def create_ticket(
    title: Annotated[str, Field(description="Short summary of the issue")],
    description: Annotated[str, Field(description="Detailed description; HTML is sanitized on save")],
    priority: Annotated[str, Field(description="Priority level: critical, high, medium, or low")],
    assigned_group: Annotated[str, Field(description="Group name or UUID to assign the ticket to")],
    assigned_user: Annotated[str | None, Field(description="Username or UUID to assign")] = None,
) -> CreateTicketResult:
    """Create a new support ticket.

    Generates an auto-incrementing ticket number (ASM-XXXX).
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
            return CreateTicketResult(
                summary=f"Created ticket {ticket.ticket_number}: {ticket.title}",
                data=TicketSummaryData(
                    id=str(ticket.id),
                    ticket_number=ticket.ticket_number,
                    title=ticket.title,
                    status=ticket.status.value,
                    priority=ticket.priority.value,
                ),
            )
    except ValueError as e:
        return CreateTicketResult(summary=f"Error: {e}", data=None)
    except Exception as e:
        return CreateTicketResult(summary=f"Unexpected error: {e}", data=None)


@mcp.tool(
    description="Get a ticket by ID or ticket number",
    annotations=ToolAnnotations(readOnlyHint=True, openWorldHint=False),
)
async def get_ticket(
    ticket_id_or_number: Annotated[str, Field(description="Ticket UUID or number (e.g. ASM-0001)")],
) -> GetTicketResult:
    """Get full ticket details including assigned group/user, SLA info, and notes."""
    try:
        async with async_session() as db:
            await get_current_mcp_user(db)
            tid = await resolve_ticket_id(db, ticket_id_or_number)
            ticket = await ticket_service.get_ticket(db, tid)
            return GetTicketResult(
                summary=f"Ticket {ticket.ticket_number}: {ticket.title} [{ticket.status.value}]",
                data=TicketDetailData(
                    id=str(ticket.id),
                    ticket_number=ticket.ticket_number,
                    title=ticket.title,
                    description=ticket.description,
                    status=ticket.status.value,
                    priority=ticket.priority.value,
                    assigned_group_id=str(ticket.assigned_group_id) if ticket.assigned_group_id else None,
                    assigned_group_name=ticket.assigned_group_name,
                    assigned_user_id=str(ticket.assigned_user_id) if ticket.assigned_user_id else None,
                    assigned_user_name=ticket.assigned_user_name,
                    created_by_id=str(ticket.created_by_id),
                    created_by_name=ticket.created_by_name,
                    sla_target_minutes=ticket.sla_target_minutes,
                    first_assigned_at=ticket.first_assigned_at.isoformat() if ticket.first_assigned_at else None,
                    created_at=ticket.created_at.isoformat(),
                    resolved_at=ticket.resolved_at.isoformat() if ticket.resolved_at else None,
                    notes=[
                        NoteData(
                            id=str(n.id),
                            author_name=n.author_name,
                            content=n.content,
                            is_internal=n.is_internal,
                            created_at=n.created_at.isoformat(),
                        )
                        for n in ticket.notes
                    ],
                ),
            )
    except ValueError as e:
        return GetTicketResult(summary=f"Error: {e}", data=None)
    except Exception as e:
        return GetTicketResult(summary=f"Unexpected error: {e}", data=None)


@mcp.tool(
    description="Update a ticket's fields",
    annotations=ToolAnnotations(idempotentHint=True, openWorldHint=False),
)
async def update_ticket(
    ticket_id_or_number: Annotated[str, Field(description="Ticket UUID or number (e.g. ASM-0001)")],
    title: Annotated[str | None, Field(description="New title")] = None,
    description: Annotated[str | None, Field(description="New description; HTML is sanitized on save")] = None,
    status: Annotated[str | None, Field(description="New status: open, under_investigation, or resolved")] = None,
    priority: Annotated[str | None, Field(description="New priority: critical, high, medium, or low")] = None,
) -> UpdateTicketResult:
    """Update a ticket's title, description, status, or priority."""
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
            return UpdateTicketResult(
                summary=f"Updated ticket {ticket.ticket_number}",
                data=TicketSummaryData(
                    id=str(ticket.id),
                    ticket_number=ticket.ticket_number,
                    title=ticket.title,
                    status=ticket.status.value,
                    priority=ticket.priority.value,
                ),
            )
    except ValueError as e:
        return UpdateTicketResult(summary=f"Error: {e}", data=None)
    except Exception as e:
        return UpdateTicketResult(summary=f"Unexpected error: {e}", data=None)


@mcp.tool(
    description="Assign or reassign a ticket to a group and/or user",
    annotations=ToolAnnotations(idempotentHint=True, openWorldHint=False),
)
async def assign_ticket(
    ticket_id_or_number: Annotated[str, Field(description="Ticket UUID or number (e.g. ASM-0001)")],
    group: Annotated[str | None, Field(description="Group name or UUID to assign to")] = None,
    user: Annotated[str | None, Field(description="Username or UUID to assign to")] = None,
) -> AssignTicketResult:
    """Assign or reassign a ticket to a group and/or user."""
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
            return AssignTicketResult(
                summary=f"Assigned ticket {ticket.ticket_number}",
                data=TicketAssignmentData(
                    id=str(ticket.id),
                    ticket_number=ticket.ticket_number,
                    assigned_group_id=str(ticket.assigned_group_id) if ticket.assigned_group_id else None,
                    assigned_user_id=str(ticket.assigned_user_id) if ticket.assigned_user_id else None,
                ),
            )
    except ValueError as e:
        return AssignTicketResult(summary=f"Error: {e}", data=None)
    except Exception as e:
        return AssignTicketResult(summary=f"Unexpected error: {e}", data=None)


@mcp.tool(
    description="List tickets with optional filters",
    annotations=ToolAnnotations(readOnlyHint=True, openWorldHint=False),
)
async def list_tickets(
    status: Annotated[str | None, Field(description="Filter by status; comma-separated for multiple (e.g. open,under_investigation)")] = None,
    priority: Annotated[str | None, Field(description="Filter by priority: critical, high, medium, or low")] = None,
    group: Annotated[str | None, Field(description="Filter by group name or UUID")] = None,
    user: Annotated[str | None, Field(description="Filter by username or UUID")] = None,
    search: Annotated[str | None, Field(description="Full-text search query")] = None,
    sla_breached: Annotated[bool | None, Field(description="Filter for SLA-breached tickets")] = None,
    page: Annotated[int, Field(description="Page number (default 1)")] = 1,
    page_size: Annotated[int, Field(description="Results per page (default 20)")] = 20,
) -> ListTicketsResult:
    """List tickets with optional filters and pagination."""
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
            return ListTicketsResult(
                summary=f"Found {total} tickets (showing page {page})",
                data=TicketListData(
                    total=total,
                    page=page,
                    tickets=[
                        TicketListItemData(
                            id=str(t.id),
                            ticket_number=t.ticket_number,
                            title=t.title,
                            status=t.status.value,
                            priority=t.priority.value,
                            assigned_group_name=t.assigned_group_name,
                            assigned_user_name=t.assigned_user_name,
                            created_by_name=t.created_by_name,
                            created_at=t.created_at.isoformat(),
                        )
                        for t in tickets
                    ],
                ),
            )
    except ValueError as e:
        return ListTicketsResult(summary=f"Error: {e}", data=None)
    except Exception as e:
        return ListTicketsResult(summary=f"Unexpected error: {e}", data=None)


@mcp.tool(
    description="Add a note to a ticket",
    annotations=ToolAnnotations(openWorldHint=False),
)
async def add_ticket_note(
    ticket_id_or_number: Annotated[str, Field(description="Ticket UUID or number (e.g. ASM-0001)")],
    content: Annotated[str, Field(description="Note content; HTML is sanitized on save")],
    is_internal: Annotated[bool, Field(description="Whether the note is internal-only")] = False,
) -> AddNoteResult:
    """Add a note to a ticket."""
    try:
        async with async_session() as db:
            current_user = await get_current_mcp_user(db)
            tid = await resolve_ticket_id(db, ticket_id_or_number)
            note = await note_service.add_note(
                db, current_user, tid, content, is_internal
            )
            await db.commit()
            return AddNoteResult(
                summary="Added note to ticket",
                data=NoteCreatedData(
                    id=str(note.id),
                    ticket_id=str(note.ticket_id),
                    content=note.content,
                    is_internal=note.is_internal,
                ),
            )
    except ValueError as e:
        return AddNoteResult(summary=f"Error: {e}", data=None)
    except Exception as e:
        return AddNoteResult(summary=f"Unexpected error: {e}", data=None)


@mcp.tool(
    description="Get all notes for a ticket",
    annotations=ToolAnnotations(readOnlyHint=True, openWorldHint=False),
)
async def get_ticket_notes(
    ticket_id_or_number: Annotated[str, Field(description="Ticket UUID or number (e.g. ASM-0001)")],
) -> GetNotesResult:
    """Get all notes for a ticket."""
    try:
        async with async_session() as db:
            await get_current_mcp_user(db)
            tid = await resolve_ticket_id(db, ticket_id_or_number)
            notes = await note_service.list_notes(db, tid)
            return GetNotesResult(
                summary=f"Found {len(notes)} {'note' if len(notes) == 1 else 'notes'}",
                data=[
                    NoteData(
                        id=str(n.id),
                        author_name=n.author_name,
                        content=n.content,
                        is_internal=n.is_internal,
                        created_at=n.created_at.isoformat(),
                    )
                    for n in notes
                ],
            )
    except ValueError as e:
        return GetNotesResult(summary=f"Error: {e}", data=None)
    except Exception as e:
        return GetNotesResult(summary=f"Unexpected error: {e}", data=None)


@mcp.tool(
    description="Resolve a ticket with optional resolution note",
    annotations=ToolAnnotations(idempotentHint=True, openWorldHint=False),
)
async def resolve_ticket(
    ticket_id_or_number: Annotated[str, Field(description="Ticket UUID or number (e.g. ASM-0001)")],
    resolution_note: Annotated[str | None, Field(description="Note to add before resolving")] = None,
) -> ResolveTicketResult:
    """Resolve a ticket, optionally adding a resolution note first."""
    try:
        async with async_session() as db:
            current_user = await get_current_mcp_user(db)
            tid = await resolve_ticket_id(db, ticket_id_or_number)
            if resolution_note:
                await note_service.add_note(db, current_user, tid, resolution_note, False)
            data = TicketUpdate(status=TicketStatus.resolved)
            ticket = await ticket_service.update_ticket(db, current_user, tid, data)
            await db.commit()
            return ResolveTicketResult(
                summary=f"Resolved ticket {ticket.ticket_number}",
                data=TicketResolvedData(
                    id=str(ticket.id),
                    ticket_number=ticket.ticket_number,
                    status=ticket.status.value,
                    resolved_at=ticket.resolved_at.isoformat() if ticket.resolved_at else None,
                ),
            )
    except ValueError as e:
        return ResolveTicketResult(summary=f"Error: {e}", data=None)
    except Exception as e:
        return ResolveTicketResult(summary=f"Unexpected error: {e}", data=None)


@mcp.tool(
    description="Batch-update multiple tickets at once",
    annotations=ToolAnnotations(idempotentHint=True, openWorldHint=False),
)
async def bulk_update_tickets(
    ticket_ids: Annotated[list[str], Field(description="List of ticket UUIDs or numbers")],
    status: Annotated[str | None, Field(description="New status to set")] = None,
    group: Annotated[str | None, Field(description="Group name or UUID to assign to")] = None,
    user: Annotated[str | None, Field(description="Username or UUID to assign to")] = None,
) -> BulkUpdateResult:
    """Batch-update multiple tickets at once."""
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
                results.append(
                    BulkUpdateItemData(
                        id=str(ticket.id),
                        ticket_number=ticket.ticket_number,
                        status=ticket.status.value,
                    )
                )
            await db.commit()
        return BulkUpdateResult(
            summary=f"Updated {len(results)} tickets",
            data=BulkUpdateData(updated=results),
        )
    except ValueError as e:
        return BulkUpdateResult(summary=f"Error: {e}", data=None)
    except Exception as e:
        return BulkUpdateResult(summary=f"Unexpected error: {e}", data=None)
