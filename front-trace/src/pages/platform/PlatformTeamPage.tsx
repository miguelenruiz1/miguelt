import { useState } from 'react'
import { Link } from 'react-router-dom'
import {
  ArrowLeft, Users, Shield, Crown, UserPlus, Search,
  CheckCircle2, XCircle, Mail,
} from 'lucide-react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { userApi } from '@/lib/user-api'
import { useAuthStore } from '@/store/auth'
import { cn } from '@/lib/utils'
import type { AuthUser } from '@/types/auth'

export function PlatformTeamPage() {
  const [search, setSearch] = useState('')
  const [showInvite, setShowInvite] = useState(false)
  const qc = useQueryClient()
  const currentUser = useAuthStore(s => s.user)

  // List all users (platform level — we show superuser status)
  const { data, isLoading } = useQuery({
    queryKey: ['platform', 'team'],
    queryFn: () => userApi.users.list({ limit: 200 }),
    staleTime: 15_000,
  })

  const toggleSuperuser = useMutation({
    mutationFn: ({ userId, value }: { userId: string; value: boolean }) =>
      userApi.users.update(userId, { is_superuser: value } as Partial<AuthUser>),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['platform', 'team'] }),
  })

  const toggleActive = useMutation({
    mutationFn: ({ userId, active }: { userId: string; active: boolean }) =>
      active ? userApi.users.reactivate(userId) : userApi.users.deactivate(userId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['platform', 'team'] }),
  })

  const users = data?.items ?? []
  const filtered = search
    ? users.filter(u =>
        u.full_name.toLowerCase().includes(search.toLowerCase()) ||
        u.email.toLowerCase().includes(search.toLowerCase())
      )
    : users

  const superusers = filtered.filter(u => u.is_superuser)
  const regularUsers = filtered.filter(u => !u.is_superuser)

  return (
    <div className="space-y-6">
      <div>
        <Link to="/platform" className="inline-flex items-center gap-1 text-sm text-slate-500 hover:text-primary mb-2">
          <ArrowLeft className="h-4 w-4" /> Panel
        </Link>
        <h1 className="text-2xl font-bold text-slate-900">Equipo de Plataforma</h1>
        <p className="text-sm text-slate-500 mt-1">
          Gestiona los operadores internos de TraceLog. Los superusuarios tienen acceso total a todos los tenants.
        </p>
      </div>

      {/* Search + stats */}
      <div className="flex flex-wrap items-center gap-3">
        <div className="relative flex-1 min-w-[240px]">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
          <input
            type="text"
            placeholder="Buscar por nombre o email..."
            value={search}
            onChange={e => setSearch(e.target.value)}
            className="w-full pl-9 pr-3 py-2.5 text-sm bg-white border border-slate-200 rounded-xl focus:ring-2 focus:ring-ring/20 focus:border-ring outline-none"
          />
        </div>
        <div className="flex items-center gap-2 text-sm text-slate-500">
          <Crown className="h-4 w-4 text-amber-500" />
          <span>{superusers.length} superusuarios</span>
          <span className="text-slate-300">|</span>
          <Users className="h-4 w-4 text-slate-400" />
          <span>{users.length} total</span>
        </div>
      </div>

      {isLoading ? (
        <div className="flex items-center justify-center h-40">
          <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-primary" />
        </div>
      ) : (
        <>
          {/* Superusers section */}
          <div className="bg-white rounded-2xl border border-amber-200/60 shadow-sm overflow-hidden">
            <div className="px-6 py-4 border-b border-amber-100 bg-amber-50/50 flex items-center gap-2">
              <Crown className="h-4 w-4 text-amber-500" />
              <h3 className="text-sm font-semibold text-amber-800">Operadores de Plataforma (Superusuarios)</h3>
            </div>
            {superusers.length === 0 ? (
              <p className="px-6 py-8 text-sm text-slate-400 text-center">Ningun superusuario encontrado</p>
            ) : (
              <div className="divide-y divide-amber-100">
                {superusers.map(u => (
                  <UserRow
                    key={u.id}
                    user={u}
                    isCurrent={u.id === currentUser?.id}
                    onToggleSuperuser={(val) => toggleSuperuser.mutate({ userId: u.id, value: val })}
                    onToggleActive={(val) => toggleActive.mutate({ userId: u.id, active: val })}
                  />
                ))}
              </div>
            )}
          </div>

          {/* Regular users section */}
          <div className="bg-white rounded-2xl border border-slate-200/60 shadow-sm overflow-hidden">
            <div className="px-6 py-4 border-b border-slate-100 flex items-center gap-2">
              <Users className="h-4 w-4 text-slate-500" />
              <h3 className="text-sm font-semibold text-slate-700">Usuarios Regulares</h3>
              <span className="ml-auto text-xs text-slate-400">{regularUsers.length} usuarios</span>
            </div>
            {regularUsers.length === 0 ? (
              <p className="px-6 py-8 text-sm text-slate-400 text-center">Sin usuarios regulares</p>
            ) : (
              <div className="divide-y divide-slate-100">
                {regularUsers.map(u => (
                  <UserRow
                    key={u.id}
                    user={u}
                    isCurrent={u.id === currentUser?.id}
                    onToggleSuperuser={(val) => toggleSuperuser.mutate({ userId: u.id, value: val })}
                    onToggleActive={(val) => toggleActive.mutate({ userId: u.id, active: val })}
                  />
                ))}
              </div>
            )}
          </div>
        </>
      )}

      {/* Info */}
      <div className="bg-primary/10 border border-primary/30 rounded-2xl p-5">
        <h4 className="text-sm font-semibold text-primary mb-1">Permisos de Plataforma</h4>
        <ul className="text-sm text-primary space-y-1 list-disc list-inside">
          <li><strong>Superusuario</strong>: acceso total a todos los tenants, panel de plataforma, pasarela de cobro</li>
          <li><strong>Usuario regular</strong>: solo tiene acceso al tenant al que pertenece, con los permisos de su rol</li>
          <li>Para agregar miembros al equipo de soporte, activa el toggle de superusuario</li>
        </ul>
      </div>
    </div>
  )
}

