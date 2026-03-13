import { useState, useEffect, useMemo } from 'react'
import { FlaskConical, Plus, Trash2, Eye, Pencil, AlertTriangle, CheckCircle2, Warehouse } from 'lucide-react'
import {
  useRecipes, useRecipe, useCreateRecipe, useUpdateRecipe, useDeleteRecipe, useProducts,
  useStockLevels, useWarehouses,
} from '@/hooks/useInventory'
import type { StockLevel, EntityRecipe } from '@/types/inventory'

type StockByProduct = Record<string, { total: number; byWarehouse: Record<string, number> }>

function buildStockMap(stockLevels: StockLevel[] | undefined): StockByProduct {
  const map: StockByProduct = {}
  for (const sl of stockLevels ?? []) {
    const qty = parseFloat(sl.qty_on_hand) - parseFloat(sl.qty_reserved)
    if (!map[sl.product_id]) map[sl.product_id] = { total: 0, byWarehouse: {} }
    map[sl.product_id].total += qty
    map[sl.product_id].byWarehouse[sl.warehouse_id] =
      (map[sl.product_id].byWarehouse[sl.warehouse_id] ?? 0) + qty
  }
  return map
}

function getRecipeAvailability(recipe: EntityRecipe, stockMap: StockByProduct) {
  const components = recipe.components ?? []
  if (components.length === 0) return { available: true, missing: [] as string[], warehouses: new Set<string>() }

  const missing: string[] = []
  const warehouses = new Set<string>()

  for (const c of components) {
    const stock = stockMap[c.component_entity_id]
    const needed = parseFloat(String(c.quantity_required))
    if (!stock || stock.total < needed) {
      missing.push(c.component_entity_id)
    }
    if (stock) {
      for (const wId of Object.keys(stock.byWarehouse)) {
        if (stock.byWarehouse[wId] > 0) warehouses.add(wId)
      }
    }
  }

  return { available: missing.length === 0, missing, warehouses }
}

function AvailabilityBadge({ available, missingCount }: { available: boolean; missingCount: number }) {
  if (available) {
    return (
      <span className="inline-flex items-center gap-1 rounded-full bg-emerald-50 px-2.5 py-0.5 text-[11px] font-semibold text-emerald-700">
        <CheckCircle2 className="h-3 w-3" /> Disponible
      </span>
    )
  }
  return (
    <span className="inline-flex items-center gap-1 rounded-full bg-red-50 px-2.5 py-0.5 text-[11px] font-semibold text-red-700">
      <AlertTriangle className="h-3 w-3" /> {missingCount} sin stock
    </span>
  )
}

