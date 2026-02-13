import uuid
from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, Field
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from app.database import async_session
from app.mcp.auth import get_current_mcp_user
from app.mcp.resolvers import resolve_group, resolve_ticket_id
from app.mcp.server import mcp
from app.models.base import TicketPriority, TicketStatus, UserRole
from app.models.group import Group, GroupMembership
from app.models.ticket import Ticket
from app.models.user import User
from app.services import audit_service, sla_service, ticket_service

try:
    from mcp.types import ToolAnnotations
except ImportError:
    ToolAnnotations = None  # type: ignore[assignment,misc]


# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------

# -- Inner models --


class SystemInfoData(BaseModel):
    statuses: list[str] = Field(description="Valid ticket statuses")
    priorities: list[str] = Field(description="Valid priority levels")
    roles: list[str] = Field(description="Valid user roles")
    ticket_number_format: str = Field(description="Ticket number format pattern")


class StatusCountData(BaseModel):
    status: str = Field(description="Ticket status")
    count: int = Field(description="Number of tickets with this status")


class PriorityCountData(BaseModel):
    priority: str = Field(description="Priority level")
    count: int = Field(description="Number of tickets with this priority")


class GroupCountData(BaseModel):
    group_name: str = Field(description="Group name")
    count: int = Field(description="Number of tickets assigned to this group")


class DashboardData(BaseModel):
    total_tickets: int = Field(description="Total number of tickets")
    by_status: list[StatusCountData] = Field(description="Ticket counts by status")
    by_priority: list[PriorityCountData] = Field(description="Ticket counts by priority")
    by_group: list[GroupCountData] = Field(description="Ticket counts by assigned group")


class SlaMetricsData(BaseModel):
    mtta_minutes: float | None = Field(description="Mean Time To Assign in minutes")
    mttr_minutes: float | None = Field(description="Mean Time To Resolve in minutes")


class GroupData(BaseModel):
    id: str = Field(description="Group UUID")
    name: str = Field(description="Group name")
    description: str | None = Field(description="Group description")
    member_count: int = Field(description="Number of members in the group")


class UserData(BaseModel):
    id: str = Field(description="User UUID")
    username: str = Field(description="Username")
    full_name: str | None = Field(description="User's full display name")
    email: str = Field(description="User's email address")
    role: str = Field(description="User role")


class AuditEntryData(BaseModel):
    id: str = Field(description="Audit entry UUID")
    action: str = Field(description="Action performed (e.g. created, updated)")
    field_changed: str | None = Field(description="Field that was changed")
    old_value: str | None = Field(description="Previous value")
    new_value: str | None = Field(description="New value")
    actor_id: str | None = Field(description="Actor's UUID")
    actor_name: str | None = Field(description="Actor's display name")
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


# -- Container models --


class GroupListData(BaseModel):
    groups: list[GroupData] = Field(description="List of groups")


class UserListData(BaseModel):
    users: list[UserData] = Field(description="List of users")


class AuditLogData(BaseModel):
    entries: list[AuditEntryData] = Field(description="Audit log entries")


class TicketListData(BaseModel):
    total: int = Field(description="Total number of matching tickets")
    page: int = Field(description="Current page number")
    tickets: list[TicketListItemData] = Field(description="Tickets on this page")


# -- Wrapper (result) models --


class SystemInfoResult(BaseModel):
    summary: str = Field(description="Human-readable result message")
    data: SystemInfoData = Field(description="System configuration")


class DashboardResult(BaseModel):
    summary: str = Field(description="Human-readable result message")
    data: DashboardData | None = Field(description="Dashboard counts, or null on error")


class SlaMetricsResult(BaseModel):
    summary: str = Field(description="Human-readable result message")
    data: SlaMetricsData | None = Field(description="SLA metrics, or null on error")


class ListGroupsResult(BaseModel):
    summary: str = Field(description="Human-readable result message")
    data: GroupListData | None = Field(description="Groups list, or null on error")


class ListUsersResult(BaseModel):
    summary: str = Field(description="Human-readable result message")
    data: UserListData | None = Field(description="Users list, or null on error")


class AuditLogResult(BaseModel):
    summary: str = Field(description="Human-readable result message")
    data: AuditLogData | None = Field(description="Audit entries, or null on error")


class MyTicketsResult(BaseModel):
    summary: str = Field(description="Human-readable result message")
    data: TicketListData | None = Field(description="Paginated ticket list, or null on error")


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------


