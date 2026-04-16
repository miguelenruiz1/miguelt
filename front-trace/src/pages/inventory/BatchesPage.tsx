import { useState, useEffect } from 'react'
import { useLocation } from 'react-router-dom'
import { Layers, Plus, Pencil, Trash2 } from 'lucide-react'
import { cn } from '@/lib/utils'
import { useFormValidation } from '@/hooks/useFormValidation'
import { useBatches, useCreateBatch, useUpdateBatch, useDeleteBatch, useProducts } from '@/hooks/useInventory'
import { useUserLookup } from '@/hooks/useUserLookup'

export function BatchesPage() {
  const [showCreate, setShowCreate] = useState(false)
  const [filterEntity, setFilterEntity] = useState('')
  const [editingBatch, setEditingBatch] = useState<any>(null)
  const deleteBatch = useDeleteBatch()
  const location = useLocation()
  useEffect(() => { setShowCreate(false) }, [location.key])

  const { data, isLoading } = useBatches({ entity_id: filterEntity || undefined })
  const { data: productsData } = useProducts()
  const { resolve } = useUserLookup(data?.items.map(b => b.created_by) ?? [])
  const productMap = Object.fromEntries((productsData?.items ?? []).map(p => [p.id, p.name]))

  const today = new Date()

  function expiryClass(date: string | null): string {
    if (!date) return ''
    const exp = new Date(date)
    const diff = (exp.getTime() - today.getTime()) / (1000 * 60 * 60 * 24)
    if (diff < 0) return 'text-red-600 bg-red-50'
    if (diff < 30) return 'text-amber-600 bg-amber-50'
    return 'text-emerald-600 bg-emerald-50'
  }

  return (
    <div className="max-w-5xl mx-auto p-6 space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-foreground">Lotes</h1>
        <button onClick={() => setShowCreate(true)}
          className="flex items-center gap-2 rounded-2xl bg-primary px-4 py-2.5 text-sm font-semibold text-white hover:bg-primary/90 ">
          <Plus className="h-4 w-4" /> Nuevo lote
        </button>
      </div>

      <div className="flex gap-3">
        <select value={filterEntity} onChange={e => setFilterEntity(e.target.value)}
          className="rounded-2xl border border-border bg-card px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-ring">
          <option value="">Todos los productos</option>
          {(productsData?.items ?? []).map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
        </select>
      </div>

      <div className="bg-card rounded-2xl border border-border  overflow-hidden">
        {isLoading ? (
          <div className="p-8 text-center text-muted-foreground">Cargando...</div>
        ) : !data?.items?.length ? (
          <div className="p-8 text-center">
            <Layers className="h-10 w-10 text-slate-200 mx-auto mb-3" />
            <p className="text-sm text-muted-foreground">Sin lotes registrados</p>
          </div>
        ) : (<>
          {/* Mobile cards */}
          <div className="space-y-3 p-4 md:hidden">
            {data.items.map(b => (
              <div key={b.id} className="rounded-xl border border-border bg-card p-4 space-y-2">
                <div className="flex items-center justify-between">
                  <span className="font-mono text-xs text-foreground font-semibold">{b.batch_number}</span>
                  <span className={cn('rounded-full px-2 py-0.5 text-xs font-semibold',
                    b.is_active ? 'bg-emerald-50 text-emerald-700' : 'bg-secondary text-muted-foreground')}>
                    {b.is_active ? 'Activo' : 'Inactivo'}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium text-foreground">{productMap[b.entity_id] ?? b.entity_id.slice(0, 8)}</span>
                  <span className="text-sm font-bold text-foreground">{Number(b.quantity).toFixed(2)}</span>
                </div>
                <div className="flex items-center justify-between text-xs text-muted-foreground">
                  <span>Fab: {b.manufacture_date ? new Date(b.manufacture_date).toLocaleDateString('es-CO') : '—'}</span>
                  <span>
                    Exp: {b.expiration_date ? (
                      <span className={cn('rounded-full px-2 py-0.5 font-semibold', expiryClass(b.expiration_date))}>
                        {new Date(b.expiration_date).toLocaleDateString('es-CO')}
                      </span>
                    ) : '—'}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-xs text-muted-foreground">{resolve(b.created_by)}</span>
                  <span className="flex gap-1">
                    <button onClick={() => setEditingBatch(b)} className="p-1 text-muted-foreground hover:text-primary"><Pencil className="h-3.5 w-3.5" /></button>
                    <button onClick={async () => { if (confirm('¿Eliminar lote ' + b.batch_number + '?')) await deleteBatch.mutateAsync(b.id) }}
                      className="p-1 text-muted-foreground hover:text-red-600"><Trash2 className="h-3.5 w-3.5" /></button>
                  </span>
                </div>
              </div>
            ))}
          </div>
          {/* Desktop table */}
          <div className="hidden md:block overflow-x-auto">
          <table className="w-full text-sm min-w-[600px]">
            <thead className="bg-muted border-b border-border">
              <tr>
                {['Lote', 'Producto', 'Cantidad', 'Fabricación', 'Expiración', 'Estado', 'Creado por', 'Acciones'].map(h => (
                  <th key={h} className="px-4 py-3 text-left text-xs font-semibold text-muted-foreground uppercase tracking-wide">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-50">
              {data.items.map(b => (
                <tr key={b.id} className="hover:bg-muted">
                  <td className="px-4 py-3 font-mono text-xs text-foreground font-semibold">{b.batch_number}</td>
                  <td className="px-4 py-3 font-medium text-foreground">{productMap[b.entity_id] ?? b.entity_id.slice(0, 8)}</td>
                  <td className="px-4 py-3 font-bold text-foreground">{Number(b.quantity).toFixed(2)}</td>
                  <td className="px-4 py-3 text-muted-foreground text-xs">
                    {b.manufacture_date ? new Date(b.manufacture_date).toLocaleDateString('es-CO') : '—'}
                  </td>
                  <td className="px-4 py-3">
                    {b.expiration_date ? (
                      <span className={cn('rounded-full px-2 py-0.5 text-xs font-semibold', expiryClass(b.expiration_date))}>
                        {new Date(b.expiration_date).toLocaleDateString('es-CO')}
                      </span>
                    ) : <span className="text-slate-300 text-xs">—</span>}
                  </td>
                  <td className="px-4 py-3">
                    <span className={cn('rounded-full px-2 py-0.5 text-xs font-semibold',
                      b.is_active ? 'bg-emerald-50 text-emerald-700' : 'bg-secondary text-muted-foreground')}>
                      {b.is_active ? 'Activo' : 'Inactivo'}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-muted-foreground text-xs">{resolve(b.created_by)}</td>
                  <td className="px-4 py-3 text-right">
                    <button onClick={() => setEditingBatch(b)} className="p-1 text-muted-foreground hover:text-primary"><Pencil className="h-3.5 w-3.5" /></button>
                    <button onClick={async () => { if (confirm('¿Eliminar lote ' + b.batch_number + '?')) await deleteBatch.mutateAsync(b.id) }}
                      className="p-1 text-muted-foreground hover:text-red-600 ml-1"><Trash2 className="h-3.5 w-3.5" /></button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          </div>
        </>)}
      </div>

      {editingBatch && <EditBatchModal batch={editingBatch} onClose={() => setEditingBatch(null)} />}
      {showCreate && <CreateBatchModal products={productsData?.items ?? []} onClose={() => setShowCreate(false)} />}
    </div>
  )
}

function CreateBatchModal({ products, onClose }: {
  products: Array<{ id: string; name: string }>
  onClose: () => void
}) {
  const create = useCreateBatch()
  const [form, setForm] = useState({
    entity_id: '', batch_number: '', quantity: '', cost: '',
    manufacture_date: '', expiration_date: '', notes: '',
  })

  async function doSubmit() {
    await create.mutateAsync({
      ...form,
      manufacture_date: form.manufacture_date || null,
      expiration_date: form.expiration_date || null,
      cost: form.cost || null,
    })
    onClose()
  }

  const { formRef, handleSubmit: validateAndSubmit } = useFormValidation(doSubmit)

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 backdrop-blur-sm">
      <div className="w-full max-w-md bg-card rounded-3xl shadow-2xl p-6">
        <h2 className="text-lg font-bold text-foreground mb-4">Nuevo Lote</h2>
        <form ref={formRef} onSubmit={validateAndSubmit} noValidate className="space-y-3">
          <select required value={form.entity_id} onChange={e => setForm(f => ({ ...f, entity_id: e.target.value }))}
            className="w-full rounded-xl border border-border px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring">
            <option value="">Producto *</option>
            {products.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
          </select>
          <input required value={form.batch_number} onChange={e => setForm(f => ({ ...f, batch_number: e.target.value }))}
            placeholder="Número de lote *" className="w-full rounded-xl border border-border px-3 py-2 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-ring" />
          <div className="grid grid-cols-2 gap-3">
            <input required type="number" step="0.01" value={form.quantity}
              onChange={e => setForm(f => ({ ...f, quantity: e.target.value }))}
              placeholder="Cantidad *" className="rounded-xl border border-border px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring" />
            <input type="number" step="0.01" value={form.cost}
              onChange={e => setForm(f => ({ ...f, cost: e.target.value }))}
              placeholder="Costo" className="rounded-xl border border-border px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring" />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs text-muted-foreground mb-1 block">Fabricación</label>
              <input type="date" value={form.manufacture_date} onChange={e => setForm(f => ({ ...f, manufacture_date: e.target.value }))}
                className="w-full rounded-xl border border-border px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring" />
            </div>
            <div>
              <label className="text-xs text-muted-foreground mb-1 block">Expiración</label>
              <input type="date" value={form.expiration_date} onChange={e => setForm(f => ({ ...f, expiration_date: e.target.value }))}
                className="w-full rounded-xl border border-border px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring" />
            </div>
          </div>
          <div className="flex gap-3 pt-2">
            <button type="button" onClick={onClose} className="flex-1 rounded-xl border border-border px-4 py-2 text-sm text-muted-foreground hover:bg-muted">Cancelar</button>
            <button type="submit" disabled={create.isPending} className="flex-1 rounded-xl bg-primary px-4 py-2 text-sm font-semibold text-white hover:bg-primary/90 disabled:opacity-60">
              {create.isPending ? 'Guardando...' : 'Crear lote'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

function EditBatchModal({ batch, onClose }: { batch: any; onClose: () => void }) {
  const update = useUpdateBatch()
  const [form, setForm] = useState({
    batch_number: batch.batch_number,
    quantity: String(batch.quantity),
    cost: batch.cost ? String(batch.cost) : '',
    manufacture_date: batch.manufacture_date?.slice(0, 10) ?? '',
    expiration_date: batch.expiration_date?.slice(0, 10) ?? '',
    notes: batch.notes ?? '',
    is_active: batch.is_active,
  })

  async function doSubmit() {
    await update.mutateAsync({
      id: batch.id,
      data: {
        batch_number: form.batch_number,
        quantity: form.quantity,
        cost: form.cost || null,
        manufacture_date: form.manufacture_date || null,
        expiration_date: form.expiration_date || null,
        notes: form.notes || null,
        is_active: form.is_active,
      },
    })
    onClose()
  }

  const { formRef, handleSubmit: validateAndSubmit } = useFormValidation(doSubmit)

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 backdrop-blur-sm">
      <div className="w-full max-w-md bg-card rounded-3xl shadow-2xl p-6">
        <h2 className="text-lg font-bold text-foreground mb-4">Editar Lote</h2>
        <form ref={formRef} onSubmit={validateAndSubmit} noValidate className="space-y-3">
          <input required value={form.batch_number} onChange={e => setForm(f => ({ ...f, batch_number: e.target.value }))}
            placeholder="Número de lote *" className="w-full rounded-xl border border-border px-3 py-2 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-ring" />
          <div className="grid grid-cols-2 gap-3">
            <input required type="number" step="0.01" value={form.quantity}
              onChange={e => setForm(f => ({ ...f, quantity: e.target.value }))}
              placeholder="Cantidad *" className="rounded-xl border border-border px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring" />
            <input type="number" step="0.01" value={form.cost}
              onChange={e => setForm(f => ({ ...f, cost: e.target.value }))}
              placeholder="Costo" className="rounded-xl border border-border px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring" />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs text-muted-foreground mb-1 block">Fabricacion</label>
              <input type="date" value={form.manufacture_date} onChange={e => setForm(f => ({ ...f, manufacture_date: e.target.value }))}
                className="w-full rounded-xl border border-border px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring" />
            </div>
            <div>
              <label className="text-xs text-muted-foreground mb-1 block">Expiracion</label>
              <input type="date" value={form.expiration_date} onChange={e => setForm(f => ({ ...f, expiration_date: e.target.value }))}
                className="w-full rounded-xl border border-border px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring" />
            </div>
          </div>
          <label className="flex items-center gap-2 text-sm text-foreground">
            <input type="checkbox" checked={form.is_active} onChange={e => setForm(f => ({ ...f, is_active: e.target.checked }))}
              className="rounded border-slate-300" /> Activo
          </label>
          <div className="flex gap-3 pt-2">
            <button type="button" onClick={onClose} className="flex-1 rounded-xl border border-border px-4 py-2 text-sm text-muted-foreground hover:bg-muted">Cancelar</button>
            <button type="submit" disabled={update.isPending} className="flex-1 rounded-xl bg-primary px-4 py-2 text-sm font-semibold text-white hover:bg-primary/90 disabled:opacity-60">
              {update.isPending ? 'Guardando...' : 'Guardar'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
