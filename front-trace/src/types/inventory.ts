// Inventory service type definitions

export interface Product {
  id: string
  tenant_id: string
  sku: string
  barcode: string | null
  name: string
  description: string | null
  product_type_id: string | null
  category_id: string | null
  unit_of_measure: string
  is_active: boolean
  track_batches: boolean
  min_stock_level: number
  reorder_point: number
  reorder_quantity: number
  preferred_supplier_id: string | null
  auto_reorder: boolean
  valuation_method: 'weighted_average' | 'fifo' | 'lifo'
  margin_target: number | null
  margin_minimum: number | null
  margin_cost_method: 'last_purchase' | 'weighted_avg' | 'avg_last_3'
  last_purchase_cost: number | null
  last_purchase_date: string | null
  last_purchase_supplier: string | null
  suggested_sale_price: number | null
  minimum_sale_price: number | null
  preferred_currency: string
  weight_per_unit: number | null
  volume_per_unit: number | null
  tax_rate_id: string | null
  is_tax_exempt: boolean
  retention_rate: number | null
  /** Backend stores image refs as `{media_file_id, url}` dicts.
   *  Legacy strings are kept for backwards compatibility. */
  images: Array<string | { media_file_id: string; url: string }>
  attributes: Record<string, unknown>
  created_by?: string | null
  updated_by?: string | null
  created_at?: string
  updated_at?: string
  has_movements?: boolean
}

export interface Warehouse {
  id: string
  tenant_id: string
  name: string
  code: string
  type: 'main' | 'secondary' | 'virtual' | 'transit'
  warehouse_type_id: string | null
  address: Record<string, unknown> | null
  is_active: boolean
  is_default: boolean
  cost_per_sqm?: number | null
  total_area_sqm?: number | null
  max_stock_capacity?: number | null
  created_by?: string | null
  updated_by?: string | null
}

export interface StockProductSummary {
  id: string
  sku: string
  name: string
  barcode: string | null
  product_type_id: string | null
  unit_of_measure: string
  reorder_point: number
}

export interface StockLevel {
  id: string
  tenant_id: string
  product_id: string
  warehouse_id: string
  location_id: string | null
  location_name: string | null
  batch_id: string | null
  qty_on_hand: string
  qty_reserved: string
  qty_in_transit: string
  weighted_avg_cost: number | null
  reorder_point: number
  max_stock: number
  qc_status?: 'pending_qc' | 'approved' | 'rejected'
  updated_at?: string
  product?: StockProductSummary | null
}

export type MovementType =
  | 'purchase'
  | 'sale'
  | 'transfer'
  | 'adjustment_in'
  | 'adjustment_out'
  | 'return'
  | 'waste'
  | 'production_in'
  | 'production_out'

export interface StockMovement {
  id: string
  tenant_id: string
  movement_type: MovementType
  movement_type_id: string | null
  product_id: string
  from_warehouse_id: string | null
  to_warehouse_id: string | null
  quantity: string
  unit_cost: string | null
  reference: string | null
  notes: string | null
  performed_by: string | null
  created_at: string
}

export interface Supplier {
  id: string
  tenant_id: string
  name: string
  code: string
  supplier_type_id: string | null
  contact_name: string | null
  email: string | null
  phone: string | null
  address: Record<string, unknown> | null
  payment_terms_days: number
  lead_time_days: number
  is_active: boolean
  notes: string | null
  custom_attributes: Record<string, unknown>
  created_by?: string | null
  updated_by?: string | null
  created_at?: string
  updated_at?: string
}

export interface PurchaseOrderLine {
  id: string
  product_id: string
  qty_ordered: string
  qty_received: string
  unit_cost: string
  line_total: string
  notes?: string | null
}

export type POStatus = 'draft' | 'pending_approval' | 'approved' | 'sent' | 'confirmed' | 'partial' | 'received' | 'canceled' | 'consolidated'

export interface PurchaseOrder {
  id: string
  tenant_id: string
  po_number: string
  supplier_id: string
  status: POStatus
  warehouse_id: string | null
  order_type_id: string | null
  expected_date: string | null
  received_date: string | null
  is_auto_generated: boolean
  reorder_trigger_stock: number | null
  notes: string | null
  created_by: string | null
  updated_by?: string | null
  created_at: string
  updated_at?: string
  is_consolidated: boolean
  consolidated_from_ids: string[] | null
  consolidated_at: string | null
  consolidated_by: string | null
  parent_consolidated_id: string | null
  attachments?: Array<{ url: string; name: string; type: string; classification?: string }> | null
  approval_required?: boolean
  approved_by?: string | null
  approved_at?: string | null
  rejected_reason?: string | null
  rejected_by?: string | null
  rejected_at?: string | null
  sent_at?: string | null
  sent_by?: string | null
  confirmed_at?: string | null
  confirmed_by?: string | null
  supplier_invoice_number?: string | null
  supplier_invoice_date?: string | null
  supplier_invoice_total?: number | null
  payment_terms?: string | null
  payment_due_date?: string | null
  related_sales_order_id?: string | null
  lines?: PurchaseOrderLine[]
}

