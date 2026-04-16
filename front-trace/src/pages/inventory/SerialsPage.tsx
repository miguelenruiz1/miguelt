import { useState, useEffect } from 'react'
import { useLocation } from 'react-router-dom'
import { Hash, Plus, Trash2 } from 'lucide-react'
import { useFormValidation } from '@/hooks/useFormValidation'
import {
  useSerials, useCreateSerial, useUpdateSerial, useDeleteSerial,
  useProducts, useWarehouses, useSerialStatuses, useProductTypes,
} from '@/hooks/useInventory'
import { useUserLookup } from '@/hooks/useUserLookup'

export function SerialsPage() {
  const [showCreate, setShowCreate] = useState(false)
  const [filterEntity, setFilterEntity] = useState('')
  const [filterStatus, setFilterStatus] = useState('')
  const location = useLocation()
  useEffect(() => { setShowCreate(false) }, [location.key])

  const { data, isLoading } = useSerials({
    entity_id: filterEntity || undefined,
    status_id: filterStatus || undefined,
  })
  const { data: productsData } = useProducts()
  const { data: warehouses = [] } = useWarehouses()
  const { data: serialStatuses = [] } = useSerialStatuses()
  const { data: productTypes = [] } = useProductTypes()
  const updateSerial = useUpdateSerial()
  const deleteSerial = useDeleteSerial()

  const { resolve } = useUserLookup(data?.items.map(s => s.created_by) ?? [])
  const productMap = Object.fromEntries((productsData?.items ?? []).map(p => [p.id, p.name]))
  const whMap = Object.fromEntries(warehouses.map(w => [w.id, w.name]))
  const statusMap = Object.fromEntries(serialStatuses.map(s => [s.id, s]))

  // Filter products that track serials (via product type)
  const serialProducts = (productsData?.items ?? []).filter(p => {
    const pt = productTypes.find(t => t.id === p.product_type_id)
    return pt?.tracks_serials
  })

  return (
    <div className="max-w-5xl mx-auto p-6 space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-foreground">Seriales</h1>
        <button onClick={() => setShowCreate(true)}
          className="flex items-center gap-2 rounded-2xl bg-primary px-4 py-2.5 text-sm font-semibold text-white hover:bg-primary/90 ">
          <Plus className="h-4 w-4" /> Nuevo serial
        </button>
      </div>

      <div className="flex gap-3">
        <select value={filterEntity} onChange={e => setFilterEntity(e.target.value)}
          className="rounded-2xl border border-border bg-card px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-ring">
          <option value="">Todos los productos</option>
          {(productsData?.items ?? []).map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
        </select>
        <select value={filterStatus} onChange={e => setFilterStatus(e.target.value)}
          className="rounded-2xl border border-border bg-card px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-ring">
          <option value="">Todos los estados</option>
          {serialStatuses.map(s => <option key={s.id} value={s.id}>{s.name}</option>)}
        </select>
      </div>

      <div className="bg-card rounded-2xl border border-border  overflow-hidden">
        {isLoading ? (
          <div className="p-8 text-center text-muted-foreground">Cargando...</div>
        ) : !data?.items?.length ? (
          <div className="p-8 text-center">
            <Hash className="h-10 w-10 text-slate-200 mx-auto mb-3" />
            <p className="text-sm text-muted-foreground">Sin seriales registrados</p>
          </div>
        ) : (<>
          {/* Mobile cards */}
          <div className="space-y-3 p-4 md:hidden">
            {data.items.map(s => {
              const st = statusMap[s.status_id]
              return (
                <div key={s.id} className="rounded-xl border border-border bg-card p-4 space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="font-mono text-xs text-foreground font-semibold">{s.serial_number}</span>
                    <span className="text-xs text-muted-foreground">{new Date(s.created_at).toLocaleDateString('es-CO')}</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium text-foreground">{productMap[s.entity_id] ?? s.entity_id.slice(0, 8)}</span>
                    <select value={s.status_id}
                      onChange={async e => { await updateSerial.mutateAsync({ id: s.id, data: { status_id: e.target.value } }) }}
                      className="rounded-full border-0 bg-muted px-2 py-0.5 text-xs font-semibold focus:outline-none focus:ring-2 focus:ring-ring"
                      style={{ color: st?.color ?? '#6366f1' }}
                    >
                      {serialStatuses.map(ss => <option key={ss.id} value={ss.id}>{ss.name}</option>)}
                    </select>
                  </div>
                  <div className="flex items-center justify-between text-xs text-muted-foreground">
                    <span>Bodega: {s.warehouse_id ? whMap[s.warehouse_id] ?? '—' : '—'}</span>
                    <span className="flex items-center gap-2">
                      <span>{resolve(s.created_by)}</span>
                      <button onClick={async () => { if (confirm('¿Eliminar serial ' + s.serial_number + '?')) await deleteSerial.mutateAsync(s.id) }}
                        className="p-1 text-muted-foreground hover:text-red-600"><Trash2 className="h-3.5 w-3.5" /></button>
                    </span>
                  </div>
                </div>
              )
            })}
          </div>
          {/* Desktop table */}
          <div className="hidden md:block">
          <table className="w-full text-sm">
            <thead className="bg-muted border-b border-border">
              <tr>
                {['Serial', 'Producto', 'Estado', 'Bodega', 'Fecha', 'Creado por', 'Acciones'].map(h => (
                  <th key={h} className="px-4 py-3 text-left text-xs font-semibold text-muted-foreground uppercase tracking-wide">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-50">
              {data.items.map(s => {
                const st = statusMap[s.status_id]
                return (
                  <tr key={s.id} className="hover:bg-muted">
                    <td className="px-4 py-3 font-mono text-xs text-foreground font-semibold">{s.serial_number}</td>
                    <td className="px-4 py-3 font-medium text-foreground">{productMap[s.entity_id] ?? s.entity_id.slice(0, 8)}</td>
                    <td className="px-4 py-3">
                      <select value={s.status_id}
                        onChange={async e => { await updateSerial.mutateAsync({ id: s.id, data: { status_id: e.target.value } }) }}
                        className="rounded-full border-0 bg-muted px-2 py-0.5 text-xs font-semibold focus:outline-none focus:ring-2 focus:ring-ring"
                        style={{ color: st?.color ?? '#6366f1' }}
                      >
                        {serialStatuses.map(ss => <option key={ss.id} value={ss.id}>{ss.name}</option>)}
                      </select>
                    </td>
                    <td className="px-4 py-3 text-muted-foreground text-xs">{s.warehouse_id ? whMap[s.warehouse_id] ?? '—' : '—'}</td>
                    <td className="px-4 py-3 text-muted-foreground text-xs">{new Date(s.created_at).toLocaleDateString('es-CO')}</td>
                    <td className="px-4 py-3 text-muted-foreground text-xs">{resolve(s.created_by)}</td>
                    <td className="px-4 py-3 text-right">
                      <button onClick={async () => { if (confirm('¿Eliminar serial ' + s.serial_number + '?')) await deleteSerial.mutateAsync(s.id) }}
                        className="p-1 text-muted-foreground hover:text-red-600"><Trash2 className="h-3.5 w-3.5" /></button>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
          </div>
        </>)}
      </div>

      {showCreate && (
        <CreateSerialModal
          products={serialProducts.length ? serialProducts : (productsData?.items ?? [])}
          warehouses={warehouses}
          statuses={serialStatuses}
          onClose={() => setShowCreate(false)}
        />
      )}
    </div>
  )
}

function CreateSerialModal({
  products, warehouses, statuses, onClose,
}: {
  products: Array<{ id: string; name: string }>
  warehouses: Array<{ id: string; name: string }>
  statuses: Array<{ id: string; name: string }>
  onClose: () => void
}) {
  const create = useCreateSerial()
  const [form, setForm] = useState({ entity_id: '', serial_number: '', status_id: '', warehouse_id: '', notes: '' })

  async function doSubmit() {
    await create.mutateAsync({ ...form, warehouse_id: form.warehouse_id || null })
    onClose()
  }

  const { formRef, handleSubmit: validateAndSubmit } = useFormValidation(doSubmit)

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 backdrop-blur-sm">
      <div className="w-full max-w-md bg-card rounded-3xl shadow-2xl p-6">
        <h2 className="text-lg font-bold text-foreground mb-4">Nuevo Serial</h2>
        <form ref={formRef} onSubmit={validateAndSubmit} noValidate className="space-y-3">
          <select required value={form.entity_id} onChange={e => setForm(f => ({ ...f, entity_id: e.target.value }))}
            className="w-full rounded-xl border border-border px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring">
            <option value="">Producto *</option>
            {products.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
          </select>
          <input required value={form.serial_number} onChange={e => setForm(f => ({ ...f, serial_number: e.target.value }))}
            placeholder="Número de serial *" className="w-full rounded-xl border border-border px-3 py-2 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-ring" />
          <div className="grid grid-cols-2 gap-3">
            <select required value={form.status_id} onChange={e => setForm(f => ({ ...f, status_id: e.target.value }))}
              className="w-full rounded-xl border border-border px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring">
              <option value="">Estado *</option>
              {statuses.map(s => <option key={s.id} value={s.id}>{s.name}</option>)}
            </select>
            <select value={form.warehouse_id} onChange={e => setForm(f => ({ ...f, warehouse_id: e.target.value }))}
              className="w-full rounded-xl border border-border px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring">
              <option value="">Bodega</option>
              {warehouses.map(w => <option key={w.id} value={w.id}>{w.name}</option>)}
            </select>
          </div>
          <input value={form.notes} onChange={e => setForm(f => ({ ...f, notes: e.target.value }))}
            placeholder="Notas (opcional)" className="w-full rounded-xl border border-border px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring" />
          <div className="flex gap-3 pt-2">
            <button type="button" onClick={onClose} className="flex-1 rounded-xl border border-border px-4 py-2 text-sm text-muted-foreground hover:bg-muted">Cancelar</button>
            <button type="submit" disabled={create.isPending} className="flex-1 rounded-xl bg-primary px-4 py-2 text-sm font-semibold text-white hover:bg-primary/90 disabled:opacity-60">
              {create.isPending ? 'Guardando...' : 'Crear serial'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
