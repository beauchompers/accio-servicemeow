import { useState, useRef, useEffect } from 'react'
import { Sun, Moon, LogOut, Lock, Eye, EyeOff } from 'lucide-react'
import { useAuth } from '@/context/AuthContext'
import { useTheme } from '@/context/ThemeContext'
import { useChangePassword } from '@/hooks/useUsers'
import { useToast } from '@/components/ui/Toast'
import Button from '@/components/ui/Button'

// ─── Helpers ────────────────────────────────────────────────────────────────

function getInitials(name: string): string {
  return name
    .split(' ')
    .map((part) => part[0])
    .join('')
    .toUpperCase()
    .slice(0, 2)
}

function roleBadgeColor(role: string): string {
  switch (role) {
    case 'admin':
      return 'bg-red-500/15 text-red-400 border border-red-500/25'
    case 'manager':
      return 'bg-amber-500/15 text-amber-400 border border-amber-500/25'
    default:
      return 'bg-blue-500/15 text-blue-400 border border-blue-500/25'
  }
}

// ─── Change Password Panel ──────────────────────────────────────────────────

function ChangePasswordPanel({ onClose }: { onClose: () => void }) {
  const toast = useToast()
  const changePassword = useChangePassword()
  const panelRef = useRef<HTMLDivElement>(null)

  const [form, setForm] = useState({ current: '', newPw: '', confirm: '' })
  const [formErrors, setFormErrors] = useState<Record<string, string>>({})
  const [showCurrent, setShowCurrent] = useState(false)
  const [showNew, setShowNew] = useState(false)
  const [showConfirm, setShowConfirm] = useState(false)

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (panelRef.current && !panelRef.current.contains(event.target as Node)) {
        onClose()
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [onClose])

  function resetAndClose() {
    setForm({ current: '', newPw: '', confirm: '' })
    setFormErrors({})
    setShowCurrent(false)
    setShowNew(false)
    setShowConfirm(false)
    onClose()
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()

    const errors: Record<string, string> = {}
    if (!form.current) errors.current = 'Current password is required.'
    if (!form.newPw) errors.newPw = 'New password is required.'
    else if (form.newPw.length < 5) errors.newPw = 'New password must be at least 5 characters.'
    if (!form.confirm) errors.confirm = 'Confirm password is required.'
    else if (form.newPw && form.newPw !== form.confirm) errors.confirm = 'New passwords do not match.'
    if (Object.keys(errors).length > 0) {
      setFormErrors(errors)
      return
    }
    setFormErrors({})

    try {
      await changePassword.mutateAsync({
        current_password: form.current,
        new_password: form.newPw,
      })
      toast.success('Password changed successfully.')
      resetAndClose()
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Failed to change password.'
      toast.error(message)
    }
  }

  const inputClass =
    'w-full bg-[var(--bg-tertiary)] border border-[var(--border)] text-[var(--text-primary)] rounded-lg px-3 py-2 pr-10 placeholder:text-[var(--text-secondary)] focus:outline-none focus:ring-2 focus:ring-[var(--accent)]/50 focus:border-[var(--accent)] transition-colors duration-200'

  const toggleClass =
    'absolute right-3 top-1/2 -translate-y-1/2 text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition-colors duration-150'

  return (
    <div
      ref={panelRef}
      className="absolute right-0 top-full mt-2 w-80 bg-[var(--bg-secondary)] border border-[var(--border)] rounded-xl shadow-xl z-50 p-5"
    >
      <h3 className="text-sm font-semibold text-[var(--text-primary)] mb-4">Change Password</h3>
      <form onSubmit={handleSubmit}>
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-[var(--text-primary)] mb-1.5">
              Current Password <span className="text-red-400">*</span>
            </label>
            <div className="relative">
              <input
                type={showCurrent ? 'text' : 'password'}
                value={form.current}
                onChange={(e) => setForm((f) => ({ ...f, current: e.target.value }))}
                placeholder="Enter current password"
                className={inputClass}
              />
              <button
                type="button"
                onClick={() => setShowCurrent((prev) => !prev)}
                className={toggleClass}
                aria-label={showCurrent ? 'Hide password' : 'Show password'}
              >
                {showCurrent ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
              </button>
            </div>
            {formErrors.current && <p className="text-sm text-red-400 mt-1">{formErrors.current}</p>}
          </div>
          <div>
            <label className="block text-sm font-medium text-[var(--text-primary)] mb-1.5">
              New Password <span className="text-red-400">*</span>
            </label>
            <div className="relative">
              <input
                type={showNew ? 'text' : 'password'}
                value={form.newPw}
                onChange={(e) => setForm((f) => ({ ...f, newPw: e.target.value }))}
                placeholder="Enter new password"
                className={inputClass}
              />
              <button
                type="button"
                onClick={() => setShowNew((prev) => !prev)}
                className={toggleClass}
                aria-label={showNew ? 'Hide password' : 'Show password'}
              >
                {showNew ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
              </button>
            </div>
            {formErrors.newPw && <p className="text-sm text-red-400 mt-1">{formErrors.newPw}</p>}
          </div>
          <div>
            <label className="block text-sm font-medium text-[var(--text-primary)] mb-1.5">
              Confirm New Password <span className="text-red-400">*</span>
            </label>
            <div className="relative">
              <input
                type={showConfirm ? 'text' : 'password'}
                value={form.confirm}
                onChange={(e) => setForm((f) => ({ ...f, confirm: e.target.value }))}
                placeholder="Confirm new password"
                className={inputClass}
              />
              <button
                type="button"
                onClick={() => setShowConfirm((prev) => !prev)}
                className={toggleClass}
                aria-label={showConfirm ? 'Hide password' : 'Show password'}
              >
                {showConfirm ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
              </button>
            </div>
            {formErrors.confirm && <p className="text-sm text-red-400 mt-1">{formErrors.confirm}</p>}
          </div>
        </div>
        <div className="flex items-center justify-end gap-2 mt-5 pt-4 border-t border-[var(--border)]">
          <Button variant="secondary" onClick={resetAndClose} type="button">
            Cancel
          </Button>
          <Button variant="primary" loading={changePassword.isPending} type="submit">
            Change Password
          </Button>
        </div>
      </form>
    </div>
  )
}

// ─── TopBar ─────────────────────────────────────────────────────────────────

export default function TopBar() {
  const { user, logout } = useAuth()
  const { theme, toggleTheme } = useTheme()
  const [showPasswordPanel, setShowPasswordPanel] = useState(false)

  return (
    <header className="h-16 bg-[var(--bg-secondary)] border-b border-[var(--border)] flex items-center justify-between px-6 shrink-0">
      {/* Left side — intentionally empty; page titles are rendered by PageHeader inside the content area */}
      <div />

      {/* Right side */}
      <div className="flex items-center gap-4">
        {/* Theme toggle */}
        <button
          onClick={toggleTheme}
          className="p-2 rounded-lg text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-tertiary)] transition-all duration-200"
          aria-label="Toggle theme"
        >
          {theme === 'dark' ? <Sun size={20} /> : <Moon size={20} />}
        </button>

        {/* Change Password */}
        <div className="relative">
          <button
            onClick={() => setShowPasswordPanel((prev) => !prev)}
            className="p-2 rounded-lg text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-tertiary)] transition-all duration-200"
            aria-label="Change password"
          >
            <Lock size={20} />
          </button>
          {showPasswordPanel && (
            <ChangePasswordPanel onClose={() => setShowPasswordPanel(false)} />
          )}
        </div>

        {/* User display */}
        {user && (
          <div className="flex items-center gap-3">
            {/* Initials circle */}
            <div className="w-8 h-8 rounded-full bg-[var(--accent)] flex items-center justify-center text-xs font-bold text-white">
              {getInitials(user.full_name)}
            </div>

            {/* Name + role */}
            <div className="flex flex-col">
              <span className="text-sm font-medium text-[var(--text-primary)] leading-tight">
                {user.full_name}
              </span>
              <span
                className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${roleBadgeColor(user.role)}`}
              >
                {user.role}
              </span>
            </div>

            {/* Logout */}
            <button
              onClick={logout}
              className="p-2 rounded-lg text-[var(--text-secondary)] hover:text-red-400 hover:bg-[var(--bg-tertiary)] transition-all duration-200"
              aria-label="Logout"
            >
              <LogOut size={18} />
            </button>
          </div>
        )}
      </div>
    </header>
  )
}
