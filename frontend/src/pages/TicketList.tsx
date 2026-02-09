import { useState, useCallback, useMemo } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { useQueryClient } from '@tanstack/react-query'
import { Plus, Ticket as TicketIcon } from 'lucide-react'
import PageHeader from '@/components/layout/PageHeader'
import Button from '@/components/ui/Button'
import Spinner from '@/components/ui/Spinner'
import EmptyState from '@/components/ui/EmptyState'
import Dropdown from '@/components/ui/Dropdown'
import Modal from '@/components/ui/Modal'
import TicketFilters from '@/components/tickets/TicketFilters'
import TicketTable from '@/components/tickets/TicketTable'
import { useTickets } from '@/hooks/useTickets'
import { useGroups } from '@/hooks/useGroups'
import { useUsers } from '@/hooks/useUsers'
import { apiClient } from '@/api/client'
import type { Ticket, TicketStatus, TicketUpdate } from '@/types'
import { statusLabel } from '@/utils/format'

// ─── Constants ──────────────────────────────────────────────────────────────

const PAGE_SIZE_OPTIONS = [
  { value: '25', label: '25 per page' },
  { value: '50', label: '50 per page' },
  { value: '100', label: '100 per page' },
]

const BULK_STATUS_OPTIONS: { value: string; label: string }[] = (
  ['open', 'under_investigation', 'resolved'] as TicketStatus[]
).map((s) => ({ value: s, label: statusLabel(s) }))

// ─── Helper: read filters from URL search params ────────────────────────────

function filtersFromParams(params: URLSearchParams) {
  return {
    search: params.get('search') || undefined,
    status: params.get('status') || undefined,
    priority: params.get('priority') || undefined,
    assigned_group_id: params.get('assigned_group_id') || undefined,
    assigned_user_id: params.get('assigned_user_id') || undefined,
    sla_breached: params.get('sla_breached') === 'true' ? true : undefined,
    sort_by: params.get('sort_by') || 'created_at',
    sort_order: params.get('sort_order') || 'desc',
    page: params.get('page') ? Number(params.get('page')) : 1,
    page_size: params.get('page_size') ? Number(params.get('page_size')) : 25,
  }
}

// ─── Helper: bulk-update a single ticket via API ────────────────────────────

