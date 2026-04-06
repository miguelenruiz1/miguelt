import { useState, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  Sparkles, Eye, EyeOff, Zap, Loader2, CheckCircle, XCircle, Trash2,
  Activity, DollarSign, TrendingUp, Building2, Bell, Settings, BarChart3, Shield,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { useAuthStore } from '@/store/auth'
import { useToast } from '@/store/toast'

const AI_API = import.meta.env.VITE_API_URL ?? 'http://localhost:9000'

function subRequest<T>(path: string, opts?: RequestInit): Promise<T> {
  const token = useAuthStore.getState().accessToken
  return fetch(`${AI_API}${path}`, {
    ...opts,
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...opts?.headers,
    },
  }).then(async r => {
    if (!r.ok) throw { status: r.status, ...(await r.json().catch(() => ({}))) }
    return r.json()
  })
}

// ─── Types ───────────────────────────────────────────────────────────────────

interface AISettings {
  anthropic_api_key_masked: string
  anthropic_api_key_set: boolean
  anthropic_model_analysis: string
  anthropic_model_premium: string
  anthropic_max_tokens: number
  anthropic_enabled: boolean
  global_daily_limit_free: number
  global_daily_limit_starter: number
  global_daily_limit_professional: number
  global_daily_limit_enterprise: number
  cache_ttl_minutes: number
  cache_enabled: boolean
  estimated_cost_per_analysis_usd: number
  alert_monthly_cost_usd: number
  current_month_calls: number
  current_month_cost_usd: number
  pnl_analysis_enabled: boolean
  updated_at: string | null
}

interface TestResult { ok: boolean; latency_ms?: number; model?: string; error?: string }
interface AIMetrics {
  current_month: {
    total_calls: number
    total_cost_usd: number
    calls_by_tenant: Array<{ tenant_id: string; calls: number; cost_usd: number }>
    calls_by_module: Record<string, number>
    calls_by_day: Array<{ date: string; calls: number }>
  }
  projected_month_cost_usd: number
  alert_threshold_usd: number
  alert_triggered: boolean
}

// ─── Hooks ───────────────────────────────────────────────────────────────────

function useAISettings() {
  return useQuery<AISettings>({ queryKey: ['platform', 'ai', 'settings'], queryFn: () => subRequest('/api/v1/settings') })
}
function useAIMetrics() {
  return useQuery<AIMetrics>({ queryKey: ['platform', 'ai', 'metrics'], queryFn: () => subRequest('/api/v1/metrics'), staleTime: 30_000 })
}
function useUpdateAISettings() {
  const qc = useQueryClient()
  return useMutation({ mutationFn: (data: Partial<AISettings>) => subRequest('/api/v1/settings', { method: 'POST', body: JSON.stringify(data) }), onSuccess: () => qc.invalidateQueries({ queryKey: ['platform', 'ai'] }) })
}
function useUpdateApiKey() {
  const qc = useQueryClient()
  return useMutation({ mutationFn: (api_key: string) => subRequest('/api/v1/settings/api-key', { method: 'PATCH', body: JSON.stringify({ api_key }) }), onSuccess: () => qc.invalidateQueries({ queryKey: ['platform', 'ai'] }) })
}
function useTestConnection() {
  return useMutation<TestResult>({ mutationFn: () => subRequest('/api/v1/settings/test', { method: 'POST' }) })
}
function useClearCache() {
  return useMutation({ mutationFn: () => subRequest('/api/v1/metrics/cache', { method: 'DELETE', body: JSON.stringify({ confirm: true }) }) })
}

interface AuditEntry {
  timestamp: string
  superuser_id: string
  superuser_email: string
  superuser_tenant: string
  target_tenant: string
  action: string
  resource: string | null
}
interface AuditResponse { items: AuditEntry[]; total: number; month: string }
function useCrossTenantAudit(month?: string) {
  const m = month || new Date().toISOString().slice(0, 7)
  return useQuery<AuditResponse>({
    queryKey: ['platform', 'ai', 'audit', m],
    queryFn: () => subRequest(`/api/v1/settings/audit/cross-tenant?month=${m}&limit=200`),
    staleTime: 15_000,
  })
}

