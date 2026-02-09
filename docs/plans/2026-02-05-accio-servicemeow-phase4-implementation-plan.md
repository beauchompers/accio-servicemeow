# Accio ServiceMeow Phase 4 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build the React frontend, wire remaining backend gaps (webhooks, SLA config CRUD, MCP error handling), integrate frontend into Docker, and write the project README.

**Architecture:** React 18 + TypeScript SPA served by nginx in production, proxying API/MCP calls to FastAPI backend. TanStack Query v5 for server state with 30s polling. TipTap rich text editor for ticket descriptions and notes. Dark-mode-first design with light mode toggle.

**Tech Stack:** React 18, TypeScript, Vite, Tailwind CSS 3, TanStack Query v5, React Router v6, TipTap (StarterKit + CodeBlockLowlight + Image + Link), Lucide React, date-fns

**Design Reference:** `docs/plans/2026-02-05-accio-servicemeow-phase4-design.md`

---

## Task 1: Backend — SLA Config CRUD Endpoint

**Files:**
- Create: `backend/app/api/routes/sla.py`
- Create: `backend/app/services/sla_config_service.py`
- Create: `backend/app/schemas/sla_config.py`
- Modify: `backend/app/main.py` (add router)

**Context:**
- SLA config model already exists at `backend/app/models/sla_config.py` with fields: `priority` (unique, TicketPriority enum), `target_assign_minutes`, `target_resolve_minutes`
- Admin page needs `GET /api/v1/sla-config` to list all and `PATCH /api/v1/sla-config` to bulk update
- TicketPriority enum: `critical`, `high`, `medium`, `low` (from `backend/app/models/base.py`)
- Auth dependency: `get_current_user` from `backend/app/api/dependencies.py`
- Use `require_role("admin")` pattern from other admin routes
- Service layer uses `db.flush()`, routes call `db.commit()`

**Step 1: Create SLA config schemas**

Create `backend/app/schemas/sla_config.py`:
```python
from pydantic import BaseModel
from app.models.base import TicketPriority


class SlaConfigItem(BaseModel):
    priority: TicketPriority
    target_assign_minutes: int
    target_resolve_minutes: int

    model_config = {"from_attributes": True}


class SlaConfigUpdate(BaseModel):
    configs: list[SlaConfigItem]
```

**Step 2: Create SLA config service**

Create `backend/app/services/sla_config_service.py`:
```python
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.sla_config import SlaConfig
from app.models.base import TicketPriority


async def get_all(db: AsyncSession) -> list[SlaConfig]:
    result = await db.execute(
        select(SlaConfig).order_by(SlaConfig.priority)
    )
    return list(result.scalars().all())


async def bulk_upsert(
    db: AsyncSession, configs: list[dict]
) -> list[SlaConfig]:
    results = []
    for cfg in configs:
        result = await db.execute(
            select(SlaConfig).where(SlaConfig.priority == cfg["priority"])
        )
        existing = result.scalar_one_or_none()
        if existing:
            existing.target_assign_minutes = cfg["target_assign_minutes"]
            existing.target_resolve_minutes = cfg["target_resolve_minutes"]
            results.append(existing)
        else:
            new_config = SlaConfig(**cfg)
            db.add(new_config)
            results.append(new_config)
    await db.flush()
    return results
```

**Step 3: Create SLA config routes**

Create `backend/app/api/routes/sla.py`:
```python
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user, get_db
from app.models.base import UserRole
from app.schemas.sla_config import SlaConfigItem, SlaConfigUpdate
from app.services import sla_config_service

router = APIRouter()


def require_admin(current_user=Depends(get_current_user)):
    if current_user.user.role != UserRole.admin:
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user


@router.get("", response_model=list[SlaConfigItem])
async def get_sla_config(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    configs = await sla_config_service.get_all(db)
    return configs


@router.patch("", response_model=list[SlaConfigItem])
async def update_sla_config(
    body: SlaConfigUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_admin),
):
    configs = await sla_config_service.bulk_upsert(
        db, [c.model_dump() for c in body.configs]
    )
    await db.commit()
    return configs
```

**Step 4: Register SLA config router**

In `backend/app/main.py`, add import and `include_router`:
```python
from app.api.routes import auth, users, groups, tickets, dashboard, api_keys, webhooks, sla
# ...
app.include_router(sla.router, prefix="/api/v1/sla-config", tags=["sla-config"])
```

**Step 5: Commit**
```bash
git add backend/app/schemas/sla_config.py backend/app/services/sla_config_service.py backend/app/api/routes/sla.py backend/app/main.py
git commit -m "feat: add SLA config CRUD endpoint (GET/PATCH /api/v1/sla-config)"
```

---

## Task 2: Backend — Wire Webhook Dispatch

**Files:**
- Modify: `backend/app/services/ticket_service.py`
- Modify: `backend/app/tasks/sla_checker.py`

**Context:**
- `dispatch_event(event_type: str, payload: dict)` is in `backend/app/events/dispatcher.py`
- It creates its own session internally and runs via `asyncio.create_task()` — safe to call from anywhere
- Events needed per design: `ticket.created`, `ticket.updated`, `ticket.status_changed`, `ticket.assigned`, `ticket.resolved`, `ticket.sla_breached`
- `ticket_service.create_ticket()` returns after `db.flush()` — ticket has ID/number at that point
- `ticket_service.update_ticket()` tracks which fields changed — can detect status/assignment changes
- `sla_checker.check_sla_breaches()` runs in infinite 60s loop, use in-memory set to fire breach event once per ticket

**Step 1: Wire dispatch in create_ticket**

In `backend/app/services/ticket_service.py`, add import at top:
```python
from app.events.dispatcher import dispatch_event
```

