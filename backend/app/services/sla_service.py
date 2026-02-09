import uuid
from datetime import datetime, timezone

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ticket import Ticket


def calculate_elapsed_seconds(ticket: Ticket) -> int:
    """Calculate elapsed time in seconds.

    elapsed = (resolved_at or now) - created_at
    """
    now = datetime.now(timezone.utc)
    end_time = ticket.resolved_at or now
    total = (end_time - ticket.created_at).total_seconds()
    return max(0, int(total))


def is_breached(ticket: Ticket) -> bool:
    """Check if ticket SLA is breached (elapsed > target)."""
    if ticket.sla_target_minutes is None:
        return False
    elapsed = calculate_elapsed_seconds(ticket)
    return elapsed > ticket.sla_target_minutes * 60


def is_at_risk(ticket: Ticket) -> bool:
    """Check if ticket SLA is at risk (elapsed > 80% of target)."""
    if ticket.sla_target_minutes is None:
        return False
    elapsed = calculate_elapsed_seconds(ticket)
    return elapsed > ticket.sla_target_minutes * 60 * 0.8


def get_sla_status(ticket: Ticket) -> dict | None:
    """Get SLA status for a ticket. Returns None if no SLA target."""
    if ticket.sla_target_minutes is None:
        return None
    elapsed = calculate_elapsed_seconds(ticket)
    target = ticket.sla_target_minutes * 60
    remaining_seconds = target - elapsed

    is_resolved = ticket.resolved_at is not None
    breached = elapsed > target
    if is_resolved:
        outcome = "over_sla" if breached else "within_sla"
    else:
        outcome = None

    return {
        "target_minutes": ticket.sla_target_minutes,
        "elapsed_minutes": round(elapsed / 60),
        "percentage": round((elapsed / target) * 100, 1) if target > 0 else 0,
        "is_breached": breached,
        "is_at_risk": elapsed > target * 0.8,
        "remaining_minutes": round(remaining_seconds / 60),
        "is_resolved": is_resolved,
        "outcome": outcome,
    }


def get_mtta_status(ticket: Ticket) -> dict | None:
    """Get MTTA (Mean Time To Assign) status for a ticket.

    Returns None if no MTTA target is set on the ticket.
    """
    if ticket.sla_target_assign_minutes is None:
        return None

    now = datetime.now(timezone.utc)
    target = ticket.sla_target_assign_minutes * 60  # seconds

    if ticket.first_assigned_at is not None:
        # Already assigned — use actual elapsed (wall-clock, no pause deduction)
        elapsed = (ticket.first_assigned_at - ticket.created_at).total_seconds()
        is_met = elapsed <= target
        is_pending = False
    else:
        # Not yet assigned — live elapsed
        elapsed = (now - ticket.created_at).total_seconds()
        is_met = False
        is_pending = True

    elapsed = max(0, int(elapsed))
    breached = elapsed > target

    return {
        "target_minutes": ticket.sla_target_assign_minutes,
        "elapsed_minutes": round(elapsed / 60),
        "percentage": round((elapsed / target) * 100, 1) if target > 0 else 0,
        "is_breached": breached,
        "is_met": is_met,
        "is_pending": is_pending,
    }


async def get_mtta(
    db: AsyncSession,
    group_id: uuid.UUID | None = None,
    priority: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
) -> float | None:
    """Mean Time To Assign: avg(first_assigned_at - created_at) in seconds."""
    query = select(
        func.avg(
            func.extract("epoch", Ticket.first_assigned_at - Ticket.created_at)
        )
    ).where(Ticket.first_assigned_at.isnot(None))

    if group_id is not None:
        query = query.where(Ticket.assigned_group_id == group_id)
    if priority is not None:
        query = query.where(Ticket.priority == priority)
    if date_from is not None:
        query = query.where(Ticket.created_at >= date_from)
    if date_to is not None:
        query = query.where(Ticket.created_at <= date_to)

    result = await db.execute(query)
    val = result.scalar()
    return float(val) if val is not None else None


async def get_mttr(
    db: AsyncSession,
    group_id: uuid.UUID | None = None,
    priority: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
) -> float | None:
    """Mean Time To Resolve: avg(resolved_at - created_at) in seconds."""
    query = select(
        func.avg(
            func.extract("epoch", Ticket.resolved_at - Ticket.created_at)
        )
    ).where(Ticket.resolved_at.isnot(None))

    if group_id is not None:
        query = query.where(Ticket.assigned_group_id == group_id)
    if priority is not None:
        query = query.where(Ticket.priority == priority)
    if date_from is not None:
        query = query.where(Ticket.created_at >= date_from)
    if date_to is not None:
        query = query.where(Ticket.created_at <= date_to)

    result = await db.execute(query)
    val = result.scalar()
    return float(val) if val is not None else None
