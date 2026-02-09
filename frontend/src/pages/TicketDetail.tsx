import { useState, useEffect, useRef, useCallback, useMemo, type DragEvent, type ChangeEvent, type RefObject, type ReactNode } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import {
  Edit,
  Save,
  X,
  MessageSquare,
  Paperclip,
  History,
  Upload,
  Download,
  Trash2,
  FileText,
  Image as ImageIcon,
  File,
  User,
  Bot,
  ArrowRight,
  Clock,
  AlertTriangle,
  ChevronLeft,
} from 'lucide-react'

import { useTicket, useUpdateTicket, useCreateNote, useUploadAttachment, useDeleteAttachment } from '@/hooks/useTickets'
import { useGroups, useGroup } from '@/hooks/useGroups'

import PageHeader from '@/components/layout/PageHeader'
import Button from '@/components/ui/Button'
import Modal from '@/components/ui/Modal'
import StatusBadge from '@/components/ui/StatusBadge'
import PriorityBadge from '@/components/ui/PriorityBadge'
import SlaIndicator from '@/components/ui/SlaIndicator'
import Dropdown from '@/components/ui/Dropdown'
import Spinner from '@/components/ui/Spinner'
import EmptyState from '@/components/ui/EmptyState'
import TipTapEditor from '@/components/editor/TipTapEditor'
import { useToast } from '@/components/ui/Toast'

import { relativeTime, absoluteDate, formatFileSize } from '@/utils/format'
import {
  getSlaColor,
  getSlaColorClasses,
  getSlaDoClasses,
  formatSlaRemaining,
  formatSlaPercentage,
  formatMinutes,
  formatMttaStatus,
  getSlaOutcomeColor,
} from '@/utils/sla'

import type { TicketStatus, TicketPriority, TicketNote, Attachment, AuditLogEntry as AuditLogEntryType, SlaStatus, MttaStatus } from '@/types'

// ─── Constants ──────────────────────────────────────────────────────────────

const STATUS_OPTIONS: { value: TicketStatus; label: string }[] = [
  { value: 'open', label: 'Open' },
  { value: 'under_investigation', label: 'Under Investigation' },
  { value: 'resolved', label: 'Resolved' },
]

const PRIORITY_OPTIONS: { value: TicketPriority; label: string }[] = [
  { value: 'critical', label: 'Critical' },
  { value: 'high', label: 'High' },
  { value: 'medium', label: 'Medium' },
  { value: 'low', label: 'Low' },
]

type TabKey = 'notes' | 'attachments' | 'audit'

const TABS: { key: TabKey; label: string; icon: typeof MessageSquare }[] = [
  { key: 'notes', label: 'Notes', icon: MessageSquare },
  { key: 'attachments', label: 'Attachments', icon: Paperclip },
  { key: 'audit', label: 'Audit Log', icon: History },
]

// ─── Helpers ────────────────────────────────────────────────────────────────

function getFileIcon(contentType: string) {
  if (contentType.startsWith('image/')) return ImageIcon
  if (contentType.startsWith('text/')) return FileText
  return File
}

function getInitialBgColor(name: string): string {
  const colors = [
    'bg-blue-600',
    'bg-emerald-600',
    'bg-violet-600',
    'bg-amber-600',
    'bg-rose-600',
    'bg-cyan-600',
    'bg-indigo-600',
    'bg-teal-600',
  ]
  let hash = 0
  for (let i = 0; i < name.length; i++) {
    hash = name.charCodeAt(i) + ((hash << 5) - hash)
  }
  return colors[Math.abs(hash) % colors.length]
}

// ─── Main Component ─────────────────────────────────────────────────────────

