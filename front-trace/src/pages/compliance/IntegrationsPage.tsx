import { useState, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Satellite, FileCheck, Key, Loader2, CheckCircle2, XCircle, Eye, EyeOff, Save, Zap } from 'lucide-react'
import { authFetch } from '@/lib/auth-fetch'
import { useToast } from '@/store/toast'
import { cn } from '@/lib/utils'

const BASE = import.meta.env.VITE_API_URL ?? 'http://localhost:9000'

interface Integration {
  provider: string
  display_name: string
  description: string
  fields: string[]
  is_configured: boolean
  is_active: boolean
  credentials: Record<string, string>
  updated_at: string | null
}

async function apiRequest<T>(path: string, opts?: RequestInit): Promise<T> {
  const r = await authFetch(`${BASE}${path}`, opts)
  if (!r.ok) throw new Error((await r.json().catch(() => ({}))).detail || r.statusText)
  return r.json()
}

function useIntegrations() {
  return useQuery<Integration[]>({
    queryKey: ['compliance', 'integrations'],
    queryFn: () => apiRequest('/api/v1/compliance/integrations/'),
  })
}

function useUpdateIntegration() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ provider, data }: { provider: string; data: Record<string, string> }) =>
      apiRequest(`/api/v1/compliance/integrations/${provider}`, { method: 'PATCH', body: JSON.stringify(data) }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['compliance', 'integrations'] }),
  })
}

function useTestIntegration() {
  return useMutation({
    mutationFn: (provider: string) =>
      apiRequest<{ ok: boolean; message?: string; error?: string }>(`/api/v1/compliance/integrations/${provider}/test`, { method: 'POST' }),
  })
}

function ProviderIcon({ provider, className }: { provider: string; className?: string }) {
  if (provider === 'gfw') return <Satellite className={className} />
  if (provider === 'traces_nt') return <FileCheck className={className} />
  return <Key className={className} />
}

