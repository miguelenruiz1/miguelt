import { authFetch } from '@/lib/auth-fetch'
import type {
  PlatformDashboard,
  TenantListResponse,
  TenantDetail,
  PlatformAnalytics,
  SalesMetrics,
  OnboardRequest,
  PaymentLinkResult,
} from '@/types/platform'

const BASE = import.meta.env.VITE_SUBSCRIPTION_API_URL ?? 'http://localhost:9002'

async function request<T>(method: string, path: string, body?: unknown): Promise<T> {
  const res = await authFetch(`${BASE}${path}`, {
    method,
    body: body != null ? JSON.stringify(body) : undefined,
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail ?? res.statusText)
  }
  if (res.status === 204) return undefined as T
  return res.json() as Promise<T>
}

const get = <T>(path: string) => request<T>('GET', path)
const post = <T>(path: string, body: unknown) => request<T>('POST', path, body)

export interface PlatformUser {
  id: string
  email: string
  username: string | null
  full_name: string
  is_active: boolean
  is_superuser: boolean
  tenant_id: string
  created_at: string
  roles: { id: string; name: string; slug: string }[]
  permissions: string[]
}

export interface PaginatedUsers {
  items: PlatformUser[]
  total: number
  offset: number
  limit: number
}

export const platformApi = {
  // Dashboard & analytics
  dashboard: () => get<PlatformDashboard>('/api/v1/platform/dashboard'),
  analytics: (months = 6) => get<PlatformAnalytics>(`/api/v1/platform/analytics?months=${months}`),
  sales: () => get<SalesMetrics>('/api/v1/platform/sales'),

  // Tenant list & detail
  tenants: (params?: {
    search?: string
    status?: string
    plan_slug?: string
    offset?: number
    limit?: number
  }) => {
    const qs = new URLSearchParams()
    if (params) {
      for (const [k, v] of Object.entries(params)) {
        if (v != null && v !== '') qs.set(k, String(v))
      }
    }
    const q = qs.toString()
    return get<TenantListResponse>(`/api/v1/platform/tenants${q ? `?${q}` : ''}`)
  },
  tenantDetail: (tenantId: string) =>
    get<TenantDetail>(`/api/v1/platform/tenants/${tenantId}`),

  // Onboard
  onboardTenant: (data: OnboardRequest) =>
    post<{ tenant_id: string; subscription_id: string; plan: string; modules_activated: string[] }>(
      '/api/v1/platform/tenants/onboard', data
    ),

  // Tenant actions
  changePlan: (tenantId: string, planSlug: string) =>
    post<{ tenant_id: string; old_plan: string; new_plan: string }>(
      `/api/v1/platform/tenants/${tenantId}/change-plan`, { plan_slug: planSlug }
    ),
  toggleModule: (tenantId: string, moduleSlug: string, active: boolean) =>
    post<{ tenant_id: string; module: string; is_active: boolean }>(
      `/api/v1/platform/tenants/${tenantId}/modules/${moduleSlug}`, { active }
    ),
  generateInvoice: (tenantId: string) =>
    post<{ id: string; invoice_number: string; amount: number }>(
      `/api/v1/platform/tenants/${tenantId}/generate-invoice`, {}
    ),
  generatePaymentLink: (tenantId: string) =>
    post<PaymentLinkResult>(
      `/api/v1/platform/tenants/${tenantId}/generate-payment-link`, {}
    ),
  cancelSubscription: (tenantId: string, reason?: string) =>
    post<{ tenant_id: string; status: string }>(
      `/api/v1/platform/tenants/${tenantId}/cancel`, { reason }
    ),
  reactivateSubscription: (tenantId: string) =>
    post<{ tenant_id: string; status: string }>(
      `/api/v1/platform/tenants/${tenantId}/reactivate`, {}
    ),

  // Cross-tenant user oversight — calls user-service directly
  users: async (params?: { search?: string; tenant_id?: string; offset?: number; limit?: number }): Promise<PaginatedUsers> => {
    const USER_BASE = import.meta.env.VITE_USER_API_URL ?? 'http://localhost:9001'
    const qs = new URLSearchParams()
    if (params) {
      for (const [k, v] of Object.entries(params)) {
        if (v != null && v !== '') qs.set(k, String(v))
      }
    }
    const q = qs.toString()
    const { authFetch } = await import('@/lib/auth-fetch')
    const res = await authFetch(`${USER_BASE}/api/v1/users/all${q ? `?${q}` : ''}`)
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }))
      throw new Error(err.detail ?? res.statusText)
    }
    return res.json()
  },
}
