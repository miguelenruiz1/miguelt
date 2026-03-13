import { useState, useEffect } from 'react'
import { Factory, Plus, Play, Trash2, Eye, Clock, CheckCircle2, XCircle, AlertTriangle, PackageCheck, PackageX, ShieldCheck, ShieldX, CircleDot, Flag } from 'lucide-react'
import { cn } from '@/lib/utils'
import {
  useProductionRuns, useProductionRun, useCreateProductionRun,
  useExecuteProductionRun, useFinishProductionRun,
  useApproveProductionRun, useRejectProductionRun,
  useDeleteProductionRun,
  useRecipes, useWarehouses, useProducts, useStockLevels,
} from '@/hooks/useInventory'

const STATUS_COLORS: Record<string, string> = {
  pending: 'bg-slate-100 text-slate-600',
  in_progress: 'bg-blue-100 text-blue-700',
  awaiting_approval: 'bg-amber-100 text-amber-700',
  completed: 'bg-emerald-100 text-emerald-700',
  rejected: 'bg-red-100 text-red-700',
  canceled: 'bg-red-100 text-red-700',
}

const STATUS_LABELS: Record<string, string> = {
  pending: 'Pendiente',
  in_progress: 'En progreso',
  awaiting_approval: 'Por aprobar',
  completed: 'Completada',
  rejected: 'Rechazada',
  canceled: 'Cancelada',
}

const STATUS_ICONS: Record<string, typeof Clock> = {
  pending: Clock,
  in_progress: CircleDot,
  awaiting_approval: ShieldCheck,
  completed: CheckCircle2,
  rejected: ShieldX,
  canceled: XCircle,
}

/* ─── Reject Modal ─────────────────────────────────────────────────────────── */

function RejectModal({ onClose, onConfirm, isPending }: {
  onClose: () => void
  onConfirm: (notes: string) => void
  isPending: boolean
}) {
  const [notes, setNotes] = useState('')

  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center bg-black/30 backdrop-blur-sm">
      <div className="w-full max-w-md bg-white rounded-3xl shadow-2xl p-6">
        <h2 className="text-lg font-bold text-slate-900 mb-2">Rechazar corrida</h2>
        <p className="text-sm text-slate-500 mb-4">Indica el motivo del rechazo. La corrida quedará como rechazada y no afectará el stock.</p>
        <textarea
          value={notes}
          onChange={e => setNotes(e.target.value)}
          placeholder="Motivo del rechazo *"
          rows={3}
          className="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-red-400 resize-none"
        />
        <div className="flex gap-3 pt-3">
          <button type="button" onClick={onClose}
            className="flex-1 rounded-xl border border-slate-200 px-4 py-2 text-sm text-slate-600 hover:bg-slate-50">
            Cancelar
          </button>
          <button
            onClick={() => onConfirm(notes)}
            disabled={!notes.trim() || isPending}
            className="flex-1 rounded-xl bg-red-600 px-4 py-2 text-sm font-semibold text-white hover:bg-red-700 disabled:opacity-60"
          >
            {isPending ? 'Rechazando...' : 'Rechazar'}
          </button>
        </div>
      </div>
    </div>
  )
}

/* ─── Run Detail Drawer ─────────────────────────────────────────────────────── */

