import type { ReactNode } from 'react'

// ─── Props ──────────────────────────────────────────────────────────────────

interface SummaryCardProps {
  title: string
  count: number
  borderColor: string
  icon: ReactNode
  onClick: () => void
}

// ─── SummaryCard ────────────────────────────────────────────────────────────

export default function SummaryCard({
  title,
  count,
  borderColor,
  icon,
  onClick,
}: SummaryCardProps) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="w-full text-left bg-[var(--bg-secondary)] border border-[var(--border)] rounded-lg p-5 transition-colors duration-200 hover:bg-[var(--bg-tertiary)] cursor-pointer group"
      style={{ borderLeftWidth: '4px', borderLeftColor: borderColor }}
    >
      <div className="flex items-start justify-between">
        <div>
          <p className="text-3xl font-bold text-[var(--text-primary)] tabular-nums">
            {count}
          </p>
          <p className="mt-1 text-sm font-medium text-[var(--text-secondary)]">
            {title}
          </p>
        </div>
        <div className="text-[var(--text-secondary)] opacity-60 group-hover:opacity-100 transition-opacity duration-200">
          {icon}
        </div>
      </div>
    </button>
  )
}
