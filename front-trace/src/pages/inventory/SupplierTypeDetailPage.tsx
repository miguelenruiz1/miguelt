import { useState } from 'react'
import { Link, useParams, Navigate } from 'react-router-dom'
import {
  ChevronRight, Truck, Info, Database, Plus, Pencil, Trash2, X, ImageIcon,
} from 'lucide-react'
import {
  useSupplierTypes, useUpdateSupplierType,
  useSupplierFields, useCreateSupplierField, useUpdateSupplierField, useDeleteSupplierField,
} from '@/hooks/useInventory'
import { useConfirm } from '@/store/confirm'
import { cn } from '@/lib/utils'
import type { CustomSupplierField, FieldType } from '@/types/inventory'

const FIELD_TYPES: { value: FieldType; label: string }[] = [
  { value: 'text', label: 'Texto' },
  { value: 'number', label: 'Número' },
  { value: 'select', label: 'Selección' },
  { value: 'boolean', label: 'Sí/No' },
  { value: 'date', label: 'Fecha' },
]

const FIELD_COLORS: Record<string, string> = {
  text: 'bg-blue-100 text-blue-700',
  number: 'bg-purple-100 text-purple-700',
  select: 'bg-amber-100 text-amber-700',
  boolean: 'bg-emerald-100 text-emerald-700',
  date: 'bg-rose-100 text-rose-700',
}

// ─── Tab: Información ────────────────────────────────────────────────────────

function InfoTab({ supplierType }: { supplierType: { id: string; name: string; slug: string; description: string | null; color: string | null } }) {
  const update = useUpdateSupplierType()
  const [form, setForm] = useState({
    name: supplierType.name,
    description: supplierType.description ?? '',
    color: supplierType.color ?? '#f59e0b',
  })
  const [saved, setSaved] = useState(false)

  async function submit(e: React.FormEvent) {
    e.preventDefault()
    await update.mutateAsync({ id: supplierType.id, data: form })
    setSaved(true)
    setTimeout(() => setSaved(false), 2000)
  }

  return (
    <form onSubmit={submit} className="space-y-6 max-w-xl">
      <div className="space-y-4">
        <div className="grid grid-cols-[1fr_80px] gap-4">
          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1.5">Nombre *</label>
            <input required value={form.name}
              onChange={e => setForm(f => ({ ...f, name: e.target.value }))}
              className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring" />
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1.5">Color</label>
            <input type="color" value={form.color}
              onChange={e => setForm(f => ({ ...f, color: e.target.value }))}
              className="h-[38px] w-full rounded-lg border border-slate-200 cursor-pointer" />
          </div>
        </div>

        <div>
          <label className="block text-xs font-medium text-slate-600 mb-1.5">Descripción</label>
          <textarea value={form.description}
            onChange={e => setForm(f => ({ ...f, description: e.target.value }))}
            rows={3} placeholder="Describe este tipo de proveedor..."
            className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring resize-none" />
        </div>

        <div>
          <label className="block text-xs font-medium text-slate-600 mb-1.5">Imagen</label>
          <div className="rounded-xl border-2 border-dashed border-slate-200 p-8 text-center hover:border-primary/50 transition-colors cursor-pointer">
            <ImageIcon className="h-8 w-8 text-slate-300 mx-auto mb-2" />
            <p className="text-xs text-slate-400">Arrastra una imagen o haz clic para subir</p>
            <p className="text-[10px] text-slate-300 mt-1">PNG, JPG hasta 2MB</p>
          </div>
        </div>

        <div className="rounded-lg bg-slate-50 px-4 py-3">
          <label className="block text-xs font-medium text-slate-500 mb-0.5">Slug</label>
          <code className="text-sm font-mono text-slate-700">{supplierType.slug}</code>
        </div>
      </div>

      <div className="flex items-center gap-3">
        <button type="submit" disabled={update.isPending}
          className="rounded-lg bg-primary px-5 py-2 text-sm font-semibold text-white hover:bg-primary/90 disabled:opacity-50 transition-colors">
          {update.isPending ? 'Guardando...' : 'Guardar cambios'}
        </button>
        {saved && <span className="text-xs font-medium text-emerald-600">Guardado</span>}
      </div>
    </form>
  )
}

