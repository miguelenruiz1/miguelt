import { useState, useMemo, useEffect } from 'react'
import { useFormValidation } from '@/hooks/useFormValidation'
import { useNavigate, useLocation } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { Plus, ShoppingCart, GitMerge, X, Check, AlertCircle } from 'lucide-react'
import { cn } from '@/lib/utils'
import {
  usePurchaseOrders,
  useCreatePO,
  useReceivePO,
  useSuppliers,
  useProducts,
  useWarehouses,
  useConsolidatePOs,
  useConsolidationCandidates,
} from '@/hooks/useInventory'
import { inventoryPricingApi } from '@/lib/inventory-api'

function CostHistoryHint({ productId }: { productId: string }) {
  const { data } = useQuery({
    queryKey: ['inventory', 'product-pricing', productId],
    queryFn: () => inventoryPricingApi.getProductPricing(productId),
    enabled: !!productId,
    staleTime: 30_000,
  })
  if (!data || !data.last_purchase_cost) return null
  return (
    <div className="text-xs text-muted-foreground mt-1 p-2 bg-amber-50 rounded col-span-full">
      Última compra: <span className="font-medium">${Number(data.last_purchase_cost).toLocaleString('es-CO')}{data.last_purchase_supplier ? ` — ${data.last_purchase_supplier}` : ''}</span>
      {data.suggested_sale_price != null && <span className="ml-2">| Precio sugerido: <span className="font-medium text-green-700">${Number(data.suggested_sale_price).toLocaleString('es-CO')}</span></span>}
    </div>
  )
}
import { useAuthStore } from '@/store/auth'
import { useUserLookup } from '@/hooks/useUserLookup'
import { VariantPicker } from '@/components/inventory/VariantPicker'
import type { PurchaseOrder, POStatus, ConsolidationCandidate, ConsolidationResult } from '@/types/inventory'

const STATUS_CONFIG: Record<POStatus, { label: string; color: string; icon?: typeof GitMerge }> = {
  draft: { label: 'Borrador', color: 'bg-secondary text-muted-foreground' },
  pending_approval: { label: 'Pend. Aprobación', color: 'bg-orange-50 text-orange-700' },
  approved: { label: 'Aprobada', color: 'bg-indigo-50 text-indigo-700' },
  sent: { label: 'Enviada', color: 'bg-blue-50 text-blue-700' },
  confirmed: { label: 'Confirmada', color: 'bg-cyan-50 text-cyan-700' },
  partial: { label: 'Parcial', color: 'bg-amber-50 text-amber-700' },
  received: { label: 'Recibida', color: 'bg-emerald-50 text-emerald-700' },
  canceled: { label: 'Cancelada', color: 'bg-red-50 text-red-600' },
  consolidated: { label: 'Consolidada', color: 'bg-secondary text-foreground', icon: GitMerge },
}

interface POLine {
  product_id: string
  variant_id: string
  qty_ordered: string
  unit_cost: string
}

