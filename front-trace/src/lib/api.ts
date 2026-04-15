import type {
  ApiErrorBody, Asset, AssetCreate, AssetMintRequest, CustodyEvent,
  CustodianType, CustodianTypeCreate, CustodianTypeUpdate,
  Organization, OrganizationCreate, OrganizationUpdate,
  EventActionResponse, GenericEventRequest, HealthResponse, PaginatedResponse, ReadyResponse,
  SolanaAccountResponse, SolanaTxResponse, Tenant, TenantCreate, MerkleTree,
  Wallet, WalletCreate, WalletGenerateRequest, WalletUpdate,
  WorkflowState, WorkflowStateCreate, WorkflowStateUpdate,
  WorkflowTransition, WorkflowTransitionCreate,
  WorkflowEventType, WorkflowEventTypeCreate, WorkflowEventTypeUpdate,
  IndustryPresetInfo, SeedResult, AvailableAction,
  EventDocumentsResponse, DocumentRequirementsResponse, MediaFile, PaginatedResponse as PaginatedResp,
} from '@/types/api'
import { useAuthStore } from '@/store/auth'
import { usePlanLimitStore } from '@/store/planLimit'

// ─── API Error class ──────────────────────────────────────────────────────────

// Normalizes FastAPI / Pydantic / generic error payloads into a readable string.
// Handles:
//   - string detail ("Plot not found")
//   - Pydantic v2 array: [{loc:["body","field"], msg:"...", type:"..."}]
//   - {error:{message:"..."}}
//   - fallback to HTTP {status}
function formatErrorDetail(
  body: ApiErrorBody & { detail?: unknown },
  status: number,
): string {
  const d = (body as any).detail
  if (typeof d === 'string' && d.trim()) return d
  if (Array.isArray(d)) {
    const parts = d
      .map((item: any) => {
        if (typeof item === 'string') return item
        if (item && typeof item === 'object') {
          const loc = Array.isArray(item.loc) ? item.loc.filter((x: any) => x !== 'body').join('.') : ''
          const msg = item.msg ?? item.message ?? ''
          return loc ? `${loc}: ${msg}` : msg
        }
        return ''
      })
      .filter(Boolean)
    if (parts.length) return parts.join(' · ')
  }
  if (d && typeof d === 'object') {
    const anyD = d as any
    if (typeof anyD.message === 'string') return anyD.message
  }
  if (body.error?.message) return body.error.message
  return `HTTP ${status}`
}

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    public readonly body: ApiErrorBody & { detail?: unknown },
  ) {
    super(formatErrorDetail(body, status))
    this.name = 'ApiError'
  }

  get code() { return this.body.error?.code ?? 'UNKNOWN' }
  get detail() { return this.message }
}

// ─── Base fetch helper ────────────────────────────────────────────────────────

const BASE = import.meta.env.VITE_API_URL ?? 'http://localhost:9000'

interface RequestOptions {
  idempotencyKey?: string
  adminKey?: string
  tenantId?: string
  params?: Record<string, string | number | undefined>
}

async function request<T>(
  method: string,
  path: string,
  body?: unknown,
  options: RequestOptions = {},
): Promise<T> {
  const authState = useAuthStore.getState()
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    'X-User-Id': authState.user?.id ?? '1',
    'X-Tenant-Id': options.tenantId ?? authState.user?.tenant_id ?? 'default',
  }
  if (authState.accessToken) headers['Authorization'] = `Bearer ${authState.accessToken}`
  if (options.idempotencyKey) headers['Idempotency-Key'] = options.idempotencyKey
  if (options.adminKey) headers['X-Admin-Key'] = options.adminKey

  let url = `${BASE}${path}`
  if (options.params) {
    const qs = new URLSearchParams()
    for (const [k, v] of Object.entries(options.params)) {
      if (v !== undefined && v !== '') qs.set(k, String(v))
    }
    const s = qs.toString()
    if (s) url += `?${s}`
  }

  const res = await fetch(url, {
    method,
    headers,
    body: body != null ? JSON.stringify(body) : undefined,
  })

  if (!res.ok) {
    const errBody = await res.json().catch(() => ({
      error: { code: 'UNKNOWN', message: res.statusText },
    })) as ApiErrorBody & { resource?: string; current?: number; limit?: number }

    if (res.status === 402) {
      usePlanLimitStore.getState().open({
        resource: errBody.resource ?? 'recurso',
        current: errBody.current ?? 0,
        limit: errBody.limit ?? 0,
        message:
          errBody.error?.message ??
          (typeof errBody.detail === 'string' ? errBody.detail : undefined) ??
          'Has alcanzado el limite de tu plan actual.',
      })
    }

    throw new ApiError(res.status, errBody)
  }

  if (res.status === 204) return undefined as T
  return res.json() as Promise<T>
}

const get = <T>(path: string, opts?: RequestOptions) => request<T>('GET', path, undefined, opts)
const post = <T>(path: string, body: unknown, opts?: RequestOptions) => request<T>('POST', path, body, opts)
const patch = <T>(path: string, body: unknown, opts?: RequestOptions) => request<T>('PATCH', path, body, opts)
const del = <T>(path: string, opts?: RequestOptions) => request<T>('DELETE', path, undefined, opts)

