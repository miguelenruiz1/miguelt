import { useState } from 'react'
import {
  CreditCard, ChevronRight, Check, Crown, Users, Box, Wallet,
  Receipt, ArrowRight, Zap, Star, Building2,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Topbar } from '@/components/layout/Topbar'
import { useAuthStore } from '@/store/auth'
import { useUsageSummary, useCheckout, useTenantInvoices } from '@/hooks/useBilling'
import { usePlans } from '@/hooks/usePlans'
import { useSubscription } from '@/hooks/useSubscriptions'
import { fmtDate } from '@/lib/utils'
import type { Plan, Invoice, InvoiceStatus, UsageCounter } from '@/types/subscription'

/* ─── Helpers ──────────────────────────────────────────────────────── */

const fmtCurrency = (n: number, currency = 'USD') =>
  n < 0
    ? 'Custom'
    : new Intl.NumberFormat('es', { style: 'currency', currency, minimumFractionDigits: 0 }).format(n)

function usagePercent(counter: UsageCounter) {
  if (counter.limit <= 0) return 0
  return Math.min(100, (counter.current / counter.limit) * 100)
}

function usageColor(pct: number) {
  if (pct >= 90) return 'bg-red-500'
  if (pct >= 70) return 'bg-amber-500'
  return 'bg-emerald-500'
}

function usageTextColor(pct: number) {
  if (pct >= 90) return 'text-red-600'
  if (pct >= 70) return 'text-amber-600'
  return 'text-emerald-600'
}

const invoiceStatusVariant: Record<InvoiceStatus, 'warning' | 'success' | 'muted' | 'default'> = {
  draft: 'muted',
  open: 'warning',
  paid: 'success',
  void: 'muted',
  uncollectible: 'muted',
}

const invoiceStatusLabel: Record<InvoiceStatus, string> = {
  draft: 'Borrador',
  open: 'Pendiente',
  paid: 'Pagada',
  void: 'Anulada',
  uncollectible: 'Incobrable',
}

/* ─── Usage Bar ────────────────────────────────────────────────────── */

function UsageBar({ counter, label, icon: Icon }: { counter?: UsageCounter; label: string; icon: React.ElementType }) {
  if (!counter) return null
  const pct = usagePercent(counter)
  const limitLabel = counter.limit < 0 ? 'Ilimitado' : counter.limit.toLocaleString('es')

  return (
    <div className="flex flex-col gap-1.5">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <Icon className="h-4 w-4 text-muted-foreground" />
          <span>{counter.label ?? label}</span>
        </div>
        <span className={cn('text-sm font-semibold', usageTextColor(pct))}>
          {counter.current.toLocaleString('es')} / {limitLabel}
        </span>
      </div>
      <div className="h-2 w-full rounded-full bg-gray-200 overflow-hidden">
        <div
          className={cn('h-full rounded-full transition-all duration-500', usageColor(pct))}
          style={{ width: counter.limit < 0 ? '5%' : `${pct}%` }}
        />
      </div>
    </div>
  )
}

/* ─── Current Plan Section ─────────────────────────────────────────── */

function CurrentPlanSection({ tenantId }: { tenantId: string }) {
  const { data: usage, isLoading } = useUsageSummary(tenantId)
  const { data: sub } = useSubscription(tenantId)

  if (isLoading) {
    return (
      <div className="rounded-2xl border border-border bg-card p-6 animate-pulse">
        <div className="h-6 w-48 bg-gray-200 rounded mb-4" />
        <div className="h-4 w-72 bg-secondary rounded" />
      </div>
    )
  }

  if (!usage) {
    return (
      <div className="rounded-2xl border border-border bg-card p-6">
        <p className="text-sm text-muted-foreground">No se encontro informacion de uso para este tenant.</p>
      </div>
    )
  }

  return (
    <div className="rounded-2xl border border-border bg-card overflow-hidden">
      <div className="flex items-center gap-3 px-6 py-4 border-b border-border bg-muted/50">
        <div className="h-8 w-8 rounded-xl bg-primary/10 flex items-center justify-center text-primary shrink-0">
          <CreditCard className="h-4 w-4" />
        </div>
        <h2 className="text-sm font-bold text-foreground">Plan Actual</h2>
      </div>
      <div className="px-6 py-5 space-y-5">
        <div className="flex items-start justify-between">
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-xl font-bold text-foreground">{usage.plan_name}</h3>
              <Badge variant="info">Activo</Badge>
            </div>
            {sub?.plan && (
              <p className="text-2xl font-extrabold text-foreground mt-1">
                {fmtCurrency(Number(sub.plan.price_monthly ?? 0), sub.plan.currency ?? 'USD')}
                <span className="text-sm font-normal text-muted-foreground"> / mes</span>
              </p>
            )}
          </div>
          <div className="text-right">
            <p className="text-xs text-muted-foreground">Proximo cobro</p>
            <p className="text-sm font-semibold text-foreground">
              {sub?.current_period_end ? fmtDate(sub.current_period_end) : '-'}
            </p>
          </div>
        </div>

        <div className="space-y-3">
          <UsageBar counter={usage.users} label="Usuarios" icon={Users} />
          <UsageBar counter={usage.assets_this_month} label="Activos (este mes)" icon={Box} />
          <UsageBar counter={usage.wallets} label="Wallets" icon={Wallet} />
        </div>

        <div className="pt-2">
          <a href="#plans">
            <Button variant="outline" size="sm">
              <ArrowRight className="h-3.5 w-3.5" />
              Cambiar plan
            </Button>
          </a>
        </div>
      </div>
    </div>
  )
}

