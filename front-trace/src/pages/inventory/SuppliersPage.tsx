import { useState } from 'react'
import { Plus, Truck, Search, Trash2 } from 'lucide-react'
import { cn } from '@/lib/utils'
import { CopyableId } from '@/components/inventory/CopyableId'
import {
  useSuppliers, useCreateSupplier, useUpdateSupplier, useDeleteSupplier,
  useSupplierTypes, useSupplierFields,
} from '@/hooks/useInventory'
import { useUserLookup } from '@/hooks/useUserLookup'
import type { CustomSupplierField, Supplier, SupplierType } from '@/types/inventory'

// ─── Custom supplier field input ──────────────────────────────────────────────

function SupplierFieldInput({
  field,
  value,
  onChange,
}: {
  field: CustomSupplierField
  value: string
  onChange: (val: string) => void
}) {
  if (field.field_type === 'boolean') {
    return (
      <label className="flex items-center gap-2 text-sm text-slate-600 cursor-pointer">
        <input
          type="checkbox"
          checked={value === 'true'}
          onChange={e => onChange(e.target.checked ? 'true' : 'false')}
          className="rounded"
        />
        {field.label}{field.required && ' *'}
      </label>
    )
  }
  if (field.field_type === 'select' && field.options) {
    return (
      <select
        required={field.required}
        value={value}
        onChange={e => onChange(e.target.value)}
        className="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400"
      >
        <option value="">{field.label}</option>
        {field.options.map(opt => <option key={opt} value={opt}>{opt}</option>)}
      </select>
    )
  }
  return (
    <input
      type={field.field_type === 'number' ? 'number' : field.field_type === 'date' ? 'date' : 'text'}
      required={field.required}
      value={value}
      onChange={e => onChange(e.target.value)}
      placeholder={`${field.label}${field.required ? ' *' : ''}`}
      className="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400"
    />
  )
}

// ─── Supplier Modal ───────────────────────────────────────────────────────────

