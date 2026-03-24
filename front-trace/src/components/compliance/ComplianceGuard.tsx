import { useIsModuleActive } from '@/hooks/useModules'
import { ShieldCheck, Zap } from 'lucide-react'
import { NavLink } from 'react-router-dom'

export function ComplianceGuard({ children }: { children: React.ReactNode }) {
  const isActive = useIsModuleActive('compliance')

  if (!isActive) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] p-8 text-center">
        <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-emerald-50 mb-4">
          <ShieldCheck className="h-8 w-8 text-emerald-400" />
        </div>
        <h2 className="text-xl font-bold text-slate-800 mb-2">Upgrade Europa</h2>
        <p className="text-sm text-slate-500 max-w-sm mb-6">
          Activa el módulo de <strong>Cumplimiento Normativo</strong> para certificar tus cargas para exportación a la Unión Europea.
        </p>
        <NavLink
          to="/marketplace"
          className="inline-flex items-center gap-2 rounded-xl bg-emerald-600 px-5 py-2.5 text-sm font-semibold text-white hover:bg-emerald-700 shadow-sm transition-colors"
        >
          <Zap className="h-4 w-4" />
          Ir al Marketplace
        </NavLink>
      </div>
    )
  }

  return <>{children}</>
}
