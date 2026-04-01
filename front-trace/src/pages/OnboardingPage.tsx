import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Truck, Boxes, Factory, ShieldCheck, Sparkles, FileText,
  Check, ChevronRight, ArrowRight, ArrowLeft, ShoppingCart,
  Star, Zap, Crown, CreditCard, X, Plus, Minus,
} from 'lucide-react'
import { useAuthStore } from '@/store/auth'
import { userApi } from '@/lib/user-api'
import { useActivateModule } from '@/hooks/useModules'
import { usePlans } from '@/hooks/usePlans'
import { useActiveGateway } from '@/hooks/usePayments'
import { useCheckout } from '@/hooks/useBilling'
import { useToast } from '@/store/toast'
import { cn } from '@/lib/utils'

// ─── Module catalog with marketing copy ──────────────────────────────────────

interface ModuleOption {
  slug: string
  name: string
  tagline: string
  description: string
  icon: React.ElementType
  color: string
  gradient: string
  price: number
  popular?: boolean
  features: string[]
  whoNeeds: string
}

const MODULES: ModuleOption[] = [
  {
    slug: 'logistics',
    name: 'Logistica',
    tagline: 'Sabe donde esta cada carga',
    description: 'Rastreo de activos en tiempo real con cadena de custodia inmutable.',
    icon: Truck,
    color: 'text-blue-600',
    gradient: 'from-blue-500 to-blue-600',
    price: 0,
    features: [
      'Tracking board en tiempo real',
      'Cadena de custodia con blockchain',
      'Custodios y organizaciones',
      'Workflow configurable por industria',
    ],
    whoNeeds: 'Transportistas, operadores logisticos, distribuidores',
  },
  {
    slug: 'inventory',
    name: 'Inventario',
    tagline: 'Control total de tu stock',
    description: 'Productos, bodegas, movimientos, compras y ventas con costos reales.',
    icon: Boxes,
    color: 'text-orange-600',
    gradient: 'from-orange-500 to-amber-600',
    price: 29,
    popular: true,
    features: [
      'Productos con variantes y lotes',
      'Multi-bodega con ubicaciones',
      'Compras y ventas con aprobaciones',
      'Kardex y valorizacion (FIFO/FEFO)',
    ],
    whoNeeds: 'Comercializadoras, mayoristas, retailers, fabricantes',
  },
  {
    slug: 'production',
    name: 'Produccion',
    tagline: 'De materia prima a producto terminado',
    description: 'BOM, corridas de produccion, emisiones, recibos y MRP automatico.',
    icon: Factory,
    color: 'text-violet-600',
    gradient: 'from-violet-500 to-purple-600',
    price: 39,
    features: [
      'Recetas (BOM) con versiones',
      'Corridas de produccion con costeo',
      'MRP con explosion recursiva',
      'Recursos y capacidad de planta',
    ],
    whoNeeds: 'Fabricantes, procesadores de alimentos, laboratorios',
  },
  {
    slug: 'compliance',
    name: 'Cumplimiento',
    tagline: 'Exporta sin preocupaciones',
    description: 'EUDR, USDA, FSSAI. Parcelas, registros y certificados verificables.',
    icon: ShieldCheck,
    color: 'text-emerald-600',
    gradient: 'from-emerald-500 to-green-600',
    price: 49,
    features: [
      'Certificacion EUDR automatica',
      'Gestion de parcelas con GeoJSON',
      'Certificados PDF verificables',
      'Evaluacion de riesgo por proveedor',
    ],
    whoNeeds: 'Exportadores a Europa, caficultores, agroindustria',
  },
  {
    slug: 'electronic-invoicing',
    name: 'Facturacion DIAN',
    tagline: 'Factura electronica legal',
    description: 'Facturas, notas credito y debito ante la DIAN. Resolucion automatica.',
    icon: FileText,
    color: 'text-muted-foreground',
    gradient: 'from-slate-600 to-slate-800',
    price: 19,
    features: [
      'Factura electronica DIAN',
      'Notas credito y debito',
      'Numeracion con resolucion',
      'Modo sandbox para pruebas',
    ],
    whoNeeds: 'Cualquier empresa colombiana que facture',
  },
  {
    slug: 'ai-analysis',
    name: 'Inteligencia Artificial',
    tagline: 'Decisiones basadas en datos',
    description: 'Analisis de rentabilidad con IA. Alertas de margen y recomendaciones.',
    icon: Sparkles,
    color: 'text-pink-600',
    gradient: 'from-pink-500 to-rose-600',
    price: 29,
    features: [
      'Analisis de rentabilidad por producto',
      'Alertas de margen automaticas',
      'Recomendaciones accionables',
      'Reportes generados con IA',
    ],
    whoNeeds: 'Gerentes, directores financieros, analistas',
  },
]

