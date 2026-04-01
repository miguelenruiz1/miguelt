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
          <h1 className="text-2xl font-bold text-foreground">Auditoría</h1>
          <p className="text-sm text-muted-foreground">Registro de acciones del sistema</p>
        </div>
      </div>

      {/* Filters */}
      <div className="flex gap-3 flex-wrap">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <input
            value={action}
            onChange={(e) => { setAction(e.target.value); setPage(0) }}
            placeholder="Filtrar por acción..."
            className="rounded-xl border border-border bg-card pl-9 pr-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring w-52"
          />
        </div>
        <input
          value={resourceType}
          onChange={(e) => { setResourceType(e.target.value); setPage(0) }}
          placeholder="Tipo de recurso..."
          className="rounded-xl border border-border bg-card px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring w-44"
        />
        {(action || resourceType) && (
          <button
            onClick={() => { setAction(''); setResourceType(''); setPage(0) }}
            className="text-sm text-muted-foreground hover:text-foreground px-3"
          >
            Limpiar
          </button>
        )}
      </div>

      {/* Table */}
      <div className="bg-card/80 rounded-2xl border border-border  overflow-hidden">
        {isLoading ? (
          <div className="p-8 text-center text-muted-foreground">Cargando...</div>
        ) : (<>
          {/* Mobile cards */}
          <div className="space-y-3 p-4 md:hidden">
            {data?.items.length === 0 ? (
              <div className="py-8 text-center text-muted-foreground">Sin registros</div>
            ) : (
              data?.items.map((log) => (
                <div key={log.id} className="rounded-xl border border-border bg-card p-4  space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="font-mono text-xs bg-secondary text-foreground rounded px-1.5 py-0.5">
                      {log.action}
                    </span>
                    <span className="text-xs text-muted-foreground">
                      {format(new Date(log.created_at), 'dd/MM/yyyy HH:mm:ss')}
                    </span>
                  </div>
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-muted-foreground">Usuario</span>
                    <span className="text-foreground">{log.user_email ?? '—'}</span>
                  </div>
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-muted-foreground">Recurso</span>
                    {log.resource_type ? (
                      <span className="text-muted-foreground">
                        {log.resource_type}
                        {log.resource_id && (
                          <span className="text-muted-foreground ml-1 font-mono">
                            #{log.resource_id.slice(0, 8)}
                          </span>
                        )}
                      </span>
                    ) : (
                      <span className="text-muted-foreground">—</span>
                    )}
                  </div>
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-muted-foreground">IP</span>
                    <span className="text-muted-foreground font-mono">{log.ip_address ?? '—'}</span>
                  </div>
                </div>
              ))
            )}
          </div>

          {/* Desktop table */}
          <div className="hidden md:block overflow-x-auto">
          <table className="w-full text-sm min-w-[600px]">
            <thead className="bg-muted border-b border-border">
              <tr>
                <th className="px-4 py-3 text-left font-semibold text-muted-foreground">Fecha</th>
                <th className="px-4 py-3 text-left font-semibold text-muted-foreground">Acción</th>
                <th className="px-4 py-3 text-left font-semibold text-muted-foreground">Usuario</th>
                <th className="px-4 py-3 text-left font-semibold text-muted-foreground">Recurso</th>
                <th className="px-4 py-3 text-left font-semibold text-muted-foreground">IP</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {data?.items.length === 0 ? (
                <tr>
                  <td colSpan={5} className="px-4 py-8 text-center text-muted-foreground">
                    Sin registros
                  </td>
                </tr>
              ) : (
                data?.items.map((log) => (
                  <tr key={log.id} className="hover:bg-muted/50">
                    <td className="px-4 py-3 text-muted-foreground text-xs whitespace-nowrap">
                      {format(new Date(log.created_at), 'dd/MM/yyyy HH:mm:ss')}
                    </td>
                    <td className="px-4 py-3">
                      <span className="font-mono text-xs bg-secondary text-foreground rounded px-1.5 py-0.5">
                        {log.action}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <div className="text-foreground text-xs">{log.user_email ?? '—'}</div>
                    </td>
                    <td className="px-4 py-3">
                      {log.resource_type ? (
                        <span className="text-xs text-muted-foreground">
                          {log.resource_type}
                          {log.resource_id && (
                            <span className="text-muted-foreground ml-1 font-mono">
                              #{log.resource_id.slice(0, 8)}
                            </span>
                          )}
                        </span>
                      ) : (
                        <span className="text-muted-foreground">—</span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-xs text-muted-foreground font-mono">
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
          <p className="text-sm text-muted-foreground">
            {data?.total ?? 0} registros · Página {page + 1} de {totalPages}
          </p>
          <div className="flex gap-2">
            <button
              onClick={() => setPage((p) => Math.max(0, p - 1))}
              disabled={page === 0}
              className="flex items-center gap-1 rounded-xl border border-border px-3 py-2 text-sm disabled:opacity-40 hover:bg-muted"
            >
              <ChevronLeft className="h-4 w-4" /> Anterior
            </button>
            <button
              onClick={() => setPage((p) => Math.min(totalPages - 1, p + 1))}
              disabled={page >= totalPages - 1}
              className="flex items-center gap-1 rounded-xl border border-border px-3 py-2 text-sm disabled:opacity-40 hover:bg-muted"
            >
              Siguiente <ChevronRight className="h-4 w-4" />
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
