import type { ModuleDefinition, TenantModuleStatus } from '@/types/modules'
import { authFetch } from '@/lib/auth-fetch'

const BASE = import.meta.env.VITE_API_URL ?? 'http://localhost:9000'

async function request<T>(path: string, options: RequestInit = {}, auth = true): Promise<T> {
  const res = await authFetch(`${BASE}${path}`, options, auth)
  if (!res.ok) {
    const err = await res.json().catch(() => ({ error: { message: res.statusText } }))
    throw new Error(err?.error?.message ?? res.statusText)
  }
  return res.json()
}

export const modulesApi = {
  catalog: () => request<ModuleDefinition[]>('/api/v1/modules/', {}, false),
  forTenant: (tenantId: string) =>
    request<TenantModuleStatus[]>(`/api/v1/modules/${tenantId}`, {}, false),
  /** Public — no auth required. Used for sidebar module gate checks. */
  checkModule: (tenantId: string, slug: string) =>
    request<{ tenant_id: string; slug: string; is_active: boolean }>(
      `/api/v1/modules/${tenantId}/${slug}`,
      {},
      false,
    ),
  activate: (tenantId: string, slug: string) =>
    request<{ tenant_id: string; slug: string; is_active: boolean }>(
      `/api/v1/modules/${tenantId}/${slug}/activate`,
      { method: 'POST' },
    ),
  deactivate: (tenantId: string, slug: string) =>
    request<{ tenant_id: string; slug: string; is_active: boolean }>(
      `/api/v1/modules/${tenantId}/${slug}/deactivate`,
      { method: 'POST' },
    ),
}
