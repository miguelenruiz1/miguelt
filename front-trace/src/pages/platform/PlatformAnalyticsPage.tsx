import { useState } from 'react'
import { Link } from 'react-router-dom'
import {
  ArrowLeft, Activity, TrendingUp, DollarSign, Layers, Building2,
} from 'lucide-react'
import {
  LineChart, Line, BarChart, Bar, PieChart, Pie, Cell,
  ResponsiveContainer, XAxis, YAxis, CartesianGrid, Tooltip, Legend,
} from 'recharts'
import { usePlatformAnalytics } from '@/hooks/usePlatform'

const STATUS_COLORS: Record<string, string> = {
  active: '#22c55e',
  trialing: '#3b82f6',
  past_due: '#f59e0b',
  canceled: '#ef4444',
  expired: '#6b7280',
}

const STATUS_LABELS: Record<string, string> = {
  active: 'Activas',
  trialing: 'Prueba',
  past_due: 'Mora',
  canceled: 'Canceladas',
  expired: 'Expiradas',
}

export function PlatformAnalyticsPage() {
  const [months, setMonths] = useState(6)
  const { data, isLoading } = usePlatformAnalytics(months)

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600" />
      </div>
    )
  }
  if (!data) return null

  const pieData = data.status_distribution.map(d => ({
    name: STATUS_LABELS[d.status] ?? d.status,
    value: d.count,
    color: STATUS_COLORS[d.status] ?? '#6b7280',
  }))

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <Link to="/platform" className="inline-flex items-center gap-1 text-sm text-slate-500 hover:text-indigo-600 mb-2">
            <ArrowLeft className="h-4 w-4" /> Panel
          </Link>
          <h1 className="text-2xl font-bold text-slate-900">Analitica de Plataforma</h1>
          <p className="text-sm text-slate-500 mt-1">Tendencias, crecimiento y adopcion de modulos.</p>
        </div>
        <select
          value={months}
          onChange={e => setMonths(Number(e.target.value))}
          className="px-3 py-2 text-sm bg-white border border-slate-200 rounded-xl"
        >
          <option value={3}>3 meses</option>
          <option value={6}>6 meses</option>
          <option value={12}>12 meses</option>
        </select>
      </div>

      {/* Subscription Growth */}
      <div className="bg-white rounded-2xl border border-slate-200/60 p-6 shadow-sm">
        <h3 className="text-sm font-semibold text-slate-700 mb-4 flex items-center gap-2">
          <TrendingUp className="h-4 w-4 text-indigo-500" /> Crecimiento de Suscripciones
        </h3>
        <ResponsiveContainer width="100%" height={280}>
          <LineChart data={data.subscription_growth}>
            <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
            <XAxis dataKey="month" tick={{ fontSize: 12 }} />
            <YAxis tick={{ fontSize: 12 }} />
            <Tooltip />
            <Line
              type="monotone"
              dataKey="total_subscriptions"
              stroke="#6366f1"
              strokeWidth={2.5}
              dot={{ r: 4, fill: '#6366f1' }}
              name="Total Suscripciones"
            />
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* Revenue Trend */}
      <div className="bg-white rounded-2xl border border-slate-200/60 p-6 shadow-sm">
        <h3 className="text-sm font-semibold text-slate-700 mb-4 flex items-center gap-2">
          <DollarSign className="h-4 w-4 text-emerald-500" /> Ingresos Mensuales
        </h3>
        <ResponsiveContainer width="100%" height={280}>
          <BarChart data={data.revenue_trend}>
            <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
            <XAxis dataKey="month" tick={{ fontSize: 12 }} />
            <YAxis tick={{ fontSize: 12 }} tickFormatter={v => `$${v}`} />
            <Tooltip formatter={(v: number) => `$${v.toLocaleString()}`} />
            <Bar dataKey="revenue" fill="#10b981" radius={[6, 6, 0, 0]} name="Ingresos" />
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Row: Status distribution + Module adoption */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Status pie */}
        <div className="bg-white rounded-2xl border border-slate-200/60 p-6 shadow-sm">
          <h3 className="text-sm font-semibold text-slate-700 mb-4 flex items-center gap-2">
            <Building2 className="h-4 w-4 text-indigo-500" /> Distribucion por Estado
          </h3>
          {pieData.length > 0 ? (
            <div className="flex items-center gap-6">
              <ResponsiveContainer width="55%" height={200}>
                <PieChart>
                  <Pie data={pieData} dataKey="value" cx="50%" cy="50%" outerRadius={80} innerRadius={45}>
                    {pieData.map((entry, i) => (
                      <Cell key={i} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip />
                </PieChart>
              </ResponsiveContainer>
              <div className="space-y-2">
                {pieData.map(d => (
                  <div key={d.name} className="flex items-center gap-2 text-sm">
                    <span className="h-3 w-3 rounded-full shrink-0" style={{ backgroundColor: d.color }} />
                    <span className="text-slate-600">{d.name}</span>
                    <span className="font-semibold text-slate-900 ml-auto">{d.value}</span>
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <p className="text-sm text-slate-400">Sin datos</p>
          )}
        </div>

        {/* Module adoption */}
        <div className="bg-white rounded-2xl border border-slate-200/60 p-6 shadow-sm">
          <h3 className="text-sm font-semibold text-slate-700 mb-4 flex items-center gap-2">
            <Layers className="h-4 w-4 text-orange-500" /> Adopcion de Modulos
          </h3>
          {data.module_adoption.length > 0 ? (
            <div className="space-y-4">
              {data.module_adoption.map(m => {
                const pct = m.total > 0 ? Math.round((m.active / m.total) * 100) : 0
                return (
                  <div key={m.slug}>
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-sm font-medium text-slate-700 capitalize">{m.slug}</span>
                      <span className="text-sm text-slate-500">
                        {m.active} activos / {m.total} total ({pct}%)
                      </span>
                    </div>
                    <div className="h-3 bg-slate-100 rounded-full overflow-hidden">
                      <div
                        className="h-full bg-indigo-500 rounded-full transition-all"
                        style={{ width: `${pct}%` }}
                      />
                    </div>
                  </div>
                )
              })}
            </div>
          ) : (
            <p className="text-sm text-slate-400">Sin datos de modulos</p>
          )}
        </div>
      </div>

      {/* Recent events */}
      <div className="bg-white rounded-2xl border border-slate-200/60 p-6 shadow-sm">
        <h3 className="text-sm font-semibold text-slate-700 mb-4 flex items-center gap-2">
          <Activity className="h-4 w-4 text-slate-500" /> Eventos Recientes
        </h3>
        {data.recent_events.length === 0 ? (
          <p className="text-sm text-slate-400">Sin eventos recientes</p>
        ) : (
          <div className="divide-y divide-slate-100">
            {data.recent_events.map(ev => (
              <div key={ev.id} className="py-3 flex items-center gap-4">
                <div className="h-8 w-8 rounded-full bg-slate-100 flex items-center justify-center shrink-0">
                  <Activity className="h-4 w-4 text-slate-500" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium text-slate-700">{ev.event_type.replace(/_/g, ' ')}</span>
                    <Link
                      to={`/platform/tenants/${encodeURIComponent(ev.tenant_id)}`}
                      className="text-xs text-indigo-600 hover:underline"
                    >
                      {ev.tenant_id}
                    </Link>
                  </div>
                  <span className="text-xs text-slate-400">
                    {ev.created_at ? new Date(ev.created_at).toLocaleString('es') : ''}
                    {ev.performed_by ? ` - por ${ev.performed_by}` : ''}
                  </span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
