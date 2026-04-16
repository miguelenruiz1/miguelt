import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { AuthUser } from '@/types/auth'

interface AuthState {
  user: AuthUser | null
  accessToken: string | null
  refreshToken: string | null
  permissions: string[]
  setAuth: (user: AuthUser, accessToken: string, refreshToken: string, permissions: string[]) => void
  clearAuth: () => void
  hasPermission: (slug: string) => boolean
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      user: null,
      accessToken: null,
      refreshToken: null,
      permissions: [],
      setAuth: (user, accessToken, refreshToken, permissions) =>
        set({ user, accessToken, refreshToken, permissions }),
      clearAuth: () =>
        set({ user: null, accessToken: null, refreshToken: null, permissions: [] }),
      hasPermission: (slug: string) => {
        const state = get()
        if (state.user?.is_superuser) return true
        return state.permissions.includes(slug)
      },
    }),
    {
      name: 'trace-auth',
      // Bump whenever AuthUser shape or persisted fields change. Rehydration
      // from a lower version triggers `migrate`; an unrecognized shape is
      // wiped so the user re-logs in instead of crashing ProtectedRoute.
      version: 1,
      migrate: (persisted, version) => {
        if (version < 1 || !persisted || typeof persisted !== 'object') {
          return {
            user: null,
            accessToken: null,
            refreshToken: null,
            permissions: [],
          } as Partial<AuthState>
        }
        return persisted as Partial<AuthState>
      },
      partialize: (state) => ({
        user: state.user,
        accessToken: state.accessToken,
        refreshToken: state.refreshToken,
        permissions: state.permissions,
      }),
    },
  ),
)
