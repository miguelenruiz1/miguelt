import { useState, useRef, useEffect, useCallback } from 'react'
import {
  ScanBarcode,
  Package,
  ArrowDownToLine,
  ArrowUpFromLine,
  ArrowLeftRight,
  Clock,
  AlertCircle,
  Plus,
  X,
  Check,
  Loader2,
} from 'lucide-react'
import {
  useWarehouses,
  useReceiveStock,
  useIssueStock,
  useTransferStock,
  useStockByProduct,
} from '@/hooks/useInventory'
import { inventoryProductsApi } from '@/lib/inventory-api'
import { useToast } from '@/store/toast'
import { cn } from '@/lib/utils'
import type { Product, Warehouse, StockLevel } from '@/types/inventory'

// ─── Audio feedback (Web Audio API) ─────────────────────────────────────────

const audioCtx = typeof window !== 'undefined' ? new (window.AudioContext || (window as never as { webkitAudioContext: typeof AudioContext }).webkitAudioContext)() : null

function playBeep(frequency: number, duration: number) {
  if (!audioCtx) return
  // Resume context if suspended (browser autoplay policy)
  if (audioCtx.state === 'suspended') audioCtx.resume()
  const osc = audioCtx.createOscillator()
  const gain = audioCtx.createGain()
  osc.connect(gain)
  gain.connect(audioCtx.destination)
  osc.type = 'sine'
  osc.frequency.value = frequency
  gain.gain.value = 0.3
  osc.start()
  gain.gain.exponentialRampToValueAtTime(0.001, audioCtx.currentTime + duration)
  osc.stop(audioCtx.currentTime + duration)
}

function playSuccessBeep() {
  playBeep(880, 0.15)
}

function playErrorBeep() {
  playBeep(220, 0.3)
}

// ─── Types ──────────────────────────────────────────────────────────────────

type QuickAction = 'receive' | 'issue' | 'transfer' | null

interface ScanEntry {
  id: string
  code: string
  product: Product | null
  timestamp: Date
}

// ─── Quick Action Forms ─────────────────────────────────────────────────────

function ReceiveForm({
  product,
  warehouses,
  onDone,
}: {
  product: Product
  warehouses: Warehouse[]
  onDone: () => void
}) {
  const toast = useToast()
  const receive = useReceiveStock()
  const [warehouseId, setWarehouseId] = useState(warehouses[0]?.id ?? '')
  const [quantity, setQuantity] = useState('')

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!warehouseId || !quantity) return
    receive.mutate(
      { product_id: product.id, warehouse_id: warehouseId, quantity },
      {
        onSuccess: () => {
          toast.success(`Entrada registrada: ${quantity} ${product.unit_of_measure} de ${product.name}`)
          playSuccessBeep()
          onDone()
        },
        onError: (err) => {
          toast.error(`Error: ${(err as Error).message}`)
          playErrorBeep()
        },
      },
    )
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-3">
      <h4 className="font-semibold text-green-700 flex items-center gap-2">
        <ArrowDownToLine className="h-4 w-4" /> Entrada de stock
      </h4>
      <select
        value={warehouseId}
        onChange={(e) => setWarehouseId(e.target.value)}
        className="w-full rounded-xl border border-border px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-green-400"
        required
      >
        <option value="">Seleccionar almacen</option>
        {warehouses.map((w) => (
          <option key={w.id} value={w.id}>
            {w.name} ({w.code})
          </option>
        ))}
      </select>
      <input
        type="number"
        min="1"
        step="any"
        placeholder="Cantidad"
        value={quantity}
        onChange={(e) => setQuantity(e.target.value)}
        className="w-full rounded-xl border border-border px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-green-400"
        required
      />
      <div className="flex gap-2">
        <button
          type="submit"
          disabled={receive.isPending}
          className="flex-1 flex items-center justify-center gap-2 rounded-xl bg-green-600 px-4 py-3 text-sm font-medium text-white hover:bg-green-700 disabled:opacity-50"
        >
          {receive.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Check className="h-4 w-4" />}
          Confirmar entrada
        </button>
        <button
          type="button"
          onClick={onDone}
          className="rounded-xl border border-border px-4 py-3 text-sm font-medium text-muted-foreground hover:bg-muted"
        >
          Cancelar
        </button>
      </div>
    </form>
  )
}

