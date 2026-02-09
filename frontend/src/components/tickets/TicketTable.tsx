import { useNavigate } from 'react-router-dom'
import { ChevronUp, ChevronDown, ArrowUpDown } from 'lucide-react'
import StatusBadge from '@/components/ui/StatusBadge'
import PriorityBadge from '@/components/ui/PriorityBadge'
import SlaIndicator from '@/components/ui/SlaIndicator'
import { relativeTime } from '@/utils/format'
import type { Ticket } from '@/types'

// ─── Types ──────────────────────────────────────────────────────────────────

interface TicketTableProps {
  tickets: Ticket[]
  onSort: (field: string, direction: string) => void
  sortBy: string
  sortOrder: string
  selectedIds: string[]
  onSelectionChange: (ids: string[]) => void
}

interface ColumnDef {
  key: string
  label: string
  sortable: boolean
  className?: string
}

// ─── Column definitions ─────────────────────────────────────────────────────

const COLUMNS: ColumnDef[] = [
  { key: 'ticket_number', label: 'Ticket #', sortable: true, className: 'w-32' },
  { key: 'title', label: 'Title', sortable: true },
  { key: 'status', label: 'Status', sortable: true, className: 'w-40' },
  { key: 'priority', label: 'Priority', sortable: true, className: 'w-28' },
  { key: 'assigned_group_name', label: 'Group', sortable: false, className: 'w-36' },
  { key: 'assigned_user_name', label: 'Assignee', sortable: false, className: 'w-36' },
  { key: 'created_at', label: 'Created', sortable: true, className: 'w-32' },
  { key: 'sla_status', label: 'SLA', sortable: false, className: 'w-28' },
]

// ─── Sort icon helper ───────────────────────────────────────────────────────

function SortIcon({ column, sortBy, sortOrder }: { column: string; sortBy: string; sortOrder: string }) {
  if (sortBy !== column) {
    return <ArrowUpDown size={14} className="text-[var(--text-secondary)]/50" />
  }
  return sortOrder === 'asc' ? (
    <ChevronUp size={14} className="text-[var(--accent)]" />
  ) : (
    <ChevronDown size={14} className="text-[var(--accent)]" />
  )
}

// ─── Component ──────────────────────────────────────────────────────────────

export default function TicketTable({
  tickets,
  onSort,
  sortBy,
  sortOrder,
  selectedIds,
  onSelectionChange,
}: TicketTableProps) {
  const navigate = useNavigate()

  const allSelected = tickets.length > 0 && selectedIds.length === tickets.length
  const someSelected = selectedIds.length > 0 && !allSelected

  function handleSelectAll() {
    if (allSelected) {
      onSelectionChange([])
    } else {
      onSelectionChange(tickets.map((t) => t.id))
    }
  }

  function handleSelectOne(id: string) {
    if (selectedIds.includes(id)) {
      onSelectionChange(selectedIds.filter((i) => i !== id))
    } else {
      onSelectionChange([...selectedIds, id])
    }
  }

  function handleHeaderClick(column: ColumnDef) {
    if (!column.sortable) return

    if (sortBy === column.key) {
      onSort(column.key, sortOrder === 'asc' ? 'desc' : 'asc')
    } else {
      onSort(column.key, 'asc')
    }
  }

  return (
    <div className="bg-[var(--bg-secondary)] border border-[var(--border)] rounded-xl overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          {/* Header */}
          <thead>
            <tr className="bg-[var(--bg-secondary)] border-b border-[var(--border)]">
              {/* Checkbox column */}
              <th className="w-10 px-4 py-3">
                <input
                  type="checkbox"
                  checked={allSelected}
                  ref={(el) => {
                    if (el) el.indeterminate = someSelected
                  }}
                  onChange={handleSelectAll}
                  className="rounded border-[var(--border)] bg-[var(--bg-tertiary)] accent-[var(--accent)]"
                />
              </th>

              {COLUMNS.map((col) => (
                <th
                  key={col.key}
                  className={[
                    'px-4 py-3 text-left text-xs font-medium text-[var(--text-secondary)] uppercase',
                    col.sortable ? 'cursor-pointer select-none hover:text-[var(--text-primary)]' : '',
                    col.className ?? '',
                  ].join(' ')}
                  onClick={() => handleHeaderClick(col)}
                >
                  <span className="inline-flex items-center gap-1">
                    {col.label}
                    {col.sortable && (
                      <SortIcon column={col.key} sortBy={sortBy} sortOrder={sortOrder} />
                    )}
                  </span>
                </th>
              ))}
            </tr>
          </thead>

          {/* Body */}
          <tbody>
            {tickets.map((ticket) => {
              const isSelected = selectedIds.includes(ticket.id)

              return (
                <tr
                  key={ticket.id}
                  onClick={() => navigate(`/tickets/${ticket.id}`)}
                  className={[
                    'cursor-pointer transition-colors duration-150 border-b border-[var(--border)]',
                    'hover:bg-[var(--bg-tertiary)]',
                    isSelected ? 'bg-[var(--accent)]/5' : 'bg-[var(--bg-primary)]',
                  ].join(' ')}
                >
                  {/* Checkbox */}
                  <td className="px-4 py-3">
                    <input
                      type="checkbox"
                      checked={isSelected}
                      onChange={() => handleSelectOne(ticket.id)}
                      onClick={(e) => e.stopPropagation()}
                      className="rounded border-[var(--border)] bg-[var(--bg-tertiary)] accent-[var(--accent)]"
                    />
                  </td>

                  {/* Ticket # */}
                  <td className="px-4 py-3">
                    <span className="font-mono text-xs text-[var(--accent)]">
                      {ticket.ticket_number}
                    </span>
                  </td>

                  {/* Title */}
                  <td className="px-4 py-3">
                    <span className="font-medium text-[var(--text-primary)] line-clamp-1">
                      {ticket.title}
                    </span>
                  </td>

                  {/* Status */}
                  <td className="px-4 py-3">
                    <StatusBadge status={ticket.status} />
                  </td>

                  {/* Priority */}
                  <td className="px-4 py-3">
                    <PriorityBadge priority={ticket.priority} />
                  </td>

                  {/* Group */}
                  <td className="px-4 py-3">
                    <span className="text-[var(--text-secondary)] truncate block max-w-[140px]">
                      {ticket.assigned_group_name ?? '\u2014'}
                    </span>
                  </td>

                  {/* Assignee */}
                  <td className="px-4 py-3">
                    <span className="text-[var(--text-secondary)] truncate block max-w-[140px]">
                      {ticket.assigned_user_name ?? 'Unassigned'}
                    </span>
                  </td>

                  {/* Created */}
                  <td className="px-4 py-3">
                    <span className="text-xs text-[var(--text-secondary)]">
                      {relativeTime(ticket.created_at)}
                    </span>
                  </td>

                  {/* SLA */}
                  <td className="px-4 py-3">
                    <SlaIndicator slaStatus={ticket.sla_status ?? null} />
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </div>
  )
}
