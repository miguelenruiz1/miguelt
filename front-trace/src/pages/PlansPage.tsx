import { useState } from 'react'
import { useForm, Controller } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Package, Edit, Archive, Plus, CheckCircle2 } from 'lucide-react'
import { useQuery } from '@tanstack/react-query'
import { usePlans, useCreatePlan, useUpdatePlan, useArchivePlan } from '@/hooks/usePlans'
import { subscriptionApi } from '@/lib/subscription-api'
import type { Plan, PlanCreate, PlanUpdate } from '@/types/subscription'
import { cn } from '@/lib/utils'

// ─── Zod schema ───────────────────────────────────────────────────────────────

const planSchema = z.object({
  name: z.string().min(1, 'Campo obligatorio').max(100),
  slug: z.string().min(1, 'Campo obligatorio').regex(/^[a-z0-9-]+$/, 'Solo minúsculas, números y guiones'),
  description: z.string().optional(),
  price_monthly: z.coerce.number().min(0, 'No puede ser negativo'),
  price_annual: z.union([z.coerce.number().min(0), z.literal('').transform(() => undefined), z.undefined(), z.null()]).optional(),
  currency: z.enum(['COP', 'USD']).default('COP'),
  max_users: z.coerce.number().int().min(1).default(3),
  max_assets: z.coerce.number().int().min(0).default(100),
  max_wallets: z.coerce.number().int().min(0).default(5),
  sort_order: z.coerce.number().int().default(0),
  modules: z.array(z.string()).default([]),
  is_active: z.boolean().default(true),
})

type PlanFormData = z.infer<typeof planSchema>

// ─── Plan Modal ───────────────────────────────────────────────────────────────

