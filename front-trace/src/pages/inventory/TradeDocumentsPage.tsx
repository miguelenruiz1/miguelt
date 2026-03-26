import { useState } from 'react'
import { FileCheck, FilePlus, Shield, Stamp, Building2, FileText, Check, X } from 'lucide-react'
import { useTradeDocuments, useCreateTradeDoc, useApproveTradeDoc, useRejectTradeDoc, useDeleteTradeDoc } from '@/hooks/useInventory'
import type { TradeDocCreate, TradeDocType, TradeDocStatus } from '@/types/inventory'
import { useToastStore } from '@/store/toast'
import { useConfirmStore } from '@/store/confirm'

const DOC_TYPES: { value: TradeDocType; label: string; icon: typeof FileCheck }[] = [
  { value: 'cert_origen', label: 'Cert. Origen', icon: Stamp },
  { value: 'fitosanitario', label: 'Fitosanitario', icon: Shield },
  { value: 'invima', label: 'INVIMA', icon: Shield },
  { value: 'dex', label: 'DEX (Exportacion)', icon: Building2 },
  { value: 'dim', label: 'DIM (Importacion)', icon: Building2 },
  { value: 'factura_comercial', label: 'Factura Comercial', icon: FileText },
  { value: 'packing_list', label: 'Packing List', icon: FileText },
  { value: 'insurance_cert', label: 'Cert. Seguro', icon: FileCheck },
]

const STATUS_COLORS: Record<TradeDocStatus, string> = {
  pending: 'bg-amber-100 text-amber-700',
  approved: 'bg-green-100 text-green-700',
  rejected: 'bg-red-100 text-red-700',
  expired: 'bg-gray-100 text-gray-500',
}

const STATUS_LABELS: Record<TradeDocStatus, string> = {
  pending: 'Pendiente',
  approved: 'Aprobado',
  rejected: 'Rechazado',
  expired: 'Vencido',
}

const ANCHOR_COLORS: Record<string, string> = {
  none: 'bg-gray-100 text-gray-600',
  pending: 'bg-amber-100 text-amber-700',
  anchored: 'bg-emerald-100 text-emerald-700',
  failed: 'bg-red-100 text-red-700',
}

