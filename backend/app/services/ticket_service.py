import uuid
from datetime import datetime, timezone

import nh3
from fastapi import HTTPException, status
from sqlalchemy import select, func, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.dependencies import CurrentUser
from app.models.attachment import Attachment
from app.models.audit_log import AuditLog
from app.models.base import ActorType, TicketPriority, TicketStatus
from app.models.group import Group, GroupMembership
from app.models.sla_config import SlaConfig
from app.models.ticket import Ticket
from app.models.ticket_note import TicketNote
from app.models.user import User
from app.schemas.ticket import TicketCreate, TicketUpdate
from app.services import audit_service


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _next_ticket_number(db: AsyncSession) -> str:
    """Generate the next ticket number using a PostgreSQL sequence."""
    result = await db.execute(text("SELECT nextval('ticket_number_seq')"))
    seq_val = result.scalar()
    return f"ASM-{seq_val:04d}"


def _actor_type_from_user(current_user: CurrentUser) -> ActorType:
    """Determine the actor type from the current user auth method."""
    if current_user.auth_type == "api_key":
        return ActorType.api_key
    return ActorType.user


async def _validate_group_and_membership(
    db: AsyncSession,
    group_id: uuid.UUID,
    user_id: uuid.UUID | None = None,
) -> None:
    """Verify the group exists and, if user_id given, that user is a member."""
    result = await db.execute(select(Group).where(Group.id == group_id))
    group = result.scalar_one_or_none()
    if group is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assigned group not found",
        )
    if user_id is not None:
        membership_result = await db.execute(
            select(GroupMembership).where(
                GroupMembership.group_id == group_id,
                GroupMembership.user_id == user_id,
            )
        )
        if membership_result.scalar_one_or_none() is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Assigned user is not a member of the assigned group",
            )


# ---------------------------------------------------------------------------
# Eager-load options (shared across get functions)
# ---------------------------------------------------------------------------

_TICKET_LOAD_OPTIONS = [
    selectinload(Ticket.notes).selectinload(TicketNote.author),
    selectinload(Ticket.attachments).selectinload(Attachment.uploaded_by),
    selectinload(Ticket.audit_entries).selectinload(AuditLog.actor),
    selectinload(Ticket.assigned_group),
    selectinload(Ticket.assigned_user),
    selectinload(Ticket.created_by),
]


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------

async def create_ticket(
    db: AsyncSession,
    current_user: CurrentUser,
    data: TicketCreate,
) -> Ticket:
    """Create a new ticket with SLA lookup and audit logging."""
    await _validate_group_and_membership(db, data.assigned_group_id, data.assigned_user_id)

    ticket_number = await _next_ticket_number(db)

    # Look up SLA target for this priority
    sla_result = await db.execute(
        select(SlaConfig).where(SlaConfig.priority == data.priority)
    )
    sla_config = sla_result.scalar_one_or_none()
    sla_target_minutes = sla_config.target_resolve_minutes if sla_config else None
    sla_target_assign_minutes = sla_config.target_assign_minutes if sla_config else None

    now = datetime.now(timezone.utc)

    # MTTA tracks when a specific user is assigned, not just a group
    first_assigned_at = None
    if data.assigned_user_id is not None:
        first_assigned_at = now

    # Sanitize description HTML
    clean_description = nh3.clean(data.description)

    ticket = Ticket(
        ticket_number=ticket_number,
        title=data.title,
        description=clean_description,
        priority=data.priority,
        status=TicketStatus.open,
        created_by_id=current_user.user.id,
        assigned_group_id=data.assigned_group_id,
        assigned_user_id=data.assigned_user_id,
        sla_target_minutes=sla_target_minutes,
        sla_target_assign_minutes=sla_target_assign_minutes,
        first_assigned_at=first_assigned_at,
    )
    db.add(ticket)
    await db.flush()

    # Audit log
    await audit_service.log_action(
        db=db,
        ticket_id=ticket.id,
        actor_id=current_user.user.id,
        actor_type=_actor_type_from_user(current_user),
        action="created",
    )

    await db.flush()
    return ticket


async def get_ticket(db: AsyncSession, ticket_id: uuid.UUID) -> Ticket:
    """Get a single ticket by ID with all relationships eager-loaded."""
    result = await db.execute(
        select(Ticket)
        .where(Ticket.id == ticket_id)
        .options(*_TICKET_LOAD_OPTIONS)
    )
    ticket = result.scalar_one_or_none()
    if ticket is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket not found",
        )
    return ticket


async def get_ticket_by_number(db: AsyncSession, ticket_number: str) -> Ticket | None:
    """Get a ticket by its ticket_number string (e.g. 'ASM-0001')."""
    result = await db.execute(
        select(Ticket)
        .where(Ticket.ticket_number == ticket_number)
        .options(*_TICKET_LOAD_OPTIONS)
    )
    return result.scalar_one_or_none()


