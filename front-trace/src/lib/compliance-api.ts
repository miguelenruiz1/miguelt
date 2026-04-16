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
  CreateRiskAssessmentInput,
  CreateSupplyChainNodeInput,
  DeclarationUpdate,
  DocumentLink,
  DocumentLinkInput,
  PlotLink,
  PlotLinkInput,
  PublicVerification,
  ReorderNodesInput,
  RiskAssessment,
  SupplyChainNode,
  TenantFrameworkActivation,
  UpdatePlotInput,
  UpdateRecordInput,
  UpdateRiskAssessmentInput,
  UpdateSupplyChainNodeInput,
  ValidationResult,
} from '@/types/compliance'

const BASE = import.meta.env.VITE_API_URL ?? 'http://localhost:9000'

/**
 * Extrae un mensaje legible del error JSON devuelto por compliance-api.
 *
 * Soporta varios shapes:
 *   { detail: "string" }                      → FastAPI HTTPException
 *   { detail: [{ msg, loc }] }                → Pydantic validation error
 *   { error: { message: "...", code: "..." } } → wrapper interno
 *   string                                    → fallback raw
 *
 * Crítico para EUDR: el validador GeoJSON devuelve mensajes en `detail`
 * con instrucciones específicas (precision insuficiente, polygon con holes,
 * etc). Estos mensajes deben llegar al usuario.
 */
function extractErrorMessage(err: unknown, fallback: string): string {
  if (typeof err === 'string') return err
  if (!err || typeof err !== 'object') return fallback
  const e = err as Record<string, any>
  if (typeof e.error?.message === 'string') return e.error.message
  if (typeof e.detail === 'string') return e.detail
  if (Array.isArray(e.detail)) {
    return e.detail
      .map((d: any) =>
        typeof d === 'string' ? d : d?.msg ?? JSON.stringify(d),
      )
      .join('; ')
  }
  if (typeof e.message === 'string') return e.message
  return fallback
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const res = await authFetch(`${BASE}${path}`, options)
  if (!res.ok) {
    const err = await res.json().catch(() => null)
    throw new Error(extractErrorMessage(err, res.statusText))
  }
  return res.json()
}

async function requestVoid(path: string, options: RequestInit = {}): Promise<void> {
  const res = await authFetch(`${BASE}${path}`, options)
  if (!res.ok) {
    const err = await res.json().catch(() => null)
    throw new Error(extractErrorMessage(err, res.statusText))
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
    throw new Error(extractErrorMessage(err, res.statusText))
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
      request<ComplianceFramework[]>(`/api/v1/compliance/frameworks/${qs(params)}`),

    get: (slug: string) =>
      request<ComplianceFramework>(`/api/v1/compliance/frameworks/${slug}`),
  },

  // ── Tenant Framework Activations ─────────────────────────────────────────
  activations: {
    list: () =>
      request<TenantFrameworkActivation[]>('/api/v1/compliance/activations/'),

    activate: (data: ActivationInput) =>
      request<TenantFrameworkActivation>('/api/v1/compliance/activations/', {
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
      request<CompliancePlot[]>(`/api/v1/compliance/plots/${qs(params)}`),

    get: (id: string) =>
      request<CompliancePlot>(`/api/v1/compliance/plots/${id}`),

    create: (data: CreatePlotInput) =>
      request<CompliancePlot>('/api/v1/compliance/plots/', {
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

    screenDeforestation: (id: string) =>
      request<any>(`/api/v1/compliance/plots/${id}/screen-deforestation`, { method: 'POST' }),

    screenDeforestationFull: (id: string) =>
      request<import('@/types/compliance').FullScreeningResult>(
        `/api/v1/compliance/plots/${id}/screen-deforestation-full`,
        { method: 'POST' },
      ),

    riskDecision: (id: string) =>
      request<import('@/types/compliance').RiskDecisionResponse>(
        `/api/v1/compliance/plots/${id}/risk-decision`,
        { method: 'POST' },
      ),

    documents: (id: string) =>
      request<DocumentLink[]>(`/api/v1/compliance/plots/${id}/documents`),

    attachDocument: (id: string, data: DocumentLinkInput) =>
      request<DocumentLink>(`/api/v1/compliance/plots/${id}/documents`, {
        method: 'POST',
        body: JSON.stringify(data),
      }),

    detachDocument: (id: string, docId: string) =>
      requestVoid(`/api/v1/compliance/plots/${id}/documents/${docId}`, { method: 'DELETE' }),
  },

  // ── Records ──────────────────────────────────────────────────────────────
  records: {
    list: (params?: {
      framework_slug?: string
      asset_id?: string
      status?: string
      commodity_type?: string
      declaration_status?: string
      has_declaration?: boolean
    }) =>
      request<ComplianceRecord[]>(`/api/v1/compliance/records/${qs(params)}`),

    get: (id: string) =>
      request<ComplianceRecord>(`/api/v1/compliance/records/${id}`),

    create: (data: CreateRecordInput) =>
      request<ComplianceRecord>('/api/v1/compliance/records/', {
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

    exportDds: (id: string) =>
      request<any>(`/api/v1/compliance/records/${id}/export-dds`, { method: 'POST' }),

    submitTraces: (id: string) =>
      request<any>(`/api/v1/compliance/records/${id}/submit-traces`, { method: 'POST' }),

    ddsStatus: (id: string) =>
      request<any>(`/api/v1/compliance/records/${id}/dds-status`),

    documents: (id: string) =>
      request<DocumentLink[]>(`/api/v1/compliance/records/${id}/documents`),

    attachDocument: (id: string, data: DocumentLinkInput) =>
      request<DocumentLink>(`/api/v1/compliance/records/${id}/documents`, {
        method: 'POST',
        body: JSON.stringify(data),
      }),

    detachDocument: (id: string, docId: string) =>
      requestVoid(`/api/v1/compliance/records/${id}/documents/${docId}`, { method: 'DELETE' }),

    supplyChain: (id: string) =>
      request<SupplyChainNode[]>(`/api/v1/compliance/records/${id}/supply-chain/`),

    addSupplyChainNode: (id: string, data: CreateSupplyChainNodeInput) =>
      request<SupplyChainNode>(`/api/v1/compliance/records/${id}/supply-chain/`, {
        method: 'POST',
        body: JSON.stringify(data),
      }),

    updateSupplyChainNode: (id: string, nodeId: string, data: UpdateSupplyChainNodeInput) =>
      request<SupplyChainNode>(`/api/v1/compliance/records/${id}/supply-chain/${nodeId}`, {
        method: 'PATCH',
        body: JSON.stringify(data),
      }),

    deleteSupplyChainNode: (id: string, nodeId: string) =>
      requestVoid(`/api/v1/compliance/records/${id}/supply-chain/${nodeId}`, { method: 'DELETE' }),

    reorderSupplyChain: (id: string, data: ReorderNodesInput) =>
      request<SupplyChainNode[]>(`/api/v1/compliance/records/${id}/supply-chain/reorder`, {
        method: 'POST',
        body: JSON.stringify(data),
      }),
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

    /**
     * Download the PDF. Uses authFetch so the bearer token is sent, then
     * triggers a browser download via a temporary anchor. The backend
     * resolves the real file location (local or S3/GCS) behind the
     * `/certificates/{id}/download` endpoint.
     */
    async download(id: string, filename?: string): Promise<void> {
      const res = await authFetch(`${BASE}/api/v1/compliance/certificates/${id}/download`, {
        method: 'GET',
      })
      if (!res.ok) {
        const err = await res.json().catch(() => null)
        throw new Error(extractErrorMessage(err, res.statusText))
      }
      const blob = await res.blob()
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = filename ?? `${id}.pdf`
      document.body.appendChild(a)
      a.click()
      a.remove()
      URL.revokeObjectURL(url)
    },
  },

  // ── Risk Assessments (EUDR Art. 10-11) ───────────────────────────────────
  riskAssessments: {
    create: (data: CreateRiskAssessmentInput) =>
      request<RiskAssessment>('/api/v1/compliance/risk-assessments/', {
        method: 'POST',
        body: JSON.stringify(data),
      }),

    getByRecord: (recordId: string) =>
      request<RiskAssessment>(`/api/v1/compliance/risk-assessments/by-record/${recordId}`),

    get: (id: string) =>
      request<RiskAssessment>(`/api/v1/compliance/risk-assessments/${id}`),

    update: (id: string, data: UpdateRiskAssessmentInput) =>
      request<RiskAssessment>(`/api/v1/compliance/risk-assessments/${id}`, {
        method: 'PATCH',
        body: JSON.stringify(data),
      }),

    complete: (id: string) =>
      request<RiskAssessment>(`/api/v1/compliance/risk-assessments/${id}/complete`, {
        method: 'POST',
      }),

    delete: (id: string) =>
      requestVoid(`/api/v1/compliance/risk-assessments/${id}`, { method: 'DELETE' }),
  },

  // ── Certification schemes (MITECO EFI credibility scoring) ──────────────
  certifications: {
    list: (params?: { commodity?: string; scope?: string; is_active?: boolean }) =>
      request<import('@/types/compliance').CertificationScheme[]>(
        `/api/v1/compliance/certifications/${qs(params)}`,
      ),

    get: (slug: string) =>
      request<import('@/types/compliance').CertificationScheme>(
        `/api/v1/compliance/certifications/${slug}`,
      ),

    update: (slug: string, body: import('@/types/compliance').CertificationSchemeUpdate) =>
      request<import('@/types/compliance').CertificationScheme>(
        `/api/v1/compliance/certifications/${slug}`,
        { method: 'PATCH', body: JSON.stringify(body) },
      ),
  },

  // ── Country risk benchmarks ─────────────────────────────────────────────
  countryRisk: {
    list: (params?: { only_current?: boolean }) =>
      request<import('@/types/compliance').CountryRiskBenchmark[]>(
        `/api/v1/compliance/country-risk/${qs(params)}`,
      ),

    get: (code: string) =>
      request<import('@/types/compliance').CountryRiskBenchmark>(
        `/api/v1/compliance/country-risk/${code}`,
      ),
  },

  // ── Legal requirements catalog (EUDR Art. 9.1 legalidad) ─────────────────
  legal: {
    listCatalogs: (params?: { country_code?: string; commodity?: string; is_active?: boolean }) =>
      request<import('@/types/compliance').LegalCatalog[]>(
        `/api/v1/compliance/legal/catalogs${qs(params)}`,
      ),

    getCatalog: (id: string) =>
      request<import('@/types/compliance').LegalCatalog>(
        `/api/v1/compliance/legal/catalogs/${id}`,
      ),

    getPlotStatus: (plotId: string) =>
      request<import('@/types/compliance').PlotLegalComplianceSummary>(
        `/api/v1/compliance/legal/plots/${plotId}/status`,
      ),

    updatePlotRequirement: (
      plotId: string,
      requirementId: string,
      body: {
        status: 'satisfied' | 'missing' | 'na' | 'pending'
        evidence_media_id?: string | null
        evidence_notes?: string | null
      },
    ) =>
      request<import('@/types/compliance').PlotLegalComplianceRow>(
        `/api/v1/compliance/legal/plots/${plotId}/requirements/${requirementId}`,
        { method: 'PATCH', body: JSON.stringify(body) },
      ),
  },

  // ── Public verification (no auth) ────────────────────────────────────────
  verify: (certificateNumber: string) =>
    publicRequest<PublicVerification>(`/api/v1/compliance/verify/${encodeURIComponent(certificateNumber)}`),
}
