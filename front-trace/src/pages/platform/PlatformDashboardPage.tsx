import { Link } from 'react-router-dom'
import {
  Building2, TrendingUp, TrendingDown, DollarSign, Users, CreditCard,
  Layers, Activity, ArrowRight, AlertTriangle, ChevronRight,
} from 'lucide-react'
import { usePlatformDashboard } from '@/hooks/usePlatform'
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip, BarChart, Bar, XAxis, YAxis, CartesianGrid } from 'recharts'

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

function KpiCard({
  label,
  value,
  icon: Icon,
  color,
  subtext,
}: {
  label: string
  value: string | number
  icon: React.ElementType
  color: string
  subtext?: string
}) {
  return (
    <div className="rounded-2xl border border-border bg-card p-5 ">
      <div className="flex items-center justify-between mb-3">
        <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">{label}</span>
        <div className={`h-9 w-9 rounded-xl flex items-center justify-center ${color}`}>
          <Icon className="h-4.5 w-4.5 text-white" />
        </div>
      </div>
      <div className="text-2xl font-bold text-foreground">{value}</div>
      {subtext && <p className="text-xs text-muted-foreground mt-1">{subtext}</p>}
    </div>
  )
}

export function PlatformDashboardPage() {
  const { data, isLoading } = usePlatformDashboard()

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
      </div>
    )
  }

  if (!data) return null

  const revDelta = data.revenue_last_month > 0
    ? ((data.revenue_this_month - data.revenue_last_month) / data.revenue_last_month * 100).toFixed(1)
    : null

  const pieData = [
    { name: 'Activas', value: data.active, color: STATUS_COLORS.active },
    { name: 'Prueba', value: data.trialing, color: STATUS_COLORS.trialing },
    { name: 'Mora', value: data.past_due, color: STATUS_COLORS.past_due },
    { name: 'Canceladas', value: data.canceled, color: STATUS_COLORS.canceled },
    { name: 'Expiradas', value: data.expired, color: STATUS_COLORS.expired },
  ].filter(d => d.value > 0)

  return (
    <div className="space-y-6">
      {/* Breadcrumb */}
      <nav className="mb-4">
        <ol className="flex items-center gap-2 text-sm">
          <li className="text-muted-foreground">Plataforma</li>
          <li><ChevronRight className="h-4 w-4 text-muted-foreground" /></li>
          <li className="text-primary">Panel Ejecutivo</li>
        </ol>
      </nav>

      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-foreground">Panel de Plataforma</h1>
          <p className="text-sm text-muted-foreground mt-1">Vision ejecutiva del negocio SaaS</p>
        </div>
        <div className="flex gap-2">
          <Link
            to="/platform/tenants"
            className="flex items-center gap-2 px-4 py-2 text-sm font-medium bg-primary/10 hover:bg-primary/15 text-primary rounded-lg transition"
          >
            <Building2 className="h-4 w-4" /> Empresas <ArrowRight className="h-3.5 w-3.5" />
          </Link>
          <Link
            to="/platform/analytics"
            className="flex items-center gap-2 px-4 py-2 text-sm font-medium bg-secondary hover:bg-gray-200 text-foreground rounded-lg transition"
          >
            <Activity className="h-4 w-4" /> Analitica
          </Link>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <KpiCard
          label="Empresas"
          value={data.total_tenants}
          icon={Building2}
          color="bg-primary"
          subtext={`${data.new_this_month} nuevas este mes`}
        />
        <KpiCard
          label="MRR"
          value={`$${data.mrr.toLocaleString('es-CO')}`}
          icon={DollarSign}
          color="bg-emerald-500"
          subtext={`ARR: $${data.arr.toLocaleString('es-CO')}`}
        />
        <KpiCard
          label="Ingreso del Mes"
          value={`$${data.revenue_this_month.toLocaleString('es-CO')}`}
          icon={CreditCard}
          color="bg-blue-500"
          subtext={revDelta ? `${Number(revDelta) >= 0 ? '+' : ''}${revDelta}% vs mes anterior` : undefined}
        />
        <KpiCard
          label="Churn Rate"
          value={`${data.churn_rate}%`}
          icon={data.churn_rate > 5 ? TrendingDown : TrendingUp}
          color={data.churn_rate > 5 ? 'bg-red-500' : 'bg-emerald-500'}
          subtext={`${data.canceled_this_month} canceladas este mes`}
        />
      </div>

      {/* Second row KPIs */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <KpiCard label="Suscripciones Activas" value={data.active} icon={Users} color="bg-green-500" />
        <KpiCard label="En Periodo de Prueba" value={data.trialing} icon={Activity} color="bg-blue-500" />
        <KpiCard label="Licencias Activas" value={data.active_licenses} icon={CreditCard} color="bg-purple-500" />
        <KpiCard label="Modulos Activados" value={data.active_modules} icon={Layers} color="bg-orange-500" />
      </div>

      {/* Charts row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Status distribution pie */}
        <div className="rounded-2xl border border-border bg-card p-6 ">
          <h3 className="text-sm font-medium text-foreground mb-4">Distribucion por Estado</h3>
          {pieData.length > 0 ? (
            <div className="flex items-center gap-6">
              <ResponsiveContainer width="50%" height={180}>
                <PieChart>
                  <Pie data={pieData} dataKey="value" cx="50%" cy="50%" outerRadius={70} innerRadius={40}>
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
                    <span className="h-3 w-3 rounded-full" style={{ backgroundColor: d.color }} />
                    <span className="text-muted-foreground">{d.name}</span>
                    <span className="font-semibold text-foreground ml-auto">{d.value}</span>
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <p className="text-sm text-muted-foreground">Sin datos</p>
          )}
        </div>

        {/* Plan breakdown bar */}
        <div className="rounded-2xl border border-border bg-card p-6 ">
          <h3 className="text-sm font-medium text-foreground mb-4">Distribucion por Plan</h3>
          {data.plan_breakdown.length > 0 ? (
            <ResponsiveContainer width="100%" height={180}>
              <BarChart data={data.plan_breakdown}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f3f4f6" />
                <XAxis dataKey="name" tick={{ fontSize: 12 }} />
                <YAxis tick={{ fontSize: 12 }} />
                <Tooltip />
                <Bar dataKey="count" fill="#6366f1" radius={[6, 6, 0, 0]} name="Suscripciones" />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <p className="text-sm text-muted-foreground">Sin datos</p>
          )}
        </div>
      </div>

      {/* Module adoption */}
      {data.module_adoption.length > 0 && (
        <div className="rounded-2xl border border-border bg-card p-6 ">
          <h3 className="text-sm font-medium text-foreground mb-4">Adopcion de Modulos</h3>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {data.module_adoption.map(m => (
              <div key={m.slug} className="bg-muted rounded-xl p-4">
                <div className="flex items-center gap-2 mb-2">
                  <Layers className="h-4 w-4 text-primary" />
                  <span className="text-sm font-semibold text-foreground capitalize">{m.slug}</span>
                </div>
                <div className="text-xl font-bold text-foreground">{m.active_tenants}</div>
                <p className="text-xs text-muted-foreground">empresas activas</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Alerts */}
      {data.past_due > 0 && (
        <div className="border-amber-200 bg-amber-50 border rounded-lg p-4 flex items-start gap-3">
          <AlertTriangle className="h-5 w-5 text-amber-600 mt-0.5 shrink-0" />
          <div>
            <p className="text-sm font-semibold text-amber-800">
              {data.past_due} {data.past_due === 1 ? 'empresa tiene' : 'empresas tienen'} pagos vencidos
            </p>
            <p className="text-xs text-amber-600 mt-0.5">Revisa las suscripciones en mora para tomar accion.</p>
          </div>
        </div>
      )}
    </div>
  )
}
