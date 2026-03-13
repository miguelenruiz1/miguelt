import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import {
  Settings2, Plus, Pencil, Trash2, X, Tag, ShoppingBag, Truck,
  ArrowLeftRight, Warehouse, AlertTriangle, Gauge, CheckCircle2, Hash,
  ChevronRight, Users, ShieldCheck,
} from 'lucide-react'
import { useConfirm } from '@/store/confirm'
import {
  useProductTypes, useCreateProductType, useUpdateProductType, useDeleteProductType,
  useOrderTypes, useCreateOrderType, useUpdateOrderType, useDeleteOrderType,
  useSupplierTypes, useCreateSupplierType, useUpdateSupplierType, useDeleteSupplierType,
  useMovementTypes, useCreateMovementType, useUpdateMovementType, useDeleteMovementType,
  useWarehouseTypes, useCreateWarehouseType, useUpdateWarehouseType, useDeleteWarehouseType,
  useEventTypes, useCreateEventType, useUpdateEventType, useDeleteEventType,
  useEventSeverities, useCreateEventSeverity, useUpdateEventSeverity, useDeleteEventSeverity,
  useEventStatuses, useCreateEventStatus, useUpdateEventStatus, useDeleteEventStatus,
  useSerialStatuses, useCreateSerialStatus, useUpdateSerialStatus, useDeleteSerialStatus,
  useApprovalThreshold, useUpdateApprovalThreshold,
  useCustomerTypes, useCreateCustomerType, useUpdateCustomerType, useDeleteCustomerType,
} from '@/hooks/useInventory'
import { cn } from '@/lib/utils'
import type {
  CustomerType,
  DynamicMovementType, DynamicWarehouseType,
  EventSeverity, EventStatus, EventType,
  OrderType,
  ProductType, SerialStatus, SupplierType,
} from '@/types/inventory'

// ─── Shared TypeCard ──────────────────────────────────────────────────────────

function TypeBadge({ color, name }: { color: string | null; name: string }) {
  return (
    <span
      className="inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-semibold text-white"
      style={{ backgroundColor: color ?? '#6366f1' }}
    >
      {name}
    </span>
  )
}

// ─── Product Types ────────────────────────────────────────────────────────────

