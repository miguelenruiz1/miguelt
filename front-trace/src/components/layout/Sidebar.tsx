import { useState, useCallback, useRef, useEffect } from 'react'
import { NavLink, useLocation, useNavigate } from 'react-router-dom'
import {
  LayoutGrid, Wallet, Box, Activity, Building2, Kanban, FileText, FolderTree,
  Settings, ChevronRight, CircleHelp, Users, ShieldCheck, Eye, ListChecks,
  LogOut, CreditCard, Grid3x3, Warehouse, ArrowLeftRight, ShoppingCart,
  Percent, BarChart3, Banknote, Zap, Fingerprint, ScrollText, Factory, Mail, Send,
  Crown, Store, TrendingUp, UserCog, UserPlus, FlaskConical,
  ShoppingBag, Tag, BellRing, BookText, Shapes,
  Users2, Globe, ScanLine, PackageCheck, RefreshCw, Scale, Search,
  CheckCircle, MapPin, Award, ChevronsUpDown, Sparkles,
  Ship, Plane, Shield, FolderOpen, Link2,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { useLiveness } from '@/hooks/useHealth'
import { useAuthStore } from '@/store/auth'
import { useLogout } from '@/hooks/useAuth'
import { useIsModuleActive } from '@/hooks/useModules'
import { useFeatureToggles } from '@/hooks/useInventory'

/* ── Data ─────────────────────────────────────────────────────────────────── */

const topItems = [
  { to: '/marketplace', icon: Store, label: 'Marketplace' },
  { to: '/', icon: LayoutGrid, label: 'Dashboard' },
  { to: '/media', icon: FolderOpen, label: 'Media' },
]

const invTop = [
  { to: '/inventario', icon: LayoutGrid, label: 'Inicio', permission: 'inventory.view' },
  { to: '/inventario/rentabilidad', icon: TrendingUp, label: 'Rentabilidad', permission: 'inventory.view' },
  { to: '/inventario/alertas', icon: BellRing, label: 'Alertas', permission: 'inventory.view' },
]

const invGroups = [
  {
    key: 'productos', icon: Box, label: 'Mis Productos',
    items: [
      { to: '/inventario/productos', icon: Box, label: 'Productos', permission: 'inventory.view' },
      { to: '/inventario/categorias', icon: FolderTree, label: 'Categorias', permission: 'inventory.view' },
    ],
  },
  {
    key: 'bodega', icon: Warehouse, label: 'Bodega y Despacho',
    items: [
      { to: '/inventario/bodegas', icon: Warehouse, label: 'Bodegas', permission: 'inventory.view' },
      { to: '/inventario/movimientos', icon: ArrowLeftRight, label: 'Movimientos', permission: 'inventory.view' },
      { to: '/inventario/lotes', icon: Grid3x3, label: 'Lotes', permission: 'inventory.view', feature: 'lotes' },
      { to: '/inventario/seriales', icon: Fingerprint, label: 'Seriales', permission: 'inventory.view', feature: 'seriales' },
      { to: '/inventario/conteos', icon: ListChecks, label: 'Conteo', permission: 'inventory.view', feature: 'conteo' },
      { to: '/inventario/escaner', icon: ScanLine, label: 'Escaner', permission: 'inventory.view', feature: 'escaner' },
      { to: '/inventario/picking', icon: PackageCheck, label: 'Picking', permission: 'inventory.view', feature: 'picking' },
      { to: '/inventario/reorden', icon: RefreshCw, label: 'Reorden', permission: 'inventory.manage' },
    ],
  },
  {
    key: 'comercial', icon: Users2, label: 'Compras y Ventas',
    items: [
      { to: '/inventario/socios', icon: Users2, label: 'Socios', permission: 'inventory.view' },
      { to: '/inventario/compras', icon: ShoppingCart, label: 'Compras', permission: 'inventory.view' },
      { to: '/inventario/ventas', icon: ShoppingBag, label: 'Ventas', permission: 'inventory.view' },
      { to: '/inventario/precios-clientes', icon: Tag, label: 'Precios', permission: 'inventory.view', feature: 'precios' },
      { to: '/inventario/aprobaciones', icon: ShieldCheck, label: 'Aprobaciones', permission: 'inventory.view', feature: 'aprobaciones' },
    ],
  },
  {
    key: 'informes', icon: BarChart3, label: 'Informes',
    items: [
      { to: '/inventario/reportes', icon: BarChart3, label: 'Reportes', permission: 'reports.view' },
      { to: '/inventario/kardex', icon: BookText, label: 'Kardex', permission: 'inventory.view', feature: 'kardex' },
      { to: '/inventario/eventos', icon: Zap, label: 'Eventos', permission: 'inventory.view', feature: 'eventos' },
      { to: '/inventario/auditoria', icon: Eye, label: 'Auditoria', permission: 'admin.audit' },
    ],
  },
  {
    key: 'ajustes', icon: Settings, label: 'Ajustes',
    items: [
      { to: '/inventario/configuracion', icon: Settings, label: 'Configuracion', permission: 'inventory.config' },
      { to: '/inventario/configuracion/impuestos', icon: Percent, label: 'Impuestos', permission: 'inventory.manage' },
      { to: '/inventario/unidades-medida', icon: Scale, label: 'Medidas', permission: 'inventory.manage' },
      { to: '/inventario/ayuda', icon: CircleHelp, label: 'Ayuda', permission: 'inventory.view' },
    ],
  },
]

const produccionItems = [
  { to: '/produccion', icon: LayoutGrid, label: 'Inicio', permission: 'production.view' },
  { to: '/produccion/ordenes', icon: Factory, label: 'Ordenes', permission: 'production.view' },
  { to: '/produccion/recetas', icon: ScrollText, label: 'Recetas (BOM)', permission: 'production.view' },
  { to: '/produccion/recursos', icon: Users2, label: 'Recursos', permission: 'production.view' },
  { to: '/produccion/mrp', icon: Search, label: 'MRP', permission: 'production.view' },
  { to: '/produccion/emisiones', icon: Send, label: 'Emisiones', permission: 'production.view' },
  { to: '/produccion/recibos', icon: PackageCheck, label: 'Recibos', permission: 'production.view' },
  { to: '/produccion/reportes', icon: BarChart3, label: 'Reportes', permission: 'production.view' },
]

const cumplimientoItems = [
  { to: '/cumplimiento/frameworks', icon: Globe, label: 'Marcos Normativos' },
  { to: '/cumplimiento/activaciones', icon: CheckCircle, label: 'Mis Normas' },
  { to: '/cumplimiento/parcelas', icon: MapPin, label: 'Parcelas' },
  { to: '/cumplimiento/registros', icon: FileText, label: 'Registros' },
  { to: '/cumplimiento/certificados', icon: Award, label: 'Certificados' },
]

const logisticaItems = [
  { to: '/tracking', icon: Kanban, label: 'Seguimiento' },
  { to: '/assets', icon: Box, label: 'Cargas' },
  { to: '/wallets', icon: Wallet, label: 'Custodios' },
  { to: '/organizations', icon: Building2, label: 'Organizaciones' },
  { to: '/logistica/analiticas', icon: BarChart3, label: 'Analiticas' },
  { to: '/configuracion/flujo-de-trabajo', icon: Settings, label: 'Flujo de trabajo' },
]


const empresaAlwaysItems = [
  { to: '/empresa/suscripcion', icon: CreditCard, label: 'Suscripcion', permission: 'subscription.view' },
  { to: '/settings/billing',    icon: Banknote,    label: 'Facturacion', permission: 'subscription.view' },
  { to: '/empresa/webhooks',    icon: Zap,         label: 'Webhooks',    permission: 'subscription.view' },
]
const empresaModuleItems: typeof empresaAlwaysItems = []

const equipoItems = [
  { to: '/equipo/usuarios',  icon: Users,         label: 'Usuarios',  permission: 'admin.users' },
  { to: '/equipo/roles',     icon: ShieldCheck,   label: 'Roles',     permission: 'admin.roles' },
  { to: '/equipo/auditoria', icon: Eye,           label: 'Auditoria', permission: 'admin.audit' },
]

/* ── Force-reset navigation when clicking the same route ───────────────── */

function useResetNav(to: string, onClick?: () => void) {
  const location = useLocation()
  const navigate = useNavigate()
  return (e: React.MouseEvent) => {
    if (location.pathname === to) {
      e.preventDefault()
      navigate(to, { replace: true })
    }
    onClick?.()
  }
}

/* ── Sub-nav link (used in expanded groups) ────────────────────────────── */

function SubNavLink({ to, label, onClick }: { to: string; label: string; onClick?: () => void }) {
  const handleClick = useResetNav(to, onClick)
  return (
    <NavLink key={to} to={to} onClick={handleClick}
      className={({ isActive }) => cn(
        'flex items-center rounded-md py-1.5 pl-9 pr-3 text-[13px] transition-colors duration-150',
        isActive ? 'text-white' : 'text-[color:var(--sidebar-foreground)] opacity-60 hover:opacity-90',
      )}>
      {label}
    </NavLink>
  )
}

/* ── Nav item — premium style ─────────────────────────────────────────────── */

function NavItem({ to, icon: Icon, label, onClick, collapsed }: {
  to: string; icon: React.ElementType; label: string; onClick?: () => void; collapsed?: boolean
}) {
  const handleClick = useResetNav(to, onClick)
  if (collapsed) {
    return (
      <div className="relative group">
        <NavLink
          to={to}
          end={to === '/' || to === '/inventario'}
          onClick={handleClick}
          className={({ isActive }) =>
            cn(
              'flex items-center justify-center rounded-md py-2 mx-auto w-10 transition-colors duration-150',
              isActive
                ? 'bg-white/[0.08] text-white'
                : 'text-[color:var(--sidebar-foreground)] hover:bg-white/[0.05]',
            )
          }
        >
          {({ isActive }) => (
            <Icon className={cn('h-4 w-4 shrink-0', isActive && 'text-emerald-400')} />
          )}
        </NavLink>
        <div className="absolute left-full top-1/2 -translate-y-1/2 ml-3 px-2.5 py-1 bg-gray-950 text-white text-xs font-medium rounded-md shadow-lg whitespace-nowrap opacity-0 pointer-events-none group-hover:opacity-100 transition-opacity z-[60]">
          {label}
        </div>
      </div>
    )
  }

  return (
    <NavLink
      to={to}
      end={to === '/' || to === '/inventario'}
      onClick={handleClick}
      className={({ isActive }) =>
        cn(
          'flex items-center gap-2.5 rounded-md px-3 py-1.5 text-sm transition-colors duration-150',
          isActive
            ? 'bg-white/[0.08] text-white font-medium'
            : 'text-[color:var(--sidebar-foreground)] hover:bg-white/[0.05] hover:text-white/90 font-normal',
        )
      }
    >
      {({ isActive }) => (
        <>
          <Icon className={cn('h-4 w-4 shrink-0', isActive ? 'text-emerald-400' : 'opacity-50')} />
          <span className="truncate">{label}</span>
        </>
      )}
    </NavLink>
  )
}

/* ── Section label ─────────────────────────────────────────────────────────── */

function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <p className="px-3 pt-5 pb-1 text-[11px] font-medium uppercase tracking-widest select-none text-[color:var(--sidebar-foreground)] opacity-40">
      {children}
    </p>
  )
}

