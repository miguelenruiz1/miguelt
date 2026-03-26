/**
 * Logistics API client — connects to trace-service (logistics module).
 * Shipments, trade documents, anchor rules, and public verification.
 */
import { useAuthStore } from '@/store/auth'
import type {
  ShipmentDocument, ShipmentDocCreate, ShipmentDocUpdate,
  TradeDocument, TradeDocCreate, TradeDocUpdate,
  AnchorRule, AnchorRuleCreate, AnchorRuleUpdate,
  PublicBatchVerification,
} from '@/types/logistics'

const BASE = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const store = useAuthStore.getState()
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    'X-Tenant-Id': store.tenantId ?? 'default',
    'X-User-Id': store.user?.id ?? '1',
    ...(options.headers as Record<string, string> || {}),
  }
  if (store.accessToken) {
    headers['Authorization'] = `Bearer ${store.accessToken}`
  }
  const res = await fetch(`${BASE}${path}`, { ...options, headers })
  if (!res.ok) {
    const err = await res.json().catch(() => null)
    throw new Error(err?.error?.message ?? err?.detail ?? `HTTP ${res.status}`)
  }
  if (res.status === 204) return undefined as T
  return res.json()
}

async function requestVoid(path: string, options: RequestInit = {}): Promise<void> {
  await request<void>(path, options)
}

// ── Shipments ─────────────────────────────────────────────────────────────────

export const logisticsShipmentsApi = {
  list: (params?: { document_type?: string; reference_type?: string; reference_id?: string }) => {
    const sp = new URLSearchParams()
    if (params?.document_type) sp.set('document_type', params.document_type)
    if (params?.reference_type) sp.set('reference_type', params.reference_type)
    if (params?.reference_id) sp.set('reference_id', params.reference_id)
    return request<ShipmentDocument[]>(`/api/v1/shipments?${sp}`)
  },
  get: (id: string) => request<ShipmentDocument>(`/api/v1/shipments/${id}`),
  create: (data: ShipmentDocCreate) =>
    request<ShipmentDocument>('/api/v1/shipments', { method: 'POST', body: JSON.stringify(data) }),
  update: (id: string, data: ShipmentDocUpdate) =>
    request<ShipmentDocument>(`/api/v1/shipments/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
  updateStatus: (id: string, status: string) =>
    request<ShipmentDocument>(`/api/v1/shipments/${id}/status`, { method: 'POST', body: JSON.stringify({ status }) }),
  delete: (id: string) =>
    requestVoid(`/api/v1/shipments/${id}`, { method: 'DELETE' }),
}

// ── Trade Documents ───────────────────────────────────────────────────────────

export const logisticsTradeDocsApi = {
  list: (params?: { document_type?: string; reference_type?: string; reference_id?: string; shipment_id?: string }) => {
    const sp = new URLSearchParams()
    if (params?.document_type) sp.set('document_type', params.document_type)
    if (params?.reference_type) sp.set('reference_type', params.reference_type)
    if (params?.reference_id) sp.set('reference_id', params.reference_id)
    if (params?.shipment_id) sp.set('shipment_id', params.shipment_id)
    return request<TradeDocument[]>(`/api/v1/trade-documents?${sp}`)
  },
  get: (id: string) => request<TradeDocument>(`/api/v1/trade-documents/${id}`),
  create: (data: TradeDocCreate) =>
    request<TradeDocument>('/api/v1/trade-documents', { method: 'POST', body: JSON.stringify(data) }),
  update: (id: string, data: TradeDocUpdate) =>
    request<TradeDocument>(`/api/v1/trade-documents/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
  approve: (id: string) =>
    request<TradeDocument>(`/api/v1/trade-documents/${id}/approve`, { method: 'POST' }),
  reject: (id: string, reason?: string) =>
    request<TradeDocument>(`/api/v1/trade-documents/${id}/reject${reason ? `?reason=${encodeURIComponent(reason)}` : ''}`, { method: 'POST' }),
  delete: (id: string) =>
    requestVoid(`/api/v1/trade-documents/${id}`, { method: 'DELETE' }),
}

// ── Anchor Rules ──────────────────────────────────────────────────────────────

export const logisticsAnchorRulesApi = {
  list: (entityType?: string) => {
    const sp = new URLSearchParams()
    if (entityType) sp.set('entity_type', entityType)
    return request<AnchorRule[]>(`/api/v1/anchor-rules?${sp}`)
  },
  get: (id: string) => request<AnchorRule>(`/api/v1/anchor-rules/${id}`),
  create: (data: AnchorRuleCreate) =>
    request<AnchorRule>('/api/v1/anchor-rules', { method: 'POST', body: JSON.stringify(data) }),
  update: (id: string, data: AnchorRuleUpdate) =>
    request<AnchorRule>(`/api/v1/anchor-rules/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
  delete: (id: string) =>
    requestVoid(`/api/v1/anchor-rules/${id}`, { method: 'DELETE' }),
  seedDefaults: () =>
    request<AnchorRule[]>('/api/v1/anchor-rules/seed-defaults', { method: 'POST' }),
}

// ── Public Verification (no auth) ────────────────────────────────────────────

export const publicVerifyApi = {
  verifyBatch: (batchNumber: string, tenantId = 'default') =>
    fetch(`${BASE}/api/v1/public/batch/${encodeURIComponent(batchNumber)}/verify?tenant_id=${tenantId}`)
      .then(res => {
        if (!res.ok) throw new Error('Batch not found')
        return res.json() as Promise<PublicBatchVerification>
      }),
}
