# Frontend Consistency Review — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Bring visual and behavioral consistency across all frontend pages — inline forms instead of modals, reusable Toggle, standardized validation, consistent states, and unified styling.

**Architecture:** Each task targets one concern area across all affected files, producing a single coherent commit. Tasks are ordered so foundational changes (shared components, styling) come first, then page-level refactors build on top.

**Tech Stack:** React 18, TypeScript, Tailwind CSS 3, TanStack Query, lucide-react

**Design doc:** `docs/plans/2026-02-08-frontend-consistency-review-design.md`

---

### Task 1: Create Toggle Component

Create the reusable Toggle UI component that later tasks will use.

**Files:**
- Create: `frontend/src/components/ui/Toggle.tsx`

**Step 1: Create the Toggle component**

```tsx
// frontend/src/components/ui/Toggle.tsx
interface ToggleProps {
  checked: boolean
  onChange: (checked: boolean) => void
  label?: string
  disabled?: boolean
}

export default function Toggle({ checked, onChange, label, disabled = false }: ToggleProps) {
  return (
    <div className="flex items-center gap-3">
      <label className={`relative inline-flex items-center ${disabled ? 'opacity-60 cursor-not-allowed' : 'cursor-pointer'}`}>
        <input
          type="checkbox"
          checked={checked}
          onChange={(e) => onChange(e.target.checked)}
          disabled={disabled}
          className="sr-only peer"
        />
        <div className="w-9 h-5 bg-[var(--bg-tertiary)] border border-[var(--border)] rounded-full peer peer-checked:bg-emerald-500 peer-checked:border-emerald-500 transition-colors duration-200 after:content-[''] after:absolute after:top-0.5 after:left-0.5 after:bg-white after:rounded-full after:h-4 after:w-4 after:transition-transform after:duration-200 peer-checked:after:translate-x-4" />
      </label>
      {label && <span className="text-sm text-[var(--text-primary)]">{label}</span>}
    </div>
  )
}
```

**Step 2: Verify TypeScript compiles**

Run: `cd frontend && npx tsc --noEmit`
Expected: no errors

**Step 3: Commit**

```
feat: add reusable Toggle UI component
```

---

### Task 2: Standardize StatusBadge and Role Badge Styling

Fix badge inconsistencies across the app. Standardize role colors (red/amber/blue), add borders to TopBar badges, fix StatusBadge padding.

**Files:**
- Modify: `frontend/src/components/ui/StatusBadge.tsx` — change `px-2.5` → `px-2`
- Modify: `frontend/src/components/layout/TopBar.tsx` — standardize role badge to `text-xs font-medium` with borders
- Modify: `frontend/src/pages/admin/Users.tsx` — change role colors from purple/blue/gray to red/amber/blue

**Step 1: Fix StatusBadge padding**

In `StatusBadge.tsx`, change the badge base class from `px-2.5` to `px-2`.

**Step 2: Standardize TopBar role badge**

In `TopBar.tsx`, update the `roleBadgeColor` function to return colors with borders:
```tsx
function roleBadgeColor(role: string): string {
  switch (role) {
    case 'admin':
      return 'bg-red-500/15 text-red-400 border border-red-500/25'
    case 'manager':
      return 'bg-amber-500/15 text-amber-400 border border-amber-500/25'
    default:
      return 'bg-blue-500/15 text-blue-400 border border-blue-500/25'
  }
}
```

Update the role badge `<span>` class from:
```
text-[10px] font-semibold uppercase tracking-wider rounded-full px-1.5 py-0.5 w-fit leading-tight ${roleBadgeColor(user.role)}
```
to:
```
inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${roleBadgeColor(user.role)}
```

**Step 3: Standardize Users.tsx role badges**

In `Users.tsx`, update `roleBadgeClasses`:
```tsx
const roleBadgeClasses: Record<UserRole, string> = {
  admin: 'bg-red-500/15 text-red-400 border border-red-500/25',
  manager: 'bg-amber-500/15 text-amber-400 border border-amber-500/25',
  agent: 'bg-blue-500/15 text-blue-400 border border-blue-500/25',
}
```

**Step 4: Verify TypeScript compiles**

Run: `cd frontend && npx tsc --noEmit`

**Step 5: Commit**

```
fix: standardize badge colors and padding across app
```

---

### Task 3: Standardize Table Styling

Fix TicketTable and SlaConfig table inconsistencies.

**Files:**
- Modify: `frontend/src/components/tickets/TicketTable.tsx`
- Modify: `frontend/src/pages/admin/SlaConfig.tsx`

