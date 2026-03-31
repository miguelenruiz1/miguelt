import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Send, Search, Loader2 } from 'lucide-react'
import { useProductionRuns, useProductionEmissions } from '@/hooks/useInventory'

export default function EmissionsPage() {
  const navigate = useNavigate()
  const { data: runsData, isLoading: runsLoading } = useProductionRuns({ limit: 200 })
  const runs = runsData?.items ?? []

  // Collect all run IDs that could have emissions
  const runsWithEmissions = runs.filter(r => ['in_progress', 'completed', 'closed'].includes(r.status))

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <Send className="h-6 w-6 text-amber-600" />
        <div>
          <h1 className="text-2xl font-bold">Emisiones de Material</h1>
          <p className="text-sm text-gray-500">Historial de componentes emitidos a produccion</p>
        </div>
      </div>

      {runsLoading ? (
        <div className="text-center py-16"><Loader2 className="h-6 w-6 animate-spin mx-auto text-gray-400" /></div>
      ) : runsWithEmissions.length === 0 ? (
        <div className="text-center py-16 text-gray-400">Sin emisiones registradas — emite componentes desde una orden liberada</div>
      ) : (
        <div className="space-y-3">
          {runsWithEmissions.map(run => (
            <RunEmissionsCard key={run.id} runId={run.id} runNumber={run.run_number} onNavigate={() => navigate(`/inventario/produccion`)} />
          ))}
        </div>
      )}
    </div>
  )
}

function RunEmissionsCard({ runId, runNumber, onNavigate }: { runId: string; runNumber: string; onNavigate: () => void }) {
  const { data: emissions } = useProductionEmissions(runId)
  if (!emissions || emissions.length === 0) return null

  return (
    <div className="bg-white rounded-xl border overflow-hidden">
      <div className="px-4 py-3 bg-gray-50 border-b">
        <button onClick={onNavigate} className="text-sm font-bold text-primary hover:underline">{runNumber}</button>
        <span className="text-xs text-gray-400 ml-2">{emissions.length} emision{emissions.length !== 1 ? 'es' : ''}</span>
      </div>
      <table className="w-full text-xs">
        <thead><tr className="text-gray-400 border-b">
          <th className="px-4 py-2 text-left"># Emision</th>
          <th className="px-4 py-2 text-left">Fecha</th>
          <th className="px-4 py-2 text-right">Componentes</th>
          <th className="px-4 py-2 text-right">Costo total</th>
          <th className="px-4 py-2 text-left">Ejecutado por</th>
        </tr></thead>
        <tbody>
          {emissions.map(em => {
            const totalCost = em.lines.reduce((s, l) => s + Number(l.total_cost), 0)
            return (
              <tr key={em.id} className="border-b border-gray-50 hover:bg-gray-50/50">
                <td className="px-4 py-2 font-mono font-medium">{em.emission_number}</td>
                <td className="px-4 py-2 text-gray-500">{new Date(em.emission_date).toLocaleString('es-CO')}</td>
                <td className="px-4 py-2 text-right">{em.lines.length}</td>
                <td className="px-4 py-2 text-right font-mono">${totalCost.toLocaleString('es-CO')}</td>
                <td className="px-4 py-2 text-gray-400">{em.performed_by?.slice(0, 8) ?? '—'}</td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
