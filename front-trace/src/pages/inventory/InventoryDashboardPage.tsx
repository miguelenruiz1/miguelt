import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Package, AlertTriangle, ShoppingCart, TrendingDown, TrendingUp,
  BarChart3, DollarSign, Factory, Layers, ClipboardCheck,
  PawPrint, Monitor, SprayCan, Sparkles, Trash2, MapPin,
  ChevronRight, Truck, Eye, EyeOff, ChevronDown, CheckCircle,
} from 'lucide-react'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  LineChart, Line, PieChart, Pie, Cell, Legend, AreaChart, Area,
} from 'recharts'
import { cn } from '@/lib/utils'
import {
  useInventoryAnalytics, useImportDemo, useDeleteDemo,
  useWarehouseOccupation, useABCClassification,
  useStockPolicy, useStorageValuation, useCommittedStock,
} from '@/hooks/useInventory'
import { useToast } from '@/store/toast'
import type { DemoDeleteResult, DemoImportResult } from '@/types/inventory'

/* ─── Helpers ──────────────────────────────────────────────────────── */

const MOVEMENT_TYPE_LABELS: Record<string, string> = {
  purchase: 'Compra', sale: 'Venta', transfer: 'Transferencia',
  adjustment_in: 'Ajuste +', adjustment_out: 'Ajuste -',
  return: 'Devolución', waste: 'Merma',
}