const STEPS = ['industry', 'modules', 'cart', 'checkout'] as const
type Step = typeof STEPS[number]

// ─── Industry presets ────────────────────────────────────────────────────────

interface Industry {
  id: string
  name: string
  icon: string
  recommended: string[]
}

const INDUSTRIES: Industry[] = [
  { id: 'coffee', name: 'Cafe / Cacao', icon: '☕', recommended: ['logistics', 'inventory', 'compliance', 'production'] },
  { id: 'agro', name: 'Agroindustria', icon: '🌿', recommended: ['logistics', 'inventory', 'compliance'] },
  { id: 'food', name: 'Alimentos', icon: '🍎', recommended: ['inventory', 'production', 'electronic-invoicing'] },
  { id: 'manufacturing', name: 'Manufactura', icon: '🏭', recommended: ['inventory', 'production', 'electronic-invoicing'] },
  { id: 'distribution', name: 'Distribucion', icon: '📦', recommended: ['logistics', 'inventory', 'electronic-invoicing'] },
  { id: 'pharma', name: 'Farmaceutico', icon: '💊', recommended: ['logistics', 'inventory', 'compliance', 'production'] },
  { id: 'retail', name: 'Retail / Comercio', icon: '🛒', recommended: ['inventory', 'electronic-invoicing', 'ai-analysis'] },
  { id: 'other', name: 'Otro', icon: '🔧', recommended: ['logistics', 'inventory'] },
]

// ─── Main Component ──────────────────────────────────────────────────────────

