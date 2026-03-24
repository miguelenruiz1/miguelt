import { authFetch } from '@/lib/auth-fetch'
import { usePlanLimitStore } from '@/store/planLimit'
import type {
  CheckoutRequest,
  CheckoutResponse,
  Invoice,
  OverviewMetrics,
  PaginatedResponse,
  Plan,
  PlanCreate,
  PlanUpdate,
  Subscription,
  SubscriptionCreate,
  SubscriptionEvent,
  UsageSummary,
} from '@/types/subscription'

// ─── API Error ────────────────────────────────────────────────────────────────

export class SubApiError extends Error {
  constructor(
    public readonly status: number,
    public readonly code: string,
    message: string,
  ) {
    super(message)
    this.name = 'SubApiError'
  }
}

// ─── Base fetch ───────────────────────────────────────────────────────────────

const BASE = import.meta.env.VITE_SUBSCRIPTION_API_URL ?? 'http://localhost:9002'

async function request<T>(
  method: string,
  path: string,
  body?: unknown,
  auth = true,
): Promise<T> {
  const res = await authFetch(
    `${BASE}${path}`,
    {
      method,
      body: body != null ? JSON.stringify(body) : undefined,
    },
    auth,
  )

  if (!res.ok) {
    const err = await res.json().catch(() => ({ error: { code: 'UNKNOWN', message: res.statusText } }))

    if (res.status === 402) {
      usePlanLimitStore.getState().open({
        resource: err.resource ?? 'recurso',
        current: err.current ?? 0,
        limit: err.limit ?? 0,
        message: err.error?.message ?? 'Has alcanzado el limite de tu plan actual.',
      })
    }

    throw new SubApiError(res.status, err.error?.code ?? 'UNKNOWN', err.error?.message ?? res.statusText)
  }

  if (res.status === 204) return undefined as T
  return res.json() as Promise<T>
}

const get = <T>(path: string, auth = true) => request<T>('GET', path, undefined, auth)
const post = <T>(path: string, body: unknown, auth = true) => request<T>('POST', path, body, auth)
const patch = <T>(path: string, body: unknown) => request<T>('PATCH', path, body)
const del = <T>(path: string) => request<T>('DELETE', path, undefined)

// ─── Typed API ────────────────────────────────────────────────────────────────

export const subscriptionApi = {
  plans: {
    list: (includeArchived = false) =>
      get<Plan[]>(`/api/v1/plans?include_archived=${includeArchived}`),
    get: (id: string) => get<Plan>(`/api/v1/plans/${id}`),
    create: (data: PlanCreate) => post<Plan>('/api/v1/plans/', data),
    update: (id: string, data: PlanUpdate) => patch<Plan>(`/api/v1/plans/${id}`, data),
    archive: (id: string) => del<void>(`/api/v1/plans/${id}`),
  },

  subscriptions: {
    list: (params?: {
      status?: string
      plan_id?: string
      tenant_id?: string
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
      return get<PaginatedResponse<Subscription>>(`/api/v1/subscriptions${q ? `?${q}` : ''}`)
    },
    get: (tenantId: string) => get<Subscription>(`/api/v1/subscriptions/${tenantId}`),
    create: (data: SubscriptionCreate) => post<Subscription>('/api/v1/subscriptions/', data),
    upgrade: (tenantId: string, planSlug: string) =>
      patch<Subscription>(`/api/v1/subscriptions/${tenantId}`, { plan_slug: planSlug }),
    cancel: (tenantId: string, reason?: string) =>
      post<void>(`/api/v1/subscriptions/${tenantId}/cancel`, { reason }),
    reactivate: (tenantId: string) =>
      post<Subscription>(`/api/v1/subscriptions/${tenantId}/reactivate`, {}),
    listInvoices: (tenantId: string) =>
      get<Invoice[]>(`/api/v1/subscriptions/${tenantId}/invoices`),
    generateInvoice: (tenantId: string) =>
      post<Invoice>(`/api/v1/subscriptions/${tenantId}/invoices`, {}),
    markPaid: (tenantId: string, invId: string, notes?: string) =>
      patch<Invoice>(`/api/v1/subscriptions/${tenantId}/invoices/${invId}/mark-paid`, { notes }),
    listEvents: (tenantId: string) =>
      get<SubscriptionEvent[]>(`/api/v1/subscriptions/${tenantId}/events`),
  },

  usage: {
    get: (tenantId: string) =>
      get<UsageSummary>(`/api/v1/usage/${tenantId}`),
  },

  checkout: {
    create: (data: CheckoutRequest) =>
      post<CheckoutResponse>('/api/v1/payments/checkout', data),
    getInvoices: (tenantId: string) =>
      get<Invoice[]>(`/api/v1/subscriptions/${tenantId}/invoices`),
  },

  admin: {
    getMetrics: () => get<OverviewMetrics>('/api/v1/admin/metrics/overview'),
  },
}