At the end of `create_ticket()`, after the audit log entry and before `return ticket`, add:
```python
asyncio.create_task(dispatch_event("ticket.created", {
    "ticket_id": str(ticket.id),
    "ticket_number": ticket.ticket_number,
    "title": ticket.title,
    "priority": ticket.priority.value,
    "status": ticket.status.value,
    "created_by_id": str(current_user.user.id),
}))
```

Add `import asyncio` at top of file.

**Step 2: Wire dispatch in update_ticket**

At the end of `update_ticket()`, after existing audit logging, before `return ticket`, add dispatch for each relevant event:

```python
# Always fire ticket.updated
asyncio.create_task(dispatch_event("ticket.updated", {
    "ticket_id": str(ticket.id),
    "ticket_number": ticket.ticket_number,
    "changes": {field: {"old": old, "new": new} for field, old, new in changes},
}))

# Conditional events
for field, old_val, new_val in changes:
    if field == "status":
        asyncio.create_task(dispatch_event("ticket.status_changed", {
            "ticket_id": str(ticket.id),
            "ticket_number": ticket.ticket_number,
            "old_status": old_val,
            "new_status": new_val,
        }))
        if new_val == "resolved":
            asyncio.create_task(dispatch_event("ticket.resolved", {
                "ticket_id": str(ticket.id),
                "ticket_number": ticket.ticket_number,
            }))
    if field in ("assigned_user_id", "assigned_group_id"):
        asyncio.create_task(dispatch_event("ticket.assigned", {
            "ticket_id": str(ticket.id),
            "ticket_number": ticket.ticket_number,
            "field": field,
            "old_value": old_val,
            "new_value": new_val,
        }))
```

Note: The `changes` list is already tracked in `update_ticket` for audit logging — it's a list of `(field_name, old_value, new_value)` tuples.

**Step 3: Wire dispatch in SLA checker**

In `backend/app/tasks/sla_checker.py`, add in-memory set and dispatch:

```python
import asyncio
from app.events.dispatcher import dispatch_event

_breached_ticket_ids: set[str] = set()

async def check_sla_breaches():
    while True:
        try:
            async with async_session() as db:
                # ... existing query for open tickets with SLA targets ...
                for ticket in tickets:
                    if sla_service.is_breached(ticket):
                        ticket_id_str = str(ticket.id)
                        if ticket_id_str not in _breached_ticket_ids:
                            _breached_ticket_ids.add(ticket_id_str)
                            asyncio.create_task(dispatch_event("ticket.sla_breached", {
                                "ticket_id": ticket_id_str,
                                "ticket_number": ticket.ticket_number,
                                "priority": ticket.priority.value,
                            }))
        except Exception:
            logger.exception("SLA check failed")
        await asyncio.sleep(60)
```

Also clear ticket from `_breached_ticket_ids` when a ticket is resolved (handle in update_ticket or ignore — breach is one-time).

**Step 4: Commit**
```bash
git add backend/app/services/ticket_service.py backend/app/tasks/sla_checker.py
git commit -m "feat: wire webhook dispatch into ticket lifecycle and SLA checker"
```

---

## Task 3: Backend — MCP Error Handling

**Files:**
- Modify: `backend/app/mcp/tools/tickets.py`
- Modify: `backend/app/mcp/tools/info.py`

**Context:**
- Each MCP tool function returns `{"summary": str, "data": dict}` on success
- Need to wrap each tool body in try/except to return structured error responses instead of crashing
- Errors to catch: `ValueError` (auth failures, validation), `HTTPException` (from service layer), `Exception` (unexpected)
- There are 8 tools in tickets.py and 5 tools in info.py — 13 total

**Step 1: Add error handling to all ticket tools**

Wrap each tool function body in:
```python
@mcp.tool()
async def tool_name(...) -> dict:
    """docstring"""
    try:
        # ... existing tool logic ...
    except ValueError as e:
        return {"summary": f"Error: {e}", "data": None}
    except Exception as e:
        return {"summary": f"Unexpected error: {e}", "data": None}
```

Apply to all 8 tools in `tickets.py`: `create_ticket`, `get_ticket`, `update_ticket`, `assign_ticket`, `list_tickets`, `add_ticket_note`, `resolve_ticket`, `bulk_update_tickets`.

**Step 2: Add error handling to all info tools**

Same pattern for all 5 tools in `info.py`: `get_dashboard_summary`, `get_sla_metrics`, `list_groups`, `list_users`, `get_ticket_audit_log`.

**Step 3: Commit**
```bash
git add backend/app/mcp/tools/tickets.py backend/app/mcp/tools/info.py
git commit -m "feat: add error handling to all MCP tool functions"
```

---

