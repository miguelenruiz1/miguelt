import { useFeatureToggles } from '@/hooks/useInventory'
import { useNavigate } from 'react-router-dom'
import { Lock } from 'lucide-react'

/**
 * Wraps a page that requires a specific feature toggle to be active.
 * If the feature is disabled, shows a message instead of the page.
 */
export function FeatureGuard({ feature, children }: { feature: string; children: React.ReactNode }) {
  const { data: features, isLoading } = useFeatureToggles()
  const navigate = useNavigate()

  if (isLoading) return null

  if (features?.[feature] === false) {
    return (
      <div className="flex flex-col items-center justify-center py-32 text-center">
        <div className="h-14 w-14 rounded-2xl bg-secondary flex items-center justify-center mb-4">
          <Lock className="h-7 w-7 text-muted-foreground" />
        </div>
        <h2 className="text-lg font-semibold text-foreground">Funcionalidad desactivada</h2>
        <p className="text-sm text-muted-foreground mt-1 max-w-sm">
          Esta funcionalidad no esta habilitada para tu negocio. Puedes activarla desde Configuracion.
        </p>
        <button
          onClick={() => navigate('/inventario/configuracion/funcionalidades')}
          className="mt-4 px-4 py-2 text-sm font-medium bg-gray-900 text-white rounded-xl hover:bg-gray-800 transition-colors"
        >
          Ir a Configuracion
        </button>
      </div>
    )
  }

  return <>{children}</>
}
