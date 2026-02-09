import { Clock, AlertTriangle } from 'lucide-react'
import Spinner from '@/components/ui/Spinner'
import { formatMinutes } from '@/utils/sla'
import { useSlaMetrics } from '@/hooks/useDashboard'

// ─── SlaPanel ───────────────────────────────────────────────────────────────

export default function SlaPanel() {
  const { data, isLoading } = useSlaMetrics()

  if (isLoading) {
    return (
      <div className="bg-[var(--bg-secondary)] border border-[var(--border)] rounded-lg p-6">
        <h2 className="text-lg font-semibold text-[var(--text-primary)] mb-4">
          SLA Health
        </h2>
        <div className="flex items-center justify-center py-12">
          <Spinner size="lg" />
        </div>
      </div>
    )
  }

  const mttaMinutes =
    data?.mtta_seconds != null ? data.mtta_seconds / 60 : null
  const mttrMinutes =
    data?.mttr_seconds != null ? data.mttr_seconds / 60 : null

  return (
    <div className="bg-[var(--bg-secondary)] border border-[var(--border)] rounded-lg p-6">
      <h2 className="text-lg font-semibold text-[var(--text-primary)] mb-4 flex items-center gap-2">
        <AlertTriangle className="w-5 h-5 text-[var(--accent)]" />
        SLA Health
      </h2>

      {/* MTTA / MTTR stat cards */}
      <div className="grid grid-cols-2 gap-4 mb-6">
        {/* MTTA */}
        <div className="bg-[var(--bg-tertiary)] border border-[var(--border)] rounded-lg p-4 text-center">
          <div className="flex items-center justify-center gap-1.5 mb-2">
            <Clock className="w-4 h-4 text-[var(--text-secondary)]" />
            <span className="text-xs font-medium text-[var(--text-secondary)] uppercase tracking-wide">
              MTTA
            </span>
          </div>
          <p className="text-2xl font-bold text-[var(--text-primary)] tabular-nums">
            {mttaMinutes != null ? formatMinutes(mttaMinutes) : 'N/A'}
          </p>
          <p className="text-xs text-[var(--text-secondary)] mt-1">
            Mean Time to Acknowledge
          </p>
        </div>

        {/* MTTR */}
        <div className="bg-[var(--bg-tertiary)] border border-[var(--border)] rounded-lg p-4 text-center">
          <div className="flex items-center justify-center gap-1.5 mb-2">
            <Clock className="w-4 h-4 text-[var(--text-secondary)]" />
            <span className="text-xs font-medium text-[var(--text-secondary)] uppercase tracking-wide">
              MTTR
            </span>
          </div>
          <p className="text-2xl font-bold text-[var(--text-primary)] tabular-nums">
            {mttrMinutes != null ? formatMinutes(mttrMinutes) : 'N/A'}
          </p>
          <p className="text-xs text-[var(--text-secondary)] mt-1">
            Mean Time to Resolve
          </p>
        </div>
      </div>

      {/* Context info */}
      {(data?.group_name || data?.priority) && (
        <div className="text-xs text-[var(--text-secondary)] border-t border-[var(--border)] pt-3">
          <div className="flex items-center gap-4">
            {data.group_name && (
              <span>
                Group: <span className="text-[var(--text-primary)]">{data.group_name}</span>
              </span>
            )}
            {data.priority && (
              <span>
                Priority: <span className="text-[var(--text-primary)]">{data.priority}</span>
              </span>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
