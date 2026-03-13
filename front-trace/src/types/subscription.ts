// ─── Enums ────────────────────────────────────────────────────────────────────

export type SubscriptionStatus = 'active' | 'trialing' | 'past_due' | 'canceled' | 'expired'
export type BillingCycle = 'monthly' | 'annual' | 'custom'
export type InvoiceStatus = 'draft' | 'open' | 'paid' | 'void' | 'uncollectible'
export type SubscriptionEventType =
  | 'created'
  | 'plan_changed'
  | 'canceled'
  | 'reactivated'
  | 'invoice_generated'
  | 'payment_received'
  | 'trial_started'
  | 'trial_ended'

// ─── Plan ─────────────────────────────────────────────────────────────────────

export interface PlanSlim {
  id: string
  name: string
  slug: string
  price_monthly: number
  currency: string
  max_users: number
  max_assets: number
  max_wallets: number
}

export interface Plan {
  id: string
  name: string
  slug: string
  description: string | null
  price_monthly: number
  price_annual: number | null
  currency: string
  max_users: number
  max_assets: number
  max_wallets: number
  modules: string[]
  features: Record<string, unknown>
  is_active: boolean
  is_archived: boolean
  sort_order: number
  created_at: string
  updated_at: string
}

export interface PlanCreate {
  name: string
  slug: string
  description?: string
  price_monthly?: number
  price_annual?: number
  currency?: string
  max_users?: number
  max_assets?: number
  max_wallets?: number
  modules?: string[]
  features?: Record<string, unknown>
  is_active?: boolean
  sort_order?: number
}

export interface PlanUpdate {
  name?: string
  description?: string
  price_monthly?: number
  price_annual?: number
  currency?: string
  max_users?: number
  max_assets?: number
  max_wallets?: number
  modules?: string[]
  features?: Record<string, unknown>
  is_active?: boolean
  sort_order?: number
}

// ─── Subscription ─────────────────────────────────────────────────────────────

export interface Subscription {
  id: string
  tenant_id: string
  plan: PlanSlim
  status: SubscriptionStatus
  billing_cycle: BillingCycle
  current_period_start: string
  current_period_end: string
  trial_ends_at: string | null
  canceled_at: string | null
  cancellation_reason: string | null
  notes: string | null
  created_at: string
  updated_at: string
}

export interface SubscriptionCreate {
  tenant_id: string
  plan_slug?: string
  billing_cycle?: BillingCycle
  notes?: string
}

// ─── Invoice ──────────────────────────────────────────────────────────────────

export interface LineItem {
  description: string
  quantity: number
  unit_price: number
  amount: number
}

export interface Invoice {
  id: string
  subscription_id: string
  tenant_id: string
  invoice_number: string
  status: InvoiceStatus
  amount: number
  currency: string
  period_start: string
  period_end: string
  due_date: string | null
  paid_at: string | null
  line_items: LineItem[]
  notes: string | null
  created_at: string
  updated_at: string
}

// ─── Events ───────────────────────────────────────────────────────────────────

export interface SubscriptionEvent {
  id: string
  subscription_id: string
  tenant_id: string
  event_type: SubscriptionEventType
  data: Record<string, unknown> | null
  performed_by: string | null
  created_at: string
}

// ─── Metrics ──────────────────────────────────────────────────────────────────

export interface PlanBreakdownItem {
  slug: string
  name: string
  price_monthly: number
  count: number
  mrr: number
}

export interface OverviewMetrics {
  mrr: number
  arr: number
  active: number
  trialing: number
  past_due: number
  canceled: number
  expired: number
  new_this_month: number
  canceled_this_month: number
  plan_breakdown: PlanBreakdownItem[]
}

// ─── Pagination ───────────────────────────────────────────────────────────────

export interface PaginatedResponse<T> {
  items: T[]
  total: number
  offset: number
  limit: number
}
