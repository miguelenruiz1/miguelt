import { useState, useRef } from 'react'
import { Link, useParams, useNavigate } from 'react-router-dom'
import { ArrowLeft, Send, CheckCircle2, XCircle, PackageCheck, Trash2, GitMerge, Info, Pencil, Paperclip, X } from 'lucide-react'
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
  useSubmitPOForApproval,
  useApprovePO,
  useRejectPO,
} from '@/hooks/useInventory'
import { useAuthStore } from '@/store/auth'
import { inventoryPOApi } from '@/lib/inventory-api'
import { useUserLookup } from '@/hooks/useUserLookup'
import { ActivityTimeline } from '@/components/inventory/ActivityTimeline'
import type { POStatus, PurchaseOrderLine } from '@/types/inventory'

const STATUS_CONFIG: Record<string, { label: string; color: string }> = {
  draft: { label: 'Borrador', color: 'bg-slate-100 text-slate-600' },
  pending_approval: { label: 'Pendiente Aprobación', color: 'bg-orange-50 text-orange-700' },
  approved: { label: 'Aprobada', color: 'bg-indigo-50 text-indigo-700' },
  sent: { label: 'Enviada', color: 'bg-blue-50 text-blue-700' },
  confirmed: { label: 'Confirmada', color: 'bg-cyan-50 text-cyan-700' },
  partial: { label: 'Parcial', color: 'bg-amber-50 text-amber-700' },
  received: { label: 'Recibida', color: 'bg-emerald-50 text-emerald-700' },
  canceled: { label: 'Cancelada', color: 'bg-red-50 text-red-600' },
  consolidated: { label: 'Consolidada', color: 'bg-gray-100 text-gray-700' },
}

const PAYMENT_TERMS_OPTIONS = [
  { value: '', label: 'Seleccionar...' },
  { value: 'contado', label: 'Contado' },
  { value: '30_dias', label: '30 días' },
  { value: '60_dias', label: '60 días' },
  { value: '90_dias', label: '90 días' },
  { value: 'consignacion', label: 'Consignación' },
]

const FILE_CLASSIFICATIONS = [
  { value: 'invoice', label: 'Factura del proveedor' },
  { value: 'remission', label: 'Remisión' },
  { value: 'transport', label: 'Guía de transporte' },
  { value: 'photo', label: 'Foto de mercancía' },
  { value: 'other', label: 'Otro documento' },
]

interface ReceiveFormData {
  lines: Array<{ line_id: string; qty_received: string }>
  supplier_invoice_number?: string
  supplier_invoice_date?: string
  supplier_invoice_total?: number
  payment_terms?: string
  attachments?: Array<{ url: string; name: string; type: string; classification: string }>
}