**Step 1: Fix TicketTable**

In `TicketTable.tsx`:

1. Container (line ~95): Add `bg-[var(--bg-secondary)]` to the outer div class:
   - From: `border border-[var(--border)] rounded-xl overflow-hidden`
   - To: `bg-[var(--bg-secondary)] border border-[var(--border)] rounded-xl overflow-hidden`

2. Header cells (line ~117): Change `px-3` to `px-4`, remove `tracking-wider`:
   - From: `px-3 py-3 text-left text-xs font-medium text-[var(--text-secondary)] uppercase tracking-wider`
   - To: `px-4 py-3 text-left text-xs font-medium text-[var(--text-secondary)] uppercase`

3. Body container: Remove `divide-y divide-[var(--border)]` from `<tbody>`.

4. Each body row: Add `border-b border-[var(--border)]` to each `<tr>` class.

5. Body cells: Change `px-3` to `px-4` on all `<td>` elements.

**Step 2: Fix SlaConfig table cell padding**

In `SlaConfig.tsx`, change body cell padding from `py-4` to `py-3` on the `<td>` elements (lines ~182-210).

**Step 3: Verify TypeScript compiles**

Run: `cd frontend && npx tsc --noEmit`

**Step 4: Commit**

```
fix: standardize table cell padding and borders
```

---

### Task 4: Standardize Input Focus Styles

Add `focus:border-[var(--accent)] transition-colors duration-200` to all form inputs that are missing it. Drop `/50` placeholder opacity where used.

**Files:**
- Modify: `frontend/src/pages/admin/Users.tsx`
- Modify: `frontend/src/pages/admin/Webhooks.tsx`
- Modify: `frontend/src/pages/admin/ApiKeys.tsx`
- Modify: `frontend/src/pages/admin/Groups.tsx`
- Modify: `frontend/src/pages/admin/SlaConfig.tsx`
- Modify: `frontend/src/pages/TicketCreate.tsx`
- Modify: `frontend/src/components/layout/TopBar.tsx`
- Modify: `frontend/src/components/tickets/TicketFilters.tsx`

The standard input class should be:
```
w-full bg-[var(--bg-tertiary)] border border-[var(--border)] text-[var(--text-primary)] rounded-lg px-3 py-2 placeholder:text-[var(--text-secondary)] focus:outline-none focus:ring-2 focus:ring-[var(--accent)]/50 focus:border-[var(--accent)] transition-colors duration-200
```

**Step 1: Update inputs in each file**

For each file, find all `<input>` and `<textarea>` elements with form input styling. For each:
- If missing `focus:border-[var(--accent)]`, add it
- If missing `transition-colors duration-200`, add it
- If has `placeholder:text-[var(--text-secondary)]/50`, change to `placeholder:text-[var(--text-secondary)]` (affects TicketFilters.tsx, Login.tsx)

Files with inputs to update (Login.tsx already correct, skip):
- Users.tsx: ~6 inputs (create + edit forms)
- Webhooks.tsx: ~6 inputs (create + edit forms)
- ApiKeys.tsx: ~1 input (name field)
- Groups.tsx: ~4 inputs (create group, add member, edit group)
- SlaConfig.tsx: ~8 number inputs
- TicketCreate.tsx: ~1 text input (title)
- TopBar.tsx: ~3 password inputs
- TicketFilters.tsx: search input — fix placeholder opacity

Leave contextual exceptions alone (Login `pl-10`, TicketFilters `pl-9 text-sm`, password `pr-10`, TicketDetail title `py-1`).

**Step 2: Verify TypeScript compiles**

Run: `cd frontend && npx tsc --noEmit`

**Step 3: Commit**

```
fix: standardize input focus styles and placeholder opacity
```

---

### Task 5: Standardize Labels, Cards, and Spacing

Fix label colors/sizes, card border radius, and form spacing inconsistencies.

**Files:**
- Modify: `frontend/src/pages/Login.tsx`
- Modify: `frontend/src/pages/TicketCreate.tsx`
- Modify: `frontend/src/pages/TicketList.tsx`
- Modify: `frontend/src/pages/TicketDetail.tsx`
- Modify: `frontend/src/pages/Dashboard.tsx`
- Modify: `frontend/src/pages/admin/Groups.tsx`

**Step 1: Fix Login.tsx labels**

Change label class (lines ~65, ~89) from `text-[var(--text-secondary)]` to `text-[var(--text-primary)]`. Add `mb-1.5` if not present.

**Step 2: Fix TicketCreate.tsx form spacing**

Change `space-y-6` to `space-y-4` on the form content container (line ~116).

