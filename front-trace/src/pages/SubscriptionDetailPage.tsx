import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import {
  ArrowLeft, CreditCard, XCircle, RefreshCw, Plus, CheckCircle,
  ShoppingBag, Calendar, DollarSign, Users, Box, Wallet, Clock,
} from 'lucide-react'
import { useAuthStore } from '@/store/auth'
import {
  useSubscription,
  useCancelSubscription,
  useReactivateSubscription,
  useInvoices,
  useCreateInvoice,
  useMarkPaid,
  useSubEvents,
} from '@/hooks/useSubscriptions'
import type { SubscriptionStatus, SubscriptionEventType } from '@/types/subscription'
import { cn } from '@/lib/utils'

// ─── Status Badge ─────────────────────────────────────────────────────────────

const STATUS_COLORS: Record<SubscriptionStatus, string> = {
  active:   'bg-emerald-100 text-emerald-700',
  trialing: 'bg-amber-100 text-amber-700',
  past_due: 'bg-red-100 text-red-700',
  canceled: 'bg-secondary text-muted-foreground',
  expired:  'bg-red-50 text-red-400',
}

const STATUS_LABELS: Record<SubscriptionStatus, string> = {
  active:   'Activa',
  trialing: 'Prueba',
  past_due: 'Pago pendiente',
  canceled: 'Cancelada',
  expired:  'Expirada',
}

function StatusBadge({ status }: { status: SubscriptionStatus }) {
  return (
    <span className={cn('inline-flex rounded-full px-2.5 py-0.5 text-xs font-semibold', STATUS_COLORS[status])}>
      {STATUS_LABELS[status]}
    </span>
  )
}

// ─── Event icon ───────────────────────────────────────────────────────────────

