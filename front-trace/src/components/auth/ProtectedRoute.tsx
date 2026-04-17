import { useLayoutEffect } from 'react'
import { Navigate, useLocation } from 'react-router-dom'
import { useAuthStore } from '@/store/auth'
import { useConfirmStore } from '@/store/confirm'

interface ProtectedRouteProps {
  children: React.ReactNode
  permission?: string
  superuserOnly?: boolean
}

export function ProtectedRoute({ children, permission, superuserOnly }: ProtectedRouteProps) {
  const { accessToken, user, hasPermission, _hasHydrated } = useAuthStore()
  const location = useLocation()

  // Clear any stuck overlay/dialog state before painting
  useLayoutEffect(() => {
    const { open, cancel } = useConfirmStore.getState()
    if (open) cancel()
    document.body.style.overflow = ''
  }, [])

  // Zustand `persist` reads localStorage asynchronously. Before that read
  // completes `accessToken` is null even when the user is logged in, so a
  // naive check redirects to /login and flashes the login page for a tick.
  // Block render until rehydration finishes.
  if (!_hasHydrated) {
    return null
  }

  if (!accessToken) {
    // Show landing page at root, login for any other protected route
    if (location.pathname === '/') {
      return <Navigate to="/home" replace />
    }
    return <Navigate to="/login" replace />
  }

  // Redirect to onboarding if not completed (skip for /onboarding itself)
  if (
    user &&
    user.onboarding_completed === false &&
    location.pathname !== '/onboarding'
  ) {
    return <Navigate to="/onboarding" replace />
  }

  if (superuserOnly && !user?.is_superuser) {
    return <Navigate to="/" replace />
  }

  if (permission && !hasPermission(permission)) {
    return <Navigate to="/" replace />
  }

  return <>{children}</>
}
