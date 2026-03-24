import React, { useState, useMemo } from 'react'
import {
  TrendingUp,
  TrendingDown,
  Download,
  FileText,
  ChevronDown,
  ChevronRight,
  ChevronUp,
  DollarSign,
  Package,
  ArrowUpRight,
  ArrowDownRight,
  Flame,
  Info,
  AlertTriangle,
  Sparkles,
  RefreshCw,
  Star,
  Lightbulb,
  Target,
  Bell,
} from 'lucide-react'
import { usePnL, useDownloadPnLPdf, usePnLAnalysis } from '@/hooks/useInventory'
import { useQueryClient } from '@tanstack/react-query'
import { SegmentedControl } from '@/components/ui/tabs'
import { Badge } from '@/components/ui/badge'
import { cn } from '@/lib/utils'
import type { PnLReport, PnLProduct, StockByWarehouse, PnLAnalysis } from '@/types/inventory'

/* ── Helpers ─────────────────────────────────────────────────────────────────── */

function formatCOP(value: number): string {
  if (value < 0) return `-$${Math.abs(value).toLocaleString('es-CO', { maximumFractionDigits: 0 })}`
  return `$${value.toLocaleString('es-CO', { maximumFractionDigits: 0 })}`
}

function marginColor(margin: number, target: number): string {
  if (margin >= target) return 'text-emerald-700 bg-emerald-50'
  if (margin >= target * 0.6) return 'text-amber-700 bg-amber-50'
  return 'text-red-700 bg-red-50'
}

function pctChange(current: number, previous: number): number | null {
  if (previous === 0) return current === 0 ? null : null
  return ((current - previous) / Math.abs(previous)) * 100
}

function formatDate(d: Date): string {
  return d.toISOString().slice(0, 10)
}

/** Shift a date range backwards by its own duration to get the "previous period". */
function getPreviousPeriod(fromStr: string, toStr: string): { prevFrom: string; prevTo: string } {
  const from = new Date(fromStr)
  const to = new Date(toStr)
  const durationMs = to.getTime() - from.getTime()
  const prevTo = new Date(from.getTime() - 86_400_000) // day before current from
  const prevFrom = new Date(prevTo.getTime() - durationMs)
  return { prevFrom: formatDate(prevFrom), prevTo: formatDate(prevTo) }
}

function exportCsv(data: PnLReport) {
  const headers = [
    'Producto',
    'SKU',
    'Ingresos',
    'Costo',
    'Utilidad',
    'Margen %',
    'Margen Obj %',
    'Diferencia pp',
  ]
  const rows = data.products.map((p) => [
    p.product_name,
    p.product_sku,
    p.summary.total_revenue,
    p.summary.total_cogs,
    p.summary.gross_profit,
    p.summary.gross_margin_pct.toFixed(1),
    p.summary.margin_target.toFixed(1),
    p.summary.margin_vs_target.toFixed(1),
  ])
  const csv = [headers.join(','), ...rows.map((r) => r.join(','))].join('\n')
  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `rentabilidad-${new Date().toISOString().slice(0, 10)}.csv`
  a.click()
  URL.revokeObjectURL(url)
}

/* ── Comparison Badge ────────────────────────────────────────────────────────── */

function ComparisonBadge({ current, previous, label }: { current: number; previous: number; label: string }) {
  const change = pctChange(current, previous)
  if (change === null) return <span className="text-xs text-muted-foreground">Sin datos previos</span>
  const isPositive = change >= 0
  return (
    <span className={cn('inline-flex items-center gap-0.5 text-xs font-medium', isPositive ? 'text-emerald-600' : 'text-red-600')}>
      {isPositive ? <ArrowUpRight className="h-3 w-3" /> : <ArrowDownRight className="h-3 w-3" />}
      {isPositive ? '+' : ''}{change.toFixed(1)}% vs {label}
    </span>
  )
}

/* ── Star Product Badge ──────────────────────────────────────────────────────── */

function isStarProduct(w: StockByWarehouse, grossMargin: number): boolean {
  const lowStock = w.qty_available < 5 || (w.qty_on_hand > 0 && w.qty_available < w.qty_on_hand * 0.1)
  return lowStock && grossMargin > 25
}

/* ── Product Detail (expanded row) ───────────────────────────────────────────── */

