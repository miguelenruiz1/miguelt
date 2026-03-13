import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Truck, Package, ClipboardList, BarChart3, Layers, CheckCircle2, XCircle, CreditCard, AlertTriangle,
  ChevronRight, FileText, FlaskConical,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { useAuthStore } from '@/store/auth'
import { useTenantModules, useActivateModule, useDeactivateModule } from '@/hooks/useModules'

const MODULE_ICONS: Record<string, React.ElementType> = {
  logistics: Truck,
  inventory: Package,
  'electronic-invoicing': FileText,
  'electronic-invoicing-sandbox': FlaskConical,
  audit: ClipboardList,
  analytics: BarChart3,
}

const MODULE_COLORS: Record<string, { bg: string; text: string }> = {
  logistics:              { bg: 'bg-indigo-50',  text: 'text-indigo-600' },
  inventory:              { bg: 'bg-emerald-50', text: 'text-emerald-600' },
  'electronic-invoicing': { bg: 'bg-cyan-50',    text: 'text-cyan-600' },
  'electronic-invoicing-sandbox': { bg: 'bg-amber-50', text: 'text-amber-600' },
  audit:                  { bg: 'bg-amber-50',   text: 'text-amber-600' },
  analytics:              { bg: 'bg-purple-50',  text: 'text-purple-600' },
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
        checked ? 'bg-indigo-500' : 'bg-gray-200',
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

export function MarketplacePage() {
  const navigate = useNavigate()
  const user = useAuthStore((s) => s.user)
  const hasPermission = useAuthStore((s) => s.hasPermission)
  const canManage = hasPermission('subscription.manage')
  const tenantId = user?.tenant_id ?? 'default'

  const { data: modules = [], isLoading, isError, error: fetchError } = useTenantModules(tenantId)
  const activateMut = useActivateModule()
  const deactivateMut = useDeactivateModule()

  const [toggling, setToggling] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [activatedModule, setActivatedModule] = useState<{ slug: string; name: string } | null>(null)

  async function handleToggle(slug: string, isActive: boolean, name: string) {
    setToggling(slug)
    setError(null)
    try {
      if (isActive) {
        await deactivateMut.mutateAsync({ tenantId, slug })
      } else {
        await activateMut.mutateAsync({ tenantId, slug })
        setActivatedModule({ slug, name })
      }
    } catch (e: any) {
      setError(e?.message ?? 'Error al cambiar estado del módulo')
    } finally {
      setToggling(null)
    }
  }

  return (
    <div className="space-y-6">
      {/* Breadcrumb */}
      <nav className="mb-4">
        <ol className="flex items-center gap-2 text-sm">
          <li className="text-gray-500">Inicio</li>
          <li><ChevronRight className="h-4 w-4 text-gray-400" /></li>
          <li className="text-indigo-500">Marketplace</li>
        </ol>
      </nav>

      {/* Header */}
      <div>
        <h1 className="text-2xl font-semibold text-gray-800">Marketplace de Módulos</h1>
        <p className="text-sm text-gray-500 mt-1">Activa o desactiva módulos para tu organización</p>
      </div>

      {/* Error alert */}
      {(error || isError) && (
        <div className="flex items-center gap-2 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          <XCircle className="h-4 w-4 shrink-0" />
          {error ?? (fetchError as Error)?.message ?? 'No se pudieron cargar los módulos. Verifica que el servicio está corriendo.'}
          <button onClick={() => setError(null)} className="ml-auto text-gray-400 hover:text-gray-600">
            <XCircle className="h-4 w-4" />
          </button>
        </div>
      )}

      {/* Grid */}
      {isLoading ? (
        <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 xl:grid-cols-3">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="h-52 rounded-2xl border border-gray-200 bg-gray-50 animate-pulse" />
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 xl:grid-cols-3">
          {modules.map((mod) => {
            const Icon = MODULE_ICONS[mod.slug] ?? Package
            const colors = MODULE_COLORS[mod.slug] ?? { bg: 'bg-gray-50', text: 'text-gray-600' }
            const isActive = mod.is_active
            const isToggling = toggling === mod.slug
            const requiresSlug = mod.requires as string | undefined
            const depMissing = requiresSlug
              ? !modules.find(m => m.slug === requiresSlug)?.is_active
              : false

            return (
              <div
                key={mod.slug}
                className="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm"
              >
                {/* Top: icon + toggle */}
                <div className="flex items-start justify-between">
                  <div className={cn('flex h-[50px] w-[50px] items-center justify-center rounded-xl', colors.bg)}>
                    <Icon className={cn('h-6 w-6', colors.text)} />
                  </div>
                  {canManage && (
                    <Toggle
                      checked={isActive}
                      disabled={isToggling || (depMissing && !isActive)}
                      title={depMissing && !isActive ? `Activa ${requiresSlug} primero` : isActive ? 'Desactivar módulo' : 'Activar módulo'}
                      onChange={() => handleToggle(mod.slug, isActive, mod.name)}
                    />
                  )}
                </div>

                {/* Title + badge */}
                <div className="mt-4 flex items-center gap-2">
                  <h3 className="text-sm font-semibold text-gray-800">{mod.name}</h3>
                  {isActive ? (
                    <span className="inline-flex items-center gap-1 rounded-full bg-emerald-50 px-2 py-0.5 text-[10px] font-semibold text-emerald-600">
                      <CheckCircle2 className="h-3 w-3" /> Activo
                    </span>
                  ) : (
                    <span className="inline-flex items-center gap-1 rounded-full bg-gray-100 px-2 py-0.5 text-[10px] font-semibold text-gray-500">
                      Inactivo
                    </span>
                  )}
                </div>
                <p className="text-xs text-gray-400 mt-0.5 capitalize">{mod.slug}</p>

                {/* Description */}
                <p className="mt-2 text-sm text-gray-500 leading-relaxed">{mod.description}</p>

                {/* Dependency warning */}
                {requiresSlug && depMissing && !isActive && (
                  <div className="mt-3 flex items-center gap-2 rounded-lg bg-amber-50 border border-amber-200 px-3 py-2">
                    <AlertTriangle className="h-3.5 w-3.5 text-amber-500 shrink-0" />
                    <p className="text-xs text-amber-700">
                      Requiere el módulo <span className="font-semibold capitalize">{requiresSlug}</span> activo
                    </p>
                  </div>
                )}

                {/* Footer */}
                {!canManage && (
                  <p className="mt-3 text-xs text-gray-400 border-t border-gray-100 pt-3">
                    Contacta a un administrador para activar este módulo.
                  </p>
                )}
              </div>
            )
          })}
        </div>
      )}

      {/* Post-activation popup */}
      {activatedModule && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4" role="dialog" aria-modal="true">
          <div className="absolute inset-0 bg-gray-900/50" onClick={() => setActivatedModule(null)} />
          <div className="relative w-full max-w-sm rounded-2xl border border-gray-200 bg-white p-8 shadow-xl text-center space-y-5">
            <div className="flex justify-center">
              <div className="flex h-14 w-14 items-center justify-center rounded-full bg-emerald-50">
                <CheckCircle2 className="h-7 w-7 text-emerald-500" />
              </div>
            </div>
            <div>
              <h2 className="text-lg font-semibold text-gray-800">¡Módulo habilitado!</h2>
              <p className="mt-2 text-sm text-gray-500 leading-relaxed">
                <span className="font-medium text-gray-800">"{activatedModule.name}"</span> está listo.
                Completa el pago de tu suscripción para mantener el acceso.
              </p>
            </div>
            <div className="flex flex-col gap-2.5">
              <button
                onClick={() => {
                  const slug = activatedModule.slug
                  setActivatedModule(null)
                  navigate(`/checkout?module=${slug}`)
                }}
                className="flex w-full items-center justify-center gap-2 rounded-lg bg-indigo-500 px-5 py-3 text-sm font-medium text-white shadow-sm transition hover:bg-indigo-600"
              >
                <CreditCard className="h-4 w-4" />
                Completar suscripción
              </button>
              <button
                onClick={() => setActivatedModule(null)}
                className="rounded-lg border border-gray-300 px-5 py-2.5 text-sm font-medium text-gray-700 transition hover:bg-gray-50"
              >
                Hacerlo después
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
