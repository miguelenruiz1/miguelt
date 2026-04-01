import { Factory, Clock, CheckCircle2, Play, Lock, XCircle, TrendingUp, DollarSign, BarChart3, Package } from 'lucide-react'
import { useProductionRuns } from '@/hooks/useInventory'
import type { ProductionRun, ProductionRunStatus } from '@/types/inventory'

const STATUS_CONFIG: Record<string, { label: string; color: string; icon: typeof Clock }> = {
  planned: { label: 'Planificadas', color: 'bg-secondary text-foreground', icon: Clock },
  released: { label: 'Liberadas', color: 'bg-blue-100 text-blue-700', icon: Play },
  in_progress: { label: 'En produccion', color: 'bg-amber-100 text-amber-700', icon: Factory },
  completed: { label: 'Completadas', color: 'bg-emerald-100 text-emerald-700', icon: CheckCircle2 },
  closed: { label: 'Cerradas', color: 'bg-secondary text-muted-foreground', icon: Lock },
  canceled: { label: 'Canceladas', color: 'bg-red-100 text-red-600', icon: XCircle },
}

function KpiCard({ icon: Icon, label, value, sub, color = 'text-indigo-600' }: {
  icon: typeof Factory; label: string; value: string; sub?: string; color?: string
}) {
  return (
    <div className="bg-card rounded-xl border p-5">
      <div className="flex items-center gap-3 mb-3">
        <div className="p-2 rounded-lg bg-muted"><Icon className={`h-5 w-5 ${color}`} /></div>
        <span className="text-sm font-medium text-muted-foreground">{label}</span>
      </div>
      <p className="text-2xl font-bold text-foreground">{value}</p>
      {sub && <p className="text-xs text-muted-foreground mt-1">{sub}</p>}
    </div>
  )
}

export default function ProductionDashboardPage() {
  const { data: allData } = useProductionRuns({ limit: 500 })
  const runs = allData?.items ?? []

  const byStatus = (s: string) => runs.filter(r => r.status === s).length
  const totalRuns = runs.length
  const activeRuns = runs.filter(r => ['planned', 'released', 'in_progress'].includes(r.status)).length
  const completedRuns = runs.filter(r => r.status === 'completed' || r.status === 'closed').length

  const totalCost = runs.reduce((sum, r) => sum + Number(r.total_production_cost ?? 0), 0)
  const avgCost = completedRuns > 0 ? totalCost / completedRuns : 0
  const totalOutput = runs.reduce((sum, r) => sum + Number(r.actual_output_quantity ?? 0), 0)
  const totalVariance = runs.filter(r => r.status === 'closed').reduce((sum, r) => sum + Number(r.variance_amount ?? 0), 0)

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <Factory className="h-6 w-6 text-foreground" />
        <div>
          <h1 className="text-2xl font-bold">Produccion</h1>
          <p className="text-sm text-muted-foreground">Panel de control del modulo de produccion</p>
        </div>
      </div>

      {/* KPIs */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <KpiCard icon={Factory} label="Ordenes activas" value={String(activeRuns)} sub={`${totalRuns} total`} color="text-amber-600" />
        <KpiCard icon={CheckCircle2} label="Completadas" value={String(completedRuns)} color="text-emerald-600" />
        <KpiCard icon={Package} label="Unidades producidas" value={totalOutput.toLocaleString('es-CO')} color="text-blue-600" />
        <KpiCard icon={DollarSign} label="Costo promedio" value={`$${avgCost.toLocaleString('es-CO', { minimumFractionDigits: 0 })}`} color="text-indigo-600" />
      </div>

      {/* Status breakdown */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-card rounded-xl border p-6">
          <h2 className="text-base font-semibold text-foreground mb-4 flex items-center gap-2">
            <BarChart3 className="h-5 w-5 text-indigo-600" /> Ordenes por Estado
          </h2>
          <div className="space-y-3">
            {Object.entries(STATUS_CONFIG).map(([status, cfg]) => {
              const count = byStatus(status)
              const pct = totalRuns > 0 ? (count / totalRuns) * 100 : 0
              const Icon = cfg.icon
              return (
                <div key={status} className="flex items-center gap-3">
                  <Icon className="h-4 w-4 text-muted-foreground shrink-0" />
                  <span className="w-28 text-xs text-muted-foreground">{cfg.label}</span>
                  <div className="flex-1 bg-secondary rounded-full h-2.5">
                    <div className={`${cfg.color.split(' ')[0]} h-2.5 rounded-full`} style={{ width: `${pct}%` }} />
                  </div>
                  <span className="w-8 text-right text-sm font-bold text-foreground">{count}</span>
                </div>
              )
            })}
          </div>
        </div>

        <div className="bg-card rounded-xl border p-6">
          <h2 className="text-base font-semibold text-foreground mb-4 flex items-center gap-2">
            <TrendingUp className="h-5 w-5 text-emerald-600" /> Indicadores
          </h2>
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <span className="text-sm text-muted-foreground">Tasa de completado</span>
              <span className="text-lg font-bold">{totalRuns > 0 ? ((completedRuns / totalRuns) * 100).toFixed(0) : 0}%</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-muted-foreground">Costo total produccion</span>
              <span className="text-lg font-bold">${totalCost.toLocaleString('es-CO')}</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-muted-foreground">Variacion total (cerradas)</span>
              <span className={`text-lg font-bold ${totalVariance === 0 ? 'text-emerald-600' : totalVariance > 0 ? 'text-red-600' : 'text-blue-600'}`}>
                ${totalVariance.toLocaleString('es-CO')}
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-muted-foreground">Unidades producidas</span>
              <span className="text-lg font-bold">{totalOutput.toLocaleString('es-CO')}</span>
            </div>
          </div>
        </div>
      </div>

      {/* Recent orders */}
      {runs.length > 0 && (
        <div className="bg-card rounded-xl border p-6">
          <h2 className="text-base font-semibold text-foreground mb-4">Ordenes recientes</h2>
          <div className="space-y-2">
            {runs.slice(0, 10).map(run => {
              const cfg = STATUS_CONFIG[run.status]
              const Icon = cfg?.icon ?? Clock
              return (
                <div key={run.id} className="flex items-center gap-3 text-sm py-2 border-b border-gray-50 last:border-0">
                  <span className="font-mono text-xs font-medium w-28">{run.run_number}</span>
                  <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold ${cfg?.color ?? ''}`}>
                    <Icon className="h-2.5 w-2.5" /> {cfg?.label ?? run.status}
                  </span>
                  <span className="text-muted-foreground text-xs flex-1">{run.order_type}</span>
                  <span className="text-muted-foreground text-xs">{new Date(run.created_at).toLocaleDateString('es-CO')}</span>
                </div>
              )
            })}
          </div>
        </div>
      )}
    </div>
  )
}