/* ── Collapsible section ──────────────────────────────────────────────────── */

function Section({ label, isOpen, onToggle, children, collapsed }: {
  label: string; isOpen: boolean; onToggle: () => void; children: React.ReactNode; accent?: string; collapsed?: boolean
}) {
  if (collapsed) {
    return <div className="pt-2 space-y-0.5">{children}</div>
  }
  return (
    <div>
      <button
        onClick={onToggle}
        className="w-full flex items-center justify-between px-3 pt-5 pb-1 text-[11px] font-medium uppercase tracking-widest select-none text-[color:var(--sidebar-foreground)] opacity-40 hover:opacity-60 transition-opacity"
      >
        <span>{label}</span>
        <ChevronRight className={cn('h-3 w-3 transition-transform duration-200', isOpen && 'rotate-90')} />
      </button>
      <div className={cn(
        'overflow-hidden transition-all duration-200',
        isOpen ? 'max-h-[2000px] opacity-100 mt-0.5' : 'max-h-0 opacity-0',
      )}>
        <div className="space-y-0.5">{children}</div>
      </div>
    </div>
  )
}

/* ── Main sidebar ─────────────────────────────────────────────────────────── */

const MIN_W = 56
const MAX_W = 280
const DEFAULT_W = 240
const COLLAPSE_W = 80

