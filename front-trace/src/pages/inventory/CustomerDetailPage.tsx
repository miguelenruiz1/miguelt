import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { ArrowLeft, Pencil, ShoppingBag, DollarSign, Mail, Phone, Building2, X, ExternalLink, Plus, Trash2, Clock, AlertTriangle } from 'lucide-react'
import { cn } from '@/lib/utils'
import {
  useCustomer, useCustomerTypes, useUpdateCustomer, useSalesOrders,
  useCustomerPricesForCustomer, useCreateCustomerPrice, useDeactivateCustomerPrice,
  useCustomerPriceHistory, useProducts,
} from '@/hooks/useInventory'
import { useToast } from '@/store/toast'
import type { SalesOrderStatus, Customer, CustomerPrice } from '@/types/inventory'

const STATUS_CONFIG: Record<SalesOrderStatus, { label: string; color: string }> = {
  draft: { label: 'Borrador', color: 'bg-slate-100 text-slate-600' },
  confirmed: { label: 'Confirmada', color: 'bg-blue-50 text-blue-700' },
  picking: { label: 'Picking', color: 'bg-amber-50 text-amber-700' },
  shipped: { label: 'Enviada', color: 'bg-indigo-50 text-indigo-700' },
  delivered: { label: 'Entregada', color: 'bg-emerald-50 text-emerald-700' },
  returned: { label: 'Devuelta', color: 'bg-orange-50 text-orange-600' },
  canceled: { label: 'Cancelada', color: 'bg-red-50 text-red-600' },
}

