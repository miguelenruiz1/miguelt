// ─── Tenant ───────────────────────────────────────────────────────────────────

export interface Tenant {
  id: string
  name: string
  slug: string
  status: string
  created_at: string
  updated_at: string
}

export interface TenantCreate {
  name: string
  slug: string
}

export interface MerkleTree {
  id: string
  tenant_id: string
  tree_address: string
  tree_authority: string
  max_depth: number
  max_buffer_size: number
  canopy_depth: number
  leaf_count: number
  helius_tree_id: string | null
  create_tx_sig: string | null
  is_simulated: boolean
  created_at: string
  updated_at: string
}

// ─── Enums ────────────────────────────────────────────────────────────────────

export type WalletStatus = 'active' | 'suspended' | 'revoked'

export type AssetState =
  | 'in_transit'
  | 'in_custody'
  | 'loaded'
  | 'qc_passed'
  | 'qc_failed'
  | 'released'
  | 'burned'

export type EventType = 'CREATED' | 'HANDOFF' | 'ARRIVED' | 'LOADED' | 'QC' | 'RELEASED' | 'BURN'

// ─── Taxonomy ─────────────────────────────────────────────────────────────────

export interface CustodianType {
  id: string
  name: string
  slug: string
  color: string
  icon: string
  description: string | null
  sort_order: number
  created_at: string
  updated_at: string
}

export interface Organization {
  id: string
  name: string
  custodian_type_id: string
  custodian_type?: CustodianType
  description: string | null
  tags: string[]
  status: string
  wallet_count: number
  created_at: string
  updated_at: string
}

export interface CustodianTypeCreate {
  name: string
  slug: string
  color?: string
  icon?: string
  description?: string
  sort_order?: number
}

export interface CustodianTypeUpdate {
  name?: string
  color?: string
  icon?: string
  description?: string
  sort_order?: number
}

export interface OrganizationCreate {
  name: string
  custodian_type_id: string
  description?: string
  tags?: string[]
}

export interface OrganizationUpdate {
  name?: string
  description?: string
  tags?: string[]
  status?: string
}

// ─── Domain models ────────────────────────────────────────────────────────────

export interface Wallet {
  id: string
  wallet_pubkey: string
  tags: string[]
  status: WalletStatus
  name: string | null
  organization_id: string | null
  created_at: string
  updated_at: string
}

export type BlockchainStatus = 'PENDING' | 'CONFIRMED' | 'FAILED' | 'SIMULATED' | 'SKIPPED'

export interface Asset {
  id: string
  asset_mint: string
  product_type: string
  metadata: Record<string, unknown>
  current_custodian_wallet: string
  state: AssetState
  last_event_hash: string | null
  blockchain_asset_id: string | null
  blockchain_tree_address: string | null
  blockchain_tx_signature: string | null
  blockchain_status: BlockchainStatus
  is_compressed: boolean
  created_at: string
  updated_at: string
}

export interface LocationData {
  lat?: number
  lng?: number
  label?: string
  extra?: Record<string, unknown>
}

export interface CustodyEvent {
  id: string
  asset_id: string
  event_type: EventType
  from_wallet: string | null
  to_wallet: string | null
  timestamp: string
  location: LocationData | null
  data: Record<string, unknown>
  prev_event_hash: string | null
  event_hash: string
  solana_tx_sig: string | null
  anchored: boolean
  anchor_attempts: number
  anchor_last_error: string | null
  created_at: string
}

// ─── Request payloads ─────────────────────────────────────────────────────────

export interface WalletCreate {
  wallet_pubkey: string
  tags: string[]
  status: WalletStatus
  name?: string
  organization_id?: string
}

export interface WalletGenerateRequest {
  tags: string[]
  status: WalletStatus
  name?: string
  organization_id?: string
}

export interface WalletUpdate {
  tags?: string[]
  status?: WalletStatus
  name?: string
  organization_id?: string
}

export interface AssetCreate {
  asset_mint: string
  product_type: string
  metadata: Record<string, unknown>
  initial_custodian_wallet: string
}

export interface AssetMintRequest {
  product_type: string
  metadata: Record<string, unknown>
  initial_custodian_wallet: string
}

export interface HandoffRequest {
  to_wallet: string
  location?: LocationData
  data?: Record<string, unknown>
}

export interface ArrivedRequest {
  location?: LocationData
  data?: Record<string, unknown>
}

export interface LoadedRequest {
  location?: LocationData
  data?: Record<string, unknown>
}

export interface QCRequest {
  result: 'pass' | 'fail'
  notes?: string
  data?: Record<string, unknown>
}

export interface ReleaseRequest {
  external_wallet: string
  reason: string
  data?: Record<string, unknown>
}

export interface BurnRequest {
  reason: string
  data?: Record<string, unknown>
}

// ─── Response wrappers ────────────────────────────────────────────────────────

export interface PaginatedResponse<T> {
  items: T[]
  total: number
}

export interface EventActionResponse {
  asset: Asset
  event: CustodyEvent
}

export interface HealthResponse {
  status: string
  version: string
}

export interface ReadyResponse {
  status: string
  checks: Record<string, string>
}

export interface SolanaAccountResponse {
  pubkey: string
  lamports: number | null
  owner: string | null
  executable: boolean | null
  data: unknown
  simulated: boolean
}

export interface SolanaTxResponse {
  signature: string
  slot: number | null
  confirmations: number | null
  err: unknown
  simulated: boolean
}

// ─── API error ────────────────────────────────────────────────────────────────

export interface ApiErrorBody {
  error: {
    code: string
    message: string
    detail?: unknown
    correlation_id?: string
  }
}
