import { useState, useEffect } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { Plus, ClipboardCheck, ChevronRight } from 'lucide-react'
import { useFormValidation } from '@/hooks/useFormValidation'
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
  draft: 'bg-secondary text-foreground',
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
  const location = useLocation()
  useEffect(() => { setShowCreate(false) }, [location.key])
  const { data, isLoading } = useCycleCounts({
    status: statusFilter || undefined,
  })
  const { resolve } = useUserLookup(data?.items.map(cc => cc.created_by) ?? [])

  return (
    <div className="max-w-5xl mx-auto p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-xl bg-primary/10">
            <ClipboardCheck className="h-6 w-6 text-primary" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-foreground">Conteo Ciclico</h1>
            <p className="text-sm text-muted-foreground">Verificacion de inventario fisico vs sistema</p>
          </div>
        </div>
        <button
          onClick={() => setShowCreate(true)}
          className="flex items-center gap-2 rounded-2xl bg-primary px-4 py-2.5 text-sm font-semibold text-white hover:bg-primary/90 "
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
                ? 'bg-primary text-white'
                : 'bg-secondary text-muted-foreground hover:bg-slate-200'
            }`}
          >
            {opt.label}
          </button>
        ))}
      </div>

      {/* Table */}
      <div className="bg-card rounded-2xl border border-border  overflow-hidden">
        {isLoading ? (
          <div className="p-8 text-center text-muted-foreground">Cargando...</div>
        ) : !data?.items?.length ? (
          <div className="p-8 text-center text-muted-foreground">Sin conteos registrados</div>
        ) : (
          <>
          {/* Mobile cards */}
          <div className="space-y-3 p-4 md:hidden">
            {data.items.map((cc) => (
              <Link key={cc.id} to={`/inventario/conteos/${cc.id}`} className="block rounded-xl border border-border bg-card p-4  space-y-2">
                <div className="flex items-center justify-between">
                  <span className="font-medium text-primary">{cc.count_number}</span>
                  <span className={`inline-block px-2 py-0.5 rounded-full text-xs font-medium ${statusColors[cc.status] ?? 'bg-secondary text-muted-foreground'}`}>
                    {statusLabels[cc.status] ?? cc.status}
                  </span>
                </div>
                <div className="space-y-1 text-sm">
                  <div className="flex justify-between"><span className="text-muted-foreground">Bodega</span><span className="text-muted-foreground">{cc.warehouse_name ?? '-'}</span></div>
                  <div className="flex justify-between"><span className="text-muted-foreground">Fecha</span><span className="text-muted-foreground">{cc.scheduled_date ? new Date(cc.scheduled_date).toLocaleDateString('es-CO') : '-'}</span></div>
                  <div className="flex justify-between"><span className="text-muted-foreground">Creado</span><span className="text-muted-foreground">{new Date(cc.created_at).toLocaleDateString('es-CO')}</span></div>
                  <div className="flex justify-between"><span className="text-muted-foreground">Creado por</span><span className="text-muted-foreground text-xs">{resolve(cc.created_by)}</span></div>
                </div>
              </Link>
            ))}
          </div>

          {/* Desktop table */}
          <div className="hidden md:block overflow-x-auto">
          <table className="w-full text-sm min-w-[600px]">
            <thead>
              <tr className="bg-muted border-b border-border">
                <th className="text-left px-4 py-3 text-xs font-semibold text-muted-foreground uppercase tracking-wide">Numero</th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-muted-foreground uppercase tracking-wide">Bodega</th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-muted-foreground uppercase tracking-wide">Estado</th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-muted-foreground uppercase tracking-wide">Fecha</th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-muted-foreground uppercase tracking-wide">Creado</th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-muted-foreground uppercase tracking-wide">Creado por</th>
                <th className="w-10" />
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-50">
              {data.items.map((cc) => (
                <tr key={cc.id} className="hover:bg-muted">
                  <td className="px-4 py-3 font-medium text-foreground">
                    <Link to={`/inventario/conteos/${cc.id}`} className="text-primary hover:underline">
                      {cc.count_number}
                    </Link>
                  </td>
                  <td className="px-4 py-3 text-muted-foreground">{cc.warehouse_name ?? '-'}</td>
                  <td className="px-4 py-3">
                    <span className={`inline-block px-2 py-0.5 rounded-full text-xs font-medium ${statusColors[cc.status] ?? 'bg-secondary text-muted-foreground'}`}>
                      {statusLabels[cc.status] ?? cc.status}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-muted-foreground">
                    {cc.scheduled_date ? new Date(cc.scheduled_date).toLocaleDateString('es-CO') : '-'}
                  </td>
                  <td className="px-4 py-3 text-muted-foreground">
                    {new Date(cc.created_at).toLocaleDateString('es-CO')}
                  </td>
                  <td className="px-4 py-3 text-muted-foreground text-xs">{resolve(cc.created_by)}</td>
                  <td className="px-4 py-3">
                    <Link to={`/inventario/conteos/${cc.id}`}>
                      <ChevronRight className="h-4 w-4 text-muted-foreground" />
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

  async function doSubmit() {
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

  const { formRef, handleSubmit: validateAndSubmit } = useFormValidation(doSubmit)

  const toggleProduct = (id: string) => {
    setSelectedProducts((prev) =>
      prev.includes(id) ? prev.filter((p) => p !== id) : [...prev, id]
    )
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 backdrop-blur-sm">
      <form
        ref={formRef}
        onSubmit={validateAndSubmit}
        noValidate
        className="w-full max-w-lg bg-card rounded-3xl shadow-2xl p-6 space-y-5 max-h-[80vh] overflow-y-auto"
      >
        <h2 className="text-lg font-bold text-foreground">Nuevo Conteo Ciclico</h2>

        {/* Warehouse */}
        <div>
          <label className="block text-sm font-medium text-foreground mb-1">Bodega *</label>
          <select
            value={warehouseId}
            onChange={(e) => setWarehouseId(e.target.value)}
            required
            className="w-full rounded-xl border border-border px-3 py-2 text-sm focus:ring-2 focus:ring-ring focus:border-primary"
          >
            <option value="">Seleccionar bodega</option>
            {warehouses?.map((w) => (
              <option key={w.id} value={w.id}>{w.name}</option>
            ))}
          </select>
        </div>

        {/* Products (optional multiselect) */}
        <div>
          <label className="block text-sm font-medium text-foreground mb-1">
            Productos <span className="text-muted-foreground text-xs">(vacio = todos con stock)</span>
          </label>
          <div className="border border-border rounded-xl max-h-40 overflow-y-auto p-2 space-y-1">
            {productsData?.items?.map((p) => (
              <label key={p.id} className="flex items-center gap-2 px-2 py-1 rounded-lg hover:bg-muted cursor-pointer">
                <input
                  type="checkbox"
                  checked={selectedProducts.includes(p.id)}
                  onChange={() => toggleProduct(p.id)}
                  className="rounded text-primary"
                />
                <span className="text-sm text-foreground">{p.sku} — {p.name}</span>
              </label>
            ))}
            {!productsData?.items?.length && (
              <p className="text-xs text-muted-foreground px-2">Sin productos</p>
            )}
          </div>
        </div>

        {/* Methodology */}
        <div>
          <label className="block text-sm font-medium text-foreground mb-1">Metodologia</label>
          <select
            value={methodology}
            onChange={(e) => setMethodology(e.target.value)}
            className="w-full rounded-xl border border-border px-3 py-2 text-sm focus:ring-2 focus:ring-ring focus:border-primary"
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
            <label className="block text-sm font-medium text-foreground mb-1">Contadores asignados</label>
            <input
              type="number"
              min={1}
              value={assignedCounters}
              onChange={(e) => setAssignedCounters(Math.max(1, parseInt(e.target.value) || 1))}
              className="w-full rounded-xl border border-border px-3 py-2 text-sm focus:ring-2 focus:ring-ring"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-foreground mb-1">Min/conteo</label>
            <input
              type="number"
              min={1}
              value={minutesPerCount}
              onChange={(e) => setMinutesPerCount(Math.max(1, parseInt(e.target.value) || 2))}
              className="w-full rounded-xl border border-border px-3 py-2 text-sm focus:ring-2 focus:ring-ring"
            />
          </div>
        </div>

        {/* Scheduled date */}
        <div>
          <label className="block text-sm font-medium text-foreground mb-1">Fecha programada</label>
          <input
            type="date"
            value={scheduledDate}
            onChange={(e) => setScheduledDate(e.target.value)}
            className="w-full rounded-xl border border-border px-3 py-2 text-sm focus:ring-2 focus:ring-ring"
          />
        </div>

        {/* Notes */}
        <div>
          <label className="block text-sm font-medium text-foreground mb-1">Notas</label>
          <textarea
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            rows={2}
            className="w-full rounded-xl border border-border px-3 py-2 text-sm focus:ring-2 focus:ring-ring"
          />
        </div>

        {/* Actions */}
        <div className="flex justify-end gap-3 pt-2">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 text-sm font-medium text-muted-foreground hover:text-foreground"
          >
            Cancelar
          </button>
          <button
            type="submit"
            disabled={!warehouseId || createMut.isPending}
            className="px-5 py-2 text-sm font-semibold text-white bg-primary rounded-xl hover:bg-primary/90 disabled:opacity-50"
          >
            {createMut.isPending ? 'Creando...' : 'Crear conteo'}
          </button>
        </div>
      </form>
    </div>
  )
}