**Step 3: Fix TicketList.tsx label styling**

In the bulk action section's dropdown labels (lines ~418, ~431), change:
- `text-[var(--text-secondary)]` → `text-[var(--text-primary)]`
- `mb-1` → `mb-1.5`

**Step 4: Fix TicketDetail.tsx sidebar labels**

In the `SidebarField` component (line ~661), the labels use `text-xs text-[var(--text-secondary)]`. Change to `text-sm text-[var(--text-primary)]`. Keep `mb-1.5` (add if missing).

**Step 5: Fix Dashboard.tsx card border radius**

In loading state cards (line ~55), change `rounded-lg` to `rounded-xl`.

**Step 6: Fix Groups.tsx detail panel spacing**

In `GroupDetailPanel`, change section header padding from `px-6 py-4` to `px-5 py-3`, and content padding from `p-6`/`px-6` to `p-5`/`px-5`.

**Step 7: Verify TypeScript compiles**

Run: `cd frontend && npx tsc --noEmit`

**Step 8: Commit**

```
fix: standardize labels, card corners, and section spacing
```

---

### Task 6: Consistent Empty, Loading, and Error States

Audit every page and ensure they all use the same loading/empty/error patterns.

**Files:**
- Modify: `frontend/src/pages/Dashboard.tsx`
- Modify: `frontend/src/pages/TicketList.tsx`
- Modify: `frontend/src/pages/TicketCreate.tsx`
- Modify: `frontend/src/pages/TicketDetail.tsx`
- Modify: `frontend/src/pages/admin/Webhooks.tsx`
- Modify: `frontend/src/pages/admin/ApiKeys.tsx`
- Modify: `frontend/src/pages/admin/Groups.tsx`
- Modify: `frontend/src/pages/admin/SlaConfig.tsx`

**Step 1: Audit and fix each page**

For each page that fetches data, ensure it has all three states:

**Loading pattern** (unless Dashboard which keeps per-card spinners):
```tsx
if (isLoading) {
  return (
    <div>
      <PageHeader title="[Page]" description="[Description]." />
      <div className="flex items-center justify-center py-20">
        <Spinner size="lg" />
      </div>
    </div>
  )
}
```

**Error pattern:**
```tsx
if (isError) {
  return (
    <div>
      <PageHeader title="[Page]" description="[Description]." />
      <EmptyState
        icon={<[Icon] size={40} />}
        title="Failed to load [things]"
        description="An error occurred while fetching data. Please try again."
      />
    </div>
  )
}
```

**Empty pattern** (for list pages):
```tsx
{items.length === 0 ? (
  <EmptyState
    icon={<[Icon] size={40} />}
    title="No [things] yet"
    description="[Guidance text]."
    action={
      <Button variant="primary" size="sm" onClick={openCreate}>
        <Plus size={16} />
        Add [Thing]
      </Button>
    }
  />
) : (
  /* table/list */
)}
```

Pages to check — add any missing states:
- Dashboard.tsx — add error state (keep per-card loading)
- TicketList.tsx — verify loading, error, empty all present (empty should have filtered variant)
- TicketCreate.tsx — verify loading for groups/users dropdowns if applicable
- TicketDetail.tsx — verify loading, error, not-found states
- Webhooks.tsx — add loading, error, empty states if missing
- ApiKeys.tsx — add loading, error, empty states if missing
- Groups.tsx — add loading, error, empty states if missing
- SlaConfig.tsx — add loading, error states if missing

Ensure each page imports `Spinner`, `EmptyState`, and `PageHeader` as needed.

**Step 2: Verify TypeScript compiles**

Run: `cd frontend && npx tsc --noEmit`

**Step 3: Commit**

```
fix: add consistent loading, error, and empty states to all pages
```

---

### Task 7: Standardize Form Validation — Inline Errors

Convert all form validation from toast-based to inline field errors. Add required field indicators.

**Files:**
- Modify: `frontend/src/pages/admin/Users.tsx`
- Modify: `frontend/src/pages/admin/Webhooks.tsx`
- Modify: `frontend/src/pages/admin/ApiKeys.tsx`
- Modify: `frontend/src/pages/admin/Groups.tsx`
- Modify: `frontend/src/pages/TicketCreate.tsx`
- Modify: `frontend/src/components/layout/TopBar.tsx`

**Step 1: Implement validation pattern**

For each page with forms, apply this pattern:

1. Add a `formErrors` state: `const [formErrors, setFormErrors] = useState<Record<string, string>>({})`

