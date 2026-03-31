import { useIsModuleActive } from '@/hooks/useModules'
import { ShieldX, Zap } from 'lucide-react'
import { NavLink } from 'react-router-dom'

const MODULE_LABELS: Record<string, string> = {
  inventory: 'Inventario',
  production: 'Produccion',
  logistics: 'Logistica',
  compliance: 'Cumplimiento',
  'electronic-invoicing': 'Facturacion Electronica',
}

export function ModuleGuard({ module = 'inventory', children }: { module?: string; children: React.ReactNode }) {
  const isActive = useIsModuleActive(module)

  if (!isActive) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] p-8 text-center">
        <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-slate-100 mb-4">
          <ShieldX className="h-8 w-8 text-slate-400" />
        </div>
        <h2 className="text-xl font-bold text-slate-800 mb-2">Modulo no activado</h2>
        <p className="text-sm text-slate-500 max-w-sm mb-6">
          El modulo <strong>{MODULE_LABELS[module] ?? module}</strong> no esta activo para tu organizacion.
          Un administrador puede activarlo desde el Marketplace.
        </p>
        <NavLink
          to="/marketplace"
          className="inline-flex items-center gap-2 rounded-xl bg-primary px-5 py-2.5 text-sm font-semibold text-white hover:bg-primary/90 shadow-sm transition-colors"
        >
          <Zap className="h-4 w-4" />
          Ir al Marketplace
        </NavLink>
      </div>
    )
  }

  return <>{children}</>
}
