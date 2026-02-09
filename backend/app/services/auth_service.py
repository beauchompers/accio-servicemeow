import secrets
import uuid
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.api_key import ApiKey


def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    """Verify a password against its bcrypt hash."""
    return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))


def create_access_token(user_id: uuid.UUID, role: str) -> str:
    """Create a JWT access token with exp, sub (user_id), and role claims."""
    payload = {
        "sub": str(user_id),
        "role": role,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes),
        "type": "access",
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def create_refresh_token(user_id: uuid.UUID) -> str:
    """Create a JWT refresh token with longer expiry."""
    payload = {
        "sub": str(user_id),
        "exp": datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_expire_days),
        "type": "refresh",
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> dict:
    """Decode and validate a JWT token. Raises jwt.InvalidTokenError on failure."""
    return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])


def generate_api_key() -> tuple[str, str, str]:
    """Generate an API key. Returns (plain_key, key_hash, key_prefix)."""
    plain_key = "asm_" + secrets.token_hex(20)
    key_hash = bcrypt.hashpw(plain_key.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    key_prefix = plain_key[:8]
    return plain_key, key_hash, key_prefix


def verify_api_key(plain_key: str, key_hash: str) -> bool:
    """Verify an API key against its bcrypt hash."""
    return bcrypt.checkpw(plain_key.encode("utf-8"), key_hash.encode("utf-8"))


async def create_api_key_for_user(
    db: AsyncSession,
    user_id: uuid.UUID,
    name: str,
) -> tuple[ApiKey, str]:
    """Create an API key for a user. Returns (ApiKey model, plain_key)."""
    plain_key, key_hash, key_prefix = generate_api_key()
    api_key = ApiKey(
        name=name,
        key_hash=key_hash,
        key_prefix=key_prefix,
        user_id=user_id,
    )
    db.add(api_key)
    await db.flush()
    return api_key, plain_key


async def list_api_keys(db: AsyncSession, user_id: uuid.UUID) -> list[ApiKey]:
    """List all active API keys for a user."""
    result = await db.execute(
        select(ApiKey).where(ApiKey.user_id == user_id, ApiKey.is_active == True)
    )
    return list(result.scalars().all())


async def revoke_api_key(
    db: AsyncSession,
    user_id: uuid.UUID,
    key_id: uuid.UUID,
) -> None:
    """Revoke an API key by setting is_active=False."""
    from fastapi import HTTPException, status

    result = await db.execute(
        select(ApiKey).where(ApiKey.id == key_id, ApiKey.user_id == user_id)
    )
    api_key = result.scalar_one_or_none()
    if api_key is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="API key not found"
        )
    api_key.is_active = False
    await db.flush()
