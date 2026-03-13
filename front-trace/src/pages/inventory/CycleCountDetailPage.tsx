import { useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import {
  ArrowLeft, Play, CheckCircle2, XCircle, ShieldCheck,
  ClipboardCheck, AlertTriangle, TrendingUp, Users, Clock, RotateCcw,
} from 'lucide-react'
import {
  useCycleCount, useStartCycleCount, useRecordCount,
  useCompleteCycleCount, useApproveCycleCount, useCancelCycleCount,
  useRecountItem,
} from '@/hooks/useInventory'
import { useUserLookup } from '@/hooks/useUserLookup'
import type { CycleCountItem } from '@/types/inventory'

const statusColors: Record<string, string> = {
  draft: 'bg-slate-100 text-slate-700',
  in_progress: 'bg-blue-100 text-blue-700',
  completed: 'bg-amber-100 text-amber-700',
  approved: 'bg-green-100 text-green-700',
  canceled: 'bg-red-100 text-red-700',
}

const statusLabels: Record<string, string> = {
  draft: 'Borrador',
  in_progress: 'En progreso',
  completed: 'Completado',
  approved: 'Aprobado',
  canceled: 'Cancelado',
}

const methodologyLabels: Record<string, string> = {
  control_group: 'Grupo de control',
  location_audit: 'Auditoria por ubicacion',
  random_selection: 'Seleccion aleatoria',
  diminishing_population: 'Poblacion decreciente',
  product_category: 'Categoria de producto',
  abc: 'Clasificacion ABC',
}

function iraColor(pct: number): string {
  if (pct >= 95) return 'text-green-600'
  if (pct >= 90) return 'text-amber-600'
  return 'text-red-600'
}

function iraBg(pct: number): string {
  if (pct >= 95) return 'bg-green-50 border-green-200'
  if (pct >= 90) return 'bg-amber-50 border-amber-200'
  return 'bg-red-50 border-red-200'
}

function discrepancyColor(d: string | null): string {
  if (!d) return 'text-slate-400'
  const n = parseFloat(d)
  if (n === 0) return 'text-green-600'
  if (n < 0) return 'text-red-600'
  return 'text-blue-600'
}

export function CycleCountDetailPage() {
  const { id } = useParams<{ id: string }>()
  const { data: cc, isLoading } = useCycleCount(id ?? '')
  const startMut = useStartCycleCount()
  const completeMut = useCompleteCycleCount()
  const approveMut = useApproveCycleCount()
  const cancelMut = useCancelCycleCount()

  const userIds = [cc?.created_by, cc?.approved_by, ...(cc?.items?.map(i => i.counted_by) ?? [])]
  const { resolve } = useUserLookup(userIds)

  if (isLoading) {
    return <div className="p-8 text-center text-slate-400">Cargando...</div>
  }
  if (!cc) {
    return <div className="p-8 text-center text-slate-400">Conteo no encontrado</div>
  }

  const items = cc.items ?? []
  const counted = items.filter((i) => i.counted_qty !== null).length
  const withDiscrepancy = items.filter((i) => i.discrepancy !== null && parseFloat(i.discrepancy) !== 0).length
  const ira = cc.ira
  const feasibility = cc.feasibility

  return (
    <div className="max-w-5xl mx-auto p-6 space-y-6">
      {/* Back + header */}
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-3">
          <Link to="/inventario/conteos" className="p-2 rounded-xl hover:bg-slate-100">
            <ArrowLeft className="h-5 w-5 text-slate-500" />
          </Link>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-2xl font-bold text-slate-900">{cc.count_number}</h1>
              <span className={`inline-block px-2.5 py-0.5 rounded-full text-xs font-medium ${statusColors[cc.status] ?? ''}`}>
                {statusLabels[cc.status] ?? cc.status}
              </span>
              {cc.methodology && (
                <span className="inline-block px-2.5 py-0.5 rounded-full text-xs font-medium bg-purple-100 text-purple-700">
                  {methodologyLabels[cc.methodology] ?? cc.methodology}
                </span>
              )}
            </div>
            <p className="text-sm text-slate-500">
              Bodega: {cc.warehouse_name ?? cc.warehouse_id}
              {cc.scheduled_date && <> &middot; Programado: {new Date(cc.scheduled_date).toLocaleDateString()}</>}
            </p>
            <p className="text-xs text-slate-400 mt-0.5">
              Creado por: {resolve(cc.created_by)}
              {cc.approved_by && <> &middot; Aprobado por: {resolve(cc.approved_by)}</>}
            </p>
          </div>
        </div>

        {/* Action buttons */}
        <div className="flex gap-2">
          {cc.status === 'draft' && (
            <button
              onClick={() => startMut.mutate(cc.id)}
              disabled={startMut.isPending}
              className="flex items-center gap-1.5 px-4 py-2 text-sm font-semibold text-white bg-blue-600 rounded-xl hover:bg-blue-700 disabled:opacity-50"
            >
              <Play className="h-4 w-4" /> Iniciar
            </button>
          )}
          {cc.status === 'in_progress' && (
            <button
              onClick={() => completeMut.mutate(cc.id)}
              disabled={completeMut.isPending}
              className="flex items-center gap-1.5 px-4 py-2 text-sm font-semibold text-white bg-amber-600 rounded-xl hover:bg-amber-700 disabled:opacity-50"
            >
              <CheckCircle2 className="h-4 w-4" /> Completar
            </button>
          )}
          {cc.status === 'completed' && (
            <button
              onClick={() => approveMut.mutate(cc.id)}
              disabled={approveMut.isPending}
              className="flex items-center gap-1.5 px-4 py-2 text-sm font-semibold text-white bg-green-600 rounded-xl hover:bg-green-700 disabled:opacity-50"
            >
              <ShieldCheck className="h-4 w-4" /> Aprobar
            </button>
          )}
          {(cc.status === 'draft' || cc.status === 'in_progress' || cc.status === 'completed') && (
            <button
              onClick={() => cancelMut.mutate(cc.id)}
              disabled={cancelMut.isPending}
              className="flex items-center gap-1.5 px-4 py-2 text-sm font-medium text-red-600 bg-red-50 rounded-xl hover:bg-red-100 disabled:opacity-50"
            >
              <XCircle className="h-4 w-4" /> Cancelar
            </button>
          )}
        </div>
      </div>

      {/* Summary cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <SummaryCard label="Total items" value={items.length} icon={ClipboardCheck} color="bg-gradient-to-br from-slate-500 to-slate-600" />
        <SummaryCard
          label="Contados"
          value={`${counted}/${items.length}`}
          icon={CheckCircle2}
          color="bg-gradient-to-br from-blue-500 to-blue-600"
          sub={items.length > 0 ? `${Math.round((counted / items.length) * 100)}%` : undefined}
        />
        <SummaryCard label="Discrepancias" value={withDiscrepancy} icon={AlertTriangle} color="bg-gradient-to-br from-amber-500 to-amber-600" />
        {ira ? (
          <div className={`rounded-2xl border p-4 ${iraBg(ira.ira_percentage)}`}>
            <div className="flex items-center gap-2 mb-1">
              <TrendingUp className={`h-4 w-4 ${iraColor(ira.ira_percentage)}`} />
              <span className="text-xs font-semibold text-slate-500 uppercase">IRA</span>
            </div>
            <p className={`text-2xl font-bold ${iraColor(ira.ira_percentage)}`}>
              {ira.ira_percentage.toFixed(1)}%
            </p>
            <p className="text-xs text-slate-500 mt-0.5">
              Valor: {ira.value_accuracy.toFixed(1)}%
            </p>
          </div>
        ) : (
          <SummaryCard label="IRA" value="--" icon={TrendingUp} color="bg-gradient-to-br from-green-500 to-green-600" sub="Pendiente" />
        )}
      </div>

      {/* Feasibility card */}
      {feasibility && (
        <div className={`rounded-2xl border p-4 ${feasibility.is_feasible ? 'bg-green-50 border-green-200' : 'bg-red-50 border-red-200'}`}>
          <div className="flex items-center gap-2 mb-2">
            <Clock className={`h-4 w-4 ${feasibility.is_feasible ? 'text-green-600' : 'text-red-600'}`} />
            <span className="text-sm font-semibold text-slate-800">Factibilidad del conteo</span>
            <span className={`ml-auto px-2.5 py-0.5 rounded-full text-xs font-medium ${feasibility.is_feasible ? 'bg-green-200 text-green-800' : 'bg-red-200 text-red-800'}`}>
              {feasibility.is_feasible ? 'Factible' : 'No factible'}
            </span>
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-sm">
            <div>
              <p className="text-xs text-slate-500">Items</p>
              <p className="font-semibold text-slate-800">{feasibility.total_items}</p>
            </div>
            <div>
              <p className="text-xs text-slate-500">Tiempo total</p>
              <p className="font-semibold text-slate-800">{feasibility.total_hours}h ({feasibility.total_minutes} min)</p>
            </div>
            <div className="flex items-center gap-1">
              <Users className="h-3.5 w-3.5 text-slate-400" />
              <div>
                <p className="text-xs text-slate-500">Contadores</p>
                <p className="font-semibold text-slate-800">{feasibility.assigned_counters}</p>
              </div>
            </div>
            <div>
              <p className="text-xs text-slate-500">Hrs/contador</p>
              <p className={`font-semibold ${feasibility.hours_per_counter <= feasibility.available_hours ? 'text-green-700' : 'text-red-700'}`}>
                {feasibility.hours_per_counter}h / {feasibility.available_hours}h
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Notes */}
      {cc.notes && (
        <div className="bg-slate-50 rounded-xl p-4 text-sm text-slate-600">
          <span className="font-medium text-slate-700">Notas:</span> {cc.notes}
        </div>
      )}

      {/* Items table */}
      <div className="bg-white rounded-2xl border border-slate-100 shadow-sm overflow-hidden">
        <div className="px-4 py-3 border-b border-slate-100">
          <h2 className="text-sm font-semibold text-slate-800">Items de conteo</h2>
        </div>
        {items.length === 0 ? (
          <div className="p-8 text-center text-slate-400">Sin items</div>
        ) : (
          <>
          {/* Mobile cards */}
          <div className="space-y-3 p-4 md:hidden">
            {items.map((item) => {
              const sysQty = parseFloat(item.system_qty)
              const hasDisc = item.discrepancy !== null && parseFloat(item.discrepancy) !== 0
              return (
                <div key={item.id} className="rounded-xl border border-gray-200 bg-white p-4 shadow-sm space-y-2">
                  <div className="flex items-center justify-between">
                    <div>
                      <span className="font-medium text-slate-900">{item.product_name ?? item.product_id}</span>
                      {item.product_sku && <span className="ml-2 text-xs text-slate-400">{item.product_sku}</span>}
                    </div>
                  </div>
                  <div className="space-y-1 text-sm">
                    <div className="flex justify-between"><span className="text-slate-400">Sistema</span><span className="font-mono text-slate-700">{sysQty.toFixed(2)}</span></div>
                    <div className="flex justify-between"><span className="text-slate-400">1er Conteo</span><span className="font-mono text-slate-700">{item.counted_qty !== null ? parseFloat(item.counted_qty).toFixed(2) : '---'}</span></div>
                    <div className="flex justify-between">
                      <span className="text-slate-400">Diferencia</span>
                      <span className={`font-mono font-semibold ${discrepancyColor(item.discrepancy)}`}>
                        {item.discrepancy !== null ? `${parseFloat(item.discrepancy) > 0 ? '+' : ''}${parseFloat(item.discrepancy).toFixed(2)}` : '---'}
                      </span>
                    </div>
                    {item.recount_qty !== null && (
                      <div className="flex justify-between"><span className="text-slate-400">Reconteo</span><span className="font-mono text-purple-600 font-semibold">{parseFloat(item.recount_qty).toFixed(2)}</span></div>
                    )}
                    {item.root_cause && <div className="flex justify-between"><span className="text-slate-400">Causa raiz</span><span className="text-slate-600 text-xs">{item.root_cause}</span></div>}
                    <div className="flex justify-between"><span className="text-slate-400">Contado por</span><span className="text-slate-500 text-xs">{resolve(item.counted_by)}</span></div>
                    {item.notes && <div className="flex justify-between"><span className="text-slate-400">Notas</span><span className="text-slate-500 text-xs truncate max-w-[60%]">{item.notes}</span></div>}
                  </div>
                </div>
              )
            })}
          </div>

          {/* Desktop table */}
          <div className="hidden md:block overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-slate-50 border-b border-slate-100">
                  <th className="text-left px-4 py-2.5 text-xs font-semibold text-slate-400 uppercase tracking-wide">Producto</th>
                  <th className="text-right px-4 py-2.5 text-xs font-semibold text-slate-400 uppercase tracking-wide">Sistema</th>
                  <th className="text-right px-4 py-2.5 text-xs font-semibold text-slate-400 uppercase tracking-wide">1er Conteo</th>
                  <th className="text-right px-4 py-2.5 text-xs font-semibold text-slate-400 uppercase tracking-wide">Diferencia</th>
                  <th className="text-right px-4 py-2.5 text-xs font-semibold text-slate-400 uppercase tracking-wide">Reconteo</th>
                  <th className="text-left px-4 py-2.5 text-xs font-semibold text-slate-400 uppercase tracking-wide">Causa raiz</th>
                  <th className="text-left px-4 py-2.5 text-xs font-semibold text-slate-400 uppercase tracking-wide">Contado por</th>
                  <th className="text-left px-4 py-2.5 text-xs font-semibold text-slate-400 uppercase tracking-wide">Notas</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-50">
                {items.map((item) => (
                  <CountItemRow
                    key={item.id}
                    item={item}
                    ccId={cc.id}
                    editable={cc.status === 'in_progress'}
                    resolveUser={resolve}
                  />
                ))}
              </tbody>
            </table>
          </div>
          </>
        )}
      </div>
    </div>
  )
}

// ── Summary card component ──────────────────────────────────────────────────

function SummaryCard({
  label, value, icon: Icon, color, sub,
}: {
  label: string
  value: number | string
  icon: React.ElementType
  color: string
  sub?: string
}) {
  return (
    <div className={`rounded-2xl p-4 text-white ${color}`}>
      <div className="flex items-center gap-2 mb-1">
        <Icon className="h-4 w-4 opacity-80" />
        <span className="text-xs font-semibold opacity-80 uppercase">{label}</span>
      </div>
      <p className="text-2xl font-bold">{value}</p>
      {sub && <p className="text-xs opacity-80 mt-0.5">{sub}</p>}
    </div>
  )
}

// ── Inline-editable count item row ──────────────────────────────────────────

function CountItemRow({
  item,
  ccId,
  editable,
  resolveUser,
}: {
  item: CycleCountItem
  ccId: string
  editable: boolean
  resolveUser: (id: string | null | undefined) => string
}) {
  const recordMut = useRecordCount()
  const recountMut = useRecountItem()
  const [localQty, setLocalQty] = useState(item.counted_qty ?? '')
  const [localNotes, setLocalNotes] = useState(item.notes ?? '')
  const [editing, setEditing] = useState(false)
  const [recountMode, setRecountMode] = useState(false)
  const [recountQty, setRecountQty] = useState(item.recount_qty ?? '')
  const [rootCause, setRootCause] = useState(item.root_cause ?? '')

  const handleSave = async () => {
    if (localQty === '') return
    await recordMut.mutateAsync({
      ccId,
      itemId: item.id,
      data: {
        counted_qty: localQty,
        notes: localNotes || undefined,
      },
    })
    setEditing(false)
  }

  const handleRecount = async () => {
    if (recountQty === '') return
    await recountMut.mutateAsync({
      ccId,
      itemId: item.id,
      data: {
        recount_qty: recountQty,
        root_cause: rootCause || undefined,
        notes: localNotes || undefined,
      },
    })
    setRecountMode(false)
  }

  const systemQty = parseFloat(item.system_qty)
  const hasDiscrepancy = item.discrepancy !== null && parseFloat(item.discrepancy) !== 0
  const canRecount = editable && item.counted_qty !== null && hasDiscrepancy

  return (
    <>
      <tr className="hover:bg-slate-50">
        <td className="px-4 py-2.5">
          <div className="font-medium text-slate-900">{item.product_name ?? item.product_id}</div>
          {item.product_sku && <div className="text-xs text-slate-400">{item.product_sku}</div>}
        </td>
        <td className="px-4 py-2.5 text-right font-mono text-slate-700">
          {systemQty.toFixed(2)}
        </td>
        <td className="px-4 py-2.5 text-right">
          {editable && editing ? (
            <div className="flex items-center gap-1 justify-end">
              <input
                type="number"
                step="0.01"
                min="0"
                value={localQty}
                onChange={(e) => setLocalQty(e.target.value)}
                className="w-24 rounded-lg border border-slate-200 px-2 py-1 text-sm text-right focus:ring-2 focus:ring-indigo-500"
                autoFocus
              />
              <button
                onClick={handleSave}
                disabled={recordMut.isPending || localQty === ''}
                className="px-2 py-1 text-xs font-semibold text-white bg-indigo-600 rounded-lg hover:bg-indigo-700 disabled:opacity-50"
              >
                {recordMut.isPending ? '...' : 'OK'}
              </button>
              <button
                onClick={() => setEditing(false)}
                className="px-2 py-1 text-xs text-slate-500 hover:text-slate-700"
              >
                X
              </button>
            </div>
          ) : editable ? (
            <button
              onClick={() => setEditing(true)}
              className="font-mono text-indigo-600 hover:underline cursor-pointer"
            >
              {item.counted_qty !== null ? parseFloat(item.counted_qty).toFixed(2) : '---'}
            </button>
          ) : (
            <span className="font-mono text-slate-700">
              {item.counted_qty !== null ? parseFloat(item.counted_qty).toFixed(2) : '---'}
            </span>
          )}
        </td>
        <td className={`px-4 py-2.5 text-right font-mono font-semibold ${discrepancyColor(item.discrepancy)}`}>
          {item.discrepancy !== null ? (
            <>
              {parseFloat(item.discrepancy) > 0 ? '+' : ''}
              {parseFloat(item.discrepancy).toFixed(2)}
            </>
          ) : (
            '---'
          )}
        </td>
        <td className="px-4 py-2.5 text-right">
          {item.recount_qty !== null ? (
            <span className="font-mono text-purple-600 font-semibold">{parseFloat(item.recount_qty).toFixed(2)}</span>
          ) : canRecount ? (
            <button
              onClick={() => setRecountMode(!recountMode)}
              className="inline-flex items-center gap-1 text-xs text-purple-600 hover:text-purple-800"
            >
              <RotateCcw className="h-3 w-3" /> Recontar
            </button>
          ) : (
            <span className="text-slate-400">-</span>
          )}
        </td>
        <td className="px-4 py-2.5 text-xs text-slate-600 max-w-[120px] truncate">
          {item.root_cause || '-'}
        </td>
        <td className="px-4 py-2.5 text-slate-400 text-xs">{resolveUser(item.counted_by)}</td>
        <td className="px-4 py-2.5 text-slate-500 text-xs max-w-[120px] truncate">
          {editable && editing ? (
            <input
              type="text"
              value={localNotes}
              onChange={(e) => setLocalNotes(e.target.value)}
              placeholder="Notas..."
              className="w-full rounded-lg border border-slate-200 px-2 py-1 text-xs focus:ring-2 focus:ring-indigo-500"
            />
          ) : (
            item.notes || '-'
          )}
        </td>
      </tr>
      {/* Recount inline form */}
      {recountMode && (
        <tr className="bg-purple-50">
          <td colSpan={7} className="px-4 py-3">
            <div className="flex items-center gap-3 flex-wrap">
              <span className="text-xs font-semibold text-purple-700">Reconteo (2do intento):</span>
              <input
                type="number"
                step="0.01"
                min="0"
                value={recountQty}
                onChange={(e) => setRecountQty(e.target.value)}
                placeholder="Cantidad"
                className="w-28 rounded-lg border border-purple-200 px-2 py-1 text-sm text-right focus:ring-2 focus:ring-purple-500"
                autoFocus
              />
              <input
                type="text"
                value={rootCause}
                onChange={(e) => setRootCause(e.target.value)}
                placeholder="Causa raiz (opcional)"
                className="flex-1 min-w-[180px] rounded-lg border border-purple-200 px-2 py-1 text-sm focus:ring-2 focus:ring-purple-500"
              />
              <button
                onClick={handleRecount}
                disabled={recountMut.isPending || recountQty === ''}
                className="px-3 py-1 text-xs font-semibold text-white bg-purple-600 rounded-lg hover:bg-purple-700 disabled:opacity-50"
              >
                {recountMut.isPending ? '...' : 'Guardar reconteo'}
              </button>
              <button
                onClick={() => setRecountMode(false)}
                className="px-2 py-1 text-xs text-slate-500 hover:text-slate-700"
              >
                Cancelar
              </button>
            </div>
          </td>
        </tr>
      )}
    </>
  )
}
