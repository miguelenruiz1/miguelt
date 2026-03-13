/**
 * Shared authenticated fetch utility with automatic token refresh.
 * When a request returns 401, attempts to refresh the access token once,
 * then retries the original request. If refresh fails, clears auth state.
 */
import { useAuthStore } from '@/store/auth'
import { useConfirmStore } from '@/store/confirm'

const USER_API = import.meta.env.VITE_USER_API_URL ?? 'http://localhost:9001'

let _refreshing: Promise<string | null> | null = null

async function refreshAccessToken(): Promise<string | null> {
  // Deduplicate concurrent refresh attempts
  if (_refreshing) return _refreshing

  _refreshing = (async () => {
    const { refreshToken, user, permissions } = useAuthStore.getState()
    if (!refreshToken) return null

    try {
      const res = await fetch(`${USER_API}/api/v1/auth/refresh`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh_token: refreshToken }),
      })
      if (!res.ok) {
        useAuthStore.getState().clearAuth()
        useConfirmStore.getState().cancel()
        document.body.style.overflow = ''
        return null
      }
      const data = await res.json()
      const newAccess: string = data.access_token
      const newRefresh: string = data.refresh_token ?? refreshToken
      const newPerms: string[] = data.permissions ?? permissions
      if (user && newAccess) {
        useAuthStore.getState().setAuth(user, newAccess, newRefresh, newPerms)
        return newAccess
      }
      return null
    } catch {
      useAuthStore.getState().clearAuth()
      useConfirmStore.getState().cancel()
      document.body.style.overflow = ''
      return null
    } finally {
      _refreshing = null
    }
  })()

  return _refreshing
}

/**
 * Wrapper around fetch that:
 * 1. Adds Authorization header from auth store when `auth=true`
 * 2. On 401, tries to refresh the access token once and retries
 * 3. On failed refresh, clears auth state
 */
export async function authFetch(
  url: string,
  options: RequestInit = {},
  auth = true,
): Promise<Response> {
  const buildHeaders = (token?: string | null): Record<string, string> => {
    const h: Record<string, string> = { 'Content-Type': 'application/json' }
    const t = token ?? (auth ? useAuthStore.getState().accessToken : null)
    if (t) h['Authorization'] = `Bearer ${t}`
    return h
  }

  const res = await fetch(url, {
    ...options,
    headers: { ...buildHeaders(), ...(options.headers as Record<string, string> ?? {}) },
  })

  if (res.status === 401 && auth) {
    const newToken = await refreshAccessToken()
    if (newToken) {
      return fetch(url, {
        ...options,
        headers: { ...buildHeaders(newToken), ...(options.headers as Record<string, string> ?? {}) },
      })
    }
  }

  return res
}
