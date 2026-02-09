import type { ReactNode } from 'react'

// ─── Props ──────────────────────────────────────────────────────────────────

interface PageHeaderProps {
  title: string
  description?: string
  actions?: ReactNode
}

// ─── PageHeader ─────────────────────────────────────────────────────────────

export default function PageHeader({ title, description, actions }: PageHeaderProps) {
  return (
    <div className="flex items-start justify-between gap-4 mb-6">
      <div>
        <h1 className="text-2xl font-bold text-[var(--text-primary)]">{title}</h1>
        {description && (
          <p className="mt-1 text-sm text-[var(--text-secondary)]">{description}</p>
        )}
      </div>
      {actions && <div className="flex items-center gap-2 shrink-0">{actions}</div>}
    </div>
  )
}
