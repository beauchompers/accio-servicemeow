import type { SlaStatus } from '@/types'
import {
  getSlaDoClasses,
  getSlaColorClasses,
  formatSlaRemaining,
  getSlaOutcomeColor,
} from '@/utils/sla'

interface SlaIndicatorProps {
  slaStatus: SlaStatus | null
}

export default function SlaIndicator({ slaStatus }: SlaIndicatorProps) {
  if (!slaStatus || slaStatus.target_minutes === null) {
    return (
      <span className="text-xs text-[var(--text-secondary)]">No SLA</span>
    )
  }

  const color = getSlaOutcomeColor(slaStatus)
  const dotClass = getSlaDoClasses(color)
  const textClass = getSlaColorClasses(color)
  const label = formatSlaRemaining(slaStatus)

  return (
    <span className="inline-flex items-center gap-1.5">
      <span
        className={['h-2 w-2 rounded-full shrink-0', dotClass].join(' ')}
      />
      <span className={['text-xs font-medium', textClass].join(' ')}>
        {label}
      </span>
    </span>
  )
}
