import { useState, useLayoutEffect, useCallback } from 'react'
import { Outlet, useLocation } from 'react-router-dom'
import { Menu } from 'lucide-react'
import { Sidebar } from './Sidebar'
import { ToastContainer } from '@/components/ui/Toast'
import { ConfirmDialog } from '@/components/ui/ConfirmDialog'
import { useConfirmStore } from '@/store/confirm'

export function Layout() {
  const { pathname } = useLocation()
  const [sidebarOpen, setSidebarOpen] = useState(false)

  // Close mobile sidebar on navigation
  useLayoutEffect(() => {
    setSidebarOpen(false)
    document.body.style.overflow = ''
    document.body.style.pointerEvents = ''
    const { open, cancel } = useConfirmStore.getState()
    if (open) cancel()
  }, [pathname])

  const closeSidebar = useCallback(() => setSidebarOpen(false), [])

  return (
    <div className="flex h-dvh overflow-hidden bg-gray-50">
      {/* Mobile backdrop */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 z-30 bg-black/50 md:hidden"
          onClick={closeSidebar}
        />
      )}

      {/* Sidebar — hidden on mobile, shown as drawer when sidebarOpen */}
      <Sidebar open={sidebarOpen} onClose={closeSidebar} />

      <div className="flex-1 flex flex-col min-w-0 overflow-y-auto relative">
        {/* Mobile topbar with hamburger */}
        <div className="sticky top-0 z-20 flex items-center gap-3 px-4 py-3 bg-white border-b border-gray-200 md:hidden">
          <button
            onClick={() => setSidebarOpen(true)}
            className="flex items-center justify-center h-9 w-9 rounded-lg text-gray-600 hover:bg-gray-100 transition-colors"
            aria-label="Abrir menú"
          >
            <Menu className="h-5 w-5" />
          </button>
          <div className="flex items-center gap-2">
            <svg width="28" height="28" viewBox="0 0 34 34" fill="none" className="shrink-0">
              <rect width="34" height="34" rx="8" fill="#4F46E5" />
              <path d="M8 11h18v2.5H18.5V25H15V13.5H8V11Z" fill="white" />
              <path d="M20 17h2.5v5.5H27V25H20V17Z" fill="white" opacity="0.7" />
            </svg>
            <p className="text-base leading-none tracking-tight">
              <span className="font-bold text-gray-900">Trace</span>
              <span className="font-medium text-indigo-600">Log</span>
            </p>
          </div>
        </div>

        <div className="p-4 mx-auto w-full max-w-screen-2xl md:p-6">
          <Outlet />
        </div>
      </div>
      <ToastContainer />
      <ConfirmDialog />
    </div>
  )
}