/* ─── Plan Card ────────────────────────────────────────────────────── */

const planIcons: Record<string, React.ElementType> = {
  free: Zap,
  starter: Star,
  professional: Crown,
  enterprise: Building2,
}

const planGradients: Record<string, string> = {
  free: 'from-gray-50 to-white border-border',
  starter: 'from-blue-50 to-white border-blue-200',
  professional: 'from-primary/10 to-white border-primary/30',
  enterprise: 'from-violet-50 to-white border-violet-200',
}

function PlanCard({
  plan,
  isCurrent,
  onSelect,
  loading,
}: {
  plan: Plan
  isCurrent: boolean
  onSelect: () => void
  loading: boolean
}) {
  const Icon = planIcons[plan.slug] ?? Star

  return (
    <div
      className={cn(
        'relative rounded-2xl border bg-gradient-to-b p-5 flex flex-col transition-all',
        planGradients[plan.slug] ?? 'from-gray-50 to-white border-border',
        isCurrent && 'ring-2 ring-ring',
      )}
    >
      {isCurrent && (
        <div className="absolute -top-2.5 left-1/2 -translate-x-1/2">
          <Badge variant="info">Plan actual</Badge>
        </div>
      )}

      <div className="flex items-center gap-2 mb-3">
        <div className="h-8 w-8 rounded-lg bg-card  flex items-center justify-center">
          <Icon className="h-4 w-4 text-primary" />
        </div>
        <h3 className="text-base font-bold text-foreground">{plan.name}</h3>
      </div>

      <p className="text-2xl font-extrabold text-foreground mb-1">
        {plan.price_monthly < 0 ? 'Custom' : fmtCurrency(plan.price_monthly, plan.currency)}
        {plan.price_monthly >= 0 && <span className="text-sm font-normal text-muted-foreground"> /mes</span>}
      </p>

      <p className="text-xs text-muted-foreground mb-4">{plan.description ?? ''}</p>

      <ul className="space-y-2 text-sm text-muted-foreground flex-1 mb-4">
        <li className="flex items-center gap-2">
          <Check className="h-3.5 w-3.5 text-emerald-500 shrink-0" />
          {plan.max_users < 0 ? 'Usuarios ilimitados' : `Hasta ${plan.max_users} usuarios`}
        </li>
        <li className="flex items-center gap-2">
          <Check className="h-3.5 w-3.5 text-emerald-500 shrink-0" />
          {plan.max_assets < 0 ? 'Assets ilimitados' : `Hasta ${plan.max_assets.toLocaleString('es')} assets/mes`}
        </li>
        <li className="flex items-center gap-2">
          <Check className="h-3.5 w-3.5 text-emerald-500 shrink-0" />
          {plan.max_wallets < 0 ? 'Wallets ilimitados' : `Hasta ${plan.max_wallets} wallets`}
        </li>
        {plan.modules.length > 0 && (
          <li className="flex items-center gap-2">
            <Check className="h-3.5 w-3.5 text-emerald-500 shrink-0" />
            {plan.modules.length} modulo{plan.modules.length > 1 ? 's' : ''} incluido{plan.modules.length > 1 ? 's' : ''}
          </li>
        )}
      </ul>

      {isCurrent ? (
        <Button variant="secondary" size="sm" disabled className="w-full">
          Plan actual
        </Button>
      ) : (
        <Button variant="primary" size="sm" onClick={onSelect} loading={loading} className="w-full">
          Seleccionar
        </Button>
      )}
    </div>
  )
}

/* ─── Plan Comparison Section ──────────────────────────────────────── */

