# Accio ServiceMeow

A case/ticket management platform with an embedded [MCP](https://modelcontextprotocol.io/) server, enabling AI assistants like Claude to create, update, and triage support tickets through natural language.

<p align="center">
  <img src="docs/screenshots/Screenshot - Dashboard.png" width="49%" alt="Dashboard" />
  <img src="docs/screenshots/Screenshot - Ticket.png" width="49%" alt="Ticket Detail" />
</p>

## Features

- **MCP Integration** — 16 tools exposed via Streamable HTTP for agentic AI workflows
- **Rich Text Editing** — TipTap editor with code blocks, links, and images
- **SLA Tracking** — configurable targets per priority with MTTA/MTTR metrics
- **Audit Trail** — every ticket mutation logged with actor, field, old/new values
- **Full-Text Search** — PostgreSQL-powered search across tickets and notes
- **Bulk Operations** — update status, assignment, or priority across multiple tickets
- **Role-Based Access** — admin and agent roles with JWT + API key authentication
- **Self-Signed TLS** — auto-generated certificates, with support for custom certs

## Quick Start

**Prerequisites:** [Docker](https://docs.docker.com/get-docker/) and [Docker Compose](https://docs.docker.com/compose/install/)

```bash
./setup.sh
```

This will:
- Create `.env` from `.env.example` (if it doesn't exist)
- Generate random secrets for `JWT_SECRET`, `POSTGRES_PASSWORD`, and `DEFAULT_ADMIN_PASSWORD`
- Copy `seed.json.example` to `seed.json` for sample data
- Build and start all containers
- Wait for the health check and print your login credentials

Once running, open the URL shown in the output and accept the self-signed certificate warning.

<details>
<summary>Manual setup</summary>

```bash
cp .env.example .env
# Edit .env to set your own secrets
docker compose up --build -d
```

Default credentials: `admin` / `change-me-in-production` (from `.env.example`)

</details>

## Architecture

```
Browser ──► nginx (TLS) ──┬──► FastAPI backend ──► PostgreSQL
                          │       ├─ REST API (/api/v1/)
                          │       └─ MCP server (/mcp/)
                          └──► Static frontend (React SPA)
```

| Layer | Tech |
|-------|------|
| Frontend | React 18, TypeScript, Vite, Tailwind CSS, TanStack Query, TipTap |
| Backend | FastAPI, SQLAlchemy 2 (async), Alembic, Pydantic v2 |
| Database | PostgreSQL 16 |
| Proxy | nginx with auto-generated or custom TLS |
| Auth | JWT (Bearer) + API Key (`api_key` header) |

## Connecting Claude Desktop

Claude Desktop only supports stdio-based MCP servers, so you need [`mcp-proxy`](https://github.com/sparfenyuk/mcp-proxy) to bridge to the HTTP endpoint.

1. **Install mcp-proxy:**
   ```bash
   pipx install mcp-proxy
   ```

2. **Create an API key** in the ServiceMeow UI under **Admin > API Keys**.

3. **Add to `claude_desktop_config.json`:**
   ```json
   {
     "mcpServers": {
       "servicemeow": {
         "command": "mcp-proxy",
         "args": [
           "--transport", "streamablehttp",
           "https://localhost:8889/mcp/"
         ],
         "env": {
           "API_KEY": "YOUR_API_KEY"
         }
       }
     }
   }
   ```

4. **Restart Claude Desktop** to pick up the new server.

> **Note:** You may need to set `NODE_TLS_REJECT_UNAUTHORIZED=0` in the `env` block for self-signed certificates.

## Connecting Claude Code

Claude Code supports Streamable HTTP natively — no proxy needed.

**Option A — CLI:**

```bash
claude mcp add servicemeow \
  --transport url \
  --url https://localhost:8889/mcp/ \
  --header "api_key: YOUR_API_KEY"
```

**Option B — `.mcp.json`:**

Add to `.mcp.json` in your project root:

```json
{
  "mcpServers": {
    "servicemeow": {
      "type": "url",
      "url": "https://localhost:8889/mcp/",
      "headers": {
        "api_key": "YOUR_API_KEY"
      }
    }
  }
}
```

> **Note:** You may need to set `NODE_TLS_REJECT_UNAUTHORIZED=0` for self-signed certificates.

## Available MCP Tools

| Tool | Description |
|------|-------------|
| `create_ticket` | Create a new support ticket with title, description, priority, and group |
| `get_ticket` | Get ticket details by UUID or ticket number (ASM-XXXX) |
| `update_ticket` | Update ticket title, description, status, or priority |
| `assign_ticket` | Assign or reassign a ticket to a group and/or user |
| `list_tickets` | Search and filter tickets with pagination |
| `add_ticket_note` | Add a note to a ticket (supports internal-only notes) |
| `get_ticket_notes` | Get all notes for a ticket by UUID or ticket number |
| `resolve_ticket` | Resolve a ticket, optionally adding a resolution note |
| `bulk_update_tickets` | Batch-update status or assignment across multiple tickets |
| `get_dashboard_summary` | Get ticket counts by status, priority, and group |
| `get_sla_metrics` | Get MTTA/MTTR metrics with optional group/priority/date filters |
| `list_groups` | List all support groups with member counts |
| `list_users` | List users, optionally filtered by group |
| `get_ticket_audit_log` | Get the full audit trail for a ticket |
| `get_my_tickets` | List tickets assigned to the authenticated user |
| `get_system_info` | Get available statuses, priorities, roles, and system config |

## Example MCP Conversations

**Create a ticket:**
> "Create a high priority ticket titled 'Login page timeout' assigned to the Platform team describing that users are seeing 30s load times on the login page."

**Triage incoming tickets:**
> "Show me all open tickets. For any critical tickets that aren't assigned to a user, assign them to admin and add a note saying we're investigating."

**Search and investigate:**
> "Search for tickets mentioning 'timeout'. Show me the notes and audit log for the most recent one."

**Resolve a ticket:**
> "Resolve ASM-0001 with a note explaining that the root cause was a missing database index and it's been deployed to production."

## Environment Variables

See `.env.example` for all available configuration.

| Variable | Default | Description |
|----------|---------|-------------|
| `ASM_PORT` | `8889` | Port nginx listens on |
| `POSTGRES_USER` | `servicemeow` | Database user |
| `POSTGRES_PASSWORD` | `change-me-in-production` | Database password |
| `POSTGRES_DB` | `servicemeow` | Database name |
| `JWT_SECRET` | `change-me-in-production` | JWT signing key |
| `DEFAULT_ADMIN_USERNAME` | `admin` | Initial admin username |
| `DEFAULT_ADMIN_PASSWORD` | `change-me-in-production` | Initial admin password |
| `DEFAULT_ADMIN_EMAIL` | `admin@servicemeow.local` | Initial admin email |
| `ALLOWED_ORIGINS` | `["https://localhost:8889"]` | CORS allowed origins |
| `MCP_PATH` | `/mcp` | MCP endpoint mount path |
| `MAX_UPLOAD_SIZE_MB` | `25` | Max file upload size in MB |

## Custom TLS Certificates

Self-signed certificates are generated automatically on first start. To use your own:

1. Place `cert.pem` and `key.pem` in `nginx/certs/`
2. Restart the stack: `docker compose restart nginx`

## Project Structure

```
accio-servicemeow/
├── backend/
│   ├── app/
│   │   ├── api/routes/       # FastAPI route handlers
│   │   ├── models/           # SQLAlchemy models
│   │   ├── schemas/          # Pydantic schemas
│   │   ├── services/         # Business logic layer
│   │   ├── mcp/              # MCP server and tool definitions
│   │   └── main.py           # App entrypoint
│   ├── alembic/              # Database migrations
│   ├── tests/                # Pytest test suite
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── api/              # API client with JWT refresh
│   │   ├── components/       # Shared UI components
│   │   ├── context/          # Auth and Theme providers
│   │   ├── hooks/            # TanStack Query hooks
│   │   ├── pages/            # Route page components
│   │   └── utils/            # Formatting and SLA utilities
│   ├── index.html
│   └── package.json
├── nginx/
│   ├── nginx.conf.template   # Nginx config (envsubst template)
│   ├── Dockerfile
│   └── entrypoint.sh         # TLS cert generation
├── docker-compose.yml
├── seed.json.example          # Sample data for seeding
└── .env.example
```

## Running Tests

```bash
docker compose exec backend pytest tests/ -v
```

## Built With

- [FastAPI](https://fastapi.tiangolo.com/) — async Python web framework
- [SQLAlchemy 2](https://www.sqlalchemy.org/) — async ORM with asyncpg
- [FastMCP](https://github.com/jlowin/fastmcp) — MCP server framework
- [React](https://react.dev/) + [Vite](https://vite.dev/) — frontend toolchain
- [Tailwind CSS](https://tailwindcss.com/) — utility-first CSS
- [TipTap](https://tiptap.dev/) — rich text editor
- [TanStack Query](https://tanstack.com/query) — async data fetching
- [PostgreSQL](https://www.postgresql.org/) — relational database
- [nginx](https://nginx.org/) — reverse proxy with TLS termination
