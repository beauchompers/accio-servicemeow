# Accio ServiceMeow — Phase 4+ Design: Frontend, Backend Gaps & Polish

**Date:** 2026-02-05
**Scope:** React frontend, remaining backend gaps, Docker integration, README
**Prerequisite:** Phases 1-3 complete (backend fully implemented)

---

## Decisions Made

- **Full TipTap** rich text editor for ticket descriptions and notes
- **TanStack Query v5** for server state, React context for auth/theme
- **Polling** (30s refetchInterval) for dashboard/activity — no WebSocket for v1
- **Nginx serves frontend** via multi-stage Docker build — no separate frontend container
- **frontend-design skill** used during implementation for polished, distinctive UI

---

## 1. Tech Stack

| Library | Purpose |
|---------|---------|
| React 18 + TypeScript | UI framework |
| Vite | Build tool / dev server |
| Tailwind CSS 3 | Utility-first styling |
| TanStack Query v5 | Server state, caching, polling |
| React Router v6 | Client-side routing |
| TipTap (StarterKit + CodeBlock + Image + Link) | Rich text editor |
| Lucide React | Icon library |
| date-fns | Date formatting |
| React Context | Auth state (JWT), theme (dark/light) |

---

## 2. Directory Structure

```
frontend/
├── Dockerfile              # Multi-stage: node build → copy to nginx
├── package.json
├── vite.config.ts
├── tailwind.config.js
├── tsconfig.json
├── index.html
├── public/
│   └── favicon.svg
└── src/
    ├── main.tsx            # Entry point, providers
    ├── App.tsx             # Router setup
    ├── api/
    │   └── client.ts       # Fetch wrapper with JWT/refresh handling
    ├── hooks/
    │   ├── useAuth.ts      # Login, logout, token refresh
    │   ├── useTickets.ts   # TanStack Query hooks for ticket CRUD
    │   ├── useDashboard.ts # Dashboard summary, SLA, activity
    │   ├── useUsers.ts     # User CRUD hooks
    │   └── useGroups.ts    # Group CRUD hooks
    ├── context/
    │   ├── AuthContext.tsx  # JWT state, current user, login/logout
    │   └── ThemeContext.tsx # Dark/light mode toggle (localStorage)
    ├── components/
    │   ├── layout/         # AppShell, Sidebar, TopBar, PageHeader
    │   ├── tickets/        # TicketTable, TicketFilters, StatusBadge, PriorityBadge, SlaIndicator
    │   ├── editor/         # TipTapEditor (reusable rich text component)
    │   ├── ui/             # Button, Modal, Toast, Dropdown, FileUpload, Spinner, EmptyState
    │   └── dashboard/      # SummaryCard, SlaGauge, ActivityFeed, PriorityChart
    ├── pages/
    │   ├── Login.tsx
    │   ├── Dashboard.tsx
    │   ├── TicketList.tsx
    │   ├── TicketDetail.tsx
    │   ├── TicketCreate.tsx
    │   └── admin/
    │       ├── Users.tsx
    │       ├── Groups.tsx
    │       ├── ApiKeys.tsx
    │       ├── Webhooks.tsx
    │       └── SlaConfig.tsx
    ├── types/
    │   └── index.ts        # TypeScript interfaces matching backend schemas
    └── utils/
        ├── sla.ts          # SLA percentage, time-remaining formatting
        └── format.ts       # Date formatting, ticket number display
```

---

## 3. Routing

| Path | Page | Auth |
|------|------|------|
| `/login` | Login | Public |
| `/` | Dashboard | Required |
| `/tickets` | Ticket List | Required |
| `/tickets/new` | Create Ticket | Required |
| `/tickets/:id` | Ticket Detail | Required |
| `/admin/users` | User Management | Admin |
| `/admin/groups` | Group Management | Admin |
| `/admin/api-keys` | API Key Management | Admin |
| `/admin/webhooks` | Webhook Management | Admin/Manager |
| `/admin/sla` | SLA Configuration | Admin |

Protected routes redirect to `/login` if no valid JWT. Admin routes return 403 for non-admin users.

---

## 4. Design System

### Theme

Dark-mode-first. Light mode via toggle, persisted to localStorage.

| Token | Dark Mode | Light Mode |
|-------|-----------|------------|
| `--bg-primary` | `#0f1117` | `#ffffff` |
| `--bg-secondary` | `#1a1d27` | `#f8fafc` |
| `--bg-tertiary` | `#242838` | `#f1f5f9` |
| `--border` | `#2e3348` | `#e2e8f0` |
| `--text-primary` | `#f1f5f9` | `#0f172a` |
| `--text-secondary` | `#94a3b8` | `#64748b` |
| `--accent` | `#3B82F6` | `#3B82F6` |
| `--accent-hover` | `#60a5fa` | `#2563eb` |