export default function TicketDetail() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const toast = useToast()

  // ── Data fetching ──────────────────────────────────────────────────────
  const { data: ticket, isLoading: ticketLoading, isError: ticketError } = useTicket(id!)
  const updateTicket = useUpdateTicket(id!)
  const createNote = useCreateNote(id!)
  const uploadAttachment = useUploadAttachment(id!)
  const deleteAttachment = useDeleteAttachment(id!)
  const { data: groupsData } = useGroups(1, 100)

  // ── Local state ────────────────────────────────────────────────────────
  const [selectedGroupId, setSelectedGroupId] = useState('')
  const [activeTab, setActiveTab] = useState<TabKey>('notes')

  // Title editing
  const [isEditingTitle, setIsEditingTitle] = useState(false)
  const [editTitle, setEditTitle] = useState('')

  // Description editing
  const [isEditingDescription, setIsEditingDescription] = useState(false)
  const [editDescription, setEditDescription] = useState('')

  // New note
  const [noteContent, setNoteContent] = useState('')
  const [noteIsInternal, setNoteIsInternal] = useState(false)

  // Attachments
  const [isDragging, setIsDragging] = useState(false)
  const [deleteConfirmId, setDeleteConfirmId] = useState<string | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  // Sync selectedGroupId from ticket data
  useEffect(() => {
    if (ticket?.assigned_group_id) {
      setSelectedGroupId(ticket.assigned_group_id)
    }
  }, [ticket?.assigned_group_id])

  const { data: groupDetail } = useGroup(selectedGroupId)

  // ── Dropdown options ───────────────────────────────────────────────────
  const groupOptions = useMemo(() => {
    const items = groupsData?.items ?? []
    return items.map((g) => ({ value: g.id, label: g.name }))
  }, [groupsData])

  const userOptions = useMemo(() => {
    const members = groupDetail?.members ?? []
    return [
      { value: '__none__', label: 'Unassigned' },
      ...members.map((m) => ({ value: m.user_id, label: m.full_name })),
    ]
  }, [groupDetail])

  // ── Handlers: Title ────────────────────────────────────────────────────
  const handleTitleEditStart = useCallback(() => {
    if (!ticket) return
    setEditTitle(ticket.title)
    setIsEditingTitle(true)
  }, [ticket])

  const handleTitleSave = useCallback(() => {
    if (!editTitle.trim()) return
    updateTicket.mutate(
      { title: editTitle.trim() },
      {
        onSuccess: () => {
          toast.success('Title updated')
          setIsEditingTitle(false)
        },
        onError: () => toast.error('Failed to update title'),
      },
    )
  }, [editTitle, updateTicket, toast])

  const handleTitleCancel = useCallback(() => {
    setIsEditingTitle(false)
    setEditTitle('')
  }, [])

  // ── Handlers: Description ──────────────────────────────────────────────
  const handleDescriptionEditStart = useCallback(() => {
    if (!ticket) return
    setEditDescription(ticket.description)
    setIsEditingDescription(true)
  }, [ticket])

  const handleDescriptionSave = useCallback(() => {
    updateTicket.mutate(
      { description: editDescription },
      {
        onSuccess: () => {
          toast.success('Description updated')
          setIsEditingDescription(false)
        },
        onError: () => toast.error('Failed to update description'),
      },
    )
  }, [editDescription, updateTicket, toast])

  const handleDescriptionCancel = useCallback(() => {
    setIsEditingDescription(false)
    setEditDescription('')
  }, [])

  // ── Handlers: Sidebar property changes ─────────────────────────────────
  const handleStatusChange = useCallback(
    (value: string) => {
      updateTicket.mutate(
        { status: value as TicketStatus },
        {
          onSuccess: () => toast.success('Status updated'),
          onError: () => toast.error('Failed to update status'),
        },
      )
    },
    [updateTicket, toast],
  )

  const handlePriorityChange = useCallback(
    (value: string) => {
      updateTicket.mutate(
        { priority: value as TicketPriority },
        {
          onSuccess: () => toast.success('Priority updated'),
          onError: () => toast.error('Failed to update priority'),
        },
      )
    },
    [updateTicket, toast],
  )

  const handleGroupChange = useCallback(
    (value: string) => {
      setSelectedGroupId(value)
      updateTicket.mutate(
        { assigned_group_id: value, assigned_user_id: null },
        {
          onSuccess: () => toast.success('Assigned group updated'),
          onError: () => toast.error('Failed to update assigned group'),
        },
      )
    },
    [updateTicket, toast],
  )

  const handleUserChange = useCallback(
    (value: string) => {
      const userId = value === '__none__' ? null : value
      updateTicket.mutate(
        { assigned_user_id: userId },
        {
          onSuccess: () => toast.success('Assigned user updated'),
          onError: () => toast.error('Failed to update assigned user'),
        },
      )
    },
    [updateTicket, toast],
  )

  // ── Handlers: Notes ────────────────────────────────────────────────────
  const handlePostNote = useCallback(() => {
    if (!noteContent.trim()) return
    createNote.mutate(
      { content: noteContent, is_internal: noteIsInternal },
      {
        onSuccess: () => {
          toast.success('Note posted')
          setNoteContent('')
          setNoteIsInternal(false)
        },
        onError: () => toast.error('Failed to post note'),
      },
    )
  }, [noteContent, noteIsInternal, createNote, toast])

  // ── Handlers: Attachments ──────────────────────────────────────────────
  const handleFileUpload = useCallback(
    (files: FileList | null) => {
      if (!files) return
      Array.from(files).forEach((file) => {
        uploadAttachment.mutate(file, {
          onSuccess: () => toast.success(`Uploaded ${file.name}`),
          onError: () => toast.error(`Failed to upload ${file.name}`),
        })
      })
    },
    [uploadAttachment, toast],
  )

  const handleDragOver = useCallback((e: DragEvent) => {
    e.preventDefault()
    setIsDragging(true)
  }, [])

  const handleDragLeave = useCallback((e: DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
  }, [])

  const handleDrop = useCallback(
    (e: DragEvent) => {
      e.preventDefault()
      setIsDragging(false)
      handleFileUpload(e.dataTransfer.files)
    },
    [handleFileUpload],
  )

  const handleFileInputChange = useCallback(
    (e: ChangeEvent<HTMLInputElement>) => {
      handleFileUpload(e.target.files)
      // Reset so the same file can be uploaded again
      if (fileInputRef.current) fileInputRef.current.value = ''
    },
    [handleFileUpload],
  )

  const handleDeleteAttachment = useCallback(
    (attachmentId: string) => {
      deleteAttachment.mutate(attachmentId, {
        onSuccess: () => {
          toast.success('Attachment deleted')
          setDeleteConfirmId(null)
        },
        onError: () => toast.error('Failed to delete attachment'),
      })
    },
    [deleteAttachment, toast],
  )

  // ── Loading state ──────────────────────────────────────────────────────
  if (ticketLoading) {
    return (
      <div>
        <PageHeader title="Ticket Details" description="Loading ticket information." />
        <div className="flex items-center justify-center py-20">
          <Spinner size="lg" />
        </div>
      </div>
    )
  }

  // ── Error state ───────────────────────────────────────────────────────
  if (ticketError) {
    return (
      <div>
        <PageHeader title="Ticket Details" description="View and manage ticket information." />
        <EmptyState
          icon={<AlertTriangle size={40} />}
          title="Failed to load ticket"
          description="An error occurred while fetching ticket data. Please try again."
          action={
            <Button variant="secondary" onClick={() => navigate('/tickets')}>
              <ChevronLeft size={16} />
              Back to Tickets
            </Button>
          }
        />
      </div>
    )
  }

  // ── Not found state ───────────────────────────────────────────────────
  if (!ticket) {
    return (
      <div>
        <PageHeader title="Ticket Details" description="View and manage ticket information." />
        <EmptyState
          icon={<AlertTriangle size={40} />}
          title="Ticket not found"
          description="The ticket you are looking for does not exist or has been deleted."
          action={
            <Button variant="secondary" onClick={() => navigate('/tickets')}>
              <ChevronLeft size={16} />
              Back to Tickets
            </Button>
          }
        />
      </div>
    )
  }

  // ── Render ─────────────────────────────────────────────────────────────
  return (
    <div className="p-6 max-w-[1600px] mx-auto">
      {/* ─── Header ──────────────────────────────────────────────────────── */}
      <div className="mb-6">
        {/* Back link */}
        <Link
          to="/tickets"
          className="inline-flex items-center gap-1 text-sm text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition-colors duration-200 mb-4"
        >
          <ChevronLeft size={16} />
          Back to Tickets
        </Link>

        <div className="flex flex-wrap items-start gap-4">
          {/* Ticket number */}
          <span className="font-mono text-sm text-[var(--text-secondary)] pt-1">
            {ticket.ticket_number}
          </span>

          {/* Title (inline editable) */}
          <div className="flex-1 min-w-0">
            {isEditingTitle ? (
              <div className="flex items-center gap-2">
                <input
                  type="text"
                  value={editTitle}
                  onChange={(e) => setEditTitle(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') handleTitleSave()
                    if (e.key === 'Escape') handleTitleCancel()
                  }}
                  autoFocus
                  className="flex-1 text-xl font-bold bg-[var(--bg-tertiary)] border border-[var(--border)] text-[var(--text-primary)] rounded-lg px-3 py-1 focus:outline-none focus:ring-2 focus:ring-[var(--accent)]/50 focus:border-[var(--accent)] transition-colors duration-200"
                />
                <Button
                  variant="primary"
                  size="sm"
                  onClick={handleTitleSave}
                  loading={updateTicket.isPending}
                >
                  <Save size={14} />
                </Button>
                <Button variant="ghost" size="sm" onClick={handleTitleCancel}>
                  <X size={14} />
                </Button>
              </div>
            ) : (
              <h1
                className="text-xl font-bold text-[var(--text-primary)] cursor-pointer hover:text-[var(--accent)] transition-colors duration-200"
                onClick={handleTitleEditStart}
                title="Click to edit title"
              >
                {ticket.title}
              </h1>
            )}
          </div>

          {/* Badges */}
          <div className="flex items-center gap-3 shrink-0 pt-1">
            <StatusBadge status={ticket.status} />
            <PriorityBadge priority={ticket.priority} />
            <SlaIndicator slaStatus={ticket.sla_status ?? null} />
          </div>
        </div>
      </div>

      {/* ─── Two-column layout ───────────────────────────────────────────── */}
      <div className="flex gap-6 flex-col lg:flex-row">
        {/* ── Left panel (~65%) ─────────────────────────────────────────── */}
        <div className="flex-1 lg:w-[65%] min-w-0 space-y-6">
          {/* Description section */}
          <section className="bg-[var(--bg-secondary)] border border-[var(--border)] rounded-xl overflow-hidden">
            <div className="flex items-center justify-between px-5 py-3 border-b border-[var(--border)]">
              <h2 className="text-sm font-semibold text-[var(--text-primary)]">Description</h2>
              {!isEditingDescription && (
                <Button variant="ghost" size="sm" onClick={handleDescriptionEditStart}>
                  <Edit size={14} />
                  Edit
                </Button>
              )}
            </div>
            <div className="p-5">
              {isEditingDescription ? (
                <div className="space-y-3">
                  <TipTapEditor
                    content={editDescription}
                    onChange={(html) => setEditDescription(html)}
                    editable
                    placeholder="Enter ticket description..."
                  />
                  <div className="flex items-center gap-2">
                    <Button
                      variant="primary"
                      size="sm"
                      onClick={handleDescriptionSave}
                      loading={updateTicket.isPending}
                    >
                      <Save size={14} />
                      Save
                    </Button>
                    <Button variant="ghost" size="sm" onClick={handleDescriptionCancel}>
                      Cancel
                    </Button>
                  </div>
                </div>
              ) : (
                <div
                  className="prose prose-invert prose-sm max-w-none text-[var(--text-primary)] [&_a]:text-[var(--accent)]"
                  dangerouslySetInnerHTML={{ __html: ticket.description || '<p class="text-[var(--text-secondary)] italic">No description provided.</p>' }}
                />
              )}
            </div>
          </section>

          {/* Tabbed section */}
          <section className="bg-[var(--bg-secondary)] border border-[var(--border)] rounded-xl overflow-hidden">
            {/* Tab bar */}
            <div className="flex border-b border-[var(--border)]">
              {TABS.map((tab) => {
                const Icon = tab.icon
                const isActive = activeTab === tab.key
                return (
                  <button
                    key={tab.key}
                    type="button"
                    onClick={() => setActiveTab(tab.key)}
                    className={[
                      'flex items-center gap-2 px-5 py-3 text-sm font-medium transition-all duration-200',
                      isActive
                        ? 'border-b-2 border-[var(--accent)] text-[var(--accent)]'
                        : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)]',
                    ].join(' ')}
                  >
                    <Icon size={16} />
                    {tab.label}
                    {tab.key === 'notes' && ticket.notes.length > 0 && (
                      <span className="ml-1 text-xs bg-[var(--bg-tertiary)] rounded-full px-1.5 py-0.5">
                        {ticket.notes.length}
                      </span>
                    )}
                    {tab.key === 'attachments' && ticket.attachments.length > 0 && (
                      <span className="ml-1 text-xs bg-[var(--bg-tertiary)] rounded-full px-1.5 py-0.5">
                        {ticket.attachments.length}
                      </span>
                    )}
                  </button>
                )
              })}
            </div>

            {/* Tab content */}
            <div className="p-5">
              {activeTab === 'notes' && (
                <NotesTab
                  notes={ticket.notes}
                  noteContent={noteContent}
                  onNoteContentChange={setNoteContent}
                  noteIsInternal={noteIsInternal}
                  onNoteIsInternalChange={setNoteIsInternal}
                  onPost={handlePostNote}
                  isPosting={createNote.isPending}
                />
              )}
              {activeTab === 'attachments' && (
                <AttachmentsTab
                  attachments={ticket.attachments}
                  isDragging={isDragging}
                  onDragOver={handleDragOver}
                  onDragLeave={handleDragLeave}
                  onDrop={handleDrop}
                  onFileInputChange={handleFileInputChange}
                  fileInputRef={fileInputRef}
                  isUploading={uploadAttachment.isPending}
                  deleteConfirmId={deleteConfirmId}
                  onDeleteConfirmOpen={setDeleteConfirmId}
                  onDeleteConfirmClose={() => setDeleteConfirmId(null)}
                  onDelete={handleDeleteAttachment}
                  isDeleting={deleteAttachment.isPending}
                />
              )}
              {activeTab === 'audit' && <AuditLogTab entries={ticket.audit_log} />}
            </div>
          </section>
        </div>

        {/* ── Right sidebar (~35%) ──────────────────────────────────────── */}
        <div className="lg:w-[35%] shrink-0">
          <div className="bg-[var(--bg-secondary)] border border-[var(--border)] rounded-xl overflow-hidden sticky top-6">
            <div className="px-5 py-3 border-b border-[var(--border)]">
              <h2 className="text-sm font-semibold text-[var(--text-primary)]">Properties</h2>
            </div>
            <div className="divide-y divide-[var(--border)]">
              {/* Status */}
              <SidebarField label="Status">
                <Dropdown
                  options={STATUS_OPTIONS}
                  value={ticket.status}
                  onChange={handleStatusChange}
                />
              </SidebarField>

              {/* Priority */}
              <SidebarField label="Priority">
                <Dropdown
                  options={PRIORITY_OPTIONS}
                  value={ticket.priority}
                  onChange={handlePriorityChange}
                />
              </SidebarField>

              {/* Assigned Group */}
              <SidebarField label="Assigned Group">
                <Dropdown
                  options={groupOptions}
                  value={ticket.assigned_group_id ?? ''}
                  onChange={handleGroupChange}
                  searchable
                  placeholder="Select group..."
                />
              </SidebarField>

              {/* Assigned User */}
              <SidebarField label="Assigned User">
                <Dropdown
                  options={userOptions}
                  value={ticket.assigned_user_id ?? '__none__'}
                  onChange={handleUserChange}
                  searchable
                  placeholder={selectedGroupId ? 'Select user...' : 'Select a group first...'}
                  disabled={!groupDetail}
                />
              </SidebarField>

              {/* Created By (read-only) */}
              <SidebarField label="Created By">
                <p className="text-sm text-[var(--text-primary)] py-2">{ticket.created_by_name}</p>
              </SidebarField>

              {/* Created */}
              <SidebarField label="Created">
                <p className="text-sm text-[var(--text-primary)] py-2">{absoluteDate(ticket.created_at)}</p>
              </SidebarField>

              {/* Updated */}
              <SidebarField label="Updated">
                <p className="text-sm text-[var(--text-primary)] py-2" title={absoluteDate(ticket.updated_at)}>
                  {relativeTime(ticket.updated_at)}
                </p>
              </SidebarField>

              {/* SLA Details */}
              {((ticket.sla_status && ticket.sla_status.target_minutes !== null) || ticket.mtta_status) && (
                <SidebarField label="SLA Details">
                  <SlaDetails slaStatus={ticket.sla_status ?? null} mttaStatus={ticket.mtta_status ?? null} />
                </SidebarField>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* ─── Delete Attachment Confirmation Modal ─────────────────────────── */}
      <Modal
        isOpen={deleteConfirmId !== null}
        onClose={() => setDeleteConfirmId(null)}
        title="Delete Attachment"
        footer={
          <>
            <Button variant="secondary" size="sm" onClick={() => setDeleteConfirmId(null)}>
              Cancel
            </Button>
            <Button
              variant="danger"
              size="sm"
              loading={deleteAttachment.isPending}
              onClick={() => deleteConfirmId && handleDeleteAttachment(deleteConfirmId)}
            >
              <Trash2 size={14} />
              Delete
            </Button>
          </>
        }
      >
        <p className="text-sm text-[var(--text-secondary)]">
          Are you sure you want to delete this attachment? This action cannot be undone.
        </p>
      </Modal>
    </div>
  )
}

