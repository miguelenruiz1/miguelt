import { useState } from 'react'
import {
  ArrowDown, Plus, Trash2, Edit2, Check, X, Loader2,
  Factory, Warehouse, Truck, Ship, Shield, Globe, User,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import {
  useSupplyChain, useAddSupplyChainNode,
  useUpdateSupplyChainNode, useDeleteSupplyChainNode,
} from '@/hooks/useCompliance'
import type { CreateSupplyChainNodeInput, SupplyChainNode } from '@/types/compliance'
import { useToast } from '@/store/toast'

const ROLE_CONFIG: Record<string, { label: string; icon: typeof Factory; color: string }> = {
  producer: { label: 'Productor', icon: Factory, color: 'bg-green-50 text-green-700 border-green-200' },
  collector: { label: 'Recolector', icon: Warehouse, color: 'bg-amber-50 text-amber-700 border-amber-200' },
  processor: { label: 'Procesador', icon: Factory, color: 'bg-purple-50 text-purple-700 border-purple-200' },
  exporter: { label: 'Exportador', icon: Ship, color: 'bg-blue-50 text-blue-700 border-blue-200' },
  importer: { label: 'Importador', icon: Globe, color: 'bg-cyan-50 text-cyan-700 border-cyan-200' },
  trader: { label: 'Comerciante', icon: User, color: 'bg-orange-50 text-orange-700 border-orange-200' },
}

const VERIFICATION_BADGE: Record<string, { label: string; color: string }> = {
  unverified: { label: 'Sin verificar', color: 'bg-slate-50 text-slate-600 border-slate-200' },
  verified: { label: 'Verificado', color: 'bg-green-50 text-green-700 border-green-200' },
  flagged: { label: 'Marcado', color: 'bg-red-50 text-red-700 border-red-200' },
}

interface Props {
  recordId: string
}

export default function SupplyChainEditor({ recordId }: Props) {
  const { data: nodes = [], isLoading } = useSupplyChain(recordId)
  const addNode = useAddSupplyChainNode(recordId)
  const updateNode = useUpdateSupplyChainNode(recordId)
  const deleteNode = useDeleteSupplyChainNode(recordId)
  const toast = useToast()

  const [showForm, setShowForm] = useState(false)
  const [editingId, setEditingId] = useState<string | null>(null)
  const [form, setForm] = useState<CreateSupplyChainNodeInput>({
    sequence_order: (nodes.length || 0) + 1,
    role: 'producer',
    actor_name: '',
    actor_country: '',
    actor_address: '',
    actor_tax_id: '',
    actor_eori: '',
    handoff_date: '',
    quantity_kg: undefined,
    notes: '',
  })

  const set = (key: string, value: unknown) => setForm(f => ({ ...f, [key]: value }))

  function resetForm() {
    setForm({
      sequence_order: nodes.length + 2,
      role: 'producer',
      actor_name: '',
      actor_country: '',
      actor_address: '',
      actor_tax_id: '',
      actor_eori: '',
      handoff_date: '',
      quantity_kg: undefined,
      notes: '',
    })
  }

  async function handleAdd(e: React.FormEvent) {
    e.preventDefault()
    try {
      const data: CreateSupplyChainNodeInput = {
        ...form,
        sequence_order: form.sequence_order ?? nodes.length + 1,
        quantity_kg: form.quantity_kg ? Number(form.quantity_kg) : undefined,
        handoff_date: (form.handoff_date as string) || undefined,
      }
      await addNode.mutateAsync(data)
      resetForm()
      setShowForm(false)
      toast.success('Actor agregado')
    } catch (e: any) {
      toast.error(e.message)
    }
  }

  async function handleDelete(nodeId: string) {
    try {
      await deleteNode.mutateAsync(nodeId)
      toast.success('Actor eliminado')
    } catch (e: any) {
      toast.error(e.message)
    }
  }

  if (isLoading) return <div className="text-sm text-slate-400 py-6 text-center">Cargando...</div>

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm font-semibold text-slate-700">Cadena de suministro</p>
          <p className="text-xs text-slate-500">EUDR Art. 9.1.e-f — Cada actor desde productor hasta importador</p>
        </div>
        <button onClick={() => { resetForm(); setShowForm(!showForm) }}
          className="flex items-center gap-1.5 rounded-xl bg-primary px-3 py-1.5 text-xs font-semibold text-white hover:bg-primary/90 transition-colors">
          <Plus className="h-3.5 w-3.5" /> Agregar actor
        </button>
      </div>

      {/* Add form */}
      {showForm && (
        <form onSubmit={handleAdd} className="rounded-xl border border-primary/30 bg-primary/5 p-4 space-y-3">
          <div className="grid grid-cols-3 gap-3">
            <div>
              <label className="text-xs font-medium text-slate-600 mb-1 block">Orden *</label>
              <input type="number" min="1" required value={form.sequence_order}
                onChange={e => set('sequence_order', Number(e.target.value))}
                className="w-full rounded-lg border border-slate-200 px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-ring" />
            </div>
            <div>
              <label className="text-xs font-medium text-slate-600 mb-1 block">Rol *</label>
              <select required value={form.role} onChange={e => set('role', e.target.value)}
                className="w-full rounded-lg border border-slate-200 px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-ring">
                {Object.entries(ROLE_CONFIG).map(([k, v]) => (
                  <option key={k} value={k}>{v.label}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="text-xs font-medium text-slate-600 mb-1 block">Nombre *</label>
              <input required value={form.actor_name} onChange={e => set('actor_name', e.target.value)}
                placeholder="Nombre de la empresa"
                className="w-full rounded-lg border border-slate-200 px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-ring" />
            </div>
          </div>
          <div className="grid grid-cols-3 gap-3">
            <div>
              <label className="text-xs font-medium text-slate-600 mb-1 block">Pais</label>
              <input value={form.actor_country ?? ''} onChange={e => set('actor_country', e.target.value)}
                placeholder="CO"
                className="w-full rounded-lg border border-slate-200 px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-ring" />
            </div>
            <div>
              <label className="text-xs font-medium text-slate-600 mb-1 block">NIT / Tax ID</label>
              <input value={form.actor_tax_id ?? ''} onChange={e => set('actor_tax_id', e.target.value)}
                className="w-full rounded-lg border border-slate-200 px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-ring" />
            </div>
            <div>
              <label className="text-xs font-medium text-slate-600 mb-1 block">EORI (si UE)</label>
              <input value={form.actor_eori ?? ''} onChange={e => set('actor_eori', e.target.value)}
                className="w-full rounded-lg border border-slate-200 px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-ring" />
            </div>
          </div>
          <div className="grid grid-cols-3 gap-3">
            <div>
              <label className="text-xs font-medium text-slate-600 mb-1 block">Fecha handoff</label>
              <input type="date" value={form.handoff_date ?? ''} onChange={e => set('handoff_date', e.target.value)}
                className="w-full rounded-lg border border-slate-200 px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-ring" />
            </div>
            <div>
              <label className="text-xs font-medium text-slate-600 mb-1 block">Cantidad (kg)</label>
              <input type="number" step="0.01" value={form.quantity_kg ?? ''} onChange={e => set('quantity_kg', e.target.value ? Number(e.target.value) : undefined)}
                className="w-full rounded-lg border border-slate-200 px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-ring" />
            </div>
            <div>
              <label className="text-xs font-medium text-slate-600 mb-1 block">Direccion</label>
              <input value={form.actor_address ?? ''} onChange={e => set('actor_address', e.target.value)}
                className="w-full rounded-lg border border-slate-200 px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-ring" />
            </div>
          </div>
          <div className="flex justify-end gap-2">
            <button type="button" onClick={() => setShowForm(false)} className="rounded-lg px-3 py-1.5 text-xs text-slate-600 hover:bg-slate-100">Cancelar</button>
            <button type="submit" disabled={addNode.isPending}
              className="rounded-lg bg-primary px-4 py-1.5 text-xs font-semibold text-white hover:bg-primary/90 disabled:opacity-50">
              {addNode.isPending ? 'Agregando...' : 'Agregar'}
            </button>
          </div>
        </form>
      )}

      {/* Supply chain timeline */}
      {nodes.length === 0 ? (
        <div className="rounded-xl border-2 border-dashed border-slate-200 p-8 text-center">
          <Truck className="h-8 w-8 text-slate-200 mx-auto mb-2" />
          <p className="text-sm font-medium text-slate-600 mb-1">Sin actores en la cadena</p>
          <p className="text-xs text-slate-400">Agrega productores, recolectores, exportadores e importadores.</p>
        </div>
      ) : (
        <div className="relative">
          {nodes.map((node, i) => {
            const cfg = ROLE_CONFIG[node.role] ?? { label: node.role, icon: User, color: 'bg-slate-50 text-slate-600 border-slate-200' }
            const Icon = cfg.icon
            const vBadge = VERIFICATION_BADGE[node.verification_status] ?? VERIFICATION_BADGE.unverified

            return (
              <div key={node.id}>
                <div className="flex items-start gap-3 rounded-xl border border-slate-100 bg-white px-4 py-3">
                  {/* Sequence number */}
                  <div className="flex h-8 w-8 items-center justify-center rounded-full bg-slate-100 text-xs font-bold text-slate-500 shrink-0 mt-0.5">
                    {node.sequence_order}
                  </div>

                  {/* Role icon */}
                  <div className={cn('flex h-8 w-8 items-center justify-center rounded-lg shrink-0 mt-0.5 border', cfg.color)}>
                    <Icon className="h-4 w-4" />
                  </div>

                  {/* Content */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <p className="text-sm font-semibold text-slate-900">{node.actor_name}</p>
                      <span className={cn('px-2 py-0.5 rounded-full text-[10px] font-semibold border', cfg.color)}>
                        {cfg.label}
                      </span>
                      <span className={cn('px-1.5 py-0.5 rounded-full text-[10px] font-medium border', vBadge.color)}>
                        {vBadge.label}
                      </span>
                    </div>
                    <div className="flex items-center gap-3 mt-0.5 text-xs text-slate-500">
                      {node.actor_country && <span>{node.actor_country}</span>}
                      {node.actor_tax_id && <span>NIT: {node.actor_tax_id}</span>}
                      {node.actor_eori && <span>EORI: {node.actor_eori}</span>}
                      {node.handoff_date && <span>{new Date(node.handoff_date).toLocaleDateString('es-CO')}</span>}
                      {node.quantity_kg != null && <span>{Number(node.quantity_kg).toLocaleString('es-CO')} kg</span>}
                    </div>
                    {node.actor_address && <p className="text-xs text-slate-400 mt-0.5">{node.actor_address}</p>}
                    {node.notes && <p className="text-xs text-slate-400 italic mt-0.5">{node.notes}</p>}
                  </div>

                  {/* Actions */}
                  <button onClick={() => handleDelete(node.id)} disabled={deleteNode.isPending}
                    className="rounded-lg p-1.5 text-slate-400 hover:text-red-500 hover:bg-red-50 transition-colors disabled:opacity-50 shrink-0">
                    <Trash2 className="h-3.5 w-3.5" />
                  </button>
                </div>

                {/* Arrow connector */}
                {i < nodes.length - 1 && (
                  <div className="flex justify-center py-1">
                    <ArrowDown className="h-4 w-4 text-slate-300" />
                  </div>
                )}
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