@mcp.tool(
    description="Get available statuses, priorities, roles, and system configuration",
    annotations=ToolAnnotations(readOnlyHint=True, openWorldHint=False),
)
async def get_system_info() -> SystemInfoResult:
    """Get available statuses, priorities, roles, and system configuration.

    This tool does not require authentication. Use it to discover valid enum
    values before creating or updating tickets.
    """
    return SystemInfoResult(
        summary="System configuration",
        data=SystemInfoData(
            statuses=[s.value for s in TicketStatus],
            priorities=[p.value for p in TicketPriority],
            roles=[r.value for r in UserRole],
            ticket_number_format="ASM-XXXX",
        ),
    )


@mcp.tool(
    description="Get a summary of ticket counts by status, priority, and group",
    annotations=ToolAnnotations(readOnlyHint=True, openWorldHint=False),
)
async def get_dashboard_summary() -> DashboardResult:
    """Get a summary of ticket counts by status, priority, and group."""
    try:
        async with async_session() as db:
            await get_current_mcp_user(db)

            # Total tickets
            total_result = await db.execute(select(func.count()).select_from(Ticket))
            total = total_result.scalar() or 0

            # By status
            status_result = await db.execute(
                select(Ticket.status, func.count()).group_by(Ticket.status)
            )
            by_status = [
                StatusCountData(status=s.value, count=c)
                for s, c in status_result.all()
            ]

            # By priority
            priority_result = await db.execute(
                select(Ticket.priority, func.count()).group_by(Ticket.priority)
            )
            by_priority = [
                PriorityCountData(priority=p.value, count=c)
                for p, c in priority_result.all()
            ]

            # By group
            group_result = await db.execute(
                select(Group.name, func.count())
                .join(Ticket, Ticket.assigned_group_id == Group.id)
                .group_by(Group.name)
            )
            by_group = [
                GroupCountData(group_name=name, count=c)
                for name, c in group_result.all()
            ]

            return DashboardResult(
                summary=f"{total} total tickets",
                data=DashboardData(
                    total_tickets=total,
                    by_status=by_status,
                    by_priority=by_priority,
                    by_group=by_group,
                ),
            )
    except ValueError as e:
        return DashboardResult(summary=f"Error: {e}", data=None)
    except Exception as e:
        return DashboardResult(summary=f"Unexpected error: {e}", data=None)


@mcp.tool(
    description="Get SLA metrics (MTTA and MTTR) in minutes",
    annotations=ToolAnnotations(readOnlyHint=True, openWorldHint=False),
)
async def get_sla_metrics(
    group: Annotated[str | None, Field(description="Group name or UUID to filter by")] = None,
    priority: Annotated[str | None, Field(description="Priority to filter by: critical, high, medium, or low")] = None,
    date_from: Annotated[str | None, Field(description="Start date in ISO format (e.g. 2026-01-01)")] = None,
    date_to: Annotated[str | None, Field(description="End date in ISO format (e.g. 2026-01-31)")] = None,
) -> SlaMetricsResult:
    """Get SLA metrics (Mean Time To Assign and Mean Time To Resolve) in minutes."""
    try:
        df = datetime.fromisoformat(date_from) if date_from else None
        dt = datetime.fromisoformat(date_to) if date_to else None

        async with async_session() as db:
            await get_current_mcp_user(db)

            gid = await resolve_group(db, group) if group else None
            mtta = await sla_service.get_mtta(db, group_id=gid, priority=priority, date_from=df, date_to=dt)
            mttr = await sla_service.get_mttr(db, group_id=gid, priority=priority, date_from=df, date_to=dt)

            mtta_min = round(mtta / 60, 1) if mtta is not None else None
            mttr_min = round(mttr / 60, 1) if mttr is not None else None

            if mtta_min is not None and mttr_min is not None:
                summary = f"MTTA: {mtta_min} min, MTTR: {mttr_min} min"
            else:
                summary = "No SLA data available"

            return SlaMetricsResult(
                summary=summary,
                data=SlaMetricsData(
                    mtta_minutes=mtta_min,
                    mttr_minutes=mttr_min,
                ),
            )
    except ValueError as e:
        return SlaMetricsResult(summary=f"Error: {e}", data=None)
    except Exception as e:
        return SlaMetricsResult(summary=f"Unexpected error: {e}", data=None)


