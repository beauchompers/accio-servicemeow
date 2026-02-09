import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.audit_log import AuditLog
from app.models.base import ActorType


async def log_action(
    db: AsyncSession,
    ticket_id: uuid.UUID,
    actor_id: uuid.UUID | None,
    actor_type: ActorType,
    action: str,
    field_changed: str | None = None,
    old_value: str | None = None,
    new_value: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> AuditLog:
    """Append an audit log entry for a ticket action."""
    entry = AuditLog(
        ticket_id=ticket_id,
        actor_id=actor_id,
        actor_type=actor_type,
        action=action,
        field_changed=field_changed,
        old_value=old_value,
        new_value=new_value,
    )
    # Handle the metadata_ attribute mapping
    if metadata is not None:
        entry.metadata_ = metadata
    db.add(entry)
    await db.flush()
    return entry


async def get_audit_log(
    db: AsyncSession,
    ticket_id: uuid.UUID,
) -> list[AuditLog]:
    """Get all audit log entries for a ticket, ordered by created_at desc."""
    result = await db.execute(
        select(AuditLog)
        .where(AuditLog.ticket_id == ticket_id)
        .order_by(AuditLog.created_at.desc())
        .options(selectinload(AuditLog.actor))
    )
    return list(result.scalars().all())
