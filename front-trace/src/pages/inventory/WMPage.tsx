import { useEffect, useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { Boxes, Layers, MapPin, Truck, BarChart3, RefreshCw } from 'lucide-react'

import { useWarehouses } from '@/hooks/useInventory'
import {
  useEmptyBinReport, useERI, useMovementOrders, useOperationTypes, useSetWMConfig,
  useStockStatus, useStorageTypes, useWMConfig, useWMRoutes,
} from '@/hooks/useWM'
import { wmApi } from '@/lib/wm-api'
import { useToast } from '@/store/toast'

type Tab = 'config' | 'locations' | 'movements' | 'inventory'

export default function WMPage() {
  const { data: warehouses = [] } = useWarehouses()
  const [wh, setWh] = useState<string>('')
  const [tab, setTab] = useState<Tab>('config')

  useEffect(() => {
    if (!wh && warehouses.length) setWh(warehouses[0].id)
  }, [warehouses, wh])

  return (
    <div className="p-6 max-w-6xl mx-auto">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h1 className="text-xl font-bold text-foreground flex items-center gap-2">
            <Boxes className="h-5 w-5" /> Gestión de Almacén (WM)
          </h1>
          <p className="text-sm text-muted-foreground">
            Tipos de almacén, ubicaciones, rutas multietapa y órdenes de movimiento interno.
          </p>
        </div>
        <select value={wh} onChange={e => setWh(e.target.value)}
          className="rounded-lg border border-border bg-card px-3 py-2 text-sm">
          {warehouses.map(w => <option key={w.id} value={w.id}>{w.name}</option>)}
        </select>
      </div>

      <div className="flex gap-1 border-b border-border mb-5">
        {([
          ['config', 'Configuración', Truck],
          ['locations', 'Ubicaciones', MapPin],
          ['movements', 'Órdenes de movimiento', Layers],
          ['inventory', 'Inventario', BarChart3],
        ] as [Tab, string, typeof Truck][]).map(([k, label, Icon]) => (
          <button key={k} onClick={() => setTab(k)}
            className={`flex items-center gap-1.5 px-3 py-2 text-sm border-b-2 -mb-px ${
              tab === k ? 'border-primary text-foreground font-medium' : 'border-transparent text-muted-foreground'
            }`}>
            <Icon className="h-4 w-4" />{label}
          </button>
        ))}
      </div>

      {!wh ? <p className="text-muted-foreground text-sm">Seleccioná un almacén.</p> : (
        <>
          {tab === 'config' && <ConfigTab wh={wh} />}
          {tab === 'locations' && <LocationsTab wh={wh} />}
          {tab === 'movements' && <MovementsTab wh={wh} />}
          {tab === 'inventory' && <InventoryTab wh={wh} />}
        </>
      )}
    </div>
  )
}

// ─── Configuración + rutas ────────────────────────────────────────────────────
function ConfigTab({ wh }: { wh: string }) {
  const toast = useToast()
  const { data: cfg } = useWMConfig(wh)
  const { data: routes = [] } = useWMRoutes(wh)
  const setCfg = useSetWMConfig(wh)
  const [r, setR] = useState(1); const [d, setD] = useState(1); const [m, setM] = useState(1)

  useEffect(() => {
    if (cfg) { setR(cfg.receive_steps); setD(cfg.deliver_steps); setM(cfg.manufacture_steps) }
  }, [cfg])

  const StepSel = ({ v, set, label }: { v: number; set: (n: number) => void; label: string }) => (
    <label className="flex flex-col gap-1 text-sm">
      <span className="text-muted-foreground">{label}</span>
      <select value={v} onChange={e => set(Number(e.target.value))}
        className="rounded-lg border border-border bg-card px-3 py-2">
        <option value={1}>1 paso</option><option value={2}>2 pasos</option><option value={3}>3 pasos</option>
      </select>
    </label>
  )

  return (
    <div className="space-y-6">
      <div className="rounded-xl border border-border p-4">
        <h2 className="font-semibold mb-3">Pasos por flujo (estilo Odoo)</h2>
        <div className="flex gap-4 flex-wrap">
          <StepSel v={r} set={setR} label="Recepción" />
          <StepSel v={d} set={setD} label="Entrega (pick/pack/out)" />
          <StepSel v={m} set={setM} label="Fabricación" />
          <button
            onClick={() => setCfg.mutate({ receive_steps: r, deliver_steps: d, manufacture_steps: m }, {
              onSuccess: () => toast.success('Configuración guardada · rutas regeneradas'),
              onError: (e: any) => toast.error(e.message),
            })}
            disabled={setCfg.isPending}
            className="self-end h-[38px] px-4 rounded-lg bg-primary text-primary-foreground text-sm font-medium">
            {setCfg.isPending ? 'Guardando…' : 'Guardar y generar rutas'}
          </button>
        </div>
      </div>

      <div className="rounded-xl border border-border p-4">
        <h2 className="font-semibold mb-3">Rutas generadas</h2>
        <div className="space-y-3">
          {routes.map(route => (
            <div key={route.id} className="text-sm">
              <div className="font-medium">{route.name} <span className="text-muted-foreground">({route.flow}, {route.steps} paso/s)</span></div>
              <div className="flex flex-wrap gap-2 mt-1">
                {route.rules.map(ru => (
                  <span key={ru.id} className="px-2 py-0.5 rounded bg-muted text-xs">
                    {ru.sequence}. {ru.name}: {ru.source_zone}→{ru.dest_zone}
                  </span>
                ))}
              </div>
            </div>
          ))}
          {!routes.length && <p className="text-muted-foreground text-sm">Sin rutas — guardá la configuración para generarlas.</p>}
        </div>
      </div>
    </div>
  )
}

// ─── Ubicaciones ──────────────────────────────────────────────────────────────
function LocationsTab({ wh }: { wh: string }) {
  const toast = useToast()
  const qc = useQueryClient()
  const { data: types = [] } = useStorageTypes(wh)
  const { data: report } = useEmptyBinReport(wh)
  const [aisles, setAisles] = useState(2); const [racks, setRacks] = useState(3); const [levels, setLevels] = useState(4)

  const createType = async () => {
    const code = prompt('Código del tipo de almacén (ej. 001):'); if (!code) return
    const name = prompt('Nombre (ej. Rack principal):') || code
    try { await wmApi.createStorageType({ warehouse_id: wh, code, name }); qc.invalidateQueries({ queryKey: ['wm', 'storage-types', wh] }); toast.success('Tipo creado') }
    catch (e: any) { toast.error(e.message) }
  }
  const bulk = async () => {
    try {
      const res = await wmApi.bulkBins({
        warehouse_id: wh,
        segments: [{ start: 1, end: aisles, pad: 1 }, { start: 1, end: racks, pad: 2 }, { start: 1, end: levels, pad: 2 }],
      })
      qc.invalidateQueries({ queryKey: ['wm', 'empty-report', wh] })
      toast.success(`${res.created} ubicaciones creadas (${res.skipped} ya existían)`)
    } catch (e: any) { toast.error(e.message) }
  }

  return (
    <div className="space-y-6">
      <div className="rounded-xl border border-border p-4">
        <div className="flex items-center justify-between mb-3">
          <h2 className="font-semibold">Tipos de almacén</h2>
          <button onClick={createType} className="text-sm px-3 py-1.5 rounded-lg bg-primary text-primary-foreground">+ Nuevo tipo</button>
        </div>
        <div className="flex flex-wrap gap-2">
          {types.map(t => (
            <span key={t.id} className="px-2.5 py-1 rounded bg-muted text-sm">{t.code} · {t.name} <span className="text-muted-foreground">({t.removal_strategy})</span></span>
          ))}
          {!types.length && <p className="text-muted-foreground text-sm">Sin tipos. Creá uno para clasificar las ubicaciones.</p>}
        </div>
      </div>

      <div className="rounded-xl border border-border p-4">
        <h2 className="font-semibold mb-3">Creación masiva de ubicaciones (LS10)</h2>
        <div className="flex gap-3 flex-wrap items-end">
          <NumField label="Pasillos" v={aisles} set={setAisles} />
          <NumField label="Estanterías" v={racks} set={setRacks} />
          <NumField label="Niveles" v={levels} set={setLevels} />
          <button onClick={bulk} className="h-[38px] px-4 rounded-lg bg-primary text-primary-foreground text-sm font-medium">
            Generar {aisles * racks * levels} bins
          </button>
        </div>
        <p className="text-xs text-muted-foreground mt-2">Genera códigos tipo 1-01-01 … {aisles}-{String(racks).padStart(2, '0')}-{String(levels).padStart(2, '0')}.</p>
      </div>

      {report && (
        <div className="rounded-xl border border-border p-4">
          <h2 className="font-semibold mb-2">Ocupación</h2>
          <div className="flex items-center gap-6 text-sm">
            <div><div className="text-2xl font-bold">{report.total_bins}</div><div className="text-muted-foreground">bins</div></div>
            <div><div className="text-2xl font-bold">{report.empty_bins}</div><div className="text-muted-foreground">vacíos</div></div>
            <div><div className="text-2xl font-bold">{report.occupancy_pct}%</div><div className="text-muted-foreground">ocupación</div></div>
          </div>
        </div>
      )}
    </div>
  )
}

// ─── Movimientos ──────────────────────────────────────────────────────────────
function MovementsTab({ wh }: { wh: string }) {
  const toast = useToast()
  const qc = useQueryClient()
  const { data: orders = [] } = useMovementOrders(wh)
  const { data: ops = [] } = useOperationTypes()

  const seed = async () => {
    try { await wmApi.seedOperationTypes(); await wmApi.ensureInterim(wh); qc.invalidateQueries({ queryKey: ['wm', 'operation-types'] }); toast.success('Tipos de operación + zonas interim listos') }
    catch (e: any) { toast.error(e.message) }
  }
  const confirm = async (orderId: string, lineId: string) => {
    try { await wmApi.confirmLine(orderId, lineId, { confirm_source: true, confirm_dest: true }); qc.invalidateQueries({ queryKey: ['wm', 'movement-orders', wh] }); toast.success('Línea confirmada') }
    catch (e: any) { toast.error(e.message) }
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <p className="text-sm text-muted-foreground">{ops.length} tipos de operación · {orders.length} órdenes</p>
        <button onClick={seed} className="text-sm px-3 py-1.5 rounded-lg border border-border flex items-center gap-1.5">
          <RefreshCw className="h-4 w-4" /> Inicializar operaciones + zonas
        </button>
      </div>
      <div className="space-y-2">
        {orders.map(o => (
          <div key={o.id} className="rounded-xl border border-border p-3">
            <div className="flex items-center justify-between">
              <span className="font-medium">{o.to_number}</span>
              <span className={`text-xs px-2 py-0.5 rounded ${o.status === 'confirmed' ? 'bg-emerald-50 text-emerald-700' : 'bg-amber-50 text-amber-700'}`}>{o.status}</span>
            </div>
            {o.notes && <p className="text-xs text-muted-foreground mt-0.5">{o.notes}</p>}
            <div className="mt-2 space-y-1">
              {o.lines.map(l => (
                <div key={l.id} className="flex items-center justify-between text-sm">
                  <span>L{l.line_no} · {Number(l.quantity)} {l.uom}</span>
                  {l.status === 'done'
                    ? <span className="text-xs text-emerald-600">✓ confirmada</span>
                    : <button onClick={() => confirm(o.id, l.id)} className="text-xs px-2 py-0.5 rounded bg-primary text-primary-foreground">Confirmar pick+putaway</button>}
                </div>
              ))}
            </div>
          </div>
        ))}
        {!orders.length && <p className="text-muted-foreground text-sm">Sin órdenes de movimiento. Se generan al confirmar ventas/compras o desde las rutas.</p>}
      </div>
    </div>
  )
}

// ─── Inventario / ERI ─────────────────────────────────────────────────────────
function InventoryTab({ wh }: { wh: string }) {
  const { data: status } = useStockStatus(wh)
  const { data: eri } = useERI(wh)
  return (
    <div className="space-y-6">
      <div className="rounded-xl border border-border p-4">
        <h2 className="font-semibold mb-3">Stock por estado</h2>
        <div className="flex gap-4 flex-wrap">
          {status?.buckets.map(b => (
            <div key={b.stock_type} className="rounded-lg bg-muted px-4 py-2 text-sm">
              <div className="text-lg font-bold">{Number(b.total_qty)}</div>
              <div className="text-muted-foreground">{b.stock_type} · {b.quants} quants</div>
            </div>
          ))}
          {!status?.buckets.length && <p className="text-muted-foreground text-sm">Sin stock.</p>}
        </div>
      </div>
      {eri && (
        <div className="rounded-xl border border-border p-4">
          <h2 className="font-semibold mb-2">ERI — Exactitud de Registro de Inventario</h2>
          <div className="flex items-end gap-2">
            <span className={`text-3xl font-bold ${eri.eri_pct >= eri.target_pct ? 'text-emerald-600' : 'text-amber-600'}`}>{eri.eri_pct}%</span>
            <span className="text-sm text-muted-foreground mb-1">/ meta {eri.target_pct}% · {eri.items_accurate}/{eri.items_counted} ítems exactos</span>
          </div>
        </div>
      )}
    </div>
  )
}

function NumField({ label, v, set }: { label: string; v: number; set: (n: number) => void }) {
  return (
    <label className="flex flex-col gap-1 text-sm">
      <span className="text-muted-foreground">{label}</span>
      <input type="number" min={1} max={20} value={v} onChange={e => set(Number(e.target.value))}
        className="w-24 rounded-lg border border-border bg-card px-3 py-2" />
    </label>
  )
}