const PIE_COLORS = ['#6366f1', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#06b6d4', '#ec4899']

const fmt = (n: number) => n.toLocaleString('es-CO', { minimumFractionDigits: 0, maximumFractionDigits: 0 })

/* ─── KPI Card — shadcn style ──────────────────────────────────── */

function HeroKpi({
  label, value, icon: Icon, sub, onClick, iconColor,
  gradient: _gradient, pulse: _pulse,
}: {
  label: string; value: number | string; icon: React.ElementType
  gradient?: string; sub?: string; pulse?: boolean; onClick?: () => void
  iconColor?: string
}) {
  return (
    <div
      onClick={onClick}
      className={cn(
        'rounded-lg border border-border bg-card p-5 transition-colors',
        onClick && 'cursor-pointer hover:bg-muted/50',
      )}
    >
      <div className="flex items-center justify-between pb-2">
        <p className="text-sm font-medium text-muted-foreground">{label}</p>
        <Icon className={cn('h-4 w-4', iconColor || 'text-muted-foreground')} />
      </div>
      <p className="text-2xl font-bold">{value}</p>
      {sub && <p className="text-xs text-muted-foreground mt-1">{sub}</p>}
      {onClick && <p className="text-xs text-primary mt-2">Ver productos →</p>}
    </div>
  )
}

/* ─── Section wrapper ───────────────────────────────────────────── */

function Section({
  title, icon: Icon, iconColor, children, collapsible, defaultOpen = true,
  actions,
}: {
  title: string; icon: React.ElementType; iconColor: string
  children: React.ReactNode; collapsible?: boolean; defaultOpen?: boolean
  actions?: React.ReactNode
}) {
  const [open, setOpen] = useState(defaultOpen)
  return (
    <div className="rounded-lg border border-border bg-card overflow-hidden">
      <button
        type="button"
        onClick={() => collapsible && setOpen(!open)}
        className={cn(
          'w-full flex items-center gap-3 px-5 py-3.5',
          collapsible && 'cursor-pointer hover:bg-muted/50 transition-colors',
        )}
      >
        <Icon className={cn('h-4 w-4 shrink-0 text-muted-foreground')} />
        <h2 className="text-sm font-semibold text-foreground flex-1 text-left">{title}</h2>
        {actions && <div className="mr-2" onClick={e => e.stopPropagation()}>{actions}</div>}
        {collapsible && (
          <ChevronDown className={cn('h-4 w-4 text-muted-foreground transition-transform', open && 'rotate-180')} />
        )}
      </button>
      {(!collapsible || open) && <div className="px-5 pb-5">{children}</div>}
    </div>
  )
}


/* ─── Custom Tooltip ────────────────────────────────────────────── */

function ChartTooltip({ active, payload, label }: any) {
  if (!active || !payload?.length) return null
  return (
    <div className="bg-card rounded-xl shadow-lg border border-border px-3 py-2 text-xs">
      <p className="font-semibold text-foreground mb-1">{label}</p>
      {payload.map((p: any) => (
        <p key={p.name} style={{ color: p.color }}>
          {p.name}: <strong>{p.value}</strong>
        </p>
      ))}
    </div>
  )
}

/* ─── Gauge (semi-circle visual) ────────────────────────────────── */

function Gauge({ value, max, label, color }: { value: number; max: number; label: string; color: string }) {
  const pct = max > 0 ? Math.min((value / max) * 100, 100) : 0
  return (
    <div className="flex flex-col items-center gap-1">
      <div className="relative w-20 h-10 overflow-hidden">
        <div className="absolute inset-0 rounded-t-full bg-muted" />
        <div
          className="absolute bottom-0 left-0 rounded-t-full origin-bottom transition-all"
          style={{
            width: '100%', height: '100%',
            background: `conic-gradient(${color} ${pct * 1.8}deg, transparent 0)`,
            clipPath: 'polygon(0 100%, 0 0, 100% 0, 100% 100%)',
          }}
        />
      </div>
      <span className="text-lg font-bold text-foreground">{pct.toFixed(0)}%</span>
      <span className="text-[10px] text-muted-foreground text-center">{label}</span>
    </div>
  )
}

/* ─── Stock Health Bar ──────────────────────────────────────────── */

function StockHealthBar({
  okCount, lowCount, outCount,
}: {
  okCount: number; lowCount: number; outCount: number
}) {
  const total = okCount + lowCount + outCount
  if (total === 0) return null
  const okPct = (okCount / total) * 100
  const lowPct = (lowCount / total) * 100
  const outPct = (outCount / total) * 100

  return (
    <div>
      <div className="flex items-center justify-between mb-2">
        <span className="text-sm font-medium text-foreground">Salud del inventario</span>
        <span className="text-xs text-muted-foreground">{total} productos</span>
      </div>
      <div className="flex gap-1 h-2 rounded-full overflow-hidden bg-muted">
        {okPct > 0 && (
          <div className="bg-emerald-500 rounded-full transition-all" style={{ width: `${okPct}%` }}
            title={`OK: ${okCount}`} />
        )}
        {lowPct > 0 && (
          <div className="bg-amber-500 rounded-full transition-all" style={{ width: `${lowPct}%` }}
            title={`Bajo stock: ${lowCount}`} />
        )}
        {outPct > 0 && (
          <div className="bg-red-500 rounded-full transition-all" style={{ width: `${outPct}%` }}
            title={`Sin stock: ${outCount}`} />
        )}
      </div>
      <div className="flex gap-4 mt-2">
        <span className="flex items-center gap-1 text-xs text-muted-foreground">
          <span className="h-2 w-2 rounded-full bg-emerald-500 inline-block" /> OK ({okCount})
        </span>
        <span className="flex items-center gap-1 text-xs text-muted-foreground">
          <span className="h-2 w-2 rounded-full bg-amber-500 inline-block" /> Bajo ({lowCount})
        </span>
        <span className="flex items-center gap-1 text-xs text-muted-foreground">
          <span className="h-2 w-2 rounded-full bg-red-500 inline-block" /> Sin stock ({outCount})
        </span>
      </div>
    </div>
  )
}

/* ─── Occupation Section ────────────────────────────────────────── */

function OccupationSection() {
  const { data: occ, isLoading, isError } = useWarehouseOccupation()
  if (isLoading) return <div className="h-32 rounded-2xl bg-muted animate-pulse" />
  if (isError) return (
    <Section title="Ocupacion de bodegas" icon={MapPin} iconColor="bg-teal-500">
      <p className="text-sm text-red-500">Error al cargar datos de ocupacion. Verifica que tengas el permiso <b>reports.view</b>.</p>
    </Section>
  )
  if (!occ) return null

  const occColor = occ.occupation_pct >= 90 ? '#ef4444' : occ.occupation_pct >= 70 ? '#f59e0b' : '#10b981'
  const warehouses = occ.by_warehouse ?? []
  const hasData = occ.total_locations > 0 || warehouses.length > 0

  if (!hasData) return (
    <Section title="Ocupacion de bodegas" icon={MapPin} iconColor="bg-teal-500">
      <p className="text-sm text-muted-foreground">Sin datos de stock. Registra entradas de producto para ver la ocupacion.</p>
    </Section>
  )

  return (
    <Section title="Ocupacion de bodegas" icon={MapPin} iconColor="bg-teal-500">
      <div className="grid grid-cols-1 md:grid-cols-[200px_1fr] gap-6 items-center">
        {/* Visual gauge */}
        <div className="flex flex-col items-center gap-3">
          <div className="relative w-32 h-32">
            <svg viewBox="0 0 120 120" className="w-full h-full -rotate-90">
              <circle cx="60" cy="60" r="52" fill="none" stroke="#f1f5f9" strokeWidth="12" />
              <circle cx="60" cy="60" r="52" fill="none" stroke={occColor} strokeWidth="12"
                strokeDasharray={`${occ.occupation_pct * 3.27} 327`} strokeLinecap="round"
                className="transition-all duration-700" />
            </svg>
            <div className="absolute inset-0 flex flex-col items-center justify-center">
              <span className="text-2xl font-extrabold text-foreground">{occ.occupation_pct.toFixed(0)}%</span>
              <span className="text-[10px] text-muted-foreground">ocupado</span>
            </div>
          </div>
          <div className="flex gap-4 text-center">
            <div>
              <p className="text-lg font-bold text-primary">{occ.occupied_locations}</p>
              <p className="text-[10px] text-muted-foreground">En stock</p>
            </div>
            <div>
              <p className="text-lg font-bold text-emerald-600">{occ.free_locations}</p>
              <p className="text-[10px] text-muted-foreground">Disponible</p>
            </div>
          </div>
        </div>

        {/* Per-warehouse bars */}
        {warehouses.length > 0 && (
          <div className="space-y-3">
            {warehouses.map(wh => {
              const hasCap = wh.has_capacity === true
              const barColor = hasCap
                ? (wh.occupation_pct >= 90 ? '#ef4444' : wh.occupation_pct >= 70 ? '#f59e0b' : '#10b981')
                : '#6366f1'
              const barWidth = hasCap ? Math.min(wh.occupation_pct, 100) : 100

              return (
                <div key={wh.warehouse_id} className="space-y-1">
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-foreground font-medium">{wh.warehouse_name}</span>
                    {hasCap ? (
                      <span className="text-muted-foreground">
                        {wh.occupied_locations}/{wh.total_locations} uds
                        <span className="ml-1 font-semibold" style={{ color: barColor }}>
                          ({wh.occupation_pct.toFixed(0)}%)
                        </span>
                      </span>
                    ) : (
                      <span className="font-semibold text-primary">
                        {wh.occupied_locations} uds
                      </span>
                    )}
                  </div>
                  <div className="w-full h-2.5 bg-muted rounded-full overflow-hidden">
                    <div
                      className="h-full rounded-full transition-all duration-500"
                      style={{ width: `${barWidth}%`, backgroundColor: barColor }}
                    />
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </div>
    </Section>
  )
}

/* ─── ABC Section ───────────────────────────────────────────────── */

function ABCSection() {
  const { data, isLoading } = useABCClassification()
  if (isLoading) return <div className="animate-pulse h-64 rounded-2xl bg-muted" />
  if (!data || data.total_products === 0) return null

  const classConfig = {
    A: { bg: 'bg-red-50', border: 'border-red-200', text: 'text-red-700', badge: 'bg-red-500', desc: 'Alto valor' },
    B: { bg: 'bg-amber-50', border: 'border-amber-200', text: 'text-amber-700', badge: 'bg-amber-500', desc: 'Valor medio' },
    C: { bg: 'bg-emerald-50', border: 'border-emerald-200', text: 'text-emerald-700', badge: 'bg-emerald-500', desc: 'Bajo valor' },
  }

  return (
    <Section title="Clasificacion ABC" icon={BarChart3} iconColor="bg-purple-500" collapsible>
      <div className="grid grid-cols-3 gap-3 mb-5">
        {(['A', 'B', 'C'] as const).map(cls => {
          const s = data.summary[cls]
          const c = classConfig[cls]
          return (
            <div key={cls} className={cn('rounded-2xl border p-4 text-center', c.bg, c.border)}>
              <div className={cn('inline-flex h-8 w-8 items-center justify-center rounded-full text-sm font-extrabold text-white', c.badge)}>
                {cls}
              </div>
              <p className={cn('text-2xl font-extrabold mt-2', c.text)}>{s.count}</p>
              <p className="text-[10px] text-muted-foreground">{c.desc}</p>
              <p className="text-xs font-semibold text-muted-foreground mt-1">{s.value_pct.toFixed(0)}% del valor</p>
              <p className="text-[10px] text-muted-foreground">${fmt(s.value)}</p>
            </div>
          )
        })}
      </div>

      {/* Visual stacked bar */}
      <div className="flex h-5 rounded-full overflow-hidden mb-2">
        {(['A', 'B', 'C'] as const).map(cls => (
          <div key={cls} className={classConfig[cls].badge} style={{ width: `${data.summary[cls].value_pct}%` }} />
        ))}
      </div>
      <p className="text-[10px] text-muted-foreground text-right">Total inventario: ${fmt(data.grand_total_value)}</p>

      {/* Top items */}
      {data.items.length > 0 && (
        <div className="mt-4 rounded-xl bg-muted/50 p-4">
          <p className="text-xs font-semibold text-muted-foreground mb-2 uppercase tracking-wide">Top 10 productos por valor</p>
          <div className="space-y-1.5">
            {data.items.slice(0, 10).map((it, i) => (
              <div key={it.product_id} className="flex items-center gap-2 text-xs">
                <span className="w-5 text-muted-foreground text-right font-mono">{i + 1}</span>
                <span className={cn(
                  'shrink-0 h-5 w-5 rounded-full flex items-center justify-center text-[9px] font-bold text-white',
                  classConfig[it.abc_class].badge,
                )}>{it.abc_class}</span>
                <span className="flex-1 text-foreground truncate">{it.name || it.sku}</span>
                <span className="text-muted-foreground font-mono">${fmt(it.total_value)}</span>
                <span className="text-muted-foreground w-12 text-right">{it.cumulative_pct.toFixed(0)}%</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </Section>
  )
}

/* ─── Stock Policy Section ──────────────────────────────────────── */

function StockPolicySection() {
  const { data, isLoading } = useStockPolicy()
  if (isLoading) return <div className="animate-pulse h-40 rounded-2xl bg-muted" />
  if (!data || data.items.length === 0) return null

  return (
    <div className="space-y-3">
      <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">Rotacion por tipo</h3>
      {data.items.map(it => {
        const pct = it.months_on_hand != null && it.target_months > 0
          ? Math.min((it.months_on_hand / it.target_months) * 100, 150) : 0
        const isOk = it.status === 'ok'
        return (
          <div key={it.product_type_id} className="rounded-xl border border-border p-3">
            <div className="flex items-center justify-between mb-1.5">
              <div className="flex items-center gap-2">
                <span className="h-3 w-3 rounded-full shrink-0" style={{ backgroundColor: it.color || '#9ca3af' }} />
                <span className="text-xs font-semibold text-foreground">{it.product_type_name}</span>
              </div>
              <span className={cn('text-[10px] font-medium px-2 py-0.5 rounded-full', isOk ? 'bg-emerald-50 text-emerald-600' : 'bg-red-50 text-red-600')}>
                {it.months_on_hand != null ? `${it.months_on_hand}m` : '?'} / {it.target_months}m
              </span>
            </div>
            <div className="h-2 bg-muted rounded-full overflow-hidden">
              <div className={cn('h-full rounded-full transition-all', isOk ? 'bg-emerald-500' : 'bg-red-500')}
                style={{ width: `${Math.min(pct, 100)}%` }} />
            </div>
          </div>
        )
      })}
    </div>
  )
}

/* ─── Storage Valuation Section ─────────────────────────────────── */

function StorageValuationSection() {
  const { data, isLoading } = useStorageValuation()
  if (isLoading) return <div className="animate-pulse h-40 rounded-2xl bg-muted" />
  if (!data) return null
  const hasData = data.items.some(it => it.monthly_cost != null)
  if (!hasData && data.total_monthly_cost === 0) return null

  return (
    <div className="space-y-3">
      <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">Costo de almacenamiento</h3>
      <div className="grid grid-cols-3 gap-2">
        <div className="rounded-xl bg-primary/10 p-3 text-center">
          <p className="text-[10px] text-primary font-semibold">$/mes</p>
          <p className="text-sm font-bold text-primary">${fmt(data.total_monthly_cost)}</p>
        </div>
        <div className="rounded-xl bg-purple-50 p-3 text-center">
          <p className="text-[10px] text-purple-500 font-semibold">Valor stock</p>
          <p className="text-sm font-bold text-purple-700">${fmt(data.total_stock_value)}</p>
        </div>
        <div className="rounded-xl bg-amber-50 p-3 text-center">
          <p className="text-[10px] text-amber-500 font-semibold">Ratio</p>
          <p className="text-sm font-bold text-amber-700">{data.storage_to_value_pct != null ? `${data.storage_to_value_pct}%` : '-'}</p>
        </div>
      </div>
      {data.items.length > 0 && (
        <div className="space-y-1.5">
          {data.items.map(it => (
            <div key={it.warehouse_id} className="flex items-center justify-between text-xs rounded-lg bg-muted/50 px-3 py-2">
              <span className="text-foreground font-medium">{it.warehouse_name}</span>
              <span className="text-muted-foreground">
                {it.monthly_cost != null ? `$${fmt(it.monthly_cost)}/mes` : '-'}
                {it.total_area_sqm != null && <span className="ml-2 text-muted-foreground">({it.total_area_sqm}m²)</span>}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

/* ─── Demo Data Section ─────────────────────────────────────────── */

const DEMO_INDUSTRIES = [
  { key: 'pet_food', label: 'Mascotas', desc: 'Materias primas y producto terminado', icon: PawPrint, color: '#f59e0b' },
  { key: 'technology', label: 'Tecnologia', desc: 'Componentes y equipos', icon: Monitor, color: '#6366f1' },
  { key: 'cleaning', label: 'Aseo', desc: 'Limpieza hogar e industrial', icon: SprayCan, color: '#0ea5e9' },
] as const

function DemoResultRow({ label, created, restored }: { label: string; created: number; restored?: number }) {
  if (created === 0 && (restored ?? 0) === 0) return null
  return (
    <>
      <span className="text-muted-foreground">{label}:</span>
      <span className="font-semibold text-emerald-600">{created > 0 ? `${created} nuevos` : '—'}</span>
      <span className="font-semibold text-blue-600">{(restored ?? 0) > 0 ? `${restored} rest.` : '—'}</span>
    </>
  )
}

function DemoResultGrid({ result: r }: { result: DemoImportResult }) {
  return (
    <div className="grid grid-cols-3 gap-x-2 gap-y-0.5 text-[11px]">
      <DemoResultRow label="Productos" created={r.products_created} restored={r.products_restored} />
      <DemoResultRow label="Bodegas" created={r.warehouses_created} restored={r.warehouses_restored} />
      <DemoResultRow label="Proveedores" created={r.suppliers_created} restored={r.suppliers_restored} />
      <DemoResultRow label="Tipos prod." created={r.types_created} restored={r.types_restored} />
      <DemoResultRow label="Tipos prov." created={r.supplier_types_created ?? 0} restored={r.supplier_types_restored ?? 0} />
      <DemoResultRow label="Tipos OC" created={r.order_types_created ?? 0} restored={r.order_types_restored ?? 0} />
      <DemoResultRow label="Lotes" created={r.batches_created ?? 0} />
      <DemoResultRow label="Seriales" created={r.serials_created ?? 0} />
      <DemoResultRow label="Recetas" created={r.recipes_created ?? 0} restored={r.recipes_restored ?? 0} />
      <DemoResultRow label="Órdenes C." created={r.pos_created ?? 0} />
      <DemoResultRow label="Producción" created={r.production_runs_created ?? 0} />
      <DemoResultRow label="Eventos" created={r.events_created ?? 0} />
      <DemoResultRow label="Config. Ev." created={r.event_config_created ?? 0} />
      <DemoResultRow label="Taxonomías" created={r.taxonomies_created ?? 0} />
    </div>
  )
}

function DeleteResultGrid({ result: r }: { result: DemoDeleteResult }) {
  const entries: Array<[string, number]> = [
    ['Productos', r.products_deleted], ['Bodegas', r.warehouses_deleted],
    ['Proveedores', r.suppliers_deleted], ['Tipos prod.', r.types_deleted],
    ['Tipos prov.', r.supplier_types_deleted], ['Tipos OC', r.order_types_deleted],
    ['Lotes', r.batches_deleted], ['Seriales', r.serials_deleted],
    ['Recetas', r.recipes_deleted], ['Órdenes C.', r.pos_deleted],
    ['Producción', r.production_runs_deleted], ['Eventos', r.events_deleted],
    ['Taxonomías', r.taxonomies_deleted],
  ]
  const nonZero = entries.filter(([, v]) => v > 0)
  if (nonZero.length === 0) return <p className="text-[11px] text-muted-foreground">Nada que eliminar</p>
  return (
    <div className="grid grid-cols-2 gap-x-2 gap-y-0.5 text-[11px]">
      {nonZero.map(([label, count]) => (
        <span key={label}><span className="text-muted-foreground">{label}:</span> <span className="font-semibold text-red-600">{count}</span></span>
      ))}
    </div>
  )
}

function DemoDataSection() {
  const importDemo = useImportDemo()
  const deleteDemo = useDeleteDemo()
  const toast = useToast()
  const [selected, setSelected] = useState<Set<string>>(new Set())
  const [results, setResults] = useState<DemoImportResult[] | null>(null)
  const [deleteResults, setDeleteResults] = useState<DemoDeleteResult[] | null>(null)
  const [confirmDelete, setConfirmDelete] = useState(false)

  function toggle(key: string) {
    setSelected(prev => {
      const next = new Set(prev)
      if (next.has(key)) next.delete(key); else next.add(key)
      return next
    })
  }

  async function handleImport() {
    if (selected.size === 0) return
    try {
      const res = await importDemo.mutateAsync([...selected])
      setResults(res); setDeleteResults(null)
      const sum = (key: keyof DemoImportResult) => res.reduce((s, r) => s + ((r[key] as number) ?? 0), 0)
      const totalCreated = sum('products_created') + sum('warehouses_created') + sum('suppliers_created')
        + sum('types_created') + sum('supplier_types_created') + sum('order_types_created')
        + sum('batches_created') + sum('serials_created') + sum('recipes_created') + sum('pos_created')
        + sum('production_runs_created') + sum('events_created') + sum('event_config_created')
        + sum('taxonomies_created')
      const totalRestored = sum('products_restored') + sum('warehouses_restored') + sum('suppliers_restored')
        + sum('types_restored') + sum('supplier_types_restored') + sum('order_types_restored')
        + sum('recipes_restored')
      const parts: string[] = []
      if (totalCreated > 0) parts.push(`${totalCreated} creados`)
      if (totalRestored > 0) parts.push(`${totalRestored} restaurados`)
      if (parts.length > 0) toast.success(`Demo cargada: ${parts.join(', ')}`)
      else toast.success('Demo al día — todos los datos ya existen')
    } catch (err: unknown) { toast.error(err instanceof Error ? err.message : 'Error al cargar demo') }
  }

  async function handleDelete() {
    if (selected.size === 0) return
    if (!confirmDelete) { setConfirmDelete(true); return }
    try {
      const res = await deleteDemo.mutateAsync([...selected])
      setDeleteResults(res); setResults(null); setConfirmDelete(false)
      const totalDeleted = res.reduce((s, r) => r.error ? s : s + r.products_deleted + r.warehouses_deleted + r.suppliers_deleted
        + r.types_deleted + r.supplier_types_deleted + r.order_types_deleted + r.batches_deleted + r.serials_deleted
        + r.recipes_deleted + r.pos_deleted + r.production_runs_deleted + r.events_deleted + r.taxonomies_deleted, 0)
      if (totalDeleted > 0) toast.success(`Demo eliminada: ${totalDeleted} registros borrados`)
      else toast.success('No había datos demo que eliminar')
    } catch (err: unknown) { toast.error(err instanceof Error ? err.message : 'Error al eliminar demo'); setConfirmDelete(false) }
  }

  return (
    <Section title="Datos de demostracion" icon={Sparkles} iconColor="bg-violet-500" collapsible defaultOpen={false}>
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 mb-4">
        {DEMO_INDUSTRIES.map(ind => {
          const isChecked = selected.has(ind.key)
          const Ic = ind.icon
          return (
            <button key={ind.key} type="button"
              onClick={() => { toggle(ind.key); setConfirmDelete(false) }}
              className={cn(
                'flex items-center gap-3 rounded-2xl border p-4 text-left transition-all',
                isChecked ? 'border-primary bg-primary/10 ' : 'border-border hover:border-border hover:bg-muted/50/50',
              )}
            >
              <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl" style={{ backgroundColor: ind.color + '20' }}>
                <Ic className="h-5 w-5" style={{ color: ind.color }} />
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-semibold text-foreground">{ind.label}</p>
                <p className="text-[11px] text-muted-foreground mt-0.5 line-clamp-1">{ind.desc}</p>
              </div>
              <div className={cn('h-5 w-5 rounded-md border-2 shrink-0 flex items-center justify-center transition-colors',
                isChecked ? 'border-primary bg-primary' : 'border-slate-300')}>
                {isChecked && <span className="text-white text-xs font-bold">✓</span>}
              </div>
            </button>
          )
        })}
      </div>

      <div className="flex items-center gap-3 flex-wrap">
        <button onClick={handleImport} disabled={selected.size === 0 || importDemo.isPending || deleteDemo.isPending}
          className="rounded-lg bg-primary px-5 py-2.5 text-sm font-semibold text-white hover:bg-primary disabled:opacity-50 transition-colors">
          {importDemo.isPending ? 'Cargando...' : `Cargar Demo (${selected.size})`}
        </button>
        <button onClick={handleDelete} disabled={selected.size === 0 || importDemo.isPending || deleteDemo.isPending}
          className={cn('rounded-lg px-5 py-2.5 text-sm font-semibold transition-colors disabled:opacity-50 flex items-center gap-2',
            confirmDelete ? 'bg-red-600 text-white hover:bg-red-700' : 'bg-red-50 text-red-600 border border-red-200 hover:bg-red-100')}>
          <Trash2 className="h-4 w-4" />
          {deleteDemo.isPending ? 'Eliminando...' : confirmDelete ? 'Confirmar' : `Eliminar (${selected.size})`}
        </button>
        {confirmDelete && <button onClick={() => setConfirmDelete(false)} className="text-xs text-muted-foreground hover:text-foreground">Cancelar</button>}
      </div>

      {results && (
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 mt-4">
          {results.map(r => (
            <div key={r.industry} className="bg-muted/50 rounded-xl p-3 space-y-1">
              <p className="text-xs font-bold text-foreground">{r.label ?? r.industry}</p>
              {r.error ? <p className="text-xs text-red-500">{r.error}</p> : <DemoResultGrid result={r} />}
            </div>
          ))}
        </div>
      )}
      {deleteResults && (
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 mt-4">
          {deleteResults.map(r => (
            <div key={r.industry} className="bg-red-50 rounded-xl p-3 space-y-1">
              <p className="text-xs font-bold text-red-700">{r.label ?? r.industry}</p>
              {r.error ? <p className="text-xs text-red-500">{r.error}</p> : <DeleteResultGrid result={r} />}
            </div>
          ))}
        </div>
      )}
    </Section>
  )
}

/* ═══════════════════════════════════════════════════════════════════
   MAIN DASHBOARD
   ═══════════════════════════════════════════════════════════════════ */

export function InventoryDashboardPage() {
  const navigate = useNavigate()
  const { data, isLoading } = useInventoryAnalytics()
  const { data: committedStock } = useCommittedStock()
  const [showAlerts, setShowAlerts] = useState(true)

  if (isLoading) {
    return (
      <div className="space-y-6 animate-pulse">
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          {[...Array(4)].map((_, i) => <div key={i} className="h-28 rounded-2xl bg-muted" />)}
        </div>
        <div className="h-8 rounded-full bg-muted w-1/2" />
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {[...Array(4)].map((_, i) => <div key={i} className="h-48 rounded-2xl bg-muted" />)}
        </div>
      </div>
    )
  }

  const movementTrend = data?.movement_trend ?? []
  const byType = (data?.movements_by_type ?? []).map(m => ({
    name: MOVEMENT_TYPE_LABELS[m.type] ?? m.type,
    value: m.count,
  }))
  const totalSkus = data?.total_skus ?? 0
  const lowStock = data?.low_stock_count ?? 0
  const outOfStock = data?.out_of_stock_count ?? 0
  const okStock = Math.max(0, totalSkus - lowStock - outOfStock)

  return (
    <div className="space-y-6 max-w-[1400px] mx-auto">
      {/* Breadcrumb */}
      <nav>
        <ol className="flex items-center gap-2 text-sm">
          <li className="text-muted-foreground">Inventario</li>
          <li><ChevronRight className="h-4 w-4 text-muted-foreground" /></li>
          <li className="text-primary font-medium">Dashboard</li>
        </ol>
      </nav>

      {/* Header */}
      <div className="flex items-end justify-between flex-wrap gap-4">
        <div>
          <h1 className="text-2xl font-bold text-foreground">Dashboard de Inventario</h1>
          <p className="text-sm text-muted-foreground mt-1">Todo tu inventario de un vistazo</p>
        </div>
      </div>

      {/* ─── HERO KPIs ─── */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <HeroKpi
          label="Total productos"
          value={totalSkus}
          icon={Package}
          sub={`${totalSkus} SKUs registrados`}
        />
        <HeroKpi
          label="Valor total"
          value={`$${fmt(data?.total_value ?? 0)}`}
          icon={DollarSign}
          sub="En inventario"
        />
        <HeroKpi
          label="Bajo stock"
          value={lowStock}
          icon={TrendingDown}
          iconColor={lowStock > 0 ? 'text-amber-500' : 'text-muted-foreground'}
          sub={lowStock > 0 ? 'Requieren reabastecimiento' : 'Todo OK'}
          onClick={lowStock > 0 ? () => navigate('/inventario/productos?stock_status=low') : undefined}
        />
        <HeroKpi
          label="Sin stock"
          value={outOfStock}
          icon={AlertTriangle}
          iconColor={outOfStock > 0 ? 'text-destructive' : 'text-muted-foreground'}
          sub={outOfStock > 0 ? 'Productos agotados' : 'Ningún agotado'}
          onClick={outOfStock > 0 ? () => navigate('/inventario/productos?stock_status=out') : undefined}
        />
      </div>

      {/* ─── STOCK HEALTH BAR ─── */}
      <div className="rounded-lg border border-border bg-card p-5">
        <StockHealthBar okCount={okStock} lowCount={lowStock} outCount={outOfStock} />
      </div>

      {/* Stock Comprometido widget */}
      {committedStock && committedStock.products_with_reservations > 0 && (
        <div className="rounded-lg border border-border bg-card p-5">
          <div className="flex items-center justify-between pb-2">
            <p className="text-sm font-medium text-muted-foreground">Stock Comprometido</p>
            <ShoppingCart className="h-4 w-4 text-muted-foreground" />
          </div>
          <p className="text-2xl font-bold">${Number(committedStock.total_reserved_value || 0).toLocaleString('es-CO', { maximumFractionDigits: 0 })}</p>
          <p className="text-xs text-muted-foreground mt-1">
            {committedStock.products_with_reservations} productos · {Number(committedStock.total_reserved_qty || 0).toLocaleString('es-CO')} unidades reservadas
          </p>
          {committedStock.total_reserved_cost > 0 && (
            <p className="text-xs text-muted-foreground mt-0.5">
              Costo: ${Number(committedStock.total_reserved_cost).toLocaleString('es-CO', { maximumFractionDigits: 0 })}
            </p>
          )}
        </div>
      )}

      {/* ─── IRA + Cycle counts ─── */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="rounded-lg border border-border bg-card p-5 text-center">
          <ClipboardCheck className={cn('h-6 w-6 mx-auto mb-2',
            data?.latest_ira != null && data.latest_ira >= 95 ? 'text-emerald-500'
              : data?.latest_ira != null && data.latest_ira >= 90 ? 'text-amber-500' : 'text-muted-foreground'
          )} />
          <p className="text-2xl font-extrabold text-foreground">
            {data?.latest_ira != null ? `${data.latest_ira.toFixed(1)}%` : 'N/A'}
          </p>
          <p className="text-[10px] text-muted-foreground mt-1">IRA (Precision de inventario)</p>
        </div>
        <div className="rounded-lg border border-border bg-card p-5 text-center">
          <ClipboardCheck className="h-6 w-6 mx-auto mb-2 text-blue-500" />
          <p className="text-2xl font-extrabold text-foreground">{data?.pending_cycle_counts ?? 0}</p>
          <p className="text-[10px] text-muted-foreground mt-1">Conteos pendientes</p>
        </div>
        {(data?.expiring_batches_count ?? 0) > 0 && (
          <div className="rounded-2xl border border-amber-200 bg-amber-50  p-5 text-center">
            <Layers className="h-6 w-6 mx-auto mb-2 text-amber-500" />
            <p className="text-2xl font-extrabold text-amber-800">{data?.expiring_batches_count}</p>
            <p className="text-[10px] text-amber-500 mt-1">Lotes por vencer (30 dias)</p>
          </div>
        )}
        {(data?.production_runs_this_month ?? 0) > 0 && (
          <div className="rounded-2xl border border-primary/30 bg-primary/10  p-5 text-center">
            <Factory className="h-6 w-6 mx-auto mb-2 text-primary" />
            <p className="text-2xl font-extrabold text-primary">{data?.production_runs_this_month}</p>
            <p className="text-[10px] text-primary mt-1">Corridas este mes</p>
          </div>
        )}
        {(data?.pending_pos ?? 0) > 0 && (
          <div className="rounded-2xl border border-blue-200 bg-blue-50  p-5 text-center">
            <ShoppingCart className="h-6 w-6 mx-auto mb-2 text-blue-500" />
            <p className="text-2xl font-extrabold text-blue-800">{data?.pending_pos}</p>
            <p className="text-[10px] text-blue-500 mt-1">OCs pendientes</p>
          </div>
        )}
      </div>

      {/* ─── CHARTS ROW 1: Trend + Pie ─── */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Movement trend */}
        <Section title="Movimientos ultimos 30 dias" icon={TrendingUp} iconColor="bg-primary">
          <div className="lg:col-span-2">
            {movementTrend.length > 0 ? (
              <ResponsiveContainer width="100%" height={220}>
                <AreaChart data={movementTrend} margin={{ top: 4, right: 8, left: -16, bottom: 0 }}>
                  <defs>
                    <linearGradient id="colorMovement" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#6366f1" stopOpacity={0.2} />
                      <stop offset="95%" stopColor="#6366f1" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                  <XAxis dataKey="date" tick={{ fontSize: 10, fill: '#94a3b8' }} tickFormatter={d => d.slice(5)} />
                  <YAxis tick={{ fontSize: 10, fill: '#94a3b8' }} allowDecimals={false} />
                  <Tooltip content={<ChartTooltip />} />
                  <Area type="monotone" dataKey="count" name="Movimientos"
                    stroke="#6366f1" strokeWidth={2} fill="url(#colorMovement)" />
                </AreaChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-[220px] flex items-center justify-center text-sm text-muted-foreground">
                Sin movimientos en los ultimos 30 dias
              </div>
            )}
          </div>
        </Section>

        {/* By type pie */}
        <Section title="Por tipo de movimiento" icon={BarChart3} iconColor="bg-emerald-500">
          {byType.length > 0 ? (
            <ResponsiveContainer width="100%" height={220}>
              <PieChart>
                <Pie data={byType} cx="50%" cy="45%" innerRadius={50} outerRadius={75}
                  paddingAngle={2} dataKey="value">
                  {byType.map((_, i) => <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />)}
                </Pie>
                <Legend formatter={v => <span style={{ fontSize: 10, color: '#64748b' }}>{v}</span>} iconSize={8} />
                <Tooltip formatter={v => [v, 'Movimientos']} />
              </PieChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-[220px] flex items-center justify-center text-sm text-muted-foreground">Sin datos</div>
          )}
        </Section>
      </div>

      {/* ─── CHARTS ROW 2: Top products + Alerts ─── */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Top products */}
        <Section title="Top productos por movimiento" icon={Package} iconColor="bg-primary">
          {data?.top_products?.length ? (
            <ResponsiveContainer width="100%" height={220}>
              <BarChart
                data={data.top_products.slice(0, 6).map(p => ({
                  name: p.sku || p.product_id.slice(0, 6), count: p.movement_count,
                }))}
                layout="vertical"
                margin={{ top: 0, right: 16, left: 0, bottom: 0 }}
              >
                <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" horizontal={false} />
                <XAxis type="number" tick={{ fontSize: 10, fill: '#94a3b8' }} allowDecimals={false} />
                <YAxis type="category" dataKey="name" tick={{ fontSize: 10, fill: '#64748b' }} width={60} />
                <Tooltip formatter={v => [v, 'Movimientos']} />
                <Bar dataKey="count" fill="#6366f1" radius={[0, 6, 6, 0]} />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <p className="text-sm text-muted-foreground py-4 text-center">Sin movimientos registrados</p>
          )}
        </Section>

        {/* Alerts */}
        <Section title="Alertas de stock" icon={AlertTriangle} iconColor="bg-amber-500"
          actions={
            <button onClick={() => setShowAlerts(!showAlerts)} className="text-muted-foreground hover:text-muted-foreground">
              {showAlerts ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
            </button>
          }
        >
          {showAlerts && (
            data?.low_stock_alerts?.length ? (
              <div className="space-y-2 max-h-[220px] overflow-y-auto pr-1">
                {data.low_stock_alerts.map(alert => (
                  <div key={`${alert.product_id}-${alert.warehouse_id}`}
                    onClick={() => navigate(`/inventario/productos?stock_status=low`)}
                    className={cn(
                      'flex items-center justify-between py-2 px-3 rounded-xl transition-colors cursor-pointer',
                      (alert.qty_available ?? alert.qty_on_hand) <= 0 ? 'bg-red-50 hover:bg-red-100' : 'bg-amber-50 hover:bg-amber-100',
                    )}>
                    <div>
                      <p className="text-xs font-semibold text-foreground">{alert.product_name ?? alert.sku}</p>
                      <p className="text-[11px] text-muted-foreground font-medium flex items-center gap-1">
                        <span className="inline-block w-1.5 h-1.5 rounded-full bg-slate-400" />
                        {alert.warehouse_name ?? 'Sin bodega'}
                      </p>
                    </div>
                    <div className="text-right">
                      <div className="flex items-center gap-1.5">
                        <span className={cn(
                          'text-sm font-extrabold',
                          (alert.qty_available ?? alert.qty_on_hand) <= 0 ? 'text-red-600' : 'text-amber-600',
                        )}>
                          {alert.qty_available != null ? Math.floor(alert.qty_available) : alert.qty_on_hand}
                        </span>
                        <span className="text-[10px] text-muted-foreground">disp.</span>
                      </div>
                      {alert.qty_reserved > 0 && (
                        <p className="text-[9px] text-orange-500">{Math.floor(alert.qty_reserved)} reserv.</p>
                      )}
                      <p className="text-[9px] text-muted-foreground">min: {alert.reorder_point}</p>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="flex flex-col items-center py-6 text-sm text-muted-foreground">
                <CheckCircle className="h-8 w-8 text-emerald-400 mb-2" />
                Sin alertas de stock
              </div>
            )
          )}
        </Section>
      </div>

      {/* ─── Type breakdowns ─── */}
      {((data?.product_type_breakdown?.length ?? 0) > 0 || (data?.supplier_type_breakdown?.length ?? 0) > 0) && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {(data?.product_type_breakdown?.length ?? 0) > 0 && (() => {
            const maxCount = Math.max(...data!.product_type_breakdown.map(i => i.count), 1)
            return (
              <Section title="Productos por tipo" icon={Package} iconColor="bg-primary">
                <div className="space-y-2">
                  {data!.product_type_breakdown.map(item => {
                    const pct = Math.round((item.count / maxCount) * 100)
                    return (
                      <div key={item.id} className="flex items-center gap-3">
                        <div className="h-3 rounded-full flex-1 bg-muted overflow-hidden">
                          <div className="h-full rounded-full transition-all"
                            style={{ width: `${pct}%`, backgroundColor: item.color ?? '#6366f1' }} />
                        </div>
                        <span className="shrink-0 rounded-full px-2.5 py-0.5 text-[10px] font-semibold text-white"
                          style={{ backgroundColor: item.color ?? '#6366f1' }}>{item.name}</span>
                        <span className="shrink-0 text-xs font-bold text-foreground w-8 text-right">{item.count}</span>
                      </div>
                    )
                  })}
                </div>
              </Section>
            )
          })()}
          {(data?.supplier_type_breakdown?.length ?? 0) > 0 && (() => {
            const maxCount = Math.max(...data!.supplier_type_breakdown.map(i => i.count), 1)
            return (
              <Section title="Proveedores por tipo" icon={Truck} iconColor="bg-amber-500">
                <div className="space-y-2">
                  {data!.supplier_type_breakdown.map(item => {
                    const pct = Math.round((item.count / maxCount) * 100)
                    return (
                      <div key={item.id} className="flex items-center gap-3">
                        <div className="h-3 rounded-full flex-1 bg-muted overflow-hidden">
                          <div className="h-full rounded-full transition-all"
                            style={{ width: `${pct}%`, backgroundColor: item.color ?? '#f59e0b' }} />
                        </div>
                        <span className="shrink-0 rounded-full px-2.5 py-0.5 text-[10px] font-semibold text-white"
                          style={{ backgroundColor: item.color ?? '#f59e0b' }}>{item.name}</span>
                        <span className="shrink-0 text-xs font-bold text-foreground w-8 text-right">{item.count}</span>
                      </div>
                    )
                  })}
                </div>
              </Section>
            )
          })()}
        </div>
      )}

      {/* ─── Events section ─── */}
      {((data?.event_summary?.length ?? 0) > 0 || (data?.event_type_summary?.length ?? 0) > 0) && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* By severity */}
          {(data?.event_summary?.length ?? 0) > 0 && (
            <Section title="Eventos abiertos por severidad" icon={AlertTriangle} iconColor="bg-red-500">
              <div className="space-y-2">
                {data!.event_summary.map(item => {
                  const maxCount = Math.max(...data!.event_summary.map(i => i.count), 1)
                  const pct = Math.round((item.count / maxCount) * 100)
                  const sevColors: Record<string, string> = {
                    Crítica: '#ef4444', Alta: '#f97316', Media: '#f59e0b', Baja: '#3b82f6',
                  }
                  const color = sevColors[item.severity] ?? '#64748b'
                  return (
                    <div key={item.severity} className="flex items-center gap-3">
                      <div className="h-3 rounded-full flex-1 bg-muted overflow-hidden">
                        <div className="h-full rounded-full transition-all" style={{ width: `${pct}%`, backgroundColor: color }} />
                      </div>
                      <span className="shrink-0 rounded-full px-2.5 py-0.5 text-[10px] font-semibold text-white" style={{ backgroundColor: color }}>
                        {item.severity}
                      </span>
                      <span className="shrink-0 text-xs font-bold text-foreground w-8 text-right">{item.count}</span>
                    </div>
                  )
                })}
              </div>
            </Section>
          )}
          {/* By event type */}
          {(data?.event_type_summary?.length ?? 0) > 0 && (
            <Section title="Eventos abiertos por tipo" icon={AlertTriangle} iconColor="bg-amber-500">
              <div className="space-y-2">
                {data!.event_type_summary.map(item => {
                  const maxCount = Math.max(...data!.event_type_summary.map(i => i.count), 1)
                  const pct = Math.round((item.count / maxCount) * 100)
                  const color = item.color ?? '#6366f1'
                  return (
                    <div key={item.type_name} className="flex items-center gap-3">
                      <div className="h-3 rounded-full flex-1 bg-muted overflow-hidden">
                        <div className="h-full rounded-full transition-all" style={{ width: `${pct}%`, backgroundColor: color }} />
                      </div>
                      <span className="shrink-0 rounded-full px-2.5 py-0.5 text-[10px] font-semibold text-white" style={{ backgroundColor: color }}>
                        {item.type_name}
                      </span>
                      <span className="shrink-0 text-xs font-bold text-foreground w-8 text-right">{item.count}</span>
                    </div>
                  )
                })}
              </div>
            </Section>
          )}
        </div>
      )}

      {/* ─── OCCUPATION ─── */}
      <OccupationSection />

      {/* ─── ABC ─── */}
      <ABCSection />

      {/* ─── Policy + Storage side by side ─── */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="rounded-lg border border-border bg-card p-5">
          <StockPolicySection />
        </div>
        <div className="rounded-lg border border-border bg-card p-5">
          <StorageValuationSection />
        </div>
      </div>


      {/* ─── DEMO DATA ─── */}
      <DemoDataSection />
    </div>
  )
}
