import { useState, useEffect } from 'react'
import { useLocation } from 'react-router-dom'
import {
  Factory, Plus, Trash2, Eye, Clock, CheckCircle2, XCircle, AlertTriangle,
  PackageCheck, Play, Square, Lock, Send, PackageOpen, BarChart3, Loader2, FileText, FolderOpen,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import {
  useProductionRuns, useProductionRun, useCreateProductionRun, useUpdateProductionRun,
  useReleaseProductionRun, useCancelProductionRun, useCloseProductionRun, useDeleteProductionRun,
  useProductionEmissions, useCreateProductionEmission,
  useProductionReceipts, useCreateProductionReceipt,
  useRecipes, useWarehouses, useProducts, useStockLevels,
} from '@/hooks/useInventory'
import { useToast } from '@/store/toast'
import { useConfirm } from '@/store/confirm'
import MediaPickerModal from '@/components/compliance/MediaPickerModal'
import { mediaApi, mediaFileUrl } from '@/lib/media-api'
import type { ProductionRun, ProductionRunStatus } from '@/types/inventory'

// ── Status config ───────────────────────────────────────────────────────────

const STATUS_COLORS: Record<string, string> = {
  planned: 'bg-secondary text-muted-foreground',
  released: 'bg-blue-100 text-blue-700',
  in_progress: 'bg-amber-100 text-amber-700',
  completed: 'bg-emerald-100 text-emerald-700',
  closed: 'bg-secondary text-muted-foreground',
  canceled: 'bg-red-100 text-red-600',
  rejected: 'bg-red-100 text-red-600',
}

const STATUS_LABELS: Record<string, string> = {
  planned: 'Planificada',
  released: 'Liberada',
  in_progress: 'En produccion',
  completed: 'Completada',
  closed: 'Cerrada',
  canceled: 'Cancelada',
  rejected: 'Rechazada',
}

const STATUS_ICONS: Record<string, typeof Clock> = {
  planned: Clock,
  released: Play,
  in_progress: Factory,
  completed: CheckCircle2,
  closed: Lock,
  canceled: XCircle,
  rejected: XCircle,
}

const ORDER_TYPE_LABELS: Record<string, string> = {
  standard: 'Estandar',
  special: 'Especial',
  disassembly: 'Desmontaje',
}

const STATUS_TABS: { key: string; label: string }[] = [
  { key: '', label: 'Todas' },
  { key: 'planned', label: 'Planificadas' },
  { key: 'released', label: 'Liberadas' },
  { key: 'in_progress', label: 'En produccion' },
  { key: 'completed', label: 'Completadas' },
  { key: 'closed', label: 'Cerradas' },
]

// ── Main page ───────────────────────────────────────────────────────────────

export function ProductionPage() {
  const [statusFilter, setStatusFilter] = useState('')
  const [showCreate, setShowCreate] = useState(false)
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const location = useLocation()
  useEffect(() => { setSelectedId(null); setShowCreate(false) }, [location.key])

  const { data, isLoading } = useProductionRuns({ status: statusFilter || undefined })
  const runs = data?.items ?? []
  const toast = useToast()

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Factory className="h-6 w-6 text-foreground" />
          <h1 className="text-2xl font-bold">Produccion</h1>
        </div>
        <button onClick={() => { setShowCreate(true); setSelectedId(null) }}
          className="flex items-center gap-1 px-4 py-2 text-sm bg-gray-900 text-white rounded-xl hover:bg-gray-800">
          <Plus className="h-4 w-4" /> Nueva orden
        </button>
      </div>

      {/* Status tabs */}
      <div className="flex gap-1.5 flex-wrap">
        {STATUS_TABS.map(t => (
          <button key={t.key} onClick={() => setStatusFilter(t.key)}
            className={cn('px-3 py-1.5 text-xs font-medium rounded-full border transition-colors',
              statusFilter === t.key ? 'bg-gray-900 text-white border-gray-900' : 'bg-card text-muted-foreground border-border hover:border-gray-400'
            )}>
            {t.label}
          </button>
        ))}
      </div>

      {/* Table */}
      {isLoading ? (
        <div className="text-center py-16 text-muted-foreground"><Loader2 className="h-6 w-6 animate-spin mx-auto" /></div>
      ) : runs.length === 0 ? (
        <div className="text-center py-16 text-muted-foreground">Sin ordenes de produccion</div>
      ) : (
        <div className="bg-card rounded-xl border overflow-hidden">
          <table className="w-full text-sm">
            <thead><tr className="border-b bg-muted">
              <th className="p-3 text-left"># Orden</th>
              <th className="p-3 text-left">Tipo</th>
              <th className="p-3 text-left">Estado</th>
              <th className="p-3 text-left">Receta</th>
              <th className="p-3 text-right">Multiplicador</th>
              <th className="p-3 text-right">Prioridad</th>
              <th className="p-3 text-left">Fecha</th>
              <th className="p-3"></th>
            </tr></thead>
            <tbody>
              {runs.map(run => {
                const Icon = STATUS_ICONS[run.status] ?? Clock
                return (
                  <tr key={run.id} className="border-b border-gray-50 hover:bg-muted/50 cursor-pointer" onClick={() => setSelectedId(run.id)}>
                    <td className="p-3 font-mono text-xs font-medium">{run.run_number}</td>
                    <td className="p-3 text-xs text-muted-foreground">{ORDER_TYPE_LABELS[run.order_type] ?? run.order_type}</td>
                    <td className="p-3">
                      <span className={cn('inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-semibold', STATUS_COLORS[run.status])}>
                        <Icon className="h-3 w-3" /> {STATUS_LABELS[run.status] ?? run.status}
                      </span>
                    </td>
                    <td className="p-3 text-muted-foreground text-xs">{run.recipe_id.slice(0, 8)}...</td>
                    <td className="p-3 text-right font-mono">{run.multiplier}x</td>
                    <td className="p-3 text-right">{run.priority}</td>
                    <td className="p-3 text-xs text-muted-foreground">{new Date(run.created_at).toLocaleDateString('es-CO')}</td>
                    <td className="p-3 text-right">
                      <button onClick={e => { e.stopPropagation(); setSelectedId(run.id) }} className="text-xs text-primary hover:underline">
                        <Eye className="h-3.5 w-3.5" />
                      </button>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}

      {/* Create modal */}
      {showCreate && <CreateRunModal onClose={() => setShowCreate(false)} />}

      {/* Detail drawer */}
      {selectedId && <RunDetail runId={selectedId} onClose={() => setSelectedId(null)} />}
    </div>
  )
}

// ── Create modal ────────────────────────────────────────────────────────────

function CreateRunModal({ onClose }: { onClose: () => void }) {
  const create = useCreateProductionRun()
  const { data: recipesData } = useRecipes()
  const { data: whData } = useWarehouses()
  const toast = useToast()
  const recipes = Array.isArray(recipesData) ? recipesData : recipesData?.items ?? []
  const warehouses = Array.isArray(whData) ? whData : whData?.items ?? []

  const [form, setForm] = useState({
    recipe_id: '', warehouse_id: '', output_warehouse_id: '', multiplier: '1',
    order_type: 'standard', priority: '50', notes: '',
  })

  async function handleCreate() {
    if (!form.recipe_id || !form.warehouse_id) return
    try {
      await create.mutateAsync({
        recipe_id: form.recipe_id,
        warehouse_id: form.warehouse_id,
        output_warehouse_id: form.output_warehouse_id || undefined,
        multiplier: form.multiplier,
        order_type: form.order_type,
        priority: Number(form.priority),
        notes: form.notes || undefined,
      })
      toast.success('Orden de produccion creada')
      onClose()
    } catch (err: any) { toast.error(err.message) }
  }

  const inputCls = "w-full bg-muted border border-border rounded-xl px-3 py-2.5 text-sm outline-none focus:bg-card focus:ring-2 focus:ring-gray-900/10"

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm" onClick={onClose}>
      <div className="bg-card rounded-2xl p-6 w-full max-w-lg shadow-2xl" onClick={e => e.stopPropagation()}>
        <h3 className="text-lg font-semibold mb-4">Nueva orden de produccion</h3>
        <div className="grid grid-cols-2 gap-3">
          <div className="col-span-2"><label className="text-xs text-muted-foreground">Receta *</label>
            <select value={form.recipe_id} onChange={e => setForm(f => ({...f, recipe_id: e.target.value}))} className={inputCls}>
              <option value="">Seleccionar...</option>
              {recipes.filter(r => r.is_active).map(r => <option key={r.id} value={r.id}>{r.name}</option>)}
            </select>
          </div>
          <div><label className="text-xs text-muted-foreground">Bodega componentes *</label>
            <select value={form.warehouse_id} onChange={e => setForm(f => ({...f, warehouse_id: e.target.value}))} className={inputCls}>
              <option value="">Seleccionar...</option>
              {warehouses.map(w => <option key={w.id} value={w.id}>{w.name}</option>)}
            </select>
          </div>
          <div><label className="text-xs text-muted-foreground">Bodega salida</label>
            <select value={form.output_warehouse_id} onChange={e => setForm(f => ({...f, output_warehouse_id: e.target.value}))} className={inputCls}>
              <option value="">Misma bodega</option>
              {warehouses.map(w => <option key={w.id} value={w.id}>{w.name}</option>)}
            </select>
          </div>
          <div><label className="text-xs text-muted-foreground">Tipo</label>
            <select value={form.order_type} onChange={e => setForm(f => ({...f, order_type: e.target.value}))} className={inputCls}>
              <option value="standard">Estandar</option>
              <option value="special">Especial</option>
              <option value="disassembly">Desmontaje</option>
            </select>
          </div>
          <div><label className="text-xs text-muted-foreground">Multiplicador</label>
            <input type="number" min="1" value={form.multiplier} onChange={e => setForm(f => ({...f, multiplier: e.target.value}))} className={inputCls} />
          </div>
          <div><label className="text-xs text-muted-foreground">Prioridad (0-100)</label>
            <input type="number" min="0" max="100" value={form.priority} onChange={e => setForm(f => ({...f, priority: e.target.value}))} className={inputCls} />
          </div>
          <div className="col-span-2"><label className="text-xs text-muted-foreground">Notas</label>
            <textarea value={form.notes} onChange={e => setForm(f => ({...f, notes: e.target.value}))} rows={2} className={inputCls} />
          </div>
        </div>
        <div className="flex gap-3 mt-4">
          <button onClick={onClose} className="flex-1 bg-secondary text-foreground rounded-xl px-4 py-2.5 text-sm">Cancelar</button>
          <button onClick={handleCreate} disabled={create.isPending || !form.recipe_id || !form.warehouse_id}
            className="flex-1 bg-gray-900 text-white rounded-xl px-4 py-2.5 text-sm font-semibold disabled:opacity-50">
            {create.isPending ? 'Creando...' : 'Crear'}
          </button>
        </div>
      </div>
    </div>
  )
}

// ── Run Detail ──────────────────────────────────────────────────────────────

function RunDetail({ runId, onClose }: { runId: string; onClose: () => void }) {
  const { data: run, isLoading } = useProductionRun(runId)
  const { data: emissions } = useProductionEmissions(runId)
  const { data: receipts } = useProductionReceipts(runId)
  const { data: recipesData } = useRecipes()
  const { data: whData } = useWarehouses()
  const toast = useToast()
  const confirm = useConfirm()

  const release = useReleaseProductionRun()
  const cancel = useCancelProductionRun()
  const close = useCloseProductionRun()
  const del = useDeleteProductionRun()
  const createEmission = useCreateProductionEmission()
  const createReceipt = useCreateProductionReceipt()

  const [tab, setTab] = useState<'general' | 'emissions' | 'receipts' | 'costs' | 'docs'>('general')

  if (isLoading || !run) return null

  const recipes = Array.isArray(recipesData) ? recipesData : recipesData?.items ?? []
  const warehouses = Array.isArray(whData) ? whData : whData?.items ?? []
  const recipe = recipes.find(r => r.id === run.recipe_id)
  const whName = (id: string) => warehouses.find(w => w.id === id)?.name ?? id.slice(0, 8)
  const Icon = STATUS_ICONS[run.status] ?? Clock

  async function handleRelease() {
    try { await release.mutateAsync(runId); toast.success('Orden liberada — componentes reservados') } catch (e: any) { toast.error(e.message) }
  }
  async function handleCancel() {
    const ok = await confirm({ title: 'Cancelar orden', message: 'Se liberaran las reservas de stock. Continuar?', confirmLabel: 'Cancelar orden', destructive: true })
    if (ok) { try { await cancel.mutateAsync(runId); toast.success('Orden cancelada') } catch (e: any) { toast.error(e.message) } }
  }
  async function handleEmit() {
    try { await createEmission.mutateAsync({ runId }); toast.success('Emision creada — componentes sacados de inventario') } catch (e: any) { toast.error(e.message) }
  }
  async function handleReceive() {
    try { await createReceipt.mutateAsync({ runId }); toast.success('Recibo creado — producto terminado en inventario') } catch (e: any) { toast.error(e.message) }
  }
  async function handleClose() {
    try { await close.mutateAsync(runId); toast.success('Orden cerrada — variaciones calculadas') } catch (e: any) { toast.error(e.message) }
  }
  async function handleDelete() {
    const ok = await confirm({ title: 'Eliminar orden', message: `Eliminar ${run.run_number}?`, confirmLabel: 'Eliminar', destructive: true })
    if (ok) { try { await del.mutateAsync(runId); toast.success('Eliminada'); onClose() } catch (e: any) { toast.error(e.message) } }
  }

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-black/40" onClick={onClose}>
      <div className="bg-card w-full max-w-2xl h-full overflow-y-auto shadow-2xl" onClick={e => e.stopPropagation()}>
        {/* Header */}
        <div className="sticky top-0 bg-card border-b px-6 py-4 z-10">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-lg font-bold">{run.run_number}</h2>
              <div className="flex items-center gap-2 mt-1">
                <span className={cn('inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-semibold', STATUS_COLORS[run.status])}>
                  <Icon className="h-3 w-3" /> {STATUS_LABELS[run.status]}
                </span>
                <span className="text-xs text-muted-foreground">{ORDER_TYPE_LABELS[run.order_type]}</span>
                <span className="text-xs text-muted-foreground">Prioridad: {run.priority}</span>
              </div>
            </div>
            <button onClick={onClose} className="text-muted-foreground hover:text-muted-foreground text-xl">&times;</button>
          </div>

          {/* Actions */}
          <div className="flex gap-2 mt-3 flex-wrap">
            {run.status === 'planned' && <>
              <button onClick={handleRelease} disabled={release.isPending}
                className="px-3 py-1.5 text-xs font-semibold bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50">
                {release.isPending ? 'Liberando...' : 'Liberar'}
              </button>
              <button onClick={handleCancel} className="px-3 py-1.5 text-xs text-red-600 border border-red-200 rounded-lg hover:bg-red-50">Cancelar</button>
              <button onClick={handleDelete} className="px-3 py-1.5 text-xs text-red-600 border border-red-200 rounded-lg hover:bg-red-50">Eliminar</button>
            </>}
            {run.status === 'released' && <>
              <button onClick={handleEmit} disabled={createEmission.isPending}
                className="px-3 py-1.5 text-xs font-semibold bg-amber-600 text-white rounded-lg hover:bg-amber-700 disabled:opacity-50">
                {createEmission.isPending ? 'Emitiendo...' : 'Emitir componentes'}
              </button>
              <button onClick={handleCancel} className="px-3 py-1.5 text-xs text-red-600 border border-red-200 rounded-lg hover:bg-red-50">Cancelar</button>
            </>}
            {run.status === 'in_progress' && <>
              <button onClick={handleReceive} disabled={createReceipt.isPending}
                className="px-3 py-1.5 text-xs font-semibold bg-emerald-600 text-white rounded-lg hover:bg-emerald-700 disabled:opacity-50">
                {createReceipt.isPending ? 'Recibiendo...' : 'Recibir producto'}
              </button>
            </>}
            {run.status === 'completed' && <>
              <button onClick={handleClose} disabled={close.isPending}
                className="px-3 py-1.5 text-xs font-semibold bg-gray-700 text-white rounded-lg hover:bg-gray-800 disabled:opacity-50">
                {close.isPending ? 'Cerrando...' : 'Cerrar orden'}
              </button>
            </>}
          </div>

          {/* Tabs */}
          <div className="flex gap-1 mt-3 border-b -mb-[1px]">
            {(['general', 'emissions', 'receipts', 'costs', 'docs'] as const).map(t => (
              <button key={t} onClick={() => setTab(t)}
                className={cn('px-3 py-1.5 text-xs font-medium border-b-2 transition-colors',
                  tab === t ? 'border-gray-900 text-foreground' : 'border-transparent text-muted-foreground hover:text-muted-foreground'
                )}>
                {t === 'general' ? 'General' : t === 'emissions' ? `Emisiones (${emissions?.length ?? 0})` : t === 'receipts' ? `Recibos (${receipts?.length ?? 0})` : t === 'costs' ? 'Costos' : 'Documentos'}
              </button>
            ))}
          </div>
        </div>

        {/* Content */}
        <div className="px-6 py-4">
          {tab === 'general' && (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <InfoField label="Receta" value={recipe?.name ?? run.recipe_id.slice(0, 8)} />
                <InfoField label="Multiplicador" value={`${run.multiplier}x`} />
                <InfoField label="Bodega componentes" value={whName(run.warehouse_id)} />
                <InfoField label="Bodega salida" value={run.output_warehouse_id ? whName(run.output_warehouse_id) : 'Misma bodega'} />
                <InfoField label="Fecha inicio planificada" value={run.planned_start_date ? new Date(run.planned_start_date).toLocaleDateString('es-CO') : '—'} />
                <InfoField label="Fecha fin planificada" value={run.planned_end_date ? new Date(run.planned_end_date).toLocaleDateString('es-CO') : '—'} />
                <InfoField label="Inicio real" value={run.actual_start_date ? new Date(run.actual_start_date).toLocaleString('es-CO') : '—'} />
                <InfoField label="Fin real" value={run.actual_end_date ? new Date(run.actual_end_date).toLocaleString('es-CO') : '—'} />
              </div>
              {run.notes && <div className="bg-muted rounded-xl p-3"><p className="text-xs text-muted-foreground uppercase font-bold mb-1">Notas</p><p className="text-sm text-foreground">{run.notes}</p></div>}

              {/* Components from recipe */}
              {recipe && recipe.components.length > 0 && (
                <div>
                  <p className="text-xs font-bold text-muted-foreground uppercase mb-2">Componentes (BOM)</p>
                  <div className="bg-card border rounded-xl overflow-hidden">
                    <table className="w-full text-xs">
                      <thead><tr className="bg-muted text-muted-foreground">
                        <th className="p-2 text-left">Componente</th>
                        <th className="p-2 text-right">Cant. base</th>
                        <th className="p-2 text-right">x{run.multiplier}</th>
                        <th className="p-2 text-right">Merma %</th>
                      </tr></thead>
                      <tbody>
                        {recipe.components.map(c => (
                          <tr key={c.id} className="border-t border-gray-50">
                            <td className="p-2 font-medium">{c.component_entity_id.slice(0, 12)}...</td>
                            <td className="p-2 text-right font-mono">{c.quantity_required}</td>
                            <td className="p-2 text-right font-mono font-bold">{(Number(c.quantity_required) * Number(run.multiplier)).toFixed(2)}</td>
                            <td className="p-2 text-right">{c.scrap_percentage ?? '0'}%</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </div>
          )}

          {tab === 'emissions' && (
            <div className="space-y-3">
              {!emissions || emissions.length === 0 ? (
                <div className="text-center py-10 text-muted-foreground text-sm">Sin emisiones registradas</div>
              ) : emissions.map(em => (
                <div key={em.id} className="bg-card border rounded-xl p-4">
                  <div className="flex items-center justify-between mb-2">
                    <span className="font-mono text-xs font-bold">{em.emission_number}</span>
                    <span className="text-xs text-muted-foreground">{new Date(em.emission_date).toLocaleString('es-CO')}</span>
                  </div>
                  <table className="w-full text-xs">
                    <thead><tr className="text-muted-foreground">
                      <th className="text-left pb-1">Componente</th>
                      <th className="text-right pb-1">Planificado</th>
                      <th className="text-right pb-1">Emitido</th>
                      <th className="text-right pb-1">Costo</th>
                    </tr></thead>
                    <tbody>
                      {em.lines.map(l => (
                        <tr key={l.id} className="border-t border-gray-50">
                          <td className="py-1">{l.component_entity_id.slice(0, 12)}...</td>
                          <td className="py-1 text-right font-mono">{l.planned_quantity}</td>
                          <td className="py-1 text-right font-mono font-bold">{l.actual_quantity}</td>
                          <td className="py-1 text-right font-mono">${Number(l.total_cost).toLocaleString()}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ))}
            </div>
          )}

          {tab === 'receipts' && (
            <div className="space-y-3">
              {!receipts || receipts.length === 0 ? (
                <div className="text-center py-10 text-muted-foreground text-sm">Sin recibos registrados</div>
              ) : receipts.map(rc => (
                <div key={rc.id} className="bg-card border rounded-xl p-4">
                  <div className="flex items-center justify-between mb-2">
                    <span className="font-mono text-xs font-bold">{rc.receipt_number}</span>
                    <span className="text-xs text-muted-foreground">{new Date(rc.receipt_date).toLocaleString('es-CO')}</span>
                  </div>
                  <table className="w-full text-xs">
                    <thead><tr className="text-muted-foreground">
                      <th className="text-left pb-1">Producto</th>
                      <th className="text-right pb-1">Planificado</th>
                      <th className="text-right pb-1">Recibido</th>
                      <th className="text-right pb-1">Costo unit.</th>
                      <th className="text-right pb-1">Total</th>
                    </tr></thead>
                    <tbody>
                      {rc.lines.map(l => (
                        <tr key={l.id} className="border-t border-gray-50">
                          <td className="py-1">{l.entity_id.slice(0, 12)}...</td>
                          <td className="py-1 text-right font-mono">{l.planned_quantity}</td>
                          <td className="py-1 text-right font-mono font-bold">{l.received_quantity}</td>
                          <td className="py-1 text-right font-mono">${Number(l.unit_cost).toFixed(4)}</td>
                          <td className="py-1 text-right font-mono">${Number(l.total_cost).toLocaleString()}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ))}
            </div>
          )}

          {tab === 'costs' && (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="bg-card border rounded-xl p-4">
                  <p className="text-xs text-muted-foreground mb-1">Costo componentes</p>
                  <p className="text-xl font-bold">${Number(run.total_component_cost ?? 0).toLocaleString()}</p>
                </div>
                <div className="bg-card border rounded-xl p-4">
                  <p className="text-xs text-muted-foreground mb-1">Costo produccion total</p>
                  <p className="text-xl font-bold">${Number(run.total_production_cost ?? 0).toLocaleString()}</p>
                </div>
                <div className="bg-card border rounded-xl p-4">
                  <p className="text-xs text-muted-foreground mb-1">Costo unitario</p>
                  <p className="text-xl font-bold">${Number(run.unit_production_cost ?? 0).toFixed(4)}</p>
                </div>
                <div className="bg-card border rounded-xl p-4">
                  <p className="text-xs text-muted-foreground mb-1">Cantidad producida</p>
                  <p className="text-xl font-bold">{run.actual_output_quantity ?? '—'}</p>
                </div>
              </div>
              {run.status === 'closed' && (
                <div className={cn('border rounded-xl p-4', Number(run.variance_amount ?? 0) === 0 ? 'bg-emerald-50 border-emerald-200' : 'bg-amber-50 border-amber-200')}>
                  <p className="text-xs text-muted-foreground mb-1">Variacion (costo real vs estandar)</p>
                  <p className="text-2xl font-bold">${Number(run.variance_amount ?? 0).toLocaleString()}</p>
                  {Number(run.variance_amount ?? 0) === 0 && <p className="text-xs text-emerald-600 mt-1">Sin variacion — produccion conforme al estandar</p>}
                </div>
              )}
            </div>
          )}

          {tab === 'docs' && (
            <DocsTab runId={runId} />
          )}
        </div>
      </div>
    </div>
  )
}

function DocsTab({ runId }: { runId: string }) {
  const [showPicker, setShowPicker] = useState(false)
  const [docs, setDocs] = useState<Array<{ media_file_id: string; url: string; name: string }>>([])

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <p className="text-sm font-semibold text-foreground">Documentos adjuntos</p>
        <button onClick={() => setShowPicker(true)}
          className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold bg-primary text-white rounded-lg hover:bg-primary/90">
          <FolderOpen className="h-3.5 w-3.5" /> Adjuntar desde Media
        </button>
      </div>
      {docs.length === 0 ? (
        <button onClick={() => setShowPicker(true)}
          className="w-full rounded-xl border-2 border-dashed border-border p-8 text-center hover:border-primary/30 hover:bg-primary/5 transition-colors group">
          <FolderOpen className="h-8 w-8 text-gray-200 mx-auto mb-2 group-hover:text-primary/40" />
          <p className="text-sm text-muted-foreground">Sin documentos adjuntos</p>
          <p className="text-xs text-muted-foreground">Adjunta instrucciones, fotos de QC, reportes de produccion</p>
        </button>
      ) : (
        <div className="space-y-2">
          {docs.map((d, i) => (
            <div key={i} className="flex items-center gap-3 bg-card border rounded-xl px-4 py-3">
              <FileText className="h-4 w-4 text-muted-foreground" />
              <span className="text-sm font-medium flex-1">{d.name}</span>
              <a href={mediaFileUrl(d.url)} target="_blank" rel="noopener noreferrer" className="text-xs text-primary hover:underline">Abrir</a>
              <button onClick={() => setDocs(ds => ds.filter((_, j) => j !== i))} className="text-xs text-red-500 hover:underline">Quitar</button>
            </div>
          ))}
        </div>
      )}
      <MediaPickerModal
        open={showPicker}
        onClose={() => setShowPicker(false)}
        onSelect={async (mid: string) => {
          const file = await mediaApi.get(mid)
          setDocs(ds => [...ds, { media_file_id: file.id, url: file.url, name: file.original_filename }])
          setShowPicker(false)
        }}
      />
    </div>
  )
}

function InfoField({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="text-sm font-medium text-foreground">{value}</p>
    </div>
  )
}
