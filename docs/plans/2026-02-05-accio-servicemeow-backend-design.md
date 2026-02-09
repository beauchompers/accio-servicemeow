# Accio ServiceMeow Backend Design — Phases 1-3

**Date:** 2026-02-05
**Scope:** Foundation, Ticket System, MCP Server (Phases 1-3)
**Frontend:** Deferred to Phase 4

---

## Decisions Made

- **Backend phases 1-3 first** — complete backend before touching frontend
- **FastMCP (high-level)** — decorator-based tool registration for the MCP server
- **Integration tests only** — pytest + httpx against a test database
- **Docker-only development** — everything runs in Docker Compose with volume mounts for hot-reload
- **Auto-seed on first run** — backend entrypoint detects empty DB and seeds automatically

---

## 1. Project Structure

```
accio-servicemeow/
├── docker-compose.yml
├── docker-compose.dev.yml          # Dev overrides (volume mounts, hot-reload)
├── .env.example
├── .gitignore
├── nginx/
│   ├── Dockerfile
│   ├── nginx.conf
│   └── entrypoint.sh               # Auto-generates self-signed TLS certs
├── backend/
│   ├── Dockerfile
│   ├── entrypoint.sh                # Migrations -> seed check -> uvicorn
│   ├── pyproject.toml               # uv-managed deps
│   ├── alembic.ini
│   ├── alembic/
│   ├── app/
│   │   ├── main.py                  # App factory, mount MCP, include routers
│   │   ├── config.py                # Pydantic Settings from env
│   │   ├── database.py              # Async engine, sessionmaker, get_db
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── base.py              # Base class with UUID id, timestamps
│   │   │   ├── user.py
│   │   │   ├── group.py             # Groups + group_memberships
│   │   │   ├── ticket.py
│   │   │   ├── ticket_note.py
│   │   │   ├── attachment.py
│   │   │   ├── audit_log.py
│   │   │   ├── api_key.py
│   │   │   ├── webhook.py
│   │   │   └── sla_config.py
│   │   ├── schemas/
│   │   │   ├── __init__.py
│   │   │   ├── auth.py
│   │   │   ├── user.py
│   │   │   ├── group.py
│   │   │   ├── ticket.py
│   │   │   ├── ticket_note.py
│   │   │   ├── attachment.py
│   │   │   ├── audit_log.py
│   │   │   ├── api_key.py
│   │   │   ├── webhook.py
│   │   │   ├── dashboard.py
│   │   │   └── common.py            # PaginatedResponse, etc.
│   │   ├── api/
│   │   │   ├── dependencies.py      # get_current_user, require_role
│   │   │   ├── middleware.py        # CORS, rate limiting
│   │   │   └── routes/
│   │   │       ├── __init__.py
│   │   │       ├── auth.py
│   │   │       ├── users.py
│   │   │       ├── groups.py
│   │   │       ├── tickets.py
│   │   │       ├── dashboard.py
│   │   │       ├── api_keys.py
│   │   │       └── webhooks.py
│   │   ├── mcp/
│   │   │   ├── server.py            # FastMCP instance + mount logic
│   │   │   └── tools/
│   │   │       ├── __init__.py
│   │   │       ├── tickets.py       # Ticket management tools
│   │   │       └── info.py          # Dashboard, SLA, groups, users tools
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── auth_service.py
│   │   │   ├── user_service.py
│   │   │   ├── group_service.py
│   │   │   ├── ticket_service.py
│   │   │   ├── note_service.py
│   │   │   ├── attachment_service.py
│   │   │   ├── audit_service.py
│   │   │   ├── sla_service.py
│   │   │   └── webhook_service.py
│   │   ├── events/
│   │   │   ├── __init__.py
│   │   │   └── dispatcher.py        # Webhook dispatch
│   │   └── tasks/
│   │       ├── __init__.py
│   │       └── sla_checker.py       # Periodic SLA breach detection
│   ├── seed.py
│   └── tests/
│       ├── conftest.py              # Test DB, async client fixture
│       ├── test_auth.py
│       ├── test_users.py
│       ├── test_groups.py
│       ├── test_tickets.py
│       └── test_mcp.py
└── frontend/                        # Phase 4 — empty for now
```

---

## 2. Docker Compose

### Services

1. **postgres** — PostgreSQL 16, persistent volume, health check via `pg_isready`
2. **backend** — FastAPI on uvicorn, depends on postgres health check
3. **nginx** — Reverse proxy with TLS termination, depends on backend

### Development Override (`docker-compose.dev.yml`)

