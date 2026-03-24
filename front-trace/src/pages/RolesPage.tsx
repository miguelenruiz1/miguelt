import { Fragment, useState, useEffect, useMemo } from 'react'
import { Shield, Plus, Save, Search, LayoutTemplate, FilePlus2 } from 'lucide-react'
import { useRoles, usePermissions, useSetRolePermissions, useCreateRole } from '@/hooks/useRoles'
import type { Permission } from '@/types/auth'
import { useQueryClient } from '@tanstack/react-query'
import { RoleTemplateModal } from '@/components/auth/RoleTemplateModal'
import { CreateTemplateModal } from '@/components/auth/CreateTemplateModal'

// ─── Permission matrix cell ───────────────────────────────────────────────────

function PermCell({
  roleId,
  permId,
  checked,
  onChange,
}: {
  roleId: string
  permId: string
  checked: boolean
  onChange: (roleId: string, permId: string, checked: boolean) => void
}) {
  return (
    <td className="px-3 py-2 text-center border-r border-slate-100 last:border-0">
      <input
        type="checkbox"
        checked={checked}
        onChange={(e) => onChange(roleId, permId, e.target.checked)}
        className="h-4 w-4 rounded border-slate-300 text-primary cursor-pointer"
      />
    </td>
  )
}

// ─── New Role Form ────────────────────────────────────────────────────────────

function NewRoleRow({ onSave }: { onSave: (name: string, slug: string) => void }) {
  const [name, setName] = useState('')
  const [slug, setSlug] = useState('')

  return (
    <tr className="bg-primary/5 border-b border-slate-200">
      <td className="px-4 py-2 sticky left-0 z-10 bg-primary/5">
        <div className="flex items-center gap-2">
          <input
            value={name}
            onChange={(e) => {
              setName(e.target.value)
              setSlug(e.target.value.toLowerCase().replace(/\s+/g, '-').replace(/[^a-z0-9-]/g, ''))
            }}
            placeholder="Nombre del rol"
            className="w-36 rounded-lg border border-primary/50 px-2 py-1 text-xs focus:outline-none focus:ring-2 focus:ring-ring"
          />
          <input
            value={slug}
            onChange={(e) => setSlug(e.target.value)}
            placeholder="slug"
            className="w-24 rounded-lg border border-primary/50 px-2 py-1 text-xs focus:outline-none focus:ring-2 focus:ring-ring"
          />
          <button
            onClick={() => { if (name && slug) { onSave(name, slug); setName(''); setSlug('') } }}
            className="rounded-lg bg-primary px-2 py-1 text-xs text-white hover:bg-primary/90 flex items-center gap-1"
          >
            <Plus className="h-3 w-3" /> Agregar
          </button>
        </div>
      </td>
      {/* empty cells for each role column placeholder */}
    </tr>
  )
}

// ─── Main component ───────────────────────────────────────────────────────────

