# Security Hardening Design

**Date:** 2026-02-08
**Scope:** Internal network deployment, flat access model (all authenticated users equal), document-only approach for default credentials.

---

## Context

Pre-push security review of the full stack: FastAPI backend, React frontend, MCP server, nginx reverse proxy, and Docker deployment. The app runs on an internal/private network with trusted users.

## Findings & Fixes

### 1. CORS: Restrict Origins (Critical)

**Problem:** `main.py` sets `allow_origins=["*"]` with `allow_credentials=True`. This lets any website make authenticated cross-origin requests using the user's refresh cookie.

**Fix:**
- Add `allowed_origins: list[str]` setting to `config.py` (default: `["https://localhost:8889"]`)
- Wire into `CORSMiddleware` in `main.py`
- Document in `.env.example`

**Files:** `backend/app/config.py`, `backend/app/main.py`, `.env.example`

### 2. Path Traversal: Validate Resolved Paths (Critical)

**Problem:** `serve_editor_image` in `tickets.py` passes user-supplied filename directly to `os.path.join` + `FileResponse`. A `../../.env` filename could serve arbitrary files.

**Fix:**
- After constructing file path, `os.path.realpath()` and verify it starts with the expected directory
- Apply same pattern to attachment download path in `attachment_service.py` (defense in depth)

**Files:** `backend/app/api/routes/tickets.py`, `backend/app/services/attachment_service.py`

### 3. Rate Limiting: Extend to JWT (Medium)

**Problem:** Rate limiter in `middleware.py` only applies to `api_key` header requests. JWT-authenticated requests (entire web UI) are unthrottled.

**Fix:**
- Extend middleware to also key on JWT `sub` claim from `Authorization: Bearer` header
- Decode claim without full validation (route handler validates); if decode fails, pass through unrated
- Same 100 req/60s limit for both auth methods

**Files:** `backend/app/api/middleware.py`

### 4a. Attachment Deletion Guard (Medium)

**Problem:** `delete_attachment` has no ownership check. Any authenticated user can delete any attachment.

**Fix:**
- Check `current_user.user.id == attachment.uploaded_by_id` or `current_user.user.role == UserRole.admin`
- Raise 403 Forbidden otherwise

**Files:** `backend/app/services/attachment_service.py`

### 4b. Content-Type Sniffing (Medium)

**Problem:** Upload whitelist validates client-supplied `content_type`, which is trivially spoofable.

**Fix:**
- Add `python-magic` dependency
- After reading file content, sniff actual MIME type and validate against whitelist
- Reject if sniffed type doesn't match whitelist

**Files:** `backend/app/services/attachment_service.py`, `pyproject.toml`

### 5a. Security Response Headers (Low)

**Problem:** No security headers on any response.

**Fix:** Add to nginx config:
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `Referrer-Policy: strict-origin-when-cross-origin`

**Files:** `nginx/nginx.conf.template`

### 5b. Cookie SameSite Strict (Low)

**Problem:** Refresh token cookie uses `samesite=lax`, allowing top-level navigations from external sites to send the cookie.

**Fix:** Change to `samesite="strict"`. Frontend and API share the same origin behind nginx, so no UX impact.

**Files:** `backend/app/api/routes/auth.py`

### 6a. `.env.example` Warnings (Low)

**Problem:** Default secrets not called out prominently.

**Fix:** Add warning comments above `ASM_JWT_SECRET`, `ASM_DEFAULT_ADMIN_PASSWORD`, and `ASM_POSTGRES_PASSWORD`.

**Files:** `.env.example`

### 6b. Startup Warning for Default JWT Secret (Low)

**Problem:** Easy to deploy with the default `"change-me-in-production"` JWT secret.

**Fix:** In `main.py` lifespan, log `WARNING` if `settings.jwt_secret` equals the default. Non-blocking.

**Files:** `backend/app/main.py`

### 6c. `.gitignore` Check (Low)

**Problem:** `.env` with real secrets could be committed.

**Fix:** Verify `.env` is in `.gitignore`.

**Files:** `.gitignore`

---

## Files Summary (11 files)

| File | Changes |
|------|---------|
| `backend/app/config.py` | Add `allowed_origins` setting |
| `backend/app/main.py` | Wire CORS origins from config, add startup warning |
| `backend/app/api/middleware.py` | Extend rate limiter to JWT |
| `backend/app/api/routes/tickets.py` | Path traversal guard on editor images |
| `backend/app/api/routes/auth.py` | Cookie samesite strict |
| `backend/app/services/attachment_service.py` | Path traversal guard, deletion ownership check, content-type sniffing |
| `pyproject.toml` | Add `python-magic` dependency |
| `nginx/nginx.conf.template` | Security response headers |
| `.env.example` | Warnings on secrets |
| `.gitignore` | Ensure `.env` excluded |

## Out of Scope

- Role-based / group-based ticket access restrictions (deferred)
- Enforced secret rotation or first-run password change
- Distributed rate limiting (Redis-backed)
- CSP headers (would require frontend asset hash integration)
