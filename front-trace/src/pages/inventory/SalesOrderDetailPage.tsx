import { useState, useRef } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import {
  ArrowLeft, Check, PackageCheck, Truck as TruckIcon, CheckCircle2, RotateCcw, XCircle, AlertTriangle,
  MapPin, Phone, Mail, FileText, Camera, Package, ExternalLink, RefreshCw, Copy, FileDown,
  Warehouse, ClipboardCheck, Lock, Clock, Percent,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import {
  useSalesOrder, useConfirmSalesOrder, usePickSalesOrder, useShipSalesOrder,
  useDeliverSalesOrder, useReturnSalesOrder, useCancelSalesOrder, useCustomer,
  useRetryInvoice, useRetryCreditNote, useUpdateLineWarehouse,
  useWarehouses, useBackorders, useConfirmBackorder, useSOReservations,
  useApproveSalesOrder, useRejectSalesOrder, useResubmitSalesOrder, useApprovalLog,
  useSoBatches, useStockCheck, useApplyDiscount,
} from '@/hooks/useInventory'
import { useAuthStore } from '@/store/auth'
import { useToast } from '@/store/toast'
import { generateSandboxInvoicePDF } from '@/utils/generateSandboxInvoicePDF'
import type { SalesOrderStatus, ShippingInfo, StockCheckResult, ConfirmWithBackorderOut, StockReservation } from '@/types/inventory'

const STATUS_CONFIG: Record<SalesOrderStatus, { label: string; color: string }> = {
  draft: { label: 'Borrador', color: 'bg-secondary text-muted-foreground' },
  pending_approval: { label: 'Pend. Aprobación', color: 'bg-yellow-50 text-yellow-700' },
  confirmed: { label: 'Confirmada', color: 'bg-blue-50 text-blue-700' },
  picking: { label: 'En Picking', color: 'bg-amber-50 text-amber-700' },
  shipped: { label: 'Enviada', color: 'bg-primary/10 text-primary' },
  delivered: { label: 'Entregada', color: 'bg-emerald-50 text-emerald-700' },
  returned: { label: 'Devuelta', color: 'bg-orange-50 text-orange-600' },
  canceled: { label: 'Cancelada', color: 'bg-red-50 text-red-600' },
  rejected: { label: 'Rechazado', color: 'bg-red-50 text-red-600' },
}

const STEPS: SalesOrderStatus[] = ['draft', 'confirmed', 'picking', 'shipped', 'delivered']

const SHIPPING_METHODS = [
  { value: 'pickup', label: 'Recoge en tienda' },
  { value: 'standard', label: 'Envio estandar' },
  { value: 'express', label: 'Envio express' },
  { value: 'same_day', label: 'Mismo dia' },
  { value: 'freight', label: 'Carga / Flete' },
  { value: 'other', label: 'Otro' },
]

function ShipModal({ onClose, onSubmit, isPending }: {
  onClose: () => void
  onSubmit: (info: ShippingInfo) => void
  isPending: boolean
}) {
  const [form, setForm] = useState<ShippingInfo>({
    recipient_name: '',
    recipient_phone: '',
    recipient_email: '',
    recipient_document: '',
    address_line: '',
    city: '',
    state: '',
    zip_code: '',
    country: 'Colombia',
    shipping_method: 'standard',
    carrier: '',
    tracking_number: '',
    photo_url: '',
    shipping_notes: '',
  })
  const fileRef = useRef<HTMLInputElement>(null)
  const [photoPreview, setPhotoPreview] = useState<string | null>(null)

  function handlePhoto(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (!file) return
    if (file.size > 5 * 1024 * 1024) { alert('La foto no puede superar 5 MB'); return }
    const reader = new FileReader()
    reader.onload = () => {
      const dataUrl = reader.result as string
      setPhotoPreview(dataUrl)
      setForm(f => ({ ...f, photo_url: dataUrl }))
    }
    reader.readAsDataURL(file)
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    onSubmit(form)
  }

  const inp = 'w-full rounded-xl border border-border px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring'

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 backdrop-blur-sm">
      <div className="w-full max-w-xl bg-card rounded-3xl shadow-2xl p-6 max-h-[92vh] overflow-y-auto">
        <h2 className="text-lg font-bold text-foreground mb-1">Datos de Envio</h2>
        <p className="text-xs text-muted-foreground mb-4">Completa la informacion del despacho antes de enviar la orden.</p>

        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Buyer info */}
          <div>
            <p className="text-xs font-bold text-muted-foreground uppercase tracking-wide mb-2 flex items-center gap-1"><FileText className="h-3 w-3" /> Datos del comprador</p>
            <div className="grid grid-cols-2 gap-3">
              <input value={form.recipient_name ?? ''} onChange={e => setForm(f => ({ ...f, recipient_name: e.target.value }))}
                placeholder="Nombre completo" className={inp} />
              <input value={form.recipient_document ?? ''} onChange={e => setForm(f => ({ ...f, recipient_document: e.target.value }))}
                placeholder="Documento / NIT" className={inp} />
              <input value={form.recipient_phone ?? ''} onChange={e => setForm(f => ({ ...f, recipient_phone: e.target.value }))}
                placeholder="Telefono" type="tel" className={inp} />
              <input value={form.recipient_email ?? ''} onChange={e => setForm(f => ({ ...f, recipient_email: e.target.value }))}
                placeholder="Email" type="email" className={inp} />
            </div>
          </div>

          {/* Address */}
          <div>
            <p className="text-xs font-bold text-muted-foreground uppercase tracking-wide mb-2 flex items-center gap-1"><MapPin className="h-3 w-3" /> Direccion de entrega</p>
            <div className="space-y-3">
              <input value={form.address_line ?? ''} onChange={e => setForm(f => ({ ...f, address_line: e.target.value }))}
                placeholder="Direccion (calle, numero, apto...)" className={inp} />
              <div className="grid grid-cols-3 gap-3">
                <input value={form.city ?? ''} onChange={e => setForm(f => ({ ...f, city: e.target.value }))}
                  placeholder="Ciudad" className={inp} />
                <input value={form.state ?? ''} onChange={e => setForm(f => ({ ...f, state: e.target.value }))}
                  placeholder="Departamento" className={inp} />
                <input value={form.zip_code ?? ''} onChange={e => setForm(f => ({ ...f, zip_code: e.target.value }))}
                  placeholder="Codigo postal" className={inp} />
              </div>
              <input value={form.country ?? ''} onChange={e => setForm(f => ({ ...f, country: e.target.value }))}
                placeholder="Pais" className={inp} />
            </div>
          </div>

          {/* Shipping method */}
          <div>
            <p className="text-xs font-bold text-muted-foreground uppercase tracking-wide mb-2 flex items-center gap-1"><TruckIcon className="h-3 w-3" /> Metodo de envio</p>
            <div className="space-y-3">
              <div className="flex gap-2 flex-wrap">
                {SHIPPING_METHODS.map(m => (
                  <button key={m.value} type="button"
                    onClick={() => setForm(f => ({ ...f, shipping_method: m.value }))}
                    className={cn(
                      'rounded-xl px-3 py-1.5 text-xs font-semibold transition-colors border',
                      form.shipping_method === m.value
                        ? 'bg-primary text-white border-primary'
                        : 'bg-card text-muted-foreground border-border hover:bg-muted'
                    )}>
                    {m.label}
                  </button>
                ))}
              </div>
              <div className="grid grid-cols-2 gap-3">
                <input value={form.carrier ?? ''} onChange={e => setForm(f => ({ ...f, carrier: e.target.value }))}
                  placeholder="Empresa transportadora" className={inp} />
                <input value={form.tracking_number ?? ''} onChange={e => setForm(f => ({ ...f, tracking_number: e.target.value }))}
                  placeholder="Numero de guia / tracking" className={inp} />
              </div>
            </div>
          </div>

          {/* Photo */}
          <div>
            <p className="text-xs font-bold text-muted-foreground uppercase tracking-wide mb-2 flex items-center gap-1"><Camera className="h-3 w-3" /> Foto del despacho</p>
            <input ref={fileRef} type="file" accept="image/*" onChange={handlePhoto} className="hidden" />
            {photoPreview ? (
              <div className="relative">
                <img src={photoPreview} alt="Foto despacho" className="w-full max-h-48 object-cover rounded-xl border border-border" />
                <button type="button" onClick={() => { setPhotoPreview(null); setForm(f => ({ ...f, photo_url: '' })); if (fileRef.current) fileRef.current.value = '' }}
                  className="absolute top-2 right-2 bg-card/80 rounded-full p-1 text-muted-foreground hover:text-red-500">
                  <XCircle className="h-4 w-4" />
                </button>
              </div>
            ) : (
              <button type="button" onClick={() => fileRef.current?.click()}
                className="w-full rounded-xl border-2 border-dashed border-border py-6 text-sm text-muted-foreground hover:border-primary/50 hover:text-primary transition-colors">
                Click para subir foto (max 5 MB)
              </button>
            )}
          </div>

          {/* Notes */}
          <textarea value={form.shipping_notes ?? ''} onChange={e => setForm(f => ({ ...f, shipping_notes: e.target.value }))}
            placeholder="Notas de envio (opcional)" rows={2} className={inp} />

          <div className="flex gap-3 pt-2">
            <button type="button" onClick={onClose} className="flex-1 rounded-xl border border-border px-4 py-2 text-sm text-muted-foreground hover:bg-muted">Cancelar</button>
            <button type="submit" disabled={isPending}
              className="flex-1 rounded-xl bg-primary px-4 py-2.5 text-sm font-semibold text-white hover:bg-primary/90 disabled:opacity-60 flex items-center justify-center gap-2">
              <TruckIcon className="h-4 w-4" />
              {isPending ? 'Enviando...' : 'Confirmar envio'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

function ShippingInfoCard({ info }: { info: ShippingInfo }) {
  const methodLabel = SHIPPING_METHODS.find(m => m.value === info.shipping_method)?.label ?? info.shipping_method

  return (
    <div className="bg-card rounded-2xl border border-border/60  overflow-hidden">
      <div className="px-6 py-3 bg-primary/10 border-b border-primary/20">
        <h3 className="text-sm font-bold text-primary flex items-center gap-2"><TruckIcon className="h-4 w-4" /> Informacion de Envio</h3>
      </div>
      <div className="p-6 grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Buyer data */}
        {(info.recipient_name || info.recipient_phone || info.recipient_email || info.recipient_document) && (
          <div>
            <p className="text-xs font-bold text-muted-foreground uppercase tracking-wide mb-2 flex items-center gap-1"><FileText className="h-3 w-3" /> Comprador</p>
            <div className="space-y-1.5">
              {info.recipient_name && <p className="text-sm font-semibold text-foreground">{info.recipient_name}</p>}
              {info.recipient_document && <p className="text-xs text-muted-foreground">Doc: {info.recipient_document}</p>}
              {info.recipient_phone && <p className="text-xs text-muted-foreground flex items-center gap-1"><Phone className="h-3 w-3" /> {info.recipient_phone}</p>}
              {info.recipient_email && <p className="text-xs text-muted-foreground flex items-center gap-1"><Mail className="h-3 w-3" /> {info.recipient_email}</p>}
            </div>
          </div>
        )}

        {/* Address */}
        {(info.address_line || info.city) && (
          <div>
            <p className="text-xs font-bold text-muted-foreground uppercase tracking-wide mb-2 flex items-center gap-1"><MapPin className="h-3 w-3" /> Direccion</p>
            <div className="space-y-0.5">
              {info.address_line && <p className="text-sm text-foreground">{info.address_line}</p>}
              <p className="text-xs text-muted-foreground">
                {[info.city, info.state, info.zip_code].filter(Boolean).join(', ')}
              </p>
              {info.country && <p className="text-xs text-muted-foreground">{info.country}</p>}
            </div>
          </div>
        )}

        {/* Shipping method */}
        {(info.shipping_method || info.carrier || info.tracking_number) && (
          <div>
            <p className="text-xs font-bold text-muted-foreground uppercase tracking-wide mb-2 flex items-center gap-1"><Package className="h-3 w-3" /> Transporte</p>
            <div className="space-y-1.5">
              {info.shipping_method && (
                <span className="inline-flex rounded-full bg-primary/10 px-2.5 py-0.5 text-[11px] font-semibold text-primary">
                  {methodLabel}
                </span>
              )}
              {info.carrier && <p className="text-sm text-foreground">Empresa: <span className="font-medium">{info.carrier}</span></p>}
              {info.tracking_number && (
                <p className="text-sm text-foreground">Guia: <span className="font-mono font-bold text-primary">{info.tracking_number}</span></p>
              )}
            </div>
          </div>
        )}

        {/* Photo */}
        {info.photo_url && (
          <div>
            <p className="text-xs font-bold text-muted-foreground uppercase tracking-wide mb-2 flex items-center gap-1"><Camera className="h-3 w-3" /> Foto del despacho</p>
            <img src={info.photo_url} alt="Foto despacho" className="w-full max-h-48 object-cover rounded-xl border border-border" />
          </div>
        )}

        {/* Notes */}
        {info.shipping_notes && (
          <div className="md:col-span-2">
            <p className="text-xs font-bold text-muted-foreground uppercase tracking-wide mb-1">Notas de envio</p>
            <p className="text-sm text-muted-foreground">{info.shipping_notes}</p>
          </div>
        )}
      </div>
    </div>
  )
}

const BATCH_STATUSES = new Set(['confirmed', 'picking', 'shipped', 'delivered'])

function BatchTraceabilitySection({ orderId, status }: { orderId: string; status: string }) {
  const { data, isLoading } = useSoBatches(BATCH_STATUSES.has(status) ? orderId : '')

  if (!BATCH_STATUSES.has(status)) return null

  const today = new Date()
  const thirtyDaysFromNow = new Date(today.getTime() + 30 * 86400000)

  function expiryBadge(expirationDate: string | null) {
    if (!expirationDate) return null
    const exp = new Date(expirationDate)
    if (exp < today) {
      return <span className="inline-flex rounded-full bg-red-50 border border-red-200 px-1.5 py-0.5 text-[10px] font-semibold text-red-700">Vencido</span>
    }
    if (exp <= thirtyDaysFromNow) {
      return <span className="inline-flex rounded-full bg-yellow-50 border border-yellow-200 px-1.5 py-0.5 text-[10px] font-semibold text-yellow-700">Vence pronto</span>
    }
    return null
  }

  return (
    <div className="bg-card rounded-2xl border border-border/60  overflow-hidden">
      <div className="px-6 py-4 border-b border-border flex items-center gap-2">
        <Package className="h-4 w-4 text-primary" />
        <h3 className="text-sm font-bold text-foreground">Trazabilidad de lotes</h3>
      </div>
      <div className="p-6">
        {isLoading ? (
          <div className="flex items-center justify-center py-8 text-muted-foreground text-sm">Cargando...</div>
        ) : !data?.batches_used?.length ? (
          <p className="text-sm text-muted-foreground text-center py-4">No se han asignado lotes a este pedido.</p>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-xs font-semibold text-muted-foreground uppercase border-b border-border">
                <th className="pb-2 pr-4">Producto</th>
                <th className="pb-2 pr-4"># Lote</th>
                <th className="pb-2 pr-4">Vencimiento</th>
                <th className="pb-2 text-right">Cantidad</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-50">
              {data.batches_used.map((b, i) => (
                <tr key={`${b.batch_id}-${b.line_id}-${i}`} className="hover:bg-muted">
                  <td className="py-2 pr-4 text-foreground">{b.product_name ?? b.product_id.slice(0, 8)}</td>
                  <td className="py-2 pr-4">
                    <span className="inline-flex rounded-full bg-secondary px-2 py-0.5 text-xs font-mono font-semibold text-foreground">{b.batch_number}</span>
                  </td>
                  <td className="py-2 pr-4">
                    <div className="flex items-center gap-2">
                      <span className="text-muted-foreground">
                        {b.expiration_date ? new Date(b.expiration_date).toLocaleDateString('es-CO') : '\u2014'}
                      </span>
                      {expiryBadge(b.expiration_date)}
                    </div>
                  </td>
                  <td className="py-2 text-right font-bold text-foreground">{b.qty_from_this_batch}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}

function DiscountModal({ orderId, currentDiscount, onClose }: {
  orderId: string; currentDiscount?: number | null; onClose: () => void
}) {
  const applyDiscount = useApplyDiscount()
  const [pct, setPct] = useState(String(currentDiscount ?? ''))
  const [reason, setReason] = useState('')

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    await applyDiscount.mutateAsync({
      id: orderId,
      data: { discount_pct: Number(pct), discount_reason: reason || null },
    })
    onClose()
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 backdrop-blur-sm">
      <div className="w-full max-w-sm bg-card rounded-3xl shadow-2xl p-6">
        <h2 className="text-lg font-bold text-foreground mb-4">Aplicar Descuento Global</h2>
        <form onSubmit={handleSubmit} className="space-y-3">
          <div>
            <label className="text-xs text-muted-foreground mb-1 block">Porcentaje de descuento</label>
            <input required type="number" step="0.01" min="0" max="100" value={pct}
              onChange={e => setPct(e.target.value)}
              placeholder="Ej: 10"
              className="w-full rounded-xl border border-border px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring" />
          </div>
          <div>
            <label className="text-xs text-muted-foreground mb-1 block">Motivo (requerido)</label>
            <input required value={reason} onChange={e => setReason(e.target.value)}
              placeholder="Ej: Cliente VIP, Promoción..."
              className="w-full rounded-xl border border-border px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring" />
          </div>
          <div className="flex gap-3 pt-2">
            <button type="button" onClick={onClose}
              className="flex-1 rounded-xl border border-border px-4 py-2 text-sm text-muted-foreground hover:bg-muted">Cancelar</button>
            <button type="submit" disabled={applyDiscount.isPending}
              className="flex-1 rounded-xl bg-primary px-4 py-2 text-sm font-semibold text-white hover:bg-primary/90 disabled:opacity-60">
              {applyDiscount.isPending ? 'Aplicando...' : 'Aplicar'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

export function SalesOrderDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const { data: order, isLoading } = useSalesOrder(id ?? '')
  const { data: customer } = useCustomer(order?.customer_id ?? '')
  const [actionError, setActionError] = useState<string | null>(null)
  const [showShipModal, setShowShipModal] = useState(false)
  const [lastBackorderResult, setLastBackorderResult] = useState<ConfirmWithBackorderOut | null>(null)
  const toast = useToast()
  const onError = (err: unknown) => {
    const msg = (err as { message?: string })?.message
      || (err as { error?: { message?: string } })?.error?.message
      || 'Error desconocido'
    setActionError(msg)
  }
  const onMutate = () => setActionError(null)
  const confirmMut = useConfirmSalesOrder()
  const confirmBackorderMut = useConfirmBackorder()
  const { data: backorders = [] } = useBackorders(order?.id)
  const { data: reservations = [] } = useSOReservations(order?.id)
  const pickMut = usePickSalesOrder()
  const shipMut = useShipSalesOrder()
  const deliverMut = useDeliverSalesOrder()
  const returnMut = useReturnSalesOrder()
  const cancelMut = useCancelSalesOrder()
  const retryInvoiceMut = useRetryInvoice()
  const retryCreditNoteMut = useRetryCreditNote()
  const updateLineWhMut = useUpdateLineWarehouse()
  const { data: warehouses = [] } = useWarehouses()
  const [stockCheck, setStockCheck] = useState<StockCheckResult | null>(null)
  const [stockCheckLoading, setStockCheckLoading] = useState(false)
  const authUser = useAuthStore((s) => s.user)
  const approveMut = useApproveSalesOrder()
  const rejectMut = useRejectSalesOrder()
  const resubmitMut = useResubmitSalesOrder()
  const [showRejectModal, setShowRejectModal] = useState(false)
  const [rejectReason, setRejectReason] = useState('')
  const { data: approvalLog = [] } = useApprovalLog(order?.approval_required ? order?.id : undefined)
  const { data: stockCheckAuto } = useStockCheck(order?.status === 'confirmed' || order?.status === 'picking' ? id : undefined)
  const [showDiscount, setShowDiscount] = useState(false)
  const applyDiscount = useApplyDiscount()

  if (isLoading) return <div className="flex justify-center py-20"><div className="animate-spin rounded-full h-6 w-6 border-b-2 border-primary" /></div>
  if (!order) return <p className="text-center text-muted-foreground py-20">Orden no encontrada</p>

  const steps: SalesOrderStatus[] = order.approval_required
    ? ['draft', 'pending_approval', 'confirmed', 'picking', 'shipped', 'delivered']
    : ['draft', 'confirmed', 'picking', 'shipped', 'delivered']
  const effectiveStatus = order.status === 'rejected' ? 'pending_approval' as SalesOrderStatus : order.status
  const currentStepIdx = steps.indexOf(effectiveStatus)
  const stepIdx = STEPS.indexOf(order.status)
  const isFinal = ['delivered', 'returned', 'canceled'].includes(order.status)

  function handleShip(info: ShippingInfo) {
    onMutate()
    shipMut.mutate(
      { id: order!.id, body: { shipping_info: info as Record<string, unknown> } },
      {
        onError,
        onSuccess: () => setShowShipModal(false),
      },
    )
  }

  async function runStockCheck() {
    setStockCheckLoading(true)
    try {
      const { inventorySalesOrdersApi } = await import('@/lib/inventory-api')
      const result = await inventorySalesOrdersApi.stockCheck(order!.id)
      setStockCheck(result)
    } catch {
      setActionError('Error al verificar disponibilidad')
    } finally {
      setStockCheckLoading(false)
    }
  }

  const isDraftOrConfirmed = order.status === 'draft' || order.status === 'confirmed' || order.status === 'pending_approval' || order.status === 'rejected'

  return (
    <div className="space-y-6">
      <button onClick={() => navigate('/inventario/ventas')} className="flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground"><ArrowLeft className="h-4 w-4" /> Volver</button>

      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground">{order.order_number}</h1>
          <p className="text-sm text-muted-foreground mt-1">Cliente: <span className="font-semibold text-foreground">{order.customer_name ?? customer?.name ?? order.customer_id.slice(0, 8)}</span></p>
          {order.warehouse_name && <p className="text-xs text-muted-foreground mt-0.5">Bodega: <span className="font-medium text-muted-foreground">{order.warehouse_name}</span></p>}
        </div>
        <span className={cn('px-3 py-1 rounded-full text-sm font-bold', STATUS_CONFIG[order.status]?.color)}>{STATUS_CONFIG[order.status]?.label}</span>
      </div>

      {/* Progress steps */}
      {!isFinal && (
        <div className="flex items-center gap-0">
          {steps.map((s, i) => {
            const active = i <= currentStepIdx
            const isRejectedStep = order.status === 'rejected' && s === 'pending_approval'
            return (
              <div key={s} className="flex items-center flex-1 last:flex-none">
                <div className={cn('h-8 w-8 rounded-full flex items-center justify-center text-xs font-bold border-2',
                  isRejectedStep ? 'bg-red-500 text-white border-red-500' :
                  active ? 'bg-primary text-white border-primary' : 'bg-card text-muted-foreground border-border')}>
                  {i + 1}
                </div>
                {i < steps.length - 1 && <div className={cn('flex-1 h-0.5', i < currentStepIdx ? 'bg-primary' : 'bg-slate-200')} />}
              </div>
            )
          })}
        </div>
      )}

      {/* Remission number on shipped step */}
      {stepIdx >= 3 && order.remission_number && (
        <div className="flex items-center gap-2 text-xs">
          <TruckIcon className="h-3.5 w-3.5 text-orange-500" />
          <span className="text-muted-foreground">Remisión:</span>
          <span className="font-mono font-bold text-orange-700">{order.remission_number}</span>
          <button
            onClick={async () => {
              try {
                const { inventorySalesOrdersApi } = await import('@/lib/inventory-api')
                const { generateRemissionPDF } = await import('@/utils/generateRemissionPDF')
                const remData = await inventorySalesOrdersApi.getRemission(order.id)
                generateRemissionPDF(remData)
              } catch { /* ignore */ }
            }}
            className="text-orange-600 hover:text-orange-800 font-semibold"
          >
            PDF
          </button>
        </div>
      )}

      {/* Invoice status chip on confirmed step */}
      {stepIdx >= 1 && order.invoice_status && (
        <div className="flex items-center gap-2 text-xs">
          <FileText className="h-3.5 w-3.5 text-muted-foreground" />
          <span className="text-muted-foreground">Factura al confirmar:</span>
          <span className={cn(
            'inline-flex rounded-full px-2 py-0.5 font-semibold',
            order.invoice_status === 'issued' ? 'bg-emerald-50 text-emerald-700' :
            order.invoice_status === 'simulated' ? 'bg-amber-50 text-amber-700' :
            order.invoice_status === 'pending' ? 'bg-blue-50 text-blue-600' :
            order.invoice_status === 'failed' ? 'bg-red-50 text-red-600' :
            'bg-secondary text-muted-foreground',
          )}>
            {order.invoice_status === 'issued' ? 'Emitida' :
             order.invoice_status === 'simulated' ? 'Simulada' :
             order.invoice_status === 'pending' ? 'Pendiente' :
             order.invoice_status === 'failed' ? 'Fallida' :
             order.invoice_status}
          </span>
        </div>
      )}

      {/* Approval banners */}
      {order.status === 'pending_approval' && (
        <div className="flex items-start gap-3 bg-yellow-50 border border-yellow-200 rounded-xl px-4 py-3">
          <Clock className="h-5 w-5 text-yellow-500 flex-shrink-0 mt-0.5" />
          <div className="flex-1">
            <p className="text-sm font-semibold text-yellow-800">Pendiente de aprobación</p>
            <p className="text-xs text-yellow-600 mt-0.5">
              Enviado a aprobación {order.approval_requested_at ? new Date(order.approval_requested_at).toLocaleString('es-CO') : ''}
              {' — '}Total: ${order.total.toLocaleString('es-CO', { minimumFractionDigits: 2 })}
            </p>
            {authUser?.id !== order.created_by ? (
              <div className="mt-3 flex gap-2">
                <button onClick={() => { onMutate(); approveMut.mutate(order.id, { onError, onSuccess: () => toast.success('Orden aprobada') }) }} disabled={approveMut.isPending} className="flex items-center gap-1.5 px-4 py-2 text-sm font-semibold text-white bg-emerald-600 hover:bg-emerald-700 rounded-xl disabled:opacity-50"><Check className="h-4 w-4" /> Aprobar</button>
                <button onClick={() => setShowRejectModal(true)} className="flex items-center gap-1.5 px-4 py-2 text-sm font-semibold text-red-600 bg-red-50 hover:bg-red-100 rounded-xl"><XCircle className="h-4 w-4" /> Rechazar</button>
              </div>
            ) : (
              <p className="text-xs text-yellow-600 mt-1 italic">Esperando aprobación de un supervisor</p>
            )}
          </div>
        </div>
      )}

      {order.status === 'rejected' && (
        <div className="flex items-start gap-3 bg-red-50 border border-red-200 rounded-xl px-4 py-3">
          <XCircle className="h-5 w-5 text-red-500 flex-shrink-0 mt-0.5" />
          <div className="flex-1">
            <p className="text-sm font-semibold text-red-800">Orden rechazada</p>
            {order.rejected_by && <p className="text-xs text-red-600 mt-0.5">Rechazado el {order.rejected_at ? new Date(order.rejected_at).toLocaleString('es-CO') : ''}</p>}
            {order.rejection_reason && <p className="text-sm text-red-700 mt-1 bg-red-100 rounded-lg px-3 py-2">{order.rejection_reason}</p>}
            <button onClick={() => { onMutate(); resubmitMut.mutate(order.id, { onError, onSuccess: () => toast.success('Orden re-enviada a aprobación') }) }} disabled={resubmitMut.isPending} className="mt-3 flex items-center gap-1.5 px-4 py-2 text-sm font-semibold text-amber-700 bg-amber-50 hover:bg-amber-100 rounded-xl disabled:opacity-50"><RotateCcw className="h-4 w-4" /> Editar y re-enviar</button>
          </div>
        </div>
      )}

      {order.status === 'confirmed' && order.approval_required && order.approved_at && (
        <div className="flex items-center gap-3 bg-emerald-50 border border-emerald-200 rounded-xl px-4 py-3 text-sm">
          <Check className="h-5 w-5 text-emerald-500 flex-shrink-0" />
          <span className="text-emerald-800">Aprobado el {new Date(order.approved_at).toLocaleString('es-CO')}</span>
        </div>
      )}

      {/* Auto stock check warning — blocks picking/shipping */}
      {stockCheckAuto && !stockCheckAuto.ready_to_ship && (
        <div className="rounded-xl border border-red-200 bg-red-50 overflow-hidden">
          <div className="flex items-start gap-3 px-4 py-3">
            <AlertTriangle className="h-5 w-5 text-red-500 mt-0.5 shrink-0" />
            <div className="flex-1">
              <p className="text-sm font-bold text-red-800">Stock insuficiente — No se puede avanzar</p>
              <p className="text-xs text-red-600 mt-0.5">Resuelve el stock faltante antes de continuar con picking o envío.</p>
              <ul className="mt-2 text-xs text-red-700 space-y-1">
                {stockCheckAuto.lines.filter((item) => !item.sufficient).map((item, i: number) => (
                  <li key={i} className="flex items-center gap-2">
                    <span className="text-red-500 font-bold">✗</span>
                    <span className="font-semibold">{item.product_name}</span>
                    <span className="text-red-500">— disponible: {item.available}, requerido: {item.required} (faltan {(item.required - item.available).toLocaleString()})</span>
                  </li>
                ))}
              </ul>
              <div className="mt-3 flex flex-wrap gap-2 text-[10px] font-semibold">
                <span className="inline-flex items-center gap-1 rounded-full bg-blue-100 text-blue-700 px-2 py-0.5">Trasladar stock desde otra bodega</span>
                <span className="inline-flex items-center gap-1 rounded-full bg-amber-100 text-amber-700 px-2 py-0.5">Crear orden de compra</span>
                <span className="inline-flex items-center gap-1 rounded-full bg-slate-200 text-muted-foreground px-2 py-0.5">Eliminar línea sin stock</span>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Action buttons */}
      <div className="flex gap-2">
        {order.status === 'draft' && (
          <button onClick={() => setShowDiscount(true)}
            className="flex items-center gap-2 rounded-xl border border-border px-4 py-2 text-sm font-semibold text-foreground hover:bg-muted">
            <Percent className="h-4 w-4" /> Descuento
          </button>
        )}
        {order.status === 'draft' && <button onClick={() => {
          onMutate()
          confirmMut.mutate(order.id, {
            onError,
            onSuccess: (res) => {
              const r = res as ConfirmWithBackorderOut & { approval_required?: boolean; message?: string }
              if (r.approval_required) {
                toast.warning(r.message || 'Orden enviada a aprobación')
              } else if (r.split_preview?.has_backorder && r.backorder) {
                setLastBackorderResult(r)
                toast.warning(`Orden confirmada con backorder: ${r.backorder.order_number}`)
              } else {
                toast.success('Orden confirmada')
              }
            },
          })
        }} disabled={confirmMut.isPending} className="flex items-center gap-1.5 px-4 py-2 text-sm font-semibold text-white bg-blue-600 hover:bg-blue-700 rounded-xl disabled:opacity-50"><Check className="h-4 w-4" /> {confirmMut.isPending ? 'Confirmando...' : 'Confirmar'}</button>}
        {order.status === 'confirmed' && <button onClick={() => { onMutate(); pickMut.mutate(order.id, { onError }) }} disabled={pickMut.isPending || (stockCheckAuto != null && !stockCheckAuto.ready_to_ship)} title={stockCheckAuto && !stockCheckAuto.ready_to_ship ? 'Resuelve el stock insuficiente antes de iniciar picking' : undefined} className={cn("flex items-center gap-1.5 px-4 py-2 text-sm font-semibold rounded-xl disabled:opacity-50", stockCheckAuto && !stockCheckAuto.ready_to_ship ? "bg-slate-300 text-muted-foreground cursor-not-allowed" : "text-white bg-amber-600 hover:bg-amber-700")}><PackageCheck className="h-4 w-4" /> {pickMut.isPending ? 'Iniciando...' : 'Picking'}</button>}
        {order.status === 'picking' && <button onClick={() => { if (stockCheckAuto && !stockCheckAuto.ready_to_ship) { setActionError('No se puede enviar: hay productos sin stock suficiente. Verifica la sección de stock.'); return; } setShowShipModal(true) }} className={cn("flex items-center gap-1.5 px-4 py-2 text-sm font-semibold rounded-xl", stockCheckAuto && !stockCheckAuto.ready_to_ship ? "bg-slate-300 text-muted-foreground cursor-not-allowed" : "text-white bg-primary hover:bg-primary/90")}><TruckIcon className="h-4 w-4" /> Enviar</button>}
        {order.status === 'shipped' && <button onClick={() => { onMutate(); deliverMut.mutate(order.id, { onError }) }} disabled={deliverMut.isPending} className="flex items-center gap-1.5 px-4 py-2 text-sm font-semibold text-white bg-emerald-600 hover:bg-emerald-700 rounded-xl disabled:opacity-50"><CheckCircle2 className="h-4 w-4" /> {deliverMut.isPending ? 'Entregando...' : 'Entregar'}</button>}
        {order.status === 'delivered' && <button onClick={() => { onMutate(); returnMut.mutate(order.id, { onError }) }} disabled={returnMut.isPending} className="flex items-center gap-1.5 px-4 py-2 text-sm font-semibold text-white bg-orange-600 hover:bg-orange-700 rounded-xl disabled:opacity-50"><RotateCcw className="h-4 w-4" /> {returnMut.isPending ? 'Procesando...' : 'Devolver'}</button>}
        {!isFinal && <button onClick={() => { onMutate(); cancelMut.mutate(order.id, { onError }) }} disabled={cancelMut.isPending} className="flex items-center gap-1.5 px-4 py-2 text-sm font-semibold text-red-600 bg-red-50 hover:bg-red-100 rounded-xl disabled:opacity-50"><XCircle className="h-4 w-4" /> {cancelMut.isPending ? 'Cancelando...' : 'Cancelar'}</button>}
      </div>

      {/* Error banner */}
      {actionError && (
        <div className="flex items-start gap-3 bg-red-50 border border-red-200 rounded-xl px-4 py-3 text-sm text-red-700">
          <AlertTriangle className="h-5 w-5 text-red-500 flex-shrink-0 mt-0.5" />
          <div className="flex-1">
            <p className="font-semibold mb-1">No se pudo completar la accion</p>
            <div className="whitespace-pre-line">{actionError}</div>
          </div>
          <button onClick={() => setActionError(null)} className="text-red-400 hover:text-red-600 text-lg leading-none">&times;</button>
        </div>
      )}

      {/* Shipping info (shown after ship) */}
      {order.shipping_info && Object.values(order.shipping_info).some(v => v) && (
        <ShippingInfoCard info={order.shipping_info} />
      )}

      {/* Remission / delivery note section */}
      {order.remission_number && (order.status === 'shipped' || order.status === 'delivered') && (
        <div className="bg-card rounded-2xl border border-border/60  overflow-hidden">
          <div className="px-6 py-3 bg-orange-50 border-b border-orange-100">
            <h3 className="text-sm font-bold text-orange-800 flex items-center gap-2">
              <TruckIcon className="h-4 w-4" /> Remisión de Entrega
            </h3>
          </div>
          <div className="p-6 flex items-center justify-between">
            <div className="space-y-1">
              <p className="text-xs font-bold text-muted-foreground uppercase">Nº Remisión</p>
              <p className="text-lg font-bold font-mono text-orange-700">{order.remission_number}</p>
              <p className="text-xs text-muted-foreground">Fecha despacho: {order.shipped_date ? new Date(order.shipped_date).toLocaleDateString('es-CO') : '--'}</p>
            </div>
            <button
              onClick={async () => {
                try {
                  const { inventorySalesOrdersApi } = await import('@/lib/inventory-api')
                  const { generateRemissionPDF } = await import('@/utils/generateRemissionPDF')
                  const remData = await inventorySalesOrdersApi.getRemission(order.id)
                  generateRemissionPDF(remData)
                } catch {
                  setActionError('Error al generar la remisión PDF')
                }
              }}
              className="flex items-center gap-2 px-4 py-2.5 text-sm font-semibold text-orange-700 bg-orange-50 hover:bg-orange-100 rounded-xl transition"
            >
              <FileDown className="h-4 w-4" /> Descargar remisión PDF
            </button>
          </div>
        </div>
      )}

      {/* Factura Electrónica section */}
      {order.invoice_status && (
        <div className="bg-card rounded-2xl border border-border/60  overflow-hidden">
          <div className={cn(
            'px-6 py-3 border-b',
            order.invoice_provider === 'sandbox' ? 'bg-amber-50 border-amber-100' : 'bg-cyan-50 border-cyan-100',
          )}>
            <h3 className={cn(
              'text-sm font-bold flex items-center gap-2',
              order.invoice_provider === 'sandbox' ? 'text-amber-800' : 'text-cyan-800',
            )}>
              <FileText className="h-4 w-4" /> Factura Electrónica
            </h3>
          </div>
          <div className="p-6 space-y-3">
            <div className="flex items-center gap-3 flex-wrap">
              {/* Provider badge */}
              {order.invoice_provider === 'sandbox' ? (
                <span className="inline-flex rounded-full bg-amber-50 px-2.5 py-0.5 text-xs font-semibold text-amber-700">SANDBOX</span>
              ) : order.invoice_provider === 'matias' ? (
                <span className="inline-flex rounded-full bg-blue-50 px-2.5 py-0.5 text-xs font-semibold text-blue-700">MATIAS</span>
              ) : null}
              {/* Status badge */}
              <span className={cn(
                'inline-flex rounded-full px-2.5 py-0.5 text-xs font-semibold',
                order.invoice_status === 'issued' ? 'bg-emerald-50 text-emerald-700' :
                order.invoice_status === 'simulated' ? 'bg-amber-50 text-amber-700' :
                order.invoice_status === 'failed' ? 'bg-red-50 text-red-600' :
                'bg-secondary text-muted-foreground',
              )}>
                {order.invoice_status === 'issued' ? 'Emitida' :
                 order.invoice_status === 'simulated' ? 'Simulada' :
                 order.invoice_status === 'failed' ? 'Fallida' :
                 order.invoice_status}
              </span>
              {order.invoice_status === 'failed' && (
                <button
                  onClick={() => { onMutate(); retryInvoiceMut.mutate(order.id, { onError }) }}
                  disabled={retryInvoiceMut.isPending}
                  className="inline-flex items-center gap-1.5 rounded-lg bg-amber-50 px-3 py-1.5 text-xs font-medium text-amber-700 hover:bg-amber-100 transition disabled:opacity-50"
                >
                  <RefreshCw className={cn('h-3.5 w-3.5', retryInvoiceMut.isPending && 'animate-spin')} />
                  {retryInvoiceMut.isPending ? 'Reintentando...' : 'Reintentar factura'}
                </button>
              )}
            </div>
            {order.invoice_number && (
              <div>
                <p className="text-xs font-bold text-muted-foreground uppercase mb-1">Nº Factura</p>
                <p className="text-sm font-bold font-mono text-foreground">{order.invoice_number}</p>
              </div>
            )}
            {order.cufe && (
              <div>
                <p className="text-xs font-bold text-muted-foreground uppercase mb-1">CUFE</p>
                <div className="flex items-center gap-2">
                  <span className="text-xs font-mono text-muted-foreground" title={order.cufe}>{order.cufe.slice(0, 20)}...</span>
                  <button
                    onClick={() => navigator.clipboard.writeText(order.cufe!)}
                    className="text-muted-foreground hover:text-primary transition"
                    title="Copiar CUFE completo"
                  >
                    <Copy className="h-3.5 w-3.5" />
                  </button>
                </div>
              </div>
            )}
            {order.invoice_pdf_url && (
              <a
                href={order.invoice_pdf_url}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1.5 rounded-lg bg-primary/10 px-4 py-2 text-sm font-medium text-primary hover:bg-primary/15 transition"
              >
                <ExternalLink className="h-4 w-4" /> Descargar PDF
              </a>
            )}
            {order.invoice_provider === 'sandbox' && order.cufe && (
              <button
                onClick={() => generateSandboxInvoicePDF({
                  company_name: authUser?.company ?? 'Mi Empresa',
                  company_nit: authUser?.tenant_id ?? '000000000',
                  company_email: authUser?.email,
                  customer_name: order.customer_name ?? 'Cliente',
                  customer_nit: '222222222',
                  invoice_number: order.order_number,
                  invoice_date: order.confirmed_at
                    ? new Date(order.confirmed_at).toLocaleDateString('es-CO')
                    : new Date().toLocaleDateString('es-CO'),
                  cufe: order.cufe,
                  items: order.lines.map(l => ({
                    description: l.product_name ?? l.product_id.slice(0, 8),
                    quantity: l.qty_shipped,
                    unit_price: l.unit_price,
                    discount_pct: l.discount_pct,
                    tax_rate: l.tax_rate ? l.tax_rate / 100 : 0.19,
                    total: l.line_total,
                  })),
                  subtotal: order.subtotal,
                  discount_pct: order.discount_pct,
                  discount_amount: order.discount_amount,
                  tax_amount: order.tax_amount,
                  total: order.total,
                })}
                className="inline-flex items-center gap-1.5 rounded-lg bg-amber-50 px-4 py-2 text-sm font-medium text-amber-700 hover:bg-amber-100 transition"
              >
                <FileDown className="h-4 w-4" /> Descargar vista previa PDF
              </button>
            )}
            {order.invoice_status === 'simulated' && (
              <p className="text-xs text-muted-foreground italic">Sin validez ante la DIAN</p>
            )}
          </div>
        </div>
      )}

      {/* Nota Crédito section */}
      {order.credit_note_status && (
        <div className="bg-card rounded-2xl border border-border/60  overflow-hidden">
          <div className={cn(
            'px-6 py-3 border-b',
            order.invoice_provider === 'sandbox' ? 'bg-orange-50 border-orange-100' : 'bg-rose-50 border-rose-100',
          )}>
            <h3 className={cn(
              'text-sm font-bold flex items-center gap-2',
              order.invoice_provider === 'sandbox' ? 'text-orange-800' : 'text-rose-800',
            )}>
              <RotateCcw className="h-4 w-4" /> Nota Crédito
            </h3>
          </div>
          <div className="p-6 space-y-3">
            <div className="flex items-center gap-3 flex-wrap">
              {order.invoice_provider === 'sandbox' ? (
                <span className="inline-flex rounded-full bg-amber-50 px-2.5 py-0.5 text-xs font-semibold text-amber-700">SANDBOX</span>
              ) : order.invoice_provider === 'matias' ? (
                <span className="inline-flex rounded-full bg-blue-50 px-2.5 py-0.5 text-xs font-semibold text-blue-700">MATIAS</span>
              ) : null}
              <span className={cn(
                'inline-flex rounded-full px-2.5 py-0.5 text-xs font-semibold',
                order.credit_note_status === 'issued' ? 'bg-emerald-50 text-emerald-700' :
                order.credit_note_status === 'simulated' ? 'bg-amber-50 text-amber-700' :
                order.credit_note_status === 'failed' ? 'bg-red-50 text-red-600' :
                'bg-secondary text-muted-foreground',
              )}>
                {order.credit_note_status === 'issued' ? 'Emitida' :
                 order.credit_note_status === 'simulated' ? 'Simulada' :
                 order.credit_note_status === 'failed' ? 'Fallida' :
                 order.credit_note_status}
              </span>
              {order.credit_note_status === 'failed' && (
                <button
                  onClick={() => { onMutate(); retryCreditNoteMut.mutate(order.id, { onError }) }}
                  disabled={retryCreditNoteMut.isPending}
                  className="inline-flex items-center gap-1.5 rounded-lg bg-amber-50 px-3 py-1.5 text-xs font-medium text-amber-700 hover:bg-amber-100 transition disabled:opacity-50"
                >
                  <RefreshCw className={cn('h-3.5 w-3.5', retryCreditNoteMut.isPending && 'animate-spin')} />
                  {retryCreditNoteMut.isPending ? 'Reintentando...' : 'Reintentar nota crédito'}
                </button>
              )}
            </div>
            {order.credit_note_number && (
              <div>
                <p className="text-xs font-bold text-muted-foreground uppercase mb-1">Nº Nota Crédito</p>
                <p className="text-sm font-bold font-mono text-foreground">{order.credit_note_number}</p>
              </div>
            )}
            {order.credit_note_cufe && (
              <div>
                <p className="text-xs font-bold text-muted-foreground uppercase mb-1">CUFE Nota Crédito</p>
                <div className="flex items-center gap-2">
                  <span className="text-xs font-mono text-muted-foreground" title={order.credit_note_cufe}>{order.credit_note_cufe.slice(0, 20)}...</span>
                  <button
                    onClick={() => navigator.clipboard.writeText(order.credit_note_cufe!)}
                    className="text-muted-foreground hover:text-primary transition"
                    title="Copiar CUFE completo"
                  >
                    <Copy className="h-3.5 w-3.5" />
                  </button>
                </div>
              </div>
            )}
            {order.credit_note_status === 'simulated' && (
              <p className="text-xs text-muted-foreground italic">Sin validez ante la DIAN</p>
            )}
          </div>
        </div>
      )}

      {/* Totals breakdown */}
      <div className="bg-card rounded-2xl border border-border/60  p-6">
        <div className="max-w-sm ml-auto space-y-2 text-sm">
          {/* Savings from special prices */}
          {(() => {
            const savings = (order.lines ?? []).reduce((acc, l) => {
              if (l.price_source === 'customer_special' && l.original_unit_price != null && l.original_unit_price > l.unit_price) {
                return acc + (l.original_unit_price - l.unit_price) * l.qty_ordered;
              }
              return acc;
            }, 0);
            const originalTotal = (order.lines ?? []).reduce((acc, l) => {
              if (l.price_source === 'customer_special' && l.original_unit_price != null) {
                return acc + l.original_unit_price * l.qty_ordered;
              }
              return acc + l.unit_price * l.qty_ordered;
            }, 0);
            if (savings > 0) {
              return (
                <div className="bg-blue-50/60 border border-blue-100 rounded-lg p-3 mb-2 space-y-1">
                  <div className="flex justify-between text-blue-600">
                    <span className="font-medium">Valor original (sin descuentos)</span>
                    <span className="font-mono font-semibold">${originalTotal.toLocaleString('es-CO', { minimumFractionDigits: 2 })}</span>
                  </div>
                  <div className="flex justify-between text-emerald-600">
                    <span className="font-medium flex items-center gap-1">Ahorro por precios especiales</span>
                    <span className="font-mono font-bold">-${savings.toLocaleString('es-CO', { minimumFractionDigits: 2 })}</span>
                  </div>
                  <div className="text-[10px] text-blue-500">
                    {(order.lines ?? []).filter(l => l.price_source === 'customer_special' && l.original_unit_price != null).length} línea(s) con precio especial · {Math.round((savings / originalTotal) * 100)}% de ahorro promedio
                  </div>
                </div>
              );
            }
            return null;
          })()}
          <div className="flex justify-between text-muted-foreground"><span>Subtotal (lineas)</span><span className="font-mono font-semibold">${order.subtotal.toLocaleString('es-CO', { minimumFractionDigits: 2 })}</span></div>
          {order.discount_pct > 0 && (
            <div className="flex justify-between text-amber-600">
              <span>Descuento global ({order.discount_pct}%){order.discount_reason ? ` — ${order.discount_reason}` : ''}</span>
              <span className="font-mono font-semibold">-${order.discount_amount.toLocaleString('es-CO', { minimumFractionDigits: 2 })}</span>
            </div>
          )}
          {order.discount_pct > 0 && (
            <div className="flex justify-between text-muted-foreground"><span>Base gravable</span><span className="font-mono">${(order.subtotal - order.discount_amount).toLocaleString('es-CO', { minimumFractionDigits: 2 })}</span></div>
          )}
          <div className="flex justify-between text-muted-foreground"><span>IVA</span><span className="font-mono font-semibold">${order.tax_amount.toLocaleString('es-CO', { minimumFractionDigits: 2 })}</span></div>
          {(order.total_retention ?? 0) > 0 && (
            <div className="flex justify-between text-orange-600"><span>Retención en la fuente</span><span className="font-mono font-semibold">-${(order.total_retention ?? 0).toLocaleString('es-CO', { minimumFractionDigits: 2 })}</span></div>
          )}
          <div className="flex justify-between text-muted-foreground border-t border-border pt-1"><span>Subtotal + IVA</span><span className="font-mono">${(order.total_with_tax ?? order.total).toLocaleString('es-CO', { minimumFractionDigits: 2 })}</span></div>
          <div className="flex justify-between font-bold text-lg text-primary border-t border-border pt-2"><span>Total a pagar</span><span className="font-mono">${(order.total_payable ?? order.total).toLocaleString('es-CO', { minimumFractionDigits: 2 })} {order.currency}</span></div>
        </div>
      </div>

      {/* Stock check section */}
      {['confirmed', 'picking'].includes(order.status) && (
        <div className="bg-card rounded-2xl border border-border/60  overflow-hidden">
          <div className="px-6 py-3 bg-muted border-b border-border/60 flex items-center justify-between">
            <h3 className="text-sm font-bold text-foreground flex items-center gap-2"><ClipboardCheck className="h-4 w-4" /> Verificacion de Stock</h3>
            <button
              onClick={runStockCheck}
              disabled={stockCheckLoading}
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold text-primary bg-primary/10 hover:bg-primary/15 rounded-lg transition disabled:opacity-50"
            >
              {stockCheckLoading ? <RefreshCw className="h-3.5 w-3.5 animate-spin" /> : <ClipboardCheck className="h-3.5 w-3.5" />}
              {stockCheckLoading ? 'Verificando...' : 'Verificar disponibilidad'}
            </button>
          </div>
          {stockCheck && (
            <div className="p-4">
              <div className={cn(
                'inline-flex rounded-full px-3 py-1 text-xs font-bold mb-3',
                stockCheck.ready_to_ship ? 'bg-emerald-50 text-emerald-700' : 'bg-red-50 text-red-600',
              )}>
                {stockCheck.ready_to_ship ? '✓ Listo para despachar' : '✗ Stock insuficiente'}
              </div>
              <table className="w-full text-sm">
                <thead><tr className="text-left text-xs font-semibold text-muted-foreground uppercase">
                  <th className="px-3 py-2">Producto</th>
                  <th className="px-3 py-2">Bodega</th>
                  <th className="px-3 py-2 text-right">Requerido</th>
                  <th className="px-3 py-2 text-right">Disponible</th>
                  <th className="px-3 py-2 text-center">Estado</th>
                </tr></thead>
                <tbody className="divide-y divide-slate-100">
                  {stockCheck.lines.map(l => (
                    <tr key={l.line_id}>
                      <td className="px-3 py-2 text-foreground">{l.product_name}</td>
                      <td className="px-3 py-2 text-muted-foreground">{l.warehouse_name}</td>
                      <td className="px-3 py-2 text-right font-mono">{l.required}</td>
                      <td className="px-3 py-2 text-right font-mono">{l.available}</td>
                      <td className="px-3 py-2 text-center">
                        {l.sufficient
                          ? <span className="text-emerald-500 font-bold">✓</span>
                          : <span className="text-red-500 font-bold">✗</span>}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* Stock reservations section */}
      {reservations.length > 0 && (
        <div className="bg-card rounded-2xl border border-border/60  overflow-hidden">
          <div className="px-6 py-3 bg-blue-50 border-b border-blue-200/60">
            <h3 className="text-sm font-bold text-blue-800 flex items-center gap-2"><Lock className="h-4 w-4" /> Reservas de Stock ({reservations.length})</h3>
          </div>
          <table className="w-full text-sm">
            <thead><tr className="bg-muted text-left text-xs font-semibold text-muted-foreground uppercase">
              <th className="px-6 py-2">Producto</th>
              <th className="px-6 py-2">Bodega</th>
              <th className="px-6 py-2 text-right">Cantidad</th>
              <th className="px-6 py-2 text-center">Estado</th>
              <th className="px-6 py-2">Fecha</th>
            </tr></thead>
            <tbody className="divide-y divide-slate-100">
              {reservations.map((r: StockReservation) => (
                <tr key={r.id}>
                  <td className="px-6 py-2">
                    <span className="font-medium text-foreground">{r.product_name ?? r.product_id.slice(0, 8)}</span>
                    {r.product_sku && <span className="ml-2 text-xs text-muted-foreground">{r.product_sku}</span>}
                  </td>
                  <td className="px-6 py-2 text-muted-foreground">{r.warehouse_name ?? r.warehouse_id.slice(0, 8)}</td>
                  <td className="px-6 py-2 text-right font-mono">{r.quantity}</td>
                  <td className="px-6 py-2 text-center">
                    <span className={cn('inline-flex rounded-full px-2 py-0.5 text-[10px] font-bold',
                      r.status === 'active' ? 'bg-emerald-50 text-emerald-700' :
                      r.status === 'consumed' ? 'bg-secondary text-muted-foreground' :
                      'bg-secondary text-muted-foreground'
                    )}>
                      {r.status === 'active' ? 'Activa' : r.status === 'consumed' ? 'Consumida' : 'Liberada'}
                    </span>
                    {r.released_reason && <span className="ml-1 text-[10px] text-muted-foreground">({r.released_reason})</span>}
                  </td>
                  <td className="px-6 py-2 text-xs text-muted-foreground">{r.reserved_at ? new Date(r.reserved_at).toLocaleDateString() : ''}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Backorder info banner */}
      {order.is_backorder && order.parent_so_id && (
        <div className="flex items-center gap-3 bg-amber-50 border border-amber-200 rounded-xl px-4 py-3 text-sm text-amber-800">
          <Package className="h-5 w-5 text-amber-500 flex-shrink-0" />
          <div>
            <span className="font-semibold">Backorder #{order.backorder_number}</span> — Esta orden fue creada automaticamente por stock insuficiente.
            <button onClick={() => navigate(`/inventario/ventas/${order.parent_so_id}`)} className="ml-2 text-amber-700 underline hover:text-amber-900">Ver orden original</button>
          </div>
        </div>
      )}

      {/* Backorder children section */}
      {(backorders.length > 0 || (order.backorder_ids && order.backorder_ids.length > 0)) && (
        <div className="bg-card rounded-2xl border border-border/60  overflow-hidden">
          <div className="px-6 py-3 bg-amber-50 border-b border-amber-200/60">
            <h3 className="text-sm font-bold text-amber-800 flex items-center gap-2"><Package className="h-4 w-4" /> Backorders ({backorders.length})</h3>
          </div>
          <div className="divide-y divide-slate-100">
            {backorders.map((bo: { id: string; order_number: string; status: string; total: number; currency: string; lines: Array<{ id: string }> }) => (
              <div key={bo.id} className="px-6 py-3 flex items-center justify-between hover:bg-muted cursor-pointer" onClick={() => navigate(`/inventario/ventas/${bo.id}`)}>
                <div className="flex items-center gap-3">
                  <span className="font-mono text-sm font-semibold text-foreground">{bo.order_number}</span>
                  <span className={cn('inline-flex rounded-full px-2.5 py-0.5 text-xs font-semibold',
                    STATUS_CONFIG[bo.status as SalesOrderStatus]?.color ?? 'bg-secondary text-muted-foreground',
                  )}>
                    {STATUS_CONFIG[bo.status as SalesOrderStatus]?.label ?? bo.status}
                  </span>
                  <span className="text-xs text-muted-foreground">{bo.lines?.length ?? 0} lineas</span>
                </div>
                <span className="font-mono text-sm font-bold text-foreground">{bo.currency} {bo.total?.toLocaleString('es-CO', { minimumFractionDigits: 2 })}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Approval history */}
      {approvalLog.length > 0 && (
        <div className="bg-card rounded-2xl border border-border/60  overflow-hidden">
          <div className="px-6 py-3 bg-yellow-50 border-b border-yellow-100">
            <h3 className="text-sm font-bold text-yellow-800 flex items-center gap-2"><Clock className="h-4 w-4" /> Historial de Aprobación</h3>
          </div>
          <div className="p-4 space-y-3">
            {approvalLog.map((entry: { id: string; action: string; performed_by_name: string | null; performed_by: string; created_at: string | null; reason: string | null; so_total_at_action: number }) => (
              <div key={entry.id} className="flex items-start gap-3">
                <div className={cn('h-2.5 w-2.5 rounded-full mt-1.5 shrink-0',
                  entry.action === 'approved' ? 'bg-emerald-500' :
                  entry.action === 'rejected' ? 'bg-red-500' :
                  entry.action === 'resubmitted' ? 'bg-amber-500' :
                  'bg-blue-500'
                )} />
                <div>
                  <p className="text-sm text-foreground">
                    <span className="font-semibold">
                      {entry.action === 'requested' ? 'Enviado a aprobación' :
                       entry.action === 'approved' ? 'Aprobado' :
                       entry.action === 'rejected' ? 'Rechazado' :
                       entry.action === 'resubmitted' ? 'Re-enviado' : entry.action}
                    </span>
                    {' por '}
                    <span className="font-medium">{entry.performed_by_name || entry.performed_by}</span>
                  </p>
                  {entry.reason && <p className="text-sm text-red-600 mt-0.5">{entry.reason}</p>}
                  <p className="text-xs text-muted-foreground">{entry.created_at ? new Date(entry.created_at).toLocaleString('es-CO') : ''} — Total: ${entry.so_total_at_action.toLocaleString('es-CO')}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Split preview after confirm */}
      {lastBackorderResult?.split_preview?.has_backorder && (
        <div className="bg-card rounded-2xl border border-amber-200  overflow-hidden">
          <div className="px-6 py-3 bg-amber-50 border-b border-amber-200/60">
            <h3 className="text-sm font-bold text-amber-800 flex items-center gap-2"><AlertTriangle className="h-4 w-4" /> Division de orden por stock insuficiente</h3>
          </div>
          <div className="p-4">
            <table className="w-full text-sm">
              <thead><tr className="text-left text-xs font-semibold text-muted-foreground uppercase">
                <th className="px-3 py-2">Producto</th>
                <th className="px-3 py-2 text-right">Pedido</th>
                <th className="px-3 py-2 text-right">Confirmado</th>
                <th className="px-3 py-2 text-right">Backorder</th>
              </tr></thead>
              <tbody className="divide-y divide-slate-100">
                {lastBackorderResult.split_preview.lines.filter(l => l.qty_backordered > 0).map((l, i) => (
                  <tr key={i}>
                    <td className="px-3 py-2 text-foreground">{l.product_name} {l.product_sku && <span className="text-xs text-muted-foreground ml-1">{l.product_sku}</span>}</td>
                    <td className="px-3 py-2 text-right font-mono">{l.qty_ordered}</td>
                    <td className="px-3 py-2 text-right font-mono text-emerald-600">{l.qty_confirmable}</td>
                    <td className="px-3 py-2 text-right font-mono text-amber-600">{l.qty_backordered}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            {lastBackorderResult.backorder && (
              <div className="mt-3 flex items-center gap-2">
                <span className="text-sm text-muted-foreground">Backorder creado:</span>
                <button onClick={() => navigate(`/inventario/ventas/${lastBackorderResult.backorder!.id}`)} className="text-sm font-semibold text-amber-700 underline hover:text-amber-900">
                  {lastBackorderResult.backorder.order_number}
                </button>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Lines table */}
      <div className="bg-card rounded-2xl border border-border/60  overflow-hidden">
        <table className="w-full text-sm">
          <thead><tr className="bg-muted text-left text-xs font-semibold text-muted-foreground uppercase">
            <th className="px-6 py-3">Producto</th>
            <th className="px-6 py-3">Bodega</th>
            <th className="px-6 py-3 text-right">Cant. Pedida</th>
            <th className="px-6 py-3 text-right">Cant. Enviada</th>
            <th className="px-6 py-3 text-right">Precio Unit.</th>
            <th className="px-6 py-3 text-right">Desc. %</th>
            <th className="px-6 py-3 text-right">IVA %</th>
            <th className="px-6 py-3 text-right">IVA $</th>
            <th className="px-6 py-3 text-right">Ret. %</th>
            <th className="px-6 py-3 text-right">Ret. $</th>
            <th className="px-6 py-3 text-right">Total</th>
          </tr></thead>
          <tbody className="divide-y divide-slate-100">
            {order.lines.map(l => (
              <tr key={l.id}>
                <td className="px-6 py-3">
                  <span className="text-sm font-medium text-foreground">{l.product_name ?? l.product_id.slice(0, 8)}</span>
                  {l.product_sku && <span className="ml-2 text-xs text-muted-foreground">{l.product_sku}</span>}
                  {l.variant_name && <span className="block text-xs text-primary/80 mt-0.5">{l.variant_name}</span>}
                </td>
                <td className="px-6 py-3">
                  {isDraftOrConfirmed ? (
                    <select
                      value={l.warehouse_id ?? ''}
                      onChange={e => {
                        if (e.target.value) {
                          updateLineWhMut.mutate({ orderId: order.id, lineId: l.id, warehouseId: e.target.value }, { onError })
                        }
                      }}
                      className="rounded-lg border border-border px-2 py-1 text-xs focus:ring-2 focus:ring-ring"
                    >
                      <option value="">{order.warehouse_name ? `Bodega SO (${order.warehouse_name})` : 'Sin bodega'}</option>
                      {warehouses.map(w => <option key={w.id} value={w.id}>{w.name}</option>)}
                    </select>
                  ) : (
                    <span className="text-sm text-muted-foreground">
                      {l.warehouse_name ?? order.warehouse_name ?? '—'}
                      {l.warehouse_id && l.warehouse_id !== order.warehouse_id ? (
                        <span className="ml-1.5 inline-flex rounded-full bg-blue-50 px-1.5 py-0.5 text-[10px] font-semibold text-blue-600">Específica</span>
                      ) : l.warehouse_id ? null : (
                        <span className="ml-1.5 inline-flex rounded-full bg-secondary px-1.5 py-0.5 text-[10px] font-semibold text-muted-foreground">Bodega SO</span>
                      )}
                    </span>
                  )}
                </td>
                <td className="px-6 py-3 text-right font-mono">{l.qty_ordered}</td>
                <td className="px-6 py-3 text-right font-mono">{l.qty_shipped}</td>
                <td className="px-6 py-3 text-right">
                  <span className="font-mono">${l.unit_price.toLocaleString()}</span>
                  {l.price_source === 'customer_special' && l.original_unit_price != null && (
                    <div className="mt-0.5">
                      <span className="text-[10px] text-muted-foreground line-through font-mono">${l.original_unit_price.toLocaleString()}</span>
                      <span className="ml-1 inline-flex rounded-full bg-blue-50 px-1.5 py-0.5 text-[10px] font-semibold text-blue-700">
                        Precio especial ({Math.round((1 - l.unit_price / l.original_unit_price) * 100)}% dto.)
                      </span>
                    </div>
                  )}
                  {l.price_source === 'manual' && (
                    <div className="mt-0.5">
                      {l.original_unit_price != null && (
                        <span className="text-[10px] text-muted-foreground line-through font-mono mr-1">${l.original_unit_price.toLocaleString()}</span>
                      )}
                      <span className="inline-flex rounded-full bg-amber-50 px-1.5 py-0.5 text-[10px] font-semibold text-amber-700">Manual</span>
                    </div>
                  )}
                </td>
                <td className="px-6 py-3 text-right">
                  {l.discount_pct > 0 ? (
                    <span className="inline-flex rounded-full bg-amber-50 px-2 py-0.5 text-xs font-semibold text-amber-700">{l.discount_pct}%</span>
                  ) : <span className="text-slate-300">—</span>}
                </td>
                <td className="px-6 py-3 text-right">{l.tax_rate}%</td>
                <td className="px-6 py-3 text-right font-mono text-xs">${(l.tax_amount ?? 0).toLocaleString('es-CO', { minimumFractionDigits: 2 })}</td>
                <td className="px-6 py-3 text-right">{(l.retention_pct ?? 0) > 0 ? `${l.retention_pct}%` : <span className="text-slate-300">—</span>}</td>
                <td className="px-6 py-3 text-right font-mono text-xs">{(l.retention_amount ?? 0) > 0 ? `$${(l.retention_amount ?? 0).toLocaleString('es-CO', { minimumFractionDigits: 2 })}` : <span className="text-slate-300">—</span>}</td>
                <td className="px-6 py-3 text-right font-bold">${l.line_total.toLocaleString()}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Batch Traceability */}
      <BatchTraceabilitySection orderId={order.id} status={order.status} />

      {/* Notes */}
      {order.notes && (
        <div className="bg-card rounded-xl border border-border/60 p-4">
          <p className="text-xs font-bold text-muted-foreground uppercase mb-2">Notas</p>
          <p className="text-sm text-foreground">{order.notes}</p>
        </div>
      )}

      {/* Ship modal */}
      {showShipModal && (
        <ShipModal
          onClose={() => setShowShipModal(false)}
          onSubmit={handleShip}
          isPending={shipMut.isPending}
        />
      )}

      {/* Discount modal */}
      {showDiscount && order && (
        <DiscountModal
          orderId={order.id}
          currentDiscount={order.discount_pct}
          onClose={() => setShowDiscount(false)}
        />
      )}

      {/* Reject modal */}
      {showRejectModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 backdrop-blur-sm">
          <div className="w-full max-w-md bg-card rounded-3xl shadow-2xl p-6">
            <h2 className="text-lg font-bold text-foreground mb-1">Rechazar Orden</h2>
            <p className="text-xs text-muted-foreground mb-4">Indica el motivo del rechazo (mínimo 10 caracteres).</p>
            <textarea
              value={rejectReason}
              onChange={e => setRejectReason(e.target.value)}
              rows={3}
              className="w-full rounded-xl border border-border px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-red-400"
              placeholder="Motivo del rechazo..."
            />
            <div className="flex justify-end gap-3 mt-4">
              <button onClick={() => { setShowRejectModal(false); setRejectReason('') }} className="px-4 py-2 text-sm font-medium text-muted-foreground hover:text-foreground">Cancelar</button>
              <button
                onClick={() => {
                  if (rejectReason.trim().length < 10) { setActionError('El motivo debe tener al menos 10 caracteres'); return }
                  onMutate()
                  rejectMut.mutate({ id: order.id, reason: rejectReason.trim() }, {
                    onError,
                    onSuccess: () => { setShowRejectModal(false); setRejectReason(''); toast.success('Orden rechazada') },
                  })
                }}
                disabled={rejectMut.isPending || rejectReason.trim().length < 10}
                className="px-5 py-2 text-sm font-semibold text-white bg-red-600 hover:bg-red-700 rounded-xl disabled:opacity-50"
              >
                {rejectMut.isPending ? 'Rechazando...' : 'Rechazar'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