export function Sidebar({ open, onClose }: { open: boolean; onClose: () => void }) {
  const { data: health } = useLiveness()
  const alive = health?.status === 'ok'

  // ── Resizable width
  const [width, setWidth] = useState(() => {
    const saved = localStorage.getItem('sidebar-w')
    return saved ? Math.min(MAX_W, Math.max(MIN_W, Number(saved))) : DEFAULT_W
  })
  const [isDragging, setIsDragging] = useState(false)
  const startX = useRef(0)
  const startW = useRef(DEFAULT_W)

  const onMouseDown = useCallback((e: React.MouseEvent) => {
    e.preventDefault()
    startX.current = e.clientX
    startW.current = width
    setIsDragging(true)
  }, [width])

  useEffect(() => {
    if (!isDragging) return
    document.body.style.cursor = 'col-resize'
    document.body.style.userSelect = 'none'
    const onMove = (e: MouseEvent) => {
      const newW = Math.min(MAX_W, Math.max(MIN_W, startW.current + (e.clientX - startX.current)))
      setWidth(newW)
    }
    const onUp = () => {
      setIsDragging(false)
      document.body.style.cursor = ''
      document.body.style.userSelect = ''
      localStorage.setItem('sidebar-w', String(width))
    }
    document.addEventListener('mousemove', onMove)
    document.addEventListener('mouseup', onUp)
    return () => {
      document.removeEventListener('mousemove', onMove)
      document.removeEventListener('mouseup', onUp)
    }
  }, [isDragging, width])

  const [logisticaOpen, setLogisticaOpen] = useState(true)
  const [inventarioOpen, setInventarioOpen] = useState(true)
  const [equipoOpen, setEquipoOpen] = useState(true)
  const [empresaOpen, setEmpresaOpen] = useState(false)
  const [plataformaOpen, setPlataformaOpen] = useState(true)
  const [produccionOpen, setProduccionOpen] = useState(true)
  const [cumplimientoOpen, setCumplimientoOpen] = useState(true)
  const [openInvGroup, setOpenInvGroup] = useState<string | null>(null)
  const collapsed = width < COLLAPSE_W

  const expandSidebar = useCallback(() => {
    setWidth(DEFAULT_W)
    localStorage.setItem('sidebar-w', String(DEFAULT_W))
  }, [])

  const user = useAuthStore((s) => s.user)
  const hasPermission = useAuthStore((s) => s.hasPermission)
  const isSuperuser = user?.is_superuser ?? false
  const logout = useLogout()

  const { data: features } = useFeatureToggles()
  const feat = (key: string) => features?.[key] !== false

  const isLogisticsActive = useIsModuleActive('logistics')
  const isInventoryActive = useIsModuleActive('inventory')
  const isEInvoicingActive = useIsModuleActive('electronic-invoicing')
  const isProductionActive = useIsModuleActive('production')
  const isComplianceActive = useIsModuleActive('compliance')

  const visibleEquipoItems = equipoItems.filter((item) => hasPermission(item.permission))
  const anyModuleActive = isLogisticsActive || isInventoryActive || isEInvoicingActive || isProductionActive || isComplianceActive
  const visibleEmpresaItems = [
    ...empresaAlwaysItems.filter((item) => hasPermission(item.permission)),
    ...(anyModuleActive ? empresaModuleItems.filter((item) => hasPermission(item.permission)) : []),
  ]
  const filterPerm = (items: typeof invTop) => items.filter(i =>
    hasPermission(i.permission) && (!('feature' in i) || feat((i as any).feature))
  )
  const hasAnyInvItem = invGroups.some(g => filterPerm(g.items).length > 0) || filterPerm(invTop).length > 0

  const initials = user?.full_name?.split(' ').map(w => w[0]).join('').slice(0, 2).toUpperCase() ?? '?'

  return (
    <aside
      className={cn(
        'fixed inset-y-0 left-0 z-40 flex flex-col h-full shrink-0',
        'md:static md:translate-x-0 md:z-20',
        open ? 'translate-x-0' : '-translate-x-full',
        !isDragging && 'transition-transform duration-300 ease-out',
      )}
      style={{ width, background: 'var(--sidebar)' }}
    >
      {/* Resize handle */}
      <div
        onMouseDown={onMouseDown}
        className="absolute top-0 -right-[3px] w-[6px] h-full cursor-col-resize z-50 group hidden md:flex items-center justify-center"
      >
        <div className={cn(
          'w-px h-full transition-colors',
          isDragging ? 'bg-emerald-500/40' : 'bg-white/[0.06] group-hover:bg-white/[0.12]',
        )} />
      </div>

      {/* ── Header ──────────────────────────────────────────────────── */}
      {collapsed ? (
        <button
          onClick={expandSidebar}
          className="flex items-center justify-center h-14 shrink-0 group relative"
        >
          <div className="flex h-7 w-7 items-center justify-center rounded-md bg-emerald-500 shrink-0">
            <svg width="14" height="14" viewBox="0 0 34 34" fill="none">
              <path d="M8 11h18v2.5H18.5V25H15V13.5H8V11Z" fill="white" />
              <path d="M20 17h2.5v5.5H27V25H20V17Z" fill="white" opacity="0.7" />
            </svg>
          </div>
          <div className="absolute left-full top-1/2 -translate-y-1/2 ml-3 px-2.5 py-1 bg-gray-950 text-white text-xs font-medium rounded-md shadow-lg whitespace-nowrap opacity-0 pointer-events-none group-hover:opacity-100 transition-opacity z-[60]">
            Expandir menu
          </div>
        </button>
      ) : (
        <NavLink to="/" onClick={onClose} className="flex items-center gap-2.5 px-4 pt-5 pb-4 shrink-0 group">
          <div className="flex h-7 w-7 items-center justify-center rounded-md bg-emerald-500 shrink-0">
            <svg width="14" height="14" viewBox="0 0 34 34" fill="none">
              <path d="M8 11h18v2.5H18.5V25H15V13.5H8V11Z" fill="white" />
              <path d="M20 17h2.5v5.5H27V25H20V17Z" fill="white" opacity="0.7" />
            </svg>
          </div>
          <span className="text-[15px] font-semibold text-white tracking-tight leading-none">
            TraceLog
          </span>
        </NavLink>
      )}

      {/* Separator */}
      {!collapsed && <div className="mx-3 h-px bg-white/[0.06]" />}

      {/* ── Navigation ──────────────────────────────────────────────── */}
      <nav className="flex-1 px-2 py-2 overflow-y-auto sidebar-scroll">
        <div className="space-y-0.5">
          {topItems.map(({ to, icon, label }) => (
            <NavItem key={to} to={to} icon={icon} label={label} onClick={onClose} collapsed={collapsed} />
          ))}
        </div>

        {/* Logistica */}
        {isLogisticsActive && (
          <Section label="Logistica" isOpen={logisticaOpen} onToggle={() => setLogisticaOpen(o => !o)} collapsed={collapsed}>
            {logisticaItems.map(({ to, icon, label }) => (
              <NavItem key={to} to={to} icon={icon} label={label} onClick={onClose} collapsed={collapsed} />
            ))}
          </Section>
        )}

        {/* Inventario */}
        {isInventoryActive && hasAnyInvItem && (
          <Section label="Inventario" isOpen={inventarioOpen} onToggle={() => setInventarioOpen(o => !o)} collapsed={collapsed}>
            {filterPerm(invTop).map(({ to, icon, label }) => (
              <NavItem key={to} to={to} icon={icon} label={label} onClick={onClose} collapsed={collapsed} />
            ))}
            {collapsed
              ? invGroups.map(group => {
                  const visible = filterPerm(group.items)
                  if (visible.length === 0) return null
                  return <NavItem key={group.key} to={visible[0].to} icon={group.icon} label={group.label} onClick={onClose} collapsed={collapsed} />
                })
              : invGroups.map(group => {
                  const visible = filterPerm(group.items)
                  if (visible.length === 0) return null
                  const isGroupOpen = openInvGroup === group.key
                  const GroupIcon = group.icon
                  return (
                    <div key={group.key}>
                      <button
                        onClick={() => setOpenInvGroup(isGroupOpen ? null : group.key)}
                        className={cn(
                          'w-full flex items-center gap-2.5 px-3 py-1.5 text-sm rounded-md transition-colors duration-150',
                          isGroupOpen
                            ? 'bg-white/[0.08] text-white font-medium'
                            : 'text-[color:var(--sidebar-foreground)] hover:bg-white/[0.05] hover:text-white/90',
                        )}
                      >
                        <GroupIcon className={cn('h-4 w-4 shrink-0', isGroupOpen ? 'text-emerald-400' : 'opacity-50')} />
                        <span className="flex-1 text-left truncate">{group.label}</span>
                        <ChevronRight className={cn('h-3 w-3 opacity-30 transition-transform duration-200', isGroupOpen && 'rotate-90')} />
                      </button>
                      {isGroupOpen && (
                        <div className="space-y-0.5 mt-0.5">
                          {visible.map(({ to, label }) => (
                            <SubNavLink key={to} to={to} label={label} onClick={onClose} />
                          ))}
                        </div>
                      )}
                    </div>
                  )
                })
            }
          </Section>
        )}

        {/* Produccion (modulo independiente) */}
        {isProductionActive && (
          <Section label="Produccion" isOpen={produccionOpen} onToggle={() => setProduccionOpen(o => !o)} collapsed={collapsed}>
            {produccionItems.filter(i => hasPermission(i.permission)).map(({ to, icon, label }) => (
              <NavItem key={to} to={to} icon={icon} label={label} onClick={onClose} collapsed={collapsed} />
            ))}
          </Section>
        )}

        {/* Cumplimiento */}
        {isComplianceActive && (
          <Section label="Cumplimiento" isOpen={cumplimientoOpen} onToggle={() => setCumplimientoOpen(o => !o)} collapsed={collapsed}>
            {cumplimientoItems.map(({ to, icon, label }) => (
              <NavItem key={to} to={to} icon={icon} label={label} onClick={onClose} collapsed={collapsed} />
            ))}
          </Section>
        )}

        {/* Separador */}
        {!collapsed && <div className="mx-3 my-2 h-px bg-white/[0.06]" />}

        {/* Mi Equipo */}
        {visibleEquipoItems.length > 0 && (
          <Section label="Equipo" isOpen={equipoOpen} onToggle={() => setEquipoOpen(o => !o)} collapsed={collapsed}>
            {visibleEquipoItems.map(({ to, icon, label }) => (
              <NavItem key={to} to={to} icon={icon} label={label} onClick={onClose} collapsed={collapsed} />
            ))}
          </Section>
        )}

        {/* Mi Empresa */}
        {visibleEmpresaItems.length > 0 && (
          <Section label="Empresa" isOpen={empresaOpen} onToggle={() => setEmpresaOpen(o => !o)} collapsed={collapsed}>
            {visibleEmpresaItems.map(({ to, icon, label }) => (
              <NavItem key={to} to={to} icon={icon} label={label} onClick={onClose} collapsed={collapsed} />
            ))}
          </Section>
        )}

        {/* Plataforma */}
        {isSuperuser && (
          <Section label="Plataforma" isOpen={plataformaOpen} onToggle={() => setPlataformaOpen(o => !o)} collapsed={collapsed}>
            <NavItem to="/platform" icon={BarChart3} label="Panel" onClick={onClose} collapsed={collapsed} />
            <NavItem to="/system" icon={Activity} label="Sistema" onClick={onClose} collapsed={collapsed} />
            <NavItem to="/platform/tenants" icon={Building2} label="Empresas" onClick={onClose} collapsed={collapsed} />
            <NavItem to="/platform/analytics" icon={TrendingUp} label="Analitica" onClick={onClose} collapsed={collapsed} />
            <NavItem to="/platform/sales" icon={TrendingUp} label="Ventas" onClick={onClose} collapsed={collapsed} />
            <NavItem to="/platform/plans" icon={Box} label="Planes" onClick={onClose} collapsed={collapsed} />
            <NavItem to="/platform/subscriptions" icon={CreditCard} label="Suscripciones" onClick={onClose} collapsed={collapsed} />
            <NavItem to="/platform/users" icon={Globe} label="Usuarios" onClick={onClose} collapsed={collapsed} />
            <NavItem to="/platform/team" icon={UserCog} label="Equipo" onClick={onClose} collapsed={collapsed} />
            <NavItem to="/platform/onboard" icon={UserPlus} label="Onboarding" onClick={onClose} collapsed={collapsed} />
            <NavItem to="/platform/payments" icon={Banknote} label="Pagos" onClick={onClose} collapsed={collapsed} />
            <NavItem to="/platform/ai" icon={Sparkles} label="Inteligencia Artificial" onClick={onClose} collapsed={collapsed} />
            <NavItem to="/platform/blockchain" icon={Link2} label="Blockchain" onClick={onClose} collapsed={collapsed} />
            <NavItem to="/facturacion-electronica" icon={FileText} label="Facturacion Electronica" onClick={onClose} collapsed={collapsed} />
            <NavItem to="/empresa/correo" icon={Mail} label="Correo" onClick={onClose} collapsed={collapsed} />
          </Section>
        )}
      </nav>

      {/* ── Footer ──────────────────────────────────────────────────── */}
      <div className="px-3 pb-4 pt-2 shrink-0">
        <div className="h-px bg-white/[0.06] mb-3" />
        {user && (
          <NavLink
            to="/profile"
            onClick={collapsed ? expandSidebar : onClose}
            className="flex items-center gap-3 rounded-md px-2 py-2 transition-colors duration-150 group hover:bg-white/[0.05]"
          >
            <div className="flex h-6 w-6 shrink-0 items-center justify-center rounded-md bg-emerald-500/20 text-[10px] font-semibold text-emerald-400">
              {user.avatar_url ? (
                <img
                  src={user.avatar_url.startsWith('http') ? user.avatar_url : `${import.meta.env.VITE_API_URL ?? 'http://localhost:9000'}${user.avatar_url}`}
                  alt={user.full_name}
                  className="h-full w-full object-cover rounded-md"
                />
              ) : initials}
            </div>
            {!collapsed && (
              <>
                <div className="flex-1 min-w-0">
                  <p className="text-[13px] font-medium text-white truncate leading-none">{user.full_name}</p>
                  <p className="text-[11px] truncate mt-0.5 text-[color:var(--sidebar-foreground)] opacity-50">{user.email}</p>
                </div>
                <button
                  onClick={(e) => { e.preventDefault(); e.stopPropagation(); logout.mutate() }}
                  className="opacity-0 group-hover:opacity-100 p-1 rounded-md hover:bg-white/[0.08] text-[color:var(--sidebar-foreground)] hover:text-red-400 transition-all"
                  title="Cerrar sesion"
                >
                  <LogOut className="h-3.5 w-3.5" />
                </button>
              </>
            )}
            {collapsed && (
              <div className="absolute left-full top-1/2 -translate-y-1/2 ml-3 px-2.5 py-1 bg-gray-950 text-white text-xs font-medium rounded-md shadow-lg whitespace-nowrap opacity-0 pointer-events-none group-hover:opacity-100 transition-opacity z-[60]">
                {user.full_name}
              </div>
            )}
          </NavLink>
        )}
      </div>
    </aside>
  )
}