function ReceiveModal({
  poId,
  lines,
  productMap,
  onSubmit,
  onClose,
  isPending,
}: {
  poId: string
  lines: PurchaseOrderLine[]
  productMap: Record<string, string>
  onSubmit: (data: ReceiveFormData) => void
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
  const [invoiceNumber, setInvoiceNumber] = useState('')
  const [invoiceDate, setInvoiceDate] = useState('')
  const [invoiceTotal, setInvoiceTotal] = useState('')
  const [paymentTerms, setPaymentTerms] = useState('')
  const [attachments, setAttachments] = useState<Array<{ file: File; classification: string }>>([])
  const fileRef = useRef<HTMLInputElement>(null)

  function handleFileSelect(e: React.ChangeEvent<HTMLInputElement>) {
    const files = Array.from(e.target.files ?? [])
    setAttachments(prev => [...prev, ...files.map(f => ({ file: f, classification: 'other' }))])
    e.target.value = ''
  }

  function removeAttachment(idx: number) {
    setAttachments(prev => prev.filter((_, i) => i !== idx))
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError('')
    const receipts = Object.entries(quantities)
      .filter(([, v]) => v && Number(v) > 0)
      .map(([line_id, qty_received]) => ({ line_id, qty_received }))
    if (receipts.length === 0) {
      setError('Ingresa al menos una cantidad a recibir')
      return
    }
    // Upload files to server first
    const uploadedAttachments: Array<{ url: string; name: string; type: string; classification: string }> = []
    for (const att of attachments) {
      try {
        const result = await inventoryPOApi.uploadAttachment(poId, att.file, att.classification)
        uploadedAttachments.push(result)
      } catch {
        setError(`Error al subir ${att.file.name}`)
        return
      }
    }
    onSubmit({
      lines: receipts,
      supplier_invoice_number: invoiceNumber || undefined,
      supplier_invoice_date: invoiceDate || undefined,
      supplier_invoice_total: invoiceTotal ? Number(invoiceTotal) : undefined,
      payment_terms: paymentTerms || undefined,
      attachments: uploadedAttachments.length > 0 ? uploadedAttachments : undefined,
    })
  }

  const cls = 'w-full rounded-lg border border-slate-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring'

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 backdrop-blur-sm">
      <div className="w-full max-w-2xl bg-white rounded-3xl shadow-2xl p-6 max-h-[90vh] overflow-y-auto">
        <h2 className="text-lg font-bold text-slate-900 mb-4">Recibir mercancía</h2>
        <form onSubmit={handleSubmit} className="space-y-5">

          {/* Lines table */}
          <div>
            <p className="text-xs font-semibold text-slate-400 uppercase mb-2">Productos a recibir</p>
            <table className="w-full text-sm">
              <thead>
                <tr className="text-xs text-slate-400 uppercase border-b border-slate-100">
                  <th className="text-left py-2">Producto</th>
                  <th className="text-right py-2">Ordenado</th>
                  <th className="text-right py-2">Recibido</th>
                  <th className="text-right py-2">Recibir ahora</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-50">
                {lines.map((line) => {
                  const remaining = Number(line.qty_ordered) - Number(line.qty_received)
                  return (
                    <tr key={line.id}>
                      <td className="py-2 text-slate-700">{productMap[line.product_id] ?? line.product_id.slice(0, 8)}</td>
                      <td className="py-2 text-right font-mono text-slate-600">{line.qty_ordered}</td>
                      <td className="py-2 text-right font-mono text-slate-600">{line.qty_received}</td>
                      <td className="py-2 text-right">
                        <input type="number" min="0" max={remaining} step="0.01"
                          value={quantities[line.id] ?? ''}
                          onChange={(e) => setQuantities((q) => ({ ...q, [line.id]: e.target.value }))}
                          placeholder="0"
                          className="w-24 rounded-lg border border-slate-200 px-2 py-1.5 text-xs text-right focus:outline-none focus:ring-2 focus:ring-ring" />
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>

          {/* Invoice data */}
          <div className="border-t border-slate-100 pt-4">
            <p className="text-xs font-semibold text-slate-400 uppercase mb-3">Datos de factura del proveedor</p>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-xs text-slate-500 mb-1 block">N° Factura</label>
                <input value={invoiceNumber} onChange={e => setInvoiceNumber(e.target.value)}
                  placeholder="FAC-2026-001" className={cls} />
              </div>
              <div>
                <label className="text-xs text-slate-500 mb-1 block">Fecha factura</label>
                <input type="date" value={invoiceDate} onChange={e => setInvoiceDate(e.target.value)} className={cls} />
              </div>
              <div>
                <label className="text-xs text-slate-500 mb-1 block">Total factura</label>
                <input type="number" step="0.01" value={invoiceTotal} onChange={e => setInvoiceTotal(e.target.value)}
                  placeholder="0.00" className={cls} />
              </div>
              <div>
                <label className="text-xs text-slate-500 mb-1 block">Términos de pago</label>
                <select value={paymentTerms} onChange={e => setPaymentTerms(e.target.value)} className={cls}>
                  {PAYMENT_TERMS_OPTIONS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
                </select>
              </div>
            </div>
          </div>

          {/* Attachments */}
          <div className="border-t border-slate-100 pt-4">
            <p className="text-xs font-semibold text-slate-400 uppercase mb-3">Documentos de soporte</p>
            <div className="space-y-2">
              {attachments.map((att, i) => (
                <div key={i} className="flex items-center gap-3 p-3 border border-slate-200 rounded-xl bg-slate-50">
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-slate-700 truncate">{att.file.name}</p>
                    <p className="text-xs text-slate-400">{(att.file.size / 1024).toFixed(0)} KB</p>
                  </div>
                  <select value={att.classification}
                    onChange={e => setAttachments(prev => prev.map((a, j) => j === i ? { ...a, classification: e.target.value } : a))}
                    className="rounded-lg border border-slate-200 px-2 py-1 text-xs focus:outline-none focus:ring-2 focus:ring-ring">
                    {FILE_CLASSIFICATIONS.map(c => <option key={c.value} value={c.value}>{c.label}</option>)}
                  </select>
                  <button type="button" onClick={() => removeAttachment(i)} className="text-slate-400 hover:text-red-500">
                    <X className="h-4 w-4" />
                  </button>
                </div>
              ))}
              <button type="button" onClick={() => fileRef.current?.click()}
                className="flex items-center gap-2 rounded-xl border border-dashed border-slate-300 px-4 py-2.5 text-sm text-slate-500 hover:border-primary hover:text-primary transition-colors w-full justify-center">
                <Paperclip className="h-4 w-4" /> Adjuntar documento
              </button>
              <input ref={fileRef} type="file" multiple accept=".pdf,.jpg,.jpeg,.png,.webp" className="hidden" onChange={handleFileSelect} />
            </div>
          </div>

          {error && (
            <p className="text-sm text-red-600 bg-red-50 border border-red-200 rounded-xl px-3 py-2">{error}</p>
          )}

          <div className="flex gap-3 pt-2 border-t border-slate-100">
            <button type="button" onClick={onClose} className="flex-1 rounded-xl border border-slate-200 px-4 py-2.5 text-sm text-slate-600 hover:bg-slate-50">
              Cancelar
            </button>
            <button type="submit" disabled={isPending} className="flex-1 rounded-xl bg-emerald-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-emerald-700 disabled:opacity-60">
              {isPending ? 'Recibiendo...' : 'Confirmar recepción'}
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
  const submitApproval = useSubmitPOForApproval()
  const approvePO = useApprovePO()
  const rejectPO = useRejectPO()
  const { hasPermission } = useAuthStore()
  const [showReject, setShowReject] = useState(false)
  const [rejectReason, setRejectReason] = useState('')

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

  async function handleCancel() {
    if (!confirm('Cancelar esta orden de compra?')) return
    await cancelPO.mutateAsync(po!.id)
  }
  async function handleDelete() {
    if (!confirm('Eliminar esta orden de compra? Esta accion no se puede deshacer.')) return
    await deletePO.mutateAsync(po!.id)
    navigate('/inventario/compras')
  }
  async function handleReceive(data: ReceiveFormData) {
    try {
      await receivePO.mutateAsync({ id: po!.id, ...data })
      setShowReceive(false)
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : 'Error al recibir mercancía')
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
          <Link to="/inventario/compras" className="inline-flex items-center gap-1 text-sm text-slate-400 hover:text-primary transition-colors mb-2">
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
          {/* Rejection reason banner */}
          {po.rejected_reason && (
            <div className="rounded-xl border border-red-200 bg-red-50 p-4 mt-4">
              <p className="text-sm font-semibold text-red-700">Rechazada</p>
              <p className="text-sm text-red-600 mt-1">{po.rejected_reason}</p>
              {po.rejected_by && <p className="text-xs text-red-400 mt-1">Por: {po.rejected_by}</p>}
            </div>
          )}
        </div>

        {/* Action buttons */}
        <div className="flex flex-wrap gap-2">
          {/* DRAFT: can submit for approval, send, edit, cancel, delete */}
          {po.status === 'draft' && (
            <>
              {hasPermission('purchase_orders.send') && (
                <button onClick={async () => { await sendPO.mutateAsync(po.id) }}
                  disabled={sendPO.isPending}
                  className="flex items-center gap-1.5 rounded-xl bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700 disabled:opacity-60">
                  <Send className="h-3.5 w-3.5" /> Enviar al proveedor
                </button>
              )}
              {hasPermission('purchase_orders.send') && (
                <button onClick={async () => { await submitApproval.mutateAsync(po.id) }}
                  disabled={submitApproval.isPending}
                  className="flex items-center gap-1.5 rounded-xl border border-orange-300 px-4 py-2 text-sm font-semibold text-orange-700 hover:bg-orange-50 disabled:opacity-60">
                  Solicitar aprobación
                </button>
              )}
              {hasPermission('purchase_orders.edit') && (
                <button onClick={() => setShowEdit(true)}
                  className="flex items-center gap-1.5 rounded-xl border border-slate-200 px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50">
                  <Pencil className="h-3.5 w-3.5" /> Editar
                </button>
              )}
              {hasPermission('purchase_orders.cancel') && (
                <button onClick={handleCancel} disabled={cancelPO.isPending}
                  className="flex items-center gap-1.5 rounded-xl border border-red-200 px-3 py-2 text-sm font-semibold text-red-600 hover:bg-red-50 disabled:opacity-60">
                  <XCircle className="h-3.5 w-3.5" /> Cancelar
                </button>
              )}
              {hasPermission('purchase_orders.delete') && (
                <button onClick={handleDelete} disabled={deletePO.isPending}
                  className="flex items-center gap-1.5 rounded-xl border border-red-200 px-3 py-2 text-sm font-semibold text-red-600 hover:bg-red-50 disabled:opacity-60">
                  <Trash2 className="h-3.5 w-3.5" /> Eliminar
                </button>
              )}
            </>
          )}

          {/* PENDING APPROVAL: approve or reject */}
          {po.status === 'pending_approval' && (
            <>
              {hasPermission('purchase_orders.approve') && (
                <button onClick={async () => { await approvePO.mutateAsync(po.id) }}
                  disabled={approvePO.isPending}
                  className="flex items-center gap-1.5 rounded-xl bg-emerald-600 px-4 py-2 text-sm font-semibold text-white hover:bg-emerald-700 disabled:opacity-60">
                  <CheckCircle2 className="h-3.5 w-3.5" /> Aprobar
                </button>
              )}
              {hasPermission('purchase_orders.approve') && (
                <button onClick={() => setShowReject(true)}
                  className="flex items-center gap-1.5 rounded-xl border border-red-200 px-4 py-2 text-sm font-semibold text-red-600 hover:bg-red-50">
                  <XCircle className="h-3.5 w-3.5" /> Rechazar
                </button>
              )}
            </>
          )}

          {/* APPROVED: can send to supplier */}
          {po.status === 'approved' && (
            <>
              {hasPermission('purchase_orders.send') && (
                <button onClick={async () => { await sendPO.mutateAsync(po.id) }}
                  disabled={sendPO.isPending}
                  className="flex items-center gap-1.5 rounded-xl bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700 disabled:opacity-60">
                  <Send className="h-3.5 w-3.5" /> Enviar al proveedor
                </button>
              )}
            </>
          )}

          {/* SENT: can confirm */}
          {po.status === 'sent' && (
            <>
              {hasPermission('purchase_orders.confirm') && (
                <button onClick={async () => { await confirmPO.mutateAsync(po.id) }}
                  disabled={confirmPO.isPending}
                  className="flex items-center gap-1.5 rounded-xl bg-cyan-600 px-4 py-2 text-sm font-semibold text-white hover:bg-cyan-700 disabled:opacity-60">
                  <CheckCircle2 className="h-3.5 w-3.5" /> Confirmar recepción proveedor
                </button>
              )}
              {hasPermission('purchase_orders.cancel') && (
                <button onClick={handleCancel} disabled={cancelPO.isPending}
                  className="flex items-center gap-1.5 rounded-xl border border-red-200 px-3 py-2 text-sm font-semibold text-red-600 hover:bg-red-50 disabled:opacity-60">
                  <XCircle className="h-3.5 w-3.5" /> Cancelar
                </button>
              )}
            </>
          )}

          {/* CONFIRMED: can receive */}
          {po.status === 'confirmed' && (
            <>
              {hasPermission('purchase_orders.receive') && (
                <button onClick={() => setShowReceive(true)}
                  className="flex items-center gap-1.5 rounded-xl bg-emerald-600 px-4 py-2 text-sm font-semibold text-white hover:bg-emerald-700">
                  <PackageCheck className="h-3.5 w-3.5" /> Recibir mercancía
                </button>
              )}
              {hasPermission('purchase_orders.cancel') && (
                <button onClick={handleCancel} disabled={cancelPO.isPending}
                  className="flex items-center gap-1.5 rounded-xl border border-red-200 px-3 py-2 text-sm font-semibold text-red-600 hover:bg-red-50 disabled:opacity-60">
                  <XCircle className="h-3.5 w-3.5" /> Cancelar
                </button>
              )}
            </>
          )}

          {/* PARTIAL: can receive remaining */}
          {po.status === 'partial' && (
            <>
              {hasPermission('purchase_orders.receive') && (
                <button onClick={() => setShowReceive(true)}
                  className="flex items-center gap-1.5 rounded-xl bg-emerald-600 px-4 py-2 text-sm font-semibold text-white hover:bg-emerald-700">
                  <PackageCheck className="h-3.5 w-3.5" /> Recibir restante
                </button>
              )}
              {hasPermission('purchase_orders.cancel') && (
                <button onClick={handleCancel} disabled={cancelPO.isPending}
                  className="flex items-center gap-1.5 rounded-xl border border-red-200 px-3 py-2 text-sm font-semibold text-red-600 hover:bg-red-50 disabled:opacity-60">
                  <XCircle className="h-3.5 w-3.5" /> Cancelar
                </button>
              )}
            </>
          )}
        </div>
      </div>

      {/* Reject modal */}
      {showReject && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 backdrop-blur-sm">
          <div className="w-full max-w-md bg-white rounded-2xl shadow-2xl p-6">
            <h3 className="text-lg font-bold text-slate-900 mb-3">Rechazar Orden de Compra</h3>
            <p className="text-sm text-slate-500 mb-4">Indica el motivo del rechazo. La OC volverá a estado borrador para que el creador la corrija.</p>
            <textarea
              value={rejectReason}
              onChange={e => setRejectReason(e.target.value)}
              placeholder="Motivo del rechazo..."
              rows={3}
              className="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring resize-none"
            />
            <div className="flex gap-3 mt-4">
              <button onClick={() => { setShowReject(false); setRejectReason('') }}
                className="flex-1 rounded-xl border border-slate-200 px-4 py-2 text-sm text-slate-600 hover:bg-slate-50">
                Cancelar
              </button>
              <button
                onClick={async () => {
                  if (!rejectReason.trim()) return
                  await rejectPO.mutateAsync({ id: po.id, reason: rejectReason })
                  setShowReject(false)
                  setRejectReason('')
                }}
                disabled={!rejectReason.trim() || rejectPO.isPending}
                className="flex-1 rounded-xl bg-red-600 px-4 py-2 text-sm font-semibold text-white hover:bg-red-700 disabled:opacity-60">
                {rejectPO.isPending ? 'Rechazando...' : 'Rechazar OC'}
              </button>
            </div>
          </div>
        </div>
      )}

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

      {/* Invoice / receipt data */}
      {(po.supplier_invoice_number || po.payment_terms) && (
        <div className="rounded-xl border border-slate-200 bg-slate-50 p-4 space-y-2 mt-4">
          <p className="text-xs font-semibold text-slate-400 uppercase">Datos de Factura</p>
          <div className="grid grid-cols-2 gap-3 text-sm">
            {po.supplier_invoice_number && (
              <div><span className="text-slate-500">N° Factura:</span> <span className="font-medium">{po.supplier_invoice_number}</span></div>
            )}
            {po.supplier_invoice_date && (
              <div><span className="text-slate-500">Fecha factura:</span> <span className="font-medium">{new Date(po.supplier_invoice_date).toLocaleDateString('es')}</span></div>
            )}
            {po.supplier_invoice_total != null && (
              <div><span className="text-slate-500">Total factura:</span> <span className="font-medium">${Number(po.supplier_invoice_total).toLocaleString('es-CO')}</span></div>
            )}
            {po.payment_terms && (
              <div><span className="text-slate-500">Términos pago:</span> <span className="font-medium">{po.payment_terms}</span></div>
            )}
            {po.payment_due_date && (
              <div><span className="text-slate-500">Vence:</span> <span className="font-medium">{new Date(po.payment_due_date).toLocaleDateString('es')}</span></div>
            )}
          </div>
        </div>
      )}

      {/* Attachments / Documents */}
      {po.attachments && po.attachments.length > 0 && (
        <div className="bg-white rounded-2xl border border-slate-100 shadow-sm p-4 space-y-3">
          <p className="text-xs font-semibold text-slate-400 uppercase">Documentos adjuntos ({po.attachments.length})</p>
          <div className="space-y-2">
            {po.attachments.map((att, i) => {
              const classLabel = {
                invoice: 'Factura',
                remission: 'Remisión',
                transport: 'Guía transporte',
                photo: 'Foto',
                other: 'Otro',
              }[att.classification || att.type || 'other'] ?? 'Documento'
              const classColor = {
                invoice: 'bg-blue-50 text-blue-700',
                remission: 'bg-purple-50 text-purple-700',
                transport: 'bg-orange-50 text-orange-700',
                photo: 'bg-green-50 text-green-700',
                other: 'bg-slate-100 text-slate-600',
              }[att.classification || att.type || 'other'] ?? 'bg-slate-100 text-slate-600'
              return (
                <div key={i} className="flex items-center gap-3 p-3 border border-slate-100 rounded-xl hover:bg-slate-50 transition-colors">
                  <Paperclip className="h-4 w-4 text-slate-400 shrink-0" />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-slate-700 truncate">{att.name}</p>
                  </div>
                  <span className={cn('rounded-full px-2 py-0.5 text-[10px] font-semibold', classColor)}>
                    {classLabel}
                  </span>
                  {att.url && (
                    <a href={att.url.startsWith('http') ? att.url : `${import.meta.env.VITE_API_URL ?? 'http://localhost:9000'}${att.url}`}
                      target="_blank" rel="noopener noreferrer"
                      className="text-xs text-primary hover:underline shrink-0">
                      Ver
                    </a>
                  )}
                </div>
              )
            })}
          </div>
        </div>
      )}

      {/* Workflow timeline */}
      {(po.sent_at || po.confirmed_at || po.approved_at) && (
        <div className="rounded-xl border border-slate-200 p-4 space-y-2 mt-4">
          <p className="text-xs font-semibold text-slate-400 uppercase">Historial</p>
          <div className="space-y-1.5 text-sm">
            {po.approved_at && (
              <div className="flex justify-between"><span className="text-slate-500">Aprobada</span><span className="text-slate-700">{new Date(po.approved_at).toLocaleString('es')}</span></div>
            )}
            {po.sent_at && (
              <div className="flex justify-between"><span className="text-slate-500">Enviada</span><span className="text-slate-700">{new Date(po.sent_at).toLocaleString('es')}</span></div>
            )}
            {po.confirmed_at && (
              <div className="flex justify-between"><span className="text-slate-500">Confirmada</span><span className="text-slate-700">{new Date(po.confirmed_at).toLocaleString('es')}</span></div>
            )}
            {po.received_date && (
              <div className="flex justify-between"><span className="text-slate-500">Recibida</span><span className="text-slate-700">{new Date(po.received_date).toLocaleString('es')}</span></div>
            )}
          </div>
        </div>
      )}

      {/* Activity timeline */}
      <div className="bg-white rounded-2xl border border-slate-100 shadow-sm p-4">
        <ActivityTimeline resourceType="purchase_order" resourceId={id!} />
      </div>

      {/* Receive modal */}
      {showReceive && (
        <ReceiveModal
          poId={po.id}
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
              className="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring" />
          </div>
          <div>
            <label className="text-xs text-slate-500 mb-1 block">Bodega destino</label>
            <select value={form.warehouse_id}
              onChange={e => setForm(f => ({ ...f, warehouse_id: e.target.value }))}
              className="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring">
              <option value="">Sin asignar</option>
              {warehouses.map((w: any) => <option key={w.id} value={w.id}>{w.name}</option>)}
            </select>
          </div>
          <div>
            <label className="text-xs text-slate-500 mb-1 block">Notas</label>
            <textarea value={form.notes}
              onChange={e => setForm(f => ({ ...f, notes: e.target.value }))}
              rows={3}
              className="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring" />
          </div>
          <div className="flex gap-3 pt-2">
            <button type="button" onClick={onClose}
              className="flex-1 rounded-xl border border-slate-200 px-4 py-2 text-sm text-slate-600 hover:bg-slate-50">Cancelar</button>
            <button type="submit" disabled={updatePO.isPending}
              className="flex-1 rounded-xl bg-primary px-4 py-2 text-sm font-semibold text-white hover:bg-primary/90 disabled:opacity-60">
              {updatePO.isPending ? 'Guardando...' : 'Guardar'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
