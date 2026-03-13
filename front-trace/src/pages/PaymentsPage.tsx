import { useState } from 'react'
import {
  Banknote, CheckCircle2, Settings, Trash2, Zap, Eye, EyeOff, X,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { useConfirm } from '@/store/confirm'
import {
  useGatewayConfigs,
  useSaveGatewayConfig,
  useSetActiveGateway,
  useDeleteGatewayConfig,
} from '@/hooks/usePayments'
import type { GatewayConfigOut, GatewayField } from '@/types/payments'

const TENANT_ID = import.meta.env.VITE_TENANT_ID ?? 'default'

// ─── Configure Gateway Modal ──────────────────────────────────────────────────

function ConfigureGatewayModal({
  gateway,
  onClose,
}: {
  gateway: GatewayConfigOut
  onClose: () => void
}) {
  const fields: GatewayField[] = gateway.fields ?? []
  const [isTestMode, setIsTestMode] = useState(gateway.is_test_mode ?? true)
  const [credentials, setCredentials] = useState<Record<string, string>>(
    () => Object.fromEntries(fields.map((f) => [f.key, ''])),
  )
  const [showFields, setShowFields] = useState<Record<string, boolean>>({})
  const [error, setError] = useState<string | null>(null)

  const saveMut = useSaveGatewayConfig(TENANT_ID)
  const deleteMut = useDeleteGatewayConfig(TENANT_ID)

  async function handleSave() {
    setError(null)
    // Validate required fields
    for (const f of fields) {
      if (f.required && !credentials[f.key]?.trim()) {
        setError(`El campo "${f.label}" es obligatorio`)
        return
      }
    }
    // Only send non-empty credential values
    const creds: Record<string, string> = {}
    for (const [k, v] of Object.entries(credentials)) {
      if (v.trim()) creds[k] = v.trim()
    }
    try {
      await saveMut.mutateAsync({ slug: gateway.slug, body: { credentials: creds, is_test_mode: isTestMode } })
      onClose()
    } catch (e: any) {
      setError(e?.message ?? 'Error al guardar configuración')
    }
  }

  const confirm = useConfirm()

  async function handleDelete() {
    const ok = await confirm({ message: `¿Eliminar configuración de ${gateway.display_name}?`, confirmLabel: 'Eliminar' })
    if (!ok) return
    try {
      await deleteMut.mutateAsync(gateway.slug)
      onClose()
    } catch (e: any) {
      setError(e?.message ?? 'Error al eliminar configuración')
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm p-4">
      <div className="w-full max-w-md rounded-3xl bg-white shadow-2xl">
        {/* Header */}
        <div
          className="flex items-center justify-between rounded-t-3xl px-6 py-4"
          style={{ backgroundColor: (gateway.color ?? '#6366f1') + '15' }}
        >
          <div className="flex items-center gap-3">
            <div
              className="flex h-10 w-10 items-center justify-center rounded-2xl text-white text-lg font-bold shadow"
              style={{ backgroundColor: gateway.color ?? '#6366f1' }}
            >
              {gateway.display_name[0]}
            </div>
            <div>
              <h2 className="font-bold text-slate-900">{gateway.display_name}</h2>
              <p className="text-xs text-slate-500">Configurar pasarela</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="rounded-xl p-2 text-slate-400 hover:bg-white/60 hover:text-slate-700 transition-colors"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        <div className="px-6 py-5 space-y-5">
          {/* Test / Production toggle */}
          <div className="flex items-center justify-between rounded-2xl bg-slate-50 px-4 py-3">
            <div>
              <p className="text-sm font-semibold text-slate-700">Modo</p>
              <p className="text-xs text-slate-400">{isTestMode ? 'Pruebas — no se cobran transacciones reales' : 'Producción — transacciones reales activas'}</p>
            </div>
            <button
              onClick={() => setIsTestMode((v) => !v)}
              className={cn(
                'relative h-6 w-11 rounded-full transition-colors duration-300',
                isTestMode ? 'bg-amber-400' : 'bg-emerald-500',
              )}
            >
              <span className={cn(
                'absolute top-0.5 left-0.5 h-5 w-5 rounded-full bg-white shadow transition-transform duration-300',
                isTestMode ? 'translate-x-0' : 'translate-x-5',
              )} />
            </button>
          </div>
          <p className="text-xs text-center font-semibold" style={{ color: isTestMode ? '#d97706' : '#10b981' }}>
            {isTestMode ? '⚡ Modo Test' : '✅ Producción'}
          </p>

          {/* Credential fields */}
          <div className="space-y-3">
            {fields.map((field) => {
              const isPassword = field.type === 'password'
              const visible = showFields[field.key]
              return (
                <div key={field.key}>
                  <label className="block text-xs font-semibold text-slate-600 mb-1">
                    {field.label}
                    {field.required && <span className="text-red-500 ml-0.5">*</span>}
                  </label>
                  <div className="relative">
                    <input
                      type={isPassword && !visible ? 'password' : 'text'}
                      value={credentials[field.key] ?? ''}
                      onChange={(e) => setCredentials((prev) => ({ ...prev, [field.key]: e.target.value }))}
                      placeholder={gateway.configured ? '••••••  (dejar vacío para mantener)' : ''}
                      className="w-full rounded-xl border border-slate-200 bg-slate-50 px-3 py-2.5 text-sm text-slate-900 placeholder:text-slate-400 focus:border-indigo-400 focus:outline-none focus:ring-2 focus:ring-indigo-100 pr-10"
                    />
                    {isPassword && (
                      <button
                        type="button"
                        onClick={() => setShowFields((prev) => ({ ...prev, [field.key]: !prev[field.key] }))}
                        className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
                      >
                        {visible ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                      </button>
                    )}
                  </div>
                </div>
              )
            })}
          </div>

          {error && (
            <p className="rounded-xl bg-red-50 border border-red-200 px-3 py-2 text-xs text-red-700">{error}</p>
          )}

          {/* Actions */}
          <div className="flex items-center gap-3 pt-1">
            {gateway.configured && (
              <button
                onClick={handleDelete}
                disabled={deleteMut.isPending}
                className="flex items-center gap-1.5 rounded-xl border border-red-200 px-3 py-2 text-xs font-semibold text-red-600 hover:bg-red-50 transition-colors disabled:opacity-50"
              >
                <Trash2 className="h-3.5 w-3.5" />
                Eliminar
              </button>
            )}
            <button
              onClick={onClose}
              className="ml-auto rounded-xl border border-slate-200 px-4 py-2 text-sm font-semibold text-slate-600 hover:bg-slate-50 transition-colors"
            >
              Cancelar
            </button>
            <button
              onClick={handleSave}
              disabled={saveMut.isPending}
              className="rounded-xl bg-indigo-600 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-700 transition-colors disabled:opacity-50"
            >
              {saveMut.isPending ? 'Guardando…' : 'Guardar'}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export function PaymentsPage() {
  const { data: configs = [], isLoading, isError, error: fetchError } = useGatewayConfigs(TENANT_ID)
  const activateMut = useSetActiveGateway(TENANT_ID)
  const [configuring, setConfiguring] = useState<GatewayConfigOut | null>(null)
  const [activating, setActivating] = useState<string | null>(null)
  const [actionError, setActionError] = useState<string | null>(null)

  async function handleActivate(slug: string) {
    setActivating(slug)
    setActionError(null)
    try {
      await activateMut.mutateAsync(slug)
    } catch (e: any) {
      setActionError(e?.message ?? 'Error al activar pasarela')
    } finally {
      setActivating(null)
    }
  }

  return (
    <div className="max-w-5xl mx-auto space-y-8 p-6">
      {/* Header */}
      <div className="flex items-center gap-4">
        <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-gradient-to-br from-emerald-500 to-teal-600 shadow-md">
          <Banknote className="h-6 w-6 text-white" />
        </div>
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Pasarela de Cobro</h1>
          <p className="text-sm text-slate-500">Elige cómo TraceLog cobra las suscripciones a tus clientes</p>
        </div>
      </div>

      {(actionError || isError) && (
        <div className="rounded-xl bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-700">
          {actionError ?? (fetchError as Error)?.message ?? 'Error al cargar pasarelas'}
        </div>
      )}

      {/* Grid */}
      {isLoading ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
          {[...Array(7)].map((_, i) => (
            <div key={i} className="h-52 rounded-3xl bg-slate-100 animate-pulse" />
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
          {configs.map((gw) => {
            const color = gw.color ?? '#6366f1'
            const isActive = gw.is_active
            const isConfigured = gw.configured
            const isActivating = activating === gw.slug

            return (
              <div
                key={gw.slug}
                className={cn(
                  'relative overflow-hidden rounded-3xl border bg-white shadow-sm transition-all duration-300',
                  isActive
                    ? 'border-emerald-300 shadow-emerald-50 ring-2 ring-emerald-200'
                    : isConfigured
                      ? 'border-blue-200'
                      : 'border-slate-200',
                )}
              >
                {/* Top color bar */}
                <div className="h-1.5 w-full" style={{ backgroundColor: color }} />

                <div className="p-5">
                  {/* Header row */}
                  <div className="flex items-start justify-between mb-3">
                    <div className="flex items-center gap-2.5">
                      <div
                        className="flex h-10 w-10 items-center justify-center rounded-2xl text-white text-base font-bold shadow-sm"
                        style={{ backgroundColor: color }}
                      >
                        {(gw.display_name ?? gw.name ?? '?')[0]}
                      </div>
                      <div>
                        <h3 className="font-bold text-slate-900 text-sm">{gw.display_name ?? gw.name}</h3>
                        <p className="text-[10px] text-slate-400 uppercase tracking-wide">{gw.slug}</p>
                      </div>
                    </div>

                    {/* Status badge */}
                    {isActive ? (
                      <span className="flex items-center gap-1 rounded-full bg-emerald-50 px-2 py-0.5 text-[10px] font-bold text-emerald-700 ring-1 ring-emerald-200">
                        <CheckCircle2 className="h-3 w-3" /> En uso
                      </span>
                    ) : isConfigured ? (
                      <span className="rounded-full bg-blue-50 px-2 py-0.5 text-[10px] font-bold text-blue-700 ring-1 ring-blue-200">
                        Configurado
                      </span>
                    ) : (
                      <span className="rounded-full bg-slate-50 px-2 py-0.5 text-[10px] font-bold text-slate-400 ring-1 ring-slate-200">
                        Sin configurar
                      </span>
                    )}
                  </div>

                  {/* Description */}
                  <p className="text-xs text-slate-500 leading-relaxed mb-4 line-clamp-2">{gw.description}</p>

                  {/* Mode chip (only when configured) */}
                  {isConfigured && (
                    <span className={cn(
                      'inline-block rounded-full px-2.5 py-0.5 text-[10px] font-semibold mb-4',
                      gw.is_test_mode
                        ? 'bg-amber-50 text-amber-700 ring-1 ring-amber-200'
                        : 'bg-emerald-50 text-emerald-700 ring-1 ring-emerald-200',
                    )}>
                      {gw.is_test_mode ? '⚡ Test' : '✅ Producción'}
                    </span>
                  )}

                  {/* Actions */}
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => setConfiguring(gw)}
                      className="flex items-center gap-1.5 rounded-xl border border-slate-200 px-3 py-1.5 text-xs font-semibold text-slate-600 hover:bg-slate-50 transition-colors"
                    >
                      <Settings className="h-3.5 w-3.5" />
                      {isConfigured ? 'Editar' : 'Configurar'}
                    </button>
                    {isConfigured && !isActive && (
                      <button
                        onClick={() => handleActivate(gw.slug)}
                        disabled={isActivating}
                        className="flex items-center gap-1.5 rounded-xl bg-emerald-500 px-3 py-1.5 text-xs font-semibold text-white hover:bg-emerald-600 transition-colors disabled:opacity-50"
                      >
                        <Zap className="h-3.5 w-3.5" />
                        {isActivating ? '…' : 'Activar'}
                      </button>
                    )}
                    {isActive && (
                      <span className="flex items-center gap-1 text-xs font-semibold text-emerald-600">
                        <CheckCircle2 className="h-3.5 w-3.5" /> Activa
                      </span>
                    )}
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      )}

      {/* Configure Modal */}
      {configuring && (
        <ConfigureGatewayModal
          gateway={configuring}
          onClose={() => setConfiguring(null)}
        />
      )}
    </div>
  )
}
