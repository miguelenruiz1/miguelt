import { useState } from 'react'
import { Users, ChevronDown, UserX, UserPlus, UserCheck, X, AlertTriangle, MailPlus, RefreshCw } from 'lucide-react'
import { useUsers, useAssignRole, useRemoveRole, useDeactivateUser, useReactivateUser, useInviteUser, useResendInvitation } from '@/hooks/useUsers'
import { useRoles } from '@/hooks/useRoles'
import { useSubscription } from '@/hooks/useSubscriptions'
import type { AuthUser } from '@/types/auth'

import { useAuthStore } from '@/store/auth'

function RoleDropdown({ user, onAssign, onRemove }: {
  user: AuthUser
  onAssign: (roleId: string) => void
  onRemove: (roleId: string) => void
}) {
  const { data: roles = [] } = useRoles()
  const [open, setOpen] = useState(false)

  return (
    <div className="relative">
      <button
        onClick={() => setOpen((o) => !o)}
        className="flex items-center gap-1 text-xs text-primary hover:text-primary font-medium"
      >
        Roles <ChevronDown className="h-3 w-3" />
      </button>
      {open && (
        <div className="absolute right-0 top-6 z-50 w-52 rounded-xl bg-card shadow-xl ring-1 ring-slate-200 py-1">
          {roles.map((role) => {
            const hasRole = user.roles.some((r) => r.id === role.id)
            return (
              <button
                key={role.id}
                onClick={() => {
                  if (hasRole) onRemove(role.id)
                  else onAssign(role.id)
                  setOpen(false)
                }}
                className="w-full flex items-center justify-between px-3 py-2 text-sm hover:bg-muted text-foreground"
              >
                <span>{role.name}</span>
                {hasRole && <span className="text-xs text-emerald-600 font-medium">✓</span>}
              </button>
            )
          })}
        </div>
      )}
    </div>
  )
}

function UserStatusBadge({ user }: { user: AuthUser }) {
  if (!user.is_active) {
    return (
      <span className="inline-flex items-center gap-1 text-xs font-medium rounded-full px-2 py-0.5 bg-secondary text-muted-foreground">
        Desactivado
      </span>
    )
  }
  if (user.invitation_sent_at && !user.invitation_accepted_at) {
    return (
      <span className="inline-flex items-center gap-1 text-xs font-medium rounded-full px-2 py-0.5 bg-amber-100 text-amber-700">
        Pendiente
      </span>
    )
  }
  return (
    <span className="inline-flex items-center gap-1 text-xs font-medium rounded-full px-2 py-0.5 bg-emerald-100 text-emerald-700">
      Activo
    </span>
  )
}

