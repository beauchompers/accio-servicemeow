import { useState, useEffect } from 'react'
import { Clock, AlertTriangle } from 'lucide-react'
import PageHeader from '@/components/layout/PageHeader'
import Button from '@/components/ui/Button'
import Spinner from '@/components/ui/Spinner'
import EmptyState from '@/components/ui/EmptyState'
import { useToast } from '@/components/ui/Toast'
import { useSlaConfig, useUpdateSlaConfig } from '@/hooks/useSlaConfig'
import type { TicketPriority, SlaConfigItem } from '@/types'

// ─── Constants ──────────────────────────────────────────────────────────────

const PRIORITIES: TicketPriority[] = ['critical', 'high', 'medium', 'low']

const priorityLabels: Record<TicketPriority, string> = {
  critical: 'Critical',
  high: 'High',
  medium: 'Medium',
  low: 'Low',
}

const priorityBadgeClasses: Record<TicketPriority, string> = {
  critical: 'bg-red-500/15 text-red-400 border border-red-500/25',
  high: 'bg-orange-500/15 text-orange-400 border border-orange-500/25',
  medium: 'bg-yellow-500/15 text-yellow-400 border border-yellow-500/25',
  low: 'bg-gray-500/15 text-gray-400 border border-gray-500/25',
}

const priorityBorderColors: Record<TicketPriority, string> = {
  critical: 'border-l-red-500',
  high: 'border-l-orange-500',
  medium: 'border-l-yellow-500',
  low: 'border-l-gray-500',
}

function getDefaultConfigs(): SlaConfigItem[] {
  return PRIORITIES.map((priority) => ({
    priority,
    target_assign_minutes: 0,
    target_resolve_minutes: 0,
  }))
}

function formatMinutesDisplay(minutes: number): string {
  if (minutes === 0) return '--'
  if (minutes < 60) return `${minutes}m`
  const hours = Math.floor(minutes / 60)
  const remaining = minutes % 60
  if (remaining === 0) return `${hours}h`
  return `${hours}h ${remaining}m`
}

// ─── SLA Config Page ────────────────────────────────────────────────────────

