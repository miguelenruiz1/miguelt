import { useState, useEffect } from 'react'
import {
  Banknote, CheckCircle2, Eye, EyeOff, Save, XCircle, ShieldCheck, TestTube, ChevronRight, ExternalLink,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import {
  useGatewayConfigs,
  useSaveGatewayConfig,
  useSetActiveGateway,
} from '@/hooks/usePayments'

const TENANT_ID = import.meta.env.VITE_TENANT_ID ?? 'default'

const FIELDS = [
  { key: 'public_key', label: 'Llave Pública', placeholder: 'pub_test_... o pub_prod_...', type: 'text' as const, required: true },
  { key: 'private_key', label: 'Llave Privada', placeholder: 'prv_test_... o prv_prod_...', type: 'password' as const, required: true },
  { key: 'integrity_key', label: 'Llave de Integridad', placeholder: 'test_integrity_... o prod_integrity_...', type: 'password' as const, required: true },
  { key: 'events_secret', label: 'Secreto de Eventos', placeholder: 'Opcional — para verificar webhooks', type: 'password' as const, required: false },
]

export function PaymentsPage() {
  const { data: configs = [], isLoading } = useGatewayConfigs(TENANT_ID)
  const saveMut = useSaveGatewayConfig(TENANT_ID)
  const activateMut = useSetActiveGateway(TENANT_ID)

  const wompi = configs.find((c) => c.slug === 'wompi')
  const isConfigured = wompi?.configured ?? false
  const isActive = wompi?.is_active ?? false

  const [credentials, setCredentials] = useState<Record<string, string>>(() =>
    Object.fromEntries(FIELDS.map(f => [f.key, ''])),
  )
  const [isTestMode, setIsTestMode] = useState(true)
  const [showFields, setShowFields] = useState<Record<string, boolean>>({})
  const [error, setError] = useState<string | null>(null)
  const [saved, setSaved] = useState(false)

  useEffect(() => {
    if (saved) {
      const t = setTimeout(() => setSaved(false), 3000)
      return () => clearTimeout(t)
    }
  }, [saved])

  async function handleSave() {
    setError(null)
    setSaved(false)

    if (!isConfigured) {
      for (const f of FIELDS) {
        if (f.required && !credentials[f.key]?.trim()) {
          setError(`El campo "${f.label}" es obligatorio`)
          return
        }
      }
    }

    const creds: Record<string, string> = {}
    for (const [k, v] of Object.entries(credentials)) {
      if (v.trim()) creds[k] = v.trim()
    }

    try {
      await saveMut.mutateAsync({ slug: 'wompi', body: { credentials: creds, is_test_mode: isTestMode } })
      await activateMut.mutateAsync('wompi')
      setSaved(true)
      setCredentials(Object.fromEntries(FIELDS.map(f => [f.key, ''])))
    } catch (e: any) {
      setError(e?.message ?? 'Error al guardar')
    }
  }

  const inputCls = 'h-11 w-full rounded-lg border border-gray-300 bg-transparent px-4 py-2.5 text-sm text-foreground  placeholder:text-muted-foreground focus:border-[#5C2D91]/50 focus:outline-none focus:ring-3 focus:ring-[#5C2D91]/20'

  return (
    <div className="mx-auto max-w-xl space-y-6">
      {/* Breadcrumb */}
      <nav className="mb-4">
        <ol className="flex items-center gap-2 text-sm">
          <li className="text-muted-foreground">Plataforma</li>
          <li><ChevronRight className="h-4 w-4 text-muted-foreground" /></li>
          <li className="text-[#5C2D91]">Pasarela de Cobro</li>
        </ol>
      </nav>

      {/* Header */}
      <div className="flex items-center gap-4">
        <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-[#5C2D91] text-white text-xl font-bold shadow">
          W
        </div>
        <div>
          <h1 className="text-xl font-semibold text-foreground">Wompi</h1>
          <p className="text-sm text-muted-foreground">Configura las llaves de Wompi para cobrar suscripciones</p>
        </div>
      </div>

      {/* Status */}
      {isConfigured && isActive && (
        <div className="flex items-center gap-2 rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-700">
          <CheckCircle2 className="h-4 w-4 shrink-0" />
          Wompi está configurado y activo. Los cobros están habilitados.
        </div>
      )}

      {error && (
        <div className="flex items-center gap-2 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          <XCircle className="h-4 w-4 shrink-0" />
          {error}
          <button onClick={() => setError(null)} className="ml-auto text-muted-foreground hover:text-muted-foreground">
            <XCircle className="h-4 w-4" />
          </button>
        </div>
      )}

      {saved && (
        <div className="flex items-center gap-2 rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-700">
          <CheckCircle2 className="h-4 w-4 shrink-0" />
          Configuración guardada correctamente
        </div>
      )}

      {/* Config */}
      {isLoading ? (
        <div className="h-64 rounded-2xl border border-border bg-muted animate-pulse" />
      ) : (
        <div className="rounded-2xl border border-border bg-card p-6  space-y-5">
          {/* Mode toggle */}
          <div className="flex items-center justify-between rounded-xl bg-muted px-4 py-3">
            <div>
              <p className="text-sm font-medium text-foreground">Modo</p>
              <p className="text-xs text-muted-foreground">
                {isTestMode ? 'Sandbox — no se cobran transacciones reales' : 'Producción — cobros reales activos'}
              </p>
            </div>
            <button
              onClick={() => setIsTestMode(v => !v)}
              className={cn(
                'relative h-6 w-11 rounded-full transition-colors',
                isTestMode ? 'bg-amber-400' : 'bg-emerald-500',
              )}
            >
              <span className={cn(
                'absolute top-0.5 left-0.5 h-5 w-5 rounded-full bg-card shadow transition-transform',
                isTestMode ? 'translate-x-0' : 'translate-x-5',
              )} />
            </button>
          </div>
          <p className="text-xs text-center font-semibold" style={{ color: isTestMode ? '#d97706' : '#10b981' }}>
            {isTestMode ? (
              <span className="inline-flex items-center gap-1"><TestTube className="h-3.5 w-3.5" /> Modo Sandbox</span>
            ) : (
              <span className="inline-flex items-center gap-1"><ShieldCheck className="h-3.5 w-3.5" /> Modo Producción</span>
            )}
          </p>

          {/* Fields */}
          <div className="space-y-4">
            {FIELDS.map(field => {
              const isPassword = field.type === 'password'
              const visible = showFields[field.key]
              return (
                <div key={field.key}>
                  <label className="mb-1.5 block text-sm font-medium text-foreground">
                    {field.label}
                    {field.required && <span className="text-red-500 ml-0.5">*</span>}
                  </label>
                  <div className="relative">
                    <input
                      type={isPassword && !visible ? 'password' : 'text'}
                      value={credentials[field.key] ?? ''}
                      onChange={e => setCredentials(prev => ({ ...prev, [field.key]: e.target.value }))}
                      placeholder={isConfigured ? '(dejar vacío para mantener)' : field.placeholder}
                      className={cn(inputCls, 'font-mono', isPassword && 'pr-10')}
                    />
                    {isPassword && (
                      <button
                        type="button"
                        onClick={() => setShowFields(prev => ({ ...prev, [field.key]: !prev[field.key] }))}
                        className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-muted-foreground"
                      >
                        {visible ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                      </button>
                    )}
                  </div>
                </div>
              )
            })}
          </div>

          <p className="text-xs text-muted-foreground text-center">
            Obtén tus llaves en{' '}
            <a href="https://comercios.wompi.co/developers" target="_blank" rel="noopener noreferrer" className="text-[#5C2D91] font-medium hover:underline">
              comercios.wompi.co/developers <ExternalLink className="h-3 w-3 inline" />
            </a>
          </p>

          {/* Save */}
          <button
            onClick={handleSave}
            disabled={saveMut.isPending || activateMut.isPending}
            className="flex w-full items-center justify-center gap-2 rounded-lg bg-[#5C2D91] px-4 py-2.5 text-sm font-medium text-white hover:bg-[#5C2D91]/90 transition disabled:opacity-50 "
          >
            <Save className="h-4 w-4" />
            {saveMut.isPending || activateMut.isPending ? 'Guardando...' : 'Guardar configuración'}
          </button>
        </div>
      )}

      {/* Configured keys preview */}
      {isConfigured && wompi?.credentials_masked && Object.keys(wompi.credentials_masked).length > 0 && (
        <div className="rounded-2xl border border-border bg-card p-6  space-y-3">
          <h3 className="text-sm font-semibold text-foreground">Llaves configuradas</h3>
          <div className="rounded-xl bg-muted border border-border divide-y divide-gray-200">
            {Object.entries(wompi.credentials_masked).map(([key, value]) => (
              <div key={key} className="flex items-center justify-between px-4 py-2.5">
                <span className="text-xs font-medium text-muted-foreground">{key}</span>
                <span className="text-xs font-mono text-muted-foreground">{value as string}</span>
              </div>
            ))}
          </div>
          {wompi.updated_at && (
            <p className="text-[10px] text-muted-foreground">
              Última actualización: {new Date(wompi.updated_at).toLocaleString()}
            </p>
          )}
        </div>
      )}

      {/* Footer */}
      <div className="flex items-center justify-between text-xs text-muted-foreground">
        <span className="flex items-center gap-1.5">
          <ShieldCheck className="h-3.5 w-3.5" />
          Las credenciales se almacenan cifradas
        </span>
        <a
          href="https://docs.wompi.co"
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center gap-1 text-[#5C2D91] font-medium hover:underline"
        >
          Documentación <ExternalLink className="h-3 w-3" />
        </a>
      </div>
    </div>
  )
}
