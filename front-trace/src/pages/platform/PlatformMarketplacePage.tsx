import { Link } from 'react-router-dom'
import { ArrowLeft, Layers, Building2, Package, Boxes, Truck } from 'lucide-react'
import { usePlatformDashboard } from '@/hooks/usePlatform'

const MODULE_META: Record<string, { name: string; description: string; icon: React.ElementType; color: string }> = {
  logistics: {
    name: 'Logistica',
    description: 'Cadena de custodia, tracking board, activos NFT, wallets y organizaciones.',
    icon: Truck,
    color: 'from-indigo-500 to-blue-600',
  },
  inventory: {
    name: 'Inventario',
    description: 'Productos, bodegas, movimientos, proveedores, compras, seriales, lotes y produccion.',
    icon: Boxes,
    color: 'from-orange-500 to-amber-600',
  },
}

export function PlatformMarketplacePage() {
  const { data, isLoading } = usePlatformDashboard()

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600" />
      </div>
    )
  }

  const moduleAdoption = data?.module_adoption ?? []

  return (
    <div className="space-y-6">
      <div>
        <Link to="/platform" className="inline-flex items-center gap-1 text-sm text-slate-500 hover:text-indigo-600 mb-2">
          <ArrowLeft className="h-4 w-4" /> Panel
        </Link>
        <h1 className="text-2xl font-bold text-slate-900">Gestion del Marketplace</h1>
        <p className="text-sm text-slate-500 mt-1">
          Modulos disponibles en el marketplace. Cada empresa puede activar/desactivar modulos desde su panel.
        </p>
      </div>

      {/* Module cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {Object.entries(MODULE_META).map(([slug, meta]) => {
          const adoption = moduleAdoption.find(m => m.slug === slug)
          const Icon = meta.icon
          return (
            <div key={slug} className="bg-white rounded-2xl border border-slate-200/60 shadow-sm overflow-hidden">
              <div className={`h-2 bg-gradient-to-r ${meta.color}`} />
              <div className="p-6">
                <div className="flex items-center gap-4 mb-4">
                  <div className={`h-12 w-12 rounded-2xl bg-gradient-to-br ${meta.color} flex items-center justify-center`}>
                    <Icon className="h-6 w-6 text-white" />
                  </div>
                  <div>
                    <h3 className="text-lg font-bold text-slate-900">{meta.name}</h3>
                    <p className="text-xs text-slate-500">Slug: <code className="bg-slate-100 px-1 rounded">{slug}</code></p>
                  </div>
                </div>
                <p className="text-sm text-slate-600 mb-4">{meta.description}</p>

                {/* Stats */}
                <div className="grid grid-cols-2 gap-4">
                  <div className="bg-slate-50 rounded-xl p-4 text-center">
                    <div className="text-2xl font-bold text-slate-900">{adoption?.active_tenants ?? 0}</div>
                    <div className="text-xs text-slate-500 flex items-center justify-center gap-1 mt-1">
                      <Building2 className="h-3 w-3" /> Empresas activas
                    </div>
                  </div>
                  <div className="bg-slate-50 rounded-xl p-4 text-center">
                    <div className="text-2xl font-bold text-emerald-600">
                      {data?.total_tenants
                        ? `${Math.round(((adoption?.active_tenants ?? 0) / data.total_tenants) * 100)}%`
                        : '0%'}
                    </div>
                    <div className="text-xs text-slate-500 mt-1">Tasa de adopcion</div>
                  </div>
                </div>
              </div>
            </div>
          )
        })}
      </div>

      {/* Info box */}
      <div className="bg-indigo-50 border border-indigo-200 rounded-2xl p-5">
        <h4 className="text-sm font-semibold text-indigo-800 mb-1">Nota sobre modulos</h4>
        <p className="text-sm text-indigo-700">
          Actualmente, los administradores de cada empresa pueden activar/desactivar modulos libremente desde el Marketplace de su tenant.
          Cuando se implemente la pasarela de pago, la activacion de modulos premium estara vinculada al plan de suscripcion contratado.
        </p>
      </div>
    </div>
  )
}
