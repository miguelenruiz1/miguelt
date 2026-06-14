// Warehouse-Management (WM) types — mirror inventory-service WM schemas.

export interface StorageType {
  id: string
  tenant_id: string
  warehouse_id: string
  code: string
  name: string
  kind: 'physical' | 'logical' | 'interim'
  putaway_strategy: 'manual' | 'fixed_bin' | 'next_empty' | 'by_section'
  removal_strategy: 'fifo' | 'fefo' | 'lifo' | 'fixed_bin'
  capacity_check: boolean
  handles_hu: boolean
  is_active: boolean
}

export interface StorageSection {
  id: string
  tenant_id: string
  storage_type_id: string
  code: string
  name: string
  rotation_class: string | null
  is_active: boolean
  sort_order: number
}

export interface BinSegment {
  start: number
  end: number
  step?: number
  pad: number
}

export interface BinBulkResult {
  created: number
  skipped: number
  sample_codes: string[]
}

export interface EmptyBinReport {
  warehouse_id: string
  total_bins: number
  empty_bins: number
  occupancy_pct: number
  items: { location_id: string; code: string; name: string }[]
}

export interface OperationType {
  id: string
  code: string
  name: string
  direction: 'inbound' | 'outbound' | 'internal'
  movement_type: string | null
  source_zone: string | null
  dest_zone: string | null
  requires_qa: boolean
  is_active: boolean
}

export interface MovementOrderLine {
  id: string
  line_no: number
  product_id: string
  batch_id: string | null
  quantity: string
  uom: string
  source_location_id: string | null
  dest_location_id: string | null
  source_confirmed: boolean
  dest_confirmed: boolean
  status: string
}

export interface MovementOrder {
  id: string
  to_number: string
  warehouse_id: string
  status: string
  notes: string | null
  lines: MovementOrderLine[]
}

export interface WMConfig {
  id: string
  warehouse_id: string
  receive_steps: number
  deliver_steps: number
  manufacture_steps: number
}

export interface RouteRule {
  id: string
  sequence: number
  name: string
  source_zone: string
  dest_zone: string
  operation_code: string | null
}

export interface WMRoute {
  id: string
  warehouse_id: string
  code: string
  name: string
  flow: 'inbound' | 'outbound' | 'manufacture'
  steps: number
  is_active: boolean
  rules: RouteRule[]
}

export interface PutawayProposal {
  location_id: string | null
  code: string | null
  storage_type_id: string | null
  reason: string
}

export interface RemovalPlan {
  strategy: string
  requested_qty: string
  allocated_qty: string
  shortfall: string
  allocations: { batch_id: string | null; batch_number: string | null; expiration_date: string | null; qty: string }[]
}

export interface StockStatus {
  warehouse_id: string
  buckets: { stock_type: string; quants: number; total_qty: string }[]
}

export interface ERI {
  warehouse_id: string
  items_counted: number
  items_accurate: number
  eri_pct: number
  value_accuracy_pct: number | null
  target_pct: number
}