function ProductDetail({ pnl }: { pnl: PnLProduct }) {
  const [tab, setTab] = useState<'result' | 'stock' | 'purchases' | 'sales'>('result')
  const s = pnl.summary
  const tabs = [
    { key: 'result' as const, label: 'Resultado' },
    { key: 'stock' as const, label: 'Donde esta' },
    { key: 'purchases' as const, label: 'Compras' },
    { key: 'sales' as const, label: 'Ventas' },
  ]

  const moneyLost =
    s.margin_vs_target < 0 ? s.total_revenue * Math.abs(s.margin_vs_target) / 100 : 0

  return (
    <div className="mt-3 rounded-lg border border-border bg-card p-5">
      <SegmentedControl
        options={tabs.map((t) => ({ value: t.key, label: t.label }))}
        value={tab}
        onChange={(k) => setTab(k as typeof tab)}
        className="mb-5"
      />

      {/* ── Resultado ──────────────────────────────────────────────────────── */}
      {tab === 'result' && (
        <div className="space-y-4">
          <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
            <div>
              <span className="text-xs text-muted-foreground">Ingresos</span>
              <p className="font-semibold">{formatCOP(s.total_revenue)}</p>
            </div>
            <div>
              <span className="text-xs text-muted-foreground">Costo real</span>
              <p className="font-semibold">{formatCOP(s.total_cogs)}</p>
            </div>
            <div>
              <span className="text-xs text-muted-foreground">Utilidad</span>
              <p className="text-lg font-bold">{formatCOP(s.gross_profit)}</p>
            </div>
            <div>
              <span className="text-xs text-muted-foreground">Margen logrado</span>
              <p className={cn('inline-block rounded px-2 py-0.5 font-semibold', marginColor(s.gross_margin_pct, s.margin_target))}>
                {s.gross_margin_pct.toFixed(1)}%
              </p>
            </div>
            <div>
              <span className="text-xs text-muted-foreground">Margen objetivo</span>
              <p>{s.margin_target.toFixed(1)}%</p>
            </div>
            <div>
              <span className="text-xs text-muted-foreground">Diferencia</span>
              <p className={s.margin_vs_target >= 0 ? 'text-emerald-600' : 'text-red-600'}>
                {s.margin_vs_target >= 0 ? '+' : ''}
                {s.margin_vs_target.toFixed(1)} puntos
              </p>
            </div>
          </div>

          {/* Suggestion card when margin below target */}
          {s.margin_vs_target < 0 && pnl.market_analysis.suggested_price_today > 0 && (
            <div className="flex items-start gap-3 rounded-lg border border-blue-200 bg-blue-50 p-4">
              <Info className="mt-0.5 h-5 w-5 shrink-0 text-blue-600" />
              <div>
                <p className="text-sm font-medium text-blue-800">Sugerencia</p>
                <p className="mt-0.5 text-sm text-blue-700">
                  Sube el precio a{' '}
                  <span className="font-bold">{formatCOP(pnl.market_analysis.suggested_price_today)}/{pnl.unit_of_measure}</span>{' '}
                  para alcanzar tu objetivo del {s.margin_target.toFixed(1)}%.
                </p>
                {moneyLost > 0 && (
                  <p className="mt-1 text-sm font-semibold text-red-600">
                    Fuga acumulada: -{formatCOP(moneyLost)}
                  </p>
                )}
              </div>
            </div>
          )}

          {/* Suggested price (when margin is on target or above) */}
          {s.margin_vs_target >= 0 && pnl.market_analysis.suggested_price_today > 0 && (
            <div className="col-span-full rounded-lg bg-emerald-50 p-3">
              <span className="text-xs font-medium text-emerald-600">Precio sugerido hoy</span>
              <p className="font-bold text-emerald-800">
                {formatCOP(pnl.market_analysis.suggested_price_today)}/{pnl.unit_of_measure}
              </p>
            </div>
          )}
        </div>
      )}

      {/* ── Donde esta ─────────────────────────────────────────────────────── */}
      {tab === 'stock' && (
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border bg-muted/50">
              <th className="p-2 text-left font-medium">Bodega</th>
              <th className="p-2 text-right font-medium">En mano</th>
              <th className="p-2 text-right font-medium">Reservado</th>
              <th className="p-2 text-right font-medium">Disponible</th>
              <th className="p-2 text-right font-medium">Valor</th>
              <th className="p-2 text-right font-medium"></th>
            </tr>
          </thead>
          <tbody>
            {pnl.stock_by_warehouse.map((w, i) => (
              <tr key={i} className="border-b border-border hover:bg-muted/30 transition-colors">
                <td className="p-2">{w.warehouse_name}</td>
                <td className="p-2 text-right">{w.qty_on_hand.toFixed(2)}</td>
                <td className="p-2 text-right">{w.qty_reserved.toFixed(2)}</td>
                <td className="p-2 text-right">{w.qty_available.toFixed(2)}</td>
                <td className="p-2 text-right">{formatCOP(w.total_value)}</td>
                <td className="p-2 text-right">
                  {isStarProduct(w, s.gross_margin_pct) && (
                    <span className="inline-flex items-center gap-1 rounded-full bg-orange-100 px-2 py-0.5 text-xs font-medium text-orange-700">
                      <Flame className="h-3 w-3" /> Reabastecer ya
                    </span>
                  )}
                </td>
              </tr>
            ))}
            {pnl.stock_by_warehouse.length === 0 && (
              <tr>
                <td colSpan={6} className="p-4 text-center text-muted-foreground">Sin stock registrado</td>
              </tr>
            )}
          </tbody>
        </table>
      )}

      {/* ── Compras ────────────────────────────────────────────────────────── */}
      {tab === 'purchases' && (
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border bg-muted/50">
              <th className="p-2 text-left font-medium">Fecha</th>
              <th className="p-2 text-left font-medium">Proveedor</th>
              <th className="p-2 text-right font-medium">Cantidad</th>
              <th className="p-2 text-right font-medium">Costo/UoM</th>
              <th className="p-2 text-right font-medium">Total</th>
            </tr>
          </thead>
          <tbody>
            {pnl.purchases.map((p, i) => (
              <tr key={i} className="border-b border-border hover:bg-muted/30 transition-colors">
                <td className="p-2">{new Date(p.received_at).toLocaleDateString('es-CO')}</td>
                <td className="p-2">{p.supplier_name}</td>
                <td className="p-2 text-right">
                  {p.qty_purchased.toFixed(2)} {p.uom_purchased}
                </td>
                <td className="p-2 text-right">{formatCOP(p.unit_cost_purchased)}</td>
                <td className="p-2 text-right">{formatCOP(p.total_cost)}</td>
              </tr>
            ))}
            {pnl.purchases.length === 0 && (
              <tr>
                <td colSpan={5} className="p-4 text-center text-muted-foreground">Sin compras en el periodo</td>
              </tr>
            )}
          </tbody>
        </table>
      )}

      {/* ── Ventas ─────────────────────────────────────────────────────────── */}
      {tab === 'sales' && (
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border bg-muted/50">
              <th className="p-2 text-left font-medium">OV</th>
              <th className="p-2 text-left font-medium">Fecha</th>
              <th className="p-2 text-right font-medium">Cantidad</th>
              <th className="p-2 text-right font-medium">Precio</th>
              <th className="p-2 text-right font-medium">Total</th>
              <th className="p-2 text-right font-medium">Margen</th>
            </tr>
          </thead>
          <tbody>
            {pnl.sales.map((sale, i) => (
              <tr key={i} className="border-b border-border hover:bg-muted/30 transition-colors">
                <td className="p-2 font-mono text-xs">{sale.order_number}</td>
                <td className="p-2">{new Date(sale.sale_date).toLocaleDateString('es-CO')}</td>
                <td className="p-2 text-right">{sale.qty_shipped.toFixed(2)}</td>
                <td className="p-2 text-right">{formatCOP(sale.unit_price)}</td>
                <td className="p-2 text-right">{formatCOP(sale.line_total)}</td>
                <td className="p-2 text-right">
                  {sale.margin_pct != null ? (
                    <span className={cn('inline-block rounded px-1.5 py-0.5 text-xs font-medium', marginColor(sale.margin_pct, s.margin_target))}>
                      {sale.margin_pct.toFixed(1)}%
                    </span>
                  ) : (
                    '—'
                  )}
                </td>
              </tr>
            ))}
            {pnl.sales.length === 0 && (
              <tr>
                <td colSpan={6} className="p-4 text-center text-muted-foreground">Sin ventas en el periodo</td>
              </tr>
            )}
          </tbody>
        </table>
      )}
    </div>
  )
}

