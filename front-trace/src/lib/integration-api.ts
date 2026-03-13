import { authFetch } from '@/lib/auth-fetch'
import type {
  IntegrationCatalogItem,
  IntegrationConfig,
  InvoiceResolution,
  PaginatedSyncJobs,
  SyncJob,
  SyncLog,
} from '@/types/integration'

const BASE = import.meta.env.VITE_INTEGRATION_API_URL ?? 'http://localhost:9004'

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const res = await authFetch(`${BASE}${path}`, options)
  if (!res.ok) {
    const err = await res.json().catch(() => null)
    const msg = err?.detail ?? res.statusText
    throw new Error(msg)
  }
  return res.json()
}

export const integrationCatalogApi = {
  list: () => request<IntegrationCatalogItem[]>('/api/v1/integrations/catalog'),
}

export const integrationConfigApi = {
  list: () => request<IntegrationConfig[]>('/api/v1/integrations'),
  get: (id: string) => request<IntegrationConfig>(`/api/v1/integrations/${id}`),
  create: (data: Record<string, unknown>) =>
    request<IntegrationConfig>('/api/v1/integrations', { method: 'POST', body: JSON.stringify(data) }),
  update: (id: string, data: Record<string, unknown>) =>
    request<IntegrationConfig>(`/api/v1/integrations/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
  delete: async (id: string) => {
    await authFetch(`${BASE}/api/v1/integrations/${id}`, { method: 'DELETE' })
  },
  testConnection: (providerSlug: string, credentials?: Record<string, unknown>) =>
    request<{ ok: boolean; provider: string; message: string }>(
      `/api/v1/integrations/${providerSlug}/test`,
      { method: 'POST', body: credentials ? JSON.stringify({ credentials }) : undefined },
    ),
}

export const integrationSyncApi = {
  trigger: (providerSlug: string, body: { direction: string; entity_type: string }) =>
    request<SyncJob>(`/api/v1/integrations/${providerSlug}/sync`, { method: 'POST', body: JSON.stringify(body) }),
  listJobs: (params?: { provider_slug?: string; status?: string; offset?: number; limit?: number }) => {
    const qs = new URLSearchParams()
    if (params?.provider_slug) qs.set('provider_slug', params.provider_slug)
    if (params?.status) qs.set('status', params.status)
    if (params?.offset !== undefined) qs.set('offset', String(params.offset))
    if (params?.limit !== undefined) qs.set('limit', String(params.limit))
    return request<PaginatedSyncJobs>(`/api/v1/integrations/sync-jobs?${qs}`)
  },
  getJobLogs: (jobId: string) => request<SyncLog[]>(`/api/v1/integrations/sync-jobs/${jobId}/logs`),
}

export const integrationInvoiceApi = {
  create: (providerSlug: string, data: Record<string, unknown>) =>
    request<Record<string, unknown>>(`/api/v1/integrations/${providerSlug}/invoices`, { method: 'POST', body: JSON.stringify(data) }),
  get: (providerSlug: string, remoteId: string) =>
    request<Record<string, unknown>>(`/api/v1/integrations/${providerSlug}/invoices/${remoteId}`),
  list: (providerSlug: string, params?: { page?: number; page_size?: number }) => {
    const qs = new URLSearchParams()
    if (params?.page) qs.set('page', String(params.page))
    if (params?.page_size) qs.set('page_size', String(params.page_size))
    return request<Record<string, unknown>[]>(`/api/v1/integrations/${providerSlug}/invoices?${qs}`)
  },
}

export const resolutionApi = {
  get: (provider: string) =>
    request<InvoiceResolution>(`/api/v1/resolutions/${provider}`),
  create: (provider: string, data: Record<string, unknown>) =>
    request<InvoiceResolution>(`/api/v1/resolutions/${provider}`, { method: 'POST', body: JSON.stringify(data) }),
  deactivate: async (provider: string) => {
    await authFetch(`${BASE}/api/v1/resolutions/${provider}`, { method: 'DELETE' })
  },
}
