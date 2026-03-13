import { useState, useDeferredValue } from 'react'
import { ArrowDownCircle, ArrowUpCircle, ArrowLeftRight, RotateCcw, Trash2, Plus, Minus, AlertTriangle, Factory, Search } from 'lucide-react'
import { cn } from '@/lib/utils'
import {
  useMovements, useWarehouses, useProducts, useStockLevels,
  useReceiveStock, useIssueStock, useTransferStock,
  useAdjustInStock, useAdjustOutStock,
  useReturnStock, useWasteStock, useMovementTypes, useLocations,
  useInitiateTransfer, useCompleteTransfer, usePendingTransfers,
} from '@/hooks/useInventory'
import { useUserLookup } from '@/hooks/useUserLookup'
import { VariantPicker } from '@/components/inventory/VariantPicker'
import type { MovementType } from '@/types/inventory'

const TYPE_CONFIG: Record<string, { label: string; icon: React.ElementType; color: string }> = {
  purchase: { label: 'Entrada', icon: ArrowDownCircle, color: 'text-emerald-600 bg-emerald-50' },
  sale: { label: 'Salida manual', icon: ArrowUpCircle, color: 'text-red-600 bg-red-50' },
  transfer: { label: 'Traslado', icon: ArrowLeftRight, color: 'text-indigo-600 bg-indigo-50' },
  adjustment_in: { label: 'Ajuste +', icon: Plus, color: 'text-blue-600 bg-blue-50' },
  adjustment_out: { label: 'Ajuste -', icon: Minus, color: 'text-orange-600 bg-orange-50' },
  return: { label: 'Devolución', icon: RotateCcw, color: 'text-purple-600 bg-purple-50' },
  waste: { label: 'Merma', icon: Trash2, color: 'text-slate-500 bg-slate-100' },
  production_in: { label: 'Prod. terminado', icon: Factory, color: 'text-teal-600 bg-teal-50' },
  production_out: { label: 'Consumo prod.', icon: Factory, color: 'text-amber-600 bg-amber-50' },
}

type ModalType = 'purchase' | 'sale' | 'transfer' | 'adjust_in' | 'adjust_out' | 'return' | 'waste'

const MODAL_TABS: { key: ModalType; label: string; color: string }[] = [
  { key: 'purchase', label: 'Entrada', color: 'bg-emerald-600' },
  { key: 'sale', label: 'Salida manual', color: 'bg-red-600' },
  { key: 'transfer', label: 'Traslado', color: 'bg-indigo-600' },
  { key: 'adjust_in', label: 'Ajuste +', color: 'bg-blue-600' },
  { key: 'adjust_out', label: 'Ajuste -', color: 'bg-orange-600' },
  { key: 'return', label: 'Devolución', color: 'bg-purple-600' },
  { key: 'waste', label: 'Merma', color: 'bg-slate-600' },
]

const DIR_ICON: Record<string, React.ElementType> = {
  in: ArrowDownCircle,
  out: ArrowUpCircle,
  internal: ArrowLeftRight,
  neutral: RotateCcw,
}

const OUTBOUND_TYPES: ModalType[] = ['sale', 'transfer', 'adjust_out', 'return', 'waste']

