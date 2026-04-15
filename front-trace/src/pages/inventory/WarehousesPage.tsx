import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Plus, Warehouse as WarehouseIcon, Pencil, Trash2, ChevronRight,
  CheckCircle2, MapPin, Ruler, DollarSign,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { useFormValidation } from '@/hooks/useFormValidation'
import { useIsModuleActive } from '@/hooks/useModules'
import { CopyableId } from '@/components/inventory/CopyableId'
import {
  useWarehouses, useCreateWarehouse, useUpdateWarehouse, useDeleteWarehouse,
  useStockLevels, useWarehouseTypes,
} from '@/hooks/useInventory'
import { useUserLookup } from '@/hooks/useUserLookup'
import type { Warehouse } from '@/types/inventory'

const WAREHOUSE_COLORS: Record<string, { bg: string; text: string }> = {
  main:      { bg: 'bg-primary/10',  text: 'text-primary' },
  secondary: { bg: 'bg-emerald-50', text: 'text-emerald-600' },
  virtual:   { bg: 'bg-purple-50',  text: 'text-purple-600' },
  transit:   { bg: 'bg-amber-50',   text: 'text-amber-600' },
}

// ─── Warehouse Modal (create + edit) ─────────────────────────────────────────

function WarehouseModal({
  warehouse,
  onClose,
}: {
  warehouse: Warehouse | null
  onClose: () => void
}) {
  const { data: warehouseTypes = [] } = useWarehouseTypes()
  const create = useCreateWarehouse()
  const update = useUpdateWarehouse()
  const remove = useDeleteWarehouse()
  const isComplianceActive = useIsModuleActive('compliance')
  const [confirmDelete, setConfirmDelete] = useState(false)

  // Address is stored as a JSONB blob server-side. We expose individual
  // fields here and recompose them on submit.
  const initialAddress = (warehouse?.address ?? {}) as Record<string, any>
  const [form, setForm] = useState({
    name: warehouse?.name ?? '',
    code: warehouse?.code ?? '',
    type: warehouse?.type ?? 'main',
    warehouse_type_id: warehouse?.warehouse_type_id ?? '',
    is_default: warehouse?.is_default ?? false,
    is_active: warehouse?.is_active ?? true,
    cost_per_sqm: warehouse?.cost_per_sqm ?? null as number | null,
    total_area_sqm: warehouse?.total_area_sqm ?? null as number | null,
    max_stock_capacity: warehouse?.max_stock_capacity ?? null as number | null,
    addr_line1: initialAddress.line1 ?? initialAddress.address_line ?? '',
    addr_city: initialAddress.city ?? '',
    addr_state: initialAddress.state ?? '',
    addr_zip: initialAddress.zip ?? initialAddress.postal_code ?? '',
    addr_country: initialAddress.country ?? 'CO',
    addr_lat: initialAddress.latitude ?? '',
    addr_lon: initialAddress.longitude ?? '',
  })

  async function doSubmit() {
    // Compose address JSON from individual fields. Only include fields with
    // values so we don't write empty strings into the JSONB blob.
    const address: Record<string, any> = {}
    if (form.addr_line1) address.line1 = form.addr_line1
    if (form.addr_city) address.city = form.addr_city
    if (form.addr_state) address.state = form.addr_state
    if (form.addr_zip) address.zip = form.addr_zip
    if (form.addr_country) address.country = form.addr_country
    if (form.addr_lat !== '' && form.addr_lat != null) address.latitude = Number(form.addr_lat)
    if (form.addr_lon !== '' && form.addr_lon != null) address.longitude = Number(form.addr_lon)

    const data: any = {
      name: form.name,
      code: form.code,
      type: form.type,
      warehouse_type_id: form.warehouse_type_id || null,
      is_default: form.is_default,
      is_active: form.is_active,
      cost_per_sqm: form.cost_per_sqm,
      total_area_sqm: form.total_area_sqm,
      max_stock_capacity: form.max_stock_capacity,
      address: Object.keys(address).length > 0 ? address : null,
    }
    if (warehouse) {
      await update.mutateAsync({ id: warehouse.id, data })
    } else {
      await create.mutateAsync(data)
    }
    onClose()
  }

  const { formRef, handleSubmit: validateAndSubmit } = useFormValidation(doSubmit)

  const isPending = create.isPending || update.isPending
  const inputCls = 'h-11 w-full rounded-lg border border-gray-300 bg-transparent px-4 py-2.5 text-sm text-foreground  placeholder:text-muted-foreground focus:border-primary/50 focus:outline-none focus:ring-3 focus:ring-ring/20'

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4" role="dialog" aria-modal="true">
      <div className="absolute inset-0 bg-gray-900/50" onClick={onClose} />
      <div className="relative w-full max-w-md bg-card rounded-2xl border border-border shadow-xl max-h-[90vh] overflow-y-auto">
        <div className="px-6 pt-6 pb-4 border-b border-border">
          <h2 className="text-lg font-semibold text-foreground">
            {warehouse ? 'Editar Bodega' : 'Nueva Bodega'}
          </h2>
          <p className="text-sm text-muted-foreground mt-0.5">
            {warehouse ? 'Modifica la configuración de la bodega' : 'Agrega una nueva bodega a tu inventario'}
          </p>
        </div>

        <form ref={formRef} onSubmit={validateAndSubmit} noValidate className="px-6 py-5 space-y-4">
          <div>
            <label className="mb-1.5 block text-sm font-medium text-foreground">Nombre *</label>
            <input required value={form.name} onChange={e => setForm(f => ({ ...f, name: e.target.value }))}
              placeholder="Ej: Bodega Central"
              className={inputCls} />
          </div>
          <div>
            <label className="mb-1.5 block text-sm font-medium text-foreground">Código *</label>
            <input required value={form.code} onChange={e => setForm(f => ({ ...f, code: e.target.value.toUpperCase() }))}
              placeholder="Ej: MAIN"
              className={cn(inputCls, 'font-mono')} />
          </div>
          <div>
            <label className="mb-1.5 block text-sm font-medium text-foreground">Tipo de bodega</label>
            <select value={form.warehouse_type_id} onChange={e => setForm(f => ({ ...f, warehouse_type_id: e.target.value }))}
              className={inputCls}>
              <option value="">Sin tipo</option>
              {warehouseTypes.map(wt => <option key={wt.id} value={wt.id}>{wt.name}</option>)}
            </select>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="mb-1.5 block text-sm font-medium text-foreground">Costo por m²</label>
              <input type="number" min={0} step="0.01" placeholder="Ej: 8.00"
                className={inputCls}
                value={form.cost_per_sqm ?? ''}
                onChange={e => setForm(f => ({ ...f, cost_per_sqm: e.target.value ? Number(e.target.value) : null }))} />
            </div>
            <div>
              <label className="mb-1.5 block text-sm font-medium text-foreground">Área total (m²)</label>
              <input type="number" min={0} step="0.01" placeholder="Ej: 500"
                className={inputCls}
                value={form.total_area_sqm ?? ''}
                onChange={e => setForm(f => ({ ...f, total_area_sqm: e.target.value ? Number(e.target.value) : null }))} />
            </div>
          </div>
          <div>
            <label className="mb-1.5 block text-sm font-medium text-foreground">Stock maximo (opcional)</label>
            <input type="number" min={1} step="1" placeholder="Ej: 500 — dejar vacio si no tiene tope"
              className={inputCls}
              value={form.max_stock_capacity ?? ''}
              onChange={e => setForm(f => ({ ...f, max_stock_capacity: e.target.value ? Number(e.target.value) : null }))} />
            <p className="mt-1 text-xs text-muted-foreground">Capacidad maxima de productos. Se usa para calcular % de ocupacion en el dashboard.</p>
          </div>

          {/* ── Dirección (opcional) ──────────────────────────────────── */}
          <div className="pt-2 border-t border-border">
            <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2">
              Dirección (opcional)
            </h3>
            <p className="text-xs text-muted-foreground mb-3">
              Útil para documentos de remisión, ruteo logístico e ICA municipal{isComplianceActive ? ', y trazabilidad EUDR' : ''}.
            </p>
            <div className="space-y-3">
              <div>
                <label className="mb-1.5 block text-sm font-medium text-foreground">Dirección</label>
                <input
                  value={form.addr_line1}
                  onChange={(e) => setForm((f) => ({ ...f, addr_line1: e.target.value }))}
                  placeholder="Ej: Cra 7 # 12-34, Bodega B"
                  className={inputCls}
                />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="mb-1.5 block text-sm font-medium text-foreground">Ciudad / Municipio</label>
                  <input
                    value={form.addr_city}
                    onChange={(e) => setForm((f) => ({ ...f, addr_city: e.target.value }))}
                    placeholder="Ej: Bogotá"
                    className={inputCls}
                  />
                </div>
                <div>
                  <label className="mb-1.5 block text-sm font-medium text-foreground">Departamento / Estado</label>
                  <input
                    value={form.addr_state}
                    onChange={(e) => setForm((f) => ({ ...f, addr_state: e.target.value }))}
                    placeholder="Ej: Cundinamarca"
                    className={inputCls}
                  />
                </div>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="mb-1.5 block text-sm font-medium text-foreground">Código postal</label>
                  <input
                    value={form.addr_zip}
                    onChange={(e) => setForm((f) => ({ ...f, addr_zip: e.target.value }))}
                    placeholder="Ej: 110111"
                    className={inputCls}
                  />
                </div>
                <div>
                  <label className="mb-1.5 block text-sm font-medium text-foreground">País (ISO 2)</label>
                  <input
                    value={form.addr_country}
                    onChange={(e) => setForm((f) => ({ ...f, addr_country: e.target.value.toUpperCase().slice(0, 2) }))}
                    placeholder="CO"
                    maxLength={2}
                    className={cn(inputCls, 'font-mono uppercase')}
                  />
                </div>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="mb-1.5 block text-sm font-medium text-foreground">Latitud (GPS)</label>
                  <input
                    type="number"
                    step="0.000001"
                    value={form.addr_lat}
                    onChange={(e) => setForm((f) => ({ ...f, addr_lat: e.target.value }))}
                    placeholder="Ej: 4.710989"
                    className={inputCls}
                  />
                </div>
                <div>
                  <label className="mb-1.5 block text-sm font-medium text-foreground">Longitud (GPS)</label>
                  <input
                    type="number"
                    step="0.000001"
                    value={form.addr_lon}
                    onChange={(e) => setForm((f) => ({ ...f, addr_lon: e.target.value }))}
                    placeholder="Ej: -74.072092"
                    className={inputCls}
                  />
                </div>
              </div>
              <p className="text-xs text-muted-foreground">
                {isComplianceActive
                  ? 'Las coordenadas GPS son opcionales pero recomendadas si necesitás cumplir EUDR (regulación europea de deforestación) o trazabilidad geográfica de cadena de frío.'
                  : 'Las coordenadas GPS son opcionales y se usan para mapas y geolocalización en reportes.'}
              </p>
            </div>
          </div>
          <label className="flex items-center gap-2 text-sm text-muted-foreground cursor-pointer">
            <input type="checkbox" checked={form.is_default} onChange={e => setForm(f => ({ ...f, is_default: e.target.checked }))}
              className="rounded" />
            Bodega predeterminada
          </label>
          {warehouse && (
            <label className="flex items-center gap-2 text-sm text-muted-foreground cursor-pointer">
              <input type="checkbox" checked={form.is_active} onChange={e => setForm(f => ({ ...f, is_active: e.target.checked }))}
                className="rounded" />
              Activa
            </label>
          )}

          {/* Delete confirmation */}
          {warehouse && confirmDelete && (
            <div className="rounded-lg border border-red-200 bg-red-50 p-3 space-y-2">
              <p className="text-sm text-red-700 font-medium">¿Eliminar esta bodega?</p>
              <p className="text-xs text-red-500">No se puede eliminar si tiene órdenes de producción activas.</p>
              <div className="flex gap-2">
                <button type="button" onClick={() => setConfirmDelete(false)}
                  className="flex-1 rounded-lg border border-gray-300 px-3 py-1.5 text-xs text-muted-foreground hover:bg-card">
                  No, cancelar
                </button>
                <button type="button" disabled={remove.isPending}
                  onClick={async () => {
                    try {
                      await remove.mutateAsync(warehouse.id)
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
        </form>

        <div className="flex gap-3 px-6 py-4 border-t border-border">
          {warehouse && !confirmDelete && (
            <button type="button" onClick={() => setConfirmDelete(true)}
              className="rounded-lg border border-red-200 px-3 py-2.5 text-sm text-red-500 hover:bg-red-50 hover:text-red-700 transition"
              title="Eliminar bodega">
              <Trash2 className="h-4 w-4" />
            </button>
          )}
          <button type="button" onClick={onClose}
            className="flex-1 rounded-lg border border-gray-300 px-4 py-2.5 text-sm font-medium text-foreground hover:bg-muted transition">
            Cancelar
          </button>
          <button type="submit" form="" disabled={isPending}
            onClick={(e) => {
              e.preventDefault()
              const formEl = document.querySelector<HTMLFormElement>('form')
              formEl?.requestSubmit()
            }}
            className="flex-1 rounded-lg bg-primary px-4 py-2.5 text-sm font-medium text-white hover:bg-primary disabled:opacity-60  transition">
            {isPending ? 'Guardando…' : warehouse ? 'Guardar' : 'Crear bodega'}
          </button>
        </div>
      </div>
    </div>
  )
}

// ─── Main Page ────────────────────────────────────────────────────────────────

export function WarehousesPage() {
  const navigate = useNavigate()
  const { data: warehouses = [], isLoading } = useWarehouses()
  const { data: allLevels = [] } = useStockLevels()
  const { data: warehouseTypes = [] } = useWarehouseTypes()
  const [modal, setModal] = useState<Warehouse | null | 'new'>(null)

  const { resolve } = useUserLookup(warehouses.map(w => w.created_by))
  const whTypeMap = Object.fromEntries(warehouseTypes.map(wt => [wt.id, wt]))

  const stockByWarehouse = allLevels.reduce<Record<string, number>>((acc, lv) => {
    const count = (acc[lv.warehouse_id] ?? 0) + 1
    return { ...acc, [lv.warehouse_id]: count }
  }, {})

  return (
    <div className="space-y-6">
      {/* Breadcrumb */}
      <nav className="mb-4">
        <ol className="flex items-center gap-2 text-sm">
          <li className="text-muted-foreground">Inventario</li>
          <li><ChevronRight className="h-4 w-4 text-muted-foreground" /></li>
          <li className="text-primary">Bodegas</li>
        </ol>
      </nav>

      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-foreground">Bodegas</h1>
          <p className="text-sm text-muted-foreground mt-1">Administra las ubicaciones de almacenamiento</p>
        </div>
        <button
          onClick={() => setModal('new')}
          className="flex items-center gap-2 rounded-lg bg-primary px-4 py-2.5 text-sm font-medium text-white hover:bg-primary  transition"
        >
          <Plus className="h-4 w-4" /> Nueva bodega
        </button>
      </div>

      {/* Cards grid */}
      {isLoading ? (
        <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 xl:grid-cols-3">
          {[...Array(3)].map((_, i) => (
            <div key={i} className="h-52 rounded-2xl border border-border bg-muted animate-pulse" />
          ))}
        </div>
      ) : warehouses.length === 0 ? (
        <div className="py-16 text-center">
          <WarehouseIcon className="h-12 w-12 text-gray-200 mx-auto mb-3" />
          <p className="text-sm font-medium text-foreground">No hay bodegas registradas</p>
          <p className="text-xs text-muted-foreground mt-1">Registra tu primera bodega para gestionar el inventario físico.</p>
          <button
            type="button"
            onClick={() => setModal('new')}
            className="mt-4 inline-flex items-center gap-2 rounded-md bg-primary px-3 py-1.5 text-xs font-medium text-primary-foreground hover:bg-primary/90"
          >
            <Plus className="h-3.5 w-3.5" /> Nueva bodega
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 xl:grid-cols-3">
          {[...warehouses].sort((a, b) => {
            if (a.is_default && !b.is_default) return -1
            if (!a.is_default && b.is_default) return 1
            if (a.is_active && !b.is_active) return -1
            if (!a.is_active && b.is_active) return 1
            return 0
          }).map((wh) => {
            const colors = WAREHOUSE_COLORS[wh.type] ?? { bg: 'bg-muted', text: 'text-muted-foreground' }
            const whType = wh.warehouse_type_id ? whTypeMap[wh.warehouse_type_id] : null
            const skuCount = stockByWarehouse[wh.id] ?? 0

            return (
              <div
                key={wh.id}
                className={cn(
                  'rounded-2xl border p-5  hover:shadow-md transition-shadow cursor-pointer',
                  wh.is_active
                    ? 'border-border bg-card'
                    : 'border-border/60 bg-muted opacity-70',
                )}
                onClick={() => navigate(`/inventario/bodegas/${wh.id}`)}
              >
                {/* Top: icon + edit button */}
                <div className="flex items-start justify-between">
                  <div className={cn('flex h-[50px] w-[50px] items-center justify-center rounded-xl', colors.bg)}>
                    <WarehouseIcon className={cn('h-6 w-6', colors.text)} />
                  </div>
                  <button
                    onClick={(e) => { e.stopPropagation(); setModal(wh) }}
                    className="rounded-lg p-2 text-muted-foreground hover:text-primary hover:bg-primary/10 transition-colors"
                    title="Editar bodega"
                  >
                    <Pencil className="h-4 w-4" />
                  </button>
                </div>

                {/* Title + badges */}
                <div className="mt-4 flex items-center gap-2">
                  <h3 className="text-sm font-semibold text-foreground">{wh.name}</h3>
                  {wh.is_active ? (
                    <span className="inline-flex items-center gap-1 rounded-full bg-emerald-50 px-2 py-0.5 text-[10px] font-semibold text-emerald-600">
                      <CheckCircle2 className="h-3 w-3" /> Activa
                    </span>
                  ) : (
                    <span className="inline-flex items-center gap-1 rounded-full bg-secondary px-2 py-0.5 text-[10px] font-semibold text-muted-foreground">
                      Inactiva
                    </span>
                  )}
                </div>
                <p className="text-xs text-muted-foreground mt-0.5 font-mono">{wh.code}</p>

                {/* Description / type */}
                <p className="mt-2 text-sm text-muted-foreground leading-relaxed">
                  {whType ? whType.name : wh.type.charAt(0).toUpperCase() + wh.type.slice(1)}
                  {wh.is_default && <span className="text-primary font-medium"> · Predeterminada</span>}
                </p>

                {/* Feature tags */}
                <div className="mt-3 flex flex-wrap gap-2">
                  <span className="inline-flex items-center gap-1 rounded-full border border-border bg-muted px-2.5 py-1 text-xs text-muted-foreground">
                    <MapPin className="h-3 w-3 text-muted-foreground" /> {skuCount} SKUs
                  </span>
                  {wh.total_area_sqm != null && (
                    <span className="inline-flex items-center gap-1 rounded-full border border-border bg-muted px-2.5 py-1 text-xs text-muted-foreground">
                      <Ruler className="h-3 w-3 text-muted-foreground" /> {wh.total_area_sqm} m²
                    </span>
                  )}
                  {wh.cost_per_sqm != null && (
                    <span className="inline-flex items-center gap-1 rounded-full border border-border bg-muted px-2.5 py-1 text-xs text-muted-foreground">
                      <DollarSign className="h-3 w-3 text-muted-foreground" /> ${wh.cost_per_sqm}/m²
                    </span>
                  )}
                  {wh.max_stock_capacity != null && (
                    <span className="inline-flex items-center gap-1 rounded-full border border-primary/30 bg-primary/10 px-2.5 py-1 text-xs text-primary">
                      Max: {wh.max_stock_capacity}
                    </span>
                  )}
                </div>

                {/* Footer: created by + ID */}
                <div className="mt-3 flex items-center justify-between border-t border-border pt-3">
                  <span className="text-xs text-muted-foreground truncate">Creado por: {resolve(wh.created_by)}</span>
                  <CopyableId id={wh.id} />
                </div>
              </div>
            )
          })}
        </div>
      )}

      {modal && (
        <WarehouseModal
          warehouse={modal === 'new' ? null : modal}
          onClose={() => setModal(null)}
        />
      )}
    </div>
  )
}
