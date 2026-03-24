import { useParams, Link } from 'react-router-dom'
import { useState } from 'react'
import {
  ArrowLeft, Building2, CreditCard, Key, Activity, Layers, Banknote,
  CheckCircle2, XCircle, Clock, AlertTriangle, RefreshCw, LinkIcon,
  Receipt, ArrowUpDown, Power,
} from 'lucide-react'
import {
  usePlatformTenantDetail,
  useChangeTenantPlan,
  useToggleTenantModule,
  useGenerateTenantInvoice,
  useGeneratePaymentLink,
  useCancelTenantSubscription,
  useReactivateTenantSubscription,
} from '@/hooks/usePlatform'
import { useQuery } from '@tanstack/react-query'
import { subscriptionApi } from '@/lib/subscription-api'
import { cn } from '@/lib/utils'
import type { PaymentLinkResult } from '@/types/platform'

const STATUS_BADGE: Record<string, { bg: string; text: string; label: string }> = {
  active:   { bg: 'bg-green-100', text: 'text-green-700', label: 'Activa' },
  trialing: { bg: 'bg-blue-100', text: 'text-blue-700', label: 'Prueba' },
  past_due: { bg: 'bg-amber-100', text: 'text-amber-700', label: 'Mora' },
  canceled: { bg: 'bg-red-100', text: 'text-red-700', label: 'Cancelada' },
  expired:  { bg: 'bg-slate-100', text: 'text-slate-600', label: 'Expirada' },
}

const INV_BADGE: Record<string, string> = {
  paid: 'bg-green-100 text-green-700',
  open: 'bg-blue-100 text-blue-700',
  draft: 'bg-slate-100 text-slate-600',
  void: 'bg-red-100 text-red-700',
  uncollectible: 'bg-amber-100 text-amber-700',
}

const EVENT_ICONS: Record<string, React.ElementType> = {
  created: CheckCircle2,
  plan_changed: Layers,
  canceled: XCircle,
  reactivated: Activity,
  invoice_generated: CreditCard,
  payment_received: Banknote,
  trial_started: Clock,
  trial_ended: AlertTriangle,
}

const ALL_MODULES = ['logistics', 'inventory']

const tabs = ['Resumen', 'Acciones', 'Facturas', 'Licencias', 'Eventos'] as const
type Tab = (typeof tabs)[number]