## Task 4: Frontend — Project Scaffolding & Configuration

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/tsconfig.json`
- Create: `frontend/tsconfig.node.json`
- Create: `frontend/vite.config.ts`
- Create: `frontend/tailwind.config.js`
- Create: `frontend/postcss.config.js`
- Create: `frontend/index.html`
- Create: `frontend/src/main.tsx`
- Create: `frontend/src/index.css` (Tailwind directives + CSS custom properties)
- Create: `frontend/src/vite-env.d.ts`
- Create: `frontend/public/favicon.svg`

**Context:**
- React 18 + TypeScript + Vite + Tailwind CSS 3
- TanStack Query v5 + React Router v6 + TipTap + Lucide React + date-fns
- Dev: Vite dev server at 5173 proxying `/api` and `/mcp` to backend
- Design tokens from phase4 design doc section 4

**Step 1: Create package.json**

```json
{
  "name": "accio-servicemeow-frontend",
  "private": true,
  "version": "0.1.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc && vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "react": "^18.3.1",
    "react-dom": "^18.3.1",
    "react-router-dom": "^6.28.0",
    "@tanstack/react-query": "^5.62.0",
    "@tiptap/react": "^2.11.0",
    "@tiptap/starter-kit": "^2.11.0",
    "@tiptap/extension-code-block-lowlight": "^2.11.0",
    "@tiptap/extension-image": "^2.11.0",
    "@tiptap/extension-link": "^2.11.0",
    "@tiptap/extension-placeholder": "^2.11.0",
    "lowlight": "^3.2.0",
    "lucide-react": "^0.468.0",
    "date-fns": "^4.1.0"
  },
  "devDependencies": {
    "@types/react": "^18.3.12",
    "@types/react-dom": "^18.3.1",
    "@vitejs/plugin-react": "^4.3.4",
    "autoprefixer": "^10.4.20",
    "postcss": "^8.4.49",
    "tailwindcss": "^3.4.16",
    "typescript": "^5.7.2",
    "vite": "^6.0.0"
  }
}
```

**Step 2: Create TypeScript configs**

`frontend/tsconfig.json`:
```json
{
  "compilerOptions": {
    "target": "ES2020",
    "useDefineForClassFields": true,
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "skipLibCheck": true,
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "isolatedModules": true,
    "moduleDetection": "force",
    "noEmit": true,
    "jsx": "react-jsx",
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noFallthroughCasesInSwitch": true,
    "forceConsistentCasingInFileNames": true,
    "baseUrl": ".",
    "paths": {
      "@/*": ["src/*"]
    }
  },
  "include": ["src"],
  "references": [{ "path": "./tsconfig.node.json" }]
}
```

`frontend/tsconfig.node.json`:
```json
{
  "compilerOptions": {
    "target": "ES2022",
    "lib": ["ES2023"],
    "module": "ESNext",
    "skipLibCheck": true,
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "isolatedModules": true,
    "moduleDetection": "force",
    "noEmit": true
  },
  "include": ["vite.config.ts"]
}
```

**Step 3: Create Vite config**

`frontend/vite.config.ts`:
```typescript
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'https://localhost',
        changeOrigin: true,
        secure: false,
      },
      '/mcp': {
        target: 'https://localhost',
        changeOrigin: true,
        secure: false,
      },
    },
  },
})
```

**Step 4: Create Tailwind + PostCSS config**

`frontend/tailwind.config.js`:
```js
/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  darkMode: 'class',
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
      },
      colors: {
        surface: {
          primary: 'var(--bg-primary)',
          secondary: 'var(--bg-secondary)',
          tertiary: 'var(--bg-tertiary)',
        },
        border: {
          DEFAULT: 'var(--border)',
        },
        content: {
          primary: 'var(--text-primary)',
          secondary: 'var(--text-secondary)',
        },
        accent: {
          DEFAULT: 'var(--accent)',
          hover: 'var(--accent-hover)',
        },
      },
    },
  },
  plugins: [],
}
```

`frontend/postcss.config.js`:
```js
export default {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
}
```

**Step 5: Create index.html and entry point**

`frontend/index.html`:
```html
<!DOCTYPE html>
<html lang="en" class="dark">
  <head>
    <meta charset="UTF-8" />
    <link rel="icon" type="image/svg+xml" href="/favicon.svg" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Accio ServiceMeow</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet" />
  </head>
  <body class="bg-surface-primary text-content-primary">
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

`frontend/src/index.css`:
```css
@tailwind base;
@tailwind components;
@tailwind utilities;

:root {
  --bg-primary: #0f1117;
  --bg-secondary: #1a1d27;
  --bg-tertiary: #242838;
  --border: #2e3348;
  --text-primary: #f1f5f9;
  --text-secondary: #94a3b8;
  --accent: #3B82F6;
  --accent-hover: #60a5fa;
}

.light {
  --bg-primary: #ffffff;
  --bg-secondary: #f8fafc;
  --bg-tertiary: #f1f5f9;
  --border: #e2e8f0;
  --text-primary: #0f172a;
  --text-secondary: #64748b;
  --accent: #3B82F6;
  --accent-hover: #2563eb;
}

body {
  margin: 0;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}
```

`frontend/src/main.tsx` (minimal — just renders placeholder):
```tsx
import React from 'react'
import ReactDOM from 'react-dom/client'
import './index.css'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <div className="flex items-center justify-center h-screen">
      <h1 className="text-2xl font-semibold">Accio ServiceMeow</h1>
    </div>
  </React.StrictMode>,
)
```

`frontend/src/vite-env.d.ts`:
```typescript
/// <reference types="vite/client" />
```

`frontend/public/favicon.svg` — simple cat/magic icon SVG.

**Step 6: Install dependencies**
```bash
cd frontend && npm install
```

**Step 7: Verify dev server starts**
```bash
cd frontend && npm run dev -- --host 0.0.0.0 &
# Should see "Local: http://localhost:5173/"
# Kill after verifying
```

**Step 8: Commit**
```bash
git add frontend/
git commit -m "feat: scaffold React frontend with Vite, Tailwind, TypeScript"
```

---

## Task 5: Frontend — TypeScript Types & API Client

**Files:**
- Create: `frontend/src/types/index.ts`
- Create: `frontend/src/api/client.ts`

**Context:**
- Types must match backend Pydantic schemas exactly (see `backend/app/schemas/`)
- API client wraps `fetch` with JWT handling: auto-adds Bearer token, refreshes on 401, redirects on failure
- Access token stored in memory (not localStorage). Refresh token via HTTP-only cookie.
- Backend auth: `POST /api/v1/auth/login` returns `{access_token, refresh_token, token_type}`
- Backend refresh: `POST /api/v1/auth/refresh` with `{refresh_token}`
- All list endpoints return `{items: T[], total: number, page: number, size: number}`

**Step 1: Create TypeScript types**

`frontend/src/types/index.ts` — interfaces matching all backend schemas:

```typescript
// Enums matching backend
export type TicketStatus = 'open' | 'under_investigation' | 'paused' | 'resolved'
export type TicketPriority = 'critical' | 'high' | 'medium' | 'low'
export type UserRole = 'admin' | 'manager' | 'agent'
export type ActorType = 'user' | 'api_key' | 'system'

// User
export interface User {
  id: string
  username: string
  email: string
  full_name: string
  role: UserRole
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface UserCreate {
  username: string
  email: string
  full_name: string
  password: string
  role: UserRole
}

export interface UserUpdate {
  email?: string
  full_name?: string
  role?: UserRole
  is_active?: boolean
}

// Group
export interface GroupMember {
  user_id: string
  username: string
  full_name: string
  is_lead: boolean
  joined_at: string
}

export interface Group {
  id: string
  name: string
  description: string
  member_count: number
  created_at: string
}

export interface GroupDetail extends Group {
  members: GroupMember[]
}

export interface GroupCreate {
  name: string
  description?: string
}

export interface GroupUpdate {
  name?: string
  description?: string
}

export interface GroupMemberAdd {
  user_id: string
  is_lead?: boolean
}

// SLA
export interface SlaStatus {
  target_minutes: number | null
  elapsed_minutes: number
  percentage: number
  is_breached: boolean
  is_at_risk: boolean
  remaining_minutes: number | null
}

// Ticket
export interface Ticket {
  id: string
  ticket_number: string
  title: string
  status: TicketStatus
  priority: TicketPriority
  assigned_group_id: string | null
  assigned_group_name: string | null
  assigned_user_id: string | null
  assigned_user_name: string | null
  created_by_id: string
  created_by_name: string
  created_at: string
  updated_at: string
  sla_status: SlaStatus | null
}

export interface TicketDetail extends Ticket {
  description: string
  resolved_at: string | null
  first_assigned_at: string | null
  notes: TicketNote[]
  attachments: Attachment[]
  audit_log: AuditLogEntry[]
}

export interface TicketCreate {
  title: string
  description: string
  priority: TicketPriority
  assigned_group_id?: string
  assigned_user_id?: string
}

export interface TicketUpdate {
  title?: string
  description?: string
  status?: TicketStatus
  priority?: TicketPriority
  assigned_group_id?: string | null
  assigned_user_id?: string | null
}

// Notes
export interface TicketNote {
  id: string
  ticket_id: string
  author_id: string
  author_name: string
  content: string
  is_internal: boolean
  created_at: string
}

export interface NoteCreate {
  content: string
  is_internal?: boolean
}

// Attachments
export interface Attachment {
  id: string
  ticket_id: string
  filename: string
  original_filename: string
  file_size: number
  content_type: string
  uploaded_by_id: string
  uploaded_by_name: string
  uploaded_at: string
}

// Audit Log
export interface AuditLogEntry {
  id: string
  ticket_id: string
  actor_id: string | null
  actor_type: ActorType
  actor_name: string | null
  action: string
  field_changed: string | null
  old_value: string | null
  new_value: string | null
  metadata: Record<string, unknown> | null
  created_at: string
}

// Dashboard
export interface StatusCount {
  status: TicketStatus
  count: number
}

export interface PriorityCount {
  priority: TicketPriority
  count: number
}

export interface GroupSla {
  group_name: string
  mtta_minutes: number | null
  mttr_minutes: number | null
  breached_count: number
}

export interface DashboardSummary {
  status_counts: StatusCount[]
  priority_counts: PriorityCount[]
  total_open: number
}

export interface SlaMetrics {
  overall_mtta_minutes: number | null
  overall_mttr_minutes: number | null
  by_group: GroupSla[]
}

// API Keys
export interface ApiKey {
  id: string
  name: string
  key_prefix: string
  user_id: string
  is_active: boolean
  last_used_at: string | null
  expires_at: string | null
  created_at: string
}

export interface ApiKeyCreateResponse {
  id: string
  name: string
  key_prefix: string
  full_key: string
  created_at: string
}

export interface ApiKeyCreate {
  name: string
}

// Webhooks
export interface Webhook {
  id: string
  name: string
  url: string
  events: string[]
  is_active: boolean
  created_by_id: string
  last_triggered_at: string | null
  created_at: string
}

export interface WebhookCreate {
  name: string
  url: string
  secret: string
  events: string[]
}

export interface WebhookUpdate {
  name?: string
  url?: string
  events?: string[]
  is_active?: boolean
}

// SLA Config
export interface SlaConfigItem {
  priority: TicketPriority
  target_assign_minutes: number
  target_resolve_minutes: number
}

// Pagination
export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  size: number
}

// Auth
export interface LoginRequest {
  username: string
  password: string
}

export interface TokenResponse {
  access_token: string
  refresh_token: string
  token_type: string
}
```

**Step 2: Create API client**

`frontend/src/api/client.ts`:

```typescript
import type { TokenResponse } from '@/types'

let accessToken: string | null = null
let refreshToken: string | null = null
let onAuthFailure: (() => void) | null = null

export function setTokens(access: string, refresh: string) {
  accessToken = access
  refreshToken = refresh
}

export function clearTokens() {
  accessToken = null
  refreshToken = null
}

export function getAccessToken(): string | null {
  return accessToken
}

export function setAuthFailureHandler(handler: () => void) {
  onAuthFailure = handler
}

async function refreshAccessToken(): Promise<boolean> {
  if (!refreshToken) return false
  try {
    const res = await fetch('/api/v1/auth/refresh', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh_token: refreshToken }),
    })
    if (!res.ok) return false
    const data: TokenResponse = await res.json()
    setTokens(data.access_token, data.refresh_token)
    return true
  } catch {
    return false
  }
}

export interface ApiError {
  status: number
  detail: string
}

export async function apiClient<T>(
  url: string,
  options: RequestInit = {},
): Promise<T> {
  const headers: Record<string, string> = {
    ...(options.headers as Record<string, string> || {}),
  }

  if (accessToken) {
    headers['Authorization'] = `Bearer ${accessToken}`
  }

  // Don't set Content-Type for FormData (browser sets multipart boundary)
  if (!(options.body instanceof FormData) && !headers['Content-Type']) {
    headers['Content-Type'] = 'application/json'
  }

  let res = await fetch(url, { ...options, headers })

  // On 401, try refresh
  if (res.status === 401 && refreshToken) {
    const refreshed = await refreshAccessToken()
    if (refreshed) {
      headers['Authorization'] = `Bearer ${accessToken}`
      res = await fetch(url, { ...options, headers })
    }
  }

  if (res.status === 401) {
    clearTokens()
    onAuthFailure?.()
    throw { status: 401, detail: 'Authentication required' } as ApiError
  }

  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }))
    throw { status: res.status, detail: body.detail || res.statusText } as ApiError
  }

  // Handle 204 No Content
  if (res.status === 204) return undefined as T

  return res.json()
}
```