// ─── Sidebar Field ──────────────────────────────────────────────────────────

function SidebarField({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="px-5 py-3">
      <label className="block text-sm font-medium text-[var(--text-primary)] mb-1.5">
        {label}
      </label>
      {children}
    </div>
  )
}

// ─── SLA Details ────────────────────────────────────────────────────────────

function SlaDetails({ slaStatus, mttaStatus }: { slaStatus: SlaStatus | null; mttaStatus: MttaStatus | null }) {
  return (
    <div className="space-y-4 py-2">
      {/* MTTA Section */}
      {mttaStatus && (
        <MttaSection mttaStatus={mttaStatus} />
      )}

      {/* Separator when both sections exist */}
      {mttaStatus && slaStatus && slaStatus.target_minutes !== null && (
        <div className="border-t border-[var(--border)]" />
      )}

      {/* MTTR Section */}
      {slaStatus && slaStatus.target_minutes !== null && (
        <MttrSection slaStatus={slaStatus} />
      )}
    </div>
  )
}

function MttaSection({ mttaStatus }: { mttaStatus: MttaStatus }) {
  const color = mttaStatus.is_met ? 'green' as const : getSlaColor(mttaStatus.percentage)
  const colorClasses = getSlaColorClasses(color)
  const barBgClass = getSlaDoClasses(color)
  const percentage = Math.min(mttaStatus.percentage, 100)

  return (
    <div className="space-y-2.5">
      <p className="text-xs font-semibold text-[var(--text-primary)] uppercase tracking-wide">Time to Assign (MTTA)</p>
      <div className="flex items-center justify-between text-xs">
        <span className="text-[var(--text-secondary)]">Target</span>
        <span className="text-[var(--text-primary)]">
          {mttaStatus.target_minutes !== null ? formatMinutes(mttaStatus.target_minutes) : 'N/A'}
        </span>
      </div>
      <div className="flex items-center justify-between text-xs">
        <span className="text-[var(--text-secondary)]">{mttaStatus.is_pending ? 'Elapsed' : 'Actual'}</span>
        <span className="text-[var(--text-primary)]">{formatMinutes(mttaStatus.elapsed_minutes)}</span>
      </div>
      <div>
        <div className="flex items-center justify-between text-xs mb-1">
          <span className="text-[var(--text-secondary)]">Progress</span>
          <span className={colorClasses}>{formatSlaPercentage(mttaStatus.percentage)}</span>
        </div>
        <div className="h-2 bg-[var(--bg-tertiary)] rounded-full overflow-hidden">
          <div
            className={['h-full rounded-full transition-all duration-500', barBgClass].join(' ')}
            style={{ width: `${percentage}%` }}
          />
        </div>
      </div>
      <div className="text-xs">
        <span className={colorClasses}>{formatMttaStatus(mttaStatus)}</span>
      </div>
    </div>
  )
}

