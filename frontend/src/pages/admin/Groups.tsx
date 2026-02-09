import { useState } from 'react'
import { Plus, Users as UsersIcon, UserPlus, Trash2, Shield, X, Edit } from 'lucide-react'
import PageHeader from '@/components/layout/PageHeader'
import Button from '@/components/ui/Button'
import Toggle from '@/components/ui/Toggle'
import Dropdown from '@/components/ui/Dropdown'
import Spinner from '@/components/ui/Spinner'
import EmptyState from '@/components/ui/EmptyState'
import { useToast } from '@/components/ui/Toast'
import {
  useGroups,
  useGroup,
  useCreateGroup,
  useUpdateGroup,
  useAddGroupMember,
  useRemoveGroupMember,
} from '@/hooks/useGroups'
import { useUsers } from '@/hooks/useUsers'
import { relativeTime, shortDate } from '@/utils/format'

// ─── Groups Page ────────────────────────────────────────────────────────────

export default function Groups() {
  const toast = useToast()
  const { data, isLoading, isError } = useGroups()
  const createGroup = useCreateGroup()

  // ─── State ──────────────────────────────────────────────────────────────
  const [showCreateForm, setShowCreateForm] = useState(false)
  const [selectedGroupId, setSelectedGroupId] = useState<string | null>(null)
  const [createForm, setCreateForm] = useState({ name: '', description: '' })
  const [createFormErrors, setCreateFormErrors] = useState<Record<string, string>>({})

  // ─── Handlers ──────────────────────────────────────────────────────────

  function openCreateForm() {
    setCreateForm({ name: '', description: '' })
    setCreateFormErrors({})
    setShowCreateForm(true)
  }

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault()

    const errors: Record<string, string> = {}
    if (!createForm.name.trim()) errors.name = 'Group name is required.'
    if (Object.keys(errors).length > 0) {
      setCreateFormErrors(errors)
      return
    }
    setCreateFormErrors({})

    try {
      await createGroup.mutateAsync({
        name: createForm.name.trim(),
        description: createForm.description.trim() || undefined,
      })
      toast.success('Group created successfully.')
      setShowCreateForm(false)
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Failed to create group.'
      toast.error(message)
    }
  }

  const groups = data?.items ?? []

  // ─── Loading state ─────────────────────────────────────────────────────

  if (isLoading) {
    return (
      <div>
        <PageHeader title="Groups" description="Manage assignment groups and their members." />
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
        <PageHeader title="Groups" description="Manage assignment groups and their members." />
        <EmptyState
          icon={<UsersIcon size={40} />}
          title="Failed to load groups"
          description="An error occurred while fetching group data. Please try again."
        />
      </div>
    )
  }

  // ─── Render ────────────────────────────────────────────────────────────

  return (
    <div>
      <PageHeader
        title="Groups"
        description="Manage assignment groups and their members."
        actions={
          <Button variant="primary" size="sm" onClick={openCreateForm}>
            <Plus size={16} />
            Add Group
          </Button>
        }
      />

      {/* ─── Inline Create Group Form ───────────────────────────────────────── */}
      {showCreateForm && (
        <div className="bg-[var(--bg-secondary)] border border-[var(--border)] rounded-xl p-5 mb-4">
          <form onSubmit={handleCreate}>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-[var(--text-primary)] mb-1.5">
                  Name <span className="text-red-400">*</span>
                </label>
                <input
                  type="text"
                  value={createForm.name}
                  onChange={(e) => setCreateForm((f) => ({ ...f, name: e.target.value }))}
                  placeholder="Enter group name"
                  className="w-full bg-[var(--bg-tertiary)] border border-[var(--border)] text-[var(--text-primary)] rounded-lg px-3 py-2 placeholder:text-[var(--text-secondary)] focus:outline-none focus:ring-2 focus:ring-[var(--accent)]/50 focus:border-[var(--accent)] transition-colors duration-200"
                />
                {createFormErrors.name && <p className="text-sm text-red-400 mt-1">{createFormErrors.name}</p>}
              </div>
              <div>
                <label className="block text-sm font-medium text-[var(--text-primary)] mb-1.5">
                  Description
                </label>
                <textarea
                  value={createForm.description}
                  onChange={(e) => setCreateForm((f) => ({ ...f, description: e.target.value }))}
                  placeholder="Enter group description (optional)"
                  rows={3}
                  className="w-full bg-[var(--bg-tertiary)] border border-[var(--border)] text-[var(--text-primary)] rounded-lg px-3 py-2 placeholder:text-[var(--text-secondary)] focus:outline-none focus:ring-2 focus:ring-[var(--accent)]/50 focus:border-[var(--accent)] transition-colors duration-200 resize-none"
                />
              </div>
            </div>
            <div className="flex items-center justify-end gap-2 mt-4">
              <Button type="button" variant="secondary" onClick={() => setShowCreateForm(false)}>
                Cancel
              </Button>
              <Button
                type="submit"
                variant="primary"
                loading={createGroup.isPending}
              >
                Create Group
              </Button>
            </div>
          </form>
        </div>
      )}

      {groups.length === 0 ? (
        <EmptyState
          icon={<UsersIcon size={40} />}
          title="No groups yet"
          description="Create your first group to organize team members."
          action={
            <Button variant="primary" size="sm" onClick={openCreateForm}>
              <Plus size={16} />
              Add Group
            </Button>
          }
        />
      ) : (
        <div className="space-y-4">
          {/* ─── Groups table ─────────────────────────────────────────────── */}
          <div className="bg-[var(--bg-secondary)] border border-[var(--border)] rounded-xl overflow-hidden">
            <table className="w-full">
              <thead>
                <tr className="border-b border-[var(--border)]">
                  <th className="text-left text-xs uppercase text-[var(--text-secondary)] font-medium px-4 py-3">Name</th>
                  <th className="text-left text-xs uppercase text-[var(--text-secondary)] font-medium px-4 py-3">Description</th>
                  <th className="text-left text-xs uppercase text-[var(--text-secondary)] font-medium px-4 py-3">Members</th>
                  <th className="text-left text-xs uppercase text-[var(--text-secondary)] font-medium px-4 py-3">Created</th>
                </tr>
              </thead>
              <tbody>
                {groups.map((group) => (
                  <tr
                    key={group.id}
                    onClick={() => setSelectedGroupId(selectedGroupId === group.id ? null : group.id)}
                    className={[
                      'border-b border-[var(--border)] cursor-pointer transition-colors duration-150',
                      selectedGroupId === group.id
                        ? 'bg-[var(--bg-tertiary)]'
                        : 'hover:bg-[var(--bg-tertiary)]',
                    ].join(' ')}
                  >
                    <td className="px-4 py-3 text-sm text-[var(--text-primary)] font-medium">
                      {group.name}
                    </td>
                    <td className="px-4 py-3 text-sm text-[var(--text-secondary)] max-w-xs truncate">
                      {group.description || <span className="italic opacity-50">No description</span>}
                    </td>
                    <td className="px-4 py-3 text-sm text-[var(--text-secondary)]">
                      <span className="inline-flex items-center gap-1">
                        <UsersIcon size={14} />
                        {group.member_count}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-sm text-[var(--text-secondary)]">
                      {relativeTime(group.created_at)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* ─── Group detail panel ──────────────────────────────────────── */}
          {selectedGroupId && (
            <GroupDetailPanel
              groupId={selectedGroupId}
              onClose={() => setSelectedGroupId(null)}
            />
          )}
        </div>
      )}
    </div>
  )
}

// ─── Group Detail Panel ──────────────────────────────────────────────────────

function GroupDetailPanel({
  groupId,
  onClose,
}: {
  groupId: string
  onClose: () => void
}) {
  const toast = useToast()
  const { data: group, isLoading } = useGroup(groupId)
  const updateGroup = useUpdateGroup(groupId)
  const addMember = useAddGroupMember(groupId)
  const removeMember = useRemoveGroupMember(groupId)
  const { data: usersData } = useUsers()

  // ─── Edit state ────────────────────────────────────────────────────────
  const [isEditing, setIsEditing] = useState(false)
  const [editName, setEditName] = useState('')
  const [editDescription, setEditDescription] = useState('')
  const [editFormErrors, setEditFormErrors] = useState<Record<string, string>>({})

  // ─── Add member state ──────────────────────────────────────────────────
  const [newMemberUserId, setNewMemberUserId] = useState('')
  const [newMemberIsLead, setNewMemberIsLead] = useState(false)
  const [addMemberErrors, setAddMemberErrors] = useState<Record<string, string>>({})

  // ─── Confirm remove state ──────────────────────────────────────────────
  const [removingUserId, setRemovingUserId] = useState<string | null>(null)

  // Derive available users (not already members)
  const existingMemberIds = new Set((group?.members ?? []).map((m) => m.user_id))
  const availableUsers = (usersData?.items ?? [])
    .filter((u) => !existingMemberIds.has(u.id))
    .map((u) => ({ value: u.id, label: `${u.full_name} (${u.username})` }))

  function startEditing() {
    if (!group) return
    setEditName(group.name)
    setEditDescription(group.description || '')
    setEditFormErrors({})
    setIsEditing(true)
  }

  async function handleSaveGroup() {
    const errors: Record<string, string> = {}
    if (!editName.trim()) errors.name = 'Group name is required.'
    if (Object.keys(errors).length > 0) {
      setEditFormErrors(errors)
      return
    }
    setEditFormErrors({})

    try {
      await updateGroup.mutateAsync({
        name: editName.trim(),
        description: editDescription.trim() || undefined,
      })
      toast.success('Group updated successfully.')
      setIsEditing(false)
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Failed to update group.'
      toast.error(message)
    }
  }

  async function handleAddMember() {
    const errors: Record<string, string> = {}
    if (!newMemberUserId) errors.user = 'Please select a user.'
    if (Object.keys(errors).length > 0) {
      setAddMemberErrors(errors)
      return
    }
    setAddMemberErrors({})

    try {
      await addMember.mutateAsync({
        user_id: newMemberUserId,
        is_lead: newMemberIsLead || undefined,
      })
      toast.success('Member added successfully.')
      setNewMemberUserId('')
      setNewMemberIsLead(false)
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Failed to add member.'
      toast.error(message)
    }
  }

  async function handleRemoveMember(userId: string) {
    try {
      await removeMember.mutateAsync(userId)
      toast.success('Member removed successfully.')
      setRemovingUserId(null)
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Failed to remove member.'
      toast.error(message)
    }
  }

  if (isLoading) {
    return (
      <div className="bg-[var(--bg-secondary)] border border-[var(--border)] rounded-xl p-6 flex items-center justify-center py-12">
        <Spinner />
      </div>
    )
  }

  if (!group) return null

  return (
    <div className="bg-[var(--bg-secondary)] border border-[var(--border)] rounded-xl overflow-hidden">
      {/* ─── Header ─────────────────────────────────────────────────────────── */}
      <div className="flex items-center justify-between px-5 py-3 border-b border-[var(--border)]">
        <h3 className="text-lg font-semibold text-[var(--text-primary)]">
          {group.name}
        </h3>
        <div className="flex items-center gap-2">
          {!isEditing && (
            <Button variant="ghost" size="sm" onClick={startEditing}>
              <Edit size={14} />
              Edit
            </Button>
          )}
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-tertiary)] transition-all duration-200"
          >
            <X size={18} />
          </button>
        </div>
      </div>

      {/* ─── Group Info (editable) ──────────────────────────────────────────── */}
      {isEditing && (
        <div className="px-5 py-3 border-b border-[var(--border)] bg-[var(--bg-primary)]/30">
          <div className="space-y-3">
            <div>
              <label className="block text-sm font-medium text-[var(--text-primary)] mb-1.5">
                Name <span className="text-red-400">*</span>
              </label>
              <input
                type="text"
                value={editName}
                onChange={(e) => setEditName(e.target.value)}
                className="w-full bg-[var(--bg-tertiary)] border border-[var(--border)] text-[var(--text-primary)] rounded-lg px-3 py-2 placeholder:text-[var(--text-secondary)] focus:outline-none focus:ring-2 focus:ring-[var(--accent)]/50 focus:border-[var(--accent)] transition-colors duration-200"
              />
              {editFormErrors.name && <p className="text-sm text-red-400 mt-1">{editFormErrors.name}</p>}
            </div>
            <div>
              <label className="block text-sm font-medium text-[var(--text-primary)] mb-1.5">
                Description
              </label>
              <textarea
                value={editDescription}
                onChange={(e) => setEditDescription(e.target.value)}
                rows={2}
                className="w-full bg-[var(--bg-tertiary)] border border-[var(--border)] text-[var(--text-primary)] rounded-lg px-3 py-2 placeholder:text-[var(--text-secondary)] focus:outline-none focus:ring-2 focus:ring-[var(--accent)]/50 focus:border-[var(--accent)] transition-colors duration-200 resize-none"
              />
            </div>
            <div className="flex items-center gap-2">
              <Button variant="primary" size="sm" loading={updateGroup.isPending} onClick={handleSaveGroup}>
                Save
              </Button>
              <Button variant="ghost" size="sm" onClick={() => setIsEditing(false)}>
                Cancel
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* ─── Description (read-only) ────────────────────────────────────────── */}
      {!isEditing && group.description && (
        <div className="px-5 py-3 border-b border-[var(--border)]">
          <p className="text-sm text-[var(--text-secondary)]">{group.description}</p>
        </div>
      )}

      {/* ─── Members list ───────────────────────────────────────────────────── */}
      <div className="px-5 py-3">
        <h4 className="text-sm font-medium text-[var(--text-primary)] mb-3">
          Members ({group.members.length})
        </h4>

        {group.members.length === 0 ? (
          <p className="text-sm text-[var(--text-secondary)] py-4 text-center">
            No members in this group yet.
          </p>
        ) : (
          <div className="space-y-1">
            {group.members.map((member) => (
              <div
                key={member.user_id}
                className="flex items-center justify-between py-2 px-3 rounded-lg hover:bg-[var(--bg-tertiary)] transition-colors duration-150"
              >
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 rounded-full bg-[var(--bg-tertiary)] border border-[var(--border)] flex items-center justify-center text-xs font-medium text-[var(--text-secondary)]">
                    {member.full_name.charAt(0).toUpperCase()}
                  </div>
                  <div>
                    <div className="text-sm text-[var(--text-primary)] font-medium">
                      {member.full_name}
                    </div>
                    <div className="text-xs text-[var(--text-secondary)]">
                      {member.username}
                    </div>
                  </div>
                  {member.is_lead && (
                    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-amber-500/15 text-amber-400 border border-amber-500/25">
                      <Shield size={10} />
                      Lead
                    </span>
                  )}
                  {!member.is_lead && (
                    <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-gray-500/15 text-gray-400 border border-gray-500/25">
                      Member
                    </span>
                  )}
                </div>
                <div className="flex items-center gap-3">
                  <span className="text-xs text-[var(--text-secondary)]">
                    {shortDate(member.joined_at)}
                  </span>
                  {removingUserId === member.user_id ? (
                    <div className="flex items-center gap-1">
                      <Button
                        variant="danger"
                        size="sm"
                        loading={removeMember.isPending}
                        onClick={() => handleRemoveMember(member.user_id)}
                      >
                        Confirm
                      </Button>
                      <Button variant="ghost" size="sm" onClick={() => setRemovingUserId(null)}>
                        Cancel
                      </Button>
                    </div>
                  ) : (
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={(e) => {
                        e.stopPropagation()
                        setRemovingUserId(member.user_id)
                      }}
                    >
                      <Trash2 size={14} className="text-red-400" />
                    </Button>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* ─── Add member section ─────────────────────────────────────────────── */}
      <div className="px-5 py-3 border-t border-[var(--border)] bg-[var(--bg-primary)]/30">
        <h4 className="text-sm font-medium text-[var(--text-primary)] mb-3">
          <UserPlus size={14} className="inline mr-1.5" />
          Add Member
        </h4>
        <div className="flex items-end gap-3">
          <div className="flex-1">
            <label className="block text-sm font-medium text-[var(--text-primary)] mb-1.5">
              User <span className="text-red-400">*</span>
            </label>
            <Dropdown
              value={newMemberUserId}
              onChange={(value) => setNewMemberUserId(value)}
              options={availableUsers}
              placeholder="Search users..."
              searchable
            />
            {addMemberErrors.user && <p className="text-sm text-red-400 mt-1">{addMemberErrors.user}</p>}
          </div>
          <div className="flex items-center gap-3 pb-0.5">
            <Toggle
              checked={newMemberIsLead}
              onChange={setNewMemberIsLead}
              label="Lead"
            />
            <Button
              variant="primary"
              size="sm"
              loading={addMember.isPending}
              onClick={handleAddMember}
            >
              <Plus size={14} />
              Add
            </Button>
          </div>
        </div>
      </div>
    </div>
  )
}