export interface ConsolidationCandidate {
  supplier_id: string
  supplier_name: string
  po_count: number
  total_amount: number
  pos: PurchaseOrder[]
}

export interface ConsolidationResult {
  consolidated_po: PurchaseOrder
  original_pos: PurchaseOrder[]
  lines_merged: number
  message: string
}

export interface ConsolidationInfo {
  type: 'consolidated' | 'original' | 'none'
  consolidated_po: PurchaseOrder | null
  original_pos: PurchaseOrder[] | null
  consolidated_at: string | null
  consolidated_by: string | null
}

export interface ReorderConfig {
  product_id: string
  product_name: string
  product_sku: string
  reorder_point: number
  reorder_quantity: number
  preferred_supplier_id: string | null
  preferred_supplier_name: string | null
  current_stock: number
  below_rop: boolean
  has_open_po: boolean
}

export interface AnalyticsOverview {
  total_skus: number
  total_value: number
  low_stock_count: number
  out_of_stock_count: number
  pending_pos: number
  top_products: Array<{ product_id: string; sku: string; name: string; movement_count: number }>
  low_stock_alerts: Array<{
    product_id: string
    sku: string | null
    product_name: string | null
    warehouse_id: string
    warehouse_name: string | null
    qty_on_hand: number
    qty_reserved: number
    qty_available: number
    reorder_point: number
  }>
  movement_trend: Array<{ date: string; count: number }>
  movements_by_type: Array<{ type: string; count: number }>
  product_type_breakdown: Array<{ id: string; name: string; color: string | null; count: number }>
  supplier_type_breakdown: Array<{ id: string; name: string; color: string | null; count: number }>
  event_summary: Array<{ severity: string; count: number }>
  event_type_summary: Array<{ type_name: string; color: string | null; count: number }>
  expiring_batches_count: number
  production_runs_this_month: number
  latest_ira: number | null
  pending_cycle_counts: number
}

// ─── ABC Classification ───────────────────────────────────────────
export interface ABCItem {
  product_id: string
  sku: string | null
  name: string | null
  total_value: number
  total_qty: number
  movement_count: number
  value_pct: number
  cumulative_pct: number
  abc_class: 'A' | 'B' | 'C'
}

export interface ABCSummaryClass {
  count: number
  value: number
  value_pct: number
}

export interface ABCClassification {
  period_months: number
  total_products: number
  grand_total_value: number
  summary: { A: ABCSummaryClass; B: ABCSummaryClass; C: ABCSummaryClass }
  items: ABCItem[]
}

// ─── EOQ ──────────────────────────────────────────────────────────
export interface EOQItem {
  product_id: string
  sku: string
  name: string
  annual_demand: number
  unit_cost: number
  eoq: number
  current_reorder_qty: number | null
  orders_per_year: number
  total_annual_cost: number
}

export interface EOQResult {
  ordering_cost: number
  holding_cost_pct: number
  total_products: number
  items: EOQItem[]
}

// ─── Stock Policy ─────────────────────────────────────────────────
export interface StockPolicyItem {
  product_type_id: string
  product_type_name: string
  color: string | null
  target_months: number
  current_stock_value: number
  monthly_consumption: number
  months_on_hand: number | null
  status: 'ok' | 'excess' | 'no_data'
}

export interface StockPolicyResult {
  items: StockPolicyItem[]
}

// ─── Storage Valuation ────────────────────────────────────────────
export interface StorageValuationItem {
  warehouse_id: string
  warehouse_name: string
  cost_per_sqm: number | null
  total_area_sqm: number | null
  monthly_cost: number | null
  stock_value: number
  location_count: number
  cost_per_location: number | null
  storage_cost_pct: number | null
}

export interface StorageValuation {
  total_monthly_cost: number
  total_stock_value: number
  storage_to_value_pct: number | null
  items: StorageValuationItem[]
}

export interface ProductType {
  id: string
  tenant_id: string
  name: string
  slug: string
  description: string | null
  color: string | null
  is_active: boolean
  tracks_serials: boolean
  tracks_batches: boolean
  requires_qc?: boolean
  dispatch_rule?: 'fifo' | 'fefo' | 'lifo'
  entry_rule_location_id?: string | null
  rotation_target_months?: number | null
  default_category_id?: string | null
  sku_prefix?: string | null
}

export interface OrderType {
  id: string
  tenant_id: string
  name: string
  slug: string
  description: string | null
  color: string | null
  is_active: boolean
}

export interface SupplierType {
  id: string
  tenant_id: string
  name: string
  slug: string
  description: string | null
  color: string | null
  is_active: boolean
}

export type FieldType = 'text' | 'number' | 'select' | 'boolean' | 'date' | 'reference'

export interface CustomField {
  id: string
  tenant_id: string
  product_type_id: string | null
  label: string
  field_key: string
  field_type: FieldType
  options: string[] | null
  required: boolean
  sort_order: number
  is_active: boolean
}

export interface CustomSupplierField {
  id: string
  tenant_id: string
  supplier_type_id: string | null
  label: string
  field_key: string
  field_type: FieldType
  options: string[] | null
  required: boolean
  sort_order: number
  is_active: boolean
}

