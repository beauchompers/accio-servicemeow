import { Link } from 'react-router-dom'
import { User, Bot, ArrowRight } from 'lucide-react'
import type { AuditLogEntry, ActorType } from '@/types'
import { relativeTime } from '@/utils/format'
import Spinner from '@/components/ui/Spinner'

// ─── Props ──────────────────────────────────────────────────────────────────

interface ActivityFeedProps {
  entries: AuditLogEntry[]
  isLoading: boolean
}

// ─── Helpers ────────────────────────────────────────────────────────────────

function actorIcon(actorType: ActorType) {
  if (actorType === 'user') {
    return <User className="w-4 h-4 text-[var(--accent)]" />
  }
  // 'system' and 'api_key' both get the Bot icon
  return <Bot className="w-4 h-4 text-emerald-400" />
}

// ─── ActivityFeed ───────────────────────────────────────────────────────────

export default function ActivityFeed({ entries, isLoading }: ActivityFeedProps) {
  return (
    <div className="bg-[var(--bg-secondary)] border border-[var(--border)] rounded-lg p-6">
      <h2 className="text-lg font-semibold text-[var(--text-primary)] mb-4">
        Recent Activity
      </h2>

      {isLoading ? (
        <div className="flex items-center justify-center py-12">
          <Spinner size="lg" />
        </div>
      ) : entries.length === 0 ? (
        <p className="text-sm text-[var(--text-secondary)] py-8 text-center">
          No recent activity.
        </p>
      ) : (
        <div className="max-h-96 overflow-y-auto space-y-1 pr-1 -mr-1">
          {entries.map((entry) => (
            <div
              key={entry.id}
              className="flex items-start gap-3 px-3 py-2.5 rounded-md hover:bg-[var(--bg-tertiary)] transition-colors duration-150"
            >
              {/* Actor icon */}
              <div className="mt-0.5 shrink-0 flex items-center justify-center w-7 h-7 rounded-full bg-[var(--bg-tertiary)] border border-[var(--border)]">
                {actorIcon(entry.actor_type)}
              </div>

              {/* Content */}
              <div className="flex-1 min-w-0">
                <p className="text-sm text-[var(--text-primary)] leading-snug">
                  <span className="font-medium">{entry.actor_name ?? entry.actor_type}</span>
                  {' '}{entry.action}
                  {entry.ticket_number && (
                    <>
                      {' on '}
                      <Link
                        to={`/tickets/${entry.ticket_id}`}
                        className="font-mono text-[var(--accent)] hover:underline"
                      >
                        {entry.ticket_number}
                      </Link>
                    </>
                  )}
                </p>

                {/* Field change details */}
                {entry.field_changed && (
                  <div className="mt-1 flex items-center gap-1.5 text-xs text-[var(--text-secondary)]">
                    <span className="font-medium">{entry.field_changed}:</span>
                    <span className="text-red-400/80 line-through truncate max-w-[120px]">
                      {entry.old_value ?? 'none'}
                    </span>
                    <ArrowRight className="w-3 h-3 shrink-0 text-[var(--text-secondary)]" />
                    <span className="text-emerald-400/80 truncate max-w-[120px]">
                      {entry.new_value ?? 'none'}
                    </span>
                  </div>
                )}
              </div>

              {/* Timestamp */}
              <span className="shrink-0 text-xs text-[var(--text-secondary)] mt-0.5 whitespace-nowrap">
                {relativeTime(entry.created_at)}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
