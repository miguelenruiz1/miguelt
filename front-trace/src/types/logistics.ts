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

// ── Transport Analytics ──────────────────────────────────────────────────────

export interface TransportAnalytics {
  on_time_delivery_pct: number | null
  avg_transit_days: number | null
  shipments_by_status: Record<string, number>
  deliveries_by_period: { period: string; count: number }[]
  avg_events_per_asset: number | null
  top_carriers: { carrier: string; shipments: number }[]
  total_logistics_cost: {
    freight: number
    insurance: number
    handling: number
    customs: number
    other: number
    total: number
  }
}

// ── Anchoring ────────────────────────────────────────────────────────────────


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