export interface CustomWarehouseField {
  id: string
  tenant_id: string
  warehouse_type_id: string | null
  label: string
  field_key: string
  field_type: FieldType
  options: string[] | null
  required: boolean
  sort_order: number
  is_active: boolean
}

export interface CustomMovementField {
  id: string
  tenant_id: string
  movement_type_id: string | null
  label: string
  field_key: string
  field_type: FieldType
  options: string[] | null
  required: boolean
  sort_order: number
  is_active: boolean
}

// ─── Categories ─────────────────────────────────────────────────────────────

export type TaxBehavior = 'addition' | 'withholding'
export type TaxBaseKind = 'subtotal' | 'subtotal_with_other_additions'

export interface TaxCategory {
  id: string
  tenant_id: string
  slug: string
  name: string
  behavior: TaxBehavior
  base_kind: TaxBaseKind
  description: string | null
  color: string | null
  sort_order: number
  is_system: boolean
  is_active: boolean
  rate_count: number
  created_at: string | null
}

export interface TaxRate {
  id: string
  tenant_id: string
  name: string
  // Legacy slug, kept for backwards compat. Prefer category info.
  tax_type: string
  category_id: string | null
  category: TaxCategory | null
  rate: string
  is_default: boolean
  is_active: boolean
  dian_code: string | null
  description: string | null
  created_at: string
}

export interface TaxRateSummary {
  default_iva: TaxRate | null
  available_iva: TaxRate[]
  available_retention: TaxRate[]
}

export interface LineTax {
  id: string
  tax_rate_id: string
  rate_pct: string
  base_amount: string
  tax_amount: string
  behavior: TaxBehavior
  rate_name?: string | null
  category_name?: string | null
  category_slug?: string | null
}

export interface Category {
  id: string
  tenant_id: string
  name: string
  slug: string
  description: string | null
  parent_id: string | null
  parent_name: string | null
  is_active: boolean
  sort_order: number
  created_at: string
  updated_at: string
}

// ─── Transfer Status ────────────────────────────────────────────────────────

export type TransferStatus = 'pending' | 'completed' | 'canceled'

// ─── SO Batch Traceability ──────────────────────────────────────────────────

export interface SOBatchEntry {
  line_id: string
  product_id: string
  product_name: string | null
  batch_id: string
  batch_number: string
  expiration_date: string | null
  qty_from_this_batch: number
}

export interface TraceBackwardOut {
  order_number: string
  customer_id: string
  customer_name: string | null
  batches_used: SOBatchEntry[]
}

export interface StockSummary {
  total_skus: number
  total_value: number
  low_stock_count: number
  out_of_stock_count: number
}

export interface PaginatedInventory<T> {
  items: T[]
  total: number
  offset: number
  limit: number
}

// ─── DynamicMovementType ───────────────────────────────────────────────

export interface DynamicMovementType {
  id: string
  tenant_id: string
  name: string
  slug: string
  description: string | null
  direction: 'in' | 'out' | 'internal' | 'neutral'
  affects_cost: boolean
  requires_reference: boolean
  color: string | null
  is_active: boolean
  is_system: boolean
  sort_order: number
}

// ─── DynamicWarehouseType ──────────────────────────────────────────────

export interface DynamicWarehouseType {
  id: string
  tenant_id: string
  name: string
  slug: string
  description: string | null
  color: string | null
  is_active: boolean
  is_system: boolean
  sort_order: number
}

// ─── WarehouseLocation ─────────────────────────────────────────────────

export interface WarehouseLocation {
  id: string
  tenant_id: string
  warehouse_id: string
  parent_location_id: string | null
  name: string
  code: string
  description: string | null
  location_type: string
  is_active: boolean
  sort_order: number
}

// ─── Event types ───────────────────────────────────────────────────────

export interface EventType {
  id: string
  tenant_id: string
  name: string
  slug: string
  description: string | null
  auto_generate_movement_type_id: string | null
  color: string | null
  icon: string | null
  is_active: boolean
}

export interface EventSeverity {
  id: string
  tenant_id: string
  name: string
  slug: string
  weight: number
  color: string | null
  is_active: boolean
}

export interface EventStatus {
  id: string
  tenant_id: string
  name: string
  slug: string
  is_final: boolean
  color: string | null
  sort_order: number
  is_active: boolean
}

export interface EventImpact {
  id: string
  event_id: string
  entity_id: string
  quantity_impact: string
  batch_id: string | null
  serial_id: string | null
  movement_id: string | null
  notes: string | null
}

export interface EventStatusLog {
  id: string
  event_id: string
  from_status_id: string | null
  to_status_id: string
  changed_by: string | null
  notes: string | null
  created_at: string
}

export interface InventoryEvent {
  id: string
  tenant_id: string
  event_type_id: string
  severity_id: string
  status_id: string
  warehouse_id: string | null
  title: string
  description: string | null
  occurred_at: string
  resolved_at: string | null
  reported_by: string | null
  updated_by?: string | null
  created_at: string
  updated_at: string
  impacts: EventImpact[]
  status_logs: EventStatusLog[]
}

// ─── Tracking ──────────────────────────────────────────────────────────

export interface SerialStatus {
  id: string
  tenant_id: string
  name: string
  slug: string
  description: string | null
  color: string | null
  is_active: boolean
}

