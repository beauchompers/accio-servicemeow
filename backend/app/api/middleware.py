import time
from collections import defaultdict

import jwt
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.config import settings

# 100 requests per minute per identity
RATE_LIMIT = 100
WINDOW_SECONDS = 60


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        self._requests: dict[str, list[float]] = defaultdict(list)

    def _extract_identity(self, request: Request) -> str | None:
        """Extract rate-limit key from API key or JWT Bearer token."""
        # API key: use prefix
        api_key = request.headers.get("api_key")
        if api_key:
            return f"apikey:{api_key[:8]}"

        # JWT: decode sub claim (lightweight, no full validation — route does that)
        auth_header = request.headers.get("authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
            try:
                payload = jwt.decode(
                    token,
                    settings.jwt_secret,
                    algorithms=[settings.jwt_algorithm],
                    options={"verify_exp": False},
                )
                sub = payload.get("sub")
                if sub:
                    return f"jwt:{sub}"
            except Exception:
                pass

        return None

    async def dispatch(self, request: Request, call_next):
        identity = self._extract_identity(request)
        if not identity:
            return await call_next(request)

        now = time.time()
        window_start = now - WINDOW_SECONDS

        # Clean old entries and check limit
        timestamps = self._requests[identity]
        self._requests[identity] = [t for t in timestamps if t > window_start]

        if len(self._requests[identity]) >= RATE_LIMIT:
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded. Maximum 100 requests per minute."},
            )

        self._requests[identity].append(now)
        return await call_next(request)
