import React, { useState } from 'react'
import { ClipboardList, Search, ChevronLeft, ChevronRight, ChevronDown, ChevronUp, User } from 'lucide-react'
import { useInventoryAudit } from '@/hooks/useInventory'
import { format } from 'date-fns'

const PAGE_SIZE = 25

const RESOURCE_TYPE_OPTIONS = [
  { value: '', label: 'Todos' },
  { value: 'product', label: 'Productos' },
  { value: 'warehouse', label: 'Bodegas' },
  { value: 'supplier', label: 'Proveedores' },
  { value: 'purchase_order', label: 'Órdenes de compra' },
  { value: 'stock', label: 'Stock' },
  { value: 'serial', label: 'Seriales' },
  { value: 'batch', label: 'Lotes' },
  { value: 'recipe', label: 'Recetas' },
  { value: 'production_run', label: 'Producción' },
  { value: 'cycle_count', label: 'Conteo cíclico' },
  { value: 'event', label: 'Eventos' },
  { value: 'config', label: 'Configuración' },
  { value: 'sales_order', label: 'Órdenes de venta' },
  { value: 'customer', label: 'Clientes' },
  { value: 'customer_type', label: 'Tipos de cliente' },
]

const RESOURCE_TYPE_LABELS: Record<string, string> = {
  product: 'Producto',
  warehouse: 'Bodega',
  supplier: 'Proveedor',
  purchase_order: 'Orden de compra',
  stock: 'Stock',
  serial: 'Serial',
  batch: 'Lote',
  recipe: 'Receta',
  production_run: 'Producción',
  cycle_count: 'Conteo cíclico',
  event: 'Evento',
  config: 'Configuración',
  sales_order: 'Orden de venta',
  customer: 'Cliente',
  customer_type: 'Tipo de cliente',
}

function DiffViewer({ label, data }: { label: string; data: Record<string, unknown> | null }) {
  if (!data || Object.keys(data).length === 0) return null
  return (
    <div className="flex-1 min-w-0">
      <p className="text-xs font-semibold text-muted-foreground mb-1">{label}</p>
      <pre className="text-xs bg-muted rounded-lg p-3 overflow-x-auto max-h-48 text-foreground whitespace-pre-wrap break-all">
        {JSON.stringify(data, null, 2)}
      </pre>
    </div>
  )
}

