import { useState } from 'react'
import { Globe, Search, ChevronLeft, ChevronRight } from 'lucide-react'
import { usePlatformUsers } from '@/hooks/usePlatform'
import { cn } from '@/lib/utils'

export function PlatformUsersPage() {
  const [search, setSearch] = useState('')
  const [tenantFilter, setTenantFilter] = useState('')
  const [page, setPage] = useState(0)
  const limit = 25

  const { data, isLoading } = usePlatformUsers({
    search: search || undefined,
    tenant_id: tenantFilter || undefined,
    offset: page * limit,
    limit,
  })

  const totalPages = data ? Math.ceil(data.total / limit) : 0

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-900 flex items-center gap-2">
          <Globe className="h-6 w-6 text-primary" />
          Usuarios — Vista Global
        </h1>
        <p className="text-sm text-slate-500 mt-1">
          Usuarios de todas las empresas registradas en la plataforma.
        </p>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-3">
        <div className="relative flex-1 min-w-[200px] max-w-sm">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
          <input
            type="text"
            placeholder="Buscar por nombre o email..."
            value={search}
            onChange={(e) => { setSearch(e.target.value); setPage(0) }}
            className="w-full pl-9 pr-4 py-2 rounded-xl border border-slate-200 text-sm focus:outline-none focus:ring-2 focus:ring-ring-300 bg-white/80"
          />
        </div>
        <input
          type="text"
          placeholder="Filtrar por tenant_id..."
          value={tenantFilter}
          onChange={(e) => { setTenantFilter(e.target.value); setPage(0) }}
          className="px-4 py-2 rounded-xl border border-slate-200 text-sm focus:outline-none focus:ring-2 focus:ring-ring-300 bg-white/80 w-48"
        />
      </div>

      {/* Stats */}
      {data && (
        <p className="text-xs text-slate-400">
          {data.total} usuario{data.total !== 1 ? 's' : ''} en total
        </p>
      )}

      {/* Table */}
      <div className="bg-white/80 backdrop-blur-md rounded-2xl shadow-sm border border-white/60 overflow-hidden">
        {/* Mobile cards */}
        <div className="space-y-3 p-4 md:hidden">
          {isLoading ? (
            <div className="py-12 text-center text-slate-400">Cargando usuarios...</div>
          ) : !data?.items.length ? (
            <div className="py-12 text-center text-slate-400">No se encontraron usuarios.</div>
          ) : (
            data.items.map((u) => (
              <div key={u.id} className="rounded-xl border border-gray-200 bg-white p-4 shadow-sm space-y-2">
                <div className="flex items-center gap-2">
                  <div className="flex h-7 w-7 items-center justify-center rounded-full bg-primary/15 text-primary font-semibold text-xs shrink-0">
                    {u.full_name?.[0]?.toUpperCase() ?? '?'}
                  </div>
                  <div className="min-w-0 flex-1">
                    <div className="font-medium text-slate-800 truncate">{u.full_name}</div>
                    <div className="text-xs text-slate-400 truncate">{u.email}</div>
                  </div>
                  <span className={cn(
                    'inline-flex items-center rounded-full px-2 py-0.5 text-xs font-semibold shrink-0',
                    u.is_active ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-600',
                  )}>
                    {u.is_active ? 'Activo' : 'Inactivo'}
                  </span>
                </div>
                <div className="flex items-center justify-between text-xs">
                  <span className="text-slate-500">Tenant</span>
                  <span className="inline-flex items-center rounded-full px-2 py-0.5 font-medium bg-slate-100 text-slate-600">
                    {u.tenant_id}
                  </span>
                </div>
                <div className="flex items-center justify-between text-xs">
                  <span className="text-slate-500">Roles</span>
                  <div className="flex flex-wrap gap-1 justify-end">
                    {u.roles?.map((r) => (
                      <span key={r.id} className="inline-flex items-center rounded-full px-2 py-0.5 font-medium bg-primary/10 text-primary">
                        {r.name}
                      </span>
                    ))}
                  </div>
                </div>
                <div className="flex items-center justify-between text-xs">
                  <span className="text-slate-500">Creado</span>
                  <span className="text-slate-400">{new Date(u.created_at).toLocaleDateString('es-CO')}</span>
                </div>
                {u.is_superuser && (
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-slate-500">Privilegio</span>
                    <span className="inline-flex items-center rounded-full px-2 py-0.5 font-semibold bg-amber-100 text-amber-700">
                      Super
                    </span>
                  </div>
                )}
              </div>
            ))
          )}
        </div>

        {/* Desktop table */}
        <div className="hidden md:block overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-100">
                <th className="text-left px-4 py-3 text-xs font-bold text-slate-500 uppercase">Usuario</th>
                <th className="text-left px-4 py-3 text-xs font-bold text-slate-500 uppercase">Email</th>
                <th className="text-left px-4 py-3 text-xs font-bold text-slate-500 uppercase">Tenant</th>
                <th className="text-left px-4 py-3 text-xs font-bold text-slate-500 uppercase">Roles</th>
                <th className="text-center px-4 py-3 text-xs font-bold text-slate-500 uppercase">Estado</th>
                <th className="text-center px-4 py-3 text-xs font-bold text-slate-500 uppercase">Super</th>
                <th className="text-left px-4 py-3 text-xs font-bold text-slate-500 uppercase">Creado</th>
              </tr>
            </thead>
            <tbody>
              {isLoading ? (
                <tr>
                  <td colSpan={7} className="px-4 py-12 text-center text-slate-400">
                    Cargando usuarios...
                  </td>
                </tr>
              ) : !data?.items.length ? (
                <tr>
                  <td colSpan={7} className="px-4 py-12 text-center text-slate-400">
                    No se encontraron usuarios.
                  </td>
                </tr>
              ) : (
                data.items.map((u) => (
                  <tr key={u.id} className="border-b border-slate-50 hover:bg-slate-50/50 transition-colors">
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        <div className="flex h-7 w-7 items-center justify-center rounded-full bg-primary/15 text-primary font-semibold text-xs shrink-0">
                          {u.full_name?.[0]?.toUpperCase() ?? '?'}
                        </div>
                        <span className="font-medium text-slate-800">{u.full_name}</span>
                      </div>
                    </td>
                    <td className="px-4 py-3 text-slate-600">{u.email}</td>
                    <td className="px-4 py-3">
                      <span className="inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium bg-slate-100 text-slate-600">
                        {u.tenant_id}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex flex-wrap gap-1">
                        {u.roles?.map((r) => (
                          <span key={r.id} className="inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium bg-primary/10 text-primary">
                            {r.name}
                          </span>
                        ))}
                      </div>
                    </td>
                    <td className="px-4 py-3 text-center">
                      <span className={cn(
                        'inline-flex items-center rounded-full px-2 py-0.5 text-xs font-semibold',
                        u.is_active ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-600',
                      )}>
                        {u.is_active ? 'Activo' : 'Inactivo'}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-center">
                      {u.is_superuser && (
                        <span className="inline-flex items-center rounded-full px-2 py-0.5 text-xs font-semibold bg-amber-100 text-amber-700">
                          Super
                        </span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-xs text-slate-400">
                      {new Date(u.created_at).toLocaleDateString('es-CO')}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="flex items-center justify-between px-4 py-3 border-t border-slate-100">
            <p className="text-xs text-slate-500">
              Página {page + 1} de {totalPages}
            </p>
            <div className="flex gap-1">
              <button
                onClick={() => setPage((p) => Math.max(0, p - 1))}
                disabled={page === 0}
                className="p-1.5 rounded-lg hover:bg-slate-100 disabled:opacity-30 transition-colors"
              >
                <ChevronLeft className="h-4 w-4" />
              </button>
              <button
                onClick={() => setPage((p) => Math.min(totalPages - 1, p + 1))}
                disabled={page >= totalPages - 1}
                className="p-1.5 rounded-lg hover:bg-slate-100 disabled:opacity-30 transition-colors"
              >
                <ChevronRight className="h-4 w-4" />
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