### Status Chips

- Open: `bg-blue-500/15 text-blue-400`
- Under Investigation: `bg-amber-500/15 text-amber-400`
- Paused: `bg-slate-500/15 text-slate-400`
- Resolved: `bg-emerald-500/15 text-emerald-400`

### Priority Badges

- Critical: red with `animate-pulse` on dot
- High: red solid
- Medium: yellow
- Low: gray

### SLA Indicator

Colored dot + text label:
- Green (< 60% elapsed)
- Yellow (60-80%, approaching)
- Red (> 80%, at risk or breached)
- Text: "2h 15m remaining" or "Breached by 45m"

### Typography

Inter font. Monospace (`font-mono`) for ticket numbers. Subtle CSS transitions (`transition-all duration-200`) on hover states.

---

## 5. Pages

### Dashboard (`/`)

Four sections in a grid layout:

**Top row — 4 summary cards:** One per status (Open, Under Investigation, Paused, Resolved). Status-colored left border accent. Count + label. Clickable — navigates to ticket list pre-filtered by status.

**Second row, left — SLA Health panel:** MTTA and MTTR as large numbers with units. Table breakdown by group: Group | MTTA | MTTR | Breached Count. Red highlight on breach rows. Data from `GET /dashboard/sla`.

**Second row, right — Priority Distribution:** Horizontal stacked bar chart built with CSS divs (no charting library). Segments colored by priority, labeled with counts.

**Bottom row — Recent Activity feed:** Scrollable list of audit log entries from `GET /dashboard/activity`. Each entry: icon (person vs robot for API key actors), actor name, action description, relative timestamp. Polls every 30s via TanStack Query `refetchInterval`.

### Ticket List (`/tickets`)

**Top area:** Search bar (full-text) + filter dropdowns (Status multi-select, Priority, Group, Assignee, SLA Breached toggle). Filters update URL query params for shareable links.

**Table:** Columns — Checkbox, Ticket #, Title, Status (chip), Priority (badge), Group, Assignee, Created (relative), SLA (dot + remaining). Sortable columns. Clickable rows → ticket detail.

**Bulk actions bar:** Appears on checkbox selection. "N selected" + Change Status / Reassign buttons → modal.

**Pagination:** "Showing 1-25 of 142", prev/next, page size selector (25/50/100).

### Ticket Detail (`/tickets/:id`)

Two-column layout: main content (~65%) + sidebar (~35%).

**Header:** Full width. Ticket number (monospace), title (inline-editable), status chip, priority badge, SLA countdown.

**Left panel:**

*Description:* Rendered HTML. "Edit" button swaps to TipTap editor. Saves via PATCH.

*Tabbed section (3 tabs):*

- **Notes/Work Log** (default): Chronological notes with author avatar (initials), name, timestamp, rendered HTML. Internal notes get "Internal" badge + different background tint. TipTap editor at bottom with "Internal note" toggle + "Post" button.

- **Attachments**: Grid of cards (filename, size, type icon, uploader, date). Drag-and-drop upload zone at top with progress bar.

- **Audit Log**: Vertical timeline. Each node: action, actor (robot icon for API, person for human), field old→new values, timestamp.

**Right panel — sidebar:**

Stacked property fields, each an inline-editable dropdown:
- Status (color-coded dropdown)
- Priority (dropdown)
- Assigned Group (dropdown)
- Assigned User (dropdown, filtered by group)
- Created By (read-only)
- Created At / Updated At (read-only)
- SLA Details: target, elapsed, percentage bar (green/yellow/red), breach text

Each dropdown change fires PATCH immediately with optimistic update.

### Ticket Create (`/tickets/new`)

Single-column centered form: Title (text input), Description (TipTap), Priority (dropdown, required), Group (optional), User (optional, filtered by group). "Create Ticket" button → navigates to new ticket detail on success.

### Login (`/login`)

Centered card on dark gradient background. App name + icon. Username/password fields, "Sign In" button. Inline error message on failure.

### Admin Pages

Shared layout with admin sub-nav in sidebar.

**Users (`/admin/users`):** Table (Name, Username, Email, Role badge, Status, Groups). "Add User" → modal (username, email, full_name, password, role). Click row → edit modal (same fields, no password, + active toggle).

**Groups (`/admin/groups`):** Table (Name, Description, Members count, Lead). "Add Group" → modal. Click row → detail view with member list, "Add Member" dropdown + is_lead checkbox, "Remove" buttons.

**API Keys (`/admin/api-keys`):** Table (Name, Prefix, Created, Last Used, Status). "Generate Key" → modal (name field) → shows full key once with copy button + warning. "Revoke" per row with confirmation.

