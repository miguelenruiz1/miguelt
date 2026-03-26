import { useState } from 'react'
import { Ship, Truck, Plane, FileText, Plus, ExternalLink, MoreHorizontal, ArrowRightLeft } from 'lucide-react'
import { useShipmentDocuments, useCreateShipment, useUpdateShipmentStatus, useDeleteShipment } from '@/hooks/useInventory'
import type { ShipmentDocCreate, ShipmentDocType, ShipmentStatus } from '@/types/inventory'
import { useToastStore } from '@/store/toast'
import { useConfirmStore } from '@/store/confirm'

const DOC_TYPES: { value: ShipmentDocType; label: string; icon: typeof Ship }[] = [
  { value: 'remision', label: 'Remision', icon: FileText },
  { value: 'bl', label: 'Bill of Lading', icon: Ship },
  { value: 'awb', label: 'Air Waybill', icon: Plane },
  { value: 'carta_porte', label: 'Carta Porte', icon: Truck },
  { value: 'guia_terrestre', label: 'Guia Terrestre', icon: Truck },
]

const STATUS_COLORS: Record<ShipmentStatus, string> = {
  draft: 'bg-gray-100 text-gray-700',
  issued: 'bg-blue-100 text-blue-700',
  in_transit: 'bg-yellow-100 text-yellow-700',
  delivered: 'bg-green-100 text-green-700',
  canceled: 'bg-red-100 text-red-700',
}

const STATUS_LABELS: Record<ShipmentStatus, string> = {
  draft: 'Borrador',
  issued: 'Emitido',
  in_transit: 'En Transito',
  delivered: 'Entregado',
  canceled: 'Cancelado',
}

const ANCHOR_COLORS: Record<string, string> = {
  none: 'bg-gray-100 text-gray-600',
  pending: 'bg-amber-100 text-amber-700',
  anchored: 'bg-emerald-100 text-emerald-700',
  failed: 'bg-red-100 text-red-700',
}