function MttrSection({ slaStatus }: { slaStatus: SlaStatus }) {
  const color = getSlaOutcomeColor(slaStatus)
  const colorClasses = getSlaColorClasses(color)
  const barBgClass = getSlaDoClasses(color)
  const percentage = Math.min(slaStatus.percentage, 100)

  return (
    <div className="space-y-2.5">
      <p className="text-xs font-semibold text-[var(--text-primary)] uppercase tracking-wide">Time to Resolve (MTTR)</p>
      <div className="flex items-center justify-between text-xs">
        <span className="text-[var(--text-secondary)]">Target</span>
        <span className="text-[var(--text-primary)]">
          {slaStatus.target_minutes !== null ? formatMinutes(slaStatus.target_minutes) : 'N/A'}
        </span>
      </div>
      <div className="flex items-center justify-between text-xs">
        <span className="text-[var(--text-secondary)]">{slaStatus.is_resolved ? 'Actual' : 'Elapsed'}</span>
        <span className="text-[var(--text-primary)]">{formatMinutes(slaStatus.elapsed_minutes)}</span>
      </div>
      <div>
        <div className="flex items-center justify-between text-xs mb-1">
          <span className="text-[var(--text-secondary)]">Progress</span>
          <span className={colorClasses}>{formatSlaPercentage(slaStatus.percentage)}</span>
        </div>
        <div className="h-2 bg-[var(--bg-tertiary)] rounded-full overflow-hidden">
          <div
            className={['h-full rounded-full transition-all duration-500', barBgClass].join(' ')}
            style={{ width: `${percentage}%` }}
          />
        </div>
      </div>
      <div className="text-xs">
        <span className={colorClasses}>{formatSlaRemaining(slaStatus)}</span>
      </div>
      {/* Breach / At-risk indicators (only for unresolved) */}
      {!slaStatus.is_resolved && slaStatus.is_breached && (
        <div className="flex items-center gap-1.5 text-xs text-red-400 bg-red-500/10 rounded-lg px-2.5 py-1.5">
          <AlertTriangle size={14} />
          SLA Breached
        </div>
      )}
      {!slaStatus.is_resolved && !slaStatus.is_breached && slaStatus.is_at_risk && (
        <div className="flex items-center gap-1.5 text-xs text-amber-400 bg-amber-500/10 rounded-lg px-2.5 py-1.5">
          <Clock size={14} />
          At Risk
        </div>
      )}
    </div>
  )
}

