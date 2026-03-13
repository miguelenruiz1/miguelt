import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  CreditCard, Search, TrendingUp, Users, AlertTriangle,
  Plus, XCircle, RefreshCw,
} from 'lucide-react'
import { useMetrics, useSubscriptions, useCreateSubscription } from '@/hooks/useSubscriptions'
import { usePlans } from '@/hooks/usePlans'
import type { SubscriptionStatus, SubscriptionCreate } from '@/types/subscription'
import { cn } from '@/lib/utils'

// ─── Status Badge ─────────────────────────────────────────────────────────────

const STATUS_COLORS: Record<SubscriptionStatus, string> = {
  active:   'bg-emerald-100 text-emerald-700',
  trialing: 'bg-amber-100 text-amber-700',
  past_due: 'bg-red-100 text-red-700',
  canceled: 'bg-slate-100 text-slate-500',
  expired:  'bg-red-50 text-red-400',
}

function StatusBadge({ status }: { status: SubscriptionStatus }) {
  return (
    <span className={cn('inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold', STATUS_COLORS[status])}>
      {status}
    </span>
  )
}

// ─── KPI Card ─────────────────────────────────────────────────────────────────

function KpiCard({
  label,
  value,
  color,
  prefix = '',
  suffix = '',
}: {
  label: string
  value: number
  color: string
  prefix?: string
  suffix?: string
}) {
  return (
    <div className={cn('rounded-2xl p-5 shadow-sm border', color)}>
      <p className="text-xs font-semibold uppercase tracking-wider opacity-70">{label}</p>
      <p className="mt-2 text-3xl font-bold">
        {prefix}{typeof value === 'number' && !Number.isInteger(value)
          ? value.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
          : value.toLocaleString()}{suffix}
      </p>
    </div>
  )
}

// ─── Create Subscription Modal ────────────────────────────────────────────────

