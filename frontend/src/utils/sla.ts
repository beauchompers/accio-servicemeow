import type { SlaStatus, MttaStatus } from '@/types'

export type SlaColor = 'green' | 'yellow' | 'red'

export function getSlaColor(percentage: number): SlaColor {
  if (percentage >= 80) return 'red'
  if (percentage >= 60) return 'yellow'
  return 'green'
}

export function getSlaColorClasses(color: SlaColor): string {
  switch (color) {
    case 'green':
      return 'text-emerald-400'
    case 'yellow':
      return 'text-amber-400'
    case 'red':
      return 'text-red-400'
  }
}

export function getSlaDoClasses(color: SlaColor): string {
  switch (color) {
    case 'green':
      return 'bg-emerald-400'
    case 'yellow':
      return 'bg-amber-400'
    case 'red':
      return 'bg-red-400'
  }
}

export function formatMinutes(minutes: number): string {
  const abs = Math.abs(minutes)
  if (abs < 1) return '< 1m'
  const h = Math.floor(abs / 60)
  const m = Math.round(abs % 60)
  if (h === 0) return `${m}m`
  if (m === 0) return `${h}h`
  return `${h}h ${m}m`
}

export function formatSlaRemaining(slaStatus: SlaStatus): string {
  if (slaStatus.target_minutes === null) return 'No SLA'
  if (slaStatus.remaining_minutes === null) return 'No SLA'

  // For resolved tickets, show outcome instead of remaining time
  if (slaStatus.is_resolved && slaStatus.outcome) {
    return slaStatus.outcome === 'within_sla' ? 'Within SLA' : 'Over SLA'
  }

  if (slaStatus.is_breached) {
    const overBy = Math.abs(slaStatus.remaining_minutes)
    return `Breached by ${formatMinutes(overBy)}`
  }

  return `${formatMinutes(slaStatus.remaining_minutes)} remaining`
}

export function formatMttaStatus(mttaStatus: MttaStatus): string {
  if (mttaStatus.is_met) return 'Within SLA'
  if (mttaStatus.is_breached && mttaStatus.is_pending) return 'Breached \u2014 unassigned'
  if (mttaStatus.is_breached) return 'Over SLA'

  // Still pending, not breached — show time remaining
  if (mttaStatus.target_minutes !== null) {
    const remaining = mttaStatus.target_minutes - mttaStatus.elapsed_minutes
    return `${formatMinutes(remaining)} remaining`
  }
  return 'No target'
}

export function getSlaOutcomeColor(slaStatus: SlaStatus): SlaColor {
  if (slaStatus.is_resolved && slaStatus.outcome === 'within_sla') return 'green'
  return getSlaColor(slaStatus.percentage)
}

export function formatSlaPercentage(percentage: number): string {
  return `${Math.round(percentage)}%`
}