**Step 3: Commit**
```bash
git add frontend/src/types/index.ts frontend/src/api/client.ts
git commit -m "feat: add TypeScript types and API client with JWT refresh"
```

---

## Task 6: Frontend — Auth Context & Theme Context

**Files:**
- Create: `frontend/src/context/AuthContext.tsx`
- Create: `frontend/src/context/ThemeContext.tsx`

**Context:**
- AuthContext: stores `User | null`, provides `login()`, `logout()`, `isLoading` flag
- Login: POST `/api/v1/auth/login` → `{access_token, refresh_token, token_type}`
- After login, fetch current user: GET `/api/v1/users/me` (this endpoint exists)
- ThemeContext: persists `dark`/`light` to localStorage, toggles `dark` class on `<html>` element
- Default to dark mode

**Step 1: Create AuthContext**

Provides: `user`, `login(username, password)`, `logout()`, `isLoading`, `isAuthenticated`

Initialize by checking for stored refresh token (in memory — if page reloads, user must re-login; this is fine for v1).

**Step 2: Create ThemeContext**

Provides: `theme`, `toggleTheme()`

Reads from `localStorage.getItem('theme')`, defaults to `'dark'`. Sets/removes `dark` class on `document.documentElement`.

**Step 3: Commit**
```bash
git add frontend/src/context/
git commit -m "feat: add AuthContext and ThemeContext providers"
```

---

## Task 7: Frontend — App Shell & Layout Components

> **REQUIRED:** Use superpowers:frontend-design skill for this task.

**Files:**
- Create: `frontend/src/App.tsx`
- Create: `frontend/src/components/layout/AppShell.tsx`
- Create: `frontend/src/components/layout/Sidebar.tsx`
- Create: `frontend/src/components/layout/TopBar.tsx`
- Create: `frontend/src/components/layout/PageHeader.tsx`

**Context:**
- App.tsx: wraps everything in providers (QueryClientProvider, AuthProvider, ThemeProvider, BrowserRouter), defines routes
- AppShell: sidebar + main content area layout
- Sidebar: nav links with Lucide icons (Dashboard, Tickets, Admin section for admin users). Cat paw/magic icon logo at top.
- TopBar: page breadcrumbs on left, theme toggle + user dropdown (name, role, logout) on right
- PageHeader: title + optional action buttons
- Dark-mode-first design tokens from CSS custom properties
- Routes per design doc section 3: `/login` public, `/` dashboard, `/tickets/*` auth required, `/admin/*` admin only

**Step 1: Create App.tsx with routing and providers**

Routes:
- `/login` → Login page (public)
- `/` → Dashboard (protected)
- `/tickets` → TicketList (protected)
- `/tickets/new` → TicketCreate (protected)
- `/tickets/:id` → TicketDetail (protected)
- `/admin/users` → Users (admin)
- `/admin/groups` → Groups (admin)
- `/admin/api-keys` → ApiKeys (admin)
- `/admin/webhooks` → Webhooks (admin)
- `/admin/sla` → SlaConfig (admin)

Use placeholder page components that just render their name for now.

**Step 2: Create layout components**

Follow the design doc section 4 design system. Sidebar nav with grouped sections. Collapsible admin section. Active link highlighting.

**Step 3: Commit**
```bash
git add frontend/src/App.tsx frontend/src/components/layout/
git commit -m "feat: add App shell, sidebar, topbar, and routing"
```

---

## Task 8: Frontend — Shared UI Components

> **REQUIRED:** Use superpowers:frontend-design skill for this task.

**Files:**
- Create: `frontend/src/components/ui/Button.tsx`
- Create: `frontend/src/components/ui/Modal.tsx`
- Create: `frontend/src/components/ui/Toast.tsx`
- Create: `frontend/src/components/ui/Dropdown.tsx`
- Create: `frontend/src/components/ui/Spinner.tsx`
- Create: `frontend/src/components/ui/EmptyState.tsx`
- Create: `frontend/src/components/ui/StatusBadge.tsx`
- Create: `frontend/src/components/ui/PriorityBadge.tsx`
- Create: `frontend/src/components/ui/SlaIndicator.tsx`

**Context:**
- StatusBadge: chip styled per status (Open=blue, Under Investigation=amber, Paused=slate, Resolved=emerald). Uses `bg-{color}-500/15 text-{color}-400` pattern.
- PriorityBadge: Critical=red with `animate-pulse` dot, High=red solid, Medium=yellow, Low=gray
- SlaIndicator: colored dot + "2h 15m remaining" or "Breached by 45m". Green <60%, Yellow 60-80%, Red >80%
- Button: variants (primary, secondary, ghost, danger), sizes (sm, md, lg)
- Modal: overlay + centered panel with title, body, footer actions
- Toast: notification system (success, error, info) — auto-dismiss
- Dropdown: select-like component with search for long lists
- Spinner: loading indicator
- EmptyState: illustration + message + optional action button

**Step 1: Create all UI components following design system**

**Step 2: Commit**
```bash
git add frontend/src/components/ui/
git commit -m "feat: add shared UI components (badges, buttons, modal, toast)"
```

---

## Task 9: Frontend — TipTap Rich Text Editor Component

> **REQUIRED:** Use superpowers:frontend-design skill for this task.