function CreateSubModal({ onClose }: { onClose: () => void }) {
  const { data: plans = [] } = usePlans()
  const create = useCreateSubscription()
  const [form, setForm] = useState<SubscriptionCreate>({ tenant_id: '', plan_slug: 'free' })

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    await create.mutateAsync(form)
    onClose()
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 backdrop-blur-sm">
      <div className="bg-white rounded-2xl shadow-xl p-6 w-full max-w-md">
        <h2 className="text-lg font-bold text-slate-800 mb-4">Nueva Suscripción</h2>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Tenant ID</label>
            <input
              required
              value={form.tenant_id}
              onChange={e => setForm(f => ({ ...f, tenant_id: e.target.value }))}
              className="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400"
              placeholder="default"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Plan</label>
            <select
              value={form.plan_slug}
              onChange={e => setForm(f => ({ ...f, plan_slug: e.target.value }))}
              className="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400"
            >
              {plans.map(p => (
                <option key={p.id} value={p.slug}>{p.name}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Ciclo de facturación</label>
            <select
              value={form.billing_cycle ?? 'monthly'}
              onChange={e => setForm(f => ({ ...f, billing_cycle: e.target.value as 'monthly' | 'annual' | 'custom' }))}
              className="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400"
            >
              <option value="monthly">Mensual</option>
              <option value="annual">Anual</option>
            </select>
          </div>
          <div className="flex justify-end gap-3 pt-2">
            <button type="button" onClick={onClose} className="rounded-xl px-4 py-2 text-sm text-slate-600 hover:bg-slate-100">
              Cancelar
            </button>
            <button
              type="submit"
              disabled={create.isPending}
              className="rounded-xl bg-indigo-600 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-700 disabled:opacity-50"
            >
              {create.isPending ? 'Creando...' : 'Crear'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

// ─── Main Page ────────────────────────────────────────────────────────────────

export function SubscriptionsPage() {
  const navigate = useNavigate()
  const [statusFilter, setStatusFilter] = useState('')
  const [planFilter, setPlanFilter] = useState('')
  const [tenantSearch, setTenantSearch] = useState('')
  const [showModal, setShowModal] = useState(false)

  const { data: metrics } = useMetrics()
  const { data: plans = [] } = usePlans()
  const { data: subs, isLoading } = useSubscriptions({
    status: statusFilter || undefined,
    plan_id: planFilter || undefined,
    tenant_id: tenantSearch || undefined,
  })

  return (
    <div className="p-8 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-indigo-100">
            <CreditCard className="h-5 w-5 text-indigo-600" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-slate-900">Suscripciones</h1>
            <p className="text-sm text-slate-500">Dashboard global SaaS</p>
          </div>
        </div>
        <button
          onClick={() => setShowModal(true)}
          className="flex items-center gap-2 rounded-xl bg-indigo-600 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-700 shadow-sm"
        >
          <Plus className="h-4 w-4" /> Nueva Suscripción
        </button>
      </div>

      {/* KPI Cards */}
      {metrics && (
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
          <KpiCard label="MRR"               value={metrics.mrr}                color="bg-green-50 border-green-200 text-green-800"   prefix="$" />
          <KpiCard label="ARR"               value={metrics.arr}                color="bg-emerald-50 border-emerald-200 text-emerald-800" prefix="$" />
          <KpiCard label="Activas"           value={metrics.active}             color="bg-blue-50 border-blue-200 text-blue-800" />
          <KpiCard label="Trialing"          value={metrics.trialing}           color="bg-amber-50 border-amber-200 text-amber-800" />
          <KpiCard label="Vencidas"          value={metrics.past_due}           color="bg-red-50 border-red-200 text-red-800" />
          <KpiCard label="Nuevas este mes"   value={metrics.new_this_month}     color="bg-purple-50 border-purple-200 text-purple-800" />
        </div>
      )}

      {/* Plan Breakdown */}
      {metrics?.plan_breakdown && metrics.plan_breakdown.length > 0 && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {metrics.plan_breakdown.map(p => (
            <div key={p.slug} className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
              <p className="text-xs font-bold uppercase tracking-wider text-slate-400">{p.name}</p>
              <p className="mt-1 text-2xl font-bold text-slate-800">{p.count}</p>
              <p className="text-xs text-slate-500 mt-1">${p.mrr.toLocaleString('en-US', { maximumFractionDigits: 0 })} MRR</p>
            </div>
          ))}
        </div>
      )}

      {/* Filters */}
      <div className="flex gap-3 flex-wrap bg-white rounded-2xl border border-slate-100 p-4 shadow-sm">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
          <input
            value={tenantSearch}
            onChange={e => setTenantSearch(e.target.value)}
            placeholder="Buscar tenant..."
            className="rounded-xl border border-slate-200 bg-slate-50 pl-9 pr-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400 w-48"
          />
        </div>
        <select
          value={statusFilter}
          onChange={e => setStatusFilter(e.target.value)}
          className="rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400"
        >
          <option value="">Todos los estados</option>
          <option value="active">Active</option>
          <option value="trialing">Trialing</option>
          <option value="past_due">Past due</option>
          <option value="canceled">Canceled</option>
          <option value="expired">Expired</option>
        </select>
        <select
          value={planFilter}
          onChange={e => setPlanFilter(e.target.value)}
          className="rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400"
        >
          <option value="">Todos los planes</option>
          {plans.map(p => (
            <option key={p.id} value={p.id}>{p.name}</option>
          ))}
        </select>
      </div>

      {/* Table */}
      <div className="rounded-2xl border border-slate-100 bg-white shadow-sm overflow-hidden">
        {isLoading ? (
          <div className="flex items-center justify-center h-40 text-slate-400 text-sm">Cargando...</div>
        ) : (<>
          {/* Mobile cards */}
          <div className="space-y-3 p-4 md:hidden">
            {(subs?.items ?? []).length === 0 ? (
              <div className="py-10 text-center text-slate-400 text-sm">No hay suscripciones</div>
            ) : (
              (subs?.items ?? []).map(sub => (
                <div
                  key={sub.id}
                  className="rounded-xl border border-gray-200 bg-white p-4 shadow-sm space-y-2 cursor-pointer hover:border-indigo-200 hover:shadow-md transition-all"
                  onClick={() => navigate(`/platform/subscriptions/${sub.tenant_id}`)}
                >
                  <div className="flex items-center justify-between">
                    <span className="font-mono text-xs text-slate-700 truncate">{sub.tenant_id}</span>
                    <StatusBadge status={sub.status} />
                  </div>
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-slate-500">Plan</span>
                    <span className="rounded-lg bg-indigo-100 px-2 py-0.5 text-xs font-semibold text-indigo-700">
                      {sub.plan.name}
                    </span>
                  </div>
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-slate-500">Período</span>
                    <span className="text-slate-600">
                      {new Date(sub.current_period_start).toLocaleDateString()} – {new Date(sub.current_period_end).toLocaleDateString()}
                    </span>
                  </div>
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-slate-500">Ciclo</span>
                    <span className="text-slate-600 capitalize">{sub.billing_cycle}</span>
                  </div>
                </div>
              ))
            )}
          </div>

          {/* Desktop table */}
          <div className="hidden md:block">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-100 bg-slate-50">
                <th className="px-4 py-3 text-left font-semibold text-slate-500">Tenant</th>
                <th className="px-4 py-3 text-left font-semibold text-slate-500">Plan</th>
                <th className="px-4 py-3 text-left font-semibold text-slate-500">Estado</th>
                <th className="px-4 py-3 text-left font-semibold text-slate-500">Período</th>
                <th className="px-4 py-3 text-left font-semibold text-slate-500">Ciclo</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-50">
              {(subs?.items ?? []).map(sub => (
                <tr
                  key={sub.id}
                  className="hover:bg-indigo-50/40 cursor-pointer transition-colors"
                  onClick={() => navigate(`/platform/subscriptions/${sub.tenant_id}`)}
                >
                  <td className="px-4 py-3 font-mono text-xs text-slate-700">{sub.tenant_id}</td>
                  <td className="px-4 py-3">
                    <span className="rounded-lg bg-indigo-100 px-2 py-0.5 text-xs font-semibold text-indigo-700">
                      {sub.plan.name}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <StatusBadge status={sub.status} />
                  </td>
                  <td className="px-4 py-3 text-xs text-slate-500">
                    {new Date(sub.current_period_start).toLocaleDateString()} –{' '}
                    {new Date(sub.current_period_end).toLocaleDateString()}
                  </td>
                  <td className="px-4 py-3 text-xs text-slate-500 capitalize">{sub.billing_cycle}</td>
                </tr>
              ))}
              {(subs?.items ?? []).length === 0 && (
                <tr>
                  <td colSpan={5} className="px-4 py-10 text-center text-slate-400 text-sm">
                    No hay suscripciones
                  </td>
                </tr>
              )}
            </tbody>
          </table>
          </div>
        </>)}
      </div>

      {showModal && <CreateSubModal onClose={() => setShowModal(false)} />}
    </div>
  )
}
