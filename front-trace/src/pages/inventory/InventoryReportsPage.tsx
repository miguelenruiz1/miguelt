import { useState } from 'react'
import { FileDown, Package, BarChart2, ArrowLeftRight, Loader2, CheckCircle, Truck, AlertTriangle, Hash, Layers, ShoppingCart } from 'lucide-react'
import { useDownloadReport } from '@/hooks/useInventory'
import { cn } from '@/lib/utils'

interface ReportCard {
  id: 'products' | 'stock' | 'movements' | 'suppliers' | 'events' | 'serials' | 'batches' | 'purchase-orders'
  label: string
  description: string
  icon: React.ElementType
  color: string
  bg: string
  hasDateFilter: boolean
}

const REPORTS: ReportCard[] = [
  {
    id: 'products',
    label: 'Reporte de Productos',
    description: 'Exporta todo el catálogo de productos con precios, categorías y configuración de stock.',
    icon: Package,
    color: 'text-indigo-600',
    bg: 'bg-indigo-100',
    hasDateFilter: false,
  },
  {
    id: 'stock',
    label: 'Reporte de Stock',
    description: 'Niveles actuales de inventario por producto y bodega, incluyendo cantidades reservadas.',
    icon: BarChart2,
    color: 'text-emerald-600',
    bg: 'bg-emerald-100',
    hasDateFilter: false,
  },
  {
    id: 'movements',
    label: 'Reporte de Movimientos',
    description: 'Historial completo de entradas, salidas, transferencias y ajustes. Filtrable por fecha.',
    icon: ArrowLeftRight,
    color: 'text-amber-600',
    bg: 'bg-amber-100',
    hasDateFilter: true,
  },
  {
    id: 'suppliers',
    label: 'Reporte de Proveedores',
    description: 'Listado de todos los proveedores con tipo, contacto, términos de pago y tiempo de entrega.',
    icon: Truck,
    color: 'text-orange-600',
    bg: 'bg-orange-100',
    hasDateFilter: false,
  },
  {
    id: 'events',
    label: 'Reporte de Eventos',
    description: 'Historial de eventos de inventario con tipo, severidad, estado e impactos.',
    icon: AlertTriangle,
    color: 'text-red-600',
    bg: 'bg-red-100',
    hasDateFilter: true,
  },
  {
    id: 'serials',
    label: 'Reporte de Seriales',
    description: 'Listado de números seriales con producto, estado, bodega y ubicación.',
    icon: Hash,
    color: 'text-cyan-600',
    bg: 'bg-cyan-100',
    hasDateFilter: false,
  },
  {
    id: 'batches',
    label: 'Reporte de Lotes',
    description: 'Listado de lotes con producto, cantidad, fechas de fabricación y expiración.',
    icon: Layers,
    color: 'text-purple-600',
    bg: 'bg-purple-100',
    hasDateFilter: false,
  },
  {
    id: 'purchase-orders',
    label: 'Reporte de Órdenes de Compra',
    description: 'Órdenes de compra con proveedor, estado, líneas de producto y totales. Filtrable por fecha.',
    icon: ShoppingCart,
    color: 'text-teal-600',
    bg: 'bg-teal-100',
    hasDateFilter: true,
  },
]

function ReportCardItem({ report }: { report: ReportCard }) {
  const download = useDownloadReport()
  const [dateFrom, setDateFrom] = useState('')
  const [dateTo, setDateTo] = useState('')
  const [success, setSuccess] = useState(false)

  async function handleDownload() {
    await download.mutateAsync({
      type: report.id,
      dateFrom: dateFrom || undefined,
      dateTo: dateTo || undefined,
    })
    setSuccess(true)
    setTimeout(() => setSuccess(false), 3000)
  }

  return (
    <div className="bg-white rounded-2xl border border-slate-100 shadow-sm p-6 space-y-4">
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-3">
          <div className={cn('flex h-10 w-10 items-center justify-center rounded-xl', report.bg)}>
            <report.icon className={cn('h-5 w-5', report.color)} />
          </div>
          <div>
            <h3 className="font-semibold text-slate-800">{report.label}</h3>
            <p className="text-xs text-slate-500 mt-0.5 max-w-sm">{report.description}</p>
          </div>
        </div>
        <span className="text-xs text-slate-400 bg-slate-50 rounded-lg px-2 py-1">CSV</span>
      </div>

      {report.hasDateFilter && (
        <div className="flex items-center gap-3">
          <div className="flex-1">
            <label className="text-xs font-medium text-slate-500 mb-1 block">Desde</label>
            <input
              type="date"
              value={dateFrom}
              onChange={e => setDateFrom(e.target.value)}
              className="w-full rounded-lg border border-slate-200 px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400"
            />
          </div>
          <div className="flex-1">
            <label className="text-xs font-medium text-slate-500 mb-1 block">Hasta</label>
            <input
              type="date"
              value={dateTo}
              onChange={e => setDateTo(e.target.value)}
              className="w-full rounded-lg border border-slate-200 px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400"
            />
          </div>
        </div>
      )}

      <button
        onClick={handleDownload}
        disabled={download.isPending}
        className={cn(
          'w-full flex items-center justify-center gap-2 rounded-xl px-4 py-2.5 text-sm font-semibold transition-all',
          success
            ? 'bg-emerald-600 text-white'
            : 'bg-indigo-600 text-white hover:bg-indigo-700 disabled:opacity-50',
        )}
      >
        {download.isPending ? (
          <>
            <Loader2 className="h-4 w-4 animate-spin" />
            Descargando...
          </>
        ) : success ? (
          <>
            <CheckCircle className="h-4 w-4" />
            ¡Descargado!
          </>
        ) : (
          <>
            <FileDown className="h-4 w-4" />
            Descargar CSV
          </>
        )}
      </button>

      {download.isError && (
        <p className="text-xs text-red-600 bg-red-50 rounded-lg px-3 py-1.5">
          Error al descargar. Verifica que hay datos disponibles.
        </p>
      )}
    </div>
  )
}

export function InventoryReportsPage() {
  return (
    <div className="p-8 space-y-6 max-w-4xl mx-auto">
      {/* Header */}
      <div className="flex items-center gap-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-amber-100">
          <FileDown className="h-5 w-5 text-amber-600" />
        </div>
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Reportes</h1>
          <p className="text-sm text-slate-500">Descarga reportes de tu inventario en formato CSV</p>
        </div>
      </div>

      {/* Info banner */}
      <div className="rounded-xl bg-blue-50 border border-blue-100 px-4 py-3 text-sm text-blue-700">
        Los reportes se generan en tiempo real con los datos actuales de tu inventario.
        Puedes abrirlos en Excel, Google Sheets o cualquier hoja de cálculo.
      </div>

      {/* Reports grid */}
      <div className="grid grid-cols-1 gap-4">
        {REPORTS.map(report => (
          <ReportCardItem key={report.id} report={report} />
        ))}
      </div>
    </div>
  )
}