export interface EntitySerial {
  id: string
  tenant_id: string
  entity_id: string
  serial_number: string
  status_id: string
  warehouse_id: string | null
  location_id: string | null
  batch_id: string | null
  notes: string | null
  created_by?: string | null
  updated_by?: string | null
  created_at: string
  updated_at: string
}

export interface EntityBatch {
  id: string
  tenant_id: string
  entity_id: string
  batch_number: string
  manufacture_date: string | null
  expiration_date: string | null
  cost: string | null
  quantity: string
  notes: string | null
  is_active: boolean
  created_by?: string | null
  updated_by?: string | null
  created_at: string
}

// ─── Production ────────────────────────────────────────────────────────

export interface RecipeComponent {
  id: string
  recipe_id: string
  component_entity_id: string
  quantity_required: string
  notes: string | null
  issue_method: string
  scrap_percentage: string
  lead_time_offset_days: number
}

export interface EntityRecipe {
  id: string
  tenant_id: string
  name: string
  output_entity_id: string
  output_quantity: string
  description: string | null
  is_active: boolean
  bom_type: string
  standard_cost: string
  planned_production_size: number
  version: string
  is_default: boolean
  created_by?: string | null
  updated_by?: string | null
  created_at: string
  components: RecipeComponent[]
}

export type ProductionRunStatus = 'planned' | 'released' | 'in_progress' | 'completed' | 'closed' | 'canceled' | 'rejected'
export type ProductionOrderType = 'standard' | 'special' | 'disassembly'

export interface ProductionRun {
  id: string
  tenant_id: string
  recipe_id: string
  run_number: string
  warehouse_id: string
  output_warehouse_id: string | null
  multiplier: string
  status: ProductionRunStatus
  order_type: ProductionOrderType
  priority: number
  planned_start_date: string | null
  planned_end_date: string | null
  actual_start_date: string | null
  actual_end_date: string | null
  actual_output_quantity: string | null
  total_component_cost: string | null
  total_production_cost: string | null
  unit_production_cost: string | null
  variance_amount: string | null
  linked_sales_order_id: string | null
  linked_customer_id: string | null
  started_at: string | null
  completed_at: string | null
  performed_by: string | null
  updated_by?: string | null
  notes: string | null
  approved_by: string | null
  approved_at: string | null
  rejection_notes: string | null
  created_at: string
}

export interface ProductionEmissionLine {
  id: string
  emission_id: string
  component_entity_id: string
  planned_quantity: string
  actual_quantity: string
  unit_cost: string
  total_cost: string
  batch_id: string | null
  warehouse_id: string | null
  variance_quantity: string
}

export interface ProductionEmission {
  id: string
  tenant_id: string
  production_run_id: string
  emission_number: string
  status: string
  emission_date: string
  warehouse_id: string | null
  notes: string | null
  performed_by: string | null
  created_at: string
  lines: ProductionEmissionLine[]
}

export interface ProductionResource {
  id: string
  tenant_id: string
  name: string
  resource_type: 'labor' | 'machine' | 'overhead'
  cost_per_hour: string
  cost_per_unit: string
  capacity_hours_per_day: string
  efficiency_pct: string
  shifts_per_day: number
  available_hours_override: string | null
  is_active: boolean
  notes: string | null
  created_at: string
}

export interface RecipeResource {
  id: string
  recipe_id: string
  resource_id: string
  hours_per_unit: string
  setup_time_hours: string
  notes: string | null
}

export interface MRPLine {
  component_entity_id: string
  component_name: string | null
  required_qty: string
  available_qty: string
  shortage: string
  suggested_order_qty: string
  preferred_supplier_id: string | null
  lead_time_offset_days: number
  estimated_unit_cost: string
  action: 'buy' | 'make'
  sub_recipe_id: string | null
  sub_recipe_name: string | null
}

export interface MRPResult {
  recipe_id: string
  recipe_name: string
  output_quantity: string
  lines: MRPLine[]
  make_suggestions: MRPLine[]
  total_estimated_cost: string
  purchase_orders_created: string[]
}

export interface CapacityLine {
  resource_id: string
  resource_name: string
  required_hours: string
  available_hours: string
  committed_hours: string
  utilization_pct: string
  has_capacity: boolean
}

export interface CapacityResult {
  lines: CapacityLine[]
  all_have_capacity: boolean
}

export interface ProductionReceiptLine {
  id: string
  receipt_id: string
  entity_id: string
  planned_quantity: string
  received_quantity: string
  unit_cost: string
  total_cost: string
  batch_id: string | null
  is_complete: boolean
}

export interface ProductionReceipt {
  id: string
  tenant_id: string
  production_run_id: string
  receipt_number: string
  status: string
  receipt_date: string
  output_warehouse_id: string | null
  notes: string | null
  performed_by: string | null
  created_at: string
  lines: ProductionReceiptLine[]
}

export interface StockLayer {
  id: string
  tenant_id: string
  entity_id: string
  warehouse_id: string
  movement_id: string | null
  quantity_initial: string
  quantity_remaining: string
  unit_cost: string
  batch_id: string | null
  created_at: string
}

