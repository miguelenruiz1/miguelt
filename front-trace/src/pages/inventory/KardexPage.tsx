import { useState } from 'react'
import { BookOpen, Search } from 'lucide-react'
import { useKardex, useProducts, useWarehouses } from '@/hooks/useInventory'

export function KardexPage() {
  const [productId, setProductId] = useState('')
  const [warehouseId, setWarehouseId] = useState('')

  const { data: productsData } = useProducts()
  const { data: warehouses = [] } = useWarehouses()
  const { data: entries = [], isLoading } = useKardex(productId, warehouseId || undefined)

  const products = productsData?.items ?? []

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-900 flex items-center gap-2"><BookOpen className="h-6 w-6 text-indigo-500" /> Kardex</h1>
        <p className="text-sm text-slate-500 mt-1">Historial valorizado de movimientos por producto</p>
      </div>

      <div className="flex flex-wrap gap-3">
        <select value={productId} onChange={e => setProductId(e.target.value)} className="min-w-[240px] rounded-xl border border-slate-200 px-3 py-2.5 text-sm focus:ring-2 focus:ring-indigo-400 outline-none">
          <option value="">Seleccionar producto...</option>
          {products.map(p => <option key={p.id} value={p.id}>{p.sku} — {p.name}</option>)}
        </select>
        <select value={warehouseId} onChange={e => setWarehouseId(e.target.value)} className="rounded-xl border border-slate-200 px-3 py-2.5 text-sm focus:ring-2 focus:ring-indigo-400 outline-none">
          <option value="">Todas las bodegas</option>
          {warehouses.map(w => <option key={w.id} value={w.id}>{w.name}</option>)}
        </select>
      </div>

      {!productId ? (
        <div className="text-center py-20 text-slate-400">
          <Search className="h-10 w-10 mx-auto mb-3 text-slate-300" />
          <p>Selecciona un producto para ver su kardex</p>
        </div>
      ) : isLoading ? (
        <div className="flex justify-center py-20"><div className="animate-spin rounded-full h-6 w-6 border-b-2 border-indigo-600" /></div>
      ) : (
        <div className="bg-white rounded-2xl border border-slate-200/60 shadow-sm overflow-hidden">
          {/* Mobile cards */}
          <div className="space-y-3 p-4 md:hidden">
            {entries.length === 0 ? (
              <div className="py-8 text-center text-slate-400 text-sm">Sin movimientos para este producto</div>
            ) : entries.map((e, i) => (
              <div key={e.movement_id + i} className="rounded-xl border border-slate-200 bg-white p-4 space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-medium text-slate-700">{e.type}</span>
                  <span className="text-xs text-slate-400">{e.date ? new Date(e.date).toLocaleDateString() : '—'}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-xs text-slate-500">{e.reference ?? '—'}</span>
                  <span className="text-sm font-mono font-bold text-slate-900">{e.quantity > 0 ? '+' : ''}{e.quantity}</span>
                </div>
                <div className="grid grid-cols-2 gap-2 text-xs">
                  <div className="flex justify-between">
                    <span className="text-slate-400">Costo Unit.</span>
                    <span className="font-mono">${(e.unit_cost ?? 0).toLocaleString()}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-400">Costo Prom.</span>
                    <span className="font-mono text-indigo-600">${(e.avg_cost ?? 0).toLocaleString()}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-400">Saldo</span>
                    <span className="font-bold">{e.balance ?? 0}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-400">Valor</span>
                    <span className="font-mono text-slate-500">{e.value != null ? `$${e.value.toLocaleString()}` : '—'}</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
          {/* Desktop table */}
          <div className="hidden md:block overflow-x-auto">
          <table className="w-full text-sm min-w-[600px]">
            <thead><tr className="bg-slate-50 text-left text-xs font-semibold text-slate-500 uppercase">
              <th className="px-6 py-3">Fecha</th>
              <th className="px-6 py-3">Tipo</th>
              <th className="px-6 py-3">Referencia</th>
              <th className="px-6 py-3 text-right">Cantidad</th>
              <th className="px-6 py-3 text-right">Costo Unit.</th>
              <th className="px-6 py-3 text-right">Costo Prom.</th>
              <th className="px-6 py-3 text-right">Saldo</th>
              <th className="px-6 py-3 text-right">Valor</th>
            </tr></thead>
            <tbody className="divide-y divide-slate-100">
              {entries.map((e, i) => (
                <tr key={e.movement_id + i} className="hover:bg-slate-50/60">
                  <td className="px-6 py-3 text-xs text-slate-500">{e.date ? new Date(e.date).toLocaleDateString() : '—'}</td>
                  <td className="px-6 py-3 text-xs">{e.type}</td>
                  <td className="px-6 py-3 text-xs text-slate-400">{e.reference ?? '—'}</td>
                  <td className="px-6 py-3 text-right font-mono">{e.quantity > 0 ? '+' : ''}{e.quantity}</td>
                  <td className="px-6 py-3 text-right font-mono">${(e.unit_cost ?? 0).toLocaleString()}</td>
                  <td className="px-6 py-3 text-right font-mono text-indigo-600">${(e.avg_cost ?? 0).toLocaleString()}</td>
                  <td className="px-6 py-3 text-right font-bold">{e.balance ?? 0}</td>
                  <td className="px-6 py-3 text-right font-mono text-slate-500">{e.value != null ? `$${e.value.toLocaleString()}` : '—'}</td>
                </tr>
              ))}
              {entries.length === 0 && <tr><td colSpan={8} className="px-6 py-12 text-center text-slate-400">Sin movimientos para este producto</td></tr>}
            </tbody>
          </table>
          </div>
        </div>
      )}
    </div>
  )
}