// ─── Notes Tab ──────────────────────────────────────────────────────────────

interface NotesTabProps {
  notes: TicketNote[]
  noteContent: string
  onNoteContentChange: (content: string) => void
  noteIsInternal: boolean
  onNoteIsInternalChange: (value: boolean) => void
  onPost: () => void
  isPosting: boolean
}

function NotesTab({
  notes,
  noteContent,
  onNoteContentChange,
  noteIsInternal,
  onNoteIsInternalChange,
  onPost,
  isPosting,
}: NotesTabProps) {
  return (
    <div className="space-y-4">
      {/* Notes list */}
      {notes.length === 0 ? (
        <EmptyState
          icon={<MessageSquare size={40} />}
          title="No notes yet"
          description="Add a note to start the conversation."
        />
      ) : (
        <div className="space-y-3">
          {notes.map((note) => (
            <NoteCard key={note.id} note={note} />
          ))}
        </div>
      )}

      {/* New note composer */}
      <div className="border-t border-[var(--border)] pt-4 space-y-3">
        <TipTapEditor
          content={noteContent}
          onChange={onNoteContentChange}
          editable
          placeholder="Write a note..."
        />
        <div className="flex items-center justify-between">
          <label className="flex items-center gap-2 cursor-pointer select-none">
            <input
              type="checkbox"
              checked={noteIsInternal}
              onChange={(e) => onNoteIsInternalChange(e.target.checked)}
              className="h-4 w-4 rounded border-[var(--border)] bg-[var(--bg-tertiary)] text-[var(--accent)] focus:ring-[var(--accent)] focus:ring-offset-0"
            />
            <span className="text-sm text-[var(--text-secondary)]">Internal note</span>
          </label>
          <Button
            variant="primary"
            size="sm"
            onClick={onPost}
            loading={isPosting}
            disabled={!noteContent.trim()}
          >
            <MessageSquare size={14} />
            Post
          </Button>
        </div>
      </div>
    </div>
  )
}

