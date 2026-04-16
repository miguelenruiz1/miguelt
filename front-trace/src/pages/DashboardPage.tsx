import { Layers, Rocket, Package, Boxes, Users, CreditCard, Settings, ChevronRight, Box, Wallet } from 'lucide-react'
import { Link } from 'react-router-dom'
import { cn } from '@/lib/utils'
import { useAuthStore } from '@/store/auth'
import { useIsModuleActive } from '@/hooks/useModules'
import { useUsageSummary } from '@/hooks/useBilling'
import type { UsageCounter } from '@/types/subscription'

function UsageKpi({ counter, label, icon: Icon, gradient }: { counter?: { current: number; limit: number; percentage?: number }; label: string; icon: React.ElementType; gradient: string }) {
  if (!counter) return null
  const pct = counter.limit > 0 ? Math.min(100, (counter.current / counter.limit) * 100) : 0
  const barColor = pct >= 90 ? 'bg-red-300' : pct >= 70 ? 'bg-amber-300' : 'bg-card/40'
  const limitLabel = counter.limit < 0 ? 'Ilimitado' : counter.limit === 0 ? '—' : counter.limit.toLocaleString('es-CO')

  return (
    <div className={cn('relative rounded-2xl p-5 text-white overflow-hidden', gradient)}>
      <div className="absolute -right-3 -top-3 opacity-10">
        <Icon className="h-24 w-24" />
      </div>
      <p className="text-xs font-medium opacity-80 uppercase tracking-wider">{label}</p>
      <p className="text-2xl font-extrabold mt-1">{counter.current.toLocaleString('es-CO')}</p>
      <p className="text-[11px] opacity-70 mt-0.5">de {limitLabel}</p>
      <div className="mt-2 h-1.5 w-full rounded-full bg-card/20 overflow-hidden">
        <div
          className={cn('h-full rounded-full transition-all', barColor)}
          style={{ width: counter.limit < 0 ? '5%' : `${pct}%` }}
        />
      </div>
    </div>
  )
}

export function DashboardPage() {
  const user = useAuthStore((s) => s.user)
  const tenantId = user?.tenant_id ?? 'default'
  const { data: usage } = useUsageSummary(tenantId)
  const isLogisticsActive = useIsModuleActive('logistics')
  const isInventoryActive = useIsModuleActive('inventory')

  const shortcuts = [
    isLogisticsActive && { to: '/tracking', icon: Package, label: 'Panel de Seguimiento', desc: 'Cadena de custodia y trazabilidad en tiempo real', color: 'bg-blue-500' },
    isInventoryActive && { to: '/inventario', icon: Boxes, label: 'Inventario', desc: 'Productos, bodegas y movimientos', color: 'bg-emerald-500' },
    { to: '/marketplace', icon: Layers, label: 'Marketplace', desc: 'Explora y activa módulos', color: 'bg-primary' },
    { to: '/equipo/usuarios', icon: Users, label: 'Mi Equipo', desc: 'Usuarios, roles y permisos', color: 'bg-violet-500' },
    { to: '/empresa/suscripcion', icon: CreditCard, label: 'Mi Suscripción', desc: 'Plan, facturación y período', color: 'bg-amber-500' },
    { to: '/profile', icon: Settings, label: 'Mi Perfil', desc: 'Datos personales y contraseña', color: 'bg-muted0' },
  ].filter(Boolean) as { to: string; icon: React.ElementType; label: string; desc: string; color: string }[]

  return (
    <div className="space-y-6">
      {/* Breadcrumb */}
      <nav className="mb-4">
        <ol className="flex items-center gap-2 text-sm">
          <li className="text-muted-foreground">Inicio</li>
          <li><ChevronRight className="h-4 w-4 text-muted-foreground" /></li>
          <li className="text-primary">Dashboard</li>
        </ol>
      </nav>

      {/* Welcome */}
      <div className="flex items-center gap-5">
        <div className="flex h-14 w-14 items-center justify-center rounded-xl bg-primary shadow-md shrink-0">
          <Rocket className="h-7 w-7 text-white" />
        </div>
        <div>
          <h1 className="text-2xl font-bold text-foreground">
            Hola, {user?.full_name?.split(' ')[0] ?? 'usuario'}
          </h1>
          <p className="text-sm text-muted-foreground mt-0.5">Bienvenido a TraceLog</p>
        </div>
      </div>

      {/* Usage summary */}
      {usage && (
        <div>
          <h2 className="text-sm font-medium text-muted-foreground uppercase tracking-wide mb-4">Tu plan: {usage.plan_name}</h2>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
            <div className="relative rounded-2xl p-5 text-white overflow-hidden bg-gradient-to-br from-primary to-emerald-600">
              <div className="absolute -right-3 -top-3 opacity-10">
                <CreditCard className="h-24 w-24" />
              </div>
              <p className="text-xs font-medium opacity-80 uppercase tracking-wider">Plan</p>
              <p className="text-2xl font-extrabold mt-1">{usage.plan_name}</p>
              <Link to="/settings/billing" className="text-[10px] opacity-60 mt-2 underline block">Ver detalles →</Link>
            </div>
            <UsageKpi counter={usage.users} label="Usuarios" icon={Users} gradient="bg-gradient-to-br from-violet-500 to-violet-600" />
            <UsageKpi counter={(usage as any).assets_this_month ?? (usage as any).assets} label="Cargas este mes" icon={Box} gradient="bg-gradient-to-br from-emerald-500 to-emerald-600" />
            <UsageKpi counter={usage.wallets} label="Wallets" icon={Wallet} gradient="bg-gradient-to-br from-amber-500 to-amber-600" />
          </div>
        </div>
      )}

      {/* Quick access grid */}
      <div>
        <h2 className="text-sm font-medium text-muted-foreground uppercase tracking-wide mb-4">Acceso rapido</h2>
        <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 xl:grid-cols-3">
          {shortcuts.map(({ to, icon: Icon, label, desc, color }) => (
            <Link
              key={to}
              to={to}
              className="group flex items-start gap-4 rounded-2xl border border-border bg-card p-5  hover:shadow-md hover:border-gray-300 transition-all"
            >
              <div className={`flex h-10 w-10 items-center justify-center rounded-xl ${color} shrink-0`}>
                <Icon className="h-5 w-5 text-white" />
              </div>
              <div className="min-w-0">
                <p className="text-sm font-semibold text-foreground group-hover:text-primary transition-colors">{label}</p>
                <p className="text-xs text-muted-foreground mt-0.5">{desc}</p>
              </div>
            </Link>
          ))}
        </div>
      </div>
    </div>
  )
}