2. In the submit handler, build errors object instead of toast:
```tsx
const errors: Record<string, string> = {}
if (!form.field.trim()) errors.field = 'Field is required.'
// ... more validations
if (Object.keys(errors).length > 0) {
  setFormErrors(errors)
  return
}
setFormErrors({})
```

3. Below each input, add inline error:
```tsx
{formErrors.field && <p className="text-sm text-red-400 mt-1">{formErrors.field}</p>}
```

4. Add required indicators to labels:
```tsx
<label className="block text-sm font-medium text-[var(--text-primary)] mb-1.5">
  Field Name <span className="text-red-400">*</span>
</label>
```

5. Keep `toast.error()` only for API/server errors in the catch block.

6. Clear formErrors when form is opened/reset.

**Forms to update:**
- Users.tsx — create form: username, email, full_name, password, role required. Edit form: email, full_name, role required.
- Webhooks.tsx — create form: name, url, secret, events required. Edit form: name, url required.
- ApiKeys.tsx — create form: name required.
- Groups.tsx — create form: name required.
- TicketCreate.tsx — title, description, priority, assigned_group_id required.
- TopBar.tsx — change password form: current, new (min 5 chars), confirm (must match) required.

**Step 2: Verify TypeScript compiles**

Run: `cd frontend && npx tsc --noEmit`

**Step 3: Commit**

```
feat: convert form validation to inline field errors with required indicators
```

---

### Task 8: Replace Users.tsx Modals with Inline Forms + Toggle

The biggest page refactor. Remove both modals, replace with inline expanding forms. Replace the ad-hoc toggle with the Toggle component.

**Files:**
- Modify: `frontend/src/pages/admin/Users.tsx`

**Step 1: Refactor state management**

Replace modal state with inline form state:
- Remove `showCreateModal` state → add `showCreateForm: boolean`
- Remove `editingUser` state → add `editingUserId: string | null`
- Keep `createForm` and `editForm` state as-is
- Remove Modal import, add Toggle import

**Step 2: Replace Create User modal with inline form**

Replace the `<Modal>` for create with an inline card above the table:
```tsx
{showCreateForm && (
  <div className="bg-[var(--bg-secondary)] border border-[var(--border)] rounded-xl p-5 mb-4">
    <h3 className="text-sm font-semibold text-[var(--text-primary)] mb-4">Add User</h3>
    <form onSubmit={handleCreate}>
      <div className="space-y-4">
        {/* Same form fields as before */}
      </div>
      <div className="flex items-center justify-end gap-3 mt-4">
        <Button variant="secondary" size="sm" onClick={() => setShowCreateForm(false)}>Cancel</Button>
        <Button variant="primary" size="sm" loading={createUser.isPending} type="submit">Create User</Button>
      </div>
    </form>
  </div>
)}
```

**Step 3: Replace Edit User modal with inline row expansion**

Replace `<EditUserModal>` with inline editing. When a row is clicked, set `editingUserId` to that user's ID. Render the edit form as a `<tr>` with a single `<td colSpan={6}>` below the clicked row:

```tsx
{users.map((user) => (
  <React.Fragment key={user.id}>
    <tr onClick={() => openEditRow(user)} ...>
      {/* existing row cells */}
    </tr>
    {editingUserId === user.id && (
      <tr>
        <td colSpan={6} className="px-4 py-4 bg-[var(--bg-tertiary)]">
          <EditUserInlineForm user={user} onClose={() => setEditingUserId(null)} />
        </td>
      </tr>
    )}
  </React.Fragment>
))}
```

Move the `EditUserModal` component to `EditUserInlineForm` — same logic, just renders a form div instead of a Modal. Include the Toggle component for is_active. Include the reset password field.

**Step 4: Replace toggle in edit form**

Replace the custom sr-only peer checkbox with:
```tsx
<Toggle
  checked={editForm.is_active}
  onChange={(checked) => setEditForm((f) => ({ ...f, is_active: checked }))}
  label="Active"
/>
```

**Step 5: Remove Modal import**

Remove the `Modal` import since it's no longer used.

**Step 6: Verify TypeScript compiles**

Run: `cd frontend && npx tsc --noEmit`

**Step 7: Commit**

```
refactor: replace Users page modals with inline forms and Toggle
```

---

### Task 9: Replace Webhooks.tsx Modals with Inline Forms + Toggle

Same pattern as Users — inline create form above table, inline edit below row, Toggle for is_active.

**Files:**
- Modify: `frontend/src/pages/admin/Webhooks.tsx`

**Step 1: Refactor state management**

- Remove `showCreateModal` → `showCreateForm: boolean`
- Remove `editingWebhook` → `editingWebhookId: string | null`
- Remove Modal import, add Toggle import

