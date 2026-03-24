import { authFetch } from '@/lib/auth-fetch'
import { useAuthStore } from '@/store/auth'
import type { DemoDeleteResult, DemoImportResult, ImportResult } from '@/types/inventory'
import type {
  ABCClassification,
  AnalyticsOverview,
  Category,
  Customer,
  CustomerPrice,
  CustomerPriceDetail,
  CustomerPriceHistory,
  CustomerPriceMetrics,
  CustomerType,
  TaxRate,
  TaxRateSummary,
  CustomField,
  CustomMovementField,
  CustomSupplierField,
  CustomWarehouseField,
  CycleCount,
  CycleCountItem,
  DynamicMovementType,
  DynamicWarehouseType,
  EOQResult,
  EntityBatch,
  EntityRecipe,
  EntitySerial,
  EventSeverity,
  EventStatus,
  EventType,
  IRACompute,
  IRATrendPoint,
  InventoryAuditLog,
  InventoryEvent,
  KardexEntry,
  OccupationData,
  OrderType,
  PaginatedInventory,
  PortalOrder,
  PortalOrderDetail,
  PortalStockItem,
  PriceLookupResponse,
  Product,
  ProductDiscrepancy,
  ProductionRun,
  ProductType,
  ProductVariant,
  PurchaseOrder,
  ConsolidationCandidate,
  ConsolidationInfo,
  ConsolidationResult,
  ReorderConfig,
  SalesOrder,
  SOApprovalLog,
  ApprovalThreshold,
  ConfirmWithBackorderOut,
  RemissionData,
  StockReservation,
  SerialStatus,
  StockAlert,
  StockCheckResult,
  StockLayer,
  StockLevel,
  StockMovement,
  StockPolicyResult,
  StorageValuation,
  Supplier,
  SupplierType,
  TraceBackwardOut,
  VariantAttribute,
  Warehouse,
  WarehouseLocation,
  UnitOfMeasure,
  UoMConversion,
  ProductCostHistory,
  ProductPricing,
  PnLReport,
  GlobalMarginConfig,
  ConvertResponse,
  BusinessPartner,
} from '@/types/inventory'

const BASE = import.meta.env.VITE_INVENTORY_API_URL ?? 'http://localhost:9003'

class ApiError extends Error {
  status: number
  body: any
  constructor(status: number, message: string, body?: any) {
    super(message)
    this.status = status
    this.body = body
  }
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const res = await authFetch(`${BASE}${path}`, options)
  if (!res.ok) {
    const err = await res.json().catch(() => null)
    if (res.status === 402) {
      const { usePlanLimitStore } = await import('@/store/planLimit')
      usePlanLimitStore.getState().open({
        resource: err?.resource ?? 'recurso',
        current: err?.current ?? 0,
        limit: err?.limit ?? 0,
        message: err?.error?.message ?? err?.detail ?? 'Has alcanzado el limite de tu plan actual.',
      })
    }
    const msg = err?.error?.message ?? err?.detail?.message ?? err?.detail ?? res.statusText
    throw new ApiError(res.status, msg, err)
  }
  return res.json()
}

async function requestVoid(path: string, options: RequestInit = {}): Promise<void> {
  const res = await authFetch(`${BASE}${path}`, options)
  if (!res.ok) {
    const err = await res.json().catch(() => null)
    if (res.status === 402) {
      const { usePlanLimitStore } = await import('@/store/planLimit')
      usePlanLimitStore.getState().open({
        resource: err?.resource ?? 'recurso',
        current: err?.current ?? 0,
        limit: err?.limit ?? 0,
        message: err?.error?.message ?? err?.detail ?? 'Has alcanzado el limite de tu plan actual.',
      })
    }
    const msg = err?.error?.message ?? err?.detail?.message ?? err?.detail ?? res.statusText
    throw new ApiError(res.status, msg, err)
  }
}

// ─── Categories ──────────────────────────────────────────────────────────────

