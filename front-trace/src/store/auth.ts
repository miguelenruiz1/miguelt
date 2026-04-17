import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { AuthUser } from '@/types/auth'

interface AuthState {
  user: AuthUser | null
  accessToken: string | null
  refreshToken: string | null
  permissions: string[]
  // True once Zustand has finished reading localStorage. ProtectedRoute
  // waits on this so the first render doesn't flash `/login` before the
  // persisted token is available.
  _hasHydrated: boolean
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
      _hasHydrated: false,
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
      // `version` lets us invalidate stored state if the persisted schema
      // changes incompatibly. We intentionally do NOT wipe everything just
      // because the stored version is lower — an earlier bug did that and
      // logged every existing user out on deploy. The migration accepts
      // any shape that has the known field names; truly bogus shapes fall
      // back to a clean empty state.
      version: 1,
      migrate: (persisted) => {
        if (!persisted || typeof persisted !== 'object') {
          return {
            user: null,
            accessToken: null,
            refreshToken: null,
            permissions: [],
          } as Partial<AuthState>
        }
        const p = persisted as Record<string, unknown>
        return {
          user: (p.user as AuthUser | null) ?? null,
          accessToken: (p.accessToken as string | null) ?? null,
          refreshToken: (p.refreshToken as string | null) ?? null,
          permissions: Array.isArray(p.permissions) ? (p.permissions as string[]) : [],
        } as Partial<AuthState>
      },
      partialize: (state) => ({
        user: state.user,
        accessToken: state.accessToken,
        refreshToken: state.refreshToken,
        permissions: state.permissions,
      }),
      // Always flip `_hasHydrated` after a rehydrate attempt — even on error
      // — so ProtectedRoute never hangs waiting for a hydration that won't
      // come. The callback fires once, right after the storage read.
      onRehydrateStorage: () => () => {
        useAuthStore.setState({ _hasHydrated: true })
      },
    },
  ),
)