**Webhooks (`/admin/webhooks`):** Table (Name, URL, Events badges, Active toggle, Last Triggered). "Add Webhook" → modal (name, URL, events multi-select, auto-generated secret shown once). Edit/delete actions.

**SLA Config (`/admin/sla`):** Table with one row per priority: Priority | Target Assign (minutes input) | Target Resolve (minutes input). "Update" button saves all. Hits `PATCH /api/v1/sla-config`.

---

## 6. API Client & Auth Flow

### Fetch Wrapper (`api/client.ts`)

A thin wrapper around `fetch` that:
- Adds `Authorization: Bearer <token>` header to all requests
- On 401 response, attempts token refresh via `POST /api/v1/auth/refresh`
- If refresh fails, clears auth state and redirects to `/login`
- Returns typed responses matching backend schemas

### Auth Context (`context/AuthContext.tsx`)

Provides:
- `user: User | null` — current logged-in user
- `login(username, password)` — calls login endpoint, stores tokens
- `logout()` — clears tokens, redirects to `/login`
- Access token stored in memory (not localStorage for security)
- Refresh token sent as HTTP-only cookie by backend

---

## 7. TipTap Editor

Reusable `<TipTapEditor>` component wrapping TipTap with:

**Extensions:** StarterKit (bold, italic, headings, bullet/ordered lists, blockquote, horizontal rule, hard break), CodeBlockLowlight (syntax highlighting), Image (paste from clipboard support), Link.

**Toolbar:** Bold, Italic, H1/H2/H3, Bullet List, Ordered List, Code Block, Image, Link, Undo/Redo.

**Props:** `content` (initial HTML), `onChange` (callback with HTML string), `editable` (toggle read-only), `placeholder`.

Used in: ticket description (create + edit), note creation.

---

## 8. Backend Additions

### 8.1 Webhook Dispatch Wiring

Add `dispatch_event()` calls in `ticket_service.py`:

- `create_ticket` → `dispatch_event("ticket.created", ticket_data)`
- `update_ticket` → `dispatch_event("ticket.updated", ...)` and conditionally `ticket.status_changed`, `ticket.assigned`, `ticket.resolved`
- `soft_delete_ticket` → `dispatch_event("ticket.resolved", ...)`

In `sla_checker.py`:
- `dispatch_event("ticket.sla_breached", ...)` with in-memory set tracking which tickets already had breach events emitted (to fire once per breach).

### 8.2 SLA Config Update Endpoint

```
PATCH /api/v1/sla-config
```

Request body: list of `{priority, target_assign_minutes, target_resolve_minutes}`. Admin-only. Upserts each row.

Also add `GET /api/v1/sla-config` to list current config (needed by the admin page).

### 8.3 MCP Error Handling

Wrap each MCP tool function body in try/except:

```python
try:
    # existing tool logic
except ValueError as e:
    return {"summary": f"Error: {e}", "data": None}
except HTTPException as e:
    return {"summary": f"Error: {e.detail}", "data": None}
except Exception as e:
    return {"summary": f"Unexpected error: {e}", "data": None}
```

### 8.4 README

Project README covering:
- Quick start: `cp .env.example .env && docker compose up -d`
- Default credentials (admin/admin)
- MCP configuration for Claude Desktop and Claude Code
- Demo walkthrough (create ticket via MCP, view in UI)
- Architecture overview

---

## 9. Docker Integration

### Frontend Build

The nginx Dockerfile gains a multi-stage build:

```dockerfile
# Stage 1: Build frontend
FROM node:20-alpine AS frontend-build
WORKDIR /app
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# Stage 2: Nginx with certs + frontend
FROM nginx:alpine
# ... existing cert generation entrypoint ...
COPY --from=frontend-build /app/dist /usr/share/nginx/html
COPY nginx/nginx.conf /etc/nginx/nginx.conf
```

### Dev Compose Override (`docker-compose.dev.yml`)

Adds a `frontend` service running Vite dev server on port 5173 with source mounted as a volume. Overrides nginx to proxy `location /` to the Vite dev server instead of serving static files.

| Mode | Command | Frontend Serving |
|------|---------|-----------------|
| Production | `docker compose up --build` | Nginx serves built assets |
| Development | `docker compose -f docker-compose.yml -f docker-compose.dev.yml up` | Nginx proxies to Vite dev server |

---

## 10. Testing Strategy

**Frontend:** TypeScript strict mode (`strict: true`) catches data-shape bugs. No component unit tests for v1. Manual smoke test checklist in README.

**Backend additions:** Integration tests for SLA config update endpoint and webhook dispatch verification (mock HTTP, assert event payloads).

**End-to-end:** Docker smoke test after build — verify nginx serves frontend at `/`, SPA routing works for deep links, API proxy functions correctly.