export function InventoryAuditPage() {
  const [page, setPage] = useState(0)
  const [action, setAction] = useState('')
  const [resourceType, setResourceType] = useState('')
  const [dateFrom, setDateFrom] = useState('')
  const [dateTo, setDateTo] = useState('')
  const [expandedRow, setExpandedRow] = useState<string | null>(null)

  const { data, isLoading } = useInventoryAudit({
    action: action || undefined,
    resource_type: resourceType || undefined,
    date_from: dateFrom || undefined,
    date_to: dateTo || undefined,
    offset: page * PAGE_SIZE,
    limit: PAGE_SIZE,
  })

  const totalPages = data ? Math.ceil(data.total / PAGE_SIZE) : 0

  const clearFilters = () => {
    setAction('')
    setResourceType('')
    setDateFrom('')
    setDateTo('')
    setPage(0)
  }

  const hasFilters = action || resourceType || dateFrom || dateTo

  return (
    <div className="p-8 space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-amber-100">
          <ClipboardList className="h-5 w-5 text-amber-600" />
        </div>
        <div>
          <h1 className="text-2xl font-bold text-foreground">Auditoría de Inventario</h1>
          <p className="text-sm text-muted-foreground">Registro de todas las acciones del módulo de inventario</p>
        </div>
      </div>

      {/* Filters */}
      <div className="flex gap-3 flex-wrap items-end">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <input
            value={action}
            onChange={(e) => { setAction(e.target.value); setPage(0) }}
            placeholder="Buscar acción..."
            className="rounded-xl border border-border bg-card pl-9 pr-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring w-60"
          />
        </div>
        <select
          value={resourceType}
          onChange={(e) => { setResourceType(e.target.value); setPage(0) }}
          className="rounded-xl border border-border bg-card px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
        >
          {RESOURCE_TYPE_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value}>{opt.label}</option>
          ))}
        </select>
        <div className="flex items-center gap-2">
          <input
            type="date"
            value={dateFrom}
            onChange={(e) => { setDateFrom(e.target.value); setPage(0) }}
            className="rounded-xl border border-border bg-card px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
          />
          <span className="text-muted-foreground text-sm">—</span>
          <input
            type="date"
            value={dateTo}
            onChange={(e) => { setDateTo(e.target.value); setPage(0) }}
            className="rounded-xl border border-border bg-card px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
          />
        </div>
        {hasFilters && (
          <button
            onClick={clearFilters}
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
        ) : (
          <>
          {/* Mobile cards */}
          <div className="space-y-3 p-4 md:hidden">
            {data?.items.length === 0 ? (
              <p className="text-center text-muted-foreground py-8">Sin registros</p>
            ) : data?.items.map((log) => {
              const displayAction = log.description || log.action
              const resourceLabel = RESOURCE_TYPE_LABELS[log.resource_type] || log.resource_type
              return (
                <div key={log.id} className="rounded-xl border border-border bg-card p-4  space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium text-foreground line-clamp-2">{displayAction}</span>
                  </div>
                  <div className="space-y-1 text-sm">
                    <div className="flex justify-between"><span className="text-muted-foreground">Fecha</span><span className="text-muted-foreground text-xs">{format(new Date(log.created_at), 'dd/MM/yyyy HH:mm')}</span></div>
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Usuario</span>
                      <span className="text-muted-foreground text-xs">{log.user_name || log.user_email || '—'}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Recurso</span>
                      <span className="text-muted-foreground text-xs">
                        {log.resource_type ? (
                          <>{resourceLabel}{log.resource_id && <span className="text-muted-foreground ml-1 font-mono">#{log.resource_id.slice(0, 8)}</span>}</>
                        ) : '—'}
                      </span>
                    </div>
                    <div className="flex justify-between"><span className="text-muted-foreground">IP</span><span className="text-muted-foreground text-xs font-mono">{log.ip_address ?? '—'}</span></div>
                  </div>
                </div>
              )
            })}
          </div>

          {/* Desktop table */}
          <div className="hidden md:block overflow-x-auto">
          <table className="w-full text-sm min-w-[600px]">
            <thead className="bg-muted border-b border-border">
              <tr>
                <th className="px-4 py-3 text-left font-semibold text-muted-foreground w-8" />
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
                  <td colSpan={6} className="px-4 py-8 text-center text-muted-foreground">
                    Sin registros
                  </td>
                </tr>
              ) : (
                data?.items.map((log) => {
                  const isExpanded = expandedRow === log.id
                  const hasDiff = log.old_data || log.new_data
                  const displayAction = log.description || log.action
                  const resourceLabel = RESOURCE_TYPE_LABELS[log.resource_type] || log.resource_type
                  return (
                    <React.Fragment key={log.id}>
                      <tr
                        className={`border-b border-border ${hasDiff ? 'cursor-pointer hover:bg-muted/50' : ''} ${isExpanded ? 'bg-muted/50' : ''}`}
                        onClick={() => hasDiff && setExpandedRow(isExpanded ? null : log.id)}
                      >
                        <td className="px-4 py-3 w-8">
                          {hasDiff && (
                            isExpanded
                              ? <ChevronUp className="h-3.5 w-3.5 text-muted-foreground" />
                              : <ChevronDown className="h-3.5 w-3.5 text-muted-foreground" />
                          )}
                        </td>
                        <td className="px-4 py-3 text-muted-foreground text-xs whitespace-nowrap">
                          {format(new Date(log.created_at), 'dd/MM/yyyy HH:mm')}
                        </td>
                        <td className="px-4 py-3 text-sm text-foreground">
                          {displayAction}
                        </td>
                        <td className="px-4 py-3">
                          {(log.user_name || log.user_email) ? (
                            <div className="flex items-center gap-2">
                              <div className="flex h-6 w-6 items-center justify-center rounded-full bg-primary/15 flex-shrink-0">
                                <User className="h-3 w-3 text-primary" />
                              </div>
                              <div className="min-w-0">
                                <div className="text-xs font-medium text-foreground truncate">{log.user_name || log.user_email}</div>
                              </div>
                            </div>
                          ) : (
                            <span className="text-muted-foreground text-xs">—</span>
                          )}
                        </td>
                        <td className="px-4 py-3 text-xs text-muted-foreground">
                          {log.resource_type ? (
                            <>{resourceLabel}{log.resource_id && <span className="text-muted-foreground ml-1 font-mono">#{log.resource_id.slice(0, 8)}</span>}</>
                          ) : '—'}
                        </td>
                        <td className="px-4 py-3 text-xs text-muted-foreground font-mono">
                          {log.ip_address ?? '—'}
                        </td>
                      </tr>
                      {isExpanded && hasDiff && (
                        <tr>
                          <td colSpan={6} className="px-6 pb-4 border-b border-border bg-muted/30">
                            <div className="flex gap-4 pt-3">
                              <DiffViewer label="Datos anteriores" data={log.old_data} />
                              <DiffViewer label="Datos nuevos" data={log.new_data} />
                            </div>
                          </td>
                        </tr>
                      )}
                    </React.Fragment>
                  )
                })
              )}
            </tbody>
          </table>
          </div>
          </>
        )}
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
