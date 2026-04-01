import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Ruler, Plus, RefreshCw } from 'lucide-react'
import { inventoryUoMApi } from '@/lib/inventory-api'
import type { UnitOfMeasure, UoMConversion } from '@/types/inventory'

export function UoMPage() {
  const qc = useQueryClient()
  const [showCreate, setShowCreate] = useState(false)
  const [showConvCreate, setShowConvCreate] = useState(false)
  const [form, setForm] = useState({ name: '', symbol: '', category: 'unit', is_base: false })
  const [convForm, setConvForm] = useState({ from_uom_id: '', to_uom_id: '', factor: '' })

  const { data: uoms = [], isLoading } = useQuery({
    queryKey: ['inventory', 'uom'],
    queryFn: () => inventoryUoMApi.list(),
  })
  const { data: conversions = [] } = useQuery({
    queryKey: ['inventory', 'uom', 'conversions'],
    queryFn: () => inventoryUoMApi.listConversions(),
  })

  const initMut = useMutation({
    mutationFn: () => inventoryUoMApi.initialize(),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['inventory', 'uom'] }) },
  })
  const createMut = useMutation({
    mutationFn: (data: typeof form) => inventoryUoMApi.create(data),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['inventory', 'uom'] }); setShowCreate(false) },
  })
  const createConvMut = useMutation({
    mutationFn: (data: { from_uom_id: string; to_uom_id: string; factor: number }) => inventoryUoMApi.createConversion(data),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['inventory', 'uom', 'conversions'] }); setShowConvCreate(false) },
  })

  const categories = ['weight', 'volume', 'length', 'unit', 'custom']
  const catLabels: Record<string, string> = { weight: 'Peso', volume: 'Volumen', length: 'Longitud', unit: 'Unidad', custom: 'Personalizado' }
  const grouped = categories.reduce((acc, cat) => {
    acc[cat] = (uoms as UnitOfMeasure[]).filter(u => u.category === cat)
    return acc
  }, {} as Record<string, UnitOfMeasure[]>)

  const uomMap = Object.fromEntries((uoms as UnitOfMeasure[]).map(u => [u.id, u]))

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Ruler className="h-6 w-6 text-foreground" />
          <h1 className="text-2xl font-bold">Unidades de Medida</h1>
        </div>
        <div className="flex gap-2">
          <button onClick={() => initMut.mutate()} disabled={initMut.isPending} className="flex items-center gap-2 px-4 py-2 text-[13px] font-medium bg-secondary text-foreground rounded-xl hover:bg-gray-200 transition-colors">
            <RefreshCw className={`h-4 w-4 ${initMut.isPending ? 'animate-spin' : ''}`} />Inicializar Colombia
          </button>
          <button onClick={() => setShowCreate(true)} className="flex items-center gap-2 px-4 py-2 text-[13px] font-medium bg-gray-900 text-white rounded-xl hover:bg-gray-800 transition-colors">
            <Plus className="h-4 w-4" />Nueva UoM
          </button>
        </div>
      </div>

      {isLoading ? <div className="text-center py-10 text-muted-foreground">Cargando...</div> : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {categories.map(cat => grouped[cat]?.length > 0 && (
            <div key={cat} className="bg-card rounded-xl border border-border p-5">
              <h3 className="font-semibold text-sm text-muted-foreground mb-3">{catLabels[cat]}</h3>
              <div className="space-y-1">
                {grouped[cat].map(u => (
                  <div key={u.id} className="flex items-center justify-between py-1.5 px-2 rounded hover:bg-muted">
                    <span>{u.name} <span className="text-muted-foreground text-xs">({u.symbol})</span></span>
                    {u.is_base && <span className="text-xs bg-blue-100 text-blue-700 px-1.5 py-0.5 rounded">base</span>}
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}

      <div className="bg-card rounded-xl border border-border p-5">
        <div className="flex items-center justify-between mb-4">
          <h3 className="font-semibold">Conversiones</h3>
          <button onClick={() => setShowConvCreate(true)} className="flex items-center gap-1 px-3 py-1.5 text-sm border rounded hover:bg-muted"><Plus className="h-4 w-4" />Nueva conversión</button>
        </div>
        <table className="w-full text-sm">
          <thead><tr className="bg-muted"><th className="p-2 text-left">De</th><th className="p-2 text-left">A</th><th className="p-2 text-right">Factor</th></tr></thead>
          <tbody>
            {(conversions as UoMConversion[]).map(c => (
              <tr key={c.id} className="border-b">
                <td className="p-2">{uomMap[c.from_uom_id]?.name ?? c.from_uom_id} ({uomMap[c.from_uom_id]?.symbol})</td>
                <td className="p-2">{uomMap[c.to_uom_id]?.name ?? c.to_uom_id} ({uomMap[c.to_uom_id]?.symbol})</td>
                <td className="p-2 text-right font-mono">{c.factor}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {showCreate && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
          <div className="bg-card rounded-2xl p-6 w-96 shadow-2xl">
            <h3 className="font-semibold mb-4">Nueva Unidad de Medida</h3>
            <div className="space-y-3">
              <input placeholder="Nombre (ej: Kilogramo)" value={form.name} onChange={e => setForm({...form, name: e.target.value})} className="w-full border rounded px-3 py-2 text-sm" />
              <input placeholder="Símbolo (ej: kg)" value={form.symbol} onChange={e => setForm({...form, symbol: e.target.value})} className="w-full border rounded px-3 py-2 text-sm" />
              <select value={form.category} onChange={e => setForm({...form, category: e.target.value})} className="w-full border rounded px-3 py-2 text-sm">
                {categories.map(c => <option key={c} value={c}>{catLabels[c]}</option>)}
              </select>
              <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={form.is_base} onChange={e => setForm({...form, is_base: e.target.checked})} />Es UoM base de esta categoría</label>
            </div>
            <div className="flex justify-end gap-2 mt-4">
              <button onClick={() => setShowCreate(false)} className="px-3 py-1.5 text-sm border rounded">Cancelar</button>
              <button onClick={() => createMut.mutate(form)} disabled={createMut.isPending} className="px-3 py-1.5 text-sm bg-gray-900 text-white rounded">Crear</button>
            </div>
          </div>
        </div>
      )}

      {showConvCreate && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
          <div className="bg-card rounded-2xl p-6 w-96 shadow-2xl">
            <h3 className="font-semibold mb-4">Nueva Conversión</h3>
            <div className="space-y-3">
              <select value={convForm.from_uom_id} onChange={e => setConvForm({...convForm, from_uom_id: e.target.value})} className="w-full border rounded px-3 py-2 text-sm">
                <option value="">De...</option>
                {(uoms as UnitOfMeasure[]).map(u => <option key={u.id} value={u.id}>{u.name} ({u.symbol})</option>)}
              </select>
              <select value={convForm.to_uom_id} onChange={e => setConvForm({...convForm, to_uom_id: e.target.value})} className="w-full border rounded px-3 py-2 text-sm">
                <option value="">A...</option>
                {(uoms as UnitOfMeasure[]).map(u => <option key={u.id} value={u.id}>{u.name} ({u.symbol})</option>)}
              </select>
              <input type="number" placeholder="Factor (ej: 1000)" value={convForm.factor} onChange={e => setConvForm({...convForm, factor: e.target.value})} className="w-full border rounded px-3 py-2 text-sm" />
            </div>
            <div className="flex justify-end gap-2 mt-4">
              <button onClick={() => setShowConvCreate(false)} className="px-3 py-1.5 text-sm border rounded">Cancelar</button>
              <button onClick={() => createConvMut.mutate({ from_uom_id: convForm.from_uom_id, to_uom_id: convForm.to_uom_id, factor: parseFloat(convForm.factor) })} disabled={createConvMut.isPending} className="px-3 py-1.5 text-sm bg-gray-900 text-white rounded">Crear</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