export function OnboardingPage() {
  const navigate = useNavigate()
  const user = useAuthStore((s) => s.user)
  const setAuth = useAuthStore((s) => s.setAuth)
  const activateModule = useActivateModule()
  const toast = useToast()

  const [step, setStep] = useState<Step>('industry')
  const [industry, setIndustry] = useState<string | null>(null)
  const [selectedModules, setSelectedModules] = useState<Set<string>>(new Set())
  const [loading, setLoading] = useState(false)

  const currentIndex = STEPS.indexOf(step)

  function selectIndustry(id: string) {
    setIndustry(id)
    const ind = INDUSTRIES.find(i => i.id === id)
    if (ind) setSelectedModules(new Set(ind.recommended))
    setStep('modules')
  }

  function toggleModule(slug: string) {
    setSelectedModules(prev => {
      const next = new Set(prev)
      if (next.has(slug)) next.delete(slug)
      else next.add(slug)
      return next
    })
  }

  const selectedList = MODULES.filter(m => selectedModules.has(m.slug))
  const monthlyTotal = selectedList.reduce((sum, m) => sum + m.price, 0)

  async function handleActivateAndFinish() {
    if (!user) return
    setLoading(true)
    try {
      // Activate all selected modules
      for (const slug of selectedModules) {
        try {
          await activateModule.mutateAsync({ tenantId: user.tenant_id, slug })
        } catch { /* ignore if already active */ }
      }

      // Mark onboarding complete
      await userApi.onboarding.complete()
      const { accessToken, refreshToken, permissions } = useAuthStore.getState()
      setAuth(
        { ...user, onboarding_completed: true, onboarding_step: 'complete' },
        accessToken!,
        refreshToken!,
        permissions,
      )

      if (monthlyTotal > 0) {
        navigate(`/checkout?modules=${Array.from(selectedModules).join(',')}`, { replace: true })
      } else {
        toast.success('Cuenta configurada')
        navigate('/', { replace: true })
      }
    } catch {
      navigate('/', { replace: true })
    } finally {
      setLoading(false)
    }
  }

  async function skipAll() {
    setLoading(true)
    try {
      await userApi.onboarding.complete()
      if (user) {
        const { accessToken, refreshToken, permissions } = useAuthStore.getState()
        setAuth(
          { ...user, onboarding_completed: true, onboarding_step: 'complete' },
          accessToken!,
          refreshToken!,
          permissions,
        )
      }
      navigate('/', { replace: true })
    } catch {
      navigate('/', { replace: true })
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-muted flex flex-col">
      {/* Top bar */}
      <div className="border-b bg-card px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 bg-gray-900 rounded-lg flex items-center justify-center">
            <span className="text-white font-bold text-sm">T</span>
          </div>
          <span className="font-semibold text-foreground">TraceLog</span>
        </div>
        <button onClick={skipAll} className="text-sm text-muted-foreground hover:text-foreground">
          Saltar todo
        </button>
      </div>

      {/* Progress */}
      <div className="px-6 pt-6 max-w-3xl mx-auto w-full">
        <div className="flex items-center gap-1 mb-1">
          {STEPS.map((_, i) => (
            <div key={i} className={cn('h-1.5 flex-1 rounded-full transition-colors', i <= currentIndex ? 'bg-gray-900' : 'bg-gray-200')} />
          ))}
        </div>
        <div className="flex justify-between text-xs text-muted-foreground">
          <span>Tu industria</span>
          <span>Modulos</span>
          <span>Resumen</span>
          <span>Pagar</span>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 flex items-start justify-center px-6 pt-6 pb-16">
        <div className="w-full max-w-3xl">
          {step === 'industry' && <IndustryStep industries={INDUSTRIES} onSelect={selectIndustry} />}
          {step === 'modules' && (
            <ModulesStep
              modules={MODULES}
              selected={selectedModules}
              industry={INDUSTRIES.find(i => i.id === industry)}
              onToggle={toggleModule}
              onBack={() => setStep('industry')}
              onNext={() => setStep('cart')}
            />
          )}
          {step === 'cart' && (
            <CartStep
              selected={selectedList}
              total={monthlyTotal}
              onRemove={(slug) => toggleModule(slug)}
              onBack={() => setStep('modules')}
              onCheckout={handleActivateAndFinish}
              loading={loading}
            />
          )}
        </div>
      </div>
    </div>
  )
}

// ─── Step 1: Industry ────────────────────────────────────────────────────────

function IndustryStep({ industries, onSelect }: { industries: Industry[]; onSelect: (id: string) => void }) {
  return (
    <div className="space-y-6">
      <div className="text-center space-y-2">
        <h1 className="text-2xl font-bold text-foreground">A que se dedica tu empresa?</h1>
        <p className="text-muted-foreground">Te recomendaremos los modulos ideales para tu industria</p>
      </div>
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        {industries.map(ind => (
          <button
            key={ind.id}
            onClick={() => onSelect(ind.id)}
            className="group bg-card border-2 border-border hover:border-gray-900 rounded-xl p-4 text-center transition-all"
          >
            <div className="text-3xl mb-2">{ind.icon}</div>
            <p className="text-sm font-semibold text-foreground">{ind.name}</p>
            <p className="text-[10px] text-muted-foreground mt-1">{ind.recommended.length} modulos recomendados</p>
          </button>
        ))}
      </div>
    </div>
  )
}

// ─── Step 2: Module Selection ────────────────────────────────────────────────

function ModulesStep({
  modules, selected, industry, onToggle, onBack, onNext,
}: {
  modules: ModuleOption[]
  selected: Set<string>
  industry?: Industry
  onToggle: (slug: string) => void
  onBack: () => void
  onNext: () => void
}) {
  const total = modules.filter(m => selected.has(m.slug)).reduce((s, m) => s + m.price, 0)

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <button onClick={onBack} className="flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground">
          <ArrowLeft className="h-4 w-4" /> Cambiar industria
        </button>
        {industry && (
          <span className="text-sm text-muted-foreground">
            {industry.icon} {industry.name}
          </span>
        )}
      </div>

      <div className="text-center space-y-2">
        <h1 className="text-2xl font-bold text-foreground">Arma tu plan</h1>
        <p className="text-muted-foreground">Selecciona los modulos que necesitas. Puedes cambiarlos despues.</p>
      </div>

      <div className="space-y-3">
        {modules.map(mod => {
          const isSelected = selected.has(mod.slug)
          const isRecommended = industry?.recommended.includes(mod.slug)
          const Icon = mod.icon

          return (
            <button
              key={mod.slug}
              onClick={() => onToggle(mod.slug)}
              className={cn(
                'w-full flex items-center gap-4 rounded-2xl border-2 p-4 text-left transition-all',
                isSelected
                  ? 'border-gray-900 bg-muted'
                  : 'border-border bg-card hover:border-gray-300',
              )}
            >
              <div className={cn('h-12 w-12 rounded-xl bg-gradient-to-br flex items-center justify-center shrink-0', mod.gradient)}>
                <Icon className="h-6 w-6 text-white" />
              </div>

              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <h3 className="text-sm font-bold text-foreground">{mod.name}</h3>
                  {isRecommended && (
                    <span className="inline-flex items-center gap-1 rounded-full bg-amber-50 px-2 py-0.5 text-[10px] font-bold text-amber-700">
                      <Star className="h-3 w-3" /> Recomendado
                    </span>
                  )}
                  {mod.popular && (
                    <span className="inline-flex items-center gap-1 rounded-full bg-blue-50 px-2 py-0.5 text-[10px] font-bold text-blue-700">
                      <Zap className="h-3 w-3" /> Popular
                    </span>
                  )}
                </div>
                <p className="text-xs text-muted-foreground mt-0.5">{mod.tagline}</p>
              </div>

              <div className="text-right shrink-0">
                <p className="text-lg font-bold text-foreground">
                  {mod.price === 0 ? 'Gratis' : `$${mod.price}`}
                </p>
                {mod.price > 0 && <p className="text-[10px] text-muted-foreground">/mes</p>}
              </div>

              <div className={cn(
                'h-6 w-6 rounded-full border-2 flex items-center justify-center shrink-0 transition-colors',
                isSelected ? 'border-gray-900 bg-gray-900' : 'border-gray-300',
              )}>
                {isSelected && <Check className="h-4 w-4 text-white" />}
              </div>
            </button>
          )
        })}
      </div>

      {/* Sticky bottom */}
      <div className="sticky bottom-0 bg-muted pt-4 pb-2">
        <button
          onClick={onNext}
          disabled={selected.size === 0}
          className="w-full flex items-center justify-center gap-3 bg-gray-900 text-white rounded-xl px-6 py-4 text-sm font-semibold hover:bg-gray-800 disabled:opacity-40 transition-colors"
        >
          <ShoppingCart className="h-5 w-5" />
          Ver resumen — {total === 0 ? 'Gratis' : `$${total}/mes`}
          <ArrowRight className="h-4 w-4" />
        </button>
      </div>
    </div>
  )
}

