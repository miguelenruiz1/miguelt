import { useState } from 'react'
import { Link } from 'react-router-dom'
import {
  FileText, Zap, CheckCircle2, XCircle, AlertTriangle, ExternalLink, ChevronRight,
  RefreshCw, Hash,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import {
  useIntegrationCatalog, useIntegrationConfigs, useCreateIntegration,
  useUpdateIntegration, useDeleteIntegration, useTestConnection, useResolution,
} from '@/hooks/useIntegrations'
import { useSalesOrders } from '@/hooks/useInventory'

const INVOICE_STATUS_COLORS: Record<string, string> = {
  issued: 'bg-emerald-50 text-emerald-700',
  simulated: 'bg-amber-50 text-amber-700',
  failed: 'bg-red-50 text-red-600',
  pending: 'bg-secondary text-muted-foreground',
}

export function EInvoicingPage() {
  const { data: configs = [] } = useIntegrationConfigs()
  const createMut = useCreateIntegration()
  const updateMut = useUpdateIntegration()
  const deleteMut = useDeleteIntegration()
  const testMut = useTestConnection()
  const { data: ordersData } = useSalesOrders({ status: 'delivered', limit: 100 })

  const [showSetup, setShowSetup] = useState(false)
  const [showUpdateKey, setShowUpdateKey] = useState(false)
  const [testResult, setTestResult] = useState<{ ok: boolean; message: string } | null>(null)
  const [apiKey, setApiKey] = useState('')
  const [simMode, setSimMode] = useState(true)

  const { data: matiasRes, error: resError } = useResolution('matias')
  const hasMatiasRes = !!matiasRes && !resError

  const matiasConfig = configs.find(c => c.provider_slug === 'matias')
  const isConnected = !!matiasConfig

  // Filter orders that have invoice data
  const allOrders = ordersData?.items ?? []
  const invoicedOrders = allOrders.filter(o => o.invoice_status)

  // Stats
  const totalIssued = invoicedOrders.filter(o => o.invoice_status === 'issued').length
  const totalSimulated = invoicedOrders.filter(o => o.invoice_status === 'simulated').length
  const totalFailed = invoicedOrders.filter(o => o.invoice_status === 'failed').length

  async function handleSetup(e: React.FormEvent) {
    e.preventDefault()
    await createMut.mutateAsync({
      provider_slug: 'matias',
      credentials: { api_key: apiKey, simulation_mode: simMode },
      is_active: true,
      simulation_mode: simMode,
    })
    setShowSetup(false)
    setApiKey('')
  }

  async function handleTest() {
    setTestResult(null)
    const res = await testMut.mutateAsync({ providerSlug: 'matias' })
    setTestResult(res)
  }

  return (
    <div className="space-y-6">
      {/* Breadcrumb */}
      <nav className="mb-4">
        <ol className="flex items-center gap-2 text-sm">
          <li className="text-muted-foreground">Inicio</li>
          <li><ChevronRight className="h-4 w-4 text-muted-foreground" /></li>
          <li className="text-primary">Facturación Electrónica</li>
        </ol>
      </nav>

      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold text-foreground">
            Facturación Electrónica DIAN
          </h1>
          <p className="text-sm text-muted-foreground mt-1">
            Emite facturas electrónicas válidas desde tus Sales Orders — Powered by MATIAS API
          </p>
        </div>
      </div>

      {/* Resolution banner + link */}
      {!hasMatiasRes && isConnected && (
        <div className="flex items-center gap-3 rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
          <AlertTriangle className="h-5 w-5 text-amber-500 shrink-0" />
          <span>No has configurado tu resolución DIAN. Las facturas reales no se podrán emitir hasta que la configures.</span>
          <Link to="/facturacion-electronica/resolucion" className="ml-auto shrink-0 inline-flex items-center gap-1.5 rounded-lg bg-amber-100 px-3 py-1.5 text-xs font-medium text-amber-800 hover:bg-amber-200 transition">
            <Hash className="h-3.5 w-3.5" /> Configurar
          </Link>
        </div>
      )}
      {hasMatiasRes && (
        <div className="flex items-center justify-between rounded-lg border border-border bg-card px-4 py-3 ">
          <div className="flex items-center gap-3 text-sm">
            <Hash className="h-4 w-4 text-primary" />
            <span className="text-muted-foreground">Resolución: <span className="font-semibold text-foreground">{matiasRes.prefix}{matiasRes.current_number + 1}</span> (próxima)</span>
            <span className="text-muted-foreground">|</span>
            <span className="text-muted-foreground">{matiasRes.remaining.toLocaleString()} restantes</span>
          </div>
          <Link to="/facturacion-electronica/resolucion" className="text-xs font-medium text-primary hover:text-primary">
            Configurar resolución DIAN
          </Link>
        </div>
      )}

      {/* Test result alert */}
      {testResult && (
        <div className={cn('rounded-lg px-4 py-3 text-sm flex items-center gap-2 border', testResult.ok ? 'bg-emerald-50 text-emerald-700 border-emerald-200' : 'bg-red-50 text-red-600 border-red-200')}>
          {testResult.ok ? <CheckCircle2 className="h-4 w-4" /> : <XCircle className="h-4 w-4" />}
          {testResult.message}
          <button onClick={() => setTestResult(null)} className="ml-auto text-muted-foreground hover:text-muted-foreground">
            <XCircle className="h-4 w-4" />
          </button>
        </div>
      )}

      {/* Section A: Config */}
      <div className="rounded-2xl border border-border bg-card p-6  space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-cyan-50">
              <FileText className="h-6 w-6 text-cyan-600" />
            </div>
            <div>
              <h2 className="text-base font-semibold text-foreground">Configuración MATIAS API</h2>
              <div className="flex items-center gap-2 mt-0.5">
                {isConnected ? (
                  <>
                    <span className="inline-flex items-center gap-1 rounded-full bg-emerald-50 px-2 py-0.5 text-[10px] font-semibold text-emerald-600">
                      <CheckCircle2 className="h-3 w-3" /> Conectado
                    </span>
                    {matiasConfig?.simulation_mode && (
                      <span className="inline-flex items-center gap-1 rounded-full bg-amber-50 px-2 py-0.5 text-[10px] font-semibold text-amber-600">
                        <AlertTriangle className="h-3 w-3" /> Simulación activa
                      </span>
                    )}
                  </>
                ) : (
                  <span className="inline-flex rounded-full bg-secondary px-2 py-0.5 text-[10px] font-semibold text-muted-foreground">
                    No configurado
                  </span>
                )}
              </div>
            </div>
          </div>
          <div className="flex items-center gap-2">
            {isConnected && (
              <>
                <button
                  onClick={handleTest}
                  disabled={testMut.isPending}
                  className="inline-flex items-center gap-1.5 rounded-lg bg-secondary px-3 py-2 text-xs font-medium text-foreground transition hover:bg-gray-200"
                >
                  <Zap className="h-3.5 w-3.5" /> {testMut.isPending ? 'Probando...' : 'Probar conexión'}
                </button>
                <button
                  onClick={() => setShowUpdateKey(true)}
                  className="inline-flex items-center gap-1.5 rounded-lg bg-secondary px-3 py-2 text-xs font-medium text-foreground transition hover:bg-gray-200"
                >
                  <RefreshCw className="h-3.5 w-3.5" /> Actualizar API Key
                </button>
                <button
                  onClick={async () => { if (window.confirm('¿Desconectar MATIAS API?')) { try { await deleteMut.mutateAsync(matiasConfig!.id) } catch { alert('Error al desconectar. Intenta de nuevo.') } } }}
                  className="inline-flex items-center gap-1.5 rounded-lg bg-red-50 px-3 py-2 text-xs font-medium text-red-600 transition hover:bg-red-100"
                >
                  <XCircle className="h-3.5 w-3.5" /> Desconectar
                </button>
              </>
            )}
            <button
              onClick={() => setShowSetup(true)}
              className={cn(
                "rounded-lg px-4 py-2 text-sm font-medium transition",
                isConnected
                  ? "bg-secondary text-foreground hover:bg-gray-200"
                  : "bg-primary text-white hover:bg-primary/90"
              )}
            >
              {isConnected ? 'Reconfigurar' : 'Configurar'}
            </button>
          </div>
        </div>
      </div>

      {/* Simulation toggle (when connected) */}
      {isConnected && matiasConfig && (
        <div className="rounded-2xl border border-border bg-card p-6 space-y-1">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-sm font-semibold text-foreground">Modo Simulación (Sandbox)</h3>
              <p className="text-xs text-muted-foreground mt-0.5">
                {matiasConfig.simulation_mode
                  ? 'Las facturas se generan como prueba, sin enviar a la DIAN.'
                  : 'Las facturas se envían a la DIAN en modo producción.'}
              </p>
            </div>
            <button
              type="button"
              role="switch"
              aria-checked={matiasConfig.simulation_mode}
              disabled={updateMut.isPending}
              onClick={() => updateMut.mutate({ id: matiasConfig.id, data: { simulation_mode: !matiasConfig.simulation_mode } })}
              className={cn(
                'relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full transition duration-150 ease-linear disabled:opacity-50',
                matiasConfig.simulation_mode ? 'bg-amber-500' : 'bg-emerald-500',
              )}
            >
              <span className={cn(
                'absolute left-0.5 top-0.5 h-5 w-5 rounded-full bg-white shadow transform transition duration-150 ease-linear',
                matiasConfig.simulation_mode ? 'translate-x-5' : 'translate-x-0',
              )} />
            </button>
          </div>
        </div>
      )}

      {/* Section C: Stats */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="rounded-2xl border border-border bg-card p-5 ">
          <p className="text-xs font-medium text-muted-foreground uppercase">Emitidas</p>
          <p className="text-2xl font-bold text-emerald-600 mt-1">{totalIssued}</p>
        </div>
        <div className="rounded-2xl border border-border bg-card p-5 ">
          <p className="text-xs font-medium text-muted-foreground uppercase">Simuladas</p>
          <p className="text-2xl font-bold text-amber-600 mt-1">{totalSimulated}</p>
        </div>
        <div className="rounded-2xl border border-border bg-card p-5 ">
          <p className="text-xs font-medium text-muted-foreground uppercase">Fallidas</p>
          <p className="text-2xl font-bold text-red-600 mt-1">{totalFailed}</p>
        </div>
      </div>

      {/* Section B: Invoice history */}
      <div className="space-y-4">
        <h2 className="text-lg font-semibold text-foreground">Historial de Facturas Electrónicas</h2>
        {invoicedOrders.length === 0 ? (
          <div className="rounded-2xl border border-border bg-card p-8 text-center text-sm text-muted-foreground">
            No hay facturas electrónicas aún. Las facturas se generan automáticamente al confirmar una Sales Order.
          </div>
        ) : (
          <div className="rounded-2xl border border-border bg-card  overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-border">
                    <th className="px-5 py-3.5 text-left text-xs font-medium text-muted-foreground uppercase">Orden</th>
                    <th className="px-5 py-3.5 text-left text-xs font-medium text-muted-foreground uppercase">Cliente</th>
                    <th className="px-5 py-3.5 text-right text-xs font-medium text-muted-foreground uppercase">Total</th>
                    <th className="px-5 py-3.5 text-left text-xs font-medium text-muted-foreground uppercase">CUFE</th>
                    <th className="px-5 py-3.5 text-left text-xs font-medium text-muted-foreground uppercase">Estado</th>
                    <th className="px-5 py-3.5 text-left text-xs font-medium text-muted-foreground uppercase">PDF</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {invoicedOrders.map(order => (
                    <tr key={order.id} className="hover:bg-muted/60">
                      <td className="px-5 py-3">
                        <Link to={`/inventario/ventas/${order.id}`} className="font-medium text-primary hover:text-primary">
                          {order.order_number}
                        </Link>
                      </td>
                      <td className="px-5 py-3 text-foreground">{order.customer_name ?? '—'}</td>
                      <td className="px-5 py-3 text-right font-mono text-foreground">${order.total.toLocaleString()} {order.currency}</td>
                      <td className="px-5 py-3">
                        {order.cufe ? (
                          <span className="font-mono text-xs text-muted-foreground" title={order.cufe}>
                            {order.cufe.slice(0, 20)}...
                          </span>
                        ) : '—'}
                      </td>
                      <td className="px-5 py-3">
                        <span className={cn('inline-flex rounded-full px-2 py-0.5 text-xs font-medium', INVOICE_STATUS_COLORS[order.invoice_status ?? ''] ?? 'bg-secondary')}>
                          {order.invoice_status}
                        </span>
                      </td>
                      <td className="px-5 py-3">
                        {order.invoice_pdf_url ? (
                          <a href={order.invoice_pdf_url} target="_blank" rel="noopener noreferrer"
                            className="inline-flex items-center gap-1 text-xs text-primary hover:text-primary font-medium">
                            <ExternalLink className="h-3.5 w-3.5" /> Ver PDF
                          </a>
                        ) : '—'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>

      {/* Setup modal */}
      {showSetup && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4" role="dialog" aria-modal="true">
          <div className="absolute inset-0 bg-gray-900/50" onClick={() => setShowSetup(false)} />
          <form
            onSubmit={handleSetup}
            onClick={e => e.stopPropagation()}
            className="relative w-full max-w-md rounded-2xl border border-border bg-card p-6 shadow-xl space-y-5"
          >
            <div>
              <h3 className="text-lg font-semibold text-foreground">Configurar MATIAS API</h3>
              <p className="text-sm text-muted-foreground mt-1">Ingresa tu API Key para conectar con el servicio de facturación electrónica.</p>
            </div>

            <div className="space-y-4">
              <div>
                <label className="mb-1.5 block text-sm font-medium text-foreground">API Key <span className="text-red-500">*</span></label>
                <input
                  value={apiKey}
                  onChange={e => setApiKey(e.target.value)}
                  type="password"
                  required
                  className="h-11 w-full rounded-lg border border-gray-300 bg-transparent px-4 py-2.5 text-sm text-foreground  placeholder:text-muted-foreground focus:border-primary/50 focus:outline-none focus:ring-3 focus:ring-ring/20"
                  placeholder="Ingresa tu API Key de MATIAS"
                />
              </div>
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-foreground">Modo Simulación</p>
                  <p className="text-xs text-muted-foreground">Genera facturas de prueba sin enviar a la DIAN</p>
                </div>
                <button
                  type="button"
                  role="switch"
                  aria-checked={simMode}
                  onClick={() => setSimMode(!simMode)}
                  className={cn(
                    'relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full transition duration-150 ease-linear',
                    simMode ? 'bg-amber-500' : 'bg-gray-200',
                  )}
                >
                  <span className={cn(
                    'absolute left-0.5 top-0.5 h-5 w-5 rounded-full bg-card  transform transition duration-150 ease-linear',
                    simMode ? 'translate-x-full' : 'translate-x-0',
                  )} />
                </button>
              </div>
            </div>

            <div className="flex justify-end gap-3 pt-1">
              <button type="button" onClick={() => setShowSetup(false)} className="rounded-lg border border-gray-300 px-4 py-2.5 text-sm font-medium text-foreground transition hover:bg-muted">
                Cancelar
              </button>
              <button type="submit" disabled={createMut.isPending} className="rounded-lg bg-primary px-5 py-2.5 text-sm font-medium text-white  transition hover:bg-primary disabled:opacity-50">
                {createMut.isPending ? 'Conectando...' : 'Conectar'}
              </button>
            </div>
          </form>
        </div>
      )}
      {/* Update API Key modal */}
      {showUpdateKey && matiasConfig && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4" role="dialog" aria-modal="true">
          <div className="absolute inset-0 bg-gray-900/50" onClick={() => setShowUpdateKey(false)} />
          <form
            onSubmit={async (e) => {
              e.preventDefault()
              await updateMut.mutateAsync({
                id: matiasConfig.id,
                data: { credentials: { api_key: apiKey } },
              })
              setShowUpdateKey(false)
              setApiKey('')
              setTestResult(null)
            }}
            onClick={e => e.stopPropagation()}
            className="relative w-full max-w-md rounded-2xl border border-border bg-card p-6 shadow-xl space-y-5"
          >
            <div>
              <h3 className="text-lg font-semibold text-foreground">Actualizar API Key</h3>
              <p className="text-sm text-muted-foreground mt-1">Ingresa tu nueva API Key de MATIAS.</p>
            </div>
            <div>
              <label className="mb-1.5 block text-sm font-medium text-foreground">Nueva API Key <span className="text-red-500">*</span></label>
              <input
                value={apiKey}
                onChange={e => setApiKey(e.target.value)}
                type="password"
                required
                className="h-11 w-full rounded-lg border border-gray-300 bg-transparent px-4 py-2.5 text-sm text-foreground placeholder:text-muted-foreground focus:border-primary/50 focus:outline-none focus:ring-3 focus:ring-ring/20"
                placeholder="Pega tu token de Matias aquí"
              />
            </div>
            <div className="flex justify-end gap-3 pt-1">
              <button type="button" onClick={() => { setShowUpdateKey(false); setApiKey('') }} className="rounded-lg border border-gray-300 px-4 py-2.5 text-sm font-medium text-foreground transition hover:bg-muted">
                Cancelar
              </button>
              <button type="submit" disabled={!apiKey.trim() || updateMut.isPending} className="rounded-lg bg-primary px-5 py-2.5 text-sm font-medium text-white transition hover:bg-primary/90 disabled:opacity-50">
                {updateMut.isPending ? 'Guardando...' : 'Guardar'}
              </button>
            </div>
          </form>
        </div>
      )}
    </div>
  )
}
