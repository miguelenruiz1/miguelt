/**
 * Media Service API client — centralized file management.
 * Points to media-service (port 9007) instead of trace-service.
 */
import { useAuthStore } from '@/store/auth'
import { ApiError } from '@/lib/api'
import type { MediaFile, PaginatedResponse } from '@/types/api'

const BASE = import.meta.env.VITE_API_URL ?? 'http://localhost:9000'

interface RequestOptions {
  params?: Record<string, string | number | undefined>
}

function headers(): Record<string, string> {
  const store = useAuthStore.getState()
  const h: Record<string, string> = {
    'X-Tenant-Id': store.user?.tenant_id ?? 'default',
  }
  // Auth bearer is REQUIRED — media-service has JWT auth enabled.
  if (store.accessToken) {
    h['Authorization'] = `Bearer ${store.accessToken}`
  }
  return h
}

async function request<T>(method: string, path: string, body?: unknown, opts: RequestOptions = {}): Promise<T> {
  const h: Record<string, string> = { ...headers(), 'Content-Type': 'application/json' }
  let url = `${BASE}${path}`
  if (opts.params) {
    const qs = new URLSearchParams()
    for (const [k, v] of Object.entries(opts.params)) {
      if (v !== undefined && v !== '') qs.set(k, String(v))
    }
    const s = qs.toString()
    if (s) url += `?${s}`
  }
  const res = await fetch(url, { method, headers: h, body: body != null ? JSON.stringify(body) : undefined })
  if (!res.ok) {
    const errBody = await res.json().catch(() => ({ error: { code: 'UNKNOWN', message: res.statusText } }))
    throw new ApiError(res.status, errBody)
  }
  if (res.status === 204) return undefined as T
  return res.json() as Promise<T>
}

async function requestMultipart<T>(method: string, path: string, formData: FormData, opts: RequestOptions = {}): Promise<T> {
  const h = headers()
  let url = `${BASE}${path}`
  if (opts.params) {
    const qs = new URLSearchParams()
    for (const [k, v] of Object.entries(opts.params)) {
      if (v !== undefined && v !== '') qs.set(k, String(v))
    }
    const s = qs.toString()
    if (s) url += `?${s}`
  }
  const res = await fetch(url, { method, headers: h, body: formData })
  if (!res.ok) {
    const errBody = await res.json().catch(() => ({ error: { code: 'UNKNOWN', message: res.statusText } }))
    throw new ApiError(res.status, errBody)
  }
  if (res.status === 204) return undefined as T
  return res.json() as Promise<T>
}

const get = <T>(path: string, opts?: RequestOptions) => request<T>('GET', path, undefined, opts)
const patch = <T>(path: string, body: unknown, opts?: RequestOptions) => request<T>('PATCH', path, body, opts)
const del = <T>(path: string, opts?: RequestOptions) => request<T>('DELETE', path, undefined, opts)

export const mediaApi = {
  upload: (file: File, opts?: { category?: string; document_type?: string; title?: string; description?: string; tags?: string }) => {
    const form = new FormData()
    form.append('file', file)
    return requestMultipart<MediaFile>(
      'POST', '/api/v1/media/files', form,
      { params: { category: opts?.category, document_type: opts?.document_type, title: opts?.title, description: opts?.description, tags: opts?.tags } },
    )
  },
  uploadBatch: (files: File[], opts?: { category?: string; document_type?: string }) => {
    const form = new FormData()
    for (const f of files) form.append('files', f)
    return requestMultipart<{ files: MediaFile[] }>(
      'POST', '/api/v1/media/files/batch', form,
      { params: { category: opts?.category, document_type: opts?.document_type } },
    )
  },
  list: (p?: { category?: string; document_type?: string; search?: string; offset?: number; limit?: number }) =>
    get<PaginatedResponse<MediaFile>>('/api/v1/media/files', { params: p }),
  get: (id: string) =>
    get<MediaFile>(`/api/v1/media/files/${id}`),
  update: (id: string, data: { title?: string; description?: string; category?: string; document_type?: string; tags?: string }) =>
    patch<MediaFile>(`/api/v1/media/files/${id}`, {}, { params: data }),
  delete: (id: string) =>
    del<void>(`/api/v1/media/files/${id}`),
}

/**
 * Fetch reference counts for media files across trace + compliance services.
 * Returns a map: { fileId: totalCount }
 */
export async function fetchMediaReferenceCounts(fileIds: string[]): Promise<Record<string, number>> {
  if (fileIds.length === 0) return {}
  const store = useAuthStore.getState()
  const gateway = import.meta.env.VITE_API_URL ?? 'http://localhost:9000'
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    'X-Tenant-Id': store.tenantId ?? 'default',
    'X-User-Id': store.user?.id ?? '1',
  }
  if (store.accessToken) headers['Authorization'] = `Bearer ${store.accessToken}`

  const [traceRes, compRes] = await Promise.allSettled([
    fetch(`${gateway}/api/v1/media/files/reference-counts`, {
      method: 'POST', headers, body: JSON.stringify(fileIds),
    }).then(r => r.ok ? r.json() : { counts: {} }),
    fetch(`${gateway}/api/v1/compliance/records/media-reference-counts`, {
      method: 'POST', headers, body: JSON.stringify(fileIds),
    }).then(r => r.ok ? r.json() : { counts: {} }),
  ])

  const traceCounts: Record<string, number> = traceRes.status === 'fulfilled' ? traceRes.value.counts : {}
  const compCounts: Record<string, number> = compRes.status === 'fulfilled' ? compRes.value.counts : {}

  const merged: Record<string, number> = {}
  for (const id of fileIds) {
    merged[id] = (traceCounts[id] ?? 0) + (compCounts[id] ?? 0)
  }
  return merged
}

/** Get the full URL for a media file (handles relative paths from local storage). */
export function mediaFileUrl(url: string): string {
  if (url.startsWith('http')) return url
  return `${BASE}${url}`
}
