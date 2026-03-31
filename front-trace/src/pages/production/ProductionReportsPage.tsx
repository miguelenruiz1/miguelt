import { useState } from 'react'
import { BarChart3, FileText, DollarSign, AlertTriangle, TrendingDown } from 'lucide-react'
import { useProductionRuns, useRecipes } from '@/hooks/useInventory'
import { cn } from '@/lib/utils'

const TABS = [
  { key: 'open', label: 'Ordenes abiertas', icon: FileText },
  { key: 'cost', label: 'Costos por receta', icon: DollarSign },
  { key: 'variance', label: 'Variaciones', icon: AlertTriangle },
]

export default function ProductionReportsPage() {
  const [tab, setTab] = useState('open')
  const { data: runsData } = useProductionRuns({ limit: 500 })
  const { data: recipesData } = useRecipes()
  const runs = runsData?.items ?? []
  const recipes = Array.isArray(recipesData) ? recipesData : recipesData?.items ?? []
  const recipeMap = new Map(recipes.map(r => [r.id, r]))

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <BarChart3 className="h-6 w-6 text-indigo-600" />
        <div>
          <h1 className="text-2xl font-bold">Reportes de Produccion</h1>
          <p className="text-sm text-gray-500">Ordenes abiertas, costos y variaciones</p>
        </div>
      </div>

      <div className="flex gap-2">
        {TABS.map(t => (
          <button key={t.key} onClick={() => setTab(t.key)}
            className={cn('inline-flex items-center gap-1.5 px-4 py-2 text-sm font-medium rounded-lg border transition-colors',
              tab === t.key ? 'bg-gray-900 text-white border-gray-900' : 'bg-white text-gray-600 border-gray-200 hover:border-gray-400'
            )}>
            <t.icon className="h-4 w-4" /> {t.label}
          </button>
        ))}
      </div>

      {/* Open Orders */}
      {tab === 'open' && (
        <div className="bg-white rounded-xl border overflow-hidden">
          <table className="w-full text-sm">
            <thead><tr className="bg-gray-50 border-b text-xs text-gray-500 uppercase">
              <th className="px-4 py-3 text-left"># Orden</th>
              <th className="px-4 py-3 text-left">Receta</th>
              <th className="px-4 py-3 text-left">Estado</th>
              <th className="px-4 py-3 text-left">Tipo</th>
              <th className="px-4 py-3 text-right">Multiplicador</th>
              <th className="px-4 py-3 text-right">Prioridad</th>
              <th className="px-4 py-3 text-left">Creada</th>
            </tr></thead>
            <tbody>
              {runs.filter(r => ['planned', 'released', 'in_progress'].includes(r.status)).map(run => (
                <tr key={run.id} className="border-b border-gray-50 hover:bg-gray-50/50">
                  <td className="px-4 py-2 font-mono text-xs font-medium">{run.run_number}</td>
                  <td className="px-4 py-2 text-xs">{recipeMap.get(run.recipe_id)?.name ?? run.recipe_id.slice(0, 8)}</td>
                  <td className="px-4 py-2"><StatusBadge status={run.status} /></td>
                  <td className="px-4 py-2 text-xs text-gray-500">{run.order_type}</td>
                  <td className="px-4 py-2 text-right font-mono">{run.multiplier}x</td>
                  <td className="px-4 py-2 text-right">{run.priority}</td>
                  <td className="px-4 py-2 text-xs text-gray-400">{new Date(run.created_at).toLocaleDateString('es-CO')}</td>
                </tr>
              ))}
              {runs.filter(r => ['planned', 'released', 'in_progress'].includes(r.status)).length === 0 && (
                <tr><td colSpan={7} className="px-4 py-10 text-center text-gray-400">Sin ordenes abiertas</td></tr>
              )}
            </tbody>
          </table>
        </div>
      )}

      {/* Cost by Recipe */}
      {tab === 'cost' && (
        <div className="bg-white rounded-xl border overflow-hidden">
          <table className="w-full text-sm">
            <thead><tr className="bg-gray-50 border-b text-xs text-gray-500 uppercase">
              <th className="px-4 py-3 text-left">Receta</th>
              <th className="px-4 py-3 text-right">Ordenes</th>
              <th className="px-4 py-3 text-right">Unidades producidas</th>
              <th className="px-4 py-3 text-right">Costo total</th>
              <th className="px-4 py-3 text-right">Costo promedio/unidad</th>
              <th className="px-4 py-3 text-right">Costo estandar</th>
            </tr></thead>
            <tbody>
              {recipes.filter(r => r.is_active && r.bom_type === 'production').map(recipe => {
                const recipeRuns = runs.filter(r => r.recipe_id === recipe.id && (r.status === 'completed' || r.status === 'closed'))
                const totalOutput = recipeRuns.reduce((s, r) => s + Number(r.actual_output_quantity ?? 0), 0)
                const totalCost = recipeRuns.reduce((s, r) => s + Number(r.total_production_cost ?? 0), 0)
                const avgCost = totalOutput > 0 ? totalCost / totalOutput : 0
                return (
                  <tr key={recipe.id} className="border-b border-gray-50 hover:bg-gray-50/50">
                    <td className="px-4 py-2 font-medium">{recipe.name}</td>
                    <td className="px-4 py-2 text-right">{recipeRuns.length}</td>
                    <td className="px-4 py-2 text-right font-mono">{totalOutput.toLocaleString('es-CO')}</td>
                    <td className="px-4 py-2 text-right font-mono">${totalCost.toLocaleString('es-CO')}</td>
                    <td className="px-4 py-2 text-right font-mono font-bold">${avgCost.toFixed(2)}</td>
                    <td className="px-4 py-2 text-right font-mono text-gray-400">${Number(recipe.standard_cost).toFixed(2)}</td>
                  </tr>
                )
              })}
              {recipes.filter(r => r.is_active && r.bom_type === 'production').length === 0 && (
                <tr><td colSpan={6} className="px-4 py-10 text-center text-gray-400">Sin recetas de produccion</td></tr>
              )}
            </tbody>
          </table>
        </div>
      )}

      {/* Variance */}
      {tab === 'variance' && (
        <div className="bg-white rounded-xl border overflow-hidden">
          <table className="w-full text-sm">
            <thead><tr className="bg-gray-50 border-b text-xs text-gray-500 uppercase">
              <th className="px-4 py-3 text-left"># Orden</th>
              <th className="px-4 py-3 text-left">Receta</th>
              <th className="px-4 py-3 text-right">Producido</th>
              <th className="px-4 py-3 text-right">Costo real</th>
              <th className="px-4 py-3 text-right">Costo estandar</th>
              <th className="px-4 py-3 text-right">Variacion</th>
            </tr></thead>
            <tbody>
              {runs.filter(r => r.status === 'closed').map(run => {
                const recipe = recipeMap.get(run.recipe_id)
                const standardTotal = Number(recipe?.standard_cost ?? 0) * Number(run.actual_output_quantity ?? 0)
                const variance = Number(run.variance_amount ?? 0)
                return (
                  <tr key={run.id} className="border-b border-gray-50 hover:bg-gray-50/50">
                    <td className="px-4 py-2 font-mono text-xs font-medium">{run.run_number}</td>
                    <td className="px-4 py-2 text-xs">{recipe?.name ?? '—'}</td>
                    <td className="px-4 py-2 text-right font-mono">{run.actual_output_quantity ?? '—'}</td>
                    <td className="px-4 py-2 text-right font-mono">${Number(run.total_production_cost ?? 0).toLocaleString('es-CO')}</td>
                    <td className="px-4 py-2 text-right font-mono text-gray-400">${standardTotal.toLocaleString('es-CO')}</td>
                    <td className={cn('px-4 py-2 text-right font-mono font-bold',
                      variance === 0 ? 'text-emerald-600' : variance > 0 ? 'text-red-600' : 'text-blue-600'
                    )}>
                      {variance > 0 ? '+' : ''}{variance.toLocaleString('es-CO')}
                    </td>
                  </tr>
                )
              })}
              {runs.filter(r => r.status === 'closed').length === 0 && (
                <tr><td colSpan={6} className="px-4 py-10 text-center text-gray-400">Sin ordenes cerradas con variaciones</td></tr>
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

function StatusBadge({ status }: { status: string }) {
  const colors: Record<string, string> = {
    planned: 'bg-slate-100 text-slate-600',
    released: 'bg-blue-100 text-blue-700',
    in_progress: 'bg-amber-100 text-amber-700',
  }
  const labels: Record<string, string> = {
    planned: 'Planificada',
    released: 'Liberada',
    in_progress: 'En produccion',
  }
  return (
    <span className={cn('px-2 py-0.5 rounded-full text-[10px] font-semibold', colors[status] ?? 'bg-gray-100 text-gray-600')}>
      {labels[status] ?? status}
    </span>
  )
}
