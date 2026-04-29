import { useState, useEffect } from 'react'
import {
  Mail, Eye, EyeOff, Send, ChevronRight, ChevronLeft, CheckCircle2, XCircle, Save, Settings,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import {
  useEmailProviderConfigs,
  useSaveEmailProviderConfig,
  useSetActiveEmailProvider,
  useTestEmailProvider,
} from '@/hooks/useEmailProviders'
import {
  useEmailTemplates,
  useUpdateEmailTemplate,
  useTestEmailTemplate,
} from '@/hooks/useUsers'
import { useAuthStore } from '@/store/auth'
import type { EmailTemplate } from '@/types/auth'

type Tab = 'templates' | 'config'

export function EmailProvidersPage() {
  const [tab, setTab] = useState<Tab>('templates')

  return (
    <div className="p-6 max-w-5xl mx-auto">
      {/* Breadcrumb */}
      <nav className="mb-4">
        <ol className="flex items-center gap-2 text-sm">
          <li className="text-muted-foreground">Plataforma</li>
          <li><ChevronRight className="h-4 w-4 text-muted-foreground" /></li>
          <li className="text-primary">Correo Electrónico</li>
        </ol>
      </nav>

      {/* Header */}
      <div className="flex items-center gap-4 mb-6">
        <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-black">
          <Mail className="h-6 w-6 text-white" />
        </div>
        <div>
          <h1 className="text-xl font-semibold text-foreground">Correo Electrónico</h1>
          <p className="text-sm text-muted-foreground">Configura el proveedor de correo y personaliza las plantillas</p>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 mb-6 bg-secondary rounded-xl p-1 w-fit">
        <button
          onClick={() => setTab('templates')}
          className={`px-4 py-2 text-sm font-medium rounded-lg transition-colors ${
            tab === 'templates' ? 'bg-card text-foreground ' : 'text-muted-foreground hover:text-foreground'
          }`}
        >
          <Mail className="h-4 w-4 inline-block mr-1.5 -mt-0.5" />
          Plantillas
        </button>
        <button
          onClick={() => setTab('config')}
          className={`px-4 py-2 text-sm font-medium rounded-lg transition-colors ${
            tab === 'config' ? 'bg-card text-foreground ' : 'text-muted-foreground hover:text-foreground'
          }`}
        >
          <Settings className="h-4 w-4 inline-block mr-1.5 -mt-0.5" />
          Configuración
        </button>
      </div>

      {tab === 'config' ? <ResendConfigTab /> : <TemplatesTab />}
    </div>
  )
}

/* ─── Resend Config Tab ─────────────────────────────────────────────────── */

function ResendConfigTab() {
  const { data: configs = [], isLoading } = useEmailProviderConfigs()
  const saveMut = useSaveEmailProviderConfig()
  const activateMut = useSetActiveEmailProvider()
  const testMut = useTestEmailProvider()

  const resendConfig = configs.find((c) => c.slug === 'resend')
  const isConfigured = resendConfig?.configured ?? false
  const isActive = resendConfig?.is_active ?? false

  const [apiKey, setApiKey] = useState('')
  const [fromEmail, setFromEmail] = useState('')
  const [showKey, setShowKey] = useState(false)
  const [testEmail, setTestEmail] = useState('')
  const [testResult, setTestResult] = useState<{ ok: boolean; error?: string } | null>(null)
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
    if (!apiKey.trim() && !isConfigured) {
      setError('El API Key es obligatorio')
      return
    }
    if (!fromEmail.trim() && !isConfigured) {
      setError('El correo de envío es obligatorio')
      return
    }

    const credentials: Record<string, string> = {}
    if (apiKey.trim()) credentials.api_key = apiKey.trim()
    if (fromEmail.trim()) credentials.from_email = fromEmail.trim()

    try {
      await saveMut.mutateAsync({ slug: 'resend', body: { credentials } })
      await activateMut.mutateAsync('resend')
      setSaved(true)
      setApiKey('')
      setFromEmail('')
    } catch (e: any) {
      setError(e?.message ?? 'Error al guardar')
    }
  }

  async function handleTest() {
    if (!testEmail.trim()) {
      setError('Ingresa un correo para la prueba')
      return
    }
    setError(null)
    setTestResult(null)
    try {
      const result = await testMut.mutateAsync({ slug: 'resend', to: testEmail.trim() })
      setTestResult(result)
    } catch (e: any) {
      setTestResult({ ok: false, error: e?.message ?? 'Error al enviar prueba' })
    }
  }

  const inputCls = 'h-11 w-full rounded-lg border border-gray-300 bg-transparent px-4 py-2.5 text-sm text-foreground  placeholder:text-muted-foreground focus:border-primary/50 focus:outline-none focus:ring-3 focus:ring-ring/20'

  return (
    <div className="max-w-xl space-y-6">
      {/* Status */}
      {isConfigured && isActive && (
        <div className="flex items-center gap-2 rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-700">
          <CheckCircle2 className="h-4 w-4 shrink-0" />
          Resend está configurado y activo. Los correos se envían en producción.
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

      {isLoading ? (
        <div className="h-64 rounded-2xl border border-border bg-muted animate-pulse" />
      ) : (
        <div className="rounded-2xl border border-border bg-card p-6  space-y-5">
          {/* API Key */}
          <div>
            <label className="mb-1.5 block text-sm font-medium text-foreground">
              API Key <span className="text-red-500">*</span>
            </label>
            <div className="relative">
              <input
                type={showKey ? 'text' : 'password'}
                value={apiKey}
                onChange={(e) => setApiKey(e.target.value)}
                placeholder={isConfigured ? '(dejar vacío para mantener el actual)' : 're_xxxxxxxxxxxxxxxxxxxxxxxxx'}
                className={cn(inputCls, 'pr-10 font-mono')}
              />
              <button
                type="button"
                onClick={() => setShowKey((v) => !v)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-muted-foreground"
              >
                {showKey ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
              </button>
            </div>
            <p className="mt-1 text-xs text-muted-foreground">
              Obtén tu API key en{' '}
              <span className="text-muted-foreground font-medium">resend.com/api-keys</span>
            </p>
          </div>

          {/* From Email */}
          <div>
            <label className="mb-1.5 block text-sm font-medium text-foreground">
              Correo de envío <span className="text-red-500">*</span>
            </label>
            <input
              type="email"
              value={fromEmail}
              onChange={(e) => setFromEmail(e.target.value)}
              placeholder={isConfigured ? '(dejar vacío para mantener el actual)' : 'noreply@tudominio.com'}
              className={inputCls}
            />
            <p className="mt-1 text-xs text-muted-foreground">
              Debe ser un dominio verificado en tu cuenta de Resend
            </p>
          </div>

          {/* Save */}
          <button
            onClick={handleSave}
            disabled={saveMut.isPending || activateMut.isPending}
            className="flex w-full items-center justify-center gap-2 rounded-lg bg-primary px-4 py-2.5 text-sm font-medium text-white hover:bg-primary/90 transition disabled:opacity-50 "
          >
            <Save className="h-4 w-4" />
            {saveMut.isPending || activateMut.isPending ? 'Guardando...' : 'Guardar configuración'}
          </button>
        </div>
      )}

      {/* Test send */}
      {isConfigured && (
        <div className="rounded-2xl border border-border bg-card p-6  space-y-4">
          <div>
            <h3 className="text-sm font-semibold text-foreground">Probar envío</h3>
            <p className="text-xs text-muted-foreground mt-0.5">Envía un correo de prueba para verificar la configuración</p>
          </div>
          <div className="flex gap-2">
            <input
              type="email"
              value={testEmail}
              onChange={(e) => setTestEmail(e.target.value)}
              placeholder="correo@ejemplo.com"
              className={cn(inputCls, 'h-10')}
            />
            <button
              onClick={handleTest}
              disabled={testMut.isPending}
              className="flex shrink-0 items-center gap-1.5 rounded-lg bg-gray-900 px-4 py-2 text-sm font-medium text-white hover:bg-gray-800 transition disabled:opacity-50 "
            >
              <Send className="h-4 w-4" />
              {testMut.isPending ? 'Enviando...' : 'Enviar prueba'}
            </button>
          </div>
          {testResult && (
            <div className={cn(
              'flex items-center gap-2 rounded-lg border px-4 py-3 text-sm',
              testResult.ok
                ? 'border-emerald-200 bg-emerald-50 text-emerald-700'
                : 'border-red-200 bg-red-50 text-red-700',
            )}>
              {testResult.ok ? <CheckCircle2 className="h-4 w-4" /> : <XCircle className="h-4 w-4" />}
              {testResult.ok ? 'Correo enviado correctamente' : testResult.error}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

/* ─── Templates Tab ─────────────────────────────────────────────────────── */

function TemplatesTab() {
  const { data: templates, isLoading } = useEmailTemplates()
  const [selectedId, setSelectedId] = useState<string | null>(null)

  const selected = templates?.find((t) => t.id === selectedId)

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="h-6 w-6 animate-spin rounded-full border-2 border-primary border-t-transparent" />
      </div>
    )
  }

  if (selected) {
    return <TemplateEditor template={selected} onBack={() => setSelectedId(null)} />
  }

  if (!templates || templates.length === 0) {
    return (
      <div className="rounded-2xl border border-dashed border-border bg-card p-10 text-center">
        <Mail className="h-10 w-10 text-muted-foreground/60 mx-auto" />
        <p className="text-sm font-semibold text-foreground mt-3">No hay plantillas de correo</p>
        <p className="text-xs text-muted-foreground mt-1 max-w-sm mx-auto">
          Tu tenant aún no tiene plantillas seedadas. Contactá a un administrador o vuelve a iniciar sesión para que el sistema las clone automáticamente.
        </p>
      </div>
    )
  }

  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
      {templates.map((tpl) => (
        <button
          key={tpl.id}
          onClick={() => setSelectedId(tpl.id)}
          className="text-left bg-card rounded-2xl border border-border p-5 hover:border-primary/50 hover:shadow-md transition-all"
        >
          <div className="flex items-center gap-3 mb-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-primary/15">
              <Mail className="h-5 w-5 text-primary" />
            </div>
            <div>
              <p className="font-semibold text-foreground text-sm">{tpl.slug.replace(/_/g, ' ')}</p>
              <p className={`text-xs ${tpl.is_active ? 'text-green-600' : 'text-muted-foreground'}`}>
                {tpl.is_active ? 'Activa' : 'Inactiva'}
              </p>
            </div>
          </div>
          <p className="text-xs text-muted-foreground line-clamp-2">{tpl.description}</p>
          <p className="text-xs text-muted-foreground mt-2 truncate">Asunto: {tpl.subject}</p>
        </button>
      ))}
    </div>
  )
}

/* ─── Template Editor ────────────────────────────────────────────────────── */

function TemplateEditor({ template, onBack }: { template: EmailTemplate; onBack: () => void }) {
  const [subject, setSubject] = useState(template.subject)
  const [htmlBody, setHtmlBody] = useState(template.html_body)
  const [description, setDescription] = useState(template.description ?? '')
  const [isActive, setIsActive] = useState(template.is_active)
  const [showPreview, setShowPreview] = useState(false)

  const update = useUpdateEmailTemplate()
  const testSend = useTestEmailTemplate()
  const currentUser = useAuthStore((s) => s.user)

  const isDirty =
    subject !== template.subject ||
    htmlBody !== template.html_body ||
    description !== (template.description ?? '') ||
    isActive !== template.is_active

  const handleSave = () => {
    update.mutate({
      id: template.id,
      data: { subject, html_body: htmlBody, description, is_active: isActive },
    })
  }

  const handleTest = () => {
    const recipient = currentUser?.email
    if (!recipient) return
    testSend.mutate({ id: template.id, to: recipient })
  }

  const previewHtml = htmlBody
    .replace(/\$user_name/g, 'Usuario de Prueba')
    .replace(/\$user_email/g, 'usuario@example.com')
    .replace(/\$link/g, '#')
    .replace(/\$app_name/g, 'TraceLog')
    .replace(/\$tenant_name/g, 'default')
    .replace(/<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>/gi, '')
    .replace(/\bon\w+\s*=\s*(?:"[^"]*"|'[^']*'|[^\s>]*)/gi, '')

  return (
    <div>
      <button
        onClick={onBack}
        className="flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground mb-4"
      >
        <ChevronLeft className="h-4 w-4" />
        Volver
      </button>

      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-lg font-semibold text-foreground">{template.slug.replace(/_/g, ' ')}</h2>
          <p className="text-sm text-muted-foreground">{template.description}</p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowPreview((p) => !p)}
            className="flex items-center gap-1.5 rounded-xl border border-border px-3 py-2 text-sm text-muted-foreground hover:bg-muted"
          >
            {showPreview ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
            {showPreview ? 'Editor' : 'Vista previa'}
          </button>
          <button
            onClick={handleTest}
            disabled={testSend.isPending}
            className="flex items-center gap-1.5 rounded-xl border border-border px-3 py-2 text-sm text-muted-foreground hover:bg-muted disabled:opacity-50"
            title={`Enviar a ${currentUser?.email}`}
          >
            <Send className="h-4 w-4" />
            {testSend.isPending ? 'Enviando...' : 'Enviar prueba'}
          </button>
          <button
            onClick={handleSave}
            disabled={!isDirty || update.isPending}
            className="flex items-center gap-1.5 rounded-xl bg-primary px-4 py-2 text-sm font-semibold text-white hover:bg-primary/90 disabled:opacity-50"
          >
            <Save className="h-4 w-4" />
            {update.isPending ? 'Guardando...' : 'Guardar'}
          </button>
        </div>
      </div>

      {testSend.isSuccess && (
        <div className="mb-4 rounded-xl bg-green-50 border border-green-200 px-4 py-3 text-sm text-green-700">
          Correo de prueba enviado a {currentUser?.email}
        </div>
      )}
      {testSend.isError && (
        <div className="mb-4 rounded-xl bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-700">
          Error al enviar: {testSend.error?.message || 'Error desconocido'}
        </div>
      )}
      {update.isSuccess && (
        <div className="mb-4 rounded-xl bg-green-50 border border-green-200 px-4 py-3 text-sm text-green-700">
          Plantilla actualizada
        </div>
      )}
      {update.isError && (
        <div className="mb-4 rounded-xl bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-700">
          Error al guardar: {update.error?.message || 'Error desconocido'}
        </div>
      )}

      <div className="bg-card rounded-2xl border border-border overflow-hidden">
        {showPreview ? (
          <div className="p-6">
            <p className="text-xs text-muted-foreground mb-2">Vista previa del correo:</p>
            <div
              className="border border-border rounded-xl p-4"
              dangerouslySetInnerHTML={{ __html: previewHtml }}
            />
          </div>
        ) : (
          <div className="divide-y divide-slate-100">
            <div className="p-4 flex items-center gap-4">
              <label className="text-sm font-medium text-foreground w-24 shrink-0">Activa</label>
              <button
                onClick={() => setIsActive((p) => !p)}
                className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                  isActive ? 'bg-primary' : 'bg-slate-300'
                }`}
              >
                <span
                  className={`inline-block h-4 w-4 transform rounded-full bg-card transition-transform ${
                    isActive ? 'translate-x-6' : 'translate-x-1'
                  }`}
                />
              </button>
            </div>
            <div className="p-4 flex items-center gap-4">
              <label className="text-sm font-medium text-foreground w-24 shrink-0">Descripción</label>
              <input
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                className="flex-1 rounded-xl border border-border bg-card px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
              />
            </div>
            <div className="p-4 flex items-center gap-4">
              <label className="text-sm font-medium text-foreground w-24 shrink-0">Asunto</label>
              <input
                value={subject}
                onChange={(e) => setSubject(e.target.value)}
                className="flex-1 rounded-xl border border-border bg-card px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
              />
            </div>
            <div className="p-4">
              <label className="text-sm font-medium text-foreground mb-2 block">Cuerpo HTML</label>
              <textarea
                value={htmlBody}
                onChange={(e) => setHtmlBody(e.target.value)}
                rows={20}
                className="w-full rounded-xl border border-border bg-muted px-4 py-3 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-ring"
              />
              <p className="text-xs text-muted-foreground mt-2">
                Variables disponibles: $user_name, $user_email, $link, $app_name, $tenant_name
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
