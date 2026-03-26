import { useState } from 'react'
import { Shield, Plus, Trash2, ToggleLeft, ToggleRight, Zap } from 'lucide-react'
import { useAnchorRules, useCreateAnchorRule, useUpdateAnchorRule, useDeleteAnchorRule, useSeedAnchorRules } from '@/hooks/useLogistics'
import type { AnchorRuleCreate } from '@/types/logistics'
import { useToast } from '@/store/toast'

const ENTITY_TYPES = [
  { value: 'purchase_order', label: 'Ordenes de Compra' },
  { value: 'sales_order', label: 'Pedidos de Venta' },
  { value: 'batch', label: 'Lotes' },
  { value: 'movement', label: 'Movimientos' },
]

const TRIGGER_EVENTS: Record<string, { value: string; label: string }[]> = {
  purchase_order: [{ value: 'received', label: 'Recibida' }, { value: 'confirmed', label: 'Confirmada' }, { value: 'sent', label: 'Enviada' }],
  sales_order: [{ value: 'delivered', label: 'Entregada' }, { value: 'shipped', label: 'Enviada' }, { value: 'confirmed', label: 'Confirmada' }],
  batch: [{ value: 'created', label: 'Creado' }],
  movement: [{ value: 'created', label: 'Creado' }, { value: 'transferred', label: 'Transferido' }],
}

