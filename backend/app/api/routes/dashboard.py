import math
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.dependencies import CurrentUser, get_current_user
from app.database import get_db
from app.models.audit_log import AuditLog
from app.models.group import Group
from app.models.ticket import Ticket
from app.schemas.audit_log import AuditLogResponse
from app.schemas.common import PaginatedResponse
from app.schemas.dashboard import (
    DashboardSummary,
    GroupCount,
    PriorityCount,
    SlaMetrics,
    StatusCount,
)
from app.services import sla_service

router = APIRouter()


@router.get("/summary", response_model=DashboardSummary)
async def get_summary(
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Get dashboard summary with ticket counts by status, priority, and group."""
    # Total tickets
    total_result = await db.execute(select(func.count()).select_from(Ticket))
    total_tickets = total_result.scalar() or 0

    # Count by status
    status_query = select(Ticket.status, func.count()).group_by(Ticket.status)
    status_result = await db.execute(status_query)
    by_status = [
        StatusCount(status=row[0].value, count=row[1])
        for row in status_result.all()
    ]

    # Count by priority
    priority_query = select(Ticket.priority, func.count()).group_by(Ticket.priority)
    priority_result = await db.execute(priority_query)
    by_priority = [
        PriorityCount(priority=row[0].value, count=row[1])
        for row in priority_result.all()
    ]

    # Count by group (join groups table)
    group_query = (
        select(Group.name, func.count())
        .join(Ticket, Ticket.assigned_group_id == Group.id)
        .group_by(Group.name)
    )
    group_result = await db.execute(group_query)
    by_group = [
        GroupCount(group_name=row[0], count=row[1])
        for row in group_result.all()
    ]

    return DashboardSummary(
        total_tickets=total_tickets,
        by_status=by_status,
        by_priority=by_priority,
        by_group=by_group,
    )


@router.get("/sla", response_model=SlaMetrics)
async def get_sla_metrics(
    group_id: uuid.UUID | None = Query(None),
    priority: str | None = Query(None),
    date_from: datetime | None = Query(None),
    date_to: datetime | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Get SLA metrics (MTTA and MTTR) with optional filters."""
    mtta = await sla_service.get_mtta(
        db, group_id=group_id, priority=priority, date_from=date_from, date_to=date_to
    )
    mttr = await sla_service.get_mttr(
        db, group_id=group_id, priority=priority, date_from=date_from, date_to=date_to
    )

    # Resolve group name if group_id was provided
    group_name = None
    if group_id is not None:
        result = await db.execute(select(Group.name).where(Group.id == group_id))
        group_name = result.scalar_one_or_none()

    return SlaMetrics(
        mtta_seconds=mtta,
        mttr_seconds=mttr,
        group_name=group_name,
        priority=priority,
    )


@router.get("/activity", response_model=PaginatedResponse[AuditLogResponse])
async def get_activity(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Get recent audit log activity, paginated."""
    # Total count
    count_result = await db.execute(select(func.count()).select_from(AuditLog))
    total = count_result.scalar() or 0

    # Paginated query with actor and ticket relationships
    offset = (page - 1) * page_size
    query = (
        select(AuditLog)
        .order_by(AuditLog.created_at.desc())
        .limit(page_size)
        .offset(offset)
        .options(selectinload(AuditLog.actor), selectinload(AuditLog.ticket))
    )
    result = await db.execute(query)
    entries = result.scalars().all()

    items = [
        AuditLogResponse(
            id=entry.id,
            ticket_id=entry.ticket_id,
            ticket_number=entry.ticket.ticket_number if entry.ticket else None,
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

    pages = math.ceil(total / page_size) if total > 0 else 0

    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )
