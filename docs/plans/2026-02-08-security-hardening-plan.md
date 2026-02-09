# Security Hardening Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Harden the Accio ServiceMeow application against real security vulnerabilities before pushing to GitHub.

**Architecture:** Targeted fixes across the existing stack — no structural changes. CORS lockdown, path traversal guards, rate limiting extension, attachment security, security headers, cookie hardening, and documentation.

**Tech Stack:** Python/FastAPI, nginx, Docker, python-magic (new dependency)

**Design:** `docs/plans/2026-02-08-security-hardening-design.md`

---

### Task 1: CORS — Restrict Origins

**Files:**
- Modify: `backend/app/config.py:4-39` — add `allowed_origins` setting
- Modify: `backend/app/main.py:31-37` — wire setting into CORS middleware

**Step 1: Add `allowed_origins` to config**

In `backend/app/config.py`, add after line 27 (`max_upload_size_mb`):

```python
    # CORS
    allowed_origins: list[str] = ["https://localhost:8889"]
```

**Step 2: Wire into CORS middleware**

In `backend/app/main.py`, replace lines 31-37:

```python
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
```

Add import at top of `main.py`:

```python
from app.config import settings
```

**Step 3: Verify**

Run: `docker compose up --build -d && sleep 5 && docker compose logs backend --tail 20`
Expected: Backend starts, no import errors.

---

### Task 2: Path Traversal — Editor Images & Attachments

**Files:**
- Modify: `backend/app/api/routes/tickets.py:60-87` — validate resolved path in `serve_editor_image`
- Modify: `backend/app/api/routes/tickets.py:100-111` — validate resolved path in `download_attachment`
- Modify: `backend/app/services/attachment_service.py:60-66` — validate storage path in `upload_file`

**Step 1: Fix `serve_editor_image`**

In `backend/app/api/routes/tickets.py`, replace lines 81-87:

```python
    file_path = os.path.join(EDITOR_IMAGES_DIR, filename)
    # Prevent path traversal
    if not os.path.realpath(file_path).startswith(os.path.realpath(EDITOR_IMAGES_DIR)):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid filename.",
        )
    if not os.path.isfile(file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Image not found.",
        )
    return FileResponse(file_path)
```

**Step 2: Fix `download_attachment`**

In `backend/app/api/routes/tickets.py`, replace lines 105-111:

```python
    """Download an attachment file by attachment ID."""
    attachment = await attachment_service.get_attachment(db, attachment_id)
    # Prevent path traversal via stored file_path
    if not os.path.realpath(attachment.file_path).startswith(os.path.realpath(settings.upload_dir)):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file path.",
        )
    return FileResponse(
        path=attachment.file_path,
        filename=attachment.original_filename,
        media_type=attachment.content_type,
    )
```

**Step 3: Fix upload path validation**

In `backend/app/services/attachment_service.py`, after line 66 (`file_path = os.path.join(...)`), add:

```python
    # Prevent path traversal via crafted original_filename
    if not os.path.realpath(file_path).startswith(os.path.realpath(settings.upload_dir)):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid filename",
        )
```

**Step 4: Verify**

Run: `docker compose up --build -d && sleep 5 && docker compose ps`
Expected: All containers running.

---

### Task 3: Rate Limiting — Extend to JWT

**Files:**
- Modify: `backend/app/api/middleware.py` — add JWT user-based rate limiting

**Step 1: Replace entire middleware**

Replace `backend/app/api/middleware.py` with:

```python
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
```

**Step 2: Verify**

Run: `docker compose up --build -d && sleep 5 && docker compose ps`
Expected: All containers running.

---

### Task 4: Attachment Security — Deletion Guard & Content-Type Sniffing

**Files:**
- Modify: `backend/pyproject.toml:5-19` — add `python-magic` dependency
- Modify: `backend/app/services/attachment_service.py` — add ownership check + magic sniffing

**Step 1: Add `python-magic` to dependencies**

In `backend/pyproject.toml`, add to the `dependencies` list after `"aiofiles>=24.0"`:

```
    "python-magic>=0.4.27",
```

**Step 2: Add deletion ownership guard**

In `backend/app/services/attachment_service.py`, add import at top:

```python
from app.models.base import ActorType, UserRole
```

(Change the existing `from app.models.base import ActorType` line to also import `UserRole`.)

In the `delete_attachment` function, after line 131 (`attachment = await get_attachment(...)`), add:

```python
    # Only the uploader or an admin can delete
    if (
        current_user.user.id != attachment.uploaded_by_id
        and current_user.user.role != UserRole.admin
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the uploader or an admin can delete this attachment",
        )
```

**Step 3: Add content-type sniffing on upload**

In `backend/app/services/attachment_service.py`, add import at top:

```python
import magic
```

In the `upload_file` function, after line 53 (`content = await file.read()`), add:

```python
    # Sniff actual content type — don't trust client header
    detected_type = magic.from_buffer(content, mime=True)
    if detected_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Detected file type {detected_type} not allowed",
        )
```

**Step 4: Verify**

Run: `docker compose up --build -d && sleep 5 && docker compose ps`
Expected: All containers running (python-magic installs `libmagic` via the wheel).

---

### Task 5: Security Headers via Nginx

**Files:**
- Modify: `nginx/nginx.conf.template:17-24` — add security headers inside `server` block

**Step 1: Add headers**

In `nginx/nginx.conf.template`, after line 25 (`client_max_body_size 25M;`), add:

```nginx
        # Security headers
        add_header X-Content-Type-Options "nosniff" always;
        add_header X-Frame-Options "DENY" always;
        add_header Referrer-Policy "strict-origin-when-cross-origin" always;
```

**Step 2: Verify**

Run: `docker compose up --build -d && sleep 5 && curl -kI https://localhost:8889/api/v1/health 2>&1 | grep -i "x-content-type\|x-frame\|referrer"`
Expected: All three headers present in response.

---

### Task 6: Cookie SameSite Strict

**Files:**
- Modify: `backend/app/api/routes/auth.py:31-37` — change `samesite` to `"strict"`

**Step 1: Change cookie attribute**

In `backend/app/api/routes/auth.py`, replace line 36:

```python
        samesite="strict",
```

**Step 2: Verify**

Run: `docker compose up --build -d`
Expected: Backend starts cleanly.

---

### Task 7: Documentation & Secrets Warnings

**Files:**
- Modify: `.env.example` — add warning comments
- Modify: `backend/app/main.py` — add startup warning for default JWT secret
- Verify: `.gitignore` — confirm `.env` is excluded

**Step 1: Update `.env.example`**

Replace the full contents of `.env.example`:

```bash
# Port (nginx listens on this)
ASM_PORT=8889

# Database
# WARNING: Change these credentials before deploying
POSTGRES_USER=servicemeow
POSTGRES_PASSWORD=change-me-in-production
POSTGRES_DB=servicemeow
DATABASE_URL=postgresql+asyncpg://servicemeow:change-me-in-production@postgres:5432/servicemeow

# Auth
# WARNING: You MUST change this secret — the default is insecure
JWT_SECRET=change-me-in-production
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=7

# Default Admin (created on first run)
# WARNING: Change the default admin password immediately after first login
DEFAULT_ADMIN_USERNAME=admin
DEFAULT_ADMIN_PASSWORD=change-me-in-production
DEFAULT_ADMIN_EMAIL=admin@servicemeow.local

# CORS (comma-separated origins)
ALLOWED_ORIGINS=["https://localhost:8889"]

# MCP
MCP_PATH=/mcp

# File Storage
UPLOAD_DIR=/app/uploads
MAX_UPLOAD_SIZE_MB=25

# SLA Defaults (minutes)
SLA_CRITICAL_ASSIGN=15
SLA_CRITICAL_RESOLVE=240
SLA_HIGH_ASSIGN=30
SLA_HIGH_RESOLVE=480
SLA_MEDIUM_ASSIGN=120
SLA_MEDIUM_RESOLVE=1440
SLA_LOW_ASSIGN=480
SLA_LOW_RESOLVE=4320
```

**Step 2: Add startup warning in `main.py`**

In `backend/app/main.py`, add import at top:

```python
import logging
```

In the `lifespan` function, add after line 17 (`async with contextlib.AsyncExitStack() as stack:`):

```python
        if settings.jwt_secret == "change-me-in-production":
            logging.warning(
                "JWT_SECRET is set to the default value. "
                "This is insecure — set a strong secret in your .env file."
            )
```

**Step 3: Verify `.gitignore`**

Check that `.gitignore` contains `.env` — it does (line 3). No action needed.

**Step 4: Verify**

Run: `docker compose up --build -d && sleep 5 && docker compose logs backend --tail 10 | grep WARNING`
Expected: Warning about default JWT secret visible in logs.

---

### Task 8: Build, Test, Verify

**Step 1: Rebuild everything**

Run: `docker compose up --build -d`
Expected: All containers build and start.

**Step 2: Run tests**

Run: `docker compose exec backend pip install pytest pytest-asyncio python-magic && docker compose exec backend python -m pytest tests/ -v`
Expected: All 63 tests pass.

**Step 3: Verify security headers**

Run: `curl -kI https://localhost:8889/api/v1/health`
Expected: Response includes `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`.

**Step 4: Verify startup warning**

Run: `docker compose logs backend | grep -i "JWT_SECRET is set to the default"`
Expected: Warning visible.

---

## Files Summary (10 files)

| File | Action |
|------|--------|
| `backend/app/config.py` | Add `allowed_origins` setting |
| `backend/app/main.py` | Wire CORS from config, add startup warning |
| `backend/app/api/middleware.py` | Rewrite: extend rate limiting to JWT |
| `backend/app/api/routes/tickets.py` | Path traversal guards on image serve + attachment download |
| `backend/app/api/routes/auth.py` | Cookie samesite → strict |
| `backend/app/services/attachment_service.py` | Path traversal guard, deletion ownership check, content-type sniffing |
| `backend/pyproject.toml` | Add `python-magic` dependency |
| `nginx/nginx.conf.template` | Add security response headers |
| `.env.example` | Add warning comments + `ALLOWED_ORIGINS` |
| `.gitignore` | Verify (no change needed) |