export function CustomerDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const toast = useToast()
  const [showEdit, setShowEdit] = useState(false)
  const [showAddPrice, setShowAddPrice] = useState(false)
  const { data: customer, isLoading } = useCustomer(id ?? '')
  const { data: types } = useCustomerTypes()
  const { data: ordersData } = useSalesOrders({ customer_id: id, limit: 50 })
  const updateMut = useUpdateCustomer()
  const { data: specialPrices = [] } = useCustomerPricesForCustomer(id ?? '')
  const { data: priceHistoryData = [] } = useCustomerPriceHistory({ customer_id: id })
  const { data: productsData } = useProducts({ limit: 200 })
  const createPriceMut = useCreateCustomerPrice()
  const deactivatePriceMut = useDeactivateCustomerPrice()
  const products = productsData?.items ?? []
  const productsMap = new Map(products.map(p => [p.id, p]))

  if (isLoading) return <div className="flex justify-center py-20"><div className="animate-spin rounded-full h-6 w-6 border-b-2 border-indigo-600" /></div>
  if (!customer) return <p className="text-center text-slate-400 py-20">Cliente no encontrado</p>

  const orders = ordersData?.items ?? []
  const typeName = types?.find(t => t.id === customer.customer_type_id)?.name

  const totalSales = orders.filter(o => o.status === 'delivered').reduce((sum, o) => sum + o.total, 0)
  const activeOrders = orders.filter(o => !['delivered', 'returned', 'canceled'].includes(o.status)).length

  return (
    <div className="space-y-6">
      <button onClick={() => navigate('/inventario/clientes')} className="flex items-center gap-1 text-sm text-slate-500 hover:text-slate-900"><ArrowLeft className="h-4 w-4" /> Clientes</button>

      {/* Header */}
      <div className="bg-white rounded-2xl border border-slate-200/60 shadow-sm p-6">
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-4">
            <div className="h-14 w-14 rounded-2xl bg-indigo-100 flex items-center justify-center">
              <Building2 className="h-7 w-7 text-indigo-600" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-slate-900">{customer.name}</h1>
              <div className="flex items-center gap-3 mt-1 text-sm text-slate-500">
                <span className="font-mono">{customer.code}</span>
                {typeName && <span className="px-2 py-0.5 bg-indigo-50 text-indigo-600 rounded-full text-xs font-semibold">{typeName}</span>}
                {customer.tax_id && <span>NIT: {customer.tax_id}</span>}
              </div>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => navigate(`/inventario/portal/${customer.id}`)}
              className="flex items-center gap-1.5 rounded-lg border border-indigo-200 bg-indigo-50 px-3 py-1.5 text-xs font-semibold text-indigo-700 hover:bg-indigo-100 transition-colors"
            >
              <ExternalLink className="h-3.5 w-3.5" /> Ver Portal
            </button>
            <button onClick={() => setShowEdit(true)} className="p-2 text-slate-400 hover:text-indigo-600 hover:bg-indigo-50 rounded-lg"><Pencil className="h-4 w-4" /></button>
          </div>
        </div>
      </div>

      {/* KPIs */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <div className="bg-white rounded-xl border border-slate-200/60 p-4">
          <p className="text-xs text-slate-400 mb-1">Total Ventas</p>
          <p className="text-xl font-bold text-emerald-600">${totalSales.toLocaleString()}</p>
        </div>
        <div className="bg-white rounded-xl border border-slate-200/60 p-4">
          <p className="text-xs text-slate-400 mb-1">Ordenes Activas</p>
          <p className="text-xl font-bold text-indigo-600">{activeOrders}</p>
        </div>
        <div className="bg-white rounded-xl border border-slate-200/60 p-4">
          <p className="text-xs text-slate-400 mb-1">Terminos de Pago</p>
          <p className="text-xl font-bold">{customer.payment_terms_days} dias</p>
        </div>
        <div className="bg-white rounded-xl border border-slate-200/60 p-4">
          <p className="text-xs text-slate-400 mb-1">Limite de Credito</p>
          <p className="text-xl font-bold">${customer.credit_limit.toLocaleString()}</p>
        </div>
      </div>

      {/* Contact info */}
      <div className="bg-white rounded-2xl border border-slate-200/60 shadow-sm p-6 grid grid-cols-1 sm:grid-cols-3 gap-4">
        {customer.contact_name && (
          <div className="flex items-center gap-2 text-sm"><Building2 className="h-4 w-4 text-slate-400" /> <span className="text-slate-700">{customer.contact_name}</span></div>
        )}
        {customer.email && (
          <div className="flex items-center gap-2 text-sm"><Mail className="h-4 w-4 text-slate-400" /> <span className="text-slate-700">{customer.email}</span></div>
        )}
        {customer.phone && (
          <div className="flex items-center gap-2 text-sm"><Phone className="h-4 w-4 text-slate-400" /> <span className="text-slate-700">{customer.phone}</span></div>
        )}
        {customer.discount_percent > 0 && (
          <div className="flex items-center gap-2 text-sm"><DollarSign className="h-4 w-4 text-slate-400" /> <span className="text-slate-700">Descuento: {customer.discount_percent}%</span></div>
        )}
      </div>

      {customer.notes && (
        <div className="bg-white rounded-xl border border-slate-200/60 p-4">
          <p className="text-xs font-bold text-slate-400 uppercase mb-2">Notas</p>
          <p className="text-sm text-slate-700">{customer.notes}</p>
        </div>
      )}

      {/* Sales orders table */}
      <div className="space-y-3">
        <h2 className="text-lg font-bold text-slate-900 flex items-center gap-2"><ShoppingBag className="h-5 w-5 text-indigo-500" /> Ordenes de Venta</h2>
        <div className="bg-white rounded-2xl border border-slate-200/60 shadow-sm overflow-hidden">
          <div className="overflow-x-auto">
          <table className="w-full text-sm min-w-[600px]">
            <thead><tr className="bg-slate-50 text-left text-xs font-semibold text-slate-500 uppercase">
              <th className="px-6 py-3"># Orden</th>
              <th className="px-6 py-3">Estado</th>
              <th className="px-6 py-3 text-right">Total</th>
              <th className="px-6 py-3">Fecha</th>
            </tr></thead>
            <tbody className="divide-y divide-slate-100">
              {orders.map(o => (
                <tr key={o.id} className="hover:bg-slate-50/60 cursor-pointer" onClick={() => navigate(`/inventario/ventas/${o.id}`)}>
                  <td className="px-6 py-3 font-mono text-xs">{o.order_number}</td>
                  <td className="px-6 py-3"><span className={cn('px-2 py-0.5 rounded-full text-xs font-semibold', STATUS_CONFIG[o.status]?.color)}>{STATUS_CONFIG[o.status]?.label}</span></td>
                  <td className="px-6 py-3 text-right font-mono">${o.total.toLocaleString()}</td>
                  <td className="px-6 py-3 text-xs text-slate-400">{o.created_at ? new Date(o.created_at).toLocaleDateString() : ''}</td>
                </tr>
              ))}
              {orders.length === 0 && <tr><td colSpan={4} className="px-6 py-12 text-center text-slate-400">Sin ordenes para este cliente</td></tr>}
            </tbody>
          </table>
          </div>
        </div>
      </div>

      {/* Special Prices Section */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-bold text-slate-900 flex items-center gap-2"><DollarSign className="h-5 w-5 text-blue-500" /> Precios Especiales</h2>
          <button onClick={() => setShowAddPrice(true)} className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold text-white bg-blue-600 hover:bg-blue-700 rounded-lg transition">
            <Plus className="h-3.5 w-3.5" /> Agregar precio especial
          </button>
        </div>
        <div className="bg-white rounded-2xl border border-slate-200/60 shadow-sm overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm min-w-[800px]">
              <thead><tr className="bg-slate-50 text-left text-xs font-semibold text-slate-500 uppercase">
                <th className="px-6 py-3">Producto</th>
                <th className="px-6 py-3 text-right">Precio especial</th>
                <th className="px-6 py-3 text-right">Precio base</th>
                <th className="px-6 py-3 text-right">Descuento %</th>
                <th className="px-6 py-3 text-right">Cant. minima</th>
                <th className="px-6 py-3">Vigente hasta</th>
                <th className="px-6 py-3">Motivo</th>
                <th className="px-6 py-3 text-right">Acciones</th>
              </tr></thead>
              <tbody className="divide-y divide-slate-100">
                {specialPrices.filter(sp => sp.is_active).map(sp => {
                  const prod = productsMap.get(sp.product_id)
                  const basePrice = Number(prod?.sale_price ?? 0)
                  const discountPct = basePrice > 0 ? ((basePrice - sp.price) / basePrice * 100) : 0
                  const now = new Date()
                  const validTo = sp.valid_to ? new Date(sp.valid_to) : null
                  const isExpired = validTo && validTo < now
                  const isExpiringSoon = validTo && !isExpired && (validTo.getTime() - now.getTime()) < 30 * 24 * 60 * 60 * 1000
                  return (
                    <tr key={sp.id} className="hover:bg-slate-50/60">
                      <td className="px-6 py-3">
                        <span className="font-semibold text-slate-900">{sp.product_name ?? prod?.name ?? sp.product_id.slice(0, 8)}</span>
                        {sp.product_sku && <span className="ml-1.5 text-xs text-slate-400 font-mono">{sp.product_sku}</span>}
                      </td>
                      <td className="px-6 py-3 text-right font-mono font-bold text-blue-700">${sp.price.toLocaleString()}</td>
                      <td className="px-6 py-3 text-right font-mono text-slate-500">${basePrice.toLocaleString()}</td>
                      <td className="px-6 py-3 text-right">
                        {discountPct > 0 ? (
                          <span className="inline-flex rounded-full bg-emerald-50 px-2 py-0.5 text-xs font-semibold text-emerald-700">{discountPct.toFixed(1)}%</span>
                        ) : <span className="text-slate-300">--</span>}
                      </td>
                      <td className="px-6 py-3 text-right text-slate-600">{sp.min_quantity}</td>
                      <td className="px-6 py-3 text-sm">
                        {validTo ? (
                          <span className="flex items-center gap-1.5">
                            {validTo.toLocaleDateString()}
                            {isExpired && <span className="inline-flex rounded-full bg-red-50 px-1.5 py-0.5 text-[10px] font-bold text-red-600">Vencido</span>}
                            {isExpiringSoon && <span className="inline-flex rounded-full bg-yellow-50 px-1.5 py-0.5 text-[10px] font-bold text-yellow-700">Vence pronto</span>}
                          </span>
                        ) : <span className="text-slate-300">Sin limite</span>}
                      </td>
                      <td className="px-6 py-3 text-sm text-slate-500 max-w-[150px] truncate" title={sp.reason ?? ''}>{sp.reason ?? '--'}</td>
                      <td className="px-6 py-3 text-right">
                        <button
                          onClick={() => {
                            if (confirm('Desactivar este precio especial?'))
                              deactivatePriceMut.mutate(sp.id, { onSuccess: () => toast.success('Precio desactivado'), onError: () => toast.error('Error al desactivar') })
                          }}
                          className="p-1.5 text-red-400 hover:bg-red-50 rounded-lg" title="Desactivar"
                        >
                          <Trash2 className="h-4 w-4" />
                        </button>
                      </td>
                    </tr>
                  )
                })}
                {specialPrices.filter(sp => sp.is_active).length === 0 && (
                  <tr><td colSpan={8} className="px-6 py-12 text-center text-slate-400">Sin precios especiales activos para este cliente</td></tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* Price History Timeline */}
      {priceHistoryData.length > 0 && (
        <div className="space-y-3">
          <h3 className="text-sm font-bold text-slate-700 flex items-center gap-2"><Clock className="h-4 w-4 text-slate-400" /> Historial de Precios</h3>
          <div className="bg-white rounded-xl border border-slate-200/60 p-4 space-y-3">
            {priceHistoryData.map(h => {
              const prod = productsMap.get(h.product_id)
              return (
                <div key={h.id} className="flex items-start gap-3 text-sm border-l-2 border-slate-200 pl-3">
                  <span className="text-xs text-slate-400 whitespace-nowrap">{new Date(h.changed_at).toLocaleDateString()}</span>
                  <span className="text-slate-700">
                    <strong>{prod?.name ?? h.product_id.slice(0, 8)}</strong>:
                    {h.old_price !== null ? (
                      <> <span className="text-red-500 line-through">${h.old_price.toLocaleString()}</span> <span className="mx-1">→</span></>
                    ) : ' Nuevo: '}
                    <span className="text-emerald-600 font-semibold">${h.new_price.toLocaleString()}</span>
                    {h.changed_by_name && <span className="text-slate-400"> por {h.changed_by_name}</span>}
                    {h.reason && <span className="italic text-slate-400"> — "{h.reason}"</span>}
                  </span>
                </div>
              )
            })}
          </div>
        </div>
      )}

      {/* Add Special Price Modal */}
      {showAddPrice && id && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40" onClick={() => setShowAddPrice(false)}>
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-lg mx-4 p-6" onClick={e => e.stopPropagation()}>
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-bold text-slate-900">Agregar Precio Especial</h3>
              <button onClick={() => setShowAddPrice(false)} className="p-1 text-slate-400 hover:text-slate-600"><X className="h-5 w-5" /></button>
            </div>
            <form onSubmit={async (e) => {
              e.preventDefault()
              const fd = new FormData(e.currentTarget)
              await createPriceMut.mutateAsync({
                customer_id: id,
                product_id: fd.get('product_id') as string,
                price: Number(fd.get('price')),
                min_quantity: Number(fd.get('min_quantity') || 1),
                valid_from: (fd.get('valid_from') as string) || new Date().toISOString().slice(0, 10),
                valid_to: (fd.get('valid_to') as string) || null,
                reason: (fd.get('reason') as string) || null,
              } as Partial<CustomerPrice>)
              toast.success('Precio especial creado')
              setShowAddPrice(false)
            }} className="space-y-3">
              <div>
                <label className="block text-xs font-medium text-slate-600 mb-1">Producto *</label>
                <select name="product_id" required className="w-full px-3 py-2 text-sm border border-slate-200 rounded-xl focus:ring-2 focus:ring-blue-500/20 focus:border-blue-400 outline-none">
                  <option value="">Seleccionar producto</option>
                  {products.map(p => <option key={p.id} value={p.id}>{p.sku} — {p.name} (${Number(p.sale_price).toLocaleString()})</option>)}
                </select>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-slate-600 mb-1">Precio especial ($) *</label>
                  <input name="price" type="number" step="0.01" required className="w-full px-3 py-2 text-sm border border-slate-200 rounded-xl focus:ring-2 focus:ring-blue-500/20 focus:border-blue-400 outline-none" />
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-600 mb-1">Cantidad minima</label>
                  <input name="min_quantity" type="number" min={1} defaultValue={1} className="w-full px-3 py-2 text-sm border border-slate-200 rounded-xl focus:ring-2 focus:ring-blue-500/20 focus:border-blue-400 outline-none" />
                </div>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-slate-600 mb-1">Vigente desde</label>
                  <input name="valid_from" type="date" defaultValue={new Date().toISOString().slice(0, 10)} className="w-full px-3 py-2 text-sm border border-slate-200 rounded-xl focus:ring-2 focus:ring-blue-500/20 focus:border-blue-400 outline-none" />
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-600 mb-1">Vigente hasta</label>
                  <input name="valid_to" type="date" className="w-full px-3 py-2 text-sm border border-slate-200 rounded-xl focus:ring-2 focus:ring-blue-500/20 focus:border-blue-400 outline-none" />
                </div>
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-600 mb-1">Motivo</label>
                <input name="reason" className="w-full px-3 py-2 text-sm border border-slate-200 rounded-xl focus:ring-2 focus:ring-blue-500/20 focus:border-blue-400 outline-none" placeholder="Ej: Acuerdo comercial 2026" />
              </div>
              <div className="flex justify-end gap-2 pt-2">
                <button type="button" onClick={() => setShowAddPrice(false)} className="px-4 py-2 text-sm text-slate-600 hover:bg-slate-100 rounded-xl transition">Cancelar</button>
                <button type="submit" disabled={createPriceMut.isPending} className="px-5 py-2 text-sm font-semibold text-white bg-blue-600 hover:bg-blue-700 rounded-xl disabled:opacity-50 transition">Guardar</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Edit modal */}
      {showEdit && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40" onClick={() => setShowEdit(false)}>
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-lg mx-4 p-6" onClick={e => e.stopPropagation()}>
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-bold text-slate-900">Editar Cliente</h3>
              <button onClick={() => setShowEdit(false)} className="p-1 text-slate-400 hover:text-slate-600"><X className="h-5 w-5" /></button>
            </div>
            <form onSubmit={async (e) => {
              e.preventDefault()
              const fd = new FormData(e.currentTarget)
              await updateMut.mutateAsync({
                id: customer.id,
                data: {
                  name: fd.get('name') as string,
                  code: fd.get('code') as string,
                  tax_id: (fd.get('tax_id') as string) || undefined,
                  customer_type_id: (fd.get('customer_type_id') as string) || undefined,
                  contact_name: (fd.get('contact_name') as string) || undefined,
                  email: (fd.get('email') as string) || undefined,
                  phone: (fd.get('phone') as string) || undefined,
                  payment_terms_days: Number(fd.get('payment_terms_days') || 30),
                  credit_limit: Number(fd.get('credit_limit') || 0),
                  notes: (fd.get('notes') as string) || undefined,
                } as Partial<Customer>,
              })
              setShowEdit(false)
            }} className="space-y-3">
              <div className="grid grid-cols-2 gap-3">
                <div><label className="block text-xs font-medium text-slate-600 mb-1">Nombre *</label><input name="name" required defaultValue={customer.name} className="w-full px-3 py-2 text-sm border border-slate-200 rounded-xl focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-400 outline-none" /></div>
                <div><label className="block text-xs font-medium text-slate-600 mb-1">Codigo *</label><input name="code" required defaultValue={customer.code} className="w-full px-3 py-2 text-sm border border-slate-200 rounded-xl focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-400 outline-none" /></div>
                <div><label className="block text-xs font-medium text-slate-600 mb-1">NIT / CC</label><input name="tax_id" defaultValue={customer.tax_id ?? ''} className="w-full px-3 py-2 text-sm border border-slate-200 rounded-xl focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-400 outline-none" /></div>
                <div><label className="block text-xs font-medium text-slate-600 mb-1">Tipo</label><select name="customer_type_id" defaultValue={customer.customer_type_id ?? ''} className="w-full px-3 py-2 text-sm border border-slate-200 rounded-xl focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-400 outline-none"><option value="">Sin tipo</option>{(types ?? []).map(t => <option key={t.id} value={t.id}>{t.name}</option>)}</select></div>
                <div><label className="block text-xs font-medium text-slate-600 mb-1">Contacto</label><input name="contact_name" defaultValue={customer.contact_name ?? ''} className="w-full px-3 py-2 text-sm border border-slate-200 rounded-xl focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-400 outline-none" /></div>
                <div><label className="block text-xs font-medium text-slate-600 mb-1">Email</label><input name="email" type="email" defaultValue={customer.email ?? ''} className="w-full px-3 py-2 text-sm border border-slate-200 rounded-xl focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-400 outline-none" /></div>
                <div><label className="block text-xs font-medium text-slate-600 mb-1">Telefono</label><input name="phone" defaultValue={customer.phone ?? ''} className="w-full px-3 py-2 text-sm border border-slate-200 rounded-xl focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-400 outline-none" /></div>
                <div><label className="block text-xs font-medium text-slate-600 mb-1">Dias de pago</label><input name="payment_terms_days" type="number" defaultValue={customer.payment_terms_days ?? 30} className="w-full px-3 py-2 text-sm border border-slate-200 rounded-xl focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-400 outline-none" /></div>
                <div><label className="block text-xs font-medium text-slate-600 mb-1">Limite credito</label><input name="credit_limit" type="number" defaultValue={customer.credit_limit ?? 0} className="w-full px-3 py-2 text-sm border border-slate-200 rounded-xl focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-400 outline-none" /></div>
              </div>
              <div><label className="block text-xs font-medium text-slate-600 mb-1">Notas</label><textarea name="notes" rows={2} defaultValue={customer.notes ?? ''} className="w-full px-3 py-2 text-sm border border-slate-200 rounded-xl focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-400 outline-none resize-none" /></div>
              <div className="flex justify-end gap-2 pt-2">
                <button type="button" onClick={() => setShowEdit(false)} className="px-4 py-2 text-sm text-slate-600 hover:bg-slate-100 rounded-xl transition">Cancelar</button>
                <button type="submit" disabled={updateMut.isPending} className="px-5 py-2 text-sm font-semibold text-white bg-indigo-600 hover:bg-indigo-700 rounded-xl disabled:opacity-50 transition">Guardar</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