**Files:**
- Create: `frontend/src/components/editor/TipTapEditor.tsx`

**Context:**
- Extensions: StarterKit (bold, italic, headings, lists, blockquote, horizontal rule, hard break), CodeBlockLowlight, Image (clipboard paste), Link, Placeholder
- Toolbar: Bold, Italic, H1/H2/H3, Bullet List, Ordered List, Code Block, Image (file select), Link, Undo/Redo
- Props: `content` (initial HTML), `onChange(html: string)`, `editable` (default true), `placeholder`
- Style the editor area to match dark/light theme (surface-secondary background, border)
- Toolbar buttons use Lucide icons, highlight when format is active
- Used in: ticket create, ticket description edit, note creation

**Step 1: Create TipTapEditor component**

**Step 2: Commit**
```bash
git add frontend/src/components/editor/
git commit -m "feat: add TipTap rich text editor component with toolbar"
```

---

## Task 10: Frontend — TanStack Query Hooks

**Files:**
- Create: `frontend/src/hooks/useAuth.ts`
- Create: `frontend/src/hooks/useTickets.ts`
- Create: `frontend/src/hooks/useDashboard.ts`
- Create: `frontend/src/hooks/useUsers.ts`
- Create: `frontend/src/hooks/useGroups.ts`

**Context:**
- All hooks use `apiClient` from `@/api/client`
- Queries use TanStack Query v5 (`useQuery`, `useMutation`, `useQueryClient`)
- Dashboard hooks use `refetchInterval: 30000` for polling
- Ticket list hook supports: pagination (page, size), filters (status, priority, group_id, assigned_user_id, search), sorting
- All list endpoints: `GET /api/v1/{resource}?page=1&size=25` → `PaginatedResponse<T>`
- Mutation hooks invalidate related queries on success

**Step 1: Create useAuth hook**

Functions: `useLogin()` mutation, `useCurrentUser()` query, `useLogout()` mutation.

**Step 2: Create useTickets hook**

Functions: `useTickets(filters)` query, `useTicket(id)` query, `useCreateTicket()` mutation, `useUpdateTicket()` mutation, `useDeleteTicket()` mutation, `useTicketNotes(ticketId)` (if notes fetched separately), `useCreateNote(ticketId)` mutation, `useUploadAttachment(ticketId)` mutation.

**Step 3: Create useDashboard hook**

Functions: `useDashboardSummary()` query with 30s polling, `useSlaMetrics()` query with 30s polling, `useRecentActivity()` query with 30s polling.

The activity feed uses `GET /api/v1/dashboard/activity` which returns recent audit log entries.

**Step 4: Create useUsers and useGroups hooks**

Standard CRUD query/mutation hooks for users and groups.

Also create: `useApiKeys()`, `useWebhooks()`, `useSlaConfig()` hooks.

**Step 5: Commit**
```bash
git add frontend/src/hooks/
git commit -m "feat: add TanStack Query hooks for all API endpoints"
```

---

## Task 11: Frontend — Utility Functions

**Files:**
- Create: `frontend/src/utils/sla.ts`
- Create: `frontend/src/utils/format.ts`

**Context:**
- SLA utils: format remaining time ("2h 15m remaining" or "Breached by 45m"), calculate SLA color (green/yellow/red based on percentage), format percentage
- Format utils: relative date ("3 hours ago" using date-fns `formatDistanceToNow`), absolute date format, ticket number display with monospace hint

**Step 1: Create utility functions**

**Step 2: Commit**
```bash
git add frontend/src/utils/
git commit -m "feat: add SLA and date formatting utility functions"
```

---

## Task 12: Frontend — Login Page

> **REQUIRED:** Use superpowers:frontend-design skill for this task.

**Files:**
- Create: `frontend/src/pages/Login.tsx`

**Context:**
- Centered card on dark gradient background
- App name ("Accio ServiceMeow") + cat/magic icon
- Username and password input fields
- "Sign In" button (primary, full width)
- Inline error message on failure (red text below form)
- On success: store tokens via AuthContext, redirect to `/`
- Uses `useLogin()` mutation hook

**Step 1: Create Login page**

**Step 2: Commit**
```bash
git add frontend/src/pages/Login.tsx
git commit -m "feat: add Login page"
```

---

## Task 13: Frontend — Dashboard Page

> **REQUIRED:** Use superpowers:frontend-design skill for this task.

**Files:**
- Create: `frontend/src/pages/Dashboard.tsx`
- Create: `frontend/src/components/dashboard/SummaryCard.tsx`
- Create: `frontend/src/components/dashboard/SlaPanel.tsx`
- Create: `frontend/src/components/dashboard/PriorityChart.tsx`
- Create: `frontend/src/components/dashboard/ActivityFeed.tsx`

**Context:**
- Four sections in grid layout per design doc section 5
- Top row: 4 summary cards (one per status, status-colored left border, count + label, clickable → ticket list filtered by status)
- Second row left: SLA Health panel (MTTA/MTTR large numbers, table by group with breach counts, red on breaches)
- Second row right: Priority Distribution (CSS stacked bar chart, no charting library, segments colored by priority)
- Bottom row: Activity feed (scrollable audit log entries, person/robot icons for actor type, relative timestamps)
- Uses `useDashboardSummary()`, `useSlaMetrics()`, `useRecentActivity()` — all polling at 30s
- Dashboard summary API: `GET /api/v1/dashboard/summary`
- SLA metrics API: `GET /api/v1/dashboard/sla`
- Activity API: `GET /api/v1/dashboard/activity`

**Step 1: Create dashboard component pieces**

**Step 2: Create Dashboard page composing all pieces**

**Step 3: Commit**
```bash
git add frontend/src/pages/Dashboard.tsx frontend/src/components/dashboard/
git commit -m "feat: add Dashboard page with summary, SLA, priority chart, activity"
```

---

## Task 14: Frontend — Ticket List Page