function IssueForm({
  product,
  warehouses,
  onDone,
}: {
  product: Product
  warehouses: Warehouse[]
  onDone: () => void
}) {
  const toast = useToast()
  const issue = useIssueStock()
  const [warehouseId, setWarehouseId] = useState(warehouses[0]?.id ?? '')
  const [quantity, setQuantity] = useState('')

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!warehouseId || !quantity) return
    issue.mutate(
      { product_id: product.id, warehouse_id: warehouseId, quantity },
      {
        onSuccess: () => {
          toast.success(`Salida registrada: ${quantity} ${product.unit_of_measure} de ${product.name}`)
          playSuccessBeep()
          onDone()
        },
        onError: (err) => {
          toast.error(`Error: ${(err as Error).message}`)
          playErrorBeep()
        },
      },
    )
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-3">
      <h4 className="font-semibold text-orange-700 flex items-center gap-2">
        <ArrowUpFromLine className="h-4 w-4" /> Salida de stock
      </h4>
      <select
        value={warehouseId}
        onChange={(e) => setWarehouseId(e.target.value)}
        className="w-full rounded-xl border border-border px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-orange-400"
        required
      >
        <option value="">Seleccionar almacen</option>
        {warehouses.map((w) => (
          <option key={w.id} value={w.id}>
            {w.name} ({w.code})
          </option>
        ))}
      </select>
      <input
        type="number"
        min="1"
        step="any"
        placeholder="Cantidad"
        value={quantity}
        onChange={(e) => setQuantity(e.target.value)}
        className="w-full rounded-xl border border-border px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-orange-400"
        required
      />
      <div className="flex gap-2">
        <button
          type="submit"
          disabled={issue.isPending}
          className="flex-1 flex items-center justify-center gap-2 rounded-xl bg-orange-600 px-4 py-3 text-sm font-medium text-white hover:bg-orange-700 disabled:opacity-50"
        >
          {issue.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Check className="h-4 w-4" />}
          Confirmar salida
        </button>
        <button
          type="button"
          onClick={onDone}
          className="rounded-xl border border-border px-4 py-3 text-sm font-medium text-muted-foreground hover:bg-muted"
        >
          Cancelar
        </button>
      </div>
    </form>
  )
}

function TransferForm({
  product,
  warehouses,
  onDone,
}: {
  product: Product
  warehouses: Warehouse[]
  onDone: () => void
}) {
  const toast = useToast()
  const transfer = useTransferStock()
  const [fromId, setFromId] = useState(warehouses[0]?.id ?? '')
  const [toId, setToId] = useState(warehouses[1]?.id ?? '')
  const [quantity, setQuantity] = useState('')

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!fromId || !toId || !quantity) return
    if (fromId === toId) {
      toast.error('Los almacenes de origen y destino deben ser diferentes')
      return
    }
    transfer.mutate(
      { product_id: product.id, from_warehouse_id: fromId, to_warehouse_id: toId, quantity },
      {
        onSuccess: () => {
          toast.success(`Transferencia registrada: ${quantity} ${product.unit_of_measure} de ${product.name}`)
          playSuccessBeep()
          onDone()
        },
        onError: (err) => {
          toast.error(`Error: ${(err as Error).message}`)
          playErrorBeep()
        },
      },
    )
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-3">
      <h4 className="font-semibold text-blue-700 flex items-center gap-2">
        <ArrowLeftRight className="h-4 w-4" /> Transferencia de stock
      </h4>
      <select
        value={fromId}
        onChange={(e) => setFromId(e.target.value)}
        className="w-full rounded-xl border border-border px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
        required
      >
        <option value="">Almacen origen</option>
        {warehouses.map((w) => (
          <option key={w.id} value={w.id}>
            {w.name} ({w.code})
          </option>
        ))}
      </select>
      <select
        value={toId}
        onChange={(e) => setToId(e.target.value)}
        className="w-full rounded-xl border border-border px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
        required
      >
        <option value="">Almacen destino</option>
        {warehouses.map((w) => (
          <option key={w.id} value={w.id}>
            {w.name} ({w.code})
          </option>
        ))}
      </select>
      <input
        type="number"
        min="1"
        step="any"
        placeholder="Cantidad"
        value={quantity}
        onChange={(e) => setQuantity(e.target.value)}
        className="w-full rounded-xl border border-border px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
        required
      />
      <div className="flex gap-2">
        <button
          type="submit"
          disabled={transfer.isPending}
          className="flex-1 flex items-center justify-center gap-2 rounded-xl bg-blue-600 px-4 py-3 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
        >
          {transfer.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Check className="h-4 w-4" />}
          Confirmar transferencia
        </button>
        <button
          type="button"
          onClick={onDone}
          className="rounded-xl border border-border px-4 py-3 text-sm font-medium text-muted-foreground hover:bg-muted"
        >
          Cancelar
        </button>
      </div>
    </form>
  )
}

