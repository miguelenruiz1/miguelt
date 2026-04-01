import { useState, useMemo, useCallback } from 'react'
import { useParams, Link } from 'react-router-dom'
import {
  ArrowLeft, Search, Package, Warehouse as WarehouseIcon,
  MapPin, ChevronRight, Plus, Pencil, Trash2, FolderTree, X, Check,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import {
  useWarehouses, useStockLevels, useProductTypes, useWarehouseTypes,
  useLocations, useCreateLocation, useUpdateLocation, useDeleteLocation,
  useQCApprove, useQCReject, useAssignStockLocation,
} from '@/hooks/useInventory'
import type { WarehouseLocation } from '@/types/inventory'

/* ------------------------------------------------------------------ */
/*  Dynamic type colors (cycle through a palette)                     */
/* ------------------------------------------------------------------ */

const COLOR_POOL = [
  { badge: 'bg-primary/10 text-primary border-primary/30', border: 'border-l-primary' },
  { badge: 'bg-sky-50 text-sky-700 border-sky-200', border: 'border-l-sky-500' },
  { badge: 'bg-amber-50 text-amber-700 border-amber-200', border: 'border-l-amber-500' },
  { badge: 'bg-emerald-50 text-emerald-700 border-emerald-200', border: 'border-l-emerald-500' },
  { badge: 'bg-rose-50 text-rose-700 border-rose-200', border: 'border-l-rose-500' },
  { badge: 'bg-violet-50 text-violet-700 border-violet-200', border: 'border-l-violet-500' },
  { badge: 'bg-orange-50 text-orange-700 border-orange-200', border: 'border-l-orange-500' },
  { badge: 'bg-teal-50 text-teal-700 border-teal-200', border: 'border-l-teal-500' },
]

function getTypeColor(type: string, allTypes: string[]) {
  const idx = allTypes.indexOf(type)
  return COLOR_POOL[(idx >= 0 ? idx : 0) % COLOR_POOL.length]
}

const DEPTH_INDENT = ['pl-3', 'pl-8', 'pl-14', 'pl-20', 'pl-26', 'pl-32']

const EMPTY_FORM = {
  name: '',
  code: '',
  location_type: '',
  parent_location_id: null as string | null,
  description: '',
  sort_order: 0,
}

/* ------------------------------------------------------------------ */
/*  Tree helpers                                                      */
/* ------------------------------------------------------------------ */

interface TreeNode {
  location: WarehouseLocation
  children: TreeNode[]
  depth: number
}

function buildTree(locations: WarehouseLocation[]): TreeNode[] {
  const map = new Map<string, TreeNode>()
  const roots: TreeNode[] = []

  const sorted = [...locations].sort((a, b) => a.sort_order - b.sort_order || a.name.localeCompare(b.name))
  for (const loc of sorted) {
    map.set(loc.id, { location: loc, children: [], depth: 0 })
  }
  for (const loc of sorted) {
    const node = map.get(loc.id)!
    if (loc.parent_location_id && map.has(loc.parent_location_id)) {
      const parent = map.get(loc.parent_location_id)!
      node.depth = parent.depth + 1
      parent.children.push(node)
    } else {
      roots.push(node)
    }
  }
  return roots
}

function flattenTree(nodes: TreeNode[], expanded: Set<string>): TreeNode[] {
  const result: TreeNode[] = []
  for (const node of nodes) {
    result.push(node)
    if (expanded.has(node.location.id) && node.children.length > 0) {
      result.push(...flattenTree(node.children, expanded))
    }
  }
  return result
}

function countDescendants(nodes: TreeNode[]): number {
  let count = 0
  for (const n of nodes) {
    count += 1 + countDescendants(n.children)
  }
  return count
}

/* ------------------------------------------------------------------ */
/*  Location inline form                                              */
/* ------------------------------------------------------------------ */

interface LocationFormProps {
  initial: typeof EMPTY_FORM
  locations: WarehouseLocation[]
  existingTypes: string[]
  onSubmit: (data: typeof EMPTY_FORM) => void
  onCancel: () => void
  submitLabel: string
}

function LocationForm({ initial, locations, existingTypes, onSubmit, onCancel, submitLabel }: LocationFormProps) {
  const [form, setForm] = useState(initial)

  const set = (key: string, val: string | number | null) =>
    setForm(prev => ({ ...prev, [key]: val }))

  const parentOptions = locations.filter(l => !('id' in initial) || l.id !== (initial as WarehouseLocation).id)

  return (
    <div className="bg-muted rounded-xl border border-border p-4 space-y-3">
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="block text-xs font-medium text-muted-foreground mb-1">Nombre *</label>
          <input
            value={form.name}
            onChange={e => set('name', e.target.value)}
            placeholder="Zona A"
            className="w-full rounded-lg border border-border px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
          />
        </div>
        <div>
          <label className="block text-xs font-medium text-muted-foreground mb-1">Codigo *</label>
          <input
            value={form.code}
            onChange={e => set('code', e.target.value)}
            placeholder="ZA-001"
            className="w-full rounded-lg border border-border px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
          />
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="block text-xs font-medium text-muted-foreground mb-1">Tipo *</label>
          <input
            list="location-types"
            value={form.location_type}
            onChange={e => set('location_type', e.target.value)}
            placeholder="Ej: zona, pasillo, estante, bin..."
            className="w-full rounded-lg border border-border px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
          />
          <datalist id="location-types">
            {existingTypes.map(t => (
              <option key={t} value={t} />
            ))}
          </datalist>
          <p className="text-[10px] text-muted-foreground mt-0.5">Escribe un tipo nuevo o selecciona uno existente</p>
        </div>
        <div>
          <label className="block text-xs font-medium text-muted-foreground mb-1">Ubicacion padre</label>
          <select
            value={form.parent_location_id ?? ''}
            onChange={e => set('parent_location_id', e.target.value || null)}
            className="w-full rounded-lg border border-border px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
          >
            <option value="">— Ninguna (raiz) —</option>
            {parentOptions.map(l => (
              <option key={l.id} value={l.id}>{l.name} ({l.location_type})</option>
            ))}
          </select>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="block text-xs font-medium text-muted-foreground mb-1">Descripcion</label>
          <input
            value={form.description}
            onChange={e => set('description', e.target.value)}
            placeholder="Opcional"
            className="w-full rounded-lg border border-border px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
          />
        </div>
        <div>
          <label className="block text-xs font-medium text-muted-foreground mb-1">Orden</label>
          <input
            type="number"
            value={form.sort_order}
            onChange={e => set('sort_order', Number(e.target.value))}
            className="w-full rounded-lg border border-border px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
          />
        </div>
      </div>

      <div className="flex items-center gap-2 pt-1">
        <button
          onClick={() => onSubmit(form)}
          disabled={!form.name.trim() || !form.code.trim() || !form.location_type.trim()}
          className="inline-flex items-center gap-1.5 rounded-lg bg-primary px-3 py-1.5 text-xs font-semibold text-white hover:bg-primary/90 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
        >
          <Check className="h-3.5 w-3.5" />
          {submitLabel}
        </button>
        <button
          onClick={onCancel}
          className="inline-flex items-center gap-1.5 rounded-lg bg-card border border-border px-3 py-1.5 text-xs font-semibold text-muted-foreground hover:bg-muted transition-colors"
        >
          <X className="h-3.5 w-3.5" />
          Cancelar
        </button>
      </div>
    </div>
  )
}

/* ------------------------------------------------------------------ */
/*  Location tree row                                                 */
/* ------------------------------------------------------------------ */

interface LocationRowProps {
  node: TreeNode
  expanded: boolean
  allTypes: string[]
  onToggle: () => void
  onEdit: () => void
  onDelete: () => void
  onToggleActive: () => void
  stockCountMap: Map<string, number>
}

function LocationRow({ node, expanded, allTypes, onToggle, onEdit, onDelete, onToggleActive, stockCountMap }: LocationRowProps) {
  const loc = node.location
  const hasChildren = node.children.length > 0
  const stockCount = stockCountMap.get(loc.id) ?? 0
  const colors = getTypeColor(loc.location_type, allTypes)

  return (
    <div
      className={cn(
        'flex items-center gap-2 py-2.5 px-3 border-l-4 rounded-lg bg-card hover:bg-muted transition-colors',
        colors.border,
        DEPTH_INDENT[Math.min(node.depth, DEPTH_INDENT.length - 1)],
      )}
    >
      {/* Expand/collapse toggle */}
      <button
        onClick={onToggle}
        className={cn(
          'flex-none h-6 w-6 flex items-center justify-center rounded transition-colors',
          hasChildren ? 'hover:bg-slate-200 text-muted-foreground' : 'text-transparent cursor-default',
        )}
        disabled={!hasChildren}
      >
        <ChevronRight className={cn(
          'h-4 w-4 transition-transform',
          expanded && 'rotate-90',
        )} />
      </button>

      {/* Icon */}
      <MapPin className="h-4 w-4 flex-none text-muted-foreground" />

      {/* Name + code */}
      <div className="flex-1 min-w-0">
        <span className="font-medium text-sm text-foreground">{loc.name}</span>
        <span className="ml-2 font-mono text-xs text-muted-foreground">{loc.code}</span>
      </div>

      {/* Type badge */}
      <span className={cn(
        'rounded-full px-2 py-0.5 text-[11px] font-semibold border',
        colors.badge,
      )}>
        {loc.location_type}
      </span>

      {/* Stock count */}
      {stockCount > 0 && (
        <span className="rounded-full bg-secondary px-2 py-0.5 text-[11px] font-semibold text-muted-foreground">
          {stockCount} items
        </span>
      )}

      {/* Active toggle */}
      <button
        onClick={onToggleActive}
        className={cn(
          'rounded-full px-2 py-0.5 text-[11px] font-semibold transition-colors',
          loc.is_active
            ? 'bg-emerald-50 text-emerald-700 hover:bg-emerald-100'
            : 'bg-secondary text-muted-foreground hover:bg-slate-200',
        )}
      >
        {loc.is_active ? 'Activa' : 'Inactiva'}
      </button>

      {/* Actions */}
      <button
        onClick={onEdit}
        className="flex-none h-7 w-7 flex items-center justify-center rounded-lg hover:bg-slate-200 text-muted-foreground hover:text-foreground transition-colors"
      >
        <Pencil className="h-3.5 w-3.5" />
      </button>
      <button
        onClick={onDelete}
        className="flex-none h-7 w-7 flex items-center justify-center rounded-lg hover:bg-red-50 text-muted-foreground hover:text-red-600 transition-colors"
      >
        <Trash2 className="h-3.5 w-3.5" />
      </button>
    </div>
  )
}

/* ------------------------------------------------------------------ */
/*  Locations tab content                                             */
/* ------------------------------------------------------------------ */

interface LocationsTabProps {
  warehouseId: string
  stockLocationCounts: Map<string, number>
}

function LocationsTab({ warehouseId, stockLocationCounts }: LocationsTabProps) {
  const { data: locations = [], isLoading } = useLocations(warehouseId)
  const createMutation = useCreateLocation()
  const updateMutation = useUpdateLocation()
  const deleteMutation = useDeleteLocation()

  const [expanded, setExpanded] = useState<Set<string>>(new Set())
  const [showCreateForm, setShowCreateForm] = useState(false)
  const [editingId, setEditingId] = useState<string | null>(null)

  const existingTypes = useMemo(() => [...new Set(locations.map(l => l.location_type))], [locations])
  const tree = useMemo(() => buildTree(locations), [locations])
  const visibleNodes = useMemo(() => flattenTree(tree, expanded), [tree, expanded])

  const toggleExpand = useCallback((id: string) => {
    setExpanded(prev => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }, [])

  const expandAll = useCallback(() => {
    setExpanded(new Set(locations.map(l => l.id)))
  }, [locations])

  const collapseAll = useCallback(() => {
    setExpanded(new Set())
  }, [])

  const handleCreate = (form: typeof EMPTY_FORM) => {
    createMutation.mutate(
      {
        warehouse_id: warehouseId,
        parent_location_id: form.parent_location_id,
        name: form.name.trim(),
        code: form.code.trim(),
        location_type: form.location_type,
        description: form.description.trim() || null,
        sort_order: form.sort_order,
      } satisfies Partial<WarehouseLocation>,
      { onSuccess: () => setShowCreateForm(false) },
    )
  }

  const handleUpdate = (id: string, form: typeof EMPTY_FORM) => {
    updateMutation.mutate(
      {
        id,
        data: {
          parent_location_id: form.parent_location_id,
          name: form.name.trim(),
          code: form.code.trim(),
          location_type: form.location_type,
          description: form.description.trim() || null,
          sort_order: form.sort_order,
        },
      },
      { onSuccess: () => setEditingId(null) },
    )
  }

  const handleDelete = (id: string) => {
    if (!confirm('Eliminar esta ubicacion y todas sus sub-ubicaciones?')) return
    deleteMutation.mutate(id)
  }

  const handleToggleActive = (loc: WarehouseLocation) => {
    updateMutation.mutate({ id: loc.id, data: { is_active: !loc.is_active } })
  }

  if (isLoading) {
    return <div className="p-8 text-center text-muted-foreground">Cargando ubicaciones...</div>
  }

  return (
    <div className="space-y-4">
      {/* Toolbar */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-sm text-muted-foreground">
            {locations.length} ubicacion{locations.length !== 1 ? 'es' : ''}
          </span>
          {locations.length > 0 && (
            <>
              <button
                onClick={expandAll}
                className="text-xs text-primary hover:text-primary font-medium"
              >
                Expandir todo
              </button>
              <span className="text-slate-300">|</span>
              <button
                onClick={collapseAll}
                className="text-xs text-primary hover:text-primary font-medium"
              >
                Colapsar todo
              </button>
            </>
          )}
        </div>
        {!showCreateForm && (
          <button
            onClick={() => setShowCreateForm(true)}
            className="inline-flex items-center gap-1.5 rounded-lg bg-primary px-3 py-1.5 text-xs font-semibold text-white hover:bg-primary/90 transition-colors"
          >
            <Plus className="h-3.5 w-3.5" />
            Nueva ubicacion
          </button>
        )}
      </div>

      {/* Create form (inline) */}
      {showCreateForm && (
        <LocationForm
          initial={EMPTY_FORM}
          locations={locations}
          existingTypes={existingTypes}
          onSubmit={handleCreate}
          onCancel={() => setShowCreateForm(false)}
          submitLabel="Crear ubicacion"
        />
      )}

      {/* Tree */}
      {locations.length === 0 && !showCreateForm ? (
        <div className="py-12 text-center">
          <FolderTree className="h-10 w-10 text-slate-200 mx-auto mb-3" />
          <p className="text-sm text-muted-foreground">No hay ubicaciones definidas para esta bodega</p>
          <button
            onClick={() => setShowCreateForm(true)}
            className="mt-3 inline-flex items-center gap-1.5 rounded-lg bg-primary px-3 py-1.5 text-xs font-semibold text-white hover:bg-primary/90 transition-colors"
          >
            <Plus className="h-3.5 w-3.5" />
            Crear primera ubicacion
          </button>
        </div>
      ) : (
        <div className="space-y-1">
          {visibleNodes.map(node => {
            const loc = node.location
            if (editingId === loc.id) {
              return (
                <LocationForm
                  key={loc.id}
                  initial={{
                    name: loc.name,
                    code: loc.code,
                    location_type: loc.location_type,
                    parent_location_id: loc.parent_location_id,
                    description: loc.description ?? '',
                    sort_order: loc.sort_order,
                  }}
                  locations={locations.filter(l => l.id !== loc.id)}
                  existingTypes={existingTypes}
                  onSubmit={form => handleUpdate(loc.id, form)}
                  onCancel={() => setEditingId(null)}
                  submitLabel="Guardar cambios"
                />
              )
            }
            return (
              <LocationRow
                key={loc.id}
                node={node}
                expanded={expanded.has(loc.id)}
                allTypes={existingTypes}
                onToggle={() => toggleExpand(loc.id)}
                onEdit={() => setEditingId(loc.id)}
                onDelete={() => handleDelete(loc.id)}
                onToggleActive={() => handleToggleActive(loc)}
                stockCountMap={stockLocationCounts}
              />
            )
          })}
        </div>
      )}
    </div>
  )
}

/* ------------------------------------------------------------------ */
/*  Main page                                                         */
/* ------------------------------------------------------------------ */

type Tab = 'inventario' | 'ubicaciones'

export function WarehouseDetailPage() {
  const { id } = useParams<{ id: string }>()
  const { data: warehouses = [] } = useWarehouses()
  const { data: stockLevels = [], isLoading: stockLoading } = useStockLevels(
    id ? { warehouse_id: id } : undefined,
  )
  const { data: productTypes = [] } = useProductTypes()
  const { data: warehouseTypes = [] } = useWarehouseTypes()
  const { data: locations = [] } = useLocations(id)
  const qcApprove = useQCApprove()
  const qcReject = useQCReject()
  const assignLocation = useAssignStockLocation()

  const [activeTab, setActiveTab] = useState<Tab>('inventario')
  const [search, setSearch] = useState('')
  const [typeFilter, setTypeFilter] = useState('')
  const [locationFilter, setLocationFilter] = useState<string>('')

  const warehouse = warehouses.find(w => w.id === id)
  const whTypeMap = Object.fromEntries(warehouseTypes.map(wt => [wt.id, wt]))
  const typeMap = useMemo(
    () => Object.fromEntries(productTypes.map(pt => [pt.id, pt])),
    [productTypes],
  )

  // Build a map of location_id → stock item count for the Locations tab
  const stockLocationCounts = useMemo(() => {
    const m = new Map<string, number>()
    for (const sl of stockLevels) {
      if (sl.location_id) m.set(sl.location_id, (m.get(sl.location_id) ?? 0) + 1)
    }
    return m
  }, [stockLevels])

  // Map of location_id → location for quick lookup
  const locationMap = useMemo(
    () => new Map(locations.map(l => [l.id, l])),
    [locations],
  )

  // Filter rows using the embedded product info from the stock endpoint
  const rows = useMemo(() => {
    return stockLevels
      .filter(sl => {
        const p = sl.product
        if (!p) return true // still show even if product info missing
        if (typeFilter && p.product_type_id !== typeFilter) return false
        if (locationFilter === '__none__' && sl.location_id) return false
        if (locationFilter === '__none__' && !sl.location_id) { /* pass */ }
        else if (locationFilter && locationFilter !== '__none__' && sl.location_id !== locationFilter) return false
        if (search) {
          const q = search.toLowerCase()
          const match =
            p.name.toLowerCase().includes(q) ||
            p.sku.toLowerCase().includes(q) ||
            (p.barcode ?? '').toLowerCase().includes(q)
          if (!match) return false
        }
        return true
      })
      .sort((a, b) => (a.product?.name ?? '').localeCompare(b.product?.name ?? ''))
  }, [stockLevels, typeFilter, locationFilter, search])

  // Types present in this warehouse for filter chips
  const typesInWarehouse = useMemo(() => {
    const ids = new Set<string>()
    for (const sl of stockLevels) {
      if (sl.product?.product_type_id) ids.add(sl.product.product_type_id)
    }
    return productTypes.filter(pt => ids.has(pt.id))
  }, [stockLevels, productTypes])

  if (!warehouse) {
    return (
      <div className="max-w-5xl mx-auto p-6">
        <Link to="/inventario/bodegas" className="inline-flex items-center gap-1 text-sm text-primary hover:text-primary mb-4">
          <ArrowLeft className="h-4 w-4" /> Bodegas
        </Link>
        <div className="py-16 text-center">
          <WarehouseIcon className="h-12 w-12 text-slate-200 mx-auto mb-3" />
          <p className="text-sm text-muted-foreground">Bodega no encontrada</p>
        </div>
      </div>
    )
  }

  const whType = warehouse.warehouse_type_id ? whTypeMap[warehouse.warehouse_type_id] : null

  return (
    <div className="max-w-5xl mx-auto p-6 space-y-6">
      {/* Back link */}
      <Link to="/inventario/bodegas" className="inline-flex items-center gap-1 text-sm text-primary hover:text-primary">
        <ArrowLeft className="h-4 w-4" /> Bodegas
      </Link>

      {/* Header */}
      <div className="bg-card rounded-2xl border border-border  p-6">
        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-2xl font-bold text-foreground">{warehouse.name}</h1>
            <p className="text-sm font-mono text-muted-foreground mt-0.5">{warehouse.code}</p>
          </div>
          <div className="flex items-center gap-2">
            {whType ? (
              <span className="rounded-full px-2.5 py-1 text-xs font-semibold text-white"
                style={{ backgroundColor: whType.color ?? '#6366f1' }}>
                {whType.name}
              </span>
            ) : (
              <span className="rounded-full px-2.5 py-1 text-xs font-semibold bg-secondary text-muted-foreground">
                {warehouse.type}
              </span>
            )}
            <span className={cn(
              'rounded-full px-2.5 py-1 text-xs font-semibold',
              warehouse.is_active ? 'bg-emerald-50 text-emerald-700' : 'bg-secondary text-muted-foreground',
            )}>
              {warehouse.is_active ? 'Activa' : 'Inactiva'}
            </span>
            {warehouse.is_default && (
              <span className="rounded-full px-2.5 py-1 text-xs font-semibold bg-primary/10 text-primary">
                Predeterminada
              </span>
            )}
          </div>
        </div>
        <div className="flex items-center gap-4 mt-4 text-sm text-muted-foreground">
          <span><strong className="text-foreground">{stockLevels.length}</strong> productos en stock</span>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 bg-secondary rounded-xl p-1">
        <button
          onClick={() => setActiveTab('inventario')}
          className={cn(
            'flex-1 inline-flex items-center justify-center gap-2 rounded-lg px-4 py-2 text-sm font-semibold transition-colors',
            activeTab === 'inventario'
              ? 'bg-card text-foreground '
              : 'text-muted-foreground hover:text-foreground',
          )}
        >
          <Package className="h-4 w-4" />
          Inventario
        </button>
        <button
          onClick={() => setActiveTab('ubicaciones')}
          className={cn(
            'flex-1 inline-flex items-center justify-center gap-2 rounded-lg px-4 py-2 text-sm font-semibold transition-colors',
            activeTab === 'ubicaciones'
              ? 'bg-card text-foreground '
              : 'text-muted-foreground hover:text-foreground',
          )}
        >
          <FolderTree className="h-4 w-4" />
          Ubicaciones
        </button>
      </div>

      {/* Tab content */}
      {activeTab === 'inventario' && (
        <>
          {/* Search */}
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <input
              value={search}
              onChange={e => setSearch(e.target.value)}
              placeholder="Buscar por nombre, SKU o codigo de barras..."
              className="w-full pl-9 pr-3 py-2 rounded-xl border border-border text-sm focus:outline-none focus:ring-2 focus:ring-ring"
            />
          </div>

          {/* Type filter chips */}
          {typesInWarehouse.length > 0 && (
            <div className="flex gap-2 flex-wrap">
              <button
                onClick={() => setTypeFilter('')}
                className={cn(
                  'rounded-full px-3 py-1.5 text-xs font-semibold transition-colors',
                  !typeFilter ? 'bg-primary text-white' : 'bg-secondary text-muted-foreground hover:bg-slate-200',
                )}
              >
                Todos
              </button>
              {typesInWarehouse.map(pt => (
                <button
                  key={pt.id}
                  onClick={() => setTypeFilter(typeFilter === pt.id ? '' : pt.id)}
                  className={cn(
                    'rounded-full px-3 py-1.5 text-xs font-semibold transition-colors',
                    typeFilter === pt.id
                      ? 'text-white'
                      : 'bg-secondary text-muted-foreground hover:bg-slate-200',
                  )}
                  style={typeFilter === pt.id ? { backgroundColor: pt.color ?? '#6366f1' } : undefined}
                >
                  {pt.name}
                </button>
              ))}
            </div>
          )}

          {/* Location filter */}
          {locations.length > 0 && (
            <div className="flex gap-2 flex-wrap items-center">
              <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mr-1">Ubicacion:</span>
              <button
                onClick={() => setLocationFilter('')}
                className={cn(
                  'rounded-full px-3 py-1.5 text-xs font-semibold transition-colors',
                  !locationFilter ? 'bg-teal-600 text-white' : 'bg-secondary text-muted-foreground hover:bg-slate-200',
                )}
              >
                Todas
              </button>
              <button
                onClick={() => setLocationFilter(locationFilter === '__none__' ? '' : '__none__')}
                className={cn(
                  'rounded-full px-3 py-1.5 text-xs font-semibold transition-colors',
                  locationFilter === '__none__' ? 'bg-slate-600 text-white' : 'bg-secondary text-muted-foreground hover:bg-slate-200',
                )}
              >
                Sin ubicacion
              </button>
              {locations.filter(l => l.is_active).map(loc => (
                <button
                  key={loc.id}
                  onClick={() => setLocationFilter(locationFilter === loc.id ? '' : loc.id)}
                  className={cn(
                    'rounded-full px-3 py-1.5 text-xs font-semibold transition-colors',
                    locationFilter === loc.id ? 'bg-teal-600 text-white' : 'bg-secondary text-muted-foreground hover:bg-slate-200',
                  )}
                >
                  {loc.name}
                </button>
              ))}
            </div>
          )}

          {/* Stock table */}
          {(() => {
            const showQcCol = rows.some(r => r.qc_status && r.qc_status !== 'approved')
            const headers = ['Producto', 'SKU', 'Tipo', 'Ubicacion', 'En stock', 'Reservado', 'Disponible', 'En transito']
            if (showQcCol) headers.push('QC', 'Acciones QC')

            return (
              <div className="bg-card rounded-2xl border border-border  overflow-hidden">
                {stockLoading ? (
                  <div className="p-8 text-center text-muted-foreground">Cargando inventario...</div>
                ) : rows.length === 0 ? (
                  <div className="p-8 text-center">
                    <Package className="h-10 w-10 text-slate-200 mx-auto mb-3" />
                    <p className="text-sm text-muted-foreground">
                      {stockLevels.length === 0
                        ? 'Esta bodega no tiene productos en stock'
                        : 'Sin resultados para los filtros aplicados'}
                    </p>
                  </div>
                ) : (
                  <table className="w-full text-sm">
                    <thead className="bg-muted border-b border-border">
                      <tr>
                        {headers.map(h => (
                          <th key={h} className="px-4 py-3 text-left text-xs font-semibold text-muted-foreground uppercase tracking-wide">{h}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-50">
                      {rows.map(row => {
                        const p = row.product
                        const pt = p?.product_type_id ? typeMap[p.product_type_id] : null
                        const qty = Number(row.qty_on_hand)
                        const reserved = Number(row.qty_reserved)
                        const inTransit = Number(row.qty_in_transit)
                        return (
                          <tr key={row.id} className="hover:bg-muted">
                            <td className="px-4 py-3 font-medium text-foreground">
                              {p?.name ?? row.product_id.slice(0, 8)}
                            </td>
                            <td className="px-4 py-3 font-mono text-xs text-muted-foreground">
                              {p?.sku ?? '\u2014'}
                            </td>
                            <td className="px-4 py-3">
                              {pt ? (
                                <span className="rounded-full px-2 py-0.5 text-[11px] font-semibold text-white"
                                  style={{ backgroundColor: pt.color ?? '#6366f1' }}>
                                  {pt.name}
                                </span>
                              ) : (
                                <span className="text-xs text-slate-300">{'\u2014'}</span>
                              )}
                            </td>
                            <td className="px-4 py-3">
                              {locations.length > 0 ? (
                                <select
                                  value={row.location_id ?? ''}
                                  onChange={e => {
                                    const newLoc = e.target.value || null
                                    assignLocation.mutate({ levelId: row.id, locationId: newLoc })
                                  }}
                                  className="rounded-lg border border-border px-2 py-1 text-xs focus:ring-2 focus:ring-teal-400 outline-none min-w-[120px]"
                                >
                                  <option value="">— Sin ubicacion —</option>
                                  {locations.filter(l => l.is_active).map(loc => (
                                    <option key={loc.id} value={loc.id}>{loc.code} — {loc.name}</option>
                                  ))}
                                </select>
                              ) : (
                                <span className="text-xs text-slate-300">{'\u2014'}</span>
                              )}
                            </td>
                            <td className="px-4 py-3">
                              <span className="text-muted-foreground text-sm tabular-nums">
                                {qty.toFixed(2)}
                              </span>
                              {p?.unit_of_measure && (
                                <span className="text-xs text-muted-foreground ml-1">{p.unit_of_measure}</span>
                              )}
                            </td>
                            <td className="px-4 py-3">
                              {reserved > 0 ? (
                                <span className="inline-flex items-center rounded-md bg-amber-500/15 text-amber-700 px-2 py-0.5 text-xs font-medium tabular-nums">
                                  {reserved.toFixed(2)}
                                </span>
                              ) : (
                                <span className="text-muted-foreground/40 text-sm tabular-nums">0</span>
                              )}
                            </td>
                            <td className="px-4 py-3">
                              {(() => {
                                const avail = qty - reserved
                                const rp = p?.reorder_point ?? 0
                                return (
                                  <span className={cn(
                                    'font-bold text-sm tabular-nums',
                                    avail < rp ? 'text-destructive' : 'text-foreground',
                                  )}>
                                    {avail.toFixed(2)}
                                  </span>
                                )
                              })()}
                            </td>
                            <td className="px-4 py-3 text-muted-foreground">{inTransit.toFixed(2)}</td>
                            {showQcCol && (
                              <>
                                <td className="px-4 py-3">
                                  {row.qc_status === 'pending_qc' && (
                                    <span className="rounded-full px-2 py-0.5 text-[11px] font-semibold bg-amber-50 text-amber-700 border border-amber-200">
                                      Pendiente QC
                                    </span>
                                  )}
                                  {row.qc_status === 'approved' && (
                                    <span className="rounded-full px-2 py-0.5 text-[11px] font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
                                      Aprobado
                                    </span>
                                  )}
                                  {row.qc_status === 'rejected' && (
                                    <span className="rounded-full px-2 py-0.5 text-[11px] font-semibold bg-red-50 text-red-700 border border-red-200">
                                      Rechazado
                                    </span>
                                  )}
                                  {!row.qc_status && (
                                    <span className="text-xs text-slate-300">{'\u2014'}</span>
                                  )}
                                </td>
                                <td className="px-4 py-3">
                                  {row.qc_status === 'pending_qc' && (
                                    <div className="flex items-center gap-1">
                                      <button
                                        onClick={() => qcApprove.mutate({ product_id: row.product_id, warehouse_id: row.warehouse_id, batch_id: row.batch_id ?? undefined })}
                                        disabled={qcApprove.isPending}
                                        className="rounded-lg px-2 py-1 text-[11px] font-semibold bg-emerald-50 text-emerald-700 hover:bg-emerald-100 border border-emerald-200 transition-colors disabled:opacity-50"
                                      >
                                        Aprobar
                                      </button>
                                      <button
                                        onClick={() => qcReject.mutate({ product_id: row.product_id, warehouse_id: row.warehouse_id, batch_id: row.batch_id ?? undefined })}
                                        disabled={qcReject.isPending}
                                        className="rounded-lg px-2 py-1 text-[11px] font-semibold bg-red-50 text-red-700 hover:bg-red-100 border border-red-200 transition-colors disabled:opacity-50"
                                      >
                                        Rechazar
                                      </button>
                                    </div>
                                  )}
                                </td>
                              </>
                            )}
                          </tr>
                        )
                      })}
                    </tbody>
                  </table>
                )}
              </div>
            )
          })()}
        </>
      )}

      {activeTab === 'ubicaciones' && id && (
        <div className="bg-card rounded-2xl border border-border  p-6">
          <LocationsTab warehouseId={id} stockLocationCounts={stockLocationCounts} />
        </div>
      )}
    </div>
  )
}
