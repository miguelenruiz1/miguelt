import { useState } from 'react'
import {
  Mail, CheckCircle2, Settings, Trash2, Zap, Eye, EyeOff, X, Send, ChevronRight, XCircle,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { useConfirm } from '@/store/confirm'
import {
  useEmailProviderConfigs,
  useSaveEmailProviderConfig,
  useSetActiveEmailProvider,
  useDeleteEmailProviderConfig,
  useTestEmailProvider,
} from '@/hooks/useEmailProviders'
import type { EmailProviderConfigOut, EmailProviderField } from '@/types/email-providers'

/* ---------- Official provider logos (inline SVG) ---------- */
function ProviderLogo({ slug, color }: { slug: string; color: string }) {
  const size = 50
  const cls = 'rounded-xl'

  // Gmail — multicolor envelope M
  if (slug === 'gmail') return (
    <div className={cn(cls, 'flex items-center justify-center bg-white border border-gray-100')} style={{ width: size, height: size }}>
      <svg width="28" height="22" viewBox="0 0 28 22" fill="none">
        <path d="M2 0h24a2 2 0 012 2v18a2 2 0 01-2 2H2a2 2 0 01-2-2V2a2 2 0 012-2z" fill="#F4F4F4"/>
        <path d="M2 0l12 9L26 0H2z" fill="#EA4335"/>
        <path d="M0 2l14 10L28 2v18a2 2 0 01-2 2H2a2 2 0 01-2-2V2z" fill="white"/>
        <path d="M0 2l14 10V22H2a2 2 0 01-2-2V2z" fill="#34A853" opacity=".8"/>
        <path d="M28 2L14 12V22h12a2 2 0 002-2V2z" fill="#4285F4" opacity=".8"/>
        <path d="M0 2l14 10L28 2" stroke="#EA4335" strokeWidth="1.5" fill="none"/>
        <rect x="0" y="0" width="4" height="22" rx="1" fill="#FBBC04" opacity=".9"/>
        <rect x="24" y="0" width="4" height="22" rx="1" fill="#34A853" opacity=".9"/>
      </svg>
    </div>
  )

  // Outlook — blue O mark
  if (slug === 'outlook') return (
    <div className={cn(cls, 'flex items-center justify-center')} style={{ width: size, height: size, backgroundColor: '#0078D4' }}>
      <svg width="26" height="26" viewBox="0 0 26 26" fill="none">
        <path d="M13 1C6.37 1 1 6.37 1 13s5.37 12 12 12 12-5.37 12-12S19.63 1 13 1z" fill="white" opacity=".2"/>
        <text x="13" y="18" textAnchor="middle" fill="white" fontSize="16" fontWeight="bold" fontFamily="Segoe UI,sans-serif">O</text>
      </svg>
    </div>
  )

  // SendGrid — SG stylized
  if (slug === 'sendgrid') return (
    <div className={cn(cls, 'flex items-center justify-center')} style={{ width: size, height: size, backgroundColor: '#1A82E2' }}>
      <svg width="28" height="28" viewBox="0 0 28 28" fill="none">
        <rect x="4" y="4" width="9" height="9" rx="1" fill="white" opacity=".9"/>
        <rect x="15" y="4" width="9" height="9" rx="1" fill="white" opacity=".5"/>
        <rect x="4" y="15" width="9" height="9" rx="1" fill="white" opacity=".5"/>
        <rect x="15" y="15" width="9" height="9" rx="1" fill="white" opacity=".9"/>
      </svg>
    </div>
  )

  // Mailgun — red MG shield
  if (slug === 'mailgun') return (
    <div className={cn(cls, 'flex items-center justify-center')} style={{ width: size, height: size, backgroundColor: '#F06B56' }}>
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
        <path d="M12 2L3 6v6c0 5.55 3.84 10.74 9 12 5.16-1.26 9-6.45 9-12V6l-9-4z" fill="white" opacity=".2"/>
        <text x="12" y="16" textAnchor="middle" fill="white" fontSize="9" fontWeight="bold" fontFamily="sans-serif">MG</text>
      </svg>
    </div>
  )

  // AWS SES — orange AWS arrow
  if (slug === 'aws_ses') return (
    <div className={cn(cls, 'flex items-center justify-center')} style={{ width: size, height: size, backgroundColor: '#232F3E' }}>
      <svg width="28" height="18" viewBox="0 0 28 18" fill="none">
        <path d="M8 14c-2.8-2-4.5-5-4.5-8.5C3.5 2.5 6 .5 9 .5c2 0 3.8 1 5 2.5C15.2 1.5 17 .5 19 .5c3 0 5.5 2 5.5 5 0 3.5-1.7 6.5-4.5 8.5" stroke="#FF9900" strokeWidth="2" fill="none"/>
        <path d="M2 13l12 4.5L26 13" stroke="#FF9900" strokeWidth="2" fill="none"/>
      </svg>
    </div>
  )

  // Postmark — yellow P stamp
  if (slug === 'postmark') return (
    <div className={cn(cls, 'flex items-center justify-center')} style={{ width: size, height: size, backgroundColor: '#FFDE00' }}>
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
        <circle cx="12" cy="12" r="10" stroke="#1E1E1E" strokeWidth="2" fill="none"/>
        <text x="12" y="17" textAnchor="middle" fill="#1E1E1E" fontSize="14" fontWeight="bold" fontFamily="sans-serif">P</text>
      </svg>
    </div>
  )

  // Resend — black R
  if (slug === 'resend') return (
    <div className={cn(cls, 'flex items-center justify-center')} style={{ width: size, height: size, backgroundColor: '#000000' }}>
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
        <text x="12" y="17.5" textAnchor="middle" fill="white" fontSize="16" fontWeight="bold" fontFamily="Inter,sans-serif">R</text>
      </svg>
    </div>
  )

  // SMTP — gray envelope icon
  if (slug === 'smtp') return (
    <div className={cn(cls, 'flex items-center justify-center bg-gray-100')} style={{ width: size, height: size }}>
      <Mail className="h-6 w-6 text-gray-500" />
    </div>
  )

  // Fallback — first letter with provider color
  return (
    <div
      className={cn(cls, 'flex items-center justify-center text-white text-lg font-bold shadow-sm')}
      style={{ width: size, height: size, backgroundColor: color }}
    >
      {slug[0]?.toUpperCase() ?? '?'}
    </div>
  )
}

/* ---------- Toggle switch (TailAdmin style) ---------- */
function Toggle({
  checked,
  onChange,
  disabled,
  title,
}: {
  checked: boolean
  onChange: () => void
  disabled?: boolean
  title?: string
}) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      disabled={disabled}
      onClick={onChange}
      title={title}
      className={cn(
        'relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full transition duration-150 ease-linear',
        checked ? 'bg-primary' : 'bg-gray-200',
        disabled && 'opacity-40 pointer-events-none',
      )}
    >
      <span
        className={cn(
          'absolute left-0.5 top-0.5 h-5 w-5 rounded-full bg-white shadow-sm transform transition duration-150 ease-linear',
          checked ? 'translate-x-full' : 'translate-x-0',
        )}
      />
    </button>
  )
}