function SupplierModal({
  supplier,
  supplierTypes,
  supplierFields,
  onClose,
}: {
  supplier: Supplier | null
  supplierTypes: SupplierType[]
  supplierFields: CustomSupplierField[]
  onClose: () => void
}) {
  const create = useCreateSupplier()
  const update = useUpdateSupplier()
  const remove = useDeleteSupplier()
  const [confirmDelete, setConfirmDelete] = useState(false)

  const activeFields = supplierFields.filter(f => f.is_active)

  const [form, setForm] = useState({
    name: supplier?.name ?? '',
    code: supplier?.code ?? '',
    supplier_type_id: supplier?.supplier_type_id ?? '',
    contact_name: supplier?.contact_name ?? '',
    email: supplier?.email ?? '',
    phone: supplier?.phone ?? '',
    payment_terms_days: String(supplier?.payment_terms_days ?? 30),
    lead_time_days: String(supplier?.lead_time_days ?? 7),
    notes: supplier?.notes ?? '',
    is_active: supplier?.is_active ?? true,
  })

  const [customAttrs, setCustomAttrs] = useState<Record<string, string>>(
    Object.fromEntries(
      Object.entries(supplier?.custom_attributes ?? {}).map(([k, v]) => [k, String(v)])
    )
  )

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    const data = {
      ...form,
      supplier_type_id: form.supplier_type_id || null,
      payment_terms_days: Number(form.payment_terms_days),
      lead_time_days: Number(form.lead_time_days),
      custom_attributes: customAttrs,
    }
    if (supplier) {
      await update.mutateAsync({ id: supplier.id, data })
    } else {
      await create.mutateAsync(data)
    }
    onClose()
  }

  const isPending = create.isPending || update.isPending

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 backdrop-blur-sm">
      <div className="w-full max-w-lg bg-white rounded-3xl shadow-2xl p-6 max-h-[90vh] overflow-y-auto">
        <h2 className="text-lg font-bold text-slate-900 mb-4">
          {supplier ? 'Editar Proveedor' : 'Nuevo Proveedor'}
        </h2>
        <form onSubmit={handleSubmit} className="space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <input required value={form.name} onChange={e => setForm(f => ({ ...f, name: e.target.value }))}
              placeholder="Nombre *"
              className="rounded-xl border border-slate-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400" />
            <input required value={form.code} onChange={e => setForm(f => ({ ...f, code: e.target.value }))}
              placeholder="Código *"
              className="rounded-xl border border-slate-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400" />
          </div>

          {/* Supplier type selector */}
          <select
            value={form.supplier_type_id}
            onChange={e => setForm(f => ({ ...f, supplier_type_id: e.target.value }))}
            className="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400"
          >
            <option value="">Sin tipo de proveedor</option>
            {supplierTypes.map(t => (
              <option key={t.id} value={t.id}>{t.name}</option>
            ))}
          </select>

          <input value={form.contact_name} onChange={e => setForm(f => ({ ...f, contact_name: e.target.value }))}
            placeholder="Contacto"
            className="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400" />
          <div className="grid grid-cols-2 gap-3">
            <input type="email" value={form.email} onChange={e => setForm(f => ({ ...f, email: e.target.value }))}
              placeholder="Email"
              className="rounded-xl border border-slate-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400" />
            <input value={form.phone} onChange={e => setForm(f => ({ ...f, phone: e.target.value }))}
              placeholder="Teléfono"
              className="rounded-xl border border-slate-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400" />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <input type="number" value={form.payment_terms_days}
              onChange={e => setForm(f => ({ ...f, payment_terms_days: e.target.value }))}
              placeholder="Días pago"
              className="rounded-xl border border-slate-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400" />
            <input type="number" value={form.lead_time_days}
              onChange={e => setForm(f => ({ ...f, lead_time_days: e.target.value }))}
              placeholder="Lead time (días)"
              className="rounded-xl border border-slate-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400" />
          </div>
          <textarea value={form.notes} onChange={e => setForm(f => ({ ...f, notes: e.target.value }))}
            placeholder="Notas"
            rows={2}
            className="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400 resize-none" />

          {/* Custom supplier fields */}
          {activeFields.length > 0 && (
            <div className="pt-2 space-y-2 border-t border-slate-100">
              <p className="text-xs font-semibold text-slate-400 uppercase tracking-wide">Campos personalizados</p>
              {activeFields.map(field => (
                <SupplierFieldInput
                  key={field.id}
                  field={field}
                  value={customAttrs[field.field_key] ?? ''}
                  onChange={val => setCustomAttrs(a => ({ ...a, [field.field_key]: val }))}
                />
              ))}
            </div>
          )}

          <label className="flex items-center gap-2 text-sm text-slate-600">
            <input type="checkbox" checked={form.is_active} onChange={e => setForm(f => ({ ...f, is_active: e.target.checked }))} className="rounded" />
            Activo
          </label>

          {/* Delete confirmation */}
          {supplier && confirmDelete && (
            <div className="rounded-xl border border-red-200 bg-red-50 p-3 space-y-2">
              <p className="text-sm text-red-700 font-medium">¿Eliminar este proveedor?</p>
              <p className="text-xs text-red-500">Esta acción no se puede deshacer. No se puede eliminar si tiene órdenes de compra activas.</p>
              <div className="flex gap-2">
                <button type="button" onClick={() => setConfirmDelete(false)}
                  className="flex-1 rounded-lg border border-slate-200 px-3 py-1.5 text-xs text-slate-600 hover:bg-white">
                  No, cancelar
                </button>
                <button type="button" disabled={remove.isPending}
                  onClick={async () => {
                    try {
                      await remove.mutateAsync(supplier.id)
                      onClose()
                    } catch (err: unknown) {
                      alert(err instanceof Error ? err.message : 'Error al eliminar')
                    }
                  }}
                  className="flex-1 rounded-lg bg-red-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-red-700 disabled:opacity-60">
                  {remove.isPending ? 'Eliminando…' : 'Sí, eliminar'}
                </button>
              </div>
            </div>
          )}

          <div className="flex gap-3 pt-2">
            {supplier && !confirmDelete && (
              <button type="button" onClick={() => setConfirmDelete(true)}
                className="rounded-xl border border-red-200 px-3 py-2 text-sm text-red-500 hover:bg-red-50 hover:text-red-700 transition-colors"
                title="Eliminar proveedor">
                <Trash2 className="h-4 w-4" />
              </button>
            )}
            <button type="button" onClick={onClose} className="flex-1 rounded-xl border border-slate-200 px-4 py-2 text-sm text-slate-600 hover:bg-slate-50">Cancelar</button>
            <button type="submit" disabled={isPending} className="flex-1 rounded-xl bg-indigo-600 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-700 disabled:opacity-60">
              {isPending ? 'Guardando…' : supplier ? 'Guardar' : 'Crear proveedor'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

// ─── Main Page ────────────────────────────────────────────────────────────────

export function SuppliersPage() {
  const { data: suppliers = [], isLoading } = useSuppliers()
  const { data: supplierTypes = [] } = useSupplierTypes()
  const { data: supplierFields = [] } = useSupplierFields()
  const [modal, setModal] = useState<Supplier | null | 'new'>(null)
  const [filterType, setFilterType] = useState('')
  const [search, setSearch] = useState('')
  const { resolve } = useUserLookup(suppliers?.map(s => s.created_by) ?? [])

  const filtered = suppliers.filter(s => {
    if (filterType && s.supplier_type_id !== filterType) return false
    if (search) {
      const q = search.toLowerCase()
      return (
        s.name.toLowerCase().includes(q) ||
        s.code.toLowerCase().includes(q) ||
        (s.contact_name ?? '').toLowerCase().includes(q) ||
        (s.email ?? '').toLowerCase().includes(q)
      )
    }
    return true
  })

  return (
    <div className="max-w-5xl mx-auto p-6 space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-slate-900">Proveedores</h1>
        <button onClick={() => setModal('new')}
          className="flex items-center gap-2 rounded-2xl bg-indigo-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-indigo-700 shadow-sm">
          <Plus className="h-4 w-4" /> Nuevo proveedor
        </button>
      </div>

      {/* Search */}
      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
        <input
          type="text"
          value={search}
          onChange={e => setSearch(e.target.value)}
          placeholder="Buscar por nombre, código, contacto o email…"
          className="w-full rounded-xl border border-slate-200 pl-10 pr-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400 bg-white"
        />
      </div>

      {/* Type filter chips */}
      {supplierTypes.length > 0 && (
        <div className="flex flex-wrap gap-2">
          <button
            onClick={() => setFilterType('')}
            className={cn(
              'rounded-full px-3 py-1 text-xs font-semibold transition-colors',
              filterType === '' ? 'bg-slate-800 text-white' : 'bg-slate-100 text-slate-600 hover:bg-slate-200',
            )}
          >
            Todos
          </button>
          {supplierTypes.map(t => (
            <button
              key={t.id}
              onClick={() => setFilterType(t.id)}
              className={cn(
                'rounded-full px-3 py-1 text-xs font-semibold transition-colors text-white',
                filterType === t.id ? 'opacity-100 ring-2 ring-offset-1' : 'opacity-70 hover:opacity-100',
              )}
              style={{ backgroundColor: t.color ?? '#f59e0b' }}
            >
              {t.name}
            </button>
          ))}
        </div>
      )}

      <div className="bg-white rounded-2xl border border-slate-100 shadow-sm overflow-hidden">
        {isLoading ? (
          <div className="p-8 text-center text-slate-400">Cargando…</div>
        ) : filtered.length === 0 ? (
          <div className="p-8 text-center">
            <Truck className="h-10 w-10 text-slate-200 mx-auto mb-3" />
            <p className="text-sm text-slate-400">Sin proveedores registrados</p>
          </div>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-slate-50 border-b border-slate-100">
              <tr>
                {['ID', 'Nombre', 'Código', 'Tipo', 'Contacto', 'Lead time', 'Creado por', 'Estado'].map(h => (
                  <th key={h} className="px-4 py-3 text-left text-xs font-semibold text-slate-400 uppercase tracking-wide">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-50">
              {filtered.map(s => {
                const sType = supplierTypes.find(t => t.id === s.supplier_type_id)
                return (
                  <tr key={s.id} onClick={() => setModal(s)} className="cursor-pointer hover:bg-slate-50 transition-colors">
                    <td className="px-4 py-3 max-w-[80px]"><CopyableId id={s.id} /></td>
                    <td className="px-4 py-3 font-medium text-slate-900">{s.name}</td>
                    <td className="px-4 py-3 font-mono text-xs text-slate-500">{s.code}</td>
                    <td className="px-4 py-3">
                      {sType ? (
                        <span
                          className="rounded-full px-2 py-0.5 text-xs font-semibold text-white"
                          style={{ backgroundColor: sType.color ?? '#f59e0b' }}
                        >
                          {sType.name}
                        </span>
                      ) : <span className="text-slate-300 text-xs">—</span>}
                    </td>
                    <td className="px-4 py-3 text-slate-600">{s.contact_name ?? '—'}</td>
                    <td className="px-4 py-3 text-slate-500">{s.lead_time_days}d</td>
                    <td className="px-4 py-3 text-slate-400 text-xs">{resolve(s.created_by)}</td>
                    <td className="px-4 py-3">
                      <span className={cn(
                        'rounded-full px-2 py-0.5 text-xs font-semibold',
                        s.is_active ? 'bg-emerald-50 text-emerald-700' : 'bg-slate-100 text-slate-500',
                      )}>
                        {s.is_active ? 'Activo' : 'Inactivo'}
                      </span>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        )}
      </div>

      {modal && (
        <SupplierModal
          supplier={modal === 'new' ? null : modal}
          supplierTypes={supplierTypes}
          supplierFields={supplierFields}
          onClose={() => setModal(null)}
        />
      )}
    </div>
  )
}
