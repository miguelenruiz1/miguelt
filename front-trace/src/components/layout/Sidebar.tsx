import { useState } from 'react'
import { NavLink } from 'react-router-dom'
import {
  LayoutDashboard, Wallet, Package, Activity, Building2, Kanban, FileText, FolderTree,
  Settings, ChevronDown, HelpCircle, BookOpen, Users, Shield, ClipboardList, ClipboardCheck,
  LogOut, CreditCard, Layers, Boxes, Warehouse, ArrowLeftRight, Truck, ShoppingCart,
  Settings2, FileDown, Banknote, AlertTriangle, Hash, FlaskConical, Factory, Mail, Send,
  Crown, BarChart3, Store, TrendingUp, UserCog, UserPlus, Receipt,
  UserCheck, ShoppingBag, DollarSign, Bell, BookOpen as BookOpenIcon, Palette,
  Building, Globe, ScanBarcode, PackageCheck, RefreshCw,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { useLiveness } from '@/hooks/useHealth'
import { useAuthStore } from '@/store/auth'
import { useLogout } from '@/hooks/useAuth'
import { useIsModuleActive } from '@/hooks/useModules'

const topItems = [
  { to: '/marketplace', icon: Layers, label: 'Marketplace' },
  { to: '/', icon: LayoutDashboard, label: 'Dashboard' },
]

const inventarioItems = [
  { to: '/inventario', icon: Boxes, label: 'Dashboard', permission: 'inventory.view' },
  { to: '/inventario/productos', icon: Package, label: 'Productos', permission: 'inventory.view' },
  { to: '/inventario/bodegas', icon: Warehouse, label: 'Bodegas', permission: 'inventory.view' },
  { to: '/inventario/movimientos', icon: ArrowLeftRight, label: 'Movimientos', permission: 'inventory.view' },
  { to: '/inventario/eventos', icon: AlertTriangle, label: 'Eventos', permission: 'inventory.view' },
  { to: '/inventario/seriales', icon: Hash, label: 'Seriales', permission: 'inventory.view' },
  { to: '/inventario/lotes', icon: Layers, label: 'Lotes', permission: 'inventory.view' },
  { to: '/inventario/recetas', icon: FlaskConical, label: 'Recetas', permission: 'inventory.view' },
  { to: '/inventario/produccion', icon: Factory, label: 'Producción', permission: 'inventory.view' },
  { to: '/inventario/clientes', icon: UserCheck, label: 'Clientes', permission: 'inventory.view' },
  { to: '/inventario/escaner', icon: ScanBarcode, label: 'Escáner', permission: 'inventory.view' },
  { to: '/inventario/picking', icon: PackageCheck, label: 'Picking', permission: 'inventory.view' },
  { to: '/inventario/ventas', icon: ShoppingBag, label: 'Ventas', permission: 'inventory.view' },
  { to: '/inventario/aprobaciones', icon: Shield, label: 'Aprobaciones', permission: 'inventory.view' },
  { to: '/inventario/proveedores', icon: Truck, label: 'Proveedores', permission: 'inventory.view' },
  { to: '/inventario/compras', icon: ShoppingCart, label: 'Compras', permission: 'inventory.view' },
  { to: '/inventario/precios-clientes', icon: DollarSign, label: 'Precios Especiales', permission: 'inventory.view' },
  { to: '/inventario/variantes', icon: Palette, label: 'Variantes', permission: 'inventory.view' },
  { to: '/inventario/reorden', icon: RefreshCw, label: 'Reorden Auto', permission: 'inventory.manage' },
  { to: '/inventario/alertas', icon: Bell, label: 'Alertas', permission: 'inventory.view' },
  { to: '/inventario/kardex', icon: BookOpenIcon, label: 'Kardex', permission: 'inventory.view' },
  { to: '/inventario/conteos', icon: ClipboardCheck, label: 'Conteo Cíclico', permission: 'inventory.view' },
  { to: '/inventario/categorias', icon: FolderTree, label: 'Categorías', permission: 'inventory.view' },
  { to: '/inventario/reportes', icon: FileDown, label: 'Reportes', permission: 'reports.view' },
  { to: '/inventario/auditoria', icon: ClipboardList, label: 'Auditoría', permission: 'admin.audit' },
  { to: '/inventario/configuracion/impuestos', icon: Receipt, label: 'Impuestos', permission: 'inventory.manage' },
  { to: '/inventario/configuracion', icon: Settings2, label: 'Configuración', permission: 'inventory.config' },
  { to: '/inventario/ayuda', icon: HelpCircle, label: 'Ayuda', permission: 'inventory.view' },
]

const logisticaItems = [
  { to: '/tracking', icon: Kanban, label: 'Panel de Seguimiento' },
  { to: '/assets', icon: Package, label: 'Cargas' },
  { to: '/wallets', icon: Wallet, label: 'Custodios' },
  { to: '/organizations', icon: Building2, label: 'Organizaciones' },
]

const ayudaItems = [
  { to: '/help', icon: BookOpen, label: 'Inicio' },
  { to: '/help/assets', icon: Package, label: 'Cargas' },
  { to: '/help/wallets', icon: Wallet, label: 'Custodios' },
  { to: '/help/organizations', icon: Building2, label: 'Organizaciones' },
  { to: '/help/tracking', icon: Kanban, label: 'Panel de Seguimiento' },
]

// Tenant self-service: subscription (always), email config (only when a module is active)
const empresaAlwaysItems = [
  { to: '/empresa/suscripcion', icon: CreditCard, label: 'Mi Suscripción', permission: 'subscription.view' },
]
const empresaModuleItems = [
  { to: '/empresa/plantillas',  icon: Mail,       label: 'Plantillas de Correo', permission: 'email.view' },
  { to: '/empresa/correo',      icon: Send,       label: 'Proveedor de Correo',  permission: 'email.manage' },
]

// Team admin: users, roles, audit
const equipoItems = [
  { to: '/equipo/usuarios',  icon: Users,         label: 'Usuarios',  permission: 'admin.users' },
  { to: '/equipo/roles',     icon: Shield,        label: 'Roles',     permission: 'admin.roles' },
  { to: '/equipo/auditoria', icon: ClipboardList, label: 'Auditoría', permission: 'admin.audit' },
]

function NavItem({ to, icon: Icon, label, onClick }: { to: string; icon: React.ElementType; label: string; onClick?: () => void }) {
  return (
    <NavLink
      to={to}
      end={to === '/'}
      onClick={onClick}
      className={({ isActive }) =>
        cn(
          'group relative flex items-center gap-2.5 rounded-sm px-4 py-2 text-sm font-medium duration-300 ease-in-out',
          isActive
            ? 'bg-indigo-50 text-indigo-600'
            : 'text-gray-600 hover:bg-gray-50 hover:text-gray-700',
        )
      }
    >
      {({ isActive }) => (
        <>
          <Icon className={cn(
            'h-[18px] w-[18px] shrink-0',
            isActive ? 'text-indigo-600' : 'text-gray-400 group-hover:text-gray-600',
          )} />
          <span>{label}</span>
        </>
      )}
    </NavLink>
  )
}

export function Sidebar({ open, onClose }: { open: boolean; onClose: () => void }) {
  const { data: health } = useLiveness()
  const alive = health?.status === 'ok'
  const [logisticaOpen, setLogisticaOpen] = useState(true)
  const [inventarioOpen, setInventarioOpen] = useState(true)
  const [ayudaOpen, setAyudaOpen] = useState(false)
  const [equipoOpen, setEquipoOpen] = useState(true)
  const [empresaOpen, setEmpresaOpen] = useState(false)
  const [plataformaOpen, setPlataformaOpen] = useState(false)

  const user = useAuthStore((s) => s.user)
  const hasPermission = useAuthStore((s) => s.hasPermission)
  const isSuperuser = user?.is_superuser ?? false
  const logout = useLogout()

  const isLogisticsActive = useIsModuleActive('logistics')
  const isInventoryActive = useIsModuleActive('inventory')
  const isEInvoicingActive = useIsModuleActive('electronic-invoicing')
  const isEInvoicingSandboxActive = useIsModuleActive('electronic-invoicing-sandbox')

  const visibleEquipoItems = equipoItems.filter((item) => hasPermission(item.permission))
  const anyModuleActive = isLogisticsActive || isInventoryActive || isEInvoicingActive || isEInvoicingSandboxActive
  const visibleEmpresaItems = [
    ...empresaAlwaysItems.filter((item) => hasPermission(item.permission)),
    ...(anyModuleActive ? empresaModuleItems.filter((item) => hasPermission(item.permission)) : []),
  ]
  const visibleInventarioItems = inventarioItems.filter((item) => hasPermission(item.permission))

  return (
    <aside className={cn(
      'fixed inset-y-0 left-0 z-40 flex flex-col h-full w-72 overflow-y-hidden bg-white border-r border-gray-200 shrink-0 transition-transform duration-300 ease-in-out',
      'md:static md:translate-x-0 md:z-20',
      open ? 'translate-x-0' : '-translate-x-full',
    )}>

      {/* Logo */}
      <div className="flex items-center gap-2.5 px-6 py-5 shrink-0">
        {/* Mark — stylized "TL" monogram */}
        <svg width="34" height="34" viewBox="0 0 34 34" fill="none" className="shrink-0">
          <rect width="34" height="34" rx="8" fill="#4F46E5" />
          <path d="M8 11h18v2.5H18.5V25H15V13.5H8V11Z" fill="white" />
          <path d="M20 17h2.5v5.5H27V25H20V17Z" fill="white" opacity="0.7" />
        </svg>
        {/* Wordmark */}
        <div className="flex flex-col">
          <p className="text-[19px] leading-none tracking-tight">
            <span className="font-bold text-gray-900">Trace</span>
            <span className="font-medium text-indigo-600">Log</span>
          </p>
          <p className="text-[10px] font-medium text-gray-400 mt-0.5 uppercase tracking-widest">Cadena de Custodia</p>
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-1 px-4 py-4 space-y-1 overflow-y-auto no-scrollbar">
        <h3 className="mb-4 ml-4 text-sm font-semibold text-gray-400 uppercase">Menú</h3>
        {topItems.map(({ to, icon, label }) => (
          <NavItem key={to} to={to} icon={icon} label={label} onClick={onClose} />
        ))}

        {/* Logística section — only when module is active */}
        {isLogisticsActive && (
        <div className="pt-4">
          <button
            onClick={() => setLogisticaOpen(o => !o)}
            className="w-full flex items-center justify-between ml-4 mb-2 text-sm font-semibold text-gray-400 uppercase hover:text-gray-600 transition-colors"
          >
            <span>Logística</span>
            <ChevronDown className={cn(
              'h-4 w-4 mr-4 transition-transform duration-200',
              logisticaOpen ? 'rotate-0' : '-rotate-90',
            )} />
          </button>

          {logisticaOpen && (
            <div className="space-y-1">
              {logisticaItems.map(({ to, icon, label }) => (
                <NavItem key={to} to={to} icon={icon} label={label} onClick={onClose} />
              ))}

              {/* Ayuda — sub-sección */}
              <div className="pt-1">
                <button
                  onClick={() => setAyudaOpen(o => !o)}
                  className="w-full flex items-center justify-between pl-4 pr-4 py-1.5 text-xs font-semibold text-gray-400 uppercase hover:text-gray-600 transition-colors rounded hover:bg-gray-50"
                >
                  <span className="flex items-center gap-1.5">
                    <HelpCircle className="h-3 w-3" /> Ayuda
                  </span>
                  <ChevronDown className={cn(
                    'h-3 w-3 transition-transform duration-200',
                    ayudaOpen ? 'rotate-0' : '-rotate-90',
                  )} />
                </button>

                {ayudaOpen && (
                  <div className="mt-1 ml-3 pl-3 border-l border-gray-200 space-y-0.5">
                    {ayudaItems.map(({ to, icon: Icon, label }) => (
                      <NavLink
                        key={to}
                        to={to}
                        end={to === '/help'}
                        onClick={onClose}
                        className={({ isActive }) =>
                          cn(
                            'flex items-center gap-2 rounded-sm px-3 py-1.5 text-xs font-medium duration-300 ease-in-out hover:text-gray-700',
                            isActive
                              ? 'text-indigo-600'
                              : 'text-gray-400',
                          )
                        }
                      >
                        <Icon className="h-3.5 w-3.5 shrink-0" />
                        {label}
                      </NavLink>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
        )}

        {/* Inventario section — only when module is active and user has at least one permission */}
        {isInventoryActive && visibleInventarioItems.length > 0 && (
        <div className="pt-4">
          <button
            onClick={() => setInventarioOpen(o => !o)}
            className="w-full flex items-center justify-between ml-4 mb-2 text-sm font-semibold text-gray-400 uppercase hover:text-gray-600 transition-colors"
          >
            <span>Inventario</span>
            <ChevronDown className={cn(
              'h-4 w-4 mr-4 transition-transform duration-200',
              inventarioOpen ? 'rotate-0' : '-rotate-90',
            )} />
          </button>
          {inventarioOpen && (
            <div className="space-y-1">
              {visibleInventarioItems.map(({ to, icon, label }) => (
                <NavItem key={to} to={to} icon={icon} label={label} onClick={onClose} />
              ))}
            </div>
          )}
        </div>
        )}


        {/* Facturación Electrónica — only when both inventory + e-invoicing modules are active */}
        {isInventoryActive && isEInvoicingActive && (
          <div className="pt-4">
            <NavItem to="/facturacion-electronica" icon={FileText} label="Facturación Electrónica" onClick={onClose} />
          </div>
        )}

        {/* Facturación Electrónica Sandbox — only when both inventory + sandbox modules are active */}
        {isInventoryActive && isEInvoicingSandboxActive && (
          <div className="pt-4">
            <NavItem to="/facturacion-electronica-sandbox" icon={FlaskConical} label="Sandbox Facturación" onClick={onClose} />
          </div>
        )}

        {/* Mi Equipo — team admin (users, roles, audit) */}
        {visibleEquipoItems.length > 0 && (
          <div className="pt-4">
            <button
              onClick={() => setEquipoOpen(o => !o)}
              className="w-full flex items-center justify-between ml-4 mb-2 text-sm font-semibold text-gray-400 uppercase hover:text-gray-600 transition-colors"
            >
              <span>Mi Equipo</span>
              <ChevronDown className={cn(
                'h-4 w-4 mr-4 transition-transform duration-200',
                equipoOpen ? 'rotate-0' : '-rotate-90',
              )} />
            </button>
            {equipoOpen && (
              <div className="space-y-1">
                {visibleEquipoItems.map(({ to, icon, label }) => (
                  <NavItem key={to} to={to} icon={icon} label={label} onClick={onClose} />
                ))}
              </div>
            )}
          </div>
        )}

        {/* Mi Empresa — tenant self-service (subscription, email) */}
        {visibleEmpresaItems.length > 0 && (
          <div className="pt-4">
            <button
              onClick={() => setEmpresaOpen(o => !o)}
              className="w-full flex items-center justify-between ml-4 mb-2 text-sm font-semibold text-emerald-600 uppercase hover:text-emerald-700 transition-colors"
            >
              <span className="flex items-center gap-1.5"><Building className="h-3.5 w-3.5" /> Mi Empresa</span>
              <ChevronDown className={cn(
                'h-4 w-4 mr-4 transition-transform duration-200',
                empresaOpen ? 'rotate-0' : '-rotate-90',
              )} />
            </button>
            {empresaOpen && (
              <div className="space-y-1">
                {visibleEmpresaItems.map(({ to, icon, label }) => (
                  <NavItem key={to} to={to} icon={icon} label={label} onClick={onClose} />
                ))}
              </div>
            )}
          </div>
        )}

        {/* Plataforma — solo superusuarios de TraceLog */}
        {isSuperuser && (
          <div className="pt-4">
            <button
              onClick={() => setPlataformaOpen(o => !o)}
              className="w-full flex items-center justify-between ml-4 mb-2 text-sm font-semibold text-indigo-600 uppercase hover:text-indigo-700 transition-colors"
            >
              <span className="flex items-center gap-1.5"><Crown className="h-3.5 w-3.5" /> Plataforma</span>
              <ChevronDown className={cn(
                'h-4 w-4 mr-4 transition-transform duration-200',
                plataformaOpen ? 'rotate-0' : '-rotate-90',
              )} />
            </button>
            {plataformaOpen && (
              <div className="space-y-1">
                <NavItem to="/platform" icon={BarChart3} label="Panel Ejecutivo" onClick={onClose} />
                <NavItem to="/system" icon={Activity} label="Sistema" onClick={onClose} />
                <NavItem to="/platform/tenants" icon={Building2} label="Empresas" onClick={onClose} />
                <NavItem to="/platform/analytics" icon={Activity} label="Analítica" onClick={onClose} />
                <NavItem to="/platform/sales" icon={TrendingUp} label="Ventas" onClick={onClose} />
                <NavItem to="/platform/plans" icon={Package} label="Planes" onClick={onClose} />
                <NavItem to="/platform/subscriptions" icon={CreditCard} label="Suscripciones" onClick={onClose} />
                <NavItem to="/platform/users" icon={Globe} label="Usuarios Global" onClick={onClose} />
                <NavItem to="/platform/marketplace" icon={Store} label="Marketplace" onClick={onClose} />
                <NavItem to="/platform/team" icon={UserCog} label="Equipo Interno" onClick={onClose} />
                <NavItem to="/platform/onboard" icon={UserPlus} label="Onboarding" onClick={onClose} />
                <NavItem to="/platform/payments" icon={Banknote} label="Pasarela de Cobro" onClick={onClose} />
                <NavItem to="/platform/blockchain" icon={Settings} label="Blockchain" onClick={onClose} />
              </div>
            )}
          </div>
        )}
      </nav>

      {/* Footer: user profile + logout */}
      <div className="px-4 py-4 border-t border-gray-200 shrink-0 space-y-2">
        {user && (
          <NavLink
            to="/profile"
            onClick={onClose}
            className={({ isActive }) =>
              cn(
                'flex items-center gap-3 rounded-sm px-3 py-2.5 transition-all',
                isActive ? 'bg-indigo-50' : 'hover:bg-gray-50',
              )
            }
          >
            <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-indigo-600 text-white font-semibold text-sm overflow-hidden">
              {user.avatar_url ? (
                <img
                  src={user.avatar_url.startsWith('http') ? user.avatar_url : `${import.meta.env.VITE_USER_API_URL ?? 'http://localhost:9001'}${user.avatar_url}`}
                  alt={user.full_name}
                  className="h-full w-full object-cover"
                />
              ) : (
                user.full_name?.[0]?.toUpperCase() ?? '?'
              )}
            </div>
            <div className="min-w-0">
              <div className="text-xs font-semibold text-gray-700 truncate">{user.full_name}</div>
              <div className="text-[10px] text-gray-400 truncate">{user.email}</div>
            </div>
          </NavLink>
        )}

        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="relative shrink-0">
              <span className={cn(
                'block h-2 w-2 rounded-full',
                alive ? 'bg-emerald-500' : 'bg-red-500',
              )} />
              {alive && (
                <span className="absolute inset-0 h-2 w-2 rounded-full bg-emerald-500 animate-ping opacity-60" />
              )}
            </div>
            <span className="text-xs text-gray-400">
              {alive ? 'API connected' : 'API unreachable'}
            </span>
          </div>
          {user && (
            <button
              onClick={() => logout.mutate()}
              className="flex items-center gap-1 rounded-sm px-2 py-1.5 text-xs text-gray-400 hover:text-red-500 hover:bg-gray-50 transition-colors"
              title="Cerrar sesión"
            >
              <LogOut className="h-3.5 w-3.5" />
            </button>
          )}
        </div>
      </div>
    </aside>
  )
}