// ─── Note Card ──────────────────────────────────────────────────────────────

function NoteCard({ note }: { note: TicketNote }) {
  const initial = note.author_name?.charAt(0)?.toUpperCase() || '?'
  const bgColor = getInitialBgColor(note.author_name)

  return (
    <div
      className={[
        'rounded-lg p-4',
        note.is_internal
          ? 'bg-amber-500/5 border-l-2 border-amber-500/30'
          : 'bg-[var(--bg-tertiary)]',
      ].join(' ')}
    >
      <div className="flex items-start gap-3">
        {/* Author avatar */}
        <div
          className={[
            'flex items-center justify-center h-8 w-8 rounded-full shrink-0 text-xs font-semibold text-white',
            bgColor,
          ].join(' ')}
        >
          {initial}
        </div>

        <div className="flex-1 min-w-0">
          {/* Meta row */}
          <div className="flex items-center gap-2 mb-1">
            <span className="text-sm font-medium text-[var(--text-primary)]">
              {note.author_name}
            </span>
            {note.is_internal && (
              <span className="text-xs font-medium text-amber-400 bg-amber-500/15 rounded px-1.5 py-0.5">
                Internal
              </span>
            )}
            <span className="text-xs text-[var(--text-secondary)]">
              {relativeTime(note.created_at)}
            </span>
          </div>

          {/* Content */}
          <div
            className="prose prose-invert prose-sm max-w-none text-[var(--text-primary)] [&_a]:text-[var(--accent)]"
            dangerouslySetInnerHTML={{ __html: note.content }}
          />
        </div>
      </div>
    </div>
  )
}