export function PlatformTenantDetailPage() {
  const { tenantId } = useParams<{ tenantId: string }>()
  const tid = tenantId ?? ''
  const { data, isLoading } = usePlatformTenantDetail(tid)
  const [tab, setTab] = useState<Tab>('Resumen')
  const [paymentLink, setPaymentLink] = useState<PaymentLinkResult | null>(null)
  const [cancelReason, setCancelReason] = useState('')
  const [showCancelConfirm, setShowCancelConfirm] = useState(false)

  // Mutations
  const changePlan = useChangeTenantPlan(tid)
  const toggleModule = useToggleTenantModule(tid)
  const generateInvoice = useGenerateTenantInvoice(tid)
  const generatePaymentLinkMut = useGeneratePaymentLink(tid)
  const cancelSub = useCancelTenantSubscription(tid)
  const reactivateSub = useReactivateTenantSubscription(tid)

  // Plans list for change-plan
  const { data: plans } = useQuery({
    queryKey: ['plans'],
    queryFn: () => subscriptionApi.plans.list(),
    staleTime: 60_000,
  })

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
      </div>
    )
  }
  if (!data) {
    return (
      <div className="text-center py-12">
        <p className="text-slate-500">Empresa no encontrada</p>
        <Link to="/platform/tenants" className="text-primary text-sm mt-2 inline-block">Volver</Link>
      </div>
    )
  }

  const sub = data.subscription
  const badge = STATUS_BADGE[sub.status] ?? STATUS_BADGE.expired
  const activePlans = (plans ?? []).filter(p => p.is_active && !p.is_archived)
  const isCanceled = sub.status === 'canceled'

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <Link to="/platform/tenants" className="inline-flex items-center gap-1 text-sm text-slate-500 hover:text-primary mb-3">
          <ArrowLeft className="h-4 w-4" /> Empresas
        </Link>
        <div className="flex items-center gap-4">
          <div className="h-12 w-12 rounded-2xl bg-primary/15 flex items-center justify-center">
            <Building2 className="h-6 w-6 text-primary" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-slate-900">{data.tenant_id}</h1>
            <div className="flex items-center gap-2 mt-1">
              <span className={`inline-flex px-2.5 py-0.5 rounded-lg text-xs font-semibold ${badge.bg} ${badge.text}`}>
                {badge.label}
              </span>
              <span className="text-xs text-slate-400">Plan: {sub.plan.name} (${sub.plan.price_monthly}/mes)</span>
            </div>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 bg-slate-100 p-1 rounded-xl w-fit">
        {tabs.map(t => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={cn(
              'px-4 py-2 text-sm font-medium rounded-lg transition',
              tab === t ? 'bg-white shadow-sm text-slate-900' : 'text-slate-500 hover:text-slate-700',
            )}
          >
            {t}
          </button>
        ))}
      </div>

      {/* === Resumen tab === */}
      {tab === 'Resumen' && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Subscription info */}
          <div className="bg-white rounded-2xl border border-slate-200/60 p-6 shadow-sm">
            <h3 className="text-sm font-semibold text-slate-700 mb-4 flex items-center gap-2">
              <CreditCard className="h-4 w-4 text-primary" /> Suscripcion
            </h3>
            <dl className="space-y-3 text-sm">
              {([
                ['Plan', sub.plan.name],
                ['Precio', `$${sub.plan.price_monthly}/mes`],
                ['Ciclo', sub.billing_cycle],
                ['Periodo actual', sub.current_period_end ? new Date(sub.current_period_end).toLocaleDateString('es') : '-'],
                ['Creada', sub.created_at ? new Date(sub.created_at).toLocaleDateString('es') : '-'],
              ] as const).map(([label, val]) => (
                <div key={label} className="flex justify-between">
                  <dt className="text-slate-500">{label}</dt>
                  <dd className="font-medium">{val}</dd>
                </div>
              ))}
              {sub.canceled_at && (
                <div className="flex justify-between">
                  <dt className="text-slate-500">Cancelada</dt>
                  <dd className="font-medium text-red-600">{new Date(sub.canceled_at).toLocaleDateString('es')}</dd>
                </div>
              )}
            </dl>
            <div className="mt-4 pt-4 border-t border-slate-100">
              <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-2">Limites</p>
              <div className="grid grid-cols-3 gap-3">
                {([['Usuarios', sub.plan.max_users], ['Assets', sub.plan.max_assets], ['Wallets', sub.plan.max_wallets]] as const).map(([l, v]) => (
                  <div key={l} className="bg-slate-50 rounded-lg p-2 text-center">
                    <div className="text-lg font-bold text-slate-900">{v}</div>
                    <div className="text-xs text-slate-500">{l}</div>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Modules + gateway */}
          <div className="bg-white rounded-2xl border border-slate-200/60 p-6 shadow-sm">
            <h3 className="text-sm font-semibold text-slate-700 mb-4 flex items-center gap-2">
              <Layers className="h-4 w-4 text-primary" /> Modulos
            </h3>
            <div className="space-y-3">
              {data.modules.length > 0 ? data.modules.map(m => (
                <div key={m.slug} className="flex items-center justify-between bg-slate-50 rounded-xl p-3">
                  <div className="flex items-center gap-3">
                    <span className={cn('h-2.5 w-2.5 rounded-full', m.is_active ? 'bg-green-500' : 'bg-slate-300')} />
                    <span className="text-sm font-medium text-slate-700 capitalize">{m.slug}</span>
                  </div>
                  <span className="text-xs text-slate-400">{m.is_active ? 'Activo' : 'Inactivo'}</span>
                </div>
              )) : (
                <p className="text-sm text-slate-400">Sin modulos activados</p>
              )}
            </div>
            {data.active_gateway && (
              <div className="mt-6 pt-4 border-t border-slate-100">
                <h4 className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-2">Pasarela</h4>
                <div className="bg-slate-50 rounded-xl p-3">
                  <span className="text-sm font-medium text-slate-700">{data.active_gateway.display_name}</span>
                  <span className={cn('ml-2 text-xs px-2 py-0.5 rounded-md font-medium',
                    data.active_gateway.is_test_mode ? 'bg-amber-100 text-amber-700' : 'bg-green-100 text-green-700',
                  )}>
                    {data.active_gateway.is_test_mode ? 'Test' : 'Produccion'}
                  </span>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* === Acciones tab === */}
      {tab === 'Acciones' && (
        <div className="space-y-6">
          {/* Change plan */}
          <div className="bg-white rounded-2xl border border-slate-200/60 p-6 shadow-sm">
            <h3 className="text-sm font-semibold text-slate-700 mb-3 flex items-center gap-2">
              <ArrowUpDown className="h-4 w-4 text-primary" /> Cambiar Plan
            </h3>
            <p className="text-xs text-slate-400 mb-3">Plan actual: <strong>{sub.plan.name}</strong></p>
            <div className="flex flex-wrap gap-2">
              {activePlans.map(p => (
                <button
                  key={p.slug}
                  disabled={p.slug === sub.plan.slug || changePlan.isPending}
                  onClick={() => changePlan.mutate(p.slug)}
                  className={cn(
                    'px-4 py-2 text-sm rounded-xl border-2 font-medium transition',
                    p.slug === sub.plan.slug
                      ? 'border-primary bg-primary/10 text-primary cursor-default'
                      : 'border-slate-200 text-slate-600 hover:border-primary/50 hover:bg-primary/10',
                  )}
                >
                  {p.name} {p.price_monthly > 0 ? `($${p.price_monthly})` : '(Gratis)'}
                </button>
              ))}
            </div>
            {changePlan.isSuccess && (
              <p className="text-sm text-emerald-600 mt-2 flex items-center gap-1"><CheckCircle2 className="h-4 w-4" /> Plan cambiado</p>
            )}
          </div>

          {/* Toggle modules */}
          <div className="bg-white rounded-2xl border border-slate-200/60 p-6 shadow-sm">
            <h3 className="text-sm font-semibold text-slate-700 mb-3 flex items-center gap-2">
              <Layers className="h-4 w-4 text-primary" /> Modulos
            </h3>
            <div className="flex gap-3">
              {ALL_MODULES.map(m => {
                const isActive = data.modules.some(mod => mod.slug === m && mod.is_active)
                return (
                  <button
                    key={m}
                    onClick={() => toggleModule.mutate({ slug: m, active: !isActive })}
                    disabled={toggleModule.isPending}
                    className={cn(
                      'flex items-center gap-2 px-4 py-3 rounded-xl border-2 text-sm font-medium transition',
                      isActive
                        ? 'border-green-500 bg-green-50 text-green-700'
                        : 'border-slate-200 text-slate-600 hover:border-slate-300',
                    )}
                  >
                    <Power className="h-4 w-4" />
                    <span className="capitalize">{m}</span>
                    <span className="text-xs">{isActive ? 'ON' : 'OFF'}</span>
                  </button>
                )
              })}
            </div>
          </div>

          {/* Invoice + payment link */}
          <div className="bg-white rounded-2xl border border-slate-200/60 p-6 shadow-sm">
            <h3 className="text-sm font-semibold text-slate-700 mb-3 flex items-center gap-2">
              <Receipt className="h-4 w-4 text-primary" /> Facturacion
            </h3>
            <div className="flex flex-wrap gap-3">
              <button
                onClick={() => generateInvoice.mutate()}
                disabled={generateInvoice.isPending}
                className="flex items-center gap-2 px-4 py-2.5 text-sm font-medium text-white bg-primary hover:bg-primary/90 rounded-xl disabled:opacity-50 transition"
              >
                <CreditCard className="h-4 w-4" /> Generar Factura
              </button>
              <button
                onClick={async () => {
                  const result = await generatePaymentLinkMut.mutateAsync()
                  setPaymentLink(result)
                }}
                disabled={generatePaymentLinkMut.isPending}
                className="flex items-center gap-2 px-4 py-2.5 text-sm font-medium text-primary bg-primary/10 hover:bg-primary/15 rounded-xl disabled:opacity-50 transition"
              >
                <LinkIcon className="h-4 w-4" /> Generar Link de Pago
              </button>
            </div>
            {generateInvoice.isSuccess && (
              <p className="text-sm text-emerald-600 mt-3 flex items-center gap-1">
                <CheckCircle2 className="h-4 w-4" /> Factura {(generateInvoice.data as { invoice_number: string })?.invoice_number} generada
              </p>
            )}
            {paymentLink && (
              <div className="mt-3 bg-slate-50 rounded-xl p-4">
                <p className="text-xs font-semibold text-slate-500 mb-1">Link de Pago Generado</p>
                <div className="flex items-center gap-2">
                  <code className="text-sm text-primary bg-white px-3 py-1.5 rounded-lg border border-slate-200 flex-1 truncate">
                    {window.location.origin}{paymentLink.link}
                  </code>
                  <button
                    onClick={() => navigator.clipboard.writeText(`${window.location.origin}${paymentLink.link}`)}
                    className="px-3 py-1.5 text-xs font-medium bg-primary/15 text-primary rounded-lg hover:bg-primary/20 transition"
                  >
                    Copiar
                  </button>
                </div>
                <p className="text-xs text-slate-400 mt-1">
                  {paymentLink.plan_name} — ${paymentLink.amount} {paymentLink.currency} — Factura: {paymentLink.invoice_number}
                </p>
              </div>
            )}
          </div>

          {/* Cancel / Reactivate */}
          <div className="bg-white rounded-2xl border border-slate-200/60 p-6 shadow-sm">
            <h3 className="text-sm font-semibold text-slate-700 mb-3 flex items-center gap-2">
              {isCanceled ? <RefreshCw className="h-4 w-4 text-emerald-500" /> : <XCircle className="h-4 w-4 text-red-500" />}
              {isCanceled ? 'Reactivar Suscripcion' : 'Cancelar Suscripcion'}
            </h3>
            {isCanceled ? (
              <button
                onClick={() => reactivateSub.mutate()}
                disabled={reactivateSub.isPending}
                className="flex items-center gap-2 px-4 py-2.5 text-sm font-medium text-white bg-emerald-600 hover:bg-emerald-700 rounded-xl disabled:opacity-50 transition"
              >
                <RefreshCw className="h-4 w-4" /> Reactivar
              </button>
            ) : showCancelConfirm ? (
              <div className="space-y-3">
                <textarea
                  value={cancelReason}
                  onChange={e => setCancelReason(e.target.value)}
                  placeholder="Razon de cancelacion (opcional)..."
                  rows={2}
                  className="w-full px-3 py-2 text-sm border border-slate-200 rounded-xl outline-none resize-none"
                />
                <div className="flex gap-2">
                  <button
                    onClick={() => { cancelSub.mutate(cancelReason || undefined); setShowCancelConfirm(false) }}
                    disabled={cancelSub.isPending}
                    className="px-4 py-2 text-sm font-medium text-white bg-red-600 hover:bg-red-700 rounded-xl transition"
                  >
                    Confirmar Cancelacion
                  </button>
                  <button
                    onClick={() => setShowCancelConfirm(false)}
                    className="px-4 py-2 text-sm font-medium text-slate-600 bg-slate-100 hover:bg-slate-200 rounded-xl transition"
                  >
                    Volver
                  </button>
                </div>
              </div>
            ) : (
              <button
                onClick={() => setShowCancelConfirm(true)}
                className="flex items-center gap-2 px-4 py-2.5 text-sm font-medium text-red-600 bg-red-50 hover:bg-red-100 rounded-xl transition"
              >
                <XCircle className="h-4 w-4" /> Cancelar Suscripcion
              </button>
            )}
          </div>
        </div>
      )}

      {/* === Facturas tab === */}
      {tab === 'Facturas' && (
        <div className="bg-white rounded-2xl border border-slate-200/60 shadow-sm overflow-hidden">
          {data.invoices.length === 0 ? (
            <div className="text-center py-12 text-slate-400">
              <CreditCard className="h-8 w-8 mx-auto mb-2 opacity-40" />
              <p className="text-sm">Sin facturas</p>
            </div>
          ) : (
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-slate-50 border-b border-slate-100">
                  <th className="text-left px-5 py-3 font-semibold text-slate-600">Factura</th>
                  <th className="text-left px-5 py-3 font-semibold text-slate-600">Estado</th>
                  <th className="text-right px-5 py-3 font-semibold text-slate-600">Monto</th>
                  <th className="text-left px-5 py-3 font-semibold text-slate-600">Periodo</th>
                  <th className="text-left px-5 py-3 font-semibold text-slate-600">Pagada</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {data.invoices.map(inv => (
                  <tr key={inv.id} className="hover:bg-slate-50/60">
                    <td className="px-5 py-3 font-medium text-slate-900">{inv.invoice_number}</td>
                    <td className="px-5 py-3">
                      <span className={`inline-flex px-2 py-0.5 rounded-md text-xs font-semibold ${INV_BADGE[inv.status] ?? INV_BADGE.draft}`}>
                        {inv.status}
                      </span>
                    </td>
                    <td className="px-5 py-3 text-right font-semibold">${inv.amount.toLocaleString()} {inv.currency}</td>
                    <td className="px-5 py-3 text-slate-500">
                      {inv.period_start ? new Date(inv.period_start).toLocaleDateString('es', { month: 'short', year: 'numeric' }) : '-'}
                    </td>
                    <td className="px-5 py-3 text-slate-500">
                      {inv.paid_at ? new Date(inv.paid_at).toLocaleDateString('es') : '-'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}

      {/* === Licencias tab === */}
      {tab === 'Licencias' && (
        <div className="bg-white rounded-2xl border border-slate-200/60 shadow-sm overflow-hidden">
          {data.licenses.length === 0 ? (
            <div className="text-center py-12 text-slate-400">
              <Key className="h-8 w-8 mx-auto mb-2 opacity-40" />
              <p className="text-sm">Sin licencias</p>
            </div>
          ) : (
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-slate-50 border-b border-slate-100">
                  <th className="text-left px-5 py-3 font-semibold text-slate-600">Clave</th>
                  <th className="text-left px-5 py-3 font-semibold text-slate-600">Estado</th>
                  <th className="text-left px-5 py-3 font-semibold text-slate-600">Activaciones</th>
                  <th className="text-left px-5 py-3 font-semibold text-slate-600">Emitida</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {data.licenses.map(lic => (
                  <tr key={lic.id} className="hover:bg-slate-50/60">
                    <td className="px-5 py-3 font-mono text-xs text-slate-700">{lic.key}</td>
                    <td className="px-5 py-3">
                      <span className={cn(
                        'inline-flex px-2 py-0.5 rounded-md text-xs font-semibold',
                        lic.status === 'active' ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700',
                      )}>
                        {lic.status}
                      </span>
                    </td>
                    <td className="px-5 py-3 text-slate-600">
                      {lic.activations_count} / {lic.max_activations === -1 ? 'ilimitado' : lic.max_activations}
                    </td>
                    <td className="px-5 py-3 text-slate-500">
                      {lic.issued_at ? new Date(lic.issued_at).toLocaleDateString('es') : '-'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}

      {/* === Eventos tab === */}
      {tab === 'Eventos' && (
        <div className="bg-white rounded-2xl border border-slate-200/60 p-6 shadow-sm">
          {data.events.length === 0 ? (
            <div className="text-center py-12 text-slate-400">
              <Activity className="h-8 w-8 mx-auto mb-2 opacity-40" />
              <p className="text-sm">Sin eventos</p>
            </div>
          ) : (
            <div className="space-y-0">
              {data.events.map((ev, idx) => {
                const Icon = EVENT_ICONS[ev.event_type] ?? Activity
                return (
                  <div key={ev.id} className="flex gap-4 relative">
                    {idx < data.events.length - 1 && (
                      <div className="absolute left-[15px] top-8 bottom-0 w-px bg-slate-200" />
                    )}
                    <div className="h-8 w-8 rounded-full bg-slate-100 flex items-center justify-center shrink-0 z-10">
                      <Icon className="h-4 w-4 text-slate-500" />
                    </div>
                    <div className="pb-6 flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-semibold text-slate-700">{ev.event_type.replace(/_/g, ' ')}</span>
                        <span className="text-xs text-slate-400">
                          {ev.created_at ? new Date(ev.created_at).toLocaleString('es') : ''}
                        </span>
                      </div>
                      {ev.performed_by && <p className="text-xs text-slate-400 mt-0.5">por {ev.performed_by}</p>}
                      {ev.data && Object.keys(ev.data).length > 0 && (
                        <pre className="mt-1 text-xs text-slate-500 bg-slate-50 rounded-lg p-2 overflow-x-auto">
                          {JSON.stringify(ev.data, null, 2)}
                        </pre>
                      )}
                    </div>
                  </div>
                )
              })}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
