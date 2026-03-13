import { useState, useEffect } from 'react'
import { Mail, Send, Save, Eye, EyeOff, ChevronLeft, Server, CheckCircle2, XCircle, Loader2 } from 'lucide-react'
import {
  useEmailTemplates,
  useUpdateEmailTemplate,
  useTestEmailTemplate,
  useEmailConfig,
  useUpdateEmailConfig,
  useTestSmtpConnection,
} from '@/hooks/useUsers'
import { useAuthStore } from '@/store/auth'
import type { EmailTemplate } from '@/types/auth'

type Tab = 'templates' | 'smtp'

export function EmailTemplatesPage() {
  const [tab, setTab] = useState<Tab>('templates')

  return (
    <div className="p-6 max-w-6xl mx-auto">
      <h1 className="text-2xl font-bold text-slate-800 mb-6">Plantillas de correo</h1>

      {/* Tabs */}
      <div className="flex gap-1 mb-6 bg-slate-100 rounded-xl p-1 w-fit">
        <button
          onClick={() => setTab('templates')}
          className={`px-4 py-2 text-sm font-medium rounded-lg transition-colors ${
            tab === 'templates' ? 'bg-white text-slate-800 shadow-sm' : 'text-slate-500 hover:text-slate-700'
          }`}
        >
          <Mail className="h-4 w-4 inline-block mr-1.5 -mt-0.5" />
          Plantillas
        </button>
        <button
          onClick={() => setTab('smtp')}
          className={`px-4 py-2 text-sm font-medium rounded-lg transition-colors ${
            tab === 'smtp' ? 'bg-white text-slate-800 shadow-sm' : 'text-slate-500 hover:text-slate-700'
          }`}
        >
          <Server className="h-4 w-4 inline-block mr-1.5 -mt-0.5" />
          Configuración SMTP
        </button>
      </div>

      {tab === 'templates' ? <TemplatesTab /> : <SmtpConfigTab />}
    </div>
  )
}

/* ─── Templates Tab ──────────────────────────────────────────────────────── */

