from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.base import TicketPriority
from app.models.sla_config import SlaConfig
from app.schemas.sla_config import SlaConfigItem


PRIORITY_ORDER = {p.value: i for i, p in enumerate(TicketPriority)}


async def get_all(db: AsyncSession) -> list[SlaConfig]:
    result = await db.execute(select(SlaConfig))
    rows = list(result.scalars().all())
    rows.sort(key=lambda r: PRIORITY_ORDER.get(r.priority.value, 99))
    return rows


async def bulk_upsert(db: AsyncSession, configs: list[SlaConfigItem]) -> list[SlaConfig]:
    results: list[SlaConfig] = []
    for item in configs:
        result = await db.execute(
            select(SlaConfig).where(SlaConfig.priority == item.priority)
        )
        existing = result.scalar_one_or_none()
        if existing:
            existing.target_assign_minutes = item.target_assign_minutes
            existing.target_resolve_minutes = item.target_resolve_minutes
            results.append(existing)
        else:
            new_config = SlaConfig(
                priority=item.priority,
                target_assign_minutes=item.target_assign_minutes,
                target_resolve_minutes=item.target_resolve_minutes,
            )
            db.add(new_config)
            await db.flush()
            results.append(new_config)
    await db.flush()
    results.sort(key=lambda r: PRIORITY_ORDER.get(r.priority.value, 99))
    return results
