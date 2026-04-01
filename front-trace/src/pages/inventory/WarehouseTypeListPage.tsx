import { useState } from 'react'
import { Link } from 'react-router-dom'
import { ChevronRight, Warehouse, Plus, Pencil, Trash2, X, Shield } from 'lucide-react'
import {
  useWarehouseTypes, useCreateWarehouseType, useUpdateWarehouseType, useDeleteWarehouseType,
} from '@/hooks/useInventory'
import { useConfirm } from '@/store/confirm'
import type { DynamicWarehouseType } from '@/types/inventory'

export function WarehouseTypeListPage() {
  const { data: types = [], isLoading } = useWarehouseTypes()
  const create = useCreateWarehouseType()
  const update = useUpdateWarehouseType()
  const del = useDeleteWarehouseType()
  const confirm = useConfirm()

  const [modal, setModal] = useState<{ open: boolean; editing: DynamicWarehouseType | null }>({ open: false, editing: null })
  const [form, setForm] = useState({ name: '', description: '', color: '#f59e0b' })

  function openCreate() {
    setForm({ name: '', description: '', color: '#f59e0b' })
    setModal({ open: true, editing: null })
  }

  function openEdit(t: DynamicWarehouseType, e: React.MouseEvent) {
    e.preventDefault()
    e.stopPropagation()
    if (t.is_system) return
    setForm({ name: t.name, description: t.description ?? '', color: t.color ?? '#f59e0b' })
    setModal({ open: true, editing: t })
  }

  async function handleDelete(t: DynamicWarehouseType, e: React.MouseEvent) {
    e.preventDefault()
    e.stopPropagation()
    if (t.is_system) return
    const ok = await confirm({ message: `¿Eliminar el tipo de bodega "${t.name}"? Esta acción no se puede deshacer.`, confirmLabel: 'Eliminar' })
    if (ok) del.mutate(t.id)
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault()
    if (modal.editing) {
      await update.mutateAsync({ id: modal.editing.id, data: form })
    } else {
      await create.mutateAsync(form)
    }
    setModal({ open: false, editing: null })
  }

  return (
    <div className="p-8 space-y-6 max-w-5xl mx-auto">
      {/* Breadcrumbs */}
      <nav className="flex items-center gap-1.5 text-xs text-muted-foreground">
        <Link to="/inventario/configuracion" className="hover:text-muted-foreground transition-colors">Configuración</Link>
        <ChevronRight className="h-3 w-3" />
        <span className="text-foreground font-medium">Tipos de bodega</span>
      </nav>

      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-amber-50">
            <Warehouse className="h-5 w-5 text-amber-600" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-foreground">Tipos de bodega</h1>
            <p className="text-sm text-muted-foreground">Clasificación de almacenes</p>
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
          <Warehouse className="h-12 w-12 text-slate-200 mx-auto mb-4" />
          <h3 className="text-sm font-semibold text-foreground mb-1">Sin tipos de bodega</h3>
          <p className="text-xs text-muted-foreground mb-4">Crea tu primer tipo para clasificar tus bodegas.</p>
          <button onClick={openCreate}
            className="inline-flex items-center gap-1.5 rounded-lg bg-primary px-4 py-2 text-xs font-semibold text-white hover:bg-primary/90">
            <Plus className="h-3.5 w-3.5" /> Crear tipo de bodega
          </button>
        </div>
      ) : (
        <div className="bg-card rounded-2xl border border-border  divide-y divide-slate-100 overflow-hidden">
          {types.map(t => (
            <Link
              key={t.id}
              to={`/inventario/configuracion/tipos-bodega/${t.id}`}
              className="flex items-center gap-3 px-5 py-4 hover:bg-muted/50 transition-colors group"
            >
              <div className="h-3 w-3 rounded-full shrink-0" style={{ backgroundColor: t.color ?? '#f59e0b' }} />
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-semibold text-foreground">{t.name}</span>
                  {t.is_system && (
                    <span className="inline-flex items-center gap-1 rounded-full bg-secondary px-2 py-0.5 text-[10px] font-medium text-muted-foreground">
                      <Shield className="h-2.5 w-2.5" /> Sistema
                    </span>
                  )}
                </div>
                {t.description && (
                  <p className="text-xs text-muted-foreground mt-0.5 truncate">{t.description}</p>
                )}
              </div>
              <code className="text-[10px] font-mono text-muted-foreground bg-muted px-1.5 py-0.5 rounded hidden sm:block">{t.slug}</code>
              {!t.is_system && (
                <>
                  <button onClick={(e) => openEdit(t, e)}
                    className="rounded-lg p-1.5 text-slate-300 hover:text-primary hover:bg-secondary transition-colors opacity-0 group-hover:opacity-100">
                    <Pencil className="h-3.5 w-3.5" />
                  </button>
                  <button onClick={(e) => handleDelete(t, e)} disabled={del.isPending}
                    className="rounded-lg p-1.5 text-slate-300 hover:text-red-500 hover:bg-red-50 transition-colors opacity-0 group-hover:opacity-100 disabled:opacity-50">
                    <Trash2 className="h-3.5 w-3.5" />
                  </button>
                </>
              )}
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
                {modal.editing ? 'Editar tipo de bodega' : 'Nuevo tipo de bodega'}
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
                    placeholder="Ej: Refrigerado, Patio"
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
                <label className="block text-xs font-medium text-muted-foreground mb-1">Descripción</label>
                <textarea value={form.description}
                  onChange={e => setForm(f => ({ ...f, description: e.target.value }))}
                  rows={2} placeholder="Descripción del tipo de bodega"
                  className="w-full rounded-lg border border-border px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring resize-none" />
              </div>
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
