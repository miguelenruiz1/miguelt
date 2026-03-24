import { useState } from 'react'
import { ClipboardList, Search, ChevronLeft, ChevronRight } from 'lucide-react'
import { useAuditLog } from '@/hooks/useAudit'
import { format } from 'date-fns'

const PAGE_SIZE = 25

export function AuditPage() {
  const [page, setPage] = useState(0)
  const [action, setAction] = useState('')
  const [resourceType, setResourceType] = useState('')

  const { data, isLoading } = useAuditLog({
    action: action || undefined,
    resource_type: resourceType || undefined,
    offset: page * PAGE_SIZE,
    limit: PAGE_SIZE,
  })

  const totalPages = data ? Math.ceil(data.total / PAGE_SIZE) : 0

  return (
    <div className="p-8 space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-amber-100">
          <ClipboardList className="h-5 w-5 text-amber-600" />
        </div>
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Auditoría</h1>
          <p className="text-sm text-slate-500">Registro de acciones del sistema</p>
        </div>
      </div>

      {/* Filters */}
      <div className="flex gap-3 flex-wrap">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
          <input
            value={action}
            onChange={(e) => { setAction(e.target.value); setPage(0) }}
            placeholder="Filtrar por acción..."
            className="rounded-xl border border-slate-200 bg-white pl-9 pr-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring w-52"
          />
        </div>
        <input
          value={resourceType}
          onChange={(e) => { setResourceType(e.target.value); setPage(0) }}
          placeholder="Tipo de recurso..."
          className="rounded-xl border border-slate-200 bg-white px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring w-44"
        />
        {(action || resourceType) && (
          <button
            onClick={() => { setAction(''); setResourceType(''); setPage(0) }}
            className="text-sm text-slate-500 hover:text-slate-700 px-3"
          >
            Limpiar
          </button>
        )}
      </div>

      {/* Table */}
      <div className="bg-white/80 rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
        {isLoading ? (
          <div className="p-8 text-center text-slate-500">Cargando...</div>
        ) : (<>
          {/* Mobile cards */}
          <div className="space-y-3 p-4 md:hidden">
            {data?.items.length === 0 ? (
              <div className="py-8 text-center text-slate-400">Sin registros</div>
            ) : (
              data?.items.map((log) => (
                <div key={log.id} className="rounded-xl border border-gray-200 bg-white p-4 shadow-sm space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="font-mono text-xs bg-slate-100 text-slate-700 rounded px-1.5 py-0.5">
                      {log.action}
                    </span>
                    <span className="text-xs text-slate-400">
                      {format(new Date(log.created_at), 'dd/MM/yyyy HH:mm:ss')}
                    </span>
                  </div>
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-slate-500">Usuario</span>
                    <span className="text-slate-700">{log.user_email ?? '—'}</span>
                  </div>
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-slate-500">Recurso</span>
                    {log.resource_type ? (
                      <span className="text-slate-600">
                        {log.resource_type}
                        {log.resource_id && (
                          <span className="text-slate-400 ml-1 font-mono">
                            #{log.resource_id.slice(0, 8)}
                          </span>
                        )}
                      </span>
                    ) : (
                      <span className="text-slate-400">—</span>
                    )}
                  </div>
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-slate-500">IP</span>
                    <span className="text-slate-400 font-mono">{log.ip_address ?? '—'}</span>
                  </div>
                </div>
              ))
            )}
          </div>

          {/* Desktop table */}
          <div className="hidden md:block overflow-x-auto">
          <table className="w-full text-sm min-w-[600px]">
            <thead className="bg-slate-50 border-b border-slate-200">
              <tr>
                <th className="px-4 py-3 text-left font-semibold text-slate-600">Fecha</th>
                <th className="px-4 py-3 text-left font-semibold text-slate-600">Acción</th>
                <th className="px-4 py-3 text-left font-semibold text-slate-600">Usuario</th>
                <th className="px-4 py-3 text-left font-semibold text-slate-600">Recurso</th>
                <th className="px-4 py-3 text-left font-semibold text-slate-600">IP</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {data?.items.length === 0 ? (
                <tr>
                  <td colSpan={5} className="px-4 py-8 text-center text-slate-400">
                    Sin registros
                  </td>
                </tr>
              ) : (
                data?.items.map((log) => (
                  <tr key={log.id} className="hover:bg-slate-50/50">
                    <td className="px-4 py-3 text-slate-500 text-xs whitespace-nowrap">
                      {format(new Date(log.created_at), 'dd/MM/yyyy HH:mm:ss')}
                    </td>
                    <td className="px-4 py-3">
                      <span className="font-mono text-xs bg-slate-100 text-slate-700 rounded px-1.5 py-0.5">
                        {log.action}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <div className="text-slate-700 text-xs">{log.user_email ?? '—'}</div>
                    </td>
                    <td className="px-4 py-3">
                      {log.resource_type ? (
                        <span className="text-xs text-slate-600">
                          {log.resource_type}
                          {log.resource_id && (
                            <span className="text-slate-400 ml-1 font-mono">
                              #{log.resource_id.slice(0, 8)}
                            </span>
                          )}
                        </span>
                      ) : (
                        <span className="text-slate-400">—</span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-xs text-slate-400 font-mono">
                      {log.ip_address ?? '—'}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
          </div>
        </>)}
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between">
          <p className="text-sm text-slate-500">
            {data?.total ?? 0} registros · Página {page + 1} de {totalPages}
          </p>
          <div className="flex gap-2">
            <button
              onClick={() => setPage((p) => Math.max(0, p - 1))}
              disabled={page === 0}
              className="flex items-center gap-1 rounded-xl border border-slate-200 px-3 py-2 text-sm disabled:opacity-40 hover:bg-slate-50"
            >
              <ChevronLeft className="h-4 w-4" /> Anterior
            </button>
            <button
              onClick={() => setPage((p) => Math.min(totalPages - 1, p + 1))}
              disabled={page >= totalPages - 1}
              className="flex items-center gap-1 rounded-xl border border-slate-200 px-3 py-2 text-sm disabled:opacity-40 hover:bg-slate-50"
            >
              Siguiente <ChevronRight className="h-4 w-4" />
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
