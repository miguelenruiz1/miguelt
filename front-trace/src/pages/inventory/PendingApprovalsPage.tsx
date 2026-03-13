import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Check, XCircle } from 'lucide-react'
import { cn } from '@/lib/utils'
import { usePendingApprovals, useApproveSalesOrder, useRejectSalesOrder } from '@/hooks/useInventory'
import { useToast } from '@/store/toast'
import type { SalesOrder } from '@/types/inventory'

function getUrgency(requestedAt: string | null): { label: string; color: string } | null {
  if (!requestedAt) return null
  const hours = (Date.now() - new Date(requestedAt).getTime()) / 3_600_000
  if (hours > 4) return { label: 'Urgente', color: 'bg-red-100 text-red-700' }
  if (hours > 1) return { label: 'Demorado', color: 'bg-orange-100 text-orange-700' }
  return null
}

function fmtWait(requestedAt: string | null): string {
  if (!requestedAt) return '--'
  const mins = Math.floor((Date.now() - new Date(requestedAt).getTime()) / 60_000)
  if (mins < 60) return `${mins}m`
  const hrs = Math.floor(mins / 60)
  if (hrs < 24) return `${hrs}h ${mins % 60}m`
  return `${Math.floor(hrs / 24)}d ${hrs % 24}h`
}