> **REQUIRED:** Use superpowers:frontend-design skill for this task.

**Files:**
- Create: `frontend/src/pages/TicketList.tsx`
- Create: `frontend/src/components/tickets/TicketTable.tsx`
- Create: `frontend/src/components/tickets/TicketFilters.tsx`

**Context:**
- Top area: search bar (full-text) + filter dropdowns (Status multi-select, Priority, Group, Assignee, SLA Breached toggle)
- Filters update URL query params (`useSearchParams`) for shareable links
- Table columns: Checkbox, Ticket # (monospace), Title, Status (chip), Priority (badge), Group, Assignee, Created (relative), SLA (indicator)
- Sortable columns (click header to toggle sort)
- Clickable rows → navigate to `/tickets/:id`
- Bulk actions bar: appears when checkboxes selected. "N selected" + Change Status / Reassign buttons → modal
- Pagination: "Showing 1-25 of 142", prev/next buttons, page size selector (25/50/100)
- API: `GET /api/v1/tickets?page=1&size=25&status=open&priority=high&search=...&sort_by=created_at&sort_order=desc`

**Step 1: Create TicketFilters component**

**Step 2: Create TicketTable component**

**Step 3: Create TicketList page composing filters, table, pagination**

**Step 4: Commit**
```bash
git add frontend/src/pages/TicketList.tsx frontend/src/components/tickets/
git commit -m "feat: add Ticket List page with filters, table, bulk actions, pagination"
```

---

## Task 15: Frontend — Ticket Detail Page

> **REQUIRED:** Use superpowers:frontend-design skill for this task.

**Files:**
- Create: `frontend/src/pages/TicketDetail.tsx`

**Context:**
- Two-column layout: main content (~65%) + sidebar (~35%)
- **Header (full width):** ticket number (monospace), title (inline-editable on click), status chip, priority badge, SLA countdown
- **Left panel — Description:** rendered HTML. "Edit" button swaps to TipTap editor. Saves via PATCH.
- **Left panel — Tabbed section (3 tabs):**
  - Notes/Work Log (default): chronological notes, author avatar (initials circle), name, timestamp, rendered HTML. Internal notes get "Internal" badge + different bg tint. TipTap editor at bottom with "Internal note" toggle + "Post" button.
  - Attachments: grid of cards (filename, size, type icon, uploader, date). Drag-and-drop upload zone with progress.
  - Audit Log: vertical timeline. Action, actor (robot/person icon), field old→new, timestamp.
- **Right panel — sidebar:** stacked property fields as inline-editable dropdowns:
  - Status (color-coded), Priority, Assigned Group, Assigned User (filtered by selected group), Created By (read-only), Created/Updated At (read-only), SLA Details (target, elapsed, percentage bar, breach text)
  - Each dropdown change fires PATCH immediately with optimistic update
- API: `GET /api/v1/tickets/:id` returns TicketDetailResponse with notes, attachments, audit_log included
- Notes: `POST /api/v1/tickets/:id/notes`
- Attachments: `POST /api/v1/tickets/:id/attachments` (multipart/form-data)
- Updates: `PATCH /api/v1/tickets/:id`

**Step 1: Create TicketDetail page with all sub-sections**

This is the most complex page. Build it section by section: header, description, notes tab, attachments tab, audit log tab, sidebar.

**Step 2: Commit**
```bash
git add frontend/src/pages/TicketDetail.tsx
git commit -m "feat: add Ticket Detail page with notes, attachments, audit log, sidebar"
```

---

## Task 16: Frontend — Ticket Create Page

> **REQUIRED:** Use superpowers:frontend-design skill for this task.

**Files:**
- Create: `frontend/src/pages/TicketCreate.tsx`

**Context:**
- Single-column centered form
- Fields: Title (text input), Description (TipTap editor), Priority (dropdown, required), Group (optional dropdown), User (optional dropdown, filtered by selected group)
- "Create Ticket" button → POST `/api/v1/tickets` → navigate to `/tickets/:id` on success
- Uses `useCreateTicket()` mutation
- Uses `useGroups()` and `useUsers()` for dropdown options

**Step 1: Create TicketCreate page**

**Step 2: Commit**
```bash
git add frontend/src/pages/TicketCreate.tsx
git commit -m "feat: add Ticket Create page with TipTap editor"
```

---

## Task 17: Frontend — Admin Pages

> **REQUIRED:** Use superpowers:frontend-design skill for this task.

**Files:**
- Create: `frontend/src/pages/admin/Users.tsx`
- Create: `frontend/src/pages/admin/Groups.tsx`
- Create: `frontend/src/pages/admin/ApiKeys.tsx`
- Create: `frontend/src/pages/admin/Webhooks.tsx`
- Create: `frontend/src/pages/admin/SlaConfig.tsx`

**Context:**

**Users (`/admin/users`):**
- Table: Name, Username, Email, Role badge, Status (active/inactive), Groups
- "Add User" button → modal with fields: username, email, full_name, password, role
- Click row → edit modal (same fields minus password, + active toggle)
- API: GET/POST `/api/v1/users`, PATCH `/api/v1/users/:id`

**Groups (`/admin/groups`):**
- Table: Name, Description, Members count, Lead name
- "Add Group" button → modal (name, description)
- Click row → detail with member list, "Add Member" dropdown + is_lead checkbox, "Remove" per member
- API: GET/POST `/api/v1/groups`, GET `/api/v1/groups/:id`, POST/DELETE `/api/v1/groups/:id/members`

**API Keys (`/admin/api-keys`):**
- Table: Name, Prefix, Created, Last Used, Status
- "Generate Key" → modal (name) → shows full key ONCE with copy button + warning
- "Revoke" per row with confirmation modal
- API: GET/POST `/api/v1/api-keys`, DELETE `/api/v1/api-keys/:id`

