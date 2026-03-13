import type {
  ApiErrorBody, Asset, AssetCreate, AssetMintRequest, AssetState, CustodyEvent,
  CustodianType, CustodianTypeCreate, CustodianTypeUpdate,
  Organization, OrganizationCreate, OrganizationUpdate,
  EventActionResponse, HandoffRequest, ArrivedRequest, LoadedRequest,
  QCRequest, ReleaseRequest, BurnRequest, HealthResponse, PaginatedResponse, ReadyResponse,
  SolanaAccountResponse, SolanaTxResponse, Tenant, TenantCreate, MerkleTree,
  Wallet, WalletCreate, WalletGenerateRequest, WalletUpdate,
} from '@/types/api'
import { useAuthStore } from '@/store/auth'

// ─── API Error class ──────────────────────────────────────────────────────────

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    public readonly body: ApiErrorBody & { detail?: string },
  ) {
    super(body.error?.message ?? body.detail ?? `HTTP ${status}`)
    this.name = 'ApiError'
  }

  get code() { return this.body.error?.code ?? 'UNKNOWN' }
  get detail() { return this.body.detail ?? this.body.error?.message ?? this.message }
}

// ─── Base fetch helper ────────────────────────────────────────────────────────

const BASE = import.meta.env.VITE_API_URL ?? ''

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
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    'X-User-Id': useAuthStore.getState().user?.id ?? '1',
    'X-Tenant-Id': options.tenantId ?? useAuthStore.getState().user?.tenant_id ?? 'default',
  }
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
    })) as ApiErrorBody
    throw new ApiError(res.status, errBody)
  }

  if (res.status === 204) return undefined as T
  return res.json() as Promise<T>
}

const get = <T>(path: string, opts?: RequestOptions) => request<T>('GET', path, undefined, opts)
const post = <T>(path: string, body: unknown, opts?: RequestOptions) => request<T>('POST', path, body, opts)
const patch = <T>(path: string, body: unknown, opts?: RequestOptions) => request<T>('PATCH', path, body, opts)
const del = <T>(path: string, opts?: RequestOptions) => request<T>('DELETE', path, undefined, opts)

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
    list: (p?: { product_type?: string; custodian?: string; state?: AssetState | ''; offset?: number; limit?: number }) =>
      get<PaginatedResponse<Asset>>('/api/v1/assets', { params: p }),
    get: (id: string) =>
      get<Asset>(`/api/v1/assets/${id}`),
    create: (data: AssetCreate, idempotencyKey?: string) =>
      post<EventActionResponse>('/api/v1/assets', data, { idempotencyKey }),
    mint: (data: AssetMintRequest, idempotencyKey?: string) =>
      post<EventActionResponse>('/api/v1/assets/mint', data, { idempotencyKey }),
    events: (id: string, p?: { offset?: number; limit?: number }) =>
      get<PaginatedResponse<CustodyEvent>>(`/api/v1/assets/${id}/events`, { params: p }),

    // Custody events
    handoff: (id: string, data: HandoffRequest, idempotencyKey?: string) =>
      post<EventActionResponse>(`/api/v1/assets/${id}/events/handoff`, data, { idempotencyKey }),
    arrived: (id: string, data: ArrivedRequest) =>
      post<EventActionResponse>(`/api/v1/assets/${id}/events/arrived`, data),
    loaded: (id: string, data: LoadedRequest) =>
      post<EventActionResponse>(`/api/v1/assets/${id}/events/loaded`, data),
    qc: (id: string, data: QCRequest) =>
      post<EventActionResponse>(`/api/v1/assets/${id}/events/qc`, data),
    release: (id: string, data: ReleaseRequest, adminKey: string, idempotencyKey?: string) =>
      post<EventActionResponse>(`/api/v1/assets/${id}/events/release`, data, { adminKey, idempotencyKey }),
    burn: (id: string, data: BurnRequest, idempotencyKey?: string) =>
      post<EventActionResponse>(`/api/v1/assets/${id}/events/burn`, data, { idempotencyKey }),
    anchor: (assetId: string, eventId: string) =>
      post<CustodyEvent>(`/api/v1/assets/${assetId}/events/${eventId}/anchor`, {}),
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
}
