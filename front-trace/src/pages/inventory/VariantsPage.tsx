import { useState } from 'react'
import { Plus, Trash2, Palette } from 'lucide-react'
import {
  useVariantAttributes, useCreateVariantAttribute,
  useDeleteVariantAttribute, useAddVariantOption,
} from '@/hooks/useInventory'

function AttributeSection() {
  const { data: attrs = [], isLoading } = useVariantAttributes()
  const createAttr = useCreateVariantAttribute()

  const deleteAttr = useDeleteVariantAttribute()
  const addOption = useAddVariantOption()
  const [showAdd, setShowAdd] = useState(false)
  const [newName, setNewName] = useState('')
  const [addingOptionTo, setAddingOptionTo] = useState<string | null>(null)
  const [newOptionValue, setNewOptionValue] = useState('')

  async function handleCreateAttr(e: React.FormEvent) {
    e.preventDefault()
    const slug = newName.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '')
    await createAttr.mutateAsync({ name: newName, slug })
    setNewName('')
    setShowAdd(false)
  }

  async function handleAddOption(attrId: string) {
    if (!newOptionValue.trim()) return
    await addOption.mutateAsync({ attrId, data: { value: newOptionValue.trim() } })
    setNewOptionValue('')
    setAddingOptionTo(null)
  }

  if (isLoading) return <div className="flex justify-center py-10"><div className="animate-spin rounded-full h-5 w-5 border-b-2 border-primary" /></div>

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-bold text-slate-900">Atributos de Variante</h2>
        <button onClick={() => setShowAdd(true)} className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold text-primary bg-primary/10 hover:bg-primary/15 rounded-lg"><Plus className="h-3.5 w-3.5" /> Atributo</button>
      </div>

      {showAdd && (
        <form onSubmit={handleCreateAttr} className="flex gap-2 items-center">
          <input value={newName} onChange={e => setNewName(e.target.value)} placeholder="Ej: Talla, Color..." required className="flex-1 px-3 py-2 text-sm border border-slate-200 rounded-xl focus:ring-2 focus:ring-ring outline-none" />
          <button type="submit" disabled={createAttr.isPending} className="px-3 py-2 text-xs font-semibold text-white bg-primary rounded-xl">Crear</button>
          <button type="button" onClick={() => setShowAdd(false)} className="text-xs text-slate-400">Cancelar</button>
        </form>
      )}

      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {attrs.map(attr => (
          <div key={attr.id} className="bg-white rounded-xl border border-slate-200/60 shadow-sm p-4 space-y-3">
            <div className="flex items-center justify-between">
              <h3 className="font-bold text-slate-900">{attr.name}</h3>
              <button onClick={() => { if (confirm('Eliminar atributo?')) deleteAttr.mutate(attr.id) }} className="p-1 text-slate-400 hover:text-red-500"><Trash2 className="h-3.5 w-3.5" /></button>
            </div>
            <div className="flex flex-wrap gap-1.5">
              {attr.options.map(opt => (
                <span key={opt.id} className="inline-flex items-center gap-1.5 px-2.5 py-1 bg-slate-100 rounded-lg text-xs font-medium text-slate-700">
                  {opt.color_hex && <span className="h-3 w-3 rounded-full shrink-0" style={{ backgroundColor: opt.color_hex }} />}
                  {opt.value}
                </span>
              ))}
            </div>
            {addingOptionTo === attr.id ? (
              <div className="flex gap-2">
                <input value={newOptionValue} onChange={e => setNewOptionValue(e.target.value)} placeholder="Valor..." className="flex-1 px-2 py-1 text-xs border border-slate-200 rounded-lg" onKeyDown={e => e.key === 'Enter' && handleAddOption(attr.id)} />
                <button onClick={() => handleAddOption(attr.id)} className="text-xs text-primary font-semibold">OK</button>
                <button onClick={() => setAddingOptionTo(null)} className="text-xs text-slate-400">X</button>
              </div>
            ) : (
              <button onClick={() => { setAddingOptionTo(attr.id); setNewOptionValue('') }} className="text-xs text-primary hover:text-primary font-medium">+ Opcion</button>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}

export function VariantsPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-900 flex items-center gap-2"><Palette className="h-6 w-6 text-primary" /> Atributos de Variante</h1>
        <p className="text-sm text-slate-500 mt-1">Define atributos globales (Talla, Color, etc). Las variantes se crean dentro de cada producto.</p>
      </div>
      <AttributeSection />
    </div>
  )
}
