import { useState, useEffect, useMemo } from 'react'
import {
  Shield, Plus, Save, Truck, Boxes, Factory, ShieldCheck, FileText, Sparkles,
  Users, Eye, CreditCard, Settings, Webhook,
} from 'lucide-react'
import { useRoles, usePermissions, useSetRolePermissions, useCreateRole } from '@/hooks/useRoles'
import type { Permission } from '@/types/auth'
import { useQueryClient } from '@tanstack/react-query'
import { cn } from '@/lib/utils'

// ─── Permission groups (simplified UX) ───────────────────────────────────────

interface PermGroup {
  key: string
  label: string
  description: string
  icon: React.ElementType
  color: string
  /** permission slug prefixes that belong to this group */
  prefixes: string[]
}

// Operational permissions — what employees actually use day-to-day
const OPERATIONS_GROUPS: PermGroup[] = [
  {
    key: 'logistics',
    label: 'Logística',
    description: 'Cargas, custodios, organizaciones, tracking, blockchain',
    icon: Truck,
    color: 'bg-blue-500',
    prefixes: ['logistics.', 'assets.', 'wallets.', 'organizations.', 'taxonomy.'],
  },
  {
    key: 'inventory',
    label: 'Inventario',
    description: 'Productos, bodegas, stock, movimientos, lotes, seriales',
    icon: Boxes,
    color: 'bg-orange-500',
    prefixes: ['inventory.', 'products.', 'warehouses.', 'stock.', 'movements.', 'batches.', 'serials.', 'variants.', 'config.', 'cycle_counts.', 'events.'],
  },
  {
    key: 'commerce',
    label: 'Compras y Ventas',
    description: 'Órdenes de compra/venta, socios comerciales, clientes, proveedores, precios',
    icon: CreditCard,
    color: 'bg-emerald-500',
    prefixes: ['purchase_orders.', 'sales_orders.', 'suppliers.', 'customers.', 'price_lists.'],
  },
  {
    key: 'production',
    label: 'Producción',
    description: 'Recetas (BOM), corridas de producción, emisiones, recibos, MRP',
    icon: Factory,
    color: 'bg-violet-500',
    prefixes: ['production.', 'recipes.'],
  },
  {
    key: 'compliance',
    label: 'Cumplimiento',
    description: 'Marcos normativos, parcelas, registros, certificados',
    icon: ShieldCheck,
    color: 'bg-green-600',
    prefixes: ['compliance.'],
  },
  {
    key: 'reports',
    label: 'Reportes',
    description: 'Reportes, descargas CSV, kardex',
    icon: Eye,
    color: 'bg-amber-500',
    prefixes: ['reports.', 'audit.'],
  },
]

// Admin permissions — only for business owners / administrators
const ADMIN_GROUPS: PermGroup[] = [
  {
    key: 'team',
    label: 'Gestión de Equipo',
    description: 'Crear usuarios, asignar roles, ver auditoría',
    icon: Users,
    color: 'bg-purple-500',
    prefixes: ['admin.', 'users.', 'roles.', 'system.'],
  },
  {
    key: 'invoicing',
    label: 'Facturación Electrónica',
    description: 'Facturas DIAN, notas crédito/débito, resoluciones',
    icon: FileText,
    color: 'bg-slate-600',
    prefixes: ['integrations.'],
  },
  {
    key: 'subscription',
    label: 'Suscripción y Pagos',
    description: 'Plan activo, licencias, facturación SaaS',
    icon: CreditCard,
    color: 'bg-indigo-500',
    prefixes: ['subscription.', 'plans.', 'licenses.'],
  },
  {
    key: 'email',
    label: 'Configuración de Correo',
    description: 'Plantillas de email, proveedor de envío',
    icon: Settings,
    color: 'bg-pink-500',
    prefixes: ['email.', 'email_providers.', 'email_templates.'],
  },
]

const ALL_GROUPS = [...OPERATIONS_GROUPS, ...ADMIN_GROUPS]

function matchesGroup(permSlug: string, group: PermGroup): boolean {
  return group.prefixes.some(prefix => permSlug.startsWith(prefix))
}

// ─── Group Row ────────────────────────────────────────────────────────────────