- Backend: mount `./backend` as volume, run with `--reload`
- Nginx: mount `./nginx/nginx.conf` for config changes without rebuild
- Expose Postgres port 5432 to host for DB inspection tools

### Backend Entrypoint (`entrypoint.sh`)

```bash
#!/bin/bash
set -e

# Wait for Postgres
until pg_isready -h postgres -p 5432 -U "$POSTGRES_USER"; do
  sleep 1
done

# Run Alembic migrations
alembic upgrade head

# Seed if empty (checks for admin user)
python seed.py --if-empty

# Start uvicorn
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 "$@"
```

### Nginx Entrypoint (`entrypoint.sh`)

Checks for `/etc/nginx/certs/server.crt`. If missing, generates self-signed cert with `openssl`. Then starts nginx.

---

## 3. Data Model

### Base Mixin

All models inherit from a `Base` class providing:
- `id: UUID` — primary key, server-default `gen_random_uuid()`
- `created_at: datetime` — server-default `now()`
- `updated_at: datetime` — server-default `now()`, onupdate `now()`

### Enums (Python StrEnum, mapped to Postgres native enums)

- `UserRole`: `admin`, `manager`, `agent`
- `TicketStatus`: `open`, `under_investigation`, `paused`, `resolved`
- `TicketPriority`: `critical`, `high`, `medium`, `low`
- `ActorType`: `user`, `api_key`, `system`

### Models

**users** — `username` (unique), `email` (unique), `full_name`, `hashed_password`, `role` (UserRole), `is_active`

**groups** — `name` (unique), `description`

**group_memberships** — `user_id` (FK), `group_id` (FK), `is_lead`, `joined_at`. Composite unique constraint on (user_id, group_id).

**tickets** — `ticket_number` (unique, auto-generated `ASM-XXXX` via DB sequence), `title`, `description` (HTML), `status` (TicketStatus), `priority` (TicketPriority), `assigned_group_id` (FK, nullable), `assigned_user_id` (FK, nullable), `created_by_id` (FK), `resolved_at`, `first_assigned_at`, `sla_target_minutes`, `paused_at`, `total_paused_seconds` (default 0)

**ticket_notes** — `ticket_id` (FK), `author_id` (FK), `content` (HTML), `is_internal`

**attachments** — `ticket_id` (FK), `note_id` (FK, nullable), `filename` (UUID-based), `original_filename`, `file_path`, `file_size`, `content_type`, `uploaded_by_id` (FK)

**audit_log** — `ticket_id` (FK), `actor_id` (FK, nullable), `actor_type` (ActorType), `action`, `field_changed`, `old_value`, `new_value`, `metadata` (JSONB)

**api_keys** — `name`, `key_hash` (bcrypt), `key_prefix` (first 8 chars), `user_id` (FK), `is_active`, `last_used_at`, `expires_at`

**webhooks** — `name`, `url`, `secret`, `events` (ARRAY of str), `is_active`, `created_by_id` (FK), `last_triggered_at`

**sla_config** — `priority` (TicketPriority, unique), `target_assign_minutes`, `target_resolve_minutes`

### Indexes

- `tickets.status`, `tickets.priority`, `tickets.assigned_group_id`, `tickets.assigned_user_id`, `tickets.created_at`
- `audit_log.ticket_id`, `audit_log.created_at`
- GIN index on `tickets` for full-text search (`to_tsvector('english', title || ' ' || description)`)

---

## 4. Authentication & Authorization

### JWT (Web UI)

- `POST /api/v1/auth/login` — validates credentials, returns `{ access_token }` in body + `refresh_token` as HTTP-only secure cookie
- Access token: 15min expiry, HS256 signed with `JWT_SECRET`
- Refresh token: 7 days, HTTP-only cookie
- `POST /api/v1/auth/refresh` — reads cookie, issues new access token
- `POST /api/v1/auth/logout` — clears refresh cookie
- No token blocklist for v1

### API Keys (MCP / Integrations)

- Format: `asm_` + 40 hex chars
- Stored as bcrypt hash; `key_prefix` stores first 8 chars for display
- Sent via `api_key` HTTP header
- Rate limiting: 100 req/min per key, in-memory sliding window

### Unified Auth Dependency

```python
async def get_current_user(
    authorization: str | None = Header(None),
    api_key: str | None = Header(None),
    db: AsyncSession = Depends(get_db),
) -> CurrentUser:
    # Try JWT first, then API key
    # Returns CurrentUser(user, auth_type, api_key_id)
```

### Role-Based Access

