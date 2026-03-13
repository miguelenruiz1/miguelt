import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import {
  ArrowLeft,
  Package,
  ShoppingBag,
  ChevronDown,
  ChevronRight,
  DollarSign,
  Clock,
  Truck,
  CheckCircle2,
  Warehouse,
  Filter,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { useCustomer, usePortalStock, usePortalOrders, usePortalOrderDetail } from '@/hooks/useInventory'
import type { SalesOrderStatus, PortalOrder } from '@/types/inventory'

const STATUS_CONFIG: Record<SalesOrderStatus, { label: string; color: string }> = {
  draft: { label: 'Borrador', color: 'bg-slate-100 text-slate-600' },
  confirmed: { label: 'Confirmada', color: 'bg-blue-50 text-blue-700' },
  picking: { label: 'Picking', color: 'bg-amber-50 text-amber-700' },
  shipped: { label: 'Enviada', color: 'bg-indigo-50 text-indigo-700' },
  delivered: { label: 'Entregada', color: 'bg-emerald-50 text-emerald-700' },
  returned: { label: 'Devuelta', color: 'bg-orange-50 text-orange-600' },
  canceled: { label: 'Cancelada', color: 'bg-red-50 text-red-600' },
}

const STATUS_FILTERS: { value: SalesOrderStatus | ''; label: string }[] = [
  { value: '', label: 'Todos' },
  { value: 'draft', label: 'Borrador' },
  { value: 'confirmed', label: 'Confirmada' },
  { value: 'picking', label: 'Picking' },
  { value: 'shipped', label: 'Enviada' },
  { value: 'delivered', label: 'Entregada' },
  { value: 'returned', label: 'Devuelta' },
  { value: 'canceled', label: 'Cancelada' },
]

type Tab = 'stock' | 'pedidos'

function KpiCard({ icon: Icon, label, value, sub, color }: {
  icon: typeof Package
  label: string
  value: string | number
  sub?: string
  color: string
}) {
  return (
    <div className="bg-white rounded-2xl border border-slate-100 shadow-sm p-5">
      <div className="flex items-center gap-3">
        <div className={cn('h-10 w-10 rounded-xl flex items-center justify-center', color)}>
          <Icon className="h-5 w-5" />
        </div>
        <div>
          <p className="text-xs text-slate-400 font-medium">{label}</p>
          <p className="text-xl font-bold text-slate-900">{value}</p>
          {sub && <p className="text-xs text-slate-400">{sub}</p>}
        </div>
      </div>
    </div>
  )
}

function OrderDetailRow({ order, customerId }: { order: PortalOrder; customerId: string }) {
  const { data: detail, isLoading } = usePortalOrderDetail(order.id, customerId)

  if (isLoading) {
    return (
      <div className="px-5 pb-4 pl-14">
        <p className="text-xs text-slate-400">Cargando detalle...</p>
      </div>
    )
  }

  if (!detail || !detail.lines || detail.lines.length === 0) {
    return (
      <div className="px-5 pb-4 pl-14">
        <p className="text-xs text-slate-400">Sin lineas</p>
      </div>
    )
  }

  return (
    <div className="px-5 pb-4 pl-14">
      <table className="w-full text-xs">
        <thead>
          <tr className="text-slate-400 uppercase tracking-wide">
            <th className="py-1.5 text-left">Producto</th>
            <th className="py-1.5 text-left">SKU</th>
            <th className="py-1.5 text-right">Pedido</th>
            <th className="py-1.5 text-right">Enviado</th>
            <th className="py-1.5 text-right">Precio</th>
            <th className="py-1.5 text-right">Total</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-50">
          {detail.lines.map(line => (
            <tr key={line.id}>
              <td className="py-1.5 text-slate-700">{line.product_name ?? line.product_id.slice(0, 8)}</td>
              <td className="py-1.5 font-mono text-slate-400">{line.sku ?? '\u2014'}</td>
              <td className="py-1.5 text-right text-slate-600">{line.qty_ordered}</td>
              <td className="py-1.5 text-right">
                <span className={cn(
                  'font-medium',
                  line.qty_shipped >= line.qty_ordered ? 'text-emerald-600' : 'text-amber-600',
                )}>
                  {line.qty_shipped}
                </span>
              </td>
              <td className="py-1.5 text-right">
                <span className="text-slate-600">${line.unit_price.toLocaleString()}</span>
                {line.price_source === 'customer_special' && line.original_unit_price != null && line.original_unit_price > line.unit_price && (
                  <div className="text-[9px]">
                    <span className="text-slate-400 line-through">${line.original_unit_price.toLocaleString()}</span>
                    <span className="ml-1 text-blue-600 font-semibold">{Math.round((1 - line.unit_price / line.original_unit_price) * 100)}% dto.</span>
                  </div>
                )}
              </td>
              <td className="py-1.5 text-right font-semibold text-slate-800">${line.line_total.toLocaleString()}</td>
            </tr>
          ))}
        </tbody>
        <tfoot>
          {(() => {
            const savings = (detail.lines ?? []).reduce((acc: number, l: any) => {
              if (l.price_source === 'customer_special' && l.original_unit_price != null && l.original_unit_price > l.unit_price) {
                return acc + (l.original_unit_price - l.unit_price) * l.qty_ordered
              }
              return acc
            }, 0)
            return savings > 0 ? (
              <tr className="border-t border-blue-100 bg-blue-50/40">
                <td colSpan={4} />
                <td className="py-1.5 text-right text-[10px] text-blue-600 font-medium">Ahorro precios especiales</td>
                <td className="py-1.5 text-right text-xs font-bold text-blue-700">-${savings.toLocaleString()}</td>
              </tr>
            ) : null
          })()}
          <tr className="border-t border-slate-200">
            <td colSpan={4} />
            <td className="py-2 text-right text-xs text-slate-400">Subtotal</td>
            <td className="py-2 text-right text-sm font-semibold">${detail.subtotal.toLocaleString()}</td>
          </tr>
          {detail.tax_amount > 0 && (
            <tr>
              <td colSpan={4} />
              <td className="py-1 text-right text-xs text-slate-400">Impuestos</td>
              <td className="py-1 text-right text-sm">${detail.tax_amount.toLocaleString()}</td>
            </tr>
          )}
          {detail.discount_amount > 0 && (
            <tr>
              <td colSpan={4} />
              <td className="py-1 text-right text-xs text-slate-400">Descuento</td>
              <td className="py-1 text-right text-sm text-emerald-600">-${detail.discount_amount.toLocaleString()}</td>
            </tr>
          )}
          <tr>
            <td colSpan={4} />
            <td className="py-1 text-right text-xs font-semibold text-slate-600">Total</td>
            <td className="py-1 text-right text-sm font-bold text-slate-900">${detail.total.toLocaleString()}</td>
          </tr>
        </tfoot>
      </table>

      {/* Dates */}
      <div className="flex gap-4 mt-3 text-xs text-slate-400">
        {detail.expected_date && <span>Esperada: {new Date(detail.expected_date).toLocaleDateString()}</span>}
        {detail.shipped_date && <span>Enviada: {new Date(detail.shipped_date).toLocaleDateString()}</span>}
        {detail.delivered_date && <span>Entregada: {new Date(detail.delivered_date).toLocaleDateString()}</span>}
      </div>
      {detail.notes && <p className="mt-2 text-xs text-slate-500 italic">{detail.notes}</p>}
    </div>
  )
}

export function CustomerPortalPage() {
  const { customerId } = useParams<{ customerId: string }>()
  const navigate = useNavigate()
  const [activeTab, setActiveTab] = useState<Tab>('stock')
  const [expandedOrder, setExpandedOrder] = useState<string | null>(null)
  const [statusFilter, setStatusFilter] = useState<string>('')
  const [stockSearch, setStockSearch] = useState('')

  const { data: customer, isLoading: customerLoading } = useCustomer(customerId ?? '')
  const { data: stockLevels = [], isLoading: stockLoading } = usePortalStock(customerId ?? '')
  const { data: orders = [], isLoading: ordersLoading } = usePortalOrders(customerId ?? '', statusFilter || undefined)

  // Stock KPIs
  const totalSkus = new Set(stockLevels.map(s => s.product_id)).size
  const totalQty = stockLevels.reduce((acc, s) => acc + s.qty_on_hand, 0)
  const totalReserved = stockLevels.reduce((acc, s) => acc + s.qty_reserved, 0)
  const warehouseCount = new Set(stockLevels.map(s => s.warehouse_id)).size

  // Orders KPIs
  const totalOrders = orders.length
  const activeOrders = orders.filter(o => !['delivered', 'canceled', 'returned'].includes(o.status)).length
  const totalValue = orders.reduce((acc, o) => acc + o.total, 0)
  const deliveredCount = orders.filter(o => o.status === 'delivered').length

  // Filtered stock
  const filteredStock = stockSearch
    ? stockLevels.filter(s =>
        (s.product_name?.toLowerCase().includes(stockSearch.toLowerCase())) ||
        (s.sku?.toLowerCase().includes(stockSearch.toLowerCase())) ||
        (s.warehouse_name?.toLowerCase().includes(stockSearch.toLowerCase()))
      )
    : stockLevels

  if (customerLoading) {
    return (
      <div className="flex justify-center py-20">
        <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-indigo-600" />
      </div>
    )
  }

  if (!customer) {
    return <p className="text-center text-slate-400 py-20">Cliente no encontrado</p>
  }

  return (
    <div className="max-w-6xl mx-auto p-6 space-y-6">
      {/* Back */}
      <button
        onClick={() => navigate(`/inventario/clientes`)}
        className="flex items-center gap-1 text-sm text-slate-500 hover:text-slate-900"
      >
        <ArrowLeft className="h-4 w-4" /> Volver a clientes
      </button>

      {/* Header */}
      <div className="bg-white rounded-2xl border border-slate-100 shadow-sm p-6">
        <div className="flex items-center gap-4">
          <div className="h-12 w-12 rounded-2xl bg-indigo-100 flex items-center justify-center">
            <Package className="h-6 w-6 text-indigo-600" />
          </div>
          <div className="flex-1">
            <h1 className="text-2xl font-bold text-slate-900">Portal de Autogestion</h1>
            <p className="text-sm text-slate-500 mt-0.5">
              <span className="font-semibold text-slate-700">{customer.name}</span>
              <span className="font-mono text-xs ml-2 text-slate-400">{customer.code}</span>
              {customer.email && <span className="ml-3">{customer.email}</span>}
            </p>
          </div>
          {customer.credit_limit > 0 && (
            <div className="text-right">
              <p className="text-xs text-slate-400">Credito</p>
              <p className="text-lg font-bold text-slate-900">${customer.credit_limit.toLocaleString()}</p>
            </div>
          )}
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 bg-slate-100 rounded-xl p-1">
        <button
          onClick={() => setActiveTab('stock')}
          className={cn(
            'flex-1 inline-flex items-center justify-center gap-2 rounded-lg px-4 py-2 text-sm font-semibold transition-colors',
            activeTab === 'stock'
              ? 'bg-white text-slate-900 shadow-sm'
              : 'text-slate-500 hover:text-slate-700',
          )}
        >
          <Package className="h-4 w-4" />
          Stock Disponible
        </button>
        <button
          onClick={() => setActiveTab('pedidos')}
          className={cn(
            'flex-1 inline-flex items-center justify-center gap-2 rounded-lg px-4 py-2 text-sm font-semibold transition-colors',
            activeTab === 'pedidos'
              ? 'bg-white text-slate-900 shadow-sm'
              : 'text-slate-500 hover:text-slate-700',
          )}
        >
          <ShoppingBag className="h-4 w-4" />
          Mis Pedidos
          {activeOrders > 0 && (
            <span className="bg-indigo-100 text-indigo-700 text-xs font-bold px-1.5 py-0.5 rounded-full">
              {activeOrders}
            </span>
          )}
        </button>
      </div>

      {/* ── Stock Tab ─────────────────────────────────────────────────── */}
      {activeTab === 'stock' && (
        <>
          {/* KPIs */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <KpiCard icon={Package} label="Productos" value={totalSkus} color="bg-indigo-100 text-indigo-600" />
            <KpiCard icon={CheckCircle2} label="Disponible" value={totalQty.toLocaleString()} color="bg-emerald-100 text-emerald-600" />
            <KpiCard icon={Clock} label="Reservado" value={totalReserved.toLocaleString()} color="bg-amber-100 text-amber-600" />
            <KpiCard icon={Warehouse} label="Bodegas" value={warehouseCount} color="bg-blue-100 text-blue-600" />
          </div>

          {/* Search */}
          <div className="flex items-center gap-3">
            <input
              type="text"
              placeholder="Buscar por producto, SKU o bodega..."
              value={stockSearch}
              onChange={e => setStockSearch(e.target.value)}
              className="flex-1 rounded-xl border border-slate-200 px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-400"
            />
          </div>

          {/* Table */}
          <div className="bg-white rounded-2xl border border-slate-100 shadow-sm overflow-hidden">
            {stockLoading ? (
              <div className="p-8 text-center text-slate-400">Cargando stock...</div>
            ) : filteredStock.length === 0 ? (
              <div className="p-12 text-center">
                <Package className="h-10 w-10 text-slate-200 mx-auto mb-3" />
                <p className="text-sm text-slate-400">
                  {stockSearch ? 'Sin resultados para la busqueda' : 'Sin productos en stock para este cliente'}
                </p>
              </div>
            ) : (
              <table className="w-full text-sm">
                <thead className="bg-slate-50 border-b border-slate-100">
                  <tr>
                    {['Producto', 'SKU', 'Bodega', 'Disponible', 'Reservado', 'QC'].map(h => (
                      <th key={h} className="px-5 py-3 text-left text-xs font-semibold text-slate-400 uppercase tracking-wide">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-50">
                  {filteredStock.map((sl, i) => {
                    const qty = sl.qty_on_hand
                    return (
                      <tr key={`${sl.product_id}-${sl.warehouse_id}-${i}`} className="hover:bg-slate-50">
                        <td className="px-5 py-3 font-medium text-slate-800">{sl.product_name ?? sl.product_id.slice(0, 8)}</td>
                        <td className="px-5 py-3 font-mono text-xs text-slate-500">{sl.sku ?? '\u2014'}</td>
                        <td className="px-5 py-3 text-sm text-slate-600">{sl.warehouse_name ?? '\u2014'}</td>
                        <td className="px-5 py-3">
                          <span className={cn('font-bold', qty <= 0 ? 'text-red-500' : 'text-slate-900')}>
                            {qty.toLocaleString()}
                          </span>
                        </td>
                        <td className="px-5 py-3 text-slate-500">{sl.qty_reserved.toLocaleString()}</td>
                        <td className="px-5 py-3">
                          {sl.qc_status && (
                            <span className={cn(
                              'px-2 py-0.5 rounded-full text-xs font-semibold',
                              sl.qc_status === 'approved' ? 'bg-emerald-50 text-emerald-700' :
                              sl.qc_status === 'rejected' ? 'bg-red-50 text-red-600' :
                              'bg-amber-50 text-amber-700',
                            )}>
                              {sl.qc_status === 'approved' ? 'Aprobado' :
                               sl.qc_status === 'rejected' ? 'Rechazado' : 'Pendiente'}
                            </span>
                          )}
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            )}
          </div>
        </>
      )}

      {/* ── Pedidos Tab ────────────────────────────────────────────────── */}
      {activeTab === 'pedidos' && (
        <>
          {/* KPIs */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <KpiCard icon={ShoppingBag} label="Total Pedidos" value={totalOrders} color="bg-indigo-100 text-indigo-600" />
            <KpiCard icon={Clock} label="En Proceso" value={activeOrders} color="bg-amber-100 text-amber-600" />
            <KpiCard icon={Truck} label="Entregados" value={deliveredCount} color="bg-emerald-100 text-emerald-600" />
            <KpiCard icon={DollarSign} label="Valor Total" value={`$${totalValue.toLocaleString()}`} color="bg-blue-100 text-blue-600" />
          </div>

          {/* Status filter */}
          <div className="flex items-center gap-2 flex-wrap">
            <Filter className="h-4 w-4 text-slate-400" />
            {STATUS_FILTERS.map(f => (
              <button
                key={f.value}
                onClick={() => setStatusFilter(f.value)}
                className={cn(
                  'px-3 py-1.5 rounded-lg text-xs font-medium transition-colors',
                  statusFilter === f.value
                    ? 'bg-indigo-100 text-indigo-700'
                    : 'bg-slate-100 text-slate-500 hover:bg-slate-200',
                )}
              >
                {f.label}
              </button>
            ))}
          </div>

          {/* Orders list */}
          <div className="bg-white rounded-2xl border border-slate-100 shadow-sm overflow-hidden">
            {ordersLoading ? (
              <div className="p-8 text-center text-slate-400">Cargando pedidos...</div>
            ) : orders.length === 0 ? (
              <div className="p-12 text-center">
                <ShoppingBag className="h-10 w-10 text-slate-200 mx-auto mb-3" />
                <p className="text-sm text-slate-400">
                  {statusFilter ? 'Sin pedidos con ese estado' : 'Sin pedidos para este cliente'}
                </p>
              </div>
            ) : (
              <div className="divide-y divide-slate-100">
                {orders.map(order => {
                  const isExpanded = expandedOrder === order.id
                  return (
                    <div key={order.id}>
                      <button
                        onClick={() => setExpandedOrder(isExpanded ? null : order.id)}
                        className="w-full flex items-center gap-4 px-5 py-4 text-left hover:bg-slate-50/60 transition-colors"
                      >
                        <div className="flex-none">
                          {isExpanded
                            ? <ChevronDown className="h-4 w-4 text-slate-400" />
                            : <ChevronRight className="h-4 w-4 text-slate-400" />}
                        </div>
                        <div className="flex-1 min-w-0">
                          <span className="font-mono text-xs text-slate-700 font-semibold">{order.order_number}</span>
                          <span className="text-xs text-slate-400 ml-3">
                            {order.created_at ? new Date(order.created_at).toLocaleDateString() : ''}
                          </span>
                          <span className="text-xs text-slate-300 ml-2">
                            {order.line_count} {order.line_count === 1 ? 'linea' : 'lineas'}
                          </span>
                        </div>
                        <span className={cn('px-2 py-0.5 rounded-full text-xs font-semibold', STATUS_CONFIG[order.status]?.color)}>
                          {STATUS_CONFIG[order.status]?.label}
                        </span>
                        <span className="font-mono text-sm font-bold text-slate-900 min-w-[80px] text-right">
                          ${order.total.toLocaleString()}
                        </span>
                      </button>

                      {/* Expanded: fetch full detail with lines */}
                      {isExpanded && (
                        <OrderDetailRow order={order} customerId={customerId!} />
                      )}
                    </div>
                  )
                })}
              </div>
            )}
          </div>
        </>
      )}
    </div>
  )
}
