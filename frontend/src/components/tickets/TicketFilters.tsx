import { useState, useEffect, useRef } from 'react'
import { Search, Filter, X } from 'lucide-react'
import Dropdown from '@/components/ui/Dropdown'
import Button from '@/components/ui/Button'
import type { TicketStatus, TicketPriority } from '@/types'
import { statusLabel, priorityLabel } from '@/utils/format'

// ─── Types ──────────────────────────────────────────────────────────────────

interface FilterValues {
  status?: string
  priority?: string
  assigned_group_id?: string
  assigned_user_id?: string
  search?: string
  sla_breached?: boolean
}

interface TicketFiltersProps {
  filters: FilterValues
  onFilterChange: (partial: Partial<FilterValues>) => void
  groupOptions: { value: string; label: string }[]
  userOptions: { value: string; label: string }[]
}

// ─── Constants ──────────────────────────────────────────────────────────────

const STATUS_OPTIONS: { value: string; label: string }[] = (
  ['open', 'under_investigation', 'resolved'] as TicketStatus[]
).map((s) => ({ value: s, label: statusLabel(s) }))

const PRIORITY_OPTIONS: { value: string; label: string }[] = (
  ['critical', 'high', 'medium', 'low'] as TicketPriority[]
).map((p) => ({ value: p, label: priorityLabel(p) }))

// ─── Component ──────────────────────────────────────────────────────────────

export default function TicketFilters({
  filters,
  onFilterChange,
  groupOptions,
  userOptions,
}: TicketFiltersProps) {
  const [searchInput, setSearchInput] = useState(filters.search ?? '')
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  // Sync external search changes into local input
  useEffect(() => {
    setSearchInput(filters.search ?? '')
  }, [filters.search])

  // Debounced search
  function handleSearchChange(value: string) {
    setSearchInput(value)

    if (debounceRef.current) {
      clearTimeout(debounceRef.current)
    }

    debounceRef.current = setTimeout(() => {
      onFilterChange({ search: value || undefined })
    }, 300)
  }

  // Cleanup timer on unmount
  useEffect(() => {
    return () => {
      if (debounceRef.current) {
        clearTimeout(debounceRef.current)
      }
    }
  }, [])

  const hasActiveFilters =
    !!filters.search ||
    !!filters.status ||
    !!filters.priority ||
    !!filters.assigned_group_id ||
    !!filters.assigned_user_id ||
    filters.sla_breached === true

  function handleClearFilters() {
    setSearchInput('')
    onFilterChange({
      search: undefined,
      status: undefined,
      priority: undefined,
      assigned_group_id: undefined,
      assigned_user_id: undefined,
      sla_breached: undefined,
    })
  }

  // Parse multi-select status values
  const statusValue = filters.status ? filters.status.split(',') : []

  function handleStatusChange(values: string[]) {
    onFilterChange({
      status: values.length > 0 ? values.join(',') : undefined,
    })
  }

  return (
    <div className="flex flex-wrap items-center gap-3 mb-6">
      {/* Search input */}
      <div className="relative flex-1 min-w-[240px] max-w-md">
        <Search
          size={16}
          className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--text-secondary)] pointer-events-none"
        />
        <input
          type="text"
          value={searchInput}
          onChange={(e) => handleSearchChange(e.target.value)}
          placeholder="Search tickets..."
          className="w-full bg-[var(--bg-tertiary)] border border-[var(--border)] text-[var(--text-primary)] rounded-lg pl-9 pr-3 py-2 text-sm placeholder:text-[var(--text-secondary)] focus:outline-none focus:ring-2 focus:ring-[var(--accent)]/50 focus:border-[var(--accent)] transition-colors duration-200"
        />
      </div>

      {/* Status multi-select */}
      <Dropdown
        multiple
        options={STATUS_OPTIONS}
        value={statusValue}
        onChange={handleStatusChange}
        placeholder="Status"
        className="w-44"
      />

      {/* Priority dropdown */}
      <Dropdown
        options={PRIORITY_OPTIONS}
        value={filters.priority ?? ''}
        onChange={(value) =>
          onFilterChange({ priority: value || undefined })
        }
        placeholder="Priority"
        className="w-36"
      />

      {/* Group dropdown */}
      <Dropdown
        options={groupOptions}
        value={filters.assigned_group_id ?? ''}
        onChange={(value) =>
          onFilterChange({ assigned_group_id: value || undefined })
        }
        placeholder="Group"
        searchable
        className="w-44"
      />

      {/* Assignee dropdown */}
      <Dropdown
        options={userOptions}
        value={filters.assigned_user_id ?? ''}
        onChange={(value) =>
          onFilterChange({ assigned_user_id: value || undefined })
        }
        placeholder="Assignee"
        searchable
        className="w-44"
      />

      {/* SLA Breached toggle */}
      <button
        type="button"
        onClick={() =>
          onFilterChange({
            sla_breached: filters.sla_breached ? undefined : true,
          })
        }
        className={[
          'inline-flex items-center gap-1.5 px-3 py-2 text-sm font-medium rounded-lg border transition-all duration-200',
          filters.sla_breached
            ? 'bg-red-500/15 border-red-500/30 text-red-400'
            : 'bg-[var(--bg-tertiary)] border-[var(--border)] text-[var(--text-secondary)] hover:bg-[var(--border)]',
        ].join(' ')}
      >
        <Filter size={14} />
        SLA Breached
      </button>

      {/* Clear filters */}
      {hasActiveFilters && (
        <Button
          variant="ghost"
          size="sm"
          onClick={handleClearFilters}
        >
          <X size={14} />
          Clear Filters
        </Button>
      )}
    </div>
  )
}