// ─── Tab: Campos personalizados ──────────────────────────────────────────────

function FieldsTab({ supplierTypeId }: { supplierTypeId: string }) {
  const { data: fields = [], isLoading } = useSupplierFields(supplierTypeId)
  const create = useCreateSupplierField()
  const update = useUpdateSupplierField()
  const del = useDeleteSupplierField()
  const confirm = useConfirm()

  const [showForm, setShowForm] = useState(false)
  const [editing, setEditing] = useState<CustomSupplierField | null>(null)
  const [form, setForm] = useState({
    label: '', field_key: '', field_type: 'text' as FieldType,
    options: '', required: false, sort_order: 0,
  })

  function openCreate() {
    setEditing(null)
    setForm({ label: '', field_key: '', field_type: 'text', options: '', required: false, sort_order: 0 })
    setShowForm(true)
  }

  function openEdit(f: CustomSupplierField) {
    setEditing(f)
    setForm({
      label: f.label, field_key: f.field_key, field_type: f.field_type as FieldType,
      options: f.options?.join(', ') ?? '', required: f.required, sort_order: f.sort_order,
    })
    setShowForm(true)
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault()
    const data: Partial<CustomSupplierField> = {
      label: form.label, field_key: form.field_key, field_type: form.field_type,
      required: form.required, sort_order: form.sort_order,
      supplier_type_id: supplierTypeId,
      options: form.field_type === 'select' && form.options
        ? form.options.split(',').map(s => s.trim()).filter(Boolean)
        : null,
    }
    if (editing) {
      await update.mutateAsync({ id: editing.id, data })
    } else {
      await create.mutateAsync(data)
    }
    setShowForm(false)
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <p className="text-sm text-slate-500">Campos exclusivos de este tipo de proveedor</p>
        <button onClick={openCreate}
          className="flex items-center gap-1.5 rounded-xl bg-primary px-3 py-1.5 text-xs font-semibold text-white hover:bg-primary/90 transition-colors">
          <Plus className="h-3.5 w-3.5" /> Nuevo campo
        </button>
      </div>

      {/* Create / Edit form */}
      {showForm && (
        <form onSubmit={submit} className="rounded-xl border border-primary/30 bg-primary/5 p-4 space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs font-medium text-slate-600 mb-1 block">Etiqueta *</label>
              <input required value={form.label} onChange={e => setForm(f => ({ ...f, label: e.target.value }))}
                className="w-full rounded-lg border border-slate-200 px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-ring" />
            </div>
            <div>
              <label className="text-xs font-medium text-slate-600 mb-1 block">Clave (key) *</label>
              <input required value={form.field_key}
                onChange={e => setForm(f => ({ ...f, field_key: e.target.value.toLowerCase().replace(/\s+/g, '_') }))}
                disabled={!!editing}
                className="w-full rounded-lg border border-slate-200 px-3 py-1.5 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-ring disabled:bg-slate-50 disabled:text-slate-400"
                placeholder="campo_personalizado" />
            </div>
          </div>
          <div className="grid grid-cols-3 gap-3">
            <div>
              <label className="text-xs font-medium text-slate-600 mb-1 block">Tipo</label>
              <select value={form.field_type} onChange={e => setForm(f => ({ ...f, field_type: e.target.value as FieldType }))}
                className="w-full rounded-lg border border-slate-200 px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-ring">
                {FIELD_TYPES.map(ft => <option key={ft.value} value={ft.value}>{ft.label}</option>)}
              </select>
            </div>
            <div>
              <label className="text-xs font-medium text-slate-600 mb-1 block">Orden</label>
              <input type="number" value={form.sort_order} onChange={e => setForm(f => ({ ...f, sort_order: Number(e.target.value) }))}
                className="w-full rounded-lg border border-slate-200 px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-ring" />
            </div>
            <div className="flex items-end pb-1.5">
              <label className="flex items-center gap-2 text-sm cursor-pointer">
                <input type="checkbox" checked={form.required} onChange={e => setForm(f => ({ ...f, required: e.target.checked }))}
                  className="rounded" />
                <span className="text-xs font-medium text-slate-600">Requerido</span>
              </label>
            </div>
          </div>
          {form.field_type === 'select' && (
            <div>
              <label className="text-xs font-medium text-slate-600 mb-1 block">Opciones (separadas por coma)</label>
              <input value={form.options} onChange={e => setForm(f => ({ ...f, options: e.target.value }))}
                placeholder="Opción 1, Opción 2, Opción 3"
                className="w-full rounded-lg border border-slate-200 px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-ring" />
            </div>
          )}
          <div className="flex justify-end gap-2">
            <button type="button" onClick={() => setShowForm(false)} className="rounded-lg px-3 py-1.5 text-xs text-slate-600 hover:bg-slate-100">
              <X className="h-3.5 w-3.5" />
            </button>
            <button type="submit" disabled={create.isPending || update.isPending}
              className="rounded-lg bg-primary px-4 py-1.5 text-xs font-semibold text-white hover:bg-primary/90 disabled:opacity-50">
              {editing ? 'Guardar' : 'Crear'}
            </button>
          </div>
        </form>
      )}

      {/* Fields table */}
      {isLoading ? (
        <div className="text-sm text-slate-400 py-6 text-center">Cargando...</div>
      ) : fields.length === 0 ? (
        <div className="rounded-xl border-2 border-dashed border-slate-200 p-10 text-center">
          <Database className="h-8 w-8 text-slate-200 mx-auto mb-3" />
          <p className="text-sm font-medium text-slate-600 mb-1">Sin campos personalizados</p>
          <p className="text-xs text-slate-400 mb-4">Crea campos exclusivos para este tipo de proveedor.</p>
          <button onClick={openCreate}
            className="inline-flex items-center gap-1.5 rounded-lg bg-primary px-4 py-2 text-xs font-semibold text-white hover:bg-primary/90">
            <Plus className="h-3.5 w-3.5" /> Nuevo campo
          </button>
        </div>
      ) : (
        <div className="bg-white rounded-xl border border-slate-100 overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-slate-50 border-b border-slate-100">
              <tr>
                <th className="px-5 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide">Etiqueta</th>
                <th className="px-5 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide">Key</th>
                <th className="px-5 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide">Tipo</th>
                <th className="px-5 py-3 text-center text-xs font-semibold text-slate-500 uppercase tracking-wide">Requerido</th>
                <th className="px-5 py-3 text-center text-xs font-semibold text-slate-500 uppercase tracking-wide">Orden</th>
                <th className="px-5 py-3 text-right text-xs font-semibold text-slate-500 uppercase tracking-wide">Acciones</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-50">
              {fields.map(f => (
                <tr key={f.id} className="hover:bg-slate-50/50 transition-colors">
                  <td className="px-5 py-3 font-medium text-slate-900">{f.label}</td>
                  <td className="px-5 py-3">
                    <code className="text-xs font-mono text-slate-500 bg-slate-50 px-1.5 py-0.5 rounded">{f.field_key}</code>
                  </td>
                  <td className="px-5 py-3">
                    <span className={cn('rounded-full px-2 py-0.5 text-[10px] font-medium', FIELD_COLORS[f.field_type] ?? 'bg-slate-100 text-slate-600')}>
                      {FIELD_TYPES.find(t => t.value === f.field_type)?.label ?? f.field_type}
                    </span>
                  </td>
                  <td className="px-5 py-3 text-center text-xs text-slate-500">{f.required ? 'Sí' : 'No'}</td>
                  <td className="px-5 py-3 text-center text-xs text-slate-500 tabular-nums">{f.sort_order}</td>
                  <td className="px-5 py-3">
                    <div className="flex items-center justify-end gap-1">
                      <button onClick={() => openEdit(f)}
                        className="rounded-lg p-1.5 text-slate-400 hover:text-primary hover:bg-slate-100 transition-colors">
                        <Pencil className="h-3.5 w-3.5" />
                      </button>
                      <button
                        onClick={async () => { if (await confirm({ message: `¿Eliminar el campo "${f.label}"?`, confirmLabel: 'Eliminar' })) del.mutate(f.id) }}
                        disabled={del.isPending}
                        className="rounded-lg p-1.5 text-slate-400 hover:text-red-500 hover:bg-red-50 transition-colors disabled:opacity-50">
                        <Trash2 className="h-3.5 w-3.5" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

// ─── Tabs ────────────────────────────────────────────────────────────────────

const TABS = [
  { id: 'info', label: 'Información', icon: Info },
  { id: 'fields', label: 'Campos', icon: Database },
] as const

type TabId = typeof TABS[number]['id']

// ─── Main Page ───────────────────────────────────────────────────────────────

export function SupplierTypeDetailPage() {
  const { id } = useParams<{ id: string }>()
  const { data: types = [], isLoading } = useSupplierTypes()
  const [activeTab, setActiveTab] = useState<TabId>('info')

  if (isLoading) {
    return (
      <div className="max-w-5xl mx-auto p-6 lg:p-8">
        <div className="text-sm text-slate-400 py-12 text-center">Cargando...</div>
      </div>
    )
  }

  const supplierType = types.find(t => t.id === id)
  if (!supplierType) return <Navigate to="/inventario/configuracion/tipos-proveedor" replace />

  return (
    <div className="p-8 space-y-6 max-w-5xl mx-auto">
      {/* Breadcrumbs */}
      <nav className="flex items-center gap-1.5 text-xs text-slate-400">
        <Link to="/inventario/configuracion" className="hover:text-slate-600 transition-colors">Configuración</Link>
        <ChevronRight className="h-3 w-3" />
        <Link to="/inventario/configuracion/tipos-proveedor" className="hover:text-slate-600 transition-colors">Tipos de proveedor</Link>
        <ChevronRight className="h-3 w-3" />
        <span className="text-slate-700 font-medium">{supplierType.name}</span>
      </nav>

      {/* Header */}
      <div className="flex items-center gap-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-xl"
          style={{ backgroundColor: (supplierType.color ?? '#f59e0b') + '15' }}>
          <Truck className="h-5 w-5" style={{ color: supplierType.color ?? '#f59e0b' }} />
        </div>
        <div className="flex-1">
          <h1 className="text-xl font-bold text-slate-900">{supplierType.name}</h1>
          {supplierType.description && (
            <p className="text-sm text-slate-500">{supplierType.description}</p>
          )}
        </div>
        <code className="hidden sm:block text-xs font-mono text-slate-400 bg-slate-50 border border-slate-100 px-2.5 py-1 rounded-lg">
          {supplierType.slug}
        </code>
      </div>

      {/* Tabs */}
      <div className="border-b border-slate-200">
        <div className="flex gap-1">
          {TABS.map(tab => (
            <button key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={cn(
                'flex items-center gap-1.5 px-4 py-2.5 text-sm font-medium border-b-2 transition-colors',
                activeTab === tab.id
                  ? 'border-primary text-primary'
                  : 'border-transparent text-slate-500 hover:text-slate-700 hover:border-slate-300',
              )}>
              <tab.icon className="h-4 w-4" />
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {/* Tab content */}
      <div className="bg-white rounded-2xl border border-slate-100 shadow-sm p-6">
        {activeTab === 'info' && <InfoTab supplierType={supplierType} />}
        {activeTab === 'fields' && <FieldsTab supplierTypeId={supplierType.id} />}
      </div>
    </div>
  )
}
