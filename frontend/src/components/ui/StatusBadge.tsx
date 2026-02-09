import type { TicketStatus } from '@/types'
import { statusLabel } from '@/utils/format'

interface StatusBadgeProps {
  status: TicketStatus
}

const statusClasses: Record<TicketStatus, string> = {
  open: 'bg-blue-500/15 text-blue-400 border-blue-500/30',
  under_investigation: 'bg-amber-500/15 text-amber-400 border-amber-500/30',
  resolved: 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30',
}

export default function StatusBadge({ status }: StatusBadgeProps) {
  return (
    <span
      className={[
        'inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium border',
        'transition-all duration-200',
        statusClasses[status],
      ].join(' ')}
    >
      {statusLabel(status)}
    </span>
  )
}
