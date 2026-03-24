import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import {
  ArrowLeft, Building2, CheckCircle2, Layers, CreditCard, Plus,
} from 'lucide-react'
import { useOnboardTenant } from '@/hooks/usePlatform'
import { useQuery } from '@tanstack/react-query'
import { subscriptionApi } from '@/lib/subscription-api'
import { cn } from '@/lib/utils'

const AVAILABLE_MODULES = ['logistics', 'inventory']

export function PlatformOnboardPage() {
  const navigate = useNavigate()
  const onboard = useOnboardTenant()

  const [tenantId, setTenantId] = useState('')
  const [planSlug, setPlanSlug] = useState('free')
  const [billingCycle, setBillingCycle] = useState('monthly')
  const [modules, setModules] = useState<string[]>([])
  const [notes, setNotes] = useState('')

  const { data: plans } = useQuery({
    queryKey: ['plans'],
    queryFn: () => subscriptionApi.plans.list(),
    staleTime: 60_000,
  })

  const activePlans = (plans ?? []).filter(p => p.is_active && !p.is_archived)

  const toggleModule = (slug: string) => {
    setModules(prev => prev.includes(slug) ? prev.filter(m => m !== slug) : [...prev, slug])
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!tenantId.trim()) return

    try {
      await onboard.mutateAsync({
        tenant_id: tenantId.trim(),
        plan_slug: planSlug,
        billing_cycle: billingCycle,
        modules,
        notes: notes || undefined,
      })
      navigate(`/platform/tenants/${encodeURIComponent(tenantId.trim())}`)
    } catch {
      // error handled by mutation
    }
  }

  return (
    <div className="space-y-6 max-w-2xl">
      <div>
        <Link to="/platform/tenants" className="inline-flex items-center gap-1 text-sm text-slate-500 hover:text-primary mb-2">
          <ArrowLeft className="h-4 w-4" /> Empresas
        </Link>
        <h1 className="text-2xl font-bold text-slate-900">Onboarding de Empresa</h1>
        <p className="text-sm text-slate-500 mt-1">
          Registra una nueva empresa, asignale un plan y activa sus modulos.
        </p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Tenant ID */}
        <div className="bg-white rounded-2xl border border-slate-200/60 p-6 shadow-sm space-y-4">
          <h3 className="text-sm font-semibold text-slate-700 flex items-center gap-2">
            <Building2 className="h-4 w-4 text-primary" /> Datos de la Empresa
          </h3>
          <div>
            <label className="block text-sm font-medium text-slate-600 mb-1">Tenant ID / Slug</label>
            <input
              type="text"
              value={tenantId}
              onChange={e => setTenantId(e.target.value)}
              placeholder="ej: empresa-abc"
              required
              className="w-full px-3 py-2.5 text-sm bg-white border border-slate-200 rounded-xl focus:ring-2 focus:ring-ring/20 focus:border-ring outline-none"
            />
            <p className="text-xs text-slate-400 mt-1">Identificador unico de la empresa en el sistema</p>
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-600 mb-1">Notas (opcional)</label>
            <textarea
              value={notes}
              onChange={e => setNotes(e.target.value)}
              placeholder="Sector, contacto, observaciones..."
              rows={2}
              className="w-full px-3 py-2.5 text-sm bg-white border border-slate-200 rounded-xl focus:ring-2 focus:ring-ring/20 focus:border-ring outline-none resize-none"
            />
          </div>
        </div>

        {/* Plan selection */}
        <div className="bg-white rounded-2xl border border-slate-200/60 p-6 shadow-sm space-y-4">
          <h3 className="text-sm font-semibold text-slate-700 flex items-center gap-2">
            <CreditCard className="h-4 w-4 text-primary" /> Plan de Suscripcion
          </h3>
          <div className="grid grid-cols-2 gap-3">
            {activePlans.map(p => (
              <button
                key={p.slug}
                type="button"
                onClick={() => setPlanSlug(p.slug)}
                className={cn(
                  'text-left rounded-xl border-2 p-4 transition',
                  planSlug === p.slug
                    ? 'border-primary bg-primary/5 ring-1 ring-ring/30'
                    : 'border-slate-200 hover:border-slate-300',
                )}
              >
                <div className="text-sm font-semibold text-slate-900">{p.name}</div>
                <div className="text-lg font-bold text-primary mt-1">
                  {p.price_monthly > 0 ? `$${p.price_monthly}/mes` : 'Gratis'}
                </div>
                <div className="text-xs text-slate-400 mt-1">
                  {p.max_users} usuarios, {p.max_assets} assets
                </div>
                {planSlug === p.slug && (
                  <CheckCircle2 className="h-5 w-5 text-primary mt-2" />
                )}
              </button>
            ))}
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-600 mb-1">Ciclo de Facturacion</label>
            <div className="flex gap-2">
              {(['monthly', 'annual'] as const).map(c => (
                <button
                  key={c}
                  type="button"
                  onClick={() => setBillingCycle(c)}
                  className={cn(
                    'px-4 py-2 text-sm rounded-xl border-2 font-medium transition',
                    billingCycle === c
                      ? 'border-primary bg-primary/10 text-primary'
                      : 'border-slate-200 text-slate-600 hover:border-slate-300',
                  )}
                >
                  {c === 'monthly' ? 'Mensual' : 'Anual'}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Module selection */}
        <div className="bg-white rounded-2xl border border-slate-200/60 p-6 shadow-sm space-y-4">
          <h3 className="text-sm font-semibold text-slate-700 flex items-center gap-2">
            <Layers className="h-4 w-4 text-primary" /> Modulos a Activar
          </h3>
          <div className="flex gap-3">
            {AVAILABLE_MODULES.map(m => (
              <button
                key={m}
                type="button"
                onClick={() => toggleModule(m)}
                className={cn(
                  'flex items-center gap-2 px-4 py-3 rounded-xl border-2 text-sm font-medium transition',
                  modules.includes(m)
                    ? 'border-primary bg-primary/10 text-primary'
                    : 'border-slate-200 text-slate-600 hover:border-slate-300',
                )}
              >
                {modules.includes(m) ? (
                  <CheckCircle2 className="h-4 w-4 text-primary" />
                ) : (
                  <Plus className="h-4 w-4 text-slate-400" />
                )}
                <span className="capitalize">{m}</span>
              </button>
            ))}
          </div>
        </div>

        {/* Submit */}
        <div className="flex items-center gap-3">
          <button
            type="submit"
            disabled={!tenantId.trim() || onboard.isPending}
            className="flex items-center gap-2 px-6 py-3 text-sm font-semibold text-white bg-primary hover:bg-primary/90 rounded-xl disabled:opacity-50 transition"
          >
            {onboard.isPending ? (
              <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white" />
            ) : (
              <Building2 className="h-4 w-4" />
            )}
            Registrar Empresa
          </button>
          {onboard.isError && (
            <p className="text-sm text-red-600">{(onboard.error as Error).message}</p>
          )}
          {onboard.isSuccess && (
            <p className="text-sm text-emerald-600 flex items-center gap-1">
              <CheckCircle2 className="h-4 w-4" /> Empresa registrada exitosamente
            </p>
          )}
        </div>
      </form>
    </div>
  )
}