async function requestMultipart<T>(
  method: string,
  path: string,
  formData: FormData,
  options: RequestOptions = {},
): Promise<T> {
  const headers: Record<string, string> = {
    'X-User-Id': useAuthStore.getState().user?.id ?? '1',
    'X-Tenant-Id': options.tenantId ?? useAuthStore.getState().user?.tenant_id ?? 'default',
  }
  if (options.idempotencyKey) headers['Idempotency-Key'] = options.idempotencyKey

  let url = `${BASE}${path}`
  if (options.params) {
    const qs = new URLSearchParams()
    for (const [k, v] of Object.entries(options.params)) {
      if (v !== undefined && v !== '') qs.set(k, String(v))
    }
    const s = qs.toString()
    if (s) url += `?${s}`
  }

  const res = await fetch(url, { method, headers, body: formData })
  if (!res.ok) {
    const errBody = await res.json().catch(() => ({
      error: { code: 'UNKNOWN', message: res.statusText },
    }))
    throw new ApiError(res.status, errBody)
  }
  if (res.status === 204) return undefined as T
  return res.json() as Promise<T>
}

// ─── Structured API ───────────────────────────────────────────────────────────

export const api = {
  health: {
    liveness: () => get<HealthResponse>('/health'),
    readiness: () => get<ReadyResponse>('/ready'),
  },

  wallets: {
    list: (p?: { tag?: string; status?: string; organization_id?: string; offset?: number; limit?: number }) =>
      get<PaginatedResponse<Wallet>>('/api/v1/registry/wallets', { params: p }),
    get: (id: string) =>
      get<Wallet>(`/api/v1/registry/wallets/${id}`),
    register: (data: WalletCreate, idempotencyKey?: string) =>
      post<Wallet>('/api/v1/registry/wallets', data, { idempotencyKey }),
    generate: (data: WalletGenerateRequest) =>
      post<Wallet>('/api/v1/registry/wallets/generate', data),
    update: (id: string, data: WalletUpdate) =>
      patch<Wallet>(`/api/v1/registry/wallets/${id}`, data),
  },

  assets: {
    list: (p?: { product_type?: string; custodian?: string; state?: string; offset?: number; limit?: number }) =>
      get<PaginatedResponse<Asset>>('/api/v1/assets', { params: p }),
    get: (id: string) =>
      get<Asset>(`/api/v1/assets/${id}`),
    create: (data: AssetCreate, idempotencyKey?: string) =>
      post<EventActionResponse>('/api/v1/assets', data, { idempotencyKey }),
    mint: (data: AssetMintRequest, idempotencyKey?: string) =>
      post<EventActionResponse>('/api/v1/assets/mint', data, { idempotencyKey }),
    events: (id: string, p?: { offset?: number; limit?: number }) =>
      get<PaginatedResponse<CustodyEvent>>(`/api/v1/assets/${id}/events`, { params: p }),
    recordEvent: (id: string, data: GenericEventRequest, idempotencyKey?: string, adminKey?: string) =>
      post<EventActionResponse>(`/api/v1/assets/${id}/events`, data, { idempotencyKey, adminKey }),
    anchor: (assetId: string, eventId: string) =>
      post<CustodyEvent>(`/api/v1/assets/${assetId}/events/${eventId}/anchor`, {}),
    delete: (id: string, adminKey?: string) =>
      del<void>(`/api/v1/assets/${id}`, { adminKey: adminKey || undefined }),
  },

  solana: {
    account: (pubkey: string) => get<SolanaAccountResponse>(`/api/v1/solana/account/${pubkey}`),
    tx: (sig: string) => get<SolanaTxResponse>(`/api/v1/solana/tx/${sig}`),
  },

  tenants: {
    list: () => get<Tenant[]>('/api/v1/tenants'),
    get: (id: string) => get<Tenant>(`/api/v1/tenants/${id}`),
    create: (data: TenantCreate) => post<Tenant>('/api/v1/tenants', data),
    provisionTree: (id: string) => post<MerkleTree>(`/api/v1/tenants/${id}/provision-tree`, {}),
    getTree: (id: string) => get<MerkleTree>(`/api/v1/tenants/${id}/tree`),
    getAssetBlockchain: (assetId: string) => get(`/api/v1/assets/${assetId}/blockchain`),
  },

  taxonomy: {
    // Custodian types
    listTypes: () =>
      get<CustodianType[]>('/api/v1/taxonomy/custodian-types'),
    createType: (data: CustodianTypeCreate) =>
      post<CustodianType>('/api/v1/taxonomy/custodian-types', data),
    updateType: (id: string, data: CustodianTypeUpdate) =>
      patch<CustodianType>(`/api/v1/taxonomy/custodian-types/${id}`, data),
    deleteType: (id: string) =>
      del<void>(`/api/v1/taxonomy/custodian-types/${id}`),

    // Organizations
    listOrgs: (p?: { custodian_type_id?: string; status?: string; offset?: number; limit?: number }) =>
      get<PaginatedResponse<Organization>>('/api/v1/taxonomy/organizations', { params: p }),
    getOrg: (id: string) =>
      get<Organization>(`/api/v1/taxonomy/organizations/${id}`),
    createOrg: (data: OrganizationCreate) =>
      post<Organization>('/api/v1/taxonomy/organizations', data),
    updateOrg: (id: string, data: OrganizationUpdate) =>
      patch<Organization>(`/api/v1/taxonomy/organizations/${id}`, data),
    deleteOrg: (id: string) =>
      del<void>(`/api/v1/taxonomy/organizations/${id}`),
    getOrgWallets: (id: string, p?: { offset?: number; limit?: number }) =>
      get<PaginatedResponse<Wallet>>(`/api/v1/taxonomy/organizations/${id}/wallets`, { params: p }),
    getOrgAssets: (id: string, p?: { offset?: number; limit?: number }) =>
      get<PaginatedResponse<Asset>>(`/api/v1/taxonomy/organizations/${id}/assets`, { params: p }),
  },

  workflow: {
    // States
    listStates: () =>
      get<WorkflowState[]>('/api/v1/config/workflow/states'),
    createState: (data: WorkflowStateCreate) =>
      post<WorkflowState>('/api/v1/config/workflow/states', data),
    updateState: (id: string, data: WorkflowStateUpdate) =>
      patch<WorkflowState>(`/api/v1/config/workflow/states/${id}`, data),
    deleteState: (id: string) =>
      del<void>(`/api/v1/config/workflow/states/${id}`),
    reorderStates: (stateIds: string[]) =>
      post<WorkflowState[]>('/api/v1/config/workflow/states/reorder', { state_ids: stateIds }),

    // Transitions
    listTransitions: () =>
      get<WorkflowTransition[]>('/api/v1/config/workflow/transitions'),
    createTransition: (data: WorkflowTransitionCreate) =>
      post<WorkflowTransition>('/api/v1/config/workflow/transitions', data),
    deleteTransition: (id: string) =>
      del<void>(`/api/v1/config/workflow/transitions/${id}`),

    // Event types
    listEventTypes: (p?: { active_only?: boolean }) =>
      get<WorkflowEventType[]>('/api/v1/config/workflow/event-types', { params: p }),
    createEventType: (data: WorkflowEventTypeCreate) =>
      post<WorkflowEventType>('/api/v1/config/workflow/event-types', data),
    updateEventType: (id: string, data: WorkflowEventTypeUpdate) =>
      patch<WorkflowEventType>(`/api/v1/config/workflow/event-types/${id}`, data),
    deleteEventType: (id: string) =>
      del<void>(`/api/v1/config/workflow/event-types/${id}`),

    // Available actions (from a specific state)
    getAvailableActions: (stateSlug: string) =>
      get<AvailableAction[]>(`/api/v1/config/workflow/states/${stateSlug}/actions`),

    // Presets
    listPresets: () =>
      get<Record<string, IndustryPresetInfo>>('/api/v1/config/workflow/presets'),
    seedPreset: (presetName: string) =>
      post<SeedResult>(`/api/v1/config/workflow/seed/${presetName}`, {}),
  },

  documents: {
    upload: (assetId: string, eventId: string, files: File[], documentType: string, title?: string) => {
      const form = new FormData()
      for (const f of files) form.append('files', f)
      return requestMultipart<EventDocumentsResponse>(
        'POST',
        `/api/v1/assets/${assetId}/events/${eventId}/documents`,
        form,
        { params: { document_type: documentType, title } },
      )
    },
    linkExisting: (assetId: string, eventId: string, mediaFileId: string, documentType: string) =>
      post<unknown>(`/api/v1/assets/${assetId}/events/${eventId}/documents/link`, {}, {
        params: { media_file_id: mediaFileId, document_type: documentType },
      }),
    list: (assetId: string, eventId: string) =>
      get<EventDocumentsResponse>(`/api/v1/assets/${assetId}/events/${eventId}/documents`),
    unlink: (assetId: string, eventId: string, linkId: string) =>
      del<void>(`/api/v1/assets/${assetId}/events/${eventId}/documents/${linkId}`),
    requirements: (assetId: string, eventType: string) =>
      get<DocumentRequirementsResponse>(`/api/v1/assets/${assetId}/document-requirements`, { params: { event_type: eventType } }),
  },

  media: {
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
      get<PaginatedResp<MediaFile>>('/api/v1/media/files', { params: p }),
    get: (id: string) =>
      get<MediaFile>(`/api/v1/media/files/${id}`),
    update: (id: string, data: { title?: string; description?: string; category?: string; document_type?: string; tags?: string }) =>
      patch<MediaFile>(`/api/v1/media/files/${id}`, {}, { params: data }),
    delete: (id: string) =>
      del<void>(`/api/v1/media/files/${id}`),
  },
}
