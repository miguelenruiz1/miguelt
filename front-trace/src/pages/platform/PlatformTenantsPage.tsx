import { useState } from 'react'
import { Link } from 'react-router-dom'
import {
  Building2, Search, ChevronRight, Layers, CreditCard, Calendar,
} from 'lucide-react'
import { usePlatformTenants } from '@/hooks/usePlatform'

const STATUS_BADGE: Record<string, { bg: string; text: string; label: string }> = {
  active:   { bg: 'bg-green-100', text: 'text-green-700', label: 'Activa' },
  trialing: { bg: 'bg-blue-100', text: 'text-blue-700', label: 'Prueba' },
  past_due: { bg: 'bg-amber-100', text: 'text-amber-700', label: 'Mora' },
  canceled: { bg: 'bg-red-100', text: 'text-red-700', label: 'Cancelada' },
  expired:  { bg: 'bg-secondary', text: 'text-muted-foreground', label: 'Expirada' },
}

const MODULE_COLORS: Record<string, string> = {
  logistics: 'bg-primary/15 text-primary',
  inventory: 'bg-orange-100 text-orange-700',
}

export function PlatformTenantsPage() {
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState('')
  const [page, setPage] = useState(0)
  const limit = 20

  const { data, isLoading } = usePlatformTenants({
    search: search || undefined,
    status: statusFilter || undefined,
    offset: page * limit,
    limit,
  })

  const totalPages = data ? Math.ceil(data.total / limit) : 0

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-foreground">Empresas Registradas</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Todas las empresas inscritas en la plataforma con sus suscripciones y modulos.
        </p>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap items-center gap-3">
        <div className="relative flex-1 min-w-[240px]">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <input
            type="text"
            placeholder="Buscar por tenant ID..."
            value={search}
            onChange={e => { setSearch(e.target.value); setPage(0) }}
            className="w-full pl-9 pr-3 py-2.5 text-sm bg-card border border-border rounded-xl focus:ring-2 focus:ring-ring/20 focus:border-ring outline-none"
          />
        </div>
        <select
          value={statusFilter}
          onChange={e => { setStatusFilter(e.target.value); setPage(0) }}
          className="px-3 py-2.5 text-sm bg-card border border-border rounded-xl focus:ring-2 focus:ring-ring/20 focus:border-ring outline-none"
        >
          <option value="">Todos los estados</option>
          <option value="active">Activas</option>
          <option value="trialing">Prueba</option>
          <option value="past_due">En mora</option>
          <option value="canceled">Canceladas</option>
          <option value="expired">Expiradas</option>
        </select>
        {data && (
          <span className="text-sm text-muted-foreground">{data.total} empresa{data.total !== 1 ? 's' : ''}</span>
        )}
      </div>

      {/* Table */}
      <div className="bg-card rounded-2xl border border-border/60  overflow-hidden">
        {isLoading ? (
          <div className="flex items-center justify-center h-40">
            <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-primary" />
          </div>
        ) : !data?.items.length ? (
          <div className="text-center py-12 text-muted-foreground">
            <Building2 className="h-10 w-10 mx-auto mb-3 opacity-40" />
            <p className="text-sm">No se encontraron empresas</p>
          </div>
        ) : (
          <>
          {/* Mobile cards */}
          <div className="space-y-3 p-4 md:hidden">
            {data.items.map(t => {
              const badge = STATUS_BADGE[t.status] ?? STATUS_BADGE.expired
              return (
                <Link
                  key={t.tenant_id}
                  to={`/platform/tenants/${encodeURIComponent(t.tenant_id)}`}
                  className="block rounded-xl border border-border bg-card p-4  space-y-2 cursor-pointer hover:border-primary/30 hover:shadow-md transition-all"
                >
                  <div className="flex items-center gap-3">
                    <div className="h-9 w-9 rounded-xl bg-primary/15 flex items-center justify-center shrink-0">
                      <Building2 className="h-4 w-4 text-primary" />
                    </div>
                    <div className="min-w-0 flex-1">
                      <div className="font-semibold text-foreground truncate">{t.tenant_id}</div>
                      <div className="text-xs text-muted-foreground">{t.billing_cycle}</div>
                    </div>
                    <span className={`inline-flex px-2.5 py-1 rounded-lg text-xs font-semibold ${badge.bg} ${badge.text}`}>
                      {badge.label}
                    </span>
                  </div>
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-muted-foreground">Plan</span>
                    <span className="font-medium text-foreground">{t.plan.name} <span className="text-muted-foreground">${t.plan.price_monthly}/mes</span></span>
                  </div>
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-muted-foreground">Modulos</span>
                    <div className="flex flex-wrap gap-1 justify-end">
                      {t.active_modules.length > 0 ? t.active_modules.map(m => (
                        <span key={m} className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-xs font-medium ${MODULE_COLORS[m] ?? 'bg-secondary text-muted-foreground'}`}>
                          <Layers className="h-3 w-3" /> {m}
                        </span>
                      )) : (
                        <span className="text-muted-foreground">-</span>
                      )}
                    </div>
                  </div>
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-muted-foreground">Ingresos</span>
                    <div className="text-right">
                      <span className="font-semibold text-foreground">${t.total_revenue.toLocaleString()}</span>
                      <span className="text-muted-foreground ml-1">({t.invoice_count} facturas)</span>
                    </div>
                  </div>
                  {t.created_at && (
                    <div className="flex items-center justify-between text-xs">
                      <span className="text-muted-foreground">Registro</span>
                      <div className="flex items-center gap-1 text-muted-foreground">
                        <Calendar className="h-3 w-3" />
                        {new Date(t.created_at).toLocaleDateString('es')}
                      </div>
                    </div>
                  )}
                </Link>
              )
            })}
          </div>

          {/* Desktop table */}
          <div className="hidden md:block overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-muted border-b border-border">
                  <th className="text-left px-5 py-3 font-semibold text-muted-foreground">Tenant</th>
                  <th className="text-left px-5 py-3 font-semibold text-muted-foreground">Plan</th>
                  <th className="text-left px-5 py-3 font-semibold text-muted-foreground">Estado</th>
                  <th className="text-left px-5 py-3 font-semibold text-muted-foreground">Modulos</th>
                  <th className="text-right px-5 py-3 font-semibold text-muted-foreground">Ingresos</th>
                  <th className="text-left px-5 py-3 font-semibold text-muted-foreground">Registro</th>
                  <th className="px-3 py-3" />
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {data.items.map(t => {
                  const badge = STATUS_BADGE[t.status] ?? STATUS_BADGE.expired
                  return (
                    <tr key={t.tenant_id} className="hover:bg-muted/60 transition">
                      <td className="px-5 py-4">
                        <div className="flex items-center gap-3">
                          <div className="h-9 w-9 rounded-xl bg-primary/15 flex items-center justify-center shrink-0">
                            <Building2 className="h-4 w-4 text-primary" />
                          </div>
                          <div>
                            <div className="font-semibold text-foreground">{t.tenant_id}</div>
                            <div className="text-xs text-muted-foreground">{t.billing_cycle}</div>
                          </div>
                        </div>
                      </td>
                      <td className="px-5 py-4">
                        <span className="font-medium text-foreground">{t.plan.name}</span>
                        <div className="text-xs text-muted-foreground">${t.plan.price_monthly}/mes</div>
                      </td>
                      <td className="px-5 py-4">
                        <span className={`inline-flex px-2.5 py-1 rounded-lg text-xs font-semibold ${badge.bg} ${badge.text}`}>
                          {badge.label}
                        </span>
                      </td>
                      <td className="px-5 py-4">
                        <div className="flex flex-wrap gap-1">
                          {t.active_modules.length > 0 ? t.active_modules.map(m => (
                            <span key={m} className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-xs font-medium ${MODULE_COLORS[m] ?? 'bg-secondary text-muted-foreground'}`}>
                              <Layers className="h-3 w-3" /> {m}
                            </span>
                          )) : (
                            <span className="text-xs text-muted-foreground">-</span>
                          )}
                        </div>
                      </td>
                      <td className="px-5 py-4 text-right">
                        <div className="font-semibold text-foreground">${t.total_revenue.toLocaleString()}</div>
                        <div className="text-xs text-muted-foreground flex items-center justify-end gap-1">
                          <CreditCard className="h-3 w-3" /> {t.invoice_count} facturas
                        </div>
                      </td>
                      <td className="px-5 py-4">
                        {t.created_at && (
                          <div className="flex items-center gap-1 text-xs text-muted-foreground">
                            <Calendar className="h-3 w-3" />
                            {new Date(t.created_at).toLocaleDateString('es')}
                          </div>
                        )}
                      </td>
                      <td className="px-3 py-4">
                        <Link
                          to={`/platform/tenants/${encodeURIComponent(t.tenant_id)}`}
                          className="text-primary hover:text-primary transition"
                        >
                          <ChevronRight className="h-4 w-4" />
                        </Link>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
          </>
        )}
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-center gap-2">
          <button
            onClick={() => setPage(p => Math.max(0, p - 1))}
            disabled={page === 0}
            className="px-3 py-1.5 text-sm rounded-lg border border-border disabled:opacity-40 hover:bg-muted"
          >
            Anterior
          </button>
          <span className="text-sm text-muted-foreground">
            Pagina {page + 1} de {totalPages}
          </span>
          <button
            onClick={() => setPage(p => Math.min(totalPages - 1, p + 1))}
            disabled={page >= totalPages - 1}
            className="px-3 py-1.5 text-sm rounded-lg border border-border disabled:opacity-40 hover:bg-muted"
          >
            Siguiente
          </button>
        </div>
      )}
    </div>
  )
}
