"""Name-or-UUID resolvers for MCP tool parameters."""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.group import Group
from app.models.user import User


async def resolve_ticket_id(db: AsyncSession, identifier: str) -> uuid.UUID:
    """Resolve a ticket number (ASM-XXXX) or UUID string to a UUID.

    Args:
        db: Active database session.
        identifier: Either a UUID string or a ticket number (e.g. ASM-0001).

    Returns:
        The ticket's UUID.

    Raises:
        ValueError: If the identifier is not a valid UUID and no ticket
            with that number exists.
    """
    if identifier.upper().startswith("ASM-"):
        from app.services import ticket_service

        ticket = await ticket_service.get_ticket_by_number(db, identifier.upper())
        if ticket is None:
            raise ValueError(f"Ticket not found: {identifier}")
        return ticket.id
    return uuid.UUID(identifier)


async def resolve_group(db: AsyncSession, identifier: str) -> uuid.UUID:
    """Resolve a group name or UUID string to a UUID.

    Args:
        db: Active database session.
        identifier: Either a UUID string or a group name.

    Returns:
        The group's UUID.

    Raises:
        ValueError: If the identifier is not a valid UUID and no group
            with that name exists.
    """
    try:
        return uuid.UUID(identifier)
    except ValueError:
        pass

    result = await db.execute(select(Group.id).where(Group.name == identifier))
    group_id = result.scalar_one_or_none()
    if group_id is None:
        raise ValueError(f"Group not found: {identifier}")
    return group_id


async def resolve_user(db: AsyncSession, identifier: str) -> uuid.UUID:
    """Resolve a username or UUID string to a UUID.

    Args:
        db: Active database session.
        identifier: Either a UUID string or a username.

    Returns:
        The user's UUID.

    Raises:
        ValueError: If the identifier is not a valid UUID and no user
            with that username exists.
    """
    try:
        return uuid.UUID(identifier)
    except ValueError:
        pass

    result = await db.execute(select(User.id).where(User.username == identifier))
    user_id = result.scalar_one_or_none()
    if user_id is None:
        raise ValueError(f"User not found: {identifier}")
    return user_id
