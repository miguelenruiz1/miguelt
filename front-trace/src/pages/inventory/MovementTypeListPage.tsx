import { useState } from 'react'
import { Link } from 'react-router-dom'
import { ChevronRight, ArrowLeftRight, Plus, Pencil, Trash2, X, Shield } from 'lucide-react'
import {
  useMovementTypes, useCreateMovementType, useUpdateMovementType, useDeleteMovementType,
} from '@/hooks/useInventory'
import { useConfirm } from '@/store/confirm'
import type { DynamicMovementType } from '@/types/inventory'

const DIRECTION_LABELS: Record<string, { label: string; color: string }> = {
  in: { label: 'Entrada', color: 'bg-emerald-100 text-emerald-700' },
  out: { label: 'Salida', color: 'bg-red-100 text-red-700' },
  internal: { label: 'Interno', color: 'bg-blue-100 text-blue-700' },
  neutral: { label: 'Neutral', color: 'bg-slate-100 text-slate-600' },
}

export function MovementTypeListPage() {
  const { data: types = [], isLoading } = useMovementTypes()
  const create = useCreateMovementType()
  const update = useUpdateMovementType()
  const del = useDeleteMovementType()
  const confirm = useConfirm()

  const [modal, setModal] = useState<{ open: boolean; editing: DynamicMovementType | null }>({ open: false, editing: null })
  const [form, setForm] = useState({ name: '', description: '', color: '#3b82f6', direction: 'in' })

  function openCreate() {
    setForm({ name: '', description: '', color: '#3b82f6', direction: 'in' })
    setModal({ open: true, editing: null })
  }

  function openEdit(t: DynamicMovementType, e: React.MouseEvent) {
    e.preventDefault()
    e.stopPropagation()
    if (t.is_system) return
    setForm({ name: t.name, description: t.description ?? '', color: t.color ?? '#3b82f6', direction: t.direction })
    setModal({ open: true, editing: t })
  }

  async function handleDelete(t: DynamicMovementType, e: React.MouseEvent) {
    e.preventDefault()
    e.stopPropagation()
    if (t.is_system) return
    const ok = await confirm({ message: `¿Eliminar el tipo de movimiento "${t.name}"? Esta acción no se puede deshacer.`, confirmLabel: 'Eliminar' })
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
      <nav className="flex items-center gap-1.5 text-xs text-slate-400">
        <Link to="/inventario/configuracion" className="hover:text-slate-600 transition-colors">Configuración</Link>
        <ChevronRight className="h-3 w-3" />
        <span className="text-slate-700 font-medium">Tipos de movimiento</span>
      </nav>

      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-blue-50">
            <ArrowLeftRight className="h-5 w-5 text-blue-600" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-slate-900">Tipos de movimiento</h1>
            <p className="text-sm text-slate-500">Tipos de movimiento de inventario</p>
          </div>
        </div>
        <button onClick={openCreate}
          className="flex items-center gap-1.5 rounded-xl bg-primary px-4 py-2 text-xs font-semibold text-white hover:bg-primary/90 shadow-sm transition-colors">
          <Plus className="h-3.5 w-3.5" /> Nuevo tipo
        </button>
      </div>

      {/* List */}
      {isLoading ? (
        <div className="bg-white rounded-2xl border border-slate-100 shadow-sm p-12 text-center text-sm text-slate-400">Cargando...</div>
      ) : types.length === 0 ? (
        <div className="bg-white rounded-2xl border-2 border-dashed border-slate-200 p-16 text-center">
          <ArrowLeftRight className="h-12 w-12 text-slate-200 mx-auto mb-4" />
          <h3 className="text-sm font-semibold text-slate-700 mb-1">Sin tipos de movimiento</h3>
          <p className="text-xs text-slate-400 mb-4">Crea tu primer tipo para clasificar tus movimientos.</p>
          <button onClick={openCreate}
            className="inline-flex items-center gap-1.5 rounded-lg bg-primary px-4 py-2 text-xs font-semibold text-white hover:bg-primary/90">
            <Plus className="h-3.5 w-3.5" /> Crear tipo de movimiento
          </button>
        </div>
      ) : (
        <div className="bg-white rounded-2xl border border-slate-100 shadow-sm divide-y divide-slate-100 overflow-hidden">
          {types.map(t => {
            const dir = DIRECTION_LABELS[t.direction] ?? DIRECTION_LABELS.neutral
            return (
              <Link
                key={t.id}
                to={`/inventario/configuracion/tipos-movimiento/${t.id}`}
                className="flex items-center gap-3 px-5 py-4 hover:bg-slate-50/50 transition-colors group"
              >
                <div className="h-3 w-3 rounded-full shrink-0" style={{ backgroundColor: t.color ?? '#3b82f6' }} />
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-semibold text-slate-900">{t.name}</span>
                    <span className={`rounded-full px-2 py-0.5 text-[10px] font-medium ${dir.color}`}>{dir.label}</span>
                    {t.is_system && (
                      <span className="inline-flex items-center gap-1 rounded-full bg-slate-100 px-2 py-0.5 text-[10px] font-medium text-slate-500">
                        <Shield className="h-2.5 w-2.5" /> Sistema
                      </span>
                    )}
                  </div>
                  {t.description && (
                    <p className="text-xs text-slate-400 mt-0.5 truncate">{t.description}</p>
                  )}
                </div>
                <code className="text-[10px] font-mono text-slate-400 bg-slate-50 px-1.5 py-0.5 rounded hidden sm:block">{t.slug}</code>
                {!t.is_system && (
                  <>
                    <button onClick={(e) => openEdit(t, e)}
                      className="rounded-lg p-1.5 text-slate-300 hover:text-primary hover:bg-slate-100 transition-colors opacity-0 group-hover:opacity-100">
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
            )
          })}
        </div>
      )}

      {/* Create / Edit Modal */}
      {modal.open && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 backdrop-blur-sm">
          <div className="w-full max-w-md bg-white rounded-2xl shadow-2xl">
            <div className="flex items-center justify-between px-6 py-4 border-b border-slate-100">
              <h3 className="text-sm font-bold text-slate-900">
                {modal.editing ? 'Editar tipo de movimiento' : 'Nuevo tipo de movimiento'}
              </h3>
              <button onClick={() => setModal({ open: false, editing: null })} className="text-slate-400 hover:text-slate-600">
                <X className="h-4 w-4" />
              </button>
            </div>
            <form onSubmit={submit} className="p-6 space-y-4">
              <div className="grid grid-cols-[1fr_72px] gap-3">
                <div>
                  <label className="block text-xs font-medium text-slate-600 mb-1">Nombre *</label>
                  <input required value={form.name}
                    onChange={e => setForm(f => ({ ...f, name: e.target.value }))}
                    placeholder="Ej: Devolución, Merma"
                    className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring" />
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-600 mb-1">Color</label>
                  <input type="color" value={form.color}
                    onChange={e => setForm(f => ({ ...f, color: e.target.value }))}
                    className="h-[38px] w-full rounded-lg border border-slate-200 cursor-pointer" />
                </div>
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-600 mb-1">Dirección</label>
                <select value={form.direction} onChange={e => setForm(f => ({ ...f, direction: e.target.value }))}
                  className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring">
                  <option value="in">Entrada</option>
                  <option value="out">Salida</option>
                  <option value="internal">Interno</option>
                  <option value="neutral">Neutral</option>
                </select>
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-600 mb-1">Descripción</label>
                <textarea value={form.description}
                  onChange={e => setForm(f => ({ ...f, description: e.target.value }))}
                  rows={2} placeholder="Descripción del tipo de movimiento"
                  className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring resize-none" />
              </div>
              <div className="flex justify-end gap-3 pt-1">
                <button type="button" onClick={() => setModal({ open: false, editing: null })}
                  className="rounded-lg border border-slate-200 px-4 py-2 text-xs text-slate-600 hover:bg-slate-50">Cancelar</button>
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
