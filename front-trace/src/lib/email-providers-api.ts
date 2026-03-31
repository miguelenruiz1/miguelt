import { authFetch } from '@/lib/auth-fetch'
import { useAuthStore } from '@/store/auth'
import type {
  EmailProviderCatalogItem,
  EmailProviderConfigOut,
  EmailProviderConfigSave,
  TestEmailResult,
} from '@/types/email-providers'

// ─── API Error ────────────────────────────────────────────────────────────────

export class EmailProvidersApiError extends Error {
  constructor(
    public readonly status: number,
    public readonly code: string,
    message: string,
  ) {
    super(message)
    this.name = 'EmailProvidersApiError'
  }
}

// ─── Base fetch ───────────────────────────────────────────────────────────────

const BASE = import.meta.env.VITE_API_URL ?? 'http://localhost:9000'

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
      headers: { 'X-Tenant-Id': useAuthStore.getState().user?.tenant_id ?? 'default' },
    },
    auth,
  )

  if (!res.ok) {
    const err = await res.json().catch(() => ({ error: { code: 'UNKNOWN', message: res.statusText } }))
    throw new EmailProvidersApiError(
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

export const emailProvidersApi = {
  catalog: () =>
    get<EmailProviderCatalogItem[]>('/api/v1/email-providers/catalog', false),

  listConfigs: () =>
    get<EmailProviderConfigOut[]>('/api/v1/email-providers/'),

  saveConfig: (slug: string, body: EmailProviderConfigSave) =>
    post<EmailProviderConfigOut>(`/api/v1/email-providers/${slug}`, body),

  setActive: (slug: string) =>
    post<EmailProviderConfigOut>(`/api/v1/email-providers/${slug}/activate`, {}),

  deleteConfig: (slug: string) =>
    del<{ deleted: boolean; slug: string }>(`/api/v1/email-providers/${slug}`),

  testProvider: (slug: string, to: string) =>
    post<TestEmailResult>(`/api/v1/email-providers/${slug}/test`, { to }),
}
