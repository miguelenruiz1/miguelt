// ─── Platform Admin Types ────────────────────────────────────────────────────

export interface PlanBreakdown {
  slug: string
  name: string
  count: number
  mrr: number
}

export interface ModuleAdoption {
  slug: string
  active_tenants: number
}

export interface PlatformDashboard {
  total_tenants: number
  active: number
  trialing: number
  past_due: number
  canceled: number
  expired: number
  mrr: number
  arr: number
  revenue_this_month: number
  revenue_last_month: number
  new_this_month: number
  canceled_this_month: number
  churn_rate: number
  active_licenses: number
  active_modules: number
  plan_breakdown: PlanBreakdown[]
  module_adoption: ModuleAdoption[]
}

export interface TenantListItem {
  tenant_id: string
  plan: { slug: string; name: string; price_monthly: number }
  status: string
  billing_cycle: string
  current_period_end: string | null
  trial_ends_at: string | null
  canceled_at: string | null
  created_at: string | null
  active_modules: string[]
  invoice_count: number
  total_revenue: number
}

export interface TenantListResponse {
  items: TenantListItem[]
  total: number
  offset: number
  limit: number
}

export interface TenantModule {
  slug: string
  name?: string
  description?: string | null
  is_active: boolean
  activated_at: string | null
  deactivated_at: string | null
}

export interface TenantInvoice {
  id: string
  invoice_number: string
  status: string
  amount: number
  currency: string
  period_start: string | null
  period_end: string | null
  paid_at: string | null
  created_at: string | null
}

export interface TenantLicense {
  id: string
  key: string
  status: string
  activations_count: number
  max_activations: number
  issued_at: string | null
  expires_at: string | null
}

export interface TenantEvent {
  id: string
  event_type: string
  data: Record<string, unknown> | null
  performed_by: string | null
  created_at: string | null
}

export interface TenantDetail {
  tenant_id: string
  subscription: {
    id: string
    status: string
    billing_cycle: string
    current_period_start: string | null
    current_period_end: string | null
    trial_ends_at: string | null
    canceled_at: string | null
    cancellation_reason: string | null
    created_at: string | null
    plan: {
      slug: string
      name: string
      price_monthly: number
      price_annual: number | null
      max_users: number
      max_assets: number
      max_wallets: number
      modules: string[]
    }
  }
  modules: TenantModule[]
  invoices: TenantInvoice[]
  licenses: TenantLicense[]
  events: TenantEvent[]
  active_gateway: { slug: string; display_name: string; is_test_mode: boolean } | null
}

export interface MonthPoint {
  month: string
  total_subscriptions?: number
  revenue?: number
}

export interface StatusDist {
  status: string
  count: number
}

export interface ModuleStat {
  slug: string
  active: number
  total: number
}

export interface RecentEvent {
  id: string
  tenant_id: string
  event_type: string
  data: Record<string, unknown> | null
  performed_by: string | null
  created_at: string | null
}

export interface PlatformAnalytics {
  subscription_growth: MonthPoint[]
  revenue_trend: MonthPoint[]
  status_distribution: StatusDist[]
  module_adoption: ModuleStat[]
  recent_events: RecentEvent[]
}

// ─── Sales ──────────────────────────────────────────────────────────────────

export interface SalesSubscriptionItem {
  tenant_id: string
  plan_name: string
  plan_slug: string
  price_monthly: number
  status: string
  billing_cycle: string
  current_period_end: string | null
  canceled_at: string | null
  cancellation_reason: string | null
  created_at: string | null
}

export interface SalesInvoiceItem {
  id: string
  tenant_id: string
  invoice_number: string
  amount: number
  currency: string
  period_end: string | null
  created_at: string | null
}

export interface SalesMetrics {
  upcoming_renewals: SalesSubscriptionItem[]
  overdue: SalesSubscriptionItem[]
  recently_canceled: SalesSubscriptionItem[]
  open_invoices: SalesInvoiceItem[]
  paid_this_month_count: number
  total_open_amount: number
  upcoming_renewal_count: number
  overdue_count: number
  canceled_this_month_count: number
}

// ─── Onboard ────────────────────────────────────────────────────────────────

export interface OnboardRequest {
  tenant_id: string
  company_name: string
  admin_email: string
  admin_password: string
  admin_name: string
  plan_slug: string
  billing_cycle: string
  modules: string[]
  notes?: string
}

export interface PaymentLinkResult {
  tenant_id: string
  token: string
  invoice_number: string
  amount: number
  currency: string
  plan_name: string
  link: string
}