function IntegrationCard({ integration }: { integration: Integration }) {
  const toast = useToast()
  const updateMut = useUpdateIntegration()
  const testMut = useTestIntegration()
  const [form, setForm] = useState<Record<string, string>>({})
  const [show, setShow] = useState<Record<string, boolean>>({})
  const [testResult, setTestResult] = useState<{ ok: boolean; message: string } | null>(null)

  const handleChange = (field: string, value: string) => setForm(f => ({ ...f, [field]: value }))

  // Seed `env` with the current value so the first save sends an explicit selection.
  useEffect(() => {
    if (integration.fields.includes('env') && form.env === undefined) {
      const current = integration.credentials.env ?? 'acceptance'
      setForm(f => ({ ...f, env: current }))
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [integration.provider])

  const handleSave = async () => {
    try {
      await updateMut.mutateAsync({ provider: integration.provider, data: form })
      toast.success(`Credenciales de ${integration.display_name} guardadas`)
      setForm({})
    } catch (e: any) {
      toast.error(e.message || 'Error al guardar')
    }
  }

  const handleTest = async () => {
    setTestResult(null)
    const result = await testMut.mutateAsync(integration.provider)
    setTestResult({ ok: result.ok, message: result.message || result.error || '' })
  }

  const fieldLabel: Record<string, string> = {
    api_key: 'API Key',
    username: 'Usuario',
    auth_key: 'Auth Key',
    env: 'Ambiente',
    client_id: 'Web Service Client ID',
  }

  return (
    <div className="rounded-2xl border border-border bg-card overflow-hidden">
      <div className="px-6 py-4 border-b border-border flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="h-10 w-10 rounded-xl bg-primary/10 flex items-center justify-center">
            <ProviderIcon provider={integration.provider} className="h-5 w-5 text-primary" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-foreground">{integration.display_name}</h3>
            <p className="text-xs text-muted-foreground">{integration.description}</p>
          </div>
        </div>
        <div>
          {integration.is_configured ? (
            <span className="inline-flex items-center gap-1 rounded-full bg-emerald-50 px-2.5 py-0.5 text-[10px] font-semibold text-emerald-700">
              <CheckCircle2 className="h-3 w-3" /> Configurado
            </span>
          ) : (
            <span className="inline-flex items-center gap-1 rounded-full bg-secondary px-2.5 py-0.5 text-[10px] font-semibold text-muted-foreground">
              No configurado
            </span>
          )}
        </div>
      </div>

      <div className="px-6 py-5 space-y-4">
        {integration.fields.map(field => {
          if (field === 'env') {
            const currentEnv = form[field] ?? integration.credentials.env ?? 'acceptance'
            return (
              <div key={field}>
                <label className="text-xs font-semibold text-muted-foreground">{fieldLabel[field] || field}</label>
                <select
                  value={currentEnv}
                  onChange={e => handleChange(field, e.target.value)}
                  className="w-full mt-1 rounded-xl border border-border bg-muted px-3 py-2.5 text-sm"
                >
                  <option value="acceptance">Acceptance (pruebas)</option>
                  <option value="production">Production</option>
                </select>
              </div>
            )
          }
          return (
            <div key={field}>
              <label className="text-xs font-semibold text-muted-foreground">{fieldLabel[field] || field}</label>
              <div className="relative mt-1">
                <input
                  type={show[field] ? 'text' : 'password'}
                  value={form[field] ?? ''}
                  onChange={e => handleChange(field, e.target.value)}
                  placeholder={integration.credentials[field] || `Ingresa ${fieldLabel[field] || field}`}
                  className="w-full rounded-xl border border-border bg-muted px-3 py-2.5 text-sm font-mono pr-10"
                />
                <button
                  type="button"
                  onClick={() => setShow(s => ({ ...s, [field]: !s[field] }))}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                >
                  {show[field] ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </button>
              </div>
              {integration.credentials[field] && !form[field] && (
                <p className="text-[10px] text-muted-foreground mt-1">Actual: {integration.credentials[field]}</p>
              )}
            </div>
          )
        })}

        {testResult && (
          <div className={cn('flex items-center gap-2 rounded-lg px-3 py-2 text-xs', testResult.ok ? 'bg-emerald-50 text-emerald-700' : 'bg-red-50 text-red-700')}>
            {testResult.ok ? <CheckCircle2 className="h-4 w-4" /> : <XCircle className="h-4 w-4" />}
            {testResult.message}
          </div>
        )}

        <div className="flex justify-end gap-2 pt-2 border-t border-border">
          {integration.is_configured && (
            <button
              onClick={handleTest}
              disabled={testMut.isPending}
              className="inline-flex items-center gap-1.5 rounded-lg border border-border px-3 py-2 text-xs font-semibold text-muted-foreground hover:bg-muted disabled:opacity-50"
            >
              {testMut.isPending ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Zap className="h-3.5 w-3.5" />}
              Probar conexión
            </button>
          )}
          <button
            onClick={handleSave}
            disabled={updateMut.isPending || Object.keys(form).length === 0}
            className="inline-flex items-center gap-1.5 rounded-lg bg-primary px-4 py-2 text-xs font-semibold text-white hover:bg-primary/90 disabled:opacity-50"
          >
            {updateMut.isPending ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Save className="h-3.5 w-3.5" />}
            Guardar
          </button>
        </div>
      </div>
    </div>
  )
}

export function ComplianceIntegrationsPage() {
  const { data: integrations = [], isLoading } = useIntegrations()

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-foreground flex items-center gap-2">
          <Key className="h-6 w-6 text-primary" /> Integraciones de Cumplimiento
        </h1>
        <p className="text-sm text-muted-foreground mt-1">
          Configura las API keys de servicios externos requeridos para EUDR y otros marcos normativos.
        </p>
      </div>

      {isLoading ? (
        <div className="flex justify-center py-20"><Loader2 className="h-6 w-6 animate-spin text-muted-foreground" /></div>
      ) : (
        <div className="space-y-4">
          {integrations.map(integ => (
            <IntegrationCard key={integ.provider} integration={integ} />
          ))}
        </div>
      )}

      <div className="rounded-xl bg-blue-50 border border-blue-200 p-4 text-xs text-blue-800">
        <p className="font-semibold mb-1">💡 Cómo obtener las credenciales:</p>
        <ul className="space-y-1 ml-4 list-disc">
          <li><strong>Global Forest Watch</strong>: gratis en <a href="https://www.globalforestwatch.org/my-gfw/" target="_blank" rel="noreferrer" className="underline">globalforestwatch.org/my-gfw</a> → genera API key</li>
          <li><strong>EU TRACES NT</strong>: registra tu empresa como operador en <a href="https://webgate.ec.europa.eu/tracesnt/" target="_blank" rel="noreferrer" className="underline">webgate.ec.europa.eu/tracesnt</a> → la UE asigna usuario y auth key</li>
        </ul>
      </div>
    </div>
  )
}