// ─── Cycle Count ──────────────────────────────────────────────────────────

export type CycleCountStatus = 'draft' | 'in_progress' | 'completed' | 'approved' | 'canceled'

export type CycleCountMethodology =
  | 'control_group'
  | 'location_audit'
  | 'random_selection'
  | 'diminishing_population'
  | 'product_category'
  | 'abc'

export interface CycleCountItem {
  id: string
  tenant_id: string
  cycle_count_id: string
  product_id: string
  product_name: string | null
  product_sku: string | null
  location_id: string | null
  batch_id: string | null
  system_qty: string
  counted_qty: string | null
  discrepancy: string | null
  recount_qty: string | null
  recount_discrepancy: string | null
  root_cause: string | null
  counted_by: string | null
  counted_at: string | null
  notes: string | null
  movement_id: string | null
  created_at: string
}

export interface IRACompute {
  total_items: number
  accurate_items: number
  ira_percentage: number
  total_system_value: number
  total_counted_value: number
  value_accuracy: number
  counted_items: number
}

export interface Feasibility {
  total_items: number
  minutes_per_count: number
  assigned_counters: number
  total_minutes: number
  total_hours: number
  hours_per_counter: number
  available_hours: number
  is_feasible: boolean
}

export interface CycleCount {
  id: string
  tenant_id: string
  count_number: string
  warehouse_id: string
  warehouse_name: string | null
  status: CycleCountStatus
  methodology: CycleCountMethodology | null
  assigned_counters: number
  minutes_per_count: number
  scheduled_date: string | null
  started_at: string | null
  completed_at: string | null
  approved_at: string | null
  approved_by: string | null
  created_by: string | null
  updated_by?: string | null
  notes: string | null
  created_at: string
  items: CycleCountItem[]
  ira: IRACompute | null
  feasibility: Feasibility | null
}

export interface IRASnapshot {
  id: string
  tenant_id: string
  cycle_count_id: string
  warehouse_id: string | null
  total_items: number
  accurate_items: number
  ira_percentage: number
  total_system_value: number
  total_counted_value: number
  value_accuracy: number
  snapshot_date: string
  created_at: string
}

export interface ProductDiscrepancy {
  cycle_count_id: string
  count_number: string
  warehouse_id: string
  warehouse_name: string | null
  counted_at: string | null
  system_qty: number
  counted_qty: number | null
  discrepancy: number | null
  root_cause: string | null
}

export interface IRATrendPoint {
  date: string
  ira_percentage: number
  value_accuracy: number
  total_items: number
  accurate_items: number
}

// ─── Import ──────────────────────────────────────────────────────────────────

export interface ImportRowError {
  row: number
  field: string
  message: string
}

export interface ImportResult {
  created: number
  skipped: number
  errors: ImportRowError[]
}

export interface DemoImportResult {
  industry: string
  label?: string
  products_created: number
  products_restored: number
  warehouses_created: number
  warehouses_restored: number
  suppliers_created: number
  suppliers_restored: number
  types_created: number
  types_restored: number
  supplier_types_created: number
  supplier_types_restored: number
  order_types_created: number
  order_types_restored: number
  batches_created: number
  serials_created: number
  recipes_created: number
  recipes_restored: number
  pos_created: number
  production_runs_created: number
  event_config_created: number
  events_created: number
  taxonomies_created: number
  error?: string
}

export interface DemoDeleteResult {
  industry: string
  label?: string
  products_deleted: number
  warehouses_deleted: number
  suppliers_deleted: number
  types_deleted: number
  supplier_types_deleted: number
  order_types_deleted: number
  recipes_deleted: number
  pos_deleted: number
  production_runs_deleted: number
  events_deleted: number
  taxonomies_deleted: number
  batches_deleted: number
  serials_deleted: number
  error?: string
}

// ─── Customer Types ──────────────────────────────────────────────────────
export interface CustomerType {
  id: string
  tenant_id: string
  name: string
  slug: string
  description: string | null
  color: string
  is_active: boolean
  created_at?: string
}

// ─── Customers ──────────────────────────────────────────────────────────
export interface Customer {
  id: string
  tenant_id: string
  name: string
  code: string
  customer_type_id: string | null
  tax_id: string | null
  tax_id_type: string | null
  contact_name: string | null
  email: string | null
  phone: string | null
  address: Record<string, unknown> | null
  shipping_address: Record<string, unknown> | null
  payment_terms_days: number
  credit_limit: number
  discount_percent: number
  is_active: boolean
  notes: string | null
  custom_attributes: Record<string, unknown>
  created_by?: string | null
  updated_by?: string | null
  created_at?: string
  updated_at?: string
}

// ─── Sales Orders ───────────────────────────────────────────────────────
export type SalesOrderStatus = 'draft' | 'pending_approval' | 'confirmed' | 'picking' | 'shipped' | 'delivered' | 'returned' | 'canceled' | 'rejected'