function ProductTypesTab() {
  const { data: types = [], isLoading } = useProductTypes()
  const create = useCreateProductType()
  const update = useUpdateProductType()
  const del = useDeleteProductType()
  const confirm = useConfirm()
  const [showForm, setShowForm] = useState(false)
  const [editing, setEditing] = useState<ProductType | null>(null)
  const [form, setForm] = useState({ name: '', description: '', color: '#6366f1' })

  function openCreate() {
    setEditing(null)
    setForm({ name: '', description: '', color: '#6366f1' })
    setShowForm(true)
  }

  function openEdit(t: ProductType) {
    setEditing(t)
    setForm({ name: t.name, description: t.description ?? '', color: t.color ?? '#6366f1' })
    setShowForm(true)
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault()
    if (editing) {
      await update.mutateAsync({ id: editing.id, data: form })
    } else {
      await create.mutateAsync(form)
    }
    setShowForm(false)
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <p className="text-sm text-slate-500">Tipos de producto para clasificar tu catálogo</p>
        <button
          onClick={openCreate}
          className="flex items-center gap-1.5 rounded-xl bg-indigo-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-indigo-700"
        >
          <Plus className="h-3.5 w-3.5" /> Nuevo tipo
        </button>
      </div>

      {showForm && (
        <form onSubmit={submit} className="rounded-xl border border-indigo-200 bg-indigo-50 p-4 space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs font-medium text-slate-600 mb-1 block">Nombre *</label>
              <input required value={form.name} onChange={e => setForm(f => ({ ...f, name: e.target.value }))}
                className="w-full rounded-lg border border-slate-200 px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400" />
            </div>
            <div>
              <label className="text-xs font-medium text-slate-600 mb-1 block">Color</label>
              <input type="color" value={form.color} onChange={e => setForm(f => ({ ...f, color: e.target.value }))}
                className="h-9 w-full rounded-lg border border-slate-200 cursor-pointer" />
            </div>
          </div>
          <div>
            <label className="text-xs font-medium text-slate-600 mb-1 block">Descripción</label>
            <input value={form.description} onChange={e => setForm(f => ({ ...f, description: e.target.value }))}
              className="w-full rounded-lg border border-slate-200 px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400" />
          </div>
          <div className="flex justify-end gap-2">
            <button type="button" onClick={() => setShowForm(false)} className="rounded-lg px-3 py-1.5 text-xs text-slate-600 hover:bg-slate-100">
              <X className="h-3.5 w-3.5" />
            </button>
            <button type="submit" disabled={create.isPending || update.isPending}
              className="rounded-lg bg-indigo-600 px-4 py-1.5 text-xs font-semibold text-white hover:bg-indigo-700 disabled:opacity-50">
              {editing ? 'Guardar' : 'Crear'}
            </button>
          </div>
        </form>
      )}

      {isLoading ? (
        <div className="text-sm text-slate-400 py-4">Cargando...</div>
      ) : types.length === 0 ? (
        <div className="rounded-xl border border-dashed border-slate-200 p-8 text-center text-sm text-slate-400">
          Sin tipos de producto. Crea el primero.
        </div>
      ) : (
        <div className="flex flex-wrap gap-2">
          {types.map(t => (
            <div key={t.id} className="flex items-center gap-2 rounded-xl bg-white border border-slate-100 px-3 py-2 shadow-sm">
              <TypeBadge color={t.color} name={t.name} />
              <button onClick={() => openEdit(t)} className="text-slate-400 hover:text-indigo-600">
                <Pencil className="h-3.5 w-3.5" />
              </button>
              <button onClick={async () => { if (await confirm({ message: `¿Eliminar "${t.name}"?`, confirmLabel: 'Eliminar' })) del.mutate(t.id) }} disabled={del.isPending} className="text-slate-400 hover:text-red-500">
                <Trash2 className="h-3.5 w-3.5" />
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

// ─── Order Types ──────────────────────────────────────────────────────────────

function OrderTypesTab() {
  const { data: types = [], isLoading } = useOrderTypes()
  const create = useCreateOrderType()
  const update = useUpdateOrderType()
  const del = useDeleteOrderType()
  const confirm = useConfirm()
  const [showForm, setShowForm] = useState(false)
  const [editing, setEditing] = useState<OrderType | null>(null)
  const [form, setForm] = useState({ name: '', description: '', color: '#10b981' })

  function openCreate() {
    setEditing(null)
    setForm({ name: '', description: '', color: '#10b981' })
    setShowForm(true)
  }

  function openEdit(t: OrderType) {
    setEditing(t)
    setForm({ name: t.name, description: t.description ?? '', color: t.color ?? '#10b981' })
    setShowForm(true)
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault()
    if (editing) {
      await update.mutateAsync({ id: editing.id, data: form })
    } else {
      await create.mutateAsync(form)
    }
    setShowForm(false)
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <p className="text-sm text-slate-500">Tipos de orden de compra para clasificar tus compras</p>
        <button
          onClick={openCreate}
          className="flex items-center gap-1.5 rounded-xl bg-emerald-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-emerald-700"
        >
          <Plus className="h-3.5 w-3.5" /> Nuevo tipo
        </button>
      </div>

      {showForm && (
        <form onSubmit={submit} className="rounded-xl border border-emerald-200 bg-emerald-50 p-4 space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs font-medium text-slate-600 mb-1 block">Nombre *</label>
              <input required value={form.name} onChange={e => setForm(f => ({ ...f, name: e.target.value }))}
                className="w-full rounded-lg border border-slate-200 px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-400" />
            </div>
            <div>
              <label className="text-xs font-medium text-slate-600 mb-1 block">Color</label>
              <input type="color" value={form.color} onChange={e => setForm(f => ({ ...f, color: e.target.value }))}
                className="h-9 w-full rounded-lg border border-slate-200 cursor-pointer" />
            </div>
          </div>
          <div>
            <label className="text-xs font-medium text-slate-600 mb-1 block">Descripción</label>
            <input value={form.description} onChange={e => setForm(f => ({ ...f, description: e.target.value }))}
              className="w-full rounded-lg border border-slate-200 px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-400" />
          </div>
          <div className="flex justify-end gap-2">
            <button type="button" onClick={() => setShowForm(false)} className="rounded-lg px-3 py-1.5 text-xs text-slate-600 hover:bg-slate-100">
              <X className="h-3.5 w-3.5" />
            </button>
            <button type="submit" disabled={create.isPending || update.isPending}
              className="rounded-lg bg-emerald-600 px-4 py-1.5 text-xs font-semibold text-white hover:bg-emerald-700 disabled:opacity-50">
              {editing ? 'Guardar' : 'Crear'}
            </button>
          </div>
        </form>
      )}

      {isLoading ? (
        <div className="text-sm text-slate-400 py-4">Cargando...</div>
      ) : types.length === 0 ? (
        <div className="rounded-xl border border-dashed border-slate-200 p-8 text-center text-sm text-slate-400">
          Sin tipos de orden. Crea el primero.
        </div>
      ) : (
        <div className="flex flex-wrap gap-2">
          {types.map(t => (
            <div key={t.id} className="flex items-center gap-2 rounded-xl bg-white border border-slate-100 px-3 py-2 shadow-sm">
              <TypeBadge color={t.color} name={t.name} />
              <button onClick={() => openEdit(t)} className="text-slate-400 hover:text-emerald-600">
                <Pencil className="h-3.5 w-3.5" />
              </button>
              <button onClick={async () => { if (await confirm({ message: `¿Eliminar "${t.name}"?`, confirmLabel: 'Eliminar' })) del.mutate(t.id) }} disabled={del.isPending} className="text-slate-400 hover:text-red-500">
                <Trash2 className="h-3.5 w-3.5" />
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

// ─── Supplier Types ───────────────────────────────────────────────────────────

function SupplierTypesTab() {
  const { data: types = [], isLoading } = useSupplierTypes()
  const create = useCreateSupplierType()
  const update = useUpdateSupplierType()
  const del = useDeleteSupplierType()
  const confirm = useConfirm()
  const [showForm, setShowForm] = useState(false)
  const [editing, setEditing] = useState<SupplierType | null>(null)
  const [form, setForm] = useState({ name: '', description: '', color: '#f59e0b' })

  function openCreate() {
    setEditing(null)
    setForm({ name: '', description: '', color: '#f59e0b' })
    setShowForm(true)
  }

  function openEdit(t: SupplierType) {
    setEditing(t)
    setForm({ name: t.name, description: t.description ?? '', color: t.color ?? '#f59e0b' })
    setShowForm(true)
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault()
    if (editing) {
      await update.mutateAsync({ id: editing.id, data: form })
    } else {
      await create.mutateAsync(form)
    }
    setShowForm(false)
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <p className="text-sm text-slate-500">Tipos de proveedor para clasificar tus contactos comerciales</p>
        <button
          onClick={openCreate}
          className="flex items-center gap-1.5 rounded-xl bg-amber-500 px-3 py-1.5 text-xs font-semibold text-white hover:bg-amber-600"
        >
          <Plus className="h-3.5 w-3.5" /> Nuevo tipo
        </button>
      </div>

      {showForm && (
        <form onSubmit={submit} className="rounded-xl border border-amber-200 bg-amber-50 p-4 space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs font-medium text-slate-600 mb-1 block">Nombre *</label>
              <input required value={form.name} onChange={e => setForm(f => ({ ...f, name: e.target.value }))}
                className="w-full rounded-lg border border-slate-200 px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-amber-400" />
            </div>
            <div>
              <label className="text-xs font-medium text-slate-600 mb-1 block">Color</label>
              <input type="color" value={form.color} onChange={e => setForm(f => ({ ...f, color: e.target.value }))}
                className="h-9 w-full rounded-lg border border-slate-200 cursor-pointer" />
            </div>
          </div>
          <div>
            <label className="text-xs font-medium text-slate-600 mb-1 block">Descripción</label>
            <input value={form.description} onChange={e => setForm(f => ({ ...f, description: e.target.value }))}
              className="w-full rounded-lg border border-slate-200 px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-amber-400" />
          </div>
          <div className="flex justify-end gap-2">
            <button type="button" onClick={() => setShowForm(false)} className="rounded-lg px-3 py-1.5 text-xs text-slate-600 hover:bg-slate-100">
              <X className="h-3.5 w-3.5" />
            </button>
            <button type="submit" disabled={create.isPending || update.isPending}
              className="rounded-lg bg-amber-500 px-4 py-1.5 text-xs font-semibold text-white hover:bg-amber-600 disabled:opacity-50">
              {editing ? 'Guardar' : 'Crear'}
            </button>
          </div>
        </form>
      )}

      {isLoading ? (
        <div className="text-sm text-slate-400 py-4">Cargando...</div>
      ) : types.length === 0 ? (
        <div className="rounded-xl border border-dashed border-slate-200 p-8 text-center text-sm text-slate-400">
          Sin tipos de proveedor. Crea el primero.
        </div>
      ) : (
        <div className="flex flex-wrap gap-2">
          {types.map(t => (
            <div key={t.id} className="flex items-center gap-2 rounded-xl bg-white border border-slate-100 px-3 py-2 shadow-sm">
              <TypeBadge color={t.color} name={t.name} />
              <button onClick={() => openEdit(t)} className="text-slate-400 hover:text-amber-600">
                <Pencil className="h-3.5 w-3.5" />
              </button>
              <button onClick={async () => { if (await confirm({ message: `¿Eliminar "${t.name}"?`, confirmLabel: 'Eliminar' })) del.mutate(t.id) }} disabled={del.isPending} className="text-slate-400 hover:text-red-500">
                <Trash2 className="h-3.5 w-3.5" />
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

// ─── Movement Types ──────────────────────────────────────────────────────────

const DIRECTIONS = [
  { value: 'in', label: 'Entrada' },
  { value: 'out', label: 'Salida' },
  { value: 'internal', label: 'Interno' },
  { value: 'neutral', label: 'Neutro' },
]

function MovementTypesTab() {
  const { data: types = [], isLoading } = useMovementTypes()
  const create = useCreateMovementType()
  const update = useUpdateMovementType()
  const del = useDeleteMovementType()
  const confirm = useConfirm()
  const [showForm, setShowForm] = useState(false)
  const [editing, setEditing] = useState<DynamicMovementType | null>(null)
  const [form, setForm] = useState({
    name: '', description: '', color: '#10b981', direction: 'in' as string,
    affects_cost: true, requires_reference: false,
  })

  function openCreate() {
    setEditing(null)
    setForm({ name: '', description: '', color: '#10b981', direction: 'in', affects_cost: true, requires_reference: false })
    setShowForm(true)
  }

  function openEdit(t: DynamicMovementType) {
    setEditing(t)
    setForm({
      name: t.name, description: t.description ?? '', color: t.color ?? '#10b981',
      direction: t.direction, affects_cost: t.affects_cost, requires_reference: t.requires_reference,
    })
    setShowForm(true)
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault()
    if (editing) {
      await update.mutateAsync({ id: editing.id, data: form })
    } else {
      await create.mutateAsync(form)
    }
    setShowForm(false)
  }

  const DIR_COLORS: Record<string, string> = { in: 'bg-emerald-100 text-emerald-700', out: 'bg-red-100 text-red-700', internal: 'bg-indigo-100 text-indigo-700', neutral: 'bg-slate-100 text-slate-600' }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <p className="text-sm text-slate-500">Tipos de movimiento de inventario</p>
        <button onClick={openCreate} className="flex items-center gap-1.5 rounded-xl bg-emerald-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-emerald-700">
          <Plus className="h-3.5 w-3.5" /> Nuevo tipo
        </button>
      </div>
      {showForm && (
        <form onSubmit={submit} className="rounded-xl border border-emerald-200 bg-emerald-50 p-4 space-y-3">
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <div>
              <label className="text-xs font-medium text-slate-600 mb-1 block">Nombre *</label>
              <input required value={form.name} onChange={e => setForm(f => ({ ...f, name: e.target.value }))}
                className="w-full rounded-lg border border-slate-200 px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-400" />
            </div>
            <div>
              <label className="text-xs font-medium text-slate-600 mb-1 block">Dirección</label>
              <select value={form.direction} onChange={e => setForm(f => ({ ...f, direction: e.target.value }))}
                className="w-full rounded-lg border border-slate-200 px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-400">
                {DIRECTIONS.map(d => <option key={d.value} value={d.value}>{d.label}</option>)}
              </select>
            </div>
            <div>
              <label className="text-xs font-medium text-slate-600 mb-1 block">Color</label>
              <input type="color" value={form.color} onChange={e => setForm(f => ({ ...f, color: e.target.value }))}
                className="h-9 w-full rounded-lg border border-slate-200 cursor-pointer" />
            </div>
          </div>
          <div>
            <label className="text-xs font-medium text-slate-600 mb-1 block">Descripción</label>
            <input value={form.description} onChange={e => setForm(f => ({ ...f, description: e.target.value }))}
              className="w-full rounded-lg border border-slate-200 px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-400" />
          </div>
          <div className="flex gap-4">
            <label className="flex items-center gap-1.5 text-xs cursor-pointer">
              <input type="checkbox" checked={form.affects_cost} onChange={e => setForm(f => ({ ...f, affects_cost: e.target.checked }))} className="rounded" />
              <span className="font-medium text-slate-600">Afecta costo</span>
            </label>
            <label className="flex items-center gap-1.5 text-xs cursor-pointer">
              <input type="checkbox" checked={form.requires_reference} onChange={e => setForm(f => ({ ...f, requires_reference: e.target.checked }))} className="rounded" />
              <span className="font-medium text-slate-600">Requiere referencia</span>
            </label>
          </div>
          <div className="flex justify-end gap-2">
            <button type="button" onClick={() => setShowForm(false)} className="rounded-lg px-3 py-1.5 text-xs text-slate-600 hover:bg-slate-100"><X className="h-3.5 w-3.5" /></button>
            <button type="submit" disabled={create.isPending || update.isPending} className="rounded-lg bg-emerald-600 px-4 py-1.5 text-xs font-semibold text-white hover:bg-emerald-700 disabled:opacity-50">
              {editing ? 'Guardar' : 'Crear'}
            </button>
          </div>
        </form>
      )}
      {isLoading ? <div className="text-sm text-slate-400 py-4">Cargando...</div>
        : types.length === 0 ? <div className="rounded-xl border border-dashed border-slate-200 p-8 text-center text-sm text-slate-400">Sin tipos de movimiento.</div>
        : (
          <div className="space-y-2">
            {types.map(t => (
              <div key={t.id} className="flex items-center gap-3 rounded-xl bg-white border border-slate-100 px-4 py-3 shadow-sm">
                <TypeBadge color={t.color} name={t.name} />
                <span className={cn('rounded-full px-2 py-0.5 text-[10px] font-medium', DIR_COLORS[t.direction] ?? 'bg-slate-100')}>
                  {DIRECTIONS.find(d => d.value === t.direction)?.label ?? t.direction}
                </span>
                {t.is_system && <span className="rounded-full bg-slate-200 text-slate-500 px-2 py-0.5 text-[10px] font-medium">Sistema</span>}
                <div className="flex-1" />
                {!t.is_system && (
                  <>
                    <button onClick={() => openEdit(t)} className="text-slate-400 hover:text-emerald-600"><Pencil className="h-3.5 w-3.5" /></button>
                    <button onClick={async () => { if (await confirm({ message: `¿Eliminar "${t.name}"?`, confirmLabel: 'Eliminar' })) del.mutate(t.id) }} disabled={del.isPending} className="text-slate-400 hover:text-red-500"><Trash2 className="h-3.5 w-3.5" /></button>
                  </>
                )}
              </div>
            ))}
          </div>
        )}
    </div>
  )
}

// ─── Warehouse Types ─────────────────────────────────────────────────────────

function WarehouseTypesTab() {
  const { data: types = [], isLoading } = useWarehouseTypes()
  const create = useCreateWarehouseType()
  const update = useUpdateWarehouseType()
  const del = useDeleteWarehouseType()
  const confirm = useConfirm()
  const [showForm, setShowForm] = useState(false)
  const [editing, setEditing] = useState<DynamicWarehouseType | null>(null)
  const [form, setForm] = useState({ name: '', description: '', color: '#8b5cf6' })

  function openCreate() { setEditing(null); setForm({ name: '', description: '', color: '#8b5cf6' }); setShowForm(true) }
  function openEdit(t: DynamicWarehouseType) { setEditing(t); setForm({ name: t.name, description: t.description ?? '', color: t.color ?? '#8b5cf6' }); setShowForm(true) }

  async function submit(e: React.FormEvent) {
    e.preventDefault()
    if (editing) await update.mutateAsync({ id: editing.id, data: form })
    else await create.mutateAsync(form)
    setShowForm(false)
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <p className="text-sm text-slate-500">Tipos de bodega para clasificar tus almacenes</p>
        <button onClick={openCreate} className="flex items-center gap-1.5 rounded-xl bg-violet-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-violet-700">
          <Plus className="h-3.5 w-3.5" /> Nuevo tipo
        </button>
      </div>
      {showForm && (
        <form onSubmit={submit} className="rounded-xl border border-violet-200 bg-violet-50 p-4 space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs font-medium text-slate-600 mb-1 block">Nombre *</label>
              <input required value={form.name} onChange={e => setForm(f => ({ ...f, name: e.target.value }))}
                className="w-full rounded-lg border border-slate-200 px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-violet-400" />
            </div>
            <div>
              <label className="text-xs font-medium text-slate-600 mb-1 block">Color</label>
              <input type="color" value={form.color} onChange={e => setForm(f => ({ ...f, color: e.target.value }))}
                className="h-9 w-full rounded-lg border border-slate-200 cursor-pointer" />
            </div>
          </div>
          <div>
            <label className="text-xs font-medium text-slate-600 mb-1 block">Descripción</label>
            <input value={form.description} onChange={e => setForm(f => ({ ...f, description: e.target.value }))}
              className="w-full rounded-lg border border-slate-200 px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-violet-400" />
          </div>
          <div className="flex justify-end gap-2">
            <button type="button" onClick={() => setShowForm(false)} className="rounded-lg px-3 py-1.5 text-xs text-slate-600 hover:bg-slate-100"><X className="h-3.5 w-3.5" /></button>
            <button type="submit" disabled={create.isPending || update.isPending} className="rounded-lg bg-violet-600 px-4 py-1.5 text-xs font-semibold text-white hover:bg-violet-700 disabled:opacity-50">
              {editing ? 'Guardar' : 'Crear'}
            </button>
          </div>
        </form>
      )}
      {isLoading ? <div className="text-sm text-slate-400 py-4">Cargando...</div>
        : types.length === 0 ? <div className="rounded-xl border border-dashed border-slate-200 p-8 text-center text-sm text-slate-400">Sin tipos de bodega.</div>
        : (
          <div className="flex flex-wrap gap-2">
            {types.map(t => (
              <div key={t.id} className="flex items-center gap-2 rounded-xl bg-white border border-slate-100 px-3 py-2 shadow-sm">
                <TypeBadge color={t.color} name={t.name} />
                {t.is_system && <span className="rounded-full bg-slate-200 text-slate-500 px-2 py-0.5 text-[10px] font-medium">Sistema</span>}
                {!t.is_system && (
                  <>
                    <button onClick={() => openEdit(t)} className="text-slate-400 hover:text-violet-600"><Pencil className="h-3.5 w-3.5" /></button>
                    <button onClick={async () => { if (await confirm({ message: `¿Eliminar "${t.name}"?`, confirmLabel: 'Eliminar' })) del.mutate(t.id) }} disabled={del.isPending} className="text-slate-400 hover:text-red-500"><Trash2 className="h-3.5 w-3.5" /></button>
                  </>
                )}
              </div>
            ))}
          </div>
        )}
    </div>
  )
}

// ─── Event Types ─────────────────────────────────────────────────────────────

function EventTypesTab() {
  const { data: types = [], isLoading } = useEventTypes()
  const { data: movementTypes = [] } = useMovementTypes()
  const create = useCreateEventType()
  const update = useUpdateEventType()
  const del = useDeleteEventType()
  const confirm = useConfirm()
  const [showForm, setShowForm] = useState(false)
  const [editing, setEditing] = useState<EventType | null>(null)
  const [form, setForm] = useState({ name: '', description: '', color: '#ef4444', auto_generate_movement_type_id: '' })

  function openCreate() { setEditing(null); setForm({ name: '', description: '', color: '#ef4444', auto_generate_movement_type_id: '' }); setShowForm(true) }
  function openEdit(t: EventType) {
    setEditing(t)
    setForm({ name: t.name, description: t.description ?? '', color: t.color ?? '#ef4444', auto_generate_movement_type_id: t.auto_generate_movement_type_id ?? '' })
    setShowForm(true)
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault()
    const payload = { ...form, auto_generate_movement_type_id: form.auto_generate_movement_type_id || null }
    if (editing) await update.mutateAsync({ id: editing.id, data: payload })
    else await create.mutateAsync(payload)
    setShowForm(false)
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <p className="text-sm text-slate-500">Tipos de evento de inventario</p>
        <button onClick={openCreate} className="flex items-center gap-1.5 rounded-xl bg-red-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-red-700">
          <Plus className="h-3.5 w-3.5" /> Nuevo tipo
        </button>
      </div>
      {showForm && (
        <form onSubmit={submit} className="rounded-xl border border-red-200 bg-red-50 p-4 space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs font-medium text-slate-600 mb-1 block">Nombre *</label>
              <input required value={form.name} onChange={e => setForm(f => ({ ...f, name: e.target.value }))}
                className="w-full rounded-lg border border-slate-200 px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-red-400" />
            </div>
            <div>
              <label className="text-xs font-medium text-slate-600 mb-1 block">Color</label>
              <input type="color" value={form.color} onChange={e => setForm(f => ({ ...f, color: e.target.value }))}
                className="h-9 w-full rounded-lg border border-slate-200 cursor-pointer" />
            </div>
          </div>
          <div>
            <label className="text-xs font-medium text-slate-600 mb-1 block">Descripción</label>
            <input value={form.description} onChange={e => setForm(f => ({ ...f, description: e.target.value }))}
              className="w-full rounded-lg border border-slate-200 px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-red-400" />
          </div>
          <div>
            <label className="text-xs font-medium text-slate-600 mb-1 block">Auto-generar movimiento</label>
            <select value={form.auto_generate_movement_type_id} onChange={e => setForm(f => ({ ...f, auto_generate_movement_type_id: e.target.value }))}
              className="w-full rounded-lg border border-slate-200 px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-red-400">
              <option value="">Ninguno</option>
              {movementTypes.map(mt => <option key={mt.id} value={mt.id}>{mt.name}</option>)}
            </select>
          </div>
          <div className="flex justify-end gap-2">
            <button type="button" onClick={() => setShowForm(false)} className="rounded-lg px-3 py-1.5 text-xs text-slate-600 hover:bg-slate-100"><X className="h-3.5 w-3.5" /></button>
            <button type="submit" disabled={create.isPending || update.isPending} className="rounded-lg bg-red-600 px-4 py-1.5 text-xs font-semibold text-white hover:bg-red-700 disabled:opacity-50">
              {editing ? 'Guardar' : 'Crear'}
            </button>
          </div>
        </form>
      )}
      {isLoading ? <div className="text-sm text-slate-400 py-4">Cargando...</div>
        : types.length === 0 ? <div className="rounded-xl border border-dashed border-slate-200 p-8 text-center text-sm text-slate-400">Sin tipos de evento.</div>
        : (
          <div className="flex flex-wrap gap-2">
            {types.map(t => (
              <div key={t.id} className="flex items-center gap-2 rounded-xl bg-white border border-slate-100 px-3 py-2 shadow-sm">
                <TypeBadge color={t.color} name={t.name} />
                <button onClick={() => openEdit(t)} className="text-slate-400 hover:text-red-600"><Pencil className="h-3.5 w-3.5" /></button>
                <button onClick={async () => { if (await confirm({ message: `¿Eliminar "${t.name}"?`, confirmLabel: 'Eliminar' })) del.mutate(t.id) }} disabled={del.isPending} className="text-slate-400 hover:text-red-500"><Trash2 className="h-3.5 w-3.5" /></button>
              </div>
            ))}
          </div>
        )}
    </div>
  )
}

// ─── Severities ──────────────────────────────────────────────────────────────

function SeveritiesTab() {
  const { data: items = [], isLoading } = useEventSeverities()
  const create = useCreateEventSeverity()
  const update = useUpdateEventSeverity()
  const del = useDeleteEventSeverity()
  const confirm = useConfirm()
  const [showForm, setShowForm] = useState(false)
  const [editing, setEditing] = useState<EventSeverity | null>(null)
  const [form, setForm] = useState({ name: '', color: '#f59e0b', weight: 1 })

  function openCreate() { setEditing(null); setForm({ name: '', color: '#f59e0b', weight: 1 }); setShowForm(true) }
  function openEdit(t: EventSeverity) { setEditing(t); setForm({ name: t.name, color: t.color ?? '#f59e0b', weight: t.weight }); setShowForm(true) }

  async function submit(e: React.FormEvent) {
    e.preventDefault()
    if (editing) await update.mutateAsync({ id: editing.id, data: form })
    else await create.mutateAsync(form)
    setShowForm(false)
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <p className="text-sm text-slate-500">Niveles de severidad para eventos</p>
        <button onClick={openCreate} className="flex items-center gap-1.5 rounded-xl bg-amber-500 px-3 py-1.5 text-xs font-semibold text-white hover:bg-amber-600">
          <Plus className="h-3.5 w-3.5" /> Nueva severidad
        </button>
      </div>
      {showForm && (
        <form onSubmit={submit} className="rounded-xl border border-amber-200 bg-amber-50 p-4 space-y-3">
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <div>
              <label className="text-xs font-medium text-slate-600 mb-1 block">Nombre *</label>
              <input required value={form.name} onChange={e => setForm(f => ({ ...f, name: e.target.value }))}
                className="w-full rounded-lg border border-slate-200 px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-amber-400" />
            </div>
            <div>
              <label className="text-xs font-medium text-slate-600 mb-1 block">Peso</label>
              <input type="number" min="1" value={form.weight} onChange={e => setForm(f => ({ ...f, weight: Number(e.target.value) }))}
                className="w-full rounded-lg border border-slate-200 px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-amber-400" />
            </div>
            <div>
              <label className="text-xs font-medium text-slate-600 mb-1 block">Color</label>
              <input type="color" value={form.color} onChange={e => setForm(f => ({ ...f, color: e.target.value }))}
                className="h-9 w-full rounded-lg border border-slate-200 cursor-pointer" />
            </div>
          </div>
          <div className="flex justify-end gap-2">
            <button type="button" onClick={() => setShowForm(false)} className="rounded-lg px-3 py-1.5 text-xs text-slate-600 hover:bg-slate-100"><X className="h-3.5 w-3.5" /></button>
            <button type="submit" disabled={create.isPending || update.isPending} className="rounded-lg bg-amber-500 px-4 py-1.5 text-xs font-semibold text-white hover:bg-amber-600 disabled:opacity-50">
              {editing ? 'Guardar' : 'Crear'}
            </button>
          </div>
        </form>
      )}
      {isLoading ? <div className="text-sm text-slate-400 py-4">Cargando...</div>
        : items.length === 0 ? <div className="rounded-xl border border-dashed border-slate-200 p-8 text-center text-sm text-slate-400">Sin severidades.</div>
        : (
          <div className="flex flex-wrap gap-2">
            {items.map(t => (
              <div key={t.id} className="flex items-center gap-2 rounded-xl bg-white border border-slate-100 px-3 py-2 shadow-sm">
                <TypeBadge color={t.color} name={t.name} />
                <span className="text-[10px] text-slate-400">peso: {t.weight}</span>
                <button onClick={() => openEdit(t)} className="text-slate-400 hover:text-amber-600"><Pencil className="h-3.5 w-3.5" /></button>
                <button onClick={async () => { if (await confirm({ message: `¿Eliminar "${t.name}"?`, confirmLabel: 'Eliminar' })) del.mutate(t.id) }} disabled={del.isPending} className="text-slate-400 hover:text-red-500"><Trash2 className="h-3.5 w-3.5" /></button>
              </div>
            ))}
          </div>
        )}
    </div>
  )
}

// ─── Event Statuses ──────────────────────────────────────────────────────────

function EventStatusesTab() {
  const { data: items = [], isLoading } = useEventStatuses()
  const create = useCreateEventStatus()
  const update = useUpdateEventStatus()
  const del = useDeleteEventStatus()
  const confirm = useConfirm()
  const [showForm, setShowForm] = useState(false)
  const [editing, setEditing] = useState<EventStatus | null>(null)
  const [form, setForm] = useState({ name: '', color: '#6366f1', is_final: false, sort_order: 0 })

  function openCreate() { setEditing(null); setForm({ name: '', color: '#6366f1', is_final: false, sort_order: 0 }); setShowForm(true) }
  function openEdit(t: EventStatus) { setEditing(t); setForm({ name: t.name, color: t.color ?? '#6366f1', is_final: t.is_final, sort_order: t.sort_order }); setShowForm(true) }

  async function submit(e: React.FormEvent) {
    e.preventDefault()
    if (editing) await update.mutateAsync({ id: editing.id, data: form })
    else await create.mutateAsync(form)
    setShowForm(false)
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <p className="text-sm text-slate-500">Estados para el flujo de eventos</p>
        <button onClick={openCreate} className="flex items-center gap-1.5 rounded-xl bg-indigo-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-indigo-700">
          <Plus className="h-3.5 w-3.5" /> Nuevo estado
        </button>
      </div>
      {showForm && (
        <form onSubmit={submit} className="rounded-xl border border-indigo-200 bg-indigo-50 p-4 space-y-3">
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <div>
              <label className="text-xs font-medium text-slate-600 mb-1 block">Nombre *</label>
              <input required value={form.name} onChange={e => setForm(f => ({ ...f, name: e.target.value }))}
                className="w-full rounded-lg border border-slate-200 px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400" />
            </div>
            <div>
              <label className="text-xs font-medium text-slate-600 mb-1 block">Orden</label>
              <input type="number" value={form.sort_order} onChange={e => setForm(f => ({ ...f, sort_order: Number(e.target.value) }))}
                className="w-full rounded-lg border border-slate-200 px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400" />
            </div>
            <div>
              <label className="text-xs font-medium text-slate-600 mb-1 block">Color</label>
              <input type="color" value={form.color} onChange={e => setForm(f => ({ ...f, color: e.target.value }))}
                className="h-9 w-full rounded-lg border border-slate-200 cursor-pointer" />
            </div>
          </div>
          <label className="flex items-center gap-1.5 text-xs cursor-pointer">
            <input type="checkbox" checked={form.is_final} onChange={e => setForm(f => ({ ...f, is_final: e.target.checked }))} className="rounded" />
            <span className="font-medium text-slate-600">Estado final (cierra el evento)</span>
          </label>
          <div className="flex justify-end gap-2">
            <button type="button" onClick={() => setShowForm(false)} className="rounded-lg px-3 py-1.5 text-xs text-slate-600 hover:bg-slate-100"><X className="h-3.5 w-3.5" /></button>
            <button type="submit" disabled={create.isPending || update.isPending} className="rounded-lg bg-indigo-600 px-4 py-1.5 text-xs font-semibold text-white hover:bg-indigo-700 disabled:opacity-50">
              {editing ? 'Guardar' : 'Crear'}
            </button>
          </div>
        </form>
      )}
      {isLoading ? <div className="text-sm text-slate-400 py-4">Cargando...</div>
        : items.length === 0 ? <div className="rounded-xl border border-dashed border-slate-200 p-8 text-center text-sm text-slate-400">Sin estados de evento.</div>
        : (
          <div className="flex flex-wrap gap-2">
            {items.map(t => (
              <div key={t.id} className="flex items-center gap-2 rounded-xl bg-white border border-slate-100 px-3 py-2 shadow-sm">
                <TypeBadge color={t.color} name={t.name} />
                {t.is_final && <span className="rounded-full bg-slate-200 text-slate-500 px-2 py-0.5 text-[10px] font-medium">Final</span>}
                <button onClick={() => openEdit(t)} className="text-slate-400 hover:text-indigo-600"><Pencil className="h-3.5 w-3.5" /></button>
                <button onClick={async () => { if (await confirm({ message: `¿Eliminar "${t.name}"?`, confirmLabel: 'Eliminar' })) del.mutate(t.id) }} disabled={del.isPending} className="text-slate-400 hover:text-red-500"><Trash2 className="h-3.5 w-3.5" /></button>
              </div>
            ))}
          </div>
        )}
    </div>
  )
}

// ─── Serial Statuses ─────────────────────────────────────────────────────────

function SerialStatusesTab() {
  const { data: items = [], isLoading } = useSerialStatuses()
  const create = useCreateSerialStatus()
  const update = useUpdateSerialStatus()
  const del = useDeleteSerialStatus()
  const confirm = useConfirm()
  const [showForm, setShowForm] = useState(false)
  const [editing, setEditing] = useState<SerialStatus | null>(null)
  const [form, setForm] = useState({ name: '', description: '', color: '#06b6d4' })

  function openCreate() { setEditing(null); setForm({ name: '', description: '', color: '#06b6d4' }); setShowForm(true) }
  function openEdit(t: SerialStatus) { setEditing(t); setForm({ name: t.name, description: t.description ?? '', color: t.color ?? '#06b6d4' }); setShowForm(true) }

  async function submit(e: React.FormEvent) {
    e.preventDefault()
    if (editing) await update.mutateAsync({ id: editing.id, data: form })
    else await create.mutateAsync(form)
    setShowForm(false)
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <p className="text-sm text-slate-500">Estados de seguimiento de seriales</p>
        <button onClick={openCreate} className="flex items-center gap-1.5 rounded-xl bg-cyan-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-cyan-700">
          <Plus className="h-3.5 w-3.5" /> Nuevo estado
        </button>
      </div>
      {showForm && (
        <form onSubmit={submit} className="rounded-xl border border-cyan-200 bg-cyan-50 p-4 space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs font-medium text-slate-600 mb-1 block">Nombre *</label>
              <input required value={form.name} onChange={e => setForm(f => ({ ...f, name: e.target.value }))}
                className="w-full rounded-lg border border-slate-200 px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-cyan-400" />
            </div>
            <div>
              <label className="text-xs font-medium text-slate-600 mb-1 block">Color</label>
              <input type="color" value={form.color} onChange={e => setForm(f => ({ ...f, color: e.target.value }))}
                className="h-9 w-full rounded-lg border border-slate-200 cursor-pointer" />
            </div>
          </div>
          <div>
            <label className="text-xs font-medium text-slate-600 mb-1 block">Descripción</label>
            <input value={form.description} onChange={e => setForm(f => ({ ...f, description: e.target.value }))}
              className="w-full rounded-lg border border-slate-200 px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-cyan-400" />
          </div>
          <div className="flex justify-end gap-2">
            <button type="button" onClick={() => setShowForm(false)} className="rounded-lg px-3 py-1.5 text-xs text-slate-600 hover:bg-slate-100"><X className="h-3.5 w-3.5" /></button>
            <button type="submit" disabled={create.isPending || update.isPending} className="rounded-lg bg-cyan-600 px-4 py-1.5 text-xs font-semibold text-white hover:bg-cyan-700 disabled:opacity-50">
              {editing ? 'Guardar' : 'Crear'}
            </button>
          </div>
        </form>
      )}
      {isLoading ? <div className="text-sm text-slate-400 py-4">Cargando...</div>
        : items.length === 0 ? <div className="rounded-xl border border-dashed border-slate-200 p-8 text-center text-sm text-slate-400">Sin estados de serial.</div>
        : (
          <div className="flex flex-wrap gap-2">
            {items.map(t => (
              <div key={t.id} className="flex items-center gap-2 rounded-xl bg-white border border-slate-100 px-3 py-2 shadow-sm">
                <TypeBadge color={t.color} name={t.name} />
                <button onClick={() => openEdit(t)} className="text-slate-400 hover:text-cyan-600"><Pencil className="h-3.5 w-3.5" /></button>
                <button onClick={async () => { if (await confirm({ message: `¿Eliminar "${t.name}"?`, confirmLabel: 'Eliminar' })) del.mutate(t.id) }} disabled={del.isPending} className="text-slate-400 hover:text-red-500"><Trash2 className="h-3.5 w-3.5" /></button>
              </div>
            ))}
          </div>
        )}
    </div>
  )
}

// ─── Customer Types ──────────────────────────────────────────────────────────

function CustomerTypesTab() {
  const { data: types = [], isLoading } = useCustomerTypes()
  const create = useCreateCustomerType()
  const update = useUpdateCustomerType()
  const del = useDeleteCustomerType()
  const confirm = useConfirm()
  const [showForm, setShowForm] = useState(false)
  const [editing, setEditing] = useState<CustomerType | null>(null)
  const [form, setForm] = useState({ name: '', description: '', color: '#0ea5e9' })

  function openCreate() {
    setEditing(null)
    setForm({ name: '', description: '', color: '#0ea5e9' })
    setShowForm(true)
  }

  function openEdit(t: CustomerType) {
    setEditing(t)
    setForm({ name: t.name, description: t.description ?? '', color: t.color ?? '#0ea5e9' })
    setShowForm(true)
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault()
    if (editing) {
      await update.mutateAsync({ id: editing.id, data: form })
    } else {
      await create.mutateAsync(form)
    }
    setShowForm(false)
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <p className="text-sm text-slate-500">Tipos de cliente para clasificar tus compradores</p>
        <button
          onClick={openCreate}
          className="flex items-center gap-1.5 rounded-xl bg-sky-500 px-3 py-1.5 text-xs font-semibold text-white hover:bg-sky-600"
        >
          <Plus className="h-3.5 w-3.5" /> Nuevo tipo
        </button>
      </div>

      {showForm && (
        <form onSubmit={submit} className="rounded-xl border border-sky-200 bg-sky-50 p-4 space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs font-medium text-slate-600 mb-1 block">Nombre *</label>
              <input required value={form.name} onChange={e => setForm(f => ({ ...f, name: e.target.value }))}
                className="w-full rounded-lg border border-slate-200 px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-sky-400" />
            </div>
            <div>
              <label className="text-xs font-medium text-slate-600 mb-1 block">Color</label>
              <input type="color" value={form.color} onChange={e => setForm(f => ({ ...f, color: e.target.value }))}
                className="h-9 w-full rounded-lg border border-slate-200 cursor-pointer" />
            </div>
          </div>
          <div>
            <label className="text-xs font-medium text-slate-600 mb-1 block">Descripcion</label>
            <input value={form.description} onChange={e => setForm(f => ({ ...f, description: e.target.value }))}
              className="w-full rounded-lg border border-slate-200 px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-sky-400" />
          </div>
          <div className="flex justify-end gap-2">
            <button type="button" onClick={() => setShowForm(false)} className="rounded-lg px-3 py-1.5 text-xs text-slate-600 hover:bg-slate-100">
              <X className="h-3.5 w-3.5" />
            </button>
            <button type="submit" disabled={create.isPending || update.isPending}
              className="rounded-lg bg-sky-500 px-4 py-1.5 text-xs font-semibold text-white hover:bg-sky-600 disabled:opacity-50">
              {editing ? 'Guardar' : 'Crear'}
            </button>
          </div>
        </form>
      )}

      {isLoading ? (
        <div className="text-sm text-slate-400 py-4">Cargando...</div>
      ) : types.length === 0 ? (
        <div className="rounded-xl border border-dashed border-slate-200 p-8 text-center text-sm text-slate-400">
          Sin tipos de cliente. Crea el primero.
        </div>
      ) : (
        <div className="flex flex-wrap gap-2">
          {types.map(t => (
            <div key={t.id} className="flex items-center gap-2 rounded-xl bg-white border border-slate-100 px-3 py-2 shadow-sm">
              <TypeBadge color={t.color} name={t.name} />
              <button onClick={() => openEdit(t)} className="text-slate-400 hover:text-sky-600">
                <Pencil className="h-3.5 w-3.5" />
              </button>
              <button onClick={async () => { if (await confirm({ message: `¿Eliminar "${t.name}"?`, confirmLabel: 'Eliminar' })) del.mutate(t.id) }} disabled={del.isPending} className="text-slate-400 hover:text-red-500">
                <Trash2 className="h-3.5 w-3.5" />
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

// ─── Approval Threshold ─────────────────────────────────────────────────────

function ApprovalThresholdTab() {
  const { data, isLoading } = useApprovalThreshold()
  const updateThreshold = useUpdateApprovalThreshold()
  const [value, setValue] = useState('')
  const [noThreshold, setNoThreshold] = useState(false)

  useEffect(() => {
    if (data !== undefined && data !== null) {
      if (data.so_approval_threshold === null || data.so_approval_threshold === undefined) {
        setNoThreshold(true)
        setValue('')
      } else {
        setNoThreshold(false)
        setValue(String(data.so_approval_threshold))
      }
    }
  }, [data])

  if (isLoading) return <div className="flex justify-center py-10"><div className="animate-spin rounded-full h-5 w-5 border-b-2 border-indigo-600" /></div>

  return (
    <div className="space-y-4">
      <div>
        <h3 className="font-semibold text-slate-900">Umbral de Aprobacion de Ordenes de Venta</h3>
        <p className="text-sm text-slate-500 mt-1">Las ordenes de venta que superen este monto requeriran aprobacion.</p>
      </div>
      <div className="bg-white rounded-2xl border border-slate-200/60 shadow-sm p-5 space-y-4 max-w-md">
        <label className="flex items-center gap-2 text-sm text-slate-700">
          <input type="checkbox" checked={noThreshold}
            onChange={e => setNoThreshold(e.target.checked)}
            className="rounded border-slate-300" />
          Sin umbral (nunca requiere aprobacion)
        </label>
        {!noThreshold && (
          <div>
            <label className="text-xs text-slate-500 mb-1 block">Monto minimo para requerir aprobacion ($)</label>
            <input type="number" step="0.01" min="0" value={value}
              onChange={e => setValue(e.target.value)}
              placeholder="Ej: 5000"
              className="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400" />
          </div>
        )}
        <button
          onClick={async () => {
            await updateThreshold.mutateAsync(noThreshold ? null : Number(value))
          }}
          disabled={updateThreshold.isPending}
          className="rounded-xl bg-indigo-600 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-700 disabled:opacity-60">
          {updateThreshold.isPending ? 'Guardando...' : 'Guardar'}
        </button>
      </div>
    </div>
  )
}

// ─── Main Page ────────────────────────────────────────────────────────────────

// ─── Config Tabs ─────────────────────────────────────────────────────────────

export const CONFIG_SECTIONS = [
  { id: 'tipos-producto', label: 'Tipos de producto', description: 'Clasifica tu catálogo de productos', icon: Tag },
  { id: 'tipos-orden', label: 'Tipos de orden', description: 'Tipos de orden de compra', icon: ShoppingBag },
  { id: 'tipos-proveedor', label: 'Tipos de proveedor', description: 'Clasificación de proveedores', icon: Truck },
  { id: 'tipos-movimiento', label: 'Tipos de movimiento', description: 'Tipos de movimiento de inventario', icon: ArrowLeftRight },
  { id: 'tipos-bodega', label: 'Tipos de bodega', description: 'Clasificación de almacenes', icon: Warehouse },
  { id: 'tipos-evento', label: 'Tipos de evento', description: 'Tipos de eventos de inventario', icon: AlertTriangle },
  { id: 'severidades', label: 'Severidades', description: 'Niveles de severidad para eventos', icon: Gauge },
  { id: 'estados-evento', label: 'Estados de evento', description: 'Estados del ciclo de vida de eventos', icon: CheckCircle2 },
  { id: 'estados-serial', label: 'Estados de serial', description: 'Estados de números de serie', icon: Hash },
  { id: 'customer-types', label: 'Tipos de Cliente', description: 'Clasificación de clientes', icon: Users },
  { id: 'approval-threshold', label: 'Umbral de Aprobación', description: 'Configurar umbral para aprobación de OV', icon: ShieldCheck },
] as const

export type ConfigSectionId = typeof CONFIG_SECTIONS[number]['id']

export const CONFIG_SECTION_COMPONENTS: Record<ConfigSectionId, React.ReactNode> = {
  'tipos-producto': <ProductTypesTab />,
  'tipos-orden': <OrderTypesTab />,
  'tipos-proveedor': <SupplierTypesTab />,
  'tipos-movimiento': <MovementTypesTab />,
  'tipos-bodega': <WarehouseTypesTab />,
  'tipos-evento': <EventTypesTab />,
  'severidades': <SeveritiesTab />,
  'estados-evento': <EventStatusesTab />,
  'estados-serial': <SerialStatusesTab />,
  'customer-types': <CustomerTypesTab />,
  'approval-threshold': <ApprovalThresholdTab />,
}

export function InventoryConfigPage() {
  return (
    <div className="p-8 space-y-8 max-w-5xl mx-auto">
      {/* Header */}
      <div className="flex items-center gap-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-slate-100">
          <Settings2 className="h-5 w-5 text-slate-600" />
        </div>
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Configuración</h1>
          <p className="text-sm text-slate-500">Tipos y parámetros del módulo de inventario</p>
        </div>
      </div>

      {/* ─── Config sections directory ────────────────────────────────── */}
      <div className="space-y-3">
        <h2 className="text-sm font-bold text-slate-500 uppercase tracking-wide">Configuraciones</h2>

        <div className="bg-white rounded-2xl border border-slate-100 shadow-sm divide-y divide-slate-100 overflow-hidden">
          {CONFIG_SECTIONS.map(item => (
            <Link
              key={item.id}
              to={`/inventario/configuracion/${item.id}`}
              className="flex items-center gap-3 px-5 py-4 hover:bg-slate-50/50 transition-colors group"
            >
              <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-slate-100 shrink-0">
                <item.icon className="h-4 w-4 text-slate-500" />
              </div>
              <div className="flex-1 min-w-0">
                <span className="text-sm font-semibold text-slate-900">{item.label}</span>
                <p className="text-xs text-slate-400 mt-0.5">{item.description}</p>
              </div>
              <ChevronRight className="h-4 w-4 text-slate-300 group-hover:text-indigo-400 transition-colors" />
            </Link>
          ))}
        </div>
      </div>
    </div>
  )
}
