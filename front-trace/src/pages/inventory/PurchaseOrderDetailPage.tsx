import { useState } from 'react'
import { Link, useParams, useNavigate } from 'react-router-dom'
import { ArrowLeft, Send, CheckCircle2, XCircle, PackageCheck, Trash2, GitMerge, Info, Pencil } from 'lucide-react'
import { cn } from '@/lib/utils'
import {
  usePO,
  useSendPO,
  useConfirmPO,
  useCancelPO,
  useReceivePO,
  useDeletePO,
  useProducts,
  useConsolidationInfo,
  useDeconsolidatePO,
  useUpdatePO,
  useWarehouses,
} from '@/hooks/useInventory'
import { useUserLookup } from '@/hooks/useUserLookup'
import { ActivityTimeline } from '@/components/inventory/ActivityTimeline'
import type { POStatus, PurchaseOrderLine } from '@/types/inventory'

const STATUS_CONFIG: Record<POStatus, { label: string; color: string }> = {
  draft: { label: 'Borrador', color: 'bg-slate-100 text-slate-600' },
  sent: { label: 'Enviada', color: 'bg-blue-50 text-blue-700' },
  confirmed: { label: 'Confirmada', color: 'bg-indigo-50 text-indigo-700' },
  partial: { label: 'Parcial', color: 'bg-amber-50 text-amber-700' },
  received: { label: 'Recibida', color: 'bg-emerald-50 text-emerald-700' },
  canceled: { label: 'Cancelada', color: 'bg-red-50 text-red-600' },
  consolidated: { label: 'Consolidada', color: 'bg-gray-100 text-gray-700' },
}