export const inventoryCategoriesApi = {
  list: (params?: { search?: string; is_active?: boolean; parent_id?: string; offset?: number; limit?: number }) => {
    const qs = new URLSearchParams()
    if (params?.search) qs.set('search', params.search)
    if (params?.is_active !== undefined) qs.set('is_active', String(params.is_active))
    if (params?.parent_id) qs.set('parent_id', params.parent_id)
    if (params?.offset !== undefined) qs.set('offset', String(params.offset))
    if (params?.limit !== undefined) qs.set('limit', String(params.limit))
    return request<PaginatedInventory<Category>>(`/api/v1/categories?${qs}`)
  },
  get: (id: string) => request<Category>(`/api/v1/categories/${id}`),
  create: (data: { name: string; description?: string | null; parent_id?: string | null; is_active?: boolean; sort_order?: number }) =>
    request<Category>('/api/v1/categories', { method: 'POST', body: JSON.stringify(data) }),
  update: (id: string, data: { name?: string; description?: string | null; parent_id?: string | null; is_active?: boolean; sort_order?: number }) =>
    request<Category>(`/api/v1/categories/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
  delete: (id: string) => requestVoid(`/api/v1/categories/${id}`, { method: 'DELETE' }),
}

// ─── Products ─────────────────────────────────────────────────────────────────

export const inventoryProductsApi = {
  list: (params?: {
    product_type_id?: string
    is_active?: boolean
    search?: string
    stock_status?: 'low' | 'out'
    offset?: number
    limit?: number
  }) => {
    const qs = new URLSearchParams()
    if (params?.product_type_id) qs.set('product_type_id', params.product_type_id)
    if (params?.is_active !== undefined) qs.set('is_active', String(params.is_active))
    if (params?.search) qs.set('search', params.search)
    if (params?.stock_status) qs.set('stock_status', params.stock_status)
    if (params?.offset !== undefined) qs.set('offset', String(params.offset))
    if (params?.limit !== undefined) qs.set('limit', String(params.limit))
    return request<PaginatedInventory<Product>>(`/api/v1/products?${qs}`)
  },
  get: (id: string) => request<Product>(`/api/v1/products/${id}`),
  create: (data: Partial<Product> & { term_ids?: string[] }) =>
    request<Product>('/api/v1/products', { method: 'POST', body: JSON.stringify(data) }),
  update: (id: string, data: Partial<Product> & { term_ids?: string[] }) =>
    request<Product>(`/api/v1/products/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
  delete: (id: string) => requestVoid(`/api/v1/products/${id}`, { method: 'DELETE' }),
  uploadImage: async (productId: string, file: File): Promise<Product> => {
    const form = new FormData()
    form.append('file', file)
    const headers: Record<string, string> = {}
    const token = useAuthStore.getState().accessToken
    if (token) headers['Authorization'] = `Bearer ${token}`
    const tenantId = useAuthStore.getState().user?.tenant_id ?? 'default'
    headers['X-Tenant-Id'] = tenantId
    const userId = useAuthStore.getState().user?.id ?? '1'
    headers['X-User-Id'] = userId
    const res = await fetch(`${BASE}/api/v1/products/${productId}/images`, {
      method: 'POST',
      headers,
      body: form,
    })
    if (!res.ok) {
      const err = await res.json().catch(() => null)
      throw new Error(err?.detail ?? err?.error?.message ?? res.statusText)
    }
    return res.json()
  },
  deleteImage: (productId: string, imageUrl: string) =>
    request<Product>(`/api/v1/products/${productId}/images?image_url=${encodeURIComponent(imageUrl)}`, { method: 'DELETE' }),
}

// ─── Warehouses ───────────────────────────────────────────────────────────────

export const inventoryWarehousesApi = {
  list: () => request<{ items: Warehouse[] }>('/api/v1/warehouses').then(r => r.items),
  get: (id: string) => request<Warehouse>(`/api/v1/warehouses/${id}`),
  create: (data: Partial<Warehouse>) =>
    request<Warehouse>('/api/v1/warehouses', { method: 'POST', body: JSON.stringify(data) }),
  update: (id: string, data: Partial<Warehouse>) =>
    request<Warehouse>(`/api/v1/warehouses/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
  delete: (id: string) => requestVoid(`/api/v1/warehouses/${id}`, { method: 'DELETE' }),
}

// ─── Stock ────────────────────────────────────────────────────────────────────

export const inventoryStockApi = {
  list: (params?: { product_id?: string; warehouse_id?: string; location_id?: string; limit?: number }) => {
    const qs = new URLSearchParams()
    if (params?.product_id) qs.set('product_id', params.product_id)
    if (params?.warehouse_id) qs.set('warehouse_id', params.warehouse_id)
    if (params?.location_id) qs.set('location_id', params.location_id)
    qs.set('limit', String(params?.limit ?? 200))
    return request<{ items: StockLevel[] }>(`/api/v1/stock?${qs}`).then(r => r.items)
  },
  assignLocation: (levelId: string, locationId: string | null) =>
    request<StockLevel>(`/api/v1/stock/levels/${levelId}/location`, { method: 'PATCH', body: JSON.stringify({ location_id: locationId }) }),
  receive: (data: { product_id: string; warehouse_id: string; quantity: string; unit_cost?: string; reference?: string; variant_id?: string; location_id?: string }) =>
    request<StockMovement>('/api/v1/stock/receive', { method: 'POST', body: JSON.stringify(data) }),
  issue: (data: { product_id: string; warehouse_id: string; quantity: string; reference?: string; variant_id?: string }) =>
    request<StockMovement>('/api/v1/stock/issue', { method: 'POST', body: JSON.stringify(data) }),
  transfer: (data: { product_id: string; from_warehouse_id: string; to_warehouse_id: string; quantity: string; variant_id?: string }) =>
    request<StockMovement>('/api/v1/stock/transfer', { method: 'POST', body: JSON.stringify(data) }),
  adjust: (data: { product_id: string; warehouse_id: string; new_qty: string; reason?: string; variant_id?: string }) =>
    request<StockMovement>('/api/v1/stock/adjust', { method: 'POST', body: JSON.stringify(data) }),
  adjust_in: (data: { product_id: string; warehouse_id: string; quantity: string; reason?: string; variant_id?: string }) =>
    request<StockMovement>('/api/v1/stock/adjust-in', { method: 'POST', body: JSON.stringify(data) }),
  adjust_out: (data: { product_id: string; warehouse_id: string; quantity: string; reason?: string; variant_id?: string }) =>
    request<StockMovement>('/api/v1/stock/adjust-out', { method: 'POST', body: JSON.stringify(data) }),
  return_stock: (data: { product_id: string; warehouse_id: string; quantity: string; reference?: string; notes?: string; variant_id?: string }) =>
    request<StockMovement>('/api/v1/stock/return', { method: 'POST', body: JSON.stringify(data) }),
  waste: (data: { product_id: string; warehouse_id: string; quantity: string; reason?: string; variant_id?: string }) =>
    request<StockMovement>('/api/v1/stock/waste', { method: 'POST', body: JSON.stringify(data) }),
  qcApprove: (data: { product_id: string; warehouse_id: string; batch_id?: string; variant_id?: string; notes?: string }) =>
    request<StockLevel>('/api/v1/stock/qc-approve', { method: 'POST', body: JSON.stringify(data) }),
  qcReject: (data: { product_id: string; warehouse_id: string; batch_id?: string; variant_id?: string; notes?: string }) =>
    request<StockLevel>('/api/v1/stock/qc-reject', { method: 'POST', body: JSON.stringify(data) }),
  initiateTransfer: (data: { product_id: string; from_warehouse_id: string; to_warehouse_id: string; quantity: number; variant_id?: string; notes?: string }) =>
    request<StockMovement>('/api/v1/stock/transfer/initiate', { method: 'POST', body: JSON.stringify(data) }),
  completeTransfer: (movementId: string) =>
    request<StockMovement>(`/api/v1/stock/transfer/${movementId}/complete`, { method: 'POST' }),
  getAvailability: (productId: string) =>
    request<{ on_hand: number; reserved: number; available: number; in_transit: number }>(`/api/v1/stock/availability/${productId}`),
}

// ─── Movements ────────────────────────────────────────────────────────────────

export const inventoryMovementsApi = {
  list: (params?: { product_id?: string; movement_type?: string; status?: string; search?: string; offset?: number; limit?: number }) => {
    const qs = new URLSearchParams()
    if (params?.product_id) qs.set('product_id', params.product_id)
    if (params?.movement_type) qs.set('movement_type', params.movement_type)
    if (params?.status) qs.set('status', params.status)
    if (params?.search) qs.set('search', params.search)
    if (params?.offset !== undefined) qs.set('offset', String(params.offset))
    if (params?.limit !== undefined) qs.set('limit', String(params.limit))
    return request<PaginatedInventory<StockMovement>>(`/api/v1/movements?${qs}`)
  },
}

// ─── Suppliers ────────────────────────────────────────────────────────────────

export const inventorySuppliersApi = {
  list: () => request<PaginatedInventory<Supplier>>('/api/v1/suppliers'),
  get: (id: string) => request<Supplier>(`/api/v1/suppliers/${id}`),
  create: (data: Partial<Supplier>) =>
    request<Supplier>('/api/v1/suppliers', { method: 'POST', body: JSON.stringify(data) }),
  update: (id: string, data: Partial<Supplier>) =>
    request<Supplier>(`/api/v1/suppliers/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
  delete: (id: string) => requestVoid(`/api/v1/suppliers/${id}`, { method: 'DELETE' }),
}

// ─── Purchase Orders ──────────────────────────────────────────────────────────

export const inventoryPOApi = {
  list: (params?: { status?: string; supplier_id?: string; offset?: number; limit?: number }) => {
    const qs = new URLSearchParams()
    if (params?.status) qs.set('status', params.status)
    if (params?.supplier_id) qs.set('supplier_id', params.supplier_id)
    if (params?.offset !== undefined) qs.set('offset', String(params.offset))
    if (params?.limit !== undefined) qs.set('limit', String(params.limit))
    return request<PaginatedInventory<PurchaseOrder>>(`/api/v1/purchase-orders?${qs}`)
  },
  get: (id: string) => request<PurchaseOrder>(`/api/v1/purchase-orders/${id}`),
  create: (data: {
    supplier_id: string
    warehouse_id?: string
    expected_date?: string
    notes?: string
    lines: Array<{ product_id: string; qty_ordered: string; unit_cost: string; variant_id?: string | null }>
  }) =>
    request<PurchaseOrder>('/api/v1/purchase-orders', { method: 'POST', body: JSON.stringify(data) }),
  update: (id: string, data: Partial<PurchaseOrder>) =>
    request<PurchaseOrder>(`/api/v1/purchase-orders/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
  send: (id: string) =>
    request<PurchaseOrder>(`/api/v1/purchase-orders/${id}/send`, { method: 'POST' }),
  confirm: (id: string) =>
    request<PurchaseOrder>(`/api/v1/purchase-orders/${id}/confirm`, { method: 'POST' }),
  cancel: (id: string) =>
    request<PurchaseOrder>(`/api/v1/purchase-orders/${id}/cancel`, { method: 'POST' }),
  receive: (id: string, data: {
    lines: Array<{ line_id: string; qty_received: string }>;
    supplier_invoice_number?: string | null;
    supplier_invoice_date?: string | null;
    supplier_invoice_total?: number | null;
    payment_terms?: string | null;
    payment_due_date?: string | null;
    attachments?: Array<{ url: string; name: string; type: string; classification: string }> | null;
  }) =>
    request<PurchaseOrder>(`/api/v1/purchase-orders/${id}/receive`, {
      method: 'POST',
      body: JSON.stringify(data),
    }),
  delete: (id: string) => requestVoid(`/api/v1/purchase-orders/${id}`, { method: 'DELETE' }),
  consolidate: (po_ids: string[]) =>
    request<ConsolidationResult>('/api/v1/purchase-orders/consolidate', { method: 'POST', body: JSON.stringify({ po_ids }) }),
  consolidationCandidates: () =>
    request<ConsolidationCandidate[]>('/api/v1/purchase-orders/consolidation-candidates'),
  consolidationInfo: (poId: string) =>
    request<ConsolidationInfo>(`/api/v1/purchase-orders/${poId}/consolidation-info`),
  deconsolidate: (poId: string) =>
    request<PurchaseOrder[]>(`/api/v1/purchase-orders/${poId}/deconsolidate`, { method: 'POST' }),
  submitForApproval: (id: string) =>
    request<PurchaseOrder>(`/api/v1/purchase-orders/${id}/submit-approval`, { method: 'POST' }),
  approve: (id: string) =>
    request<PurchaseOrder>(`/api/v1/purchase-orders/${id}/approve`, { method: 'POST' }),
  reject: (id: string, reason: string) =>
    request<PurchaseOrder>(`/api/v1/purchase-orders/${id}/reject`, { method: 'POST', body: JSON.stringify({ reason }) }),
  getApprovalLog: (id: string) =>
    request<Array<{ id: string; action: string; performed_by: string; performed_by_name: string | null; reason: string | null; po_total: number | null; created_at: string }>>(`/api/v1/purchase-orders/${id}/approval-log`),
  getPdf: (id: string) =>
    request<Blob>(`/api/v1/purchase-orders/${id}/pdf`),
  uploadAttachment: async (poId: string, file: File, classification: string): Promise<{ url: string; name: string; type: string; classification: string }> => {
    const formData = new FormData()
    formData.append('file', file)
    // Must use raw fetch to avoid authFetch setting Content-Type: application/json
    const token = (await import('@/store/auth')).useAuthStore.getState().accessToken
    const tenantId = (await import('@/store/auth')).useAuthStore.getState().user?.tenant_id
    const headers: Record<string, string> = {}
    if (token) headers['Authorization'] = `Bearer ${token}`
    if (tenantId) headers['X-Tenant-Id'] = tenantId
    const res = await fetch(`${BASE}/api/v1/purchase-orders/${poId}/upload-attachment?classification=${encodeURIComponent(classification)}`, {
      method: 'POST',
      body: formData,
      headers,
    })
    if (!res.ok) {
      const err = await res.json().catch(() => null)
      throw new Error(err?.detail ?? 'Error al subir archivo')
    }
    return res.json()
  },
}

// ─── Analytics ────────────────────────────────────────────────────────────────

export const inventoryAnalyticsApi = {
  overview: () => request<AnalyticsOverview>('/api/v1/analytics/overview'),
  occupation: (warehouseId?: string) => {
    const qs = new URLSearchParams()
    if (warehouseId) qs.set('warehouse_id', warehouseId)
    return request<OccupationData>(`/api/v1/analytics/occupation?${qs}`)
  },
  abc: (months = 12) =>
    request<ABCClassification>(`/api/v1/analytics/abc?months=${months}`),
  eoq: (orderingCost = 50, holdingCostPct = 25) =>
    request<EOQResult>(`/api/v1/analytics/eoq?ordering_cost=${orderingCost}&holding_cost_pct=${holdingCostPct}`),
  stockPolicy: () =>
    request<StockPolicyResult>('/api/v1/analytics/stock-policy'),
  storageValuation: () =>
    request<StorageValuation>('/api/v1/analytics/storage-valuation'),
  committedStock: () =>
    request<{ products_with_reservations: number; total_reserved_qty: number; total_reserved_value: number; currency: string }>('/api/v1/analytics/committed-stock'),
}

// ─── Config ───────────────────────────────────────────────────────────────────

export const inventoryConfigApi = {
  // Product types
  listProductTypes: () => request<{ items: ProductType[] }>('/api/v1/config/product-types').then(r => r.items),
  createProductType: (data: Partial<ProductType>) =>
    request<ProductType>('/api/v1/config/product-types', { method: 'POST', body: JSON.stringify(data) }),
  updateProductType: (id: string, data: Partial<ProductType>) =>
    request<ProductType>(`/api/v1/config/product-types/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
  deleteProductType: (id: string) => requestVoid(`/api/v1/config/product-types/${id}`, { method: 'DELETE' }),

  // Order types
  listOrderTypes: () => request<{ items: OrderType[] }>('/api/v1/config/order-types').then(r => r.items),
  createOrderType: (data: Partial<OrderType>) =>
    request<OrderType>('/api/v1/config/order-types', { method: 'POST', body: JSON.stringify(data) }),
  updateOrderType: (id: string, data: Partial<OrderType>) =>
    request<OrderType>(`/api/v1/config/order-types/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
  deleteOrderType: (id: string) => requestVoid(`/api/v1/config/order-types/${id}`, { method: 'DELETE' }),

  // Custom product fields
  listCustomFields: (productTypeId?: string) =>
    request<{ items: CustomField[] }>(`/api/v1/config/custom-fields${productTypeId ? `?product_type_id=${productTypeId}` : ''}`).then(r => r.items),
  createCustomField: (data: Partial<CustomField>) =>
    request<CustomField>('/api/v1/config/custom-fields', { method: 'POST', body: JSON.stringify(data) }),
  updateCustomField: (id: string, data: Partial<CustomField>) =>
    request<CustomField>(`/api/v1/config/custom-fields/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
  deleteCustomField: (id: string) => requestVoid(`/api/v1/config/custom-fields/${id}`, { method: 'DELETE' }),

  // Supplier types
  listSupplierTypes: () => request<{ items: SupplierType[] }>('/api/v1/config/supplier-types').then(r => r.items),
  createSupplierType: (data: Partial<SupplierType>) =>
    request<SupplierType>('/api/v1/config/supplier-types', { method: 'POST', body: JSON.stringify(data) }),
  updateSupplierType: (id: string, data: Partial<SupplierType>) =>
    request<SupplierType>(`/api/v1/config/supplier-types/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
  deleteSupplierType: (id: string) => requestVoid(`/api/v1/config/supplier-types/${id}`, { method: 'DELETE' }),

  // Custom supplier fields
  listSupplierFields: (supplierTypeId?: string) =>
    request<{ items: CustomSupplierField[] }>(`/api/v1/config/supplier-fields${supplierTypeId ? `?supplier_type_id=${supplierTypeId}` : ''}`).then(r => r.items),
  createSupplierField: (data: Partial<CustomSupplierField>) =>
    request<CustomSupplierField>('/api/v1/config/supplier-fields', { method: 'POST', body: JSON.stringify(data) }),
  updateSupplierField: (id: string, data: Partial<CustomSupplierField>) =>
    request<CustomSupplierField>(`/api/v1/config/supplier-fields/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
  deleteSupplierField: (id: string) => requestVoid(`/api/v1/config/supplier-fields/${id}`, { method: 'DELETE' }),

  // Custom warehouse fields
  listWarehouseFields: (warehouseTypeId?: string) =>
    request<{ items: CustomWarehouseField[] }>(`/api/v1/config/warehouse-fields${warehouseTypeId ? `?warehouse_type_id=${warehouseTypeId}` : ''}`).then(r => r.items),
  createWarehouseField: (data: Partial<CustomWarehouseField>) =>
    request<CustomWarehouseField>('/api/v1/config/warehouse-fields', { method: 'POST', body: JSON.stringify(data) }),
  updateWarehouseField: (id: string, data: Partial<CustomWarehouseField>) =>
    request<CustomWarehouseField>(`/api/v1/config/warehouse-fields/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
  deleteWarehouseField: (id: string) => requestVoid(`/api/v1/config/warehouse-fields/${id}`, { method: 'DELETE' }),

  // Custom movement fields
  listMovementFields: (movementTypeId?: string) =>
    request<{ items: CustomMovementField[] }>(`/api/v1/config/movement-fields${movementTypeId ? `?movement_type_id=${movementTypeId}` : ''}`).then(r => r.items),
  createMovementField: (data: Partial<CustomMovementField>) =>
    request<CustomMovementField>('/api/v1/config/movement-fields', { method: 'POST', body: JSON.stringify(data) }),
  updateMovementField: (id: string, data: Partial<CustomMovementField>) =>
    request<CustomMovementField>(`/api/v1/config/movement-fields/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
  deleteMovementField: (id: string) => requestVoid(`/api/v1/config/movement-fields/${id}`, { method: 'DELETE' }),

  // SO Approval threshold
  getApprovalThreshold: () => request<ApprovalThreshold>('/api/v1/config/so-approval-threshold'),
  updateApprovalThreshold: (threshold: number | null) => request<ApprovalThreshold>('/api/v1/config/so-approval-threshold', { method: 'PATCH', body: JSON.stringify({ threshold }) }),

  // Feature toggles
  getFeatures: () => request<Record<string, boolean>>('/api/v1/config/features'),
  updateFeatures: (data: Record<string, boolean>) =>
    request<Record<string, boolean>>('/api/v1/config/features', { method: 'PATCH', body: JSON.stringify(data) }),
}

// ─── Reports (download CSV) ───────────────────────────────────────────────────

export const inventoryReportsApi = {
  downloadProducts: () =>
    fetch(`${BASE}/api/v1/reports/products`, {
      headers: { Authorization: `Bearer ${useAuthStore.getState().accessToken ?? ''}` },
    }),
  downloadStock: () =>
    fetch(`${BASE}/api/v1/reports/stock`, {
      headers: { Authorization: `Bearer ${useAuthStore.getState().accessToken ?? ''}` },
    }),
  downloadSuppliers: () =>
    fetch(`${BASE}/api/v1/reports/suppliers`, {
      headers: { Authorization: `Bearer ${useAuthStore.getState().accessToken ?? ''}` },
    }),
  downloadMovements: (dateFrom?: string, dateTo?: string) => {
    const qs = new URLSearchParams()
    if (dateFrom) qs.set('date_from', dateFrom)
    if (dateTo) qs.set('date_to', dateTo)
    return fetch(`${BASE}/api/v1/reports/movements?${qs}`, {
      headers: { Authorization: `Bearer ${useAuthStore.getState().accessToken ?? ''}` },
    })
  },
  downloadEvents: (dateFrom?: string, dateTo?: string) => {
    const qs = new URLSearchParams()
    if (dateFrom) qs.set('date_from', dateFrom)
    if (dateTo) qs.set('date_to', dateTo)
    return fetch(`${BASE}/api/v1/reports/events?${qs}`, {
      headers: { Authorization: `Bearer ${useAuthStore.getState().accessToken ?? ''}` },
    })
  },
  downloadSerials: () =>
    fetch(`${BASE}/api/v1/reports/serials`, {
      headers: { Authorization: `Bearer ${useAuthStore.getState().accessToken ?? ''}` },
    }),
  downloadBatches: () =>
    fetch(`${BASE}/api/v1/reports/batches`, {
      headers: { Authorization: `Bearer ${useAuthStore.getState().accessToken ?? ''}` },
    }),
  downloadPurchaseOrders: (dateFrom?: string, dateTo?: string) => {
    const qs = new URLSearchParams()
    if (dateFrom) qs.set('date_from', dateFrom)
    if (dateTo) qs.set('date_to', dateTo)
    return fetch(`${BASE}/api/v1/reports/purchase-orders?${qs}`, {
      headers: { Authorization: `Bearer ${useAuthStore.getState().accessToken ?? ''}` },
    })
  },
}

// ─── Movement Types ──────────────────────────────────────────────────────────

export const inventoryMovementTypesApi = {
  list: () => request<{ items: DynamicMovementType[] }>('/api/v1/config/movement-types').then(r => r.items),
  create: (data: Partial<DynamicMovementType>) =>
    request<DynamicMovementType>('/api/v1/config/movement-types', { method: 'POST', body: JSON.stringify(data) }),
  update: (id: string, data: Partial<DynamicMovementType>) =>
    request<DynamicMovementType>(`/api/v1/config/movement-types/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
  delete: (id: string) => requestVoid(`/api/v1/config/movement-types/${id}`, { method: 'DELETE' }),
}

// ─── Warehouse Types ─────────────────────────────────────────────────────────

export const inventoryWarehouseTypesApi = {
  list: () => request<{ items: DynamicWarehouseType[] }>('/api/v1/config/warehouse-types').then(r => r.items),
  create: (data: Partial<DynamicWarehouseType>) =>
    request<DynamicWarehouseType>('/api/v1/config/warehouse-types', { method: 'POST', body: JSON.stringify(data) }),
  update: (id: string, data: Partial<DynamicWarehouseType>) =>
    request<DynamicWarehouseType>(`/api/v1/config/warehouse-types/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
  delete: (id: string) => requestVoid(`/api/v1/config/warehouse-types/${id}`, { method: 'DELETE' }),
}

// ─── Locations ───────────────────────────────────────────────────────────────

export const inventoryLocationsApi = {
  list: (warehouseId?: string) => {
    const qs = new URLSearchParams()
    if (warehouseId) qs.set('warehouse_id', warehouseId)
    return request<{ items: WarehouseLocation[] }>(`/api/v1/config/locations?${qs}`).then(r => r.items)
  },
  create: (data: Partial<WarehouseLocation>) =>
    request<WarehouseLocation>('/api/v1/config/locations', { method: 'POST', body: JSON.stringify(data) }),
  update: (id: string, data: Partial<WarehouseLocation>) =>
    request<WarehouseLocation>(`/api/v1/config/locations/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
  delete: (id: string) => requestVoid(`/api/v1/config/locations/${id}`, { method: 'DELETE' }),
}

// ─── Event Config ────────────────────────────────────────────────────────────

export const inventoryEventConfigApi = {
  listEventTypes: () => request<{ items: EventType[] }>('/api/v1/config/event-types').then(r => r.items),
  createEventType: (data: Partial<EventType>) =>
    request<EventType>('/api/v1/config/event-types', { method: 'POST', body: JSON.stringify(data) }),
  updateEventType: (id: string, data: Partial<EventType>) =>
    request<EventType>(`/api/v1/config/event-types/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
  deleteEventType: (id: string) => requestVoid(`/api/v1/config/event-types/${id}`, { method: 'DELETE' }),

  listSeverities: () => request<{ items: EventSeverity[] }>('/api/v1/config/event-severities').then(r => r.items),
  createSeverity: (data: Partial<EventSeverity>) =>
    request<EventSeverity>('/api/v1/config/event-severities', { method: 'POST', body: JSON.stringify(data) }),
  updateSeverity: (id: string, data: Partial<EventSeverity>) =>
    request<EventSeverity>(`/api/v1/config/event-severities/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
  deleteSeverity: (id: string) => requestVoid(`/api/v1/config/event-severities/${id}`, { method: 'DELETE' }),

  listStatuses: () => request<{ items: EventStatus[] }>('/api/v1/config/event-statuses').then(r => r.items),
  createStatus: (data: Partial<EventStatus>) =>
    request<EventStatus>('/api/v1/config/event-statuses', { method: 'POST', body: JSON.stringify(data) }),
  updateStatus: (id: string, data: Partial<EventStatus>) =>
    request<EventStatus>(`/api/v1/config/event-statuses/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
  deleteStatus: (id: string) => requestVoid(`/api/v1/config/event-statuses/${id}`, { method: 'DELETE' }),

  listSerialStatuses: () => request<{ items: SerialStatus[] }>('/api/v1/config/serial-statuses').then(r => r.items),
  createSerialStatus: (data: Partial<SerialStatus>) =>
    request<SerialStatus>('/api/v1/config/serial-statuses', { method: 'POST', body: JSON.stringify(data) }),
  updateSerialStatus: (id: string, data: Partial<SerialStatus>) =>
    request<SerialStatus>(`/api/v1/config/serial-statuses/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
  deleteSerialStatus: (id: string) => requestVoid(`/api/v1/config/serial-statuses/${id}`, { method: 'DELETE' }),
}

// ─── Events ──────────────────────────────────────────────────────────────────

export const inventoryEventsApi = {
  list: (params?: { event_type_id?: string; severity_id?: string; status_id?: string; offset?: number; limit?: number }) => {
    const qs = new URLSearchParams()
    if (params?.event_type_id) qs.set('event_type_id', params.event_type_id)
    if (params?.severity_id) qs.set('severity_id', params.severity_id)
    if (params?.status_id) qs.set('status_id', params.status_id)
    if (params?.offset !== undefined) qs.set('offset', String(params.offset))
    if (params?.limit !== undefined) qs.set('limit', String(params.limit))
    return request<PaginatedInventory<InventoryEvent>>(`/api/v1/events?${qs}`)
  },
  get: (id: string) => request<InventoryEvent>(`/api/v1/events/${id}`),
  create: (data: Record<string, unknown>) =>
    request<InventoryEvent>('/api/v1/events', { method: 'POST', body: JSON.stringify(data) }),
  changeStatus: (id: string, data: { status_id: string; notes?: string; changed_by?: string; resolved_at?: string }) =>
    request<InventoryEvent>(`/api/v1/events/${id}/status`, { method: 'POST', body: JSON.stringify(data) }),
  addImpact: (eventId: string, data: Record<string, unknown>) =>
    request<unknown>(`/api/v1/events/${eventId}/impacts`, { method: 'POST', body: JSON.stringify(data) }),
}

// ─── Serials ─────────────────────────────────────────────────────────────────

export const inventorySerialsApi = {
  list: (params?: { entity_id?: string; status_id?: string; warehouse_id?: string; offset?: number; limit?: number }) => {
    const qs = new URLSearchParams()
    if (params?.entity_id) qs.set('entity_id', params.entity_id)
    if (params?.status_id) qs.set('status_id', params.status_id)
    if (params?.warehouse_id) qs.set('warehouse_id', params.warehouse_id)
    if (params?.offset !== undefined) qs.set('offset', String(params.offset))
    if (params?.limit !== undefined) qs.set('limit', String(params.limit))
    return request<PaginatedInventory<EntitySerial>>(`/api/v1/serials?${qs}`)
  },
  get: (id: string) => request<EntitySerial>(`/api/v1/serials/${id}`),
  create: (data: Record<string, unknown>) =>
    request<EntitySerial>('/api/v1/serials', { method: 'POST', body: JSON.stringify(data) }),
  update: (id: string, data: Record<string, unknown>) =>
    request<EntitySerial>(`/api/v1/serials/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
  delete: (id: string) => requestVoid(`/api/v1/serials/${id}`, { method: 'DELETE' }),
}

// ─── Batches ─────────────────────────────────────────────────────────────────

export const inventoryBatchesApi = {
  list: (params?: { entity_id?: string; is_active?: boolean; offset?: number; limit?: number }) => {
    const qs = new URLSearchParams()
    if (params?.entity_id) qs.set('entity_id', params.entity_id)
    if (params?.is_active !== undefined) qs.set('is_active', String(params.is_active))
    if (params?.offset !== undefined) qs.set('offset', String(params.offset))
    if (params?.limit !== undefined) qs.set('limit', String(params.limit))
    return request<PaginatedInventory<EntityBatch>>(`/api/v1/batches?${qs}`)
  },
  get: (id: string) => request<EntityBatch>(`/api/v1/batches/${id}`),
  create: (data: Record<string, unknown>) =>
    request<EntityBatch>('/api/v1/batches', { method: 'POST', body: JSON.stringify(data) }),
  update: (id: string, data: Record<string, unknown>) =>
    request<EntityBatch>(`/api/v1/batches/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
  delete: (id: string) => requestVoid(`/api/v1/batches/${id}`, { method: 'DELETE' }),
}

// ─── Recipes ─────────────────────────────────────────────────────────────────

export const inventoryRecipesApi = {
  list: () => request<{ items: EntityRecipe[] }>('/api/v1/recipes').then(r => r.items),
  get: (id: string) => request<EntityRecipe>(`/api/v1/recipes/${id}`),
  create: (data: Record<string, unknown>) =>
    request<EntityRecipe>('/api/v1/recipes', { method: 'POST', body: JSON.stringify(data) }),
  update: (id: string, data: Record<string, unknown>) =>
    request<EntityRecipe>(`/api/v1/recipes/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
  delete: (id: string) => requestVoid(`/api/v1/recipes/${id}`, { method: 'DELETE' }),
}

// ─── Production Runs ─────────────────────────────────────────────────────────

export const inventoryProductionApi = {
  list: (params?: { status?: string; offset?: number; limit?: number }) => {
    const qs = new URLSearchParams()
    if (params?.status) qs.set('status', params.status)
    if (params?.offset !== undefined) qs.set('offset', String(params.offset))
    if (params?.limit !== undefined) qs.set('limit', String(params.limit))
    return request<PaginatedInventory<ProductionRun>>(`/api/v1/production-runs?${qs}`)
  },
  get: (id: string) => request<ProductionRun>(`/api/v1/production-runs/${id}`),
  create: (data: { recipe_id: string; warehouse_id: string; multiplier?: string; notes?: string }) =>
    request<ProductionRun>('/api/v1/production-runs', { method: 'POST', body: JSON.stringify(data) }),
  execute: (id: string) =>
    request<ProductionRun>(`/api/v1/production-runs/${id}/execute`, { method: 'POST' }),
  finish: (id: string) =>
    request<ProductionRun>(`/api/v1/production-runs/${id}/finish`, { method: 'POST' }),
  approve: (id: string) =>
    request<ProductionRun>(`/api/v1/production-runs/${id}/approve`, { method: 'POST' }),
  reject: (id: string, rejection_notes: string) =>
    request<ProductionRun>(`/api/v1/production-runs/${id}/reject`, {
      method: 'POST', body: JSON.stringify({ rejection_notes }),
    }),
  delete: (id: string) => requestVoid(`/api/v1/production-runs/${id}`, { method: 'DELETE' }),
}

// ─── Cycle Counts ───────────────────────────────────────────────────────────

export const inventoryCycleCountsApi = {
  list: (params?: { status?: string; warehouse_id?: string; offset?: number; limit?: number }) => {
    const qs = new URLSearchParams()
    if (params?.status) qs.set('status', params.status)
    if (params?.warehouse_id) qs.set('warehouse_id', params.warehouse_id)
    if (params?.offset !== undefined) qs.set('offset', String(params.offset))
    if (params?.limit !== undefined) qs.set('limit', String(params.limit))
    return request<PaginatedInventory<CycleCount>>(`/api/v1/cycle-counts?${qs}`)
  },
  get: (id: string) => request<CycleCount>(`/api/v1/cycle-counts/${id}`),
  create: (data: {
    warehouse_id: string
    product_ids?: string[]
    methodology?: string
    assigned_counters?: number
    minutes_per_count?: number
    scheduled_date?: string
    notes?: string
  }) =>
    request<CycleCount>('/api/v1/cycle-counts', { method: 'POST', body: JSON.stringify(data) }),
  start: (id: string) =>
    request<CycleCount>(`/api/v1/cycle-counts/${id}/start`, { method: 'POST' }),
  recordCount: (ccId: string, itemId: string, data: { counted_qty: string; notes?: string }) =>
    request<CycleCountItem>(`/api/v1/cycle-counts/${ccId}/items/${itemId}/count`, {
      method: 'POST', body: JSON.stringify(data),
    }),
  recount: (ccId: string, itemId: string, data: { recount_qty: string; root_cause?: string; notes?: string }) =>
    request<CycleCountItem>(`/api/v1/cycle-counts/${ccId}/items/${itemId}/recount`, {
      method: 'POST', body: JSON.stringify(data),
    }),
  complete: (id: string) =>
    request<CycleCount>(`/api/v1/cycle-counts/${id}/complete`, { method: 'POST' }),
  approve: (id: string) =>
    request<CycleCount>(`/api/v1/cycle-counts/${id}/approve`, { method: 'POST' }),
  cancel: (id: string) =>
    request<CycleCount>(`/api/v1/cycle-counts/${id}/cancel`, { method: 'POST' }),
  getIRA: (id: string) =>
    request<IRACompute>(`/api/v1/cycle-counts/${id}/ira`),
  iraTrend: (params?: { warehouse_id?: string }) => {
    const qs = new URLSearchParams()
    if (params?.warehouse_id) qs.set('warehouse_id', params.warehouse_id)
    return request<IRATrendPoint[]>(`/api/v1/cycle-counts/analytics/ira-trend?${qs}`)
  },
  productHistory: (productId: string) =>
    request<ProductDiscrepancy[]>(`/api/v1/cycle-counts/analytics/product-history/${productId}`),
}

// ─── Imports (CSV + Demo) ────────────────────────────────────────────────────

export const inventoryImportsApi = {
  uploadCsv: async (file: File): Promise<ImportResult> => {
    const fd = new FormData()
    fd.append('file', file)
    const res = await fetch(`${BASE}/api/v1/imports/products`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${useAuthStore.getState().accessToken ?? ''}` },
      body: fd,
    })
    if (!res.ok) {
      const err = await res.json().catch(() => null)
      throw new Error(err?.detail ?? res.statusText)
    }
    return res.json()
  },

  downloadTemplate: (name: string) =>
    fetch(`${BASE}/api/v1/imports/templates/${name}`, {
      headers: { Authorization: `Bearer ${useAuthStore.getState().accessToken ?? ''}` },
    }),

  importDemo: (industries: string[]) =>
    request<DemoImportResult[]>('/api/v1/imports/demo', {
      method: 'POST',
      body: JSON.stringify({ industries }),
    }),

  deleteDemo: (industries: string[]) =>
    request<DemoDeleteResult[]>('/api/v1/imports/demo', {
      method: 'DELETE',
      body: JSON.stringify({ industries }),
    }),
}

// ─── Audit ──────────────────────────────────────────────────────────────────

export const inventoryAuditApi = {
  list: (params?: {
    action?: string
    user_id?: string
    resource_type?: string
    resource_id?: string
    date_from?: string
    date_to?: string
    offset?: number
    limit?: number
  }) => {
    const qs = new URLSearchParams()
    if (params?.action) qs.set('action', params.action)
    if (params?.user_id) qs.set('user_id', params.user_id)
    if (params?.resource_type) qs.set('resource_type', params.resource_type)
    if (params?.resource_id) qs.set('resource_id', params.resource_id)
    if (params?.date_from) qs.set('date_from', params.date_from)
    if (params?.date_to) qs.set('date_to', params.date_to)
    if (params?.offset !== undefined) qs.set('offset', String(params.offset))
    if (params?.limit !== undefined) qs.set('limit', String(params.limit))
    return request<PaginatedInventory<InventoryAuditLog>>(`/api/v1/audit?${qs}`)
  },
  entityTimeline: (resourceType: string, resourceId: string, params?: { offset?: number; limit?: number }) => {
    const qs = new URLSearchParams()
    if (params?.offset !== undefined) qs.set('offset', String(params.offset))
    if (params?.limit !== undefined) qs.set('limit', String(params.limit))
    return request<PaginatedInventory<InventoryAuditLog>>(`/api/v1/audit/entity/${resourceType}/${resourceId}?${qs}`)
  },
}

// ─── Customers ────────────────────────────────────────────────────────────────

export const inventoryCustomersApi = {
  list: (params?: { customer_type_id?: string; is_active?: boolean; search?: string; offset?: number; limit?: number }) => {
    const qs = new URLSearchParams()
    if (params?.customer_type_id) qs.set('customer_type_id', params.customer_type_id)
    if (params?.is_active !== undefined) qs.set('is_active', String(params.is_active))
    if (params?.search) qs.set('search', params.search)
    if (params?.offset !== undefined) qs.set('offset', String(params.offset))
    if (params?.limit !== undefined) qs.set('limit', String(params.limit))
    return request<PaginatedInventory<Customer>>(`/api/v1/customers?${qs}`)
  },
  get: (id: string) => request<Customer>(`/api/v1/customers/${id}`),
  prices: (id: string) => request<Record<string, Array<{ unit_price: number; min_quantity: number; discount_pct: number; variant_id: string | null }>>>(`/api/v1/customers/${id}/prices`),
  create: (data: Partial<Customer>) => request<Customer>('/api/v1/customers', { method: 'POST', body: JSON.stringify(data) }),
  update: (id: string, data: Partial<Customer>) => request<Customer>(`/api/v1/customers/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
  delete: (id: string) => requestVoid(`/api/v1/customers/${id}`, { method: 'DELETE' }),
}

export const inventoryCustomerTypesApi = {
  list: () => request<{ items: CustomerType[] }>('/api/v1/config/customer-types').then(r => r.items),
  create: (data: Partial<CustomerType>) => request<CustomerType>('/api/v1/config/customer-types', { method: 'POST', body: JSON.stringify(data) }),
  update: (id: string, data: Partial<CustomerType>) => request<CustomerType>(`/api/v1/config/customer-types/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
  delete: (id: string) => requestVoid(`/api/v1/config/customer-types/${id}`, { method: 'DELETE' }),
}

// ─── Sales Orders ─────────────────────────────────────────────────────────────

export const inventorySalesOrdersApi = {
  list: (params?: { status?: string; customer_id?: string; offset?: number; limit?: number }) => {
    const qs = new URLSearchParams()
    if (params?.status) qs.set('status', params.status)
    if (params?.customer_id) qs.set('customer_id', params.customer_id)
    if (params?.offset !== undefined) qs.set('offset', String(params.offset))
    if (params?.limit !== undefined) qs.set('limit', String(params.limit))
    return request<PaginatedInventory<SalesOrder>>(`/api/v1/sales-orders?${qs}`)
  },
  get: (id: string) => request<SalesOrder>(`/api/v1/sales-orders/${id}`),
  summary: () => request<Record<string, number>>('/api/v1/sales-orders/summary'),
  create: (data: Record<string, unknown>) => request<SalesOrder>('/api/v1/sales-orders', { method: 'POST', body: JSON.stringify(data) }),
  update: (id: string, data: Record<string, unknown>) => request<SalesOrder>(`/api/v1/sales-orders/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
  confirm: (id: string) => request<ConfirmWithBackorderOut & { approval_required?: boolean; status?: string; message?: string }>(`/api/v1/sales-orders/${id}/confirm`, { method: 'POST' }),
  pick: (id: string) => request<SalesOrder>(`/api/v1/sales-orders/${id}/pick`, { method: 'POST' }),
  ship: (id: string, body?: { line_shipments?: Array<{ line_id: string; qty_shipped: number }>; shipping_info?: Record<string, unknown> }) =>
    request<SalesOrder>(`/api/v1/sales-orders/${id}/ship`, { method: 'POST', body: body ? JSON.stringify(body) : undefined }),
  deliver: (id: string) => request<SalesOrder>(`/api/v1/sales-orders/${id}/deliver`, { method: 'POST' }),
  returnOrder: (id: string) => request<SalesOrder>(`/api/v1/sales-orders/${id}/return`, { method: 'POST' }),
  cancel: (id: string) => request<SalesOrder>(`/api/v1/sales-orders/${id}/cancel`, { method: 'POST' }),
  retryInvoice: (id: string) => request<SalesOrder>(`/api/v1/sales-orders/${id}/retry-invoice`, { method: 'POST' }),
  retryCreditNote: (id: string) => request<SalesOrder>(`/api/v1/sales-orders/${id}/retry-credit-note`, { method: 'POST' }),
  listBackorders: (id: string) => request<SalesOrder[]>(`/api/v1/sales-orders/${id}/backorders`),
  confirmBackorder: (id: string) => request<ConfirmWithBackorderOut>(`/api/v1/sales-orders/${id}/confirm-backorder`, { method: 'POST' }),
  stockCheck: (id: string) => request<StockCheckResult>(`/api/v1/sales-orders/${id}/stock-check`),
  listReservations: (id: string) => request<StockReservation[]>(`/api/v1/sales-orders/${id}/reservations`),
  applyDiscount: (id: string, data: { discount_pct: number; discount_reason?: string | null }) =>
    request<SalesOrder>(`/api/v1/sales-orders/${id}/discount`, { method: 'PATCH', body: JSON.stringify(data) }),
  updateLineWarehouse: (orderId: string, lineId: string, warehouseId: string) =>
    request<SalesOrder>(`/api/v1/sales-orders/${orderId}/lines/${lineId}/warehouse`, {
      method: 'PATCH', body: JSON.stringify({ warehouse_id: warehouseId }),
    }),
  delete: (id: string) => requestVoid(`/api/v1/sales-orders/${id}`, { method: 'DELETE' }),
  getRemission: (id: string) => request<RemissionData>(`/api/v1/sales-orders/${id}/remission`),
  approve: (id: string) => request<ConfirmWithBackorderOut>(`/api/v1/sales-orders/${id}/approve`, { method: 'POST' }),
  reject: (id: string, reason: string) => request<SalesOrder>(`/api/v1/sales-orders/${id}/reject`, { method: 'POST', body: JSON.stringify({ reason }) }),
  resubmit: (id: string) => request<SalesOrder>(`/api/v1/sales-orders/${id}/resubmit`, { method: 'POST' }),
  approvalLog: (id: string) => request<SOApprovalLog[]>(`/api/v1/sales-orders/${id}/approval-log`),
  pendingApprovals: (params?: { offset?: number; limit?: number }) => {
    const qs = new URLSearchParams()
    if (params?.offset !== undefined) qs.set('offset', String(params.offset))
    if (params?.limit !== undefined) qs.set('limit', String(params.limit))
    return request<PaginatedInventory<SalesOrder>>(`/api/v1/sales-orders/pending-approval?${qs}`)
  },
  batches: (soId: string) => request<TraceBackwardOut>(`/api/v1/sales-orders/${soId}/batches`),
}

// ─── Variants ─────────────────────────────────────────────────────────────────

export const inventoryVariantAttributesApi = {
  list: () => request<VariantAttribute[]>('/api/v1/variant-attributes'),
  create: (data: Record<string, unknown>) => request<VariantAttribute>('/api/v1/variant-attributes', { method: 'POST', body: JSON.stringify(data) }),
  update: (id: string, data: Record<string, unknown>) => request<VariantAttribute>(`/api/v1/variant-attributes/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
  delete: (id: string) => requestVoid(`/api/v1/variant-attributes/${id}`, { method: 'DELETE' }),
  addOption: (attrId: string, data: Record<string, unknown>) =>
    request<unknown>(`/api/v1/variant-attributes/${attrId}/options`, { method: 'POST', body: JSON.stringify(data) }),
  updateOption: (optId: string, data: Record<string, unknown>) =>
    request<unknown>(`/api/v1/variant-options/${optId}`, { method: 'PATCH', body: JSON.stringify(data) }),
  deleteOption: (optId: string) => requestVoid(`/api/v1/variant-options/${optId}`, { method: 'DELETE' }),
}

export const inventoryVariantsApi = {
  list: (params?: { parent_id?: string; search?: string; offset?: number; limit?: number }) => {
    const qs = new URLSearchParams()
    if (params?.parent_id) qs.set('parent_id', params.parent_id)
    if (params?.search) qs.set('search', params.search)
    if (params?.offset !== undefined) qs.set('offset', String(params.offset))
    if (params?.limit !== undefined) qs.set('limit', String(params.limit))
    return request<PaginatedInventory<ProductVariant>>(`/api/v1/variants?${qs}`)
  },
  listForProduct: (productId: string) => request<ProductVariant[]>(`/api/v1/products/${productId}/variants`),
  get: (id: string) => request<ProductVariant>(`/api/v1/variants/${id}`),
  create: (data: Record<string, unknown>) => request<ProductVariant>('/api/v1/variants', { method: 'POST', body: JSON.stringify(data) }),
  update: (id: string, data: Record<string, unknown>) => request<ProductVariant>(`/api/v1/variants/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
  delete: (id: string) => requestVoid(`/api/v1/variants/${id}`, { method: 'DELETE' }),
}

// ─── Stock Alerts ─────────────────────────────────────────────────────────────

export const inventoryAlertsApi = {
  list: (params?: { is_resolved?: boolean; alert_type?: string; offset?: number; limit?: number }) => {
    const qs = new URLSearchParams()
    if (params?.is_resolved !== undefined) qs.set('is_resolved', String(params.is_resolved))
    if (params?.alert_type) qs.set('alert_type', params.alert_type)
    if (params?.offset !== undefined) qs.set('offset', String(params.offset))
    if (params?.limit !== undefined) qs.set('limit', String(params.limit))
    return request<PaginatedInventory<StockAlert>>(`/api/v1/alerts?${qs}`)
  },
  unreadCount: () => request<{ count: number }>('/api/v1/alerts/unread-count'),
  markRead: (id: string) => request<StockAlert>(`/api/v1/alerts/${id}/read`, { method: 'POST' }),
  resolve: (id: string) => request<StockAlert>(`/api/v1/alerts/${id}/resolve`, { method: 'POST' }),
  scan: () => request<{ created: number; alerts: Array<{ id: string; type: string; product: string }> }>('/api/v1/alerts/scan', { method: 'POST' }),
}

// ─── Kardex ───────────────────────────────────────────────────────────────────

export const inventoryKardexApi = {
  get: (productId: string, warehouseId?: string) => {
    const qs = new URLSearchParams()
    if (warehouseId) qs.set('warehouse_id', warehouseId)
    return request<KardexEntry[]>(`/api/v1/kardex/${productId}?${qs}`)
  },
}

// ─── Auto Reorder ────────────────────────────────────────────────────────────

export const inventoryReorderApi = {
  config: () => request<ReorderConfig[]>('/api/v1/reorder/config'),
  checkAll: () => request<PurchaseOrder[]>('/api/v1/reorder/check', { method: 'POST' }),
  checkProduct: (productId: string) => request<PurchaseOrder | null>(`/api/v1/reorder/check/${productId}`, { method: 'POST' }),
}

// ─── Portal (customer-facing read-only) ──────────────────────────────────────

export const inventoryPortalApi = {
  getStock: (customerId: string) =>
    request<PortalStockItem[]>(`/api/v1/portal/stock?customer_id=${customerId}`),
  getOrders: (customerId: string, status?: string) => {
    const qs = new URLSearchParams({ customer_id: customerId })
    if (status) qs.set('status', status)
    return request<PortalOrder[]>(`/api/v1/portal/orders?${qs}`)
  },
  getOrderDetail: (orderId: string, customerId: string) =>
    request<PortalOrderDetail>(`/api/v1/portal/orders/${orderId}?customer_id=${customerId}`),
}

// ─── Customer Special Prices ──────────────────────────────────────────────────

export const inventoryCustomerPricesApi = {
  list: (params?: { customer_id?: string; product_id?: string; is_active?: boolean; is_expired?: boolean; offset?: number; limit?: number }) => {
    const qs = new URLSearchParams()
    if (params?.customer_id) qs.set('customer_id', params.customer_id)
    if (params?.product_id) qs.set('product_id', params.product_id)
    if (params?.is_active !== undefined) qs.set('is_active', String(params.is_active))
    if (params?.is_expired !== undefined) qs.set('is_expired', String(params.is_expired))
    if (params?.offset !== undefined) qs.set('offset', String(params.offset))
    if (params?.limit !== undefined) qs.set('limit', String(params.limit))
    return request<CustomerPrice[]>(`/api/v1/customer-prices?${qs}`)
  },
  get: (id: string) =>
    request<CustomerPriceDetail>(`/api/v1/customer-prices/${id}`),
  create: (data: Partial<CustomerPrice>) =>
    request<CustomerPrice>('/api/v1/customer-prices', { method: 'POST', body: JSON.stringify(data) }),
  deactivate: (id: string) =>
    requestVoid(`/api/v1/customer-prices/${id}`, { method: 'DELETE' }),
  history: (params?: { customer_id?: string; product_id?: string }) => {
    const qs = new URLSearchParams()
    if (params?.customer_id) qs.set('customer_id', params.customer_id)
    if (params?.product_id) qs.set('product_id', params.product_id)
    return request<CustomerPriceHistory[]>(`/api/v1/customer-prices/history?${qs}`)
  },
  lookup: (data: { customer_id: string; product_id: string; quantity: number; variant_id?: string }) =>
    request<PriceLookupResponse>('/api/v1/customer-prices/lookup', { method: 'POST', body: JSON.stringify(data) }),
  forCustomer: (customerId: string) =>
    request<CustomerPrice[]>(`/api/v1/customers/${customerId}/special-prices`),
  forProduct: (productId: string) =>
    request<CustomerPrice[]>(`/api/v1/products/${productId}/customer-prices`),
  metrics: () =>
    request<CustomerPriceMetrics>('/api/v1/customer-prices/metrics'),
}

// ─── Tax Rates ──────────────────────────────────────────────────────────────
export const inventoryTaxApi = {
  list: (params?: { tax_type?: string; is_active?: boolean }) => {
    const qs = new URLSearchParams()
    if (params?.tax_type) qs.set('tax_type', params.tax_type)
    if (params?.is_active !== undefined) qs.set('is_active', String(params.is_active))
    return request<TaxRate[]>(`/api/v1/tax-rates?${qs}`)
  },
  summary: () => request<TaxRateSummary>('/api/v1/tax-rates/summary'),
  create: (data: Partial<TaxRate>) =>
    request<TaxRate>('/api/v1/tax-rates', { method: 'POST', body: JSON.stringify(data) }),
  update: (id: string, data: Partial<TaxRate>) =>
    request<TaxRate>(`/api/v1/tax-rates/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
  deactivate: (id: string) =>
    request<TaxRate>(`/api/v1/tax-rates/${id}`, { method: 'DELETE' }),
  initialize: () =>
    request<TaxRate[]>('/api/v1/tax-rates/initialize', { method: 'POST' }),
}

// ── UoM API ──────────────────────────────────────────────────────────────────

export const inventoryUoMApi = {
  list: () => request<UnitOfMeasure[]>('/api/v1/uom'),
  initialize: () => request<UnitOfMeasure[]>('/api/v1/uom/initialize', { method: 'POST' }),
  create: (data: { name: string; symbol: string; category: string; is_base?: boolean }) =>
    request<UnitOfMeasure>('/api/v1/uom', { method: 'POST', body: JSON.stringify(data) }),
  listConversions: () => request<UoMConversion[]>('/api/v1/uom/conversions'),
  createConversion: (data: { from_uom_id: string; to_uom_id: string; factor: number }) =>
    request<UoMConversion>('/api/v1/uom/conversions', { method: 'POST', body: JSON.stringify(data) }),
  convert: (data: { quantity: number; from_uom: string; to_uom: string }) =>
    request<ConvertResponse>('/api/v1/uom/convert', { method: 'POST', body: JSON.stringify(data) }),
}

// ── Pricing API ──────────────────────────────────────────────────────────────

export const inventoryPricingApi = {
  getProductCostHistory: (productId: string, limit = 10, supplierId?: string) => {
    const params = new URLSearchParams({ limit: String(limit) })
    if (supplierId) params.set('supplier_id', supplierId)
    return request<ProductCostHistory[]>(`/api/v1/products/${productId}/cost-history?${params}`)
  },
  getProductPricing: (productId: string) =>
    request<ProductPricing>(`/api/v1/products/${productId}/pricing`),
  recalculatePrices: (productId: string) =>
    request<Product>(`/api/v1/products/${productId}/recalculate-prices`, { method: 'POST' }),
  updateMargins: (productId: string, data: { margin_target?: number; margin_minimum?: number; margin_cost_method?: string }) => {
    const params = new URLSearchParams()
    if (data.margin_target !== undefined) params.set('margin_target', String(data.margin_target))
    if (data.margin_minimum !== undefined) params.set('margin_minimum', String(data.margin_minimum))
    if (data.margin_cost_method) params.set('margin_cost_method', data.margin_cost_method)
    return request<Product>(`/api/v1/products/${productId}/margins?${params}`, { method: 'PATCH' })
  },
  getGlobalMargins: () => request<GlobalMarginConfig>('/api/v1/config/margins'),
  updateGlobalMargins: (data: Partial<GlobalMarginConfig>) => {
    const params = new URLSearchParams()
    if (data.margin_target_global !== undefined) params.set('margin_target_global', String(data.margin_target_global))
    if (data.margin_minimum_global !== undefined) params.set('margin_minimum_global', String(data.margin_minimum_global))
    if (data.margin_cost_method_global) params.set('margin_cost_method_global', data.margin_cost_method_global)
    if (data.below_minimum_requires_auth !== undefined) params.set('below_minimum_requires_auth', String(data.below_minimum_requires_auth))
    return request<GlobalMarginConfig>(`/api/v1/config/margins?${params}`, { method: 'PATCH' })
  },
}

// ── P&L API ──────────────────────────────────────────────────────────────────

export const inventoryPnLApi = {
  getPnL: (dateFrom?: string, dateTo?: string, productId?: string) => {
    const params = new URLSearchParams()
    if (dateFrom) params.set('date_from', dateFrom)
    if (dateTo) params.set('date_to', dateTo)
    if (productId) params.set('product_id', productId)
    return request<PnLReport>(`/api/v1/reports/pnl?${params}`)
  },
  downloadCsv: async (dateFrom?: string, dateTo?: string) => {
    const params = new URLSearchParams()
    if (dateFrom) params.set('date_from', dateFrom)
    if (dateTo) params.set('date_to', dateTo)
    const res = await fetch(`${BASE}/api/v1/reports/pnl/csv?${params}`, {
      headers: {
        'X-Tenant-Id': useAuthStore.getState().user?.tenant_id ?? 'default',
        'X-User-Id': useAuthStore.getState().user?.id ?? '1',
        ...(useAuthStore.getState().accessToken ? { Authorization: `Bearer ${useAuthStore.getState().accessToken}` } : {}),
      },
    })
    const blob = await res.blob()
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `pnl-${new Date().toISOString().slice(0, 10)}.zip`
    a.click()
    URL.revokeObjectURL(url)
  },
  downloadPdf: async (dateFrom?: string, dateTo?: string) => {
    const params = new URLSearchParams()
    if (dateFrom) params.set('date_from', dateFrom)
    if (dateTo) params.set('date_to', dateTo)
    const res = await fetch(`${BASE}/api/v1/reports/pnl/pdf?${params}`, {
      headers: {
        'X-Tenant-Id': useAuthStore.getState().user?.tenant_id ?? 'default',
        'X-User-Id': useAuthStore.getState().user?.id ?? '1',
        ...(useAuthStore.getState().accessToken ? { Authorization: `Bearer ${useAuthStore.getState().accessToken}` } : {}),
      },
    })
    const blob = await res.blob()
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `pnl-${new Date().toISOString().slice(0, 10)}.pdf`
    a.click()
    URL.revokeObjectURL(url)
  },
  getAiAnalysis: (dateFrom?: string, dateTo?: string, force?: boolean) => {
    const params = new URLSearchParams()
    if (dateFrom) params.set('date_from', dateFrom)
    if (dateTo) params.set('date_to', dateTo)
    if (force) params.set('force', 'true')
    return request<import('@/types/inventory').PnLAnalysis>(`/api/v1/reports/pnl/analysis?${params}`)
  },
}

// ── Partners API (unified suppliers + customers) ─────────────────────────────

export const inventoryPartnersApi = {
  list: (params?: { is_supplier?: boolean; is_customer?: boolean; is_active?: boolean; search?: string; offset?: number; limit?: number }) => {
    const sp = new URLSearchParams()
    if (params?.is_supplier !== undefined) sp.set('is_supplier', String(params.is_supplier))
    if (params?.is_customer !== undefined) sp.set('is_customer', String(params.is_customer))
    if (params?.is_active !== undefined) sp.set('is_active', String(params.is_active))
    if (params?.search) sp.set('search', params.search)
    if (params?.offset !== undefined) sp.set('offset', String(params.offset))
    if (params?.limit !== undefined) sp.set('limit', String(params.limit))
    return request<{ items: BusinessPartner[]; total: number; offset: number; limit: number }>(`/api/v1/partners?${sp}`)
  },
  get: (id: string) => request<BusinessPartner>(`/api/v1/partners/${id}`),
  create: (data: Partial<BusinessPartner>) =>
    request<BusinessPartner>('/api/v1/partners', { method: 'POST', body: JSON.stringify(data) }),
  update: (id: string, data: Partial<BusinessPartner>) =>
    request<BusinessPartner>(`/api/v1/partners/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
  delete: (id: string) =>
    requestVoid(`/api/v1/partners/${id}`, { method: 'DELETE' }),
}
