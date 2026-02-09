import {
  createContext,
  useContext,
  useState,
  useCallback,
  useEffect,
  type ReactNode,
} from 'react'
import { CheckCircle, XCircle, Info, X } from 'lucide-react'

// ─── Types ──────────────────────────────────────────────────────────────────

type ToastType = 'success' | 'error' | 'info'

interface ToastItem {
  id: number
  type: ToastType
  message: string
  visible: boolean
}

interface ToastApi {
  success: (message: string) => void
  error: (message: string) => void
  info: (message: string) => void
}

// ─── Context ────────────────────────────────────────────────────────────────

const ToastContext = createContext<ToastApi | null>(null)

let nextId = 0

// ─── Provider ───────────────────────────────────────────────────────────────

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<ToastItem[]>([])

  const removeToast = useCallback((id: number) => {
    setToasts((prev) =>
      prev.map((t) => (t.id === id ? { ...t, visible: false } : t)),
    )
    // Remove from DOM after transition
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id))
    }, 300)
  }, [])

  const addToast = useCallback(
    (type: ToastType, message: string) => {
      const id = nextId++
      setToasts((prev) => [...prev, { id, type, message, visible: true }])
      setTimeout(() => removeToast(id), 5000)
    },
    [removeToast],
  )

  const api: ToastApi = {
    success: (message: string) => addToast('success', message),
    error: (message: string) => addToast('error', message),
    info: (message: string) => addToast('info', message),
  }

  return (
    <ToastContext.Provider value={api}>
      {children}

      {/* Toast container */}
      <div className="fixed top-4 right-4 z-[100] flex flex-col gap-2 pointer-events-none">
        {toasts.map((toast) => (
          <ToastMessage
            key={toast.id}
            toast={toast}
            onClose={() => removeToast(toast.id)}
          />
        ))}
      </div>
    </ToastContext.Provider>
  )
}

// ─── Hook ───────────────────────────────────────────────────────────────────

export function useToast(): ToastApi {
  const ctx = useContext(ToastContext)
  if (!ctx) {
    throw new Error('useToast must be used within a ToastProvider')
  }
  return ctx
}

// ─── Individual toast ───────────────────────────────────────────────────────

const icons: Record<ToastType, ReactNode> = {
  success: <CheckCircle size={18} className="text-emerald-400 shrink-0" />,
  error: <XCircle size={18} className="text-red-400 shrink-0" />,
  info: <Info size={18} className="text-blue-400 shrink-0" />,
}

const borderColors: Record<ToastType, string> = {
  success: 'border-emerald-500/30',
  error: 'border-red-500/30',
  info: 'border-blue-500/30',
}

function ToastMessage({
  toast,
  onClose,
}: {
  toast: ToastItem
  onClose: () => void
}) {
  const [mounted, setMounted] = useState(false)

  useEffect(() => {
    // Trigger entrance animation on next frame
    requestAnimationFrame(() => setMounted(true))
  }, [])

  const isVisible = mounted && toast.visible

  return (
    <div
      className={[
        'pointer-events-auto flex items-center gap-3 px-4 py-3 rounded-lg border',
        'bg-[var(--bg-secondary)] shadow-lg max-w-sm w-full',
        'transition-all duration-300',
        borderColors[toast.type],
        isVisible
          ? 'opacity-100 translate-x-0'
          : 'opacity-0 translate-x-4',
      ].join(' ')}
    >
      {icons[toast.type]}
      <span className="flex-1 text-sm text-[var(--text-primary)]">
        {toast.message}
      </span>
      <button
        onClick={onClose}
        className="p-0.5 rounded text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition-all duration-200"
      >
        <X size={14} />
      </button>
    </div>
  )
}
