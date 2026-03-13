import { useState } from 'react'
import { Plus, Pencil, Trash2, Palette, Layers } from 'lucide-react'
import { cn } from '@/lib/utils'
import {
  useVariantAttributes, useCreateVariantAttribute, useUpdateVariantAttribute,
  useDeleteVariantAttribute, useAddVariantOption,
  useProductVariants, useCreateVariant, useDeleteVariant, useUpdateVariant, useProducts,
} from '@/hooks/useInventory'
import type { VariantAttribute, ProductVariant } from '@/types/inventory'

function AttributeSection() {
  const { data: attrs = [], isLoading } = useVariantAttributes()
  const createAttr = useCreateVariantAttribute()
  const updateAttr = useUpdateVariantAttribute()
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

  if (isLoading) return <div className="flex justify-center py-10"><div className="animate-spin rounded-full h-5 w-5 border-b-2 border-indigo-600" /></div>

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-bold text-slate-900">Atributos de Variante</h2>
        <button onClick={() => setShowAdd(true)} className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold text-indigo-600 bg-indigo-50 hover:bg-indigo-100 rounded-lg"><Plus className="h-3.5 w-3.5" /> Atributo</button>
      </div>

      {showAdd && (
        <form onSubmit={handleCreateAttr} className="flex gap-2 items-center">
          <input value={newName} onChange={e => setNewName(e.target.value)} placeholder="Ej: Talla, Color..." required className="flex-1 px-3 py-2 text-sm border border-slate-200 rounded-xl focus:ring-2 focus:ring-indigo-400 outline-none" />
          <button type="submit" disabled={createAttr.isPending} className="px-3 py-2 text-xs font-semibold text-white bg-indigo-600 rounded-xl">Crear</button>
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
                <button onClick={() => handleAddOption(attr.id)} className="text-xs text-indigo-600 font-semibold">OK</button>
                <button onClick={() => setAddingOptionTo(null)} className="text-xs text-slate-400">X</button>
              </div>
            ) : (
              <button onClick={() => { setAddingOptionTo(attr.id); setNewOptionValue('') }} className="text-xs text-indigo-500 hover:text-indigo-700 font-medium">+ Opcion</button>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}

function CreateVariantForm({ onCreated }: { onCreated: () => void }) {
  const { data: productsData } = useProducts()
  const { data: attrs = [] } = useVariantAttributes()
  const createVariant = useCreateVariant()
  const [error, setError] = useState('')
  const [form, setForm] = useState({
    parent_id: '', sku: '', name: '', cost_price: '', sale_price: '',
  })
  const [optionValues, setOptionValues] = useState<Record<string, string>>({})

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError('')
    const filtered = Object.fromEntries(Object.entries(optionValues).filter(([, v]) => v))
    try {
      await createVariant.mutateAsync({
        parent_id: form.parent_id,
        sku: form.sku,
        name: form.name,
        cost_price: parseFloat(form.cost_price) || 0,
        sale_price: parseFloat(form.sale_price) || 0,
        option_values: filtered,
      })
      setForm({ parent_id: '', sku: '', name: '', cost_price: '', sale_price: '' })
      setOptionValues({})
      onCreated()
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Error al crear variante')
    }
  }

  const products = productsData?.items ?? []

  return (
    <form onSubmit={handleSubmit} className="bg-white rounded-2xl border border-slate-200/60 shadow-sm p-5 space-y-4">
      <h3 className="font-bold text-slate-900">Nueva Variante</h3>
      <div className="grid grid-cols-2 gap-3">
        <select required value={form.parent_id} onChange={e => setForm(f => ({ ...f, parent_id: e.target.value }))}
          className="col-span-2 rounded-xl border border-slate-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400">
          <option value="">Producto padre *</option>
          {products.map(p => <option key={p.id} value={p.id}>{p.name} ({p.sku})</option>)}
        </select>
        <input required value={form.sku} onChange={e => setForm(f => ({ ...f, sku: e.target.value }))}
          placeholder="SKU *" className="rounded-xl border border-slate-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400" />
        <input required value={form.name} onChange={e => setForm(f => ({ ...f, name: e.target.value }))}
          placeholder="Nombre *" className="rounded-xl border border-slate-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400" />
        <input type="number" step="0.01" value={form.cost_price} onChange={e => setForm(f => ({ ...f, cost_price: e.target.value }))}
          placeholder="Costo" className="rounded-xl border border-slate-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400" />
        <input type="number" step="0.01" value={form.sale_price} onChange={e => setForm(f => ({ ...f, sale_price: e.target.value }))}
          placeholder="Precio venta" className="rounded-xl border border-slate-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400" />
      </div>
      {attrs.length > 0 && (
        <div className="space-y-2">
          <p className="text-xs font-semibold text-slate-500 uppercase">Opciones</p>
          <div className="grid grid-cols-2 gap-3">
            {attrs.map(attr => (
              <div key={attr.id}>
                <label className="text-xs font-medium text-slate-600 mb-1 block">{attr.name}</label>
                <select value={optionValues[attr.name] ?? ''} onChange={e => setOptionValues(ov => ({ ...ov, [attr.name]: e.target.value }))}
                  className="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400">
                  <option value="">— ninguno —</option>
                  {attr.options.map(opt => <option key={opt.id} value={opt.value}>{opt.value}</option>)}
                </select>
              </div>
            ))}
          </div>
        </div>
      )}
      {error && <p className="text-xs text-red-600 bg-red-50 px-3 py-2 rounded-xl">{error}</p>}
      <button type="submit" disabled={createVariant.isPending}
        className="w-full rounded-xl bg-indigo-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-indigo-700 disabled:opacity-50">
        {createVariant.isPending ? 'Creando…' : 'Crear Variante'}
      </button>
    </form>
  )
}

function VariantsList() {
  const { data, isLoading } = useProductVariants({ limit: 100 })
  const deleteVar = useDeleteVariant()
  const [showCreate, setShowCreate] = useState(false)
  const [editingVariant, setEditingVariant] = useState<ProductVariant | null>(null)
  const variants = data?.items ?? []

  if (isLoading) return <div className="flex justify-center py-10"><div className="animate-spin rounded-full h-5 w-5 border-b-2 border-indigo-600" /></div>

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-bold text-slate-900">Variantes de Producto</h2>
        <button onClick={() => setShowCreate(s => !s)} className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold text-indigo-600 bg-indigo-50 hover:bg-indigo-100 rounded-lg">
          <Plus className="h-3.5 w-3.5" /> {showCreate ? 'Ocultar' : 'Nueva Variante'}
        </button>
      </div>

      {showCreate && <CreateVariantForm onCreated={() => setShowCreate(false)} />}
      <div className="bg-white rounded-2xl border border-slate-200/60 shadow-sm overflow-hidden">
        <table className="w-full text-sm">
          <thead><tr className="bg-slate-50 text-left text-xs font-semibold text-slate-500 uppercase">
            <th className="px-6 py-3">SKU</th>
            <th className="px-6 py-3">Nombre</th>
            <th className="px-6 py-3">Opciones</th>
            <th className="px-6 py-3 text-right">Costo</th>
            <th className="px-6 py-3 text-right">Venta</th>
            <th className="px-6 py-3 text-right">Acciones</th>
          </tr></thead>
          <tbody className="divide-y divide-slate-100">
            {variants.map(v => (
              <tr key={v.id} className="hover:bg-slate-50/60">
                <td className="px-6 py-3 font-mono text-xs">{v.sku}</td>
                <td className="px-6 py-3 font-semibold text-slate-900">{v.name}</td>
                <td className="px-6 py-3">
                  <div className="flex flex-wrap gap-1">
                    {Object.entries(v.option_values).map(([k, val]) => (
                      <span key={k} className="px-2 py-0.5 bg-slate-100 rounded text-[10px] font-medium">{k}: {val}</span>
                    ))}
                  </div>
                </td>
                <td className="px-6 py-3 text-right font-mono">${v.cost_price}</td>
                <td className="px-6 py-3 text-right font-mono">${v.sale_price}</td>
                <td className="px-6 py-3 text-right">
                  <button onClick={() => setEditingVariant(v)} className="p-1.5 text-slate-400 hover:text-indigo-600 rounded-lg hover:bg-indigo-50"><Pencil className="h-4 w-4" /></button>
                  <button onClick={() => { if (confirm('Eliminar?')) deleteVar.mutate(v.id) }} className="p-1.5 text-slate-400 hover:text-red-600 rounded-lg hover:bg-red-50"><Trash2 className="h-4 w-4" /></button>
                </td>
              </tr>
            ))}
            {variants.length === 0 && <tr><td colSpan={6} className="px-6 py-12 text-center text-slate-400">Sin variantes creadas</td></tr>}
          </tbody>
        </table>
      </div>
      {editingVariant && <EditVariantModal variant={editingVariant} onClose={() => setEditingVariant(null)} />}
    </div>
  )
}