export default function ShipmentsPage() {
  const [typeFilter, setTypeFilter] = useState<string>('')
  const [showCreate, setShowCreate] = useState(false)
  const { data: shipments, isLoading } = useShipmentDocuments(typeFilter ? { document_type: typeFilter } : undefined)
  const createMut = useCreateShipment()
  const statusMut = useUpdateShipmentStatus()
  const deleteMut = useDeleteShipment()
  const toast = useToastStore()
  const confirm = useConfirmStore()

  const [form, setForm] = useState<Partial<ShipmentDocCreate>>({ document_type: 'remision', document_number: '' })

  const handleCreate = async () => {
    if (!form.document_number || !form.document_type) return
    try {
      await createMut.mutateAsync(form as ShipmentDocCreate)
      toast.success('Documento de transporte creado')
      setShowCreate(false)
      setForm({ document_type: 'remision', document_number: '' })
    } catch (e: any) {
      toast.error(e.message || 'Error al crear')
    }
  }

  const handleStatus = async (id: string, status: string) => {
    try {
      await statusMut.mutateAsync({ id, status })
      toast.success(`Estado actualizado: ${STATUS_LABELS[status as ShipmentStatus] || status}`)
    } catch (e: any) {
      toast.error(e.message)
    }
  }

  const handleDelete = (id: string) => {
    confirm.open({
      title: 'Eliminar documento',
      message: 'Esta seguro de eliminar este documento de transporte?',
      onConfirm: async () => {
        await deleteMut.mutateAsync(id)
        toast.success('Eliminado')
      },
    })
  }

  const getIcon = (type: string) => {
    if (type === 'bl') return <Ship className="h-4 w-4" />
    if (type === 'awb') return <Plane className="h-4 w-4" />
    return <Truck className="h-4 w-4" />
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Documentos de Transporte</h1>
          <p className="text-sm text-gray-500 mt-1">Guias de remision, BL, AWB, carta porte</p>
        </div>
        <button onClick={() => setShowCreate(true)} className="inline-flex items-center gap-2 px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700">
          <Plus className="h-4 w-4" /> Nuevo Documento
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
      ) : !shipments?.length ? (
        <div className="text-center py-12 text-gray-400">No hay documentos de transporte</div>
      ) : (
        <div className="bg-white rounded-xl border overflow-hidden">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Tipo</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Numero</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Ruta</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Transportista</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Estado</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Blockchain</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Acciones</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {shipments.map(s => (
                <tr key={s.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2">
                      {getIcon(s.document_type)}
                      <span className="text-xs font-medium uppercase">{s.document_type}</span>
                    </div>
                  </td>
                  <td className="px-4 py-3 font-mono text-sm">{s.document_number}</td>
                  <td className="px-4 py-3 text-sm">
                    {s.origin_city || s.origin_country || '-'} <ArrowRightLeft className="h-3 w-3 inline mx-1" /> {s.destination_city || s.destination_country || '-'}
                  </td>
                  <td className="px-4 py-3 text-sm">{s.carrier_name || '-'}</td>
                  <td className="px-4 py-3">
                    <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${STATUS_COLORS[s.status]}`}>
                      {STATUS_LABELS[s.status] || s.status}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${ANCHOR_COLORS[s.anchor_status] || ANCHOR_COLORS.none}`}>
                      {s.anchor_status}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex gap-1">
                      {s.status === 'draft' && (
                        <button onClick={() => handleStatus(s.id, 'issued')} className="text-xs text-blue-600 hover:underline">Emitir</button>
                      )}
                      {s.status === 'issued' && (
                        <button onClick={() => handleStatus(s.id, 'in_transit')} className="text-xs text-yellow-600 hover:underline">En Transito</button>
                      )}
                      {s.status === 'in_transit' && (
                        <button onClick={() => handleStatus(s.id, 'delivered')} className="text-xs text-green-600 hover:underline">Entregado</button>
                      )}
                      {s.tracking_url && (
                        <a href={s.tracking_url} target="_blank" rel="noopener noreferrer" className="text-xs text-indigo-600 hover:underline inline-flex items-center gap-0.5">
                          <ExternalLink className="h-3 w-3" /> Track
                        </a>
                      )}
                      <button onClick={() => handleDelete(s.id)} className="text-xs text-red-500 hover:underline ml-2">Eliminar</button>
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
            <h2 className="text-lg font-semibold mb-4">Nuevo Documento de Transporte</h2>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Tipo</label>
                <select value={form.document_type} onChange={e => setForm({ ...form, document_type: e.target.value as ShipmentDocType })} className="w-full border rounded-lg px-3 py-2 text-sm">
                  {DOC_TYPES.map(dt => <option key={dt.value} value={dt.value}>{dt.label}</option>)}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Numero *</label>
                <input value={form.document_number || ''} onChange={e => setForm({ ...form, document_number: e.target.value })} className="w-full border rounded-lg px-3 py-2 text-sm" placeholder="REM-2026-001" />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Transportista</label>
                <input value={form.carrier_name || ''} onChange={e => setForm({ ...form, carrier_name: e.target.value })} className="w-full border rounded-lg px-3 py-2 text-sm" />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Placa</label>
                <input value={form.vehicle_plate || ''} onChange={e => setForm({ ...form, vehicle_plate: e.target.value })} className="w-full border rounded-lg px-3 py-2 text-sm" />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Ciudad Origen</label>
                <input value={form.origin_city || ''} onChange={e => setForm({ ...form, origin_city: e.target.value })} className="w-full border rounded-lg px-3 py-2 text-sm" />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Ciudad Destino</label>
                <input value={form.destination_city || ''} onChange={e => setForm({ ...form, destination_city: e.target.value })} className="w-full border rounded-lg px-3 py-2 text-sm" />
              </div>
              {(form.document_type === 'bl') && (
                <>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Buque</label>
                    <input value={form.vessel_name || ''} onChange={e => setForm({ ...form, vessel_name: e.target.value })} className="w-full border rounded-lg px-3 py-2 text-sm" />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Contenedor</label>
                    <input value={form.container_number || ''} onChange={e => setForm({ ...form, container_number: e.target.value })} className="w-full border rounded-lg px-3 py-2 text-sm" />
                  </div>
                </>
              )}
              {(form.document_type === 'awb') && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Numero de Vuelo</label>
                  <input value={form.flight_number || ''} onChange={e => setForm({ ...form, flight_number: e.target.value })} className="w-full border rounded-lg px-3 py-2 text-sm" />
                </div>
              )}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Paquetes</label>
                <input type="number" value={form.total_packages || ''} onChange={e => setForm({ ...form, total_packages: Number(e.target.value) })} className="w-full border rounded-lg px-3 py-2 text-sm" />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Peso (kg)</label>
                <input type="number" value={form.total_weight_kg || ''} onChange={e => setForm({ ...form, total_weight_kg: Number(e.target.value) })} className="w-full border rounded-lg px-3 py-2 text-sm" />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Tracking #</label>
                <input value={form.tracking_number || ''} onChange={e => setForm({ ...form, tracking_number: e.target.value })} className="w-full border rounded-lg px-3 py-2 text-sm" />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Tracking URL</label>
                <input value={form.tracking_url || ''} onChange={e => setForm({ ...form, tracking_url: e.target.value })} className="w-full border rounded-lg px-3 py-2 text-sm" />
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