// ─── Attachments Tab ────────────────────────────────────────────────────────

interface AttachmentsTabProps {
  attachments: Attachment[]
  isDragging: boolean
  onDragOver: (e: DragEvent) => void
  onDragLeave: (e: DragEvent) => void
  onDrop: (e: DragEvent) => void
  onFileInputChange: (e: ChangeEvent<HTMLInputElement>) => void
  fileInputRef: RefObject<HTMLInputElement>
  isUploading: boolean
  deleteConfirmId: string | null
  onDeleteConfirmOpen: (id: string) => void
  onDeleteConfirmClose: () => void
  onDelete: (id: string) => void
  isDeleting: boolean
}

function AttachmentsTab({
  attachments,
  isDragging,
  onDragOver,
  onDragLeave,
  onDrop,
  onFileInputChange,
  fileInputRef,
  isUploading,
  onDeleteConfirmOpen,
}: AttachmentsTabProps) {
  return (
    <div className="space-y-4">
      {/* Upload zone */}
      <div
        onDragOver={onDragOver}
        onDragLeave={onDragLeave}
        onDrop={onDrop}
        className={[
          'flex flex-col items-center justify-center gap-2 p-6 border-2 border-dashed rounded-lg transition-all duration-200 cursor-pointer',
          isDragging
            ? 'border-[var(--accent)] bg-[var(--accent)]/5'
            : 'border-[var(--border)] hover:border-[var(--text-secondary)]',
        ].join(' ')}
        onClick={() => fileInputRef.current?.click()}
      >
        {isUploading ? (
          <Spinner size="md" />
        ) : (
          <>
            <Upload size={24} className="text-[var(--text-secondary)]" />
            <p className="text-sm text-[var(--text-secondary)]">
              Drag and drop files here or <span className="text-[var(--accent)] font-medium">browse</span>
            </p>
          </>
        )}
        <input
          ref={fileInputRef}
          type="file"
          multiple
          onChange={onFileInputChange}
          className="hidden"
        />
      </div>

      {/* Attachments grid */}
      {attachments.length === 0 ? (
        <EmptyState
          icon={<Paperclip size={40} />}
          title="No attachments"
          description="Upload files to attach them to this ticket."
        />
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {attachments.map((attachment) => (
            <AttachmentCardContent
              key={attachment.id}
              attachment={attachment}
              onRequestDelete={onDeleteConfirmOpen}
            />
          ))}
        </div>
      )}
    </div>
  )
}