async def update_ticket(
    db: AsyncSession,
    current_user: CurrentUser,
    ticket_id: uuid.UUID,
    data: TicketUpdate,
) -> Ticket:
    """Update a ticket with status-transition logic, SLA tracking, and audit."""
    ticket = await get_ticket(db, ticket_id)
    now = datetime.now(timezone.utc)
    actor_type = _actor_type_from_user(current_user)

    update_fields = data.model_dump(exclude_unset=True)

    # Validate group/membership when assignment fields change
    new_group_id = update_fields.get("assigned_group_id", ticket.assigned_group_id)
    new_user_id = update_fields.get("assigned_user_id", ticket.assigned_user_id)
    if "assigned_group_id" in update_fields or "assigned_user_id" in update_fields:
        if new_group_id is not None:
            await _validate_group_and_membership(db, new_group_id, new_user_id)

    for field, new_value in update_fields.items():
        old_value = getattr(ticket, field)

        # Convert enums to their value for comparison and audit logging
        old_str = old_value.value if isinstance(old_value, (TicketStatus, TicketPriority)) else str(old_value) if old_value is not None else None
        new_str = new_value.value if isinstance(new_value, (TicketStatus, TicketPriority)) else str(new_value) if new_value is not None else None

        # Skip if value hasn't actually changed
        if old_str == new_str:
            continue

        # --- Status transition logic ---
        if field == "status":
            old_status = old_value
            new_status = new_value

            # Transitioning TO resolved
            if new_status == TicketStatus.resolved:
                ticket.resolved_at = now

        # --- Assignment logic (MTTA tracks user assignment only) ---
        if field == "assigned_user_id":
            if ticket.first_assigned_at is None and new_value is not None:
                ticket.first_assigned_at = now

        # --- Resolve names for audit logging ---
        if field == "assigned_user_id":
            old_str = ticket.assigned_user_name if old_value is not None else None
            if new_value is not None:
                user_row = await db.execute(select(User).where(User.id == new_value))
                user_obj = user_row.scalar_one_or_none()
                new_str = user_obj.full_name if user_obj else new_str
        elif field == "assigned_group_id":
            old_str = ticket.assigned_group_name if old_value is not None else None
            if new_value is not None:
                group_row = await db.execute(select(Group).where(Group.id == new_value))
                group_obj = group_row.scalar_one_or_none()
                new_str = group_obj.name if group_obj else new_str

        # --- HTML sanitization for description ---
        if field == "description" and new_value is not None:
            new_value = nh3.clean(new_value)
            new_str = new_value  # update audit string after sanitization

        # Apply the change
        setattr(ticket, field, new_value)

        # Log audit for each changed field
        await audit_service.log_action(
            db=db,
            ticket_id=ticket.id,
            actor_id=current_user.user.id,
            actor_type=actor_type,
            action="updated",
            field_changed=field,
            old_value=old_str,
            new_value=new_str,
        )

    await db.flush()
    return ticket


async def list_tickets(
    db: AsyncSession,
    filters: dict,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[Ticket], int]:
    """List tickets with filtering, search, sorting, and pagination."""
    query = select(Ticket).options(
        selectinload(Ticket.created_by),
        selectinload(Ticket.assigned_user),
        selectinload(Ticket.assigned_group),
    )
    count_query = select(func.count()).select_from(Ticket)

    conditions = []

    # --- Filters ---
    if "status" in filters and filters["status"] is not None:
        status_val = filters["status"]
        if "," in status_val:
            statuses = [s.strip() for s in status_val.split(",")]
            conditions.append(Ticket.status.in_(statuses))
        else:
            conditions.append(Ticket.status == status_val)

    if "priority" in filters and filters["priority"] is not None:
        conditions.append(Ticket.priority == filters["priority"])

    if "assigned_group_id" in filters and filters["assigned_group_id"] is not None:
        conditions.append(Ticket.assigned_group_id == filters["assigned_group_id"])

    if "assigned_user_id" in filters and filters["assigned_user_id"] is not None:
        conditions.append(Ticket.assigned_user_id == filters["assigned_user_id"])

    if "created_by_id" in filters and filters["created_by_id"] is not None:
        conditions.append(Ticket.created_by_id == filters["created_by_id"])

    # Full-text search
    if "search" in filters and filters["search"] is not None:
        search_term = filters["search"]
        ts_vector = func.to_tsvector(
            "english",
            Ticket.title + " " + Ticket.description,
        )
        conditions.append(ts_vector.match(search_term))

    # SLA breached filter
    if "sla_breached" in filters and filters["sla_breached"]:
        # A ticket is breached when elapsed time exceeds sla_target_minutes.
        # Elapsed = (resolved_at or now) - created_at
        now_utc = func.now()
        effective_end = func.coalesce(Ticket.resolved_at, now_utc)
        elapsed_seconds = func.extract("epoch", effective_end - Ticket.created_at)
        conditions.append(Ticket.sla_target_minutes.isnot(None))
        conditions.append(elapsed_seconds > Ticket.sla_target_minutes * 60)

    # Apply conditions
    for cond in conditions:
        query = query.where(cond)
        count_query = count_query.where(cond)

    # --- Sorting ---
    sort_by = filters.get("sort_by", "created_at")
    sort_order = filters.get("sort_order", "desc")

    # Validate sort_by against Ticket columns to prevent injection
    allowed_sort_fields = {
        "created_at", "updated_at", "title", "status", "priority",
        "ticket_number", "resolved_at",
    }
    if sort_by not in allowed_sort_fields:
        sort_by = "created_at"

    sort_column = getattr(Ticket, sort_by)
    if sort_order == "asc":
        query = query.order_by(sort_column.asc())
    else:
        query = query.order_by(sort_column.desc())

    # --- Pagination ---
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)

    # Execute
    total_result = await db.execute(count_query)
    total_count = total_result.scalar() or 0

    items_result = await db.execute(query)
    items = list(items_result.scalars().all())

    return items, total_count


async def soft_delete_ticket(
    db: AsyncSession,
    current_user: CurrentUser,
    ticket_id: uuid.UUID,
) -> None:
    """Soft-delete a ticket by setting its status to resolved."""
    ticket = await get_ticket(db, ticket_id)

    ticket.status = TicketStatus.resolved
    if ticket.resolved_at is None:
        ticket.resolved_at = datetime.now(timezone.utc)

    # Audit log
    await audit_service.log_action(
        db=db,
        ticket_id=ticket.id,
        actor_id=current_user.user.id,
        actor_type=_actor_type_from_user(current_user),
        action="deleted",
    )

    await db.flush()
