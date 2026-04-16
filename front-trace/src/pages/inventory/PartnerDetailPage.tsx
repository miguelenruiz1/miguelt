import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
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
  if (!partner) return <p className="text-center text-muted-foreground py-20">Socio no encontrado</p>

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
      <button onClick={() => navigate('/inventario/socios')} className="flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground">
        <ArrowLeft className="h-4 w-4" /> Socios Comerciales
      </button>

      {/* Header */}
      <div className="bg-card rounded-2xl border border-border/60  p-6">
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-4">
            <div className="h-14 w-14 rounded-2xl bg-primary/15 flex items-center justify-center">
              <Building2 className="h-7 w-7 text-primary" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-foreground">{partner.name}</h1>
              <div className="flex items-center gap-3 mt-1 text-sm text-muted-foreground">
                <span className="font-mono">{partner.code}</span>
                {partner.tax_id && <span>NIT: {partner.tax_id}</span>}
                {!partner.is_active && <span className="px-2 py-0.5 bg-red-100 text-red-600 rounded-full text-xs font-semibold">Inactivo</span>}
              </div>
              <div className="mt-2">{roleBadges}</div>
            </div>
          </div>
          <button onClick={() => setShowEdit(true)} className="p-2 text-muted-foreground hover:text-primary hover:bg-primary/10 rounded-lg">
            <Pencil className="h-4 w-4" />
          </button>
        </div>
      </div>

      {/* KPIs */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <div className="bg-card rounded-xl border border-border/60 p-4">
          <p className="text-xs text-muted-foreground mb-1">Terminos de Pago</p>
          <p className="text-xl font-bold">{partner.payment_terms_days} dias</p>
        </div>
        {partner.is_supplier && (
          <div className="bg-card rounded-xl border border-border/60 p-4">
            <p className="text-xs text-muted-foreground mb-1">Lead Time</p>
            <p className="text-xl font-bold text-blue-600">{partner.lead_time_days} dias</p>
          </div>
        )}
        {partner.is_customer && (
          <>
            <div className="bg-card rounded-xl border border-border/60 p-4">
              <p className="text-xs text-muted-foreground mb-1">Limite de Credito</p>
              <p className="text-xl font-bold text-emerald-600">${partner.credit_limit.toLocaleString('es-CO')}</p>
            </div>
            <div className="bg-card rounded-xl border border-border/60 p-4">
              <p className="text-xs text-muted-foreground mb-1">Descuento</p>
              <p className="text-xl font-bold">{partner.discount_percent}%</p>
            </div>
          </>
        )}
      </div>

      {/* Contact & Address */}
      <div className="bg-card rounded-2xl border border-border/60  p-6">
        <h2 className="text-sm font-bold text-muted-foreground uppercase tracking-wider mb-4">Informacion de Contacto</h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {partner.contact_name && (
            <div className="flex items-center gap-2 text-sm"><Building2 className="h-4 w-4 text-muted-foreground shrink-0" /> <span className="text-foreground">{partner.contact_name}</span></div>
          )}
          {partner.email && (
            <div className="flex items-center gap-2 text-sm"><Mail className="h-4 w-4 text-muted-foreground shrink-0" /> <a href={`mailto:${partner.email}`} className="text-primary hover:underline">{partner.email}</a></div>
          )}
          {partner.phone && (
            <div className="flex items-center gap-2 text-sm"><Phone className="h-4 w-4 text-muted-foreground shrink-0" /> <span className="text-foreground">{partner.phone}</span></div>
          )}
        </div>
        {(addressStr || shippingStr) && (
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mt-4 pt-4 border-t border-border">
            {addressStr && (
              <div>
                <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-1">Direccion</p>
                <div className="flex items-start gap-2 text-sm text-foreground">
                  <MapPin className="h-4 w-4 text-muted-foreground shrink-0 mt-0.5" />
                  <span>{addressStr}</span>
                </div>
              </div>
            )}
            {shippingStr && (
              <div>
                <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-1">Direccion de Envio</p>
                <div className="flex items-start gap-2 text-sm text-foreground">
                  <MapPin className="h-4 w-4 text-emerald-400 shrink-0 mt-0.5" />
                  <span>{shippingStr}</span>
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      {partner.notes && (
        <div className="bg-card rounded-xl border border-border/60 p-4">
          <p className="text-xs font-bold text-muted-foreground uppercase mb-2">Notas</p>
          <p className="text-sm text-foreground whitespace-pre-wrap">{partner.notes}</p>
        </div>
      )}

      {/* Purchase Orders (supplier) */}
      {partner.is_supplier && (
        <div className="space-y-3">
          <h2 className="text-lg font-bold text-foreground flex items-center gap-2"><ShoppingCart className="h-5 w-5 text-blue-500" /> Ordenes de Compra</h2>
          <div className="bg-card rounded-2xl border border-border/60  overflow-hidden">
            <table className="w-full text-sm">
              <thead><tr className="bg-muted text-left text-xs font-semibold text-muted-foreground uppercase">
                <th className="px-6 py-3"># Orden</th>
                <th className="px-6 py-3">Estado</th>
                <th className="px-6 py-3 text-right">Total</th>
                <th className="px-6 py-3">Fecha</th>
              </tr></thead>
              <tbody className="divide-y divide-slate-100">
                {pos.map(o => (
                  <tr key={o.id} className="hover:bg-muted/60 cursor-pointer" onClick={() => navigate(`/inventario/compras/${o.id}`)}>
                    <td className="px-6 py-3 font-mono text-xs">{o.po_number}</td>
                    <td className="px-6 py-3"><span className={cn('px-2 py-0.5 rounded-full text-xs font-semibold',
                      o.status === 'received' ? 'bg-emerald-50 text-emerald-700' :
                      o.status === 'canceled' ? 'bg-red-50 text-red-600' :
                      'bg-secondary text-muted-foreground'
                    )}>{o.status}</span></td>
                    <td className="px-6 py-3 text-right font-mono">${Number(o.total ?? 0).toLocaleString('es-CO')}</td>
                    <td className="px-6 py-3 text-xs text-muted-foreground">{o.created_at ? new Date(o.created_at).toLocaleDateString('es-CO') : ''}</td>
                  </tr>
                ))}
                {pos.length === 0 && <tr><td colSpan={4} className="px-6 py-12 text-center text-muted-foreground">Sin ordenes de compra</td></tr>}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Sales Orders (customer) */}
      {partner.is_customer && (
        <div className="space-y-3">
          <h2 className="text-lg font-bold text-foreground flex items-center gap-2"><ShoppingBag className="h-5 w-5 text-green-500" /> Ordenes de Venta</h2>
          <div className="bg-card rounded-2xl border border-border/60  overflow-hidden">
            <table className="w-full text-sm">
              <thead><tr className="bg-muted text-left text-xs font-semibold text-muted-foreground uppercase">
                <th className="px-6 py-3"># Orden</th>
                <th className="px-6 py-3">Estado</th>
                <th className="px-6 py-3 text-right">Total</th>
                <th className="px-6 py-3">Fecha</th>
              </tr></thead>
              <tbody className="divide-y divide-slate-100">
                {sos.map(o => (
                  <tr key={o.id} className="hover:bg-muted/60 cursor-pointer" onClick={() => navigate(`/inventario/ventas/${o.id}`)}>
                    <td className="px-6 py-3 font-mono text-xs">{o.order_number}</td>
                    <td className="px-6 py-3"><span className={cn('px-2 py-0.5 rounded-full text-xs font-semibold',
                      o.status === 'delivered' ? 'bg-emerald-50 text-emerald-700' :
                      o.status === 'canceled' ? 'bg-red-50 text-red-600' :
                      o.status === 'shipped' ? 'bg-primary/10 text-primary' :
                      'bg-secondary text-muted-foreground'
                    )}>{o.status}</span></td>
                    <td className="px-6 py-3 text-right font-mono">${Number(o.total ?? 0).toLocaleString('es-CO')}</td>
                    <td className="px-6 py-3 text-xs text-muted-foreground">{o.created_at ? new Date(o.created_at).toLocaleDateString('es-CO') : ''}</td>
                  </tr>
                ))}
                {sos.length === 0 && <tr><td colSpan={4} className="px-6 py-12 text-center text-muted-foreground">Sin ordenes de venta</td></tr>}
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

// ─── NIT validation (Colombia) ────────────────────────────────────────────────

const nitRegex = /^\d{6,10}(-?\d)?$/

function validateNitDv(nit: string): boolean {
  const [body, dv] = nit.split('-')
  if (!dv) return true // DV optional per regex
  const weights = [3, 7, 13, 17, 19, 23, 29, 37, 41, 43, 47, 53, 59, 67, 71]
  const digits = body.padStart(15, '0').split('').map(Number)
  const sum = digits.reduce((acc, d, i) => acc + d * weights[14 - i], 0)
  const remainder = sum % 11
  const expectedDv = remainder < 2 ? remainder : 11 - remainder
  return expectedDv === parseInt(dv)
}

const partnerUpdateSchema = z.object({
  name: z.string().min(1, 'Campo obligatorio').max(255),
  code: z.string().min(1, 'Campo obligatorio'),
  tax_id: z.string().regex(nitRegex, 'NIT inválido (formato: 900123456-7)')
    .refine(v => !v.includes('-') || validateNitDv(v), { message: 'Dígito verificador incorrecto' }),
  tax_regime: z.enum(['1', '2']).default('2'),
  contact_name: z.string().optional(),
  email: z.string().email('Email inválido').optional().or(z.literal('')),
  phone: z.string().optional(),
  payment_terms_days: z.coerce.number().int().min(0).default(0),
  lead_time_days: z.coerce.number().int().min(0).default(0),
  credit_limit: z.coerce.number().min(0).default(0),
  discount_percent: z.coerce.number().min(0).max(100).default(0),
  supplier_type_id: z.string().optional(),
  customer_type_id: z.string().optional(),
  notes: z.string().optional(),
  address_line1: z.string().optional(),
  address_line2: z.string().optional(),
  address_city: z.string().optional(),
  address_state: z.string().optional(),
  address_zip: z.string().optional(),
  address_country: z.string().optional(),
  shipping_line1: z.string().optional(),
  shipping_line2: z.string().optional(),
  shipping_city: z.string().optional(),
  shipping_state: z.string().optional(),
  shipping_zip: z.string().optional(),
  shipping_country: z.string().optional(),
})

type PartnerUpdateFormData = z.infer<typeof partnerUpdateSchema>

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

  const {
    register,
    handleSubmit,
    formState: { errors, isValid, isSubmitting },
  } = useForm<PartnerUpdateFormData>({
    resolver: zodResolver(partnerUpdateSchema),
    mode: 'onChange',
    defaultValues: {
      name: partner.name,
      code: partner.code,
      tax_id: partner.tax_id ?? '',
      tax_regime: (String((partner as any).tax_regime ?? 2) === '1' ? '1' : '2') as '1' | '2',
      contact_name: partner.contact_name ?? '',
      email: partner.email ?? '',
      phone: partner.phone ?? '',
      payment_terms_days: partner.payment_terms_days,
      lead_time_days: partner.lead_time_days,
      credit_limit: partner.credit_limit,
      discount_percent: partner.discount_percent,
      supplier_type_id: partner.supplier_type_id ?? '',
      customer_type_id: partner.customer_type_id ?? '',
      notes: partner.notes ?? '',
      address_line1: addr.line1 ?? '', address_line2: addr.line2 ?? '',
      address_city: addr.city ?? '', address_state: addr.state ?? '',
      address_zip: addr.zip ?? '', address_country: addr.country ?? '',
      shipping_line1: ship.line1 ?? '', shipping_line2: ship.line2 ?? '',
      shipping_city: ship.city ?? '', shipping_state: ship.state ?? '',
      shipping_zip: ship.zip ?? '', shipping_country: ship.country ?? '',
    },
  })

  const onSubmit = async (form: PartnerUpdateFormData) => {
    const hasAddr = [form.address_line1, form.address_city, form.address_country].some(v => (v ?? '').trim())
    const hasShip = [form.shipping_line1, form.shipping_city, form.shipping_country].some(v => (v ?? '').trim())
    await updateMut.mutateAsync({
      id: partner.id,
      data: {
        name: form.name, code: form.code,
        tax_id: form.tax_id || null,
        tax_regime: Number(form.tax_regime) || 2,
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

  const inputCls = "w-full bg-muted border border-border rounded-xl px-3 py-2.5 text-sm focus:bg-card focus:ring-2 focus:ring-gray-900/10 focus:border-gray-300 transition-all outline-none"
  const errCls = 'mt-1 text-xs text-red-600'

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm" onClick={onClose}>
      <form onSubmit={handleSubmit(onSubmit)} className="bg-card rounded-2xl p-6 w-full max-w-lg max-h-[90vh] overflow-y-auto shadow-2xl" onClick={e => e.stopPropagation()} noValidate>
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold">Editar socio</h3>
          <button type="button" onClick={onClose} className="p-1 text-muted-foreground hover:text-muted-foreground"><X className="h-5 w-5" /></button>
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div className="col-span-2"><label className="text-xs text-muted-foreground">Nombre *</label><input {...register('name')} className={inputCls} />{errors.name && <p className={errCls}>{errors.name.message}</p>}</div>
          <div><label className="text-xs text-muted-foreground">Codigo *</label><input {...register('code')} className={inputCls} />{errors.code && <p className={errCls}>{errors.code.message}</p>}</div>
          <div><label className="text-xs text-muted-foreground">NIT / Número de identificación *</label><input {...register('tax_id')} placeholder="Ej: 900123456-7" className={inputCls} />{errors.tax_id && <p className={errCls}>{errors.tax_id.message}</p>}</div>
          <div><label className="text-xs text-muted-foreground">Régimen fiscal</label><select {...register('tax_regime')} className={inputCls}><option value="1">Responsable de IVA</option><option value="2">No responsable de IVA</option></select></div>
          <div><label className="text-xs text-muted-foreground">Contacto</label><input {...register('contact_name')} className={inputCls} /></div>
          <div><label className="text-xs text-muted-foreground">Email</label><input type="email" {...register('email')} className={inputCls} />{errors.email && <p className={errCls}>{errors.email.message}</p>}</div>
          <div><label className="text-xs text-muted-foreground">Telefono</label><input {...register('phone')} className={inputCls} /></div>
          <div><label className="text-xs text-muted-foreground">Plazo pago (dias)</label><input type="number" {...register('payment_terms_days')} className={inputCls} />{errors.payment_terms_days && <p className={errCls}>{errors.payment_terms_days.message}</p>}</div>
          {partner.is_supplier && (<>
            <div><label className="text-xs text-muted-foreground">Tipo proveedor</label><select {...register('supplier_type_id')} className={inputCls}><option value="">Sin tipo</option>{(supplierTypes as any)?.items?.map((t: any) => <option key={t.id} value={t.id}>{t.name}</option>)}</select></div>
            <div><label className="text-xs text-muted-foreground">Lead time (dias)</label><input type="number" {...register('lead_time_days')} className={inputCls} />{errors.lead_time_days && <p className={errCls}>{errors.lead_time_days.message}</p>}</div>
          </>)}
          {partner.is_customer && (<>
            <div><label className="text-xs text-muted-foreground">Tipo cliente</label><select {...register('customer_type_id')} className={inputCls}><option value="">Sin tipo</option>{(customerTypes as any)?.items?.map((t: any) => <option key={t.id} value={t.id}>{t.name}</option>)}</select></div>
            <div><label className="text-xs text-muted-foreground">Limite credito</label><input type="number" {...register('credit_limit')} className={inputCls} />{errors.credit_limit && <p className={errCls}>{errors.credit_limit.message}</p>}</div>
            <div><label className="text-xs text-muted-foreground">Descuento %</label><input type="number" min="0" max="100" {...register('discount_percent')} className={inputCls} />{errors.discount_percent && <p className={errCls}>{errors.discount_percent.message}</p>}</div>
          </>)}

          {/* Address */}
          <div className="col-span-2 pt-2"><p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Direccion</p></div>
          <div className="col-span-2"><label className="text-xs text-muted-foreground">Linea 1</label><input {...register('address_line1')} placeholder="Calle, carrera, numero" className={inputCls} /></div>
          <div className="col-span-2"><label className="text-xs text-muted-foreground">Linea 2</label><input {...register('address_line2')} placeholder="Barrio, vereda (opcional)" className={inputCls} /></div>
          <div><label className="text-xs text-muted-foreground">Ciudad</label><input {...register('address_city')} className={inputCls} /></div>
          <div><label className="text-xs text-muted-foreground">Depto / Estado</label><input {...register('address_state')} className={inputCls} /></div>
          <div><label className="text-xs text-muted-foreground">Codigo postal</label><input {...register('address_zip')} className={inputCls} /></div>
          <div><label className="text-xs text-muted-foreground">Pais</label><input {...register('address_country')} placeholder="CO, DE, US..." className={inputCls} /></div>

          {partner.is_customer && (<>
            <div className="col-span-2 pt-2"><p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Direccion de envio</p></div>
            <div className="col-span-2"><label className="text-xs text-muted-foreground">Linea 1</label><input {...register('shipping_line1')} className={inputCls} /></div>
            <div className="col-span-2"><label className="text-xs text-muted-foreground">Linea 2</label><input {...register('shipping_line2')} className={inputCls} /></div>
            <div><label className="text-xs text-muted-foreground">Ciudad</label><input {...register('shipping_city')} className={inputCls} /></div>
            <div><label className="text-xs text-muted-foreground">Depto / Estado</label><input {...register('shipping_state')} className={inputCls} /></div>
            <div><label className="text-xs text-muted-foreground">Codigo postal</label><input {...register('shipping_zip')} className={inputCls} /></div>
            <div><label className="text-xs text-muted-foreground">Pais</label><input {...register('shipping_country')} placeholder="CO, DE, US..." className={inputCls} /></div>
          </>)}

          <div className="col-span-2"><label className="text-xs text-muted-foreground">Notas</label><textarea {...register('notes')} rows={2} className={inputCls} /></div>
        </div>
        <div className="flex gap-3 mt-4">
          <button type="button" onClick={onClose} className="flex-1 bg-secondary text-foreground rounded-xl px-4 py-2.5 text-sm font-medium hover:bg-gray-200 transition-colors">Cancelar</button>
          <button type="submit" disabled={!isValid || isSubmitting || updateMut.isPending} className="flex-1 bg-gray-900 text-white rounded-xl px-4 py-2.5 text-sm font-semibold hover:bg-gray-800 disabled:opacity-50 transition-colors">Guardar</button>
        </div>
      </form>
    </div>
  )
}
