import { useState, useRef, useEffect, useMemo } from 'react'
import { useSearchParams, useLocation } from 'react-router-dom'
import { Plus, Search, Package, Tag, ArrowLeft, Upload, Download, X, FileText, Trash2, Pencil, Lock, Save, ChevronRight, ChevronLeft, ChevronsLeft, ChevronsRight, ArrowUpDown, ArrowUp, ArrowDown, AlertTriangle, TrendingDown, Camera, ImageIcon, Loader2, ZoomIn, DollarSign, Sliders, Receipt, Warehouse } from 'lucide-react'
import {
  useProducts, useProduct, useCreateProduct, useUpdateProduct, useDeleteProduct,
  useStockByProduct, useWarehouses, useProductTypes, useCustomFields, useCategories,
  useImportProductsCsv, useDownloadTemplate,
  useUploadProductImage, useDeleteProductImage,
  useSuppliers,
  useCustomerPricesForProduct, useAdjustStock,
  useTaxRates, useStockAvailability,
  useProductVariantsForProduct,
  useCreateVariant, useUpdateVariant, useDeleteVariant,
  useInventoryAnalytics,
} from '@/hooks/useInventory'
import { useToast } from '@/store/toast'
import { useFormValidation } from '@/hooks/useFormValidation'
import { cn } from '@/lib/utils'
import { CopyableId } from '@/components/inventory/CopyableId'
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs'
import type { CustomField, Product, ProductType, ProductVariant } from '@/types/inventory'
import { inventoryProductsApi } from '@/lib/inventory-api'
import MediaPickerModal from '@/components/compliance/MediaPickerModal'

const INV_API_BASE = import.meta.env.VITE_INVENTORY_API_URL ?? 'http://localhost:9003'
const MEDIA_API_BASE = import.meta.env.VITE_MEDIA_API_URL ?? 'http://localhost:9007'

function imgSrc(img: string | { media_file_id?: string; url?: string }) {
  // New format: { media_file_id, url } — url is relative to media-service
  if (typeof img === 'object' && img.url) {
    return img.url.startsWith('http') ? img.url : `${MEDIA_API_BASE}${img.url}`
  }
  // Legacy format: plain string URL — relative to inventory-service
  const url = typeof img === 'string' ? img : ''
  if (url.startsWith('http')) return url
  if (url.startsWith('/uploads/media/')) return `${MEDIA_API_BASE}${url}`
  return `${INV_API_BASE}${url}`
}

// ─── Product thumbnail (reused in table + cards) ────────────────────────────

