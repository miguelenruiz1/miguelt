import { useState } from 'react'
import {
  Download, Box, Warehouse, ArrowLeftRight, Loader2, Check,
  Users2, Zap, Fingerprint, Grid3x3, ShoppingCart,
  TrendingUp, FileText, FileSpreadsheet,
} from 'lucide-react'
import { useDownloadReport, useFeatureToggles } from '@/hooks/useInventory'
import { inventoryPnLApi } from '@/lib/inventory-api'
import { cn } from '@/lib/utils'

type ReportId = 'products' | 'stock' | 'movements' | 'suppliers' | 'events' | 'serials' | 'batches' | 'purchase-orders' | 'pnl-csv' | 'pnl-pdf'

interface ReportDef {
  id: ReportId
  label: string
  desc: string
  icon: React.ElementType
  gradient: string
  iconBg: string
  hasDateFilter: boolean
  format: 'csv' | 'pdf' | 'zip'
  feature?: string  // if set, only show when this feature toggle is active
}

const REPORTS: ReportDef[] = [
  {
    id: 'pnl-pdf',
    label: 'Rentabilidad PDF',
    desc: 'Reporte ejecutivo de P&L con graficas y analisis por producto',
    icon: TrendingUp,
    gradient: 'from-primary to-violet-500',
    iconBg: 'bg-white/20',
    hasDateFilter: true,
    format: 'pdf',
  },
  {
    id: 'pnl-csv',
    label: 'Rentabilidad CSV',
    desc: 'Datos de compras, ventas y utilidad en formato tabular',
    icon: TrendingUp,
    gradient: 'from-violet-500 to-purple-500',
    iconBg: 'bg-white/20',
    hasDateFilter: true,
    format: 'zip',
  },
  {
    id: 'products',
    label: 'Catalogo de Productos',
    desc: 'Todo tu catalogo con precios, categorias y stock',
    icon: Box,
    gradient: 'from-blue-500 to-cyan-500',
    iconBg: 'bg-white/20',
    hasDateFilter: false,
    format: 'csv',
  },
  {
    id: 'stock',
    label: 'Inventario Actual',
    desc: 'Niveles de stock por producto y bodega en tiempo real',
    icon: Warehouse,
    gradient: 'from-emerald-500 to-teal-500',
    iconBg: 'bg-white/20',
    hasDateFilter: false,
    format: 'csv',
  },
  {
    id: 'movements',
    label: 'Movimientos',
    desc: 'Entradas, salidas, transferencias y ajustes',
    icon: ArrowLeftRight,
    gradient: 'from-amber-500 to-orange-500',
    iconBg: 'bg-white/20',
    hasDateFilter: true,
    format: 'csv',
  },
  {
    id: 'purchase-orders',
    label: 'Ordenes de Compra',
    desc: 'OC con proveedor, estado, lineas y totales',
    icon: ShoppingCart,
    gradient: 'from-teal-500 to-emerald-500',
    iconBg: 'bg-white/20',
    hasDateFilter: true,
    format: 'csv',
  },
  {
    id: 'suppliers',
    label: 'Socios Comerciales',
    desc: 'Proveedores y clientes con contacto y condiciones',
    icon: Users2,
    gradient: 'from-pink-500 to-rose-500',
    iconBg: 'bg-white/20',
    hasDateFilter: false,
    format: 'csv',
  },
  {
    id: 'events',
    label: 'Eventos',
    desc: 'Incidentes con severidad, estado e impactos',
    icon: Zap,
    gradient: 'from-red-500 to-orange-500',
    iconBg: 'bg-white/20',
    hasDateFilter: true,
    format: 'csv',
    feature: 'eventos',
  },
  {
    id: 'serials',
    label: 'Seriales',
    desc: 'Numeros de serie con estado y ubicacion',
    icon: Fingerprint,
    gradient: 'from-cyan-500 to-blue-500',
    iconBg: 'bg-white/20',
    hasDateFilter: false,
    format: 'csv',
    feature: 'seriales',
  },
  {
    id: 'batches',
    label: 'Lotes',
    desc: 'Lotes con fechas de fabricacion y vencimiento',
    icon: Grid3x3,
    gradient: 'from-purple-500 to-primary',
    iconBg: 'bg-white/20',
    hasDateFilter: false,
    format: 'csv',
    feature: 'lotes',
  },
]

const FORMAT_LABELS: Record<string, { label: string; icon: React.ElementType }> = {
  csv: { label: 'CSV', icon: FileSpreadsheet },
  zip: { label: 'ZIP', icon: FileSpreadsheet },
  pdf: { label: 'PDF', icon: FileText },
}