@mcp.tool(
    description="List all groups with member counts",
    annotations=ToolAnnotations(readOnlyHint=True, openWorldHint=False),
)
async def list_groups() -> ListGroupsResult:
    """List all groups with member counts."""
    try:
        async with async_session() as db:
            await get_current_mcp_user(db)
            result = await db.execute(
                select(Group).options(selectinload(Group.memberships))
            )
            groups = result.scalars().all()
            return ListGroupsResult(
                summary=f"{len(groups)} groups",
                data=GroupListData(
                    groups=[
                        GroupData(
                            id=str(g.id),
                            name=g.name,
                            description=g.description,
                            member_count=len(g.memberships),
                        )
                        for g in groups
                    ],
                ),
            )
    except ValueError as e:
        return ListGroupsResult(summary=f"Error: {e}", data=None)
    except Exception as e:
        return ListGroupsResult(summary=f"Unexpected error: {e}", data=None)


@mcp.tool(
    description="List users, optionally filtered by group",
    annotations=ToolAnnotations(readOnlyHint=True, openWorldHint=False),
)
async def list_users(
    group: Annotated[str | None, Field(description="Group name or UUID to filter by")] = None,
) -> ListUsersResult:
    """List active users, optionally filtered by group membership."""
    try:
        async with async_session() as db:
            await get_current_mcp_user(db)
            query = select(User).where(User.is_active == True)  # noqa: E712
            if group:
                group_id = await resolve_group(db, group)
                query = (
                    query
                    .join(GroupMembership, GroupMembership.user_id == User.id)
                    .where(GroupMembership.group_id == group_id)
                )
            result = await db.execute(query)
            users = result.scalars().all()
            return ListUsersResult(
                summary=f"{len(users)} users",
                data=UserListData(
                    users=[
                        UserData(
                            id=str(u.id),
                            username=u.username,
                            full_name=u.full_name,
                            email=u.email,
                            role=u.role.value,
                        )
                        for u in users
                    ],
                ),
            )
    except ValueError as e:
        return ListUsersResult(summary=f"Error: {e}", data=None)
    except Exception as e:
        return ListUsersResult(summary=f"Unexpected error: {e}", data=None)


@mcp.tool(
    description="Get the full audit trail for a ticket",
    annotations=ToolAnnotations(readOnlyHint=True, openWorldHint=False),
)
async def get_ticket_audit_log(
    ticket_id_or_number: Annotated[str, Field(description="Ticket UUID or number (e.g. ASM-0001)")],
) -> AuditLogResult:
    """Get the full audit trail for a ticket."""
    try:
        async with async_session() as db:
            await get_current_mcp_user(db)
            tid = await resolve_ticket_id(db, ticket_id_or_number)
            entries = await audit_service.get_audit_log(db, tid)
            return AuditLogResult(
                summary=f"{len(entries)} audit entries",
                data=AuditLogData(
                    entries=[
                        AuditEntryData(
                            id=str(e.id),
                            action=e.action,
                            field_changed=e.field_changed,
                            old_value=e.old_value,
                            new_value=e.new_value,
                            actor_id=str(e.actor_id) if e.actor_id else None,
                            actor_name=e.actor_name,
                            created_at=e.created_at.isoformat(),
                        )
                        for e in entries
                    ],
                ),
            )
    except ValueError as e:
        return AuditLogResult(summary=f"Error: {e}", data=None)
    except Exception as e:
        return AuditLogResult(summary=f"Unexpected error: {e}", data=None)


@mcp.tool(
    description="List tickets assigned to the authenticated user",
    annotations=ToolAnnotations(readOnlyHint=True, openWorldHint=False),
)
async def get_my_tickets(
    status: Annotated[str | None, Field(description="Filter by status: open, under_investigation, or resolved")] = None,
    page: Annotated[int, Field(description="Page number (default 1)")] = 1,
    page_size: Annotated[int, Field(description="Results per page (default 20)")] = 20,
) -> MyTicketsResult:
    """List tickets assigned to the authenticated user."""
    try:
        async with async_session() as db:
            current_user = await get_current_mcp_user(db)
            filters: dict = {"assigned_user_id": current_user.user.id}
            if status:
                filters["status"] = status

            tickets, total = await ticket_service.list_tickets(
                db, filters=filters, page=page, page_size=page_size
            )
            return MyTicketsResult(
                summary=f"Found {total} tickets assigned to you (showing page {page})",
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
        return MyTicketsResult(summary=f"Error: {e}", data=None)
    except Exception as e:
        return MyTicketsResult(summary=f"Unexpected error: {e}", data=None)
