// WM API client (warehouse management). Reuses authFetch (auth + tenant headers).
import { authFetch } from '@/lib/auth-fetch'
import type {
  BinBulkResult, BinSegment, EmptyBinReport, ERI, MovementOrder, OperationType,
  PutawayProposal, RemovalPlan, StockStatus, StorageSection, StorageType,
  WMConfig, WMRoute,
} from '@/types/wm'

const BASE = import.meta.env.VITE_API_URL ?? 'http://localhost:9000'

async function req<T>(path: string, options: RequestInit = {}): Promise<T> {
  const res = await authFetch(`${BASE}${path}`, options)
  if (!res.ok) {
    const err = await res.json().catch(() => null)
    const msg = err?.error?.message ?? err?.detail ?? `HTTP ${res.status}`
    throw new Error(typeof msg === 'string' ? msg : `HTTP ${res.status}`)
  }
  if (res.status === 204) return undefined as T
  return res.json()
}

const jsonBody = (data: unknown): RequestInit => ({
  method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data),
})

export const wmApi = {
  // Storage types / sections
  listStorageTypes: (warehouseId: string) =>
    req<StorageType[]>(`/api/v1/wm/storage-types?warehouse_id=${warehouseId}`),
  createStorageType: (data: Partial<StorageType> & { warehouse_id: string; code: string; name: string }) =>
    req<StorageType>('/api/v1/wm/storage-types', jsonBody(data)),
  deleteStorageType: (id: string) =>
    req<void>(`/api/v1/wm/storage-types/${id}`, { method: 'DELETE' }),
  listSections: (storageTypeId: string) =>
    req<StorageSection[]>(`/api/v1/wm/storage-sections?storage_type_id=${storageTypeId}`),
  createSection: (data: { storage_type_id: string; code: string; name: string; rotation_class?: string }) =>
    req<StorageSection>('/api/v1/wm/storage-sections', jsonBody(data)),

  // Bins
  bulkBins: (data: {
    warehouse_id: string; storage_type_id?: string | null; storage_section_id?: string | null
    separator?: string; prefix?: string; segments: BinSegment[]
    height_m?: number; max_weight_kg?: number; max_capacity?: number
  }) => req<BinBulkResult>('/api/v1/wm/bins/bulk', jsonBody(data)),
  emptyReport: (warehouseId: string) =>
    req<EmptyBinReport>(`/api/v1/wm/bins/empty-report?warehouse_id=${warehouseId}`),
  blockBin: (locationId: string, data: { blocked_inbound?: boolean; blocked_outbound?: boolean; block_reason?: string }) =>
    req(`/api/v1/wm/bins/${locationId}/block`, jsonBody(data)),
  unblockBin: (locationId: string) =>
    req(`/api/v1/wm/bins/${locationId}/unblock`, { method: 'POST' }),

  // Operation types + interim zones
  listOperationTypes: () => req<OperationType[]>('/api/v1/wm/operation-types'),
  seedOperationTypes: () => req<OperationType[]>('/api/v1/wm/operation-types/seed', { method: 'POST' }),
  ensureInterim: (warehouseId: string) =>
    req<{ zones: { code: string; location_id: string; name: string }[] }>(
      `/api/v1/wm/interim-zones?warehouse_id=${warehouseId}`, { method: 'POST' }),

  // Movement orders
  listMovementOrders: (warehouseId: string, status?: string) =>
    req<MovementOrder[]>(`/api/v1/wm/movement-orders?warehouse_id=${warehouseId}${status ? `&status=${status}` : ''}`),
  getMovementOrder: (id: string) => req<MovementOrder>(`/api/v1/wm/movement-orders/${id}`),
  createMovementOrder: (data: {
    warehouse_id: string
    lines: { product_id: string; quantity: number; source_location_id?: string; dest_location_id?: string }[]
    notes?: string
  }) => req<MovementOrder>('/api/v1/wm/movement-orders', jsonBody(data)),
  confirmLine: (orderId: string, lineId: string, data: { confirm_source?: boolean; confirm_dest?: boolean }) =>
    req<MovementOrderLineLike>(`/api/v1/wm/movement-orders/${orderId}/lines/${lineId}/confirm`, jsonBody(data)),

  // Config + routes
  getConfig: (warehouseId: string) => req<WMConfig>(`/api/v1/wm/warehouses/${warehouseId}/config`),
  setConfig: (warehouseId: string, data: { receive_steps: number; deliver_steps: number; manufacture_steps: number }) =>
    req<WMConfig>(`/api/v1/wm/warehouses/${warehouseId}/config`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) }),
  listRoutes: (warehouseId: string) => req<WMRoute[]>(`/api/v1/wm/routes?warehouse_id=${warehouseId}`),
  generateChain: (data: {
    warehouse_id: string; flow: 'inbound' | 'outbound' | 'manufacture'
    lines: { product_id: string; quantity: number }[]
  }) => req<{ flow: string; steps: number; orders: { to_number: string; sequence: number; step_name: string; source_zone: string; dest_zone: string }[] }>(
    '/api/v1/wm/routes/generate-chain', jsonBody(data)),

  // Putaway / removal / inventory
  proposePutaway: (data: { warehouse_id: string; product_id: string; quantity?: number }) =>
    req<PutawayProposal>('/api/v1/wm/putaway/propose', jsonBody(data)),
  removalPlan: (data: { warehouse_id: string; product_id: string; quantity: number; strategy?: string }) =>
    req<RemovalPlan>('/api/v1/wm/removal/plan', jsonBody(data)),
  stockStatus: (warehouseId: string) => req<StockStatus>(`/api/v1/wm/stock-status?warehouse_id=${warehouseId}`),
  eri: (warehouseId: string) => req<ERI>(`/api/v1/wm/eri?warehouse_id=${warehouseId}`),
}

interface MovementOrderLineLike { id: string; status: string; source_confirmed: boolean; dest_confirmed: boolean }
