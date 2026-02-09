import { Outlet } from 'react-router-dom'
import Sidebar from '@/components/layout/Sidebar'
import TopBar from '@/components/layout/TopBar'

// ─── AppShell ───────────────────────────────────────────────────────────────

export default function AppShell() {
  return (
    <div className="min-h-screen bg-[var(--bg-primary)]">
      {/* Fixed sidebar */}
      <Sidebar />

      {/* Main content area — offset by sidebar width */}
      <div className="ml-64 flex flex-col min-h-screen">
        <TopBar />

        <main className="flex-1 p-6">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