export default function SlaConfig() {
  const toast = useToast()
  const { data, isLoading, isError } = useSlaConfig()
  const updateSlaConfig = useUpdateSlaConfig()

  // ─── Form state ─────────────────────────────────────────────────────────
  const [configs, setConfigs] = useState<SlaConfigItem[]>(getDefaultConfigs())
  const [hasChanges, setHasChanges] = useState(false)

  // ─── Sync form state from query data ───────────────────────────────────
  useEffect(() => {
    if (!data) return

    const merged = PRIORITIES.map((priority) => {
      const existing = data.find((c) => c.priority === priority)
      return existing ?? { priority, target_assign_minutes: 0, target_resolve_minutes: 0 }
    })

    setConfigs(merged)
    setHasChanges(false)
  }, [data])

  // ─── Handlers ──────────────────────────────────────────────────────────

  function handleChange(
    priority: TicketPriority,
    field: 'target_assign_minutes' | 'target_resolve_minutes',
    value: string,
  ) {
    const numValue = value === '' ? 0 : Math.max(0, parseInt(value, 10) || 0)

    setConfigs((prev) =>
      prev.map((c) =>
        c.priority === priority ? { ...c, [field]: numValue } : c,
      ),
    )
    setHasChanges(true)
  }

  async function handleSave() {
    try {
      await updateSlaConfig.mutateAsync(configs)
      toast.success('SLA configuration saved successfully.')
      setHasChanges(false)
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Failed to save SLA configuration.'
      toast.error(message)
    }
  }

  // ─── Loading state ─────────────────────────────────────────────────────

  if (isLoading) {
    return (
      <div>
        <PageHeader title="SLA Configuration" description="Define service level agreement targets by priority." />
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
        <PageHeader title="SLA Configuration" description="Define service level agreement targets by priority." />
        <EmptyState
          icon={<Clock size={40} />}
          title="Failed to load SLA configuration"
          description="An error occurred while fetching SLA data. Please try again."
        />
      </div>
    )
  }

  // ─── Render ────────────────────────────────────────────────────────────

  return (
    <div>
      <PageHeader
        title="SLA Configuration"
        description="Define service level agreement targets by priority."
      />

      <div className="max-w-4xl">
        {/* ─── Info banner ─────────────────────────────────────────────────── */}
        <div className="flex items-start gap-3 p-4 rounded-xl bg-[var(--bg-secondary)] border border-[var(--border)] mb-6">
          <Clock size={18} className="text-[var(--accent)] shrink-0 mt-0.5" />
          <div>
            <p className="text-sm text-[var(--text-primary)]">
              SLA targets define the maximum allowed time for ticket assignment and resolution based on priority level.
            </p>
            <p className="mt-1 text-xs text-[var(--text-secondary)]">
              Values are in minutes. Set to 0 to disable SLA tracking for a specific target.
            </p>
          </div>
        </div>

        {/* ─── Config table ────────────────────────────────────────────────── */}
        <div className="bg-[var(--bg-secondary)] border border-[var(--border)] rounded-xl overflow-hidden">
          <table className="w-full">
            <thead>
              <tr className="border-b border-[var(--border)]">
                <th className="text-left text-xs uppercase text-[var(--text-secondary)] font-medium px-4 py-3">
                  Priority
                </th>
                <th className="text-left text-xs uppercase text-[var(--text-secondary)] font-medium px-4 py-3">
                  Target Assignment Time
                </th>
                <th className="text-left text-xs uppercase text-[var(--text-secondary)] font-medium px-4 py-3">
                  Target Resolution Time
                </th>
                <th className="text-left text-xs uppercase text-[var(--text-secondary)] font-medium px-4 py-3 w-[140px]">
                  Preview
                </th>
              </tr>
            </thead>
            <tbody>
              {configs.map((config) => (
                <tr
                  key={config.priority}
                  className={`border-b border-[var(--border)] border-l-4 ${priorityBorderColors[config.priority]}`}
                >
                  <td className="px-4 py-3 text-sm">
                    <span className={`inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium ${priorityBadgeClasses[config.priority]}`}>
                      {priorityLabels[config.priority]}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-sm">
                    <div className="flex items-center gap-2 max-w-[200px]">
                      <input
                        type="number"
                        min="0"
                        value={config.target_assign_minutes || ''}
                        onChange={(e) => handleChange(config.priority, 'target_assign_minutes', e.target.value)}
                        placeholder="0"
                        className="w-full bg-[var(--bg-tertiary)] border border-[var(--border)] text-[var(--text-primary)] rounded-lg px-3 py-2 placeholder:text-[var(--text-secondary)] focus:outline-none focus:ring-2 focus:ring-[var(--accent)]/50 focus:border-[var(--accent)] transition-colors duration-200 text-sm [appearance:textfield] [&::-webkit-outer-spin-button]:appearance-none [&::-webkit-inner-spin-button]:appearance-none"
                      />
                      <span className="text-xs text-[var(--text-secondary)] shrink-0">min</span>
                    </div>
                  </td>
                  <td className="px-4 py-3 text-sm">
                    <div className="flex items-center gap-2 max-w-[200px]">
                      <input
                        type="number"
                        min="0"
                        value={config.target_resolve_minutes || ''}
                        onChange={(e) => handleChange(config.priority, 'target_resolve_minutes', e.target.value)}
                        placeholder="0"
                        className="w-full bg-[var(--bg-tertiary)] border border-[var(--border)] text-[var(--text-primary)] rounded-lg px-3 py-2 placeholder:text-[var(--text-secondary)] focus:outline-none focus:ring-2 focus:ring-[var(--accent)]/50 focus:border-[var(--accent)] transition-colors duration-200 text-sm [appearance:textfield] [&::-webkit-outer-spin-button]:appearance-none [&::-webkit-inner-spin-button]:appearance-none"
                      />
                      <span className="text-xs text-[var(--text-secondary)] shrink-0">min</span>
                    </div>
                  </td>
                  <td className="px-4 py-3 text-sm">
                    <div className="text-xs text-[var(--text-secondary)] space-y-0.5">
                      <div>Assign: {formatMinutesDisplay(config.target_assign_minutes)}</div>
                      <div>Resolve: {formatMinutesDisplay(config.target_resolve_minutes)}</div>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* ─── Validation warning ──────────────────────────────────────────── */}
        {configs.some(
          (c) =>
            c.target_assign_minutes > 0 &&
            c.target_resolve_minutes > 0 &&
            c.target_assign_minutes >= c.target_resolve_minutes,
        ) && (
          <div className="flex items-start gap-3 p-4 rounded-xl bg-amber-500/10 border border-amber-500/25 mt-4">
            <AlertTriangle size={18} className="text-amber-400 shrink-0 mt-0.5" />
            <p className="text-sm text-amber-400">
              Warning: Some priorities have an assignment target that exceeds or equals the resolution target.
              The assignment time should typically be shorter than the resolution time.
            </p>
          </div>
        )}

        {/* ─── Save button ─────────────────────────────────────────────────── */}
        <div className="flex items-center justify-end gap-3 mt-6">
          {hasChanges && (
            <span className="text-sm text-[var(--text-secondary)]">
              You have unsaved changes.
            </span>
          )}
          <Button
            variant="primary"
            loading={updateSlaConfig.isPending}
            disabled={!hasChanges}
            onClick={handleSave}
          >
            Save Changes
          </Button>
        </div>
      </div>
    </div>
  )
}
