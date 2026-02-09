import { useNavigate } from 'react-router-dom'
import { Ticket, Search, CheckCircle, LayoutDashboard } from 'lucide-react'
import PageHeader from '@/components/layout/PageHeader'
import Spinner from '@/components/ui/Spinner'
import EmptyState from '@/components/ui/EmptyState'
import SummaryCard from '@/components/dashboard/SummaryCard'
import SlaPanel from '@/components/dashboard/SlaPanel'
import PriorityChart from '@/components/dashboard/PriorityChart'
import ActivityFeed from '@/components/dashboard/ActivityFeed'
import { useDashboardSummary, useRecentActivity } from '@/hooks/useDashboard'
import { statusLabel } from '@/utils/format'

// ─── Status card config ─────────────────────────────────────────────────────

const statusCardConfig: {
  status: string
  borderColor: string
  icon: React.ReactNode
}[] = [
  { status: 'open', borderColor: '#3b82f6', icon: <Ticket className="w-6 h-6" /> },
  { status: 'under_investigation', borderColor: '#f59e0b', icon: <Search className="w-6 h-6" /> },
  { status: 'resolved', borderColor: '#10b981', icon: <CheckCircle className="w-6 h-6" /> },
]

// ─── Dashboard ──────────────────────────────────────────────────────────────

export default function Dashboard() {
  const navigate = useNavigate()
  const { data: summary, isLoading: summaryLoading, isError: summaryError } = useDashboardSummary()
  const { data: activity, isLoading: activityLoading, isError: activityError } = useRecentActivity(1, 50)

  function getCountForStatus(status: string): number {
    if (!summary?.by_status) return 0
    const match = summary.by_status.find((s) => s.status === status)
    return match?.count ?? 0
  }

  function handleStatusClick(status: string) {
    navigate(`/tickets?status=${status}`)
  }

  // ─── Error state ──────────────────────────────────────────────────────

  if (summaryError && activityError) {
    return (
      <div>
        <PageHeader
          title="Dashboard"
          description="Overview of ticket activity, SLA health, and priority distribution."
        />
        <EmptyState
          icon={<LayoutDashboard size={40} />}
          title="Failed to load dashboard"
          description="An error occurred while fetching data. Please try again."
        />
      </div>
    )
  }

  return (
    <div>
      <PageHeader
        title="Dashboard"
        description="Overview of ticket activity, SLA health, and priority distribution."
      />

      {/* ─── Top row: Summary cards ────────────────────────────────────────── */}
      <div className="grid grid-cols-3 gap-4 mb-6">
        {summaryLoading
          ? statusCardConfig.map((cfg) => (
              <div
                key={cfg.status}
                className="bg-[var(--bg-secondary)] border border-[var(--border)] rounded-xl p-5 flex items-center justify-center"
                style={{ borderLeftWidth: '4px', borderLeftColor: cfg.borderColor }}
              >
                <Spinner />
              </div>
            ))
          : statusCardConfig.map((cfg) => (
              <SummaryCard
                key={cfg.status}
                title={statusLabel(cfg.status)}
                count={getCountForStatus(cfg.status)}
                borderColor={cfg.borderColor}
                icon={cfg.icon}
                onClick={() => handleStatusClick(cfg.status)}
              />
            ))}
      </div>

      {/* ─── Second row: SLA Health + Priority Distribution ────────────────── */}
      <div className="grid grid-cols-2 gap-4 mb-6">
        <SlaPanel />
        <PriorityChart data={summary?.by_priority ?? []} />
      </div>

      {/* ─── Bottom row: Activity feed ─────────────────────────────────────── */}
      <ActivityFeed
        entries={activity?.items ?? []}
        isLoading={activityLoading}
      />
    </div>
  )
}
