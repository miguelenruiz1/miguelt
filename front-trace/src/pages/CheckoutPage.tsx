import { useState } from 'react'
import { useSearchParams, useNavigate } from 'react-router-dom'
import {
  CreditCard, CheckCircle2, AlertCircle, ArrowLeft, ShieldCheck, Zap,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { usePlans } from '@/hooks/usePlans'
import { useActiveGateway } from '@/hooks/usePayments'
import { useAuthStore } from '@/store/auth'


// Plan sort order for display
const PLAN_SORT: Record<string, number> = {
  free: 0, starter: 1, professional: 2, enterprise: 3,
}

const PLAN_COLORS: Record<string, string> = {
  free:         'from-slate-400 to-slate-500',
  starter:      'from-blue-500 to-blue-600',
  professional: 'from-indigo-500 to-purple-600',
  enterprise:   'from-slate-800 to-slate-900',
}

const PLAN_HIGHLIGHT: Record<string, boolean> = {
  professional: true,
}

// Module → which plans include it
const MODULE_MIN_PLAN: Record<string, string> = {
  logistics:  'free',
  inventory:  'starter',
  audit:      'starter',
  analytics:  'professional',
}

export function CheckoutPage() {
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const moduleSlug = searchParams.get('module') ?? ''

  const { data: plans = [], isLoading: plansLoading } = usePlans()
  const userTenantId = useAuthStore((s) => s.user?.tenant_id) ?? 'default'
  const { data: activeGateway, isLoading: gatewayLoading } = useActiveGateway(userTenantId)
  const user = useAuthStore((s) => s.user)

  const [selectedPlanId, setSelectedPlanId] = useState<string | null>(null)
  const [paymentDone, setPaymentDone] = useState(false)

  // Filter plans that include the module (sorted by price)
  const eligiblePlans = plans
    .filter((p) => !p.is_archived && p.is_active && p.modules.includes(moduleSlug))
    .sort((a, b) => (PLAN_SORT[a.slug] ?? 99) - (PLAN_SORT[b.slug] ?? 99))

  const selectedPlan = plans.find((p) => p.id === selectedPlanId) ?? eligiblePlans[0] ?? null

  const isLoading = plansLoading || gatewayLoading

  // ─── Payment submitted (mock — real integration via gateway SDK) ─────────────
  function handlePay() {
    if (!selectedPlan) return
    if (!activeGateway) return
    // In production: redirect to gateway hosted page or open SDK widget
    // For now: show success state
    setPaymentDone(true)
  }

  // ─── Success screen ───────────────────────────────────────────────────────────
  if (paymentDone) {
    return (
      <div className="flex items-center justify-center p-6">
        <div className="w-full max-w-md rounded-3xl bg-white shadow-2xl p-10 text-center space-y-6">
          <div className="flex justify-center">
            <div className="flex h-20 w-20 items-center justify-center rounded-full bg-emerald-50 ring-4 ring-emerald-100">
              <CheckCircle2 className="h-10 w-10 text-emerald-500" />
            </div>
          </div>
          <div>
            <h1 className="text-2xl font-bold text-slate-900">¡Pago procesado!</h1>
            <p className="mt-2 text-sm text-slate-500 leading-relaxed">
              Tu suscripción al plan <span className="font-semibold text-slate-700">{selectedPlan?.name}</span> está activa.
              Ahora tienes acceso completo a todos sus módulos.
            </p>
          </div>
          <button
            onClick={() => navigate('/marketplace')}
            className="w-full rounded-2xl bg-indigo-600 py-3 text-sm font-bold text-white hover:bg-indigo-700 transition-colors"
          >
            Ir al Marketplace
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="p-6">
      <div className="max-w-4xl mx-auto space-y-8">

        {/* Back */}
        <button
          onClick={() => navigate(-1)}
          className="flex items-center gap-2 text-sm font-semibold text-slate-500 hover:text-slate-800 transition-colors"
        >
          <ArrowLeft className="h-4 w-4" /> Volver
        </button>

        {/* Header */}
        <div className="text-center space-y-2">
          <div className="flex justify-center">
            <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-gradient-to-br from-indigo-500 to-purple-600 shadow-lg">
              <CreditCard className="h-7 w-7 text-white" />
            </div>
          </div>
          <h1 className="text-3xl font-bold text-slate-900">Completa tu suscripción</h1>
          {moduleSlug && (
            <p className="text-sm text-slate-500">
              Para usar el módulo <span className="font-semibold text-indigo-600 capitalize">{moduleSlug}</span> necesitas un plan que lo incluya
            </p>
          )}
        </div>

        {isLoading ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {[...Array(3)].map((_, i) => (
              <div key={i} className="h-52 rounded-3xl bg-white/60 animate-pulse" />
            ))}
          </div>
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">

            {/* ── Plan selection ─────────────────────────────────────────────── */}
            <div className="lg:col-span-2 space-y-4">
              <h2 className="text-sm font-bold text-slate-500 uppercase tracking-widest">Elige tu plan</h2>

              {eligiblePlans.length === 0 ? (
                <div className="rounded-3xl bg-white p-8 text-center shadow-sm">
                  <p className="text-slate-500 text-sm">No hay planes disponibles para este módulo.</p>
                </div>
              ) : (
                <div className="space-y-3">
                  {eligiblePlans.map((plan) => {
                    const isSelected = (selectedPlanId ?? eligiblePlans[0]?.id) === plan.id
                    const isHighlighted = PLAN_HIGHLIGHT[plan.slug]
                    const gradient = PLAN_COLORS[plan.slug] ?? 'from-slate-500 to-slate-600'

                    return (
                      <button
                        key={plan.id}
                        onClick={() => setSelectedPlanId(plan.id)}
                        className={cn(
                          'w-full text-left rounded-3xl border bg-white p-5 transition-all duration-200 shadow-sm',
                          isSelected
                            ? 'border-indigo-400 ring-2 ring-indigo-200 shadow-indigo-50'
                            : 'border-slate-200 hover:border-slate-300 hover:shadow-md',
                        )}
                      >
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-3">
                            <div className={cn(
                              'flex h-10 w-10 items-center justify-center rounded-2xl bg-gradient-to-br text-white text-sm font-bold shadow-sm',
                              gradient,
                            )}>
                              {plan.name[0]}
                            </div>
                            <div>
                              <div className="flex items-center gap-2">
                                <span className="font-bold text-slate-900">{plan.name}</span>
                                {isHighlighted && (
                                  <span className="rounded-full bg-indigo-100 px-2 py-0.5 text-[10px] font-bold text-indigo-700">
                                    Recomendado
                                  </span>
                                )}
                              </div>
                              <p className="text-xs text-slate-400">
                                Incluye: {plan.modules.join(', ')}
                              </p>
                            </div>
                          </div>
                          <div className="text-right">
                            {plan.price_monthly === 0 ? (
                              <span className="text-lg font-bold text-slate-900">Gratis</span>
                            ) : (
                              <>
                                <span className="text-lg font-bold text-slate-900">
                                  ${plan.price_monthly.toLocaleString()}
                                </span>
                                <span className="text-xs text-slate-400 block">{plan.currency}/mes</span>
                              </>
                            )}
                          </div>
                        </div>

                        {isSelected && (
                          <div className="mt-3 pt-3 border-t border-slate-100 grid grid-cols-3 gap-2 text-xs text-slate-500">
                            <span>👥 Hasta {plan.max_users} usuarios</span>
                            <span>📦 {plan.max_assets} activos</span>
                            <span>👛 {plan.max_wallets} custodios</span>
                          </div>
                        )}
                      </button>
                    )
                  })}
                </div>
              )}
            </div>

            {/* ── Order summary + Payment ─────────────────────────────────────── */}
            <div className="space-y-4">
              <h2 className="text-sm font-bold text-slate-500 uppercase tracking-widest">Resumen</h2>

              <div className="rounded-3xl bg-white shadow-sm border border-slate-200 overflow-hidden">
                {/* Plan summary */}
                <div className="p-5 space-y-3">
                  {selectedPlan ? (
                    <>
                      <div className="flex items-center justify-between">
                        <span className="text-sm text-slate-600">Plan {selectedPlan.name}</span>
                        <span className="font-bold text-slate-900">
                          {selectedPlan.price_monthly === 0
                            ? 'Gratis'
                            : `$${selectedPlan.price_monthly.toLocaleString()} ${selectedPlan.currency}`}
                        </span>
                      </div>
                      <div className="flex items-center justify-between text-xs text-slate-400">
                        <span>Facturación mensual</span>
                      </div>
                      <div className="border-t border-slate-100 pt-3 flex items-center justify-between">
                        <span className="font-semibold text-slate-800">Total / mes</span>
                        <span className="text-xl font-bold text-indigo-700">
                          {selectedPlan.price_monthly === 0
                            ? '$0'
                            : `$${selectedPlan.price_monthly.toLocaleString()}`}
                        </span>
                      </div>
                    </>
                  ) : (
                    <p className="text-sm text-slate-400">Selecciona un plan</p>
                  )}
                </div>

                {/* Payment method */}
                <div className="border-t border-slate-100 p-5 space-y-3">
                  <p className="text-xs font-bold text-slate-500 uppercase tracking-widest">Método de pago</p>

                  {gatewayLoading ? (
                    <div className="h-10 rounded-xl bg-slate-100 animate-pulse" />
                  ) : activeGateway ? (
                    <div className="flex items-center gap-3 rounded-2xl bg-slate-50 px-4 py-3">
                      <div
                        className="flex h-9 w-9 items-center justify-center rounded-xl text-white text-sm font-bold shrink-0"
                        style={{ backgroundColor: activeGateway.color }}
                      >
                        {activeGateway.display_name[0]}
                      </div>
                      <div className="min-w-0">
                        <p className="text-sm font-semibold text-slate-800">{activeGateway.display_name}</p>
                        <p className="text-[10px] text-slate-400">
                          {activeGateway.is_test_mode ? '⚡ Modo test' : '✅ Producción'}
                        </p>
                      </div>
                    </div>
                  ) : (
                    <div className="flex items-start gap-2 rounded-2xl bg-amber-50 border border-amber-200 px-4 py-3">
                      <AlertCircle className="h-4 w-4 text-amber-500 shrink-0 mt-0.5" />
                      <p className="text-xs text-amber-700 leading-relaxed">
                        No hay pasarela de pago configurada. Contacta al administrador.
                      </p>
                    </div>
                  )}
                </div>

                {/* Pay button */}
                <div className="px-5 pb-5">
                  <button
                    onClick={handlePay}
                    disabled={!selectedPlan || !activeGateway || selectedPlan.price_monthly === 0}
                    className={cn(
                      'w-full rounded-2xl py-3.5 text-sm font-bold text-white transition-all shadow-sm',
                      selectedPlan && activeGateway && selectedPlan.price_monthly > 0
                        ? 'bg-indigo-600 hover:bg-indigo-700 hover:shadow-md'
                        : 'bg-slate-300 cursor-not-allowed',
                    )}
                  >
                    {!activeGateway
                      ? 'Sin pasarela configurada'
                      : !selectedPlan
                        ? 'Selecciona un plan'
                        : selectedPlan.price_monthly === 0
                          ? 'Plan gratuito — sin cobro'
                          : (
                            <span className="flex items-center justify-center gap-2">
                              <Zap className="h-4 w-4" />
                              Pagar con {activeGateway.display_name}
                            </span>
                          )
                    }
                  </button>

                  {selectedPlan?.price_monthly === 0 && (
                    <button
                      onClick={() => navigate('/marketplace')}
                      className="mt-2 w-full rounded-2xl border border-slate-200 py-2.5 text-sm font-semibold text-slate-600 hover:bg-slate-50 transition-colors"
                    >
                      Continuar con plan gratuito
                    </button>
                  )}

                  <div className="mt-4 flex items-center justify-center gap-1.5 text-xs text-slate-400">
                    <ShieldCheck className="h-3.5 w-3.5" />
                    <span>Pago seguro procesado por {activeGateway?.display_name ?? 'pasarela'}</span>
                  </div>
                </div>
              </div>

              {/* User info */}
              {user && (
                <div className="rounded-2xl bg-white/70 border border-slate-200 px-4 py-3">
                  <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-1">Facturar a</p>
                  <p className="text-sm font-semibold text-slate-700">{user.full_name}</p>
                  <p className="text-xs text-slate-400">{user.email}</p>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
