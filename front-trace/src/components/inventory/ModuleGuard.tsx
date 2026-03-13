import { useIsModuleActive } from '@/hooks/useModules'
import { ShieldX, Zap } from 'lucide-react'
import { NavLink } from 'react-router-dom'

export function ModuleGuard({ children }: { children: React.ReactNode }) {
  const isActive = useIsModuleActive('inventory')

  if (!isActive) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] p-8 text-center">
        <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-slate-100 mb-4">
          <ShieldX className="h-8 w-8 text-slate-400" />
        </div>
        <h2 className="text-xl font-bold text-slate-800 mb-2">Módulo no activado</h2>
        <p className="text-sm text-slate-500 max-w-sm mb-6">
          El módulo <strong>Inventario</strong> no está activo para tu organización.
          Un administrador puede activarlo desde el Marketplace.
        </p>
        <NavLink
          to="/marketplace"
          className="inline-flex items-center gap-2 rounded-xl bg-indigo-600 px-5 py-2.5 text-sm font-semibold text-white hover:bg-indigo-700 shadow-sm transition-colors"
        >
          <Zap className="h-4 w-4" />
          Ir al Marketplace
        </NavLink>
      </div>
    )
  }

  return <>{children}</>
}
