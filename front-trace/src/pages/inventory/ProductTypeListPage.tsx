import { useState } from 'react'
import { Link } from 'react-router-dom'
import { ChevronRight, Tag, Plus, Pencil, Trash2, X } from 'lucide-react'
import { CopyableId } from '@/components/inventory/CopyableId'
import {
  useProductTypes, useCreateProductType, useUpdateProductType, useDeleteProductType,
  useLocations,
} from '@/hooks/useInventory'
import { useConfirm } from '@/store/confirm'
import type { ProductType } from '@/types/inventory'

export function ProductTypeListPage() {
  const { data: types = [], isLoading } = useProductTypes()
  const create = useCreateProductType()
  const update = useUpdateProductType()
  const del = useDeleteProductType()
  const confirm = useConfirm()

  const { data: locations = [] } = useLocations()

  const [modal, setModal] = useState<{ open: boolean; editing: ProductType | null }>({ open: false, editing: null })
  const [form, setForm] = useState({ name: '', description: '', color: '#6366f1', dispatch_rule: 'fifo' as 'fifo' | 'fefo' | 'lifo', requires_qc: false, entry_rule_location_id: '', rotation_target_months: null as number | null })

  function openCreate() {
    setForm({ name: '', description: '', color: '#6366f1', dispatch_rule: 'fifo', requires_qc: false, entry_rule_location_id: '', rotation_target_months: null })
    setModal({ open: true, editing: null })
  }

  function openEdit(t: ProductType, e: React.MouseEvent) {
    e.preventDefault()
    e.stopPropagation()
    setForm({ name: t.name, description: t.description ?? '', color: t.color ?? '#6366f1', dispatch_rule: t.dispatch_rule ?? 'fifo', requires_qc: t.requires_qc ?? false, entry_rule_location_id: t.entry_rule_location_id ?? '', rotation_target_months: t.rotation_target_months ?? null })
    setModal({ open: true, editing: t })
  }

  async function handleDelete(t: ProductType, e: React.MouseEvent) {
    e.preventDefault()
    e.stopPropagation()
    const ok = await confirm({ message: `¿Eliminar el tipo de producto "${t.name}"? Esta acción no se puede deshacer.`, confirmLabel: 'Eliminar' })
    if (ok) del.mutate(t.id)
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault()
    const data = {
      name: form.name,
      description: form.description || null,
      color: form.color,
      dispatch_rule: form.dispatch_rule,
      requires_qc: form.requires_qc,
      entry_rule_location_id: form.entry_rule_location_id || null,
      rotation_target_months: form.rotation_target_months,
    }
    if (modal.editing) {
      await update.mutateAsync({ id: modal.editing.id, data })
    } else {
      await create.mutateAsync(data)
    }
    setModal({ open: false, editing: null })
  }

  return (
    <div className="p-8 space-y-6 max-w-5xl mx-auto">
      {/* Breadcrumbs */}
      <nav className="flex items-center gap-1.5 text-xs text-muted-foreground">
        <Link to="/inventario/configuracion" className="hover:text-muted-foreground transition-colors">Configuración</Link>
        <ChevronRight className="h-3 w-3" />
        <span className="text-foreground font-medium">Tipos de producto</span>
      </nav>

      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-primary/10">
            <Tag className="h-5 w-5 text-primary" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-foreground">Tipos de producto</h1>
            <p className="text-sm text-muted-foreground">Clasifica tu catálogo de productos</p>
          </div>
        </div>
        <button onClick={openCreate}
          className="flex items-center gap-1.5 rounded-xl bg-primary px-4 py-2 text-xs font-semibold text-white hover:bg-primary/90  transition-colors">
          <Plus className="h-3.5 w-3.5" /> Nuevo tipo
        </button>
      </div>

      {/* List */}
      {isLoading ? (
        <div className="bg-card rounded-2xl border border-border  p-12 text-center text-sm text-muted-foreground">Cargando...</div>
      ) : types.length === 0 ? (
        <div className="bg-card rounded-2xl border-2 border-dashed border-border p-16 text-center">
          <Tag className="h-12 w-12 text-slate-200 mx-auto mb-4" />
          <h3 className="text-sm font-semibold text-foreground mb-1">Sin tipos de producto</h3>
          <p className="text-xs text-muted-foreground mb-4">Crea tu primer tipo para clasificar tus productos.</p>
          <button onClick={openCreate}
            className="inline-flex items-center gap-1.5 rounded-lg bg-primary px-4 py-2 text-xs font-semibold text-white hover:bg-primary/90">
            <Plus className="h-3.5 w-3.5" /> Crear tipo de producto
          </button>
        </div>
      ) : (
        <div className="bg-card rounded-2xl border border-border  divide-y divide-slate-100 overflow-hidden">
          {types.map(t => (
            <Link
              key={t.id}
              to={`/inventario/configuracion/tipos-producto/${t.id}`}
              className="flex items-center gap-3 px-5 py-4 hover:bg-muted/50 transition-colors group"
            >
              <div className="h-3 w-3 rounded-full shrink-0" style={{ backgroundColor: t.color ?? '#6366f1' }} />
              <div className="flex-1 min-w-0">
                <span className="text-sm font-semibold text-foreground">{t.name}</span>
                <div className="flex items-center gap-2 mt-0.5">
                  <CopyableId id={t.id} />
                  {t.description && (
                    <p className="text-xs text-muted-foreground truncate">{t.description}</p>
                  )}
                </div>
              </div>
              <code className="text-[10px] font-mono text-muted-foreground bg-muted px-1.5 py-0.5 rounded hidden sm:block">{t.slug}</code>
              <button onClick={(e) => openEdit(t, e)}
                className="rounded-lg p-1.5 text-slate-300 hover:text-primary hover:bg-secondary transition-colors opacity-0 group-hover:opacity-100">
                <Pencil className="h-3.5 w-3.5" />
              </button>
              <button onClick={(e) => handleDelete(t, e)} disabled={del.isPending}
                className="rounded-lg p-1.5 text-slate-300 hover:text-red-500 hover:bg-red-50 transition-colors opacity-0 group-hover:opacity-100 disabled:opacity-50">
                <Trash2 className="h-3.5 w-3.5" />
              </button>
              <ChevronRight className="h-4 w-4 text-slate-300 group-hover:text-primary/70 transition-colors" />
            </Link>
          ))}
        </div>
      )}

      {/* Create / Edit Modal */}
      {modal.open && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 backdrop-blur-sm">
          <div className="w-full max-w-md bg-card rounded-2xl shadow-2xl">
            <div className="flex items-center justify-between px-6 py-4 border-b border-border">
              <h3 className="text-sm font-bold text-foreground">
                {modal.editing ? 'Editar tipo de producto' : 'Nuevo tipo de producto'}
              </h3>
              <button onClick={() => setModal({ open: false, editing: null })} className="text-muted-foreground hover:text-muted-foreground">
                <X className="h-4 w-4" />
              </button>
            </div>
            <form onSubmit={submit} className="p-6 space-y-4">
              <div className="grid grid-cols-[1fr_72px] gap-3">
                <div>
                  <label className="block text-xs font-medium text-muted-foreground mb-1">Nombre *</label>
                  <input required value={form.name}
                    onChange={e => setForm(f => ({ ...f, name: e.target.value }))}
                    placeholder="Ej: Electrónico, Perecedero"
                    className="w-full rounded-lg border border-border px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring" />
                </div>
                <div>
                  <label className="block text-xs font-medium text-muted-foreground mb-1">Color</label>
                  <input type="color" value={form.color}
                    onChange={e => setForm(f => ({ ...f, color: e.target.value }))}
                    className="h-[38px] w-full rounded-lg border border-border cursor-pointer" />
                </div>
              </div>
              <div>
                <label className="block text-xs font-medium text-muted-foreground mb-1">Descripcion</label>
                <textarea value={form.description}
                  onChange={e => setForm(f => ({ ...f, description: e.target.value }))}
                  rows={2} placeholder="Descripcion del tipo de producto"
                  className="w-full rounded-lg border border-border px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring resize-none" />
              </div>
              <div>
                <label className="block text-xs font-medium text-muted-foreground mb-1">Regla de despacho</label>
                <select
                  value={form.dispatch_rule}
                  onChange={e => setForm(f => ({ ...f, dispatch_rule: e.target.value as 'fifo' | 'fefo' | 'lifo' }))}
                  className="w-full rounded-lg border border-border px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                >
                  <option value="fifo">FIFO (primero en entrar, primero en salir)</option>
                  <option value="fefo">FEFO (por vencimiento)</option>
                  <option value="lifo">LIFO (ultimo en entrar, primero en salir)</option>
                </select>
              </div>
              <div className="flex items-center gap-2">
                <input type="checkbox" checked={form.requires_qc}
                  onChange={e => setForm(f => ({ ...f, requires_qc: e.target.checked }))}
                  className="rounded border-slate-300" id="requires_qc" />
                <label htmlFor="requires_qc" className="text-xs font-medium text-muted-foreground cursor-pointer">Requiere control de calidad al recibir</label>
              </div>
              <div>
                <label className="block text-xs font-medium text-muted-foreground mb-1">Ubicacion de entrada predeterminada</label>
                <select
                  value={form.entry_rule_location_id}
                  onChange={e => setForm(f => ({ ...f, entry_rule_location_id: e.target.value }))}
                  className="w-full rounded-lg border border-border px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                >
                  <option value="">Sin ubicacion predeterminada</option>
                  {locations.map(loc => (
                    <option key={loc.id} value={loc.id}>{loc.name} ({loc.code})</option>
                  ))}
                </select>
              </div>
              <label className="flex flex-col gap-1">
                <span className="text-xs font-semibold text-muted-foreground">Meses de rotacion objetivo</span>
                <input
                  type="number"
                  min={1}
                  max={36}
                  placeholder="Ej: 3"
                  className="rounded-xl border border-border px-3 py-2 text-sm focus:ring-2 focus:ring-ring/30 focus:border-ring"
                  value={form.rotation_target_months ?? ''}
                  onChange={e => setForm(f => ({ ...f, rotation_target_months: e.target.value ? Number(e.target.value) : null }))}
                />
                <span className="text-[10px] text-muted-foreground">Politica de stock: maximo meses de inventario permitidos</span>
              </label>
              <div className="flex justify-end gap-3 pt-1">
                <button type="button" onClick={() => setModal({ open: false, editing: null })}
                  className="rounded-lg border border-border px-4 py-2 text-xs text-muted-foreground hover:bg-muted">Cancelar</button>
                <button type="submit" disabled={create.isPending || update.isPending}
                  className="rounded-lg bg-primary px-4 py-2 text-xs font-semibold text-white hover:bg-primary/90 disabled:opacity-50">
                  {create.isPending || update.isPending ? 'Guardando...' : modal.editing ? 'Guardar' : 'Crear'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
