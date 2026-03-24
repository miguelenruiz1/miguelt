import { authFetch } from '@/lib/auth-fetch'
import type {
  ActivationInput,
  ActivationUpdateInput,
  CertificateListResponse,
  ComplianceCertificate,
  ComplianceFramework,
  CompliancePlot,
  ComplianceRecord,
  CreatePlotInput,
  CreateRecordInput,
  DeclarationUpdate,
  PlotLink,
  PlotLinkInput,
  PublicVerification,
  TenantFrameworkActivation,
  UpdatePlotInput,
  UpdateRecordInput,
  ValidationResult,
} from '@/types/compliance'

const BASE = import.meta.env.VITE_COMPLIANCE_API_URL ?? ''

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const res = await authFetch(`${BASE}${path}`, options)
  if (!res.ok) {
    const err = await res.json().catch(() => null)
    const msg = err?.error?.message ?? err?.detail ?? res.statusText
    throw new Error(msg)
  }
  return res.json()
}

async function requestVoid(path: string, options: RequestInit = {}): Promise<void> {
  const res = await authFetch(`${BASE}${path}`, options)
  if (!res.ok) {
    const err = await res.json().catch(() => null)
    const msg = err?.error?.message ?? err?.detail ?? res.statusText
    throw new Error(msg)
  }
}

/**
 * Public fetch (no auth headers) — used for the verify endpoint.
 */
async function publicRequest<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
  })
  if (!res.ok) {
    const err = await res.json().catch(() => null)
    const msg = err?.error?.message ?? err?.detail ?? res.statusText
    throw new Error(msg)
  }
  return res.json()
}

// ─── Helper ──────────────────────────────────────────────────────────────────

function qs(params?: Record<string, string | number | boolean | undefined | null>): string {
  if (!params) return ''
  const sp = new URLSearchParams()
  for (const [k, v] of Object.entries(params)) {
    if (v !== undefined && v !== null && v !== '') sp.set(k, String(v))
  }
  const s = sp.toString()
  return s ? `?${s}` : ''
}

// ─── API client ──────────────────────────────────────────────────────────────

export const complianceApi = {
  // ── Frameworks (read-only catalogue) ─────────────────────────────────────
  frameworks: {
    list: (params?: { target_market?: string; commodity?: string }) =>
      request<ComplianceFramework[]>(`/api/v1/compliance/frameworks${qs(params)}`),

    get: (slug: string) =>
      request<ComplianceFramework>(`/api/v1/compliance/frameworks/${slug}`),
  },

  // ── Tenant Framework Activations ─────────────────────────────────────────
  activations: {
    list: () =>
      request<TenantFrameworkActivation[]>('/api/v1/compliance/activations'),

    activate: (data: ActivationInput) =>
      request<TenantFrameworkActivation>('/api/v1/compliance/activations', {
        method: 'POST',
        body: JSON.stringify(data),
      }),

    update: (slug: string, data: ActivationUpdateInput) =>
      request<TenantFrameworkActivation>(`/api/v1/compliance/activations/${slug}`, {
        method: 'PATCH',
        body: JSON.stringify(data),
      }),

    deactivate: (slug: string) =>
      requestVoid(`/api/v1/compliance/activations/${slug}`, { method: 'DELETE' }),
  },

  // ── Plots (production parcels) ───────────────────────────────────────────
  plots: {
    list: (params?: { organization_id?: string; risk_level?: string; is_active?: boolean }) =>
      request<CompliancePlot[]>(`/api/v1/compliance/plots${qs(params)}`),

    get: (id: string) =>
      request<CompliancePlot>(`/api/v1/compliance/plots/${id}`),

    create: (data: CreatePlotInput) =>
      request<CompliancePlot>('/api/v1/compliance/plots', {
        method: 'POST',
        body: JSON.stringify(data),
      }),

    update: (id: string, data: UpdatePlotInput) =>
      request<CompliancePlot>(`/api/v1/compliance/plots/${id}`, {
        method: 'PATCH',
        body: JSON.stringify(data),
      }),

    delete: (id: string) =>
      requestVoid(`/api/v1/compliance/plots/${id}`, { method: 'DELETE' }),
  },

  // ── Records ──────────────────────────────────────────────────────────────
  records: {
    list: (params?: {
      framework_slug?: string
      asset_id?: string
      status?: string
      commodity_type?: string
    }) =>
      request<ComplianceRecord[]>(`/api/v1/compliance/records${qs(params)}`),

    get: (id: string) =>
      request<ComplianceRecord>(`/api/v1/compliance/records/${id}`),

    create: (data: CreateRecordInput) =>
      request<ComplianceRecord>('/api/v1/compliance/records', {
        method: 'POST',
        body: JSON.stringify(data),
      }),

    update: (id: string, data: UpdateRecordInput) =>
      request<ComplianceRecord>(`/api/v1/compliance/records/${id}`, {
        method: 'PATCH',
        body: JSON.stringify(data),
      }),

    delete: (id: string) =>
      requestVoid(`/api/v1/compliance/records/${id}`, { method: 'DELETE' }),

    validate: (id: string) =>
      request<ValidationResult>(`/api/v1/compliance/records/${id}/validate`),

    plots: (id: string) =>
      request<PlotLink[]>(`/api/v1/compliance/records/${id}/plots`),

    linkPlot: (id: string, data: PlotLinkInput) =>
      request<PlotLink>(`/api/v1/compliance/records/${id}/plots`, {
        method: 'POST',
        body: JSON.stringify(data),
      }),

    unlinkPlot: (id: string, plotId: string) =>
      requestVoid(`/api/v1/compliance/records/${id}/plots/${plotId}`, { method: 'DELETE' }),

    updateDeclaration: (id: string, data: DeclarationUpdate) =>
      request<ComplianceRecord>(`/api/v1/compliance/records/${id}/declaration`, {
        method: 'PATCH',
        body: JSON.stringify(data),
      }),

    generateCertificate: (id: string) =>
      request<ComplianceCertificate>(`/api/v1/compliance/records/${id}/certificate`, {
        method: 'POST',
      }),

    getCertificate: (id: string) =>
      request<ComplianceCertificate>(`/api/v1/compliance/records/${id}/certificate`),
  },

  // ── Asset compliance (cross-framework view) ──────────────────────────────
  assets: {
    compliance: (assetId: string) =>
      request<ComplianceRecord[]>(`/api/v1/compliance/assets/${assetId}`),
  },

  // ── Certificates ─────────────────────────────────────────────────────────
  certificates: {
    list: (params?: {
      framework_slug?: string
      status?: string
      year?: number
      offset?: number
      limit?: number
    }) =>
      request<CertificateListResponse>(`/api/v1/compliance/certificates${qs(params)}`),

    get: (id: string) =>
      request<ComplianceCertificate>(`/api/v1/compliance/certificates/${id}`),

    regenerate: (id: string) =>
      request<ComplianceCertificate>(`/api/v1/compliance/certificates/${id}/regenerate`, {
        method: 'POST',
      }),

    revoke: (id: string, reason: string) =>
      request<ComplianceCertificate>(`/api/v1/compliance/certificates/${id}/revoke`, {
        method: 'POST',
        body: JSON.stringify({ reason }),
      }),
  },

  // ── Public verification (no auth) ────────────────────────────────────────
  verify: (certificateNumber: string) =>
    publicRequest<PublicVerification>(`/api/v1/compliance/verify/${encodeURIComponent(certificateNumber)}`),
}