export interface SalesOrderLine {
  id: string
  order_id: string
  product_id: string
  product_name: string | null
  product_sku: string | null
  variant_id: string | null
  variant_name: string | null
  warehouse_id: string | null
  warehouse_name: string | null
  qty_ordered: number
  qty_shipped: number
  original_quantity: number | null
  unit_price: number
  original_unit_price?: number | null
  discount_pct: number
  discount_amount: number
  line_subtotal: number
  tax_rate: number
  tax_rate_id?: string | null
  tax_rate_pct?: number | null
  tax_amount?: number
  retention_pct?: number | null
  retention_amount?: number
  line_total_with_tax?: number
  line_total: number
  notes: string | null
  backorder_line_id: string | null
  price_source?: string | null
  customer_price_id?: string | null
}

export interface StockCheckLine {
  line_id: string
  product_name: string
  warehouse_name: string
  required: number
  available: number
  sufficient: boolean
}

export interface StockCheckResult {
  ready_to_ship: boolean
  lines: StockCheckLine[]
}

export interface ShippingInfo {
  recipient_name?: string | null
  recipient_phone?: string | null
  recipient_email?: string | null
  recipient_document?: string | null
  address_line?: string | null
  city?: string | null
  state?: string | null
  zip_code?: string | null
  country?: string | null
  shipping_method?: string | null
  carrier?: string | null
  tracking_number?: string | null
  photo_url?: string | null
  shipping_notes?: string | null
}

export interface SalesOrder {
  id: string
  tenant_id: string
  order_number: string
  customer_id: string
  customer_name: string | null
  status: SalesOrderStatus
  warehouse_id: string | null
  warehouse_name: string | null
  shipping_address: Record<string, unknown> | null
  expected_date: string | null
  confirmed_at: string | null
  shipped_date: string | null
  delivered_date: string | null
  subtotal: number
  tax_amount: number
  discount_pct: number
  discount_amount: number
  discount_reason: string | null
  total: number
  total_retention: number
  total_with_tax: number
  total_payable: number
  currency: string
  incoterm: string | null
  origin_country: string | null
  destination_country: string | null
  notes: string | null
  shipping_info: ShippingInfo | null
  cufe: string | null
  invoice_number: string | null
  invoice_pdf_url: string | null
  invoice_status: string | null
  invoice_remote_id: string | null
  invoice_provider: string | null
  credit_note_cufe: string | null
  credit_note_number: string | null
  credit_note_remote_id: string | null
  credit_note_status: string | null
  returned_at: string | null
  is_backorder: boolean
  parent_so_id: string | null
  backorder_number: number
  backorder_ids: string[]
  remission_number: string | null
  remission_generated_at: string | null
  approval_required: boolean
  approved_by: string | null
  approved_at: string | null
  rejected_by: string | null
  rejected_at: string | null
  rejection_reason: string | null
  approval_requested_at: string | null
  lines: SalesOrderLine[]
  created_at?: string
  created_by?: string | null
  updated_at?: string
  updated_by?: string | null
}

export interface RemissionData {
  remission_number: string
  remission_date: string | null
  shipped_at: string | null
  company: {
    name: string
    nit: string
    address: string
    phone: string
    email: string
  }
  customer: {
    name: string
    nit: string
    address: string
    phone: string
    email: string
    contact_name: string
  }
  warehouse: {
    name: string
    address: string
    city: string
  }
  so_number: string
  invoice_number: string | null
  notes: string | null
  lines: {
    product_name: string
    product_code: string
    quantity: number
    unit: string
    warehouse_name: string
    lot_number: string | null
    serial_number: string | null
  }[]
  total_items: number
  total_quantity: number
}

export interface StockReservation {
  id: string
  sales_order_id: string
  sales_order_line_id: string
  product_id: string
  product_name: string | null
  product_sku: string | null
  variant_id: string | null
  warehouse_id: string
  warehouse_name: string | null
  quantity: number
  status: 'active' | 'released' | 'consumed'
  reserved_at: string | null
  released_at: string | null
  released_reason: string | null
}

export interface BackorderLinePreview {
  product_name: string
  product_sku: string | null
  warehouse_name: string | null
  qty_ordered: number
  qty_confirmable: number
  qty_backordered: number
}

export interface BackorderPreview {
  has_backorder: boolean
  lines: BackorderLinePreview[]
}

export interface ConfirmWithBackorderOut {
  order: SalesOrder
  backorder: SalesOrder | null
  split_preview: BackorderPreview
}

// ─── SO Approval ────────────────────────────────────────────────────────
export interface SOApprovalLog {
  id: string
  tenant_id: string
  sales_order_id: string
  action: string
  performed_by: string
  performed_by_name: string | null
  reason: string | null
  so_total_at_action: number
  created_at: string | null
}

export interface ApprovalThreshold {
  tenant_id: string
  so_approval_threshold: number | null
}

// ─── Variant Attributes ─────────────────────────────────────────────────
export interface VariantOption {
  id: string
  attribute_id: string
  value: string
  color_hex: string | null
  sort_order: number
  is_active: boolean
}

export interface VariantAttribute {
  id: string
  tenant_id: string
  name: string
  slug: string
  sort_order: number
  is_active: boolean
  options: VariantOption[]
  created_at?: string
}