export function PendingApprovalsPage() {
  const navigate = useNavigate()
  const { data, isLoading } = usePendingApprovals({ limit: 100 })
  const approveMut = useApproveSalesOrder()
  const rejectMut = useRejectSalesOrder()
  const toast = useToast()
  const [rejectTarget, setRejectTarget] = useState<string | null>(null)
  const [rejectReason, setRejectReason] = useState('')

  const orders = data?.items ?? []
  const onError = (err: unknown) => toast.error((err as { message?: string })?.message ?? 'Error')

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-900">Aprobaciones Pendientes</h1>
        <p className="text-sm text-slate-500 mt-1">Ordenes de venta que requieren aprobación por monto</p>
      </div>

      {/* KPIs */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <div className="bg-white rounded-2xl border border-slate-200/60 p-4 text-center">
          <p className="text-xs font-bold text-slate-400 uppercase">Pendientes</p>
          <p className="text-2xl font-bold text-yellow-600 mt-1">{orders.length}</p>
        </div>
        <div className="bg-white rounded-2xl border border-slate-200/60 p-4 text-center">
          <p className="text-xs font-bold text-slate-400 uppercase">Urgentes (&gt;4h)</p>
          <p className="text-2xl font-bold text-red-600 mt-1">{orders.filter(o => { const h = o.approval_requested_at ? (Date.now() - new Date(o.approval_requested_at).getTime()) / 3_600_000 : 0; return h > 4 }).length}</p>
        </div>
        <div className="bg-white rounded-2xl border border-slate-200/60 p-4 text-center">
          <p className="text-xs font-bold text-slate-400 uppercase">Demoradas (1-4h)</p>
          <p className="text-2xl font-bold text-orange-600 mt-1">{orders.filter(o => { const h = o.approval_requested_at ? (Date.now() - new Date(o.approval_requested_at).getTime()) / 3_600_000 : 0; return h >= 1 && h <= 4 }).length}</p>
        </div>
        <div className="bg-white rounded-2xl border border-slate-200/60 p-4 text-center">
          <p className="text-xs font-bold text-slate-400 uppercase">Recientes (&lt;1h)</p>
          <p className="text-2xl font-bold text-emerald-600 mt-1">{orders.filter(o => { const h = o.approval_requested_at ? (Date.now() - new Date(o.approval_requested_at).getTime()) / 3_600_000 : 0; return h < 1 }).length}</p>
        </div>
      </div>

      {isLoading ? (
        <div className="flex justify-center py-20"><div className="animate-spin rounded-full h-6 w-6 border-b-2 border-yellow-600" /></div>
      ) : orders.length === 0 ? (
        <div className="bg-white rounded-2xl border border-slate-200/60 shadow-sm p-12 text-center">
          <Check className="h-12 w-12 text-emerald-400 mx-auto mb-3" />
          <p className="text-lg font-semibold text-slate-700">Sin aprobaciones pendientes</p>
          <p className="text-sm text-slate-400 mt-1">Todas las ordenes están al día</p>
        </div>
      ) : (
        <div className="bg-white rounded-2xl border border-slate-200/60 shadow-sm overflow-hidden">
          <table className="w-full text-sm">
            <thead><tr className="bg-slate-50 text-left text-xs font-semibold text-slate-500 uppercase">
              <th className="px-6 py-3"># Orden</th>
              <th className="px-6 py-3">Cliente</th>
              <th className="px-6 py-3 text-right">Total</th>
              <th className="px-6 py-3">Creado por</th>
              <th className="px-6 py-3">Esperando</th>
              <th className="px-6 py-3 text-right">Acciones</th>
            </tr></thead>
            <tbody className="divide-y divide-slate-100">
              {orders.map((o: SalesOrder) => {
                const urgency = getUrgency(o.approval_requested_at)
                return (
                  <tr key={o.id} className="hover:bg-slate-50/60 cursor-pointer" onClick={() => navigate(`/inventario/ventas/${o.id}`)}>
                    <td className="px-6 py-3 font-mono text-xs font-semibold">{o.order_number}</td>
                    <td className="px-6 py-3 text-slate-700">{o.customer_name ?? o.customer_id.slice(0, 8)}</td>
                    <td className="px-6 py-3 text-right font-mono font-bold">${o.total.toLocaleString('es-CO')} {o.currency}</td>
                    <td className="px-6 py-3 text-slate-500 text-xs">{o.created_by ?? '--'}</td>
                    <td className="px-6 py-3">
                      <span className="text-xs font-medium text-slate-600">{fmtWait(o.approval_requested_at)}</span>
                      {urgency && <span className={cn('ml-2 inline-flex rounded-full px-2 py-0.5 text-[10px] font-bold', urgency.color)}>{urgency.label}</span>}
                    </td>
                    <td className="px-6 py-3 text-right" onClick={e => e.stopPropagation()}>
                      <div className="flex gap-1 justify-end">
                        <button onClick={() => approveMut.mutate(o.id, { onError, onSuccess: () => toast.success(`${o.order_number} aprobada`) })} disabled={approveMut.isPending} title="Aprobar" className="p-1.5 text-emerald-600 hover:bg-emerald-50 rounded-lg disabled:opacity-50"><Check className="h-4 w-4" /></button>
                        <button onClick={() => { setRejectTarget(o.id); setRejectReason('') }} title="Rechazar" className="p-1.5 text-red-500 hover:bg-red-50 rounded-lg"><XCircle className="h-4 w-4" /></button>
                      </div>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}

      {/* Reject modal */}
      {rejectTarget && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 backdrop-blur-sm">
          <div className="w-full max-w-md bg-white rounded-3xl shadow-2xl p-6">
            <h2 className="text-lg font-bold text-slate-900 mb-1">Rechazar Orden</h2>
            <p className="text-xs text-slate-400 mb-4">Indica el motivo del rechazo (mínimo 10 caracteres).</p>
            <textarea value={rejectReason} onChange={e => setRejectReason(e.target.value)} rows={3} className="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-red-400" placeholder="Motivo del rechazo..." />
            <div className="flex justify-end gap-3 mt-4">
              <button onClick={() => setRejectTarget(null)} className="px-4 py-2 text-sm font-medium text-slate-600">Cancelar</button>
              <button onClick={() => { if (rejectReason.trim().length < 10) return; rejectMut.mutate({ id: rejectTarget, reason: rejectReason.trim() }, { onError, onSuccess: () => { setRejectTarget(null); toast.success('Orden rechazada') } }) }} disabled={rejectMut.isPending || rejectReason.trim().length < 10} className="px-5 py-2 text-sm font-semibold text-white bg-red-600 hover:bg-red-700 rounded-xl disabled:opacity-50">{rejectMut.isPending ? 'Rechazando...' : 'Rechazar'}</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