function RecipeDrawer({ recipeId, onClose, onEdit, stockMap, warehouseMap }: {
  recipeId: string; onClose: () => void; onEdit: (id: string) => void
  stockMap: StockByProduct; warehouseMap: Record<string, string>
}) {
  const { data: recipe } = useRecipe(recipeId)
  const { data: productsData } = useProducts()
  const productMap = Object.fromEntries((productsData?.items ?? []).map(p => [p.id, p]))

  if (!recipe) return null
  const outputProduct = productMap[recipe.output_entity_id]
  const availability = getRecipeAvailability(recipe, stockMap)

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-black/20 backdrop-blur-sm">
      <div className="w-full max-w-md bg-white h-full shadow-2xl p-6 overflow-y-auto">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h2 className="font-bold text-slate-900">{recipe.name}</h2>
            {recipe.description && <p className="text-xs text-slate-400 mt-1">{recipe.description}</p>}
          </div>
          <div className="flex items-center gap-2">
            <button onClick={() => { onClose(); onEdit(recipeId) }} className="text-slate-400 hover:text-indigo-600" title="Editar">
              <Pencil className="h-4 w-4" />
            </button>
            <button onClick={onClose} className="text-slate-400 hover:text-slate-600 text-xl font-bold">x</button>
          </div>
        </div>

        <div className="space-y-4">
          {/* Availability alert */}
          {!availability.available && (
            <div className="bg-red-50 border border-red-200 rounded-xl p-3 flex items-start gap-2">
              <AlertTriangle className="h-4 w-4 text-red-500 mt-0.5 shrink-0" />
              <div>
                <p className="text-xs font-semibold text-red-800">Componentes sin stock suficiente</p>
                <p className="text-xs text-red-600 mt-0.5">
                  {availability.missing.map(id => productMap[id]?.name ?? id.slice(0, 8)).join(', ')}
                </p>
              </div>
            </div>
          )}

          {/* Warehouses where components exist */}
          {availability.warehouses.size > 0 && (
            <div className="bg-slate-50 border border-slate-200 rounded-xl p-3">
              <p className="text-xs font-bold text-slate-500 uppercase tracking-wide mb-1.5 flex items-center gap-1">
                <Warehouse className="h-3 w-3" /> Bodegas con stock
              </p>
              <div className="flex flex-wrap gap-1.5">
                {[...availability.warehouses].map(wId => (
                  <span key={wId} className="inline-flex rounded-full bg-white border border-slate-200 px-2.5 py-0.5 text-[11px] font-medium text-slate-700">
                    {warehouseMap[wId] ?? wId.slice(0, 8)}
                  </span>
                ))}
              </div>
            </div>
          )}

          <div className="bg-indigo-50 rounded-xl p-4">
            <p className="text-xs font-bold text-indigo-400 uppercase tracking-wide mb-1">Producto de salida</p>
            <p className="font-semibold text-indigo-900">{outputProduct?.name ?? recipe.output_entity_id.slice(0, 8)}</p>
            <p className="text-sm text-indigo-600">Cantidad: {recipe.output_quantity}</p>
          </div>

          <div>
            <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wide mb-2">
              Componentes ({recipe.components?.length ?? 0})
            </h3>
            {recipe.components?.length ? (
              <div className="space-y-2">
                {recipe.components.map(c => {
                  const p = productMap[c.component_entity_id]
                  const stock = stockMap[c.component_entity_id]
                  const totalAvail = stock?.total ?? 0
                  const needed = parseFloat(String(c.quantity_required))
                  const hasEnough = totalAvail >= needed

                  return (
                    <div key={c.id} className={`rounded-xl p-3 ${hasEnough ? 'bg-slate-50' : 'bg-red-50 border border-red-100'}`}>
                      <div className="flex justify-between items-center">
                        <span className="font-medium text-slate-700">{p?.name ?? c.component_entity_id.slice(0, 8)}</span>
                        <div className="flex items-center gap-2">
                          <span className={`text-xs font-medium ${hasEnough ? 'text-emerald-600' : 'text-red-600'}`}>
                            {totalAvail.toFixed(1)} / {needed}
                          </span>
                          <span className="font-bold text-slate-900">{c.quantity_required}</span>
                        </div>
                      </div>
                      {/* Warehouse breakdown */}
                      {stock && Object.keys(stock.byWarehouse).length > 0 && (
                        <div className="flex flex-wrap gap-1 mt-1.5">
                          {Object.entries(stock.byWarehouse)
                            .filter(([, qty]) => qty > 0)
                            .map(([wId, qty]) => (
                            <span key={wId} className="inline-flex items-center gap-1 rounded bg-white border border-slate-200 px-1.5 py-0.5 text-[10px] text-slate-500">
                              <Warehouse className="h-2.5 w-2.5" />
                              {warehouseMap[wId] ?? wId.slice(0, 6)}: <b className="text-slate-700">{qty.toFixed(1)}</b>
                            </span>
                          ))}
                        </div>
                      )}
                      {!stock && (
                        <p className="text-[10px] text-red-500 mt-1">Sin stock en ninguna bodega</p>
                      )}
                    </div>
                  )
                })}
              </div>
            ) : <p className="text-sm text-slate-400">Sin componentes</p>}
          </div>
        </div>
      </div>
    </div>
  )
}