// ─── Product Variants ───────────────────────────────────────────────────
export interface ProductVariant {
  id: string
  tenant_id: string
  parent_id: string
  sku: string
  barcode: string | null
  name: string
  cost_price: number
  sale_price: number
  weight: number | null
  is_active: boolean
  option_values: Record<string, string>
  images: string[]
  created_at?: string
  updated_at?: string
}

// ─── Stock Alerts ───────────────────────────────────────────────────────
export type AlertType = 'low_stock' | 'out_of_stock' | 'reorder_point'

export interface StockAlert {
  id: string
  tenant_id: string
  product_id: string
  warehouse_id: string | null
  alert_type: AlertType
  message: string
  current_qty: number
  threshold_qty: number
  is_read: boolean
  is_resolved: boolean
  created_at?: string
  resolved_at?: string | null
  product_name?: string | null
  product_sku?: string | null
  warehouse_name?: string | null
  uom?: string | null
}

// ─── Kardex ─────────────────────────────────────────────────────────────
export interface KardexEntry {
  movement_id: string
  date: string | null
  type: string
  reference: string | null
  quantity: number
  unit_cost: number
  avg_cost: number
  balance: number
  value: number | null
}

// ─── Audit Log ────────────────────────────────────────────────────────────
export interface InventoryAuditLog {
  id: string
  tenant_id: string
  user_id: string | null
  user_email: string | null
  user_name: string | null
  action: string
  description: string | null
  resource_type: string
  resource_id: string | null
  old_data: Record<string, unknown> | null
  new_data: Record<string, unknown> | null
  ip_address: string | null
  user_agent: string | null
  created_at: string
}

// ─── Occupation ────────────────────────────────────────────────────────────
export interface WarehouseOccupation {
  warehouse_id: string
  warehouse_name: string
  total_locations: number
  occupied_locations: number
  free_locations: number
  occupation_pct: number
  has_capacity?: boolean
}

export interface OccupationData {
  total_locations: number
  occupied_locations: number
  free_locations: number
  occupation_pct: number
  by_warehouse: WarehouseOccupation[]
}

// ─── Portal (customer self-service) ──────────────────────────────────────
export interface PortalStockItem {
  product_id: string
  sku: string | null
  product_name: string | null
  warehouse_id: string
  warehouse_name: string | null
  qty_on_hand: number
  qty_reserved: number
  qc_status: string | null
}

export interface PortalOrder {
  id: string
  order_number: string
  status: SalesOrderStatus
  subtotal: number
  tax_amount: number
  discount_amount: number
  total: number
  currency: string
  expected_date: string | null
  shipped_date: string | null
  delivered_date: string | null
  notes: string | null
  line_count: number
  created_at: string | null
}

export interface PortalOrderLine {
  id: string
  product_id: string
  sku: string | null
  product_name: string | null
  variant_id: string | null
  variant_name: string | null
  qty_ordered: number
  qty_shipped: number
  unit_price: number
  discount_pct: number
  tax_rate: number
  line_total: number
  notes: string | null
}

export interface PortalOrderDetail {
  id: string
  order_number: string
  status: SalesOrderStatus
  subtotal: number
  tax_amount: number
  discount_amount: number
  total: number
  currency: string
  expected_date: string | null
  shipped_date: string | null
  delivered_date: string | null
  notes: string | null
  lines: PortalOrderLine[]
  created_at: string | null
  updated_at: string | null
}

// ─── Customer Special Prices ──────────────────────────────────────────────────

export interface CustomerPrice {
  id: string
  tenant_id: string
  customer_id: string
  customer_name?: string
  product_id: string
  product_name?: string
  product_sku?: string
  variant_id: string | null
  variant_name?: string | null
  variant_sku?: string | null
  base_price?: number | null
  price: number
  min_quantity: number
  currency: string
  valid_from: string
  valid_to: string | null
  reason: string | null
  is_active: boolean
  created_by: string
  created_at: string
  updated_at: string
}

export interface CustomerPriceHistory {
  id: string
  customer_price_id: string
  customer_id: string
  product_id: string
  old_price: number | null
  new_price: number
  changed_by: string
  changed_by_name: string | null
  reason: string | null
  changed_at: string
}

export interface CustomerPriceDetail extends CustomerPrice {
  history: CustomerPriceHistory[]
}

export interface PriceLookupResponse {
  price: number
  original_price: number | null
  source: 'customer_special' | 'product_base'
  customer_price_id: string | null
  valid_to: string | null
  reason: string | null
}

export interface CustomerPriceMetrics {
  active_count: number
  expiring_soon: number
  customers_with_prices: number
}

// ── Dynamic Pricing & UoM Types ──────────────────────────────────────

export interface ProductCostHistory {
  id: string
  tenant_id: string
  product_id: string
  variant_id: string | null
  purchase_order_id: string
  purchase_order_line_id: string
  supplier_id: string
  supplier_name: string
  uom_purchased: string
  qty_purchased: number
  qty_in_base_uom: number
  unit_cost_purchased: number
  unit_cost_base_uom: number
  total_cost: number
  market_note: string | null
  received_at: string
}

export interface UnitOfMeasure {
  id: string
  tenant_id: string
  name: string
  symbol: string
  // Open string so any system or custom category is valid.
  // Common slugs: weight, volume, length, area, unit, time, energy, custom.
  category: string
  is_base: boolean
  is_active: boolean
  created_at: string
}

