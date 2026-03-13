import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Plus, ClipboardCheck, ChevronRight } from 'lucide-react'
import { useCycleCounts, useCreateCycleCount, useWarehouses, useProducts } from '@/hooks/useInventory'
import { useUserLookup } from '@/hooks/useUserLookup'

const STATUS_OPTIONS: { value: string; label: string }[] = [
  { value: '', label: 'Todos' },
  { value: 'draft', label: 'Borrador' },
  { value: 'in_progress', label: 'En progreso' },
  { value: 'completed', label: 'Completado' },
  { value: 'approved', label: 'Aprobado' },
  { value: 'canceled', label: 'Cancelado' },
]

const statusColors: Record<string, string> = {
  draft: 'bg-slate-100 text-slate-700',
  in_progress: 'bg-blue-100 text-blue-700',
  completed: 'bg-amber-100 text-amber-700',
  approved: 'bg-green-100 text-green-700',
  canceled: 'bg-red-100 text-red-700',
}

const statusLabels: Record<string, string> = {
  draft: 'Borrador',
  in_progress: 'En progreso',
  completed: 'Completado',
  approved: 'Aprobado',
  canceled: 'Cancelado',
}

export function CycleCountsPage() {
  const [statusFilter, setStatusFilter] = useState('')
  const [showCreate, setShowCreate] = useState(false)
  const { data, isLoading } = useCycleCounts({
    status: statusFilter || undefined,
  })
  const { resolve } = useUserLookup(data?.items.map(cc => cc.created_by) ?? [])

  return (
    <div className="max-w-5xl mx-auto p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-xl bg-indigo-50">
            <ClipboardCheck className="h-6 w-6 text-indigo-600" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-slate-900">Conteo Ciclico</h1>
            <p className="text-sm text-slate-500">Verificacion de inventario fisico vs sistema</p>
          </div>
        </div>
        <button
          onClick={() => setShowCreate(true)}
          className="flex items-center gap-2 rounded-2xl bg-indigo-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-indigo-700 shadow-sm"
        >
          <Plus className="h-4 w-4" /> Nuevo conteo
        </button>
      </div>

      {/* Status filter chips */}
      <div className="flex gap-2 flex-wrap">
        {STATUS_OPTIONS.map((opt) => (
          <button
            key={opt.value}
            onClick={() => setStatusFilter(opt.value)}
            className={`px-3 py-1.5 rounded-full text-xs font-medium transition ${
              statusFilter === opt.value
                ? 'bg-indigo-600 text-white'
                : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
            }`}
          >
            {opt.label}
          </button>
        ))}
      </div>

      {/* Table */}
      <div className="bg-white rounded-2xl border border-slate-100 shadow-sm overflow-hidden">
        {isLoading ? (
          <div className="p-8 text-center text-slate-400">Cargando...</div>
        ) : !data?.items?.length ? (
          <div className="p-8 text-center text-slate-400">Sin conteos registrados</div>
        ) : (
          <>
          {/* Mobile cards */}
          <div className="space-y-3 p-4 md:hidden">
            {data.items.map((cc) => (
              <Link key={cc.id} to={`/inventario/conteos/${cc.id}`} className="block rounded-xl border border-gray-200 bg-white p-4 shadow-sm space-y-2">
                <div className="flex items-center justify-between">
                  <span className="font-medium text-indigo-600">{cc.count_number}</span>
                  <span className={`inline-block px-2 py-0.5 rounded-full text-xs font-medium ${statusColors[cc.status] ?? 'bg-slate-100 text-slate-600'}`}>
                    {statusLabels[cc.status] ?? cc.status}
                  </span>
                </div>
                <div className="space-y-1 text-sm">
                  <div className="flex justify-between"><span className="text-slate-400">Bodega</span><span className="text-slate-600">{cc.warehouse_name ?? '-'}</span></div>
                  <div className="flex justify-between"><span className="text-slate-400">Fecha</span><span className="text-slate-600">{cc.scheduled_date ? new Date(cc.scheduled_date).toLocaleDateString() : '-'}</span></div>
                  <div className="flex justify-between"><span className="text-slate-400">Creado</span><span className="text-slate-600">{new Date(cc.created_at).toLocaleDateString()}</span></div>
                  <div className="flex justify-between"><span className="text-slate-400">Creado por</span><span className="text-slate-500 text-xs">{resolve(cc.created_by)}</span></div>
                </div>
              </Link>
            ))}
          </div>

          {/* Desktop table */}
          <div className="hidden md:block overflow-x-auto">
          <table className="w-full text-sm min-w-[600px]">
            <thead>
              <tr className="bg-slate-50 border-b border-slate-100">
                <th className="text-left px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wide">Numero</th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wide">Bodega</th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wide">Estado</th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wide">Fecha</th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wide">Creado</th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wide">Creado por</th>
                <th className="w-10" />
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-50">
              {data.items.map((cc) => (
                <tr key={cc.id} className="hover:bg-slate-50">
                  <td className="px-4 py-3 font-medium text-slate-900">
                    <Link to={`/inventario/conteos/${cc.id}`} className="text-indigo-600 hover:underline">
                      {cc.count_number}
                    </Link>
                  </td>
                  <td className="px-4 py-3 text-slate-600">{cc.warehouse_name ?? '-'}</td>
                  <td className="px-4 py-3">
                    <span className={`inline-block px-2 py-0.5 rounded-full text-xs font-medium ${statusColors[cc.status] ?? 'bg-slate-100 text-slate-600'}`}>
                      {statusLabels[cc.status] ?? cc.status}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-slate-500">
                    {cc.scheduled_date ? new Date(cc.scheduled_date).toLocaleDateString() : '-'}
                  </td>
                  <td className="px-4 py-3 text-slate-500">
                    {new Date(cc.created_at).toLocaleDateString()}
                  </td>
                  <td className="px-4 py-3 text-slate-400 text-xs">{resolve(cc.created_by)}</td>
                  <td className="px-4 py-3">
                    <Link to={`/inventario/conteos/${cc.id}`}>
                      <ChevronRight className="h-4 w-4 text-slate-400" />
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          </div>
          </>
        )}
      </div>

      {/* Create modal */}
      {showCreate && <CreateCycleCountModal onClose={() => setShowCreate(false)} />}
    </div>
  )
}

// ── Create modal ──────────────────────────────────────────────────────────────

function CreateCycleCountModal({ onClose }: { onClose: () => void }) {
  const { data: warehouses } = useWarehouses()
  const { data: productsData } = useProducts({ limit: 200 })
  const createMut = useCreateCycleCount()

  const [warehouseId, setWarehouseId] = useState('')
  const [selectedProducts, setSelectedProducts] = useState<string[]>([])
  const [methodology, setMethodology] = useState('')
  const [assignedCounters, setAssignedCounters] = useState(1)
  const [minutesPerCount, setMinutesPerCount] = useState(2)
  const [scheduledDate, setScheduledDate] = useState('')
  const [notes, setNotes] = useState('')

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!warehouseId) return
    await createMut.mutateAsync({
      warehouse_id: warehouseId,
      product_ids: selectedProducts.length > 0 ? selectedProducts : undefined,
      methodology: methodology || undefined,
      assigned_counters: assignedCounters,
      minutes_per_count: minutesPerCount,
      scheduled_date: scheduledDate || undefined,
      notes: notes || undefined,
    })
    onClose()
  }

  const toggleProduct = (id: string) => {
    setSelectedProducts((prev) =>
      prev.includes(id) ? prev.filter((p) => p !== id) : [...prev, id]
    )
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 backdrop-blur-sm">
      <form
        onSubmit={handleSubmit}
        className="w-full max-w-lg bg-white rounded-3xl shadow-2xl p-6 space-y-5 max-h-[80vh] overflow-y-auto"
      >
        <h2 className="text-lg font-bold text-slate-900">Nuevo Conteo Ciclico</h2>

        {/* Warehouse */}
        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1">Bodega *</label>
          <select
            value={warehouseId}
            onChange={(e) => setWarehouseId(e.target.value)}
            required
            className="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
          >
            <option value="">Seleccionar bodega</option>
            {warehouses?.map((w) => (
              <option key={w.id} value={w.id}>{w.name}</option>
            ))}
          </select>
        </div>

        {/* Products (optional multiselect) */}
        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1">
            Productos <span className="text-slate-400 text-xs">(vacio = todos con stock)</span>
          </label>
          <div className="border border-slate-200 rounded-xl max-h-40 overflow-y-auto p-2 space-y-1">
            {productsData?.items?.map((p) => (
              <label key={p.id} className="flex items-center gap-2 px-2 py-1 rounded-lg hover:bg-slate-50 cursor-pointer">
                <input
                  type="checkbox"
                  checked={selectedProducts.includes(p.id)}
                  onChange={() => toggleProduct(p.id)}
                  className="rounded text-indigo-600"
                />
                <span className="text-sm text-slate-700">{p.sku} — {p.name}</span>
              </label>
            ))}
            {!productsData?.items?.length && (
              <p className="text-xs text-slate-400 px-2">Sin productos</p>
            )}
          </div>
        </div>

        {/* Methodology */}
        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1">Metodologia</label>
          <select
            value={methodology}
            onChange={(e) => setMethodology(e.target.value)}
            className="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
          >
            <option value="">Sin metodologia especifica</option>
            <option value="control_group">Grupo de control</option>
            <option value="location_audit">Auditoria por ubicacion</option>
            <option value="random_selection">Seleccion aleatoria</option>
            <option value="diminishing_population">Poblacion decreciente</option>
            <option value="product_category">Categoria de producto</option>
            <option value="abc">Clasificacion ABC</option>
          </select>
        </div>

        {/* Personnel */}
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Contadores asignados</label>
            <input
              type="number"
              min={1}
              value={assignedCounters}
              onChange={(e) => setAssignedCounters(Math.max(1, parseInt(e.target.value) || 1))}
              className="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm focus:ring-2 focus:ring-indigo-500"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Min/conteo</label>
            <input
              type="number"
              min={1}
              value={minutesPerCount}
              onChange={(e) => setMinutesPerCount(Math.max(1, parseInt(e.target.value) || 2))}
              className="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm focus:ring-2 focus:ring-indigo-500"
            />
          </div>
        </div>

        {/* Scheduled date */}
        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1">Fecha programada</label>
          <input
            type="date"
            value={scheduledDate}
            onChange={(e) => setScheduledDate(e.target.value)}
            className="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm focus:ring-2 focus:ring-indigo-500"
          />
        </div>

        {/* Notes */}
        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1">Notas</label>
          <textarea
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            rows={2}
            className="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm focus:ring-2 focus:ring-indigo-500"
          />
        </div>

        {/* Actions */}
        <div className="flex justify-end gap-3 pt-2">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 text-sm font-medium text-slate-600 hover:text-slate-900"
          >
            Cancelar
          </button>
          <button
            type="submit"
            disabled={!warehouseId || createMut.isPending}
            className="px-5 py-2 text-sm font-semibold text-white bg-indigo-600 rounded-xl hover:bg-indigo-700 disabled:opacity-50"
          >
            {createMut.isPending ? 'Creando...' : 'Crear conteo'}
          </button>
        </div>
      </form>
    </div>
  )
}
