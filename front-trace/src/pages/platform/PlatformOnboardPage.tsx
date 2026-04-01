import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import {
  ArrowLeft, Building2, CheckCircle2, Layers, CreditCard, Plus, User, Eye, EyeOff,
} from 'lucide-react'
import { useOnboardTenant } from '@/hooks/usePlatform'
import { useQuery } from '@tanstack/react-query'
import { subscriptionApi } from '@/lib/subscription-api'
import { cn } from '@/lib/utils'

const AVAILABLE_MODULES = ['logistics', 'inventory', 'compliance', 'production', 'ai-analysis']

const MODULE_LABELS: Record<string, string> = {
  logistics: 'Logística',
  inventory: 'Inventario',
  compliance: 'Cumplimiento',
  production: 'Producción',
  'ai-analysis': 'IA',
}

export function PlatformOnboardPage() {
  const navigate = useNavigate()
  const onboard = useOnboardTenant()

  const [tenantId, setTenantId] = useState('')
  const [companyName, setCompanyName] = useState('')
  const [adminEmail, setAdminEmail] = useState('')
  const [adminPassword, setAdminPassword] = useState('')
  const [adminName, setAdminName] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [planSlug, setPlanSlug] = useState('free')
  const [billingCycle, setBillingCycle] = useState('monthly')
  const [modules, setModules] = useState<string[]>([])
  const [notes, setNotes] = useState('')

  const { data: plans } = useQuery({
    queryKey: ['plans'],
    queryFn: () => subscriptionApi.plans.list(),
    staleTime: 60_000,
  })

  const activePlans = (plans ?? []).filter(p => p.is_active && !p.is_archived)

  const toggleModule = (slug: string) => {
    setModules(prev => prev.includes(slug) ? prev.filter(m => m !== slug) : [...prev, slug])
  }

  // Auto-generate tenant slug from company name
  const handleCompanyChange = (value: string) => {
    setCompanyName(value)
    if (!tenantId || tenantId === slugify(companyName)) {
      setTenantId(slugify(value))
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!tenantId.trim() || !companyName.trim() || !adminEmail.trim() || !adminPassword.trim() || !adminName.trim()) return

    try {
      await onboard.mutateAsync({
        tenant_id: tenantId.trim(),
        company_name: companyName.trim(),
        admin_email: adminEmail.trim(),
        admin_password: adminPassword,
        admin_name: adminName.trim(),
        plan_slug: planSlug,
        billing_cycle: billingCycle,
        modules,
        notes: notes || undefined,
      })
      navigate(`/platform/tenants/${encodeURIComponent(tenantId.trim())}`)
    } catch {
      // error handled by mutation
    }
  }

  const inputCls = 'w-full px-3 py-2.5 text-sm bg-card border border-border rounded-xl focus:ring-2 focus:ring-ring/20 focus:border-ring outline-none'

  return (
    <div className="space-y-6 max-w-2xl">
      <div>
        <Link to="/platform/tenants" className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-primary mb-2">
          <ArrowLeft className="h-4 w-4" /> Empresas
        </Link>
        <h1 className="text-2xl font-bold text-foreground">Onboarding de Empresa</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Registra una nueva empresa con su administrador, plan y módulos.
        </p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Company + Tenant */}
        <div className="bg-card rounded-2xl border border-border/60 p-6  space-y-4">
          <h3 className="text-sm font-semibold text-foreground flex items-center gap-2">
            <Building2 className="h-4 w-4 text-primary" /> Datos de la Empresa
          </h3>
          <div>
            <label className="block text-sm font-medium text-muted-foreground mb-1">
              Nombre de la empresa <span className="text-red-500">*</span>
            </label>
            <input
              type="text"
              value={companyName}
              onChange={e => handleCompanyChange(e.target.value)}
              placeholder="Ejemplo: Café Origen S.A.S."
              required
              className={inputCls}
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-muted-foreground mb-1">
              Tenant ID (slug) <span className="text-red-500">*</span>
            </label>
            <input
              type="text"
              value={tenantId}
              onChange={e => setTenantId(e.target.value)}
              placeholder="cafe-origen"
              required
              className={cn(inputCls, 'font-mono')}
            />
            <p className="text-xs text-muted-foreground mt-1">Identificador único. Se genera automáticamente del nombre.</p>
          </div>
          <div>
            <label className="block text-sm font-medium text-muted-foreground mb-1">Notas (opcional)</label>
            <textarea
              value={notes}
              onChange={e => setNotes(e.target.value)}
              placeholder="Sector, contacto, observaciones..."
              rows={2}
              className={cn(inputCls, 'resize-none')}
            />
          </div>
        </div>

        {/* Admin user */}
        <div className="bg-card rounded-2xl border border-border/60 p-6  space-y-4">
          <h3 className="text-sm font-semibold text-foreground flex items-center gap-2">
            <User className="h-4 w-4 text-primary" /> Usuario Administrador
          </h3>
          <p className="text-xs text-muted-foreground -mt-2">
            Se creará como primer usuario con rol Administrador.
          </p>
          <div className="grid grid-cols-2 gap-4">
            <div className="col-span-2">
              <label className="block text-sm font-medium text-muted-foreground mb-1">
                Nombre completo <span className="text-red-500">*</span>
              </label>
              <input
                type="text"
                value={adminName}
                onChange={e => setAdminName(e.target.value)}
                placeholder="Juan Pérez"
                required
                className={inputCls}
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-muted-foreground mb-1">
                Correo electrónico <span className="text-red-500">*</span>
              </label>
              <input
                type="email"
                value={adminEmail}
                onChange={e => setAdminEmail(e.target.value)}
                placeholder="admin@empresa.com"
                required
                className={inputCls}
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-muted-foreground mb-1">
                Contraseña <span className="text-red-500">*</span>
              </label>
              <div className="relative">
                <input
                  type={showPassword ? 'text' : 'password'}
                  value={adminPassword}
                  onChange={e => setAdminPassword(e.target.value)}
                  placeholder="Mínimo 6 caracteres"
                  required
                  minLength={6}
                  className={cn(inputCls, 'pr-10')}
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(p => !p)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-muted-foreground"
                >
                  {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* Plan selection */}
        <div className="bg-card rounded-2xl border border-border/60 p-6  space-y-4">
          <h3 className="text-sm font-semibold text-foreground flex items-center gap-2">
            <CreditCard className="h-4 w-4 text-primary" /> Plan de Suscripción
          </h3>
          <div className="grid grid-cols-2 gap-3">
            {activePlans.map(p => (
              <button
                key={p.slug}
                type="button"
                onClick={() => setPlanSlug(p.slug)}
                className={cn(
                  'text-left rounded-xl border-2 p-4 transition',
                  planSlug === p.slug
                    ? 'border-primary bg-primary/5 ring-1 ring-ring/30'
                    : 'border-border hover:border-slate-300',
                )}
              >
                <div className="text-sm font-semibold text-foreground">{p.name}</div>
                <div className="text-lg font-bold text-primary mt-1">
                  {p.price_monthly > 0 ? `$${p.price_monthly}/mes` : 'Gratis'}
                </div>
                <div className="text-xs text-muted-foreground mt-1">
                  {p.max_users} usuarios, {p.max_assets} assets
                </div>
                {planSlug === p.slug && (
                  <CheckCircle2 className="h-5 w-5 text-primary mt-2" />
                )}
              </button>
            ))}
          </div>

          <div>
            <label className="block text-sm font-medium text-muted-foreground mb-1">Ciclo de Facturación</label>
            <div className="flex gap-2">
              {(['monthly', 'annual'] as const).map(c => (
                <button
                  key={c}
                  type="button"
                  onClick={() => setBillingCycle(c)}
                  className={cn(
                    'px-4 py-2 text-sm rounded-xl border-2 font-medium transition',
                    billingCycle === c
                      ? 'border-primary bg-primary/10 text-primary'
                      : 'border-border text-muted-foreground hover:border-slate-300',
                  )}
                >
                  {c === 'monthly' ? 'Mensual' : 'Anual'}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Module selection */}
        <div className="bg-card rounded-2xl border border-border/60 p-6  space-y-4">
          <h3 className="text-sm font-semibold text-foreground flex items-center gap-2">
            <Layers className="h-4 w-4 text-primary" /> Módulos a Activar
          </h3>
          <div className="flex flex-wrap gap-3">
            {AVAILABLE_MODULES.map(m => (
              <button
                key={m}
                type="button"
                onClick={() => toggleModule(m)}
                className={cn(
                  'flex items-center gap-2 px-4 py-3 rounded-xl border-2 text-sm font-medium transition',
                  modules.includes(m)
                    ? 'border-primary bg-primary/10 text-primary'
                    : 'border-border text-muted-foreground hover:border-slate-300',
                )}
              >
                {modules.includes(m) ? (
                  <CheckCircle2 className="h-4 w-4 text-primary" />
                ) : (
                  <Plus className="h-4 w-4 text-muted-foreground" />
                )}
                <span>{MODULE_LABELS[m] ?? m}</span>
              </button>
            ))}
          </div>
        </div>

        {/* Submit */}
        <div className="flex items-center gap-3">
          <button
            type="submit"
            disabled={!tenantId.trim() || !companyName.trim() || !adminEmail.trim() || !adminPassword.trim() || !adminName.trim() || onboard.isPending}
            className="flex items-center gap-2 px-6 py-3 text-sm font-semibold text-white bg-primary hover:bg-primary/90 rounded-xl disabled:opacity-50 transition"
          >
            {onboard.isPending ? (
              <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white" />
            ) : (
              <Building2 className="h-4 w-4" />
            )}
            Registrar Empresa
          </button>
          {onboard.isError && (
            <p className="text-sm text-red-600">{(onboard.error as Error).message}</p>
          )}
          {onboard.isSuccess && (
            <p className="text-sm text-emerald-600 flex items-center gap-1">
              <CheckCircle2 className="h-4 w-4" /> Empresa registrada exitosamente
            </p>
          )}
        </div>
      </form>
    </div>
  )
}

function slugify(str: string): string {
  return str
    .toLowerCase()
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '')
    .slice(0, 50)
}
