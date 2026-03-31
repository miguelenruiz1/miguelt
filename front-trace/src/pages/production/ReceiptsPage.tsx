import { useNavigate } from 'react-router-dom'
import { PackageCheck, Loader2 } from 'lucide-react'
import { useProductionRuns, useProductionReceipts } from '@/hooks/useInventory'

export default function ReceiptsPage() {
  const navigate = useNavigate()
  const { data: runsData, isLoading } = useProductionRuns({ limit: 200 })
  const runs = runsData?.items ?? []
  const runsWithReceipts = runs.filter(r => ['completed', 'closed'].includes(r.status))

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <PackageCheck className="h-6 w-6 text-emerald-600" />
        <div>
          <h1 className="text-2xl font-bold">Recibos de Produccion</h1>
          <p className="text-sm text-gray-500">Historial de productos terminados recibidos</p>
        </div>
      </div>

      {isLoading ? (
        <div className="text-center py-16"><Loader2 className="h-6 w-6 animate-spin mx-auto text-gray-400" /></div>
      ) : runsWithReceipts.length === 0 ? (
        <div className="text-center py-16 text-gray-400">Sin recibos registrados — recibe productos desde una orden en produccion</div>
      ) : (
        <div className="space-y-3">
          {runsWithReceipts.map(run => (
            <RunReceiptsCard key={run.id} runId={run.id} runNumber={run.run_number} onNavigate={() => navigate(`/inventario/produccion`)} />
          ))}
        </div>
      )}
    </div>
  )
}

function RunReceiptsCard({ runId, runNumber, onNavigate }: { runId: string; runNumber: string; onNavigate: () => void }) {
  const { data: receipts } = useProductionReceipts(runId)
  if (!receipts || receipts.length === 0) return null

  return (
    <div className="bg-white rounded-xl border overflow-hidden">
      <div className="px-4 py-3 bg-gray-50 border-b">
        <button onClick={onNavigate} className="text-sm font-bold text-primary hover:underline">{runNumber}</button>
        <span className="text-xs text-gray-400 ml-2">{receipts.length} recibo{receipts.length !== 1 ? 's' : ''}</span>
      </div>
      <table className="w-full text-xs">
        <thead><tr className="text-gray-400 border-b">
          <th className="px-4 py-2 text-left"># Recibo</th>
          <th className="px-4 py-2 text-left">Fecha</th>
          <th className="px-4 py-2 text-right">Cantidad</th>
          <th className="px-4 py-2 text-right">Costo unitario</th>
          <th className="px-4 py-2 text-right">Costo total</th>
          <th className="px-4 py-2 text-center">Completo</th>
        </tr></thead>
        <tbody>
          {receipts.map(rc => (
            rc.lines.map(l => (
              <tr key={l.id} className="border-b border-gray-50 hover:bg-gray-50/50">
                <td className="px-4 py-2 font-mono font-medium">{rc.receipt_number}</td>
                <td className="px-4 py-2 text-gray-500">{new Date(rc.receipt_date).toLocaleString('es-CO')}</td>
                <td className="px-4 py-2 text-right font-mono font-bold">{l.received_quantity}</td>
                <td className="px-4 py-2 text-right font-mono">${Number(l.unit_cost).toFixed(4)}</td>
                <td className="px-4 py-2 text-right font-mono">${Number(l.total_cost).toLocaleString('es-CO')}</td>
                <td className="px-4 py-2 text-center">{l.is_complete ? '✓' : '—'}</td>
              </tr>
            ))
          ))}
        </tbody>
      </table>
    </div>
  )
}