function patchTicket(id: string, data: TicketUpdate) {
  return apiClient<Ticket>(`/api/v1/tickets/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  })
}

// ─── Component ──────────────────────────────────────────────────────────────

export default function TicketList() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [searchParams, setSearchParams] = useSearchParams()

  // Derive filter state from URL
  const filters = useMemo(() => filtersFromParams(searchParams), [searchParams])

  // Selection state
  const [selectedIds, setSelectedIds] = useState<string[]>([])

  // Bulk action modals
  const [bulkStatusOpen, setBulkStatusOpen] = useState(false)
  const [bulkReassignOpen, setBulkReassignOpen] = useState(false)
  const [bulkStatusValue, setBulkStatusValue] = useState('')
  const [bulkGroupValue, setBulkGroupValue] = useState('')
  const [bulkUserValue, setBulkUserValue] = useState('')
  const [bulkApplying, setBulkApplying] = useState(false)

  // Data fetching
  const { data: ticketData, isLoading, isError } = useTickets(filters)
  const { data: groupData } = useGroups()
  const { data: userData } = useUsers()

  const tickets = ticketData?.items ?? []
  const totalItems = ticketData?.total ?? 0
  const currentPage = filters.page ?? 1
  const pageSize = filters.page_size ?? 25
  const totalPages = Math.max(1, Math.ceil(totalItems / pageSize))

  // Dropdown options for filters
  const groupOptions = useMemo(
    () => (groupData?.items ?? []).map((g) => ({ value: g.id, label: g.name })),
    [groupData],
  )

  const userOptions = useMemo(
    () =>
      (userData?.items ?? []).map((u) => ({
        value: u.id,
        label: u.full_name,
      })),
    [userData],
  )

  // ─── URL param syncing ──────────────────────────────────────────────────

  const updateFilters = useCallback(
    (partial: Record<string, string | boolean | number | undefined>) => {
      setSearchParams((prev) => {
        const next = new URLSearchParams(prev)

        // Reset to page 1 when filters change (unless page itself is being set)
        if (!('page' in partial)) {
          next.set('page', '1')
        }

        for (const [key, value] of Object.entries(partial)) {
          if (value === undefined || value === '' || value === false) {
            next.delete(key)
          } else {
            next.set(key, String(value))
          }
        }
        return next
      })

      // Clear selection when filters change
      setSelectedIds([])
    },
    [setSearchParams],
  )

  function handleFilterChange(partial: Record<string, string | boolean | undefined>) {
    updateFilters(partial)
  }

  function handleSort(field: string, direction: string) {
    updateFilters({ sort_by: field, sort_order: direction })
  }

  function handlePageChange(page: number) {
    updateFilters({ page })
  }

  function handlePageSizeChange(size: string) {
    updateFilters({ page_size: Number(size), page: 1 })
  }

  // ─── Bulk actions ─────────────────────────────────────────────────────

  async function handleBulkStatusApply() {
    if (!bulkStatusValue || selectedIds.length === 0) return

    setBulkApplying(true)
    try {
      await Promise.all(
        selectedIds.map((id) =>
          patchTicket(id, { status: bulkStatusValue as TicketStatus }),
        ),
      )
      queryClient.invalidateQueries({ queryKey: ['tickets'] })
    } finally {
      setBulkApplying(false)
      setBulkStatusOpen(false)
      setBulkStatusValue('')
      setSelectedIds([])
    }
  }

  async function handleBulkReassignApply() {
    if (selectedIds.length === 0) return

    setBulkApplying(true)
    try {
      await Promise.all(
        selectedIds.map((id) =>
          patchTicket(id, {
            ...(bulkGroupValue ? { assigned_group_id: bulkGroupValue } : {}),
            assigned_user_id: bulkUserValue || null,
          }),
        ),
      )
      queryClient.invalidateQueries({ queryKey: ['tickets'] })
    } finally {
      setBulkApplying(false)
      setBulkReassignOpen(false)
      setBulkGroupValue('')
      setBulkUserValue('')
      setSelectedIds([])
    }
  }

  // ─── Pagination info ──────────────────────────────────────────────────

  const rangeStart = totalItems === 0 ? 0 : (currentPage - 1) * pageSize + 1
  const rangeEnd = Math.min(currentPage * pageSize, totalItems)

  // ─── Render ───────────────────────────────────────────────────────────

  return (
    <div>
      {/* Page header */}
      <PageHeader
        title="Tickets"
        description="Manage and track all support tickets"
        actions={
          <Button
            variant="primary"
            size="md"
            onClick={() => navigate('/tickets/new')}
          >
            <Plus size={16} />
            New Ticket
          </Button>
        }
      />

      {/* Filters */}
      <TicketFilters
        filters={filters}
        onFilterChange={handleFilterChange}
        groupOptions={groupOptions}
        userOptions={userOptions}
      />

      {/* Bulk action bar */}
      {selectedIds.length > 0 && (
        <div className="flex items-center gap-3 mb-4 px-4 py-3 bg-[var(--accent)]/10 border border-[var(--accent)]/20 rounded-xl">
          <span className="text-sm font-medium text-[var(--text-primary)]">
            {selectedIds.length} selected
          </span>

          <div className="h-4 w-px bg-[var(--border)]" />

          <Button
            variant="secondary"
            size="sm"
            onClick={() => {
              setBulkStatusValue('')
              setBulkStatusOpen(true)
            }}
          >
            Change Status
          </Button>

          <Button
            variant="secondary"
            size="sm"
            onClick={() => {
              setBulkGroupValue('')
              setBulkUserValue('')
              setBulkReassignOpen(true)
            }}
          >
            Reassign
          </Button>

          <Button
            variant="ghost"
            size="sm"
            onClick={() => setSelectedIds([])}
          >
            Clear Selection
          </Button>
        </div>
      )}

      {/* Main content */}
      {isLoading ? (
        <div className="flex items-center justify-center py-20">
          <Spinner size="lg" />
        </div>
      ) : isError ? (
        <EmptyState
          icon={<TicketIcon size={40} />}
          title="Failed to load tickets"
          description="An error occurred while fetching data. Please try again."
        />
      ) : tickets.length === 0 ? (
        <EmptyState
          icon={<TicketIcon size={40} />}
          title="No tickets found"
          description={
            Object.keys(Object.fromEntries(searchParams)).length > 0
              ? 'Try adjusting your filters to find what you are looking for.'
              : 'Get started by creating your first ticket.'
          }
          action={
            <Button
              variant="primary"
              size="md"
              onClick={() => navigate('/tickets/new')}
            >
              <Plus size={16} />
              New Ticket
            </Button>
          }
        />
      ) : (
        <>
          <TicketTable
            tickets={tickets}
            onSort={handleSort}
            sortBy={filters.sort_by ?? 'created_at'}
            sortOrder={filters.sort_order ?? 'desc'}
            selectedIds={selectedIds}
            onSelectionChange={setSelectedIds}
          />

          {/* Pagination */}
          <div className="flex flex-wrap items-center justify-between gap-4 mt-4">
            <span className="text-sm text-[var(--text-secondary)]">
              Showing {rangeStart}&ndash;{rangeEnd} of {totalItems}
            </span>

            <div className="flex items-center gap-3">
              {/* Page size selector */}
              <Dropdown
                options={PAGE_SIZE_OPTIONS}
                value={String(pageSize)}
                onChange={handlePageSizeChange}
                className="w-36"
              />

              {/* Prev / Next buttons */}
              <div className="flex items-center gap-1">
                <Button
                  variant="secondary"
                  size="sm"
                  disabled={currentPage <= 1}
                  onClick={() => handlePageChange(currentPage - 1)}
                >
                  Previous
                </Button>

                <span className="px-3 text-sm text-[var(--text-secondary)]">
                  Page {currentPage} of {totalPages}
                </span>

                <Button
                  variant="secondary"
                  size="sm"
                  disabled={currentPage >= totalPages}
                  onClick={() => handlePageChange(currentPage + 1)}
                >
                  Next
                </Button>
              </div>
            </div>
          </div>
        </>
      )}

      {/* Bulk status change modal */}
      <Modal
        isOpen={bulkStatusOpen}
        onClose={() => setBulkStatusOpen(false)}
        title="Change Status"
        footer={
          <>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setBulkStatusOpen(false)}
            >
              Cancel
            </Button>
            <Button
              variant="primary"
              size="sm"
              loading={bulkApplying}
              disabled={!bulkStatusValue}
              onClick={handleBulkStatusApply}
            >
              Apply to {selectedIds.length} ticket{selectedIds.length !== 1 ? 's' : ''}
            </Button>
          </>
        }
      >
        <p className="text-sm text-[var(--text-secondary)] mb-4">
          Select the new status to apply to {selectedIds.length} selected ticket
          {selectedIds.length !== 1 ? 's' : ''}.
        </p>
        <Dropdown
          options={BULK_STATUS_OPTIONS}
          value={bulkStatusValue}
          onChange={setBulkStatusValue}
          placeholder="Select status..."
          className="w-full"
        />
      </Modal>

      {/* Bulk reassign modal */}
      <Modal
        isOpen={bulkReassignOpen}
        onClose={() => setBulkReassignOpen(false)}
        title="Reassign Tickets"
        footer={
          <>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setBulkReassignOpen(false)}
            >
              Cancel
            </Button>
            <Button
              variant="primary"
              size="sm"
              loading={bulkApplying}
              onClick={handleBulkReassignApply}
            >
              Apply to {selectedIds.length} ticket{selectedIds.length !== 1 ? 's' : ''}
            </Button>
          </>
        }
      >
        <p className="text-sm text-[var(--text-secondary)] mb-4">
          Reassign {selectedIds.length} selected ticket
          {selectedIds.length !== 1 ? 's' : ''} to a new group and/or user.
        </p>
        <div className="space-y-3">
          <div>
            <label className="block text-sm font-medium text-[var(--text-primary)] mb-1.5">
              Group
            </label>
            <Dropdown
              options={[{ value: '', label: 'No Group' }, ...groupOptions]}
              value={bulkGroupValue}
              onChange={setBulkGroupValue}
              placeholder="Select group..."
              searchable
              className="w-full"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-[var(--text-primary)] mb-1.5">
              Assignee
            </label>
            <Dropdown
              options={[{ value: '', label: 'Unassigned' }, ...userOptions]}
              value={bulkUserValue}
              onChange={setBulkUserValue}
              placeholder="Select assignee..."
              searchable
              className="w-full"
            />
          </div>
        </div>
      </Modal>
    </div>
  )
}
