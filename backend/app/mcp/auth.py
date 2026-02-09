"""MCP transport-level authentication via ASGI middleware + contextvars.

Authenticates API keys at the ASGI layer before requests reach the MCP framework.
Stores lightweight auth info in a contextvar so MCP tools can retrieve the
authenticated user without passing credentials as tool parameters.
"""

from __future__ import annotations

import json
import uuid
from contextvars import ContextVar
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import select

from app.database import async_session
from app.models.api_key import ApiKey
from app.models.user import User
from app.services.auth_service import verify_api_key

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.api.dependencies import CurrentUser


@dataclass(frozen=True)
class McpAuthInfo:
    """Lightweight auth identity safe to store in a contextvar.

    Contains only scalar fields -- no SQLAlchemy models -- so it can
    safely cross async-session boundaries.
    """

    user_id: uuid.UUID
    auth_type: str
    api_key_id: uuid.UUID | None = None


mcp_auth_var: ContextVar[McpAuthInfo | None] = ContextVar("mcp_auth_var", default=None)


async def _authenticate_api_key(api_key_header: str) -> McpAuthInfo:
    """Validate an API key and return auth info.

    Opens its own database session (separate from any tool session) to
    perform prefix lookup + bcrypt verification, check expiry and user
    active status, and update ``last_used_at``.

    Raises:
        ValueError: If the key is invalid, expired, or the user is inactive.
    """
    async with async_session() as db:
        prefix = api_key_header[:8]
        result = await db.execute(
            select(ApiKey).where(ApiKey.key_prefix == prefix, ApiKey.is_active == True)  # noqa: E712
        )
        keys = result.scalars().all()

        for key in keys:
            if verify_api_key(api_key_header, key.key_hash):
                if key.expires_at and key.expires_at < datetime.now(timezone.utc):
                    raise ValueError("API key expired")

                user_result = await db.execute(
                    select(User).where(User.id == key.user_id, User.is_active == True)  # noqa: E712
                )
                user = user_result.scalar_one_or_none()
                if not user:
                    raise ValueError("API key user not found or inactive")

                key.last_used_at = datetime.now(timezone.utc)
                # commit() (not flush()) because this is the middleware's own
                # session — it closes when the context manager exits, so a
                # flush-only would be lost.
                await db.commit()

                return McpAuthInfo(
                    user_id=user.id,
                    auth_type="api_key",
                    api_key_id=key.id,
                )

        raise ValueError("Invalid API key")


async def get_current_mcp_user(db: AsyncSession) -> CurrentUser:
    """Build a ``CurrentUser`` from the contextvar set by the middleware.

    Loads the ``User`` model by primary key from the provided session so
    the returned object is bound to the caller's session.

    Args:
        db: The async session owned by the calling tool.

    Returns:
        A ``CurrentUser`` instance.

    Raises:
        ValueError: If no auth info is present in the contextvar
            (i.e., the request was unauthenticated).
    """
    from app.api.dependencies import CurrentUser  # avoid circular import at module level

    auth_info = mcp_auth_var.get()
    if auth_info is None:
        raise ValueError("Authentication required -- provide an api_key header")

    result = await db.execute(select(User).where(User.id == auth_info.user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise ValueError("Authenticated user no longer exists")

    return CurrentUser(
        user=user,
        auth_type=auth_info.auth_type,
        api_key_id=auth_info.api_key_id,
    )


class McpAuthMiddleware:
    """ASGI middleware that authenticates MCP requests via API key header.

    Behaviour:
    - Non-HTTP scopes: passed through unchanged.
    - HTTP with valid ``api_key`` header: contextvar set, request forwarded.
    - HTTP with invalid ``api_key`` header: HTTP 401 JSON response returned.
    - HTTP without ``api_key`` header: passed through (allows tool discovery).
    - Contextvar is always reset in a ``finally`` block.
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        token = mcp_auth_var.set(None)
        try:
            # Extract api_key from headers
            api_key_value = None
            for header_name, header_value in scope.get("headers", []):
                if header_name == b"api_key":
                    api_key_value = header_value.decode("utf-8")
                    break

            if api_key_value:
                try:
                    auth_info = await _authenticate_api_key(api_key_value)
                    mcp_auth_var.set(auth_info)
                except ValueError as exc:
                    # Invalid key -- return 401 before MCP framework sees it
                    await self._send_401(send, str(exc))
                    return

            # Valid key, or no key (unauthenticated discovery) -- forward
            await self.app(scope, receive, send)
        finally:
            mcp_auth_var.reset(token)

    @staticmethod
    async def _send_401(send, detail: str) -> None:
        """Send an HTTP 401 JSON error response."""
        body = json.dumps({"error": detail}).encode("utf-8")
        await send(
            {
                "type": "http.response.start",
                "status": 401,
                "headers": [
                    [b"content-type", b"application/json"],
                    [b"content-length", str(len(body)).encode("utf-8")],
                ],
            }
        )
        await send(
            {
                "type": "http.response.body",
                "body": body,
            }
        )