// ─── Product Detail Card ────────────────────────────────────────────────────

function ProductCard({
  product,
  warehouses,
}: {
  product: Product
  warehouses: Warehouse[]
}) {
  const [action, setAction] = useState<QuickAction>(null)
  const { data: stockLevels } = useStockByProduct(product.id)

  const warehouseMap = new Map(warehouses.map((w) => [w.id, w]))

  return (
    <div className="rounded-2xl border border-border bg-card  overflow-hidden">
      {/* Product header */}
      <div className="px-5 py-4 border-b border-border">
        <div className="flex items-start gap-3">
          <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-primary/10 text-primary">
            <Package className="h-6 w-6" />
          </div>
          <div className="min-w-0 flex-1">
            <h3 className="text-lg font-semibold text-foreground truncate">{product.name}</h3>
            <div className="mt-1 flex flex-wrap gap-x-4 gap-y-1 text-sm text-muted-foreground">
              <span>SKU: <span className="font-mono font-medium text-foreground">{product.sku}</span></span>
              {product.barcode && (
                <span>Cod. barras: <span className="font-mono font-medium text-foreground">{product.barcode}</span></span>
              )}
              <span>UOM: {product.unit_of_measure}</span>
            </div>
            {product.description && (
              <p className="mt-1 text-sm text-muted-foreground line-clamp-2">{product.description}</p>
            )}
          </div>
        </div>
      </div>

      {/* Stock levels per warehouse */}
      <div className="px-5 py-3 border-b border-border">
        <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2">Stock por almacen</h4>
        {stockLevels && stockLevels.length > 0 ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2">
            {stockLevels.map((sl: StockLevel) => {
              const wh = warehouseMap.get(sl.warehouse_id)
              return (
                <div
                  key={sl.id}
                  className="flex items-center justify-between rounded-xl bg-muted px-3 py-2"
                >
                  <span className="text-sm text-muted-foreground truncate">
                    {wh?.name ?? sl.warehouse_id}
                  </span>
                  <span
                    className={cn(
                      'text-sm font-semibold tabular-nums',
                      Number(sl.qty_on_hand) <= 0 ? 'text-red-600' : 'text-foreground',
                    )}
                  >
                    {sl.qty_on_hand}
                  </span>
                </div>
              )
            })}
          </div>
        ) : (
          <p className="text-sm text-muted-foreground italic">Sin stock registrado</p>
        )}
      </div>

      {/* Quick actions */}
      <div className="px-5 py-4">
        {action === null ? (
          <div className="grid grid-cols-3 gap-2">
            <button
              onClick={() => setAction('receive')}
              className="flex flex-col items-center gap-1.5 rounded-xl border border-green-200 bg-green-50 px-3 py-3 text-green-700 hover:bg-green-100 transition-colors"
            >
              <ArrowDownToLine className="h-5 w-5" />
              <span className="text-sm font-medium">Entrada</span>
            </button>
            <button
              onClick={() => setAction('issue')}
              className="flex flex-col items-center gap-1.5 rounded-xl border border-orange-200 bg-orange-50 px-3 py-3 text-orange-700 hover:bg-orange-100 transition-colors"
            >
              <ArrowUpFromLine className="h-5 w-5" />
              <span className="text-sm font-medium">Salida</span>
            </button>
            <button
              onClick={() => setAction('transfer')}
              className="flex flex-col items-center gap-1.5 rounded-xl border border-blue-200 bg-blue-50 px-3 py-3 text-blue-700 hover:bg-blue-100 transition-colors"
            >
              <ArrowLeftRight className="h-5 w-5" />
              <span className="text-sm font-medium">Transferir</span>
            </button>
          </div>
        ) : (
          <div>
            {action === 'receive' && (
              <ReceiveForm product={product} warehouses={warehouses} onDone={() => setAction(null)} />
            )}
            {action === 'issue' && (
              <IssueForm product={product} warehouses={warehouses} onDone={() => setAction(null)} />
            )}
            {action === 'transfer' && (
              <TransferForm product={product} warehouses={warehouses} onDone={() => setAction(null)} />
            )}
          </div>
        )}
      </div>
    </div>
  )
}

