import { authFetch } from '@/lib/auth-fetch'
import type {
  ActiveGateway,
  GatewayCatalogItem,
  GatewayConfigOut,
  GatewayConfigSave,
} from '@/types/payments'

// ─── API Error ────────────────────────────────────────────────────────────────

export class PaymentsApiError extends Error {
  constructor(
    public readonly status: number,
    public readonly code: string,
    message: string,
  ) {
    super(message)
    this.name = 'PaymentsApiError'
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
    throw new PaymentsApiError(
      res.status,
      err.error?.code ?? 'UNKNOWN',
      err.error?.message ?? err.detail ?? res.statusText,
    )
  }

  if (res.status === 204) return undefined as T
  return res.json() as Promise<T>
}

const get  = <T>(path: string, auth = true) => request<T>('GET', path, undefined, auth)
const post = <T>(path: string, body: unknown) => request<T>('POST', path, body)
const del  = <T>(path: string) => request<T>('DELETE', path, undefined)

// ─── Typed API ────────────────────────────────────────────────────────────────

export const paymentsApi = {
  catalog: () =>
    get<GatewayCatalogItem[]>('/api/v1/payments/catalog', false),

  listConfigs: (tenantId: string) =>
    get<GatewayConfigOut[]>(`/api/v1/payments/${tenantId}`),

  saveConfig: (tenantId: string, slug: string, body: GatewayConfigSave) =>
    post<GatewayConfigOut>(`/api/v1/payments/${tenantId}/${slug}`, body),

  setActive: (tenantId: string, slug: string) =>
    post<GatewayConfigOut>(`/api/v1/payments/${tenantId}/${slug}/activate`, {}),

  deleteConfig: (tenantId: string, slug: string) =>
    del<{ deleted: boolean; slug: string }>(`/api/v1/payments/${tenantId}/${slug}`),

  getActive: (tenantId: string) =>
    get<ActiveGateway | null>(`/api/v1/payments/${tenantId}/active`, false),
}
