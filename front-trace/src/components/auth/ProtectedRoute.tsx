import { useLayoutEffect } from 'react'
import { Navigate } from 'react-router-dom'
import { useAuthStore } from '@/store/auth'
import { useConfirmStore } from '@/store/confirm'

interface ProtectedRouteProps {
  children: React.ReactNode
  permission?: string
  superuserOnly?: boolean
}

export function ProtectedRoute({ children, permission, superuserOnly }: ProtectedRouteProps) {
  const { accessToken, user, hasPermission } = useAuthStore()

  // Clear any stuck overlay/dialog state before painting
  useLayoutEffect(() => {
    const { open, cancel } = useConfirmStore.getState()
    if (open) cancel()
    document.body.style.overflow = ''
  }, [])

  if (!accessToken) {
    return <Navigate to="/login" replace />
  }

  if (superuserOnly && !user?.is_superuser) {
    return <Navigate to="/" replace />
  }

  if (permission && !hasPermission(permission)) {
    return <Navigate to="/" replace />
  }

  return <>{children}</>
}