function RunDrawer({
  runId,
  onClose,
  onExecute,
  onFinish,
  onDelete,
  onApprove,
  onReject,
}: {
  runId: string
  onClose: () => void
  onExecute: (id: string) => void
  onFinish: (id: string) => void
  onDelete: (id: string) => void
  onApprove: (id: string) => void
  onReject: (id: string) => void
}) {
  const { data: run } = useProductionRun(runId)
  const { data: recipes = [] } = useRecipes()
  const { data: warehouses = [] } = useWarehouses()
  const { data: productsData } = useProducts()
  const { data: stockLevels = [] } = useStockLevels(
    run ? { warehouse_id: run.warehouse_id } : undefined
  )
  const [confirmDelete, setConfirmDelete] = useState(false)

  const recipeMap = Object.fromEntries(recipes.map(r => [r.id, r]))
  const whMap = Object.fromEntries(warehouses.map(w => [w.id, w.name]))
  const productMap = Object.fromEntries((productsData?.items ?? []).map(p => [p.id, p.name]))
  const stockMap: Record<string, number> = {}
  for (const s of stockLevels) {
    stockMap[s.product_id] = (stockMap[s.product_id] ?? 0) + Number(s.qty_on_hand) - Number(s.qty_reserved)
  }

  if (!run) return null

  const recipe = recipeMap[run.recipe_id]
  const StatusIcon = STATUS_ICONS[run.status] ?? Clock

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-black/20 backdrop-blur-sm" onClick={onClose}>
      <div className="w-full max-w-md bg-white h-full shadow-2xl p-6 overflow-y-auto" onClick={e => e.stopPropagation()}>
        <div className="flex items-center justify-between mb-6">
          <div>
            <h2 className="font-bold text-slate-900 font-mono">{run.run_number}</h2>
            <div className="flex items-center gap-2 mt-1">
              <StatusIcon className="h-3.5 w-3.5" />
              <span className={cn('rounded-full px-2 py-0.5 text-xs font-semibold', STATUS_COLORS[run.status])}>
                {STATUS_LABELS[run.status] ?? run.status}
              </span>
            </div>
          </div>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-600 text-xl font-bold">x</button>
        </div>

        <div className="space-y-4">
          {/* Recipe Info */}
          <div className="bg-indigo-50 rounded-xl p-4">
            <p className="text-xs font-bold text-indigo-400 uppercase tracking-wide mb-1">Receta</p>
            <p className="font-semibold text-indigo-900">{recipe?.name ?? '—'}</p>
            {recipe && (
              <p className="text-sm text-indigo-600 mt-1">
                Salida: {productMap[recipe.output_entity_id] ?? recipe.output_entity_id.slice(0, 8)} x {recipe.output_quantity}
              </p>
            )}
          </div>

          {/* Run Details */}
          <div className="grid grid-cols-2 gap-3">
            <div className="bg-slate-50 rounded-xl p-3">
              <p className="text-[10px] font-bold text-slate-400 uppercase">Bodega componentes</p>
              <p className="font-medium text-slate-800 text-sm">{whMap[run.warehouse_id] ?? '—'}</p>
            </div>
            <div className="bg-slate-50 rounded-xl p-3">
              <p className="text-[10px] font-bold text-slate-400 uppercase">Bodega destino</p>
              <p className="font-medium text-slate-800 text-sm">{run.output_warehouse_id ? whMap[run.output_warehouse_id] ?? '—' : whMap[run.warehouse_id] ?? '—'}</p>
              {run.output_warehouse_id && run.output_warehouse_id !== run.warehouse_id && (
                <span className="inline-flex rounded-full bg-blue-50 px-1.5 py-0.5 text-[9px] font-bold text-blue-600 mt-1">Diferente</span>
              )}
            </div>
          </div>
          <div className="bg-slate-50 rounded-xl p-3">
            <p className="text-[10px] font-bold text-slate-400 uppercase">Multiplicador</p>
            <p className="font-bold text-slate-900 text-sm">{run.multiplier}x</p>
          </div>

          {/* Components with stock availability */}
          {recipe?.components?.length ? (() => {
            const allSufficient = recipe.components.every(c => {
              const required = Number(c.quantity_required) * Number(run.multiplier)
              const available = stockMap[c.component_entity_id] ?? 0
              return available >= required
            })
            return (
              <div>
                <div className="flex items-center justify-between mb-2">
                  <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wide">
                    Componentes ({recipe.components.length})
                  </h3>
                  {run.status === 'pending' && (
                    <span className={cn(
                      'inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-bold',
                      allSufficient ? 'bg-emerald-50 text-emerald-700' : 'bg-red-50 text-red-600'
                    )}>
                      {allSufficient ? <PackageCheck className="h-3 w-3" /> : <PackageX className="h-3 w-3" />}
                      {allSufficient ? 'Stock OK' : 'Stock insuficiente'}
                    </span>
                  )}
                </div>
                <div className="space-y-2">
                  {recipe.components.map(c => {
                    const required = Number(c.quantity_required) * Number(run.multiplier)
                    const available = stockMap[c.component_entity_id] ?? 0
                    const sufficient = available >= required
                    return (
                      <div key={c.id} className={cn(
                        'rounded-xl p-3',
                        run.status === 'pending'
                          ? sufficient ? 'bg-emerald-50/60' : 'bg-red-50/60 border border-red-100'
                          : 'bg-slate-50'
                      )}>
                        <div className="flex justify-between items-center">
                          <span className="font-medium text-slate-700 text-sm">
                            {productMap[c.component_entity_id] ?? c.component_entity_id.slice(0, 8)}
                          </span>
                          <span className="font-bold text-slate-900 text-sm">
                            {required.toFixed(2)}
                          </span>
                        </div>
                        {run.status === 'pending' && (
                          <div className="flex justify-between items-center mt-1">
                            <span className={cn('text-xs', sufficient ? 'text-emerald-600' : 'text-red-600')}>
                              Disponible: {available.toFixed(2)}
                            </span>
                            {!sufficient && (
                              <span className="text-[10px] font-bold text-red-500">
                                Faltan {(required - available).toFixed(2)}
                              </span>
                            )}
                          </div>
                        )}
                      </div>
                    )
                  })}
                </div>
              </div>
            )
          })() : null}

          {/* Approval Info */}
          {run.status === 'completed' && run.approved_by && (
            <div className="bg-emerald-50 rounded-xl p-4 border border-emerald-100">
              <p className="text-xs font-bold text-emerald-500 uppercase tracking-wide mb-1">Aprobado por</p>
              <p className="font-semibold text-emerald-800 text-sm">{run.approved_by}</p>
              {run.approved_at && (
                <p className="text-xs text-emerald-600 mt-1">
                  {new Date(run.approved_at).toLocaleString('es-CO')}
                </p>
              )}
            </div>
          )}

          {/* Rejection Info */}
          {run.status === 'rejected' && (
            <div className="bg-red-50 rounded-xl p-4 border border-red-100">
              <p className="text-xs font-bold text-red-500 uppercase tracking-wide mb-1">Rechazada</p>
              {run.rejection_notes && (
                <p className="text-sm text-red-700 mt-1">{run.rejection_notes}</p>
              )}
            </div>
          )}

          {/* Timestamps */}
          <div className="border-t border-slate-100 pt-3 space-y-1">
            <p className="text-xs text-slate-400">
              Creado: {new Date(run.created_at).toLocaleString('es-CO')}
            </p>
            {run.started_at && (
              <p className="text-xs text-slate-400">
                Iniciado: {new Date(run.started_at).toLocaleString('es-CO')}
              </p>
            )}
            {run.completed_at && (
              <p className="text-xs text-slate-400">
                Completado: {new Date(run.completed_at).toLocaleString('es-CO')}
              </p>
            )}
            {run.notes && (
              <p className="text-xs text-slate-500 italic mt-2">{run.notes}</p>
            )}
          </div>

          {/* Pending Actions — Ejecutar + Eliminar */}
          {run.status === 'pending' && (() => {
            const canExecute = recipe?.components?.every(c => {
              const required = Number(c.quantity_required) * Number(run.multiplier)
              const available = stockMap[c.component_entity_id] ?? 0
              return available >= required
            }) ?? false
            return (
            <div className="border-t border-slate-100 pt-4 space-y-2">
              {!canExecute && (
                <div className="flex items-center gap-2 rounded-xl bg-amber-50 border border-amber-200 px-3 py-2">
                  <AlertTriangle className="h-4 w-4 text-amber-500 flex-shrink-0" />
                  <p className="text-xs text-amber-700">No hay suficiente stock para ejecutar esta producción. Revisa los componentes marcados en rojo.</p>
                </div>
              )}
              <button
                onClick={() => { onExecute(run.id); onClose() }}
                disabled={!canExecute}
                className={cn(
                  "w-full flex items-center justify-center gap-2 rounded-xl px-4 py-2.5 text-sm font-semibold text-white",
                  canExecute
                    ? "bg-emerald-600 hover:bg-emerald-700"
                    : "bg-slate-300 cursor-not-allowed"
                )}
              >
                <Play className="h-4 w-4" /> Iniciar producción
              </button>

              {confirmDelete ? (
                <div className="flex gap-2">
                  <button
                    onClick={() => { onDelete(run.id); onClose() }}
                    className="flex-1 rounded-xl bg-red-600 px-4 py-2 text-sm font-semibold text-white hover:bg-red-700"
                  >
                    Confirmar eliminar
                  </button>
                  <button
                    onClick={() => setConfirmDelete(false)}
                    className="flex-1 rounded-xl border border-slate-200 px-4 py-2 text-sm text-slate-600 hover:bg-slate-50"
                  >
                    Cancelar
                  </button>
                </div>
              ) : (
                <button
                  onClick={() => setConfirmDelete(true)}
                  className="w-full flex items-center justify-center gap-2 rounded-xl border border-red-200 px-4 py-2 text-sm font-semibold text-red-600 hover:bg-red-50"
                >
                  <Trash2 className="h-4 w-4" /> Eliminar corrida
                </button>
              )}
            </div>
            )
          })()}

          {/* In Progress Actions — Finalizar */}
          {run.status === 'in_progress' && (
            <div className="border-t border-slate-100 pt-4 space-y-2">
              <div className="flex items-center gap-2 rounded-xl bg-blue-50 border border-blue-200 px-3 py-2">
                <CircleDot className="h-4 w-4 text-blue-500 flex-shrink-0" />
                <p className="text-xs text-blue-700">Producción en curso. Cuando el producto esté listo, finaliza para enviar a aprobación.</p>
              </div>
              <button
                onClick={() => { onFinish(run.id); onClose() }}
                className="w-full flex items-center justify-center gap-2 rounded-xl bg-amber-500 px-4 py-2.5 text-sm font-semibold text-white hover:bg-amber-600"
              >
                <Flag className="h-4 w-4" /> Finalizar producción
              </button>
            </div>
          )}

          {/* Awaiting Approval Actions — Aprobar / Rechazar */}
          {run.status === 'awaiting_approval' && (
            <div className="border-t border-slate-100 pt-4 space-y-2">
              <div className="flex items-center gap-2 rounded-xl bg-amber-50 border border-amber-200 px-3 py-2">
                <ShieldCheck className="h-4 w-4 text-amber-500 flex-shrink-0" />
                <p className="text-xs text-amber-700">Esta corrida requiere aprobación de un supervisor.</p>
              </div>
              <button
                onClick={() => { onApprove(run.id); onClose() }}
                className="w-full flex items-center justify-center gap-2 rounded-xl bg-emerald-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-emerald-700"
              >
                <ShieldCheck className="h-4 w-4" /> Aprobar
              </button>
              <button
                onClick={() => { onReject(run.id) }}
                className="w-full flex items-center justify-center gap-2 rounded-xl border border-red-200 px-4 py-2 text-sm font-semibold text-red-600 hover:bg-red-50"
              >
                <ShieldX className="h-4 w-4" /> Rechazar
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

/* ─── Create Modal ──────────────────────────────────────────────────────────── */

function CreateProductionModal({ onClose }: { onClose: () => void }) {
  const { data: recipes = [] } = useRecipes()
  const { data: warehouses = [] } = useWarehouses()
  const create = useCreateProductionRun()
  const [error, setError] = useState('')

  const [form, setForm] = useState({ recipe_id: '', warehouse_id: '', output_warehouse_id: '', multiplier: '1', notes: '' })

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError('')
    try {
      await create.mutateAsync({
        recipe_id: form.recipe_id,
        warehouse_id: form.warehouse_id,
        output_warehouse_id: form.output_warehouse_id || undefined,
        multiplier: form.multiplier,
        notes: form.notes || undefined,
      })
      onClose()
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Error al crear corrida')
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 backdrop-blur-sm">
      <div className="w-full max-w-md bg-white rounded-3xl shadow-2xl p-6">
        <h2 className="text-lg font-bold text-slate-900 mb-4">Nueva Corrida de Producción</h2>
        <form onSubmit={handleSubmit} className="space-y-3">
          <select required value={form.recipe_id} onChange={e => setForm(f => ({ ...f, recipe_id: e.target.value }))}
            className="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400">
            <option value="">Receta *</option>
            {recipes.map(r => <option key={r.id} value={r.id}>{r.name}</option>)}
          </select>
          <select required value={form.warehouse_id} onChange={e => setForm(f => ({ ...f, warehouse_id: e.target.value }))}
            className="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400">
            <option value="">Bodega de componentes *</option>
            {warehouses.map(w => <option key={w.id} value={w.id}>{w.name}</option>)}
          </select>
          <select value={form.output_warehouse_id} onChange={e => setForm(f => ({ ...f, output_warehouse_id: e.target.value }))}
            className="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400">
            <option value="">Bodega destino (misma si vacío)</option>
            {warehouses.map(w => <option key={w.id} value={w.id}>{w.name}</option>)}
          </select>
          <input required type="number" step="0.01" min="0.01" value={form.multiplier}
            onChange={e => setForm(f => ({ ...f, multiplier: e.target.value }))}
            placeholder="Multiplicador *" className="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400" />
          <input value={form.notes} onChange={e => setForm(f => ({ ...f, notes: e.target.value }))}
            placeholder="Notas (opcional)" className="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400" />

          {error && (
            <div className="flex items-center gap-2 rounded-xl bg-red-50 border border-red-200 px-3 py-2">
              <AlertTriangle className="h-4 w-4 text-red-500 flex-shrink-0" />
              <p className="text-sm text-red-700">{error}</p>
            </div>
          )}

          <div className="flex gap-3 pt-2">
            <button type="button" onClick={onClose} className="flex-1 rounded-xl border border-slate-200 px-4 py-2 text-sm text-slate-600 hover:bg-slate-50">Cancelar</button>
            <button type="submit" disabled={create.isPending} className="flex-1 rounded-xl bg-indigo-600 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-700 disabled:opacity-60">
              {create.isPending ? 'Creando...' : 'Crear corrida'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

/* ─── Main Page ─────────────────────────────────────────────────────────────── */

export function ProductionPage() {
  const [showCreate, setShowCreate] = useState(false)
  const [selectedRunId, setSelectedRunId] = useState<string | null>(null)
  const [statusFilter, setStatusFilter] = useState('')
  const [actionError, setActionError] = useState('')
  const [actionSuccess, setActionSuccess] = useState('')
  const [confirmDeleteId, setConfirmDeleteId] = useState<string | null>(null)
  const [rejectRunId, setRejectRunId] = useState<string | null>(null)

  const { data, isLoading } = useProductionRuns({ status: statusFilter || undefined })
  const { data: recipes = [] } = useRecipes()
  const { data: warehouses = [] } = useWarehouses()
  const execute = useExecuteProductionRun()
  const finish = useFinishProductionRun()
  const approve = useApproveProductionRun()
  const reject = useRejectProductionRun()
  const del = useDeleteProductionRun()

  const recipeMap = Object.fromEntries(recipes.map(r => [r.id, r.name]))
  const whMap = Object.fromEntries(warehouses.map(w => [w.id, w.name]))

  // Auto-dismiss success banner after 5 seconds
  useEffect(() => {
    if (!actionSuccess) return
    const t = setTimeout(() => setActionSuccess(''), 5000)
    return () => clearTimeout(t)
  }, [actionSuccess])

  async function handleExecute(runId: string) {
    setActionError('')
    setActionSuccess('')
    try {
      const result = await execute.mutateAsync(runId)
      setActionSuccess(`Producción ${result.run_number} iniciada`)
    } catch (err: unknown) {
      setActionError(err instanceof Error ? err.message : 'Error al iniciar producción')
    }
  }

  async function handleFinish(runId: string) {
    setActionError('')
    setActionSuccess('')
    try {
      const result = await finish.mutateAsync(runId)
      setActionSuccess(`Producción ${result.run_number} finalizada — pendiente de aprobación`)
    } catch (err: unknown) {
      setActionError(err instanceof Error ? err.message : 'Error al finalizar producción')
    }
  }

  async function handleApprove(runId: string) {
    setActionError('')
    setActionSuccess('')
    try {
      const result = await approve.mutateAsync(runId)
      setActionSuccess(`Producción ${result.run_number} aprobada exitosamente`)
    } catch (err: unknown) {
      setActionError(err instanceof Error ? err.message : 'Error al aprobar producción')
    }
  }

  async function handleReject(runId: string, notes: string) {
    setActionError('')
    setActionSuccess('')
    try {
      const result = await reject.mutateAsync({ id: runId, rejection_notes: notes })
      setActionSuccess(`Producción ${result.run_number} rechazada`)
      setRejectRunId(null)
    } catch (err: unknown) {
      setActionError(err instanceof Error ? err.message : 'Error al rechazar producción')
    }
  }

  async function handleDelete(runId: string) {
    setActionError('')
    setConfirmDeleteId(null)
    try {
      await del.mutateAsync(runId)
    } catch (err: unknown) {
      setActionError(err instanceof Error ? err.message : 'Error al eliminar corrida')
    }
  }

  return (
    <div className="max-w-5xl mx-auto p-6 space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-slate-900">Producción</h1>
        <button onClick={() => setShowCreate(true)}
          className="flex items-center gap-2 rounded-2xl bg-indigo-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-indigo-700 shadow-sm">
          <Plus className="h-4 w-4" /> Nueva corrida
        </button>
      </div>

      {/* Status Filter */}
      <div className="flex gap-2 flex-wrap">
        {['', 'pending', 'in_progress', 'awaiting_approval', 'completed', 'rejected', 'canceled'].map(s => (
          <button key={s || 'all'} onClick={() => setStatusFilter(s)}
            className={cn('rounded-full px-3 py-1.5 text-xs font-semibold transition-colors',
              statusFilter === s ? 'bg-indigo-600 text-white' : 'bg-slate-100 text-slate-600 hover:bg-slate-200')}>
            {s ? STATUS_LABELS[s] : 'Todos'}
          </button>
        ))}
      </div>

      {/* Success Banner */}
      {actionSuccess && (
        <div className="rounded-xl bg-emerald-50 border border-emerald-200 px-4 py-3">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="h-4 w-4 text-emerald-600 flex-shrink-0" />
            <p className="flex-1 text-sm font-medium text-emerald-700">{actionSuccess}</p>
            <button onClick={() => setActionSuccess('')} className="text-emerald-400 hover:text-emerald-600 text-sm font-bold flex-shrink-0">x</button>
          </div>
        </div>
      )}

      {/* Error Banner */}
      {actionError && (
        <div className="rounded-xl bg-red-50 border border-red-200 px-4 py-3">
          <div className="flex items-start gap-2">
            <AlertTriangle className="h-4 w-4 text-red-500 flex-shrink-0 mt-0.5" />
            <div className="flex-1 text-sm text-red-700 whitespace-pre-line">{actionError}</div>
            <button onClick={() => setActionError('')} className="text-red-400 hover:text-red-600 text-sm font-bold flex-shrink-0">x</button>
          </div>
        </div>
      )}

      {/* Table */}
      <div className="bg-white rounded-2xl border border-slate-100 shadow-sm overflow-hidden">
        {isLoading ? (
          <div className="p-8 text-center text-slate-400">Cargando...</div>
        ) : !data?.items?.length ? (
          <div className="p-8 text-center">
            <Factory className="h-10 w-10 text-slate-200 mx-auto mb-3" />
            <p className="text-sm text-slate-400">Sin corridas de producción</p>
          </div>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-slate-50 border-b border-slate-100">
              <tr>
                {['Corrida', 'Receta', 'Bodega', 'Mult.', 'Estado', 'Fecha', ''].map(h => (
                  <th key={h} className="px-4 py-3 text-left text-xs font-semibold text-slate-400 uppercase tracking-wide">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-50">
              {data.items.map(run => {
                const StatusIcon = STATUS_ICONS[run.status] ?? Clock
                return (
                  <tr key={run.id} className="group hover:bg-slate-50">
                    <td className="px-4 py-3 font-mono text-xs text-slate-700 font-semibold">{run.run_number}</td>
                    <td className="px-4 py-3 font-medium text-slate-700">{recipeMap[run.recipe_id] ?? '—'}</td>
                    <td className="px-4 py-3 text-slate-500">{whMap[run.warehouse_id] ?? '—'}</td>
                    <td className="px-4 py-3 font-bold text-slate-900">{run.multiplier}x</td>
                    <td className="px-4 py-3">
                      <span className={cn('inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-semibold', STATUS_COLORS[run.status])}>
                        <StatusIcon className="h-3 w-3" />
                        {STATUS_LABELS[run.status] ?? run.status}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-xs text-slate-400">
                      {new Date(run.created_at).toLocaleDateString('es-CO')}
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex gap-1.5 justify-end">
                        {/* View detail */}
                        <button onClick={() => setSelectedRunId(run.id)}
                          className="text-slate-400 hover:text-indigo-600 p-1 rounded-lg hover:bg-indigo-50"
                          title="Ver detalle">
                          <Eye className="h-4 w-4" />
                        </button>

                        {/* Execute — only pending */}
                        {run.status === 'pending' && (
                          <button
                            onClick={() => handleExecute(run.id)}
                            disabled={execute.isPending}
                            className="flex items-center gap-1 rounded-lg bg-blue-600 px-2.5 py-1 text-xs font-semibold text-white hover:bg-blue-700 disabled:opacity-50"
                            title="Iniciar producción"
                          >
                            <Play className="h-3 w-3" />
                            Iniciar
                          </button>
                        )}

                        {/* Finish — only in_progress */}
                        {run.status === 'in_progress' && (
                          <button
                            onClick={() => handleFinish(run.id)}
                            disabled={finish.isPending}
                            className="flex items-center gap-1 rounded-lg bg-amber-500 px-2.5 py-1 text-xs font-semibold text-white hover:bg-amber-600 disabled:opacity-50"
                            title="Finalizar producción"
                          >
                            <Flag className="h-3 w-3" />
                            Finalizar
                          </button>
                        )}

                        {/* Approve — only awaiting_approval */}
                        {run.status === 'awaiting_approval' && (
                          <button
                            onClick={() => handleApprove(run.id)}
                            disabled={approve.isPending}
                            className="flex items-center gap-1 rounded-lg bg-emerald-600 px-2.5 py-1 text-xs font-semibold text-white hover:bg-emerald-700 disabled:opacity-50"
                            title="Aprobar"
                          >
                            <ShieldCheck className="h-3 w-3" />
                            Aprobar
                          </button>
                        )}

                        {/* Reject — only awaiting_approval */}
                        {run.status === 'awaiting_approval' && (
                          <button
                            onClick={() => setRejectRunId(run.id)}
                            disabled={reject.isPending}
                            className="flex items-center gap-1 rounded-lg border border-red-200 px-2.5 py-1 text-xs font-semibold text-red-600 hover:bg-red-50 disabled:opacity-50"
                            title="Rechazar"
                          >
                            <ShieldX className="h-3 w-3" />
                            Rechazar
                          </button>
                        )}

                        {/* Delete — only pending */}
                        {run.status === 'pending' && (
                          confirmDeleteId === run.id ? (
                            <div className="flex items-center gap-1">
                              <button
                                disabled={del.isPending}
                                onClick={() => handleDelete(run.id)}
                                className="rounded-lg bg-red-600 px-2.5 py-1 text-[11px] font-semibold text-white hover:bg-red-700 disabled:opacity-60"
                              >
                                {del.isPending ? '...' : 'Confirmar'}
                              </button>
                              <button onClick={() => setConfirmDeleteId(null)}
                                className="rounded-lg border border-slate-200 px-2.5 py-1 text-[11px] text-slate-500 hover:bg-slate-50">
                                No
                              </button>
                            </div>
                          ) : (
                            <button onClick={() => setConfirmDeleteId(run.id)}
                              className="text-slate-400 hover:text-red-500 p-1 rounded-lg hover:bg-red-50"
                              title="Eliminar corrida">
                              <Trash2 className="h-4 w-4" />
                            </button>
                          )
                        )}
                      </div>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        )}
      </div>

      {showCreate && <CreateProductionModal onClose={() => setShowCreate(false)} />}
      {selectedRunId && (
        <RunDrawer
          runId={selectedRunId}
          onClose={() => setSelectedRunId(null)}
          onExecute={handleExecute}
          onFinish={handleFinish}
          onDelete={handleDelete}
          onApprove={handleApprove}
          onReject={(id) => { setSelectedRunId(null); setRejectRunId(id) }}
        />
      )}
      {rejectRunId && (
        <RejectModal
          onClose={() => setRejectRunId(null)}
          onConfirm={(notes) => handleReject(rejectRunId, notes)}
          isPending={reject.isPending}
        />
      )}
    </div>
  )
}