// ─── Step 3: Cart ────────────────────────────────────────────────────────────

function CartStep({
  selected, total, onRemove, onBack, onCheckout, loading,
}: {
  selected: ModuleOption[]
  total: number
  onRemove: (slug: string) => void
  onBack: () => void
  onCheckout: () => void
  loading: boolean
}) {
  return (
    <div className="space-y-6">
      <button onClick={onBack} className="flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground">
        <ArrowLeft className="h-4 w-4" /> Agregar mas modulos
      </button>

      <div className="text-center space-y-2">
        <h1 className="text-2xl font-bold text-foreground">Tu plan TraceLog</h1>
        <p className="text-muted-foreground">{selected.length} modulo{selected.length !== 1 ? 's' : ''} seleccionado{selected.length !== 1 ? 's' : ''}</p>
      </div>

      {/* Cart items */}
      <div className="bg-card rounded-2xl border border-border overflow-hidden divide-y divide-gray-100">
        {selected.map(mod => {
          const Icon = mod.icon
          return (
            <div key={mod.slug} className="flex items-center gap-4 px-5 py-4">
              <div className={cn('h-10 w-10 rounded-xl bg-gradient-to-br flex items-center justify-center shrink-0', mod.gradient)}>
                <Icon className="h-5 w-5 text-white" />
              </div>
              <div className="flex-1 min-w-0">
                <h3 className="text-sm font-semibold text-foreground">{mod.name}</h3>
                <p className="text-xs text-muted-foreground">{mod.tagline}</p>
              </div>
              <p className="text-sm font-bold text-foreground shrink-0">
                {mod.price === 0 ? 'Gratis' : `$${mod.price}/mes`}
              </p>
              <button
                onClick={() => onRemove(mod.slug)}
                className="text-gray-300 hover:text-red-500 transition-colors shrink-0"
              >
                <X className="h-4 w-4" />
              </button>
            </div>
          )
        })}
      </div>

      {/* Summary */}
      <div className="bg-gray-900 text-white rounded-2xl p-6 space-y-4">
        <div className="flex items-center justify-between">
          <span className="text-muted-foreground">Subtotal mensual</span>
          <span className="text-lg font-bold">${total} USD</span>
        </div>
        {total === 0 && (
          <p className="text-xs text-muted-foreground">Plan gratuito — sin tarjeta de credito requerida</p>
        )}
        {total > 0 && (
          <>
            <div className="flex items-center justify-between text-sm">
              <span className="text-muted-foreground">Pago anual (20% dto)</span>
              <span className="font-semibold text-emerald-400">${Math.round(total * 12 * 0.8)} USD/ano</span>
            </div>
            <p className="text-xs text-muted-foreground">
              Ahorras ${Math.round(total * 12 * 0.2)} USD al ano con pago anual
            </p>
          </>
        )}
      </div>

      {/* Features included */}
      <div className="bg-card rounded-2xl border border-border p-5">
        <h3 className="text-sm font-semibold text-foreground mb-3">Incluido en todos los planes</h3>
        <div className="grid grid-cols-2 gap-2">
          {[
            'HTTPS y SSL automatico',
            'Multi-usuario con roles',
            'Soporte por email',
            'Actualizaciones gratuitas',
            'Datos en la nube (GCP)',
            'Backups diarios automaticos',
          ].map(f => (
            <div key={f} className="flex items-center gap-2 text-xs text-muted-foreground">
              <Check className="h-3.5 w-3.5 text-emerald-500 shrink-0" />
              {f}
            </div>
          ))}
        </div>
      </div>

      {/* CTA */}
      <button
        onClick={onCheckout}
        disabled={loading || selected.length === 0}
        className="w-full flex items-center justify-center gap-3 bg-gray-900 text-white rounded-xl px-6 py-4 text-sm font-semibold hover:bg-gray-800 disabled:opacity-40 transition-colors"
      >
        {loading ? (
          <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white" />
        ) : total === 0 ? (
          <>
            <Zap className="h-5 w-5" />
            Empezar gratis
          </>
        ) : (
          <>
            <CreditCard className="h-5 w-5" />
            Continuar al pago — ${total}/mes
          </>
        )}
      </button>

      <p className="text-center text-xs text-muted-foreground">
        Puedes cancelar o cambiar tu plan en cualquier momento
      </p>
    </div>
  )
}
