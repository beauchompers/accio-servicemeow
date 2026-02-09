import uuid
from datetime import datetime

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


@mcp.tool(description="Get available statuses, priorities, roles, and system configuration")
async def get_system_info() -> dict:
    """Get available statuses, priorities, roles, and system configuration.

    This tool does not require authentication. Use it to discover valid enum
    values before creating or updating tickets.
    """
    return {
        "summary": "System configuration",
        "data": {
            "statuses": [s.value for s in TicketStatus],
            "priorities": [p.value for p in TicketPriority],
            "roles": [r.value for r in UserRole],
            "ticket_number_format": "ASM-XXXX",
        },
    }


@mcp.tool(description="Get a summary of ticket counts by status, priority, and group")
async def get_dashboard_summary() -> dict:
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
            by_status = [{"status": s.value, "count": c} for s, c in status_result.all()]

            # By priority
            priority_result = await db.execute(
                select(Ticket.priority, func.count()).group_by(Ticket.priority)
            )
            by_priority = [{"priority": p.value, "count": c} for p, c in priority_result.all()]

            # By group
            group_result = await db.execute(
                select(Group.name, func.count())
                .join(Ticket, Ticket.assigned_group_id == Group.id)
                .group_by(Group.name)
            )
            by_group = [{"group_name": name, "count": c} for name, c in group_result.all()]

            return {
                "summary": f"{total} total tickets",
                "data": {
                    "total_tickets": total,
                    "by_status": by_status,
                    "by_priority": by_priority,
                    "by_group": by_group,
                },
            }
    except ValueError as e:
        return {"summary": f"Error: {e}", "data": None}
    except Exception as e:
        return {"summary": f"Unexpected error: {e}", "data": None}


@mcp.tool(description="Get SLA metrics (MTTA and MTTR) in minutes")
async def get_sla_metrics(
    group: str | None = None,
    priority: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
) -> dict:
    """Get SLA metrics (Mean Time To Assign and Mean Time To Resolve) in minutes.

    Args:
        group: Optional group name or UUID to filter by
        priority: Optional priority to filter by (critical, high, medium, low)
        date_from: Optional start date (ISO format)
        date_to: Optional end date (ISO format)
    """
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

            return {
                "summary": summary,
                "data": {
                    "mtta_minutes": mtta_min,
                    "mttr_minutes": mttr_min,
                },
            }
    except ValueError as e:
        return {"summary": f"Error: {e}", "data": None}
    except Exception as e:
        return {"summary": f"Unexpected error: {e}", "data": None}


@mcp.tool(description="List all groups with member counts")
async def list_groups() -> dict:
    """List all groups with member counts."""
    try:
        async with async_session() as db:
            await get_current_mcp_user(db)
            result = await db.execute(
                select(Group).options(selectinload(Group.memberships))
            )
            groups = result.scalars().all()
            return {
                "summary": f"{len(groups)} groups",
                "data": {
                    "groups": [
                        {
                            "id": str(g.id),
                            "name": g.name,
                            "description": g.description,
                            "member_count": len(g.memberships),
                        }
                        for g in groups
                    ],
                },
            }
    except ValueError as e:
        return {"summary": f"Error: {e}", "data": None}
    except Exception as e:
        return {"summary": f"Unexpected error: {e}", "data": None}


@mcp.tool(description="List users, optionally filtered by group")
async def list_users(
    group: str | None = None,
) -> dict:
    """List users, optionally filtered by group.

    Args:
        group: Optional group name or UUID to filter by
    """
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
            return {
                "summary": f"{len(users)} users",
                "data": {
                    "users": [
                        {
                            "id": str(u.id),
                            "username": u.username,
                            "full_name": u.full_name,
                            "email": u.email,
                            "role": u.role.value,
                        }
                        for u in users
                    ],
                },
            }
    except ValueError as e:
        return {"summary": f"Error: {e}", "data": None}
    except Exception as e:
        return {"summary": f"Unexpected error: {e}", "data": None}


@mcp.tool(description="Get the full audit trail for a ticket")
async def get_ticket_audit_log(
    ticket_id_or_number: str,
) -> dict:
    """Get the full audit trail for a ticket.

    Args:
        ticket_id_or_number: UUID or ticket number (e.g. ASM-0001)
    """
    try:
        async with async_session() as db:
            await get_current_mcp_user(db)
            tid = await resolve_ticket_id(db, ticket_id_or_number)
            entries = await audit_service.get_audit_log(db, tid)
            return {
                "summary": f"{len(entries)} audit entries",
                "data": {
                    "entries": [
                        {
                            "id": str(e.id),
                            "action": e.action,
                            "field_changed": e.field_changed,
                            "old_value": e.old_value,
                            "new_value": e.new_value,
                            "actor_id": str(e.actor_id) if e.actor_id else None,
                            "actor_name": e.actor_name,
                            "created_at": e.created_at.isoformat(),
                        }
                        for e in entries
                    ],
                },
            }
    except ValueError as e:
        return {"summary": f"Error: {e}", "data": None}
    except Exception as e:
        return {"summary": f"Unexpected error: {e}", "data": None}


@mcp.tool(description="List tickets assigned to the authenticated user")
async def get_my_tickets(
    status: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> dict:
    """List tickets assigned to the authenticated user.

    Args:
        status: Optional status filter (open, under_investigation, resolved)
        page: Page number (default 1)
        page_size: Results per page (default 20)
    """
    try:
        async with async_session() as db:
            current_user = await get_current_mcp_user(db)
            filters: dict = {"assigned_user_id": current_user.user.id}
            if status:
                filters["status"] = status

            tickets, total = await ticket_service.list_tickets(
                db, filters=filters, page=page, page_size=page_size
            )
            return {
                "summary": f"Found {total} tickets assigned to you (showing page {page})",
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