function ProductThumb({ images, name, size = 'sm' }: { images?: (string | { media_file_id?: string; url?: string })[]; name: string; size?: 'sm' | 'md' | 'lg' }) {
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
        className="h-11 w-full rounded-lg border border-gray-300 bg-transparent px-4 py-2.5 text-sm text-gray-800 shadow-sm focus:border-primary/50 focus:outline-none focus:ring-3 focus:ring-ring/20"
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
      className="h-11 w-full rounded-lg border border-gray-300 bg-transparent px-4 py-2.5 text-sm text-gray-800 shadow-sm focus:border-primary/50 focus:outline-none focus:ring-3 focus:ring-ring/20"
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
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <button onClick={onClose} className="rounded-lg p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100 transition-colors">
          <ArrowLeft className="h-5 w-5" />
        </button>
        <div>
          <h1 className="text-xl font-bold text-gray-900">Nuevo Producto</h1>
          <p className="text-sm text-gray-500">Selecciona el tipo de producto que deseas crear</p>
        </div>
      </div>

      {/* Type grid */}
      {isLoading ? (
        <div className="py-12 text-center text-sm text-gray-400">Cargando tipos...</div>
      ) : productTypes.length === 0 ? (
        <div className="py-12 text-center">
          <Tag className="h-10 w-10 text-gray-200 mx-auto mb-3" />
          <p className="text-sm font-medium text-gray-600 mb-1">Sin tipos de producto</p>
          <p className="text-xs text-gray-400">Crea tipos de producto en Configuración antes de crear productos.</p>
        </div>
      ) : (
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4">
          {productTypes.map(pt => (
            <button
              key={pt.id}
              onClick={() => onSelect(pt)}
              className="flex flex-col items-center gap-3 rounded-2xl border border-gray-200 bg-white p-6 text-center hover:border-primary/50 hover:bg-primary/5 hover:shadow-md transition-all group"
            >
              <div
                className="flex h-14 w-14 items-center justify-center rounded-xl transition-transform group-hover:scale-110"
                style={{ backgroundColor: (pt.color ?? '#6366f1') + '15' }}
              >
                <Tag className="h-6 w-6" style={{ color: pt.color ?? '#6366f1' }} />
              </div>
              <div>
                <span className="text-sm font-semibold text-gray-900 block">{pt.name}</span>
                {pt.description && (
                  <span className="text-xs text-gray-400 mt-1 block line-clamp-2">{pt.description}</span>
                )}
              </div>
            </button>
          ))}
        </div>
      )}
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
    unit_of_measure: 'un', reorder_point: '0',
    tax_rate_id: '',
    is_tax_exempt: false,
    retention_rate: '',
    category_id: '',
  })
  const [imageFiles, setImageFiles] = useState<File[]>([])
  const [imagePreviews, setImagePreviews] = useState<string[]>([])
  const createImgRef = useRef<HTMLInputElement>(null)
  const [attributes, setAttributes] = useState<Record<string, unknown>>({})

  // Custom fields from the selected product type template
  const { data: customFields = [] } = useCustomFields(productType.id)
  const activeFields = customFields.filter(f => f.is_active)
  const regularFields = activeFields.filter(f => f.field_type !== 'reference')

  const { data: categoriesData } = useCategories()
  const categories = categoriesData?.items ?? []
  const { data: taxRates = [] } = useTaxRates({ is_active: true })
  const ivaRates = taxRates.filter(r => r.tax_type === 'iva')
  const retentionRates = taxRates.filter(r => r.tax_type === 'retention')

  const { formRef: createFormRef, handleSubmit: validateAndCreate } = useFormValidation(doCreate)

  async function doCreate() {
    try {
      const product = await create.mutateAsync({
        sku: form.sku,
        name: form.name,
        description: form.description || null,
        product_type_id: productType.id,
        category_id: form.category_id || null,
        unit_of_measure: form.unit_of_measure,
        reorder_point: Number(form.reorder_point),
        valuation_method: productType.dispatch_rule === 'fifo' ? 'fifo' : 'weighted_average',
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

  const cls = "h-11 w-full rounded-lg border border-gray-300 bg-transparent px-4 py-2.5 text-sm text-gray-800 shadow-sm focus:border-primary/50 focus:outline-none focus:ring-3 focus:ring-ring/20"

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <button onClick={onBack} className="rounded-lg p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100 transition-colors">
          <ArrowLeft className="h-5 w-5" />
        </button>
        <div
          className="flex h-10 w-10 items-center justify-center rounded-xl shrink-0"
          style={{ backgroundColor: (productType.color ?? '#6366f1') + '15' }}
        >
          <Tag className="h-5 w-5" style={{ color: productType.color ?? '#6366f1' }} />
        </div>
        <div className="flex-1 min-w-0">
          <h1 className="text-xl font-bold text-gray-900">Nuevo {productType.name}</h1>
          {productType.description && (
            <p className="text-sm text-gray-400 truncate">{productType.description}</p>
          )}
        </div>
      </div>

      {/* Form */}
      <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-6">
        <form id="create-product-form" ref={createFormRef} onSubmit={validateAndCreate} className="space-y-5" noValidate>
          <div className="space-y-4">
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

              <div>
                <label className="text-xs font-medium text-gray-600 mb-1 block">Categoría</label>
                <select value={form.category_id} onChange={e => setForm(f => ({ ...f, category_id: e.target.value }))} className={cls}>
                  <option value="">Sin categoría</option>
                  {categories.map(c => (
                    <option key={c.id} value={c.id}>{c.name}</option>
                  ))}
                </select>
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
                    className="h-16 w-16 rounded-lg border-2 border-dashed border-gray-200 flex items-center justify-center text-gray-300 hover:border-primary/50 hover:text-primary/70 transition-colors"
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

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs font-medium text-gray-600 mb-1 block">Pto. reorden</label>
                  <input type="number" value={form.reorder_point} onChange={e => setForm(f => ({ ...f, reorder_point: e.target.value }))} className={cls} />
                </div>
                <p className="text-xs text-gray-500 self-end pb-3">Los precios se calculan automáticamente al recibir órdenes de compra.</p>
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

        {/* Footer */}
        <div className="flex gap-3 pt-5 border-t border-gray-100">
          <button type="button" onClick={onClose}
            className="rounded-lg border border-gray-300 px-6 py-2.5 text-sm text-gray-600 hover:bg-gray-100 transition-colors">
            Cancelar
          </button>
          <button type="submit" form="create-product-form" disabled={create.isPending}
            className="rounded-lg bg-primary px-6 py-2.5 text-sm font-semibold text-white hover:bg-primary disabled:opacity-60 transition-colors">
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
        className="flex items-center gap-2 text-sm font-semibold text-slate-700 hover:text-primary w-full text-left">
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
                <span className="font-bold text-primary">${Number(p.price).toFixed(2)}</span>
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
            className="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring">
            <option value="">Bodega *</option>
            {warehouses.map((w: any) => <option key={w.id} value={w.id}>{w.name}</option>)}
          </select>
          <input required type="number" step="1" value={form.quantity}
            onChange={e => setForm(f => ({ ...f, quantity: e.target.value }))}
            placeholder="Cantidad (+ entrada, - salida) *"
            className="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring" />
          <input value={form.reason} onChange={e => setForm(f => ({ ...f, reason: e.target.value }))}
            placeholder="Motivo"
            className="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring" />
          <div className="flex gap-3 pt-2">
            <button type="button" onClick={onClose}
              className="flex-1 rounded-xl border border-slate-200 px-4 py-2 text-sm text-slate-600 hover:bg-slate-50">Cancelar</button>
            <button type="submit" disabled={adjust.isPending}
              className="flex-1 rounded-xl bg-primary px-4 py-2 text-sm font-semibold text-white hover:bg-primary/90 disabled:opacity-60">
              {adjust.isPending ? 'Ajustando...' : 'Ajustar'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

// ─── Product Variants Tab (inside drawer) ────────────────────────────────────

function ProductVariantsTab({ product }: { product: Product }) {
  const { data: variants = [], isLoading } = useProductVariantsForProduct(product.id)
  const createVariant = useCreateVariant()
  const updateVar = useUpdateVariant()
  const deleteVar = useDeleteVariant()
  const toast = useToast()

  const [showAdd, setShowAdd] = useState(false)
  const [editingVar, setEditingVar] = useState<ProductVariant | null>(null)
  const [form, setForm] = useState({ sku: '', name: '', cost_price: '', sale_price: '' })

  const resetForm = () => setForm({ sku: '', name: '', cost_price: '', sale_price: '' })

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault()
    try {
      await createVariant.mutateAsync({
        parent_id: product.id,
        sku: form.sku,
        name: form.name,
        cost_price: parseFloat(form.cost_price) || 0,
        sale_price: parseFloat(form.sale_price) || 0,
        option_values: {},
      })
      toast.success('Variante creada')
      resetForm()
      setShowAdd(false)
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : 'Error al crear variante')
    }
  }

  async function handleUpdate(e: React.FormEvent) {
    e.preventDefault()
    if (!editingVar) return
    try {
      await updateVar.mutateAsync({
        id: editingVar.id,
        data: {
          sku: form.sku,
          name: form.name,
          cost_price: parseFloat(form.cost_price) || 0,
          sale_price: parseFloat(form.sale_price) || 0,
        },
      })
      toast.success('Variante actualizada')
      setEditingVar(null)
      resetForm()
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : 'Error al actualizar')
    }
  }

  function openEdit(v: ProductVariant) {
    setForm({ sku: v.sku, name: v.name, cost_price: String(v.cost_price), sale_price: String(v.sale_price) })
    setEditingVar(v)
    setShowAdd(false)
  }

  const cls = 'w-full rounded-lg border border-gray-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring'

  if (isLoading) return <div className="py-8 text-center text-gray-400 text-sm">Cargando variantes...</div>

  return (
    <div className="space-y-4 pt-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <p className="text-xs font-semibold text-gray-400 uppercase tracking-wide">
          Variantes ({variants.length})
        </p>
        {!showAdd && !editingVar && (
          <button onClick={() => { resetForm(); setShowAdd(true) }}
            className="flex items-center gap-1 text-xs font-semibold text-primary hover:text-primary/80">
            <Plus className="h-3.5 w-3.5" /> Nueva variante
          </button>
        )}
      </div>

      {/* Create / Edit form */}
      {(showAdd || editingVar) && (
        <form onSubmit={editingVar ? handleUpdate : handleCreate}
          className="rounded-xl border border-primary/20 bg-primary/5 p-4 space-y-3">
          <p className="text-xs font-semibold text-gray-700">
            {editingVar ? 'Editar variante' : 'Nueva variante'}
          </p>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs font-medium text-gray-600 mb-1 block">SKU *</label>
              <input required value={form.sku} onChange={e => setForm(f => ({ ...f, sku: e.target.value }))} className={cls} />
            </div>
            <div>
              <label className="text-xs font-medium text-gray-600 mb-1 block">Nombre *</label>
              <input required value={form.name} onChange={e => setForm(f => ({ ...f, name: e.target.value }))} className={cls} />
            </div>
            <div>
              <label className="text-xs font-medium text-gray-600 mb-1 block">Costo</label>
              <input type="number" step="0.01" value={form.cost_price} onChange={e => setForm(f => ({ ...f, cost_price: e.target.value }))} className={cls} />
            </div>
            <div>
              <label className="text-xs font-medium text-gray-600 mb-1 block">Precio venta</label>
              <input type="number" step="0.01" value={form.sale_price} onChange={e => setForm(f => ({ ...f, sale_price: e.target.value }))} className={cls} />
            </div>
          </div>

          <div className="flex gap-2 justify-end pt-1">
            <button type="button" onClick={() => { setShowAdd(false); setEditingVar(null); resetForm() }}
              className="px-3 py-1.5 text-xs text-gray-500 hover:bg-gray-100 rounded-lg">Cancelar</button>
            <button type="submit" disabled={createVariant.isPending || updateVar.isPending}
              className="px-4 py-1.5 text-xs font-semibold text-white bg-primary rounded-lg hover:bg-primary/90 disabled:opacity-50">
              {editingVar ? 'Guardar' : 'Crear'}
            </button>
          </div>
        </form>
      )}

      {/* Variants list */}
      {variants.length === 0 && !showAdd ? (
        <div className="rounded-xl border border-dashed border-gray-200 p-8 text-center">
          <p className="text-sm text-gray-400">Este producto no tiene variantes.</p>
          <button onClick={() => { resetForm(); setShowAdd(true) }}
            className="mt-2 text-xs font-semibold text-primary hover:underline">
            Crear primera variante
          </button>
        </div>
      ) : (
        <div className="space-y-2">
          {variants.map(v => (
            <div key={v.id}
              className={cn(
                'rounded-xl border p-3 transition-colors',
                editingVar?.id === v.id ? 'border-primary/30 bg-primary/5' : 'border-gray-100 bg-white hover:border-gray-200',
              )}>
              <div className="flex items-center justify-between">
                <div className="min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-xs text-gray-500">{v.sku}</span>
                    <span className="font-medium text-sm text-gray-900">{v.name}</span>
                  </div>
                </div>
                <div className="flex items-center gap-3 shrink-0">
                  <div className="text-right">
                    <div className="text-xs text-gray-400">Costo</div>
                    <div className="text-sm font-mono">${Number(v.cost_price).toLocaleString('es-CO')}</div>
                  </div>
                  <div className="text-right">
                    <div className="text-xs text-gray-400">Venta</div>
                    <div className="text-sm font-mono">${Number(v.sale_price).toLocaleString('es-CO')}</div>
                  </div>
                  <div className="flex gap-1">
                    <button onClick={() => openEdit(v)} className="p-1 text-gray-400 hover:text-primary rounded">
                      <Pencil className="h-3.5 w-3.5" />
                    </button>
                    <button onClick={async () => {
                      if (window.confirm(`¿Eliminar variante ${v.sku}?`)) {
                        await deleteVar.mutateAsync(v.id)
                        toast.success('Variante eliminada')
                      }
                    }} className="p-1 text-gray-400 hover:text-red-500 rounded">
                      <Trash2 className="h-3.5 w-3.5" />
                    </button>
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

// ─── Product Drawer ───────────────────────────────────────────────────────────

function ProductDrawer({
  product: listProduct,
  productTypes,
  categoryMap,
  onClose,
}: {
  product: Product
  productTypes: ProductType[]
  categoryMap: Map<string, string>
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
  const [drawerTab, setDrawerTab] = useState('general')
  const [confirmDelete, setConfirmDelete] = useState(false)
  const [lightboxIdx, setLightboxIdx] = useState<number | null>(null)
  const [showAdjust, setShowAdjust] = useState(false)
  const [showImagePicker, setShowImagePicker] = useState(false)
  const { data: levels = [] } = useStockByProduct(product.id)
  const { data: warehouses = [] } = useWarehouses()
  const { data: suppliers = [] } = useSuppliers()
  const whMap = Object.fromEntries(warehouses.map(w => [w.id, w.name]))
  const typeName = productTypes.find(t => t.id === product.product_type_id)?.name

  const { data: taxRates = [] } = useTaxRates({ is_active: true })
  const ivaRates = taxRates.filter(r => r.tax_type === 'iva')
  const retentionRates = taxRates.filter(r => r.tax_type === 'retention')

  const { data: availability } = useStockAvailability(product.id)

  // Edit form state
  const [form, setForm] = useState({
    name: product.name,
    description: product.description ?? '',
    barcode: product.barcode ?? '',
    category_id: product.category_id ?? '',
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
    valuation_method: product.valuation_method ?? 'weighted_average',
    margin_cost_method: product.margin_cost_method ?? 'last_purchase',
    margin_target: product.margin_target != null ? String(product.margin_target) : '',
    margin_minimum: product.margin_minimum != null ? String(product.margin_minimum) : '',
  })

  // Reset form when product changes or entering edit mode
  useEffect(() => {
    setForm({
      name: product.name,
      description: product.description ?? '',
      barcode: product.barcode ?? '',
      category_id: product.category_id ?? '',
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
      valuation_method: product.valuation_method ?? 'weighted_average',
      margin_cost_method: product.margin_cost_method ?? 'last_purchase',
      margin_target: product.margin_target != null ? String(product.margin_target) : '',
      margin_minimum: product.margin_minimum != null ? String(product.margin_minimum) : '',
    })
  }, [product, editing])

  // Price simulator (computed, not saved)
  const costBase = product.last_purchase_cost ? Number(product.last_purchase_cost) : 0
  const marginTarget = Number(form.margin_target) || 0
  const marginMinimum = Number(form.margin_minimum) || 0
  const simulatedPrice = marginTarget > 0 && marginTarget < 100
    ? costBase / (1 - marginTarget / 100)
    : 0
  const simulatedMinPrice = marginMinimum > 0 && marginMinimum < 100
    ? costBase / (1 - marginMinimum / 100)
    : 0

  async function handleSave() {
    try {
      await update.mutateAsync({
        id: product.id,
        data: {
          name: form.name,
          description: form.description || null,
          barcode: form.barcode || null,
          category_id: form.category_id || null,
          reorder_point: Number(form.reorder_point),
          reorder_quantity: Number(form.reorder_quantity),
          min_stock_level: Number(form.min_stock_level),
          is_active: form.is_active,
          preferred_supplier_id: form.preferred_supplier_id || null,
          auto_reorder: form.auto_reorder,
          tax_rate_id: form.tax_rate_id || null,
          is_tax_exempt: form.is_tax_exempt,
          retention_rate: form.retention_rate ? Number(form.retention_rate) / 100 : null,
          valuation_method: form.valuation_method,
          margin_cost_method: form.margin_cost_method,
          margin_target: form.margin_target ? Number(form.margin_target) : null,
          margin_minimum: form.margin_minimum ? Number(form.margin_minimum) : null,
        },
      })
      toast.success('Producto actualizado')
      setEditing(false)
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : 'Error al actualizar')
    }
  }

  const cls = "h-11 w-full rounded-lg border border-gray-300 bg-transparent px-4 py-2.5 text-sm text-gray-800 shadow-sm focus:border-primary/50 focus:outline-none focus:ring-3 focus:ring-ring/20"

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div className="flex items-start gap-4 flex-1 min-w-0">
          <button onClick={onClose} className="rounded-lg p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100 transition-colors mt-0.5">
            <ArrowLeft className="h-5 w-5" />
          </button>
          {!editing && <ProductThumb images={product.images} name={product.name} size="md" />}
          <div className="flex-1 min-w-0">
            {editing ? (
              <input
                value={form.name}
                onChange={e => setForm(f => ({ ...f, name: e.target.value }))}
                className="font-bold text-gray-900 w-full rounded-lg border border-gray-200 px-3 py-2 text-xl focus:outline-none focus:ring-2 focus:ring-ring"
              />
            ) : (
              <h1 className="text-xl font-bold text-gray-900">{product.name}</h1>
            )}
            <div className="flex items-center gap-2 mt-1">
              <p className="text-sm text-gray-400 font-mono">{product.sku}</p>
              {hasMovements && (
                <span className="flex items-center gap-0.5 text-xs text-amber-600 bg-amber-50 rounded-full px-2 py-0.5">
                  <Lock className="h-3 w-3" /> Trazado
                </span>
              )}
            </div>
            <div className="flex flex-wrap gap-1 mt-1">
                {typeName && (
                  <span className="inline-block rounded-full bg-primary/15 text-primary text-xs px-2 py-0.5 font-medium">
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
            <div className="flex items-center gap-2 ml-2">
              {!editing && (
                <button
                  onClick={() => setEditing(true)}
                  className="rounded-lg px-4 py-2 text-sm font-medium text-primary bg-primary/10 hover:bg-primary/15 transition-colors"
                >
                  <Pencil className="h-4 w-4 inline mr-1.5" />Editar
                </button>
              )}
            </div>
          </div>

        {/* Content */}
        <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-6 space-y-4">
          {editing ? (
            /* ─── EDIT MODE (3 tabs) ─── */
            <div className="space-y-4">
              {/* Locked fields info */}
              {hasMovements && (
                <div className="flex items-start gap-2 rounded-xl bg-amber-50 border border-amber-200 px-3 py-2.5">
                  <Lock className="h-4 w-4 text-amber-500 flex-shrink-0 mt-0.5" />
                  <div>
                    <p className="text-xs font-semibold text-amber-700">Campos protegidos</p>
                    <p className="text-xs text-amber-600 mt-0.5">
                      SKU, unidad de medida, valorización y rastreo por lotes no se pueden modificar porque el producto ya tiene movimientos de inventario.
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
                        onClick={() => {
                          const url = typeof img === 'string' ? img : (img.url ?? '')
                          const mid = typeof img === 'object' ? img.media_file_id : undefined
                          deleteImage.mutate({ productId: product.id, imageUrl: url, mediaFileId: mid })
                        }}
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
                    onClick={() => setShowImagePicker(true)}
                    disabled={uploadImage.isPending}
                    className="h-16 w-16 rounded-lg border-2 border-dashed border-gray-200 flex items-center justify-center text-gray-300 hover:border-primary/50 hover:text-primary/70 transition-colors disabled:opacity-50"
                  >
                    {uploadImage.isPending ? (
                      <Loader2 className="h-5 w-5 animate-spin" />
                    ) : (
                      <Camera className="h-5 w-5" />
                    )}
                  </button>
                </div>
                <MediaPickerModal
                  open={showImagePicker}
                  onClose={() => setShowImagePicker(false)}
                  onSelect={async (mediaFileId) => {
                    await uploadImage.mutateAsync({ productId: product.id, mediaFileId })
                    setShowImagePicker(false)
                  }}
                />
              </div>

              {/* ── Tab bar ── */}
              <div className="flex border-b border-border mb-4">
                {[
                  { key: 'general', label: 'General' },
                  { key: 'finanzas', label: 'Finanzas' },
                  { key: 'inventario', label: 'Inventario' },
                  { key: 'variantes', label: 'Variantes' },
                ].map(tab => (
                  <button
                    key={tab.key}
                    type="button"
                    onClick={() => setDrawerTab(tab.key)}
                    className={cn(
                      'px-4 py-2 text-xs font-medium border-b-2 -mb-px transition-colors',
                      drawerTab === tab.key
                        ? 'border-primary text-primary'
                        : 'border-transparent text-muted-foreground hover:text-foreground',
                    )}
                  >
                    {tab.label}
                  </button>
                ))}
              </div>

                {drawerTab === 'general' && (
                  <div className="space-y-4 pt-4">
                    {/* Name */}
                    <div>
                      <label className="text-xs font-medium text-gray-600 mb-1 block">Nombre</label>
                      <input
                        value={form.name}
                        onChange={e => setForm(f => ({ ...f, name: e.target.value }))}
                        className={cls}
                      />
                    </div>

                    {/* SKU (locked if has_movements) */}
                    <div>
                      <label className="text-xs font-medium text-gray-600 mb-1 flex items-center gap-1">
                        SKU {hasMovements && <Lock className="h-3 w-3 text-amber-400" />}
                      </label>
                      <div className="relative">
                        <input
                          value={product.sku}
                          disabled
                          className={cn(cls, 'bg-gray-50 text-gray-400 cursor-not-allowed')}
                        />
                        {hasMovements && (
                          <div className="absolute right-3 top-1/2 -translate-y-1/2" title="Bloqueado — tiene movimientos">
                            <Lock className="h-3.5 w-3.5 text-muted-foreground" />
                          </div>
                        )}
                      </div>
                    </div>

                    {/* Barcode */}
                    <div>
                      <label className="text-xs font-medium text-gray-600 mb-1 block">Código de barras</label>
                      <input
                        value={form.barcode}
                        onChange={e => setForm(f => ({ ...f, barcode: e.target.value }))}
                        placeholder="Código de barras (opcional)"
                        className={cls}
                      />
                    </div>

                    {/* Description */}
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

                    {/* Category */}
                    <div>
                      <label className="text-xs font-medium text-gray-600 mb-1 block">Categoría</label>
                      <select
                        value={form.category_id}
                        onChange={e => setForm(f => ({ ...f, category_id: e.target.value }))}
                        className={cls}
                      >
                        <option value="">Sin categoría</option>
                        {Array.from(categoryMap.entries()).map(([id, name]) => (
                          <option key={id} value={id}>{name}</option>
                        ))}
                      </select>
                    </div>

                    {/* Active toggle */}
                    <div>
                      <label className="text-xs font-medium text-gray-600 mb-1 flex items-center gap-1">Estado</label>
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
                )}

                {/* ══════════════════ Tab: Finanzas ══════════════════ */}
                {drawerTab === 'finanzas' && (
                  <div className="space-y-5 pt-4">
                    {/* Costo Base (read-only) */}
                    <div className="space-y-2">
                      <p className="text-xs font-semibold text-gray-400 uppercase tracking-wide">Costo Base</p>
                      <div className="rounded-xl bg-gray-50 p-3 space-y-1.5">
                        <div className="flex justify-between text-sm">
                          <span className="text-gray-500">Última compra</span>
                          <span className="font-medium">{product.last_purchase_cost ? `$${Number(product.last_purchase_cost).toLocaleString('es-CO')}` : '—'}</span>
                        </div>
                        <div className="flex justify-between text-sm">
                          <span className="text-gray-500">Fecha</span>
                          <span className="font-medium">{product.last_purchase_date ? new Date(product.last_purchase_date).toLocaleDateString('es-CO') : '—'}</span>
                        </div>
                        <div className="flex justify-between text-sm">
                          <span className="text-gray-500">Proveedor</span>
                          <span className="font-medium">{product.last_purchase_supplier ?? '—'}</span>
                        </div>
                      </div>
                    </div>

                    {/* Valorización */}
                    <div className="space-y-3">
                      <p className="text-xs font-semibold text-gray-400 uppercase tracking-wide">Valorización</p>
                      <div>
                        <label className="text-xs font-medium text-gray-600 mb-1 flex items-center gap-1">
                          Método de valorización {hasMovements && <Lock className="h-3 w-3 text-amber-400" />}
                        </label>
                        <div className="relative">
                          <select
                            value={form.valuation_method}
                            onChange={e => setForm(f => ({ ...f, valuation_method: e.target.value as 'weighted_average' | 'fifo' | 'lifo' }))}
                            disabled={hasMovements}
                            className={cn(cls, hasMovements && 'bg-gray-50 text-gray-400 cursor-not-allowed')}
                          >
                            <option value="weighted_average">Promedio Ponderado</option>
                            <option value="fifo">FIFO</option>
                          </select>
                          {hasMovements && (
                            <div className="absolute right-8 top-1/2 -translate-y-1/2" title="Bloqueado — tiene movimientos">
                              <Lock className="h-3.5 w-3.5 text-muted-foreground" />
                            </div>
                          )}
                        </div>
                      </div>
                      <div>
                        <label className="text-xs font-medium text-gray-600 mb-1 block">Método de costo para margen</label>
                        <select
                          value={form.margin_cost_method}
                          onChange={e => setForm(f => ({ ...f, margin_cost_method: e.target.value as 'last_purchase' | 'weighted_avg' | 'avg_last_3' }))}
                          className={cls}
                        >
                          <option value="last_purchase">Última compra</option>
                          <option value="weighted_avg">Promedio ponderado</option>
                          <option value="avg_last_3">Promedio últimas 3 compras</option>
                        </select>
                      </div>
                    </div>

                    {/* Márgenes */}
                    <div className="space-y-3">
                      <p className="text-xs font-semibold text-gray-400 uppercase tracking-wide">Márgenes</p>
                      <div className="grid grid-cols-2 gap-3">
                        <div>
                          <label className="text-xs font-medium text-gray-600 mb-1 block">Margen objetivo (%)</label>
                          <input
                            type="number"
                            step="0.1"
                            min="0"
                            max="99.99"
                            value={form.margin_target}
                            onChange={e => setForm(f => ({ ...f, margin_target: e.target.value }))}
                            placeholder="Ej: 30"
                            className={cls}
                          />
                        </div>
                        <div>
                          <label className="text-xs font-medium text-gray-600 mb-1 block">Margen mínimo (%)</label>
                          <input
                            type="number"
                            step="0.1"
                            min="0"
                            max="99.99"
                            value={form.margin_minimum}
                            onChange={e => setForm(f => ({ ...f, margin_minimum: e.target.value }))}
                            placeholder="Ej: 15"
                            className={cls}
                          />
                        </div>
                      </div>
                    </div>

                    {/* Price Simulator */}
                    {costBase > 0 && (
                      <div className="space-y-2">
                        <p className="text-xs font-semibold text-gray-400 uppercase tracking-wide flex items-center gap-1">
                          <DollarSign className="h-3.5 w-3.5" /> Simulador de precios
                        </p>
                        <div className="rounded-xl bg-blue-50 border border-blue-100 p-3 space-y-2">
                          <div className="flex justify-between text-sm">
                            <span className="text-blue-600">Costo base</span>
                            <span className="font-medium text-blue-800">${costBase.toLocaleString('es-CO', { minimumFractionDigits: 2 })}</span>
                          </div>
                          <div className="flex justify-between text-sm">
                            <span className="text-blue-600">Precio sugerido ({marginTarget || 0}%)</span>
                            <span className="font-bold text-green-700">
                              {simulatedPrice > 0 ? `$${simulatedPrice.toLocaleString('es-CO', { minimumFractionDigits: 2 })}` : '—'}
                            </span>
                          </div>
                          <div className="flex justify-between text-sm">
                            <span className="text-blue-600">Precio mínimo ({marginMinimum || 0}%)</span>
                            <span className="font-bold text-amber-700">
                              {simulatedMinPrice > 0 ? `$${simulatedMinPrice.toLocaleString('es-CO', { minimumFractionDigits: 2 })}` : '—'}
                            </span>
                          </div>
                        </div>
                      </div>
                    )}

                    {/* Impuestos */}
                    <div className="space-y-3">
                      <p className="text-xs font-semibold text-gray-400 uppercase tracking-wide flex items-center gap-1">
                        <Receipt className="h-3.5 w-3.5" /> Impuestos
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
                  </div>
                )}

                {/* ══════════════════ Tab: Inventario ══════════════════ */}
                {drawerTab === 'inventario' && (
                  <div className="space-y-5 pt-4">
                    {/* Niveles */}
                    <div className="space-y-3">
                      <p className="text-xs font-semibold text-gray-400 uppercase tracking-wide">Niveles</p>
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
                    </div>

                    {/* Reabastecimiento */}
                    <div className="space-y-3">
                      <p className="text-xs font-semibold text-gray-400 uppercase tracking-wide">Reabastecimiento</p>
                      <div className="space-y-3 rounded-lg border border-gray-200 p-3">
                        <label className="flex items-center gap-2 text-sm cursor-pointer">
                          <input
                            type="checkbox"
                            checked={form.auto_reorder}
                            onChange={e => setForm(f => ({ ...f, auto_reorder: e.target.checked }))}
                            className="rounded"
                          />
                          <span className="font-medium text-gray-700">Reorden automático</span>
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
                    </div>

                    {/* Disponibilidad (read-only card) */}
                    <div className="space-y-2">
                      <p className="text-xs font-semibold text-gray-400 uppercase tracking-wide">Disponibilidad</p>
                      {availability ? (
                        <div className="rounded-xl bg-gray-50 border border-gray-200 p-3 space-y-1.5">
                          <div className="flex justify-between text-sm">
                            <span className="text-muted-foreground">Físico</span>
                            <span className="font-medium text-gray-600">{Number(availability.on_hand).toLocaleString('es-CO', { minimumFractionDigits: 2 })}</span>
                          </div>
                          <div className="flex justify-between text-sm">
                            <span className="text-muted-foreground">Reservado</span>
                            <span className={cn('font-medium', Number(availability.reserved) > 0 ? 'text-amber-600' : 'text-gray-600')}>
                              {Number(availability.reserved).toLocaleString('es-CO', { minimumFractionDigits: 2 })}
                            </span>
                          </div>
                          <div className="flex justify-between text-sm border-t border-gray-200 pt-1.5">
                            <span className="font-semibold text-gray-700">Disponible</span>
                            <span className="font-bold text-gray-900">{Number(availability.available).toLocaleString('es-CO', { minimumFractionDigits: 2 })}</span>
                          </div>
                          <div className="flex justify-between text-sm">
                            <span className="text-muted-foreground">En tránsito</span>
                            <span className="font-medium text-gray-600">{Number(availability.in_transit).toLocaleString('es-CO', { minimumFractionDigits: 2 })}</span>
                          </div>
                        </div>
                      ) : (
                        <p className="text-xs text-gray-400">Cargando disponibilidad...</p>
                      )}
                    </div>

                    {/* Trazabilidad */}
                    <div className="space-y-3">
                      <p className="text-xs font-semibold text-gray-400 uppercase tracking-wide">Trazabilidad</p>
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
                      <div>
                        <label className="text-xs font-medium text-gray-600 mb-1 flex items-center gap-1">
                          Unidad de medida {hasMovements && <Lock className="h-3 w-3 text-amber-400" />}
                        </label>
                        <div className="relative">
                          <select
                            value={product.unit_of_measure}
                            disabled={hasMovements}
                            className={cn(cls, hasMovements && 'bg-gray-50 text-gray-400 cursor-not-allowed')}
                          >
                            {['un', 'kg', 'lt', 'm', 'm2', 'caja', 'palet'].map(u => <option key={u}>{u}</option>)}
                          </select>
                          {hasMovements && (
                            <div className="absolute right-8 top-1/2 -translate-y-1/2" title="Bloqueado — tiene movimientos">
                              <Lock className="h-3.5 w-3.5 text-muted-foreground" />
                            </div>
                          )}
                        </div>
                      </div>
                    </div>
                  </div>
                )}


                {/* ══════════════════ Tab: Variantes ══════════════════ */}
                {drawerTab === 'variantes' && (
                  <ProductVariantsTab product={product} />
                )}

              {/* Save / Cancel (hidden on variantes tab — managed inline) */}
              {drawerTab !== 'variantes' && (
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
                  className="flex-1 flex items-center justify-center gap-2 rounded-lg bg-primary px-4 py-2.5 text-sm font-semibold text-white hover:bg-primary disabled:opacity-60 transition-colors"
                >
                  <Save className="h-4 w-4" />
                  {update.isPending ? 'Guardando…' : 'Guardar cambios'}
                </button>
              </div>
              )}
            </div>
          ) : (
            /* ─── VIEW MODE — same 3 tabs as edit, but read-only ─── */
            <div className="space-y-4">
              {/* Images */}
              {product.images && product.images.length > 0 && (
                <div className="flex flex-wrap gap-2">
                  {product.images.map((img, i) => (
                    <button key={i} onClick={() => setLightboxIdx(i)}
                      className="group relative h-16 w-16 rounded-lg overflow-hidden border border-border hover:border-primary/50 transition-all cursor-zoom-in">
                      <img src={imgSrc(img)} alt={product.name} className="h-full w-full object-cover" />
                      <div className="absolute inset-0 bg-black/0 group-hover:bg-black/20 transition-colors flex items-center justify-center">
                        <ZoomIn className="h-4 w-4 text-white opacity-0 group-hover:opacity-100 transition-opacity" />
                      </div>
                    </button>
                  ))}
                </div>
              )}
              {lightboxIdx !== null && product.images && (
                <ImageLightbox images={product.images} initial={lightboxIdx} onClose={() => setLightboxIdx(null)} />
              )}

              {/* Tab bar */}
              <div className="flex border-b border-border">
                {[
                  { key: 'general', label: 'General' },
                  { key: 'finanzas', label: 'Finanzas' },
                  { key: 'inventario', label: 'Inventario' },
                  { key: 'variantes', label: 'Variantes' },
                ].map(t => (
                  <button key={t.key} type="button" onClick={() => setDrawerTab(t.key)}
                    className={cn('px-4 py-2 text-xs font-medium border-b-2 -mb-px transition-colors',
                      drawerTab === t.key ? 'border-primary text-primary' : 'border-transparent text-muted-foreground hover:text-foreground')}>
                    {t.label}
                  </button>
                ))}
              </div>

              {/* ── Tab: General (read-only) ── */}
              {drawerTab === 'general' && (
                <div className="space-y-3">
                  {product.description && <p className="text-sm text-muted-foreground">{product.description}</p>}
                  {product.barcode && (
                    <div className="flex justify-between text-sm"><span className="text-muted-foreground">Código de barras</span><span className="font-mono">{product.barcode}</span></div>
                  )}
                  <div className="flex justify-between text-sm"><span className="text-muted-foreground">Tipo</span><span className="font-medium">{typeName ?? '—'}</span></div>
                  <div className="flex justify-between text-sm"><span className="text-muted-foreground">Categoría</span><span className="font-medium">{categoryMap.get(product.category_id ?? '') ?? '—'}</span></div>
                  <div className="flex justify-between text-sm"><span className="text-muted-foreground">Unidad</span><span className="font-medium">{product.unit_of_measure}</span></div>
                  <div className="flex justify-between text-sm"><span className="text-muted-foreground">Estado</span><span className={product.is_active ? 'text-emerald-600 font-medium' : 'text-muted-foreground'}>
                    {product.is_active ? 'Activo' : 'Inactivo'}
                  </span></div>
                  {product.attributes && Object.keys(product.attributes).length > 0 && (
                    <div className="pt-2 border-t border-border">
                      <p className="text-xs font-medium text-muted-foreground mb-2">Atributos</p>
                      {Object.entries(product.attributes).map(([k, v]) => (
                        <div key={k} className="flex justify-between text-sm py-1">
                          <span className="text-muted-foreground">{k}</span>
                          <span className="font-medium">{Array.isArray(v) ? v.join(', ') : typeof v === 'boolean' ? (v ? 'Sí' : 'No') : String(v)}</span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}

              {/* ── Tab: Finanzas (read-only) ── */}
              {drawerTab === 'finanzas' && (
                <div className="space-y-4">
                  <div className="rounded-lg bg-muted/50 p-3 space-y-2">
                    <p className="text-xs font-medium text-muted-foreground">Costo Base</p>
                    <div className="flex justify-between text-sm"><span className="text-muted-foreground">Último costo</span><span className="font-bold">{product.last_purchase_cost ? `$${Number(product.last_purchase_cost).toLocaleString('es-CO')}` : '—'}</span></div>
                    {product.last_purchase_date && <div className="flex justify-between text-sm"><span className="text-muted-foreground">Fecha</span><span>{new Date(product.last_purchase_date).toLocaleDateString('es-CO')}</span></div>}
                    {product.last_purchase_supplier && <div className="flex justify-between text-sm"><span className="text-muted-foreground">Proveedor</span><span>{product.last_purchase_supplier}</span></div>}
                  </div>
                  <div className="grid grid-cols-2 gap-3">
                    <div className="rounded-lg border border-border p-3">
                      <p className="text-xs text-muted-foreground">Valorización</p>
                      <p className="font-medium text-sm mt-1">{product.valuation_method === 'fifo' ? 'FIFO' : 'Promedio Ponderado'}</p>
                    </div>
                    <div className="rounded-lg border border-border p-3">
                      <p className="text-xs text-muted-foreground">Método costo</p>
                      <p className="font-medium text-sm mt-1">{{last_purchase: 'Última compra', weighted_avg: 'Promedio', avg_last_3: 'Últimas 3'}[product.margin_cost_method] ?? product.margin_cost_method}</p>
                    </div>
                  </div>
                  <div className="grid grid-cols-2 gap-3">
                    <div className="rounded-lg border border-border p-3">
                      <p className="text-xs text-muted-foreground">Margen objetivo</p>
                      <p className="font-bold text-sm mt-1">{product.margin_target != null ? `${product.margin_target}%` : 'Global'}</p>
                    </div>
                    <div className="rounded-lg border border-border p-3">
                      <p className="text-xs text-muted-foreground">Margen mínimo</p>
                      <p className="font-bold text-sm mt-1">{product.margin_minimum != null ? `${product.margin_minimum}%` : 'Global'}</p>
                    </div>
                  </div>
                  <div className="grid grid-cols-2 gap-3">
                    <div className="rounded-lg bg-emerald-50 border border-emerald-200 p-3">
                      <p className="text-xs text-emerald-600">Precio sugerido</p>
                      <p className="font-bold text-emerald-700 mt-1">{product.suggested_sale_price ? `$${Number(product.suggested_sale_price).toLocaleString('es-CO')}` : '—'}</p>
                    </div>
                    <div className="rounded-lg bg-amber-50 border border-amber-200 p-3">
                      <p className="text-xs text-amber-600">Precio mínimo</p>
                      <p className="font-bold text-amber-700 mt-1">{product.minimum_sale_price ? `$${Number(product.minimum_sale_price).toLocaleString('es-CO')}` : '—'}</p>
                    </div>
                  </div>
                  <div className="pt-2 border-t border-border space-y-2">
                    <p className="text-xs font-medium text-muted-foreground">Tributación</p>
                    <div className="flex justify-between text-sm">
                      <span className="text-muted-foreground">IVA</span>
                      <span>{product.is_tax_exempt ? 'Exento' : (taxRates.find(r => r.id === product.tax_rate_id)?.name ?? 'Por defecto')}</span>
                    </div>
                    {product.retention_rate && Number(product.retention_rate) > 0 && (
                      <div className="flex justify-between text-sm"><span className="text-muted-foreground">Retención</span><span>{(Number(product.retention_rate) * 100).toFixed(2)}%</span></div>
                    )}
                  </div>
                  <CustomerPricesSection productId={product.id} />
                </div>
              )}

              {/* ── Tab: Inventario (read-only) ── */}
              {drawerTab === 'inventario' && (
                <div className="space-y-4">
                  <div className="grid grid-cols-3 gap-3">
                    <div className="rounded-lg border border-border p-3">
                      <p className="text-xs text-muted-foreground">Stock mínimo</p>
                      <p className="font-bold text-sm mt-1">{product.min_stock_level}</p>
                    </div>
                    <div className="rounded-lg border border-border p-3">
                      <p className="text-xs text-muted-foreground">Punto reorden</p>
                      <p className="font-bold text-sm mt-1">{product.reorder_point}</p>
                    </div>
                    <div className="rounded-lg border border-border p-3">
                      <p className="text-xs text-muted-foreground">Cant. reorden</p>
                      <p className="font-bold text-sm mt-1">{product.reorder_quantity}</p>
                    </div>
                  </div>
                  {product.auto_reorder && (
                    <div className="rounded-lg bg-primary/10 border border-primary/20 p-3">
                      <p className="text-xs font-medium text-primary">Reorden automático activo</p>
                      <p className="text-sm text-foreground mt-0.5">Proveedor: {suppliers.find(s => s.id === product.preferred_supplier_id)?.name ?? '—'}</p>
                    </div>
                  )}
                  {/* Stock by warehouse */}
                  <div>
                    <p className="text-xs font-medium text-muted-foreground mb-2">Stock por bodega</p>
                    {levels.length === 0 ? (
                      <p className="text-sm text-muted-foreground">Sin stock registrado</p>
                    ) : (
                      <div className="space-y-2">
                        {levels.map(lv => {
                          const qty = Number(lv.qty_on_hand)
                          const reserved = Number(lv.qty_reserved)
                          const available = qty - reserved
                          return (
                            <div key={lv.id} className="rounded-lg border border-border p-3">
                              <div className="flex justify-between text-sm mb-1">
                                <span className="font-medium">{whMap[lv.warehouse_id] ?? lv.warehouse_id}</span>
                              </div>
                              <div className="flex gap-4 text-xs">
                                <span className="text-muted-foreground">Físico: <span className="font-medium text-foreground">{qty.toFixed(0)}</span></span>
                                {reserved > 0 && <span className="text-amber-600">Reservado: <span className="font-medium">{reserved.toFixed(0)}</span></span>}
                                <span className="text-foreground">Disponible: <span className="font-bold">{available.toFixed(0)}</span></span>
                              </div>
                            </div>
                          )
                        })}
                      </div>
                    )}
                  </div>
                  <div className="pt-2 border-t border-border space-y-2">
                    <div className="flex justify-between text-sm"><span className="text-muted-foreground">Lotes</span><span>{product.track_batches ? 'Sí' : 'No'}</span></div>
                    <div className="flex justify-between text-sm"><span className="text-muted-foreground">Unidad</span><span>{product.unit_of_measure}</span></div>
                  </div>
                </div>
              )}

              {/* View mode variantes tab */}
              {drawerTab === 'variantes' && (
                <ProductVariantsTab product={product} />
              )}

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
                  className="flex items-center gap-1.5 rounded-xl border border-gray-200 px-3 py-1.5 text-xs font-medium text-gray-600 hover:bg-gray-50 hover:border-primary/50 transition-colors"
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
              className="w-full flex items-center gap-3 rounded-2xl border-2 border-dashed border-gray-200 p-4 text-sm text-gray-500 hover:border-primary/50 hover:bg-primary/5 transition-colors"
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
              className="flex-1 flex items-center justify-center gap-2 rounded-lg bg-primary px-4 py-2.5 text-sm font-semibold text-white hover:bg-primary disabled:opacity-60 transition-colors"
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

// ─── Low Stock Table ──────────────────────────────────────────────────────────

function LowStockTable({ stockStatus, onClear }: { stockStatus: 'low' | 'out'; onClear: () => void }) {
  const { data, isLoading } = useInventoryAnalytics()
  const alerts = data?.low_stock_alerts ?? []

  // "out" = only zero/negative stock; "low" = everything below threshold (includes out-of-stock & oversold)
  const filtered = stockStatus === 'out'
    ? alerts.filter(a => (a.qty_available ?? a.qty_on_hand) <= 0)
    : alerts

  const isOut = stockStatus === 'out'

  return (
    <div className="overflow-hidden rounded-xl border border-gray-200 bg-white">
      <div className="px-5 py-4 border-b border-gray-100 flex items-center justify-between">
        <div className="flex items-center gap-3">
          {isOut ? <AlertTriangle className="h-5 w-5 text-red-500" /> : <TrendingDown className="h-5 w-5 text-amber-500" />}
          <div>
            <p className={cn('text-sm font-semibold', isOut ? 'text-red-800' : 'text-amber-800')}>
              {isOut ? 'Productos sin stock' : 'Productos con stock bajo'} ({filtered.length})
            </p>
            <p className="text-xs text-slate-500 mt-0.5">
              {isOut
                ? 'Productos agotados en al menos una bodega'
                : 'Productos por debajo del punto de reorden'}
            </p>
          </div>
        </div>
        <button
          onClick={onClear}
          className={cn(
            'flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-medium transition',
            isOut ? 'bg-red-100 text-red-700 hover:bg-red-200' : 'bg-amber-100 text-amber-700 hover:bg-amber-200',
          )}
        >
          <X className="h-3.5 w-3.5" /> Ver todos los productos
        </button>
      </div>

      {isLoading ? (
        <div className="p-12 text-center text-gray-400">Cargando...</div>
      ) : filtered.length === 0 ? (
        <div className="p-12 text-center">
          <Package className="h-10 w-10 text-gray-200 mx-auto mb-3" />
          <p className="text-sm text-gray-500">Sin productos en esta categoría.</p>
        </div>
      ) : (
        <>
          {/* Mobile cards */}
          <div className="space-y-3 p-4 md:hidden">
            {filtered.map((a, i) => (
              <div key={`${a.product_id}-${a.warehouse_id}-${i}`}
                className={cn(
                  'rounded-xl border p-4 space-y-2',
                  (a.qty_available ?? a.qty_on_hand) <= 0 ? 'bg-red-50 border-red-200' : 'bg-amber-50 border-amber-200',
                )}>
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <p className="font-medium text-gray-800">{a.product_name ?? '—'}</p>
                    <p className="font-mono text-xs text-gray-400 mt-0.5">{a.sku}</p>
                  </div>
                  <span className={cn(
                    'text-lg font-extrabold tabular-nums',
                    (a.qty_available ?? a.qty_on_hand) <= 0 ? 'text-red-600' : 'text-amber-600',
                  )}>
                    {a.qty_available != null ? Math.floor(a.qty_available) : Math.floor(a.qty_on_hand)}
                  </span>
                </div>
                <div className="flex flex-wrap items-center gap-2 text-xs text-slate-600">
                  <span className="flex items-center gap-1 px-2 py-0.5 bg-white/70 rounded-md">
                    <Warehouse className="h-3 w-3" /> {a.warehouse_name ?? 'Sin bodega'}
                  </span>
                  <span>En mano: {Math.floor(a.qty_on_hand)}</span>
                  {a.qty_reserved > 0 && <span className="text-orange-600">Reservado: {Math.floor(a.qty_reserved)}</span>}
                  <span>Umbral: {a.reorder_point}</span>
                </div>
              </div>
            ))}
          </div>

          {/* Desktop table */}
          <div className="hidden md:block max-w-full overflow-x-auto">
            <table className="min-w-full">
              <thead>
                <tr className="border-b border-gray-100 bg-gray-50/50">
                  <th className="px-5 py-3 text-start text-sm font-medium text-gray-500">Producto</th>
                  <th className="px-5 py-3 text-start text-sm font-medium text-gray-500">SKU</th>
                  <th className="px-5 py-3 text-start text-sm font-medium text-gray-500">Bodega</th>
                  <th className="px-5 py-3 text-end text-sm font-medium text-gray-500">En mano</th>
                  <th className="px-5 py-3 text-end text-sm font-medium text-gray-500">Reservado</th>
                  <th className="px-5 py-3 text-end text-sm font-medium text-gray-500">Disponible</th>
                  <th className="px-5 py-3 text-end text-sm font-medium text-gray-500">Umbral</th>
                  <th className="px-5 py-3 text-end text-sm font-medium text-gray-500">Déficit</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {filtered.map((a, i) => {
                  const available = a.qty_available ?? a.qty_on_hand
                  const deficit = a.reorder_point - available
                  return (
                    <tr key={`${a.product_id}-${a.warehouse_id}-${i}`} className="hover:bg-gray-50/50 transition-colors">
                      <td className="px-5 py-3.5 font-medium text-gray-800">{a.product_name ?? '—'}</td>
                      <td className="px-5 py-3.5 font-mono text-xs text-gray-500">{a.sku}</td>
                      <td className="px-5 py-3.5">
                        <span className="inline-flex items-center gap-1.5 text-sm text-gray-700">
                          <Warehouse className="h-3.5 w-3.5 text-gray-400" />
                          {a.warehouse_name ?? 'Sin bodega'}
                        </span>
                      </td>
                      <td className="px-5 py-3.5 text-end tabular-nums text-sm text-gray-700">{Math.floor(a.qty_on_hand)}</td>
                      <td className="px-5 py-3.5 text-end tabular-nums text-sm">
                        {a.qty_reserved > 0 ? (
                          <span className="text-orange-600 font-medium">{Math.floor(a.qty_reserved)}</span>
                        ) : (
                          <span className="text-gray-300">0</span>
                        )}
                      </td>
                      <td className="px-5 py-3.5 text-end tabular-nums">
                        <span className={cn(
                          'text-sm font-bold',
                          available <= 0 ? 'text-red-600' : 'text-amber-600',
                        )}>
                          {Math.floor(available)}
                        </span>
                      </td>
                      <td className="px-5 py-3.5 text-end tabular-nums text-sm text-gray-500">{a.reorder_point}</td>
                      <td className="px-5 py-3.5 text-end tabular-nums">
                        {deficit > 0 ? (
                          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-red-50 text-red-700 text-xs font-semibold">
                            -{Math.ceil(deficit)}
                          </span>
                        ) : (
                          <span className="text-gray-300 text-xs">—</span>
                        )}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </>
      )}

      <div className="px-5 py-3 border-t border-gray-100 text-xs text-gray-400">
        {filtered.length} registro(s) · Datos del último escaneo de stock
      </div>
    </div>
  )
}


// ─── Main Page ────────────────────────────────────────────────────────────────

type SortKey = 'sku' | 'name' | 'suggested_sale_price' | 'unit_of_measure' | 'is_active'
type SortDir = 'asc' | 'desc'

const COLUMNS: { key: string; label: string; sortable?: SortKey }[] = [
  { key: 'photo', label: '' },
  { key: 'sku', label: 'SKU', sortable: 'sku' },
  { key: 'name', label: 'Nombre', sortable: 'name' },
  { key: 'category', label: 'Categoría' },
  { key: 'type', label: 'Tipo' },
  { key: 'unit', label: 'Unidad', sortable: 'unit_of_measure' },
  { key: 'cost', label: 'P. Sugerido', sortable: 'suggested_sale_price' },
  { key: 'status', label: 'Estado', sortable: 'is_active' },
]

export function ProductsPage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const location = useLocation()
  const stockStatusParam = searchParams.get('stock_status') as 'low' | 'out' | null

  const [search, setSearch] = useState('')
  const [filterType, setFilterType] = useState('')
  const [showCreate, setShowCreate] = useState(false)
  const [showImport, setShowImport] = useState(false)
  const [selected, setSelected] = useState<Product | null>(null)

  // Reset to list view when navigating to this page (e.g. clicking sidebar)
  useEffect(() => {
    setSelected(null)
    setShowCreate(false)
  }, [location.key])

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
  const { data: categoriesData } = useCategories()
  const allCategories = categoriesData?.items ?? []
  const categoryMap = useMemo(() => new Map(allCategories.map(c => [c.id, c.name])), [allCategories])

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
      else if (sortBy === 'suggested_sale_price') { va = Number(a.suggested_sale_price ?? 0); vb = Number(b.suggested_sale_price ?? 0) }
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
      ? <ArrowUp className="h-3.5 w-3.5 text-primary" />
      : <ArrowDown className="h-3.5 w-3.5 text-primary" />
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

  // ── Full-page create ──
  if (showCreate) {
    return <CreateProductModal onClose={() => setShowCreate(false)} />
  }

  // ── Full-page product detail / edit ──
  if (selected) {
    return (
      <ProductDrawer
        product={selected}
        productTypes={productTypes}
        categoryMap={categoryMap}
        onClose={() => setSelected(null)}
      />
    )
  }

  return (
    <div className="space-y-6">
      {/* Breadcrumb */}
      <nav className="mb-4">
        <ol className="flex items-center gap-2 text-sm">
          <li className="text-gray-500">Inventario</li>
          <li><ChevronRight className="h-4 w-4 text-gray-400" /></li>
          <li className="text-primary">Productos</li>
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
            className="flex items-center gap-2 rounded-lg bg-primary px-3 sm:px-4 py-2 sm:py-2.5 text-sm font-medium text-white hover:bg-primary shadow-sm transition"
          >
            <Plus className="h-4 w-4" /> Nuevo
          </button>
        </div>
      </div>

      {/* ─── Low Stock / Out of Stock dedicated table ─── */}
      {stockStatusParam ? (
        <LowStockTable stockStatus={stockStatusParam} onClear={() => { searchParams.delete('stock_status'); setSearchParams(searchParams) }} />
      ) : (
        <>
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
                    className="h-9 rounded-lg border border-gray-300 bg-transparent px-2 py-1 text-sm text-gray-800 focus:border-primary/50 focus:outline-none focus:ring-3 focus:ring-ring/20"
                  >
                    {[5, 10, 25, 50].map(n => <option key={n} value={n}>{n}</option>)}
                  </select>
                  <span>registros</span>
                </div>
                {productTypes.length > 0 && (
                  <select
                    value={filterType}
                    onChange={e => setFilterType(e.target.value)}
                    className="h-9 rounded-lg border border-gray-300 bg-transparent px-3 py-1 text-sm text-gray-800 focus:border-primary/50 focus:outline-none focus:ring-3 focus:ring-ring/20"
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
                  className="h-9 w-full rounded-lg border border-gray-300 bg-transparent pl-9 pr-4 py-1 text-sm text-gray-800 placeholder:text-gray-400 focus:border-primary/50 focus:outline-none focus:ring-3 focus:ring-ring/20 sm:w-64"
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
                        className="rounded-xl border border-gray-200 bg-white p-4 shadow-sm cursor-pointer hover:border-primary/30 hover:shadow-md transition-all active:scale-[0.99] space-y-2"
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
                          {categoryMap.get(p.category_id ?? '') && (
                            <span className="text-xs text-gray-500">{categoryMap.get(p.category_id ?? '')}</span>
                          )}
                          <span className="text-xs text-gray-500">{p.unit_of_measure}</span>
                          <span className="text-xs font-medium text-gray-700">{p.suggested_sale_price ? `$${Number(p.suggested_sale_price).toLocaleString('es-CO', {maximumFractionDigits: 0})}` : '—'}</span>
                        </div>
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
                            <td className="px-5 py-4 text-sm text-muted-foreground">
                              {categoryMap.get(p.category_id ?? '') ?? '—'}
                            </td>
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
                            <td className="px-5 py-4 text-gray-500 text-sm">{p.unit_of_measure}</td>
                            <td className="px-5 py-4 text-gray-500 text-sm">{p.suggested_sale_price ? `$${Number(p.suggested_sale_price).toLocaleString('es-CO', {maximumFractionDigits: 0})}` : '—'}</td>
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
                            ? 'bg-primary text-white shadow-sm'
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
        </>
      )}
    </div>
  )
}
