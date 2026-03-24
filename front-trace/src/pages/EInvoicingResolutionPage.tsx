import { useState } from 'react'
import { Link } from 'react-router-dom'
import {
  ChevronRight, AlertTriangle, CheckCircle2, XCircle, Hash, RefreshCw, Settings2,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { useResolution, useCreateResolution, useDeactivateResolution } from '@/hooks/useIntegrations'

export function EInvoicingResolutionPage() {
  const { data: matiasRes, isLoading: loadingMatias, error: matiasError } = useResolution('matias')
  const { data: sandboxRes, isLoading: loadingSandbox } = useResolution('sandbox')
  const createMut = useCreateResolution()
  const deactivateMut = useDeactivateResolution()

  const [showSandbox, setShowSandbox] = useState(false)
  const [form, setForm] = useState({
    resolution_number: '',
    prefix: '',
    range_from: '',
    range_to: '',
    valid_from: '',
    valid_to: '',
  })

  function populateForm() {
    if (matiasRes) {
      setForm({
        resolution_number: matiasRes.resolution_number,
        prefix: matiasRes.prefix,
        range_from: String(matiasRes.range_from),
        range_to: String(matiasRes.range_to),
        valid_from: matiasRes.valid_from,
        valid_to: matiasRes.valid_to,
      })
    }
  }

  async function handleSave(e: React.FormEvent) {
    e.preventDefault()
    await createMut.mutateAsync({
      provider: 'matias',
      data: {
        provider: 'matias',
        resolution_number: form.resolution_number,
        prefix: form.prefix,
        range_from: Number(form.range_from),
        range_to: Number(form.range_to),
        valid_from: form.valid_from,
        valid_to: form.valid_to,
      },
    })
  }

  async function handleResetSandbox() {
    if (!confirm('Esto reiniciará la resolución sandbox. ¿Continuar?')) return
    await deactivateMut.mutateAsync('sandbox')
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

  const hasMatiasRes = !!matiasRes && !matiasError

  return (
    <div className="space-y-6">
      <nav className="mb-4">
        <ol className="flex items-center gap-2 text-sm">
          <li className="text-gray-500">Inicio</li>
          <li><ChevronRight className="h-4 w-4 text-gray-400" /></li>
          <li><Link to="/facturacion-electronica" className="text-gray-500 hover:text-primary">Facturación Electrónica</Link></li>
          <li><ChevronRight className="h-4 w-4 text-gray-400" /></li>
          <li className="text-primary">Resolución DIAN</li>
        </ol>
      </nav>

      <div>
        <h1 className="text-2xl font-semibold text-gray-800 flex items-center gap-2">
          <Hash className="h-6 w-6 text-primary" />
          Resolución de Facturación DIAN
        </h1>
        <p className="text-sm text-gray-500 mt-1">
          Configura el prefijo, rango de numeración y datos de resolución para tus facturas electrónicas.
        </p>
      </div>

      {/* Section A — Current MATIAS resolution status */}
      <div className="rounded-2xl border border-gray-200 bg-white p-6 shadow-sm space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-base font-semibold text-gray-800">Resolución MATIAS (Producción)</h2>
          {hasMatiasRes && (
            <div className="flex items-center gap-2">
              {matiasRes.is_expired && (
                <span className="inline-flex items-center gap-1 rounded-full bg-red-50 px-2.5 py-0.5 text-xs font-semibold text-red-600">
                  <XCircle className="h-3 w-3" /> Vencida
                </span>
              )}
              {matiasRes.is_exhausted && (
                <span className="inline-flex items-center gap-1 rounded-full bg-red-50 px-2.5 py-0.5 text-xs font-semibold text-red-600">
                  <XCircle className="h-3 w-3" /> Agotada
                </span>
              )}
              {!matiasRes.is_expired && !matiasRes.is_exhausted && (
                <span className="inline-flex items-center gap-1 rounded-full bg-emerald-50 px-2.5 py-0.5 text-xs font-semibold text-emerald-600">
                  <CheckCircle2 className="h-3 w-3" /> Vigente
                </span>
              )}
            </div>
          )}
        </div>

        {loadingMatias ? (
          <div className="flex justify-center py-6"><div className="animate-spin rounded-full h-5 w-5 border-b-2 border-primary" /></div>
        ) : hasMatiasRes ? (
          <div className="space-y-4">
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
              <div>
                <p className="text-xs font-medium text-gray-400 uppercase">Nº Resolución</p>
                <p className="text-sm font-bold text-gray-800 mt-0.5">{matiasRes.resolution_number}</p>
              </div>
              <div>
                <p className="text-xs font-medium text-gray-400 uppercase">Prefijo</p>
                <p className="text-sm font-bold text-gray-800 mt-0.5">{matiasRes.prefix}</p>
              </div>
              <div>
                <p className="text-xs font-medium text-gray-400 uppercase">Rango</p>
                <p className="text-sm font-bold text-gray-800 mt-0.5">{matiasRes.range_from.toLocaleString()} — {matiasRes.range_to.toLocaleString()}</p>
              </div>
              <div>
                <p className="text-xs font-medium text-gray-400 uppercase">Vigente hasta</p>
                <p className={cn('text-sm font-bold mt-0.5', matiasRes.is_expired ? 'text-red-600' : 'text-gray-800')}>
                  {new Date(matiasRes.valid_to).toLocaleDateString('es-CO')}
                </p>
              </div>
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
              <div className="rounded-xl border border-gray-100 bg-gray-50 p-4">
                <p className="text-xs font-medium text-gray-400 uppercase">Facturas emitidas</p>
                <p className="text-xl font-bold text-gray-800 mt-1">{matiasRes.current_number.toLocaleString()}</p>
              </div>
              <div className="rounded-xl border border-gray-100 bg-gray-50 p-4">
                <p className="text-xs font-medium text-gray-400 uppercase">Restantes</p>
                <p className={cn('text-xl font-bold mt-1', matiasRes.remaining < 100 ? 'text-red-600' : 'text-gray-800')}>
                  {matiasRes.remaining.toLocaleString()}
                </p>
              </div>
              <div className="rounded-xl border border-gray-100 bg-gray-50 p-4">
                <p className="text-xs font-medium text-gray-400 uppercase">Próxima factura</p>
                <p className="text-xl font-bold text-primary mt-1 font-mono">{matiasRes.next_invoice_number}</p>
              </div>
            </div>

            {matiasRes.remaining < 100 && !matiasRes.is_exhausted && (
              <div className="flex items-center gap-2 rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
                <AlertTriangle className="h-4 w-4 text-amber-500 shrink-0" />
                Quedan pocas facturas disponibles. Configura una nueva resolución pronto.
              </div>
            )}
            {matiasRes.is_expired && (
              <div className="flex items-center gap-2 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
                <XCircle className="h-4 w-4 text-red-500 shrink-0" />
                La resolución está vencida. No se pueden emitir facturas hasta que configures una nueva.
              </div>
            )}
          </div>
        ) : (
          <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-4 text-sm text-amber-800 flex items-start gap-3">
            <AlertTriangle className="h-5 w-5 text-amber-500 shrink-0 mt-0.5" />
            <div>
              <p className="font-semibold">No hay resolución MATIAS configurada</p>
              <p className="mt-1 text-amber-700">Las facturas electrónicas reales no se podrán emitir hasta que configures una resolución DIAN válida.</p>
            </div>
          </div>
        )}
      </div>

      {/* Section B — Configure / update resolution form */}
      <div className="rounded-2xl border border-gray-200 bg-white p-6 shadow-sm space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-base font-semibold text-gray-800 flex items-center gap-2">
            <Settings2 className="h-4 w-4 text-gray-400" />
            {hasMatiasRes ? 'Actualizar resolución' : 'Configurar resolución DIAN'}
          </h2>
          {hasMatiasRes && (
            <button
              type="button"
              onClick={populateForm}
              className="text-xs text-primary hover:text-primary font-medium"
            >
              Cargar datos actuales
            </button>
          )}
        </div>

        <form onSubmit={handleSave} className="space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="mb-1.5 block text-sm font-medium text-gray-700">Número de resolución</label>
              <input
                value={form.resolution_number}
                onChange={e => setForm(f => ({ ...f, resolution_number: e.target.value }))}
                required
                className="h-10 w-full rounded-lg border border-gray-300 px-3 text-sm focus:border-primary/50 focus:ring-3 focus:ring-ring/20 focus:outline-none"
                placeholder="18764000001"
              />
            </div>
            <div>
              <label className="mb-1.5 block text-sm font-medium text-gray-700">Prefijo</label>
              <input
                value={form.prefix}
                onChange={e => setForm(f => ({ ...f, prefix: e.target.value.slice(0, 10) }))}
                required
                maxLength={10}
                className="h-10 w-full rounded-lg border border-gray-300 px-3 text-sm focus:border-primary/50 focus:ring-3 focus:ring-ring/20 focus:outline-none"
                placeholder="FE"
              />
            </div>
            <div>
              <label className="mb-1.5 block text-sm font-medium text-gray-700">Rango desde</label>
              <input
                type="number"
                value={form.range_from}
                onChange={e => setForm(f => ({ ...f, range_from: e.target.value }))}
                required
                min={0}
                className="h-10 w-full rounded-lg border border-gray-300 px-3 text-sm focus:border-primary/50 focus:ring-3 focus:ring-ring/20 focus:outline-none"
                placeholder="1"
              />
            </div>
            <div>
              <label className="mb-1.5 block text-sm font-medium text-gray-700">Rango hasta</label>
              <input
                type="number"
                value={form.range_to}
                onChange={e => setForm(f => ({ ...f, range_to: e.target.value }))}
                required
                min={1}
                className="h-10 w-full rounded-lg border border-gray-300 px-3 text-sm focus:border-primary/50 focus:ring-3 focus:ring-ring/20 focus:outline-none"
                placeholder="5000000"
              />
            </div>
            <div>
              <label className="mb-1.5 block text-sm font-medium text-gray-700">Fecha inicio vigencia</label>
              <input
                type="date"
                value={form.valid_from}
                onChange={e => setForm(f => ({ ...f, valid_from: e.target.value }))}
                required
                className="h-10 w-full rounded-lg border border-gray-300 px-3 text-sm focus:border-primary/50 focus:ring-3 focus:ring-ring/20 focus:outline-none"
              />
            </div>
            <div>
              <label className="mb-1.5 block text-sm font-medium text-gray-700">Fecha fin vigencia</label>
              <input
                type="date"
                value={form.valid_to}
                onChange={e => setForm(f => ({ ...f, valid_to: e.target.value }))}
                required
                className="h-10 w-full rounded-lg border border-gray-300 px-3 text-sm focus:border-primary/50 focus:ring-3 focus:ring-ring/20 focus:outline-none"
              />
            </div>
          </div>

          <div className="flex justify-end">
            <button
              type="submit"
              disabled={createMut.isPending}
              className="rounded-lg bg-primary px-5 py-2.5 text-sm font-medium text-white shadow-sm transition hover:bg-primary disabled:opacity-50"
            >
              {createMut.isPending ? 'Guardando...' : 'Guardar resolución'}
            </button>
          </div>
        </form>
      </div>

      {/* Section C — Sandbox resolution (collapsed) */}
      <div className="rounded-2xl border border-gray-200 bg-white shadow-sm overflow-hidden">
        <button
          onClick={() => setShowSandbox(!showSandbox)}
          className="w-full flex items-center justify-between px-6 py-4 text-left hover:bg-gray-50 transition"
        >
          <h2 className="text-base font-semibold text-gray-800">Resolución Sandbox</h2>
          <ChevronRight className={cn('h-4 w-4 text-gray-400 transition-transform', showSandbox && 'rotate-90')} />
        </button>

        {showSandbox && (
          <div className="px-6 pb-6 space-y-4 border-t border-gray-100 pt-4">
            {loadingSandbox ? (
              <div className="flex justify-center py-4"><div className="animate-spin rounded-full h-5 w-5 border-b-2 border-amber-500" /></div>
            ) : sandboxRes ? (
              <>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
                  <div>
                    <p className="text-xs font-medium text-gray-400 uppercase">Prefijo</p>
                    <p className="text-sm font-bold text-gray-800 mt-0.5">{sandboxRes.prefix}</p>
                  </div>
                  <div>
                    <p className="text-xs font-medium text-gray-400 uppercase">Rango</p>
                    <p className="text-sm font-bold text-gray-800 mt-0.5">{sandboxRes.range_from.toLocaleString()} — {sandboxRes.range_to.toLocaleString()}</p>
                  </div>
                  <div>
                    <p className="text-xs font-medium text-gray-400 uppercase">Consecutivo actual</p>
                    <p className="text-sm font-bold text-gray-800 mt-0.5">{sandboxRes.current_number.toLocaleString()}</p>
                  </div>
                  <div>
                    <p className="text-xs font-medium text-gray-400 uppercase">Próxima factura</p>
                    <p className="text-sm font-bold text-amber-600 mt-0.5 font-mono">{sandboxRes.next_invoice_number}</p>
                  </div>
                </div>
                <button
                  onClick={handleResetSandbox}
                  disabled={deactivateMut.isPending || createMut.isPending}
                  className="inline-flex items-center gap-1.5 rounded-lg bg-amber-50 px-4 py-2 text-sm font-medium text-amber-700 hover:bg-amber-100 transition disabled:opacity-50"
                >
                  <RefreshCw className={cn('h-4 w-4', (deactivateMut.isPending || createMut.isPending) && 'animate-spin')} />
                  Resetear sandbox
                </button>
              </>
            ) : (
              <p className="text-sm text-gray-400">No hay resolución sandbox configurada. Se creará automáticamente al simular la primera factura.</p>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
