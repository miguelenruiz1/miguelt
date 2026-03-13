import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Plus, Search, Users, Pencil, Trash2, Building2, ExternalLink,
} from 'lucide-react'
import { useCustomers, useCreateCustomer, useUpdateCustomer, useDeleteCustomer, useCustomerTypes } from '@/hooks/useInventory'
import { cn } from '@/lib/utils'
import type { Customer } from '@/types/inventory'

export function CustomersPage() {
  const navigate = useNavigate()
  const [search, setSearch] = useState('')
  const [typeFilter, setTypeFilter] = useState<string | undefined>()
  const [showModal, setShowModal] = useState(false)
  const [editing, setEditing] = useState<Customer | null>(null)

  const { data, isLoading } = useCustomers({ search: search || undefined, customer_type_id: typeFilter, limit: 100 })
  const { data: types } = useCustomerTypes()
  const createMut = useCreateCustomer()
  const updateMut = useUpdateCustomer()
  const deleteMut = useDeleteCustomer()

  const customers = data?.items ?? []

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    const fd = new FormData(e.currentTarget)
    const payload: Record<string, unknown> = {
      name: fd.get('name'),
      code: fd.get('code'),
      customer_type_id: fd.get('customer_type_id') || null,
      tax_id: fd.get('tax_id') || null,
      contact_name: fd.get('contact_name') || null,
      email: fd.get('email') || null,
      phone: fd.get('phone') || null,
      payment_terms_days: Number(fd.get('payment_terms_days') || 30),
      credit_limit: Number(fd.get('credit_limit') || 0),
      notes: fd.get('notes') || null,
    }
    if (editing) {
      await updateMut.mutateAsync({ id: editing.id, data: payload as Partial<Customer> })
    } else {
      await createMut.mutateAsync(payload as Partial<Customer>)
    }
    setShowModal(false)
    setEditing(null)
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Clientes</h1>
          <p className="text-sm text-slate-500 mt-1">Gestiona tus clientes para ventas y despachos</p>
        </div>
        <button onClick={() => { setEditing(null); setShowModal(true) }} className="flex items-center gap-2 px-4 py-2.5 text-sm font-semibold text-white bg-indigo-600 hover:bg-indigo-700 rounded-xl transition">
          <Plus className="h-4 w-4" /> Nuevo Cliente
        </button>
      </div>

      <div className="flex flex-wrap items-center gap-3">
        <div className="relative flex-1 min-w-[240px]">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
          <input type="text" placeholder="Buscar por nombre, codigo o email..." value={search} onChange={e => setSearch(e.target.value)} className="w-full pl-9 pr-3 py-2.5 text-sm bg-white border border-slate-200 rounded-xl focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-400 outline-none" />
        </div>
        <div className="flex gap-2">
          <button onClick={() => setTypeFilter(undefined)} className={cn('px-3 py-1.5 text-xs font-medium rounded-lg transition', !typeFilter ? 'bg-indigo-100 text-indigo-700' : 'bg-slate-100 text-slate-600 hover:bg-slate-200')}>Todos</button>
          {(types ?? []).map(t => (
            <button key={t.id} onClick={() => setTypeFilter(t.id)} className={cn('px-3 py-1.5 text-xs font-medium rounded-lg transition', typeFilter === t.id ? 'text-white' : 'bg-slate-100 text-slate-600 hover:bg-slate-200')} style={typeFilter === t.id ? { backgroundColor: t.color } : undefined}>{t.name}</button>
          ))}
        </div>
      </div>

      {isLoading ? (
        <div className="flex justify-center py-20"><div className="animate-spin rounded-full h-6 w-6 border-b-2 border-indigo-600" /></div>
      ) : (<>
        {/* Mobile cards */}
        <div className="space-y-3 p-4 md:hidden">
          {customers.length === 0 ? (
            <p className="text-center text-slate-400 py-8">Sin clientes registrados</p>
          ) : customers.map(c => (
            <div key={c.id} className="rounded-xl border border-gray-200 bg-white p-4 shadow-sm space-y-2" onClick={() => navigate(`/inventario/clientes/${c.id}`)}>
              <div className="flex items-center justify-between">
                <span className="font-semibold text-slate-900">{c.name}</span>
                <span className="font-mono text-xs text-slate-500">{c.code}</span>
              </div>
              <div className="space-y-1 text-sm">
                <div className="flex justify-between"><span className="text-slate-400">NIT/CC</span><span className="text-slate-600">{c.tax_id || '—'}</span></div>
                <div className="flex justify-between"><span className="text-slate-400">Email</span><span className="text-slate-600">{c.email || '—'}</span></div>
                <div className="flex justify-between"><span className="text-slate-400">Telefono</span><span className="text-slate-600">{c.phone || '—'}</span></div>
              </div>
              <div className="flex items-center justify-between pt-1" onClick={e => e.stopPropagation()}>
                <span className="text-xs text-slate-400">{c.payment_terms_days}d pago</span>
                <div className="flex gap-1">
                  <button onClick={() => navigate(`/inventario/portal/${c.id}`)} title="Portal de autogestion" className="p-1.5 text-slate-400 hover:text-emerald-600 rounded-lg hover:bg-emerald-50 transition"><ExternalLink className="h-4 w-4" /></button>
                  <button onClick={() => { setEditing(c); setShowModal(true) }} className="p-1.5 text-slate-400 hover:text-indigo-600 rounded-lg hover:bg-indigo-50 transition"><Pencil className="h-4 w-4" /></button>
                  <button onClick={() => { if (confirm('Eliminar?')) deleteMut.mutate(c.id) }} className="p-1.5 text-slate-400 hover:text-red-600 rounded-lg hover:bg-red-50 transition"><Trash2 className="h-4 w-4" /></button>
                </div>
              </div>
            </div>
          ))}
        </div>

        {/* Desktop table */}
        <div className="hidden md:block bg-white rounded-2xl border border-slate-200/60 shadow-sm overflow-hidden">
          <div className="overflow-x-auto">
          <table className="w-full text-sm min-w-[600px]">
            <thead><tr className="bg-slate-50 text-left text-xs font-semibold text-slate-500 uppercase">
              <th className="px-6 py-3">Codigo</th><th className="px-6 py-3">Nombre</th><th className="px-6 py-3">NIT/CC</th><th className="px-6 py-3">Email</th><th className="px-6 py-3">Telefono</th><th className="px-6 py-3">Terminos</th><th className="px-6 py-3 text-right">Acciones</th>
            </tr></thead>
            <tbody className="divide-y divide-slate-100">
              {customers.map(c => (
                <tr key={c.id} className="hover:bg-slate-50/60 cursor-pointer" onClick={() => navigate(`/inventario/clientes/${c.id}`)}>
                  <td className="px-6 py-3 font-mono text-xs">{c.code}</td>
                  <td className="px-6 py-3 font-semibold text-slate-900">{c.name}</td>
                  <td className="px-6 py-3 text-slate-500">{c.tax_id || '—'}</td>
                  <td className="px-6 py-3 text-slate-500">{c.email || '—'}</td>
                  <td className="px-6 py-3 text-slate-500">{c.phone || '—'}</td>
                  <td className="px-6 py-3 text-slate-500">{c.payment_terms_days}d</td>
                  <td className="px-6 py-3 text-right" onClick={e => e.stopPropagation()}>
                    <button onClick={() => navigate(`/inventario/portal/${c.id}`)} title="Portal de autogestion" className="p-1.5 text-slate-400 hover:text-emerald-600 rounded-lg hover:bg-emerald-50 transition"><ExternalLink className="h-4 w-4" /></button>
                    <button onClick={() => { setEditing(c); setShowModal(true) }} className="p-1.5 text-slate-400 hover:text-indigo-600 rounded-lg hover:bg-indigo-50 transition ml-1"><Pencil className="h-4 w-4" /></button>
                    <button onClick={() => { if (confirm('Eliminar?')) deleteMut.mutate(c.id) }} className="p-1.5 text-slate-400 hover:text-red-600 rounded-lg hover:bg-red-50 transition ml-1"><Trash2 className="h-4 w-4" /></button>
                  </td>
                </tr>
              ))}
              {customers.length === 0 && <tr><td colSpan={7} className="px-6 py-12 text-center text-slate-400">Sin clientes registrados</td></tr>}
            </tbody>
          </table>
          </div>
        </div>
      </>)}

      {showModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 backdrop-blur-sm" onClick={() => setShowModal(false)}>
          <form onSubmit={handleSubmit} onClick={e => e.stopPropagation()} className="bg-white rounded-2xl shadow-xl w-full max-w-lg p-6 space-y-4">
            <h3 className="text-lg font-bold text-slate-900 flex items-center gap-2"><Building2 className="h-5 w-5 text-indigo-500" /> {editing ? 'Editar' : 'Nuevo'} Cliente</h3>
            <div className="grid grid-cols-2 gap-4">
              <div><label className="block text-xs font-medium text-slate-600 mb-1">Nombre *</label><input name="name" required defaultValue={editing?.name ?? ''} className="w-full px-3 py-2 text-sm border border-slate-200 rounded-xl focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-400 outline-none" /></div>
              <div><label className="block text-xs font-medium text-slate-600 mb-1">Codigo *</label><input name="code" required defaultValue={editing?.code ?? ''} className="w-full px-3 py-2 text-sm border border-slate-200 rounded-xl focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-400 outline-none" /></div>
              <div><label className="block text-xs font-medium text-slate-600 mb-1">NIT / CC</label><input name="tax_id" defaultValue={editing?.tax_id ?? ''} className="w-full px-3 py-2 text-sm border border-slate-200 rounded-xl focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-400 outline-none" /></div>
              <div><label className="block text-xs font-medium text-slate-600 mb-1">Tipo</label><select name="customer_type_id" defaultValue={editing?.customer_type_id ?? ''} className="w-full px-3 py-2 text-sm border border-slate-200 rounded-xl focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-400 outline-none"><option value="">Sin tipo</option>{(types ?? []).map(t => <option key={t.id} value={t.id}>{t.name}</option>)}</select></div>
              <div><label className="block text-xs font-medium text-slate-600 mb-1">Contacto</label><input name="contact_name" defaultValue={editing?.contact_name ?? ''} className="w-full px-3 py-2 text-sm border border-slate-200 rounded-xl focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-400 outline-none" /></div>
              <div><label className="block text-xs font-medium text-slate-600 mb-1">Email</label><input name="email" type="email" defaultValue={editing?.email ?? ''} className="w-full px-3 py-2 text-sm border border-slate-200 rounded-xl focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-400 outline-none" /></div>
              <div><label className="block text-xs font-medium text-slate-600 mb-1">Telefono</label><input name="phone" defaultValue={editing?.phone ?? ''} className="w-full px-3 py-2 text-sm border border-slate-200 rounded-xl focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-400 outline-none" /></div>
              <div><label className="block text-xs font-medium text-slate-600 mb-1">Dias de pago</label><input name="payment_terms_days" type="number" defaultValue={editing?.payment_terms_days ?? 30} className="w-full px-3 py-2 text-sm border border-slate-200 rounded-xl focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-400 outline-none" /></div>
              <div><label className="block text-xs font-medium text-slate-600 mb-1">Limite credito</label><input name="credit_limit" type="number" defaultValue={editing?.credit_limit ?? 0} className="w-full px-3 py-2 text-sm border border-slate-200 rounded-xl focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-400 outline-none" /></div>
            </div>
            <div><label className="block text-xs font-medium text-slate-600 mb-1">Notas</label><textarea name="notes" rows={2} defaultValue={editing?.notes ?? ''} className="w-full px-3 py-2 text-sm border border-slate-200 rounded-xl focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-400 outline-none resize-none" /></div>
            <div className="flex justify-end gap-3 pt-2">
              <button type="button" onClick={() => setShowModal(false)} className="px-4 py-2 text-sm font-medium text-slate-600 hover:text-slate-900 transition">Cancelar</button>
              <button type="submit" disabled={createMut.isPending || updateMut.isPending} className="px-5 py-2 text-sm font-semibold text-white bg-indigo-600 hover:bg-indigo-700 rounded-xl disabled:opacity-50 transition">{editing ? 'Guardar' : 'Crear'}</button>
            </div>
          </form>
        </div>
      )}
    </div>
  )
}