function UserRow({ user, isCurrent, onToggleSuperuser, onToggleActive }: {
  user: AuthUser
  isCurrent: boolean
  onToggleSuperuser: (val: boolean) => void
  onToggleActive: (val: boolean) => void
}) {
  return (
    <div className="px-6 py-3 flex items-center gap-4 hover:bg-slate-50/60">
      {/* Avatar */}
      <div className={cn(
        'h-10 w-10 rounded-full flex items-center justify-center text-sm font-semibold shrink-0',
        user.is_superuser ? 'bg-amber-100 text-amber-700' : 'bg-slate-100 text-slate-600',
      )}>
        {user.full_name?.[0]?.toUpperCase() ?? '?'}
      </div>

      {/* Info */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className="text-sm font-semibold text-slate-900 truncate">{user.full_name}</span>
          {isCurrent && <span className="text-[10px] bg-primary/15 text-primary px-1.5 py-0.5 rounded-md font-medium">Tu</span>}
          {user.is_superuser && <Crown className="h-3.5 w-3.5 text-amber-500" />}
        </div>
        <div className="flex items-center gap-3 text-xs text-slate-400">
          <span className="flex items-center gap-1"><Mail className="h-3 w-3" /> {user.email}</span>
          <span>Tenant: {user.tenant_id}</span>
          {user.roles && user.roles.length > 0 && (
            <span className="flex items-center gap-1">
              <Shield className="h-3 w-3" /> {user.roles.map(r => r.name).join(', ')}
            </span>
          )}
        </div>
      </div>

      {/* Status */}
      <div className="flex items-center gap-1">
        {user.is_active ? (
          <span className="flex items-center gap-1 text-xs text-emerald-600">
            <CheckCircle2 className="h-3.5 w-3.5" /> Activo
          </span>
        ) : (
          <span className="flex items-center gap-1 text-xs text-red-500">
            <XCircle className="h-3.5 w-3.5" /> Inactivo
          </span>
        )}
      </div>

      {/* Actions */}
      <div className="flex items-center gap-2">
        {/* Superuser toggle */}
        <button
          onClick={() => onToggleSuperuser(!user.is_superuser)}
          disabled={isCurrent}
          className={cn(
            'text-xs px-3 py-1.5 rounded-lg font-medium transition',
            user.is_superuser
              ? 'bg-amber-100 text-amber-700 hover:bg-amber-200'
              : 'bg-slate-100 text-slate-600 hover:bg-primary/15 hover:text-primary',
            isCurrent && 'opacity-50 cursor-not-allowed',
          )}
          title={isCurrent ? 'No puedes cambiar tu propio estado' : ''}
        >
          {user.is_superuser ? 'Quitar Superusuario' : 'Hacer Superusuario'}
        </button>

        {/* Active toggle */}
        {!isCurrent && (
          <button
            onClick={() => onToggleActive(!user.is_active)}
            className={cn(
              'text-xs px-3 py-1.5 rounded-lg font-medium transition',
              user.is_active
                ? 'bg-red-50 text-red-600 hover:bg-red-100'
                : 'bg-emerald-50 text-emerald-600 hover:bg-emerald-100',
            )}
          >
            {user.is_active ? 'Desactivar' : 'Reactivar'}
          </button>
        )}
      </div>
    </div>
  )
}
