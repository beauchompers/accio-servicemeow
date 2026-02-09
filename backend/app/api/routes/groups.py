import math
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import CurrentUser, get_current_user
from app.database import get_db
from app.schemas.common import PaginatedResponse
from app.schemas.group import (
    GroupCreate,
    GroupDetailResponse,
    GroupMemberAdd,
    GroupMemberResponse,
    GroupResponse,
    GroupUpdate,
)
from app.services import group_service

router = APIRouter()


@router.post("/", response_model=GroupResponse, status_code=status.HTTP_201_CREATED)
async def create_group(
    data: GroupCreate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Create a new group. Requires authentication."""
    group = await group_service.create_group(db, data)
    await db.commit()
    await db.refresh(group)
    return GroupResponse(
        id=group.id,
        name=group.name,
        description=group.description,
        member_count=0,
        created_at=group.created_at,
        updated_at=group.updated_at,
    )


@router.get("/", response_model=PaginatedResponse[GroupResponse])
async def list_groups(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """List all groups with pagination and member counts."""
    items, total = await group_service.list_groups(db, page=page, page_size=page_size)
    pages = math.ceil(total / page_size) if total > 0 else 0
    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


@router.get("/{group_id}", response_model=GroupDetailResponse)
async def get_group(
    group_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Get a group with its members. Requires authentication."""
    group = await group_service.get_group(db, group_id)
    members = [
        GroupMemberResponse(
            user_id=membership.user_id,
            username=membership.user.username,
            full_name=membership.user.full_name,
            is_lead=membership.is_lead,
            joined_at=membership.joined_at,
        )
        for membership in group.memberships
    ]
    member_count = len(members)
    return GroupDetailResponse(
        id=group.id,
        name=group.name,
        description=group.description,
        member_count=member_count,
        created_at=group.created_at,
        updated_at=group.updated_at,
        members=members,
    )


@router.patch("/{group_id}", response_model=GroupResponse)
async def update_group(
    group_id: UUID,
    data: GroupUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Update a group. Requires authentication."""
    group = await group_service.update_group(db, group_id, data)
    await db.commit()
    await db.refresh(group)
    member_count = await group_service.get_member_count(db, group_id)
    return GroupResponse(
        id=group.id,
        name=group.name,
        description=group.description,
        member_count=member_count,
        created_at=group.created_at,
        updated_at=group.updated_at,
    )


@router.post(
    "/{group_id}/members",
    response_model=GroupMemberResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_member(
    group_id: UUID,
    data: GroupMemberAdd,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Add a member to a group. Requires authentication."""
    membership = await group_service.add_member(
        db, group_id, data.user_id, data.is_lead
    )
    # Capture values before commit expires relationships
    resp = GroupMemberResponse(
        user_id=membership.user_id,
        username=membership.user.username,
        full_name=membership.user.full_name,
        is_lead=membership.is_lead,
        joined_at=membership.joined_at,
    )
    await db.commit()
    return resp


@router.delete(
    "/{group_id}/members/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def remove_member(
    group_id: UUID,
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Remove a member from a group. Requires authentication."""
    await group_service.remove_member(db, group_id, user_id)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