function GroupRow({
  group,
  roles,
  groupPermIds,
  isGroupActive,
  isGroupPartial,
  toggleGroup,
}: {
  group: PermGroup
  roles: { id: string; name: string; is_system?: boolean }[]
  groupPermIds: Record<string, string[]>
  isGroupActive: (roleId: string, groupKey: string) => boolean
  isGroupPartial: (roleId: string, groupKey: string) => boolean
  toggleGroup: (roleId: string, groupKey: string) => void
}) {
  const permCount = groupPermIds[group.key]?.length ?? 0
  if (permCount === 0) return null
  const Icon = group.icon

  return (
    <div className="rounded-2xl border border-slate-200 bg-white shadow-sm overflow-hidden">
      <div className="flex items-center gap-3 px-5 py-4 border-b border-slate-100">
        <div className={cn('flex h-9 w-9 items-center justify-center rounded-xl text-white shrink-0', group.color)}>
          <Icon className="h-4 w-4" />
        </div>
        <div className="flex-1 min-w-0">
          <h3 className="text-sm font-semibold text-slate-800">{group.label}</h3>
          <p className="text-xs text-slate-400">{group.description}</p>
        </div>
      </div>
      <div className="px-5 py-3 flex flex-wrap gap-3">
        {roles.map(role => {
          const active = isGroupActive(role.id, group.key)
          const partial = isGroupPartial(role.id, group.key)
          return (
            <button
              key={role.id}
              onClick={() => toggleGroup(role.id, group.key)}
              className={cn(
                'flex items-center gap-2 rounded-xl border-2 px-4 py-2.5 text-sm font-medium transition-all',
                active
                  ? 'border-primary bg-primary/5 text-primary'
                  : partial
                    ? 'border-amber-300 bg-amber-50 text-amber-700'
                    : 'border-slate-200 text-slate-500 hover:border-slate-300',
              )}
            >
              <div className={cn(
                'h-4 w-4 rounded border-2 flex items-center justify-center shrink-0',
                active ? 'border-primary bg-primary' : partial ? 'border-amber-400 bg-amber-400' : 'border-slate-300',
              )}>
                {(active || partial) && (
                  <svg className="h-3 w-3 text-white" viewBox="0 0 12 12" fill="none">
                    {active ? (
                      <path d="M2.5 6L5 8.5L9.5 3.5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                    ) : (
                      <path d="M3 6H9" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
                    )}
                  </svg>
                )}
              </div>
              <span>{role.name}</span>
              {role.is_system && (
                <span className="text-[10px] bg-purple-50 text-purple-600 rounded px-1">sistema</span>
              )}
            </button>
          )
        })}
      </div>
    </div>
  )
}

// ─── Main component ───────────────────────────────────────────────────────────

