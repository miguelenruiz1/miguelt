import { useState, useEffect, useCallback } from 'react'
import { useFormValidation } from '@/hooks/useFormValidation'
import { useNavigate, useLocation } from 'react-router-dom'
import {
  Plus, Search, ShoppingBag, Pencil, Trash2, Check, PackageCheck, Truck as TruckIcon,
  CheckCircle2, RotateCcw, XCircle,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import {
  useSalesOrders, useSalesOrderSummary, useCreateSalesOrder, useDeleteSalesOrder,
  useConfirmSalesOrder, usePickSalesOrder, useShipSalesOrder,
  useDeliverSalesOrder, useReturnSalesOrder, useCancelSalesOrder,
  usePartners, useProducts, useWarehouses, useStockLevels,
  useApproveSalesOrder, useRejectSalesOrder, useResubmitSalesOrder,
  usePriceLookup, useTaxRates,
} from '@/hooks/useInventory'
import { useQuery } from '@tanstack/react-query'
import { useToast } from '@/store/toast'
import { VariantPicker } from '@/components/inventory/VariantPicker'
import { inventoryPricingApi } from '@/lib/inventory-api'
import type { SalesOrder, SalesOrderStatus, ConfirmWithBackorderOut, PriceLookupResponse } from '@/types/inventory'

function PriceSemaphore({ productId, unitPrice }: { productId: string; unitPrice: number }) {
  const { data } = useQuery({
    queryKey: ['inventory', 'product-pricing', productId],
    queryFn: () => inventoryPricingApi.getProductPricing(productId),
    enabled: !!productId,
    staleTime: 30_000,
  })
  if (!data || !data.last_purchase_cost) return null
  const cost = data.last_purchase_cost
  const margin = cost > 0 ? ((unitPrice - cost) / unitPrice) * 100 : 0
  const suggested = data.suggested_sale_price || 0
  const minimum = data.minimum_sale_price || 0
  let color = 'bg-green-50 text-green-700 border-green-200'
  let icon = '🟢'
  let msg = `Margen ${margin.toFixed(1)}% — Por encima del objetivo`
  if (margin < 0 || (unitPrice < minimum && minimum > 0)) {
    color = 'bg-red-50 text-red-700 border-red-200'; icon = '🔴'
    msg = margin < 0
      ? `Margen ${margin.toFixed(1)}% — Vendiendo por debajo del costo`
      : `Margen ${margin.toFixed(1)}% — Por debajo del mínimo. Requiere autorización.`
  } else if (unitPrice < suggested && suggested > 0) {
    color = 'bg-orange-50 text-orange-700 border-orange-200'; icon = '🟡'
    msg = `Margen ${margin.toFixed(1)}% — Por debajo del objetivo (mín: $${minimum.toLocaleString('es-CO')})`
  }
  return (
    <div className={`text-xs mt-1 p-2 rounded border ${color} col-span-full`}>
      {icon} {msg}
      <div className="mt-1 text-muted-foreground">Costo: ${cost.toLocaleString('es-CO')} | Sugerido: ${suggested.toLocaleString('es-CO')} | Mínimo: ${minimum.toLocaleString('es-CO')}</div>
    </div>
  )
}

const STATUS_CONFIG: Record<SalesOrderStatus, { label: string; color: string }> = {
  draft: { label: 'Borrador', color: 'bg-secondary text-muted-foreground' },
  confirmed: { label: 'Confirmada', color: 'bg-blue-50 text-blue-700' },
  picking: { label: 'En Picking', color: 'bg-amber-50 text-amber-700' },
  shipped: { label: 'Enviada', color: 'bg-primary/10 text-primary' },
  delivered: { label: 'Entregada', color: 'bg-emerald-50 text-emerald-700' },
  returned: { label: 'Devuelta', color: 'bg-orange-50 text-orange-600' },
  canceled: { label: 'Cancelada', color: 'bg-red-50 text-red-600' },
  pending_approval: { label: 'Pend. Aprobación', color: 'bg-yellow-50 text-yellow-700' },
  rejected: { label: 'Rechazado', color: 'bg-red-50 text-red-600' },
}

const STATUS_FILTERS: { value: string; label: string }[] = [
  { value: '', label: 'Todas' },
  { value: 'draft', label: 'Borrador' },
  { value: 'confirmed', label: 'Confirmada' },
  { value: 'picking', label: 'Picking' },
  { value: 'shipped', label: 'Enviada' },
  { value: 'delivered', label: 'Entregada' },
  { value: 'returned', label: 'Devuelta' },
  { value: 'canceled', label: 'Cancelada' },
  { value: 'pending_approval', label: 'Pend. Aprobación' },
  { value: 'rejected', label: 'Rechazado' },
]

interface SOLine { product_id: string; variant_id: string; warehouse_id: string; qty_ordered: string; unit_price: string; discount_pct: string; tax_rate: string }

function CreateSOModal({ onClose }: { onClose: () => void }) {
  const { data: partnersData } = usePartners({ limit: 200 })
  const { data: productsData } = useProducts()
  const { data: warehouses = [] } = useWarehouses()
  const create = useCreateSalesOrder()
  const priceLookupMut = usePriceLookup()
  const { data: taxRates = [] } = useTaxRates({ is_active: true })
  const ivaRates = taxRates.filter(r => r.tax_type === 'iva')
  const { data: stockLevels = [] } = useStockLevels({ limit: 500 })
  const partners = partnersData?.items ?? []
  const allProducts = productsData?.items ?? []
  // Build set of product IDs that have stock > 0
  const productsWithStock = new Set(
    stockLevels.filter(sl => Number(sl.qty_on_hand) - Number(sl.qty_reserved ?? 0) > 0).map(sl => sl.product_id)
  )
  // Only show active products with available stock
  const products = allProducts.filter(p => p.is_active && productsWithStock.has(p.id))

  const [form, setForm] = useState({ customer_id: '', warehouse_id: '', expected_date: '', notes: '', discount_pct: '0', discount_reason: '' })
  const [lines, setLines] = useState<SOLine[]>([{ product_id: '', variant_id: '', warehouse_id: '', qty_ordered: '1', unit_price: '0', discount_pct: '0', tax_rate: '19' }])
  const [linePriceSources, setLinePriceSources] = useState<Record<number, PriceLookupResponse>>({})

  // Lookup price via API (checks customer special prices first, then base)
  const doLookup = useCallback(async (lineIdx: number, customerId: string, productId: string, qty: number, variantId?: string) => {
    if (!customerId || !productId) return
    try {
      const result = await priceLookupMut.mutateAsync({
        customer_id: customerId,
        product_id: productId,
        quantity: qty,
        variant_id: variantId,
      })
      setLinePriceSources(prev => ({ ...prev, [lineIdx]: result }))
      setLines(l => l.map((ln, idx) => idx === lineIdx ? { ...ln, unit_price: result.price.toFixed(2) } : ln))
    } catch {
      // Fallback to local resolution if lookup endpoint fails
      const { price } = resolvePriceLocal(productId, qty, variantId)
      setLines(l => l.map((ln, idx) => idx === lineIdx ? { ...ln, unit_price: price } : ln))
      setLinePriceSources(prev => { const n = { ...prev }; delete n[lineIdx]; return n })
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [form.customer_id])

  function resolvePriceLocal(productId: string, _qty: number, _variantId?: string): { price: string; fromList: boolean } {
    // Use product's suggested sale price as base
    const p = products.find(x => x.id === productId)
    return { price: p?.suggested_sale_price ? String(p.suggested_sale_price) : '0', fromList: false }
  }

  function addLine() {
    setLines(l => [...l, { product_id: '', variant_id: '', warehouse_id: '', qty_ordered: '1', unit_price: '0', discount_pct: '0', tax_rate: '19' }])
  }
  function removeLine(i: number) {
    setLines(l => l.filter((_, idx) => idx !== i))
    setLinePriceSources(prev => { const n = { ...prev }; delete n[i]; return n })
  }
  function updateLine(i: number, key: keyof SOLine, value: string) {
    setLines(l => l.map((ln, idx) => {
      if (idx !== i) return ln
      const updated = { ...ln, [key]: value }
      return updated
    }))
    // Re-resolve price when qty changes via lookup
    if (key === 'qty_ordered') {
      const ln = lines[i]
      if (ln?.product_id && form.customer_id) {
        doLookup(i, form.customer_id, ln.product_id, Number(value), ln.variant_id || undefined)
      }
    }
  }

  function onProductSelect(i: number, productId: string) {
    const qty = Number(lines[i]?.qty_ordered ?? 1)
    // Set product immediately, then lookup price
    setLines(l => l.map((ln, idx) => idx === i ? { ...ln, product_id: productId, variant_id: '' } : ln))
    if (form.customer_id) {
      doLookup(i, form.customer_id, productId, qty, undefined)
    } else {
      const { price } = resolvePriceLocal(productId, qty, undefined)
      setLines(l => l.map((ln, idx) => idx === i ? { ...ln, unit_price: price } : ln))
    }
    // Auto-set tax rate from product
    const prod = products.find(x => x.id === productId)
    if (prod?.is_tax_exempt) {
      setLines(l => l.map((ln, idx) => idx === i ? { ...ln, tax_rate: '0' } : ln))
    }
  }

  function onCustomerChange(customerId: string) {
    setForm(f => ({ ...f, customer_id: customerId }))
    // Re-lookup all line prices with the new customer
    setLinePriceSources({})
    lines.forEach((ln, i) => {
      if (ln.product_id && customerId) {
        doLookup(i, customerId, ln.product_id, Number(ln.qty_ordered), ln.variant_id || undefined)
      }
    })
  }

  const { formRef, handleSubmit: validateAndSubmit } = useFormValidation(doSubmit)

  async function doSubmit() {
    await create.mutateAsync({
      customer_id: form.customer_id,
      warehouse_id: form.warehouse_id || null,
      expected_date: form.expected_date || null,
      notes: form.notes || null,
      discount_pct: Number(form.discount_pct) || 0,
      discount_reason: form.discount_reason || null,
      lines: lines.map(l => ({
        product_id: l.product_id,
        variant_id: l.variant_id || null,
        warehouse_id: l.warehouse_id || null,
        qty_ordered: Number(l.qty_ordered),
        unit_price: Number(l.unit_price),
        discount_pct: Number(l.discount_pct),
        tax_rate: Number(l.tax_rate),
      })),
    })
    onClose()
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 backdrop-blur-sm" onClick={onClose}>
      <div className="w-full max-w-5xl bg-card rounded-3xl shadow-2xl p-6 max-h-[90vh] overflow-y-auto" onClick={e => e.stopPropagation()}>
        <h2 className="text-lg font-bold text-foreground mb-4 flex items-center gap-2"><ShoppingBag className="h-5 w-5 text-primary" /> Nueva Orden de Venta</h2>
        <form ref={formRef} onSubmit={validateAndSubmit} className="space-y-3" noValidate>
          {/* Alerts */}
          {partners.length === 0 && (
            <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
              No hay socios comerciales registrados. Crea uno primero en <span className="font-semibold">Socios Comerciales</span>.
            </div>
          )}
          {products.length === 0 && allProducts.length > 0 && (
            <div className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-700">
              Ningún producto tiene stock disponible. Recibe mercancía en una Orden de Compra primero.
            </div>
          )}
          {allProducts.length === 0 && (
            <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
              No hay productos registrados. Crea productos primero.
            </div>
          )}

          <select required value={form.customer_id} onChange={e => onCustomerChange(e.target.value)} className="w-full rounded-xl border border-border px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring">
            <option value="">Cliente *</option>
            {partners.map(c => <option key={c.id} value={c.id}>{c.name} ({c.code})</option>)}
          </select>
          <input type="date" value={form.expected_date} onChange={e => setForm(f => ({ ...f, expected_date: e.target.value }))} className="w-full rounded-xl border border-border px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring" />
          <textarea value={form.notes} onChange={e => setForm(f => ({ ...f, notes: e.target.value }))} placeholder="Notas" rows={2} className="w-full rounded-xl border border-border px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring resize-none" />

          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <p className="text-xs font-bold text-muted-foreground uppercase tracking-wide">Lineas</p>
              <button type="button" onClick={addLine} className="text-xs text-primary hover:text-primary font-semibold">+ Linea</button>
            </div>
            {lines.map((line, i) => {
              const priceSource = linePriceSources[i]
              const isSpecial = priceSource?.source === 'customer_special'
              return (
                <div key={i}>
                <div className="flex gap-2 items-center">
                  <select required value={line.product_id} onChange={e => onProductSelect(i, e.target.value)} className="flex-1 rounded-xl border border-border px-2 py-1.5 text-xs focus:ring-2 focus:ring-ring">
                    <option value="">Producto *</option>
                    {products.map(p => <option key={p.id} value={p.id}>{p.sku} — {p.name}</option>)}
                  </select>
                  <VariantPicker
                    productId={line.product_id || undefined}
                    value={line.variant_id}
                    onChange={(v, salePrice) => {
                      setLines(l => l.map((ln, idx) => {
                        if (idx !== i) return ln
                        return { ...ln, variant_id: v }
                      }))
                      // Lookup with variant
                      if (form.customer_id && line.product_id) {
                        doLookup(i, form.customer_id, line.product_id, Number(line.qty_ordered), v || undefined)
                      } else {
                        const { price, fromList } = resolvePriceLocal(line.product_id, Number(line.qty_ordered), v || undefined)
                        if (fromList) {
                          setLines(l => l.map((ln, idx) => idx === i ? { ...ln, variant_id: v, unit_price: price } : ln))
                        } else if (salePrice !== undefined && salePrice > 0) {
                          setLines(l => l.map((ln, idx) => idx === i ? { ...ln, variant_id: v, unit_price: salePrice.toFixed(2) } : ln))
                        } else {
                          setLines(l => l.map((ln, idx) => idx === i ? { ...ln, variant_id: v, unit_price: price } : ln))
                        }
                      }
                    }}
                  />
                  <select
                    required
                    value={line.warehouse_id}
                    onChange={e => updateLine(i, 'warehouse_id', e.target.value)}
                    className="w-32 rounded-xl border border-border px-2 py-1.5 text-xs focus:ring-2 focus:ring-ring"
                  >
                    <option value="">Bodega *</option>
                    {warehouses.map(w => <option key={w.id} value={w.id}>{w.name}</option>)}
                  </select>
                  <input required type="number" min={1} value={line.qty_ordered} onChange={e => updateLine(i, 'qty_ordered', e.target.value)} className="w-16 rounded-xl border border-border px-2 py-1.5 text-xs" placeholder="Qty" />
                  <div className="relative">
                    <input type="number" step="0.01" value={line.unit_price} onChange={e => updateLine(i, 'unit_price', e.target.value)}
                      className={cn('w-24 rounded-xl border px-2 py-1.5 text-xs',
                        isSpecial ? 'border-blue-300 bg-blue-50' :
                        'border-border'
                      )}
                      placeholder="Precio"
                      title={isSpecial ? 'Precio especial del cliente' : 'Precio base del producto'}
                    />
                    {isSpecial && priceSource && (
                      <div className="absolute -top-2 -right-1 inline-flex items-center gap-1 rounded-full bg-blue-100 px-1.5 py-0.5 text-[9px] font-bold text-blue-700 whitespace-nowrap">
                        Esp.
                        {priceSource.original_price != null && priceSource.original_price !== priceSource.price && (
                          <span className="text-muted-foreground line-through font-normal">${priceSource.original_price.toLocaleString()}</span>
                        )}
                      </div>
                    )}
                  </div>
                  <input type="number" step="0.01" min={0} max={100} value={line.discount_pct} onChange={e => updateLine(i, 'discount_pct', e.target.value)} className="w-16 rounded-xl border border-border px-2 py-1.5 text-xs" placeholder="Desc%" title="Descuento linea %" />
                  <select value={line.tax_rate} onChange={e => updateLine(i, 'tax_rate', e.target.value)} className="w-20 rounded-xl border border-border px-1 py-1.5 text-xs focus:ring-2 focus:ring-ring" title="IVA %">
                    <option value="0">0%</option>
                    <option value="5">5%</option>
                    <option value="19">19%</option>
                    {ivaRates.filter(r => ![0, 0.05, 0.19].includes(Number(r.rate))).map(r => (
                      <option key={r.id} value={String(Number(r.rate) * 100)}>{(Number(r.rate) * 100).toFixed(0)}%</option>
                    ))}
                  </select>
                  {lines.length > 1 && <button type="button" onClick={() => removeLine(i)} className="text-red-400 hover:text-red-600"><Trash2 className="h-3.5 w-3.5" /></button>}
                </div>
                {line.product_id && Number(line.unit_price) > 0 && <PriceSemaphore productId={line.product_id} unitPrice={Number(line.unit_price)} />}
                </div>
              )
            })}
          </div>

          {/* Global discount */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-[10px] font-bold text-muted-foreground uppercase mb-1">Descuento global %</label>
              <input type="number" step="0.01" min={0} max={100} value={form.discount_pct} onChange={e => setForm(f => ({ ...f, discount_pct: e.target.value }))} className="w-full rounded-xl border border-border px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring" placeholder="0" />
            </div>
            <div>
              <label className="block text-[10px] font-bold text-muted-foreground uppercase mb-1">Razon descuento</label>
              <input value={form.discount_reason} onChange={e => setForm(f => ({ ...f, discount_reason: e.target.value }))} className="w-full rounded-xl border border-border px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring" placeholder="Ej: Descuento mayorista" />
            </div>
          </div>

          {/* Totals preview */}
          {(() => {
            const globalDisc = Math.min(100, Math.max(0, Number(form.discount_pct) || 0))
            const discFactor = (100 - globalDisc) / 100
            let subtotal = 0; let taxTotal = 0; let specialSavings = 0
            for (let idx = 0; idx < lines.length; idx++) {
              const ln = lines[idx]
              const qty = Number(ln.qty_ordered) || 0
              const price = Number(ln.unit_price) || 0
              const lpct = Number(ln.discount_pct) || 0
              const taxR = Number(ln.tax_rate) || 0
              const base = price * qty
              const lineDisc = base * lpct / 100
              const lineSub = base - lineDisc
              subtotal += lineSub
              taxTotal += lineSub * discFactor * taxR / 100
              // Calculate savings from special prices
              const ps = linePriceSources[idx]
              if (ps?.source === 'customer_special' && ps.original_price != null && ps.original_price > ps.price) {
                specialSavings += (ps.original_price - ps.price) * qty
              }
            }
            const discAmount = subtotal * globalDisc / 100
            const total = subtotal - discAmount + taxTotal
            return (
              <div className="bg-muted rounded-xl px-4 py-3 space-y-1 text-sm">
                {specialSavings > 0 && (
                  <div className="flex justify-between text-blue-600 bg-blue-50 -mx-4 -mt-3 px-4 py-2 rounded-t-xl mb-1">
                    <span className="font-medium">Ahorro precios especiales</span>
                    <span className="font-mono font-bold">-${specialSavings.toLocaleString('es-CO', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span>
                  </div>
                )}
                <div className="flex justify-between text-muted-foreground"><span>Subtotal</span><span className="font-mono">${subtotal.toLocaleString('es-CO', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span></div>
                {globalDisc > 0 && <div className="flex justify-between text-amber-600"><span>Descuento global ({globalDisc}%)</span><span className="font-mono">-${discAmount.toLocaleString('es-CO', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span></div>}
                <div className="flex justify-between text-muted-foreground"><span>Impuestos</span><span className="font-mono">${taxTotal.toLocaleString('es-CO', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span></div>
                <div className="flex justify-between text-xs text-muted-foreground"><span>Retención: calculada al confirmar</span></div>
                <div className="flex justify-between font-bold text-foreground border-t border-border pt-1"><span>Total</span><span className="font-mono">${total.toLocaleString('es-CO', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span></div>
              </div>
            )
          })()}

          <div className="flex justify-end gap-3 pt-3">
            <button type="button" onClick={onClose} className="px-4 py-2 text-sm font-medium text-muted-foreground hover:text-foreground">Cancelar</button>
            <button type="submit" disabled={create.isPending} className="px-5 py-2 text-sm font-semibold text-white bg-primary hover:bg-primary/90 rounded-xl disabled:opacity-50">Crear</button>
          </div>
        </form>
      </div>
    </div>
  )
}

export function SalesOrdersPage() {
  const navigate = useNavigate()
  const [statusFilter, setStatusFilter] = useState('')
  const [showCreate, setShowCreate] = useState(false)
  const location = useLocation()
  useEffect(() => { setShowCreate(false) }, [location.key])

  const { data, isLoading } = useSalesOrders({ status: statusFilter || undefined, limit: 100 })
  const { data: summary } = useSalesOrderSummary()
  const { data: partnersListData } = usePartners({ limit: 200 })
  const toast = useToast()
  const deleteMut = useDeleteSalesOrder()
  const confirmMut = useConfirmSalesOrder()
  const pickMut = usePickSalesOrder()
  const shipMut = useShipSalesOrder()
  const deliverMut = useDeliverSalesOrder()
  const returnMut = useReturnSalesOrder()
  const cancelMut = useCancelSalesOrder()
  const approveMut = useApproveSalesOrder()
  const rejectMut = useRejectSalesOrder()
  const resubmitMut = useResubmitSalesOrder()

  const orders = data?.items ?? []
  const customersMap = new Map((partnersListData?.items ?? []).map(c => [c.id, c.name]))
  const onError = (err: unknown) => {
    const msg = (err as { message?: string })?.message ?? 'Error desconocido'
    toast.error(msg)
  }

  function actionBtn(order: SalesOrder) {
    const btns: JSX.Element[] = []
    if (order.status === 'draft') {
      btns.push(<button key="confirm" onClick={() => confirmMut.mutate(order.id, {
        onError,
        onSuccess: (res) => {
          const r = res as ConfirmWithBackorderOut & { approval_required?: boolean; message?: string }
          if (r.approval_required) {
            toast.warning(r.message || 'Orden enviada a aprobación')
          } else if (r.split_preview?.has_backorder && r.backorder) {
            toast.warning(`Orden confirmada. Backorder creado: ${r.backorder.order_number}`)
          }
        },
      })} title="Confirmar" className="p-1.5 text-blue-500 hover:bg-blue-50 rounded-lg"><Check className="h-4 w-4" /></button>)
      btns.push(<button key="del" onClick={() => { if (confirm('Eliminar?')) deleteMut.mutate(order.id) }} title="Eliminar" className="p-1.5 text-red-400 hover:bg-red-50 rounded-lg"><Trash2 className="h-4 w-4" /></button>)
    }
    if (order.status === 'confirmed') btns.push(<button key="pick" onClick={() => pickMut.mutate(order.id, { onError })} title="Picking" className="p-1.5 text-amber-500 hover:bg-amber-50 rounded-lg"><PackageCheck className="h-4 w-4" /></button>)
    if (order.status === 'picking') btns.push(<button key="ship" onClick={() => navigate(`/inventario/ventas/${order.id}`)} title="Enviar (completar datos)" className="p-1.5 text-primary hover:bg-primary/10 rounded-lg"><TruckIcon className="h-4 w-4" /></button>)
    if (order.status === 'shipped') btns.push(<button key="deliver" onClick={() => deliverMut.mutate(order.id, { onError })} title="Entregar" className="p-1.5 text-emerald-500 hover:bg-emerald-50 rounded-lg"><CheckCircle2 className="h-4 w-4" /></button>)
    if (order.status === 'delivered') btns.push(<button key="return" onClick={() => returnMut.mutate(order.id, { onError })} title="Devolver" className="p-1.5 text-orange-500 hover:bg-orange-50 rounded-lg"><RotateCcw className="h-4 w-4" /></button>)
    if (order.status === 'pending_approval') {
      btns.push(<button key="approve" onClick={(e) => { e.stopPropagation(); approveMut.mutate(order.id, { onError }) }} title="Aprobar" className="p-1.5 text-emerald-500 hover:bg-emerald-50 rounded-lg"><Check className="h-4 w-4" /></button>)
      btns.push(<button key="reject" onClick={(e) => { e.stopPropagation(); const reason = prompt('Motivo del rechazo (mín. 10 caracteres):'); if (reason && reason.length >= 10) rejectMut.mutate({ id: order.id, reason }, { onError }); else if (reason) toast.error('El motivo debe tener al menos 10 caracteres') }} title="Rechazar" className="p-1.5 text-red-400 hover:bg-red-50 rounded-lg"><XCircle className="h-4 w-4" /></button>)
    }
    if (order.status === 'rejected') {
      btns.push(<button key="resubmit" onClick={(e) => { e.stopPropagation(); resubmitMut.mutate(order.id, { onError }) }} title="Re-enviar" className="p-1.5 text-amber-500 hover:bg-amber-50 rounded-lg"><RotateCcw className="h-4 w-4" /></button>)
    }
    if (!['delivered', 'returned', 'canceled'].includes(order.status)) btns.push(<button key="cancel" onClick={() => cancelMut.mutate(order.id, { onError })} title="Cancelar" className="p-1.5 text-red-400 hover:bg-red-50 rounded-lg"><XCircle className="h-4 w-4" /></button>)
    return <div className="flex gap-0.5 justify-end">{btns}</div>
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground">Ordenes de Venta</h1>
          <p className="text-sm text-muted-foreground mt-1">Gestiona el ciclo de vida de tus ventas</p>
        </div>
        <button onClick={() => setShowCreate(true)} className="flex items-center gap-2 px-4 py-2.5 text-sm font-semibold text-white bg-primary hover:bg-primary/90 rounded-xl transition">
          <Plus className="h-4 w-4" /> Nueva Orden
        </button>
      </div>

      {/* Summary KPIs */}
      {summary && (
        <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-7 gap-3">
          {Object.entries(STATUS_CONFIG).map(([key, cfg]) => (
            <div key={key} className="bg-card rounded-xl border border-border/60 px-4 py-3 text-center">
              <span className={cn('inline-block px-2 py-0.5 rounded-full text-[10px] font-bold mb-1', cfg.color)}>{cfg.label}</span>
              <p className="text-lg font-bold text-foreground">{(summary as Record<string, number>)[key] ?? 0}</p>
            </div>
          ))}
        </div>
      )}

      {/* Filter */}
      <div className="flex gap-2 flex-wrap">
        {STATUS_FILTERS.map(f => (
          <button key={f.value} onClick={() => setStatusFilter(f.value)} className={cn('px-3 py-1.5 text-xs font-medium rounded-lg transition', statusFilter === f.value ? 'bg-primary/15 text-primary' : 'bg-secondary text-muted-foreground hover:bg-slate-200')}>{f.label}</button>
        ))}
      </div>

      {isLoading ? (
        <div className="flex justify-center py-20"><div className="animate-spin rounded-full h-6 w-6 border-b-2 border-primary" /></div>
      ) : (
        <div className="bg-card rounded-2xl border border-border/60  overflow-hidden">
          <table className="w-full text-sm">
            <thead><tr className="bg-muted text-left text-xs font-semibold text-muted-foreground uppercase">
              <th className="px-6 py-3"># Orden</th>
              <th className="px-6 py-3">Cliente</th>
              <th className="px-6 py-3">Bodega</th>
              <th className="px-6 py-3">Remisión</th>
              <th className="px-6 py-3">Estado</th>
              <th className="px-6 py-3 text-right">Total</th>
              <th className="px-6 py-3">Fecha</th>
              <th className="px-6 py-3 text-right">Acciones</th>
            </tr></thead>
            <tbody className="divide-y divide-slate-100">
              {orders.map(o => (
                <tr key={o.id} className="hover:bg-muted/60 cursor-pointer" onClick={() => navigate(`/inventario/ventas/${o.id}`)}>
                  <td className="px-6 py-3 font-mono text-xs">
                    {o.order_number}
                    {o.is_backorder && <span className="ml-1.5 inline-flex rounded-full px-1.5 py-0.5 text-[10px] font-bold bg-amber-100 text-amber-700">BO</span>}
                    {o.backorder_ids && o.backorder_ids.length > 0 && <span className="ml-1.5 inline-flex rounded-full px-1.5 py-0.5 text-[10px] font-bold bg-blue-100 text-blue-700">{o.backorder_ids.length} BO</span>}
                  </td>
                  <td className="px-6 py-3 font-semibold text-foreground">{o.customer_name ?? customersMap.get(o.customer_id) ?? o.customer_id.slice(0, 8)}</td>
                  <td className="px-6 py-3 text-sm text-muted-foreground">{o.warehouse_name ?? '—'}</td>
                  <td className="px-6 py-3 font-mono text-xs">{o.remission_number ? <span className="text-orange-700 font-semibold">{o.remission_number}</span> : <span className="text-slate-300">—</span>}</td>
                  <td className="px-6 py-3"><span className={cn('px-2 py-0.5 rounded-full text-xs font-semibold', STATUS_CONFIG[o.status]?.color)}>{STATUS_CONFIG[o.status]?.label}</span></td>
                  <td className="px-6 py-3 text-right font-mono">${o.total.toLocaleString()}</td>
                  <td className="px-6 py-3 text-muted-foreground text-xs">{o.created_at ? new Date(o.created_at).toLocaleDateString() : ''}</td>
                  <td className="px-6 py-3" onClick={e => e.stopPropagation()}>{actionBtn(o)}</td>
                </tr>
              ))}
              {orders.length === 0 && <tr><td colSpan={8} className="px-6 py-12 text-center text-muted-foreground">Sin ordenes de venta</td></tr>}
            </tbody>
          </table>
        </div>
      )}

      {showCreate && <CreateSOModal onClose={() => setShowCreate(false)} />}
    </div>
  )
}