**Step 2: Replace Create Webhook modal with inline form**

Same pattern as Users Task 8 — inline card above table with all create form fields (name, url, secret, events).

**Step 3: Replace Edit Webhook modal with inline row expansion**

Convert `EditWebhookModal` to `EditWebhookInlineForm`. Render below clicked row in a `<tr><td colSpan={N}>`.

**Step 4: Replace toggle**

In `WebhookRow`, replace the custom toggle button (lines ~402-413) with:
```tsx
<Toggle
  checked={webhook.is_active}
  onChange={(checked) => handleToggleActive(webhook, checked)}
/>
```

And in the inline edit form, use Toggle for is_active.

**Step 5: Remove Modal import**

**Step 6: Verify TypeScript compiles**

Run: `cd frontend && npx tsc --noEmit`

**Step 7: Commit**

```
refactor: replace Webhooks page modals with inline forms and Toggle
```

---

### Task 10: Replace ApiKeys.tsx Modal with Inline Form

ApiKeys only has a create modal (no edit). Replace with inline form above table.

**Files:**
- Modify: `frontend/src/pages/admin/ApiKeys.tsx`

**Step 1: Refactor state management**

- Remove `showCreateModal` → `showCreateForm: boolean`
- Remove Modal import
- Keep the `createdKey` state for showing the generated key inline

**Step 2: Replace Create API Key modal with inline form**

Inline card above table. When a key is created, show the full key inline in the same card (with copy button and warning). The "Done" button collapses the form.

**Step 3: Remove Modal import**

**Step 4: Verify TypeScript compiles**

Run: `cd frontend && npx tsc --noEmit`

**Step 5: Commit**

```
refactor: replace ApiKeys page modal with inline form
```

---

### Task 11: Replace Groups.tsx Checkbox with Toggle

Groups already uses a side panel (no modal to remove). Just replace the is_lead checkbox.

**Files:**
- Modify: `frontend/src/pages/admin/Groups.tsx`

**Step 1: Replace is_lead checkbox with Toggle**

In the add member section and member list, replace the plain checkbox for `is_lead` with:
```tsx
<Toggle
  checked={isLead}
  onChange={setIsLead}
  label="Group Lead"
/>
```

Import Toggle component.

**Step 2: Verify TypeScript compiles**

Run: `cd frontend && npx tsc --noEmit`

**Step 3: Commit**

```
refactor: replace Groups is_lead checkbox with Toggle component
```

---

### Task 12: Replace TopBar Change Password Modal with Dropdown Panel

Convert the modal to an anchored dropdown panel below the Lock icon.

**Files:**
- Modify: `frontend/src/components/layout/TopBar.tsx`

**Step 1: Replace ChangePasswordModal with dropdown panel**

Replace the `<ChangePasswordModal>` component with a `<ChangePasswordPanel>` that renders as an absolutely positioned dropdown:

```tsx
function ChangePasswordPanel({ onClose }: { onClose: () => void }) {
  // ... same form logic as before ...
  return (
    <div className="absolute right-0 top-full mt-2 w-80 bg-[var(--bg-secondary)] border border-[var(--border)] rounded-xl shadow-xl z-50 p-5">
      <h3 className="text-sm font-semibold text-[var(--text-primary)] mb-4">Change Password</h3>
      {/* same form fields */}
      <div className="flex items-center justify-end gap-3 mt-4">
        <Button variant="secondary" size="sm" onClick={onClose}>Cancel</Button>
        <Button variant="primary" size="sm" ...>Change Password</Button>
      </div>
    </div>
  )
}
```

Wrap the Lock button + panel in a `relative` container. Add click-outside handler using `useRef` + `useEffect` with mousedown event.

**Step 2: Remove Modal import**

Remove the Modal and Button imports if Button is still needed (it will be for the panel buttons — keep it).

**Step 3: Verify TypeScript compiles**

Run: `cd frontend && npx tsc --noEmit`

**Step 4: Commit**

```
refactor: replace TopBar password modal with dropdown panel
```

---

### Task 13: Final Build Verification

**Step 1: Full TypeScript check**

Run: `cd frontend && npx tsc --noEmit`

**Step 2: Docker build**

Run: `docker compose up --build -d`
Expected: clean build, all containers running

**Step 3: Commit design doc**

```
git add docs/plans/2026-02-08-frontend-consistency-review-design.md docs/plans/2026-02-08-frontend-consistency-implementation-plan.md
git commit -m "docs: add frontend consistency review design and implementation plan"
```