export interface UoMConversion {
  id: string
  tenant_id: string
  from_uom_id: string
  to_uom_id: string
  factor: number
  is_active: boolean
}

export interface UoMCatalogOption {
  symbol: string
  name: string
  suggested_default: boolean
}

export interface UoMCatalogCategory {
  category: string
  label: string
  options: UoMCatalogOption[]
}

export interface UoMSetupRequest {
  bases: { category: string; base_symbol: string }[]
}

export interface UoMSetupResponse {
  created: number
  categories_set_up: string[]
  skipped?: string[]
}

export interface UoMChangeBaseRequest {
  new_base_id: string
}

export interface UoMChangeBaseResponse {
  old_base: string
  new_base: string
  pivot: string
  affected: Record<string, number>
}

export interface ProductPricing {
  last_purchase_cost: number | null
  last_purchase_date: string | null
  last_purchase_supplier: string | null
  suggested_sale_price: number | null
  minimum_sale_price: number | null
  margin_target: number | null
  margin_minimum: number | null
  margin_cost_method: string | null
  current_avg_cost: number | null
  cost_history: ProductCostHistory[]
}

export interface PnLProduct {
  product_id: string
  product_name: string
  product_sku: string
  unit_of_measure: string
  purchases: PurchaseRecord[]
  sales: SaleRecord[]
  stock_by_warehouse: StockByWarehouse[]
  summary: PnLSummary
  market_analysis: MarketAnalysis
}

export interface PurchaseRecord {
  received_at: string
  supplier_name: string
  uom_purchased: string
  qty_purchased: number
  qty_in_base_uom: number
  unit_cost_purchased: number
  unit_cost_base_uom: number
  total_cost: number
  purchase_order_id: string
  market_note: string | null
}

export interface SaleRecord {
  order_number: string
  sale_date: string
  qty_ordered: number
  qty_shipped: number
  unit_price: number
  line_total: number
  margin_pct: number | null
}

export interface StockByWarehouse {
  warehouse_name: string
  qty_on_hand: number
  qty_reserved: number
  qty_available: number
  avg_cost: number
  total_value: number
}

export interface PnLSummary {
  total_purchased_qty: number
  total_purchased_cost: number
  total_sold_qty: number
  total_revenue: number
  total_cogs: number
  gross_profit: number
  gross_margin_pct: number
  margin_target: number
  margin_vs_target: number
  stock_current_qty: number
  stock_current_value: number
  potential_revenue: number
  potential_profit: number
}

export interface MarketAnalysis {
  lowest_purchase_cost: number
  highest_purchase_cost: number
  price_variation_pct: number
  best_supplier: string
  suggested_price_today: number
  minimum_price_today: number
}

export interface PnLReport {
  products: PnLProduct[]
  totals: {
    total_purchased_cost: number
    total_revenue: number
    total_cogs: number
    gross_profit: number
    gross_margin_pct: number
    stock_current_value: number
    product_count: number
  }
}

// ─── AI P&L Analysis ─────────────────────────────────────────────────────────

export interface PnLAlert {
  titulo: string
  detalle: string
  severidad: 'alta' | 'media' | 'baja'
  producto_sku: string | null
}

export interface PnLOportunidad {
  titulo: string
  detalle: string
  impacto_estimado: string
  producto_sku: string | null
}

export interface PnLProductoEstrella {
  sku: string
  nombre: string
  razon: string
}

export interface PnLRecomendacion {
  accion: string
  prioridad: 'alta' | 'media' | 'baja'
  producto_sku: string | null
  plazo?: 'inmediato' | 'esta_semana' | 'este_mes' | null
}

export interface PnLAnalysis {
  resumen: string
  alertas: PnLAlert[]
  oportunidades: PnLOportunidad[]
  productos_estrella: PnLProductoEstrella[]
  recomendaciones: PnLRecomendacion[]
  is_cached?: boolean
  cached_at?: string
  cache_source?: 'fresh' | 'session_cache' | 'last_saved'
}

export interface GlobalMarginConfig {
  margin_target_global: number
  margin_minimum_global: number
  margin_cost_method_global: string
  below_minimum_requires_auth: boolean
}

export interface ConvertResponse {
  quantity: number
  from_uom: string
  to_uom: string
  result: number
  factor: number
}

export interface BusinessPartner {
  id: string
  tenant_id: string
  name: string
  code: string
  is_supplier: boolean
  is_customer: boolean
  supplier_type_id: string | null
  customer_type_id: string | null
  tax_id: string | null
  dv: string | null
  document_type: string
  organization_type: number
  tax_regime: number
  tax_liability: number
  municipality_id: number
  company_name: string | null
  contact_name: string | null
  email: string | null
  phone: string | null
  address: Record<string, unknown> | null
  shipping_address: Record<string, unknown> | null
  credit_limit: number
  discount_percent: number
  lead_time_days: number
  payment_terms_days: number
  is_active: boolean
  notes: string | null
  custom_attributes: Record<string, unknown>
  created_by?: string | null
  updated_by?: string | null
  created_at?: string
  updated_at?: string
}

