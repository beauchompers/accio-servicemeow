# Frontend Consistency Review — Design

## Goal

Bring visual and behavioral consistency across all frontend pages. Five areas:

1. Replace all modals with inline expanding forms
2. Create a reusable Toggle component, replace all ad-hoc toggles
3. Standardize form validation (inline field errors) and API error handling (toasts)
4. Consistent empty states, loading states, and error states on every page
5. Standardize styling: tables, inputs, badges, labels, cards, and spacing

---

## 1. Replace Modals with Inline Forms

Remove all `<Modal>` usage from admin pages. Forms expand inline, pushing page content down.

### Pattern

- **Add/Create:** Clicking the "Add" button shows an inline form card at the top of the list. The card has the same styling as other page sections (`bg-[var(--bg-secondary)] border border-[var(--border)] rounded-xl`). Cancel collapses it.
- **Edit:** Clicking a table row expands an edit form directly below that row. Only one edit form open at a time — opening another collapses the previous. Cancel collapses it.
- **TopBar Change Password:** Convert from modal to a dropdown panel anchored below the Lock icon. Click outside or Cancel to close.

### Pages Affected

| Page | Create | Edit |
|------|--------|------|
| Users | Inline form card above table | Inline form below clicked row |
| Webhooks | Inline form card above table | Inline form below clicked row |
| ApiKeys | Inline form card above table | N/A (no edit, just revoke) |
| Groups | Already inline (side panel) | No change |
| TopBar | N/A | Change Password → dropdown panel |
| Tickets | Already inline | No change |

### Component Changes

- Remove `Modal` import from Users.tsx, Webhooks.tsx, ApiKeys.tsx, TopBar.tsx
- No new shared component needed — each page manages its own expand/collapse state
- The `Modal` component itself stays (may be useful for future confirmation dialogs)

---

## 2. Reusable Toggle Component

### New Component: `components/ui/Toggle.tsx`

```
interface ToggleProps {
  checked: boolean
  onChange: (checked: boolean) => void
  label?: string
  disabled?: boolean
}
```

Uses the sr-only peer checkbox pattern from Users.tsx (most accessible). Track/thumb with emerald-500 checked state, smooth transition.

### Replacements

| Page | Current Implementation | Replace With |
|------|----------------------|-------------|
| Users.tsx | Custom sr-only peer checkbox | `<Toggle>` |
| Webhooks.tsx | Custom toggle button with inline styles | `<Toggle>` |
| Groups.tsx | Plain checkbox for is_lead | `<Toggle>` |

---

## 3. Standardized Form Validation & Errors

### Rules

- **Field validation errors:** Inline `<p className="text-sm text-red-400 mt-1">` below the input. Never use toast for validation.
- **API/server errors:** Toast via `useToast().error()`. These are unexpected failures.
- **Success feedback:** Toast via `useToast().success()`.
- **Required field indicators:** Red `*` after label text for required fields.
- **Validation timing:** On submit only. No blur or change validation.
- **Error extraction:** Standardize on `err instanceof Error ? err.message : 'Failed to [action].'`

### Pages Affected

All pages with forms: Users, Groups, Webhooks, ApiKeys, SlaConfig, TicketCreate, TopBar (Change Password).

---

## 4. Consistent Empty, Loading, and Error States

### Loading

Every page: `<PageHeader>` + centered `<Spinner size="lg">` in a `py-20` container.

Exception: Dashboard keeps its per-card spinners (loading multiple independent sections).

### Empty States

Every list page uses `<EmptyState>` with:
- `icon` — relevant lucide icon for the page
- `title` — "No [things] yet" or "No [things] configured"
- `description` — brief guidance
- `action` — CTA button when user can create something
- Filtered variant: "No [things] match your filters" when filters are active

### Error States

Every page that fetches data handles errors with `<EmptyState>`:
- `title` — "Failed to load [things]"
- `description` — "An error occurred while fetching data. Please try again."
- No action button (retry is manual page refresh)

### Pages to Audit

Dashboard, TicketList, TicketDetail, TicketCreate, Users, Groups, ApiKeys, Webhooks, SlaConfig.

---

## 5. Standardize Styling

### Tables

Standardize all tables to match the admin page pattern (Users/Webhooks/ApiKeys):

```
Container: bg-[var(--bg-secondary)] border border-[var(--border)] rounded-xl overflow-hidden
Header cells: text-left text-xs uppercase text-[var(--text-secondary)] font-medium px-4 py-3
Body rows: border-b border-[var(--border)] hover:bg-[var(--bg-tertiary)] transition-colors duration-150
Body cells: px-4 py-3 text-sm
```

