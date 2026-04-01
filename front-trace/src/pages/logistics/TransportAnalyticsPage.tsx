import { useState } from 'react'
import { BarChart3, Clock, Truck, DollarSign, TrendingUp, Package } from 'lucide-react'
import { useTransportAnalytics } from '@/hooks/useLogistics'

const PERIOD_OPTIONS = [
  { value: 'day', label: 'Diario' },
  { value: 'week', label: 'Semanal' },
  { value: 'month', label: 'Mensual' },
]

const STATUS_LABELS: Record<string, string> = {
  draft: 'Borrador',
  issued: 'Emitido',
  in_transit: 'En Transito',
  delivered: 'Entregado',
  canceled: 'Cancelado',
}

const STATUS_COLORS: Record<string, string> = {
  draft: 'bg-gray-200',
  issued: 'bg-blue-400',
  in_transit: 'bg-yellow-400',
  delivered: 'bg-green-400',
  canceled: 'bg-red-400',
}

function KpiCard({ icon: Icon, label, value, sub, color = 'text-indigo-600' }: {
  icon: typeof BarChart3; label: string; value: string; sub?: string; color?: string
}) {
  return (
    <div className="bg-card rounded-xl border p-5">
      <div className="flex items-center gap-3 mb-3">
        <div className={`p-2 rounded-lg bg-muted`}><Icon className={`h-5 w-5 ${color}`} /></div>
        <span className="text-sm font-medium text-muted-foreground">{label}</span>
      </div>
      <p className="text-2xl font-bold text-foreground">{value}</p>
      {sub && <p className="text-xs text-muted-foreground mt-1">{sub}</p>}
    </div>
  )
}

export default function TransportAnalyticsPage() {
  const [period, setPeriod] = useState('month')
  const { data, isLoading } = useTransportAnalytics(period)

  const fmt = (n: number | null | undefined) => n != null ? n.toFixed(1) : '--'
  const fmtPct = (n: number | null | undefined) => n != null ? `${n.toFixed(0)}%` : '--'
  const fmtMoney = (n: number | null | undefined) => n != null ? `$${n.toLocaleString('es-CO', { minimumFractionDigits: 0 })}` : '--'

  const totalShipments = data ? Object.values(data.shipments_by_status).reduce((a, b) => a + b, 0) : 0
  const maxBarValue = data ? Math.max(...data.deliveries_by_period.map(d => d.count), 1) : 1
  const maxCarrierValue = data ? Math.max(...data.top_carriers.map(c => c.shipments), 1) : 1

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground">Analiticas de Transporte</h1>
          <p className="text-sm text-muted-foreground mt-1">Metricas operativas de envios, tiempos y costos logisticos</p>
        </div>
        <div className="flex gap-1 bg-secondary rounded-lg p-1">
          {PERIOD_OPTIONS.map(o => (
            <button
              key={o.value}
              onClick={() => setPeriod(o.value)}
              className={`px-3 py-1.5 text-xs font-medium rounded-md transition-colors ${
                period === o.value ? 'bg-card text-foreground ' : 'text-muted-foreground hover:text-foreground'
              }`}
            >
              {o.label}
            </button>
          ))}
        </div>
      </div>

      {isLoading ? (
        <div className="flex items-center justify-center py-20">
          <div className="h-8 w-8 border-4 border-indigo-200 border-t-indigo-600 rounded-full animate-spin" />
        </div>
      ) : !data ? (
        <div className="text-center py-20 text-muted-foreground">Sin datos de analiticas</div>
      ) : (
        <>
          {/* KPI Cards */}
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            <KpiCard icon={TrendingUp} label="Entregas a tiempo" value={fmtPct(data.on_time_delivery_pct)} color="text-green-600" />
            <KpiCard icon={Clock} label="Transito promedio" value={`${fmt(data.avg_transit_days)} dias`} color="text-blue-600" />
            <KpiCard icon={Package} label="Total envios" value={String(totalShipments)} color="text-indigo-600" />
            <KpiCard icon={BarChart3} label="Eventos / activo" value={fmt(data.avg_events_per_asset)} color="text-purple-600" />
          </div>

          {/* Cost Breakdown + Shipments by Status */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Costs */}
            <div className="bg-card rounded-xl border p-6">
              <div className="flex items-center gap-2 mb-4">
                <DollarSign className="h-5 w-5 text-emerald-600" />
                <h2 className="text-base font-semibold text-foreground">Costos Logisticos</h2>
              </div>
              <p className="text-3xl font-bold text-foreground mb-4">{fmtMoney(data.total_logistics_cost.total)}</p>
              <div className="space-y-3">
                {([
                  { key: 'freight', label: 'Flete', color: 'bg-blue-500' },
                  { key: 'insurance', label: 'Seguro', color: 'bg-green-500' },
                  { key: 'handling', label: 'Manejo', color: 'bg-yellow-500' },
                  { key: 'customs', label: 'Aduanas', color: 'bg-purple-500' },
                  { key: 'other', label: 'Otros', color: 'bg-gray-400' },
                ] as const).map(item => {
                  const val = data.total_logistics_cost[item.key]
                  const pct = data.total_logistics_cost.total > 0 ? (val / data.total_logistics_cost.total) * 100 : 0
                  return (
                    <div key={item.key} className="flex items-center gap-3">
                      <span className="w-20 text-xs text-muted-foreground">{item.label}</span>
                      <div className="flex-1 bg-secondary rounded-full h-2">
                        <div className={`${item.color} h-2 rounded-full`} style={{ width: `${pct}%` }} />
                      </div>
                      <span className="w-24 text-right text-xs font-medium text-foreground">{fmtMoney(val)}</span>
                    </div>
                  )
                })}
              </div>
            </div>

            {/* Shipments by Status */}
            <div className="bg-card rounded-xl border p-6">
              <div className="flex items-center gap-2 mb-4">
                <Truck className="h-5 w-5 text-indigo-600" />
                <h2 className="text-base font-semibold text-foreground">Envios por Estado</h2>
              </div>
              <div className="space-y-3">
                {Object.entries(data.shipments_by_status).map(([status, count]) => (
                  <div key={status} className="flex items-center gap-3">
                    <span className="w-24 text-xs text-muted-foreground">{STATUS_LABELS[status] ?? status}</span>
                    <div className="flex-1 bg-secondary rounded-full h-3">
                      <div
                        className={`${STATUS_COLORS[status] ?? 'bg-gray-300'} h-3 rounded-full transition-all`}
                        style={{ width: `${totalShipments > 0 ? (count / totalShipments) * 100 : 0}%` }}
                      />
                    </div>
                    <span className="w-8 text-right text-sm font-semibold text-foreground">{count}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Deliveries by Period + Top Carriers */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Deliveries Chart */}
            <div className="bg-card rounded-xl border p-6">
              <h2 className="text-base font-semibold text-foreground mb-4">Entregas por Periodo</h2>
              {data.deliveries_by_period.length === 0 ? (
                <p className="text-sm text-muted-foreground py-8 text-center">Sin entregas en este periodo</p>
              ) : (
                <div className="flex items-end gap-1 h-40">
                  {data.deliveries_by_period.map((d, i) => (
                    <div key={i} className="flex-1 flex flex-col items-center gap-1">
                      <span className="text-[10px] font-medium text-muted-foreground">{d.count}</span>
                      <div
                        className="w-full bg-indigo-400 rounded-t-sm min-h-[4px] transition-all"
                        style={{ height: `${(d.count / maxBarValue) * 100}%` }}
                      />
                      <span className="text-[9px] text-muted-foreground truncate w-full text-center">
                        {d.period.slice(5, 10)}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Top Carriers */}
            <div className="bg-card rounded-xl border p-6">
              <h2 className="text-base font-semibold text-foreground mb-4">Top Transportistas</h2>
              {data.top_carriers.length === 0 ? (
                <p className="text-sm text-muted-foreground py-8 text-center">Sin datos de transportistas</p>
              ) : (
                <div className="space-y-3">
                  {data.top_carriers.map((c, i) => (
                    <div key={i} className="flex items-center gap-3">
                      <span className="w-6 text-xs font-bold text-muted-foreground">#{i + 1}</span>
                      <span className="w-32 text-sm text-foreground truncate">{c.carrier}</span>
                      <div className="flex-1 bg-secondary rounded-full h-2.5">
                        <div
                          className="bg-indigo-500 h-2.5 rounded-full transition-all"
                          style={{ width: `${(c.shipments / maxCarrierValue) * 100}%` }}
                        />
                      </div>
                      <span className="w-8 text-right text-sm font-semibold text-foreground">{c.shipments}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </>
      )}
    </div>
  )
}