**Webhooks (`/admin/webhooks`):**
- Table: Name, URL, Events badges, Active toggle, Last Triggered
- "Add Webhook" → modal (name, URL, events multi-select, auto-generated secret shown once)
- Edit/delete actions
- API: GET/POST `/api/v1/webhooks`, PATCH/DELETE `/api/v1/webhooks/:id`

**SLA Config (`/admin/sla`):**
- Table: one row per priority (Critical, High, Medium, Low)
- Columns: Priority, Target Assign (minutes input), Target Resolve (minutes input)
- "Update" button saves all at once via PATCH `/api/v1/sla-config`
- API: GET/PATCH `/api/v1/sla-config`

**Step 1: Create Users admin page**

**Step 2: Create Groups admin page**

**Step 3: Create ApiKeys admin page**

**Step 4: Create Webhooks admin page**

**Step 5: Create SlaConfig admin page**

**Step 6: Commit**
```bash
git add frontend/src/pages/admin/
git commit -m "feat: add admin pages (users, groups, API keys, webhooks, SLA config)"
```

---

## Task 18: Docker — Multi-Stage Nginx Build with Frontend

**Files:**
- Modify: `nginx/Dockerfile`
- Modify: `docker-compose.yml` (add frontend build context)
- Modify: `docker-compose.dev.yml` (add Vite dev server service)

**Context:**
- Current nginx Dockerfile: `FROM nginx:1.27-alpine`, copies nginx.conf and entrypoint
- Need multi-stage: Stage 1 builds frontend with Node 20, Stage 2 copies dist to nginx
- Production: `docker compose up --build` → nginx serves built React assets
- Development: `docker compose -f docker-compose.yml -f docker-compose.dev.yml up` → nginx proxies to Vite dev server on port 5173
- Frontend build context needs to be accessible from nginx Dockerfile — use Docker build context root
- nginx.conf already has `location / { root /usr/share/nginx/html; try_files ... /index.html; }` for SPA

**Step 1: Update nginx Dockerfile for multi-stage build**

```dockerfile
# Stage 1: Build frontend
FROM node:20-alpine AS frontend-build
WORKDIR /app
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# Stage 2: Nginx with certs + frontend
FROM nginx:1.27-alpine
RUN apk add --no-cache openssl bash
COPY --from=frontend-build /app/dist /usr/share/nginx/html
COPY nginx/nginx.conf /etc/nginx/nginx.conf
COPY nginx/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
EXPOSE 443
ENTRYPOINT ["/entrypoint.sh"]
```

**Step 2: Update docker-compose.yml**

Change nginx build context from `./nginx` to `.` (project root) and set dockerfile path:
```yaml
nginx:
  build:
    context: .
    dockerfile: nginx/Dockerfile
```

**Step 3: Update docker-compose.dev.yml**

Add `frontend` service running Vite dev server:
```yaml
services:
  frontend:
    image: node:20-alpine
    working_dir: /app
    command: sh -c "npm install && npm run dev -- --host 0.0.0.0"
    volumes:
      - ./frontend:/app
      - frontend_node_modules:/app/node_modules
    ports:
      - "5173:5173"

  nginx:
    build:
      context: ./nginx
    volumes:
      - ./nginx/nginx.dev.conf:/etc/nginx/nginx.conf:ro
```

Create `nginx/nginx.dev.conf` that proxies `/` to `frontend:5173` instead of serving static files.

**Step 4: Build and verify**
```bash
docker compose build nginx
docker compose up -d
# Verify: curl -k https://localhost/ should return React HTML
```

**Step 5: Commit**
```bash
git add nginx/Dockerfile docker-compose.yml docker-compose.dev.yml nginx/nginx.dev.conf
git commit -m "feat: multi-stage Docker build serving React frontend via nginx"
```

---

## Task 19: README

**Files:**
- Create: `README.md`

**Context:**
- Project README covering: quick start, default credentials, MCP config, demo walkthrough, architecture
- Quick start: `cp .env.example .env && docker compose up -d`
- Default creds: admin/admin
- MCP config for Claude Desktop (`claude_desktop_config.json`) and Claude Code (`.mcp.json`)
- Endpoints: `https://localhost/api/v1/`, `https://localhost/mcp/`
- Architecture: FastAPI + PostgreSQL + nginx + React

**Step 1: Write README.md**

Cover all sections from design doc section 8.4.

**Step 2: Commit**
```bash
git add README.md
git commit -m "docs: add project README with quickstart and MCP configuration"
```

---

## Task 20: End-to-End Smoke Test

**Files:** None (testing only)

**Context:**
- Rebuild and test the full stack
- Verify: frontend loads, login works, create ticket, view dashboard, admin pages accessible
- Verify: MCP still works via curl
- Verify: webhook dispatch fires (check logs)

**Step 1: Rebuild Docker**
```bash
docker compose down && docker compose up --build -d
```

**Step 2: Wait for services and run smoke tests**
```bash
# Health check
curl -sk https://localhost/api/v1/health

# Frontend loads
curl -sk https://localhost/ | head -20  # Should show React HTML with <div id="root">

# Login
curl -sk -X POST https://localhost/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"username":"admin","password":"admin"}'

# MCP initialize
curl -sk -X POST https://localhost/mcp/ \
  -H 'Content-Type: application/json' \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-03-26","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}}}'
```

**Step 3: Verify and commit any fixes**

---

## Execution Notes

- Tasks 1-3 are backend-only and independent — can be done first
- Task 4 must complete before Tasks 5-17 (frontend depends on scaffolding)
- Tasks 5-6 must complete before Tasks 7+ (hooks and context used everywhere)
- Task 7 must complete before Tasks 12-17 (layout wraps all pages)
- Tasks 8-9 can be done in parallel with Task 7 (component library)
- Tasks 10-11 should complete before page tasks (hooks used in pages)
- Task 18 depends on frontend being buildable (after Task 4+ at minimum)
- Task 19 can be done anytime
- Task 20 is final verification
