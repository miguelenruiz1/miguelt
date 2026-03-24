import { useState } from 'react'
import {
  Banknote, CheckCircle2, Settings, Trash2, Eye, EyeOff, X,
  ShieldCheck, TestTube, Zap, ExternalLink,
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

// ─── Configure Modal ──────────────────────────────────────────────────────────

function ConfigureWompiModal({
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
  const activateMut = useSetActiveGateway(TENANT_ID)

  async function handleSave() {
    setError(null)
    for (const f of fields) {
      if (f.required && !credentials[f.key]?.trim() && !gateway.configured) {
        setError(`El campo "${f.label}" es obligatorio`)
        return
      }
    }
    const creds: Record<string, string> = {}
    for (const [k, v] of Object.entries(credentials)) {
      if (v.trim()) creds[k] = v.trim()
    }
    try {
      await saveMut.mutateAsync({ slug: 'wompi', body: { credentials: creds, is_test_mode: isTestMode } })
      // Auto-activate after saving
      await activateMut.mutateAsync('wompi')
      onClose()
    } catch (e: any) {
      setError(e?.message ?? 'Error al guardar configuración')
    }
  }

  const confirm = useConfirm()

  async function handleDelete() {
    const ok = await confirm({ message: '¿Eliminar configuración de Wompi? Se deshabilitarán los cobros.', confirmLabel: 'Eliminar' })
    if (!ok) return
    try {
      await deleteMut.mutateAsync('wompi')
      onClose()
    } catch (e: any) {
      setError(e?.message ?? 'Error al eliminar')
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm p-4">
      <div className="w-full max-w-lg rounded-3xl bg-white shadow-2xl">
        {/* Header */}
        <div className="flex items-center justify-between rounded-t-3xl px-6 py-4 bg-[#5C2D91]/10">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-2xl bg-[#5C2D91] text-white text-lg font-bold shadow">
              W
            </div>
            <div>
              <h2 className="font-bold text-slate-900">Configurar Wompi</h2>
              <p className="text-xs text-slate-500">Llaves de tu cuenta Wompi</p>
            </div>
          </div>
          <button onClick={onClose} className="rounded-xl p-2 text-slate-400 hover:bg-white/60 hover:text-slate-700 transition-colors">
            <X className="h-4 w-4" />
          </button>
        </div>

        <div className="px-6 py-5 space-y-5">
          {/* Test / Production toggle */}
          <div className="flex items-center justify-between rounded-2xl bg-slate-50 px-4 py-3">
            <div>
              <p className="text-sm font-semibold text-slate-700">Modo</p>
              <p className="text-xs text-slate-400">
                {isTestMode ? 'Sandbox — no se cobran transacciones reales' : 'Producción — transacciones reales'}
              </p>
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

          <div className="flex justify-center">
            <span className={cn(
              'inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-bold',
              isTestMode ? 'bg-amber-50 text-amber-700' : 'bg-emerald-50 text-emerald-700',
            )}>
              {isTestMode ? <TestTube className="h-3.5 w-3.5" /> : <ShieldCheck className="h-3.5 w-3.5" />}
              {isTestMode ? 'Modo Sandbox' : 'Modo Producción'}
            </span>
          </div>

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
                      placeholder={gateway.configured ? '••••••  (dejar vacío para mantener)' : isTestMode ? `${field.label} de sandbox` : ''}
                      className="w-full rounded-xl border border-slate-200 bg-slate-50 px-3 py-2.5 text-sm text-slate-900 placeholder:text-slate-400 focus:border-[#5C2D91]/50 focus:outline-none focus:ring-2 focus:ring-[#5C2D91]/20 pr-10 font-mono"
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

          <p className="text-[10px] text-slate-400 text-center">
            Encuentra tus llaves en{' '}
            <a href="https://comercios.wompi.co/developers" target="_blank" rel="noopener noreferrer" className="text-[#5C2D91] underline">
              comercios.wompi.co/developers
            </a>
          </p>

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
                <Trash2 className="h-3.5 w-3.5" /> Eliminar
              </button>
            )}
            <button onClick={onClose} className="ml-auto rounded-xl border border-slate-200 px-4 py-2 text-sm font-semibold text-slate-600 hover:bg-slate-50 transition-colors">
              Cancelar
            </button>
            <button
              onClick={handleSave}
              disabled={saveMut.isPending || activateMut.isPending}
              className="rounded-xl bg-[#5C2D91] px-5 py-2 text-sm font-semibold text-white hover:bg-[#5C2D91]/90 transition-colors disabled:opacity-50"
            >
              {saveMut.isPending || activateMut.isPending ? 'Guardando…' : 'Guardar y activar'}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export function PaymentsPage() {
  const { data: configs = [], isLoading } = useGatewayConfigs(TENANT_ID)
  const [showModal, setShowModal] = useState(false)

  const wompi = configs.find((c) => c.slug === 'wompi')
  const isConfigured = wompi?.configured ?? false
  const isActive = wompi?.is_active ?? false
  const isTestMode = wompi?.is_test_mode ?? true

  return (
    <div className="max-w-3xl mx-auto space-y-8 p-6">
      {/* Header */}
      <div className="flex items-center gap-4">
        <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-[#5C2D91] shadow-md">
          <Banknote className="h-6 w-6 text-white" />
        </div>
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Pasarela de Cobro</h1>
          <p className="text-sm text-slate-500">Configura Wompi para cobrar suscripciones y planes</p>
        </div>
      </div>

      {isLoading ? (
        <div className="h-64 rounded-3xl bg-slate-100 animate-pulse" />
      ) : (
        <div className="rounded-3xl border border-slate-200 bg-white shadow-sm overflow-hidden">
          {/* Top color bar */}
          <div className="h-2 w-full bg-[#5C2D91]" />

          <div className="p-6 sm:p-8">
            <div className="flex flex-col sm:flex-row sm:items-center gap-6">
              {/* Logo + info */}
              <div className="flex items-center gap-4 flex-1">
                <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-[#5C2D91] text-white text-2xl font-bold shadow-lg shrink-0">
                  W
                </div>
                <div>
                  <h2 className="text-xl font-bold text-slate-900">Wompi</h2>
                  <p className="text-sm text-slate-500 mt-0.5">Bancolombia · Tarjetas, PSE, Nequi</p>

                  {/* Status */}
                  <div className="flex items-center gap-2 mt-2">
                    {isActive ? (
                      <span className="flex items-center gap-1 rounded-full bg-emerald-50 px-2.5 py-0.5 text-xs font-bold text-emerald-700 ring-1 ring-emerald-200">
                        <CheckCircle2 className="h-3 w-3" /> Activa
                      </span>
                    ) : isConfigured ? (
                      <span className="rounded-full bg-blue-50 px-2.5 py-0.5 text-xs font-bold text-blue-700 ring-1 ring-blue-200">
                        Configurada
                      </span>
                    ) : (
                      <span className="rounded-full bg-slate-50 px-2.5 py-0.5 text-xs font-bold text-slate-400 ring-1 ring-slate-200">
                        Sin configurar
                      </span>
                    )}

                    {isConfigured && (
                      <span className={cn(
                        'rounded-full px-2.5 py-0.5 text-xs font-bold',
                        isTestMode
                          ? 'bg-amber-50 text-amber-700 ring-1 ring-amber-200'
                          : 'bg-emerald-50 text-emerald-700 ring-1 ring-emerald-200',
                      )}>
                        {isTestMode ? 'Sandbox' : 'Producción'}
                      </span>
                    )}
                  </div>
                </div>
              </div>

              {/* Action button */}
              <button
                onClick={() => setShowModal(true)}
                className="flex items-center gap-2 rounded-xl bg-[#5C2D91] px-5 py-2.5 text-sm font-semibold text-white hover:bg-[#5C2D91]/90 transition-colors shadow-sm shrink-0"
              >
                <Settings className="h-4 w-4" />
                {isConfigured ? 'Editar llaves' : 'Configurar'}
              </button>
            </div>

            {/* Configured credentials preview */}
            {isConfigured && wompi?.credentials_masked && (
              <div className="mt-6 rounded-2xl bg-slate-50 border border-slate-200 divide-y divide-slate-200">
                {Object.entries(wompi.credentials_masked).map(([key, value]) => (
                  <div key={key} className="flex items-center justify-between px-4 py-2.5">
                    <span className="text-xs font-medium text-slate-500">{key}</span>
                    <span className="text-xs font-mono text-slate-400">{value as string}</span>
                  </div>
                ))}
                {wompi.updated_at && (
                  <div className="px-4 py-2 text-[10px] text-slate-400">
                    Última actualización: {new Date(wompi.updated_at).toLocaleString()}
                  </div>
                )}
              </div>
            )}

            {/* Help text */}
            {!isConfigured && (
              <div className="mt-6 rounded-2xl bg-amber-50 border border-amber-200 px-5 py-4">
                <p className="text-sm text-amber-800 font-medium">Configura tus llaves de Wompi para habilitar cobros</p>
                <p className="text-xs text-amber-600 mt-1">
                  Necesitas una cuenta en{' '}
                  <a href="https://comercios.wompi.co" target="_blank" rel="noopener noreferrer" className="underline font-semibold">
                    comercios.wompi.co
                  </a>
                  . Copia tus llaves pública, privada, de integridad y el secreto de eventos desde el panel de desarrolladores.
                </p>
              </div>
            )}
          </div>

          {/* Info footer */}
          <div className="border-t border-slate-100 bg-slate-50/50 px-6 sm:px-8 py-4 flex items-center justify-between">
            <div className="flex items-center gap-2 text-xs text-slate-400">
              <ShieldCheck className="h-3.5 w-3.5" />
              <span>Las credenciales se almacenan cifradas y nunca se exponen</span>
            </div>
            <a
              href="https://docs.wompi.co"
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-1 text-xs text-[#5C2D91] font-medium hover:underline"
            >
              Documentación <ExternalLink className="h-3 w-3" />
            </a>
          </div>
        </div>
      )}

      {/* Configure Modal */}
      {showModal && wompi && (
        <ConfigureWompiModal gateway={wompi} onClose={() => setShowModal(false)} />
      )}
      {showModal && !wompi && (
        <ConfigureWompiModal
          gateway={{
            slug: 'wompi',
            display_name: 'Wompi',
            name: 'Wompi',
            description: 'Pasarela de pagos de Bancolombia',
            color: '#5C2D91',
            is_active: false,
            is_test_mode: true,
            configured: false,
            credentials_masked: {},
            updated_at: null,
            fields: [
              { key: 'public_key', label: 'Llave pública (pub_...)', type: 'text', required: true },
              { key: 'private_key', label: 'Llave privada (prv_...)', type: 'password', required: true },
              { key: 'events_secret', label: 'Secreto de eventos', type: 'password', required: false },
              { key: 'integrity_key', label: 'Llave de integridad', type: 'password', required: true },
            ],
          }}
          onClose={() => setShowModal(false)}
        />
      )}
    </div>
  )
}
