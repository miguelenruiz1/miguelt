import { useState, useRef, useEffect, useMemo } from 'react'
import { useSearchParams } from 'react-router-dom'
import { Plus, Search, Package, Tag, ArrowLeft, Upload, Download, X, FileText, Trash2, Pencil, Lock, Save, ChevronRight, ChevronLeft, ChevronsLeft, ChevronsRight, ArrowUpDown, ArrowUp, ArrowDown, AlertTriangle, TrendingDown, Camera, ImageIcon, Loader2, ZoomIn, DollarSign, Sliders, Receipt } from 'lucide-react'
import {
  useProducts, useProduct, useCreateProduct, useUpdateProduct, useDeleteProduct,
  useStockByProduct, useWarehouses, useProductTypes, useCustomFields,
  useImportProductsCsv, useDownloadTemplate,
  useUploadProductImage, useDeleteProductImage,
  useSuppliers,
  useCustomerPricesForProduct, useAdjustStock,
  useTaxRates,
} from '@/hooks/useInventory'
import { useUserLookup } from '@/hooks/useUserLookup'
import { useToast } from '@/store/toast'
import { cn } from '@/lib/utils'
import { CopyableId } from '@/components/inventory/CopyableId'
import type { CustomField, Product, ProductType } from '@/types/inventory'
import { inventoryProductsApi } from '@/lib/inventory-api'

const INV_API_BASE = import.meta.env.VITE_INVENTORY_API_URL ?? 'http://localhost:9003'
function imgSrc(url: string) {
  return url.startsWith('http') ? url : `${INV_API_BASE}${url}`
}

// ─── Product thumbnail (reused in table + cards) ────────────────────────────

function ProductThumb({ images, name, size = 'sm' }: { images?: string[]; name: string; size?: 'sm' | 'md' | 'lg' }) {
  const dim = size === 'lg' ? 'h-24 w-24' : size === 'md' ? 'h-14 w-14' : 'h-9 w-9'
  const iconDim = size === 'lg' ? 'h-8 w-8' : size === 'md' ? 'h-5 w-5' : 'h-4 w-4'
  if (images && images.length > 0) {
    return (
      <div className={cn(dim, 'rounded-lg overflow-hidden bg-gray-100 shrink-0')}>
        <img src={imgSrc(images[0])} alt={name} className="h-full w-full object-cover" />
      </div>
    )
  }
  return (
    <div className={cn(dim, 'rounded-lg bg-gray-100 flex items-center justify-center shrink-0')}>
      <Package className={cn(iconDim, 'text-gray-300')} />
    </div>
  )
}

// ─── Image Lightbox / Gallery ────────────────────────────────────────────────

function ImageLightbox({ images, initial = 0, onClose }: { images: string[]; initial?: number; onClose: () => void }) {
  const [idx, setIdx] = useState(initial)
  const total = images.length

  useEffect(() => {
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
      if (e.key === 'ArrowRight') setIdx(i => (i + 1) % total)
      if (e.key === 'ArrowLeft') setIdx(i => (i - 1 + total) % total)
    }
    window.addEventListener('keydown', handleKey)
    return () => window.removeEventListener('keydown', handleKey)
  }, [total, onClose])

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/90" onClick={onClose}>
      {/* Close */}
      <button onClick={onClose} className="absolute top-4 right-4 text-white/70 hover:text-white transition-colors z-10">
        <X className="h-8 w-8" />
      </button>

      {/* Counter */}
      <div className="absolute top-4 left-1/2 -translate-x-1/2 text-white/70 text-sm font-medium z-10">
        {idx + 1} / {total}
      </div>

      {/* Prev */}
      {total > 1 && (
        <button
          onClick={e => { e.stopPropagation(); setIdx(i => (i - 1 + total) % total) }}
          className="absolute left-4 top-1/2 -translate-y-1/2 rounded-full bg-white/10 hover:bg-white/20 p-3 text-white transition-colors z-10"
        >
          <ChevronLeft className="h-6 w-6" />
        </button>
      )}

      {/* Image */}
      <img
        src={imgSrc(images[idx])}
        alt={`Foto ${idx + 1}`}
        className="max-h-[85vh] max-w-[90vw] object-contain rounded-lg select-none"
        onClick={e => e.stopPropagation()}
      />

      {/* Next */}
      {total > 1 && (
        <button
          onClick={e => { e.stopPropagation(); setIdx(i => (i + 1) % total) }}
          className="absolute right-4 top-1/2 -translate-y-1/2 rounded-full bg-white/10 hover:bg-white/20 p-3 text-white transition-colors z-10"
        >
          <ChevronRight className="h-6 w-6" />
        </button>
      )}

      {/* Thumbnails strip */}
      {total > 1 && (
        <div className="absolute bottom-6 left-1/2 -translate-x-1/2 flex gap-2 z-10">
          {images.map((img, i) => (
            <button
              key={i}
              onClick={e => { e.stopPropagation(); setIdx(i) }}
              className={cn(
                'h-14 w-14 rounded-lg overflow-hidden border-2 transition-all shrink-0',
                i === idx ? 'border-white scale-110 shadow-lg' : 'border-white/30 opacity-60 hover:opacity-100',
              )}
            >
              <img src={imgSrc(img)} alt="" className="h-full w-full object-cover" />
            </button>
          ))}
        </div>
      )}
    </div>
  )
}

// ─── Legacy custom field renderer (for CustomProductField) ──────────────────

function CustomFieldInput({
  field,
  value,
  onChange,
}: {
  field: CustomField
  value: string
  onChange: (val: string) => void
}) {
  if (field.field_type === 'boolean') {
    return (
      <label className="flex items-center gap-2 text-sm text-gray-600 cursor-pointer">
        <input
          type="checkbox"
          checked={value === 'true'}
          onChange={e => onChange(e.target.checked ? 'true' : 'false')}
          className="rounded"
        />
        {field.label}{field.required && ' *'}
      </label>
    )
  }
  if (field.field_type === 'select' && field.options) {
    return (
      <select
        required={field.required}
        value={value}
        onChange={e => onChange(e.target.value)}
        className="h-11 w-full rounded-lg border border-gray-300 bg-transparent px-4 py-2.5 text-sm text-gray-800 shadow-sm focus:border-indigo-300 focus:outline-none focus:ring-3 focus:ring-indigo-500/20"
      >
        <option value="">{field.label}</option>
        {field.options.map(opt => <option key={opt} value={opt}>{opt}</option>)}
      </select>
    )
  }
  return (
    <input
      type={field.field_type === 'number' ? 'number' : field.field_type === 'date' ? 'date' : 'text'}
      required={field.required}
      value={value}
      onChange={e => onChange(e.target.value)}
      placeholder={`${field.label}${field.required ? ' *' : ''}`}
      className="h-11 w-full rounded-lg border border-gray-300 bg-transparent px-4 py-2.5 text-sm text-gray-800 shadow-sm focus:border-indigo-300 focus:outline-none focus:ring-3 focus:ring-indigo-500/20"
    />
  )
}

// ─── Step 1: Product Type Picker ──────────────────────────────────────────────

