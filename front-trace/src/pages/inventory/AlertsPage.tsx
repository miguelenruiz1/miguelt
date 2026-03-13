import { useState, useEffect, useRef } from 'react'
import { Bell, BellOff, RefreshCw, CheckCircle2, Eye } from 'lucide-react'
import { cn } from '@/lib/utils'
import { useStockAlerts, useUnreadAlertCount, useMarkAlertRead, useResolveAlert, useScanAlerts } from '@/hooks/useInventory'
import type { AlertType } from '@/types/inventory'

const ALERT_TYPE_CONFIG: Record<AlertType, { label: string; color: string }> = {
  low_stock: { label: 'Stock Bajo', color: 'bg-amber-50 text-amber-700' },
  out_of_stock: { label: 'Sin Stock', color: 'bg-red-50 text-red-600' },
  reorder_point: { label: 'Pto. Reorden', color: 'bg-blue-50 text-blue-700' },
}

const FILTER_OPTIONS = [
  { value: '', label: 'Todas' },
  { value: 'low_stock', label: 'Stock Bajo' },
  { value: 'out_of_stock', label: 'Sin Stock' },
  { value: 'reorder_point', label: 'Pto. Reorden' },
]

export function AlertsPage() {
  const [typeFilter, setTypeFilter] = useState('')
  const [showResolved, setShowResolved] = useState(false)

  const { data, isLoading } = useStockAlerts({ alert_type: typeFilter || undefined, is_resolved: showResolved ? undefined : false, limit: 200 })
  const { data: unread } = useUnreadAlertCount()
  const markRead = useMarkAlertRead()
  const resolve = useResolveAlert()
  const scan = useScanAlerts()

  const alerts = data?.items ?? []

  // Auto-scan on first visit when no alerts exist
  const autoScanned = useRef(false)
  useEffect(() => {
    if (!autoScanned.current && data && data.total === 0 && !scan.isPending) {
      autoScanned.current = true
      scan.mutate()
    }
  }, [data])

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 flex items-center gap-2">
            <Bell className="h-6 w-6 text-amber-500" /> Alertas de Stock
            {(unread?.count ?? 0) > 0 && (
              <span className="ml-2 px-2 py-0.5 bg-red-500 text-white text-xs font-bold rounded-full">{unread?.count}</span>
            )}
          </h1>
          <p className="text-sm text-slate-500 mt-1">Monitorea niveles criticos de inventario</p>
        </div>
        <button onClick={() => scan.mutate()} disabled={scan.isPending} className="flex items-center gap-2 px-4 py-2.5 text-sm font-semibold text-white bg-indigo-600 hover:bg-indigo-700 rounded-xl transition disabled:opacity-50">
          <RefreshCw className={cn('h-4 w-4', scan.isPending && 'animate-spin')} /> Escanear
        </button>
      </div>

      {scan.data && (
        <div className="bg-emerald-50 border border-emerald-200 rounded-xl px-4 py-3 text-sm text-emerald-700">
          Escaneo completo: {scan.data.created} nuevas alertas generadas.
        </div>
      )}

      <div className="flex flex-wrap items-center gap-3">
        <div className="flex gap-2">
          {FILTER_OPTIONS.map(f => (
            <button key={f.value} onClick={() => setTypeFilter(f.value)} className={cn('px-3 py-1.5 text-xs font-medium rounded-lg transition', typeFilter === f.value ? 'bg-indigo-100 text-indigo-700' : 'bg-slate-100 text-slate-600 hover:bg-slate-200')}>{f.label}</button>
          ))}
        </div>
        <label className="flex items-center gap-2 text-xs text-slate-500 ml-auto">
          <input type="checkbox" checked={showResolved} onChange={e => setShowResolved(e.target.checked)} className="rounded" />
          Mostrar resueltas
        </label>
      </div>

      {isLoading ? (
        <div className="flex justify-center py-20"><div className="animate-spin rounded-full h-6 w-6 border-b-2 border-indigo-600" /></div>
      ) : (
        <div className="space-y-3">
          {alerts.map(a => (
            <div key={a.id} className={cn('bg-white rounded-xl border border-slate-200/60 shadow-sm p-4 flex items-center gap-4', !a.is_read && 'ring-2 ring-indigo-200')}>
              <div className={cn('shrink-0 h-10 w-10 rounded-full flex items-center justify-center', ALERT_TYPE_CONFIG[a.alert_type]?.color ?? 'bg-slate-100')}>
                {a.alert_type === 'out_of_stock' ? <BellOff className="h-5 w-5" /> : <Bell className="h-5 w-5" />}
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-semibold text-slate-900">{a.message}</p>
                <div className="flex items-center gap-3 mt-1 text-xs text-slate-400">
                  <span className={cn('px-1.5 py-0.5 rounded font-semibold', ALERT_TYPE_CONFIG[a.alert_type]?.color)}>{ALERT_TYPE_CONFIG[a.alert_type]?.label}</span>
                  <span>Actual: {a.current_qty} | Umbral: {a.threshold_qty}</span>
                  {a.created_at && <span>{new Date(a.created_at).toLocaleString()}</span>}
                  {a.is_resolved && <span className="px-1.5 py-0.5 bg-emerald-50 text-emerald-600 rounded font-semibold">Resuelta</span>}
                </div>
              </div>
              <div className="flex gap-1 shrink-0">
                {!a.is_read && (
                  <button onClick={() => markRead.mutate(a.id)} title="Marcar leida" className="p-2 text-slate-400 hover:text-indigo-600 hover:bg-indigo-50 rounded-lg"><Eye className="h-4 w-4" /></button>
                )}
                {!a.is_resolved && (
                  <button onClick={() => resolve.mutate(a.id)} title="Resolver" className="p-2 text-slate-400 hover:text-emerald-600 hover:bg-emerald-50 rounded-lg"><CheckCircle2 className="h-4 w-4" /></button>
                )}
              </div>
            </div>
          ))}
          {alerts.length === 0 && <p className="text-center text-slate-400 py-12">Sin alertas</p>}
        </div>
      )}
    </div>
  )
}
