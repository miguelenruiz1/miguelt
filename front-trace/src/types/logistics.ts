/**
 * Types for the logistics module (trace-service).
 * Shipments, trade documents, anchor rules, blockchain, public verification.
 * Completely independent from inventory types.
 */

// ── Blockchain ────────────────────────────────────────────────────────────────

export interface BlockchainStatus {
  entity_type: string
  entity_id: string
  anchor_hash: string | null
  anchor_status: 'none' | 'pending' | 'anchored' | 'failed'
  anchor_tx_sig: string | null
  anchored_at: string | null
}

export interface BlockchainVerifyResult {
  entity_type: string
  entity_id: string
  anchor_hash: string | null
  is_anchored: boolean
  solana_tx_sig: string | null
  solana_verified: boolean
  solana_status: Record<string, unknown> | null
}

// ── Anchor Rules ──────────────────────────────────────────────────────────────

export interface AnchorRule {
  id: string
  tenant_id: string
  name: string
  entity_type: string
  trigger_event: string
  conditions: Record<string, unknown>
  actions: Record<string, unknown>
  is_active: boolean
  priority: number
  created_by?: string | null
}

export interface AnchorRuleCreate {
  name: string
  entity_type: string
  trigger_event: string
  conditions?: Record<string, unknown>
  actions?: Record<string, unknown>
  is_active?: boolean
  priority?: number
}

export interface AnchorRuleUpdate {
  name?: string
  conditions?: Record<string, unknown>
  actions?: Record<string, unknown>
  is_active?: boolean
  priority?: number
}

// ── Shipment Documents ────────────────────────────────────────────────────────

export type ShipmentDocType = 'remision' | 'bl' | 'awb' | 'carta_porte' | 'guia_terrestre'
export type ShipmentStatus = 'draft' | 'issued' | 'in_transit' | 'delivered' | 'canceled'

export interface ShipmentDocument {
  id: string
  tenant_id: string
  document_type: ShipmentDocType
  document_number: string
  carrier_name: string | null
  vehicle_plate: string | null
  driver_name: string | null
  origin_city: string | null
  destination_city: string | null
  origin_country: string | null
  destination_country: string | null
  vessel_name: string | null
  container_number: string | null
  flight_number: string | null
  total_packages: number | null
  total_weight_kg: number | null
  status: ShipmentStatus
  tracking_number: string | null
  tracking_url: string | null
  anchor_hash: string | null
  anchor_status: string
  reference_id: string | null
  reference_type: string | null
  created_at: string
}

export interface ShipmentDocCreate {
  document_type: ShipmentDocType
  document_number: string
  carrier_name?: string
  carrier_code?: string
  vehicle_plate?: string
  driver_name?: string
  driver_id_number?: string
  origin_address?: string
  destination_address?: string
  origin_city?: string
  destination_city?: string
  origin_country?: string
  destination_country?: string
  vessel_name?: string
  voyage_number?: string
  container_number?: string
  container_type?: string
  seal_number?: string
  flight_number?: string
  total_packages?: number
  total_weight_kg?: number
  total_volume_m3?: number
  cargo_description?: string
  declared_value?: number
  declared_currency?: string
  issued_date?: string
  shipped_date?: string
  estimated_arrival?: string
  tracking_number?: string
  tracking_url?: string
  notes?: string
  file_url?: string
  reference_id?: string
  reference_type?: string
  metadata?: Record<string, unknown>
}

export interface ShipmentDocUpdate {
  carrier_name?: string
  vehicle_plate?: string
  driver_name?: string
  container_number?: string
  seal_number?: string
  total_packages?: number
  total_weight_kg?: number
  shipped_date?: string
  estimated_arrival?: string
  actual_arrival?: string
  tracking_number?: string
  tracking_url?: string
  notes?: string
  file_url?: string
}

// ── Trade Documents ───────────────────────────────────────────────────────────

export type TradeDocType = 'cert_origen' | 'fitosanitario' | 'invima' | 'dex' | 'dim' | 'factura_comercial' | 'packing_list' | 'insurance_cert'
export type TradeDocStatus = 'pending' | 'approved' | 'rejected' | 'expired'

export interface TradeDocument {
  id: string
  tenant_id: string
  document_type: TradeDocType
  document_number: string | null
  shipment_document_id: string | null
  title: string
  issuing_authority: string | null
  issuing_country: string | null
  issued_date: string | null
  expiry_date: string | null
  status: TradeDocStatus
  hs_code: string | null
  fob_value: number | null
  cif_value: number | null
  currency: string | null
  file_url: string | null
  file_hash: string | null
  anchor_hash: string | null
  anchor_status: string
  reference_id: string | null
  reference_type: string | null
  created_at: string
}

export interface TradeDocCreate {
  document_type: TradeDocType
  document_number?: string
  shipment_document_id?: string | null
  title: string
  issuing_authority?: string
  issuing_country?: string
  issued_date?: string
  expiry_date?: string
  description?: string
  content_data?: Record<string, unknown>
  file_url?: string
  file_hash?: string
  hs_code?: string
  fob_value?: number
  cif_value?: number
  currency?: string
  notes?: string
  reference_id?: string
  reference_type?: string
  metadata?: Record<string, unknown>
}

export interface TradeDocUpdate {
  document_number?: string
  title?: string
  issuing_authority?: string
  issued_date?: string
  expiry_date?: string
  description?: string
  file_url?: string
  file_hash?: string
  hs_code?: string
  fob_value?: number
  cif_value?: number
  currency?: string
  notes?: string
}

// ── Public Batch Verification ─────────────────────────────────────────────────

export interface PublicProofEntry {
  event_type: string
  description: string
  timestamp: string | null
  anchor_hash: string | null
  anchor_tx_sig: string | null
  solana_explorer_url: string | null
}

export interface PublicBatchVerification {
  batch_number: string
  product_name: string
  product_sku: string
  manufacture_date: string | null
  expiration_date: string | null
  expiration_status: string
  origin_supplier: string | null
  blockchain_asset_id: string | null
  blockchain_status: string
  anchor_hash: string | null
  anchor_status: string
  proof_chain: PublicProofEntry[]
  total_events_anchored: number
  verified_at: string
}
