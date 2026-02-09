import React, { useState } from 'react'
import { Plus, Users as UsersIcon } from 'lucide-react'
import PageHeader from '@/components/layout/PageHeader'
import Button from '@/components/ui/Button'
import Dropdown from '@/components/ui/Dropdown'
import Toggle from '@/components/ui/Toggle'
import Spinner from '@/components/ui/Spinner'
import EmptyState from '@/components/ui/EmptyState'
import { useToast } from '@/components/ui/Toast'
import { useUsers, useCreateUser, useUpdateUser } from '@/hooks/useUsers'
import { relativeTime } from '@/utils/format'
import type { User, UserRole } from '@/types'

// ─── Constants ──────────────────────────────────────────────────────────────

const roleOptions = [
  { value: 'admin', label: 'Admin' },
  { value: 'manager', label: 'Manager' },
  { value: 'agent', label: 'Agent' },
]

const roleBadgeClasses: Record<UserRole, string> = {
  admin: 'bg-red-500/15 text-red-400 border border-red-500/25',
  manager: 'bg-amber-500/15 text-amber-400 border border-amber-500/25',
  agent: 'bg-blue-500/15 text-blue-400 border border-blue-500/25',
}

// ─── Users Page ─────────────────────────────────────────────────────────────

export default function Users() {
  const toast = useToast()
  const { data, isLoading, isError } = useUsers()
  const createUser = useCreateUser()

  // ─── Inline form state ────────────────────────────────────────────────────
  const [showCreateForm, setShowCreateForm] = useState(false)
  const [editingUserId, setEditingUserId] = useState<string | null>(null)

  // ─── Create form state ──────────────────────────────────────────────────
  const [createForm, setCreateForm] = useState({
    username: '',
    email: '',
    full_name: '',
    password: '',
    role: '' as string,
  })
  const [createFormErrors, setCreateFormErrors] = useState<Record<string, string>>({})

  // ─── Edit form state ───────────────────────────────────────────────────
  const [editForm, setEditForm] = useState({
    email: '',
    full_name: '',
    role: '' as string,
    is_active: true,
    password: '',
  })

  // ─── Handlers ──────────────────────────────────────────────────────────

  function openCreateForm() {
    setCreateForm({ username: '', email: '', full_name: '', password: '', role: '' })
    setCreateFormErrors({})
    setShowCreateForm(true)
  }

  function openEditRow(user: User) {
    if (editingUserId === user.id) {
      setEditingUserId(null)
      return
    }
    setEditingUserId(user.id)
    setEditForm({
      email: user.email,
      full_name: user.full_name,
      role: user.role,
      is_active: user.is_active,
      password: '',
    })
  }

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault()

    const errors: Record<string, string> = {}
    if (!createForm.username.trim()) errors.username = 'Username is required.'
    if (!createForm.email.trim()) errors.email = 'Email is required.'
    if (!createForm.full_name.trim()) errors.full_name = 'Full name is required.'
    if (!createForm.password.trim()) errors.password = 'Password is required.'
    if (!createForm.role) errors.role = 'Role is required.'
    if (Object.keys(errors).length > 0) {
      setCreateFormErrors(errors)
      return
    }
    setCreateFormErrors({})

    try {
      await createUser.mutateAsync({
        username: createForm.username.trim(),
        email: createForm.email.trim(),
        full_name: createForm.full_name.trim(),
        password: createForm.password,
        role: createForm.role as UserRole,
      })
      toast.success('User created successfully.')
      setShowCreateForm(false)
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Failed to create user.'
      toast.error(message)
    }
  }

  const users = data?.items ?? []

  // ─── Loading state ─────────────────────────────────────────────────────

  if (isLoading) {
    return (
      <div>
        <PageHeader title="Users" description="Manage user accounts and roles." />
        <div className="flex items-center justify-center py-20">
          <Spinner size="lg" />
        </div>
      </div>
    )
  }

  // ─── Error state ───────────────────────────────────────────────────────

  if (isError) {
    return (
      <div>
        <PageHeader title="Users" description="Manage user accounts and roles." />
        <EmptyState
          icon={<UsersIcon size={40} />}
          title="Failed to load users"
          description="An error occurred while fetching user data. Please try again."
        />
      </div>
    )
  }

  // ─── Render ────────────────────────────────────────────────────────────

  return (
    <div>
      <PageHeader
        title="Users"
        description="Manage user accounts and roles."
        actions={
          <Button variant="primary" size="sm" onClick={openCreateForm}>
            <Plus size={16} />
            Add User
          </Button>
        }
      />

      {/* ─── Inline Create User Form ──────────────────────────────────────── */}
      {showCreateForm && (
        <form onSubmit={handleCreate}>
          <div className="bg-[var(--bg-secondary)] border border-[var(--border)] rounded-xl p-5 mb-4">
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-[var(--text-primary)] mb-1.5">
                  Username <span className="text-red-400">*</span>
                </label>
                <input
                  type="text"
                  value={createForm.username}
                  onChange={(e) => setCreateForm((f) => ({ ...f, username: e.target.value }))}
                  placeholder="Enter username"
                  className="w-full bg-[var(--bg-tertiary)] border border-[var(--border)] text-[var(--text-primary)] rounded-lg px-3 py-2 placeholder:text-[var(--text-secondary)] focus:outline-none focus:ring-2 focus:ring-[var(--accent)]/50 focus:border-[var(--accent)] transition-colors duration-200"
                />
                {createFormErrors.username && <p className="text-sm text-red-400 mt-1">{createFormErrors.username}</p>}
              </div>
              <div>
                <label className="block text-sm font-medium text-[var(--text-primary)] mb-1.5">
                  Email <span className="text-red-400">*</span>
                </label>
                <input
                  type="email"
                  value={createForm.email}
                  onChange={(e) => setCreateForm((f) => ({ ...f, email: e.target.value }))}
                  placeholder="Enter email address"
                  className="w-full bg-[var(--bg-tertiary)] border border-[var(--border)] text-[var(--text-primary)] rounded-lg px-3 py-2 placeholder:text-[var(--text-secondary)] focus:outline-none focus:ring-2 focus:ring-[var(--accent)]/50 focus:border-[var(--accent)] transition-colors duration-200"
                />
                {createFormErrors.email && <p className="text-sm text-red-400 mt-1">{createFormErrors.email}</p>}
              </div>
              <div>
                <label className="block text-sm font-medium text-[var(--text-primary)] mb-1.5">
                  Full Name <span className="text-red-400">*</span>
                </label>
                <input
                  type="text"
                  value={createForm.full_name}
                  onChange={(e) => setCreateForm((f) => ({ ...f, full_name: e.target.value }))}
                  placeholder="Enter full name"
                  className="w-full bg-[var(--bg-tertiary)] border border-[var(--border)] text-[var(--text-primary)] rounded-lg px-3 py-2 placeholder:text-[var(--text-secondary)] focus:outline-none focus:ring-2 focus:ring-[var(--accent)]/50 focus:border-[var(--accent)] transition-colors duration-200"
                />
                {createFormErrors.full_name && <p className="text-sm text-red-400 mt-1">{createFormErrors.full_name}</p>}
              </div>
              <div>
                <label className="block text-sm font-medium text-[var(--text-primary)] mb-1.5">
                  Password <span className="text-red-400">*</span>
                </label>
                <input
                  type="password"
                  value={createForm.password}
                  onChange={(e) => setCreateForm((f) => ({ ...f, password: e.target.value }))}
                  placeholder="Enter password"
                  className="w-full bg-[var(--bg-tertiary)] border border-[var(--border)] text-[var(--text-primary)] rounded-lg px-3 py-2 placeholder:text-[var(--text-secondary)] focus:outline-none focus:ring-2 focus:ring-[var(--accent)]/50 focus:border-[var(--accent)] transition-colors duration-200"
                />
                {createFormErrors.password && <p className="text-sm text-red-400 mt-1">{createFormErrors.password}</p>}
              </div>
              <div>
                <label className="block text-sm font-medium text-[var(--text-primary)] mb-1.5">
                  Role <span className="text-red-400">*</span>
                </label>
                <Dropdown
                  value={createForm.role}
                  onChange={(value) => setCreateForm((f) => ({ ...f, role: value }))}
                  options={roleOptions}
                  placeholder="Select role"
                />
                {createFormErrors.role && <p className="text-sm text-red-400 mt-1">{createFormErrors.role}</p>}
              </div>
            </div>
            <div className="flex items-center justify-end gap-3 mt-5 pt-4 border-t border-[var(--border)]">
              <Button variant="secondary" onClick={() => setShowCreateForm(false)}>
                Cancel
              </Button>
              <Button variant="primary" loading={createUser.isPending} type="submit">
                Create User
              </Button>
            </div>
          </div>
        </form>
      )}

      {users.length === 0 ? (
        <EmptyState
          icon={<UsersIcon size={40} />}
          title="No users yet"
          description="Create your first user to get started."
          action={
            <Button variant="primary" size="sm" onClick={openCreateForm}>
              <Plus size={16} />
              Add User
            </Button>
          }
        />
      ) : (
        <div className="bg-[var(--bg-secondary)] border border-[var(--border)] rounded-xl overflow-hidden">
          <table className="w-full">
            <thead>
              <tr className="border-b border-[var(--border)]">
                <th className="text-left text-xs uppercase text-[var(--text-secondary)] font-medium px-4 py-3">Full Name</th>
                <th className="text-left text-xs uppercase text-[var(--text-secondary)] font-medium px-4 py-3">Username</th>
                <th className="text-left text-xs uppercase text-[var(--text-secondary)] font-medium px-4 py-3">Email</th>
                <th className="text-left text-xs uppercase text-[var(--text-secondary)] font-medium px-4 py-3">Role</th>
                <th className="text-left text-xs uppercase text-[var(--text-secondary)] font-medium px-4 py-3">Status</th>
                <th className="text-left text-xs uppercase text-[var(--text-secondary)] font-medium px-4 py-3">Created</th>
              </tr>
            </thead>
            <tbody>
              {users.map((user) => (
                <React.Fragment key={user.id}>
                  <tr
                    onClick={() => openEditRow(user)}
                    className="border-b border-[var(--border)] hover:bg-[var(--bg-tertiary)] cursor-pointer transition-colors duration-150"
                  >
                    <td className="px-4 py-3 text-sm text-[var(--text-primary)] font-medium">
                      {user.full_name}
                    </td>
                    <td className="px-4 py-3 text-sm text-[var(--text-secondary)]">
                      {user.username}
                    </td>
                    <td className="px-4 py-3 text-sm text-[var(--text-secondary)]">
                      {user.email}
                    </td>
                    <td className="px-4 py-3 text-sm">
                      <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${roleBadgeClasses[user.role]}`}>
                        {user.role.charAt(0).toUpperCase() + user.role.slice(1)}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-sm">
                      <span className="inline-flex items-center gap-1.5 text-xs">
                        <span className={`w-2 h-2 rounded-full ${user.is_active ? 'bg-emerald-400' : 'bg-red-400'}`} />
                        <span className={user.is_active ? 'text-emerald-400' : 'text-red-400'}>
                          {user.is_active ? 'Active' : 'Inactive'}
                        </span>
                      </span>
                    </td>
                    <td className="px-4 py-3 text-sm text-[var(--text-secondary)]">
                      {relativeTime(user.created_at)}
                    </td>
                  </tr>
                  {editingUserId === user.id && (
                    <tr>
                      <td colSpan={6} className="bg-[var(--bg-tertiary)]">
                        <EditUserInlineForm
                          user={user}
                          editForm={editForm}
                          setEditForm={setEditForm}
                          onClose={() => setEditingUserId(null)}
                        />
                      </td>
                    </tr>
                  )}
                </React.Fragment>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

// ─── Edit User Inline Form (separate component for hook rules) ──────────────

function EditUserInlineForm({
  user,
  editForm,
  setEditForm,
  onClose,
}: {
  user: User
  editForm: { email: string; full_name: string; role: string; is_active: boolean; password: string }
  setEditForm: React.Dispatch<React.SetStateAction<{ email: string; full_name: string; role: string; is_active: boolean; password: string }>>
  onClose: () => void
}) {
  const toast = useToast()
  const updateUser = useUpdateUser(user.id)
  const [formErrors, setFormErrors] = useState<Record<string, string>>({})

  async function handleUpdate(e: React.FormEvent) {
    e.preventDefault()

    const errors: Record<string, string> = {}
    if (!editForm.email.trim()) errors.email = 'Email is required.'
    if (!editForm.full_name.trim()) errors.full_name = 'Full name is required.'
    if (!editForm.role) errors.role = 'Role is required.'
    if (Object.keys(errors).length > 0) {
      setFormErrors(errors)
      return
    }
    setFormErrors({})

    try {
      const payload: Record<string, unknown> = {
        email: editForm.email.trim(),
        full_name: editForm.full_name.trim(),
        role: editForm.role as UserRole,
        is_active: editForm.is_active,
      }
      if (editForm.password.trim()) {
        payload.password = editForm.password
      }
      await updateUser.mutateAsync(payload as import('@/types').UserUpdate)
      toast.success('User updated successfully.')
      onClose()
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Failed to update user.'
      toast.error(message)
    }
  }

  return (
    <form onSubmit={handleUpdate}>
      <div className="p-5">
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-[var(--text-primary)] mb-1.5">
              Username
            </label>
            <input
              type="text"
              value={user.username}
              disabled
              className="w-full bg-[var(--bg-tertiary)] border border-[var(--border)] text-[var(--text-secondary)] rounded-lg px-3 py-2 opacity-60 cursor-not-allowed"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-[var(--text-primary)] mb-1.5">
              Email <span className="text-red-400">*</span>
            </label>
            <input
              type="email"
              value={editForm.email}
              onChange={(e) => setEditForm((f) => ({ ...f, email: e.target.value }))}
              placeholder="Enter email address"
              className="w-full bg-[var(--bg-tertiary)] border border-[var(--border)] text-[var(--text-primary)] rounded-lg px-3 py-2 placeholder:text-[var(--text-secondary)] focus:outline-none focus:ring-2 focus:ring-[var(--accent)]/50 focus:border-[var(--accent)] transition-colors duration-200"
            />
            {formErrors.email && <p className="text-sm text-red-400 mt-1">{formErrors.email}</p>}
          </div>
          <div>
            <label className="block text-sm font-medium text-[var(--text-primary)] mb-1.5">
              Full Name <span className="text-red-400">*</span>
            </label>
            <input
              type="text"
              value={editForm.full_name}
              onChange={(e) => setEditForm((f) => ({ ...f, full_name: e.target.value }))}
              placeholder="Enter full name"
              className="w-full bg-[var(--bg-tertiary)] border border-[var(--border)] text-[var(--text-primary)] rounded-lg px-3 py-2 placeholder:text-[var(--text-secondary)] focus:outline-none focus:ring-2 focus:ring-[var(--accent)]/50 focus:border-[var(--accent)] transition-colors duration-200"
            />
            {formErrors.full_name && <p className="text-sm text-red-400 mt-1">{formErrors.full_name}</p>}
          </div>
          <div>
            <label className="block text-sm font-medium text-[var(--text-primary)] mb-1.5">
              Role <span className="text-red-400">*</span>
            </label>
            <Dropdown
              value={editForm.role}
              onChange={(value) => setEditForm((f) => ({ ...f, role: value }))}
              options={roleOptions}
              placeholder="Select role"
            />
            {formErrors.role && <p className="text-sm text-red-400 mt-1">{formErrors.role}</p>}
          </div>
          <Toggle
            checked={editForm.is_active}
            onChange={(checked) => setEditForm((f) => ({ ...f, is_active: checked }))}
            label="Active"
          />
          <div>
            <label className="block text-sm font-medium text-[var(--text-primary)] mb-1.5">
              Reset Password
            </label>
            <input
              type="password"
              value={editForm.password}
              onChange={(e) => setEditForm((f) => ({ ...f, password: e.target.value }))}
              placeholder="Leave blank to keep current password"
              className="w-full bg-[var(--bg-tertiary)] border border-[var(--border)] text-[var(--text-primary)] rounded-lg px-3 py-2 placeholder:text-[var(--text-secondary)] focus:outline-none focus:ring-2 focus:ring-[var(--accent)]/50 focus:border-[var(--accent)] transition-colors duration-200"
            />
          </div>
        </div>
        <div className="flex items-center justify-end gap-3 mt-5 pt-4 border-t border-[var(--border)]">
          <Button variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button variant="primary" loading={updateUser.isPending} type="submit">
            Save Changes
          </Button>
        </div>
      </div>
    </form>
  )
}