function ProductTypePicker({
  onSelect,
  onClose,
}: {
  onSelect: (productType: ProductType) => void
  onClose: () => void
}) {
  const { data: productTypes = [], isLoading } = useProductTypes()

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 backdrop-blur-sm">
      <div className="w-full max-w-md bg-white rounded-2xl shadow-2xl overflow-hidden">
        {/* Header */}
        <div className="px-6 pt-6 pb-4 border-b border-gray-100">
          <h2 className="text-lg font-bold text-gray-900">Nuevo Producto</h2>
          <p className="text-sm text-gray-500 mt-0.5">Selecciona el tipo de producto que deseas crear</p>
        </div>

        {/* Type grid */}
        <div className="p-4 max-h-[60vh] overflow-y-auto">
          {isLoading ? (
            <div className="py-12 text-center text-sm text-gray-400">Cargando tipos...</div>
          ) : productTypes.length === 0 ? (
            <div className="py-12 text-center">
              <Tag className="h-10 w-10 text-gray-200 mx-auto mb-3" />
              <p className="text-sm font-medium text-gray-600 mb-1">Sin tipos de producto</p>
              <p className="text-xs text-gray-400">Crea tipos de producto en Configuraci&oacute;n antes de crear productos.</p>
            </div>
          ) : (
            <div className="grid grid-cols-2 gap-3">
              {productTypes.map(pt => (
                <button
                  key={pt.id}
                  onClick={() => onSelect(pt)}
                  className="flex flex-col items-center gap-2.5 rounded-2xl border border-gray-200 p-5 text-center hover:border-indigo-300 hover:bg-indigo-50/30 hover:shadow-sm transition-all group"
                >
                  <div
                    className="flex h-11 w-11 items-center justify-center rounded-xl transition-transform group-hover:scale-110"
                    style={{ backgroundColor: (pt.color ?? '#6366f1') + '15' }}
                  >
                    <Tag className="h-5 w-5" style={{ color: pt.color ?? '#6366f1' }} />
                  </div>
                  <div>
                    <span className="text-sm font-semibold text-gray-900 block">{pt.name}</span>
                    {pt.description && (
                      <span className="text-[11px] text-gray-400 mt-0.5 block line-clamp-2">{pt.description}</span>
                    )}
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-gray-100 bg-gray-50/50">
          <button onClick={onClose} className="w-full rounded-lg border border-gray-300 px-4 py-2 text-sm text-gray-600 hover:bg-gray-100 transition-colors">
            Cancelar
          </button>
        </div>
      </div>
    </div>
  )
}

// ─── Step 2: Create Product Form ──────────────────────────────────────────────

function CreateProductForm({
  productType,
  onBack,
  onClose,
}: {
  productType: ProductType
  onBack: () => void
  onClose: () => void
}) {
  const create = useCreateProduct()
  const toast = useToast()

  const [form, setForm] = useState({
    sku: '', name: '', description: '',
    unit_of_measure: 'un', cost_price: '0', sale_price: '0', reorder_point: '0',
    tax_rate_id: '',
    is_tax_exempt: false,
    retention_rate: '',
  })
  const [imageFiles, setImageFiles] = useState<File[]>([])
  const [imagePreviews, setImagePreviews] = useState<string[]>([])
  const createImgRef = useRef<HTMLInputElement>(null)
  const [attributes, setAttributes] = useState<Record<string, unknown>>({})

  // Custom fields from the selected product type template
  const { data: customFields = [] } = useCustomFields(productType.id)
  const activeFields = customFields.filter(f => f.is_active)
  const regularFields = activeFields.filter(f => f.field_type !== 'reference')

  const { data: taxRates = [] } = useTaxRates({ is_active: true })
  const ivaRates = taxRates.filter(r => r.tax_type === 'iva')
  const retentionRates = taxRates.filter(r => r.tax_type === 'retention')

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    try {
      const product = await create.mutateAsync({
        sku: form.sku,
        name: form.name,
        description: form.description || null,
        product_type_id: productType.id,
        unit_of_measure: form.unit_of_measure,
        cost_price: Number(form.cost_price),
        sale_price: Number(form.sale_price),
        reorder_point: Number(form.reorder_point),
        attributes: { ...attributes },
        tax_rate_id: form.tax_rate_id || null,
        is_tax_exempt: form.is_tax_exempt,
        retention_rate: form.retention_rate ? Number(form.retention_rate) / 100 : null,
      })
      // Upload images sequentially after creation
      if (imageFiles.length > 0) {
        const uploadImage = inventoryProductsApi.uploadImage
        for (const file of imageFiles) {
          try { await uploadImage(product.id, file) } catch { /* ignore individual failures */ }
        }
      }
      toast.success('Producto creado correctamente')
      onClose()
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Error al crear el producto'
      toast.error(msg)
    }
  }

  const cls = "h-11 w-full rounded-lg border border-gray-300 bg-transparent px-4 py-2.5 text-sm text-gray-800 shadow-sm focus:border-indigo-300 focus:outline-none focus:ring-3 focus:ring-indigo-500/20"

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 backdrop-blur-sm">
      <div className="w-full max-w-lg bg-white rounded-2xl shadow-2xl overflow-hidden max-h-[90vh] flex flex-col">
        {/* Header with product type badge */}
        <div className="px-6 pt-5 pb-4 border-b border-gray-100 shrink-0">
          <div className="flex items-center gap-3">
            <button onClick={onBack} className="rounded-lg p-1.5 text-gray-400 hover:text-gray-600 hover:bg-gray-100 transition-colors">
              <ArrowLeft className="h-4 w-4" />
            </button>
            <div
              className="flex h-9 w-9 items-center justify-center rounded-xl shrink-0"
              style={{ backgroundColor: (productType.color ?? '#6366f1') + '15' }}
            >
              <Tag className="h-4 w-4" style={{ color: productType.color ?? '#6366f1' }} />
            </div>
            <div className="flex-1 min-w-0">
              <h2 className="text-base font-bold text-gray-900">Nuevo {productType.name}</h2>
              {productType.description && (
                <p className="text-xs text-gray-400 truncate">{productType.description}</p>
              )}
            </div>
          </div>
        </div>

        {/* Scrollable form */}
        <div className="flex-1 overflow-y-auto px-6 py-5">
          <form id="create-product-form" onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-3">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs font-medium text-gray-600 mb-1 block">SKU *</label>
                  <input required value={form.sku} onChange={e => setForm(f => ({ ...f, sku: e.target.value }))} className={cls} />
                </div>
                <div>
                  <label className="text-xs font-medium text-gray-600 mb-1 block">Nombre *</label>
                  <input required value={form.name} onChange={e => setForm(f => ({ ...f, name: e.target.value }))} className={cls} />
                </div>
              </div>

              {/* Image upload */}
              <div>
                <label className="text-xs font-medium text-gray-600 mb-1 block">Fotos del producto</label>
                <div className="flex flex-wrap gap-2">
                  {imagePreviews.map((src, i) => (
                    <div key={i} className="relative h-16 w-16 rounded-lg overflow-hidden border border-gray-200 group">
                      <img src={src} alt="" className="h-full w-full object-cover" />
                      <button
                        type="button"
                        onClick={() => {
                          setImageFiles(f => f.filter((_, idx) => idx !== i))
                          setImagePreviews(p => p.filter((_, idx) => idx !== i))
                        }}
                        className="absolute inset-0 bg-black/50 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity"
                      >
                        <X className="h-4 w-4 text-white" />
                      </button>
                    </div>
                  ))}
                  <button
                    type="button"
                    onClick={() => createImgRef.current?.click()}
                    className="h-16 w-16 rounded-lg border-2 border-dashed border-gray-200 flex items-center justify-center text-gray-300 hover:border-indigo-300 hover:text-indigo-400 transition-colors"
                  >
                    <Camera className="h-5 w-5" />
                  </button>
                </div>
                <input
                  ref={createImgRef}
                  type="file"
                  accept="image/jpeg,image/png,image/webp,image/gif"
                  multiple
                  className="hidden"
                  onChange={e => {
                    const files = Array.from(e.target.files ?? [])
                    setImageFiles(prev => [...prev, ...files])
                    files.forEach(f => {
                      const reader = new FileReader()
                      reader.onload = ev => setImagePreviews(prev => [...prev, ev.target?.result as string])
                      reader.readAsDataURL(f)
                    })
                    e.target.value = ''
                  }}
                />
              </div>

              <div>
                <label className="text-xs font-medium text-gray-600 mb-1 block">Descripción</label>
                <textarea value={form.description} onChange={e => setForm(f => ({ ...f, description: e.target.value }))}
                  rows={2} placeholder="Descripción del producto"
                  className={cn(cls, 'resize-none')} />
              </div>

              <div>
                <label className="text-xs font-medium text-gray-600 mb-1 block">Unidad de medida</label>
                <select value={form.unit_of_measure} onChange={e => setForm(f => ({ ...f, unit_of_measure: e.target.value }))} className={cls}>
                  {['un', 'kg', 'lt', 'm', 'm2', 'caja', 'palet'].map(u => <option key={u}>{u}</option>)}
                </select>
              </div>

              <div className="grid grid-cols-3 gap-3">
                <div>
                  <label className="text-xs font-medium text-gray-600 mb-1 block">Precio costo</label>
                  <input type="number" step="0.01" value={form.cost_price} onChange={e => setForm(f => ({ ...f, cost_price: e.target.value }))} className={cls} />
                </div>
                <div>
                  <label className="text-xs font-medium text-gray-600 mb-1 block">Precio venta</label>
                  <input type="number" step="0.01" value={form.sale_price} onChange={e => setForm(f => ({ ...f, sale_price: e.target.value }))} className={cls} />
                </div>
                <div>
                  <label className="text-xs font-medium text-gray-600 mb-1 block">Pto. reorden</label>
                  <input type="number" value={form.reorder_point} onChange={e => setForm(f => ({ ...f, reorder_point: e.target.value }))} className={cls} />
                </div>
              </div>
            </div>

            {/* Tributación */}
            <div className="pt-3 space-y-3 border-t border-gray-100">
              <p className="text-xs font-semibold text-gray-400 uppercase tracking-wide flex items-center gap-1">
                <Receipt className="h-3.5 w-3.5" /> Tributación
              </p>
              <label className="flex items-center gap-2 text-sm text-gray-700 cursor-pointer">
                <input
                  type="checkbox"
                  checked={form.is_tax_exempt}
                  onChange={e => setForm(f => ({ ...f, is_tax_exempt: e.target.checked, tax_rate_id: e.target.checked ? '' : f.tax_rate_id }))}
                  className="rounded"
                />
                Producto exento de IVA
              </label>
              {!form.is_tax_exempt && (
                <div>
                  <label className="text-xs font-medium text-gray-600 mb-1 block">Tarifa IVA</label>
                  <select
                    value={form.tax_rate_id}
                    onChange={e => setForm(f => ({ ...f, tax_rate_id: e.target.value }))}
                    className={cls}
                  >
                    <option value="">IVA por defecto del tenant</option>
                    {ivaRates.map(r => (
                      <option key={r.id} value={r.id}>{r.name} ({(Number(r.rate) * 100).toFixed(0)}%)</option>
                    ))}
                  </select>
                </div>
              )}
              <div>
                <label className="text-xs font-medium text-gray-600 mb-1 block">Retención en la fuente</label>
                <select
                  value={form.retention_rate}
                  onChange={e => setForm(f => ({ ...f, retention_rate: e.target.value }))}
                  className={cls}
                >
                  <option value="">Sin retención</option>
                  {retentionRates.map(r => (
                    <option key={r.id} value={String(Number(r.rate) * 100)}>{r.name} ({(Number(r.rate) * 100).toFixed(2)}%)</option>
                  ))}
                </select>
              </div>
            </div>

            {/* Custom fields from product type template */}
            {regularFields.length > 0 && (
              <div className="pt-3 space-y-3 border-t border-gray-100">
                <p className="text-xs font-semibold text-gray-400 uppercase tracking-wide">
                  Campos de {productType.name}
                </p>
                {regularFields.map(field => (
                  <CustomFieldInput
                    key={field.id}
                    field={field}
                    value={String(attributes[field.field_key] ?? '')}
                    onChange={val => setAttributes(a => ({ ...a, [field.field_key]: val }))}
                  />
                ))}
              </div>
            )}
          </form>
        </div>

        {/* Footer */}
        <div className="flex gap-3 px-6 py-4 border-t border-gray-100 bg-gray-50/50 shrink-0">
          <button type="button" onClick={onClose}
            className="flex-1 rounded-lg border border-gray-300 px-4 py-2.5 text-sm text-gray-600 hover:bg-gray-100 transition-colors">
            Cancelar
          </button>
          <button type="submit" form="create-product-form" disabled={create.isPending}
            className="flex-1 rounded-lg bg-indigo-500 px-4 py-2.5 text-sm font-semibold text-white hover:bg-indigo-600 disabled:opacity-60 transition-colors">
            {create.isPending ? 'Guardando...' : `Crear ${productType.name}`}
          </button>
        </div>
      </div>
    </div>
  )
}

// ─── Create Product Modal (2-step flow) ───────────────────────────────────────

function CreateProductModal({ onClose }: { onClose: () => void }) {
  const [selectedType, setSelectedType] = useState<ProductType | null>(null)

  if (!selectedType) {
    return <ProductTypePicker onSelect={setSelectedType} onClose={onClose} />
  }

  return (
    <CreateProductForm
      productType={selectedType}
      onBack={() => setSelectedType(null)}
      onClose={onClose}
    />
  )
}

// ─── Customer Special Prices Section ──────────────────────────────────────────

function CustomerPricesSection({ productId }: { productId: string }) {
  const { data: prices = [], isLoading } = useCustomerPricesForProduct(productId)
  const [expanded, setExpanded] = useState(false)

  if (isLoading) return null
  if (!prices.length) return null

  return (
    <div className="border-t border-slate-100 pt-4">
      <button onClick={() => setExpanded(!expanded)}
        className="flex items-center gap-2 text-sm font-semibold text-slate-700 hover:text-indigo-600 w-full text-left">
        <DollarSign className="h-4 w-4" />
        Precios Especiales ({prices.length})
        <span className="ml-auto text-xs text-slate-400">{expanded ? '\u25B2' : '\u25BC'}</span>
      </button>
      {expanded && (
        <div className="mt-3 space-y-2">
          {prices.map((p: any) => (
            <div key={p.id} className="flex items-center justify-between rounded-xl bg-slate-50 px-3 py-2 text-xs">
              <span className="font-medium text-slate-700">{p.customer_name ?? 'Cliente'}</span>
              <div className="text-right">
                <span className="font-bold text-indigo-600">${Number(p.price).toFixed(2)}</span>
                {p.valid_to && <span className="ml-2 text-slate-400">hasta {new Date(p.valid_to).toLocaleDateString('es')}</span>}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

// ─── Adjust Stock Modal ──────────────────────────────────────────────────────

function AdjustStockModal({ productId, productName, onClose }: { productId: string; productName: string; onClose: () => void }) {
  const adjust = useAdjustStock()
  const { data: warehouses = [] } = useWarehouses()
  const [form, setForm] = useState({ warehouse_id: '', quantity: '', reason: '' })

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    await adjust.mutateAsync({
      product_id: productId,
      warehouse_id: form.warehouse_id,
      quantity: Number(form.quantity),
      reason: form.reason || undefined,
    })
    onClose()
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 backdrop-blur-sm">
      <div className="w-full max-w-sm bg-white rounded-3xl shadow-2xl p-6">
        <h2 className="text-lg font-bold text-slate-900 mb-1">Ajustar Stock</h2>
        <p className="text-sm text-slate-500 mb-4">{productName}</p>
        <form onSubmit={handleSubmit} className="space-y-3">
          <select required value={form.warehouse_id} onChange={e => setForm(f => ({ ...f, warehouse_id: e.target.value }))}
            className="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400">
            <option value="">Bodega *</option>
            {warehouses.map((w: any) => <option key={w.id} value={w.id}>{w.name}</option>)}
          </select>
          <input required type="number" step="1" value={form.quantity}
            onChange={e => setForm(f => ({ ...f, quantity: e.target.value }))}
            placeholder="Cantidad (+ entrada, - salida) *"
            className="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400" />
          <input value={form.reason} onChange={e => setForm(f => ({ ...f, reason: e.target.value }))}
            placeholder="Motivo"
            className="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400" />
          <div className="flex gap-3 pt-2">
            <button type="button" onClick={onClose}
              className="flex-1 rounded-xl border border-slate-200 px-4 py-2 text-sm text-slate-600 hover:bg-slate-50">Cancelar</button>
            <button type="submit" disabled={adjust.isPending}
              className="flex-1 rounded-xl bg-indigo-600 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-700 disabled:opacity-60">
              {adjust.isPending ? 'Ajustando...' : 'Ajustar'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

// ─── Product Drawer ───────────────────────────────────────────────────────────

function ProductDrawer({
  product: listProduct,
  productTypes,
  onClose,
}: {
  product: Product
  productTypes: ProductType[]
  onClose: () => void
}) {
  // Fetch full product detail (with has_movements)
  const { data: fullProduct } = useProduct(listProduct.id)
  const product = fullProduct ?? listProduct
  const hasMovements = product.has_movements ?? false

  const remove = useDeleteProduct()
  const update = useUpdateProduct()
  const uploadImage = useUploadProductImage()
  const deleteImage = useDeleteProductImage()
  const toast = useToast()
  const [editing, setEditing] = useState(false)
  const [confirmDelete, setConfirmDelete] = useState(false)
  const [lightboxIdx, setLightboxIdx] = useState<number | null>(null)
  const [showAdjust, setShowAdjust] = useState(false)
  const drawerImgRef = useRef<HTMLInputElement>(null)
  const { data: levels = [] } = useStockByProduct(product.id)
  const { data: warehouses = [] } = useWarehouses()
  const { data: suppliers = [] } = useSuppliers()
  const whMap = Object.fromEntries(warehouses.map(w => [w.id, w.name]))
  const typeName = productTypes.find(t => t.id === product.product_type_id)?.name

  const { data: taxRates = [] } = useTaxRates({ is_active: true })
  const ivaRates = taxRates.filter(r => r.tax_type === 'iva')
  const retentionRates = taxRates.filter(r => r.tax_type === 'retention')

  // Edit form state
  const [form, setForm] = useState({
    name: product.name,
    description: product.description ?? '',
    barcode: product.barcode ?? '',
    cost_price: String(product.cost_price),
    sale_price: String(product.sale_price),
    reorder_point: String(product.reorder_point),
    reorder_quantity: String(product.reorder_quantity),
    min_stock_level: String(product.min_stock_level),
    is_active: product.is_active,
    product_type_id: product.product_type_id ?? '',
    preferred_supplier_id: product.preferred_supplier_id ?? '',
    auto_reorder: product.auto_reorder ?? false,
    tax_rate_id: product.tax_rate_id ?? '',
    is_tax_exempt: product.is_tax_exempt ?? false,
    retention_rate: product.retention_rate ? String(Number(product.retention_rate) * 100) : '',
  })

  // Reset form when product changes or entering edit mode
  useEffect(() => {
    setForm({
      name: product.name,
      description: product.description ?? '',
      barcode: product.barcode ?? '',
      cost_price: String(product.cost_price),
      sale_price: String(product.sale_price),
      reorder_point: String(product.reorder_point),
      reorder_quantity: String(product.reorder_quantity),
      min_stock_level: String(product.min_stock_level),
      is_active: product.is_active,
      product_type_id: product.product_type_id ?? '',
      preferred_supplier_id: product.preferred_supplier_id ?? '',
      auto_reorder: product.auto_reorder ?? false,
      tax_rate_id: product.tax_rate_id ?? '',
      is_tax_exempt: product.is_tax_exempt ?? false,
      retention_rate: product.retention_rate ? String(Number(product.retention_rate) * 100) : '',
    })
  }, [product, editing])

  async function handleSave() {
    try {
      await update.mutateAsync({
        id: product.id,
        data: {
          name: form.name,
          description: form.description || null,
          barcode: form.barcode || null,
          cost_price: Number(form.cost_price) || 0,
          sale_price: Number(form.sale_price) || 0,
          reorder_point: Number(form.reorder_point),
          reorder_quantity: Number(form.reorder_quantity),
          min_stock_level: Number(form.min_stock_level),
          is_active: form.is_active,
          product_type_id: form.product_type_id || null,
          preferred_supplier_id: form.preferred_supplier_id || null,
          auto_reorder: form.auto_reorder,
          tax_rate_id: form.tax_rate_id || null,
          is_tax_exempt: form.is_tax_exempt,
          retention_rate: form.retention_rate ? Number(form.retention_rate) / 100 : null,
        },
      })
      toast.success('Producto actualizado')
      setEditing(false)
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : 'Error al actualizar')
    }
  }

  const cls = "h-11 w-full rounded-lg border border-gray-300 bg-transparent px-4 py-2.5 text-sm text-gray-800 shadow-sm focus:border-indigo-300 focus:outline-none focus:ring-3 focus:ring-indigo-500/20"

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-black/20 backdrop-blur-sm">
      <div className="w-full max-w-md bg-white h-full shadow-2xl flex flex-col">
        {/* Header */}
        <div className="p-6 pb-4 shrink-0">
          <div className="flex items-start justify-between">
            <div className="flex items-start gap-3 flex-1 min-w-0">
              {!editing && <ProductThumb images={product.images} name={product.name} size="md" />}
              <div className="flex-1 min-w-0">
              {editing ? (
                <input
                  value={form.name}
                  onChange={e => setForm(f => ({ ...f, name: e.target.value }))}
                  className="font-bold text-gray-900 w-full rounded-lg border border-gray-200 px-2 py-1 text-base focus:outline-none focus:ring-2 focus:ring-indigo-400"
                />
              ) : (
                <h2 className="font-bold text-gray-900">{product.name}</h2>
              )}
              <div className="flex items-center gap-2 mt-1">
                <p className="text-xs text-gray-400 font-mono">{product.sku}</p>
                {hasMovements && (
                  <span className="flex items-center gap-0.5 text-[10px] text-amber-600 bg-amber-50 rounded-full px-1.5 py-0.5">
                    <Lock className="h-2.5 w-2.5" /> Trazado
                  </span>
                )}
              </div>
              <div className="flex flex-wrap gap-1 mt-1">
                {typeName && (
                  <span className="inline-block rounded-full bg-indigo-100 text-indigo-700 text-xs px-2 py-0.5 font-medium">
                    {typeName}
                  </span>
                )}
                <span className={cn(
                  'rounded-full px-2 py-0.5 text-xs font-semibold',
                  product.is_active ? 'bg-emerald-50 text-emerald-700' : 'bg-gray-100 text-gray-500',
                )}>
                  {product.is_active ? 'Activo' : 'Inactivo'}
                </span>
              </div>
            </div>
            </div>
            <div className="flex items-center gap-1 ml-2">
              {!editing && (
                <button
                  onClick={() => setEditing(true)}
                  className="rounded-lg p-2 text-gray-400 hover:text-indigo-600 hover:bg-indigo-50 transition-colors"
                  title="Editar producto"
                >
                  <Pencil className="h-4 w-4" />
                </button>
              )}
              <button onClick={onClose} className="text-gray-400 hover:text-gray-600 text-xl font-bold">&times;</button>
            </div>
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto px-6 pb-6 space-y-4">
          {editing ? (
            /* ─── EDIT MODE ─── */
            <div className="space-y-4">
              {/* Locked fields info */}
              {hasMovements && (
                <div className="flex items-start gap-2 rounded-xl bg-amber-50 border border-amber-200 px-3 py-2.5">
                  <Lock className="h-4 w-4 text-amber-500 flex-shrink-0 mt-0.5" />
                  <div>
                    <p className="text-xs font-semibold text-amber-700">Campos protegidos</p>
                    <p className="text-xs text-amber-600 mt-0.5">
                      SKU, unidad de medida y rastreo por lotes no se pueden modificar porque el producto ya tiene movimientos de inventario.
                    </p>
                  </div>
                </div>
              )}

              {/* Image management in edit mode */}
              <div className="space-y-3">
                <p className="text-xs font-semibold text-gray-400 uppercase tracking-wide">Fotos</p>
                <div className="flex flex-wrap gap-2">
                  {(product.images ?? []).map((img, i) => (
                    <div key={i} className="relative h-16 w-16 rounded-lg overflow-hidden border border-gray-200 group">
                      <img src={imgSrc(img)} alt="" className="h-full w-full object-cover" />
                      <button
                        type="button"
                        onClick={() => deleteImage.mutate({ productId: product.id, imageUrl: img })}
                        className="absolute inset-0 bg-black/50 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity"
                      >
                        {deleteImage.isPending ? (
                          <Loader2 className="h-4 w-4 text-white animate-spin" />
                        ) : (
                          <Trash2 className="h-4 w-4 text-white" />
                        )}
                      </button>
                    </div>
                  ))}
                  <button
                    type="button"
                    onClick={() => drawerImgRef.current?.click()}
                    disabled={uploadImage.isPending}
                    className="h-16 w-16 rounded-lg border-2 border-dashed border-gray-200 flex items-center justify-center text-gray-300 hover:border-indigo-300 hover:text-indigo-400 transition-colors disabled:opacity-50"
                  >
                    {uploadImage.isPending ? (
                      <Loader2 className="h-5 w-5 animate-spin" />
                    ) : (
                      <Camera className="h-5 w-5" />
                    )}
                  </button>
                </div>
                <input
                  ref={drawerImgRef}
                  type="file"
                  accept="image/jpeg,image/png,image/webp,image/gif"
                  className="hidden"
                  onChange={e => {
                    const file = e.target.files?.[0]
                    if (file) uploadImage.mutate({ productId: product.id, file })
                    e.target.value = ''
                  }}
                />
              </div>

              {/* Identity section */}
              <div className="space-y-3">
                <p className="text-xs font-semibold text-gray-400 uppercase tracking-wide">Identidad</p>
                <div>
                  <label className="text-xs font-medium text-gray-600 mb-1 flex items-center gap-1">
                    SKU {hasMovements && <Lock className="h-3 w-3 text-amber-400" />}
                  </label>
                  <input
                    value={product.sku}
                    disabled
                    className={cn(cls, 'bg-gray-50 text-gray-400 cursor-not-allowed')}
                  />
                </div>
                <div>
                  <label className="text-xs font-medium text-gray-600 mb-1 block">Código de barras</label>
                  <input
                    value={form.barcode}
                    onChange={e => setForm(f => ({ ...f, barcode: e.target.value }))}
                    placeholder="Código de barras (opcional)"
                    className={cls}
                  />
                </div>
                <div>
                  <label className="text-xs font-medium text-gray-600 mb-1 block">Descripción</label>
                  <textarea
                    value={form.description}
                    onChange={e => setForm(f => ({ ...f, description: e.target.value }))}
                    rows={2}
                    placeholder="Descripción del producto"
                    className={cn(cls, 'resize-none')}
                  />
                </div>
              </div>

              {/* Classification */}
              <div className="space-y-3 pt-3 border-t border-gray-100">
                <p className="text-xs font-semibold text-gray-400 uppercase tracking-wide">Clasificación</p>
                <div>
                  <label className="text-xs font-medium text-gray-600 mb-1 block">Tipo de producto</label>
                  <select
                    value={form.product_type_id}
                    onChange={e => setForm(f => ({ ...f, product_type_id: e.target.value }))}
                    className={cls}
                  >
                    <option value="">Sin tipo</option>
                    {productTypes.map(t => <option key={t.id} value={t.id}>{t.name}</option>)}
                  </select>
                </div>
                <div>
                  <label className="text-xs font-medium text-gray-600 mb-1 flex items-center gap-1">
                    Estado
                  </label>
                  <label className="flex items-center gap-2 text-sm text-gray-600 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={form.is_active}
                      onChange={e => setForm(f => ({ ...f, is_active: e.target.checked }))}
                      className="rounded"
                    />
                    Producto activo
                  </label>
                </div>
              </div>

              {/* Pricing */}
              <div className="space-y-3 pt-3 border-t border-gray-100">
                <p className="text-xs font-semibold text-gray-400 uppercase tracking-wide">Precios</p>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="text-xs font-medium text-gray-600 mb-1 block">Precio costo</label>
                    <input
                      type="number"
                      step="0.01"
                      value={form.cost_price}
                      onChange={e => setForm(f => ({ ...f, cost_price: e.target.value }))}
                      className={cls}
                    />
                  </div>
                  <div>
                    <label className="text-xs font-medium text-gray-600 mb-1 block">Precio venta</label>
                    <input
                      type="number"
                      step="0.01"
                      value={form.sale_price}
                      onChange={e => setForm(f => ({ ...f, sale_price: e.target.value }))}
                      className={cls}
                    />
                  </div>
                </div>
              </div>

              {/* Tributación */}
              <div className="pt-3 space-y-3 border-t border-gray-100">
                <p className="text-xs font-semibold text-gray-400 uppercase tracking-wide flex items-center gap-1">
                  <Receipt className="h-3.5 w-3.5" /> Tributación
                </p>
                <label className="flex items-center gap-2 text-sm text-gray-700 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={form.is_tax_exempt}
                    onChange={e => setForm(f => ({ ...f, is_tax_exempt: e.target.checked, tax_rate_id: e.target.checked ? '' : f.tax_rate_id }))}
                    className="rounded"
                  />
                  Producto exento de IVA
                </label>
                {!form.is_tax_exempt && (
                  <div>
                    <label className="text-xs font-medium text-gray-600 mb-1 block">Tarifa IVA</label>
                    <select
                      value={form.tax_rate_id}
                      onChange={e => setForm(f => ({ ...f, tax_rate_id: e.target.value }))}
                      className={cls}
                    >
                      <option value="">IVA por defecto del tenant</option>
                      {ivaRates.map(r => (
                        <option key={r.id} value={r.id}>{r.name} ({(Number(r.rate) * 100).toFixed(0)}%)</option>
                      ))}
                    </select>
                  </div>
                )}
                <div>
                  <label className="text-xs font-medium text-gray-600 mb-1 block">Retención en la fuente</label>
                  <select
                    value={form.retention_rate}
                    onChange={e => setForm(f => ({ ...f, retention_rate: e.target.value }))}
                    className={cls}
                  >
                    <option value="">Sin retención</option>
                    {retentionRates.map(r => (
                      <option key={r.id} value={String(Number(r.rate) * 100)}>{r.name} ({(Number(r.rate) * 100).toFixed(2)}%)</option>
                    ))}
                  </select>
                </div>
              </div>

              {/* Inventory control */}
              <div className="space-y-3 pt-3 border-t border-gray-100">
                <p className="text-xs font-semibold text-gray-400 uppercase tracking-wide">Control de inventario</p>
                <div>
                  <label className="text-xs font-medium text-gray-600 mb-1 flex items-center gap-1">
                    Unidad de medida {hasMovements && <Lock className="h-3 w-3 text-amber-400" />}
                  </label>
                  <select
                    value={product.unit_of_measure}
                    disabled={hasMovements}
                    className={cn(cls, hasMovements && 'bg-gray-50 text-gray-400 cursor-not-allowed')}
                  >
                    {['un', 'kg', 'lt', 'm', 'm2', 'caja', 'palet'].map(u => <option key={u}>{u}</option>)}
                  </select>
                </div>
                <div className="grid grid-cols-3 gap-3">
                  <div>
                    <label className="text-xs font-medium text-gray-600 mb-1 block">Stock mín.</label>
                    <input
                      type="number"
                      value={form.min_stock_level}
                      onChange={e => setForm(f => ({ ...f, min_stock_level: e.target.value }))}
                      className={cls}
                    />
                  </div>
                  <div>
                    <label className="text-xs font-medium text-gray-600 mb-1 block">Pto. reorden</label>
                    <input
                      type="number"
                      value={form.reorder_point}
                      onChange={e => setForm(f => ({ ...f, reorder_point: e.target.value }))}
                      className={cls}
                    />
                  </div>
                  <div>
                    <label className="text-xs font-medium text-gray-600 mb-1 block">Cant. reorden</label>
                    <input
                      type="number"
                      value={form.reorder_quantity}
                      onChange={e => setForm(f => ({ ...f, reorder_quantity: e.target.value }))}
                      className={cls}
                    />
                  </div>
                </div>

                {/* Auto reorder section */}
                <div className="space-y-3 rounded-lg border border-gray-200 p-3">
                  <label className="flex items-center gap-2 text-sm cursor-pointer">
                    <input
                      type="checkbox"
                      checked={form.auto_reorder}
                      onChange={e => setForm(f => ({ ...f, auto_reorder: e.target.checked }))}
                      className="rounded"
                    />
                    <span className="font-medium text-gray-700">Reorden automatico</span>
                  </label>
                  {form.auto_reorder && (
                    <div>
                      <label className="text-xs font-medium text-gray-600 mb-1 block">Proveedor preferido</label>
                      <select
                        value={form.preferred_supplier_id}
                        onChange={e => setForm(f => ({ ...f, preferred_supplier_id: e.target.value }))}
                        className={cls}
                      >
                        <option value="">— Seleccionar proveedor —</option>
                        {suppliers.map(s => (
                          <option key={s.id} value={s.id}>{s.name}</option>
                        ))}
                      </select>
                    </div>
                  )}
                </div>

                <div>
                  <label className="text-xs font-medium text-gray-600 mb-1 flex items-center gap-1">
                    Rastreo por lotes {hasMovements && <Lock className="h-3 w-3 text-amber-400" />}
                  </label>
                  <label className={cn(
                    'flex items-center gap-2 text-sm text-gray-600',
                    hasMovements ? 'cursor-not-allowed opacity-60' : 'cursor-pointer',
                  )}>
                    <input
                      type="checkbox"
                      checked={product.track_batches}
                      disabled={hasMovements}
                      className="rounded"
                    />
                    Rastrear lotes
                  </label>
                </div>
              </div>

              {/* Save / Cancel */}
              <div className="flex gap-3 pt-4 border-t border-gray-100">
                <button
                  onClick={() => setEditing(false)}
                  className="flex-1 rounded-lg border border-gray-300 px-4 py-2.5 text-sm text-gray-600 hover:bg-gray-50 transition-colors"
                >
                  Cancelar
                </button>
                <button
                  onClick={handleSave}
                  disabled={update.isPending || !form.name.trim()}
                  className="flex-1 flex items-center justify-center gap-2 rounded-lg bg-indigo-500 px-4 py-2.5 text-sm font-semibold text-white hover:bg-indigo-600 disabled:opacity-60 transition-colors"
                >
                  <Save className="h-4 w-4" />
                  {update.isPending ? 'Guardando…' : 'Guardar cambios'}
                </button>
              </div>
            </div>
          ) : (
            /* ─── VIEW MODE ─── */
            <div className="space-y-4">
              {/* Product images */}
              {product.images && product.images.length > 0 && (
                <div>
                  <h3 className="text-xs font-bold text-gray-400 uppercase tracking-wide mb-2">Fotos</h3>
                  <div className="flex flex-wrap gap-2">
                    {product.images.map((img, i) => (
                      <button
                        key={i}
                        onClick={() => setLightboxIdx(i)}
                        className="group relative h-20 w-20 rounded-xl overflow-hidden border border-gray-200 shadow-sm hover:shadow-md hover:border-indigo-300 transition-all cursor-zoom-in"
                      >
                        <img src={imgSrc(img)} alt={product.name} className="h-full w-full object-cover" />
                        <div className="absolute inset-0 bg-black/0 group-hover:bg-black/20 transition-colors flex items-center justify-center">
                          <ZoomIn className="h-5 w-5 text-white opacity-0 group-hover:opacity-100 transition-opacity drop-shadow-lg" />
                        </div>
                      </button>
                    ))}
                  </div>
                  {lightboxIdx !== null && product.images && (
                    <ImageLightbox images={product.images} initial={lightboxIdx} onClose={() => setLightboxIdx(null)} />
                  )}
                </div>
              )}

              {/* Description */}
              {product.description && (
                <p className="text-sm text-gray-500">{product.description}</p>
              )}


              {/* Tax info */}
              <div>
                <h3 className="text-xs font-bold text-gray-400 uppercase tracking-wide mb-2">Tributación</h3>
                <div className="space-y-1 text-sm">
                  {product.is_tax_exempt ? (
                    <p className="text-amber-600 font-medium">Exento de IVA</p>
                  ) : (
                    <p className="text-gray-600">
                      IVA: {product.tax_rate_id
                        ? taxRates.find(r => r.id === product.tax_rate_id)?.name ?? 'Personalizado'
                        : 'Por defecto del tenant'}
                    </p>
                  )}
                  {product.retention_rate && Number(product.retention_rate) > 0 && (
                    <p className="text-gray-600">Retención: {(Number(product.retention_rate) * 100).toFixed(2)}%</p>
                  )}
                  {!product.is_tax_exempt && !product.tax_rate_id && !(product.retention_rate && Number(product.retention_rate) > 0) && (
                    <p className="text-gray-400 text-xs">Usa la tarifa por defecto del tenant</p>
                  )}
                </div>
              </div>

              <div>
                <h3 className="text-xs font-bold text-gray-400 uppercase tracking-wide mb-2">Stock por bodega</h3>
                {levels.length === 0 ? (
                  <p className="text-sm text-gray-400">Sin stock registrado</p>
                ) : (
                  <div className="space-y-2">
                    {levels.map(lv => {
                      const pct = lv.reorder_point > 0
                        ? Math.min(100, (Number(lv.qty_on_hand) / lv.reorder_point) * 100)
                        : 100
                      return (
                        <div key={lv.id} className="bg-gray-50 rounded-xl p-3">
                          <div className="flex justify-between text-sm mb-1">
                            <span className="font-medium text-gray-700">{whMap[lv.warehouse_id] ?? lv.warehouse_id}</span>
                            <span className="font-bold text-gray-900">{Number(lv.qty_on_hand).toFixed(2)}</span>
                          </div>
                          <div className="h-1.5 bg-gray-200 rounded-full overflow-hidden">
                            <div
                              className={cn('h-full rounded-full', pct >= 100 ? 'bg-emerald-500' : pct >= 50 ? 'bg-amber-500' : 'bg-red-500')}
                              style={{ width: `${pct}%` }}
                            />
                          </div>
                        </div>
                      )
                    })}
                  </div>
                )}
              </div>

              <div className="grid grid-cols-2 gap-3 pt-2">
                <div className="bg-gray-50 rounded-xl p-3">
                  <p className="text-xs text-gray-400">Costo</p>
                  <p className="font-bold text-gray-900">${Number(product.cost_price).toFixed(2)}</p>
                </div>
                <div className="bg-gray-50 rounded-xl p-3">
                  <p className="text-xs text-gray-400">Precio venta</p>
                  <p className="font-bold text-gray-900">${Number(product.sale_price).toFixed(2)}</p>
                </div>
                <div className="bg-gray-50 rounded-xl p-3">
                  <p className="text-xs text-gray-400">Reorden</p>
                  <p className="font-bold text-gray-900">{product.reorder_point}</p>
                </div>
                <div className="bg-gray-50 rounded-xl p-3">
                  <p className="text-xs text-gray-400">Unidad</p>
                  <p className="font-bold text-gray-900">{product.unit_of_measure}</p>
                </div>
              </div>

              {/* Auto reorder */}
              {product.auto_reorder && (
                <div className="bg-indigo-50 rounded-xl p-3">
                  <p className="text-xs text-indigo-500 font-medium">Reorden automatico activo</p>
                  <p className="text-sm text-gray-700 mt-0.5">
                    Proveedor: {suppliers.find(s => s.id === product.preferred_supplier_id)?.name ?? '—'}
                  </p>
                </div>
              )}

              {/* Barcode */}
              {product.barcode && (
                <div className="bg-gray-50 rounded-xl p-3">
                  <p className="text-xs text-gray-400">Código de barras</p>
                  <p className="font-mono text-sm text-gray-700">{product.barcode}</p>
                </div>
              )}

              {/* Custom attributes */}
              {product.attributes && Object.keys(product.attributes).length > 0 && (
                <div>
                  <h3 className="text-xs font-bold text-gray-400 uppercase tracking-wide mb-2">Atributos</h3>
                  <div className="space-y-1">
                    {Object.entries(product.attributes).map(([k, v]) => {
                      const displayValue = Array.isArray(v) ? v.join(', ')
                        : typeof v === 'boolean' ? (v ? 'Sí' : 'No')
                        : String(v)
                      return (
                        <div key={k} className="flex justify-between text-sm bg-gray-50 rounded-lg px-3 py-2">
                          <span className="text-xs text-gray-500">{k}</span>
                          <span className="font-medium text-gray-700">{displayValue}</span>
                        </div>
                      )
                    })}
                  </div>
                </div>
              )}

              {/* Customer Special Prices */}
              <CustomerPricesSection productId={product.id} />

              {/* Quick actions */}
              <div className="border-t border-gray-100 pt-4 flex flex-wrap gap-2">
                <button onClick={() => setShowAdjust(true)}
                  className="flex items-center gap-2 rounded-xl border border-slate-200 px-3 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-50">
                  <Sliders className="h-3.5 w-3.5" /> Ajustar stock
                </button>
              </div>

              {/* Delete */}
              <div className="pt-4 border-t border-gray-100">
                {confirmDelete ? (
                  <div className="rounded-xl border border-red-200 bg-red-50 p-3 space-y-2">
                    <p className="text-sm text-red-700 font-medium">¿Eliminar este producto?</p>
                    <p className="text-xs text-red-500">No se puede eliminar si tiene órdenes de compra activas o es componente de alguna receta.</p>
                    <div className="flex gap-2">
                      <button onClick={() => setConfirmDelete(false)}
                        className="flex-1 rounded-lg border border-gray-200 px-3 py-1.5 text-xs text-gray-600 hover:bg-white">
                        No, cancelar
                      </button>
                      <button disabled={remove.isPending}
                        onClick={async () => {
                          try {
                            await remove.mutateAsync(product.id)
                            onClose()
                          } catch (err: unknown) {
                            toast.error(err instanceof Error ? err.message : 'Error al eliminar')
                          }
                        }}
                        className="flex-1 rounded-lg bg-red-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-red-700 disabled:opacity-60">
                        {remove.isPending ? 'Eliminando…' : 'Sí, eliminar'}
                      </button>
                    </div>
                  </div>
                ) : (
                  <button onClick={() => setConfirmDelete(true)}
                    className="flex items-center gap-2 rounded-xl border border-red-200 px-4 py-2 text-sm text-red-500 hover:bg-red-50 hover:text-red-700 transition-colors">
                    <Trash2 className="h-4 w-4" /> Eliminar producto
                  </button>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
      {showAdjust && (
        <AdjustStockModal
          productId={product.id}
          productName={product.name}
          onClose={() => setShowAdjust(false)}
        />
      )}
    </div>
  )
}

// ─── Import CSV Modal ─────────────────────────────────────────────────────────

function ImportProductsModal({ onClose }: { onClose: () => void }) {
  const importCsv = useImportProductsCsv()
  const downloadTemplate = useDownloadTemplate()
  const toast = useToast()
  const fileRef = useRef<HTMLInputElement>(null)
  const [file, setFile] = useState<File | null>(null)
  const [result, setResult] = useState<{ created: number; skipped: number; errors: Array<{ row: number; field: string; message: string }> } | null>(null)

  const templates = [
    { key: 'basic', label: 'Básico' },
    { key: 'pet_food', label: 'Mascotas' },
    { key: 'technology', label: 'Tecnología' },
    { key: 'cleaning', label: 'Aseo' },
  ]

  async function handleUpload() {
    if (!file) return
    try {
      const res = await importCsv.mutateAsync(file)
      setResult(res)
      if (res.created > 0) toast.success(`${res.created} productos importados`)
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : 'Error al importar')
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 backdrop-blur-sm">
      <div className="w-full max-w-lg bg-white rounded-2xl shadow-2xl overflow-hidden max-h-[85vh] flex flex-col">
        {/* Header */}
        <div className="px-6 pt-5 pb-4 border-b border-gray-100 shrink-0 flex items-center justify-between">
          <div>
            <h2 className="text-base font-bold text-gray-900">Importar Productos CSV</h2>
            <p className="text-xs text-gray-400 mt-0.5">Sube un archivo CSV con tus productos</p>
          </div>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600"><X className="h-5 w-5" /></button>
        </div>

        <div className="flex-1 overflow-y-auto px-6 py-5 space-y-5">
          {/* Templates */}
          <div>
            <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">Descargar plantilla de ejemplo</p>
            <div className="flex flex-wrap gap-2">
              {templates.map(t => (
                <button
                  key={t.key}
                  onClick={() => downloadTemplate.mutate(t.key)}
                  disabled={downloadTemplate.isPending}
                  className="flex items-center gap-1.5 rounded-xl border border-gray-200 px-3 py-1.5 text-xs font-medium text-gray-600 hover:bg-gray-50 hover:border-indigo-300 transition-colors"
                >
                  <Download className="h-3 w-3" /> {t.label}
                </button>
              ))}
            </div>
          </div>

          {/* File picker */}
          <div>
            <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">Archivo CSV</p>
            <input
              ref={fileRef}
              type="file"
              accept=".csv,.txt"
              className="hidden"
              onChange={e => {
                setFile(e.target.files?.[0] ?? null)
                setResult(null)
              }}
            />
            <button
              onClick={() => fileRef.current?.click()}
              className="w-full flex items-center gap-3 rounded-2xl border-2 border-dashed border-gray-200 p-4 text-sm text-gray-500 hover:border-indigo-300 hover:bg-indigo-50/30 transition-colors"
            >
              <FileText className="h-5 w-5 text-gray-300" />
              {file ? (
                <span className="text-gray-700 font-medium">{file.name} <span className="text-gray-400">({(file.size / 1024).toFixed(1)} KB)</span></span>
              ) : (
                <span>Seleccionar archivo CSV...</span>
              )}
            </button>
          </div>

          {/* Results */}
          {result && (
            <div className="space-y-3">
              <div className="flex gap-3">
                <div className="flex-1 bg-emerald-50 rounded-xl p-3 text-center">
                  <p className="text-2xl font-bold text-emerald-700">{result.created}</p>
                  <p className="text-xs text-emerald-600">Creados</p>
                </div>
                <div className="flex-1 bg-amber-50 rounded-xl p-3 text-center">
                  <p className="text-2xl font-bold text-amber-700">{result.skipped}</p>
                  <p className="text-xs text-amber-600">Omitidos</p>
                </div>
              </div>
              {result.errors.length > 0 && (
                <div className="bg-red-50 rounded-xl p-3 max-h-40 overflow-y-auto">
                  <p className="text-xs font-semibold text-red-600 mb-1">Errores ({result.errors.length})</p>
                  {result.errors.map((err, i) => (
                    <p key={i} className="text-xs text-red-500">
                      Fila {err.row}{err.field ? ` [${err.field}]` : ''}: {err.message}
                    </p>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex gap-3 px-6 py-4 border-t border-gray-100 bg-gray-50/50 shrink-0">
          <button onClick={onClose} className="flex-1 rounded-lg border border-gray-300 px-4 py-2.5 text-sm text-gray-600 hover:bg-gray-100 transition-colors">
            {result ? 'Cerrar' : 'Cancelar'}
          </button>
          {!result && (
            <button
              onClick={handleUpload}
              disabled={!file || importCsv.isPending}
              className="flex-1 flex items-center justify-center gap-2 rounded-lg bg-indigo-500 px-4 py-2.5 text-sm font-semibold text-white hover:bg-indigo-600 disabled:opacity-60 transition-colors"
            >
              <Upload className="h-4 w-4" />
              {importCsv.isPending ? 'Importando...' : 'Subir'}
            </button>
          )}
        </div>
      </div>
    </div>
  )
}

// ─── Main Page ────────────────────────────────────────────────────────────────

type SortKey = 'sku' | 'name' | 'cost_price' | 'unit_of_measure' | 'is_active'
type SortDir = 'asc' | 'desc'

const COLUMNS: { key: string; label: string; sortable?: SortKey }[] = [
  { key: 'photo', label: '' },
  { key: 'sku', label: 'SKU', sortable: 'sku' },
  { key: 'name', label: 'Nombre', sortable: 'name' },
  { key: 'type', label: 'Tipo' },
  { key: 'terms', label: 'Términos' },
  { key: 'unit', label: 'Unidad', sortable: 'unit_of_measure' },
  { key: 'cost', label: 'Costo', sortable: 'cost_price' },
  { key: 'created_by', label: 'Creado por' },
  { key: 'status', label: 'Estado', sortable: 'is_active' },
]

export function ProductsPage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const stockStatusParam = searchParams.get('stock_status') as 'low' | 'out' | null

  const [search, setSearch] = useState('')
  const [filterType, setFilterType] = useState('')
  const [showCreate, setShowCreate] = useState(false)
  const [showImport, setShowImport] = useState(false)
  const [selected, setSelected] = useState<Product | null>(null)

  // Datatable state
  const [perPage, setPerPage] = useState(10)
  const [currentPage, setCurrentPage] = useState(1)
  const [sortBy, setSortBy] = useState<SortKey | null>(null)
  const [sortDir, setSortDir] = useState<SortDir>('asc')

  const { data, isLoading } = useProducts({
    search: search || undefined,
    stock_status: stockStatusParam || undefined,
  })
  const { data: productTypes = [] } = useProductTypes()
  const { resolve } = useUserLookup(data?.items.map(p => p.created_by) ?? [])

  // Filter
  const allItems = data?.items ?? []
  const filtered = useMemo(() => {
    let items = allItems
    if (filterType) items = items.filter(p => p.product_type_id === filterType)
    return items
  }, [allItems, filterType])

  // Sort
  const sorted = useMemo(() => {
    if (!sortBy) return filtered
    const arr = [...filtered]
    arr.sort((a, b) => {
      let va: string | number | boolean = ''
      let vb: string | number | boolean = ''
      if (sortBy === 'sku') { va = a.sku; vb = b.sku }
      else if (sortBy === 'name') { va = a.name; vb = b.name }
      else if (sortBy === 'cost_price') { va = Number(a.cost_price); vb = Number(b.cost_price) }
      else if (sortBy === 'unit_of_measure') { va = a.unit_of_measure; vb = b.unit_of_measure }
      else if (sortBy === 'is_active') { va = a.is_active ? 1 : 0; vb = b.is_active ? 1 : 0 }
      if (va < vb) return sortDir === 'asc' ? -1 : 1
      if (va > vb) return sortDir === 'asc' ? 1 : -1
      return 0
    })
    return arr
  }, [filtered, sortBy, sortDir])

  // Pagination
  const totalEntries = sorted.length
  const totalPages = Math.max(1, Math.ceil(totalEntries / perPage))
  const safePage = Math.min(currentPage, totalPages)
  const startIdx = (safePage - 1) * perPage
  const endIdx = Math.min(startIdx + perPage, totalEntries)
  const pageItems = sorted.slice(startIdx, endIdx)

  // Reset page on filter/search/perPage change
  useEffect(() => { setCurrentPage(1) }, [search, filterType, perPage])

  function handleSort(key: SortKey) {
    if (sortBy === key) {
      setSortDir(d => d === 'asc' ? 'desc' : 'asc')
    } else {
      setSortBy(key)
      setSortDir('asc')
    }
  }

  function SortIcon({ col }: { col: SortKey }) {
    if (sortBy !== col) return <ArrowUpDown className="h-3.5 w-3.5 text-gray-300" />
    return sortDir === 'asc'
      ? <ArrowUp className="h-3.5 w-3.5 text-indigo-500" />
      : <ArrowDown className="h-3.5 w-3.5 text-indigo-500" />
  }

  // Page numbers to show
  const pageNumbers: (number | '...')[] = useMemo(() => {
    if (totalPages <= 7) return Array.from({ length: totalPages }, (_, i) => i + 1)
    const pages: (number | '...')[] = [1]
    if (safePage > 3) pages.push('...')
    const start = Math.max(2, safePage - 1)
    const end = Math.min(totalPages - 1, safePage + 1)
    for (let i = start; i <= end; i++) pages.push(i)
    if (safePage < totalPages - 2) pages.push('...')
    pages.push(totalPages)
    return pages
  }, [totalPages, safePage])

  return (
    <div className="space-y-6">
      {/* Breadcrumb */}
      <nav className="mb-4">
        <ol className="flex items-center gap-2 text-sm">
          <li className="text-gray-500">Inventario</li>
          <li><ChevronRight className="h-4 w-4 text-gray-400" /></li>
          <li className="text-indigo-500">Productos</li>
        </ol>
      </nav>

      {/* Header */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-xl sm:text-2xl font-semibold text-gray-800">Productos</h1>
          <p className="text-sm text-gray-500 mt-1">Gestiona el catálogo de productos de tu organización</p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => setShowImport(true)}
            className="flex items-center gap-2 rounded-lg border border-gray-300 bg-white px-3 sm:px-4 py-2 sm:py-2.5 text-sm font-medium text-gray-700 hover:bg-gray-50 shadow-sm transition"
          >
            <Upload className="h-4 w-4" /> <span className="hidden sm:inline">Importar</span> CSV
          </button>
          <button
            onClick={() => setShowCreate(true)}
            className="flex items-center gap-2 rounded-lg bg-indigo-500 px-3 sm:px-4 py-2 sm:py-2.5 text-sm font-medium text-white hover:bg-indigo-600 shadow-sm transition"
          >
            <Plus className="h-4 w-4" /> Nuevo
          </button>
        </div>
      </div>

      {/* Stock status filter banner */}
      {stockStatusParam && (
        <div className={cn(
          'flex items-center gap-3 rounded-xl border px-4 py-3',
          stockStatusParam === 'out' ? 'bg-red-50 border-red-200' : 'bg-amber-50 border-amber-200',
        )}>
          {stockStatusParam === 'out' ? (
            <AlertTriangle className="h-5 w-5 text-red-500 shrink-0" />
          ) : (
            <TrendingDown className="h-5 w-5 text-amber-500 shrink-0" />
          )}
          <div className="flex-1">
            <p className={cn('text-sm font-semibold', stockStatusParam === 'out' ? 'text-red-800' : 'text-amber-800')}>
              {stockStatusParam === 'out' ? 'Productos sin stock' : 'Productos con stock bajo'}
            </p>
            <p className="text-xs text-slate-500 mt-0.5">
              {stockStatusParam === 'out'
                ? 'Productos agotados que tienen umbral de stock configurado. Edita un producto para reabastecer o ajustar umbrales.'
                : 'Productos cuyo stock actual esta por debajo del punto de reorden. Haz clic en un producto para editarlo.'}
            </p>
          </div>
          <button
            onClick={() => { searchParams.delete('stock_status'); setSearchParams(searchParams) }}
            className={cn(
              'shrink-0 flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-medium transition',
              stockStatusParam === 'out' ? 'bg-red-100 text-red-700 hover:bg-red-200' : 'bg-amber-100 text-amber-700 hover:bg-amber-200',
            )}
          >
            <X className="h-3.5 w-3.5" /> Quitar filtro
          </button>
        </div>
      )}

      {/* Datatable card */}
      <div className="overflow-hidden rounded-xl border border-gray-200 bg-white">
        {/* Top controls: entries selector + type filter + search */}
        <div className="flex flex-col gap-3 px-5 py-4 sm:flex-row sm:items-center sm:justify-between border-b border-gray-100">
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-2 text-sm text-gray-600">
              <span>Mostrar</span>
              <select
                value={perPage}
                onChange={e => setPerPage(Number(e.target.value))}
                className="h-9 rounded-lg border border-gray-300 bg-transparent px-2 py-1 text-sm text-gray-800 focus:border-indigo-300 focus:outline-none focus:ring-3 focus:ring-indigo-500/20"
              >
                {[5, 10, 25, 50].map(n => <option key={n} value={n}>{n}</option>)}
              </select>
              <span>registros</span>
            </div>
            {productTypes.length > 0 && (
              <select
                value={filterType}
                onChange={e => setFilterType(e.target.value)}
                className="h-9 rounded-lg border border-gray-300 bg-transparent px-3 py-1 text-sm text-gray-800 focus:border-indigo-300 focus:outline-none focus:ring-3 focus:ring-indigo-500/20"
              >
                <option value="">Todos los tipos</option>
                {productTypes.map(t => <option key={t.id} value={t.id}>{t.name}</option>)}
              </select>
            )}
          </div>
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
            <input
              value={search}
              onChange={e => setSearch(e.target.value)}
              placeholder="Buscar..."
              className="h-9 w-full rounded-lg border border-gray-300 bg-transparent pl-9 pr-4 py-1 text-sm text-gray-800 placeholder:text-gray-400 focus:border-indigo-300 focus:outline-none focus:ring-3 focus:ring-indigo-500/20 sm:w-64"
            />
          </div>
        </div>

        {/* Table / Cards */}
        {isLoading ? (
          <div className="p-12 text-center text-gray-400">Cargando...</div>
        ) : totalEntries === 0 ? (
          <div className="p-12 text-center">
            <Package className="h-10 w-10 text-gray-200 mx-auto mb-3" />
            <p className="text-sm text-gray-500">Sin productos encontrados.</p>
          </div>
        ) : (
          <>
            {/* Mobile cards */}
            <div className="space-y-3 p-4 md:hidden">
              {pageItems.map(p => {
                const pType = productTypes.find(t => t.id === p.product_type_id)
                return (
                  <div
                    key={p.id}
                    onClick={() => setSelected(p)}
                    className="rounded-xl border border-gray-200 bg-white p-4 shadow-sm cursor-pointer hover:border-indigo-200 hover:shadow-md transition-all active:scale-[0.99] space-y-2"
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div className="flex items-center gap-3 min-w-0">
                        <ProductThumb images={p.images} name={p.name} size="md" />
                        <div className="min-w-0">
                          <p className="font-medium text-gray-800 truncate">{p.name}</p>
                          <p className="font-mono text-xs text-gray-400 mt-0.5">{p.sku}</p>
                        </div>
                      </div>
                      <span className={cn(
                        'rounded-full px-2.5 py-0.5 text-xs font-medium shrink-0',
                        p.is_active ? 'bg-emerald-50 text-emerald-700' : 'bg-gray-100 text-gray-500',
                      )}>
                        {p.is_active ? 'Activo' : 'Inactivo'}
                      </span>
                    </div>
                    <div className="flex flex-wrap items-center gap-2">
                      {pType && (
                        <span className="rounded-full px-2.5 py-0.5 text-xs font-medium text-white" style={{ backgroundColor: pType.color ?? '#6366f1' }}>
                          {pType.name}
                        </span>
                      )}
                      <span className="text-xs text-gray-500">{p.unit_of_measure}</span>
                      <span className="text-xs font-medium text-gray-700">${Number(p.cost_price).toFixed(2)}</span>
                    </div>
                    {p.terms && p.terms.length > 0 && (
                      <div className="flex flex-wrap gap-1">
                        {p.terms.slice(0, 3).map(t => (
                          <span key={t.term_id} className="rounded-full bg-violet-50 text-violet-700 px-2 py-0.5 text-[10px] font-medium">{t.term_name}</span>
                        ))}
                        {p.terms.length > 3 && <span className="text-[10px] text-gray-400">+{p.terms.length - 3}</span>}
                      </div>
                    )}
                  </div>
                )
              })}
            </div>

            {/* Desktop table */}
            <div className="hidden md:block max-w-full overflow-x-auto">
              <table className="min-w-full">
                <thead>
                  <tr className="border-b border-gray-100 bg-gray-50/50">
                    {COLUMNS.map(col => (
                      <th
                        key={col.key}
                        className={cn(
                          'px-5 py-3 text-start text-sm font-medium text-gray-500 whitespace-nowrap',
                          col.sortable && 'cursor-pointer select-none hover:text-gray-700',
                        )}
                        onClick={col.sortable ? () => handleSort(col.sortable!) : undefined}
                      >
                        <span className="inline-flex items-center gap-1.5">
                          {col.label}
                          {col.sortable && <SortIcon col={col.sortable} />}
                        </span>
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {pageItems.map(p => {
                    const pType = productTypes.find(t => t.id === p.product_type_id)
                    return (
                      <tr
                        key={p.id}
                        onClick={() => setSelected(p)}
                        className="cursor-pointer hover:bg-gray-50/50 transition-colors"
                      >
                        <td className="px-3 py-3 w-12">
                          <ProductThumb images={p.images} name={p.name} />
                        </td>
                        <td className="px-5 py-4 font-mono text-xs text-gray-500">{p.sku}</td>
                        <td className="px-5 py-4 font-medium text-gray-800">{p.name}</td>
                        <td className="px-5 py-4">
                          {pType ? (
                            <span
                              className="rounded-full px-2.5 py-0.5 text-xs font-medium text-white"
                              style={{ backgroundColor: pType.color ?? '#6366f1' }}
                            >
                              {pType.name}
                            </span>
                          ) : <span className="text-gray-300 text-xs">—</span>}
                        </td>
                        <td className="px-5 py-4">
                          {p.terms && p.terms.length > 0 ? (
                            <div className="flex flex-wrap gap-1">
                              {p.terms.slice(0, 3).map(t => (
                                <span key={t.term_id} className="rounded-full bg-violet-50 text-violet-700 px-2 py-0.5 text-[10px] font-medium">
                                  {t.term_name}
                                </span>
                              ))}
                              {p.terms.length > 3 && (
                                <span className="text-[10px] text-gray-400">+{p.terms.length - 3}</span>
                              )}
                            </div>
                          ) : <span className="text-gray-300 text-xs">—</span>}
                        </td>
                        <td className="px-5 py-4 text-gray-500 text-sm">{p.unit_of_measure}</td>
                        <td className="px-5 py-4 text-gray-500 text-sm">${Number(p.cost_price).toFixed(2)}</td>
                        <td className="px-5 py-4 text-gray-400 text-xs">{resolve(p.created_by)}</td>
                        <td className="px-5 py-4">
                          <span className={cn(
                            'rounded-full px-2.5 py-0.5 text-xs font-medium',
                            p.is_active ? 'bg-emerald-50 text-emerald-700' : 'bg-gray-100 text-gray-500',
                          )}>
                            {p.is_active ? 'Activo' : 'Inactivo'}
                          </span>
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          </>
        )}

        {/* Bottom: showing info + pagination */}
        {totalEntries > 0 && (
          <div className="flex flex-col gap-3 px-5 py-4 sm:flex-row sm:items-center sm:justify-between border-t border-gray-100">
            <p className="text-sm text-gray-500">
              Mostrando <span className="font-medium text-gray-800">{startIdx + 1}</span> a{' '}
              <span className="font-medium text-gray-800">{endIdx}</span> de{' '}
              <span className="font-medium text-gray-800">{totalEntries}</span> registros
            </p>
            <nav className="flex items-center gap-1">
              <button
                onClick={() => setCurrentPage(1)}
                disabled={safePage <= 1}
                className="flex h-8 w-8 items-center justify-center rounded-lg border border-gray-200 text-gray-500 transition hover:bg-gray-50 hover:text-gray-700 disabled:opacity-40 disabled:pointer-events-none"
              >
                <ChevronsLeft className="h-4 w-4" />
              </button>
              <button
                onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
                disabled={safePage <= 1}
                className="flex h-8 w-8 items-center justify-center rounded-lg border border-gray-200 text-gray-500 transition hover:bg-gray-50 hover:text-gray-700 disabled:opacity-40 disabled:pointer-events-none"
              >
                <ChevronLeft className="h-4 w-4" />
              </button>
              {pageNumbers.map((pg, i) =>
                pg === '...' ? (
                  <span key={`dots-${i}`} className="flex h-8 w-8 items-center justify-center text-sm text-gray-400">...</span>
                ) : (
                  <button
                    key={pg}
                    onClick={() => setCurrentPage(pg)}
                    className={cn(
                      'flex h-8 w-8 items-center justify-center rounded-lg text-sm font-medium transition',
                      safePage === pg
                        ? 'bg-indigo-500 text-white shadow-sm'
                        : 'border border-gray-200 text-gray-600 hover:bg-gray-50 hover:text-gray-800',
                    )}
                  >
                    {pg}
                  </button>
                )
              )}
              <button
                onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))}
                disabled={safePage >= totalPages}
                className="flex h-8 w-8 items-center justify-center rounded-lg border border-gray-200 text-gray-500 transition hover:bg-gray-50 hover:text-gray-700 disabled:opacity-40 disabled:pointer-events-none"
              >
                <ChevronRight className="h-4 w-4" />
              </button>
              <button
                onClick={() => setCurrentPage(totalPages)}
                disabled={safePage >= totalPages}
                className="flex h-8 w-8 items-center justify-center rounded-lg border border-gray-200 text-gray-500 transition hover:bg-gray-50 hover:text-gray-700 disabled:opacity-40 disabled:pointer-events-none"
              >
                <ChevronsRight className="h-4 w-4" />
              </button>
            </nav>
          </div>
        )}
      </div>

      {showImport && <ImportProductsModal onClose={() => setShowImport(false)} />}
      {showCreate && <CreateProductModal onClose={() => setShowCreate(false)} />}
      {selected && (
        <ProductDrawer
          product={selected}
          productTypes={productTypes}
          onClose={() => setSelected(null)}
        />
      )}
    </div>
  )
}
