import { useState } from 'react'
import { Package, Edit, Archive, Plus, CheckCircle2 } from 'lucide-react'
import { useQuery } from '@tanstack/react-query'
import { usePlans, useCreatePlan, useUpdatePlan, useArchivePlan } from '@/hooks/usePlans'
import { subscriptionApi } from '@/lib/subscription-api'
import type { Plan, PlanCreate, PlanUpdate } from '@/types/subscription'
import { cn } from '@/lib/utils'

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

  const [form, setForm] = useState({
    name: plan?.name ?? '',
    slug: plan?.slug ?? '',
    description: plan?.description ?? '',
    price_monthly: plan?.price_monthly ?? 0,
    price_annual: plan?.price_annual ?? '',
    max_users: plan?.max_users ?? 3,
    max_assets: plan?.max_assets ?? 100,
    max_wallets: plan?.max_wallets ?? 5,
    modules: plan?.modules ?? ([] as string[]),
    is_active: plan?.is_active ?? true,
    sort_order: plan?.sort_order ?? 0,
  })

  function toggleModule(mod: string) {
    setForm(f => ({
      ...f,
      modules: f.modules.includes(mod)
        ? f.modules.filter(m => m !== mod)
        : [...f.modules, mod],
    }))
  }

  // Auto-generate slug from name
  function handleNameChange(value: string) {
    setForm(f => ({
      ...f,
      name: value,
      ...(!isEdit && (!f.slug || f.slug === slugify(f.name)) ? { slug: slugify(value) } : {}),
    }))
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    const data = {
      ...form,
      price_monthly: Number(form.price_monthly),
      price_annual: form.price_annual !== '' ? Number(form.price_annual) : undefined,
      max_users: Number(form.max_users),
      max_assets: Number(form.max_assets),
      max_wallets: Number(form.max_wallets),
      sort_order: Number(form.sort_order),
    }
    if (isEdit) {
      await updateMut.mutateAsync({ id: plan!.id, data: data as PlanUpdate })
    } else {
      await createMut.mutateAsync(data as PlanCreate)
    }
    onClose()
  }

  const isPending = createMut.isPending || updateMut.isPending
  const inputCls = 'w-full rounded-xl border border-slate-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring'

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 backdrop-blur-sm">
      <div className="bg-white rounded-2xl shadow-xl p-6 w-full max-w-lg max-h-[90vh] overflow-y-auto">
        <h2 className="text-lg font-bold text-slate-800 mb-4">{isEdit ? 'Editar Plan' : 'Nuevo Plan'}</h2>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Nombre</label>
              <input required value={form.name} onChange={e => handleNameChange(e.target.value)}
                placeholder="Ej: Profesional"
                className={inputCls} />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Slug</label>
              <input required value={form.slug} onChange={e => setForm(f => ({ ...f, slug: e.target.value }))}
                disabled={isEdit}
                className={cn(inputCls, 'font-mono', isEdit && 'bg-slate-50 text-slate-400')} />
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Descripción</label>
            <input value={form.description} onChange={e => setForm(f => ({ ...f, description: e.target.value }))}
              placeholder="Descripción breve del plan"
              className={inputCls} />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Precio/mes ($)</label>
              <input type="number" step="0.01" value={form.price_monthly}
                onChange={e => setForm(f => ({ ...f, price_monthly: Number(e.target.value) }))}
                className={inputCls} />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Precio/año ($)</label>
              <input type="number" step="0.01" value={form.price_annual}
                onChange={e => setForm(f => ({ ...f, price_annual: e.target.value }))}
                placeholder="Opcional"
                className={inputCls} />
            </div>
          </div>

          <div className="grid grid-cols-3 gap-4">
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Max usuarios</label>
              <input type="number" value={form.max_users} onChange={e => setForm(f => ({ ...f, max_users: Number(e.target.value) }))}
                className={inputCls} />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Max activos</label>
              <input type="number" value={form.max_assets} onChange={e => setForm(f => ({ ...f, max_assets: Number(e.target.value) }))}
                className={inputCls} />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Max wallets</label>
              <input type="number" value={form.max_wallets} onChange={e => setForm(f => ({ ...f, max_wallets: Number(e.target.value) }))}
                className={inputCls} />
            </div>
          </div>

          {/* Modules from catalog */}
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-2">Módulos incluidos</label>
            <div className="grid grid-cols-2 gap-2">
              {catalog.map(mod => {
                const selected = form.modules.includes(mod.slug)
                return (
                  <button
                    key={mod.slug}
                    type="button"
                    onClick={() => toggleModule(mod.slug)}
                    className={cn(
                      'flex items-center gap-2 rounded-xl border-2 px-3 py-2.5 text-left text-sm font-medium transition',
                      selected
                        ? 'border-primary bg-primary/5 text-primary'
                        : 'border-slate-200 text-slate-600 hover:border-slate-300',
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
                        <div className="text-[10px] text-slate-400 font-normal">
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
            <input
              type="checkbox"
              id="is_active"
              checked={form.is_active}
              onChange={e => setForm(f => ({ ...f, is_active: e.target.checked }))}
              className="rounded"
            />
            <label htmlFor="is_active" className="text-sm font-medium text-slate-700">Plan activo</label>
          </div>

          <div className="flex justify-end gap-3 pt-2">
            <button type="button" onClick={onClose} className="rounded-xl px-4 py-2 text-sm text-slate-600 hover:bg-slate-100">Cancelar</button>
            <button type="submit" disabled={isPending} className="rounded-xl bg-primary px-4 py-2 text-sm font-semibold text-white hover:bg-primary/90 disabled:opacity-50">
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
      'rounded-2xl border bg-white p-6 shadow-sm transition-all',
      plan.is_archived ? 'opacity-60 border-slate-200' : 'border-slate-200 hover:shadow-md',
    )}>
      <div className="flex items-start justify-between">
        <div>
          <h3 className="text-lg font-bold text-slate-800">{plan.name}</h3>
          <p className="text-xs text-slate-400 mt-0.5 font-mono">{plan.slug}</p>
        </div>
        <div className="flex gap-1">
          <button onClick={onEdit} className="rounded-lg p-1.5 text-slate-400 hover:text-primary hover:bg-primary/10 transition-colors">
            <Edit className="h-4 w-4" />
          </button>
          {!plan.is_archived && (
            <button
              onClick={() => archive.mutate(plan.id)}
              disabled={archive.isPending}
              className="rounded-lg p-1.5 text-slate-400 hover:text-red-600 hover:bg-red-50 transition-colors disabled:opacity-50"
            >
              <Archive className="h-4 w-4" />
            </button>
          )}
        </div>
      </div>

      {plan.description && (
        <p className="mt-2 text-sm text-slate-500">{plan.description}</p>
      )}

      <div className="mt-4">
        <p className="text-3xl font-bold text-slate-800">
          {Number(plan.price_monthly) === -1 ? 'Custom' : `$${Number(plan.price_monthly).toLocaleString()}`}
          <span className="text-sm font-normal text-slate-400">/mes</span>
        </p>
      </div>

      <div className="mt-4 grid grid-cols-3 gap-2 text-xs text-slate-500">
        <div className="rounded-lg bg-slate-50 p-2 text-center">
          <p className="font-bold text-slate-700">{plan.max_users === -1 ? '∞' : plan.max_users}</p>
          <p>usuarios</p>
        </div>
        <div className="rounded-lg bg-slate-50 p-2 text-center">
          <p className="font-bold text-slate-700">{plan.max_assets === -1 ? '∞' : plan.max_assets.toLocaleString()}</p>
          <p>activos</p>
        </div>
        <div className="rounded-lg bg-slate-50 p-2 text-center">
          <p className="font-bold text-slate-700">{plan.max_wallets === -1 ? '∞' : plan.max_wallets}</p>
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
        <div className="mt-3 rounded-lg bg-slate-100 px-2 py-1 text-xs text-slate-500 text-center font-medium">
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
            <h1 className="text-2xl font-bold text-slate-900">Planes</h1>
            <p className="text-sm text-slate-500">Gestión de planes de suscripción</p>
          </div>
        </div>
        <button
          onClick={() => setShowCreate(true)}
          className="flex items-center gap-2 rounded-xl bg-primary px-4 py-2 text-sm font-semibold text-white hover:bg-primary/90 shadow-sm"
        >
          <Plus className="h-4 w-4" /> Nuevo Plan
        </button>
      </div>

      {/* Plans grid */}
      {isLoading ? (
        <div className="text-center text-slate-400 py-12">Cargando planes...</div>
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