export default function AnchorRulesPage() {
  const { data: rules, isLoading } = useAnchorRules()
  const createMut = useCreateAnchorRule()
  const updateMut = useUpdateAnchorRule()
  const deleteMut = useDeleteAnchorRule()
  const seedMut = useSeedAnchorRules()
  const toast = useToast()
  const [showCreate, setShowCreate] = useState(false)
  const [form, setForm] = useState<Partial<AnchorRuleCreate>>({
    entity_type: 'purchase_order',
    trigger_event: 'received',
    name: '',
    conditions: {},
    actions: { anchor: true },
    priority: 0,
  })
  const [condMinValue, setCondMinValue] = useState('')

  const handleCreate = async () => {
    if (!form.name) return
    const conditions: Record<string, unknown> = {}
    if (condMinValue) conditions.min_value = Number(condMinValue)
    if (!condMinValue) conditions.always = true
    try {
      await createMut.mutateAsync({ ...form, conditions } as AnchorRuleCreate)
      toast.success('Regla creada')
      setShowCreate(false)
      setForm({ entity_type: 'purchase_order', trigger_event: 'received', name: '', conditions: {}, actions: { anchor: true }, priority: 0 })
      setCondMinValue('')
    } catch (e: any) {
      toast.error(e.message)
    }
  }

  const toggleActive = async (id: string, currentActive: boolean) => {
    try {
      await updateMut.mutateAsync({ id, data: { is_active: !currentActive } })
      toast.success(currentActive ? 'Regla desactivada' : 'Regla activada')
    } catch (e: any) {
      toast.error(e.message)
    }
  }

  const handleDelete = async (id: string) => {
    try {
      await deleteMut.mutateAsync(id)
      toast.success('Regla eliminada')
    } catch (e: any) {
      toast.error(e.message)
    }
  }

  const handleSeed = async () => {
    try {
      const created = await seedMut.mutateAsync()
      toast.success(`${created.length} reglas por defecto creadas`)
    } catch (e: any) {
      toast.error(e.message)
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Reglas de Blockchain</h1>
          <p className="text-sm text-gray-500 mt-1">Configure que eventos se anclan automaticamente en Solana</p>
        </div>
        <div className="flex gap-2">
          <button onClick={handleSeed} disabled={seedMut.isPending} className="inline-flex items-center gap-2 px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200">
            <Zap className="h-4 w-4" /> Reglas por Defecto
          </button>
          <button onClick={() => setShowCreate(true)} className="inline-flex items-center gap-2 px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700">
            <Plus className="h-4 w-4" /> Nueva Regla
          </button>
        </div>
      </div>

      {/* Info */}
      <div className="bg-indigo-50 border border-indigo-200 rounded-xl p-4">
        <div className="flex items-start gap-3">
          <Shield className="h-5 w-5 text-indigo-600 mt-0.5" />
          <div>
            <p className="text-sm font-medium text-indigo-900">Como funcionan las reglas</p>
            <p className="text-sm text-indigo-700 mt-1">
              Cada vez que ocurre un evento (recepcion de OC, entrega de pedido, etc), el sistema evalua las reglas en orden de prioridad.
              La primera regla que coincida determina si el evento se ancla en blockchain. Si no hay reglas, todo se ancla por defecto.
            </p>
          </div>
        </div>
      </div>

      {/* Rules list */}
      {isLoading ? (
        <div className="text-center py-12 text-gray-500">Cargando...</div>
      ) : !rules?.length ? (
        <div className="text-center py-12">
          <Shield className="h-12 w-12 text-gray-300 mx-auto mb-3" />
          <p className="text-gray-500">No hay reglas configuradas</p>
          <p className="text-sm text-gray-400 mt-1">Sin reglas, todos los eventos se anclan automaticamente</p>
          <button onClick={handleSeed} className="mt-4 px-4 py-2 bg-indigo-600 text-white rounded-lg text-sm">Crear reglas por defecto</button>
        </div>
      ) : (
        <div className="space-y-3">
          {rules.map(rule => (
            <div key={rule.id} className={`bg-white rounded-xl border p-4 ${rule.is_active ? '' : 'opacity-50'}`}>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <button onClick={() => toggleActive(rule.id, rule.is_active)} className="text-gray-400 hover:text-indigo-600">
                    {rule.is_active ? <ToggleRight className="h-6 w-6 text-indigo-600" /> : <ToggleLeft className="h-6 w-6" />}
                  </button>
                  <div>
                    <p className="font-medium text-gray-900">{rule.name}</p>
                    <div className="flex items-center gap-2 mt-1">
                      <span className="text-xs bg-blue-100 text-blue-700 px-2 py-0.5 rounded">{ENTITY_TYPES.find(e => e.value === rule.entity_type)?.label || rule.entity_type}</span>
                      <span className="text-xs text-gray-400">cuando</span>
                      <span className="text-xs bg-purple-100 text-purple-700 px-2 py-0.5 rounded">{rule.trigger_event}</span>
                      {rule.conditions && Object.keys(rule.conditions).length > 0 && (
                        <>
                          <span className="text-xs text-gray-400">si</span>
                          <span className="text-xs bg-amber-100 text-amber-700 px-2 py-0.5 rounded font-mono">
                            {(rule.conditions as any).always ? 'siempre' : JSON.stringify(rule.conditions)}
                          </span>
                        </>
                      )}
                    </div>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-xs text-gray-400">Prioridad: {rule.priority}</span>
                  <button onClick={() => handleDelete(rule.id)} className="text-gray-400 hover:text-red-500">
                    <Trash2 className="h-4 w-4" />
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Create Modal */}
      {showCreate && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50" onClick={() => setShowCreate(false)}>
          <div className="bg-white rounded-xl p-6 w-full max-w-lg" onClick={e => e.stopPropagation()}>
            <h2 className="text-lg font-semibold mb-4">Nueva Regla de Blockchain</h2>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Nombre *</label>
                <input value={form.name || ''} onChange={e => setForm({ ...form, name: e.target.value })} className="w-full border rounded-lg px-3 py-2 text-sm" placeholder="Anclar OCs mayores a $1,000 USD" />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Entidad</label>
                  <select value={form.entity_type} onChange={e => setForm({ ...form, entity_type: e.target.value, trigger_event: TRIGGER_EVENTS[e.target.value]?.[0]?.value })} className="w-full border rounded-lg px-3 py-2 text-sm">
                    {ENTITY_TYPES.map(et => <option key={et.value} value={et.value}>{et.label}</option>)}
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Evento</label>
                  <select value={form.trigger_event} onChange={e => setForm({ ...form, trigger_event: e.target.value })} className="w-full border rounded-lg px-3 py-2 text-sm">
                    {(TRIGGER_EVENTS[form.entity_type || 'purchase_order'] || []).map(te => <option key={te.value} value={te.value}>{te.label}</option>)}
                  </select>
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Valor minimo (dejar vacio = siempre)</label>
                <input type="number" value={condMinValue} onChange={e => setCondMinValue(e.target.value)} className="w-full border rounded-lg px-3 py-2 text-sm" placeholder="1000" />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Prioridad (mayor = primero)</label>
                <input type="number" value={form.priority || 0} onChange={e => setForm({ ...form, priority: Number(e.target.value) })} className="w-full border rounded-lg px-3 py-2 text-sm" />
              </div>
            </div>
            <div className="flex justify-end gap-3 mt-6">
              <button onClick={() => setShowCreate(false)} className="px-4 py-2 text-sm text-gray-600 hover:bg-gray-100 rounded-lg">Cancelar</button>
              <button onClick={handleCreate} disabled={createMut.isPending} className="px-4 py-2 text-sm bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-50">
                {createMut.isPending ? 'Creando...' : 'Crear Regla'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