export default function TradeDocumentsPage() {
  const [typeFilter, setTypeFilter] = useState<string>('')
  const [showCreate, setShowCreate] = useState(false)
  const { data: docs, isLoading } = useTradeDocuments(typeFilter ? { document_type: typeFilter } : undefined)
  const createMut = useCreateTradeDoc()
  const approveMut = useApproveTradeDoc()
  const rejectMut = useRejectTradeDoc()
  const deleteMut = useDeleteTradeDoc()
  const toast = useToastStore()
  const confirm = useConfirmStore()

  const [form, setForm] = useState<Partial<TradeDocCreate>>({ document_type: 'cert_origen', title: '' })

  const handleCreate = async () => {
    if (!form.title || !form.document_type) return
    try {
      await createMut.mutateAsync(form as TradeDocCreate)
      toast.success('Documento creado y anclado en blockchain')
      setShowCreate(false)
      setForm({ document_type: 'cert_origen', title: '' })
    } catch (e: any) {
      toast.error(e.message || 'Error al crear')
    }
  }

  const handleApprove = async (id: string) => {
    try {
      await approveMut.mutateAsync(id)
      toast.success('Documento aprobado y anclado en blockchain')
    } catch (e: any) {
      toast.error(e.message)
    }
  }

  const handleReject = (id: string) => {
    const reason = prompt('Razon del rechazo:')
    if (reason !== null) {
      rejectMut.mutateAsync({ id, reason: reason || undefined })
        .then(() => toast.success('Documento rechazado'))
        .catch((e: any) => toast.error(e.message))
    }
  }

  const handleDelete = (id: string) => {
    confirm.open({
      title: 'Eliminar documento',
      message: 'Esta seguro de eliminar este documento de comercio exterior?',
      onConfirm: async () => {
        await deleteMut.mutateAsync(id)
        toast.success('Eliminado')
      },
    })
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Documentos de Comercio Exterior</h1>
          <p className="text-sm text-gray-500 mt-1">Certificados, declaraciones aduaneras y documentos de cumplimiento</p>
        </div>
        <button onClick={() => setShowCreate(true)} className="inline-flex items-center gap-2 px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700">
          <FilePlus className="h-4 w-4" /> Nuevo Documento
        </button>
      </div>

      {/* Type filters */}
      <div className="flex gap-2 flex-wrap">
        <button onClick={() => setTypeFilter('')} className={`px-3 py-1.5 rounded-full text-sm font-medium ${!typeFilter ? 'bg-indigo-100 text-indigo-700' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'}`}>
          Todos
        </button>
        {DOC_TYPES.map(dt => (
          <button key={dt.value} onClick={() => setTypeFilter(dt.value)} className={`px-3 py-1.5 rounded-full text-sm font-medium inline-flex items-center gap-1.5 ${typeFilter === dt.value ? 'bg-indigo-100 text-indigo-700' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'}`}>
            <dt.icon className="h-3.5 w-3.5" /> {dt.label}
          </button>
        ))}
      </div>

      {/* Table */}
      {isLoading ? (
        <div className="text-center py-12 text-gray-500">Cargando...</div>
      ) : !docs?.length ? (
        <div className="text-center py-12 text-gray-400">No hay documentos de comercio exterior</div>
      ) : (
        <div className="bg-white rounded-xl border overflow-hidden">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Tipo</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Numero</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Titulo</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Autoridad</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">HS Code</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Estado</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Blockchain</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Acciones</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {docs.map(d => (
                <tr key={d.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3">
                    <span className="text-xs font-medium uppercase bg-gray-100 px-2 py-0.5 rounded">{d.document_type.replace('_', ' ')}</span>
                  </td>
                  <td className="px-4 py-3 font-mono text-sm">{d.document_number || '-'}</td>
                  <td className="px-4 py-3 text-sm max-w-[200px] truncate">{d.title}</td>
                  <td className="px-4 py-3 text-sm">{d.issuing_authority || '-'}</td>
                  <td className="px-4 py-3 font-mono text-xs">{d.hs_code || '-'}</td>
                  <td className="px-4 py-3">
                    <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${STATUS_COLORS[d.status]}`}>
                      {STATUS_LABELS[d.status] || d.status}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${ANCHOR_COLORS[d.anchor_status] || ANCHOR_COLORS.none}`}>
                      {d.anchor_status}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex gap-1">
                      {d.status === 'pending' && (
                        <>
                          <button onClick={() => handleApprove(d.id)} className="text-xs text-green-600 hover:underline inline-flex items-center gap-0.5">
                            <Check className="h-3 w-3" /> Aprobar
                          </button>
                          <button onClick={() => handleReject(d.id)} className="text-xs text-red-600 hover:underline inline-flex items-center gap-0.5">
                            <X className="h-3 w-3" /> Rechazar
                          </button>
                        </>
                      )}
                      <button onClick={() => handleDelete(d.id)} className="text-xs text-red-500 hover:underline ml-2">Eliminar</button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Create Modal */}
      {showCreate && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50" onClick={() => setShowCreate(false)}>
          <div className="bg-white rounded-xl p-6 w-full max-w-2xl max-h-[90vh] overflow-y-auto" onClick={e => e.stopPropagation()}>
            <h2 className="text-lg font-semibold mb-4">Nuevo Documento de Comercio Exterior</h2>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Tipo</label>
                <select value={form.document_type} onChange={e => setForm({ ...form, document_type: e.target.value as TradeDocType })} className="w-full border rounded-lg px-3 py-2 text-sm">
                  {DOC_TYPES.map(dt => <option key={dt.value} value={dt.value}>{dt.label}</option>)}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Numero</label>
                <input value={form.document_number || ''} onChange={e => setForm({ ...form, document_number: e.target.value })} className="w-full border rounded-lg px-3 py-2 text-sm" />
              </div>
              <div className="col-span-2">
                <label className="block text-sm font-medium text-gray-700 mb-1">Titulo *</label>
                <input value={form.title || ''} onChange={e => setForm({ ...form, title: e.target.value })} className="w-full border rounded-lg px-3 py-2 text-sm" placeholder="Certificado de Origen TLC CO-US" />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Autoridad Emisora</label>
                <input value={form.issuing_authority || ''} onChange={e => setForm({ ...form, issuing_authority: e.target.value })} className="w-full border rounded-lg px-3 py-2 text-sm" placeholder="DIAN, ICA, INVIMA..." />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Pais Emisor</label>
                <input value={form.issuing_country || ''} onChange={e => setForm({ ...form, issuing_country: e.target.value })} className="w-full border rounded-lg px-3 py-2 text-sm" placeholder="CO" maxLength={3} />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Codigo Arancelario (HS)</label>
                <input value={form.hs_code || ''} onChange={e => setForm({ ...form, hs_code: e.target.value })} className="w-full border rounded-lg px-3 py-2 text-sm font-mono" placeholder="0901.21.10" />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Valor FOB</label>
                <input type="number" value={form.fob_value || ''} onChange={e => setForm({ ...form, fob_value: Number(e.target.value) })} className="w-full border rounded-lg px-3 py-2 text-sm" />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Valor CIF</label>
                <input type="number" value={form.cif_value || ''} onChange={e => setForm({ ...form, cif_value: Number(e.target.value) })} className="w-full border rounded-lg px-3 py-2 text-sm" />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Moneda</label>
                <select value={form.currency || 'USD'} onChange={e => setForm({ ...form, currency: e.target.value })} className="w-full border rounded-lg px-3 py-2 text-sm">
                  <option value="USD">USD</option>
                  <option value="COP">COP</option>
                  <option value="EUR">EUR</option>
                </select>
              </div>
              <div className="col-span-2">
                <label className="block text-sm font-medium text-gray-700 mb-1">Descripcion</label>
                <textarea value={form.description || ''} onChange={e => setForm({ ...form, description: e.target.value })} className="w-full border rounded-lg px-3 py-2 text-sm" rows={2} />
              </div>
            </div>
            <div className="flex justify-end gap-3 mt-6">
              <button onClick={() => setShowCreate(false)} className="px-4 py-2 text-sm text-gray-600 hover:bg-gray-100 rounded-lg">Cancelar</button>
              <button onClick={handleCreate} disabled={createMut.isPending} className="px-4 py-2 text-sm bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-50">
                {createMut.isPending ? 'Creando...' : 'Crear'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
