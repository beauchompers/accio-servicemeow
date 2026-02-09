from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate
from app.services import auth_service


async def create_user(db: AsyncSession, data: UserCreate) -> User:
    """Create a new user. Raises 409 if username or email already exists."""
    # Check for existing username
    result = await db.execute(select(User).where(User.username == data.username))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username already exists",
        )

    # Check for existing email
    result = await db.execute(select(User).where(User.email == data.email))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already exists",
        )

    user = User(
        username=data.username,
        email=data.email,
        full_name=data.full_name,
        hashed_password=auth_service.hash_password(data.password),
        role=data.role,
    )
    db.add(user)
    await db.flush()
    return user


async def get_user(db: AsyncSession, user_id: UUID) -> User:
    """Get a user by ID. Raises 404 if not found."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    return user


async def get_user_by_username(db: AsyncSession, username: str) -> User | None:
    """Get a user by username. Returns None if not found."""
    result = await db.execute(select(User).where(User.username == username))
    return result.scalar_one_or_none()


async def list_users(
    db: AsyncSession, page: int = 1, page_size: int = 25
) -> tuple[list[User], int]:
    """Return a paginated list of users and total count."""
    # Get total count
    count_result = await db.execute(select(func.count()).select_from(User))
    total = count_result.scalar_one()

    # Get paginated results
    offset = (page - 1) * page_size
    result = await db.execute(
        select(User).order_by(User.created_at).offset(offset).limit(page_size)
    )
    users = list(result.scalars().all())

    return users, total


async def update_user(db: AsyncSession, user_id: UUID, data: UserUpdate) -> User:
    """Partial update of a user. Only sets non-None fields. Raises 404 if not found."""
    user = await get_user(db, user_id)

    update_data = data.model_dump(exclude_none=True)
    password = update_data.pop("password", None)
    for field, value in update_data.items():
        setattr(user, field, value)
    if password is not None:
        user.hashed_password = auth_service.hash_password(password)

    await db.flush()
    return user


async def change_own_password(
    db: AsyncSession, user: User, current_password: str, new_password: str
) -> None:
    """Change a user's own password. Verifies current password first."""
    if not auth_service.verify_password(current_password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )
    user.hashed_password = auth_service.hash_password(new_password)
    await db.flush()
