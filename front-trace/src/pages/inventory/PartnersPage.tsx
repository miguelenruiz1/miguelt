import { useState, useEffect } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { Plus, Search, Users, Truck, ShoppingBag, Building } from 'lucide-react'
import { cn } from '@/lib/utils'
import { useFormValidation } from '@/hooks/useFormValidation'
import { SegmentedControl } from '@/components/ui/tabs'
import {
  usePartners, useCreatePartner, useUpdatePartner, useDeletePartner,
  useSupplierTypes, useCustomerTypes,
} from '@/hooks/useInventory'
import { useConfirm } from '@/store/confirm'
import type { BusinessPartner } from '@/types/inventory'

const ROLE_TABS = [
  { key: 'all', label: 'Todos', icon: Users },
  { key: 'supplier', label: 'Proveedores', icon: Truck },
  { key: 'customer', label: 'Clientes', icon: ShoppingBag },
  { key: 'both', label: 'Ambos', icon: Building },
] as const

type RoleTab = typeof ROLE_TABS[number]['key']

export function PartnersPage() {
  const [roleTab, setRoleTab] = useState<RoleTab>('all')
  const [search, setSearch] = useState('')
  const [showCreate, setShowCreate] = useState(false)
  const [editPartner, setEditPartner] = useState<BusinessPartner | null>(null)
  const confirm = useConfirm()
  const navigate = useNavigate()
  const location = useLocation()
  useEffect(() => { setShowCreate(false); setEditPartner(null) }, [location.key])

  const queryParams = {
    is_supplier: roleTab === 'supplier' || roleTab === 'both' ? true : roleTab === 'customer' ? undefined : undefined,
    is_customer: roleTab === 'customer' || roleTab === 'both' ? true : roleTab === 'supplier' ? undefined : undefined,
    search: search || undefined,
    limit: 100,
  }
  // Refine filters
  if (roleTab === 'supplier') { queryParams.is_supplier = true }
  if (roleTab === 'customer') { queryParams.is_customer = true }

  const { data, isLoading } = usePartners(queryParams)
  const partners = data?.items || []

  // Further filter "both" on client side
  const filtered = roleTab === 'both'
    ? partners.filter(p => p.is_supplier && p.is_customer)
    : partners

  const createMut = useCreatePartner()
  const updateMut = useUpdatePartner()
  const deleteMut = useDeletePartner()

  const { data: supplierTypes } = useSupplierTypes()
  const { data: customerTypes } = useCustomerTypes()

  const emptyAddress = { line1: '', line2: '', city: '', state: '', zip: '', country: '' }

  const [form, setForm] = useState({
    name: '', code: '', is_supplier: false, is_customer: false,
    supplier_type_id: '', customer_type_id: '', tax_id: '', contact_name: '',
    email: '', phone: '', payment_terms_days: '30', lead_time_days: '7',
    credit_limit: '0', discount_percent: '0', notes: '',
    document_type: 'CC', dv: '', company_name: '',
    organization_type: '2', tax_regime: '2', tax_liability: '7', municipality_id: '149',
    address: { ...emptyAddress },
    shipping_address: { ...emptyAddress },
    differentShippingAddress: false,
  })

  const resetForm = () => setForm({
    name: '', code: '', is_supplier: false, is_customer: false,
    supplier_type_id: '', customer_type_id: '', tax_id: '', contact_name: '',
    email: '', phone: '', payment_terms_days: '30', lead_time_days: '7',
    credit_limit: '0', discount_percent: '0', notes: '',
    document_type: 'CC', dv: '', company_name: '',
    organization_type: '2', tax_regime: '2', tax_liability: '7', municipality_id: '149',
    address: { ...emptyAddress },
    shipping_address: { ...emptyAddress },
    differentShippingAddress: false,
  })

  const openEdit = (p: BusinessPartner) => {
    const addr = (p as any).address ?? emptyAddress
    const shipAddr = (p as any).shipping_address ?? emptyAddress
    const hasDifferentShipping = Object.values(shipAddr).some((v: any) => v && String(v).trim() !== '')
    setForm({
      name: p.name, code: p.code, is_supplier: p.is_supplier, is_customer: p.is_customer,
      supplier_type_id: p.supplier_type_id || '', customer_type_id: p.customer_type_id || '',
      tax_id: p.tax_id || '', contact_name: p.contact_name || '',
      document_type: (p as any).document_type || 'CC', dv: (p as any).dv || '',
      company_name: (p as any).company_name || '',
      organization_type: String((p as any).organization_type ?? 2),
      tax_regime: String((p as any).tax_regime ?? 2),
      tax_liability: String((p as any).tax_liability ?? 7),
      municipality_id: String((p as any).municipality_id ?? 149),
      email: p.email || '', phone: p.phone || '',
      payment_terms_days: String(p.payment_terms_days), lead_time_days: String(p.lead_time_days),
      credit_limit: String(p.credit_limit), discount_percent: String(p.discount_percent),
      notes: p.notes || '',
      address: { line1: addr.line1 || '', line2: addr.line2 || '', city: addr.city || '', state: addr.state || '', zip: addr.zip || '', country: addr.country || '' },
      shipping_address: { line1: shipAddr.line1 || '', line2: shipAddr.line2 || '', city: shipAddr.city || '', state: shipAddr.state || '', zip: shipAddr.zip || '', country: shipAddr.country || '' },
      differentShippingAddress: hasDifferentShipping,
    })
    setEditPartner(p)
  }

  const inputCls = "w-full bg-muted border border-border rounded-xl px-3 py-2.5 text-sm focus:bg-card focus:ring-2 focus:ring-gray-900/10 focus:border-gray-300 transition-all outline-none"
  const hasAddress = (a: typeof emptyAddress) => Object.values(a).some(v => v.trim() !== '')

  async function doSubmit() {
    if (form.is_customer && !form.tax_id.trim()) {
      alert('El número de documento (NIT/Cédula) es obligatorio para clientes.')
      return
    }
    if (form.is_customer && !form.address.city.trim()) {
      alert('La ciudad es obligatoria para clientes (requerida para facturación electrónica).')
      return
    }
    if (form.document_type === 'NIT' && !form.dv.trim()) {
      alert('El dígito de verificación (DV) es obligatorio para NIT.')
      return
    }
    const payload: Record<string, unknown> = {
      name: form.name, code: form.code,
      is_supplier: form.is_supplier, is_customer: form.is_customer,
      supplier_type_id: form.supplier_type_id || null,
      customer_type_id: form.customer_type_id || null,
      tax_id: form.tax_id || null,
      document_type: form.document_type,
      dv: form.dv || null,
      company_name: form.company_name || null,
      organization_type: Number(form.organization_type),
      tax_regime: Number(form.tax_regime),
      tax_liability: Number(form.tax_liability),
      municipality_id: Number(form.municipality_id),
      contact_name: form.contact_name || null,
      email: form.email || null, phone: form.phone || null,
      payment_terms_days: Number(form.payment_terms_days),
      lead_time_days: Number(form.lead_time_days),
      credit_limit: Number(form.credit_limit),
      discount_percent: Number(form.discount_percent),
      notes: form.notes || null,
      address: hasAddress(form.address) ? form.address : null,
      shipping_address: form.differentShippingAddress && hasAddress(form.shipping_address) ? form.shipping_address : null,
    }
    if (editPartner) {
      await updateMut.mutateAsync({ id: editPartner.id, data: payload })
      setEditPartner(null)
    } else {
      await createMut.mutateAsync(payload)
      setShowCreate(false)
    }
    resetForm()
  }

  const { formRef, handleSubmit: validateAndSubmit } = useFormValidation(doSubmit)

  const roleBadge = (p: BusinessPartner) => {
    if (p.is_supplier && p.is_customer) return <span className="text-xs bg-purple-100 text-purple-700 px-2 py-0.5 rounded-full">Ambos</span>
    if (p.is_supplier) return <span className="text-xs bg-blue-100 text-blue-700 px-2 py-0.5 rounded-full">Proveedor</span>
    return <span className="text-xs bg-green-100 text-green-700 px-2 py-0.5 rounded-full">Cliente</span>
  }

  const showModal = showCreate || editPartner !== null

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Users className="h-6 w-6 text-foreground" />
          <h1 className="text-2xl font-bold">Socios Comerciales</h1>
        </div>
        <button onClick={() => { resetForm(); setShowCreate(true) }}
          className="flex items-center gap-1 px-4 py-2 text-sm bg-gray-900 text-white rounded-xl hover:bg-gray-800">
          <Plus className="h-4 w-4" />Nuevo socio
        </button>
      </div>

      {/* Role tabs + search */}
      <div className="flex flex-wrap items-center gap-4">
        <SegmentedControl
          options={ROLE_TABS.map(t => ({ key: t.key, label: t.label, icon: t.icon }))}
          value={roleTab}
          onChange={(k) => setRoleTab(k as RoleTab)}
        />
        <div className="relative flex-1 max-w-xs">
          <Search className="absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
          <input value={search} onChange={e => setSearch(e.target.value)}
            placeholder="Buscar por nombre, codigo, email..."
            className="w-full pl-9 pr-3 py-2 bg-muted border border-border rounded-xl text-sm focus:bg-card focus:ring-2 focus:ring-gray-900/10 focus:border-gray-300 transition-all" />
        </div>
      </div>

      {/* Table */}
      {isLoading ? <div className="text-center py-10 text-muted-foreground">Cargando...</div> : (
        <div className="bg-card rounded-xl border border-border overflow-hidden">
          <table className="w-full text-sm">
            <thead><tr className="border-b border-border">
              <th className="p-3 text-left">Nombre</th>
              <th className="p-3 text-left">Codigo</th>
              <th className="p-3 text-left">Rol</th>
              <th className="p-3 text-left">Contacto</th>
              <th className="p-3 text-left">Email</th>
              <th className="p-3 text-right">Plazo pago</th>
              <th className="p-3 text-center">Estado</th>
              <th className="p-3"></th>
            </tr></thead>
            <tbody>
              {filtered.map(p => (
                <tr key={p.id} className="border-b border-gray-50 hover:bg-muted/50 cursor-pointer transition-colors" onClick={() => navigate(`/inventario/socios/${p.id}`)}>
                  <td className="p-3 font-medium">{p.name}</td>
                  <td className="p-3 font-mono text-xs text-muted-foreground">{p.code}</td>
                  <td className="p-3">{roleBadge(p)}</td>
                  <td className="p-3 text-muted-foreground">{p.contact_name || '\u2014'}</td>
                  <td className="p-3 text-muted-foreground">{p.email || '\u2014'}</td>
                  <td className="p-3 text-right">{p.payment_terms_days}d</td>
                  <td className="p-3 text-center">{p.is_active ? <span className="text-xs bg-green-100 text-green-700 px-2 py-0.5 rounded-full">Activo</span> : <span className="text-xs bg-secondary text-muted-foreground px-2 py-0.5 rounded-full">Inactivo</span>}</td>
                  <td className="p-3 text-right" onClick={e => e.stopPropagation()}>
                    <button onClick={() => openEdit(p)} className="text-xs text-primary hover:underline mr-2">Editar</button>
                    <button onClick={async () => { const ok = await confirm({ title: 'Desactivar socio', message: `¿Desactivar ${p.name}?`, confirmLabel: 'Desactivar' }); if (ok) deleteMut.mutate(p.id) }}
                      className="text-xs text-red-500 hover:underline">Desactivar</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {filtered.length === 0 && <div className="text-center py-10 text-muted-foreground">No se encontraron socios comerciales</div>}
        </div>
      )}

      {/* Create/Edit Modal */}
      {showModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
          <form ref={formRef} onSubmit={validateAndSubmit} noValidate className="bg-card rounded-2xl p-6 w-full max-w-lg max-h-[90vh] overflow-y-auto shadow-2xl">
            <h3 className="text-lg font-semibold mb-4">{editPartner ? 'Editar socio' : 'Nuevo socio comercial'}</h3>

            {/* Role checkboxes */}
            <div className="flex gap-4 mb-4">
              <label className="flex items-center gap-2 text-sm">
                <input type="checkbox" checked={form.is_supplier} onChange={e => setForm(f => ({...f, is_supplier: e.target.checked}))} className="rounded" />
                <Truck className="h-4 w-4 text-blue-600" />Proveedor
              </label>
              <label className="flex items-center gap-2 text-sm">
                <input type="checkbox" checked={form.is_customer} onChange={e => setForm(f => ({...f, is_customer: e.target.checked}))} className="rounded" />
                <ShoppingBag className="h-4 w-4 text-green-600" />Cliente
              </label>
            </div>

            <div className="grid grid-cols-2 gap-3">
              {/* ── Identificacion ── */}
              <div className="col-span-2"><label className="text-xs text-muted-foreground">Nombre *</label><input required value={form.name} onChange={e => setForm(f => ({...f, name: e.target.value}))} className={inputCls} /></div>
              <div><label className="text-xs text-muted-foreground">Codigo *</label><input required value={form.code} onChange={e => setForm(f => ({...f, code: e.target.value}))} className={inputCls} /></div>
              <div>
                <label className="text-xs text-muted-foreground">Tipo documento</label>
                <select value={form.document_type} onChange={e => setForm(f => ({...f, document_type: e.target.value}))} className={inputCls}>
                  <option value="CC">Cédula (CC)</option>
                  <option value="NIT">NIT</option>
                  <option value="CE">Cédula Extranjería</option>
                  <option value="PP">Pasaporte</option>
                  <option value="TI">Tarjeta Identidad</option>
                </select>
              </div>
              <div><label className="text-xs text-muted-foreground">{form.document_type === 'NIT' ? 'NIT *' : 'Nº Documento *'}</label><input value={form.tax_id} onChange={e => setForm(f => ({...f, tax_id: e.target.value}))} className={inputCls} required /></div>
              {form.document_type === 'NIT' && (
                <div><label className="text-xs text-muted-foreground">DV *</label><input maxLength={1} value={form.dv} onChange={e => setForm(f => ({...f, dv: e.target.value}))} className={inputCls} placeholder="0-9" required /></div>
              )}
              {form.document_type === 'NIT' && (
                <>
                  <div className="col-span-2"><label className="text-xs text-muted-foreground">Razón social</label><input value={form.company_name} onChange={e => setForm(f => ({...f, company_name: e.target.value}))} className={inputCls} /></div>
                  <div>
                    <label className="text-xs text-muted-foreground">Régimen fiscal</label>
                    <select value={form.tax_regime} onChange={e => setForm(f => ({...f, tax_regime: e.target.value}))} className={inputCls}>
                      <option value="1">Responsable de IVA</option>
                      <option value="2">No responsable de IVA</option>
                    </select>
                  </div>
                </>
              )}

              {/* ── Contacto ── */}
              <div className="col-span-2 pt-2"><p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Contacto</p></div>
              <div><label className="text-xs text-muted-foreground">Nombre contacto</label><input value={form.contact_name} onChange={e => setForm(f => ({...f, contact_name: e.target.value}))} className={inputCls} /></div>
              <div><label className="text-xs text-muted-foreground">Email</label><input type="email" value={form.email} onChange={e => setForm(f => ({...f, email: e.target.value}))} className={inputCls} /></div>
              <div><label className="text-xs text-muted-foreground">Telefono</label><input value={form.phone} onChange={e => setForm(f => ({...f, phone: e.target.value}))} className={inputCls} /></div>
              <div><label className="text-xs text-muted-foreground">Plazo pago (dias)</label><input type="number" value={form.payment_terms_days} onChange={e => setForm(f => ({...f, payment_terms_days: e.target.value}))} className={inputCls} /></div>

              {/* ── Direccion ── */}
              <div className="col-span-2 pt-2"><p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Direccion</p></div>
              <div className="col-span-2"><label className="text-xs text-muted-foreground">Dirección</label><input value={form.address.line1} onChange={e => setForm(f => ({...f, address: {...f.address, line1: e.target.value}}))} placeholder="Calle, carrera, numero" className={inputCls} /></div>
              <div><label className="text-xs text-muted-foreground">Ciudad *</label><input value={form.address.city} onChange={e => setForm(f => ({...f, address: {...f.address, city: e.target.value}}))} placeholder="Ciudad" className={inputCls} required /></div>
              <div><input value={form.address.state} onChange={e => setForm(f => ({...f, address: {...f.address, state: e.target.value}}))} placeholder="Departamento / Estado" className={inputCls} /></div>
              <div><input value={form.address.country} onChange={e => setForm(f => ({...f, address: {...f.address, country: e.target.value}}))} placeholder="Pais (CO, DE...)" className={inputCls} /></div>
              <div><input value={form.address.zip} onChange={e => setForm(f => ({...f, address: {...f.address, zip: e.target.value}}))} placeholder="Codigo postal" className={inputCls} /></div>

              {/* Shipping address toggle (customer only) */}
              {form.is_customer && (
                <div className="col-span-2 pt-1">
                  <label className="flex items-center gap-2 text-xs text-muted-foreground cursor-pointer">
                    <input type="checkbox" checked={form.differentShippingAddress} onChange={e => setForm(f => ({...f, differentShippingAddress: e.target.checked}))} className="rounded" />
                    Direccion de envio diferente
                  </label>
                </div>
              )}
              {form.is_customer && form.differentShippingAddress && (<>
                <div className="col-span-2"><input value={form.shipping_address.line1} onChange={e => setForm(f => ({...f, shipping_address: {...f.shipping_address, line1: e.target.value}}))} placeholder="Calle, carrera, numero (envio)" className={inputCls} /></div>
                <div><input value={form.shipping_address.city} onChange={e => setForm(f => ({...f, shipping_address: {...f.shipping_address, city: e.target.value}}))} placeholder="Ciudad" className={inputCls} /></div>
                <div><input value={form.shipping_address.state} onChange={e => setForm(f => ({...f, shipping_address: {...f.shipping_address, state: e.target.value}}))} placeholder="Depto / Estado" className={inputCls} /></div>
                <div><input value={form.shipping_address.country} onChange={e => setForm(f => ({...f, shipping_address: {...f.shipping_address, country: e.target.value}}))} placeholder="Pais" className={inputCls} /></div>
                <div><input value={form.shipping_address.zip} onChange={e => setForm(f => ({...f, shipping_address: {...f.shipping_address, zip: e.target.value}}))} placeholder="Codigo postal" className={inputCls} /></div>
              </>)}

              {/* ── Proveedor ── */}
              {form.is_supplier && (<>
                <div className="col-span-2 pt-2"><p className="text-xs font-semibold text-blue-400 uppercase tracking-wider">Proveedor</p></div>
                <div><label className="text-xs text-muted-foreground">Tipo</label>
                  <select value={form.supplier_type_id} onChange={e => setForm(f => ({...f, supplier_type_id: e.target.value}))} className={inputCls}>
                    <option value="">Sin tipo</option>
                    {(Array.isArray(supplierTypes) ? supplierTypes : (supplierTypes as any)?.items ?? []).map((t: any) => <option key={t.id} value={t.id}>{t.name}</option>)}
                  </select>
                </div>
                <div><label className="text-xs text-muted-foreground">Lead time (dias)</label><input type="number" value={form.lead_time_days} onChange={e => setForm(f => ({...f, lead_time_days: e.target.value}))} className={inputCls} /></div>
              </>)}

              {/* ── Cliente ── */}
              {form.is_customer && (<>
                <div className="col-span-2 pt-2"><p className="text-xs font-semibold text-green-400 uppercase tracking-wider">Cliente</p></div>
                <div><label className="text-xs text-muted-foreground">Tipo</label>
                  <select value={form.customer_type_id} onChange={e => setForm(f => ({...f, customer_type_id: e.target.value}))} className={inputCls}>
                    <option value="">Sin tipo</option>
                    {(Array.isArray(customerTypes) ? customerTypes : (customerTypes as any)?.items ?? []).map((t: any) => <option key={t.id} value={t.id}>{t.name}</option>)}
                  </select>
                </div>
                <div><label className="text-xs text-muted-foreground">Limite credito</label><input type="number" value={form.credit_limit} onChange={e => setForm(f => ({...f, credit_limit: e.target.value}))} className={inputCls} /></div>
                <div><label className="text-xs text-muted-foreground">Descuento %</label><input type="number" min="0" max="100" value={form.discount_percent} onChange={e => setForm(f => ({...f, discount_percent: e.target.value}))} className={inputCls} /></div>
              </>)}

              <div className="col-span-2"><label className="text-xs text-muted-foreground">Notas</label><textarea value={form.notes} onChange={e => setForm(f => ({...f, notes: e.target.value}))} rows={2} className={inputCls} /></div>
            </div>

            <div className="flex gap-3 mt-4">
              <button type="button" onClick={() => { setShowCreate(false); setEditPartner(null); resetForm() }}
                className="flex-1 bg-secondary text-foreground rounded-xl px-4 py-2.5 text-sm font-medium hover:bg-gray-200 transition-colors">Cancelar</button>
              <button type="submit" disabled={createMut.isPending || updateMut.isPending || (!form.is_supplier && !form.is_customer)}
                className="flex-1 bg-gray-900 text-white rounded-xl px-4 py-2.5 text-sm font-semibold hover:bg-gray-800 disabled:opacity-50 transition-colors">
                {editPartner ? 'Guardar' : 'Crear'}
              </button>
            </div>
          </form>
        </div>
      )}
    </div>
  )
}
