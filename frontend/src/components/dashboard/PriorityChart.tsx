import { priorityLabel } from '@/utils/format'

// ─── Types ──────────────────────────────────────────────────────────────────

interface PriorityItem {
  priority: string
  count: number
}

interface PriorityChartProps {
  data: PriorityItem[]
}

// ─── Priority Colors ────────────────────────────────────────────────────────

const priorityColors: Record<string, string> = {
  critical: '#ef4444',
  high: '#f97316',
  medium: '#eab308',
  low: '#6b7280',
}

function getColor(priority: string): string {
  return priorityColors[priority.toLowerCase()] ?? '#6b7280'
}

// ─── PriorityChart ──────────────────────────────────────────────────────────

export default function PriorityChart({ data }: PriorityChartProps) {
  const total = data.reduce((sum, item) => sum + item.count, 0)

  // Sort by severity: critical, high, medium, low
  const order = ['critical', 'high', 'medium', 'low']
  const sorted = [...data].sort((a, b) => {
    const ai = order.indexOf(a.priority.toLowerCase())
    const bi = order.indexOf(b.priority.toLowerCase())
    return (ai === -1 ? 999 : ai) - (bi === -1 ? 999 : bi)
  })

  return (
    <div className="bg-[var(--bg-secondary)] border border-[var(--border)] rounded-lg p-6">
      <h2 className="text-lg font-semibold text-[var(--text-primary)] mb-4">
        Priority Distribution
      </h2>

      {total === 0 ? (
        <p className="text-sm text-[var(--text-secondary)] py-8 text-center">
          No ticket data available.
        </p>
      ) : (
        <>
          {/* Stacked horizontal bar */}
          <div className="w-full h-8 rounded-md overflow-hidden flex bg-[var(--bg-tertiary)]">
            {sorted.map((item) => {
              const pct = (item.count / total) * 100
              if (pct === 0) return null
              return (
                <div
                  key={item.priority}
                  className="h-full transition-all duration-500 relative group"
                  style={{
                    width: `${pct}%`,
                    backgroundColor: getColor(item.priority),
                    minWidth: pct > 0 ? '2px' : '0',
                  }}
                  title={`${priorityLabel(item.priority)}: ${item.count} (${pct.toFixed(1)}%)`}
                >
                  {/* Tooltip on hover */}
                  <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-2 py-1 bg-[var(--bg-primary)] border border-[var(--border)] rounded text-xs text-[var(--text-primary)] whitespace-nowrap opacity-0 group-hover:opacity-100 transition-opacity duration-150 pointer-events-none z-10">
                    {priorityLabel(item.priority)}: {item.count}
                  </div>
                </div>
              )
            })}
          </div>

          {/* Legend */}
          <div className="mt-4 flex flex-wrap gap-x-5 gap-y-2">
            {sorted.map((item) => {
              const pct = total > 0 ? (item.count / total) * 100 : 0
              return (
                <div key={item.priority} className="flex items-center gap-2">
                  <span
                    className="w-3 h-3 rounded-sm shrink-0"
                    style={{ backgroundColor: getColor(item.priority) }}
                  />
                  <span className="text-sm text-[var(--text-secondary)]">
                    {priorityLabel(item.priority)}
                  </span>
                  <span className="text-sm font-medium text-[var(--text-primary)] tabular-nums">
                    {item.count}
                  </span>
                  <span className="text-xs text-[var(--text-secondary)] tabular-nums">
                    ({pct.toFixed(1)}%)
                  </span>
                </div>
              )
            })}
          </div>
        </>
      )}
    </div>
  )
}