function TemplatesTab() {
  const { data: templates, isLoading } = useEmailTemplates()
  const [selectedId, setSelectedId] = useState<string | null>(null)

  const selected = templates?.find((t) => t.id === selectedId)

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="h-6 w-6 animate-spin rounded-full border-2 border-indigo-500 border-t-transparent" />
      </div>
    )
  }

  if (selected) {
    return <TemplateEditor template={selected} onBack={() => setSelectedId(null)} />
  }

  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
      {templates?.map((tpl) => (
        <button
          key={tpl.id}
          onClick={() => setSelectedId(tpl.id)}
          className="text-left bg-white rounded-2xl border border-slate-200 p-5 hover:border-indigo-300 hover:shadow-md transition-all"
        >
          <div className="flex items-center gap-3 mb-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-indigo-100">
              <Mail className="h-5 w-5 text-indigo-600" />
            </div>
            <div>
              <p className="font-semibold text-slate-800 text-sm">{tpl.slug.replace(/_/g, ' ')}</p>
              <p className={`text-xs ${tpl.is_active ? 'text-green-600' : 'text-slate-400'}`}>
                {tpl.is_active ? 'Activa' : 'Inactiva'}
              </p>
            </div>
          </div>
          <p className="text-xs text-slate-500 line-clamp-2">{tpl.description}</p>
          <p className="text-xs text-slate-400 mt-2 truncate">Asunto: {tpl.subject}</p>
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
  const { data: emailConfig } = useEmailConfig()

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
    const recipient = emailConfig?.test_email || currentUser?.email
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
        className="flex items-center gap-1 text-sm text-slate-500 hover:text-slate-700 mb-4"
      >
        <ChevronLeft className="h-4 w-4" />
        Volver
      </button>

      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-lg font-semibold text-slate-800">{template.slug.replace(/_/g, ' ')}</h2>
          <p className="text-sm text-slate-500">{template.description}</p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowPreview((p) => !p)}
            className="flex items-center gap-1.5 rounded-xl border border-slate-200 px-3 py-2 text-sm text-slate-600 hover:bg-slate-50"
          >
            {showPreview ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
            {showPreview ? 'Editor' : 'Vista previa'}
          </button>
          <button
            onClick={handleTest}
            disabled={testSend.isPending}
            className="flex items-center gap-1.5 rounded-xl border border-slate-200 px-3 py-2 text-sm text-slate-600 hover:bg-slate-50 disabled:opacity-50"
            title={emailConfig?.test_email ? `Enviar a ${emailConfig.test_email}` : `Enviar a ${currentUser?.email}`}
          >
            <Send className="h-4 w-4" />
            {testSend.isPending ? 'Enviando...' : 'Enviar prueba'}
          </button>
          <button
            onClick={handleSave}
            disabled={!isDirty || update.isPending}
            className="flex items-center gap-1.5 rounded-xl bg-indigo-600 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-700 disabled:opacity-50"
          >
            <Save className="h-4 w-4" />
            {update.isPending ? 'Guardando...' : 'Guardar'}
          </button>
        </div>
      </div>

      {testSend.isSuccess && (
        <div className="mb-4 rounded-xl bg-green-50 border border-green-200 px-4 py-3 text-sm text-green-700">
          Correo de prueba enviado a {testSend.data?.recipient || currentUser?.email}
        </div>
      )}

      {testSend.isError && (
        <div className="mb-4 rounded-xl bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-700">
          Error al enviar correo de prueba: {testSend.error?.message || 'Error desconocido'}
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

      <div className="bg-white rounded-2xl border border-slate-200 overflow-hidden">
        {showPreview ? (
          <div className="p-6">
            <p className="text-xs text-slate-400 mb-2">Vista previa del correo:</p>
            <div
              className="border border-slate-100 rounded-xl p-4"
              dangerouslySetInnerHTML={{ __html: previewHtml }}
            />
          </div>
        ) : (
          <div className="divide-y divide-slate-100">
            <div className="p-4 flex items-center gap-4">
              <label className="text-sm font-medium text-slate-700 w-24 shrink-0">Activa</label>
              <button
                onClick={() => setIsActive((p) => !p)}
                className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                  isActive ? 'bg-indigo-600' : 'bg-slate-300'
                }`}
              >
                <span
                  className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                    isActive ? 'translate-x-6' : 'translate-x-1'
                  }`}
                />
              </button>
            </div>
            <div className="p-4 flex items-center gap-4">
              <label className="text-sm font-medium text-slate-700 w-24 shrink-0">Descripción</label>
              <input
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                className="flex-1 rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400"
              />
            </div>
            <div className="p-4 flex items-center gap-4">
              <label className="text-sm font-medium text-slate-700 w-24 shrink-0">Asunto</label>
              <input
                value={subject}
                onChange={(e) => setSubject(e.target.value)}
                className="flex-1 rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400"
              />
            </div>
            <div className="p-4">
              <label className="text-sm font-medium text-slate-700 mb-2 block">Cuerpo HTML</label>
              <textarea
                value={htmlBody}
                onChange={(e) => setHtmlBody(e.target.value)}
                rows={20}
                className="w-full rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-indigo-400"
              />
              <p className="text-xs text-slate-400 mt-2">
                Variables disponibles: $user_name, $user_email, $link, $app_name, $tenant_name
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

/* ─── SMTP Config Tab ────────────────────────────────────────────────────── */

function SmtpConfigTab() {
  const { data: config, isLoading } = useEmailConfig()
  const updateConfig = useUpdateEmailConfig()
  const testConnection = useTestSmtpConnection()

  const [smtpHost, setSmtpHost] = useState('')
  const [smtpPort, setSmtpPort] = useState(587)
  const [smtpUser, setSmtpUser] = useState('')
  const [smtpPassword, setSmtpPassword] = useState('')
  const [smtpFrom, setSmtpFrom] = useState('')
  const [smtpUseTls, setSmtpUseTls] = useState(true)
  const [adminEmail, setAdminEmail] = useState('')
  const [testEmail, setTestEmail] = useState('')
  const [showPassword, setShowPassword] = useState(false)

  // Sync form with loaded config
  useEffect(() => {
    if (config) {
      setSmtpHost(config.smtp_host ?? '')
      setSmtpPort(config.smtp_port ?? 587)
      setSmtpUser(config.smtp_user ?? '')
      setSmtpPassword(config.smtp_password ?? '')
      setSmtpFrom(config.smtp_from ?? '')
      setSmtpUseTls(config.smtp_use_tls ?? true)
      setAdminEmail(config.admin_email ?? '')
      setTestEmail(config.test_email ?? '')
    }
  }, [config])

  const isDirty =
    smtpHost !== (config?.smtp_host ?? '') ||
    smtpPort !== (config?.smtp_port ?? 587) ||
    smtpUser !== (config?.smtp_user ?? '') ||
    smtpPassword !== (config?.smtp_password ?? '') ||
    smtpFrom !== (config?.smtp_from ?? '') ||
    smtpUseTls !== (config?.smtp_use_tls ?? true) ||
    adminEmail !== (config?.admin_email ?? '') ||
    testEmail !== (config?.test_email ?? '')

  const handleSave = () => {
    updateConfig.mutate({
      smtp_host: smtpHost || undefined,
      smtp_port: smtpPort,
      smtp_user: smtpUser || undefined,
      smtp_password: smtpPassword || undefined,
      smtp_from: smtpFrom || undefined,
      smtp_use_tls: smtpUseTls,
      admin_email: adminEmail || undefined,
      test_email: testEmail || undefined,
    })
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="h-6 w-6 animate-spin rounded-full border-2 border-indigo-500 border-t-transparent" />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* SMTP Server */}
      <div className="bg-white rounded-2xl border border-slate-200 overflow-hidden">
        <div className="px-5 py-4 border-b border-slate-100">
          <h3 className="text-sm font-semibold text-slate-800">Servidor SMTP</h3>
          <p className="text-xs text-slate-500 mt-0.5">Configura el servidor de correo saliente para este tenant</p>
        </div>
        <div className="divide-y divide-slate-100">
          <div className="p-4 flex items-center gap-4">
            <label className="text-sm font-medium text-slate-700 w-32 shrink-0">Host</label>
            <input
              value={smtpHost}
              onChange={(e) => setSmtpHost(e.target.value)}
              placeholder="smtp.ejemplo.com"
              className="flex-1 rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400"
            />
          </div>
          <div className="p-4 flex items-center gap-4">
            <label className="text-sm font-medium text-slate-700 w-32 shrink-0">Puerto</label>
            <input
              type="number"
              value={smtpPort}
              onChange={(e) => setSmtpPort(Number(e.target.value))}
              className="w-28 rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400"
            />
          </div>
          <div className="p-4 flex items-center gap-4">
            <label className="text-sm font-medium text-slate-700 w-32 shrink-0">Usuario</label>
            <input
              value={smtpUser}
              onChange={(e) => setSmtpUser(e.target.value)}
              placeholder="usuario@ejemplo.com"
              className="flex-1 rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400"
            />
          </div>
          <div className="p-4 flex items-center gap-4">
            <label className="text-sm font-medium text-slate-700 w-32 shrink-0">Contraseña</label>
            <div className="flex-1 relative">
              <input
                type={showPassword ? 'text' : 'password'}
                value={smtpPassword}
                onChange={(e) => setSmtpPassword(e.target.value)}
                placeholder="••••••••"
                className="w-full rounded-xl border border-slate-200 bg-white px-3 py-2 pr-10 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400"
              />
              <button
                type="button"
                onClick={() => setShowPassword((p) => !p)}
                className="absolute right-2 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
              >
                {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
              </button>
            </div>
          </div>
          <div className="p-4 flex items-center gap-4">
            <label className="text-sm font-medium text-slate-700 w-32 shrink-0">Email remitente</label>
            <input
              value={smtpFrom}
              onChange={(e) => setSmtpFrom(e.target.value)}
              placeholder="noreply@trace.app"
              className="flex-1 rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400"
            />
          </div>
          <div className="p-4 flex items-center gap-4">
            <label className="text-sm font-medium text-slate-700 w-32 shrink-0">Usar TLS</label>
            <button
              onClick={() => setSmtpUseTls((p) => !p)}
              className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                smtpUseTls ? 'bg-indigo-600' : 'bg-slate-300'
              }`}
            >
              <span
                className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                  smtpUseTls ? 'translate-x-6' : 'translate-x-1'
                }`}
              />
            </button>
          </div>
        </div>
      </div>

      {/* System Emails */}
      <div className="bg-white rounded-2xl border border-slate-200 overflow-hidden">
        <div className="px-5 py-4 border-b border-slate-100">
          <h3 className="text-sm font-semibold text-slate-800">Correos de sistema</h3>
          <p className="text-xs text-slate-500 mt-0.5">Configuración de correos administrativos y de prueba</p>
        </div>
        <div className="divide-y divide-slate-100">
          <div className="p-4 flex items-center gap-4">
            <label className="text-sm font-medium text-slate-700 w-32 shrink-0">Email admin (CC)</label>
            <div className="flex-1">
              <input
                value={adminEmail}
                onChange={(e) => setAdminEmail(e.target.value)}
                placeholder="admin@ejemplo.com"
                className="w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400"
              />
              <p className="text-xs text-slate-400 mt-1">Se agregará en CC en correos del sistema (invitaciones, resets)</p>
            </div>
          </div>
          <div className="p-4 flex items-center gap-4">
            <label className="text-sm font-medium text-slate-700 w-32 shrink-0">Email de prueba</label>
            <div className="flex-1">
              <input
                value={testEmail}
                onChange={(e) => setTestEmail(e.target.value)}
                placeholder="test@ejemplo.com"
                className="w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400"
              />
              <p className="text-xs text-slate-400 mt-1">Destinatario por defecto al enviar correos de prueba desde plantillas</p>
            </div>
          </div>
        </div>
      </div>

      {/* Actions */}
      <div className="flex items-center gap-3">
        <button
          onClick={() => testConnection.mutate()}
          disabled={testConnection.isPending}
          className="flex items-center gap-1.5 rounded-xl border border-slate-200 px-4 py-2.5 text-sm font-medium text-slate-600 hover:bg-slate-50 disabled:opacity-50"
        >
          {testConnection.isPending ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <Server className="h-4 w-4" />
          )}
          {testConnection.isPending ? 'Probando...' : 'Probar conexión'}
        </button>
        <button
          onClick={handleSave}
          disabled={!isDirty || updateConfig.isPending}
          className="flex items-center gap-1.5 rounded-xl bg-indigo-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-indigo-700 disabled:opacity-50"
        >
          <Save className="h-4 w-4" />
          {updateConfig.isPending ? 'Guardando...' : 'Guardar configuración'}
        </button>
      </div>

      {/* Connection test feedback */}
      {testConnection.isSuccess && testConnection.data && (
        <div
          className={`rounded-xl border px-4 py-3 text-sm flex items-center gap-2 ${
            testConnection.data.ok
              ? 'bg-green-50 border-green-200 text-green-700'
              : 'bg-red-50 border-red-200 text-red-700'
          }`}
        >
          {testConnection.data.ok ? (
            <>
              <CheckCircle2 className="h-4 w-4 shrink-0" />
              Conexión SMTP exitosa
            </>
          ) : (
            <>
              <XCircle className="h-4 w-4 shrink-0" />
              Error de conexión: {testConnection.data.error}
            </>
          )}
        </div>
      )}

      {updateConfig.isSuccess && (
        <div className="rounded-xl bg-green-50 border border-green-200 px-4 py-3 text-sm text-green-700 flex items-center gap-2">
          <CheckCircle2 className="h-4 w-4 shrink-0" />
          Configuración guardada
        </div>
      )}

      {/* Info box */}
      {config && !config.id && (
        <div className="rounded-xl bg-blue-50 border border-blue-200 px-4 py-3 text-sm text-blue-700">
          Mostrando configuración por defecto del servidor. Guarda para personalizar la configuración de este tenant.
        </div>
      )}
    </div>
  )
}
