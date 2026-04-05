import { useState } from 'react'
import { Link } from 'react-router-dom'
import {
  ChevronRight, AlertTriangle, CheckCircle2, XCircle, Hash, RefreshCw, Settings2,
  ChevronDown, FileText, CreditCard, Receipt, ShoppingCart, ReceiptText,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { useResolution, useCreateResolution, useDeactivateResolution } from '@/hooks/useIntegrations'

/* ── Document type definitions ──────────────────────────────────────────────── */

const DOC_TYPES = [
  { slug: 'matias_fev', label: 'Factura Electrónica de Venta', prefix: 'FEV', icon: FileText, color: 'text-blue-600 bg-blue-50' },
  { slug: 'matias_nc',  label: 'Nota Crédito',                prefix: 'NC',  icon: CreditCard, color: 'text-emerald-600 bg-emerald-50' },
  { slug: 'matias_nd',  label: 'Nota Débito',                 prefix: 'ND',  icon: Receipt, color: 'text-amber-600 bg-amber-50' },
  { slug: 'matias_ds',  label: 'Documento Soporte Electrónico', prefix: 'DS', icon: ReceiptText, color: 'text-purple-600 bg-purple-50' },
  { slug: 'matias_pos', label: 'POS Electrónico',             prefix: 'DPOS', icon: ShoppingCart, color: 'text-pink-600 bg-pink-50' },
  { slug: 'matias_er',  label: 'Eventos de Recepción',        prefix: 'ER',  icon: RefreshCw, color: 'text-cyan-600 bg-cyan-50' },
] as const

/* ── Single resolution section ──────────────────────────────────────────────── */

function ResolutionSection({ slug, label, defaultPrefix, icon: Icon, colorClass }: {
  slug: string; label: string; defaultPrefix: string; icon: React.ComponentType<{ className?: string }>; colorClass: string
}) {
  const { data: res, isLoading, error } = useResolution(slug)
  const createMut = useCreateResolution()
  const deactivateMut = useDeactivateResolution()
  const hasRes = !!res && !error

  const [expanded, setExpanded] = useState(false)
  const [form, setForm] = useState({
    resolution_number: '',
    prefix: defaultPrefix,
    range_from: '1',
    range_to: '1000',
    valid_from: '',
    valid_to: '',
  })

  function populateForm() {
    if (res) {
      setForm({
        resolution_number: res.resolution_number,
        prefix: res.prefix,
        range_from: String(res.range_from),
        range_to: String(res.range_to),
        valid_from: res.valid_from,
        valid_to: res.valid_to,
      })
    }
  }

  async function handleSave(e: React.FormEvent) {
    e.preventDefault()
    await createMut.mutateAsync({
      provider: slug,
      data: {
        provider: slug,
        resolution_number: form.resolution_number,
        prefix: form.prefix,
        range_from: Number(form.range_from),
        range_to: Number(form.range_to),
        valid_from: form.valid_from,
        valid_to: form.valid_to,
      },
    })
    setExpanded(false)
  }

  return (
    <div className="rounded-xl border border-border bg-card overflow-hidden">
      <button
        onClick={() => setExpanded(v => !v)}
        className="w-full flex items-center justify-between px-5 py-3.5 hover:bg-muted/30 transition-colors"
      >
        <div className="flex items-center gap-3">
          <div className={cn('flex h-9 w-9 items-center justify-center rounded-lg', colorClass)}>
            <Icon className="h-4.5 w-4.5" />
          </div>
          <div className="text-left">
            <h3 className="text-sm font-semibold text-foreground">{label}</h3>
            <div className="flex items-center gap-2 mt-0.5">
              {isLoading ? (
                <span className="text-[10px] text-muted-foreground">Cargando...</span>
              ) : hasRes ? (
                <>
                  <span className="text-[10px] text-muted-foreground font-mono">{res.prefix}{res.current_number + 1}</span>
                  <span className="text-[10px] text-muted-foreground">·</span>
                  <span className="text-[10px] text-muted-foreground">{res.remaining.toLocaleString()} restantes</span>
                  {res.is_expired ? (
                    <span className="inline-flex items-center gap-0.5 rounded-full bg-red-50 px-1.5 py-0.5 text-[9px] font-semibold text-red-600"><XCircle className="h-2.5 w-2.5" /> Vencida</span>
                  ) : (
                    <span className="inline-flex items-center gap-0.5 rounded-full bg-emerald-50 px-1.5 py-0.5 text-[9px] font-semibold text-emerald-600"><CheckCircle2 className="h-2.5 w-2.5" /> Vigente</span>
                  )}
                </>
              ) : (
                <span className="inline-flex items-center gap-0.5 rounded-full bg-secondary px-1.5 py-0.5 text-[9px] font-semibold text-muted-foreground">Sin configurar</span>
              )}
            </div>
          </div>
        </div>
        <ChevronDown className={cn('h-4 w-4 text-muted-foreground transition-transform', expanded && 'rotate-180')} />
      </button>

      {expanded && (
        <div className="border-t border-border px-5 py-4 space-y-4">
          {/* Current resolution details */}
          {hasRes && (
            <div className="space-y-3">
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                <div>
                  <p className="text-[10px] font-medium text-muted-foreground uppercase">Nº Resolución</p>
                  <p className="text-sm font-bold text-foreground">{res.resolution_number}</p>
                </div>
                <div>
                  <p className="text-[10px] font-medium text-muted-foreground uppercase">Prefijo</p>
                  <p className="text-sm font-bold text-foreground">{res.prefix}</p>
                </div>
                <div>
                  <p className="text-[10px] font-medium text-muted-foreground uppercase">Rango</p>
                  <p className="text-sm font-bold text-foreground">{res.range_from.toLocaleString()} — {res.range_to.toLocaleString()}</p>
                </div>
                <div>
                  <p className="text-[10px] font-medium text-muted-foreground uppercase">Vigente hasta</p>
                  <p className={cn('text-sm font-bold', res.is_expired ? 'text-red-600' : 'text-foreground')}>
                    {new Date(res.valid_to).toLocaleDateString('es-CO')}
                  </p>
                </div>
              </div>
              <div className="grid grid-cols-3 gap-3">
                <div className="rounded-lg border border-border bg-muted p-3">
                  <p className="text-[10px] font-medium text-muted-foreground uppercase">Emitidos</p>
                  <p className="text-lg font-bold text-foreground">{res.current_number.toLocaleString()}</p>
                </div>
                <div className="rounded-lg border border-border bg-muted p-3">
                  <p className="text-[10px] font-medium text-muted-foreground uppercase">Restantes</p>
                  <p className={cn('text-lg font-bold', res.remaining < 100 ? 'text-red-600' : 'text-foreground')}>
                    {res.remaining.toLocaleString()}
                  </p>
                </div>
                <div className="rounded-lg border border-border bg-muted p-3">
                  <p className="text-[10px] font-medium text-muted-foreground uppercase">Próximo</p>
                  <p className="text-lg font-bold text-primary font-mono">{res.next_invoice_number}</p>
                </div>
              </div>
            </div>
          )}

          {/* Form */}
          <div className="pt-2">
            <div className="flex items-center justify-between mb-3">
              <h4 className="text-xs font-semibold text-muted-foreground uppercase">
                {hasRes ? 'Actualizar resolución' : 'Configurar resolución'}
              </h4>
              {hasRes && (
                <button type="button" onClick={populateForm} className="text-[10px] text-primary hover:underline font-medium">
                  Cargar datos actuales
                </button>
              )}
            </div>
            <form onSubmit={handleSave} className="space-y-3">
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                <div>
                  <label className="mb-1 block text-xs font-medium text-foreground">Nº Resolución</label>
                  <input value={form.resolution_number} onChange={e => setForm(f => ({ ...f, resolution_number: e.target.value }))} required
                    className="h-9 w-full rounded-lg border border-border bg-muted px-2.5 text-sm focus:border-primary/50 focus:outline-none focus:ring-2 focus:ring-ring/20"
                    placeholder="18760000001" />
                </div>
                <div>
                  <label className="mb-1 block text-xs font-medium text-foreground">Prefijo</label>
                  <input value={form.prefix} onChange={e => setForm(f => ({ ...f, prefix: e.target.value.slice(0, 10) }))} required maxLength={10}
                    className="h-9 w-full rounded-lg border border-border bg-muted px-2.5 text-sm focus:border-primary/50 focus:outline-none focus:ring-2 focus:ring-ring/20"
                    placeholder={defaultPrefix} />
                </div>
                <div className="col-span-2 sm:col-span-1 grid grid-cols-2 gap-2">
                  <div>
                    <label className="mb-1 block text-xs font-medium text-foreground">Desde</label>
                    <input type="number" value={form.range_from} onChange={e => setForm(f => ({ ...f, range_from: e.target.value }))} required min={0}
                      className="h-9 w-full rounded-lg border border-border bg-muted px-2.5 text-sm focus:border-primary/50 focus:outline-none focus:ring-2 focus:ring-ring/20" />
                  </div>
                  <div>
                    <label className="mb-1 block text-xs font-medium text-foreground">Hasta</label>
                    <input type="number" value={form.range_to} onChange={e => setForm(f => ({ ...f, range_to: e.target.value }))} required min={1}
                      className="h-9 w-full rounded-lg border border-border bg-muted px-2.5 text-sm focus:border-primary/50 focus:outline-none focus:ring-2 focus:ring-ring/20" />
                  </div>
                </div>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="mb-1 block text-xs font-medium text-foreground">Vigencia desde</label>
                  <input type="date" value={form.valid_from} onChange={e => setForm(f => ({ ...f, valid_from: e.target.value }))} required
                    className="h-9 w-full rounded-lg border border-border bg-muted px-2.5 text-sm focus:border-primary/50 focus:outline-none focus:ring-2 focus:ring-ring/20" />
                </div>
                <div>
                  <label className="mb-1 block text-xs font-medium text-foreground">Vigencia hasta</label>
                  <input type="date" value={form.valid_to} onChange={e => setForm(f => ({ ...f, valid_to: e.target.value }))} required
                    className="h-9 w-full rounded-lg border border-border bg-muted px-2.5 text-sm focus:border-primary/50 focus:outline-none focus:ring-2 focus:ring-ring/20" />
                </div>
              </div>
              <div className="flex justify-end">
                <button type="submit" disabled={createMut.isPending}
                  className="rounded-lg bg-primary px-4 py-2 text-sm font-medium text-white hover:bg-primary/90 disabled:opacity-50 transition">
                  {createMut.isPending ? 'Guardando...' : 'Guardar'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}

/* ── Sandbox section ────────────────────────────────────────────────────────── */

function SandboxSection() {
  const { data: sandboxRes, isLoading } = useResolution('sandbox')
  const createMut = useCreateResolution()
  const deactivateMut = useDeactivateResolution()
  const [expanded, setExpanded] = useState(false)

  async function handleResetSandbox() {
    if (!confirm('Esto reiniciará la resolución sandbox. ¿Continuar?')) return
    try { await deactivateMut.mutateAsync('sandbox') } catch { /* ignore if not exists */ }
    await createMut.mutateAsync({
      provider: 'sandbox',
      data: {
        provider: 'sandbox',
        resolution_number: '18760000001',
        prefix: 'SANDBOX',
        range_from: 990000000,
        range_to: 995000000,
        valid_from: '2019-01-19',
        valid_to: '2030-01-19',
      },
    })
  }

  return (
    <div className="rounded-xl border border-amber-200 bg-amber-50/30 overflow-hidden">
      <button onClick={() => setExpanded(v => !v)} className="w-full flex items-center justify-between px-5 py-3.5 hover:bg-amber-50/50 transition-colors">
        <div className="flex items-center gap-2">
          <AlertTriangle className="h-4 w-4 text-amber-500" />
          <h3 className="text-sm font-semibold text-foreground">Resolución Sandbox (Pruebas)</h3>
        </div>
        <ChevronDown className={cn('h-4 w-4 text-muted-foreground transition-transform', expanded && 'rotate-180')} />
      </button>
      {expanded && (
        <div className="px-5 pb-4 pt-2 space-y-3 border-t border-amber-200">
          {isLoading ? (
            <div className="flex justify-center py-4"><div className="animate-spin rounded-full h-5 w-5 border-b-2 border-amber-500" /></div>
          ) : sandboxRes ? (
            <>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                <div><p className="text-[10px] font-medium text-muted-foreground uppercase">Prefijo</p><p className="text-sm font-bold">{sandboxRes.prefix}</p></div>
                <div><p className="text-[10px] font-medium text-muted-foreground uppercase">Rango</p><p className="text-sm font-bold">{sandboxRes.range_from.toLocaleString()} — {sandboxRes.range_to.toLocaleString()}</p></div>
                <div><p className="text-[10px] font-medium text-muted-foreground uppercase">Actual</p><p className="text-sm font-bold">{sandboxRes.current_number.toLocaleString()}</p></div>
                <div><p className="text-[10px] font-medium text-muted-foreground uppercase">Próxima</p><p className="text-sm font-bold text-amber-600 font-mono">{sandboxRes.next_invoice_number}</p></div>
              </div>
              <button onClick={handleResetSandbox} disabled={deactivateMut.isPending || createMut.isPending}
                className="inline-flex items-center gap-1.5 rounded-lg bg-amber-100 px-3 py-2 text-xs font-medium text-amber-700 hover:bg-amber-200 transition disabled:opacity-50">
                <RefreshCw className={cn('h-3.5 w-3.5', (deactivateMut.isPending || createMut.isPending) && 'animate-spin')} />
                Resetear sandbox
              </button>
            </>
          ) : (
            <div className="space-y-2">
              <p className="text-sm text-muted-foreground">No hay resolución sandbox configurada.</p>
              <button onClick={handleResetSandbox} disabled={createMut.isPending}
                className="inline-flex items-center gap-1.5 rounded-lg bg-amber-100 px-3 py-2 text-xs font-medium text-amber-700 hover:bg-amber-200 transition disabled:opacity-50">
                <RefreshCw className={cn('h-3.5 w-3.5', createMut.isPending && 'animate-spin')} />
                {createMut.isPending ? 'Creando...' : 'Crear resolución sandbox'}
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

/* ── Page ────────────────────────────────────────────────────────────────────── */

export function EInvoicingResolutionPage() {
  return (
    <div className="space-y-6">
      <nav className="mb-4">
        <ol className="flex items-center gap-2 text-sm">
          <li className="text-muted-foreground">Inicio</li>
          <li><ChevronRight className="h-4 w-4 text-muted-foreground" /></li>
          <li><Link to="/facturacion-electronica" className="text-muted-foreground hover:text-primary">Facturación Electrónica</Link></li>
          <li><ChevronRight className="h-4 w-4 text-muted-foreground" /></li>
          <li className="text-primary">Resoluciones DIAN</li>
        </ol>
      </nav>

      <div>
        <h1 className="text-2xl font-semibold text-foreground flex items-center gap-2">
          <Hash className="h-6 w-6 text-primary" />
          Resoluciones de Facturación DIAN
        </h1>
        <p className="text-sm text-muted-foreground mt-1">
          Configura las resoluciones para cada tipo de documento electrónico.
        </p>
      </div>

      {/* All 6 document types */}
      <div className="space-y-3">
        {DOC_TYPES.map(doc => (
          <ResolutionSection
            key={doc.slug}
            slug={doc.slug}
            label={doc.label}
            defaultPrefix={doc.prefix}
            icon={doc.icon}
            colorClass={doc.color}
          />
        ))}
      </div>

      {/* Sandbox */}
      <SandboxSection />

      {/* Legal note */}
      <div className="bg-amber-50 border border-amber-200 rounded-xl p-4">
        <p className="text-xs text-amber-800">
          <strong>Nota:</strong> Las resoluciones de facturación deben coincidir exactamente con las autorizadas por la DIAN
          en tu habilitación como facturador electrónico. Consulta tus resoluciones en{' '}
          <a href="https://auth-v2.matias-api.com" target="_blank" rel="noopener noreferrer" className="text-primary hover:underline">
            Matias API → Ajustes → Numeraciones
          </a>.
        </p>
      </div>
    </div>
  )
}