function ReportCard({ report }: { report: ReportDef }) {
  const download = useDownloadReport()
  const [dateFrom, setDateFrom] = useState('')
  const [dateTo, setDateTo] = useState('')
  const [status, setStatus] = useState<'idle' | 'loading' | 'done'>('idle')

  async function handleDownload() {
    setStatus('loading')
    try {
      if (report.id === 'pnl-pdf') {
        await inventoryPnLApi.downloadPdf(dateFrom || undefined, dateTo || undefined)
      } else if (report.id === 'pnl-csv') {
        await inventoryPnLApi.downloadCsv(dateFrom || undefined, dateTo || undefined)
      } else {
        await download.mutateAsync({ type: report.id, dateFrom: dateFrom || undefined, dateTo: dateTo || undefined })
      }
      setStatus('done')
      setTimeout(() => setStatus('idle'), 2500)
    } catch {
      setStatus('idle')
    }
  }

  const Icon = report.icon
  const fmt = FORMAT_LABELS[report.format]

  return (
    <div className="group relative bg-white rounded-2xl border border-gray-100 overflow-hidden hover:shadow-lg hover:border-gray-200 transition-all duration-300">
      {/* Gradient accent top */}
      <div className={cn('h-1 bg-gradient-to-r', report.gradient)} />

      <div className="p-5">
        <div className="flex items-start gap-4">
          {/* Icon circle with gradient */}
          <div className={cn('flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl bg-gradient-to-br shadow-lg', report.gradient)}>
            <Icon className="h-6 w-6 text-white" />
          </div>

          {/* Content */}
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2">
              <h3 className="text-[15px] font-semibold text-gray-900 tracking-tight">{report.label}</h3>
              <span className="flex items-center gap-1 text-[10px] font-bold text-gray-400 bg-gray-100 rounded-md px-1.5 py-0.5 uppercase">
                <fmt.icon className="h-3 w-3" />
                {fmt.label}
              </span>
            </div>
            <p className="text-[13px] text-gray-500 mt-0.5 leading-relaxed">{report.desc}</p>

            {/* Date filters */}
            {report.hasDateFilter && (
              <div className="flex items-center gap-2 mt-3">
                <input
                  type="date"
                  value={dateFrom}
                  onChange={e => setDateFrom(e.target.value)}
                  className="flex-1 bg-gray-50 border border-gray-200 rounded-lg px-2.5 py-1.5 text-xs focus:bg-white focus:ring-2 focus:ring-gray-900/10 focus:border-gray-300 transition-all outline-none"
                />
                <span className="text-gray-300 text-xs">—</span>
                <input
                  type="date"
                  value={dateTo}
                  onChange={e => setDateTo(e.target.value)}
                  className="flex-1 bg-gray-50 border border-gray-200 rounded-lg px-2.5 py-1.5 text-xs focus:bg-white focus:ring-2 focus:ring-gray-900/10 focus:border-gray-300 transition-all outline-none"
                />
              </div>
            )}
          </div>

          {/* Download button */}
          <button
            onClick={handleDownload}
            disabled={status === 'loading'}
            className={cn(
              'flex items-center justify-center h-10 w-10 rounded-xl shrink-0 transition-all duration-200',
              status === 'done'
                ? 'bg-emerald-500 text-white scale-110'
                : status === 'loading'
                ? 'bg-gray-100 text-gray-400'
                : 'bg-gray-100 text-gray-500 hover:bg-gray-900 hover:text-white hover:scale-105',
            )}
          >
            {status === 'loading' ? (
              <Loader2 className="h-4.5 w-4.5 animate-spin" />
            ) : status === 'done' ? (
              <Check className="h-4.5 w-4.5" />
            ) : (
              <Download className="h-4.5 w-4.5" />
            )}
          </button>
        </div>
      </div>
    </div>
  )
}

export function InventoryReportsPage() {
  const { data: features } = useFeatureToggles()
  const isActive = (r: ReportDef) => !r.feature || features?.[r.feature] !== false

  const featured = REPORTS.slice(0, 2).filter(isActive)
  const standard = REPORTS.slice(2).filter(isActive)

  return (
    <div className="space-y-8 max-w-5xl mx-auto">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900 tracking-tight">Reportes</h1>
        <p className="text-[15px] text-gray-500 mt-1">Descarga los datos de tu inventario en un click</p>
      </div>

      {/* Featured reports — larger cards */}
      {featured.length > 0 && (
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {featured.map(report => (
          <ReportCard key={report.id} report={report} />
        ))}
      </div>
      )}

      {/* Standard reports grid */}
      {standard.length > 0 && (
      <div>
        <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-3">Datos operativos</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {standard.map(report => (
            <ReportCard key={report.id} report={report} />
          ))}
        </div>
      </div>
      )}
    </div>
  )
}