const EVENT_ICONS: Record<SubscriptionEventType, string> = {
  created:           '🎉',
  plan_changed:      '🔄',
  canceled:          '❌',
  reactivated:       '✅',
  invoice_generated: '🧾',
  payment_received:  '💳',
  trial_started:     '🚀',
  trial_ended:       '⏰',
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

function formatCurrency(amount: number, currency = 'USD') {
  return new Intl.NumberFormat('es-CO', { style: 'currency', currency }).format(amount)
}

function daysRemaining(endDate: string): number {
  const diff = new Date(endDate).getTime() - Date.now()
  return Math.max(0, Math.ceil(diff / 86_400_000))
}

const CYCLE_LABELS: Record<string, string> = {
  monthly: 'Mensual',
  annual: 'Anual',
  custom: 'Personalizado',
}

// ─── Empty State ──────────────────────────────────────────────────────────────

function NoSubscription() {
  const navigate = useNavigate()

  return (
    <div className="flex flex-col items-center justify-center py-24 px-4">
      <div className="flex h-20 w-20 items-center justify-center rounded-3xl bg-secondary mb-6">
        <CreditCard className="h-10 w-10 text-muted-foreground" />
      </div>
      <h2 className="text-xl font-bold text-foreground mb-2">No tienes suscripciones activas</h2>
      <p className="text-sm text-muted-foreground max-w-md text-center mb-8">
        Explora nuestro Marketplace para activar modulos y obtener una suscripcion que se adapte a las necesidades de tu empresa.
      </p>
      <button
        onClick={() => navigate('/marketplace')}
        className="flex items-center gap-2 rounded-xl bg-primary px-6 py-3 text-sm font-semibold text-white hover:bg-primary/90 transition-colors"
      >
        <ShoppingBag className="h-4 w-4" /> Ir al Marketplace
      </button>
    </div>
  )
}

// ─── Main Page ────────────────────────────────────────────────────────────────

export function SubscriptionDetailPage() {
  const { tenantId } = useParams<{ tenantId: string }>()
  const navigate = useNavigate()
  const [tab, setTab] = useState<'invoices' | 'events'>('invoices')
  const [cancelConfirm, setCancelConfirm] = useState(false)

  // Fall back to user's own tenant_id when accessed from /empresa/suscripcion
  const userTenantId = useAuthStore((s) => s.user?.tenant_id) ?? 'default'
  const tid = tenantId ?? userTenantId

  const { data: sub, isLoading } = useSubscription(tid)
  const { data: invoices = [] } = useInvoices(tid)
  const { data: events = [] } = useSubEvents(tid)

  const cancel = useCancelSubscription()
  const reactivate = useReactivateSubscription()
  const createInvoice = useCreateInvoice()
  const markPaid = useMarkPaid()

  if (isLoading) {
    return (
      <div className="flex items-center justify-center p-16">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary/30 border-t-primary" />
      </div>
    )
  }

  if (!sub) {
    return (
      <div className="p-8">
        <button onClick={() => navigate(-1)} className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground transition-colors mb-6">
          <ArrowLeft className="h-4 w-4" /> Volver
        </button>
        <div className="rounded-2xl border border-border bg-card ">
          <NoSubscription />
        </div>
      </div>
    )
  }

  const days = daysRemaining(sub.current_period_end)
  const price = sub.plan.price_monthly
  const tabs = [
    { key: 'invoices' as const, label: `Facturas (${invoices.length})` },
    { key: 'events' as const, label: `Eventos (${events.length})` },
  ]

  return (
    <div className="p-8 space-y-6">
      {/* Back */}
      <button onClick={() => navigate(-1)} className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground transition-colors">
        <ArrowLeft className="h-4 w-4" /> Volver
      </button>

      {/* Header */}
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-4">
          <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-primary/15">
            <CreditCard className="h-6 w-6 text-primary" />
          </div>
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-2xl font-bold text-foreground">Mi Suscripcion</h1>
              <span className="rounded-lg bg-primary/15 px-2 py-0.5 text-xs font-semibold text-primary">
                {sub.plan.name}
              </span>
              <StatusBadge status={sub.status} />
            </div>
            <p className="text-sm text-muted-foreground mt-0.5">
              Tenant: <span className="font-mono">{sub.tenant_id}</span>
            </p>
          </div>
        </div>

        <div className="flex gap-2">
          {sub.status !== 'canceled' && (
            <button
              onClick={() => setCancelConfirm(true)}
              className="flex items-center gap-2 rounded-xl border border-red-200 px-3 py-2 text-sm font-semibold text-red-600 hover:bg-red-50"
            >
              <XCircle className="h-4 w-4" /> Cancelar
            </button>
          )}
          {sub.status === 'canceled' && (
            <button
              onClick={() => reactivate.mutate(tid)}
              disabled={reactivate.isPending}
              className="flex items-center gap-2 rounded-xl border border-emerald-200 px-3 py-2 text-sm font-semibold text-emerald-600 hover:bg-emerald-50 disabled:opacity-50"
            >
              <RefreshCw className="h-4 w-4" /> Reactivar
            </button>
          )}
        </div>
      </div>

      {/* Plan detail cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="rounded-2xl border border-border bg-card p-4 ">
          <div className="flex items-center gap-2 text-muted-foreground mb-2">
            <DollarSign className="h-4 w-4" />
            <span className="text-xs font-semibold uppercase tracking-wide">Costo mensual</span>
          </div>
          <p className="text-2xl font-bold text-foreground">
            {price < 0 ? 'Personalizado' : formatCurrency(price, sub.plan.currency)}
          </p>
          <p className="text-xs text-muted-foreground mt-1">{CYCLE_LABELS[sub.billing_cycle] ?? sub.billing_cycle}</p>
        </div>

        <div className="rounded-2xl border border-border bg-card p-4 ">
          <div className="flex items-center gap-2 text-muted-foreground mb-2">
            <Clock className="h-4 w-4" />
            <span className="text-xs font-semibold uppercase tracking-wide">Tiempo restante</span>
          </div>
          <p className="text-2xl font-bold text-foreground">{days} dias</p>
          <p className="text-xs text-muted-foreground mt-1">
            Vence {new Date(sub.current_period_end).toLocaleDateString()}
          </p>
        </div>

        <div className="rounded-2xl border border-border bg-card p-4 ">
          <div className="flex items-center gap-2 text-muted-foreground mb-2">
            <Calendar className="h-4 w-4" />
            <span className="text-xs font-semibold uppercase tracking-wide">Periodo actual</span>
          </div>
          <p className="text-sm font-semibold text-foreground">
            {new Date(sub.current_period_start).toLocaleDateString()}
          </p>
          <p className="text-xs text-muted-foreground mt-1">
            hasta {new Date(sub.current_period_end).toLocaleDateString()}
          </p>
        </div>

        <div className="rounded-2xl border border-border bg-card p-4 ">
          <div className="flex items-center gap-2 text-muted-foreground mb-2">
            <Calendar className="h-4 w-4" />
            <span className="text-xs font-semibold uppercase tracking-wide">Creada</span>
          </div>
          <p className="text-sm font-semibold text-foreground">
            {new Date(sub.created_at).toLocaleDateString()}
          </p>
          {sub.trial_ends_at && (
            <p className="text-xs text-amber-600 mt-1">
              Prueba hasta {new Date(sub.trial_ends_at).toLocaleDateString()}
            </p>
          )}
        </div>
      </div>

      {/* Plan limits */}
      <div className="rounded-2xl border border-border bg-card p-5 ">
        <h3 className="text-sm font-semibold text-foreground mb-3">Limites del plan</h3>
        <div className="grid grid-cols-3 gap-4">
          <div className="flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-blue-50">
              <Users className="h-4 w-4 text-blue-600" />
            </div>
            <div>
              <p className="text-lg font-bold text-foreground">
                {sub.plan.max_users === -1 ? 'Ilimitados' : sub.plan.max_users}
              </p>
              <p className="text-xs text-muted-foreground">Usuarios</p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-emerald-50">
              <Box className="h-4 w-4 text-emerald-600" />
            </div>
            <div>
              <p className="text-lg font-bold text-foreground">
                {sub.plan.max_assets === -1 ? 'Ilimitados' : sub.plan.max_assets}
              </p>
              <p className="text-xs text-muted-foreground">Activos</p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-violet-50">
              <Wallet className="h-4 w-4 text-violet-600" />
            </div>
            <div>
              <p className="text-lg font-bold text-foreground">
                {sub.plan.max_wallets === -1 ? 'Ilimitadas' : sub.plan.max_wallets}
              </p>
              <p className="text-xs text-muted-foreground">Wallets</p>
            </div>
          </div>
        </div>
      </div>

      {/* Cancel confirm */}
      {cancelConfirm && (
        <div className="rounded-xl border border-red-200 bg-red-50 p-4 flex items-center justify-between">
          <p className="text-sm text-red-700 font-medium">¿Confirmar cancelacion de la suscripcion?</p>
          <div className="flex gap-2">
            <button onClick={() => setCancelConfirm(false)} className="rounded-lg px-3 py-1.5 text-sm text-muted-foreground hover:bg-card">No</button>
            <button
              onClick={() => { cancel.mutate({ tenantId: tid }); setCancelConfirm(false) }}
              className="rounded-lg bg-red-600 px-3 py-1.5 text-sm font-semibold text-white hover:bg-red-700"
            >
              Si, cancelar
            </button>
          </div>
        </div>
      )}

      {/* Tabs */}
      <div className="flex gap-1 border-b border-border">
        {tabs.map(t => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className={cn(
              'px-4 py-2.5 text-sm font-semibold transition-colors border-b-2 -mb-px',
              tab === t.key
                ? 'border-primary text-primary'
                : 'border-transparent text-muted-foreground hover:text-foreground',
            )}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* Invoices Tab */}
      {tab === 'invoices' && (
        <div className="space-y-4">
          <div className="flex justify-end">
            <button
              onClick={() => createInvoice.mutate(tid)}
              disabled={createInvoice.isPending}
              className="flex items-center gap-2 rounded-xl bg-primary px-3 py-2 text-sm font-semibold text-white hover:bg-primary/90 disabled:opacity-50"
            >
              <Plus className="h-4 w-4" /> Generar factura
            </button>
          </div>
          <div className="rounded-2xl border border-border bg-card  overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border bg-muted">
                  <th className="px-4 py-3 text-left font-semibold text-muted-foreground">Numero</th>
                  <th className="px-4 py-3 text-left font-semibold text-muted-foreground">Estado</th>
                  <th className="px-4 py-3 text-left font-semibold text-muted-foreground">Monto</th>
                  <th className="px-4 py-3 text-left font-semibold text-muted-foreground">Periodo</th>
                  <th className="px-4 py-3 text-left font-semibold text-muted-foreground">Accion</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-50">
                {invoices.map(inv => (
                  <tr key={inv.id}>
                    <td className="px-4 py-3 font-mono text-xs">{inv.invoice_number}</td>
                    <td className="px-4 py-3">
                      <span className={cn(
                        'rounded-full px-2 py-0.5 text-xs font-semibold',
                        inv.status === 'paid' ? 'bg-emerald-100 text-emerald-700' :
                        inv.status === 'open' ? 'bg-amber-100 text-amber-700' :
                        'bg-secondary text-muted-foreground',
                      )}>
                        {inv.status}
                      </span>
                    </td>
                    <td className="px-4 py-3 font-semibold">{formatCurrency(Number(inv.amount), inv.currency)}</td>
                    <td className="px-4 py-3 text-xs text-muted-foreground">
                      {new Date(inv.period_start).toLocaleDateString()} – {new Date(inv.period_end).toLocaleDateString()}
                    </td>
                    <td className="px-4 py-3">
                      {inv.status === 'open' && (
                        <button
                          onClick={() => markPaid.mutate({ tenantId: tid, invId: inv.id })}
                          disabled={markPaid.isPending}
                          className="flex items-center gap-1 text-xs font-semibold text-emerald-600 hover:text-emerald-800 disabled:opacity-50"
                        >
                          <CheckCircle className="h-3.5 w-3.5" /> Marcar pagada
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
                {invoices.length === 0 && (
                  <tr><td colSpan={5} className="px-4 py-8 text-center text-muted-foreground text-sm">Sin facturas</td></tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Events Tab */}
      {tab === 'events' && (
        <div className="space-y-3">
          {events.map(ev => (
            <div key={ev.id} className="flex items-start gap-4 rounded-2xl border border-border bg-card p-4 ">
              <span className="text-2xl">{EVENT_ICONS[ev.event_type] ?? '📌'}</span>
              <div className="flex-1">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-semibold text-foreground capitalize">{ev.event_type.replace(/_/g, ' ')}</span>
                  {ev.performed_by && (
                    <span className="text-xs text-muted-foreground">por {ev.performed_by}</span>
                  )}
                </div>
                <p className="text-xs text-muted-foreground mt-0.5">{new Date(ev.created_at).toLocaleString()}</p>
                {ev.data && Object.keys(ev.data).length > 0 && (
                  <pre className="mt-2 text-xs text-muted-foreground bg-muted rounded-lg p-2 overflow-x-auto">
                    {JSON.stringify(ev.data, null, 2)}
                  </pre>
                )}
              </div>
            </div>
          ))}
          {events.length === 0 && (
            <div className="rounded-2xl border border-border bg-card p-8 text-center text-muted-foreground text-sm">
              Sin eventos
            </div>
          )}
        </div>
      )}

    </div>
  )
}