/* ── Main Page ───────────────────────────────────────────────────────────────── */

/* ── AI Insights Panel ──────────────────────────────────────────────────────── */

const SEVERITY_STYLES = {
  alta: 'border-l-red-500 bg-red-50/50',
  media: 'border-l-amber-500 bg-amber-50/50',
  baja: 'border-l-blue-500 bg-blue-50/50',
} as const

const PRIORITY_BADGE = {
  alta: 'bg-red-100 text-red-700',
  media: 'bg-amber-100 text-amber-700',
  baja: 'bg-blue-100 text-blue-700',
} as const

function AiInsightsPanelInner({ dateFrom, dateTo }: { dateFrom: string; dateTo: string }) {
  const { data: analysis, isLoading, isError, error } = usePnLAnalysis(dateFrom, dateTo)
  const [expanded, setExpanded] = useState(true)
  const qc = useQueryClient()

  const errorStatus = isError ? (error as any)?.status : null
  const is501 = errorStatus === 501
  const is429 = errorStatus === 429
  const is503 = errorStatus === 503

  function handleRegenerate() {
    qc.removeQueries({ queryKey: ['inventory', 'pnl', 'analysis', dateFrom, dateTo] })
    qc.fetchQuery({
      queryKey: ['inventory', 'pnl', 'analysis', dateFrom, dateTo],
      queryFn: () => import('@/lib/inventory-api').then(m => m.inventoryPnLApi.getAiAnalysis(dateFrom, dateTo, true)),
    })
  }

  // State A/C: not configured or not purchased → hide completely
  if (is501) return null

  return (
    <div className="rounded-xl border border-border bg-card overflow-hidden">
      {/* Header */}
      <button
        onClick={() => setExpanded(v => !v)}
        className="w-full flex items-center justify-between px-5 py-3.5 hover:bg-muted/30 transition-colors"
      >
        <div className="flex items-center gap-2.5">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-violet-500 to-purple-600 shadow-sm">
            <Sparkles className="h-4 w-4 text-white" />
          </div>
          <div className="text-left">
            <h3 className="text-sm font-bold text-foreground">Analisis IA</h3>
            <p className="text-[10px] text-muted-foreground">Powered by Claude Haiku</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {!isLoading && analysis && (
            <button
              onClick={(e) => { e.stopPropagation(); handleRegenerate() }}
              className="p-1.5 rounded-lg text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
              title="Regenerar analisis"
            >
              <RefreshCw className="h-3.5 w-3.5" />
            </button>
          )}
          {expanded ? <ChevronUp className="h-4 w-4 text-muted-foreground" /> : <ChevronDown className="h-4 w-4 text-muted-foreground" />}
        </div>
      </button>

      {expanded && (
        <div className="border-t border-border px-5 py-4">
          {/* Last saved badge */}
          {analysis?.cache_source === 'last_saved' && analysis?.cached_at && (
            <div className="flex items-center justify-between mb-3 text-xs text-muted-foreground">
              <span>Analisis del {new Date(analysis.cached_at).toLocaleDateString('es-CO', { day: 'numeric', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' })}</span>
              <button onClick={(e) => { e.stopPropagation(); handleRegenerate() }} className="text-primary hover:underline font-medium">Actualizar</button>
            </div>
          )}

          {isLoading ? (
            <div className="space-y-3 animate-pulse">
              <div className="h-4 w-3/4 rounded bg-muted" />
              <div className="h-4 w-1/2 rounded bg-muted" />
              <div className="h-20 rounded-lg bg-muted" />
              <p className="text-xs text-muted-foreground text-center pt-1">Analizando rentabilidad...</p>
            </div>
          ) : is429 ? (
            <div className="flex items-center gap-3 p-4 bg-amber-50 border border-amber-200 rounded-lg">
              <AlertTriangle className="h-5 w-5 text-amber-500 shrink-0" />
              <div>
                <p className="text-sm font-medium text-amber-800">Limite diario alcanzado</p>
                <p className="text-xs text-amber-600 mt-0.5">El contador se reinicia a medianoche.</p>
              </div>
            </div>
          ) : is503 ? (
            <p className="text-sm text-muted-foreground py-4 text-center">Analisis IA temporalmente no disponible. Intenta mas tarde.</p>
          ) : isError ? (
            <p className="text-sm text-muted-foreground py-4 text-center">Analisis no disponible en este momento.</p>
          ) : analysis ? (
            <div className="space-y-5">
              {/* Resumen */}
              {analysis.resumen && (
                <div className="rounded-lg bg-violet-50/60 border border-violet-200/50 px-4 py-3">
                  <p className="text-sm text-slate-700 leading-relaxed">{analysis.resumen}</p>
                </div>
              )}

              {/* Alertas */}
              {(analysis.alertas?.length ?? 0) > 0 && (
                <div>
                  <h4 className="flex items-center gap-1.5 text-xs font-bold text-slate-500 uppercase tracking-wider mb-2">
                    <Bell className="h-3.5 w-3.5" /> Alertas
                  </h4>
                  <div className="space-y-2">
                    {(analysis.alertas ?? []).map((a, i) => (
                      <div key={i} className={cn('rounded-lg border-l-4 px-4 py-2.5', SEVERITY_STYLES[a.severidad])}>
                        <p className="text-sm font-semibold text-slate-800">{a.titulo}</p>
                        <p className="text-xs text-slate-600 mt-0.5">{a.detalle}</p>
                        {a.producto_sku && <span className="inline-block mt-1 text-[10px] font-mono bg-white/80 rounded px-1.5 py-0.5 text-slate-500">{a.producto_sku}</span>}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Oportunidades */}
              {(analysis.oportunidades?.length ?? 0) > 0 && (
                <div>
                  <h4 className="flex items-center gap-1.5 text-xs font-bold text-slate-500 uppercase tracking-wider mb-2">
                    <Lightbulb className="h-3.5 w-3.5" /> Oportunidades
                  </h4>
                  <div className="space-y-2">
                    {(analysis.oportunidades ?? []).map((o, i) => (
                      <div key={i} className="rounded-lg border-l-4 border-l-emerald-500 bg-emerald-50/50 px-4 py-2.5">
                        <div className="flex items-start justify-between gap-2">
                          <div>
                            <p className="text-sm font-semibold text-slate-800">{o.titulo}</p>
                            <p className="text-xs text-slate-600 mt-0.5">{o.detalle}</p>
                          </div>
                          <span className="shrink-0 rounded-full bg-emerald-100 text-emerald-700 px-2 py-0.5 text-[10px] font-bold">{o.impacto_estimado}</span>
                        </div>
                        {o.producto_sku && <span className="inline-block mt-1 text-[10px] font-mono bg-white/80 rounded px-1.5 py-0.5 text-slate-500">{o.producto_sku}</span>}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Productos Estrella */}
              {(analysis.productos_estrella?.length ?? 0) > 0 && (
                <div>
                  <h4 className="flex items-center gap-1.5 text-xs font-bold text-slate-500 uppercase tracking-wider mb-2">
                    <Star className="h-3.5 w-3.5" /> Productos Estrella
                  </h4>
                  <div className="flex flex-wrap gap-2">
                    {(analysis.productos_estrella ?? []).map((p, i) => (
                      <div key={i} className="flex items-center gap-2 rounded-xl bg-amber-50 border border-amber-200/60 px-3 py-2">
                        <Star className="h-4 w-4 text-amber-500 fill-amber-400 shrink-0" />
                        <div>
                          <p className="text-xs font-bold text-slate-800">{p.nombre} <span className="font-mono font-normal text-slate-400">({p.sku})</span></p>
                          <p className="text-[10px] text-slate-500">{p.razon}</p>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Recomendaciones */}
              {(analysis.recomendaciones?.length ?? 0) > 0 && (
                <div>
                  <h4 className="flex items-center gap-1.5 text-xs font-bold text-slate-500 uppercase tracking-wider mb-2">
                    <Target className="h-3.5 w-3.5" /> Recomendaciones
                  </h4>
                  <ol className="space-y-1.5">
                    {(analysis.recomendaciones ?? []).map((r, i) => (
                      <li key={i} className="flex items-start gap-2.5 text-sm text-slate-700">
                        <span className="shrink-0 flex h-5 w-5 items-center justify-center rounded-full bg-slate-200 text-[10px] font-bold text-slate-600">{i + 1}</span>
                        <div className="flex-1">
                          <span>{r.accion}</span>
                          <span className={cn('ml-2 inline-flex rounded-full px-1.5 py-0.5 text-[9px] font-bold', PRIORITY_BADGE[r.prioridad])}>{r.prioridad}</span>
                          {r.plazo && <span className="ml-1 inline-flex rounded-full bg-slate-100 text-slate-500 px-1.5 py-0.5 text-[9px] font-medium">{r.plazo.replace('_', ' ')}</span>}
                        </div>
                      </li>
                    ))}
                  </ol>
                </div>
              )}
            </div>
          ) : null}
        </div>
      )}
    </div>
  )
}


class AiErrorBoundary extends React.Component<{ children: React.ReactNode }, { hasError: boolean }> {
  constructor(props: { children: React.ReactNode }) { super(props); this.state = { hasError: false } }
  static getDerivedStateFromError() { return { hasError: true } }
  render() {
    if (this.state.hasError) {
      return <div className="text-sm text-muted-foreground p-4 text-center rounded-xl border border-border bg-card">Panel de analisis no disponible</div>
    }
    return this.props.children
  }
}

function AiInsightsPanel({ dateFrom, dateTo }: { dateFrom: string; dateTo: string }) {
  return (
    <AiErrorBoundary>
      <AiInsightsPanelInner dateFrom={dateFrom} dateTo={dateTo} />
    </AiErrorBoundary>
  )
}


export function PnLPage() {
  const now = new Date()
  const defaultFrom = formatDate(new Date(now.getFullYear(), now.getMonth(), 1))
  const defaultTo = formatDate(now)

  const [dateFrom, setDateFrom] = useState(defaultFrom)
  const [dateTo, setDateTo] = useState(defaultTo)
  const [expandedId, setExpandedId] = useState<string | null>(null)

  // Current period
  const { data, isLoading } = usePnL(dateFrom || undefined, dateTo || undefined)
  const pnl = data as PnLReport | undefined
  const totals = pnl?.totals
  const products = pnl?.products ?? []

  // Previous period (for comparison)
  const prev = useMemo(() => {
    if (!dateFrom || !dateTo) return { prevFrom: undefined, prevTo: undefined }
    return getPreviousPeriod(dateFrom, dateTo)
  }, [dateFrom, dateTo])

  const { data: prevData } = usePnL(prev.prevFrom, prev.prevTo)
  const prevPnl = prevData as PnLReport | undefined
  const prevTotals = prevPnl?.totals

  // PDF download
  const downloadPdf = useDownloadPnLPdf()

  const comparisonLabel = useMemo(() => {
    if (!dateFrom || !dateTo) return 'periodo anterior'
    const from = new Date(dateFrom)
    const to = new Date(dateTo)
    const days = Math.round((to.getTime() - from.getTime()) / 86_400_000)
    if (days <= 1) return 'dia anterior'
    if (days <= 7) return 'semana anterior'
    if (days <= 31) return 'mes anterior'
    return 'periodo anterior'
  }, [dateFrom, dateTo])

  const setPreset = (preset: string) => {
    const fmt = formatDate
    if (preset === 'today') {
      setDateFrom(fmt(now))
      setDateTo(fmt(now))
    } else if (preset === 'week') {
      const s = new Date(now)
      s.setDate(now.getDate() - now.getDay())
      setDateFrom(fmt(s))
      setDateTo(fmt(now))
    } else if (preset === 'month') {
      setDateFrom(fmt(new Date(now.getFullYear(), now.getMonth(), 1)))
      setDateTo(fmt(now))
    } else if (preset === 'year') {
      setDateFrom(fmt(new Date(now.getFullYear(), 0, 1)))
      setDateTo(fmt(now))
    }
  }

  /* ── KPI variant helpers ──────────────────────────────────────────────────── */

  function kpiVariant(current: number, previous: number | undefined, invert = false): 'default' | 'success' | 'warning' | 'danger' {
    if (previous == null || previous === 0) return 'default'
    const change = ((current - previous) / Math.abs(previous)) * 100
    const effective = invert ? -change : change
    if (effective >= 5) return 'success'
    if (effective >= -5) return 'default'
    return 'danger'
  }

  function kpiSub(current: number, previous: number | undefined): string {
    if (previous == null || previous === 0) return ''
    const change = pctChange(current, previous)
    if (change === null) return ''
    const sign = change >= 0 ? '+' : ''
    return `${sign}${change.toFixed(1)}% vs ${comparisonLabel}`
  }

  return (
    <div className="space-y-6">
      {/* ── Header ───────────────────────────────────────────────────────── */}
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold tracking-tight">Rentabilidad</h1>
        <div className="flex gap-2">
          <button
            onClick={() => pnl && exportCsv(pnl)}
            disabled={!pnl || products.length === 0}
            className="flex items-center gap-2 rounded-lg border border-border bg-card px-4 py-2 text-[13px] font-medium text-foreground transition-colors hover:bg-muted disabled:opacity-40 disabled:cursor-not-allowed"
          >
            <Download className="h-4 w-4" />
            CSV
          </button>
          <button
            onClick={() => downloadPdf.mutate({ dateFrom: dateFrom || undefined, dateTo: dateTo || undefined })}
            disabled={downloadPdf.isPending}
            className="flex items-center gap-2 rounded-lg bg-foreground px-4 py-2 text-[13px] font-medium text-background transition-colors hover:bg-foreground/90 disabled:opacity-60"
          >
            <FileText className="h-4 w-4" />
            {downloadPdf.isPending ? 'Generando...' : 'PDF'}
          </button>
        </div>
      </div>

      {/* ── Date Range + Presets ──────────────────────────────────────────── */}
      <div className="flex flex-wrap items-center gap-4">
        <div className="flex items-center gap-2">
          <input
            type="date"
            value={dateFrom}
            onChange={(e) => setDateFrom(e.target.value)}
            className="rounded-lg border border-border bg-card px-3 py-2 text-sm transition-all focus:bg-background focus:ring-2 focus:ring-ring"
          />
          <span className="text-muted-foreground">—</span>
          <input
            type="date"
            value={dateTo}
            onChange={(e) => setDateTo(e.target.value)}
            className="rounded-lg border border-border bg-card px-3 py-2 text-sm transition-all focus:bg-background focus:ring-2 focus:ring-ring"
          />
        </div>
        <SegmentedControl
          options={[
            { value: 'today', label: 'Hoy' },
            { value: 'week', label: 'Semana' },
            { value: 'month', label: 'Mes' },
            { value: 'year', label: 'Año' },
          ]}
          value=""
          onChange={setPreset}
        />
      </div>

      {/* ── KPI Cards with Period Comparison ──────────────────────────────── */}
      {totals && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {[
            { label: 'Ingresos', value: formatCOP(totals.total_revenue), icon: DollarSign, variant: kpiVariant(totals.total_revenue, prevTotals?.total_revenue), sub: kpiSub(totals.total_revenue, prevTotals?.total_revenue), tooltip: 'Ingresos netos sin impuestos' },
            { label: 'Costo ventas', value: formatCOP(totals.total_cogs), icon: Package, variant: kpiVariant(totals.total_cogs, prevTotals?.total_cogs, true), sub: kpiSub(totals.total_cogs, prevTotals?.total_cogs), tooltip: 'Costo de ventas calculado vía FIFO/Capas' },
            { label: 'Utilidad', value: formatCOP(totals.gross_profit), icon: totals.gross_profit >= 0 ? TrendingUp : TrendingDown, variant: kpiVariant(totals.gross_profit, prevTotals?.gross_profit), sub: kpiSub(totals.gross_profit, prevTotals?.gross_profit), tooltip: 'Ingresos menos costo de ventas' },
            { label: 'Margen', value: `${totals.gross_margin_pct.toFixed(1)}%`, icon: TrendingUp, variant: (totals.gross_margin_pct >= 25 ? 'success' : totals.gross_margin_pct >= 15 ? 'warning' : 'danger') as 'success' | 'warning' | 'danger', sub: prevTotals ? `${(totals.gross_margin_pct - prevTotals.gross_margin_pct) >= 0 ? '+' : ''}${(totals.gross_margin_pct - prevTotals.gross_margin_pct).toFixed(1)}pp vs ${comparisonLabel}` : '', tooltip: 'Utilidad / Ingresos × 100' },
          ].map((kpi) => {
            const Icon = kpi.icon
            const borderColor = kpi.variant === 'success' ? 'border-l-emerald-500' : kpi.variant === 'danger' ? 'border-l-red-500' : 'border-l-transparent'
            return (
              <div key={kpi.label} className={cn('rounded-lg border border-border bg-card p-4 border-l-4', borderColor)} title={kpi.tooltip}>
                <div className="flex items-center justify-between pb-1">
                  <span className="text-xs font-medium text-muted-foreground">{kpi.label}</span>
                  <Icon className="h-4 w-4 text-muted-foreground" />
                </div>
                <p className="text-xl font-bold tabular-nums">{kpi.value}</p>
                {kpi.sub && (
                  <p className={cn('mt-1 text-xs font-medium', kpi.sub.startsWith('+') ? 'text-emerald-600' : kpi.sub.startsWith('-') ? 'text-red-600' : 'text-muted-foreground')}>
                    {kpi.sub}
                  </p>
                )}
              </div>
            )
          })}
        </div>
      )}

      {/* ── AI Insights ──────────────────────────────────────────────────── */}
      <AiInsightsPanel dateFrom={dateFrom} dateTo={dateTo} />

      {/* ── Product Table ────────────────────────────────────────────────── */}
      {isLoading ? (
        <div className="py-16 text-center text-muted-foreground">Cargando...</div>
      ) : (
        <div className="rounded-lg border border-border overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border bg-muted/50">
                <th className="w-8 p-3"></th>
                <th className="p-3 text-left font-medium">Producto</th>
                <th className="p-3 text-right font-medium">Ingresos</th>
                <th className="p-3 text-right font-medium">Costo</th>
                <th className="p-3 text-right font-medium">Utilidad</th>
                <th className="p-3 text-right font-medium">Margen</th>
                <th className="p-3 text-right font-medium">Objetivo</th>
              </tr>
            </thead>
            <tbody>
              {products.map((p) => {
                const isExpanded = expandedId === p.product_id
                const s = p.summary
                const hasCostWarning = s.total_revenue > 0 && s.total_cogs === 0
                const profitLeak =
                  s.margin_vs_target < 0 ? s.total_revenue * Math.abs(s.margin_vs_target) / 100 : 0

                return (
                  <React.Fragment key={p.product_id}>
                    <tr
                      className="border-b border-border cursor-pointer hover:bg-muted/40 transition-colors"
                      onClick={() => setExpandedId(isExpanded ? null : p.product_id)}
                    >
                      <td className="p-3 text-muted-foreground">
                        {isExpanded ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
                      </td>
                      <td className="p-3">
                        <div className="flex items-center gap-2">
                          <span className="font-medium">{p.product_name}</span>
                          <span className="text-xs text-muted-foreground">{p.product_sku}</span>
                          {hasCostWarning && (
                            <span className="inline-flex items-center gap-1 rounded-full bg-amber-100 px-2 py-0.5 text-[10px] font-medium text-amber-700">
                              <AlertTriangle className="h-3 w-3" /> Sin costo
                            </span>
                          )}
                        </div>
                      </td>
                      <td className="p-3 text-right tabular-nums">{formatCOP(s.total_revenue)}</td>
                      <td className="p-3 text-right tabular-nums">{formatCOP(s.total_cogs)}</td>
                      <td className="p-3 text-right font-semibold tabular-nums">{formatCOP(s.gross_profit)}</td>
                      <td className="p-3 text-right">
                        <span className={cn('inline-block rounded px-2 py-0.5 text-xs font-medium', marginColor(s.gross_margin_pct, s.margin_target))}>
                          {s.gross_margin_pct.toFixed(1)}%
                        </span>
                        {profitLeak > 0 && (
                          <div className="mt-0.5 text-[10px] font-medium text-red-600">
                            Fuga: -{formatCOP(profitLeak)}
                          </div>
                        )}
                      </td>
                      <td className="p-3 text-right text-muted-foreground tabular-nums">
                        {s.margin_target.toFixed(1)}%
                      </td>
                    </tr>
                    {isExpanded && (
                      <tr>
                        <td colSpan={7} className="p-0 border-b border-border bg-muted/20">
                          <div className="px-4 py-4">
                            <ProductDetail pnl={p} />
                          </div>
                        </td>
                      </tr>
                    )}
                  </React.Fragment>
                )
              })}
            </tbody>
          </table>
          {products.length === 0 && (
            <div className="py-16 text-center text-muted-foreground">
              No hay datos para el periodo seleccionado
            </div>
          )}
        </div>
      )}
    </div>
  )
}
