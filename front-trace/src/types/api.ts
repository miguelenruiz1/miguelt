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

// Asset state and event type are dynamic strings (workflow-driven)
export type AssetState = string
export type EventType = string

export interface GenericEventRequest {
  event_type: string
  to_wallet?: string
  location?: { lat?: number; lng?: number; label?: string; extra?: Record<string, unknown> }
  data?: Record<string, unknown>
  notes?: string
  result?: 'pass' | 'fail'
  reason?: string
}

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
  workflow_state_id: string | null
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
  event_type: string
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

// ─── Workflow Engine ─────────────────────────────────────────────────────────

export interface WorkflowState {
  id: string
  tenant_id: string
  slug: string
  label: string
  color: string
  icon: string | null
  is_initial: boolean
  is_terminal: boolean
  sort_order: number
  created_at: string
  updated_at: string
}

export interface WorkflowStateCreate {
  slug: string
  label: string
  color?: string
  icon?: string
  is_initial?: boolean
  is_terminal?: boolean
  sort_order?: number
}

export interface WorkflowStateUpdate {
  label?: string
  color?: string
  icon?: string
  is_initial?: boolean
  is_terminal?: boolean
  sort_order?: number
}

export interface WorkflowTransition {
  id: string
  tenant_id: string
  from_state_id: string | null
  from_state: WorkflowState | null
  to_state_id: string
  to_state: WorkflowState | null
  event_type_slug: string | null
  label: string | null
  requires_data: Record<string, unknown> | null
  created_at: string
}

export interface WorkflowTransitionCreate {
  from_state_id: string | null
  to_state_id: string
  event_type_slug?: string
  label?: string
  requires_data?: Record<string, unknown>
}

export interface WorkflowEventType {
  id: string
  tenant_id: string
  slug: string
  name: string
  description: string | null
  icon: string
  color: string
  is_informational: boolean
  requires_wallet: boolean
  requires_notes: boolean
  requires_reason: boolean
  requires_admin: boolean
  data_schema: Record<string, unknown> | null
  required_documents: DocumentRequirementsConfig | null
  compliance_required_documents: DocumentRequirementsConfig | null
  sort_order: number
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface WorkflowEventTypeCreate {
  slug: string
  name: string
  description?: string
  icon?: string
  color?: string
  is_informational?: boolean
  requires_wallet?: boolean
  requires_notes?: boolean
  requires_reason?: boolean
  requires_admin?: boolean
  data_schema?: Record<string, unknown>
  required_documents?: DocumentRequirementsConfig
  compliance_required_documents?: DocumentRequirementsConfig
  sort_order?: number
}

export interface WorkflowEventTypeUpdate {
  name?: string
  description?: string
  icon?: string
  color?: string
  is_informational?: boolean
  requires_wallet?: boolean
  requires_notes?: boolean
  requires_reason?: boolean
  requires_admin?: boolean
  data_schema?: Record<string, unknown>
  required_documents?: DocumentRequirementsConfig
  compliance_required_documents?: DocumentRequirementsConfig
  sort_order?: number
  is_active?: boolean
}

export interface IndustryPresetInfo {
  states: number
  transitions: number
  event_types: number
}

export interface ActionStateInfo {
  slug: string
  label: string
  color: string
  icon: string | null
  is_terminal: boolean
}

export interface ActionEventTypeInfo {
  slug: string
  name: string
  description: string | null
  icon: string
  color: string
  is_informational: boolean
  requires_wallet: boolean
  requires_notes: boolean
  requires_reason: boolean
  requires_admin: boolean
}

export interface AvailableAction {
  transition_id: string
  to_state: ActionStateInfo | null
  event_type_slug: string | null
  label: string | null
  event_type: ActionEventTypeInfo | null
}

export interface SeedResult {
  preset: string
  states_created: number
  transitions_created: number
  event_types_created: number
}

// ─── Media Module ────────────────────────────────────────────────────────────

export interface MediaFile {
  id: string
  tenant_id: string
  filename: string
  original_filename: string
  content_type: string
  file_size: number
  file_hash: string
  storage_backend: string
  url: string
  category: string
  document_type: string | null
  title: string | null
  description: string | null
  tags: string[]
  uploaded_by: string | null
  created_at: string
  updated_at: string
}

export interface EventDocumentLink {
  id: string
  event_id: string
  asset_id: string
  media_file_id: string
  document_type: string
  is_required: boolean
  compliance_source: string | null
  linked_by: string | null
  created_at: string
  file: {
    id: string
    filename: string
    original_filename: string
    content_type: string
    file_size: number
    file_hash: string
    url: string
    title: string | null
    category: string
    storage_backend: string
  }
}

export interface DocumentRequirement {
  type: string
  label: string
  required: boolean
  accept?: string[]
  max_size_mb?: number
  max_count?: number
}

export interface DocumentRequirementsConfig {
  documents: DocumentRequirement[]
  block_transition?: boolean
}

export interface DocumentRequirementsResponse {
  event_type_slug: string
  base_requirements: DocumentRequirement[]
  compliance_requirements: DocumentRequirement[]
  compliance_active: boolean
  merged_requirements: DocumentRequirement[]
  block_transition: boolean
}

export interface DocumentCompleteness {
  complete: boolean
  total_uploaded: number
  total_required: number
  missing: { type: string; label: string; source: string }[]
  satisfied: { type: string; label: string; count: number }[]
  block_transition: boolean
}

export interface EventDocumentsResponse {
  documents: EventDocumentLink[]
  completeness: DocumentCompleteness
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