function InviteUserModal({ onClose }: { onClose: () => void }) {
  const [email, setEmail] = useState('')
  const [fullName, setFullName] = useState('')
  const [selectedRoles, setSelectedRoles] = useState<string[]>([])
  const [error, setError] = useState('')
  const invite = useInviteUser()
  const { data: roles = [] } = useRoles()

  function toggleRole(roleId: string) {
    setSelectedRoles((prev) =>
      prev.includes(roleId) ? prev.filter((id) => id !== roleId) : [...prev, roleId]
    )
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault()
    setError('')
    try {
      await invite.mutateAsync({ email, full_name: fullName, role_ids: selectedRoles })
      onClose()
    } catch (err: any) {
      setError(err?.message ?? 'Error al invitar usuario')
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 backdrop-blur-sm">
      <div className="w-full max-w-md rounded-2xl bg-card shadow-2xl border border-border">
        <div className="flex items-center justify-between px-6 py-4 border-b border-border">
          <h2 className="font-semibold text-foreground text-lg">Invitar usuario</h2>
          <button onClick={onClose} className="text-muted-foreground hover:text-muted-foreground">
            <X className="h-5 w-5" />
          </button>
        </div>
        <form onSubmit={submit} className="p-6 space-y-4">
          <div>
            <label className="block text-xs font-medium text-muted-foreground mb-1">Nombre completo</label>
            <input
              required
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              className="w-full rounded-lg border border-border px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
              placeholder="María García"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-muted-foreground mb-1">Email</label>
            <input
              required
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full rounded-lg border border-border px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
              placeholder="maria@empresa.com"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-muted-foreground mb-1">Roles</label>
            <div className="flex flex-wrap gap-2 mt-1">
              {roles.map((role) => {
                const selected = selectedRoles.includes(role.id)
                return (
                  <button
                    key={role.id}
                    type="button"
                    onClick={() => toggleRole(role.id)}
                    className={`text-xs rounded-full px-3 py-1.5 border transition-colors ${
                      selected
                        ? 'bg-primary text-white border-primary'
                        : 'bg-card text-muted-foreground border-border hover:border-primary/50'
                    }`}
                  >
                    {role.name}
                  </button>
                )
              })}
            </div>
          </div>

          <div className="rounded-lg bg-blue-50 border border-blue-200 px-3 py-2 text-xs text-blue-700">
            <MailPlus className="h-3.5 w-3.5 inline mr-1" />
            Se enviará un correo de invitación con un enlace para activar la cuenta.
          </div>

          {error && <p className="text-xs text-red-600 bg-red-50 rounded-lg px-3 py-2">{error}</p>}
          <div className="flex justify-end gap-2 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-sm text-muted-foreground hover:text-foreground"
            >
              Cancelar
            </button>
            <button
              type="submit"
              disabled={invite.isPending}
              className="px-5 py-2 text-sm font-medium rounded-xl bg-primary text-white hover:bg-primary/90 disabled:opacity-50"
            >
              {invite.isPending ? 'Enviando...' : 'Enviar invitación'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

function PlanLimitBadge({ used, max }: { used: number; max: number }) {
  if (max === -1) {
    return (
      <span className="text-xs text-muted-foreground bg-secondary rounded-full px-3 py-1">
        {used} usuarios · ilimitado
      </span>
    )
  }
  const pct = used / max
  const color = pct >= 1 ? 'bg-red-100 text-red-700' : pct >= 0.8 ? 'bg-amber-100 text-amber-700' : 'bg-emerald-100 text-emerald-700'
  return (
    <span className={`text-xs font-medium rounded-full px-3 py-1 ${color}`}>
      {used} / {max} usuarios
    </span>
  )
}

export function UsersPage() {
  const tenantId = useAuthStore((s) => s.user?.tenant_id) ?? 'default'
  const { data, isLoading } = useUsers()
  const { data: subscription } = useSubscription(tenantId)
  const assignRole = useAssignRole()
  const removeRole = useRemoveRole()
  const deactivate = useDeactivateUser()
  const reactivate = useReactivateUser()
  const resend = useResendInvitation()
  const [showInvite, setShowInvite] = useState(false)

  const total = data?.total ?? 0
  const maxUsers = subscription?.plan?.max_users ?? -1
  const atLimit = maxUsers !== -1 && total >= maxUsers

  return (
    <div className="p-8 space-y-6">
      {showInvite && <InviteUserModal onClose={() => setShowInvite(false)} />}

      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-primary/15">
            <Users className="h-5 w-5 text-primary" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-foreground">Mi Equipo</h1>
            <p className="text-sm text-muted-foreground">Usuarios, roles y permisos de tu organización</p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          {!isLoading && <PlanLimitBadge used={total} max={maxUsers} />}
          <button
            onClick={() => setShowInvite(true)}
            disabled={atLimit}
            title={atLimit ? `Límite del plan alcanzado (${maxUsers} usuarios)` : 'Invitar nuevo usuario'}
            className="flex items-center gap-2 px-4 py-2 rounded-xl bg-primary text-white text-sm font-medium hover:bg-primary/90 disabled:opacity-40 disabled:cursor-not-allowed"
          >
            <UserPlus className="h-4 w-4" />
            Invitar usuario
          </button>
        </div>
      </div>

      {atLimit && (
        <div className="flex items-center gap-2 rounded-xl bg-amber-50 border border-amber-200 px-4 py-3 text-sm text-amber-800">
          <AlertTriangle className="h-4 w-4 shrink-0" />
          Has alcanzado el límite de {maxUsers} usuarios de tu plan <strong>{subscription?.plan?.name}</strong>. Actualiza tu plan para agregar más.
        </div>
      )}

      <div className="bg-card/80 rounded-2xl border border-border  overflow-hidden">
        {isLoading ? (
          <div className="p-8 text-center text-muted-foreground">Cargando...</div>
        ) : (<>
          {/* Mobile cards */}
          <div className="space-y-3 p-4 md:hidden">
            {data?.items.map((user) => {
              const isPending = !!user.invitation_sent_at && !user.invitation_accepted_at
              return (
                <div key={user.id} className="rounded-xl border border-border bg-card p-4  space-y-3">
                  <div className="flex items-center gap-3">
                    <div className="flex h-8 w-8 items-center justify-center rounded-full bg-primary/15 text-primary font-semibold text-sm shrink-0">
                      {user.full_name[0]?.toUpperCase()}
                    </div>
                    <div className="min-w-0 flex-1">
                      <div className="font-medium text-foreground truncate">{user.full_name}</div>
                      <div className="text-xs text-muted-foreground truncate">{user.email}</div>
                    </div>
                    <UserStatusBadge user={user} />
                  </div>
                  <div className="flex flex-wrap gap-1">
                    {user.roles.map((r) => (
                      <span key={r.id} className="text-xs bg-primary/15 text-primary rounded-full px-2 py-0.5">
                        {r.name}
                      </span>
                    ))}
                  </div>
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-muted-foreground">Creado: {new Date(user.created_at).toLocaleDateString('es')}</span>
                  </div>
                  <div className="flex items-center gap-3 pt-1 border-t border-border">
                    <RoleDropdown
                      user={user}
                      onAssign={(roleId) => assignRole.mutate({ userId: user.id, roleId })}
                      onRemove={(roleId) => removeRole.mutate({ userId: user.id, roleId })}
                    />
                    {isPending && (
                      <button
                        onClick={() => resend.mutate(user.id)}
                        disabled={resend.isPending}
                        className="text-xs text-primary hover:text-primary flex items-center gap-1"
                        title="Reenviar invitación"
                      >
                        <RefreshCw className="h-3.5 w-3.5" /> Reenviar
                      </button>
                    )}
                    {user.is_active ? (
                      <button
                        onClick={() => deactivate.mutate(user.id)}
                        className="text-xs text-red-500 hover:text-red-700 flex items-center gap-1"
                      >
                        <UserX className="h-3.5 w-3.5" /> Desactivar
                      </button>
                    ) : (
                      <button
                        onClick={() => reactivate.mutate(user.id)}
                        className="text-xs text-emerald-500 hover:text-emerald-700 flex items-center gap-1"
                      >
                        <UserCheck className="h-3.5 w-3.5" /> Reactivar
                      </button>
                    )}
                  </div>
                </div>
              )
            })}
          </div>

          {/* Desktop table */}
          <div className="hidden md:block">
          <table className="w-full text-sm">
            <thead className="bg-muted border-b border-border">
              <tr>
                <th className="px-4 py-3 text-left font-semibold text-muted-foreground">Usuario</th>
                <th className="px-4 py-3 text-left font-semibold text-muted-foreground">Roles</th>
                <th className="px-4 py-3 text-left font-semibold text-muted-foreground">Estado</th>
                <th className="px-4 py-3 text-left font-semibold text-muted-foreground">Creado</th>
                <th className="px-4 py-3 text-right font-semibold text-muted-foreground">Acciones</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {data?.items.map((user) => {
                const isPending = !!user.invitation_sent_at && !user.invitation_accepted_at
                return (
                  <tr key={user.id} className="hover:bg-muted/50">
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-3">
                        <div className="flex h-8 w-8 items-center justify-center rounded-full bg-primary/15 text-primary font-semibold text-sm shrink-0">
                          {user.full_name[0]?.toUpperCase()}
                        </div>
                        <div>
                          <div className="font-medium text-foreground">{user.full_name}</div>
                          <div className="text-xs text-muted-foreground">{user.email}</div>
                        </div>
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex flex-wrap gap-1">
                        {user.roles.map((r) => (
                          <span key={r.id} className="text-xs bg-primary/15 text-primary rounded-full px-2 py-0.5">
                            {r.name}
                          </span>
                        ))}
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <UserStatusBadge user={user} />
                    </td>
                    <td className="px-4 py-3 text-muted-foreground text-xs">
                      {new Date(user.created_at).toLocaleDateString('es')}
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center justify-end gap-3">
                        <RoleDropdown
                          user={user}
                          onAssign={(roleId) => assignRole.mutate({ userId: user.id, roleId })}
                          onRemove={(roleId) => removeRole.mutate({ userId: user.id, roleId })}
                        />

                        {isPending && (
                          <button
                            onClick={() => resend.mutate(user.id)}
                            disabled={resend.isPending}
                            className="text-xs text-primary hover:text-primary flex items-center gap-1"
                            title="Reenviar invitación"
                          >
                            <RefreshCw className="h-3.5 w-3.5" /> Reenviar
                          </button>
                        )}

                        {user.is_active ? (
                          <button
                            onClick={() => deactivate.mutate(user.id)}
                            className="text-xs text-red-500 hover:text-red-700 flex items-center gap-1"
                          >
                            <UserX className="h-3.5 w-3.5" /> Desactivar
                          </button>
                        ) : (
                          <button
                            onClick={() => reactivate.mutate(user.id)}
                            className="text-xs text-emerald-500 hover:text-emerald-700 flex items-center gap-1"
                          >
                            <UserCheck className="h-3.5 w-3.5" /> Reactivar
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
          </div>
        </>)}
      </div>
    </div>
  )
}