- `admin`: full access
- `manager`: CRUD tickets/groups, view all users, manage own group
- `agent`: view/update tickets assigned to self or own group, create tickets, add notes

---

## 5. REST API

Base path: `/api/v1`

### Auth
- `POST /auth/login` — JWT login
- `POST /auth/refresh` — refresh access token
- `POST /auth/logout` — clear refresh cookie

### Users
- `POST /users` — create (admin only)
- `GET /users` — list
- `GET /users/{id}` — detail
- `PATCH /users/{id}` — update

### Groups
- `POST /groups` — create
- `GET /groups` — list
- `GET /groups/{id}` — detail with members
- `POST /groups/{id}/members` — add member
- `DELETE /groups/{id}/members/{user_id}` — remove member

### Tickets
- `POST /tickets` — create
- `GET /tickets` — list (paginated, filterable by status, priority, group, user, search, sla_breached; sortable)
- `GET /tickets/{id}` — detail with notes, attachments, audit log
- `PATCH /tickets/{id}` — update
- `DELETE /tickets/{id}` — soft delete
- `POST /tickets/{id}/notes` — add note
- `GET /tickets/{id}/notes` — list notes
- `PATCH /tickets/{id}/notes/{note_id}` — edit note
- `POST /tickets/{id}/attachments` — upload file(s)
- `GET /tickets/{id}/attachments` — list attachments
- `GET /attachments/{id}/download` — download file
- `DELETE /attachments/{id}` — remove attachment
- `GET /tickets/{id}/audit-log` — audit trail

### Dashboard
- `GET /dashboard/summary` — counts by status, group, priority
- `GET /dashboard/sla` — MTTA/MTTR by group/priority
- `GET /dashboard/activity` — recent activity feed

### API Keys
- `POST /api-keys` — create (returns plain key once)
- `GET /api-keys` — list (prefix + metadata)
- `DELETE /api-keys/{id}` — revoke

### Webhooks
- `POST /webhooks` — register
- `GET /webhooks` — list
- `PATCH /webhooks/{id}` — update
- `DELETE /webhooks/{id}` — remove

### Pagination Response Format
```json
{
  "items": [...],
  "total": 42,
  "page": 1,
  "page_size": 25,
  "pages": 2
}
```

---

## 6. Services Layer

Business logic separated from routes. Each service receives `AsyncSession` and `CurrentUser`.

- **auth_service** — JWT encode/decode, API key create/verify, password hashing
- **user_service** — CRUD users, password management
- **group_service** — CRUD groups, membership management
- **ticket_service** — Create (auto ticket number from sequence, set SLA target from config), update (status transitions, pause/unpause tracking, `first_assigned_at`), assign, resolve, list with filters/search/pagination, soft delete
- **note_service** — Add/edit notes, sanitize HTML with `nh3`
- **attachment_service** — Stream to disk at `/app/uploads/{ticket_id}/{uuid}_{filename}`, validate type/size, serve downloads
- **audit_service** — Append-only log, called by other services on mutations
- **sla_service** — Calculate elapsed time (minus pauses), breach status, MTTA/MTTR aggregates
- **webhook_service** — CRUD subscriptions

### Key Patterns

- All ticket mutations: audit log entry + webhook dispatch (background task)
- Full-text search: PostgreSQL `to_tsvector`/`to_tsquery` on title + description
- Ticket numbers: DB sequence formatted as `ASM-{seq:04d}`
- HTML sanitization: `nh3` on write for all rich text fields (descriptions, notes)

---

## 7. MCP Server

### Setup

- `FastMCP` instance created in `app/mcp/server.py`
- Mounted at `/mcp` via `app.mount("/mcp", mcp.streamable_http_app())`
- API key auth enforced via middleware on the MCP sub-app

### Ticket Management Tools

| Tool | Parameters | Returns |
|------|-----------|---------|
| `create_ticket` | title, description, priority, assigned_group_id?, assigned_user_id? | Created ticket + summary |
| `get_ticket` | ticket_id_or_number (UUID or ASM-XXXX) | Full ticket with notes, attachments, SLA status |
| `update_ticket` | ticket_id, title?, description?, status?, priority? | Updated ticket |
| `assign_ticket` | ticket_id, group_id?, user_id? | Updated ticket |
| `list_tickets` | status?, priority?, group_id?, user_id?, search?, sla_breached?, page?, page_size? | Paginated ticket list |
| `add_ticket_note` | ticket_id, content, is_internal? | Created note + ticket |
| `resolve_ticket` | ticket_id, resolution_note? | Resolved ticket |
| `bulk_update_tickets` | ticket_ids[], status?, group_id?, user_id? | Updated tickets |

