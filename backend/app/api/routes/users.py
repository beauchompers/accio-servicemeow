import math
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import CurrentUser, get_current_user, require_role
from app.database import get_db
from app.models.base import UserRole
from app.schemas.common import PaginatedResponse
from app.schemas.user import ChangePasswordRequest, UserCreate, UserResponse, UserUpdate
from app.services import user_service

router = APIRouter()


@router.get("/me", response_model=UserResponse)
async def get_current_user_profile(
    current_user: CurrentUser = Depends(get_current_user),
):
    """Return the currently authenticated user's profile."""
    return current_user.user


@router.post("/me/password", status_code=status.HTTP_204_NO_CONTENT)
async def change_own_password(
    data: ChangePasswordRequest,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Change the currently authenticated user's password."""
    await user_service.change_own_password(
        db, current_user.user, data.current_password, data.new_password
    )
    await db.commit()


@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    data: UserCreate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_role(UserRole.admin)),
):
    """Create a new user. Requires admin role."""
    user = await user_service.create_user(db, data)
    await db.commit()
    return user


@router.get("/", response_model=PaginatedResponse[UserResponse])
async def list_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """List users with pagination. Requires authentication."""
    users, total = await user_service.list_users(db, page=page, page_size=page_size)
    pages = math.ceil(total / page_size) if total > 0 else 0
    return PaginatedResponse(
        items=users,
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Get a user by ID. Requires authentication."""
    return await user_service.get_user(db, user_id)


@router.patch("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: UUID,
    data: UserUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_role(UserRole.admin)),
):
    """Update a user. Requires admin role."""
    user = await user_service.update_user(db, user_id, data)
    await db.commit()
    await db.refresh(user)
    return user
