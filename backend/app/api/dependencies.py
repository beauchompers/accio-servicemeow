import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.api_key import ApiKey
from app.models.base import UserRole
from app.models.user import User
from app.services import auth_service


@dataclass
class CurrentUser:
    user: User
    auth_type: str  # "jwt" or "api_key"
    api_key_id: uuid.UUID | None = None


async def get_current_user(
    authorization: str | None = Header(None),
    api_key: str | None = Header(None, alias="api_key"),
    db: AsyncSession = Depends(get_db),
) -> CurrentUser:
    """Unified auth dependency. Tries JWT first, then API key."""
    # Try JWT
    if authorization and authorization.startswith("Bearer "):
        token = authorization[7:]
        try:
            payload = auth_service.decode_token(token)
            if payload.get("type") != "access":
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")
            user_id = uuid.UUID(payload["sub"])
        except HTTPException:
            raise
        except Exception:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")

        result = await db.execute(select(User).where(User.id == user_id, User.is_active == True))
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or inactive")
        return CurrentUser(user=user, auth_type="jwt")

    # Try API key
    if api_key:
        # Find matching key by prefix
        prefix = api_key[:8]
        result = await db.execute(
            select(ApiKey).where(ApiKey.key_prefix == prefix, ApiKey.is_active == True)
        )
        keys = result.scalars().all()
        for key in keys:
            if auth_service.verify_api_key(api_key, key.key_hash):
                # Check expiry
                if key.expires_at and key.expires_at < datetime.now(timezone.utc):
                    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="API key expired")
                # Load user
                user_result = await db.execute(select(User).where(User.id == key.user_id, User.is_active == True))
                user = user_result.scalar_one_or_none()
                if not user:
                    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="API key user not found or inactive")
                # Update last_used_at (flush, not commit — route handler commits)
                key.last_used_at = datetime.now(timezone.utc)
                await db.flush()
                return CurrentUser(user=user, auth_type="api_key", api_key_id=key.id)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")

    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")


def require_role(*roles: UserRole):
    """Dependency factory that checks if the current user has one of the required roles."""
    async def role_checker(current_user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if current_user.user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role {current_user.user.role.value} not authorized. Required: {[r.value for r in roles]}"
            )
        return current_user
    return role_checker
