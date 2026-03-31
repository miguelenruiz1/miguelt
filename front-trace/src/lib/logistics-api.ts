/**
 * Logistics API client — connects to trace-service (logistics module).
 * Transport analytics and public verification.
 */
import { useAuthStore } from '@/store/auth'
import type {
  PublicBatchVerification,
  TransportAnalytics,
} from '@/types/logistics'

const BASE = import.meta.env.VITE_API_URL ?? 'http://localhost:9000'

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const store = useAuthStore.getState()
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    'X-Tenant-Id': store.tenantId ?? 'default',
    'X-User-Id': store.user?.id ?? '1',
    ...(options.headers as Record<string, string> || {}),
  }
  if (store.accessToken) {
    headers['Authorization'] = `Bearer ${store.accessToken}`
  }
  const res = await fetch(`${BASE}${path}`, { ...options, headers })
  if (!res.ok) {
    const err = await res.json().catch(() => null)
    throw new Error(err?.error?.message ?? err?.detail ?? `HTTP ${res.status}`)
  }
  if (res.status === 204) return undefined as T
  return res.json()
}

// ── Transport Analytics ──────────────────────────────────────────────────────

export const logisticsAnalyticsApi = {
  transport: (period: string = 'month') =>
    request<TransportAnalytics>(`/api/v1/analytics/transport?period=${period}`),
}

// ── Public Verification (no auth) ────────────────────────────────────────────

export const publicVerifyApi = {
  verifyBatch: (batchNumber: string, tenantId = 'default') =>
    fetch(`${BASE}/api/v1/public/batch/${encodeURIComponent(batchNumber)}/verify?tenant_id=${tenantId}`)
      .then(res => {
        if (!res.ok) throw new Error('Batch not found')
        return res.json() as Promise<PublicBatchVerification>
      }),
}
