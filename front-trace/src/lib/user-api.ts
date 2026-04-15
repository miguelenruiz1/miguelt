import type {
  AuthUser,
  AuditEvent,
  EmailConfig,
  EmailTemplate,
  InviteUserRequest,
  LoginResponse,
  Permission,
  PaginatedResponse,
  Role,
  RoleTemplate,
} from '@/types/auth'
import { useAuthStore } from '@/store/auth'

// ─── API Error ────────────────────────────────────────────────────────────────

export class UserApiError extends Error {
  constructor(
    public readonly status: number,
    public readonly code: string,
    message: string,
  ) {
    super(message)
    this.name = 'UserApiError'
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
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    'X-Tenant-Id': useAuthStore.getState().user?.tenant_id ?? 'default',
  }

  if (auth) {
    const token = useAuthStore.getState().accessToken
    if (token) headers['Authorization'] = `Bearer ${token}`
  }

  const res = await fetch(`${BASE}${path}`, {
    method,
    headers,
    body: body != null ? JSON.stringify(body) : undefined,
  })

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    const d = err.detail
    let msg: string
    if (typeof d === 'string' && d.trim()) msg = d
    else if (Array.isArray(d)) {
      msg = d.map((it: any) => {
        if (typeof it === 'string') return it
        const loc = Array.isArray(it?.loc) ? it.loc.filter((x: any) => x !== 'body').join('.') : ''
        const m = it?.msg ?? it?.message ?? ''
        return loc ? `${loc}: ${m}` : m
      }).filter(Boolean).join(' · ') || res.statusText
    }
    else if (d && typeof d === 'object' && typeof (d as any).message === 'string') msg = (d as any).message
    else msg = err.error?.message ?? err.message ?? res.statusText
    const code = err.error?.code ?? err.code ?? 'ERROR'
    throw new UserApiError(res.status, code, msg)
  }

  if (res.status === 204) return undefined as T
  return res.json() as Promise<T>
}

const get = <T>(path: string, auth = true) => request<T>('GET', path, undefined, auth)
const post = <T>(path: string, body: unknown, auth = true) => request<T>('POST', path, body, auth)
const patch = <T>(path: string, body: unknown) => request<T>('PATCH', path, body)
const put = <T>(path: string, body: unknown) => request<T>('PUT', path, body)
const del = <T>(path: string) => request<T>('DELETE', path, undefined)

// ─── Typed API ────────────────────────────────────────────────────────────────

