import { useState } from 'react'
import { Search, AlertTriangle, CheckCircle2, ShoppingCart, Package, Loader2, DollarSign, Factory } from 'lucide-react'
import { useMRPExplode, useRecipes, useWarehouses } from '@/hooks/useInventory'
import { useToast } from '@/store/toast'
import { cn } from '@/lib/utils'
import type { MRPResult } from '@/types/inventory'

export default function MRPPage() {
  const { data: recipesData } = useRecipes()
  const { data: whData } = useWarehouses()
  const mrpMut = useMRPExplode()
  const toast = useToast()
  const recipes = Array.isArray(recipesData) ? recipesData : recipesData?.items ?? []
  const warehouses = Array.isArray(whData) ? whData : whData?.items ?? []

  const [form, setForm] = useState({ recipe_id: '', quantity: '1', warehouse_id: '', auto_create_po: false })
  const [result, setResult] = useState<MRPResult | null>(null)

  async function handleExplode() {
    if (!form.recipe_id || !form.warehouse_id) return
    try {
      const r = await mrpMut.mutateAsync({
        recipe_id: form.recipe_id,
        quantity: form.quantity,
        warehouse_id: form.warehouse_id,
        consider_reserved: true,
        auto_create_po: form.auto_create_po,
      })
      setResult(r)
      if (r.purchase_orders_created.length > 0) {
        toast.success(`${r.purchase_orders_created.length} OC borrador(es) creada(s)`)
      }
    } catch (e: any) { toast.error(e.message) }
  }

  const inputCls = "w-full bg-muted border border-border rounded-xl px-3 py-2.5 text-sm outline-none focus:bg-card focus:ring-2 focus:ring-gray-900/10"

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <Search className="h-6 w-6 text-indigo-600" />
        <div>
          <h1 className="text-2xl font-bold">MRP — Planificacion de Necesidades</h1>
          <p className="text-sm text-muted-foreground">Explota la BOM, verifica stock y genera sugerencias de compra</p>
        </div>
      </div>

      {/* Form */}
      <div className="bg-card rounded-xl border p-6">
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <div>
            <label className="text-xs text-muted-foreground">Receta *</label>
            <select value={form.recipe_id} onChange={e => setForm(f => ({...f, recipe_id: e.target.value}))} className={inputCls}>
              <option value="">Seleccionar...</option>
              {recipes.filter(r => r.is_active).map(r => <option key={r.id} value={r.id}>{r.name}</option>)}
            </select>
          </div>
          <div>
            <label className="text-xs text-muted-foreground">Cantidad a producir *</label>
            <input type="number" min="1" step="1" value={form.quantity} onChange={e => setForm(f => ({...f, quantity: e.target.value}))} className={inputCls} />
          </div>
          <div>
            <label className="text-xs text-muted-foreground">Bodega *</label>
            <select value={form.warehouse_id} onChange={e => setForm(f => ({...f, warehouse_id: e.target.value}))} className={inputCls}>
              <option value="">Seleccionar...</option>
              {warehouses.map(w => <option key={w.id} value={w.id}>{w.name}</option>)}
            </select>
          </div>
          <div className="flex items-end gap-3">
            <label className="flex items-center gap-2 text-sm text-muted-foreground pb-2">
              <input type="checkbox" checked={form.auto_create_po} onChange={e => setForm(f => ({...f, auto_create_po: e.target.checked}))} className="rounded" />
              Auto-crear OC
            </label>
            <button onClick={handleExplode} disabled={mrpMut.isPending || !form.recipe_id || !form.warehouse_id}
              className="px-5 py-2.5 bg-indigo-600 text-white text-sm font-semibold rounded-xl hover:bg-indigo-700 disabled:opacity-50 whitespace-nowrap">
              {mrpMut.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : 'Explotar BOM'}
            </button>
          </div>
        </div>
      </div>

      {/* Results */}
      {result && (
        <div className="space-y-4">
          {/* Summary */}
          <div className="grid grid-cols-3 gap-4">
            <div className="bg-card rounded-xl border p-4">
              <p className="text-xs text-muted-foreground mb-1">Receta</p>
              <p className="text-lg font-bold">{result.recipe_name}</p>
            </div>
            <div className="bg-card rounded-xl border p-4">
              <p className="text-xs text-muted-foreground mb-1">Cantidad a producir</p>
              <p className="text-lg font-bold">{result.output_quantity}</p>
            </div>
            <div className="bg-card rounded-xl border p-4">
              <p className="text-xs text-muted-foreground mb-1">Costo estimado total</p>
              <p className="text-lg font-bold text-indigo-600">${Number(result.total_estimated_cost).toLocaleString('es-CO')}</p>
            </div>
          </div>

          {/* POs created */}
          {result.purchase_orders_created.length > 0 && (
            <div className="bg-emerald-50 border border-emerald-200 rounded-xl p-4 flex items-center gap-3">
              <ShoppingCart className="h-5 w-5 text-emerald-600" />
              <div>
                <p className="text-sm font-semibold text-emerald-800">{result.purchase_orders_created.length} Orden(es) de Compra creada(s) en borrador</p>
                <p className="text-xs text-emerald-600">Revisa en Compras para aprobar y enviar</p>
              </div>
            </div>
          )}

          {/* Make suggestions (sub-assemblies) */}
          {result.make_suggestions.length > 0 && (
            <div className="bg-card rounded-xl border overflow-hidden">
              <div className="px-4 py-3 bg-purple-50 border-b flex items-center gap-2">
                <Factory className="h-4 w-4 text-purple-600" />
                <span className="text-sm font-bold text-purple-800">Sub-ensambles a fabricar</span>
                <span className="text-xs text-purple-500">({result.make_suggestions.length} componentes tienen su propia BOM)</span>
              </div>
              <table className="w-full text-sm">
                <thead><tr className="bg-muted border-b text-xs text-muted-foreground uppercase">
                  <th className="px-4 py-3 text-left">Componente</th>
                  <th className="px-4 py-3 text-left">Receta</th>
                  <th className="px-4 py-3 text-right">Requerido</th>
                  <th className="px-4 py-3 text-right">Disponible</th>
                  <th className="px-4 py-3 text-right">Producir</th>
                </tr></thead>
                <tbody>
                  {result.make_suggestions.map((line, i) => (
                    <tr key={i} className="border-b border-gray-50 bg-purple-50/30">
                      <td className="px-4 py-2.5 font-medium">{line.component_name ?? line.component_entity_id.slice(0, 12)}</td>
                      <td className="px-4 py-2.5 text-xs text-purple-600">{line.sub_recipe_name ?? '—'}</td>
                      <td className="px-4 py-2.5 text-right font-mono">{Number(line.required_qty).toFixed(2)}</td>
                      <td className="px-4 py-2.5 text-right font-mono">{Number(line.available_qty).toFixed(2)}</td>
                      <td className="px-4 py-2.5 text-right font-mono font-bold text-purple-700">{Number(line.shortage).toFixed(2)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {/* Buy Lines (materials to purchase) */}
          <div className="bg-card rounded-xl border overflow-hidden">
            {result.lines.length > 0 && (
              <div className="px-4 py-3 bg-blue-50 border-b flex items-center gap-2">
                <ShoppingCart className="h-4 w-4 text-blue-600" />
                <span className="text-sm font-bold text-blue-800">Materiales a comprar</span>
              </div>
            )}
            <table className="w-full text-sm">
              <thead><tr className="bg-muted border-b text-xs text-muted-foreground uppercase">
                <th className="px-4 py-3 text-left">Componente</th>
                <th className="px-4 py-3 text-right">Requerido</th>
                <th className="px-4 py-3 text-right">Disponible</th>
                <th className="px-4 py-3 text-right">Faltante</th>
                <th className="px-4 py-3 text-right">Sugerir compra</th>
                <th className="px-4 py-3 text-right">Costo est.</th>
                <th className="px-4 py-3 text-center">Estado</th>
              </tr></thead>
              <tbody>
                {result.lines.map((line, i) => {
                  const shortage = Number(line.shortage)
                  return (
                    <tr key={i} className={cn('border-b border-gray-50', shortage > 0 && 'bg-red-50/30')}>
                      <td className="px-4 py-2.5 font-medium">{line.component_name ?? line.component_entity_id.slice(0, 12)}</td>
                      <td className="px-4 py-2.5 text-right font-mono">{Number(line.required_qty).toFixed(2)}</td>
                      <td className="px-4 py-2.5 text-right font-mono">{Number(line.available_qty).toFixed(2)}</td>
                      <td className="px-4 py-2.5 text-right font-mono font-bold">{shortage > 0 ? shortage.toFixed(2) : '—'}</td>
                      <td className="px-4 py-2.5 text-right font-mono">{shortage > 0 ? Number(line.suggested_order_qty).toFixed(2) : '—'}</td>
                      <td className="px-4 py-2.5 text-right font-mono text-muted-foreground">${Number(line.estimated_unit_cost).toFixed(2)}</td>
                      <td className="px-4 py-2.5 text-center">
                        {shortage > 0 ? (
                          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-red-100 text-red-700">
                            <AlertTriangle className="h-2.5 w-2.5" /> Faltante
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-emerald-100 text-emerald-700">
                            <CheckCircle2 className="h-2.5 w-2.5" /> OK
                          </span>
                        )}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  )
}