function EditRecipeModal({ recipeId, onClose }: { recipeId: string; onClose: () => void }) {
  const { data: recipe } = useRecipe(recipeId)
  const { data: productsData } = useProducts()
  const update = useUpdateRecipe()

  const [form, setForm] = useState({ name: '', description: '', output_entity_id: '', output_quantity: '1' })
  const [components, setComponents] = useState<Array<{ component_entity_id: string; quantity_required: string }>>([])
  const [loaded, setLoaded] = useState(false)

  useEffect(() => {
    if (recipe && !loaded) {
      setForm({
        name: recipe.name,
        description: recipe.description ?? '',
        output_entity_id: recipe.output_entity_id,
        output_quantity: String(recipe.output_quantity),
      })
      setComponents(
        (recipe.components ?? []).map(c => ({
          component_entity_id: c.component_entity_id,
          quantity_required: String(c.quantity_required),
        }))
      )
      setLoaded(true)
    }
  }, [recipe, loaded])

  function addComponent() {
    setComponents(c => [...c, { component_entity_id: '', quantity_required: '1' }])
  }

  function removeComponent(idx: number) {
    setComponents(c => c.filter((_, i) => i !== idx))
  }

  function updateComponent(idx: number, key: string, val: string) {
    setComponents(c => c.map((comp, i) => i === idx ? { ...comp, [key]: val } : comp))
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    await update.mutateAsync({ id: recipeId, data: { ...form, components } })
    onClose()
  }

  if (!recipe) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 backdrop-blur-sm">
      <div className="w-full max-w-lg bg-white rounded-3xl shadow-2xl p-6 max-h-[90vh] overflow-y-auto">
        <h2 className="text-lg font-bold text-slate-900 mb-4">Editar Receta</h2>
        <form onSubmit={handleSubmit} className="space-y-3">
          <input required value={form.name} onChange={e => setForm(f => ({ ...f, name: e.target.value }))}
            placeholder="Nombre *" className="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400" />
          <div className="grid grid-cols-2 gap-3">
            <select required value={form.output_entity_id} onChange={e => setForm(f => ({ ...f, output_entity_id: e.target.value }))}
              className="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400">
              <option value="">Producto de salida *</option>
              {productsData?.items?.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
            </select>
            <input required type="number" step="0.01" min="0.01" value={form.output_quantity}
              onChange={e => setForm(f => ({ ...f, output_quantity: e.target.value }))}
              placeholder="Cantidad salida *" className="rounded-xl border border-slate-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400" />
          </div>
          <textarea value={form.description} onChange={e => setForm(f => ({ ...f, description: e.target.value }))}
            placeholder="Descripcion" rows={2}
            className="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400" />

          <div className="border-t border-slate-100 pt-3">
            <div className="flex items-center justify-between mb-2">
              <p className="text-xs font-bold text-slate-400 uppercase tracking-wide">Componentes</p>
              <button type="button" onClick={addComponent} className="text-xs text-indigo-600 hover:text-indigo-800 font-semibold">
                + Agregar
              </button>
            </div>
            {components.map((c, i) => (
              <div key={i} className="flex gap-2 mb-2">
                <select required value={c.component_entity_id} onChange={e => updateComponent(i, 'component_entity_id', e.target.value)}
                  className="flex-1 rounded-lg border border-slate-200 px-2 py-1.5 text-sm">
                  <option value="">Producto *</option>
                  {productsData?.items?.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
                </select>
                <input required type="number" step="0.01" min="0.01" value={c.quantity_required}
                  onChange={e => updateComponent(i, 'quantity_required', e.target.value)}
                  placeholder="Cant." className="w-24 rounded-lg border border-slate-200 px-2 py-1.5 text-sm" />
                <button type="button" onClick={() => removeComponent(i)} className="text-slate-400 hover:text-red-500">
                  <Trash2 className="h-4 w-4" />
                </button>
              </div>
            ))}
            {components.length === 0 && (
              <p className="text-xs text-slate-400 text-center py-2">Sin componentes. Usa "+ Agregar" para anadir.</p>
            )}
          </div>

          <div className="flex gap-3 pt-2">
            <button type="button" onClick={onClose} className="flex-1 rounded-xl border border-slate-200 px-4 py-2 text-sm text-slate-600 hover:bg-slate-50">Cancelar</button>
            <button type="submit" disabled={update.isPending} className="flex-1 rounded-xl bg-indigo-600 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-700 disabled:opacity-60">
              {update.isPending ? 'Guardando...' : 'Guardar cambios'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

function CreateRecipeModal({ onClose }: { onClose: () => void }) {
  const { data: productsData } = useProducts()
  const create = useCreateRecipe()

  const [form, setForm] = useState({
    name: '', description: '', output_entity_id: '', output_quantity: '1',
  })
  const [components, setComponents] = useState<Array<{ component_entity_id: string; quantity_required: string }>>([])

  function addComponent() {
    setComponents(c => [...c, { component_entity_id: '', quantity_required: '1' }])
  }

  function removeComponent(idx: number) {
    setComponents(c => c.filter((_, i) => i !== idx))
  }

  function updateComponent(idx: number, key: string, val: string) {
    setComponents(c => c.map((comp, i) => i === idx ? { ...comp, [key]: val } : comp))
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    await create.mutateAsync({ ...form, components })
    onClose()
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 backdrop-blur-sm">
      <div className="w-full max-w-lg bg-white rounded-3xl shadow-2xl p-6 max-h-[90vh] overflow-y-auto">
        <h2 className="text-lg font-bold text-slate-900 mb-4">Nueva Receta</h2>
        <form onSubmit={handleSubmit} className="space-y-3">
          <input required value={form.name} onChange={e => setForm(f => ({ ...f, name: e.target.value }))}
            placeholder="Nombre *" className="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400" />
          <div className="grid grid-cols-2 gap-3">
            <select required value={form.output_entity_id} onChange={e => setForm(f => ({ ...f, output_entity_id: e.target.value }))}
              className="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400">
              <option value="">Producto de salida *</option>
              {productsData?.items?.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
            </select>
            <input required type="number" step="0.01" min="0.01" value={form.output_quantity}
              onChange={e => setForm(f => ({ ...f, output_quantity: e.target.value }))}
              placeholder="Cantidad salida *" className="rounded-xl border border-slate-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400" />
          </div>
          <textarea value={form.description} onChange={e => setForm(f => ({ ...f, description: e.target.value }))}
            placeholder="Descripcion" rows={2}
            className="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400" />

          <div className="border-t border-slate-100 pt-3">
            <div className="flex items-center justify-between mb-2">
              <p className="text-xs font-bold text-slate-400 uppercase tracking-wide">Componentes</p>
              <button type="button" onClick={addComponent} className="text-xs text-indigo-600 hover:text-indigo-800 font-semibold">
                + Agregar
              </button>
            </div>
            {components.map((c, i) => (
              <div key={i} className="flex gap-2 mb-2">
                <select required value={c.component_entity_id} onChange={e => updateComponent(i, 'component_entity_id', e.target.value)}
                  className="flex-1 rounded-lg border border-slate-200 px-2 py-1.5 text-sm">
                  <option value="">Producto *</option>
                  {productsData?.items?.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
                </select>
                <input required type="number" step="0.01" min="0.01" value={c.quantity_required}
                  onChange={e => updateComponent(i, 'quantity_required', e.target.value)}
                  placeholder="Cant." className="w-24 rounded-lg border border-slate-200 px-2 py-1.5 text-sm" />
                <button type="button" onClick={() => removeComponent(i)} className="text-slate-400 hover:text-red-500">
                  <Trash2 className="h-4 w-4" />
                </button>
              </div>
            ))}
          </div>

          <div className="flex gap-3 pt-2">
            <button type="button" onClick={onClose} className="flex-1 rounded-xl border border-slate-200 px-4 py-2 text-sm text-slate-600 hover:bg-slate-50">Cancelar</button>
            <button type="submit" disabled={create.isPending} className="flex-1 rounded-xl bg-indigo-600 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-700 disabled:opacity-60">
              {create.isPending ? 'Guardando...' : 'Crear receta'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

export function RecipesPage() {
  const [showCreate, setShowCreate] = useState(false)
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [editId, setEditId] = useState<string | null>(null)
  const [confirmDeleteId, setConfirmDeleteId] = useState<string | null>(null)
  const { data: recipes = [], isLoading } = useRecipes()
  const { data: productsData } = useProducts()
  const { data: stockLevels } = useStockLevels()
  const { data: warehouses = [] } = useWarehouses()
  const del = useDeleteRecipe()
  const productMap = Object.fromEntries((productsData?.items ?? []).map(p => [p.id, p.name]))
  const warehouseMap = useMemo(() => Object.fromEntries(warehouses.map(w => [w.id, w.name])), [warehouses])
  const stockMap = useMemo(() => buildStockMap(stockLevels), [stockLevels])

  return (
    <div className="max-w-5xl mx-auto p-6 space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-slate-900">Recetas</h1>
        <button onClick={() => setShowCreate(true)}
          className="flex items-center gap-2 rounded-2xl bg-indigo-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-indigo-700 shadow-sm">
          <Plus className="h-4 w-4" /> Nueva receta
        </button>
      </div>

      <div className="bg-white rounded-2xl border border-slate-100 shadow-sm overflow-hidden">
        {isLoading ? (
          <div className="p-8 text-center text-slate-400">Cargando...</div>
        ) : recipes.length === 0 ? (
          <div className="p-8 text-center">
            <FlaskConical className="h-10 w-10 text-slate-200 mx-auto mb-3" />
            <p className="text-sm text-slate-400">Sin recetas. Crea la primera.</p>
          </div>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-slate-50 border-b border-slate-100">
              <tr>
                {['Nombre', 'Producto salida', 'Cant. salida', 'Componentes', 'Disponibilidad', 'Bodegas', ''].map(h => (
                  <th key={h} className="px-4 py-3 text-left text-xs font-semibold text-slate-400 uppercase tracking-wide">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-50">
              {recipes.map(r => {
                const avail = getRecipeAvailability(r, stockMap)
                return (
                  <tr key={r.id} className="hover:bg-slate-50">
                    <td className="px-4 py-3 font-medium text-slate-900">{r.name}</td>
                    <td className="px-4 py-3 text-slate-700">{productMap[r.output_entity_id] ?? '\u2014'}</td>
                    <td className="px-4 py-3 font-bold text-slate-900">{r.output_quantity}</td>
                    <td className="px-4 py-3 text-slate-500">{r.components?.length ?? 0}</td>
                    <td className="px-4 py-3">
                      <AvailabilityBadge available={avail.available} missingCount={avail.missing.length} />
                    </td>
                    <td className="px-4 py-3">
                      {avail.warehouses.size > 0 ? (
                        <div className="flex flex-wrap gap-1">
                          {[...avail.warehouses].map(wId => (
                            <span key={wId} className="inline-flex items-center gap-0.5 rounded-full bg-slate-100 px-2 py-0.5 text-[10px] font-medium text-slate-600">
                              <Warehouse className="h-2.5 w-2.5" />
                              {warehouseMap[wId] ?? wId.slice(0, 6)}
                            </span>
                          ))}
                        </div>
                      ) : (
                        <span className="text-[11px] text-slate-400">\u2014</span>
                      )}
                    </td>
                    <td className="px-4 py-3">
                      {confirmDeleteId === r.id ? (
                        <div className="flex items-center gap-1">
                          <button
                            disabled={del.isPending}
                            onClick={async () => {
                              try {
                                await del.mutateAsync(r.id)
                                setConfirmDeleteId(null)
                              } catch (err: unknown) {
                                alert(err instanceof Error ? err.message : 'Error al eliminar')
                                setConfirmDeleteId(null)
                              }
                            }}
                            className="rounded-lg bg-red-600 px-2.5 py-1 text-[11px] font-semibold text-white hover:bg-red-700 disabled:opacity-60"
                          >
                            {del.isPending ? '...' : 'Confirmar'}
                          </button>
                          <button onClick={() => setConfirmDeleteId(null)}
                            className="rounded-lg border border-slate-200 px-2.5 py-1 text-[11px] text-slate-500 hover:bg-slate-50">
                            No
                          </button>
                        </div>
                      ) : (
                        <div className="flex gap-2 justify-end">
                          <button onClick={() => setSelectedId(r.id)} className="text-slate-400 hover:text-indigo-600" title="Ver">
                            <Eye className="h-4 w-4" />
                          </button>
                          <button onClick={() => setEditId(r.id)} className="text-slate-400 hover:text-amber-600" title="Editar">
                            <Pencil className="h-4 w-4" />
                          </button>
                          <button onClick={() => setConfirmDeleteId(r.id)} className="text-slate-400 hover:text-red-500" title="Eliminar">
                            <Trash2 className="h-4 w-4" />
                          </button>
                        </div>
                      )}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        )}
      </div>

      {showCreate && <CreateRecipeModal onClose={() => setShowCreate(false)} />}
      {editId && <EditRecipeModal recipeId={editId} onClose={() => setEditId(null)} />}
      {selectedId && <RecipeDrawer recipeId={selectedId} onClose={() => setSelectedId(null)} onEdit={setEditId} stockMap={stockMap} warehouseMap={warehouseMap} />}
    </div>
  )
}
