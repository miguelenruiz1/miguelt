import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import {
  ArrowLeft, Pencil, Building2, Mail, Phone, MapPin, Truck, ShoppingBag,
  X, CreditCard, Clock, DollarSign, FileText, ShoppingCart,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import {
  usePartner, useUpdatePartner, useSupplierTypes, useCustomerTypes,
  usePurchaseOrders, useSalesOrders,
} from '@/hooks/useInventory'
import { useToast } from '@/store/toast'
import type { BusinessPartner } from '@/types/inventory'

function fmtAddress(addr: Record<string, unknown> | null | undefined): string | null {
  if (!addr) return null
  const parts = [addr.line1, addr.line2, addr.city, addr.state, addr.zip, addr.country].filter(Boolean)
  return parts.length > 0 ? parts.join(', ') : null
}

export function PartnerDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const toast = useToast()
  const [showEdit, setShowEdit] = useState(false)

  const { data: partner, isLoading } = usePartner(id ?? '')
  const { data: supplierTypes } = useSupplierTypes()
  const { data: customerTypes } = useCustomerTypes()
  const updateMut = useUpdatePartner()

  const { data: posData } = usePurchaseOrders(partner?.is_supplier ? { supplier_id: id, limit: 20 } : undefined)
  const { data: sosData } = useSalesOrders(partner?.is_customer ? { customer_id: id, limit: 20 } : undefined)

  const pos = posData?.items ?? []
  const sos = sosData?.items ?? []

  if (isLoading) return <div className="flex justify-center py-20"><div className="animate-spin rounded-full h-6 w-6 border-b-2 border-primary" /></div>
  if (!partner) return <p className="text-center text-slate-400 py-20">Socio no encontrado</p>

  const supplierTypeName = (supplierTypes as any)?.items?.find((t: any) => t.id === partner.supplier_type_id)?.name
  const customerTypeName = (customerTypes as any)?.items?.find((t: any) => t.id === partner.customer_type_id)?.name
  const addressStr = fmtAddress(partner.address)
  const shippingStr = fmtAddress(partner.shipping_address)

  const roleBadges = (
    <div className="flex gap-2">
      {partner.is_supplier && (
        <span className="inline-flex items-center gap-1 px-2.5 py-1 bg-blue-50 text-blue-700 rounded-full text-xs font-semibold">
          <Truck className="h-3 w-3" /> Proveedor{supplierTypeName ? ` — ${supplierTypeName}` : ''}
        </span>
      )}
      {partner.is_customer && (
        <span className="inline-flex items-center gap-1 px-2.5 py-1 bg-green-50 text-green-700 rounded-full text-xs font-semibold">
          <ShoppingBag className="h-3 w-3" /> Cliente{customerTypeName ? ` — ${customerTypeName}` : ''}
        </span>
      )}
    </div>
  )

  return (
    <div className="space-y-6">
      <button onClick={() => navigate('/inventario/socios')} className="flex items-center gap-1 text-sm text-slate-500 hover:text-slate-900">
        <ArrowLeft className="h-4 w-4" /> Socios Comerciales
      </button>

      {/* Header */}
      <div className="bg-white rounded-2xl border border-slate-200/60 shadow-sm p-6">
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-4">
            <div className="h-14 w-14 rounded-2xl bg-primary/15 flex items-center justify-center">
              <Building2 className="h-7 w-7 text-primary" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-slate-900">{partner.name}</h1>
              <div className="flex items-center gap-3 mt-1 text-sm text-slate-500">
                <span className="font-mono">{partner.code}</span>
                {partner.tax_id && <span>NIT: {partner.tax_id}</span>}
                {!partner.is_active && <span className="px-2 py-0.5 bg-red-100 text-red-600 rounded-full text-xs font-semibold">Inactivo</span>}
              </div>
              <div className="mt-2">{roleBadges}</div>
            </div>
          </div>
          <button onClick={() => setShowEdit(true)} className="p-2 text-slate-400 hover:text-primary hover:bg-primary/10 rounded-lg">
            <Pencil className="h-4 w-4" />
          </button>
        </div>
      </div>

      {/* KPIs */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <div className="bg-white rounded-xl border border-slate-200/60 p-4">
          <p className="text-xs text-slate-400 mb-1">Terminos de Pago</p>
          <p className="text-xl font-bold">{partner.payment_terms_days} dias</p>
        </div>
        {partner.is_supplier && (
          <div className="bg-white rounded-xl border border-slate-200/60 p-4">
            <p className="text-xs text-slate-400 mb-1">Lead Time</p>
            <p className="text-xl font-bold text-blue-600">{partner.lead_time_days} dias</p>
          </div>
        )}
        {partner.is_customer && (
          <>
            <div className="bg-white rounded-xl border border-slate-200/60 p-4">
              <p className="text-xs text-slate-400 mb-1">Limite de Credito</p>
              <p className="text-xl font-bold text-emerald-600">${partner.credit_limit.toLocaleString()}</p>
            </div>
            <div className="bg-white rounded-xl border border-slate-200/60 p-4">
              <p className="text-xs text-slate-400 mb-1">Descuento</p>
              <p className="text-xl font-bold">{partner.discount_percent}%</p>
            </div>
          </>
        )}
      </div>

      {/* Contact & Address */}
      <div className="bg-white rounded-2xl border border-slate-200/60 shadow-sm p-6">
        <h2 className="text-sm font-bold text-slate-400 uppercase tracking-wider mb-4">Informacion de Contacto</h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {partner.contact_name && (
            <div className="flex items-center gap-2 text-sm"><Building2 className="h-4 w-4 text-slate-400 shrink-0" /> <span className="text-slate-700">{partner.contact_name}</span></div>
          )}
          {partner.email && (
            <div className="flex items-center gap-2 text-sm"><Mail className="h-4 w-4 text-slate-400 shrink-0" /> <a href={`mailto:${partner.email}`} className="text-primary hover:underline">{partner.email}</a></div>
          )}
          {partner.phone && (
            <div className="flex items-center gap-2 text-sm"><Phone className="h-4 w-4 text-slate-400 shrink-0" /> <span className="text-slate-700">{partner.phone}</span></div>
          )}
        </div>
        {(addressStr || shippingStr) && (
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mt-4 pt-4 border-t border-slate-100">
            {addressStr && (
              <div>
                <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1">Direccion</p>
                <div className="flex items-start gap-2 text-sm text-slate-700">
                  <MapPin className="h-4 w-4 text-slate-400 shrink-0 mt-0.5" />
                  <span>{addressStr}</span>
                </div>
              </div>
            )}
            {shippingStr && (
              <div>
                <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1">Direccion de Envio</p>
                <div className="flex items-start gap-2 text-sm text-slate-700">
                  <MapPin className="h-4 w-4 text-emerald-400 shrink-0 mt-0.5" />
                  <span>{shippingStr}</span>
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      {partner.notes && (
        <div className="bg-white rounded-xl border border-slate-200/60 p-4">
          <p className="text-xs font-bold text-slate-400 uppercase mb-2">Notas</p>
          <p className="text-sm text-slate-700 whitespace-pre-wrap">{partner.notes}</p>
        </div>
      )}

      {/* Purchase Orders (supplier) */}
      {partner.is_supplier && (
        <div className="space-y-3">
          <h2 className="text-lg font-bold text-slate-900 flex items-center gap-2"><ShoppingCart className="h-5 w-5 text-blue-500" /> Ordenes de Compra</h2>
          <div className="bg-white rounded-2xl border border-slate-200/60 shadow-sm overflow-hidden">
            <table className="w-full text-sm">
              <thead><tr className="bg-slate-50 text-left text-xs font-semibold text-slate-500 uppercase">
                <th className="px-6 py-3"># Orden</th>
                <th className="px-6 py-3">Estado</th>
                <th className="px-6 py-3 text-right">Total</th>
                <th className="px-6 py-3">Fecha</th>
              </tr></thead>
              <tbody className="divide-y divide-slate-100">
                {pos.map(o => (
                  <tr key={o.id} className="hover:bg-slate-50/60 cursor-pointer" onClick={() => navigate(`/inventario/compras/${o.id}`)}>
                    <td className="px-6 py-3 font-mono text-xs">{o.po_number}</td>
                    <td className="px-6 py-3"><span className={cn('px-2 py-0.5 rounded-full text-xs font-semibold',
                      o.status === 'received' ? 'bg-emerald-50 text-emerald-700' :
                      o.status === 'canceled' ? 'bg-red-50 text-red-600' :
                      'bg-slate-100 text-slate-600'
                    )}>{o.status}</span></td>
                    <td className="px-6 py-3 text-right font-mono">${Number(o.total ?? 0).toLocaleString()}</td>
                    <td className="px-6 py-3 text-xs text-slate-400">{o.created_at ? new Date(o.created_at).toLocaleDateString() : ''}</td>
                  </tr>
                ))}
                {pos.length === 0 && <tr><td colSpan={4} className="px-6 py-12 text-center text-slate-400">Sin ordenes de compra</td></tr>}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Sales Orders (customer) */}
      {partner.is_customer && (
        <div className="space-y-3">
          <h2 className="text-lg font-bold text-slate-900 flex items-center gap-2"><ShoppingBag className="h-5 w-5 text-green-500" /> Ordenes de Venta</h2>
          <div className="bg-white rounded-2xl border border-slate-200/60 shadow-sm overflow-hidden">
            <table className="w-full text-sm">
              <thead><tr className="bg-slate-50 text-left text-xs font-semibold text-slate-500 uppercase">
                <th className="px-6 py-3"># Orden</th>
                <th className="px-6 py-3">Estado</th>
                <th className="px-6 py-3 text-right">Total</th>
                <th className="px-6 py-3">Fecha</th>
              </tr></thead>
              <tbody className="divide-y divide-slate-100">
                {sos.map(o => (
                  <tr key={o.id} className="hover:bg-slate-50/60 cursor-pointer" onClick={() => navigate(`/inventario/ventas/${o.id}`)}>
                    <td className="px-6 py-3 font-mono text-xs">{o.order_number}</td>
                    <td className="px-6 py-3"><span className={cn('px-2 py-0.5 rounded-full text-xs font-semibold',
                      o.status === 'delivered' ? 'bg-emerald-50 text-emerald-700' :
                      o.status === 'canceled' ? 'bg-red-50 text-red-600' :
                      o.status === 'shipped' ? 'bg-primary/10 text-primary' :
                      'bg-slate-100 text-slate-600'
                    )}>{o.status}</span></td>
                    <td className="px-6 py-3 text-right font-mono">${Number(o.total ?? 0).toLocaleString()}</td>
                    <td className="px-6 py-3 text-xs text-slate-400">{o.created_at ? new Date(o.created_at).toLocaleDateString() : ''}</td>
                  </tr>
                ))}
                {sos.length === 0 && <tr><td colSpan={4} className="px-6 py-12 text-center text-slate-400">Sin ordenes de venta</td></tr>}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Edit Modal */}
      {showEdit && <EditPartnerModal partner={partner} supplierTypes={supplierTypes} customerTypes={customerTypes} updateMut={updateMut} toast={toast} onClose={() => setShowEdit(false)} />}
    </div>
  )
}

function EditPartnerModal({ partner, supplierTypes, customerTypes, updateMut, toast, onClose }: {
  partner: BusinessPartner
  supplierTypes: any
  customerTypes: any
  updateMut: ReturnType<typeof useUpdatePartner>
  toast: ReturnType<typeof useToast>
  onClose: () => void
}) {
  const addr = partner.address as any ?? {}
  const ship = partner.shipping_address as any ?? {}
  const [form, setForm] = useState({
    name: partner.name,
    code: partner.code,
    tax_id: partner.tax_id ?? '',
    contact_name: partner.contact_name ?? '',
    email: partner.email ?? '',
    phone: partner.phone ?? '',
    payment_terms_days: String(partner.payment_terms_days),
    lead_time_days: String(partner.lead_time_days),
    credit_limit: String(partner.credit_limit),
    discount_percent: String(partner.discount_percent),
    supplier_type_id: partner.supplier_type_id ?? '',
    customer_type_id: partner.customer_type_id ?? '',
    notes: partner.notes ?? '',
    address_line1: addr.line1 ?? '', address_line2: addr.line2 ?? '',
    address_city: addr.city ?? '', address_state: addr.state ?? '',
    address_zip: addr.zip ?? '', address_country: addr.country ?? '',
    shipping_line1: ship.line1 ?? '', shipping_line2: ship.line2 ?? '',
    shipping_city: ship.city ?? '', shipping_state: ship.state ?? '',
    shipping_zip: ship.zip ?? '', shipping_country: ship.country ?? '',
  })

  const hasAddr = [form.address_line1, form.address_city, form.address_country].some(v => v.trim())
  const hasShip = [form.shipping_line1, form.shipping_city, form.shipping_country].some(v => v.trim())

  async function handleSave(e: React.FormEvent) {
    e.preventDefault()
    await updateMut.mutateAsync({
      id: partner.id,
      data: {
        name: form.name, code: form.code,
        tax_id: form.tax_id || null,
        contact_name: form.contact_name || null,
        email: form.email || null, phone: form.phone || null,
        payment_terms_days: Number(form.payment_terms_days),
        lead_time_days: Number(form.lead_time_days),
        credit_limit: Number(form.credit_limit),
        discount_percent: Number(form.discount_percent),
        supplier_type_id: form.supplier_type_id || null,
        customer_type_id: form.customer_type_id || null,
        notes: form.notes || null,
        address: hasAddr ? { line1: form.address_line1, line2: form.address_line2, city: form.address_city, state: form.address_state, zip: form.address_zip, country: form.address_country } : null,
        shipping_address: hasShip ? { line1: form.shipping_line1, line2: form.shipping_line2, city: form.shipping_city, state: form.shipping_state, zip: form.shipping_zip, country: form.shipping_country } : null,
      } as any,
    })
    toast.success('Socio actualizado')
    onClose()
  }

  const inputCls = "w-full bg-gray-50 border border-gray-200 rounded-xl px-3 py-2.5 text-sm focus:bg-white focus:ring-2 focus:ring-gray-900/10 focus:border-gray-300 transition-all outline-none"

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm" onClick={onClose}>
      <form onSubmit={handleSave} className="bg-white rounded-2xl p-6 w-full max-w-lg max-h-[90vh] overflow-y-auto shadow-2xl" onClick={e => e.stopPropagation()}>
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold">Editar socio</h3>
          <button type="button" onClick={onClose} className="p-1 text-slate-400 hover:text-slate-600"><X className="h-5 w-5" /></button>
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div className="col-span-2"><label className="text-xs text-gray-500">Nombre *</label><input required value={form.name} onChange={e => setForm(f => ({...f, name: e.target.value}))} className={inputCls} /></div>
          <div><label className="text-xs text-gray-500">Codigo *</label><input required value={form.code} onChange={e => setForm(f => ({...f, code: e.target.value}))} className={inputCls} /></div>
          <div><label className="text-xs text-gray-500">NIT / RUT</label><input value={form.tax_id} onChange={e => setForm(f => ({...f, tax_id: e.target.value}))} className={inputCls} /></div>
          <div><label className="text-xs text-gray-500">Contacto</label><input value={form.contact_name} onChange={e => setForm(f => ({...f, contact_name: e.target.value}))} className={inputCls} /></div>
          <div><label className="text-xs text-gray-500">Email</label><input type="email" value={form.email} onChange={e => setForm(f => ({...f, email: e.target.value}))} className={inputCls} /></div>
          <div><label className="text-xs text-gray-500">Telefono</label><input value={form.phone} onChange={e => setForm(f => ({...f, phone: e.target.value}))} className={inputCls} /></div>
          <div><label className="text-xs text-gray-500">Plazo pago (dias)</label><input type="number" value={form.payment_terms_days} onChange={e => setForm(f => ({...f, payment_terms_days: e.target.value}))} className={inputCls} /></div>
          {partner.is_supplier && (<>
            <div><label className="text-xs text-gray-500">Tipo proveedor</label><select value={form.supplier_type_id} onChange={e => setForm(f => ({...f, supplier_type_id: e.target.value}))} className={inputCls}><option value="">Sin tipo</option>{(supplierTypes as any)?.items?.map((t: any) => <option key={t.id} value={t.id}>{t.name}</option>)}</select></div>
            <div><label className="text-xs text-gray-500">Lead time (dias)</label><input type="number" value={form.lead_time_days} onChange={e => setForm(f => ({...f, lead_time_days: e.target.value}))} className={inputCls} /></div>
          </>)}
          {partner.is_customer && (<>
            <div><label className="text-xs text-gray-500">Tipo cliente</label><select value={form.customer_type_id} onChange={e => setForm(f => ({...f, customer_type_id: e.target.value}))} className={inputCls}><option value="">Sin tipo</option>{(customerTypes as any)?.items?.map((t: any) => <option key={t.id} value={t.id}>{t.name}</option>)}</select></div>
            <div><label className="text-xs text-gray-500">Limite credito</label><input type="number" value={form.credit_limit} onChange={e => setForm(f => ({...f, credit_limit: e.target.value}))} className={inputCls} /></div>
            <div><label className="text-xs text-gray-500">Descuento %</label><input type="number" min="0" max="100" value={form.discount_percent} onChange={e => setForm(f => ({...f, discount_percent: e.target.value}))} className={inputCls} /></div>
          </>)}

          {/* Address */}
          <div className="col-span-2 pt-2"><p className="text-xs font-semibold text-gray-400 uppercase tracking-wider">Direccion</p></div>
          <div className="col-span-2"><label className="text-xs text-gray-500">Linea 1</label><input value={form.address_line1} onChange={e => setForm(f => ({...f, address_line1: e.target.value}))} placeholder="Calle, carrera, numero" className={inputCls} /></div>
          <div className="col-span-2"><label className="text-xs text-gray-500">Linea 2</label><input value={form.address_line2} onChange={e => setForm(f => ({...f, address_line2: e.target.value}))} placeholder="Barrio, vereda (opcional)" className={inputCls} /></div>
          <div><label className="text-xs text-gray-500">Ciudad</label><input value={form.address_city} onChange={e => setForm(f => ({...f, address_city: e.target.value}))} className={inputCls} /></div>
          <div><label className="text-xs text-gray-500">Depto / Estado</label><input value={form.address_state} onChange={e => setForm(f => ({...f, address_state: e.target.value}))} className={inputCls} /></div>
          <div><label className="text-xs text-gray-500">Codigo postal</label><input value={form.address_zip} onChange={e => setForm(f => ({...f, address_zip: e.target.value}))} className={inputCls} /></div>
          <div><label className="text-xs text-gray-500">Pais</label><input value={form.address_country} onChange={e => setForm(f => ({...f, address_country: e.target.value}))} placeholder="CO, DE, US..." className={inputCls} /></div>

          {partner.is_customer && (<>
            <div className="col-span-2 pt-2"><p className="text-xs font-semibold text-gray-400 uppercase tracking-wider">Direccion de envio</p></div>
            <div className="col-span-2"><label className="text-xs text-gray-500">Linea 1</label><input value={form.shipping_line1} onChange={e => setForm(f => ({...f, shipping_line1: e.target.value}))} className={inputCls} /></div>
            <div className="col-span-2"><label className="text-xs text-gray-500">Linea 2</label><input value={form.shipping_line2} onChange={e => setForm(f => ({...f, shipping_line2: e.target.value}))} className={inputCls} /></div>
            <div><label className="text-xs text-gray-500">Ciudad</label><input value={form.shipping_city} onChange={e => setForm(f => ({...f, shipping_city: e.target.value}))} className={inputCls} /></div>
            <div><label className="text-xs text-gray-500">Depto / Estado</label><input value={form.shipping_state} onChange={e => setForm(f => ({...f, shipping_state: e.target.value}))} className={inputCls} /></div>
            <div><label className="text-xs text-gray-500">Codigo postal</label><input value={form.shipping_zip} onChange={e => setForm(f => ({...f, shipping_zip: e.target.value}))} className={inputCls} /></div>
            <div><label className="text-xs text-gray-500">Pais</label><input value={form.shipping_country} onChange={e => setForm(f => ({...f, shipping_country: e.target.value}))} placeholder="CO, DE, US..." className={inputCls} /></div>
          </>)}

          <div className="col-span-2"><label className="text-xs text-gray-500">Notas</label><textarea value={form.notes} onChange={e => setForm(f => ({...f, notes: e.target.value}))} rows={2} className={inputCls} /></div>
        </div>
        <div className="flex gap-3 mt-4">
          <button type="button" onClick={onClose} className="flex-1 bg-gray-100 text-gray-700 rounded-xl px-4 py-2.5 text-sm font-medium hover:bg-gray-200 transition-colors">Cancelar</button>
          <button type="submit" disabled={updateMut.isPending} className="flex-1 bg-gray-900 text-white rounded-xl px-4 py-2.5 text-sm font-semibold hover:bg-gray-800 disabled:opacity-50 transition-colors">Guardar</button>
        </div>
      </form>
    </div>
  )
}
