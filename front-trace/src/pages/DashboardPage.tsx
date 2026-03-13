import { Layers, Rocket, Package, Boxes, Users, CreditCard, Settings, ChevronRight } from 'lucide-react'
import { Link } from 'react-router-dom'
import { useAuthStore } from '@/store/auth'
import { useIsModuleActive } from '@/hooks/useModules'

export function DashboardPage() {
  const user = useAuthStore((s) => s.user)
  const isLogisticsActive = useIsModuleActive('logistics')
  const isInventoryActive = useIsModuleActive('inventory')

  const shortcuts = [
    isLogisticsActive && { to: '/tracking', icon: Package, label: 'Panel de Seguimiento', desc: 'Cadena de custodia y trazabilidad en tiempo real', color: 'bg-blue-500' },
    isInventoryActive && { to: '/inventario', icon: Boxes, label: 'Inventario', desc: 'Productos, bodegas y movimientos', color: 'bg-emerald-500' },
    { to: '/marketplace', icon: Layers, label: 'Marketplace', desc: 'Explora y activa módulos', color: 'bg-indigo-500' },
    { to: '/equipo/usuarios', icon: Users, label: 'Mi Equipo', desc: 'Usuarios, roles y permisos', color: 'bg-violet-500' },
    { to: '/empresa/suscripcion', icon: CreditCard, label: 'Mi Suscripción', desc: 'Plan, facturación y período', color: 'bg-amber-500' },
    { to: '/profile', icon: Settings, label: 'Mi Perfil', desc: 'Datos personales y contraseña', color: 'bg-gray-500' },
  ].filter(Boolean) as { to: string; icon: React.ElementType; label: string; desc: string; color: string }[]

  return (
    <div className="space-y-6">
      {/* Breadcrumb */}
      <nav className="mb-4">
        <ol className="flex items-center gap-2 text-sm">
          <li className="text-gray-500">Inicio</li>
          <li><ChevronRight className="h-4 w-4 text-gray-400" /></li>
          <li className="text-indigo-500">Dashboard</li>
        </ol>
      </nav>

      {/* Welcome */}
      <div className="flex items-center gap-5">
        <div className="flex h-14 w-14 items-center justify-center rounded-xl bg-indigo-500 shadow-md shrink-0">
          <Rocket className="h-7 w-7 text-white" />
        </div>
        <div>
          <h1 className="text-2xl font-bold text-gray-800">
            Hola, {user?.full_name?.split(' ')[0] ?? 'usuario'}
          </h1>
          <p className="text-sm text-gray-500 mt-0.5">Bienvenido a TraceLog</p>
        </div>
      </div>

      {/* Quick access grid */}
      <div>
        <h2 className="text-sm font-medium text-gray-500 uppercase tracking-wide mb-4">Acceso rapido</h2>
        <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 xl:grid-cols-3">
          {shortcuts.map(({ to, icon: Icon, label, desc, color }) => (
            <Link
              key={to}
              to={to}
              className="group flex items-start gap-4 rounded-2xl border border-gray-200 bg-white p-5 shadow-sm hover:shadow-md hover:border-gray-300 transition-all"
            >
              <div className={`flex h-10 w-10 items-center justify-center rounded-xl ${color} shrink-0`}>
                <Icon className="h-5 w-5 text-white" />
              </div>
              <div className="min-w-0">
                <p className="text-sm font-semibold text-gray-800 group-hover:text-indigo-700 transition-colors">{label}</p>
                <p className="text-xs text-gray-500 mt-0.5">{desc}</p>
              </div>
            </Link>
          ))}
        </div>
      </div>
    </div>
  )
}
