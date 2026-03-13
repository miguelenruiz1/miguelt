import { useState } from 'react'
import { RefreshCw, AlertTriangle, CheckCircle, Package, Loader2, Play } from 'lucide-react'
import { useReorderConfig, useCheckAllReorder, useCheckProductReorder } from '@/hooks/useInventory'
import type { ReorderConfig } from '@/types/inventory'

export function ReorderConfigPage() {
  const { data: configs, isLoading } = useReorderConfig()
  const checkAll = useCheckAllReorder()
  const checkProduct = useCheckProductReorder()
  const [lastResult, setLastResult] = useState<string | null>(null)

  const handleCheckAll = () => {
    checkAll.mutate(undefined, {
      onSuccess: (pos) => {
        setLastResult(
          pos.length > 0
            ? `Se crearon ${pos.length} PO(s) de reorden: ${pos.map(p => p.po_number).join(', ')}`
            : 'No se requieren reórdenes en este momento.'
        )
      },
    })
  }

  const handleCheckProduct = (productId: string) => {
    checkProduct.mutate(productId, {
      onSuccess: (po) => {
        setLastResult(
          po
            ? `PO de reorden creada: ${po.po_number}`
            : 'No se requiere reorden para este producto.'
        )
      },
    })
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
      </div>
    )
  }

  const items = configs ?? []
  const belowROP = items.filter(c => c.below_rop).length

  return (
    <div className="space-y-6 p-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Reorden Automatico</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Productos configurados con reorden automatico. El sistema crea POs borrador cuando el stock disponible baja del punto de reorden.
          </p>
        </div>
        <button
          onClick={handleCheckAll}
          disabled={checkAll.isPending}
          className="inline-flex items-center gap-2 rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
        >
          {checkAll.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4" />}
          Ejecutar Reorden
        </button>
      </div>

      {/* Result banner */}
      {lastResult && (
        <div className="rounded-md border border-blue-200 bg-blue-50 px-4 py-3 text-sm text-blue-800">
          {lastResult}
        </div>
      )}

      {/* KPI cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="rounded-lg border bg-card p-4">
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <RefreshCw className="h-4 w-4" />
            <span>Productos con Reorden</span>
          </div>
          <p className="text-2xl font-bold mt-1">{items.length}</p>
        </div>
        <div className="rounded-lg border bg-card p-4">
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <AlertTriangle className="h-4 w-4 text-amber-500" />
            <span>Bajo Punto de Reorden</span>
          </div>
          <p className="text-2xl font-bold mt-1 text-amber-600">{belowROP}</p>
        </div>
        <div className="rounded-lg border bg-card p-4">
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <CheckCircle className="h-4 w-4 text-green-500" />
            <span>Stock Suficiente</span>
          </div>
          <p className="text-2xl font-bold mt-1 text-green-600">{items.length - belowROP}</p>
        </div>
      </div>

      {/* Table */}
      {items.length === 0 ? (
        <div className="rounded-lg border bg-card p-8 text-center text-muted-foreground">
          <Package className="h-10 w-10 mx-auto mb-3 opacity-40" />
          <p className="font-medium">No hay productos con reorden automatico</p>
          <p className="text-sm mt-1">
            Activa "Reorden automatico" y asigna un proveedor preferido en la ficha de producto.
          </p>
        </div>
      ) : (
        <div className="rounded-lg border bg-card overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b bg-muted/50">
                <th className="text-left px-4 py-3 font-medium">Producto</th>
                <th className="text-left px-4 py-3 font-medium">SKU</th>
                <th className="text-left px-4 py-3 font-medium">Proveedor Preferido</th>
                <th className="text-right px-4 py-3 font-medium">ROP</th>
                <th className="text-right px-4 py-3 font-medium">Cant. Reorden</th>
                <th className="text-right px-4 py-3 font-medium">Stock Actual</th>
                <th className="text-center px-4 py-3 font-medium">Estado</th>
                <th className="text-center px-4 py-3 font-medium">PO Abierta</th>
                <th className="text-center px-4 py-3 font-medium"></th>
              </tr>
            </thead>
            <tbody>
              {items.map((c: ReorderConfig) => (
                <tr key={c.product_id} className="border-b last:border-0 hover:bg-muted/30">
                  <td className="px-4 py-3 font-medium">{c.product_name}</td>
                  <td className="px-4 py-3 text-muted-foreground">{c.product_sku}</td>
                  <td className="px-4 py-3">{c.preferred_supplier_name ?? '—'}</td>
                  <td className="px-4 py-3 text-right tabular-nums">{c.reorder_point}</td>
                  <td className="px-4 py-3 text-right tabular-nums">{c.reorder_quantity}</td>
                  <td className="px-4 py-3 text-right tabular-nums">
                    <span className={c.below_rop ? 'text-red-600 font-semibold' : 'text-green-600'}>
                      {c.current_stock}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-center">
                    {c.below_rop ? (
                      <span className="inline-flex items-center gap-1 rounded-full bg-amber-100 px-2 py-0.5 text-xs font-medium text-amber-800">
                        <AlertTriangle className="h-3 w-3" />
                        Bajo ROP
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1 rounded-full bg-green-100 px-2 py-0.5 text-xs font-medium text-green-800">
                        <CheckCircle className="h-3 w-3" />
                        OK
                      </span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-center">
                    {c.has_open_po ? (
                      <span className="inline-flex items-center rounded-full bg-blue-100 px-2 py-0.5 text-xs font-medium text-blue-800">
                        PO activa
                      </span>
                    ) : (
                      <span className="text-muted-foreground">—</span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-center">
                    {c.below_rop && !c.has_open_po && (
                      <button
                        onClick={() => handleCheckProduct(c.product_id)}
                        disabled={checkProduct.isPending}
                        className="inline-flex items-center gap-1 rounded-md border px-2 py-1 text-xs font-medium hover:bg-muted disabled:opacity-50"
                        title="Crear PO de reorden"
                      >
                        <RefreshCw className="h-3 w-3" />
                        Reordenar
                      </button>
                    )}
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