export function RolesPage() {
  const { data: roles = [], isLoading: rolesLoading } = useRoles()
  const { data: allPerms = [], isLoading: permsLoading } = usePermissions()
  const createRole = useCreateRole()
  const setPerms = useSetRolePermissions()
  const qc = useQueryClient()

  // Local state: roleId → Set<permId>
  const [localPerms, setLocalPerms] = useState<Record<string, Set<string>>>({})
  const [dirty, setDirty] = useState<Set<string>>(new Set())
  const [filter, setFilter] = useState('')
  const [saving, setSaving] = useState(false)
  const [templateOpen, setTemplateOpen] = useState(false)
  const [createTmplOpen, setCreateTmplOpen] = useState(false)

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

  // Group permissions by module
  const modules = useMemo(() => {
    const filtered = allPerms.filter(
      (p) =>
        !filter ||
        p.name.toLowerCase().includes(filter.toLowerCase()) ||
        p.slug.toLowerCase().includes(filter.toLowerCase()),
    )
    const grouped: Record<string, Permission[]> = {}
    for (const p of filtered) {
      if (!grouped[p.module]) grouped[p.module] = []
      grouped[p.module].push(p)
    }
    return grouped
  }, [allPerms, filter])

  const handleChange = (roleId: string, permId: string, checked: boolean) => {
    setLocalPerms((prev) => {
      const set = new Set(prev[roleId] ?? [])
      if (checked) set.add(permId)
      else set.delete(permId)
      return { ...prev, [roleId]: set }
    })
    setDirty((prev) => new Set(prev).add(roleId))
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

  if (rolesLoading || permsLoading) {
    return <div className="p-8 text-slate-500">Cargando...</div>
  }

  return (
    <div className="p-8 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-purple-100">
            <Shield className="h-5 w-5 text-purple-600" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-slate-900">Roles y Permisos</h1>
            <p className="text-sm text-slate-500">Matriz de control de acceso</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setCreateTmplOpen(true)}
            className="flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50 transition-colors"
          >
            <FilePlus2 className="h-4 w-4" />
            Crear plantilla
          </button>
          <button
            onClick={() => setTemplateOpen(true)}
            className="flex items-center gap-2 rounded-xl bg-primary px-4 py-2 text-sm font-semibold text-white hover:bg-primary/90 transition-colors"
          >
            <LayoutTemplate className="h-4 w-4" />
            Crear desde plantilla
          </button>
        </div>
      </div>

      {/* Filter */}
      <div className="relative max-w-xs">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
        <input
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
          placeholder="Buscar permiso..."
          className="w-full rounded-xl border border-slate-200 bg-white pl-9 pr-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
        />
      </div>

      {/* Matrix table */}
      <div className="overflow-x-auto rounded-2xl border border-slate-200 bg-white/80 shadow-sm">
        <table className="w-full text-sm border-collapse">
          <thead>
            <tr className="bg-slate-50 border-b border-slate-200">
              <th className="sticky left-0 z-20 bg-slate-50 px-4 py-3 text-left font-semibold text-slate-600 min-w-[220px]">
                Permiso
              </th>
              {roles.map((role) => (
                <th
                  key={role.id}
                  className="px-3 py-3 text-center font-semibold text-slate-600 min-w-[100px] border-l border-slate-100"
                >
                  <div className="flex flex-col items-center gap-0.5">
                    <span className="truncate max-w-[90px]">{role.name}</span>
                    {role.is_system && (
                      <span className="text-[10px] text-purple-600 bg-purple-50 rounded px-1">sistema</span>
                    )}
                  </div>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {Object.entries(modules).map(([module, perms]) => (
              <Fragment key={module}>
                {/* Module header row */}
                <tr className="bg-slate-50/80">
                  <td
                    colSpan={roles.length + 1}
                    className="sticky left-0 px-4 py-2 text-xs font-bold text-slate-500 uppercase tracking-widest border-b border-t border-slate-100 bg-slate-50/80"
                  >
                    {module}
                  </td>
                </tr>
                {/* Permission rows */}
                {perms.map((perm) => (
                  <tr key={perm.id} className="border-b border-slate-100 hover:bg-slate-50/50">
                    <td className="sticky left-0 z-10 bg-white px-4 py-2 hover:bg-slate-50/50">
                      <div>
                        <div className="text-slate-700 font-medium text-xs">{perm.name}</div>
                        <div className="text-[10px] text-slate-400 font-mono">{perm.slug}</div>
                      </div>
                    </td>
                    {roles.map((role) => (
                      <PermCell
                        key={role.id}
                        roleId={role.id}
                        permId={perm.id}
                        checked={localPerms[role.id]?.has(perm.id) ?? false}
                        onChange={handleChange}
                      />
                    ))}
                  </tr>
                ))}
              </Fragment>
            ))}
            {/* New role row */}
            <NewRoleRow
              onSave={(name, slug) => createRole.mutate({ name, slug })}
            />
          </tbody>
        </table>
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
            onClick={() => setDirty(new Set())}
            className="text-slate-400 hover:text-white text-xs"
          >
            Cancelar
          </button>
        </div>
      )}

      <RoleTemplateModal open={templateOpen} onClose={() => setTemplateOpen(false)} />
      <CreateTemplateModal open={createTmplOpen} onClose={() => setCreateTmplOpen(false)} />
    </div>
  )
}
