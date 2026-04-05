import { useState, useDeferredValue } from 'react'
import { FolderTree, Plus, Pencil, Trash2, Search, X } from 'lucide-react'
import { cn } from '@/lib/utils'
import { useFormValidation } from '@/hooks/useFormValidation'
import {
  useCategories, useCreateCategory, useUpdateCategory, useDeleteCategory,
} from '@/hooks/useInventory'
import type { Category } from '@/types/inventory'

function CategoryModal({
  category,
  categories,
  onClose,
}: {
  category: Category | null
  categories: Category[]
  onClose: () => void
}) {
  const create = useCreateCategory()
  const update = useUpdateCategory()
  const [error, setError] = useState('')
  const [form, setForm] = useState({
    name: category?.name ?? '',
    description: category?.description ?? '',
    parent_id: category?.parent_id ?? '',
    is_active: category?.is_active ?? true,
  })

  const isPending = create.isPending || update.isPending

  async function doSubmit() {
    setError('')
    try {
      const payload = {
        name: form.name,
        description: form.description || null,
        parent_id: form.parent_id || null,
        is_active: form.is_active,
      }
      if (category) {
        await update.mutateAsync({ id: category.id, data: payload })
      } else {
        await create.mutateAsync(payload)
      }
      onClose()
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Error al guardar')
    }
  }

  const { formRef, handleSubmit: validateAndSubmit } = useFormValidation(doSubmit)

  // Filter out self and descendants to prevent circular parent references
  const parentOptions = categories.filter(c => !category || c.id !== category.id)

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 backdrop-blur-sm">
      <div className="w-full max-w-lg bg-card rounded-3xl shadow-2xl p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-bold text-foreground">
            {category ? 'Editar categoría' : 'Nueva categoría'}
          </h2>
          <button onClick={onClose} className="p-1 hover:bg-secondary rounded-lg">
            <X className="h-4 w-4 text-muted-foreground" />
          </button>
        </div>
        <form ref={formRef} onSubmit={validateAndSubmit} noValidate className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-muted-foreground mb-1">Nombre *</label>
            <input
              required
              value={form.name}
              onChange={e => setForm(f => ({ ...f, name: e.target.value }))}
              className="w-full rounded-xl border border-border px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
              placeholder="Ej: Materias primas"
            />
          </div>
          <div>
            <label className="block text-xs font-semibold text-muted-foreground mb-1">Descripción</label>
            <textarea
              value={form.description}
              onChange={e => setForm(f => ({ ...f, description: e.target.value }))}
              rows={2}
              className="w-full rounded-xl border border-border px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
              placeholder="Descripción opcional"
            />
          </div>
          <div>
            <label className="block text-xs font-semibold text-muted-foreground mb-1">Categoría padre</label>
            <select
              value={form.parent_id}
              onChange={e => setForm(f => ({ ...f, parent_id: e.target.value }))}
              className="w-full rounded-xl border border-border px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
            >
              <option value="">Sin padre (raíz)</option>
              {(() => {
                const opts: { id: string; label: string }[] = []
                const roots = parentOptions.filter(c => !c.parent_id)
                for (const root of roots) {
                  opts.push({ id: root.id, label: root.name })
                  for (const child of parentOptions.filter(c => c.parent_id === root.id)) {
                    opts.push({ id: child.id, label: `  ↳ ${child.name}` })
                  }
                }
                const listed = new Set(opts.map(o => o.id))
                for (const c of parentOptions) {
                  if (!listed.has(c.id)) opts.push({ id: c.id, label: c.name })
                }
                return opts.map(o => <option key={o.id} value={o.id}>{o.label}</option>)
              })()}
            </select>
          </div>
          <div className="flex items-center gap-2">
            <input
              type="checkbox"
              checked={form.is_active}
              onChange={e => setForm(f => ({ ...f, is_active: e.target.checked }))}
              id="cat-active"
              className="rounded border-slate-300"
            />
            <label htmlFor="cat-active" className="text-sm text-muted-foreground">Activa</label>
          </div>
          {error && (
            <div className="rounded-xl bg-red-50 border border-red-200 px-3 py-2 text-sm text-red-700">
              {error}
            </div>
          )}
          <div className="flex gap-3 pt-2">
            <button type="button" onClick={onClose} className="flex-1 rounded-xl border border-border px-4 py-2 text-sm text-muted-foreground hover:bg-muted">
              Cancelar
            </button>
            <button type="submit" disabled={isPending} className="flex-1 rounded-xl bg-primary px-4 py-2 text-sm font-semibold text-white hover:bg-primary/90 disabled:opacity-60">
              {isPending ? 'Guardando...' : category ? 'Guardar' : 'Crear'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

export function CategoriesPage() {
  const [showModal, setShowModal] = useState(false)
  const [editing, setEditing] = useState<Category | null>(null)
  const [searchText, setSearchText] = useState('')
  const [showInactive, setShowInactive] = useState(false)
  const deferredSearch = useDeferredValue(searchText)
  const deleteMut = useDeleteCategory()

  const { data, isLoading } = useCategories({
    search: deferredSearch || undefined,
    is_active: showInactive ? undefined : true,
  })

  const categories = data?.items ?? []

  function handleEdit(cat: Category) {
    setEditing(cat)
    setShowModal(true)
  }

  function handleClose() {
    setShowModal(false)
    setEditing(null)
  }

  async function handleDelete(cat: Category) {
    if (!confirm(`Eliminar categoría "${cat.name}"?`)) return
    await deleteMut.mutateAsync(cat.id)
  }

  return (
    <div className="max-w-5xl mx-auto p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <FolderTree className="h-6 w-6 text-primary" />
          <h1 className="text-2xl font-bold text-foreground">Categorías de producto</h1>
        </div>
        <button
          onClick={() => { setEditing(null); setShowModal(true) }}
          className="flex items-center gap-2 rounded-2xl bg-primary px-4 py-2.5 text-sm font-semibold text-white hover:bg-primary/90 "
        >
          <Plus className="h-4 w-4" /> Nueva categoría
        </button>
      </div>

      {/* Search + filters */}
      <div className="flex items-center gap-3">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <input
            type="text"
            value={searchText}
            onChange={e => setSearchText(e.target.value)}
            placeholder="Buscar categorías..."
            className="w-full rounded-xl border border-border pl-9 pr-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
          />
        </div>
        <button
          onClick={() => setShowInactive(v => !v)}
          className={cn(
            'rounded-xl px-3 py-2 text-xs font-semibold transition-colors',
            showInactive ? 'bg-slate-700 text-white' : 'bg-secondary text-muted-foreground hover:bg-slate-200',
          )}
        >
          {showInactive ? 'Mostrando inactivas' : 'Solo activas'}
        </button>
      </div>

      {/* Table */}
      <div className="bg-card rounded-2xl border border-border  overflow-hidden">
        {isLoading ? (
          <div className="p-8 text-center text-muted-foreground">Cargando...</div>
        ) : !categories.length ? (
          <div className="p-8 text-center text-muted-foreground">Sin categorías</div>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-muted border-b border-border">
              <tr>
                {['Nombre', 'Descripción', 'Estado', 'Acciones'].map(h => (
                  <th key={h} className="px-5 py-3 text-left text-xs font-semibold text-muted-foreground uppercase tracking-wide">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-50">
              {(() => {
                // Build tree: parents first, then children indented
                const roots = categories.filter(c => !c.parent_id)
                const children = (parentId: string) => categories.filter(c => c.parent_id === parentId)
                const rows: { cat: Category; depth: number }[] = []
                for (const root of roots) {
                  rows.push({ cat: root, depth: 0 })
                  for (const child of children(root.id)) {
                    rows.push({ cat: child, depth: 1 })
                    for (const grandchild of children(child.id)) {
                      rows.push({ cat: grandchild, depth: 2 })
                    }
                  }
                }
                // Add orphans (parent not in current list)
                const listed = new Set(rows.map(r => r.cat.id))
                for (const cat of categories) {
                  if (!listed.has(cat.id)) rows.push({ cat, depth: 0 })
                }
                return rows.map(({ cat, depth }) => (
                  <tr key={cat.id} className="hover:bg-muted">
                    <td className="px-5 py-3 font-medium text-foreground">
                      <div className="flex items-center gap-2" style={{ paddingLeft: depth * 24 }}>
                        {depth > 0 && <span className="text-muted-foreground">└</span>}
                        <FolderTree className={cn('h-3.5 w-3.5 shrink-0', depth === 0 ? 'text-primary' : 'text-muted-foreground')} />
                        <span>{cat.name}</span>
                        {children(cat.id).length > 0 && (
                          <span className="text-[10px] bg-secondary text-muted-foreground rounded-full px-1.5 py-0.5">{children(cat.id).length}</span>
                        )}
                      </div>
                    </td>
                    <td className="px-5 py-3 text-muted-foreground text-xs max-w-[250px] truncate">{cat.description || '\u2014'}</td>
                    <td className="px-5 py-3">
                      <span className={cn(
                        'inline-flex rounded-full px-2 py-0.5 text-[11px] font-semibold',
                        cat.is_active ? 'bg-emerald-50 text-emerald-700' : 'bg-secondary text-muted-foreground',
                      )}>
                        {cat.is_active ? 'Activa' : 'Inactiva'}
                      </span>
                    </td>
                    <td className="px-5 py-3">
                      <div className="flex items-center gap-2">
                        <button onClick={() => handleEdit(cat)} className="p-1.5 hover:bg-secondary rounded-lg" title="Editar">
                          <Pencil className="h-3.5 w-3.5 text-muted-foreground" />
                        </button>
                        <button onClick={() => handleDelete(cat)} className="p-1.5 hover:bg-red-50 rounded-lg" title="Eliminar" disabled={deleteMut.isPending}>
                          <Trash2 className="h-3.5 w-3.5 text-red-500" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))
              })()}
            </tbody>
          </table>
        )}
      </div>

      {showModal && <CategoryModal category={editing} categories={categories} onClose={handleClose} />}
    </div>
  )
}
