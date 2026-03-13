// ─── Auth Types ───────────────────────────────────────────────────────────────

export interface AuthRole {
  id: string
  name: string
  slug: string
}

export interface AuthUser {
  id: string
  email: string
  username: string
  full_name: string
  is_active: boolean
  is_superuser: boolean
  tenant_id: string
  avatar_url: string | null
  phone: string | null
  job_title: string | null
  company: string | null
  bio: string | null
  timezone: string | null
  language: string | null
  invitation_sent_at: string | null
  invitation_accepted_at: string | null
  must_change_password: boolean
  created_at: string
  updated_at: string
  roles: AuthRole[]
  permissions: string[]
}

export interface LoginResponse {
  access_token: string
  refresh_token: string
  token_type: string
  user: AuthUser
  permissions: string[]
}

export interface Permission {
  id: string
  name: string
  slug: string
  module: string
  description: string | null
  created_at: string
}

export interface Role {
  id: string
  name: string
  slug: string
  description: string | null
  is_system: boolean
  tenant_id: string
  created_at: string
  updated_at: string
}

export interface AuditEvent {
  id: string
  user_id: string | null
  user_email: string | null
  action: string
  resource_type: string | null
  resource_id: string | null
  metadata: Record<string, unknown> | null
  ip_address: string | null
  user_agent: string | null
  tenant_id: string
  created_at: string
}

export interface PaginatedResponse<T> {
  items: T[]
  total: number
  offset: number
  limit: number
}

// ─── Invitation & Email Templates ─────────────────────────────────────────────

export interface InviteUserRequest {
  email: string
  full_name: string
  role_ids: string[]
}

export interface EmailTemplate {
  id: string
  tenant_id: string
  slug: string
  subject: string
  html_body: string
  description: string | null
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface RoleTemplate {
  id: string
  tenant_id: string
  slug: string
  name: string
  description: string | null
  icon: string
  permissions: string[]
  is_default: boolean
  created_at: string
  updated_at: string
}

export interface EmailConfig {
  id: string
  tenant_id: string
  smtp_host: string | null
  smtp_port: number
  smtp_user: string | null
  smtp_password: string | null
  smtp_from: string | null
  smtp_use_tls: boolean
  admin_email: string | null
  test_email: string | null
  created_at: string
  updated_at: string
}