function CreatePOModal({ onClose }: { onClose: () => void }) {
  const { data: suppliers = [] } = useSuppliers()
  const { data: productsData } = useProducts()
  const { data: warehouses = [] } = useWarehouses()
  const create = useCreatePO()

  const [form, setForm] = useState({ supplier_id: '', warehouse_id: '', expected_date: '', notes: '' })
  const [lines, setLines] = useState<POLine[]>([{ product_id: '', variant_id: '', qty_ordered: '1', unit_cost: '0' }])

  function addLine() {
    setLines((l) => [...l, { product_id: '', variant_id: '', qty_ordered: '1', unit_cost: '0' }])
  }
  function removeLine(i: number) {
    setLines((l) => l.filter((_, idx) => idx !== i))
  }
  function updateLine(i: number, key: keyof POLine, value: string) {
    setLines((l) => l.map((line, idx) => idx === i ? { ...line, [key]: value } : line))
  }

  const { formRef, handleSubmit: validateAndSubmit } = useFormValidation(doSubmit)

  async function doSubmit() {
    await create.mutateAsync({
      ...form,
      lines: lines.map((l) => ({ product_id: l.product_id, variant_id: l.variant_id || null, qty_ordered: l.qty_ordered, unit_cost: l.unit_cost })),
    })
    onClose()
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 backdrop-blur-sm">
      <div className="w-full max-w-lg bg-card rounded-3xl shadow-2xl p-6 max-h-[90vh] overflow-y-auto">
        <h2 className="text-lg font-bold text-foreground mb-4">Nueva Orden de Compra</h2>
        <form ref={formRef} onSubmit={validateAndSubmit} className="space-y-3" noValidate>
          <select required value={form.supplier_id} onChange={(e) => setForm((f) => ({ ...f, supplier_id: e.target.value }))}
            className="w-full rounded-xl border border-border px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring">
            <option value="">Proveedor *</option>
            {suppliers.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
          </select>
          <select required value={form.warehouse_id} onChange={(e) => setForm((f) => ({ ...f, warehouse_id: e.target.value }))}
            className="w-full rounded-xl border border-border px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring">
            <option value="">Bodega destino *</option>
            {warehouses.map((w) => <option key={w.id} value={w.id}>{w.name}</option>)}
          </select>
          <input type="date" value={form.expected_date} onChange={(e) => setForm((f) => ({ ...f, expected_date: e.target.value }))}
            className="w-full rounded-xl border border-border px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring" />
          <textarea value={form.notes} onChange={(e) => setForm((f) => ({ ...f, notes: e.target.value }))}
            placeholder="Notas" rows={2}
            className="w-full rounded-xl border border-border px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring resize-none" />

          {/* Lines */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <p className="text-xs font-bold text-muted-foreground uppercase tracking-wide">Lineas</p>
              <button type="button" onClick={addLine} className="text-xs text-primary hover:text-primary font-semibold">+ Linea</button>
            </div>
            {lines.map((line, i) => (
              <div key={i}>
                <div className="flex gap-2 items-center">
                  <select required value={line.product_id} onChange={(e) => setLines(l => l.map((ln, idx) => idx === i ? { ...ln, product_id: e.target.value, variant_id: '' } : ln))}
                    className="flex-1 rounded-xl border border-border px-3 py-2 text-xs focus:outline-none focus:ring-2 focus:ring-ring">
                    <option value="">Producto</option>
                    {productsData?.items?.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
                  </select>
                  <VariantPicker
                    productId={line.product_id || undefined}
                    value={line.variant_id}
                    onChange={v => updateLine(i, 'variant_id', v)}
                  />
                  <input type="number" min="0.01" step="0.01" required value={line.qty_ordered}
                    onChange={(e) => updateLine(i, 'qty_ordered', e.target.value)}
                    placeholder="Qty" className="w-16 rounded-xl border border-border px-2 py-2 text-xs focus:outline-none focus:ring-2 focus:ring-ring" />
                  <input type="number" min="0.01" step="0.01" required value={line.unit_cost}
                    onChange={(e) => updateLine(i, 'unit_cost', e.target.value)}
                    placeholder="Costo *" className="w-20 rounded-xl border border-border px-2 py-2 text-xs focus:outline-none focus:ring-2 focus:ring-ring" />
                  {lines.length > 1 && (
                    <button type="button" onClick={() => removeLine(i)} className="text-muted-foreground hover:text-red-500 font-bold text-lg leading-none">&times;</button>
                  )}
                </div>
                {line.product_id && <CostHistoryHint productId={line.product_id} />}
              </div>
            ))}
          </div>

          <div className="flex gap-3 pt-2">
            <button type="button" onClick={onClose} className="flex-1 rounded-xl border border-border px-4 py-2 text-sm text-muted-foreground hover:bg-muted">Cancelar</button>
            <button type="submit" disabled={create.isPending} className="flex-1 rounded-xl bg-primary px-4 py-2 text-sm font-semibold text-white hover:bg-primary/90 disabled:opacity-60">
              {create.isPending ? 'Creando...' : 'Crear OC'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

/* ──────────────── Consolidation Preview Modal (2-step) ──────────────── */

function ConsolidatePreviewModal({
  selectedPOs,
  supplierMap,
  productMap,
  onClose,
}: {
  selectedPOs: PurchaseOrder[]
  supplierMap: Record<string, string>
  productMap: Record<string, string>
  onClose: (result?: ConsolidationResult) => void
}) {
  const consolidate = useConsolidatePOs()
  const [result, setResult] = useState<ConsolidationResult | null>(null)
  const navigate = useNavigate()

  const totalLines = selectedPOs.reduce((sum, po) => sum + (po.lines?.length ?? 0), 0)
  const totalValue = selectedPOs.reduce(
    (sum, po) => sum + (po.lines ?? []).reduce((ls, l) => ls + Number(l.line_total), 0),
    0,
  )

  // Detect lines with the same product (will be merged)
  const productLineCounts = useMemo(() => {
    const counts: Record<string, { name: string; count: number; totalQty: number }> = {}
    for (const po of selectedPOs) {
      for (const line of po.lines ?? []) {
        const existing = counts[line.product_id]
        if (existing) {
          existing.count += 1
          existing.totalQty += Number(line.qty_ordered)
        } else {
          counts[line.product_id] = {
            name: productMap[line.product_id] ?? line.product_id.slice(0, 8),
            count: 1,
            totalQty: Number(line.qty_ordered),
          }
        }
      }
    }
    return counts
  }, [selectedPOs, productMap])

  const mergeableLines = Object.values(productLineCounts).filter((c) => c.count > 1)

  async function handleConsolidate() {
    const ids = selectedPOs.map((po) => po.id)
    const res = await consolidate.mutateAsync(ids)
    setResult(res)
  }

  if (result) {
    return (
      <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 backdrop-blur-sm">
        <div className="w-full max-w-md bg-card rounded-3xl shadow-2xl p-6">
          <div className="flex items-center gap-2 mb-4">
            <div className="h-10 w-10 rounded-full bg-emerald-100 flex items-center justify-center">
              <Check className="h-5 w-5 text-emerald-600" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-foreground">Consolidacion exitosa</h2>
              <p className="text-sm text-muted-foreground">{result.message}</p>
            </div>
          </div>
          <div className="bg-muted rounded-xl p-3 mb-4 space-y-1 text-sm">
            <p className="text-foreground">
              <span className="font-semibold">Nueva OC:</span>{' '}
              <span className="font-mono text-primary">{result.consolidated_po.po_number}</span>
            </p>
            <p className="text-foreground">
              <span className="font-semibold">OC originales:</span> {result.original_pos.length}
            </p>
            <p className="text-foreground">
              <span className="font-semibold">Lineas fusionadas:</span> {result.lines_merged}
            </p>
          </div>
          <div className="flex gap-3">
            <button
              onClick={() => onClose(result)}
              className="flex-1 rounded-xl border border-border px-4 py-2 text-sm text-muted-foreground hover:bg-muted"
            >
              Cerrar
            </button>
            <button
              onClick={() => navigate(`/inventario/compras/${result.consolidated_po.id}`)}
              className="flex-1 rounded-xl bg-primary px-4 py-2 text-sm font-semibold text-white hover:bg-primary/90"
            >
              Ver OC consolidada
            </button>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 backdrop-blur-sm">
      <div className="w-full max-w-lg bg-card rounded-3xl shadow-2xl p-6 max-h-[90vh] overflow-y-auto">
        <div className="flex items-center gap-2 mb-4">
          <GitMerge className="h-5 w-5 text-blue-600" />
          <h2 className="text-lg font-bold text-foreground">Consolidar Ordenes de Compra</h2>
        </div>

        {/* Selected POs table */}
        <div className="bg-muted rounded-xl overflow-hidden mb-4">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-xs text-muted-foreground uppercase">
                <th className="text-left px-3 py-2">Numero</th>
                <th className="text-left px-3 py-2">Proveedor</th>
                <th className="text-right px-3 py-2">Lineas</th>
                <th className="text-right px-3 py-2">Total</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {selectedPOs.map((po) => {
                const poTotal = (po.lines ?? []).reduce((s, l) => s + Number(l.line_total), 0)
                return (
                  <tr key={po.id}>
                    <td className="px-3 py-2 font-mono text-xs text-primary font-semibold">{po.po_number}</td>
                    <td className="px-3 py-2 text-foreground">{supplierMap[po.supplier_id] ?? po.supplier_id.slice(0, 8)}</td>
                    <td className="px-3 py-2 text-right text-muted-foreground">{po.lines?.length ?? 0}</td>
                    <td className="px-3 py-2 text-right font-mono text-muted-foreground">${poTotal.toLocaleString('es', { minimumFractionDigits: 2 })}</td>
                  </tr>
                )
              })}
            </tbody>
            <tfoot>
              <tr className="bg-secondary font-semibold text-xs">
                <td colSpan={2} className="px-3 py-2 text-muted-foreground">Total</td>
                <td className="px-3 py-2 text-right text-foreground">{totalLines}</td>
                <td className="px-3 py-2 text-right font-mono text-foreground">${totalValue.toLocaleString('es', { minimumFractionDigits: 2 })}</td>
              </tr>
            </tfoot>
          </table>
        </div>

        {/* Merge preview */}
        {mergeableLines.length > 0 && (
          <div className="bg-blue-50 border border-blue-200 rounded-xl p-3 mb-4">
            <p className="text-xs font-semibold text-blue-700 uppercase mb-2">Lineas que se fusionaran (mismo producto)</p>
            <ul className="space-y-1 text-sm text-blue-800">
              {mergeableLines.map((ml) => (
                <li key={ml.name} className="flex items-center gap-2">
                  <GitMerge className="h-3.5 w-3.5 text-blue-500 flex-shrink-0" />
                  <span>{ml.name}: {ml.count} lineas &rarr; 1 linea ({ml.totalQty} uds.)</span>
                </li>
              ))}
            </ul>
          </div>
        )}

        <div className="flex gap-3 pt-2">
          <button onClick={() => onClose()} className="flex-1 rounded-xl border border-border px-4 py-2 text-sm text-muted-foreground hover:bg-muted">
            Cancelar
          </button>
          <button
            onClick={handleConsolidate}
            disabled={consolidate.isPending}
            className="flex-1 rounded-xl bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700 disabled:opacity-60"
          >
            {consolidate.isPending ? 'Consolidando...' : 'Confirmar consolidacion'}
          </button>
        </div>

        {consolidate.isError && (
          <p className="mt-3 text-sm text-red-600 bg-red-50 border border-red-200 rounded-xl px-3 py-2">
            {consolidate.error?.message ?? 'Error al consolidar'}
          </p>
        )}
      </div>
    </div>
  )
}

/* ──────────────── Candidates Drawer ──────────────── */

function CandidatesModal({
  candidates,
  supplierMap,
  productMap,
  onClose,
}: {
  candidates: ConsolidationCandidate[]
  supplierMap: Record<string, string>
  productMap: Record<string, string>
  onClose: () => void
}) {
  const consolidate = useConsolidatePOs()
  const navigate = useNavigate()
  const [selectedGroup, setSelectedGroup] = useState<Record<string, Set<string>>>({})
  const [successResult, setSuccessResult] = useState<ConsolidationResult | null>(null)

  function togglePO(supplierId: string, poId: string) {
    setSelectedGroup((prev) => {
      const current = new Set(prev[supplierId] ?? [])
      if (current.has(poId)) current.delete(poId)
      else current.add(poId)
      return { ...prev, [supplierId]: current }
    })
  }

  async function handleConsolidateGroup(supplierId: string, poIds: string[]) {
    const res = await consolidate.mutateAsync(poIds)
    setSuccessResult(res)
  }

  if (successResult) {
    return (
      <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 backdrop-blur-sm">
        <div className="w-full max-w-md bg-card rounded-3xl shadow-2xl p-6">
          <div className="flex items-center gap-2 mb-4">
            <div className="h-10 w-10 rounded-full bg-emerald-100 flex items-center justify-center">
              <Check className="h-5 w-5 text-emerald-600" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-foreground">Consolidacion exitosa</h2>
              <p className="text-sm text-muted-foreground">{successResult.message}</p>
            </div>
          </div>
          <div className="flex gap-3">
            <button onClick={onClose} className="flex-1 rounded-xl border border-border px-4 py-2 text-sm text-muted-foreground hover:bg-muted">
              Cerrar
            </button>
            <button
              onClick={() => navigate(`/inventario/compras/${successResult.consolidated_po.id}`)}
              className="flex-1 rounded-xl bg-primary px-4 py-2 text-sm font-semibold text-white hover:bg-primary/90"
            >
              Ver OC consolidada
            </button>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 backdrop-blur-sm">
      <div className="w-full max-w-2xl bg-card rounded-3xl shadow-2xl p-6 max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <GitMerge className="h-5 w-5 text-blue-600" />
            <h2 className="text-lg font-bold text-foreground">Sugerencias de consolidacion</h2>
          </div>
          <button onClick={onClose} className="text-muted-foreground hover:text-muted-foreground">
            <X className="h-5 w-5" />
          </button>
        </div>

        <div className="space-y-4">
          {candidates.map((candidate) => {
            const groupSelected = selectedGroup[candidate.supplier_id] ?? new Set()
            const allSelected = candidate.pos.every((po) => groupSelected.has(po.id))
            return (
              <div key={candidate.supplier_id} className="border border-border rounded-xl overflow-hidden">
                <div className="bg-muted px-4 py-3 flex items-center justify-between">
                  <div>
                    <p className="font-semibold text-foreground">{candidate.supplier_name}</p>
                    <p className="text-xs text-muted-foreground">{candidate.po_count} OC &middot; Total: ${candidate.total_amount.toLocaleString('es', { minimumFractionDigits: 2 })}</p>
                  </div>
                  <button
                    onClick={() => {
                      const ids = candidate.pos.map((po) => po.id)
                      handleConsolidateGroup(candidate.supplier_id, groupSelected.size >= 2 ? Array.from(groupSelected) : ids)
                    }}
                    disabled={consolidate.isPending || (groupSelected.size > 0 && groupSelected.size < 2)}
                    className="rounded-xl bg-blue-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-blue-700 disabled:opacity-60"
                  >
                    {consolidate.isPending ? 'Consolidando...' : `Consolidar ${groupSelected.size >= 2 ? groupSelected.size : candidate.po_count} OC`}
                  </button>
                </div>
                <div className="divide-y divide-slate-100">
                  {candidate.pos.map((po) => {
                    const poTotal = (po.lines ?? []).reduce((s, l) => s + Number(l.line_total), 0)
                    return (
                      <label key={po.id} className="flex items-center gap-3 px-4 py-2.5 hover:bg-muted cursor-pointer">
                        <input
                          type="checkbox"
                          checked={groupSelected.has(po.id)}
                          onChange={() => togglePO(candidate.supplier_id, po.id)}
                          className="rounded border-slate-300 text-blue-600 focus:ring-blue-500"
                        />
                        <span className="font-mono text-xs text-primary font-semibold">{po.po_number}</span>
                        <span className="text-sm text-muted-foreground flex-1">{po.lines?.length ?? 0} lineas</span>
                        <span className="text-sm font-mono text-muted-foreground">${poTotal.toLocaleString('es', { minimumFractionDigits: 2 })}</span>
                      </label>
                    )
                  })}
                </div>
              </div>
            )
          })}
        </div>

        {consolidate.isError && (
          <p className="mt-3 text-sm text-red-600 bg-red-50 border border-red-200 rounded-xl px-3 py-2">
            {consolidate.error?.message ?? 'Error al consolidar'}
          </p>
        )}
      </div>
    </div>
  )
}

/* ──────────────── Main Page ──────────────── */

export function PurchaseOrdersPage() {
  const navigate = useNavigate()
  const { hasPermission } = useAuthStore()
  const { data, isLoading } = usePurchaseOrders()
  const { data: suppliers = [] } = useSuppliers()
  const { data: productsData } = useProducts({ limit: 200 })
  const { data: candidates } = useConsolidationCandidates()
  const [showCreate, setShowCreate] = useState(false)
  const [showCandidates, setShowCandidates] = useState(false)
  const [showConsolidate, setShowConsolidate] = useState(false)
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set())
  const [error, setError] = useState('')
  const location = useLocation()
  useEffect(() => { setShowCreate(false) }, [location.key])

  const { resolve } = useUserLookup(data?.items.map(po => po.created_by) ?? [])
  const supplierMap = Object.fromEntries(suppliers.map((s) => [s.id, s.name]))
  const productMap = Object.fromEntries((productsData?.items ?? []).map((p) => [p.id, p.name]))

  const items = data?.items ?? []

  function toggleSelect(poId: string) {
    setSelectedIds((prev) => {
      const next = new Set(prev)
      if (next.has(poId)) next.delete(poId)
      else next.add(poId)
      return next
    })
    setError('')
  }

  function handleConsolidateClick() {
    // Validate: all selected POs must have the same supplier
    const selected = items.filter((po) => selectedIds.has(po.id))
    const supplierIds = new Set(selected.map((po) => po.supplier_id))
    if (supplierIds.size > 1) {
      setError('Solo puedes consolidar OC del mismo proveedor. Selecciona OC con el mismo proveedor.')
      return
    }
    setError('')
    setShowConsolidate(true)
  }

  const selectedPOs = items.filter((po) => selectedIds.has(po.id))

  return (
    <div className="max-w-5xl mx-auto p-6 space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-foreground">Ordenes de Compra</h1>
        {hasPermission('purchase_orders.create') && (
          <button onClick={() => setShowCreate(true)}
            className="flex items-center gap-2 rounded-2xl bg-primary px-4 py-2.5 text-sm font-semibold text-white hover:bg-primary/90 ">
            <Plus className="h-4 w-4" /> Nueva OC
          </button>
        )}
      </div>

      {/* Consolidation suggestions banner */}
      {candidates && candidates.length > 0 && (
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <GitMerge className="w-5 h-5 text-blue-600" />
            <span className="text-blue-800 text-sm">
              Tienes POs en borrador al mismo proveedor que puedes consolidar
            </span>
          </div>
          <button onClick={() => setShowCandidates(true)} className="text-blue-600 hover:text-blue-800 font-medium text-sm">
            Ver sugerencias
          </button>
        </div>
      )}

      {/* Validation error */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-3 flex items-center gap-2">
          <AlertCircle className="w-4 h-4 text-red-500 flex-shrink-0" />
          <span className="text-sm text-red-700">{error}</span>
          <button onClick={() => setError('')} className="ml-auto text-red-400 hover:text-red-600">
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      <div className="bg-card rounded-2xl border border-border  overflow-hidden">
        {isLoading ? (
          <div className="p-8 text-center text-muted-foreground">Cargando...</div>
        ) : !items.length ? (
          <div className="p-8 text-center">
            <ShoppingCart className="h-10 w-10 text-slate-200 mx-auto mb-3" />
            <p className="text-sm text-muted-foreground">Sin ordenes de compra</p>
          </div>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-muted border-b border-border">
              <tr>
                <th className="px-3 py-3 text-left w-10">
                  {/* Select-all header — intentionally empty */}
                </th>
                {['Numero', 'Proveedor', 'Estado', 'Fecha', 'Creado por'].map((h) => (
                  <th key={h} className="px-4 py-3 text-left text-xs font-semibold text-muted-foreground uppercase tracking-wide">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-50">
              {items.map((po) => {
                const cfg = STATUS_CONFIG[po.status]
                const isDraft = po.status === 'draft'
                const isSelected = selectedIds.has(po.id)
                return (
                  <tr key={po.id} className="hover:bg-muted transition-colors">
                    <td className="px-3 py-3">
                      {isDraft && (
                        <input
                          type="checkbox"
                          checked={isSelected}
                          onChange={() => toggleSelect(po.id)}
                          className="rounded border-slate-300 text-blue-600 focus:ring-blue-500"
                        />
                      )}
                    </td>
                    <td className="px-4 py-3 cursor-pointer" onClick={() => navigate(`/inventario/compras/${po.id}`)}>
                      <span className="font-mono text-xs font-semibold text-primary">{po.po_number}</span>
                      {po.is_auto_generated && (
                        <span className="ml-2 inline-flex items-center rounded-full bg-purple-100 px-1.5 py-0.5 text-[10px] font-medium text-purple-700">Auto</span>
                      )}
                      {po.is_consolidated && (
                        <span className="ml-2 inline-flex items-center gap-1 rounded-full bg-blue-100 px-1.5 py-0.5 text-[10px] font-medium text-blue-700">
                          <GitMerge className="h-2.5 w-2.5" /> Consolidada
                        </span>
                      )}
                    </td>
                    <td className="px-4 py-3 font-medium text-foreground cursor-pointer" onClick={() => navigate(`/inventario/compras/${po.id}`)}>{supplierMap[po.supplier_id] ?? po.supplier_id.slice(0, 8)}</td>
                    <td className="px-4 py-3 cursor-pointer" onClick={() => navigate(`/inventario/compras/${po.id}`)}>
                      <span className={cn('rounded-full px-2 py-0.5 text-xs font-semibold inline-flex items-center gap-1', cfg?.color ?? 'bg-secondary text-muted-foreground')}>
                        {cfg?.icon && <cfg.icon className="h-3 w-3" />}
                        {cfg?.label ?? po.status}
                      </span>
                      {po.status === 'consolidated' && po.parent_consolidated_id && (
                        <span className="ml-1 text-[10px] text-muted-foreground">(fusionada)</span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-muted-foreground text-xs cursor-pointer" onClick={() => navigate(`/inventario/compras/${po.id}`)}>{new Date(po.created_at).toLocaleDateString('es')}</td>
                    <td className="px-4 py-3 text-muted-foreground text-xs cursor-pointer" onClick={() => navigate(`/inventario/compras/${po.id}`)}>{resolve(po.created_by)}</td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        )}
      </div>

      {/* Sticky bottom toolbar for consolidation */}
      {selectedIds.size >= 2 && (
        <div className="fixed bottom-4 left-1/2 -translate-x-1/2 bg-card shadow-lg rounded-lg border p-4 flex items-center gap-4 z-50">
          <span className="font-medium text-sm text-foreground">{selectedIds.size} OC seleccionadas</span>
          <button
            onClick={handleConsolidateClick}
            className="flex items-center gap-1.5 bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 text-sm font-semibold"
          >
            <GitMerge className="h-4 w-4" /> Consolidar seleccionadas
          </button>
          <button
            onClick={() => { setSelectedIds(new Set()); setError(''); }}
            className="text-muted-foreground hover:text-foreground text-sm"
          >
            Cancelar
          </button>
        </div>
      )}

      {showCreate && <CreatePOModal onClose={() => setShowCreate(false)} />}

      {showConsolidate && selectedPOs.length >= 2 && (
        <ConsolidatePreviewModal
          selectedPOs={selectedPOs}
          supplierMap={supplierMap}
          productMap={productMap}
          onClose={(result) => {
            setShowConsolidate(false)
            if (result) setSelectedIds(new Set())
          }}
        />
      )}

      {showCandidates && candidates && (
        <CandidatesModal
          candidates={candidates}
          supplierMap={supplierMap}
          productMap={productMap}
          onClose={() => setShowCandidates(false)}
        />
      )}
    </div>
  )
}