// ─── Configure Provider Modal ────────────────────────────────────────────────

function ConfigureProviderModal({
  provider,
  onClose,
}: {
  provider: EmailProviderConfigOut
  onClose: () => void
}) {
  const fields: EmailProviderField[] = provider.fields ?? []
  const [isTestMode, setIsTestMode] = useState(provider.is_test_mode ?? true)
  const [credentials, setCredentials] = useState<Record<string, string>>(
    () => Object.fromEntries(fields.map((f) => [f.key, ''])),
  )
  const [showFields, setShowFields] = useState<Record<string, boolean>>({})
  const [error, setError] = useState<string | null>(null)
  const [testEmail, setTestEmail] = useState('')
  const [testResult, setTestResult] = useState<{ ok: boolean; error?: string } | null>(null)

  const saveMut = useSaveEmailProviderConfig()
  const deleteMut = useDeleteEmailProviderConfig()
  const testMut = useTestEmailProvider()

  async function handleSave() {
    setError(null)
    for (const f of fields) {
      if (f.required && !credentials[f.key]?.trim()) {
        setError(`El campo "${f.label}" es obligatorio`)
        return
      }
    }
    const creds: Record<string, string> = {}
    for (const [k, v] of Object.entries(credentials)) {
      if (v.trim()) creds[k] = v.trim()
    }
    try {
      await saveMut.mutateAsync({ slug: provider.slug, body: { credentials: creds, is_test_mode: isTestMode } })
      onClose()
    } catch (e: any) {
      setError(e?.message ?? 'Error al guardar configuración')
    }
  }

  const confirm = useConfirm()

  async function handleDelete() {
    const ok = await confirm({ message: `¿Eliminar configuración de ${provider.display_name}?`, confirmLabel: 'Eliminar' })
    if (!ok) return
    try {
      await deleteMut.mutateAsync(provider.slug)
      onClose()
    } catch (e: any) {
      setError(e?.message ?? 'Error al eliminar configuración')
    }
  }

  async function handleTest() {
    if (!testEmail.trim()) {
      setError('Ingresa un correo para la prueba')
      return
    }
    setTestResult(null)
    setError(null)
    try {
      const result = await testMut.mutateAsync({ slug: provider.slug, to: testEmail.trim() })
      setTestResult(result)
    } catch (e: any) {
      setTestResult({ ok: false, error: e?.message ?? 'Error al enviar prueba' })
    }
  }

  const inputCls = 'h-11 w-full rounded-lg border border-gray-300 bg-transparent px-4 py-2.5 text-sm text-gray-800 shadow-sm placeholder:text-gray-400 focus:border-primary/50 focus:outline-none focus:ring-3 focus:ring-ring/20'

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4" role="dialog" aria-modal="true">
      <div className="absolute inset-0 bg-gray-900/50" onClick={onClose} />
      <div className="relative w-full max-w-md rounded-2xl border border-gray-200 bg-white shadow-xl max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between px-6 pt-6 pb-4 border-b border-gray-100">
          <div className="flex items-center gap-3">
            <ProviderLogo slug={provider.slug} color={provider.color ?? '#6366f1'} />
            <div>
              <h2 className="font-semibold text-gray-800">{provider.display_name}</h2>
              <p className="text-xs text-gray-500">Configurar proveedor de correo</p>
            </div>
          </div>
          <button onClick={onClose} className="rounded-lg p-2 text-gray-400 hover:bg-gray-100 hover:text-gray-700 transition-colors">
            <X className="h-4 w-4" />
          </button>
        </div>

        <div className="px-6 py-5 space-y-5">
          {/* Test / Production toggle */}
          <div className="flex items-center justify-between rounded-lg bg-gray-50 px-4 py-3">
            <div>
              <p className="text-sm font-medium text-gray-700">Modo</p>
              <p className="text-xs text-gray-400">{isTestMode ? 'Pruebas — no se envían correos reales' : 'Producción — envío real activo'}</p>
            </div>
            <Toggle
              checked={!isTestMode}
              onChange={() => setIsTestMode((v) => !v)}
              title={isTestMode ? 'Cambiar a producción' : 'Cambiar a pruebas'}
            />
          </div>
          <p className="text-xs text-center font-semibold" style={{ color: isTestMode ? '#d97706' : '#10b981' }}>
            {isTestMode ? 'Modo Test' : 'Producción'}
          </p>

          {/* Credential fields */}
          <div className="space-y-4">
            {fields.map((field) => {
              const isPassword = field.type === 'password'
              const visible = showFields[field.key]
              return (
                <div key={field.key}>
                  <label className="mb-1.5 block text-sm font-medium text-gray-700">
                    {field.label}
                    {field.required && <span className="text-red-500 ml-0.5">*</span>}
                  </label>
                  <div className="relative">
                    <input
                      type={isPassword && !visible ? 'password' : 'text'}
                      value={credentials[field.key] ?? ''}
                      onChange={(e) => setCredentials((prev) => ({ ...prev, [field.key]: e.target.value }))}
                      placeholder={provider.configured ? '(dejar vacío para mantener)' : ''}
                      className={cn(inputCls, 'pr-10')}
                    />
                    {isPassword && (
                      <button
                        type="button"
                        onClick={() => setShowFields((prev) => ({ ...prev, [field.key]: !prev[field.key] }))}
                        className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
                      >
                        {visible ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                      </button>
                    )}
                  </div>
                </div>
              )
            })}
          </div>

          {/* Test email section — only when configured */}
          {provider.configured && (
            <div className="rounded-lg bg-gray-50 border border-gray-200 p-4 space-y-3">
              <p className="text-sm font-medium text-gray-700">Enviar correo de prueba</p>
              <div className="flex gap-2">
                <input
                  type="email"
                  value={testEmail}
                  onChange={(e) => setTestEmail(e.target.value)}
                  placeholder="correo@ejemplo.com"
                  className={cn(inputCls, 'h-9 py-1')}
                />
                <button
                  onClick={handleTest}
                  disabled={testMut.isPending}
                  className="flex items-center gap-1.5 rounded-lg bg-primary px-3 py-2 text-xs font-medium text-white hover:bg-primary transition disabled:opacity-50 shadow-sm"
                >
                  <Send className="h-3.5 w-3.5" />
                  {testMut.isPending ? '...' : 'Probar'}
                </button>
              </div>
              {testResult && (
                <p className={cn(
                  'text-xs rounded-lg px-3 py-2 border',
                  testResult.ok
                    ? 'bg-emerald-50 border-emerald-200 text-emerald-700'
                    : 'bg-red-50 border-red-200 text-red-700',
                )}>
                  {testResult.ok ? 'Correo enviado correctamente' : testResult.error}
                </p>
              )}
            </div>
          )}

          {error && (
            <p className="rounded-lg bg-red-50 border border-red-200 px-3 py-2 text-xs text-red-700">{error}</p>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center gap-3 px-6 py-4 border-t border-gray-100">
          {provider.configured && (
            <button
              onClick={handleDelete}
              disabled={deleteMut.isPending}
              className="flex items-center gap-1.5 rounded-lg border border-red-200 px-3 py-2.5 text-xs font-medium text-red-600 hover:bg-red-50 transition disabled:opacity-50"
            >
              <Trash2 className="h-3.5 w-3.5" />
              Eliminar
            </button>
          )}
          <button
            onClick={onClose}
            className="ml-auto rounded-lg border border-gray-300 px-4 py-2.5 text-sm font-medium text-gray-700 hover:bg-gray-50 transition"
          >
            Cancelar
          </button>
          <button
            onClick={handleSave}
            disabled={saveMut.isPending}
            className="rounded-lg bg-primary px-4 py-2.5 text-sm font-medium text-white hover:bg-primary transition disabled:opacity-50 shadow-sm"
          >
            {saveMut.isPending ? 'Guardando...' : 'Guardar'}
          </button>
        </div>
      </div>
    </div>
  )
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export function EmailProvidersPage() {
  const { data: configs = [], isLoading, isError, error: fetchError } = useEmailProviderConfigs()
  const activateMut = useSetActiveEmailProvider()
  const [configuring, setConfiguring] = useState<EmailProviderConfigOut | null>(null)
  const [activating, setActivating] = useState<string | null>(null)
  const [actionError, setActionError] = useState<string | null>(null)

  async function handleActivate(slug: string) {
    setActivating(slug)
    setActionError(null)
    try {
      await activateMut.mutateAsync(slug)
    } catch (e: any) {
      setActionError(e?.message ?? 'Error al activar proveedor')
    } finally {
      setActivating(null)
    }
  }

  return (
    <div className="space-y-6">
      {/* Breadcrumb */}
      <nav className="mb-4">
        <ol className="flex items-center gap-2 text-sm">
          <li className="text-gray-500">Mi Empresa</li>
          <li><ChevronRight className="h-4 w-4 text-gray-400" /></li>
          <li className="text-primary">Proveedor de Correo</li>
        </ol>
      </nav>

      {/* Header */}
      <div>
        <h1 className="text-2xl font-semibold text-gray-800">Proveedores de Correo</h1>
        <p className="text-sm text-gray-500 mt-1">Configura cómo TraceLog envía correos electrónicos a tu organización</p>
      </div>

      {/* Error alert */}
      {(actionError || isError) && (
        <div className="flex items-center gap-2 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          <XCircle className="h-4 w-4 shrink-0" />
          {actionError ?? (fetchError as Error)?.message ?? 'Error al cargar proveedores'}
          <button onClick={() => setActionError(null)} className="ml-auto text-gray-400 hover:text-gray-600">
            <XCircle className="h-4 w-4" />
          </button>
        </div>
      )}

      {/* Grid */}
      {isLoading ? (
        <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 xl:grid-cols-3">
          {[...Array(6)].map((_, i) => (
            <div key={i} className="h-52 rounded-2xl border border-gray-200 bg-gray-50 animate-pulse" />
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 xl:grid-cols-3">
          {configs.map((prov) => {
            const color = prov.color ?? '#6366f1'
            const isActive = prov.is_active
            const isConfigured = prov.configured
            const isActivating = activating === prov.slug
            return (
              <div
                key={prov.slug}
                className="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm"
              >
                {/* Top: icon + toggle */}
                <div className="flex items-start justify-between">
                  <ProviderLogo slug={prov.slug} color={color} />
                  <Toggle
                    checked={isActive}
                    disabled={!isConfigured || isActivating}
                    title={!isConfigured ? 'Configura primero' : isActive ? 'Proveedor activo' : 'Activar proveedor'}
                    onChange={() => {
                      if (!isActive && isConfigured) handleActivate(prov.slug)
                    }}
                  />
                </div>

                {/* Title + badge */}
                <div className="mt-4 flex items-center gap-2">
                  <h3 className="text-sm font-semibold text-gray-800">{prov.display_name ?? prov.name}</h3>
                  {isActive ? (
                    <span className="inline-flex items-center gap-1 rounded-full bg-emerald-50 px-2 py-0.5 text-[10px] font-semibold text-emerald-600">
                      <CheckCircle2 className="h-3 w-3" /> En uso
                    </span>
                  ) : isConfigured ? (
                    <span className="inline-flex items-center gap-1 rounded-full bg-blue-50 px-2 py-0.5 text-[10px] font-semibold text-blue-600">
                      Configurado
                    </span>
                  ) : (
                    <span className="inline-flex items-center gap-1 rounded-full bg-gray-100 px-2 py-0.5 text-[10px] font-semibold text-gray-500">
                      Sin configurar
                    </span>
                  )}
                </div>
                <p className="text-xs text-gray-400 mt-0.5 uppercase tracking-wide">{prov.slug}</p>

                {/* Description */}
                <p className="mt-2 text-sm text-gray-500 leading-relaxed line-clamp-2">{prov.description}</p>

                {/* Feature tags */}
                <div className="mt-3 flex flex-wrap gap-2">
                  {isConfigured && (
                    <span className={cn(
                      'inline-flex items-center gap-1 rounded-full border px-2.5 py-1 text-xs',
                      prov.is_test_mode
                        ? 'border-amber-200 bg-amber-50 text-amber-700'
                        : 'border-emerald-200 bg-emerald-50 text-emerald-700',
                    )}>
                      <Zap className="h-3 w-3" />
                      {prov.is_test_mode ? 'Test' : 'Producción'}
                    </span>
                  )}
                  <button
                    onClick={() => setConfiguring(prov)}
                    className="inline-flex items-center gap-1 rounded-full border border-gray-200 bg-gray-50 px-2.5 py-1 text-xs text-gray-600 hover:bg-gray-100 transition-colors"
                  >
                    <Settings className="h-3 w-3 text-gray-400" />
                    {isConfigured ? 'Editar' : 'Configurar'}
                  </button>
                </div>
              </div>
            )
          })}
        </div>
      )}

      {/* Configure Modal */}
      {configuring && (
        <ConfigureProviderModal
          provider={configuring}
          onClose={() => setConfiguring(null)}
        />
      )}
    </div>
  )
}
