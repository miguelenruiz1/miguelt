import { useState, useEffect } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import {
  ArrowLeft, Building2, CheckCircle2, Layers, CreditCard, Plus, User, Eye, EyeOff,
} from 'lucide-react'
import { useOnboardTenant } from '@/hooks/usePlatform'
import { useQuery } from '@tanstack/react-query'
import { subscriptionApi } from '@/lib/subscription-api'
import { cn } from '@/lib/utils'

// ─── Zod schema ───────────────────────────────────────────────────────────────

const onboardSchema = z.object({
  tenant_id: z.string().regex(/^[a-z0-9-]{3,50}$/, '3-50 chars, minúsculas/números/guiones'),
  company_name: z.string().min(1, 'Campo obligatorio').max(255),
  country: z.enum(['CO']).default('CO'),
  admin_email: z.string().email('Email inválido'),
  admin_full_name: z.string().min(1, 'Campo obligatorio').max(255),
  admin_password: z.string().min(6, 'Mínimo 6 caracteres'),
  plan_slug: z.string().min(1, 'Seleccioná un plan'),
  billing_cycle: z.enum(['monthly', 'annual']).default('monthly'),
  modules: z.array(z.string()).min(1, 'Activá al menos un módulo'),
  notes: z.string().optional(),
})

type OnboardFormData = z.infer<typeof onboardSchema>

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
  const [showPassword, setShowPassword] = useState(false)

  const {
    register,
    handleSubmit,
    watch,
    setValue,
    formState: { errors, isValid, isSubmitting },
  } = useForm<OnboardFormData>({
    resolver: zodResolver(onboardSchema),
    mode: 'onChange',
    defaultValues: {
      tenant_id: '',
      company_name: '',
      country: 'CO',
      admin_email: '',
      admin_full_name: '',
      admin_password: '',
      plan_slug: 'free',
      billing_cycle: 'monthly',
      modules: [],
      notes: '',
    },
  })

  const { data: plans } = useQuery({
    queryKey: ['plans'],
    queryFn: () => subscriptionApi.plans.list(),
    staleTime: 60_000,
  })

  const activePlans = (plans ?? []).filter(p => p.is_active && !p.is_archived)

  const tenantId = watch('tenant_id')
  const companyName = watch('company_name')
  const planSlug = watch('plan_slug')
  const billingCycle = watch('billing_cycle')
  const modules = watch('modules') ?? []

  // Track previous company slugified value so we can keep tenant auto-synced until user edits it manually
  const [prevCompanySlug, setPrevCompanySlug] = useState('')

  useEffect(() => {
    // When company_name changes, keep tenant_id in sync unless user manually edited it
    if (!tenantId || tenantId === prevCompanySlug) {
      const next = slugify(companyName ?? '')
      if (next !== tenantId) {
        setValue('tenant_id', next, { shouldValidate: true, shouldDirty: true })
      }
      setPrevCompanySlug(next)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [companyName])

  const toggleModule = (slug: string) => {
    const next = modules.includes(slug) ? modules.filter(m => m !== slug) : [...modules, slug]
    setValue('modules', next, { shouldValidate: true, shouldDirty: true })
  }

  const onSubmit = async (data: OnboardFormData) => {
    try {
      await onboard.mutateAsync({
        tenant_id: data.tenant_id.trim(),
        company_name: data.company_name.trim(),
        admin_email: data.admin_email.trim(),
        admin_password: data.admin_password,
        admin_name: data.admin_full_name.trim(),
        plan_slug: data.plan_slug,
        billing_cycle: data.billing_cycle,
        modules: data.modules,
        notes: data.notes || undefined,
      })
      navigate(`/platform/tenants/${encodeURIComponent(data.tenant_id.trim())}`)
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

      <form onSubmit={handleSubmit(onSubmit)} className="space-y-6" noValidate>
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
              {...register('company_name')}
              placeholder="Ejemplo: Café Origen S.A.S."
              className={inputCls}
            />
            {errors.company_name && <p className="mt-1 text-xs text-red-600">{errors.company_name.message}</p>}
          </div>
          <div>
            <label className="block text-sm font-medium text-muted-foreground mb-1">
              Tenant ID (slug) <span className="text-red-500">*</span>
            </label>
            <input
              type="text"
              {...register('tenant_id')}
              placeholder="cafe-origen"
              className={cn(inputCls, 'font-mono')}
            />
            <p className="text-xs text-muted-foreground mt-1">Identificador único. Se genera automáticamente del nombre.</p>
            {errors.tenant_id && <p className="mt-1 text-xs text-red-600">{errors.tenant_id.message}</p>}
          </div>
          <div>
            <label className="block text-sm font-medium text-muted-foreground mb-1">Notas (opcional)</label>
            <textarea
              {...register('notes')}
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
                {...register('admin_full_name')}
                placeholder="Juan Pérez"
                className={inputCls}
              />
              {errors.admin_full_name && <p className="mt-1 text-xs text-red-600">{errors.admin_full_name.message}</p>}
            </div>
            <div>
              <label className="block text-sm font-medium text-muted-foreground mb-1">
                Correo electrónico <span className="text-red-500">*</span>
              </label>
              <input
                type="email"
                {...register('admin_email')}
                placeholder="admin@empresa.com"
                className={inputCls}
              />
              {errors.admin_email && <p className="mt-1 text-xs text-red-600">{errors.admin_email.message}</p>}
            </div>
            <div>
              <label className="block text-sm font-medium text-muted-foreground mb-1">
                Contraseña <span className="text-red-500">*</span>
              </label>
              <div className="relative">
                <input
                  type={showPassword ? 'text' : 'password'}
                  {...register('admin_password')}
                  placeholder="Mínimo 6 caracteres"
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
              {errors.admin_password && <p className="mt-1 text-xs text-red-600">{errors.admin_password.message}</p>}
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
                onClick={() => setValue('plan_slug', p.slug, { shouldValidate: true, shouldDirty: true })}
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
                  onClick={() => setValue('billing_cycle', c, { shouldValidate: true, shouldDirty: true })}
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
          {errors.modules && <p className="text-xs text-red-600">{errors.modules.message as string}</p>}
        </div>

        {/* Submit */}
        <div className="flex items-center gap-3">
          <button
            type="submit"
            disabled={!isValid || isSubmitting || onboard.isPending}
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