// ─── Tab: Configuración ──────────────────────────────────────────────────────

function ConfigTab({ settings }: { settings: AISettings }) {
  const toast = useToast()
  const updateMut = useUpdateAISettings()
  const keyMut = useUpdateApiKey()
  const testMut = useTestConnection()
  const cacheMut = useClearCache()

  const [newKey, setNewKey] = useState('')
  const [showKey, setShowKey] = useState(false)
  const [model, setModel] = useState(settings.anthropic_model_analysis)
  const [maxTokens, setMaxTokens] = useState(settings.anthropic_max_tokens)
  const [enabled, setEnabled] = useState(settings.anthropic_enabled)
  const [pnlEnabled, setPnlEnabled] = useState(settings.pnl_analysis_enabled)
  const [cacheEnabled, setCacheEnabled] = useState(settings.cache_enabled)
  const [cacheTtl, setCacheTtl] = useState(settings.cache_ttl_minutes)
  const [limits, setLimits] = useState({
    free: settings.global_daily_limit_free,
    starter: settings.global_daily_limit_starter,
    professional: settings.global_daily_limit_professional,
    enterprise: settings.global_daily_limit_enterprise,
  })
  const [alertCost, setAlertCost] = useState(settings.alert_monthly_cost_usd)

  useEffect(() => {
    setModel(settings.anthropic_model_analysis)
    setMaxTokens(settings.anthropic_max_tokens)
    setEnabled(settings.anthropic_enabled)
    setPnlEnabled(settings.pnl_analysis_enabled)
    setCacheEnabled(settings.cache_enabled)
    setCacheTtl(settings.cache_ttl_minutes)
    setAlertCost(settings.alert_monthly_cost_usd)
    setLimits({
      free: settings.global_daily_limit_free,
      starter: settings.global_daily_limit_starter,
      professional: settings.global_daily_limit_professional,
      enterprise: settings.global_daily_limit_enterprise,
    })
  }, [settings])

  function handleSaveAll() {
    updateMut.mutate({
      anthropic_model_analysis: model,
      anthropic_max_tokens: maxTokens,
      anthropic_enabled: enabled,
      pnl_analysis_enabled: pnlEnabled,
      cache_enabled: cacheEnabled,
      cache_ttl_minutes: cacheTtl,
      global_daily_limit_free: limits.free,
      global_daily_limit_starter: limits.starter,
      global_daily_limit_professional: limits.professional,
      global_daily_limit_enterprise: limits.enterprise,
      alert_monthly_cost_usd: alertCost,
    }, { onSuccess: () => toast.success('Configuración guardada') })
  }

  function handleSaveKey() {
    if (!newKey.trim()) return
    keyMut.mutate(newKey.trim(), { onSuccess: () => { toast.success('API key guardada'); setNewKey('') } })
  }

  return (
    <div className="space-y-6">
      {/* Provider Card */}
      <div className="rounded-xl border border-border bg-card overflow-hidden">
        <div className="flex items-center justify-between px-6 py-4 border-b border-border">
          <div className="flex items-center gap-3">
            <div className="h-10 w-10 rounded-xl bg-orange-100 flex items-center justify-center"><span className="text-lg">🤖</span></div>
            <div>
              <h3 className="text-sm font-bold text-foreground">Anthropic Claude</h3>
              <p className="text-xs text-muted-foreground">Proveedor principal de IA</p>
            </div>
          </div>
          <span className={cn('rounded-full px-2.5 py-0.5 text-xs font-bold', enabled ? 'bg-emerald-100 text-emerald-700' : 'bg-secondary text-muted-foreground')}>
            {enabled ? 'Activo' : 'Inactivo'}
          </span>
        </div>
        <div className="px-6 py-5 space-y-5">
          {/* API Key */}
          <div className="space-y-2">
            <label className="text-xs font-semibold text-muted-foreground">API Key</label>
            <div className="flex gap-2">
              <div className="relative flex-1">
                <input
                  type={showKey ? 'text' : 'password'}
                  value={newKey || settings.anthropic_api_key_masked}
                  onChange={e => setNewKey(e.target.value)}
                  onFocus={() => { if (!newKey) setNewKey('') }}
                  placeholder="sk-ant-api03-..."
                  className="w-full rounded-xl border border-border bg-muted px-3 py-2.5 text-sm font-mono pr-10 focus:border-primary/50 focus:outline-none focus:ring-2 focus:ring-ring/20"
                />
                <button onClick={() => setShowKey(v => !v)} className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-muted-foreground">
                  {showKey ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </button>
              </div>
              <button onClick={() => testMut.mutate()} disabled={testMut.isPending} className="flex items-center gap-1.5 rounded-xl border border-border px-3 py-2 text-sm font-semibold text-muted-foreground hover:bg-muted disabled:opacity-50">
                {testMut.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Zap className="h-4 w-4" />}
                Probar
              </button>
              <button onClick={handleSaveKey} disabled={!newKey.trim() || keyMut.isPending} className="rounded-xl bg-primary px-4 py-2 text-sm font-semibold text-white hover:bg-primary/90 disabled:opacity-50">
                Guardar
              </button>
            </div>
            {testMut.data && (
              <div className={cn('flex items-center gap-2 text-sm p-2.5 rounded-lg mt-1', testMut.data.ok ? 'bg-emerald-50 text-emerald-700' : 'bg-red-50 text-red-700')}>
                {testMut.data.ok ? <CheckCircle className="h-4 w-4" /> : <XCircle className="h-4 w-4" />}
                {testMut.data.ok ? `Conexión exitosa · ${testMut.data.latency_ms}ms · ${testMut.data.model}` : `Error: ${testMut.data.error}`}
              </div>
            )}
            <p className="text-[10px] text-muted-foreground">
              Obtén tu API key en <a href="https://console.anthropic.com" target="_blank" rel="noopener noreferrer" className="text-primary hover:underline">console.anthropic.com</a>
            </p>
          </div>

          {/* Model + tokens */}
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-muted-foreground">Modelo — Análisis estándar</label>
              <select value={model} onChange={e => setModel(e.target.value)} className="w-full rounded-xl border border-border bg-muted px-3 py-2.5 text-sm">
                <option value="claude-haiku-4-5-20251001">Claude Haiku 4.5 (recomendado)</option>
                <option value="claude-sonnet-4-6">Claude Sonnet 4.6 (más preciso)</option>
              </select>
              <p className="text-[10px] text-muted-foreground">Haiku: ~$0.003/análisis · Sonnet: ~$0.018</p>
            </div>
            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-muted-foreground">Max tokens respuesta</label>
              <input type="number" value={maxTokens} onChange={e => setMaxTokens(Number(e.target.value))} min={500} max={4000} className="w-full rounded-xl border border-border bg-muted px-3 py-2.5 text-sm" />
              <p className="text-[10px] text-muted-foreground">Recomendado: 1000</p>
            </div>
          </div>

          {/* Enable toggle */}
          <div className="flex items-center justify-between rounded-xl bg-muted px-4 py-3">
            <div>
              <p className="text-sm font-semibold text-foreground">IA habilitada globalmente</p>
              <p className="text-xs text-muted-foreground">Activa/desactiva toda la funcionalidad de IA</p>
            </div>
            <button onClick={() => setEnabled(v => !v)} className={cn('relative h-6 w-11 rounded-full transition-colors', enabled ? 'bg-emerald-500' : 'bg-slate-300')}>
              <span className={cn('absolute top-0.5 left-0.5 h-5 w-5 rounded-full bg-card shadow transition-transform', enabled ? 'translate-x-5' : 'translate-x-0')} />
            </button>
          </div>
        </div>
      </div>

      {/* Modules */}
      <div className="rounded-xl border border-border bg-card p-6">
        <h3 className="text-sm font-bold text-foreground mb-3">Módulos con IA</h3>
        <div className="flex items-center justify-between p-3 border rounded-lg">
          <div className="flex items-center gap-3">
            <div className="h-8 w-8 rounded-lg bg-violet-100 flex items-center justify-center"><TrendingUp className="h-4 w-4 text-violet-600" /></div>
            <div>
              <p className="text-sm font-medium">Análisis de Rentabilidad</p>
              <p className="text-xs text-muted-foreground">P&L con insights automáticos</p>
            </div>
          </div>
          <button onClick={() => setPnlEnabled(v => !v)} className={cn('relative h-6 w-11 rounded-full transition-colors', pnlEnabled ? 'bg-emerald-500' : 'bg-slate-300')}>
            <span className={cn('absolute top-0.5 left-0.5 h-5 w-5 rounded-full bg-card shadow transition-transform', pnlEnabled ? 'translate-x-5' : 'translate-x-0')} />
          </button>
        </div>
      </div>

      {/* Limits */}
      <div className="rounded-xl border border-border bg-card p-6">
        <h3 className="text-sm font-bold text-foreground mb-1">Límites diarios de análisis</h3>
        <p className="text-xs text-muted-foreground mb-4">Cuántos análisis IA puede hacer cada tenant por día según su plan</p>
        <div className="space-y-3">
          {([
            { plan: 'Free', key: 'free' as const, color: 'text-muted-foreground' },
            { plan: 'Starter', key: 'starter' as const, color: 'text-blue-600' },
            { plan: 'Professional', key: 'professional' as const, color: 'text-purple-600' },
            { plan: 'Enterprise', key: 'enterprise' as const, color: 'text-emerald-600' },
          ]).map(({ plan, key, color }) => (
            <div key={key} className="flex items-center justify-between">
              <label className={cn('text-sm font-medium', color)}>{plan}</label>
              <div className="flex items-center gap-2">
                <input type="number" value={limits[key]} onChange={e => setLimits(l => ({ ...l, [key]: Number(e.target.value) }))} min={-1} className="w-24 text-right rounded-lg border border-border bg-muted px-2 py-1.5 text-sm" />
                <span className="text-xs text-muted-foreground w-16">{limits[key] === -1 ? 'ilimitado' : '/ día'}</span>
              </div>
            </div>
          ))}
          <p className="text-[10px] text-muted-foreground">-1 = sin límite</p>
        </div>
      </div>

      {/* Cache */}
      <div className="rounded-xl border border-border bg-card p-6 space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <label className="text-sm font-semibold text-foreground">Cache habilitado</label>
            <p className="text-xs text-muted-foreground mt-0.5">Evita llamadas repetidas a la API</p>
          </div>
          <button onClick={() => setCacheEnabled(v => !v)} className={cn('relative h-6 w-11 rounded-full transition-colors', cacheEnabled ? 'bg-emerald-500' : 'bg-slate-300')}>
            <span className={cn('absolute top-0.5 left-0.5 h-5 w-5 rounded-full bg-card shadow transition-transform', cacheEnabled ? 'translate-x-5' : 'translate-x-0')} />
          </button>
        </div>
        <div className="space-y-1.5">
          <label className="text-xs font-semibold text-muted-foreground">TTL del cache (minutos)</label>
          <input type="number" value={cacheTtl} onChange={e => setCacheTtl(Number(e.target.value))} min={5} max={1440} className="w-32 rounded-lg border border-border bg-muted px-2 py-1.5 text-sm" />
        </div>
        <button onClick={() => cacheMut.mutate(undefined, { onSuccess: () => toast.success('Cache limpiado') })} disabled={cacheMut.isPending} className="flex items-center gap-2 rounded-xl border border-red-200 px-3 py-2 text-xs font-semibold text-red-600 hover:bg-red-50 disabled:opacity-50">
          <Trash2 className="h-3.5 w-3.5" /> Limpiar cache global
        </button>
      </div>

      {/* Alerts */}
      <div className="rounded-xl border border-border bg-card p-6 space-y-3">
        <h3 className="text-sm font-bold text-foreground">Alerta de costo mensual</h3>
        <div className="flex items-center gap-2">
          <label className="text-xs text-muted-foreground">Alertar cuando supere</label>
          <input type="number" value={alertCost} onChange={e => setAlertCost(Number(e.target.value))} min={1} className="w-24 rounded-lg border border-border bg-muted px-2 py-1.5 text-sm text-right" />
          <span className="text-xs text-muted-foreground">USD / mes</span>
        </div>
      </div>

      {/* Save */}
      <div className="flex justify-end">
        <button onClick={handleSaveAll} disabled={updateMut.isPending} className="flex items-center gap-2 rounded-xl bg-primary px-6 py-2.5 text-sm font-semibold text-white hover:bg-primary/90 disabled:opacity-50">
          {updateMut.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Settings className="h-4 w-4" />}
          Guardar configuración
        </button>
      </div>
    </div>
  )
}

// ─── Tab: Métricas ───────────────────────────────────────────────────────────

function MetricsTab() {
  const { data: metrics, isLoading } = useAIMetrics()

  if (isLoading || !metrics) {
    return <div className="space-y-4 animate-pulse">{[...Array(4)].map((_, i) => <div key={i} className="h-20 rounded-xl bg-muted" />)}</div>
  }

  const m = metrics.current_month

  return (
    <div className="space-y-6">
      {/* KPIs */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {[
          { label: 'Llamadas este mes', value: m.total_calls, icon: Activity },
          { label: 'Costo estimado', value: `$${m.total_cost_usd.toFixed(2)} USD`, icon: DollarSign, alert: m.total_cost_usd > metrics.alert_threshold_usd * 0.8 },
          { label: 'Costo proyectado', value: `$${metrics.projected_month_cost_usd.toFixed(2)} USD`, icon: TrendingUp },
          { label: 'Tenants activos', value: m.calls_by_tenant.length, icon: Building2 },
        ].map((kpi) => (
          <div key={kpi.label} className={cn('rounded-xl border bg-card p-4', kpi.alert ? 'border-amber-300 bg-amber-50/30' : 'border-border')}>
            <div className="flex items-center justify-between pb-1">
              <span className="text-xs font-medium text-muted-foreground">{kpi.label}</span>
              <kpi.icon className="h-4 w-4 text-muted-foreground" />
            </div>
            <p className="text-xl font-bold tabular-nums">{kpi.value}</p>
          </div>
        ))}
      </div>

      {metrics.alert_triggered && (
        <div className="flex items-center gap-3 rounded-xl bg-red-50 border border-red-200 px-4 py-3">
          <Bell className="h-5 w-5 text-red-500 shrink-0" />
          <div>
            <p className="text-sm font-semibold text-red-800">Alerta de costo activada</p>
            <p className="text-xs text-red-600">El costo proyectado (${metrics.projected_month_cost_usd.toFixed(2)}) supera el umbral de ${metrics.alert_threshold_usd} USD/mes</p>
          </div>
        </div>
      )}

      {/* Tenant usage table */}
      {m.calls_by_tenant.length > 0 && (
        <div className="rounded-xl border border-border bg-card overflow-hidden">
          <div className="px-5 py-3 border-b border-border bg-muted/30">
            <h3 className="text-sm font-bold text-foreground">Uso por tenant</h3>
          </div>
          <table className="w-full">
            <thead>
              <tr className="border-b border-border text-xs text-muted-foreground">
                <th className="px-5 py-2.5 text-left font-medium">Tenant</th>
                <th className="px-5 py-2.5 text-right font-medium">Llamadas</th>
                <th className="px-5 py-2.5 text-right font-medium">Costo USD</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {m.calls_by_tenant.map(t => (
                <tr key={t.tenant_id} className="text-sm">
                  <td className="px-5 py-2.5 font-mono text-xs text-muted-foreground">{t.tenant_id}</td>
                  <td className="px-5 py-2.5 text-right tabular-nums">{t.calls}</td>
                  <td className="px-5 py-2.5 text-right tabular-nums text-muted-foreground">${t.cost_usd.toFixed(4)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Daily chart (simple bars) */}
      {m.calls_by_day.length > 0 && (
        <div className="rounded-xl border border-border bg-card p-5">
          <h3 className="text-sm font-bold text-foreground mb-3">Llamadas por día</h3>
          <div className="flex items-end gap-1 h-32">
            {m.calls_by_day.map(d => {
              const max = Math.max(...m.calls_by_day.map(x => x.calls), 1)
              const pct = (d.calls / max) * 100
              return (
                <div key={d.date} className="flex-1 flex flex-col items-center gap-1">
                  <span className="text-[9px] tabular-nums text-muted-foreground">{d.calls}</span>
                  <div className="w-full bg-primary/80 rounded-t" style={{ height: `${pct}%`, minHeight: d.calls > 0 ? 4 : 0 }} />
                  <span className="text-[8px] text-muted-foreground">{d.date.slice(8)}</span>
                </div>
              )
            })}
          </div>
        </div>
      )}
    </div>
  )
}

// ─── Page ────────────────────────────────────────────────────────────────────

// ─── Tab: Auditoría de accesos cross-tenant ─────────────────────────────────

const ACTION_LABELS: Record<string, string> = {
  'ai.analyze_pnl': 'Análisis P&L',
  'ai.memory.read': 'Lectura de memoria',
  'ai.memory.delete': 'Borrado de memoria',
  'ai.memory.delete_last': 'Borrado último análisis',
}

function AuditTab() {
  const [month, setMonth] = useState(new Date().toISOString().slice(0, 7))
  const { data, isLoading } = useCrossTenantAudit(month)

  return (
    <div className="space-y-5">
      <div className="bg-card rounded-2xl border border-border p-5">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="text-base font-bold text-foreground flex items-center gap-2">
              <Shield className="h-4 w-4 text-amber-500" /> Accesos cross-tenant
            </h3>
            <p className="text-xs text-muted-foreground mt-1">
              Registro de cada vez que un superusuario accedió a datos de IA de otro tenant.
            </p>
          </div>
          <div className="flex items-center gap-2">
            <input
              type="month"
              value={month}
              onChange={e => setMonth(e.target.value)}
              className="rounded-lg border border-border px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
            />
          </div>
        </div>

        {isLoading ? (
          <div className="flex justify-center py-12"><Loader2 className="h-5 w-5 animate-spin text-muted-foreground" /></div>
        ) : !data?.items.length ? (
          <div className="text-center py-12 text-muted-foreground">
            <Shield className="h-8 w-8 mx-auto mb-2 opacity-30" />
            <p className="text-sm">Sin accesos cross-tenant en {month}</p>
            <p className="text-xs mt-1">Esto es bueno — significa que no se accedió a datos de otros tenants.</p>
          </div>
        ) : (
          <>
            <div className="mb-3 flex items-center gap-2">
              <span className="inline-flex items-center rounded-full bg-amber-50 px-2.5 py-1 text-xs font-semibold text-amber-700">
                {data.total} acceso{data.total !== 1 ? 's' : ''}
              </span>
              <span className="text-xs text-muted-foreground">en {month}</span>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-xs text-muted-foreground uppercase border-b border-border">
                    <th className="text-left px-3 py-2">Fecha</th>
                    <th className="text-left px-3 py-2">Superusuario</th>
                    <th className="text-left px-3 py-2">Tenant consultado</th>
                    <th className="text-left px-3 py-2">Acción</th>
                    <th className="text-left px-3 py-2">Recurso</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {data.items.map((entry, i) => (
                    <tr key={i} className="hover:bg-muted/40">
                      <td className="px-3 py-2 text-xs text-muted-foreground whitespace-nowrap">
                        {new Date(entry.timestamp).toLocaleString('es-CO', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' })}
                      </td>
                      <td className="px-3 py-2">
                        <span className="text-xs font-medium text-foreground">{entry.superuser_email}</span>
                      </td>
                      <td className="px-3 py-2">
                        <span className="inline-flex items-center rounded-full bg-blue-50 px-2 py-0.5 text-xs font-semibold text-blue-700">
                          {entry.target_tenant}
                        </span>
                      </td>
                      <td className="px-3 py-2 text-xs text-foreground">{ACTION_LABELS[entry.action] ?? entry.action}</td>
                      <td className="px-3 py-2 text-xs text-muted-foreground font-mono">{entry.resource ?? '—'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        )}
      </div>

      {/* Tenant memory inspector */}
      <TenantMemoryInspector />

      {/* Legal note */}
      <div className="bg-amber-50 border border-amber-200 rounded-xl p-4">
        <p className="text-xs text-amber-800">
          <strong>Nota legal:</strong> Este registro cumple con la Ley 1581 de 2012 (Habeas Data) de Colombia.
          Cualquier titular de datos puede solicitar evidencia de quién accedió a su información.
          Conservar estos registros es obligatorio por un mínimo de 5 años.
        </p>
      </div>
    </div>
  )
}

function TenantMemoryInspector() {
  const [tenantId, setTenantId] = useState('')
  const [query, setQuery] = useState('')
  const { data: memory, isLoading, refetch } = useQuery<Record<string, unknown>>({
    queryKey: ['platform', 'ai', 'memory', query],
    queryFn: () => subRequest(`/api/v1/memory/${query}`),
    enabled: !!query,
    staleTime: 10_000,
  })

  function doSearch() {
    if (tenantId.trim()) setQuery(tenantId.trim())
  }

  return (
    <div className="bg-card rounded-2xl border border-border p-5">
      <h3 className="text-base font-bold text-foreground flex items-center gap-2 mb-1">
        <Building2 className="h-4 w-4 text-blue-500" /> Consultar contexto de IA por tenant
      </h3>
      <p className="text-xs text-muted-foreground mb-4">
        Inspecciona la memoria de IA almacenada para un tenant específico. Este acceso queda registrado en auditoría.
      </p>

      <div className="flex gap-2 mb-4">
        <input
          value={tenantId}
          onChange={e => setTenantId(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && doSearch()}
          placeholder="ID del tenant (ej: chape-5f2a09, platform)"
          className="flex-1 rounded-lg border border-border px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
        />
        <button
          onClick={doSearch}
          disabled={!tenantId.trim() || isLoading}
          className="px-4 py-2 text-sm font-semibold text-white bg-blue-600 hover:bg-blue-700 rounded-lg disabled:opacity-50 transition"
        >
          {isLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : 'Consultar'}
        </button>
      </div>

      {query && !isLoading && memory && (
        <div className="space-y-3">
          {Object.keys(memory).length === 0 ? (
            <p className="text-sm text-muted-foreground text-center py-6">Sin memoria de IA para este tenant.</p>
          ) : (
            <div className="bg-muted rounded-xl p-4 space-y-3">
              {memory.industria_detectada && (
                <div>
                  <p className="text-[10px] font-bold text-muted-foreground uppercase">Industria detectada</p>
                  <p className="text-sm text-foreground">{String(memory.industria_detectada)}</p>
                </div>
              )}
              {memory.total_analisis != null && (
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <p className="text-[10px] font-bold text-muted-foreground uppercase">Total análisis</p>
                    <p className="text-sm font-semibold text-foreground">{String(memory.total_analisis)}</p>
                  </div>
                  <div>
                    <p className="text-[10px] font-bold text-muted-foreground uppercase">Primer análisis</p>
                    <p className="text-sm text-foreground">{String(memory.primer_analisis ?? '—')}</p>
                  </div>
                </div>
              )}
              {Array.isArray(memory.productos_estrella_historicos) && (memory.productos_estrella_historicos as string[]).length > 0 && (
                <div>
                  <p className="text-[10px] font-bold text-muted-foreground uppercase">Productos estrella históricos</p>
                  <div className="flex flex-wrap gap-1 mt-1">
                    {(memory.productos_estrella_historicos as string[]).map((p, i) => (
                      <span key={i} className="inline-flex rounded-full bg-emerald-50 px-2 py-0.5 text-xs font-medium text-emerald-700">{p}</span>
                    ))}
                  </div>
                </div>
              )}
              {Array.isArray(memory.alertas_recurrentes) && (memory.alertas_recurrentes as Array<{alerta: string; veces: number}>).length > 0 && (
                <div>
                  <p className="text-[10px] font-bold text-muted-foreground uppercase">Alertas recurrentes</p>
                  <div className="space-y-1 mt-1">
                    {(memory.alertas_recurrentes as Array<{alerta: string; veces: number}>).map((a, i) => (
                      <div key={i} className="flex items-center justify-between text-xs">
                        <span className="text-foreground">{a.alerta}</span>
                        <span className="text-amber-600 font-semibold">{a.veces}x</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
              {Array.isArray(memory.patrones_detectados) && (memory.patrones_detectados as string[]).length > 0 && (
                <div>
                  <p className="text-[10px] font-bold text-muted-foreground uppercase">Patrones detectados</p>
                  <ul className="text-xs text-foreground mt-1 space-y-0.5">
                    {(memory.patrones_detectados as string[]).map((p, i) => <li key={i}>• {p}</li>)}
                  </ul>
                </div>
              )}
              {/* Raw JSON fallback */}
              <details className="text-xs">
                <summary className="text-muted-foreground cursor-pointer hover:text-foreground">Ver JSON completo</summary>
                <pre className="mt-2 bg-card rounded-lg p-3 overflow-x-auto text-[10px] text-muted-foreground border border-border">
                  {JSON.stringify(memory, null, 2)}
                </pre>
              </details>
              <div className="flex gap-2 pt-2">
                <button
                  onClick={async () => { if (confirm('¿Borrar toda la memoria de IA de este tenant?')) { await subRequest(`/api/v1/memory/${query}`, { method: 'DELETE' }); refetch() } }}
                  className="text-xs font-medium text-red-600 hover:text-red-700 bg-red-50 px-3 py-1.5 rounded-lg hover:bg-red-100 transition"
                >
                  Borrar memoria
                </button>
                <button
                  onClick={async () => { if (confirm('¿Borrar último análisis cache?')) { await subRequest(`/api/v1/memory/${query}/last`, { method: 'DELETE' }); refetch() } }}
                  className="text-xs font-medium text-amber-600 hover:text-amber-700 bg-amber-50 px-3 py-1.5 rounded-lg hover:bg-amber-100 transition"
                >
                  Borrar último análisis
                </button>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

const TABS = [
  { key: 'config', label: 'Configuración', icon: Settings },
  { key: 'metrics', label: 'Métricas de Uso', icon: BarChart3 },
  { key: 'audit', label: 'Auditoría', icon: Shield },
] as const

export function PlatformAiSettingsPage() {
  const [tab, setTab] = useState<'config' | 'metrics' | 'audit'>('config')
  const { data: settings, isLoading } = useAISettings()

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center gap-4">
        <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-gradient-to-br from-violet-500 to-purple-600 shadow-md">
          <Sparkles className="h-6 w-6 text-white" />
        </div>
        <div>
          <h1 className="text-2xl font-bold text-foreground">Inteligencia Artificial</h1>
          <p className="text-sm text-muted-foreground">Configura el proveedor de IA, límites y monitorea costos</p>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 rounded-xl bg-muted p-1">
        {TABS.map(t => (
          <button key={t.key} onClick={() => setTab(t.key)} className={cn('flex items-center gap-2 rounded-lg px-4 py-2 text-sm font-medium transition-colors flex-1 justify-center', tab === t.key ? 'bg-card text-foreground ' : 'text-muted-foreground hover:text-foreground')}>
            <t.icon className="h-4 w-4" /> {t.label}
          </button>
        ))}
      </div>

      {/* Content */}
      {isLoading ? (
        <div className="space-y-4 animate-pulse">{[...Array(4)].map((_, i) => <div key={i} className="h-32 rounded-xl bg-muted" />)}</div>
      ) : tab === 'config' && settings ? (
        <ConfigTab settings={settings} />
      ) : tab === 'metrics' ? (
        <MetricsTab />
      ) : tab === 'audit' ? (
        <AuditTab />
      ) : null}
    </div>
  )
}