function RegisterMovementModal({ onClose }: { onClose: () => void }) {
  const { data: productsData } = useProducts()
  const { data: stockLevels = [] } = useStockLevels()
  const { data: warehouses = [] } = useWarehouses()
  const receive = useReceiveStock()
  const issue = useIssueStock()
  const transfer = useTransferStock()
  const initiateTransfer = useInitiateTransfer()
  const adjustIn = useAdjustInStock()
  const adjustOut = useAdjustOutStock()
  const returnStock = useReturnStock()
  const waste = useWasteStock()

  const [type, setType] = useState<ModalType>('purchase')
  const [error, setError] = useState('')
  const [form, setForm] = useState({
    product_id: '', variant_id: '', warehouse_id: '', from_warehouse_id: '', to_warehouse_id: '',
    quantity: '', unit_cost: '', reference: '', reason: '', notes: '', location_id: '',
  })

  // Load locations for the selected warehouse (for receive)
  const { data: warehouseLocations = [] } = useLocations(form.warehouse_id || undefined)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError('')
    try {
      const vid = form.variant_id || undefined
      if (type === 'purchase') {
        await receive.mutateAsync({
          product_id: form.product_id,
          warehouse_id: form.warehouse_id,
          quantity: form.quantity,
          unit_cost: form.unit_cost || undefined,
          reference: form.reference || undefined,
          variant_id: vid,
          location_id: form.location_id || undefined,
        })
      } else if (type === 'sale') {
        await issue.mutateAsync({
          product_id: form.product_id,
          warehouse_id: form.warehouse_id,
          quantity: form.quantity,
          reference: form.reference || undefined,
          variant_id: vid,
        })
      } else if (type === 'transfer') {
        await initiateTransfer.mutateAsync({
          product_id: form.product_id,
          from_warehouse_id: form.from_warehouse_id,
          to_warehouse_id: form.to_warehouse_id,
          quantity: Number(form.quantity),
          variant_id: vid,
          notes: form.notes || undefined,
        })
      } else if (type === 'adjust_in') {
        await adjustIn.mutateAsync({
          product_id: form.product_id,
          warehouse_id: form.warehouse_id,
          quantity: form.quantity,
          reason: form.reason || undefined,
          variant_id: vid,
        })
      } else if (type === 'adjust_out') {
        await adjustOut.mutateAsync({
          product_id: form.product_id,
          warehouse_id: form.warehouse_id,
          quantity: form.quantity,
          reason: form.reason || undefined,
          variant_id: vid,
        })
      } else if (type === 'return') {
        await returnStock.mutateAsync({
          product_id: form.product_id,
          warehouse_id: form.warehouse_id,
          quantity: form.quantity,
          reference: form.reference || undefined,
          notes: form.notes || undefined,
          variant_id: vid,
        })
      } else if (type === 'waste') {
        await waste.mutateAsync({
          product_id: form.product_id,
          warehouse_id: form.warehouse_id,
          quantity: form.quantity,
          reason: form.reason || undefined,
          variant_id: vid,
        })
      }
      onClose()
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Error al registrar movimiento')
    }
  }

  const isPending = receive.isPending || issue.isPending || transfer.isPending || initiateTransfer.isPending
    || adjustIn.isPending || adjustOut.isPending || returnStock.isPending || waste.isPending

  const needsWarehouse = type !== 'transfer'
  const needsTransferWarehouses = type === 'transfer'
  const needsUnitCost = type === 'purchase'
  const needsReference = type === 'purchase' || type === 'sale' || type === 'return'
  const needsReason = type === 'adjust_in' || type === 'adjust_out' || type === 'waste'
  const needsNotes = type === 'return' || type === 'transfer'

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 backdrop-blur-sm">
      <div className="w-full max-w-lg bg-white rounded-3xl shadow-2xl p-6">
        <h2 className="text-lg font-bold text-slate-900 mb-4">Registrar Movimiento</h2>
        <form onSubmit={handleSubmit} className="space-y-3">
          {/* Type selector */}
          <div className="flex gap-1.5 flex-wrap">
            {MODAL_TABS.map(t => (
              <button
                key={t.key}
                type="button"
                onClick={() => { setType(t.key); setForm(f => ({ ...f, product_id: '', variant_id: '' })) }}
                className={cn(
                  'rounded-xl px-3 py-1.5 text-xs font-semibold transition-colors',
                  type === t.key ? `${t.color} text-white` : 'bg-slate-100 text-slate-600 hover:bg-slate-200',
                )}
              >
                {t.label}
              </button>
            ))}
          </div>

          {/* Hint for sale type */}
          {type === 'sale' && (
            <div className="flex items-start gap-2 rounded-xl bg-amber-50 border border-amber-200 px-3 py-2">
              <AlertTriangle className="h-4 w-4 text-amber-500 flex-shrink-0 mt-0.5" />
              <p className="text-xs text-amber-700">Salida manual: uso interno, muestras, donaciones, etc. Las ventas se gestionan desde <strong>Órdenes de Venta</strong>.</p>
            </div>
          )}

          {/* Product — outbound movements only show products with stock > 0 */}
          <select required value={form.product_id} onChange={e => setForm(f => ({ ...f, product_id: e.target.value, variant_id: '' }))}
            className="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400">
            <option value="">Seleccionar producto *</option>
            {(() => {
              const isOutbound = OUTBOUND_TYPES.includes(type)
              if (!isOutbound) {
                return productsData?.items?.map(p => <option key={p.id} value={p.id}>{p.name} ({p.sku})</option>)
              }
              const productsWithStock = new Map<string, number>()
              for (const sl of stockLevels) {
                const qty = Number(sl.qty_on_hand) - Number(sl.qty_reserved)
                productsWithStock.set(sl.product_id, (productsWithStock.get(sl.product_id) ?? 0) + qty)
              }
              return productsData?.items
                ?.filter(p => (productsWithStock.get(p.id) ?? 0) > 0)
                .map(p => {
                  const avail = productsWithStock.get(p.id) ?? 0
                  return <option key={p.id} value={p.id}>{p.name} ({p.sku}) — Stock: {avail.toFixed(2)}</option>
                })
            })()}
          </select>

          <VariantPicker
            productId={form.product_id || undefined}
            value={form.variant_id}
            onChange={v => setForm(f => ({ ...f, variant_id: v }))}
            className="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400"
          />

          {/* Single warehouse */}
          {needsWarehouse && (
            <select required value={form.warehouse_id} onChange={e => setForm(f => ({ ...f, warehouse_id: e.target.value, location_id: '' }))}
              className="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400">
              <option value="">Bodega *</option>
              {warehouses.map(w => <option key={w.id} value={w.id}>{w.name}</option>)}
            </select>
          )}

          {/* Location picker (for receive/purchase) */}
          {type === 'purchase' && form.warehouse_id && warehouseLocations.length > 0 && (
            <select value={form.location_id} onChange={e => setForm(f => ({ ...f, location_id: e.target.value }))}
              className="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-teal-400">
              <option value="">Ubicacion (opcional)</option>
              {warehouseLocations.filter(l => l.is_active).map(l => (
                <option key={l.id} value={l.id}>{l.code} — {l.name}</option>
              ))}
            </select>
          )}

          {/* Transfer warehouses */}
          {needsTransferWarehouses && (
            <>
              <select required value={form.from_warehouse_id} onChange={e => setForm(f => ({ ...f, from_warehouse_id: e.target.value }))}
                className="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400">
                <option value="">Origen *</option>
                {warehouses.map(w => <option key={w.id} value={w.id}>{w.name}</option>)}
              </select>
              <select required value={form.to_warehouse_id} onChange={e => setForm(f => ({ ...f, to_warehouse_id: e.target.value }))}
                className="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400">
                <option value="">Destino *</option>
                {warehouses.map(w => <option key={w.id} value={w.id}>{w.name}</option>)}
              </select>
            </>
          )}

          {/* Quantity */}
          <input required type="number" step="0.01" min="0.01" value={form.quantity}
            onChange={e => setForm(f => ({ ...f, quantity: e.target.value }))}
            placeholder={type === 'adjust_in' ? 'Cantidad a agregar *' : type === 'adjust_out' ? 'Cantidad a retirar *' : 'Cantidad *'}
            className="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400" />

          {/* Unit cost (purchase only) */}
          {needsUnitCost && (
            <input type="number" step="0.01" value={form.unit_cost}
              onChange={e => setForm(f => ({ ...f, unit_cost: e.target.value }))}
              placeholder="Costo unitario"
              className="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400" />
          )}

          {/* Reference */}
          {needsReference && (
            <input value={form.reference} onChange={e => setForm(f => ({ ...f, reference: e.target.value }))}
              placeholder="Referencia (opcional)"
              className="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400" />
          )}

          {/* Reason (adjust/waste) */}
          {needsReason && (
            <input value={form.reason} onChange={e => setForm(f => ({ ...f, reason: e.target.value }))}
              placeholder={type === 'waste' ? 'Motivo de merma (opcional)' : type === 'adjust_in' ? 'Razón del ingreso (opcional)' : 'Razón del retiro (opcional)'}
              className="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400" />
          )}

          {/* Notes (return) */}
          {needsNotes && (
            <input value={form.notes} onChange={e => setForm(f => ({ ...f, notes: e.target.value }))}
              placeholder="Notas (opcional)"
              className="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400" />
          )}

          {/* Error */}
          {error && (
            <div className="flex items-start gap-2 rounded-xl bg-red-50 border border-red-200 px-3 py-2">
              <AlertTriangle className="h-4 w-4 text-red-500 flex-shrink-0 mt-0.5" />
              <p className="text-sm text-red-700 whitespace-pre-line">{error}</p>
            </div>
          )}

          <div className="flex gap-3 pt-2">
            <button type="button" onClick={onClose} className="flex-1 rounded-xl border border-slate-200 px-4 py-2 text-sm text-slate-600 hover:bg-slate-50">Cancelar</button>
            <button type="submit" disabled={isPending} className="flex-1 rounded-xl bg-indigo-600 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-700 disabled:opacity-60">
              {isPending ? 'Registrando…' : 'Registrar'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

function PendingTransfersSection({
  productMap,
  warehouseMap,
}: {
  productMap: Record<string, string>
  warehouseMap: Record<string, string>
}) {
  const { data: pendingData, isLoading } = usePendingTransfers()
  const completeTransfer = useCompleteTransfer()
  const [errorId, setErrorId] = useState<string | null>(null)

  const items = pendingData?.items ?? []
  if (isLoading) return null
  if (!items.length) return null

  return (
    <div className="bg-white rounded-2xl border border-amber-200 shadow-sm overflow-hidden">
      <div className="px-5 py-3 bg-amber-50 border-b border-amber-200">
        <h2 className="text-sm font-bold text-amber-800 flex items-center gap-2">
          <ArrowLeftRight className="h-4 w-4" />
          Transferencias en tránsito ({items.length})
        </h2>
      </div>
      {errorId && (
        <div className="px-5 py-2 bg-red-50 border-b border-red-200 text-xs text-red-700">
          Error al confirmar recepción. El movimiento puede haber sido completado previamente.
        </div>
      )}
      <div className="divide-y divide-slate-50">
        {items.map(mv => (
          <div key={mv.id} className="flex items-center justify-between px-5 py-3 hover:bg-slate-50">
            <div className="flex items-center gap-4">
              <span className="inline-flex items-center gap-1 rounded-full bg-amber-50 border border-amber-200 px-2 py-0.5 text-[11px] font-semibold text-amber-700">
                En tránsito
              </span>
              <span className="text-sm font-medium text-slate-700">
                {productMap[mv.product_id] ?? mv.product_id.slice(0, 8)}
              </span>
              <span className="text-sm font-bold text-slate-900">{Number(mv.quantity).toFixed(2)}</span>
              <div className="flex items-center gap-1 text-xs text-slate-500">
                {mv.from_warehouse_id && (
                  <span className="inline-flex items-center gap-0.5 rounded bg-red-50 border border-red-100 px-1.5 py-0.5 text-red-600">
                    <ArrowUpCircle className="h-2.5 w-2.5" />
                    {warehouseMap[mv.from_warehouse_id] ?? '?'}
                  </span>
                )}
                <ArrowLeftRight className="h-3 w-3 text-slate-400" />
                {mv.to_warehouse_id && (
                  <span className="inline-flex items-center gap-0.5 rounded bg-emerald-50 border border-emerald-100 px-1.5 py-0.5 text-emerald-600">
                    <ArrowDownCircle className="h-2.5 w-2.5" />
                    {warehouseMap[mv.to_warehouse_id] ?? '?'}
                  </span>
                )}
              </div>
              <span className="text-xs text-slate-400">
                {new Date(mv.created_at).toLocaleDateString('es')}
              </span>
            </div>
            <button
              onClick={() => {
                setErrorId(null)
                completeTransfer.mutate(mv.id, {
                  onError: () => setErrorId(mv.id),
                })
              }}
              disabled={completeTransfer.isPending}
              className="flex items-center gap-1.5 rounded-xl bg-emerald-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-emerald-700 disabled:opacity-50"
            >
              <ArrowDownCircle className="h-3.5 w-3.5" />
              {completeTransfer.isPending ? 'Confirmando...' : 'Confirmar recepción'}
            </button>
          </div>
        ))}
      </div>
    </div>
  )
}

export function MovementsPage() {
  const [showCreate, setShowCreate] = useState(false)
  const [typeFilter, setTypeFilter] = useState('')
  const [searchText, setSearchText] = useState('')
  const deferredSearch = useDeferredValue(searchText)
  const { data, isLoading } = useMovements({ movement_type: typeFilter || undefined, search: deferredSearch || undefined })
  const { data: productsData } = useProducts()
  const { data: warehouses = [] } = useWarehouses()
  const { data: dynamicTypes = [] } = useMovementTypes()
  const productMap = Object.fromEntries((productsData?.items ?? []).map(p => [p.id, p.name]))
  const warehouseMap = Object.fromEntries(warehouses.map(w => [w.id, w.name]))
  const dynTypeMap = Object.fromEntries(dynamicTypes.map(t => [t.id, t]))
  const { resolve } = useUserLookup(data?.items.map(m => m.performed_by) ?? [])

  return (
    <div className="max-w-5xl mx-auto p-6 space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-slate-900">Movimientos</h1>
        <button onClick={() => setShowCreate(true)}
          className="flex items-center gap-2 rounded-2xl bg-indigo-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-indigo-700 shadow-sm">
          <Plus className="h-4 w-4" /> Nuevo movimiento
        </button>
      </div>

      {/* Search */}
      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
        <input
          type="text"
          value={searchText}
          onChange={e => setSearchText(e.target.value)}
          placeholder="Buscar por producto, referencia, notas, lote…"
          className="w-full rounded-xl border border-slate-200 pl-9 pr-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400"
        />
      </div>

      {/* Type filter */}
      <div className="flex gap-2 flex-wrap">
        {['', ...Object.keys(TYPE_CONFIG)].map(t => (
          <button
            key={t || 'all'}
            onClick={() => setTypeFilter(t)}
            className={cn(
              'rounded-full px-3 py-1.5 text-xs font-semibold transition-colors',
              typeFilter === t ? 'bg-indigo-600 text-white' : 'bg-slate-100 text-slate-600 hover:bg-slate-200',
            )}
          >
            {t ? TYPE_CONFIG[t]?.label : 'Todos'}
          </button>
        ))}
      </div>

      {/* Pending transfers */}
      <PendingTransfersSection productMap={productMap} warehouseMap={warehouseMap} />

      {/* Table */}
      <div className="bg-white rounded-2xl border border-slate-100 shadow-sm overflow-hidden">
        {isLoading ? (
          <div className="p-8 text-center text-slate-400">Cargando…</div>
        ) : !data?.items?.length ? (
          <div className="p-8 text-center text-slate-400">Sin movimientos</div>
        ) : (<>
          {/* Mobile cards */}
          <div className="space-y-3 p-4 md:hidden">
            {data.items.map(mv => {
              const dynType = mv.movement_type_id ? dynTypeMap[mv.movement_type_id] : null
              const cfg = TYPE_CONFIG[mv.movement_type as MovementType]
              const Icon = dynType ? (DIR_ICON[dynType.direction] ?? ArrowLeftRight) : (cfg?.icon ?? ArrowLeftRight)
              const label = dynType?.name ?? cfg?.label ?? mv.movement_type
              return (
                <div key={mv.id} className="rounded-xl border border-slate-200 bg-white p-4 space-y-2">
                  <div className="flex items-center justify-between">
                    {dynType ? (
                      <span className="flex items-center gap-1.5 rounded-full px-2 py-0.5 text-xs font-semibold text-white w-fit"
                        style={{ backgroundColor: dynType.color ?? '#6366f1' }}>
                        <Icon className="h-3 w-3" />
                        {label}
                      </span>
                    ) : (
                      <span className={cn('flex items-center gap-1.5 rounded-full px-2 py-0.5 text-xs font-semibold w-fit', cfg?.color ?? 'bg-slate-100 text-slate-600')}>
                        <Icon className="h-3 w-3" />
                        {label}
                      </span>
                    )}
                    <span className="text-xs text-slate-400">{new Date(mv.created_at).toLocaleDateString('es')}</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium text-slate-700">{productMap[mv.product_id] ?? mv.product_id.slice(0, 8) + '…'}</span>
                    <span className="text-sm font-bold text-slate-900">{Number(mv.quantity).toFixed(2)}</span>
                  </div>
                  {/* Warehouse origin/destination */}
                  {(mv.from_warehouse_id || mv.to_warehouse_id) && (
                    <div className="flex items-center gap-1 text-xs text-slate-500">
                      {mv.from_warehouse_id && (
                        <span className="inline-flex items-center gap-0.5 rounded bg-red-50 border border-red-100 px-1.5 py-0.5 text-red-600">
                          <ArrowUpCircle className="h-2.5 w-2.5" />
                          {warehouseMap[mv.from_warehouse_id] ?? mv.from_warehouse_id.slice(0, 8)}
                        </span>
                      )}
                      {mv.from_warehouse_id && mv.to_warehouse_id && (
                        <ArrowLeftRight className="h-3 w-3 text-slate-400" />
                      )}
                      {mv.to_warehouse_id && (
                        <span className="inline-flex items-center gap-0.5 rounded bg-emerald-50 border border-emerald-100 px-1.5 py-0.5 text-emerald-600">
                          <ArrowDownCircle className="h-2.5 w-2.5" />
                          {warehouseMap[mv.to_warehouse_id] ?? mv.to_warehouse_id.slice(0, 8)}
                        </span>
                      )}
                    </div>
                  )}
                  <div className="flex items-center justify-between text-xs text-slate-500">
                    <span>{mv.reference ?? mv.notes ?? '\u2014'}</span>
                    <span>{resolve(mv.performed_by)}</span>
                  </div>
                </div>
              )
            })}
          </div>
          {/* Desktop table */}
          <div className="hidden md:block overflow-x-auto">
          <table className="w-full text-sm min-w-[800px]">
            <thead className="bg-slate-50 border-b border-slate-100">
              <tr>
                {['Tipo', 'Producto', 'Cantidad', 'Origen', 'Destino', 'Referencia', 'Fecha', 'Realizado por'].map(h => (
                  <th key={h} className="px-4 py-3 text-left text-xs font-semibold text-slate-400 uppercase tracking-wide">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-50">
              {data.items.map(mv => {
                const dynType = mv.movement_type_id ? dynTypeMap[mv.movement_type_id] : null
                const cfg = TYPE_CONFIG[mv.movement_type as MovementType]
                const Icon = dynType ? (DIR_ICON[dynType.direction] ?? ArrowLeftRight) : (cfg?.icon ?? ArrowLeftRight)
                const label = dynType?.name ?? cfg?.label ?? mv.movement_type
                return (
                  <tr key={mv.id} className="hover:bg-slate-50">
                    <td className="px-4 py-3">
                      {dynType ? (
                        <span className="flex items-center gap-1.5 rounded-full px-2 py-0.5 text-xs font-semibold text-white w-fit"
                          style={{ backgroundColor: dynType.color ?? '#6366f1' }}>
                          <Icon className="h-3 w-3" />
                          {label}
                        </span>
                      ) : (
                        <span className={cn('flex items-center gap-1.5 rounded-full px-2 py-0.5 text-xs font-semibold w-fit', cfg?.color ?? 'bg-slate-100 text-slate-600')}>
                          <Icon className="h-3 w-3" />
                          {label}
                        </span>
                      )}
                    </td>
                    <td className="px-4 py-3 font-medium text-slate-700">
                      {productMap[mv.product_id] ?? mv.product_id.slice(0, 8) + '…'}
                    </td>
                    <td className="px-4 py-3 font-bold text-slate-900">{Number(mv.quantity).toFixed(2)}</td>
                    <td className="px-4 py-3">
                      {mv.from_warehouse_id ? (
                        <span className="inline-flex items-center gap-1 rounded-full bg-red-50 px-2 py-0.5 text-[11px] font-medium text-red-700">
                          <ArrowUpCircle className="h-3 w-3" />
                          {warehouseMap[mv.from_warehouse_id] ?? mv.from_warehouse_id.slice(0, 8)}
                        </span>
                      ) : (
                        <span className="text-xs text-slate-300">{'\u2014'}</span>
                      )}
                    </td>
                    <td className="px-4 py-3">
                      {mv.to_warehouse_id ? (
                        <span className="inline-flex items-center gap-1 rounded-full bg-emerald-50 px-2 py-0.5 text-[11px] font-medium text-emerald-700">
                          <ArrowDownCircle className="h-3 w-3" />
                          {warehouseMap[mv.to_warehouse_id] ?? mv.to_warehouse_id.slice(0, 8)}
                        </span>
                      ) : (
                        <span className="text-xs text-slate-300">{'\u2014'}</span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-slate-500 text-xs">{mv.reference ?? mv.notes ?? '\u2014'}</td>
                    <td className="px-4 py-3 text-slate-400 text-xs">
                      {new Date(mv.created_at).toLocaleDateString('es')}
                    </td>
                    <td className="px-4 py-3 text-slate-400 text-xs">{resolve(mv.performed_by)}</td>
                  </tr>
                )
              })}
            </tbody>
          </table>
          </div>
        </>)}
      </div>

      {showCreate && <RegisterMovementModal onClose={() => setShowCreate(false)} />}
    </div>
  )
}
