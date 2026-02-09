from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.group import Group, GroupMembership
from app.models.user import User
from app.schemas.group import GroupCreate, GroupUpdate


async def create_group(db: AsyncSession, data: GroupCreate) -> Group:
    """Create a new group. Raises 409 if name already exists."""
    result = await db.execute(select(Group).where(Group.name == data.name))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Group name already exists",
        )

    group = Group(
        name=data.name,
        description=data.description,
    )
    db.add(group)
    await db.flush()
    return group


async def get_group(db: AsyncSession, group_id: UUID) -> Group:
    """Get a group by ID with eager-loaded members. Raises 404 if not found."""
    result = await db.execute(
        select(Group)
        .where(Group.id == group_id)
        .options(
            selectinload(Group.memberships).selectinload(GroupMembership.user)
        )
    )
    group = result.scalar_one_or_none()
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Group not found",
        )
    return group


async def list_groups(
    db: AsyncSession, page: int = 1, page_size: int = 50
) -> tuple[list[dict], int]:
    """Return paginated groups with member counts."""
    # Total count
    count_result = await db.execute(select(func.count()).select_from(Group))
    total = count_result.scalar() or 0

    # Member count subquery
    member_count_sq = (
        select(
            GroupMembership.group_id,
            func.count().label("member_count"),
        )
        .group_by(GroupMembership.group_id)
        .subquery()
    )

    offset = (page - 1) * page_size
    query = (
        select(Group, func.coalesce(member_count_sq.c.member_count, 0).label("member_count"))
        .outerjoin(member_count_sq, Group.id == member_count_sq.c.group_id)
        .order_by(Group.created_at)
        .limit(page_size)
        .offset(offset)
    )
    result = await db.execute(query)
    rows = result.all()

    items = []
    for group, count in rows:
        items.append({
            "id": group.id,
            "name": group.name,
            "description": group.description,
            "member_count": count,
            "created_at": group.created_at,
            "updated_at": group.updated_at,
        })

    return items, total


async def get_member_count(db: AsyncSession, group_id: UUID) -> int:
    """Get the number of members in a group."""
    result = await db.execute(
        select(func.count()).where(GroupMembership.group_id == group_id)
    )
    return result.scalar() or 0


async def update_group(db: AsyncSession, group_id: UUID, data: GroupUpdate) -> Group:
    """Partial update of a group. Only sets non-None fields. Raises 404 if not found."""
    result = await db.execute(select(Group).where(Group.id == group_id))
    group = result.scalar_one_or_none()
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Group not found",
        )

    update_data = data.model_dump(exclude_none=True)
    for field, value in update_data.items():
        setattr(group, field, value)

    await db.flush()
    return group


async def add_member(
    db: AsyncSession, group_id: UUID, user_id: UUID, is_lead: bool = False
) -> GroupMembership:
    """Add a user to a group. Raises 404 if group or user not found. Raises 409 if already a member."""
    # Check group exists
    result = await db.execute(select(Group).where(Group.id == group_id))
    if not result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Group not found",
        )

    # Check user exists
    result = await db.execute(select(User).where(User.id == user_id))
    if not result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Check not already a member
    result = await db.execute(
        select(GroupMembership).where(
            GroupMembership.group_id == group_id,
            GroupMembership.user_id == user_id,
        )
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User is already a member of this group",
        )

    membership = GroupMembership(
        group_id=group_id,
        user_id=user_id,
        is_lead=is_lead,
    )
    db.add(membership)
    await db.flush()

    # Eager-load the user relationship for the response
    result = await db.execute(
        select(GroupMembership)
        .where(GroupMembership.id == membership.id)
        .options(selectinload(GroupMembership.user))
    )
    return result.scalar_one()


async def remove_member(db: AsyncSession, group_id: UUID, user_id: UUID) -> None:
    """Remove a user from a group. Raises 404 if membership not found."""
    result = await db.execute(
        select(GroupMembership).where(
            GroupMembership.group_id == group_id,
            GroupMembership.user_id == user_id,
        )
    )
    membership = result.scalar_one_or_none()
    if not membership:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Membership not found",
        )

    await db.delete(membership)
    await db.flush()