// ─── Not Found Card ─────────────────────────────────────────────────────────

function NotFoundCard({ code, onCreateNew }: { code: string; onCreateNew: () => void }) {
  return (
    <div className="rounded-2xl border border-red-200 bg-red-50 p-6 text-center">
      <AlertCircle className="mx-auto h-10 w-10 text-red-400" />
      <h3 className="mt-3 text-lg font-semibold text-red-800">Producto no encontrado</h3>
      <p className="mt-1 text-sm text-red-600">
        No se encontro un producto con el codigo <span className="font-mono font-semibold">{code}</span>
      </p>
      <button
        onClick={onCreateNew}
        className="mt-4 inline-flex items-center gap-2 rounded-xl bg-red-600 px-5 py-3 text-sm font-medium text-white hover:bg-red-700 transition-colors"
      >
        <Plus className="h-4 w-4" />
        Crear nuevo producto
      </button>
    </div>
  )
}

// ─── Scanner Page ───────────────────────────────────────────────────────────

export function ScannerPage() {
  const toast = useToast()
  const inputRef = useRef<HTMLInputElement>(null)
  const { data: warehouses = [] } = useWarehouses()

  const [scanCode, setScanCode] = useState('')
  const [isSearching, setIsSearching] = useState(false)
  const [foundProduct, setFoundProduct] = useState<Product | null>(null)
  const [notFoundCode, setNotFoundCode] = useState<string | null>(null)
  const [history, setHistory] = useState<ScanEntry[]>([])

  // Keep input focused at all times (for barcode scanner input)
  const refocusInput = useCallback(() => {
    // Small delay to allow any click events to finish
    setTimeout(() => inputRef.current?.focus(), 50)
  }, [])

  useEffect(() => {
    inputRef.current?.focus()
  }, [])

  const handleScan = async (code: string) => {
    const trimmed = code.trim()
    if (!trimmed) return

    setIsSearching(true)
    setFoundProduct(null)
    setNotFoundCode(null)

    try {
      // Search by barcode or SKU
      const result = await inventoryProductsApi.list({ search: trimmed, limit: 10 })
      // Try exact match on barcode first, then SKU, then first result
      const exactBarcode = result.items.find(
        (p) => p.barcode?.toLowerCase() === trimmed.toLowerCase(),
      )
      const exactSku = result.items.find(
        (p) => p.sku.toLowerCase() === trimmed.toLowerCase(),
      )
      const product = exactBarcode ?? exactSku ?? result.items[0] ?? null

      const entry: ScanEntry = {
        id: crypto.randomUUID(),
        code: trimmed,
        product,
        timestamp: new Date(),
      }
      setHistory((prev) => [entry, ...prev].slice(0, 50))

      if (product) {
        setFoundProduct(product)
        playSuccessBeep()
      } else {
        setNotFoundCode(trimmed)
        playErrorBeep()
      }
    } catch (err) {
      toast.error(`Error al buscar: ${(err as Error).message}`)
      playErrorBeep()
      setNotFoundCode(trimmed)
    } finally {
      setIsSearching(false)
      setScanCode('')
      refocusInput()
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      e.preventDefault()
      handleScan(scanCode)
    }
  }

  const handleCreateNew = () => {
    // Navigate to products page with pre-filled barcode
    window.location.href = `/inventario/productos?new=1&barcode=${encodeURIComponent(notFoundCode ?? '')}`
  }

  const handleHistoryClick = (entry: ScanEntry) => {
    if (entry.product) {
      setFoundProduct(entry.product)
      setNotFoundCode(null)
    } else {
      setNotFoundCode(entry.code)
      setFoundProduct(null)
    }
    refocusInput()
  }

  return (
    <div className="mx-auto max-w-4xl space-y-6 p-4 sm:p-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-foreground flex items-center gap-3">
          <ScanBarcode className="h-7 w-7 text-primary" />
          Escaner
        </h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Escanea codigos de barras para operaciones rapidas
        </p>
      </div>

      {/* Scanner input */}
      <div className="relative">
        <div className="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-5">
          {isSearching ? (
            <Loader2 className="h-6 w-6 animate-spin text-primary" />
          ) : (
            <ScanBarcode className="h-6 w-6 text-muted-foreground" />
          )}
        </div>
        <input
          ref={inputRef}
          type="text"
          value={scanCode}
          onChange={(e) => setScanCode(e.target.value)}
          onKeyDown={handleKeyDown}
          onBlur={refocusInput}
          placeholder="Escanea o escribe un codigo de barras / SKU..."
          autoComplete="off"
          autoCorrect="off"
          autoCapitalize="off"
          spellCheck={false}
          className={cn(
            'w-full rounded-2xl border-2 bg-card py-5 pl-14 pr-5 text-lg font-mono tracking-wider',
            'placeholder:text-slate-300 placeholder:font-sans placeholder:tracking-normal placeholder:text-base',
            'focus:outline-none focus:ring-4 focus:ring-ring/30 focus:border-primary',
            'border-border transition-all',
            isSearching && 'border-primary/70 ring-4 ring-ring/20',
          )}
        />
        {scanCode && (
          <button
            onClick={() => {
              setScanCode('')
              refocusInput()
            }}
            className="absolute inset-y-0 right-0 flex items-center pr-5 text-muted-foreground hover:text-muted-foreground"
          >
            <X className="h-5 w-5" />
          </button>
        )}
      </div>

      {/* Result area */}
      {foundProduct && (
        <ProductCard product={foundProduct} warehouses={warehouses} />
      )}

      {notFoundCode && !foundProduct && (
        <NotFoundCard code={notFoundCode} onCreateNew={handleCreateNew} />
      )}

      {!foundProduct && !notFoundCode && !isSearching && (
        <div className="rounded-2xl border-2 border-dashed border-border bg-muted/50 py-16 text-center">
          <ScanBarcode className="mx-auto h-16 w-16 text-slate-300" />
          <p className="mt-4 text-lg font-medium text-muted-foreground">
            Listo para escanear
          </p>
          <p className="mt-1 text-sm text-slate-300">
            Usa un lector de codigos de barras USB/Bluetooth o escribe manualmente
          </p>
        </div>
      )}

      {/* Scan history */}
      {history.length > 0 && (
        <div>
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider flex items-center gap-2">
              <Clock className="h-4 w-4" />
              Historial de escaneos ({history.length})
            </h2>
            <button
              onClick={() => {
                setHistory([])
                refocusInput()
              }}
              className="text-xs text-muted-foreground hover:text-muted-foreground"
            >
              Limpiar
            </button>
          </div>
          <div className="space-y-1.5">
            {history.map((entry) => (
              <button
                key={entry.id}
                onClick={() => handleHistoryClick(entry)}
                className={cn(
                  'w-full flex items-center gap-3 rounded-xl px-4 py-3 text-left transition-colors',
                  entry.product
                    ? 'bg-card border border-border hover:border-border hover:bg-muted'
                    : 'bg-red-50/50 border border-red-100 hover:bg-red-50',
                )}
              >
                <div
                  className={cn(
                    'flex h-8 w-8 shrink-0 items-center justify-center rounded-lg',
                    entry.product ? 'bg-green-100 text-green-600' : 'bg-red-100 text-red-500',
                  )}
                >
                  {entry.product ? (
                    <Package className="h-4 w-4" />
                  ) : (
                    <AlertCircle className="h-4 w-4" />
                  )}
                </div>
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-sm font-medium text-foreground truncate">
                      {entry.code}
                    </span>
                    {entry.product && (
                      <span className="text-sm text-muted-foreground truncate">
                        — {entry.product.name}
                      </span>
                    )}
                    {!entry.product && (
                      <span className="text-xs text-red-500 font-medium">No encontrado</span>
                    )}
                  </div>
                </div>
                <span className="shrink-0 text-xs text-slate-300 tabular-nums">
                  {entry.timestamp.toLocaleTimeString('es', {
                    hour: '2-digit',
                    minute: '2-digit',
                    second: '2-digit',
                  })}
                </span>
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
