import { useState, useMemo, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Package, CheckCircle2, Circle, MapPin, ClipboardList, Truck, ArrowLeft, Warehouse,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import {
  useSalesOrders, useSalesOrder, usePickSalesOrder, useShipSalesOrder,
  useStockLevels, useLocations, useCustomers, useProducts,
} from '@/hooks/useInventory'
import { useToast } from '@/store/toast'
import type { SalesOrder, SalesOrderLine } from '@/types/inventory'

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const STATUS_LABEL: Record<string, { label: string; color: string }> = {
  confirmed: { label: 'Confirmada', color: 'bg-blue-50 text-blue-700' },
  picking:   { label: 'En Picking', color: 'bg-amber-50 text-amber-700' },
}

function fmtDate(iso?: string | null) {
  if (!iso) return '--'
  return new Date(iso).toLocaleDateString('es', { day: '2-digit', month: 'short', year: 'numeric' })
}

// ---------------------------------------------------------------------------
// Main page
// ---------------------------------------------------------------------------

export function PickingPage() {
  const [activeOrderId, setActiveOrderId] = useState<string | null>(null)

  if (activeOrderId) {
    return <ActivePicking orderId={activeOrderId} onBack={() => setActiveOrderId(null)} />
  }

  return <PickQueue onSelect={setActiveOrderId} />
}

// ---------------------------------------------------------------------------
// Pick Queue (list of confirmed + picking orders)
// ---------------------------------------------------------------------------

function PickQueue({ onSelect }: { onSelect: (id: string) => void }) {
  const { data: confirmedData, isLoading: l1 } = useSalesOrders({ status: 'confirmed', limit: 100 })
  const { data: pickingData, isLoading: l2 } = useSalesOrders({ status: 'picking', limit: 100 })
  const { data: customersData } = useCustomers()
  const pickMut = usePickSalesOrder()
  const toast = useToast()

  const customerMap = useMemo(() => {
    const m = new Map<string, string>()
    if (customersData?.items) {
      for (const c of customersData.items) m.set(c.id, c.name)
    }
    return m
  }, [customersData])

  const orders = useMemo(() => {
    const all: SalesOrder[] = []
    if (pickingData?.items) all.push(...pickingData.items)
    if (confirmedData?.items) all.push(...confirmedData.items)
    return all
  }, [confirmedData, pickingData])

  const isLoading = l1 || l2

  const handleInitPicking = useCallback((orderId: string) => {
    pickMut.mutate(orderId, {
      onSuccess: () => {
        toast.push('Picking iniciado', 'success')
        onSelect(orderId)
      },
      onError: (err: Error) => toast.push(err.message, 'error'),
    })
  }, [pickMut, toast, onSelect])

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <ClipboardList className="h-7 w-7 text-amber-600" />
        <h1 className="text-2xl font-bold text-foreground">Cola de Picking</h1>
      </div>

      {isLoading && (
        <div className="flex justify-center py-20">
          <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-amber-600" />
        </div>
      )}

      {!isLoading && orders.length === 0 && (
        <div className="text-center py-20 text-muted-foreground">
          <Package className="h-12 w-12 mx-auto mb-3 opacity-40" />
          <p className="text-lg font-medium">Sin ordenes pendientes de picking</p>
        </div>
      )}

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {orders.map(order => {
          const cfg = STATUS_LABEL[order.status] ?? STATUS_LABEL.confirmed
          return (
            <div
              key={order.id}
              className="bg-card rounded-2xl border border-border/60  p-5 flex flex-col gap-3"
            >
              {/* Header */}
              <div className="flex items-start justify-between">
                <div>
                  <p className="text-lg font-bold text-foreground">{order.order_number}</p>
                  <p className="text-sm text-muted-foreground mt-0.5">
                    {customerMap.get(order.customer_id) ?? order.customer_id.slice(0, 8)}
                  </p>
                </div>
                <span className={cn('px-2.5 py-0.5 rounded-full text-xs font-bold', cfg.color)}>
                  {cfg.label}
                </span>
              </div>

              {/* Info row */}
              <div className="flex items-center gap-4 text-sm text-muted-foreground">
                <span>{order.lines.length} linea{order.lines.length !== 1 ? 's' : ''}</span>
                <span className="font-semibold text-foreground">
                  ${order.total.toLocaleString('es-CO')} {order.currency}
                </span>
                <span className="ml-auto text-xs">{fmtDate(order.created_at)}</span>
              </div>

              {/* Action */}
              {order.status === 'confirmed' && (
                <button
                  onClick={() => handleInitPicking(order.id)}
                  disabled={pickMut.isPending}
                  className="w-full mt-1 flex items-center justify-center gap-2 px-4 py-3 text-sm font-bold text-white bg-amber-600 hover:bg-amber-700 disabled:opacity-50 rounded-xl transition-colors"
                >
                  <Package className="h-5 w-5" /> Iniciar Picking
                </button>
              )}
              {order.status === 'picking' && (
                <button
                  onClick={() => onSelect(order.id)}
                  className="w-full mt-1 flex items-center justify-center gap-2 px-4 py-3 text-sm font-bold text-white bg-primary hover:bg-primary/90 rounded-xl transition-colors"
                >
                  <ClipboardList className="h-5 w-5" /> Continuar
                </button>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Active Picking view (checklist + packing summary)
// ---------------------------------------------------------------------------

function ActivePicking({ orderId, onBack }: { orderId: string; onBack: () => void }) {
  const navigate = useNavigate()
  const { data: order, isLoading } = useSalesOrder(orderId)
  const { data: customersData } = useCustomers()
  const { data: productsData } = useProducts({ limit: 200 })
  const { data: stockData } = useStockLevels(
    order?.warehouse_id ? { warehouse_id: order.warehouse_id } : undefined,
  )
  const { data: locationsData } = useLocations(order?.warehouse_id ?? undefined)

  const shipMut = useShipSalesOrder()
  const toast = useToast()

  const [pickedSet, setPickedSet] = useState<Set<string>>(new Set())
  const [showPacking, setShowPacking] = useState(false)

  // Maps
  const customerName = useMemo(() => {
    if (!customersData?.items || !order) return ''
    return customersData.items.find(c => c.id === order.customer_id)?.name ?? order.customer_id.slice(0, 8)
  }, [customersData, order])

  const productMap = useMemo(() => {
    const m = new Map<string, { name: string; sku: string; barcode: string | null }>()
    if (productsData?.items) {
      for (const p of productsData.items) m.set(p.id, { name: p.name, sku: p.sku, barcode: p.barcode })
    }
    return m
  }, [productsData])

  const locationMap = useMemo(() => {
    const m = new Map<string, string>()
    if (locationsData) {
      for (const l of locationsData) m.set(l.id, `${l.code} - ${l.name}`)
    }
    return m
  }, [locationsData])

  // Map product_id -> location hint (first stock level with a location)
  const productLocationHint = useMemo(() => {
    const m = new Map<string, string>()
    if (stockData) {
      for (const sl of stockData) {
        if (sl.location_id && !m.has(sl.product_id)) {
          m.set(sl.product_id, locationMap.get(sl.location_id) ?? sl.location_id.slice(0, 8))
        }
      }
    }
    return m
  }, [stockData, locationMap])

  // For packing summary: group picked lines by warehouse (primary) then location
  const packingGroups = useMemo(() => {
    if (!order) return []
    const groups = new Map<string, { location: string; lines: (SalesOrderLine & { prodName: string })[] }>()
    for (const line of order.lines) {
      if (!pickedSet.has(line.id)) continue
      // Group by warehouse first, then by location hint
      const whLabel = line.warehouse_name ?? order.warehouse_name ?? 'Sin bodega'
      const locHint = productLocationHint.get(line.product_id)
      const groupKey = locHint ? `${whLabel} — ${locHint}` : whLabel
      if (!groups.has(groupKey)) groups.set(groupKey, { location: groupKey, lines: [] })
      groups.get(groupKey)!.lines.push({
        ...line,
        prodName: productMap.get(line.product_id)?.name ?? line.product_id.slice(0, 8),
      })
    }
    return Array.from(groups.values())
  }, [order, pickedSet, productLocationHint, productMap])

  const togglePicked = useCallback((lineId: string) => {
    setPickedSet(prev => {
      const next = new Set(prev)
      if (next.has(lineId)) next.delete(lineId)
      else next.add(lineId)
      return next
    })
  }, [])

  const allPicked = order ? order.lines.length > 0 && pickedSet.size === order.lines.length : false
  const progress = order ? (order.lines.length > 0 ? (pickedSet.size / order.lines.length) * 100 : 0) : 0

  const handleCompletePicking = useCallback(() => {
    setShowPacking(true)
  }, [])

  const handleConfirmShip = useCallback(() => {
    if (!order) return
    const lineShipments = order.lines.map(l => ({
      line_id: l.id,
      qty_shipped: l.qty_ordered,
    }))
    shipMut.mutate(
      { id: order.id, body: { line_shipments: lineShipments } },
      {
        onSuccess: async () => {
          toast.push('Envio confirmado', 'success')
          // Try to download remission PDF automatically
          try {
            const { inventorySalesOrdersApi } = await import('@/lib/inventory-api')
            const { generateRemissionPDF } = await import('@/utils/generateRemissionPDF')
            const remData = await inventorySalesOrdersApi.getRemission(order.id)
            generateRemissionPDF(remData)
            toast.push('Remisión descargada', 'success')
          } catch {
            // Remission download is best-effort
          }
          navigate(`/inventario/ventas/${order.id}`)
        },
        onError: (err: Error) => toast.push(err.message, 'error'),
      },
    )
  }, [order, shipMut, toast, navigate])

  if (isLoading) {
    return (
      <div className="flex justify-center py-20">
        <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-amber-600" />
      </div>
    )
  }

  if (!order) {
    return <p className="text-center text-muted-foreground py-20">Orden no encontrada</p>
  }

  // ── Packing summary view ──
  if (showPacking) {
    return (
      <div className="space-y-6">
        <button onClick={() => setShowPacking(false)} className="flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground">
          <ArrowLeft className="h-4 w-4" /> Volver al checklist
        </button>

        <div className="flex items-center gap-3">
          <Truck className="h-7 w-7 text-primary" />
          <h1 className="text-2xl font-bold text-foreground">Resumen de Packing</h1>
        </div>

        <div className="bg-card rounded-2xl border border-border/60  p-5">
          <p className="text-sm text-muted-foreground mb-1">Orden</p>
          <p className="text-lg font-bold">{order.order_number}</p>
          <p className="text-sm text-muted-foreground mt-1">Cliente: <span className="font-semibold text-foreground">{customerName}</span></p>
        </div>

        {packingGroups.map(g => (
          <div key={g.location} className="bg-card rounded-2xl border border-border/60  overflow-hidden">
            <div className="px-5 py-3 bg-muted flex items-center gap-2 border-b border-border/60">
              <MapPin className="h-4 w-4 text-muted-foreground" />
              <span className="text-sm font-bold text-foreground">{g.location}</span>
            </div>
            <ul className="divide-y divide-slate-100">
              {g.lines.map(l => (
                <li key={l.id} className="px-5 py-3 flex items-center justify-between">
                  <div>
                    <p className="text-sm font-semibold text-foreground">{l.prodName}</p>
                    <p className="text-xs text-muted-foreground">{productMap.get(l.product_id)?.sku ?? '--'}</p>
                  </div>
                  <span className="text-sm font-bold text-foreground">x{l.qty_ordered}</span>
                </li>
              ))}
            </ul>
          </div>
        ))}

        <button
          onClick={handleConfirmShip}
          disabled={shipMut.isPending}
          className="w-full flex items-center justify-center gap-2 px-6 py-4 text-base font-bold text-white bg-primary hover:bg-primary/90 disabled:opacity-50 rounded-xl transition-colors"
        >
          <Truck className="h-5 w-5" />
          {shipMut.isPending ? 'Enviando...' : 'Confirmar Envio'}
        </button>
      </div>
    )
  }

  // ── Picking checklist view ──
  return (
    <div className="space-y-6">
      <button onClick={onBack} className="flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground">
        <ArrowLeft className="h-4 w-4" /> Cola de Picking
      </button>

      {/* Order header */}
      <div className="bg-card rounded-2xl border border-border/60  p-5 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div>
          <p className="text-xs text-muted-foreground uppercase font-bold">Picking Activo</p>
          <h1 className="text-2xl font-bold text-foreground mt-1">{order.order_number}</h1>
          <p className="text-sm text-muted-foreground mt-0.5">
            Cliente: <span className="font-semibold text-foreground">{customerName}</span>
          </p>
        </div>
        <div className="text-right">
          <p className="text-xs text-muted-foreground">{fmtDate(order.expected_date)}</p>
          <p className="text-lg font-bold text-primary mt-1">${order.total.toLocaleString('es-CO')} {order.currency}</p>
        </div>
      </div>

      {/* Progress bar */}
      <div className="bg-card rounded-2xl border border-border/60  p-5">
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm font-semibold text-foreground">Progreso</span>
          <span className="text-sm font-bold text-foreground">
            {pickedSet.size} / {order.lines.length}
          </span>
        </div>
        <div className="h-3 bg-secondary rounded-full overflow-hidden">
          <div
            className={cn(
              'h-full rounded-full transition-all duration-300',
              allPicked ? 'bg-emerald-500' : 'bg-amber-500',
            )}
            style={{ width: `${progress}%` }}
          />
        </div>
      </div>

      {/* Checklist */}
      <div className="space-y-3">
        {order.lines.map(line => {
          const picked = pickedSet.has(line.id)
          const prod = productMap.get(line.product_id)
          const locationHint = productLocationHint.get(line.product_id)

          return (
            <button
              key={line.id}
              type="button"
              onClick={() => togglePicked(line.id)}
              className={cn(
                'w-full text-left bg-card rounded-2xl border  p-5 flex items-start gap-4 transition-colors',
                picked
                  ? 'border-emerald-300 bg-emerald-50/40'
                  : 'border-border/60 hover:border-amber-300',
              )}
            >
              {/* Checkbox */}
              <div className="pt-0.5 shrink-0">
                {picked ? (
                  <CheckCircle2 className="h-7 w-7 text-emerald-500" />
                ) : (
                  <Circle className="h-7 w-7 text-slate-300" />
                )}
              </div>

              {/* Info */}
              <div className="flex-1 min-w-0">
                <p className={cn('text-base font-semibold', picked ? 'text-emerald-700 line-through' : 'text-foreground')}>
                  {prod?.name ?? line.product_id.slice(0, 8)}
                </p>
                <div className="flex flex-wrap items-center gap-3 mt-1 text-xs text-muted-foreground">
                  {prod?.sku && (
                    <span className="font-mono bg-secondary px-1.5 py-0.5 rounded">{prod.sku}</span>
                  )}
                  {line.variant_id && (
                    <span className="italic text-muted-foreground">Variante: {line.variant_id.slice(0, 8)}</span>
                  )}
                </div>
                {(line.warehouse_name || (order.warehouse_name && !line.warehouse_id)) && (
                  <p className="flex items-center gap-1 text-xs text-muted-foreground mt-1.5">
                    <Warehouse className="h-3.5 w-3.5" /> {line.warehouse_name ?? order.warehouse_name}
                    {line.warehouse_id && line.warehouse_id !== order.warehouse_id && (
                      <span className="ml-1 rounded-full bg-blue-50 px-1.5 py-0.5 text-[10px] font-semibold text-blue-600">Específica</span>
                    )}
                  </p>
                )}
                {locationHint && (
                  <p className="flex items-center gap-1 text-xs text-primary mt-1">
                    <MapPin className="h-3.5 w-3.5" /> {locationHint}
                  </p>
                )}
                {prod?.barcode && (
                  <p className="text-xs text-muted-foreground mt-1 font-mono">
                    Codigo: {prod.barcode}
                  </p>
                )}
              </div>

              {/* Quantity */}
              <div className="shrink-0 text-right">
                <p className="text-2xl font-bold text-foreground">{line.qty_ordered}</p>
                <p className="text-xs text-muted-foreground">unidades</p>
              </div>
            </button>
          )
        })}
      </div>

      {/* Complete picking button */}
      {allPicked && (
        <button
          onClick={handleCompletePicking}
          className="w-full flex items-center justify-center gap-2 px-6 py-4 text-base font-bold text-white bg-emerald-600 hover:bg-emerald-700 rounded-xl transition-colors"
        >
          <CheckCircle2 className="h-5 w-5" /> Completar Picking
        </button>
      )}
    </div>
  )
}
