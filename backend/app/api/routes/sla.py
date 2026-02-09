from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import CurrentUser, get_current_user, require_role
from app.database import get_db
from app.models.base import UserRole
from app.schemas.sla_config import SlaConfigItem, SlaConfigUpdate
from app.services import sla_config_service

router = APIRouter()


@router.get("", response_model=list[SlaConfigItem])
async def get_sla_config(
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Get all SLA configuration entries."""
    return await sla_config_service.get_all(db)


@router.patch("", response_model=list[SlaConfigItem])
async def update_sla_config(
    data: SlaConfigUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_role(UserRole.admin)),
):
    """Bulk upsert SLA configuration. Admin only."""
    configs = await sla_config_service.bulk_upsert(db, data.configs)
    await db.commit()
    return configs
