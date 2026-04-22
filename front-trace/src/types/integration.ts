// Integration service type definitions

export interface IntegrationCatalogItem {
  slug: string
  name: string
  description: string
  country: string
  category: string
  features: string[]
  logo_url: string | null
  coming_soon?: boolean
}

export interface IntegrationConfig {
  id: string
  tenant_id: string
  provider_slug: string
  display_name: string
  is_active: boolean
  extra_config: Record<string, unknown>
  sync_products: boolean
  sync_customers: boolean
  sync_invoices: boolean
  last_sync_at: string | null
  created_at?: string
  updated_at?: string
}

export interface SyncJob {
  id: string
  tenant_id: string
  integration_id: string
  provider_slug: string
  direction: string
  entity_type: string
  status: string
  total_records: number
  synced_records: number
  failed_records: number
  error_summary: string | null
  started_at: string | null
  completed_at: string | null
  triggered_by: string | null
  created_at?: string
}

export interface SyncLog {
  id: string
  sync_job_id: string
  tenant_id: string
  entity_type: string
  local_id: string | null
  remote_id: string | null
  action: string
  status: string
  error_detail: string | null
  created_at?: string
}

export interface WebhookLog {
  id: string
  tenant_id: string | null
  provider_slug: string
  event_type: string | null
  payload: Record<string, unknown>
  status: string
  processing_result: string | null
  created_at?: string
}

export interface PaginatedSyncJobs {
  items: SyncJob[]
  total: number
  offset: number
  limit: number
}

export interface PaginatedWebhookLogs {
  items: WebhookLog[]
  total: number
  offset: number
  limit: number
}

export interface InvoiceResolution {
  id: string
  tenant_id: string
  provider: string
  is_active: boolean
  resolution_number: string
  prefix: string
  range_from: number
  range_to: number
  current_number: number
  valid_from: string
  valid_to: string
  next_invoice_number: string
  remaining: number
  is_expired: boolean
  is_exhausted: boolean
  created_at?: string
  updated_at?: string
}
