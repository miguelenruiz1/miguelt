import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Truck, Globe, Check, ChevronRight, ArrowRight, Building2, Leaf, ShieldCheck, FileCheck, BarChart3 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { useAuthStore } from '@/store/auth'
import { userApi } from '@/lib/user-api'
import { useCustodianTypes, useCreateOrganization } from '@/hooks/useTaxonomy'
import { useActivateModule } from '@/hooks/useModules'
import { cn } from '@/lib/utils'

const STEPS = ['welcome', 'eudr', 'organization', 'complete'] as const
type Step = typeof STEPS[number]

export function OnboardingPage() {
  const navigate = useNavigate()
  const user = useAuthStore((s) => s.user)
  const setAuth = useAuthStore((s) => s.setAuth)
  const [step, setStep] = useState<Step>('welcome')
  const [loading, setLoading] = useState(false)

  // Step 3 form state
  const [orgName, setOrgName] = useState('')
  const [orgTypeId, setOrgTypeId] = useState('')
  const { data: custodianTypes } = useCustodianTypes()
  const createOrg = useCreateOrganization()
  const activateModule = useActivateModule()

  const currentIndex = STEPS.indexOf(step)

  async function goToStep(next: Step) {
    try {
      await userApi.onboarding.updateStep(next)
    } catch {
      // non-blocking
    }
    setStep(next)
  }

  async function finishOnboarding() {
    setLoading(true)
    try {
      await userApi.onboarding.complete()
      // Update local auth state
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

  async function skipAll() {
    await finishOnboarding()
  }

  async function handleEudrActivate() {
    if (!user) return
    setLoading(true)
    try {
      await activateModule.mutateAsync({ tenantId: user.tenant_id, slug: 'compliance' })
    } catch {
      // ignore — module might already be active
    } finally {
      setLoading(false)
      goToStep('organization')
    }
  }

  async function handleCreateOrg() {
    if (!orgName.trim() || !orgTypeId) return
    setLoading(true)
    try {
      await createOrg.mutateAsync({ name: orgName.trim(), custodian_type_id: orgTypeId })
    } catch {
      // ignore
    } finally {
      setLoading(false)
      goToStep('complete')
    }
  }

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      {/* Top bar */}
      <div className="border-b bg-white px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 bg-gray-900 rounded-lg flex items-center justify-center">
            <span className="text-white font-bold text-sm">T</span>
          </div>
          <span className="font-semibold text-gray-900">TraceLog</span>
        </div>
        <button
          onClick={skipAll}
          className="text-sm text-gray-500 hover:text-gray-700 transition-colors"
        >
          Saltar todo
        </button>
      </div>

      {/* Progress bar */}
      <div className="px-6 pt-8 max-w-2xl mx-auto w-full">
        <div className="flex items-center gap-1 mb-2">
          {STEPS.map((s, i) => (
            <div
              key={s}
              className={cn(
                'h-1.5 flex-1 rounded-full transition-colors duration-300',
                i <= currentIndex ? 'bg-gray-900' : 'bg-gray-200',
              )}
            />
          ))}
        </div>
        <p className="text-xs text-gray-500 text-right">
          Paso {currentIndex + 1} de {STEPS.length}
        </p>
      </div>

      {/* Content */}
      <div className="flex-1 flex items-start justify-center px-6 pt-8 pb-16">
        <div className="w-full max-w-2xl">
          {step === 'welcome' && (
            <WelcomeStep
              onDomestic={async () => {
                await finishOnboarding()
              }}
              onExport={() => goToStep('eudr')}
            />
          )}
          {step === 'eudr' && (
            <EudrStep
              loading={loading}
              onActivate={handleEudrActivate}
              onSkip={() => goToStep('organization')}
            />
          )}
          {step === 'organization' && (
            <OrganizationStep
              orgName={orgName}
              setOrgName={setOrgName}
              orgTypeId={orgTypeId}
              setOrgTypeId={setOrgTypeId}
              custodianTypes={custodianTypes ?? []}
              loading={loading}
              onCreate={handleCreateOrg}
              onSkip={() => goToStep('complete')}
            />
          )}
          {step === 'complete' && (
            <CompleteStep loading={loading} onFinish={finishOnboarding} />
          )}
        </div>
      </div>
    </div>
  )
}

// ─── Step 1: Welcome ─────────────────────────────────────────────────────────

function WelcomeStep({
  onDomestic,
  onExport,
}: {
  onDomestic: () => void
  onExport: () => void
}) {
  return (
    <div className="space-y-6">
      <div className="text-center space-y-2">
        <h1 className="text-2xl font-bold text-gray-900">
          Bienvenido a TraceLog
        </h1>
        <p className="text-gray-600">
          Cuéntanos qué necesitas para personalizar tu experiencia
        </p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mt-8">
        <button
          onClick={onDomestic}
          className="group relative bg-white border-2 border-gray-200 hover:border-gray-900 rounded-xl p-6 text-left transition-all duration-200"
        >
          <div className="flex flex-col items-center text-center gap-4">
            <div className="w-14 h-14 bg-gray-100 group-hover:bg-gray-900 rounded-xl flex items-center justify-center transition-colors">
              <Truck className="w-7 h-7 text-gray-600 group-hover:text-white transition-colors" />
            </div>
            <div>
              <h3 className="font-semibold text-gray-900 mb-1">Solo logística nacional</h3>
              <p className="text-sm text-gray-500">
                Gestiona tus cadenas de custodia, activos e inventario dentro del país
              </p>
            </div>
          </div>
          <ChevronRight className="absolute top-1/2 right-3 -translate-y-1/2 w-5 h-5 text-gray-300 group-hover:text-gray-900 transition-colors" />
        </button>

        <button
          onClick={onExport}
          className="group relative bg-white border-2 border-gray-200 hover:border-emerald-600 rounded-xl p-6 text-left transition-all duration-200"
        >
          <div className="flex flex-col items-center text-center gap-4">
            <div className="w-14 h-14 bg-emerald-50 group-hover:bg-emerald-600 rounded-xl flex items-center justify-center transition-colors">
              <Globe className="w-7 h-7 text-emerald-600 group-hover:text-white transition-colors" />
            </div>
            <div>
              <h3 className="font-semibold text-gray-900 mb-1">Exportar a Europa</h3>
              <p className="text-sm text-gray-500">
                Certifica tus cargas con EUDR y trazabilidad internacional
              </p>
            </div>
          </div>
          <ChevronRight className="absolute top-1/2 right-3 -translate-y-1/2 w-5 h-5 text-gray-300 group-hover:text-emerald-600 transition-colors" />
        </button>
      </div>
    </div>
  )
}

// ─── Step 2: EUDR Activation ─────────────────────────────────────────────────

function EudrStep({
  loading,
  onActivate,
  onSkip,
}: {
  loading: boolean
  onActivate: () => void
  onSkip: () => void
}) {
  const benefits = [
    { icon: Leaf, text: 'Cumple con la regulación EUDR de la Unión Europea' },
    { icon: ShieldCheck, text: 'Genera declaraciones de diligencia debida (DDS) automáticas' },
    { icon: FileCheck, text: 'Certificados verificables con código QR para cada carga' },
    { icon: BarChart3, text: 'Trazabilidad completa desde parcela hasta destino' },
  ]

  return (
    <div className="space-y-6">
      <div className="text-center space-y-2">
        <div className="w-14 h-14 bg-emerald-100 rounded-xl flex items-center justify-center mx-auto mb-4">
          <Globe className="w-7 h-7 text-emerald-600" />
        </div>
        <h1 className="text-2xl font-bold text-gray-900">
          Activa el Upgrade Europa
        </h1>
        <p className="text-gray-600">
          Certifica tus cargas para exportación bajo la regulación EUDR
        </p>
      </div>

      <div className="bg-white border border-gray-200 rounded-xl p-6 space-y-4">
        {benefits.map((b, i) => (
          <div key={i} className="flex items-start gap-3">
            <div className="w-8 h-8 bg-emerald-50 rounded-lg flex items-center justify-center shrink-0 mt-0.5">
              <b.icon className="w-4 h-4 text-emerald-600" />
            </div>
            <p className="text-sm text-gray-700 pt-1">{b.text}</p>
          </div>
        ))}
      </div>

      <div className="flex flex-col sm:flex-row gap-3">
        <Button
          variant="primary"
          size="lg"
          className="flex-1 bg-emerald-600 hover:bg-emerald-700"
          loading={loading}
          onClick={onActivate}
        >
          Activar ahora
          <ArrowRight className="w-4 h-4" />
        </Button>
        <Button variant="ghost" size="lg" onClick={onSkip}>
          Saltar
        </Button>
      </div>
    </div>
  )
}

// ─── Step 3: Create Organization ─────────────────────────────────────────────

function OrganizationStep({
  orgName,
  setOrgName,
  orgTypeId,
  setOrgTypeId,
  custodianTypes,
  loading,
  onCreate,
  onSkip,
}: {
  orgName: string
  setOrgName: (v: string) => void
  orgTypeId: string
  setOrgTypeId: (v: string) => void
  custodianTypes: { id: string; name: string }[]
  loading: boolean
  onCreate: () => void
  onSkip: () => void
}) {
  return (
    <div className="space-y-6">
      <div className="text-center space-y-2">
        <div className="w-14 h-14 bg-blue-100 rounded-xl flex items-center justify-center mx-auto mb-4">
          <Building2 className="w-7 h-7 text-blue-600" />
        </div>
        <h1 className="text-2xl font-bold text-gray-900">
          Registra tu primera organización
        </h1>
        <p className="text-gray-600">
          Una organización agrupa tus operaciones (finca, bodega, transporte, etc.)
        </p>
      </div>

      <div className="bg-white border border-gray-200 rounded-xl p-6 space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1.5">
            Nombre
          </label>
          <input
            type="text"
            value={orgName}
            onChange={(e) => setOrgName(e.target.value)}
            placeholder="Ej: Finca La Esperanza"
            className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-gray-500 focus:ring-1 focus:ring-gray-500 outline-none"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1.5">
            Tipo
          </label>
          <select
            value={orgTypeId}
            onChange={(e) => setOrgTypeId(e.target.value)}
            className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-gray-500 focus:ring-1 focus:ring-gray-500 outline-none bg-white"
          >
            <option value="">Selecciona un tipo...</option>
            {custodianTypes.map((t) => (
              <option key={t.id} value={t.id}>{t.name}</option>
            ))}
          </select>
        </div>
      </div>

      <div className="flex flex-col sm:flex-row gap-3">
        <Button
          variant="primary"
          size="lg"
          className="flex-1"
          loading={loading}
          disabled={!orgName.trim() || !orgTypeId}
          onClick={onCreate}
        >
          Crear organización
          <ArrowRight className="w-4 h-4" />
        </Button>
        <Button variant="ghost" size="lg" onClick={onSkip}>
          Saltar
        </Button>
      </div>
    </div>
  )
}

// ─── Step 4: Complete ────────────────────────────────────────────────────────

function CompleteStep({
  loading,
  onFinish,
}: {
  loading: boolean
  onFinish: () => void
}) {
  return (
    <div className="space-y-6 text-center">
      <div className="w-16 h-16 bg-emerald-100 rounded-full flex items-center justify-center mx-auto">
        <Check className="w-8 h-8 text-emerald-600" />
      </div>
      <div className="space-y-2">
        <h1 className="text-2xl font-bold text-gray-900">
          Todo listo
        </h1>
        <p className="text-gray-600">
          Tu cuenta está configurada. Puedes empezar a usar TraceLog ahora.
        </p>
      </div>

      <Button
        variant="primary"
        size="lg"
        loading={loading}
        onClick={onFinish}
      >
        Ir al Dashboard
        <ArrowRight className="w-4 h-4" />
      </Button>
    </div>
  )
}