function PlanComparisonSection({ tenantId, currentPlanSlug }: { tenantId: string; currentPlanSlug?: string }) {
  const { data: plans, isLoading } = usePlans()
  const checkout = useCheckout()
  const [selectingSlug, setSelectingSlug] = useState<string | null>(null)

  const activePlans = (plans ?? []).filter((p) => p.is_active && !p.is_archived).sort((a, b) => a.sort_order - b.sort_order)

  const handleSelect = async (plan: Plan) => {
    setSelectingSlug(plan.slug)
    try {
      const result = await checkout.mutateAsync({ tenant_id: tenantId, plan_slug: plan.slug })
      if (result.checkout_url) {
        window.location.href = result.checkout_url
      }
    } catch {
      // error handled by React Query
    } finally {
      setSelectingSlug(null)
    }
  }

  if (isLoading) {
    return (
      <div className="rounded-2xl border border-border bg-card p-6 animate-pulse">
        <div className="h-6 w-48 bg-gray-200 rounded mb-4" />
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="h-64 bg-secondary rounded-xl" />
          ))}
        </div>
      </div>
    )
  }

  return (
    <div id="plans" className="rounded-2xl border border-border bg-card overflow-hidden">
      <div className="flex items-center gap-3 px-6 py-4 border-b border-border bg-muted/50">
        <div className="h-8 w-8 rounded-xl bg-violet-50 flex items-center justify-center text-violet-500 shrink-0">
          <Crown className="h-4 w-4" />
        </div>
        <h2 className="text-sm font-bold text-foreground">Comparar Planes</h2>
      </div>
      <div className="px-6 py-5">
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {activePlans.map((plan) => (
            <PlanCard
              key={plan.id}
              plan={plan}
              isCurrent={plan.slug === currentPlanSlug}
              onSelect={() => handleSelect(plan)}
              loading={selectingSlug === plan.slug}
            />
          ))}
        </div>
      </div>
    </div>
  )
}

/* ─── Invoice History Section ──────────────────────────────────────── */

function InvoiceHistorySection({ tenantId }: { tenantId: string }) {
  const { data: invoices, isLoading } = useTenantInvoices(tenantId)

  return (
    <div className="rounded-2xl border border-border bg-card overflow-hidden">
      <div className="flex items-center gap-3 px-6 py-4 border-b border-border bg-muted/50">
        <div className="h-8 w-8 rounded-xl bg-emerald-50 flex items-center justify-center text-emerald-500 shrink-0">
          <Receipt className="h-4 w-4" />
        </div>
        <h2 className="text-sm font-bold text-foreground">Historial de Facturas</h2>
      </div>
      <div className="px-6 py-5">
        {isLoading ? (
          <div className="animate-pulse space-y-3">
            {[1, 2, 3].map((i) => (
              <div key={i} className="h-10 bg-secondary rounded" />
            ))}
          </div>
        ) : !invoices || invoices.length === 0 ? (
          <p className="text-sm text-muted-foreground text-center py-6">No hay facturas registradas.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead>
                <tr className="border-b border-border">
                  <th className="text-left py-2 px-3 text-xs font-semibold text-muted-foreground uppercase tracking-wider">Numero</th>
                  <th className="text-left py-2 px-3 text-xs font-semibold text-muted-foreground uppercase tracking-wider">Periodo</th>
                  <th className="text-right py-2 px-3 text-xs font-semibold text-muted-foreground uppercase tracking-wider">Monto</th>
                  <th className="text-center py-2 px-3 text-xs font-semibold text-muted-foreground uppercase tracking-wider">Estado</th>
                  <th className="text-left py-2 px-3 text-xs font-semibold text-muted-foreground uppercase tracking-wider">Fecha pago</th>
                </tr>
              </thead>
              <tbody>
                {invoices.map((inv) => (
                  <tr key={inv.id} className="border-b border-gray-50 hover:bg-muted/50 transition-colors">
                    <td className="py-2.5 px-3 font-mono text-xs text-foreground">{inv.invoice_number}</td>
                    <td className="py-2.5 px-3 text-muted-foreground">
                      {fmtDate(inv.period_start)} - {fmtDate(inv.period_end)}
                    </td>
                    <td className="py-2.5 px-3 text-right font-semibold text-foreground">
                      {fmtCurrency(inv.amount, inv.currency)}
                    </td>
                    <td className="py-2.5 px-3 text-center">
                      <Badge variant={invoiceStatusVariant[inv.status] ?? 'default'} dot>
                        {invoiceStatusLabel[inv.status] ?? inv.status}
                      </Badge>
                    </td>
                    <td className="py-2.5 px-3 text-muted-foreground">
                      {inv.paid_at ? fmtDate(inv.paid_at) : '-'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}

/* ─── Main BillingPage ─────────────────────────────────────────────── */

export function BillingPage() {
  const user = useAuthStore((s) => s.user)
  const tenantId = user?.tenant_id ?? 'default'
  const { data: sub } = useSubscription(tenantId)

  return (
    <div className="flex flex-col flex-1 overflow-hidden">
      <Topbar
        title="Facturacion y Plan"
        subtitle="Gestiona tu suscripcion, uso y facturas"
      />
      <div className="flex-1 overflow-y-auto p-6">
        <div className="max-w-4xl mx-auto space-y-5">
          <CurrentPlanSection tenantId={tenantId} />
          <PlanComparisonSection tenantId={tenantId} currentPlanSlug={sub?.plan?.slug} />
          <InvoiceHistorySection tenantId={tenantId} />
        </div>
      </div>
    </div>
  )
}