// ─── Actual Attachment Card (standalone) ────────────────────────────────────

function AttachmentCardContent({
  attachment,
  onRequestDelete,
}: {
  attachment: Attachment
  onRequestDelete: (id: string) => void
}) {
  const FileIcon = getFileIcon(attachment.content_type)

  return (
    <div className="flex items-start gap-3 p-3 bg-[var(--bg-tertiary)] rounded-lg group">
      {/* File icon */}
      <div className="flex items-center justify-center h-10 w-10 rounded-lg bg-[var(--bg-primary)] shrink-0">
        <FileIcon size={20} className="text-[var(--text-secondary)]" />
      </div>

      {/* Info */}
      <div className="flex-1 min-w-0">
        <a
          href={`/api/v1/tickets/attachments/${attachment.id}/download`}
          className="text-sm font-medium text-[var(--text-primary)] hover:text-[var(--accent)] truncate block transition-colors duration-200"
          title={attachment.original_filename}
          download
        >
          {attachment.original_filename}
        </a>
        <p className="text-xs text-[var(--text-secondary)]">
          {formatFileSize(attachment.file_size)} &middot; {attachment.uploaded_by_name} &middot; {relativeTime(attachment.uploaded_at)}
        </p>
      </div>

      {/* Download button */}
      <a
        href={`/api/v1/tickets/attachments/${attachment.id}/download`}
        download
        className="p-1.5 rounded-lg text-[var(--text-secondary)] hover:text-[var(--accent)] hover:bg-[var(--accent)]/10 opacity-0 group-hover:opacity-100 transition-all duration-200 shrink-0"
        title="Download attachment"
      >
        <Download size={14} />
      </a>

      {/* Delete button */}
      <button
        type="button"
        onClick={() => onRequestDelete(attachment.id)}
        className="p-1.5 rounded-lg text-[var(--text-secondary)] hover:text-red-400 hover:bg-red-500/10 opacity-0 group-hover:opacity-100 transition-all duration-200 shrink-0"
        title="Delete attachment"
      >
        <Trash2 size={14} />
      </button>
    </div>
  )
}

// ─── Audit Log Tab ──────────────────────────────────────────────────────────

function AuditLogTab({ entries }: { entries: AuditLogEntryType[] }) {
  if (entries.length === 0) {
    return (
      <EmptyState
        icon={<History size={40} />}
        title="No audit entries"
        description="Actions on this ticket will appear here."
      />
    )
  }

  return (
    <div className="relative">
      {/* Connecting line */}
      <div className="absolute left-[15px] top-2 bottom-2 w-px bg-[var(--border)]" />

      <div className="space-y-4">
        {entries.map((entry) => (
          <AuditLogEntryRow key={entry.id} entry={entry} />
        ))}
      </div>
    </div>
  )
}

function AuditLogEntryRow({ entry }: { entry: AuditLogEntryType }) {
  const isSystem = entry.actor_type === 'system' || entry.actor_type === 'api_key'
  const ActorIcon = isSystem ? Bot : User

  return (
    <div className="relative flex items-start gap-3 pl-0">
      {/* Timeline dot */}
      <div className="relative z-10 flex items-center justify-center h-[30px] w-[30px] rounded-full bg-[var(--bg-secondary)] border border-[var(--border)] shrink-0">
        <ActorIcon size={14} className="text-[var(--text-secondary)]" />
      </div>

      {/* Content */}
      <div className="flex-1 min-w-0 pt-1">
        <div className="flex flex-wrap items-baseline gap-x-2 gap-y-0.5">
          <span className="text-sm font-medium text-[var(--text-primary)]">
            {entry.actor_name || entry.actor_type}
          </span>
          <span className="text-sm text-[var(--text-secondary)]">{entry.action}</span>
          <span className="text-xs text-[var(--text-secondary)]">
            {relativeTime(entry.created_at)}
          </span>
        </div>

        {/* Field change */}
        {entry.field_changed && (
          <div className="mt-1 flex items-center gap-2 text-xs">
            <span className="font-medium text-[var(--text-secondary)]">{entry.field_changed}:</span>
            {entry.old_value && (
              <span className="bg-red-500/10 text-red-400 rounded px-1.5 py-0.5 line-through">
                {entry.old_value}
              </span>
            )}
            <ArrowRight size={12} className="text-[var(--text-secondary)] shrink-0" />
            {entry.new_value && (
              <span className="bg-emerald-500/10 text-emerald-400 rounded px-1.5 py-0.5">
                {entry.new_value}
              </span>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
