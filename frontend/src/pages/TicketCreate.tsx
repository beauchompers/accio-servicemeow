import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ArrowLeft, Send } from 'lucide-react'
import PageHeader from '@/components/layout/PageHeader'
import Button from '@/components/ui/Button'
import Dropdown from '@/components/ui/Dropdown'
import TipTapEditor from '@/components/editor/TipTapEditor'
import { useToast } from '@/components/ui/Toast'
import { useCreateTicket } from '@/hooks/useTickets'
import { useGroups, useGroup } from '@/hooks/useGroups'
import type { TicketPriority } from '@/types'

// ─── Priority options ────────────────────────────────────────────────────────

const priorityOptions = [
  { value: 'critical', label: 'Critical' },
  { value: 'high', label: 'High' },
  { value: 'medium', label: 'Medium' },
  { value: 'low', label: 'Low' },
]

// ─── TicketCreate ────────────────────────────────────────────────────────────

export default function TicketCreate() {
  const navigate = useNavigate()
  const toast = useToast()
  const createTicket = useCreateTicket()

  const { data: groupsData } = useGroups()

  // ─── Form state ──────────────────────────────────────────────────────────

  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [priority, setPriority] = useState('')
  const [assignedGroupId, setAssignedGroupId] = useState('')
  const [assignedUserId, setAssignedUserId] = useState('')
  const [formErrors, setFormErrors] = useState<Record<string, string>>({})

  // ─── Derived data ────────────────────────────────────────────────────────

  const { data: groupDetail } = useGroup(assignedGroupId)

  const groupOptions = (groupsData?.items ?? []).map((group) => ({
    value: group.id,
    label: group.name,
  }))

  const userOptions = (groupDetail?.members ?? []).map((member) => ({
    value: member.user_id,
    label: member.full_name,
  }))

  // ─── Submit handler ──────────────────────────────────────────────────────

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()

    const errors: Record<string, string> = {}
    if (!title.trim()) errors.title = 'Title is required.'
    if (!description.trim()) errors.description = 'Description is required.'
    if (!priority) errors.priority = 'Priority is required.'
    if (!assignedGroupId) errors.assigned_group_id = 'Group is required.'
    if (Object.keys(errors).length > 0) {
      setFormErrors(errors)
      return
    }
    setFormErrors({})

    try {
      const result = await createTicket.mutateAsync({
        title: title.trim(),
        description,
        priority: priority as TicketPriority,
        assigned_group_id: assignedGroupId,
        ...(assignedUserId ? { assigned_user_id: assignedUserId } : {}),
      })
      toast.success('Ticket created successfully.')
      navigate(`/tickets/${result.id}`)
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : 'Failed to create ticket.'
      toast.error(message)
    }
  }

  // ─── Render ──────────────────────────────────────────────────────────────

  return (
    <div>
      <PageHeader
        title="Create Ticket"
        actions={
          <Button
            variant="ghost"
            size="sm"
            onClick={() => navigate('/tickets')}
          >
            <ArrowLeft size={16} />
            Back
          </Button>
        }
      />

      <div className="max-w-3xl mx-auto">
        <form onSubmit={handleSubmit}>
          <div className="bg-[var(--bg-secondary)] border border-[var(--border)] rounded-xl p-6">
            <div className="space-y-4">
              {/* Title */}
              <div>
                <label htmlFor="title" className="block text-sm font-medium text-[var(--text-primary)] mb-1.5">
                  Title <span className="text-red-400">*</span>
                </label>
                <input
                  id="title"
                  type="text"
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  placeholder="Enter ticket title"
                  className="w-full bg-[var(--bg-tertiary)] border border-[var(--border)] text-[var(--text-primary)] rounded-lg px-3 py-2 placeholder:text-[var(--text-secondary)] focus:outline-none focus:ring-2 focus:ring-[var(--accent)]/50 focus:border-[var(--accent)] transition-colors duration-200"
                />
                {formErrors.title && <p className="text-sm text-red-400 mt-1">{formErrors.title}</p>}
              </div>

              {/* Description */}
              <div>
                <label className="block text-sm font-medium text-[var(--text-primary)] mb-1.5">
                  Description <span className="text-red-400">*</span>
                </label>
                <TipTapEditor
                  content={description}
                  onChange={(html) => setDescription(html)}
                  placeholder="Describe the issue..."
                />
                {formErrors.description && <p className="text-sm text-red-400 mt-1">{formErrors.description}</p>}
              </div>

              {/* Priority */}
              <div>
                <label className="block text-sm font-medium text-[var(--text-primary)] mb-1.5">
                  Priority <span className="text-red-400">*</span>
                </label>
                <Dropdown
                  value={priority}
                  onChange={(value) => setPriority(value)}
                  options={priorityOptions}
                  placeholder="Select priority"
                />
                {formErrors.priority && <p className="text-sm text-red-400 mt-1">{formErrors.priority}</p>}
              </div>

              {/* Group */}
              <div>
                <label className="block text-sm font-medium text-[var(--text-primary)] mb-1.5">
                  Group <span className="text-red-400">*</span>
                </label>
                <Dropdown
                  value={assignedGroupId}
                  onChange={(value) => {
                    setAssignedGroupId(value)
                    setAssignedUserId('')
                  }}
                  options={groupOptions}
                  placeholder="Select group"
                  searchable
                />
                {formErrors.assigned_group_id && <p className="text-sm text-red-400 mt-1">{formErrors.assigned_group_id}</p>}
              </div>

              {/* User */}
              <div>
                <label className="block text-sm font-medium text-[var(--text-primary)] mb-1.5">
                  User
                </label>
                <Dropdown
                  value={assignedUserId}
                  onChange={(value) => setAssignedUserId(value)}
                  options={userOptions}
                  placeholder={assignedGroupId ? 'Select user (optional)' : 'Select a group first...'}
                  searchable
                  disabled={!assignedGroupId}
                />
              </div>
            </div>

            {/* Actions */}
            <div className="flex items-center justify-end gap-3 mt-8">
              <Button
                type="button"
                variant="secondary"
                onClick={() => navigate('/tickets')}
              >
                Cancel
              </Button>
              <Button
                type="submit"
                variant="primary"
                loading={createTicket.isPending}
              >
                <Send size={16} />
                Create Ticket
              </Button>
            </div>
          </div>
        </form>
      </div>
    </div>
  )
}
