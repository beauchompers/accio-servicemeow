# Accio ServiceMeow

Case management platform with embedded MCP server for agentic AI workflows.

## Tech Stack

- **Backend:** Python 3.12 / FastAPI / SQLAlchemy 2.x (async) / asyncpg / Alembic
- **Database:** PostgreSQL 16
- **MCP:** FastMCP with Streamable HTTP, mounted at `/mcp`
- **Frontend:** React 18 + Tailwind CSS 3 + Vite
- **Auth:** JWT (web UI) + API Keys (MCP/integrations)
- **Deployment:** Docker Compose with Nginx reverse proxy + self-signed TLS

## Development

Everything runs in a single Docker Compose file:

```bash
./setup.sh
```

This generates secrets, copies config files, and starts all containers. For manual setup:

```bash
cp .env.example .env
docker compose up --build -d
```

Backend source is mounted with `--reload` for hot-reloading. Frontend runs via Vite dev server.
Default port is `8889` (configurable via `ASM_PORT` in `.env`).

To use custom TLS certs, place `cert.pem` and `key.pem` in `nginx/certs/`.
If none are provided, a self-signed certificate is generated on first start.

## Running Tests

```bash
docker compose exec backend pytest tests/ -v
```

## Project Structure

- `backend/app/` — FastAPI application
  - `models/` — SQLAlchemy models
  - `schemas/` — Pydantic request/response schemas
  - `services/` — Business logic layer
  - `api/routes/` — REST API route handlers
  - `mcp/` — MCP server and tool implementations
- `backend/app/tasks/` — Background tasks (SLA checker)
- `nginx/` — Reverse proxy with auto TLS

## Key Patterns

- Services receive `AsyncSession` + `CurrentUser`, routes are thin wrappers
- All ticket mutations log to audit trail
- HTML content sanitized with `nh3` on write
- Ticket numbers: `ASM-{sequence:04d}` via PostgreSQL sequence
- MCP tools return `{"summary": "...", "data": {...}}` for LLM readability
