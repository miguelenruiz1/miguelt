import { useState, useEffect } from 'react'
import { DollarSign, Users, AlertTriangle, Clock, Trash2, Plus, RefreshCw, X, ChevronsLeft, ChevronLeft, ChevronRight, ChevronsRight, Eye, History } from 'lucide-react'
import { cn } from '@/lib/utils'
import { useFormValidation } from '@/hooks/useFormValidation'
import {
  useCustomerSpecialPrices, useCustomerPriceMetrics, useDeactivateCustomerPrice,
  useCreateCustomerPrice, useCustomers, useProducts, useCustomerPriceDetail,
  useProductVariantsForProduct,
} from '@/hooks/useInventory'
import { useToast } from '@/store/toast'
import type { CustomerPrice } from '@/types/inventory'

export function CustomerPricesPage() {
  const toast = useToast()
  const [customerFilter, setCustomerFilter] = useState('')
  const [productFilter, setProductFilter] = useState('')
  const [activeFilter, setActiveFilter] = useState<'active' | 'expired' | 'all'>('active')
  const [showCreate, setShowCreate] = useState(false)
  const [renewFrom, setRenewFrom] = useState<CustomerPrice | null>(null)
  const [detailId, setDetailId] = useState<string | null>(null)
  const [currentPage, setCurrentPage] = useState(1)
  const PAGE_SIZE = 50

  const { data: metrics } = useCustomerPriceMetrics()
  const { data: prices = [], isLoading } = useCustomerSpecialPrices({
    customer_id: customerFilter || undefined,
    product_id: productFilter || undefined,
    is_active: activeFilter === 'active' ? true : activeFilter === 'expired' ? false : undefined,
  })
  const { data: customersData } = useCustomers({ limit: 200 })
  const { data: productsData } = useProducts({ limit: 200 })
  const deactivateMut = useDeactivateCustomerPrice()
  const createMut = useCreateCustomerPrice()

  const customers = customersData?.items ?? []
  const products = productsData?.items ?? []
  const productsMap = new Map(products.map(p => [p.id, p]))

  const now = new Date()

  // Reset page when filters change
  useEffect(() => setCurrentPage(1), [customerFilter, productFilter, activeFilter])

  // Client-side pagination
  const totalPages = Math.max(1, Math.ceil(prices.length / PAGE_SIZE))
  const safePage = Math.min(currentPage, totalPages)
  const startIdx = (safePage - 1) * PAGE_SIZE
  const endIdx = Math.min(startIdx + PAGE_SIZE, prices.length)
  const pagePrices = prices.slice(startIdx, endIdx)

  async function doSubmitPrice() {
    const form = createFormRef.current
    if (!form) return
    const fd = new FormData(form)
    await createMut.mutateAsync({
      customer_id: fd.get('customer_id') as string,
      product_id: fd.get('product_id') as string,
      variant_id: (fd.get('variant_id') as string) || null,
      price: Number(fd.get('price')),
      min_quantity: Number(fd.get('min_quantity') || 1),
      valid_from: (fd.get('valid_from') as string) || new Date().toISOString().slice(0, 10),
      valid_to: (fd.get('valid_to') as string) || null,
      reason: (fd.get('reason') as string) || null,
    } as Partial<CustomerPrice>)
    toast.success(renewFrom ? 'Precio renovado' : 'Precio especial creado')
    setShowCreate(false)
    setRenewFrom(null)
  }

  const { formRef: createFormRef, handleSubmit: validateAndSubmitPrice } = useFormValidation(doSubmitPrice)

  // Expiring soon (within 30 days)
  const expiringSoon = prices.filter(p => {
    if (!p.valid_to || !p.is_active) return false
    const validTo = new Date(p.valid_to)
    return validTo > now && (validTo.getTime() - now.getTime()) < 30 * 24 * 60 * 60 * 1000
  })

  function getStatus(sp: CustomerPrice): { label: string; color: string } {
    if (!sp.is_active) return { label: 'Inactivo', color: 'bg-secondary text-muted-foreground' }
    if (sp.valid_to) {
      const validTo = new Date(sp.valid_to)
      if (validTo < now) return { label: 'Vencido', color: 'bg-red-50 text-red-600' }
      if ((validTo.getTime() - now.getTime()) < 30 * 24 * 60 * 60 * 1000) return { label: 'Vence pronto', color: 'bg-yellow-50 text-yellow-700' }
    }
    return { label: 'Activo', color: 'bg-emerald-50 text-emerald-700' }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground">Precios Especiales por Cliente</h1>
          <p className="text-sm text-muted-foreground mt-1">Gestiona precios preferenciales para clientes individuales</p>
        </div>
        <button onClick={() => { setRenewFrom(null); setShowCreate(true) }} className="flex items-center gap-2 px-4 py-2.5 text-sm font-semibold text-white bg-blue-600 hover:bg-blue-700 rounded-xl transition">
          <Plus className="h-4 w-4" /> Nuevo Precio
        </button>
      </div>

      {/* Metrics */}
      {metrics && (
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <div className="bg-card rounded-xl border border-border/60 p-4">
            <div className="flex items-center gap-3">
              <div className="h-10 w-10 rounded-xl bg-blue-50 flex items-center justify-center"><DollarSign className="h-5 w-5 text-blue-600" /></div>
              <div>
                <p className="text-xs text-muted-foreground">Precios especiales activos</p>
                <p className="text-2xl font-bold text-foreground">{metrics.active_count}</p>
              </div>
            </div>
          </div>
          <div className="bg-card rounded-xl border border-border/60 p-4">
            <div className="flex items-center gap-3">
              <div className="h-10 w-10 rounded-xl bg-yellow-50 flex items-center justify-center"><AlertTriangle className="h-5 w-5 text-yellow-600" /></div>
              <div>
                <p className="text-xs text-muted-foreground">Vencen en 30 dias</p>
                <p className="text-2xl font-bold text-yellow-600">{metrics.expiring_soon}</p>
              </div>
            </div>
          </div>
          <div className="bg-card rounded-xl border border-border/60 p-4">
            <div className="flex items-center gap-3">
              <div className="h-10 w-10 rounded-xl bg-primary/10 flex items-center justify-center"><Users className="h-5 w-5 text-primary" /></div>
              <div>
                <p className="text-xs text-muted-foreground">Clientes con precio especial</p>
                <p className="text-2xl font-bold text-foreground">{metrics.customers_with_prices}</p>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Filters */}
      <div className="flex flex-wrap gap-3 items-center">
        <select value={customerFilter} onChange={e => setCustomerFilter(e.target.value)} className="rounded-xl border border-border px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400">
          <option value="">Todos los clientes</option>
          {customers.map(c => <option key={c.id} value={c.id}>{c.name} ({c.code})</option>)}
        </select>
        <select value={productFilter} onChange={e => setProductFilter(e.target.value)} className="rounded-xl border border-border px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400">
          <option value="">Todos los productos</option>
          {products.map(p => <option key={p.id} value={p.id}>{p.sku} — {p.name}</option>)}
        </select>
        <div className="flex rounded-lg overflow-hidden border border-border">
          {(['active', 'expired', 'all'] as const).map(v => (
            <button key={v} onClick={() => setActiveFilter(v)}
              className={cn('px-3 py-1.5 text-xs font-medium transition', activeFilter === v ? 'bg-blue-100 text-blue-700' : 'bg-card text-muted-foreground hover:bg-muted')}
            >
              {v === 'active' ? 'Activos' : v === 'expired' ? 'Vencidos' : 'Todos'}
            </button>
          ))}
        </div>
      </div>

      {/* Table */}
      {isLoading ? (
        <div className="flex justify-center py-20"><div className="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-600" /></div>
      ) : (
        <div className="bg-card rounded-2xl border border-border/60  overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm min-w-[900px]">
              <thead><tr className="bg-muted text-left text-xs font-semibold text-muted-foreground uppercase">
                <th className="px-6 py-3">Cliente</th>
                <th className="px-6 py-3">Producto</th>
                <th className="px-6 py-3">Variante</th>
                <th className="px-6 py-3 text-right">Precio esp.</th>
                <th className="px-6 py-3 text-right">Precio base</th>
                <th className="px-6 py-3 text-right">Ahorro %</th>
                <th className="px-6 py-3">Vigencia</th>
                <th className="px-6 py-3">Estado</th>
                <th className="px-6 py-3 text-right">Acciones</th>
              </tr></thead>
              <tbody className="divide-y divide-slate-100">
                {pagePrices.map(sp => {
                  const prod = productsMap.get(sp.product_id)
                  const basePrice = sp.base_price ?? Number(prod?.suggested_sale_price ?? 0)
                  const savingsPct = basePrice > 0 ? ((basePrice - sp.price) / basePrice * 100) : 0
                  const status = getStatus(sp)
                  return (
                    <tr key={sp.id} className="hover:bg-muted/60">
                      <td className="px-6 py-3 font-semibold text-foreground">{sp.customer_name ?? sp.customer_id.slice(0, 8)}</td>
                      <td className="px-6 py-3">
                        <span className="text-foreground">{sp.product_name ?? prod?.name ?? sp.product_id.slice(0, 8)}</span>
                        {(sp.product_sku || prod?.sku) && <span className="ml-1.5 text-xs text-muted-foreground font-mono">{sp.product_sku ?? prod?.sku}</span>}
                      </td>
                      <td className="px-6 py-3 text-xs text-muted-foreground">
                        {sp.variant_id ? (
                          <span>{sp.variant_name ?? sp.variant_sku ?? sp.variant_id.slice(0, 8)}</span>
                        ) : '—'}
                      </td>
                      <td className="px-6 py-3 text-right font-mono font-bold text-blue-700">${sp.price.toLocaleString('es-CO')}</td>
                      <td className="px-6 py-3 text-right font-mono text-muted-foreground">${basePrice.toLocaleString('es-CO')}</td>
                      <td className="px-6 py-3 text-right">
                        {savingsPct > 0 ? (
                          <span className="inline-flex rounded-full bg-emerald-50 px-2 py-0.5 text-xs font-semibold text-emerald-700">{savingsPct.toFixed(1)}%</span>
                        ) : <span className="text-slate-300">--</span>}
                      </td>
                      <td className="px-6 py-3 text-xs text-muted-foreground">
                        {new Date(sp.valid_from).toLocaleDateString('es-CO')}
                        {sp.valid_to ? ` — ${new Date(sp.valid_to).toLocaleDateString('es-CO')}` : ' — Sin limite'}
                      </td>
                      <td className="px-6 py-3"><span className={cn('px-2 py-0.5 rounded-full text-xs font-semibold', status.color)}>{status.label}</span></td>
                      <td className="px-6 py-3 text-right">
                        <div className="flex gap-1 justify-end">
                          <button onClick={() => setDetailId(sp.id)} className="p-1 text-muted-foreground hover:text-primary" title="Ver detalle">
                            <Eye className="h-3.5 w-3.5" />
                          </button>
                          {sp.is_active && (
                            <button
                              onClick={() => {
                                if (confirm('Desactivar?'))
                                  deactivateMut.mutate(sp.id, { onSuccess: () => toast.success('Desactivado'), onError: () => toast.error('Error') })
                              }}
                              className="p-1.5 text-red-400 hover:bg-red-50 rounded-lg" title="Desactivar"
                            >
                              <Trash2 className="h-4 w-4" />
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  )
                })}
                {pagePrices.length === 0 && <tr><td colSpan={9} className="px-6 py-12 text-center text-muted-foreground">Sin precios especiales</td></tr>}
              </tbody>
            </table>
          </div>
          {totalPages > 1 && (
            <div className="flex items-center justify-between px-4 py-3 border-t">
              <span className="text-sm text-muted-foreground">
                Mostrando {startIdx + 1}–{endIdx} de {prices.length}
              </span>
              <div className="flex items-center gap-1">
                <button
                  disabled={safePage <= 1}
                  onClick={() => setCurrentPage(1)}
                  className="h-8 w-8 flex items-center justify-center rounded-lg border border-border text-muted-foreground hover:bg-muted disabled:opacity-40 disabled:pointer-events-none"
                >
                  <ChevronsLeft className="w-4 h-4" />
                </button>
                <button
                  disabled={safePage <= 1}
                  onClick={() => setCurrentPage(p => p - 1)}
                  className="h-8 w-8 flex items-center justify-center rounded-lg border border-border text-muted-foreground hover:bg-muted disabled:opacity-40 disabled:pointer-events-none"
                >
                  <ChevronLeft className="w-4 h-4" />
                </button>
                <span className="px-3 text-sm text-muted-foreground">{safePage} / {totalPages}</span>
                <button
                  disabled={safePage >= totalPages}
                  onClick={() => setCurrentPage(p => p + 1)}
                  className="h-8 w-8 flex items-center justify-center rounded-lg border border-border text-muted-foreground hover:bg-muted disabled:opacity-40 disabled:pointer-events-none"
                >
                  <ChevronRight className="w-4 h-4" />
                </button>
                <button
                  disabled={safePage >= totalPages}
                  onClick={() => setCurrentPage(totalPages)}
                  className="h-8 w-8 flex items-center justify-center rounded-lg border border-border text-muted-foreground hover:bg-muted disabled:opacity-40 disabled:pointer-events-none"
                >
                  <ChevronsRight className="w-4 h-4" />
                </button>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Expiring alerts */}
      {expiringSoon.length > 0 && (
        <div className="space-y-3">
          <h2 className="text-sm font-bold text-yellow-700 flex items-center gap-2"><AlertTriangle className="h-4 w-4" /> Vencen pronto ({expiringSoon.length})</h2>
          <div className="bg-yellow-50 rounded-xl border border-yellow-200 p-4 space-y-2">
            {expiringSoon.map(sp => {
              const prod = productsMap.get(sp.product_id)
              return (
                <div key={sp.id} className="flex items-center justify-between text-sm">
                  <span>
                    <strong>{sp.customer_name ?? sp.customer_id.slice(0, 8)}</strong> —{' '}
                    {sp.product_name ?? prod?.name ?? sp.product_id.slice(0, 8)}: ${sp.price.toLocaleString('es-CO')}
                    <span className="text-xs text-yellow-600 ml-2">vence {new Date(sp.valid_to!).toLocaleDateString('es-CO')}</span>
                  </span>
                  <button
                    onClick={() => { setRenewFrom(sp); setShowCreate(true) }}
                    className="flex items-center gap-1 px-2.5 py-1 text-xs font-semibold text-yellow-700 bg-yellow-100 hover:bg-yellow-200 rounded-lg transition"
                  >
                    <RefreshCw className="h-3 w-3" /> Renovar
                  </button>
                </div>
              )
            })}
          </div>
        </div>
      )}

      {/* Detail modal */}
      {detailId && <PriceDetailModal id={detailId} onClose={() => setDetailId(null)} />}

      {/* Create / Renew modal */}
      {showCreate && (
        <CreatePriceModal
          renewFrom={renewFrom}
          customers={customers}
          products={products}
          createFormRef={createFormRef}
          validateAndSubmitPrice={validateAndSubmitPrice}
          createMut={createMut}
          onClose={() => { setShowCreate(false); setRenewFrom(null) }}
        />
      )}
    </div>
  )
}

function CreatePriceModal({
  renewFrom, customers, products, createFormRef, validateAndSubmitPrice, createMut, onClose,
}: {
  renewFrom: CustomerPrice | null
  customers: any[]
  products: any[]
  createFormRef: React.RefObject<HTMLFormElement | null>
  validateAndSubmitPrice: (e: React.FormEvent) => void
  createMut: { isPending: boolean }
  onClose: () => void
}) {
  const [selectedProductId, setSelectedProductId] = useState(renewFrom?.product_id ?? '')
  const { data: variantsData } = useProductVariantsForProduct(selectedProductId || undefined)
  const variants = variantsData?.items ?? variantsData ?? []

  const cls = 'w-full px-3 py-2 text-sm border border-border rounded-xl focus:ring-2 focus:ring-blue-500/20 focus:border-blue-400 outline-none'

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40" onClick={onClose}>
      <div className="bg-card rounded-2xl shadow-2xl w-full max-w-lg mx-4 p-6" onClick={e => e.stopPropagation()}>
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-bold text-foreground">{renewFrom ? 'Renovar Precio Especial' : 'Nuevo Precio Especial'}</h3>
          <button onClick={onClose} className="p-1 text-muted-foreground hover:text-muted-foreground"><X className="h-5 w-5" /></button>
        </div>
        <form ref={createFormRef} onSubmit={validateAndSubmitPrice} noValidate className="space-y-3">
          <div>
            <label className="block text-xs font-medium text-muted-foreground mb-1">Cliente *</label>
            <select name="customer_id" required defaultValue={renewFrom?.customer_id ?? ''} className={cls}>
              <option value="">Seleccionar cliente</option>
              {customers.map(c => <option key={c.id} value={c.id}>{c.name} ({c.code})</option>)}
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-muted-foreground mb-1">Producto *</label>
            <select
              name="product_id"
              required
              value={selectedProductId}
              onChange={e => setSelectedProductId(e.target.value)}
              className={cls}
            >
              <option value="">Seleccionar producto</option>
              {products.map(p => <option key={p.id} value={p.id}>{p.sku} — {p.name} (${Number(p.suggested_sale_price ?? 0).toLocaleString('es-CO')})</option>)}
            </select>
          </div>
          {Array.isArray(variants) && variants.length > 0 && (
            <div>
              <label className="block text-xs font-medium text-muted-foreground mb-1">Variante</label>
              <select name="variant_id" defaultValue={(renewFrom as any)?.variant_id ?? ''} className={cls}>
                <option value="">Todas las variantes (precio general)</option>
                {variants.map((v: any) => (
                  <option key={v.id} value={v.id}>{v.sku} — {v.name ?? v.attribute_values?.map((a: any) => a.value).join(', ')}</option>
                ))}
              </select>
              <p className="text-[10px] text-muted-foreground mt-1">Si seleccionas una variante, el precio aplica solo a esa variante. Si lo dejas vacio, aplica al producto completo.</p>
            </div>
          )}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium text-muted-foreground mb-1">Precio especial ($) *</label>
              <input name="price" type="number" step="0.01" required defaultValue={renewFrom?.price ?? ''} className={cls} />
            </div>
            <div>
              <label className="block text-xs font-medium text-muted-foreground mb-1">Cantidad minima</label>
              <input name="min_quantity" type="number" min={1} defaultValue={renewFrom?.min_quantity ?? 1} className={cls} />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium text-muted-foreground mb-1">Vigente desde</label>
              <input name="valid_from" type="date" defaultValue={new Date().toISOString().slice(0, 10)} className={cls} />
            </div>
            <div>
              <label className="block text-xs font-medium text-muted-foreground mb-1">Vigente hasta</label>
              <input name="valid_to" type="date" className={cls} />
            </div>
          </div>
          <div>
            <label className="block text-xs font-medium text-muted-foreground mb-1">Motivo</label>
            <input name="reason" defaultValue={renewFrom?.reason ?? ''} className={cls} placeholder="Ej: Renovacion acuerdo 2026" />
          </div>
          <div className="flex justify-end gap-2 pt-2">
            <button type="button" onClick={onClose} className="px-4 py-2 text-sm text-muted-foreground hover:bg-secondary rounded-xl transition">Cancelar</button>
            <button type="submit" disabled={createMut.isPending} className="px-5 py-2 text-sm font-semibold text-white bg-blue-600 hover:bg-blue-700 rounded-xl disabled:opacity-50 transition">{renewFrom ? 'Renovar' : 'Crear'}</button>
          </div>
        </form>
      </div>
    </div>
  )
}

function PriceDetailModal({ id, onClose }: { id: string; onClose: () => void }) {
  const { data: detail, isLoading } = useCustomerPriceDetail(id)

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 backdrop-blur-sm" onClick={onClose}>
      <div className="w-full max-w-lg bg-card rounded-3xl shadow-2xl p-6 max-h-[90vh] overflow-y-auto" onClick={e => e.stopPropagation()}>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-bold text-foreground">Detalle de Precio Especial</h2>
          <button onClick={onClose} className="p-1 text-muted-foreground hover:text-muted-foreground"><X className="h-5 w-5" /></button>
        </div>

        {isLoading ? (
          <div className="flex justify-center py-12"><div className="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-600" /></div>
        ) : !detail ? (
          <p className="text-center text-muted-foreground py-8">No se encontro el detalle</p>
        ) : (
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-3">
              <div>
                <p className="text-xs text-muted-foreground">Cliente</p>
                <p className="text-sm font-semibold text-foreground">{detail.customer_name ?? detail.customer_id?.slice(0, 8)}</p>
              </div>
              <div>
                <p className="text-xs text-muted-foreground">Producto</p>
                <p className="text-sm font-semibold text-foreground">{detail.product_name ?? detail.product_id?.slice(0, 8)}</p>
                {detail.variant_id && <p className="text-xs text-muted-foreground mt-0.5">Variante: {detail.variant_name ?? detail.variant_id.slice(0, 8)}</p>}
              </div>
              <div>
                <p className="text-xs text-muted-foreground">Precio especial</p>
                <p className="text-sm font-bold text-blue-700">${detail.price?.toLocaleString('es-CO')}</p>
              </div>
              <div>
                <p className="text-xs text-muted-foreground">Cantidad minima</p>
                <p className="text-sm text-foreground">{detail.min_quantity ?? 1}</p>
              </div>
              <div>
                <p className="text-xs text-muted-foreground">Vigente desde</p>
                <p className="text-sm text-foreground">{detail.valid_from ? new Date(detail.valid_from).toLocaleDateString('es-CO') : '--'}</p>
              </div>
              <div>
                <p className="text-xs text-muted-foreground">Vigente hasta</p>
                <p className="text-sm text-foreground">{detail.valid_to ? new Date(detail.valid_to).toLocaleDateString('es-CO') : 'Sin limite'}</p>
              </div>
            </div>

            {detail.reason && (
              <div>
                <p className="text-xs text-muted-foreground">Motivo</p>
                <p className="text-sm text-foreground">{detail.reason}</p>
              </div>
            )}

            {/* Price change history */}
            {detail.history && detail.history.length > 0 && (
              <div>
                <h3 className="text-sm font-bold text-foreground flex items-center gap-1.5 mb-3">
                  <History className="h-4 w-4 text-muted-foreground" /> Historial de cambios
                </h3>
                <div className="space-y-2">
                  {detail.history.map((h: any, idx: number) => (
                    <div key={idx} className="flex items-center gap-3 text-sm border-l-2 border-primary/30 pl-3 py-1">
                      <div className="flex-1">
                        <span className="font-mono text-muted-foreground">${h.old_price?.toLocaleString('es-CO')}</span>
                        <span className="mx-1.5 text-slate-300">&rarr;</span>
                        <span className="font-mono font-semibold text-primary">${h.new_price?.toLocaleString('es-CO')}</span>
                        {h.reason && <span className="ml-2 text-xs text-muted-foreground">({h.reason})</span>}
                      </div>
                      <span className="text-xs text-muted-foreground whitespace-nowrap">
                        {h.changed_at ? new Date(h.changed_at).toLocaleDateString('es-CO') : ''}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
