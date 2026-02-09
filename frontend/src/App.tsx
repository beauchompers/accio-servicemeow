import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ThemeProvider } from '@/context/ThemeContext'
import { AuthProvider, useAuth } from '@/context/AuthContext'
import { ToastProvider } from '@/components/ui/Toast'
import AppShell from '@/components/layout/AppShell'
import Login from '@/pages/Login'
import Dashboard from '@/pages/Dashboard'
import TicketList from '@/pages/TicketList'
import TicketCreate from '@/pages/TicketCreate'
import TicketDetail from '@/pages/TicketDetail'
import Users from '@/pages/admin/Users'
import Groups from '@/pages/admin/Groups'
import ApiKeys from '@/pages/admin/ApiKeys'
import SlaConfig from '@/pages/admin/SlaConfig'

// ─── Query client ───────────────────────────────────────────────────────────

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
})

// ─── Route guards ───────────────────────────────────────────────────────────

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, isLoading } = useAuth()

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-screen bg-[var(--bg-primary)]">
        <div className="text-[var(--text-secondary)] text-sm">Loading...</div>
      </div>
    )
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />
  }

  return <>{children}</>
}

function AdminRoute({ children }: { children: React.ReactNode }) {
  const { user } = useAuth()

  if (user?.role !== 'admin') {
    return (
      <div className="flex flex-col items-center justify-center py-20">
        <h2 className="text-xl font-semibold text-[var(--text-primary)]">403 — Forbidden</h2>
        <p className="mt-2 text-sm text-[var(--text-secondary)]">
          You do not have permission to access this page.
        </p>
      </div>
    )
  }

  return <>{children}</>
}

// ─── App ────────────────────────────────────────────────────────────────────

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider>
        <AuthProvider>
          <ToastProvider>
            <BrowserRouter>
              <Routes>
                {/* Public */}
                <Route path="/login" element={<Login />} />

                {/* Protected — wrapped in AppShell layout */}
                <Route
                  element={
                    <ProtectedRoute>
                      <AppShell />
                    </ProtectedRoute>
                  }
                >
                  <Route index element={<Dashboard />} />
                  <Route path="tickets" element={<TicketList />} />
                  <Route path="tickets/new" element={<TicketCreate />} />
                  <Route path="tickets/:id" element={<TicketDetail />} />

                  {/* Admin routes */}
                  <Route
                    path="admin/users"
                    element={
                      <AdminRoute>
                        <Users />
                      </AdminRoute>
                    }
                  />
                  <Route
                    path="admin/groups"
                    element={
                      <AdminRoute>
                        <Groups />
                      </AdminRoute>
                    }
                  />
                  <Route
                    path="admin/api-keys"
                    element={
                      <AdminRoute>
                        <ApiKeys />
                      </AdminRoute>
                    }
                  />
                  <Route
                    path="admin/sla"
                    element={
                      <AdminRoute>
                        <SlaConfig />
                      </AdminRoute>
                    }
                  />
                </Route>

                {/* Catch-all */}
                <Route path="*" element={<Navigate to="/" replace />} />
              </Routes>
            </BrowserRouter>
          </ToastProvider>
        </AuthProvider>
      </ThemeProvider>
    </QueryClientProvider>
  )
}
