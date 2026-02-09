import { NavLink } from 'react-router-dom'
import {
  Cat,
  LayoutDashboard,
  Ticket,
  Users,
  Building2,
  Key,
  Clock,
} from 'lucide-react'
import { useAuth } from '@/context/AuthContext'

// ─── Nav item type ──────────────────────────────────────────────────────────

interface NavItem {
  label: string
  to: string
  icon: React.ReactNode
}

// ─── Link component ─────────────────────────────────────────────────────────

function SidebarLink({ to, icon, label }: NavItem) {
  return (
    <NavLink
      to={to}
      end={to === '/'}
      className={({ isActive }) =>
        [
          'flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-all duration-200',
          isActive
            ? 'bg-[var(--accent)]/10 text-[var(--accent)]'
            : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-tertiary)]',
        ].join(' ')
      }
    >
      {icon}
      <span>{label}</span>
    </NavLink>
  )
}

// ─── Main nav items ─────────────────────────────────────────────────────────

const mainNav: NavItem[] = [
  { label: 'Dashboard', to: '/', icon: <LayoutDashboard size={20} /> },
  { label: 'Tickets', to: '/tickets', icon: <Ticket size={20} /> },
]

// ─── Admin nav items ────────────────────────────────────────────────────────

const adminNav: NavItem[] = [
  { label: 'Users', to: '/admin/users', icon: <Users size={20} /> },
  { label: 'Groups', to: '/admin/groups', icon: <Building2 size={20} /> },
  { label: 'API Keys', to: '/admin/api-keys', icon: <Key size={20} /> },
  { label: 'SLA Config', to: '/admin/sla', icon: <Clock size={20} /> },
]

// ─── Sidebar ────────────────────────────────────────────────────────────────

export default function Sidebar() {
  const { user } = useAuth()
  const isAdmin = user?.role === 'admin'

  return (
    <aside className="fixed inset-y-0 left-0 w-64 bg-[var(--bg-secondary)] border-r border-[var(--border)] flex flex-col z-30">
      {/* Logo */}
      <div className="flex items-center gap-2.5 px-5 h-16 border-b border-[var(--border)] shrink-0">
        <Cat size={24} className="text-[var(--accent)]" />
        <span className="text-lg font-bold text-[var(--text-primary)] tracking-tight">
          ServiceMeow
        </span>
      </div>

      {/* Navigation */}
      <nav className="flex-1 overflow-y-auto px-3 py-4 space-y-1">
        {mainNav.map((item) => (
          <SidebarLink key={item.to} {...item} />
        ))}

        {isAdmin && (
          <>
            <div className="pt-6 pb-2 px-3">
              <span className="text-xs font-semibold uppercase tracking-wider text-[var(--text-secondary)]">
                Administration
              </span>
            </div>
            {adminNav.map((item) => (
              <SidebarLink key={item.to} {...item} />
            ))}
          </>
        )}
      </nav>
    </aside>
  )
}
