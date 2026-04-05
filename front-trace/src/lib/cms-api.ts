import { authFetch } from '@/lib/auth-fetch'

const BASE = import.meta.env.VITE_API_URL ?? 'http://localhost:9000'

// ─── Types ──────────────────────────────────────────────────────────────────

export interface CmsScript {
  id: string
  page_id: string
  src?: string
  inline_code?: string
  placement: 'head' | 'body_start' | 'body_end'
  load_strategy: 'async' | 'defer' | 'blocking'
  is_active: boolean
  created_at: string
}

export interface CmsSection {
  id: string
  page_id: string
  block_type: string
  position: number
  anchor_id?: string
  css_class?: string
  is_visible: boolean
  config: Record<string, any>
  created_at: string
  updated_at: string
}

export interface CmsPage {
  id: string
  tenant_id: string
  slug: string
  title: string
  lang: string
  status: 'draft' | 'published' | 'archived'
  seo_title?: string
  seo_description?: string
  seo_keywords?: string
  og_image?: string
  canonical_url?: string
  robots?: string
  navbar_config?: Record<string, any>
  footer_config?: Record<string, any>
  theme_overrides?: Record<string, string>
  sections: CmsSection[]
  scripts: CmsScript[]
  published_at?: string
  created_at: string
  updated_at: string
}

export interface CmsPageSummary {
  id: string
  slug: string
  title: string
  lang: string
  status: 'draft' | 'published' | 'archived'
  published_at?: string
  created_at: string
  updated_at: string
  section_count: number
}

export interface CreatePageRequest {
  title: string
  slug: string
  lang?: string
}

export interface UpdatePageRequest {
  title?: string
  slug?: string
  lang?: string
  seo_title?: string
  seo_description?: string
  seo_keywords?: string
  og_image?: string
  canonical_url?: string
  robots?: string
  navbar_config?: Record<string, any>
  footer_config?: Record<string, any>
  theme_overrides?: Record<string, string>
}

export interface AddSectionRequest {
  block_type: string
  position?: number
  anchor_id?: string
  css_class?: string
  config?: Record<string, any>
}

export interface UpdateSectionRequest {
  anchor_id?: string
  css_class?: string
  is_visible?: boolean
  config?: Record<string, any>
}

export interface CreateScriptRequest {
  src?: string
  inline_code?: string
  placement: 'head' | 'body_start' | 'body_end'
  load_strategy?: 'async' | 'defer' | 'blocking'
  is_active?: boolean
}

export interface UpdateScriptRequest {
  src?: string
  inline_code?: string
  placement?: 'head' | 'body_start' | 'body_end'
  load_strategy?: 'async' | 'defer' | 'blocking'
  is_active?: boolean
}

// ─── Auth request helper ────────────────────────────────────────────────────

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
const patch = <T>(path: string, body: unknown) => request<T>('PATCH', path, body)
const del = <T>(path: string) => request<T>('DELETE', path)

// ─── Admin API ──────────────────────────────────────────────────────────────

export const cmsApi = {
  // Pages
  listPages: () => get<CmsPageSummary[]>('/api/v1/cms/pages'),
  createPage: (data: CreatePageRequest) => post<CmsPage>('/api/v1/cms/pages', data),
  getPage: (id: string) => get<CmsPage>(`/api/v1/cms/pages/${id}`),
  updatePage: (id: string, data: UpdatePageRequest) => patch<CmsPage>(`/api/v1/cms/pages/${id}`, data),
  deletePage: (id: string) => del<void>(`/api/v1/cms/pages/${id}`),
  publishPage: (id: string) => post<CmsPage>(`/api/v1/cms/pages/${id}/publish`, {}),
  unpublishPage: (id: string) => post<CmsPage>(`/api/v1/cms/pages/${id}/unpublish`, {}),
  duplicatePage: (id: string) => post<CmsPage>(`/api/v1/cms/pages/${id}/duplicate`, {}),

  // Sections
  addSection: (pageId: string, data: AddSectionRequest) =>
    post<CmsSection>(`/api/v1/cms/pages/${pageId}/sections`, data),
  updateSection: (pageId: string, sectionId: string, data: UpdateSectionRequest) =>
    patch<CmsSection>(`/api/v1/cms/pages/${pageId}/sections/${sectionId}`, data),
  deleteSection: (pageId: string, sectionId: string) =>
    del<void>(`/api/v1/cms/pages/${pageId}/sections/${sectionId}`),
  reorderSections: (pageId: string, sectionIds: string[]) =>
    post<void>(`/api/v1/cms/pages/${pageId}/sections/reorder`, { section_ids: sectionIds }),

  // Scripts
  listScripts: (pageId: string) => get<CmsScript[]>(`/api/v1/cms/pages/${pageId}/scripts`),
  createScript: (pageId: string, data: CreateScriptRequest) =>
    post<CmsScript>(`/api/v1/cms/pages/${pageId}/scripts`, data),
  updateScript: (pageId: string, scriptId: string, data: UpdateScriptRequest) =>
    patch<CmsScript>(`/api/v1/cms/pages/${pageId}/scripts/${scriptId}`, data),
  deleteScript: (pageId: string, scriptId: string) =>
    del<void>(`/api/v1/cms/pages/${pageId}/scripts/${scriptId}`),
}

// ─── Public API (no auth) ───────────────────────────────────────────────────

export async function getPublicPage(slug: string): Promise<CmsPage | null> {
  const res = await fetch(`${BASE}/api/v1/cms/public/${slug}`)
  if (res.status === 404) return null
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail ?? res.statusText)
  }
  return res.json() as Promise<CmsPage>
}