**TicketTable.tsx fixes:**
- Change `px-3` → `px-4` on all cells
- Remove `tracking-wider` from headers
- Replace `divide-y` on tbody with `border-b` on each row
- Add `bg-[var(--bg-secondary)]` to container

**SlaConfig.tsx fix:**
- Change `py-4` → `py-3` on body cells (left border accent is fine to keep)

### Inputs

Standard input class (all regular form inputs):

```
w-full bg-[var(--bg-tertiary)] border border-[var(--border)] text-[var(--text-primary)] rounded-lg px-3 py-2 placeholder:text-[var(--text-secondary)] focus:outline-none focus:ring-2 focus:ring-[var(--accent)]/50 focus:border-[var(--accent)] transition-colors duration-200
```

Changes from current standard:
- Add `focus:border-[var(--accent)] transition-colors duration-200` everywhere (Login already has this)
- Drop placeholder `/50` opacity — use `placeholder:text-[var(--text-secondary)]` consistently

Exceptions (keep as-is):
- Login inputs: `pl-10` for icon — fine
- TicketFilters search: `pl-9 text-sm` for icon and context — fine
- Password inputs: `pr-10` for eye toggle — fine
- TicketDetail title: `text-xl font-bold py-1` context-specific — fine

### Labels

Standard label class (all form labels):

```
block text-sm font-medium text-[var(--text-primary)] mb-1.5
```

**Fixes:**
- Login.tsx: change `text-[var(--text-secondary)]` → `text-[var(--text-primary)]`
- TicketDetail.tsx sidebar labels: change `text-xs` → `text-sm`, `text-[var(--text-secondary)]` → `text-[var(--text-primary)]`
- TicketList.tsx modal labels: change `mb-1` → `mb-1.5`, `text-[var(--text-secondary)]` → `text-[var(--text-primary)]`

### Role Badges

Standardize on TopBar color scheme everywhere, add borders:

```
admin:   bg-red-500/15 text-red-400 border border-red-500/25
manager: bg-amber-500/15 text-amber-400 border border-amber-500/25
agent:   bg-blue-500/15 text-blue-400 border border-blue-500/25
```

Badge class: `inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium`

**TopBar.tsx:** change `text-[10px] font-semibold uppercase tracking-wider px-1.5` → standard badge class + add borders
**Users.tsx:** change purple/blue/gray → red/amber/blue scheme

### Status Badges

Standardize padding to `px-2 py-0.5` across StatusBadge.tsx and ApiKeys.tsx (currently StatusBadge uses `px-2.5`).

### Cards/Sections

Standard: `bg-[var(--bg-secondary)] border border-[var(--border)] rounded-xl`

**Fixes:**
- Dashboard loading cards: change `rounded-lg` → `rounded-xl`
- Login: keep `rounded-2xl` and shadow — it's a standalone page, intentionally elevated

### Spacing

Standard form gap: `space-y-4`
Standard section padding: `px-5 py-3` for headers, `p-5` for content

**Fixes:**
- TicketCreate.tsx: change `space-y-6` → `space-y-4`
- Groups.tsx detail panel: change `px-6 py-4` → `px-5 py-3` for headers, `p-5` for content

---

## Files Modified

### New Files
- `frontend/src/components/ui/Toggle.tsx`

### Modified Files
- `frontend/src/pages/admin/Users.tsx` — inline forms, Toggle, validation, empty/error states, role badge colors
- `frontend/src/pages/admin/Webhooks.tsx` — inline forms, Toggle, validation, empty/error states
- `frontend/src/pages/admin/ApiKeys.tsx` — inline forms, validation, empty/error states, status badge padding
- `frontend/src/pages/admin/Groups.tsx` — Toggle, validation audit, empty/error states, section spacing
- `frontend/src/pages/admin/SlaConfig.tsx` — validation audit, empty/error states, table cell padding
- `frontend/src/pages/TicketCreate.tsx` — validation audit, form spacing
- `frontend/src/pages/TicketList.tsx` — empty/error states audit, label styling
- `frontend/src/pages/TicketDetail.tsx` — empty/error states audit, label styling
- `frontend/src/pages/Dashboard.tsx` — error states audit, card border radius
- `frontend/src/pages/Login.tsx` — label color fix, input focus styles already correct
- `frontend/src/components/layout/TopBar.tsx` — Change Password dropdown panel, role badge standardization
- `frontend/src/components/tickets/TicketTable.tsx` — cell padding, header tracking, row borders, container bg
- `frontend/src/components/ui/StatusBadge.tsx` — badge padding standardization

### Unchanged
- `frontend/src/components/ui/Modal.tsx` — kept (not deleted)
