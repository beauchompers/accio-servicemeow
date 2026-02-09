import uuid

from fastapi import APIRouter, Cookie, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.auth import LoginRequest, TokenResponse
from app.services import auth_service
from app.services import user_service

router = APIRouter()


@router.post("/login", response_model=TokenResponse)
async def login(
    data: LoginRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    """Authenticate user and return access token. Sets refresh token as HTTP-only cookie."""
    user = await user_service.get_user_by_username(db, data.username)
    if not user or not auth_service.verify_password(data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )

    access_token = auth_service.create_access_token(user.id, user.role.value)
    refresh_token = auth_service.create_refresh_token(user.id)

    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=True,
        samesite="strict",
    )

    return TokenResponse(access_token=access_token)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    db: AsyncSession = Depends(get_db),
    refresh_token: str | None = Cookie(None),
):
    """Issue a new access token using the refresh token cookie."""
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token missing",
        )

    try:
        payload = auth_service.decode_token(refresh_token)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )

    if payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type",
        )

    user_id = uuid.UUID(payload["sub"])
    user = await user_service.get_user(db, user_id)

    access_token = auth_service.create_access_token(user.id, user.role.value)
    return TokenResponse(access_token=access_token)


@router.post("/logout")
async def logout(response: Response):
    """Log out by deleting the refresh token cookie."""
    response.delete_cookie(key="refresh_token")
    return {"message": "Logged out"}