function EditVariantModal({ variant, onClose }: { variant: ProductVariant; onClose: () => void }) {
  const updateVar = useUpdateVariant()
  const [form, setForm] = useState({
    sku: variant.sku,
    name: variant.name,
    cost_price: String(variant.cost_price),
    sale_price: String(variant.sale_price),
  })

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    await updateVar.mutateAsync({
      id: variant.id,
      data: {
        sku: form.sku,
        name: form.name,
        cost_price: parseFloat(form.cost_price) || 0,
        sale_price: parseFloat(form.sale_price) || 0,
      },
    })
    onClose()
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 backdrop-blur-sm">
      <div className="w-full max-w-md bg-white rounded-3xl shadow-2xl p-6">
        <h2 className="text-lg font-bold text-slate-900 mb-4">Editar Variante</h2>
        <form onSubmit={handleSubmit} className="space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <input required value={form.sku} onChange={e => setForm(f => ({ ...f, sku: e.target.value }))}
              placeholder="SKU *" className="rounded-xl border border-slate-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400" />
            <input required value={form.name} onChange={e => setForm(f => ({ ...f, name: e.target.value }))}
              placeholder="Nombre *" className="rounded-xl border border-slate-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400" />
            <input type="number" step="0.01" value={form.cost_price} onChange={e => setForm(f => ({ ...f, cost_price: e.target.value }))}
              placeholder="Costo" className="rounded-xl border border-slate-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400" />
            <input type="number" step="0.01" value={form.sale_price} onChange={e => setForm(f => ({ ...f, sale_price: e.target.value }))}
              placeholder="Precio venta" className="rounded-xl border border-slate-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400" />
          </div>
          <div className="flex gap-3 pt-2">
            <button type="button" onClick={onClose} className="flex-1 rounded-xl border border-slate-200 px-4 py-2 text-sm text-slate-600 hover:bg-slate-50">Cancelar</button>
            <button type="submit" disabled={updateVar.isPending} className="flex-1 rounded-xl bg-indigo-600 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-700 disabled:opacity-60">
              {updateVar.isPending ? 'Guardando...' : 'Guardar'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

export function VariantsPage() {
  const [tab, setTab] = useState<'attributes' | 'variants'>('attributes')

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-900 flex items-center gap-2"><Palette className="h-6 w-6 text-indigo-500" /> Variantes</h1>
        <p className="text-sm text-slate-500 mt-1">Administra atributos (Talla, Color) y variantes de productos</p>
      </div>

      <div className="flex gap-2 border-b border-slate-200 pb-0">
        <button onClick={() => setTab('attributes')} className={cn('px-4 py-2 text-sm font-semibold border-b-2 transition', tab === 'attributes' ? 'border-indigo-600 text-indigo-700' : 'border-transparent text-slate-500 hover:text-slate-700')}>Atributos</button>
        <button onClick={() => setTab('variants')} className={cn('px-4 py-2 text-sm font-semibold border-b-2 transition', tab === 'variants' ? 'border-indigo-600 text-indigo-700' : 'border-transparent text-slate-500 hover:text-slate-700')}>Variantes</button>
      </div>

      {tab === 'attributes' ? <AttributeSection /> : <VariantsList />}
    </div>
  )
}