function PlanModal({
  plan,
  onClose,
}: {
  plan?: Plan
  onClose: () => void
}) {
  const createMut = useCreatePlan()
  const updateMut = useUpdatePlan()

  const { data: catalog = [] } = useQuery({
    queryKey: ['module-catalog'],
    queryFn: () => subscriptionApi.modules.catalog(),
    staleTime: 120_000,
  })

  const isEdit = !!plan

  const {
    register,
    handleSubmit,
    control,
    watch,
    setValue,
    formState: { errors, isValid, isSubmitting },
  } = useForm<PlanFormData>({
    resolver: zodResolver(planSchema),
    mode: 'onChange',
    defaultValues: {
      name: plan?.name ?? '',
      slug: plan?.slug ?? '',
      description: plan?.description ?? '',
      price_monthly: plan?.price_monthly ?? 0,
      price_annual: (plan?.price_annual ?? undefined) as number | undefined,
      currency: 'COP',
      max_users: plan?.max_users ?? 3,
      max_assets: plan?.max_assets ?? 100,
      max_wallets: plan?.max_wallets ?? 5,
      sort_order: plan?.sort_order ?? 0,
      modules: plan?.modules ?? [],
      is_active: plan?.is_active ?? true,
    },
  })

  const nameValue = watch('name')
  const slugValue = watch('slug')
  const modulesValue = watch('modules') ?? []

  function toggleModule(mod: string) {
    const current = modulesValue
    const next = current.includes(mod) ? current.filter(m => m !== mod) : [...current, mod]
    setValue('modules', next, { shouldDirty: true, shouldValidate: true })
  }

  // Auto-generate slug from name (only on create, if slug is empty or still matches previous slugified name)
  function handleNameChange(value: string) {
    setValue('name', value, { shouldDirty: true, shouldValidate: true })
    if (!isEdit && (!slugValue || slugValue === slugify(nameValue ?? ''))) {
      setValue('slug', slugify(value), { shouldDirty: true, shouldValidate: true })
    }
  }

  const onSubmit = async (data: PlanFormData) => {
    const payload = {
      ...data,
      price_annual: data.price_annual === undefined || data.price_annual === null
        ? undefined
        : Number(data.price_annual),
    }
    if (isEdit) {
      await updateMut.mutateAsync({ id: plan!.id, data: payload as unknown as PlanUpdate })
    } else {
      await createMut.mutateAsync(payload as unknown as PlanCreate)
    }
    onClose()
  }

  const isPending = createMut.isPending || updateMut.isPending || isSubmitting
  const inputCls = 'w-full rounded-xl border border-border px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring'
  const errCls = 'mt-1 text-xs text-red-600'

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 backdrop-blur-sm">
      <div className="bg-card rounded-2xl shadow-xl p-6 w-full max-w-lg max-h-[90vh] overflow-y-auto">
        <h2 className="text-lg font-bold text-foreground mb-4">{isEdit ? 'Editar Plan' : 'Nuevo Plan'}</h2>
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4" noValidate>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-foreground mb-1">Nombre</label>
              <input
                value={nameValue ?? ''}
                onChange={e => handleNameChange(e.target.value)}
                placeholder="Ej: Profesional"
                className={inputCls}
              />
              {errors.name && <p className={errCls}>{errors.name.message}</p>}
            </div>
            <div>
              <label className="block text-sm font-medium text-foreground mb-1">Slug</label>
              <input
                {...register('slug')}
                disabled={isEdit}
                className={cn(inputCls, 'font-mono', isEdit && 'bg-muted text-muted-foreground')}
              />
              {errors.slug && <p className={errCls}>{errors.slug.message}</p>}
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-foreground mb-1">Descripción</label>
            <input {...register('description')} placeholder="Descripción breve del plan" className={inputCls} />
            {errors.description && <p className={errCls}>{errors.description.message}</p>}
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-foreground mb-1">Precio/mes ($)</label>
              <input type="number" step="0.01" {...register('price_monthly')} className={inputCls} />
              {errors.price_monthly && <p className={errCls}>{errors.price_monthly.message}</p>}
            </div>
            <div>
              <label className="block text-sm font-medium text-foreground mb-1">Precio/año ($)</label>
              <input type="number" step="0.01" {...register('price_annual')} placeholder="Opcional" className={inputCls} />
              {errors.price_annual && <p className={errCls}>{errors.price_annual.message as string}</p>}
            </div>
          </div>

          <div className="grid grid-cols-3 gap-4">
            <div>
              <label className="block text-sm font-medium text-foreground mb-1">Max usuarios</label>
              <input type="number" {...register('max_users')} className={inputCls} />
              {errors.max_users && <p className={errCls}>{errors.max_users.message}</p>}
            </div>
            <div>
              <label className="block text-sm font-medium text-foreground mb-1">Max activos</label>
              <input type="number" {...register('max_assets')} className={inputCls} />
              {errors.max_assets && <p className={errCls}>{errors.max_assets.message}</p>}
            </div>
            <div>
              <label className="block text-sm font-medium text-foreground mb-1">Max wallets</label>
              <input type="number" {...register('max_wallets')} className={inputCls} />
              {errors.max_wallets && <p className={errCls}>{errors.max_wallets.message}</p>}
            </div>
          </div>

          {/* Modules from catalog */}
          <div>
            <label className="block text-sm font-medium text-foreground mb-2">Módulos incluidos</label>
            <div className="grid grid-cols-2 gap-2">
              {catalog.map(mod => {
                const selected = modulesValue.includes(mod.slug)
                return (
                  <button
                    key={mod.slug}
                    type="button"
                    onClick={() => toggleModule(mod.slug)}
                    className={cn(
                      'flex items-center gap-2 rounded-xl border-2 px-3 py-2.5 text-left text-sm font-medium transition',
                      selected
                        ? 'border-primary bg-primary/5 text-primary'
                        : 'border-border text-muted-foreground hover:border-slate-300',
                    )}
                  >
                    {selected ? (
                      <CheckCircle2 className="h-4 w-4 shrink-0 text-primary" />
                    ) : (
                      <div className="h-4 w-4 shrink-0 rounded-full border-2 border-slate-300" />
                    )}
                    <div className="min-w-0">
                      <div className="truncate">{mod.name}</div>
                      {mod.dependencies?.length ? (
                        <div className="text-[10px] text-muted-foreground font-normal">
                          Requiere: {mod.dependencies.join(', ')}
                        </div>
                      ) : null}
                    </div>
                  </button>
                )
              })}
            </div>
          </div>

          <div className="flex items-center gap-3">
            <Controller
              control={control}
              name="is_active"
              render={({ field }) => (
                <input
                  type="checkbox"
                  id="is_active"
                  checked={!!field.value}
                  onChange={e => field.onChange(e.target.checked)}
                  className="rounded"
                />
              )}
            />
            <label htmlFor="is_active" className="text-sm font-medium text-foreground">Plan activo</label>
          </div>

          <div className="flex justify-end gap-3 pt-2">
            <button type="button" onClick={onClose} className="rounded-xl px-4 py-2 text-sm text-muted-foreground hover:bg-secondary">Cancelar</button>
            <button
              type="submit"
              disabled={!isValid || isPending}
              className="rounded-xl bg-primary px-4 py-2 text-sm font-semibold text-white hover:bg-primary/90 disabled:opacity-50"
            >
              {isPending ? 'Guardando...' : isEdit ? 'Guardar' : 'Crear'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

// ─── Plan Card ────────────────────────────────────────────────────────────────

function PlanCard({ plan, onEdit }: { plan: Plan; onEdit: () => void }) {
  const archive = useArchivePlan()

  return (
    <div className={cn(
      'rounded-2xl border bg-card p-6  transition-all',
      plan.is_archived ? 'opacity-60 border-border' : 'border-border hover:shadow-md',
    )}>
      <div className="flex items-start justify-between">
        <div>
          <h3 className="text-lg font-bold text-foreground">{plan.name}</h3>
          <p className="text-xs text-muted-foreground mt-0.5 font-mono">{plan.slug}</p>
        </div>
        <div className="flex gap-1">
          <button onClick={onEdit} className="rounded-lg p-1.5 text-muted-foreground hover:text-primary hover:bg-primary/10 transition-colors">
            <Edit className="h-4 w-4" />
          </button>
          {!plan.is_archived && (
            <button
              onClick={() => archive.mutate(plan.id)}
              disabled={archive.isPending}
              className="rounded-lg p-1.5 text-muted-foreground hover:text-red-600 hover:bg-red-50 transition-colors disabled:opacity-50"
            >
              <Archive className="h-4 w-4" />
            </button>
          )}
        </div>
      </div>

      {plan.description && (
        <p className="mt-2 text-sm text-muted-foreground">{plan.description}</p>
      )}

      <div className="mt-4">
        <p className="text-3xl font-bold text-foreground">
          {Number(plan.price_monthly) === -1 ? 'Custom' : `$${Number(plan.price_monthly).toLocaleString('es-CO')}`}
          <span className="text-sm font-normal text-muted-foreground">/mes</span>
        </p>
      </div>

      <div className="mt-4 grid grid-cols-3 gap-2 text-xs text-muted-foreground">
        <div className="rounded-lg bg-muted p-2 text-center">
          <p className="font-bold text-foreground">{plan.max_users === -1 ? '∞' : plan.max_users}</p>
          <p>usuarios</p>
        </div>
        <div className="rounded-lg bg-muted p-2 text-center">
          <p className="font-bold text-foreground">{plan.max_assets === -1 ? '∞' : plan.max_assets.toLocaleString('es-CO')}</p>
          <p>activos</p>
        </div>
        <div className="rounded-lg bg-muted p-2 text-center">
          <p className="font-bold text-foreground">{plan.max_wallets === -1 ? '∞' : plan.max_wallets}</p>
          <p>wallets</p>
        </div>
      </div>

      {plan.modules.length > 0 && (
        <div className="mt-4 flex flex-wrap gap-1.5">
          {plan.modules.map((mod: string) => (
            <span key={mod} className="rounded-full bg-primary/10 px-2 py-0.5 text-xs font-medium text-primary">
              {mod}
            </span>
          ))}
        </div>
      )}

      {(plan.is_archived || !plan.is_active) && (
        <div className="mt-3 rounded-lg bg-secondary px-2 py-1 text-xs text-muted-foreground text-center font-medium">
          {plan.is_archived ? 'Archivado' : 'Inactivo'}
        </div>
      )}
    </div>
  )
}

// ─── Main Page ────────────────────────────────────────────────────────────────

export function PlansPage() {
  const { data: plans = [], isLoading } = usePlans(true)
  const [editingPlan, setEditingPlan] = useState<Plan | null>(null)
  const [showCreate, setShowCreate] = useState(false)

  return (
    <div className="p-8 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-purple-100">
            <Package className="h-5 w-5 text-purple-600" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-foreground">Planes</h1>
            <p className="text-sm text-muted-foreground">Gestión de planes de suscripción</p>
          </div>
        </div>
        <button
          onClick={() => setShowCreate(true)}
          className="flex items-center gap-2 rounded-xl bg-primary px-4 py-2 text-sm font-semibold text-white hover:bg-primary/90 "
        >
          <Plus className="h-4 w-4" /> Nuevo Plan
        </button>
      </div>

      {/* Plans grid */}
      {isLoading ? (
        <div className="text-center text-muted-foreground py-12">Cargando planes...</div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
          {plans.map(p => (
            <PlanCard key={p.id} plan={p} onEdit={() => setEditingPlan(p)} />
          ))}
        </div>
      )}

      {editingPlan && <PlanModal plan={editingPlan} onClose={() => setEditingPlan(null)} />}
      {showCreate && <PlanModal onClose={() => setShowCreate(false)} />}
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