export function RolesPage() {
  const { data: roles = [], isLoading: rolesLoading } = useRoles()
  const { data: allPerms = [], isLoading: permsLoading } = usePermissions()
  const createRole = useCreateRole()
  const setPerms = useSetRolePermissions()
  const qc = useQueryClient()

  const [localPerms, setLocalPerms] = useState<Record<string, Set<string>>>({})
  const [dirty, setDirty] = useState<Set<string>>(new Set())
  const [saving, setSaving] = useState(false)
  const [newRoleName, setNewRoleName] = useState('')

  // Load permissions for all roles
  useEffect(() => {
    if (!roles.length) return
    const load = async () => {
      const next: Record<string, Set<string>> = {}
      await Promise.all(
        roles.map(async (role) => {
          const data = await qc.fetchQuery({
            queryKey: ['admin', 'roles', role.id, 'permissions'],
            queryFn: () => import('@/lib/user-api').then((m) => m.userApi.roles.getPermissions(role.id)),
            staleTime: 60_000,
          })
          next[role.id] = new Set((data as Permission[]).map((p) => p.id))
        })
      )
      setLocalPerms(next)
      setDirty(new Set())
    }
    load()
  }, [roles.length])

  // Map perm slugs to IDs per group
  const groupPermIds = useMemo(() => {
    const map: Record<string, string[]> = {}
    for (const group of ALL_GROUPS) {
      map[group.key] = allPerms
        .filter(p => matchesGroup(p.slug, group))
        .map(p => p.id)
    }
    return map
  }, [allPerms])

  // Check if a role has ALL perms in a group
  function isGroupActive(roleId: string, groupKey: string): boolean {
    const ids = groupPermIds[groupKey] ?? []
    if (ids.length === 0) return false
    const roleSet = localPerms[roleId]
    if (!roleSet) return false
    return ids.every(id => roleSet.has(id))
  }

  // Check if a role has SOME perms in a group
  function isGroupPartial(roleId: string, groupKey: string): boolean {
    const ids = groupPermIds[groupKey] ?? []
    if (ids.length === 0) return false
    const roleSet = localPerms[roleId]
    if (!roleSet) return false
    const count = ids.filter(id => roleSet.has(id)).length
    return count > 0 && count < ids.length
  }

  function toggleGroup(roleId: string, groupKey: string) {
    const ids = groupPermIds[groupKey] ?? []
    const active = isGroupActive(roleId, groupKey)
    setLocalPerms(prev => {
      const set = new Set(prev[roleId] ?? [])
      for (const id of ids) {
        if (active) set.delete(id)
        else set.add(id)
      }
      return { ...prev, [roleId]: set }
    })
    setDirty(prev => new Set(prev).add(roleId))
  }

  const handleSave = async () => {
    setSaving(true)
    try {
      await Promise.all(
        Array.from(dirty).map((roleId) =>
          setPerms.mutateAsync({
            roleId,
            permissionIds: Array.from(localPerms[roleId] ?? []),
          })
        )
      )
      setDirty(new Set())
    } finally {
      setSaving(false)
    }
  }

  const handleCreateRole = () => {
    if (!newRoleName.trim()) return
    const slug = newRoleName.trim().toLowerCase().replace(/\s+/g, '-').replace(/[^a-z0-9-]/g, '')
    createRole.mutate({ name: newRoleName.trim(), slug })
    setNewRoleName('')
  }

  if (rolesLoading || permsLoading) {
    return <div className="p-8 text-slate-500">Cargando...</div>
  }

  return (
    <div className="p-8 space-y-6 max-w-5xl">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-purple-100">
            <Shield className="h-5 w-5 text-purple-600" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-slate-900">Roles y Permisos</h1>
            <p className="text-sm text-slate-500">Asigna módulos completos a cada rol</p>
          </div>
        </div>
      </div>

      {/* New role */}
      <div className="flex items-center gap-2">
        <input
          value={newRoleName}
          onChange={e => setNewRoleName(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && handleCreateRole()}
          placeholder="Nombre del nuevo rol..."
          className="rounded-xl border border-slate-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring w-64"
        />
        <button
          onClick={handleCreateRole}
          disabled={!newRoleName.trim() || createRole.isPending}
          className="flex items-center gap-1.5 rounded-xl bg-primary px-4 py-2 text-sm font-semibold text-white hover:bg-primary/90 disabled:opacity-50"
        >
          <Plus className="h-4 w-4" /> Crear rol
        </button>
      </div>

      {/* Operaciones — day-to-day employee access */}
      <div>
        <h2 className="text-sm font-bold text-slate-500 uppercase tracking-wider mb-3">Operaciones</h2>
        <p className="text-xs text-slate-400 mb-4">Permisos del día a día — asigna a empleados, operarios y colaboradores</p>
        <div className="space-y-3">
          {OPERATIONS_GROUPS.map(group => (
            <GroupRow key={group.key} group={group} roles={roles} groupPermIds={groupPermIds} isGroupActive={isGroupActive} isGroupPartial={isGroupPartial} toggleGroup={toggleGroup} />
          ))}
        </div>
      </div>

      {/* Administración — business owner only */}
      <div>
        <h2 className="text-sm font-bold text-slate-500 uppercase tracking-wider mb-3">Administración</h2>
        <p className="text-xs text-slate-400 mb-4">Solo para dueños o gerentes — control total del negocio</p>
        <div className="space-y-3">
          {ADMIN_GROUPS.map(group => (
            <GroupRow key={group.key} group={group} roles={roles} groupPermIds={groupPermIds} isGroupActive={isGroupActive} isGroupPartial={isGroupPartial} toggleGroup={toggleGroup} />
          ))}
        </div>
      </div>

      {/* Floating save bar */}
      {dirty.size > 0 && (
        <div className="fixed bottom-6 left-1/2 -translate-x-1/2 z-50 flex items-center gap-4 rounded-2xl bg-slate-900 px-6 py-4 shadow-2xl text-white text-sm">
          <span className="font-medium">
            {dirty.size} rol{dirty.size > 1 ? 'es' : ''} con cambios pendientes
          </span>
          <button
            onClick={handleSave}
            disabled={saving}
            className="flex items-center gap-2 rounded-xl bg-primary px-4 py-2 text-sm font-semibold hover:bg-primary/70 disabled:opacity-60 transition-colors"
          >
            <Save className="h-4 w-4" />
            {saving ? 'Guardando...' : 'Guardar cambios'}
          </button>
          <button
            onClick={() => {
              // Reload from server
              setDirty(new Set())
              qc.invalidateQueries({ queryKey: ['admin', 'roles'] })
            }}
            className="text-slate-400 hover:text-white text-xs"
          >
            Cancelar
          </button>
        </div>
      )}
    </div>
  )
}