export const userApi = {
  auth: {
    register: (data: {
      email: string; username: string; full_name: string; password: string;
      phone?: string; job_title?: string; company?: string; tenant_id?: string;
    }) => post<AuthUser>('/api/v1/auth/register', data, false),
    login: (data: { email: string; password: string }) =>
      post<LoginResponse>('/api/v1/auth/login', data, false),
    logout: () => post<void>('/api/v1/auth/logout', {}),
    me: () => get<AuthUser>('/api/v1/auth/me'),
    updateMe: (data: Partial<{
      full_name: string; username: string; email: string; avatar_url: string;
      phone: string; job_title: string; company: string; bio: string;
      timezone: string; language: string;
    }>) => patch<AuthUser>('/api/v1/auth/me', data),
    changePassword: (data: { current_password: string; new_password: string }) =>
      patch<void>('/api/v1/auth/me/password', data),
    uploadAvatar: async (file: File) => {
      const form = new FormData()
      form.append('file', file)
      const headers: Record<string, string> = {
        'X-Tenant-Id': useAuthStore.getState().user?.tenant_id ?? 'default',
      }
      const token = useAuthStore.getState().accessToken
      if (token) headers['Authorization'] = `Bearer ${token}`
      const res = await fetch(`${BASE}/api/v1/auth/me/avatar`, {
        method: 'POST',
        headers,
        body: form,
      })
      if (!res.ok) {
        const err = await res.json().catch(() => ({ error: { code: 'UNKNOWN', message: res.statusText } }))
        throw new UserApiError(res.status, err.error?.code ?? 'UNKNOWN', err.error?.message ?? err.detail ?? res.statusText)
      }
      return res.json() as Promise<AuthUser>
    },
    deleteAvatar: () => del<AuthUser>('/api/v1/auth/me/avatar'),
    refresh: (refresh_token: string) =>
      post<LoginResponse>('/api/v1/auth/refresh', { refresh_token }, false),
    acceptInvitation: (data: { token: string; password: string }) =>
      post<AuthUser>('/api/v1/auth/accept-invitation', data, false),
    forgotPassword: (email: string) =>
      post<{ detail: string }>('/api/v1/auth/forgot-password', { email }, false),
    resetPassword: (data: { token: string; new_password: string }) =>
      post<AuthUser>('/api/v1/auth/reset-password', data, false),
  },

  users: {
    invite: (data: InviteUserRequest) =>
      post<AuthUser>('/api/v1/users', data),
    list: (params?: { offset?: number; limit?: number }) => {
      const qs = new URLSearchParams()
      if (params?.offset != null) qs.set('offset', String(params.offset))
      if (params?.limit != null) qs.set('limit', String(params.limit))
      const q = qs.toString()
      return get<PaginatedResponse<AuthUser>>(`/api/v1/users${q ? `?${q}` : ''}`)
    },
    get: (id: string) => get<AuthUser>(`/api/v1/users/${id}`),
    update: (id: string, data: Partial<AuthUser>) => patch<AuthUser>(`/api/v1/users/${id}`, data),
    resendInvitation: (id: string) => post<AuthUser>(`/api/v1/users/${id}/resend-invitation`, {}),
    deactivate: (id: string) => post<AuthUser>(`/api/v1/users/${id}/deactivate`, {}),
    reactivate: (id: string) => post<AuthUser>(`/api/v1/users/${id}/reactivate`, {}),
    assignRole: (userId: string, roleId: string) =>
      post<void>(`/api/v1/users/${userId}/roles/${roleId}`, {}),
    removeRole: (userId: string, roleId: string) =>
      del<void>(`/api/v1/users/${userId}/roles/${roleId}`),
  },

  roles: {
    list: () => get<Role[]>('/api/v1/roles'),
    get: (id: string) => get<Role>(`/api/v1/roles/${id}`),
    create: (data: { name: string; slug: string; description?: string }) =>
      post<Role>('/api/v1/roles', data),
    update: (id: string, data: Partial<{ name: string; description: string }>) =>
      patch<Role>(`/api/v1/roles/${id}`, data),
    delete: (id: string) => del<void>(`/api/v1/roles/${id}`),
    getPermissions: (id: string) => get<Permission[]>(`/api/v1/roles/${id}/permissions`),
    setPermissions: (id: string, permission_ids: string[]) =>
      put<void>(`/api/v1/roles/${id}/permissions`, { permission_ids }),
    listTemplates: () => get<RoleTemplate[]>('/api/v1/roles/templates'),
    createTemplate: (data: { name: string; slug: string; description?: string; icon?: string; permissions: string[] }) =>
      post<RoleTemplate>('/api/v1/roles/templates', data),
    updateTemplate: (id: string, data: Partial<{ name: string; description: string; icon: string; permissions: string[] }>) =>
      patch<RoleTemplate>(`/api/v1/roles/templates/${id}`, data),
    deleteTemplate: (id: string) => del<void>(`/api/v1/roles/templates/${id}`),
    createFromTemplate: (template_id: string) =>
      post<Role>('/api/v1/roles/from-template', { template_id }),
  },

  permissions: {
    list: () => get<Permission[]>('/api/v1/permissions'),
  },

  audit: {
    list: (params?: {
      action?: string
      user_id?: string
      resource_type?: string
      date_from?: string
      date_to?: string
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
      return get<PaginatedResponse<AuditEvent>>(`/api/v1/audit${q ? `?${q}` : ''}`)
    },
  },

  emailTemplates: {
    list: () => get<EmailTemplate[]>('/api/v1/email-templates'),
    get: (id: string) => get<EmailTemplate>(`/api/v1/email-templates/${id}`),
    update: (id: string, data: Partial<{ subject: string; html_body: string; description: string; is_active: boolean }>) =>
      put<EmailTemplate>(`/api/v1/email-templates/${id}`, data),
    test: (id: string, to?: string) =>
      post<{ sent: boolean; recipient: string }>(`/api/v1/email-templates/${id}/test`, { to: to || null }),
  },

  onboarding: {
    status: () => get<{ completed: boolean; step: string }>('/api/v1/onboarding/status'),
    updateStep: (step: string) => patch<{ completed: boolean; step: string }>('/api/v1/onboarding/step', { step }),
    complete: () => patch<{ completed: boolean; step: string }>('/api/v1/onboarding/complete', {}),
  },

  emailConfig: {
    get: () => get<EmailConfig>('/api/v1/email-config'),
    update: (data: Partial<EmailConfig>) => put<EmailConfig>('/api/v1/email-config', data),
    testConnection: () => post<{ ok: boolean; error?: string }>('/api/v1/email-config/test-connection', {}),
  },
}