function ReceiveModal({
  lines,
  productMap,
  onSubmit,
  onClose,
  isPending,
}: {
  lines: PurchaseOrderLine[]
  productMap: Record<string, string>
  onSubmit: (receipts: Array<{ line_id: string; qty_received: string }>) => void
  onClose: () => void
  isPending: boolean
}) {
  const [quantities, setQuantities] = useState<Record<string, string>>(() =>
    Object.fromEntries(
      lines.map((l) => {
        const remaining = Math.max(0, Number(l.qty_ordered) - Number(l.qty_received))
        return [l.id, remaining > 0 ? String(remaining) : '']
      })
    )
  )
  const [error, setError] = useState('')

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError('')
    const receipts = Object.entries(quantities)
      .filter(([, v]) => v && Number(v) > 0)
      .map(([line_id, qty_received]) => ({ line_id, qty_received }))
    if (receipts.length === 0) {
      setError('Ingresa al menos una cantidad a recibir')
      return
    }
    onSubmit(receipts)
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 backdrop-blur-sm">
      <div className="w-full max-w-lg bg-white rounded-3xl shadow-2xl p-6 max-h-[90vh] overflow-y-auto">
        <h2 className="text-lg font-bold text-slate-900 mb-4">Recibir mercancia</h2>
        <form onSubmit={handleSubmit} className="space-y-3">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-xs text-slate-400 uppercase">
                <th className="text-left py-2">Producto</th>
                <th className="text-right py-2">Ordenado</th>
                <th className="text-right py-2">Recibido</th>
                <th className="text-right py-2">Recibir ahora</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {lines.map((line) => {
                const remaining = Number(line.qty_ordered) - Number(line.qty_received)
                return (
                  <tr key={line.id}>
                    <td className="py-2 text-slate-700">{productMap[line.product_id] ?? line.product_id.slice(0, 8)}</td>
                    <td className="py-2 text-right font-mono text-slate-600">{line.qty_ordered}</td>
                    <td className="py-2 text-right font-mono text-slate-600">{line.qty_received}</td>
                    <td className="py-2 text-right">
                      <input
                        type="number"
                        min="0"
                        max={remaining}
                        step="0.01"
                        value={quantities[line.id] ?? ''}
                        onChange={(e) => setQuantities((q) => ({ ...q, [line.id]: e.target.value }))}
                        placeholder="0"
                        className="w-20 rounded-xl border border-slate-200 px-2 py-1 text-xs text-right focus:outline-none focus:ring-2 focus:ring-indigo-400"
                      />
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
          {error && (
            <p className="text-sm text-red-600 bg-red-50 border border-red-200 rounded-xl px-3 py-2">{error}</p>
          )}
          <div className="flex gap-3 pt-2">
            <button type="button" onClick={onClose} className="flex-1 rounded-xl border border-slate-200 px-4 py-2 text-sm text-slate-600 hover:bg-slate-50">
              Cancelar
            </button>
            <button type="submit" disabled={isPending} className="flex-1 rounded-xl bg-indigo-600 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-700 disabled:opacity-60">
              {isPending ? 'Recibiendo...' : 'Confirmar recepcion'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

export function PurchaseOrderDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const { data: po, isLoading } = usePO(id!)
  const { data: productsData } = useProducts({ limit: 200 })
  const sendPO = useSendPO()
  const confirmPO = useConfirmPO()
  const cancelPO = useCancelPO()
  const receivePO = useReceivePO()
  const deletePO = useDeletePO()
  const deconsolidatePO = useDeconsolidatePO()
  const { data: consolidationInfo } = useConsolidationInfo(id!)
  const [showReceive, setShowReceive] = useState(false)
  const updatePO = useUpdatePO()
  const [showEdit, setShowEdit] = useState(false)

  const userIds = po ? [po.created_by, po.updated_by].filter(Boolean) : []
  const { resolve } = useUserLookup(userIds)
  const productMap = Object.fromEntries((productsData?.items ?? []).map((p) => [p.id, p.name]))

  if (isLoading) return <div className="p-8 text-center text-slate-400">Cargando...</div>
  if (!po) return <div className="p-8 text-center text-slate-400">Orden no encontrada</div>

  const lines = po.lines ?? []
  const totalLines = lines.length
  const totalValue = lines.reduce((s, l) => s + Number(l.line_total), 0)
  const pendingReceive = lines.reduce((s, l) => s + Math.max(0, Number(l.qty_ordered) - Number(l.qty_received)), 0)
  const cfg = STATUS_CONFIG[po.status]

  async function handleSend() {
    await sendPO.mutateAsync(po!.id)
  }
  async function handleConfirm() {
    await confirmPO.mutateAsync(po!.id)
  }
  async function handleCancel() {
    if (!confirm('Cancelar esta orden de compra?')) return
    await cancelPO.mutateAsync(po!.id)
  }
  async function handleDelete() {
    if (!confirm('Eliminar esta orden de compra? Esta accion no se puede deshacer.')) return
    await deletePO.mutateAsync(po!.id)
    navigate('/inventario/compras')
  }
  async function handleReceive(receipts: Array<{ line_id: string; qty_received: string }>) {
    try {
      await receivePO.mutateAsync({ id: po!.id, lines: receipts })
      setShowReceive(false)
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : 'Error al recibir mercancia')
    }
  }
  async function handleDeconsolidate() {
    if (!confirm('Revertir la consolidacion? Se restauraran las OC originales.')) return
    try {
      await deconsolidatePO.mutateAsync(po!.id)
      navigate('/inventario/compras')
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : 'Error al revertir consolidacion')
    }
  }

  return (
    <div className="max-w-5xl mx-auto p-6 space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div className="space-y-1">
          <Link to="/inventario/compras" className="inline-flex items-center gap-1 text-sm text-slate-400 hover:text-indigo-600 transition-colors mb-2">
            <ArrowLeft className="h-4 w-4" /> Ordenes de Compra
          </Link>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold text-slate-900 font-mono">{po.po_number}</h1>
            <span className={cn('rounded-full px-3 py-1 text-xs font-semibold', cfg?.color)}>
              {cfg?.label ?? po.status}
            </span>
            {po.is_consolidated && (
              <span className="inline-flex items-center gap-1 rounded-full bg-blue-100 px-2.5 py-1 text-xs font-semibold text-blue-700">
                <GitMerge className="h-3.5 w-3.5" /> Consolidada
              </span>
            )}
          </div>
          <div className="flex flex-wrap gap-4 text-xs text-slate-400 mt-1">
            <span>Creado: {new Date(po.created_at).toLocaleDateString('es')}</span>
            {po.expected_date && <span>Esperado: {new Date(po.expected_date).toLocaleDateString('es')}</span>}
            {po.received_date && <span>Recibido: {new Date(po.received_date).toLocaleDateString('es')}</span>}
            {po.created_by && <span>Por: {resolve(po.created_by)}</span>}
          </div>
          {po.is_auto_generated && (
            <div className="mt-2 rounded-md bg-purple-50 border border-purple-200 px-3 py-1.5 text-xs text-purple-700">
              Generada automaticamente por reorden -- stock al momento: {po.reorder_trigger_stock ?? '--'}
            </div>
          )}
        </div>

        {/* Action buttons */}
        <div className="flex gap-2">
          {po.status === 'draft' && (
            <>
              <button onClick={() => setShowEdit(true)}
                className="flex items-center gap-2 rounded-xl border border-slate-200 px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50">
                <Pencil className="h-4 w-4" /> Editar
              </button>
              <button onClick={handleSend} disabled={sendPO.isPending}
                className="flex items-center gap-1.5 rounded-xl bg-blue-600 px-3 py-2 text-sm font-semibold text-white hover:bg-blue-700 disabled:opacity-60">
                <Send className="h-3.5 w-3.5" /> Enviar
              </button>
              <button onClick={handleDelete} disabled={deletePO.isPending}
                className="flex items-center gap-1.5 rounded-xl bg-red-600 px-3 py-2 text-sm font-semibold text-white hover:bg-red-700 disabled:opacity-60">
                <Trash2 className="h-3.5 w-3.5" /> Eliminar
              </button>
            </>
          )}
          {po.status === 'sent' && (
            <button onClick={handleConfirm} disabled={confirmPO.isPending}
              className="flex items-center gap-1.5 rounded-xl bg-indigo-600 px-3 py-2 text-sm font-semibold text-white hover:bg-indigo-700 disabled:opacity-60">
              <CheckCircle2 className="h-3.5 w-3.5" /> Confirmar
            </button>
          )}
          {(po.status === 'confirmed' || po.status === 'partial') && (
            <button onClick={() => setShowReceive(true)}
              className="flex items-center gap-1.5 rounded-xl bg-emerald-600 px-3 py-2 text-sm font-semibold text-white hover:bg-emerald-700">
              <PackageCheck className="h-3.5 w-3.5" /> Recibir
            </button>
          )}
          {!['received', 'canceled', 'consolidated'].includes(po.status) && po.status !== 'draft' && (
            <button onClick={handleCancel} disabled={cancelPO.isPending}
              className="flex items-center gap-1.5 rounded-xl border border-red-200 px-3 py-2 text-sm font-semibold text-red-600 hover:bg-red-50 disabled:opacity-60">
              <XCircle className="h-3.5 w-3.5" /> Cancelar
            </button>
          )}
        </div>
      </div>

      {/* Consolidated PO banner (this PO is a consolidated PO) */}
      {po.is_consolidated && consolidationInfo?.type === 'consolidated' && (
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
          <div className="flex items-center gap-2 mb-2">
            <GitMerge className="w-5 h-5 text-blue-600" />
            <span className="font-medium text-blue-800">Orden de compra consolidada</span>
          </div>
          <p className="text-sm text-blue-700">
            Consolida:{' '}
            {consolidationInfo.original_pos?.map((origPo, idx) => (
              <span key={origPo.id}>
                {idx > 0 && ', '}
                <Link to={`/inventario/compras/${origPo.id}`} className="underline hover:text-blue-900">
                  {origPo.po_number}
                </Link>
              </span>
            ))}
          </p>
          {consolidationInfo.consolidated_at && (
            <p className="text-xs text-blue-500 mt-1">
              Consolidada el {new Date(consolidationInfo.consolidated_at).toLocaleDateString('es')}
            </p>
          )}
          {po.status === 'draft' && (
            <button
              onClick={handleDeconsolidate}
              disabled={deconsolidatePO.isPending}
              className="mt-2 text-sm text-blue-600 hover:text-blue-800 font-medium disabled:opacity-60"
            >
              {deconsolidatePO.isPending ? 'Revirtiendo...' : 'Revertir consolidacion'}
            </button>
          )}
        </div>
      )}

      {/* Original PO that was consolidated into another */}
      {po.status === 'consolidated' && consolidationInfo?.consolidated_po && (
        <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
          <div className="flex items-center gap-2">
            <GitMerge className="w-5 h-5 text-gray-500" />
            <span className="text-gray-700">
              Esta OC fue consolidada en{' '}
              <Link to={`/inventario/compras/${consolidationInfo.consolidated_po.id}`} className="font-medium underline hover:text-gray-900">
                {consolidationInfo.consolidated_po.po_number}
              </Link>
            </span>
          </div>
        </div>
      )}

      {/* Summary cards */}
      <div className="grid grid-cols-3 gap-4">
        <div className="bg-white rounded-2xl border border-slate-100 shadow-sm p-4">
          <p className="text-xs font-semibold text-slate-400 uppercase">Total lineas</p>
          <p className="text-2xl font-bold text-slate-900 mt-1">{totalLines}</p>
        </div>
        <div className="bg-white rounded-2xl border border-slate-100 shadow-sm p-4">
          <p className="text-xs font-semibold text-slate-400 uppercase">Valor total</p>
          <p className="text-2xl font-bold text-slate-900 mt-1">${totalValue.toLocaleString('es', { minimumFractionDigits: 2 })}</p>
        </div>
        <div className="bg-white rounded-2xl border border-slate-100 shadow-sm p-4">
          <p className="text-xs font-semibold text-slate-400 uppercase">Pendiente por recibir</p>
          <p className="text-2xl font-bold text-amber-600 mt-1">{pendingReceive.toLocaleString('es', { minimumFractionDigits: 2 })}</p>
        </div>
      </div>

      {/* Notes */}
      {po.notes && (
        <div className="bg-white rounded-2xl border border-slate-100 shadow-sm p-4">
          <h3 className="text-xs font-semibold text-slate-400 uppercase mb-2">Notas</h3>
          <p className="text-sm text-slate-700 whitespace-pre-wrap">{po.notes}</p>
        </div>
      )}

      {/* Lines table */}
      <div className="bg-white rounded-2xl border border-slate-100 shadow-sm overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-slate-50 border-b border-slate-100">
            <tr>
              {['Producto', 'Qty Ordenada', 'Qty Recibida', 'Costo Unitario', 'Total Linea', 'Progreso'].map((h) => (
                <th key={h} className="px-4 py-3 text-left text-xs font-semibold text-slate-400 uppercase tracking-wide">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-50">
            {lines.map((line) => {
              const ordered = Number(line.qty_ordered)
              const received = Number(line.qty_received)
              const pct = ordered > 0 ? Math.min(100, (received / ordered) * 100) : 0
              const hasConsolidatedNote = line.notes?.includes('Consolidado desde:')
              return (
                <tr key={line.id} className="hover:bg-slate-50 transition-colors">
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2">
                      <div>
                        <p className="font-medium text-slate-700">{productMap[line.product_id] ?? 'Producto'}</p>
                        <p className="text-xs text-slate-400 font-mono">{line.product_id.slice(0, 8)}</p>
                      </div>
                      {hasConsolidatedNote && (
                        <span className="inline-flex items-center gap-0.5 rounded-full bg-blue-50 px-1.5 py-0.5 text-[10px] font-medium text-blue-600" title={line.notes ?? ''}>
                          <Info className="h-2.5 w-2.5" /> Fusionada
                        </span>
                      )}
                    </div>
                  </td>
                  <td className="px-4 py-3 font-mono text-slate-700 text-right">{line.qty_ordered}</td>
                  <td className="px-4 py-3 font-mono text-slate-700 text-right">{line.qty_received}</td>
                  <td className="px-4 py-3 font-mono text-slate-700 text-right">${Number(line.unit_cost).toLocaleString('es', { minimumFractionDigits: 2 })}</td>
                  <td className="px-4 py-3 font-mono text-slate-700 text-right">${Number(line.line_total).toLocaleString('es', { minimumFractionDigits: 2 })}</td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2">
                      <div className="flex-1 h-2 bg-slate-100 rounded-full overflow-hidden">
                        <div
                          className={cn('h-full rounded-full transition-all', pct >= 100 ? 'bg-emerald-500' : pct > 0 ? 'bg-amber-400' : 'bg-slate-200')}
                          style={{ width: `${pct}%` }}
                        />
                      </div>
                      <span className="text-xs text-slate-400 font-mono w-10 text-right">{pct.toFixed(0)}%</span>
                    </div>
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>

      {/* Activity timeline */}
      <div className="bg-white rounded-2xl border border-slate-100 shadow-sm p-4">
        <ActivityTimeline resourceType="purchase_order" resourceId={id!} />
      </div>

      {/* Receive modal */}
      {showReceive && (
        <ReceiveModal
          lines={lines}
          productMap={productMap}
          onSubmit={handleReceive}
          onClose={() => setShowReceive(false)}
          isPending={receivePO.isPending}
        />
      )}

      {/* Edit modal */}
      {showEdit && po && <EditPOModal po={po} onClose={() => setShowEdit(false)} />}
    </div>
  )
}

function EditPOModal({ po, onClose }: { po: any; onClose: () => void }) {
  const updatePO = useUpdatePO()
  const { data: warehouses = [] } = useWarehouses()
  const [form, setForm] = useState({
    expected_date: po.expected_date?.slice(0, 10) ?? '',
    notes: po.notes ?? '',
    warehouse_id: po.warehouse_id ?? '',
  })

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    await updatePO.mutateAsync({
      id: po.id,
      data: {
        expected_date: form.expected_date || null,
        notes: form.notes || null,
        warehouse_id: form.warehouse_id || null,
      },
    })
    onClose()
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 backdrop-blur-sm">
      <div className="w-full max-w-md bg-white rounded-3xl shadow-2xl p-6">
        <h2 className="text-lg font-bold text-slate-900 mb-4">Editar Orden de Compra</h2>
        <form onSubmit={handleSubmit} className="space-y-3">
          <div>
            <label className="text-xs text-slate-500 mb-1 block">Fecha esperada</label>
            <input type="date" value={form.expected_date}
              onChange={e => setForm(f => ({ ...f, expected_date: e.target.value }))}
              className="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400" />
          </div>
          <div>
            <label className="text-xs text-slate-500 mb-1 block">Bodega destino</label>
            <select value={form.warehouse_id}
              onChange={e => setForm(f => ({ ...f, warehouse_id: e.target.value }))}
              className="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400">
              <option value="">Sin asignar</option>
              {warehouses.map((w: any) => <option key={w.id} value={w.id}>{w.name}</option>)}
            </select>
          </div>
          <div>
            <label className="text-xs text-slate-500 mb-1 block">Notas</label>
            <textarea value={form.notes}
              onChange={e => setForm(f => ({ ...f, notes: e.target.value }))}
              rows={3}
              className="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400" />
          </div>
          <div className="flex gap-3 pt-2">
            <button type="button" onClick={onClose}
              className="flex-1 rounded-xl border border-slate-200 px-4 py-2 text-sm text-slate-600 hover:bg-slate-50">Cancelar</button>
            <button type="submit" disabled={updatePO.isPending}
              className="flex-1 rounded-xl bg-indigo-600 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-700 disabled:opacity-60">
              {updatePO.isPending ? 'Guardando...' : 'Guardar'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
