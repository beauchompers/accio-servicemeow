import type { TicketPriority } from '@/types'
import { priorityLabel } from '@/utils/format'

interface PriorityBadgeProps {
  priority: TicketPriority
}

const dotClasses: Record<TicketPriority, string> = {
  critical: 'bg-red-500 animate-pulse',
  high: 'bg-red-500',
  medium: 'bg-yellow-500',
  low: 'bg-slate-400',
}

const textClasses: Record<TicketPriority, string> = {
  critical: 'text-red-400',
  high: 'text-red-400',
  medium: 'text-yellow-400',
  low: 'text-slate-400',
}

export default function PriorityBadge({ priority }: PriorityBadgeProps) {
  return (
    <span className="inline-flex items-center gap-1.5">
      <span
        className={['h-2 w-2 rounded-full shrink-0', dotClasses[priority]].join(
          ' ',
        )}
      />
      <span className={['text-xs font-medium', textClasses[priority]].join(' ')}>
        {priorityLabel(priority)}
      </span>
    </span>
  )
}