### Information Tools

| Tool | Parameters | Returns |
|------|-----------|---------|
| `get_dashboard_summary` | (none) | Counts by status/priority/group |
| `get_sla_metrics` | group_id?, priority?, date_from?, date_to? | MTTA/MTTR aggregates |
| `list_groups` | (none) | Groups with member counts |
| `list_users` | group_id? | Users, optionally filtered |
| `get_ticket_audit_log` | ticket_id | Full audit trail |

### Response Pattern

All tools return structured JSON with:
- `summary`: human-readable natural language description
- `data`: full structured data
- Mutation tools include updated ticket state
- Errors include actionable guidance for LLM self-correction

### MCP Resources

- `servicemeow://tickets/{id}` — ticket detail
- `servicemeow://dashboard` — dashboard summary
- `servicemeow://groups` — group listing

---

## 8. SLA Tracking

### Configuration

`sla_config` table seeded with defaults from the spec:

| Priority | Assign Target | Resolve Target |
|----------|---------------|----------------|
| Critical | 15 min | 4 hours |
| High | 30 min | 8 hours |
| Medium | 2 hours | 24 hours |
| Low | 8 hours | 72 hours |

### Tracking

- On ticket creation: copy `sla_target_minutes` from config based on priority
- On first assignment: record `first_assigned_at`
- On status -> `paused`: record `paused_at`
- On status change away from `paused`: add delta to `total_paused_seconds`, clear `paused_at`
- Elapsed SLA time = `now() - created_at - total_paused_seconds`

### Breach Detection

Background task (asyncio, runs every 60s):
- Query open tickets where elapsed > `sla_target_minutes`
- Flag as breached (queryable via API/MCP filter)
- Emit `ticket.sla_breached` webhook event (once per breach)
- Tickets at >80% of target flagged as "at risk"

---

## 9. Webhook System

### Events

`ticket.created`, `ticket.updated`, `ticket.status_changed`, `ticket.assigned`, `ticket.note_added`, `ticket.resolved`, `ticket.sla_breached`

### Dispatch (`events/dispatcher.py`)

- Receives event type + payload from services
- Queries active webhook subscriptions matching the event
- Fires HTTP POST for each match as a FastAPI background task
- Payload: `{ event, timestamp, ticket, actor }`
- HMAC-SHA256 signature in `X-ServiceMeow-Signature` header
- 3 retries with exponential backoff (1s, 5s, 30s) via `httpx.AsyncClient`

---

## 10. Testing

### Framework

pytest + httpx `AsyncClient` + test PostgreSQL database

### conftest.py

- Create isolated test database
- Run Alembic migrations
- Provide `async_client` fixture (httpx `AsyncClient` pointing at the test app)
- Transaction rollback between tests for isolation

### Test Files

- `test_auth.py` — login, refresh, logout, API key auth, invalid credentials
- `test_users.py` — CRUD, role enforcement
- `test_groups.py` — CRUD, membership management
- `test_tickets.py` — CRUD, status transitions, assignment, SLA tracking, search, pagination, notes, attachments
- `test_mcp.py` — Tool discovery, tool execution, auth enforcement

### Coverage Focus

Happy paths + key error cases: auth failures, validation errors, not found, permission denied.

---

## 11. Seed Data

### Auto-seed Logic

`seed.py --if-empty` checks for existence of admin user. If not found, seeds:

- **Admin user** from env vars (`DEFAULT_ADMIN_USERNAME/PASSWORD/EMAIL`)
- **4 groups**: IT Operations, Cybersecurity, Server Infrastructure, Desktop Support
- **8-10 users** with realistic names, distributed across groups with varied roles
- **SLA config** with default targets per priority
- **1 API key** named "Claude MCP Agent" — plain key printed to stdout on creation

No tickets seeded — created during demos via MCP or web UI.

---

## 12. Dependencies (`pyproject.toml`)

```toml
[project]
name = "accio-servicemeow"
version = "0.1.0"
requires-python = ">=3.12"

dependencies = [
    "fastapi>=0.115",
    "uvicorn[standard]>=0.34",
    "sqlalchemy[asyncio]>=2.0",
    "asyncpg>=0.30",
    "alembic>=1.14",
    "pydantic-settings>=2.7",
    "pyjwt>=2.10",
    "bcrypt>=4.2",
    "python-multipart>=0.0.18",
    "nh3>=0.2",
    "httpx>=0.28",
    "mcp>=1.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-asyncio>=0.24",
    "httpx>=0.28",
]
```
