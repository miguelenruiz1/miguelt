import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { useQueryClient } from '@tanstack/react-query'
import {
  RefreshCw, CheckCircle2, XCircle, Clock, AlertTriangle, ExternalLink,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { useRecords } from '@/hooks/useCompliance'
import { complianceApi } from '@/lib/compliance-api'
import { useToast } from '@/store/toast'
import type { ComplianceRecord } from '@/types/compliance'

// ─── Status styling ──────────────────────────────────────────────────────────

const DDS_STATUS_LABEL: Record<string, string> = {
  not_required: 'No requerido',
  pending: 'Pendiente',
  submitted: 'En validacion',
  accepted: 'Aceptada',
  validated: 'Validada',
  rejected: 'Rechazada',
  amended: 'Enmendada',
}

const DDS_STATUS_CLASS: Record<string, string> = {
  submitted: 'bg-amber-50 text-amber-700 border-amber-200',
  pending: 'bg-amber-50 text-amber-700 border-amber-200',
  validated: 'bg-emerald-50 text-emerald-700 border-emerald-200',
  accepted: 'bg-emerald-50 text-emerald-700 border-emerald-200',
  rejected: 'bg-red-50 text-red-700 border-red-200',
  amended: 'bg-purple-50 text-purple-700 border-purple-200',
  not_required: 'bg-muted text-muted-foreground border-border',
}

function StatusBadge({ status }: { status: string }) {
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-semibold border',
        DDS_STATUS_CLASS[status] || 'bg-muted text-muted-foreground border-border',
      )}
    >
      {(status === 'validated' || status === 'accepted') && <CheckCircle2 className="h-3 w-3" />}
      {status === 'rejected' && <XCircle className="h-3 w-3" />}
      {status === 'submitted' && <Clock className="h-3 w-3" />}
      {DDS_STATUS_LABEL[status] || status}
    </span>
  )
}

// ─── Filters ─────────────────────────────────────────────────────────────────

type StatusFilter = 'all' | 'submitted' | 'validated' | 'rejected' | 'amended'

interface Filters {
  status: StatusFilter
  commodity: string
  dateFrom: string
  dateTo: string
}

function matchesFilters(rec: ComplianceRecord, f: Filters): boolean {
  if (f.status === 'all' && !rec.declaration_status) return false
  if (f.status !== 'all') {
    // 'validated' bucket includes both 'validated' and 'accepted'
    if (f.status === 'validated') {
      if (rec.declaration_status !== 'validated' && rec.declaration_status !== 'accepted') {
        return false
      }
    } else if (rec.declaration_status !== f.status) {
      return false
    }
  }
  if (f.commodity && rec.commodity_type !== f.commodity) return false
  if (f.dateFrom && rec.declaration_submission_date) {
    if (rec.declaration_submission_date < f.dateFrom) return false
  }
  if (f.dateTo && rec.declaration_submission_date) {
    if (rec.declaration_submission_date > f.dateTo) return false
  }
  return true
}

// ─── Page ────────────────────────────────────────────────────────────────────

export default function DDSStatusPage() {
  const [filters, setFilters] = useState<Filters>({
    status: 'all',
    commodity: '',
    dateFrom: '',
    dateTo: '',
  })
  const toast = useToast()
  const qc = useQueryClient()

  // Pull all records that have an EUDR declaration status !== not_required.
  const { data: records = [], isLoading, refetch } = useRecords({ has_declaration: true })
  const [refreshing, setRefreshing] = useState(false)

  const rows = useMemo(
    () => records.filter(r => matchesFilters(r, filters)),
    [records, filters],
  )

  // KPIs (over all fetched records, not just filtered)
  const kpis = useMemo(() => {
    const tally = { submitted: 0, validated: 0, rejected: 0, amended: 0, total: 0 }
    for (const r of records) {
      if (!r.declaration_status || r.declaration_status === 'not_required') continue
      tally.total += 1
      if (r.declaration_status === 'submitted' || r.declaration_status === 'pending') tally.submitted += 1
      if (r.declaration_status === 'validated' || r.declaration_status === 'accepted') tally.validated += 1
      if (r.declaration_status === 'rejected') tally.rejected += 1
      if (r.declaration_status === 'amended') tally.amended += 1
    }
    return tally
  }, [records])

  async function refreshAllSubmitted() {
    const submitted = records.filter(
      r => r.declaration_status === 'submitted' || r.declaration_status === 'pending',
    )
    if (submitted.length === 0) {
      toast.info?.('No hay DDS en estado "En validacion" para actualizar')
      return
    }
    setRefreshing(true)
    try {
      let changed = 0
      for (const r of submitted) {
        try {
          const res = await complianceApi.records.ddsStatus(r.id)
          if (res?.polled && res?.declaration_status && res.declaration_status !== r.declaration_status) {
            changed += 1
          }
        } catch (e) {
          // ignore individual failures
        }
      }
      qc.invalidateQueries({ queryKey: ['compliance', 'records'] })
      toast.success(`Actualizadas ${submitted.length} DDS — ${changed} cambios detectados`)
    } finally {
      setRefreshing(false)
    }
  }

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <h1 className="text-2xl font-bold text-foreground">DDS TRACES NT</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Panel de estado de las Declaraciones de Diligencia Debida enviadas al sistema TRACES NT de la Comision Europea.
          </p>
        </div>
        <button
          onClick={refreshAllSubmitted}
          disabled={refreshing}
          className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700 disabled:opacity-50"
        >
          <RefreshCw className={cn('h-4 w-4', refreshing && 'animate-spin')} />
          Actualizar todo
        </button>
      </div>

      {/* KPI cards */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
        <KpiCard label="Total DDS" value={kpis.total} color="muted" />
        <KpiCard label="En validacion" value={kpis.submitted} color="amber" />
        <KpiCard label="Validadas" value={kpis.validated} color="emerald" />
        <KpiCard label="Rechazadas" value={kpis.rejected} color="red" />
        <KpiCard label="Enmendadas" value={kpis.amended} color="purple" />
      </div>

      {/* Filters */}
      <div className="flex gap-3 flex-wrap items-end rounded-xl border border-border bg-card p-4">
        <div>
          <label className="block text-xs font-medium text-muted-foreground mb-1">Estado</label>
          <select
            value={filters.status}
            onChange={e => setFilters(f => ({ ...f, status: e.target.value as StatusFilter }))}
            className="rounded-lg border border-border bg-card px-3 py-1.5 text-sm"
          >
            <option value="all">Todos</option>
            <option value="submitted">En validacion</option>
            <option value="validated">Validadas</option>
            <option value="rejected">Rechazadas</option>
            <option value="amended">Enmendadas</option>
          </select>
        </div>
        <div>
          <label className="block text-xs font-medium text-muted-foreground mb-1">Commodity</label>
          <select
            value={filters.commodity}
            onChange={e => setFilters(f => ({ ...f, commodity: e.target.value }))}
            className="rounded-lg border border-border bg-card px-3 py-1.5 text-sm"
          >
            <option value="">Todos</option>
            <option value="coffee">Cafe</option>
            <option value="cacao">Cacao</option>
            <option value="palm">Palma</option>
            <option value="other">Otros</option>
          </select>
        </div>
        <div>
          <label className="block text-xs font-medium text-muted-foreground mb-1">Desde</label>
          <input
            type="date"
            value={filters.dateFrom}
            onChange={e => setFilters(f => ({ ...f, dateFrom: e.target.value }))}
            className="rounded-lg border border-border bg-card px-3 py-1.5 text-sm"
          />
        </div>
        <div>
          <label className="block text-xs font-medium text-muted-foreground mb-1">Hasta</label>
          <input
            type="date"
            value={filters.dateTo}
            onChange={e => setFilters(f => ({ ...f, dateTo: e.target.value }))}
            className="rounded-lg border border-border bg-card px-3 py-1.5 text-sm"
          />
        </div>
        <button
          onClick={() => refetch()}
          className="inline-flex items-center gap-2 rounded-lg border border-border bg-card px-3 py-1.5 text-sm hover:bg-muted"
        >
          <RefreshCw className="h-3.5 w-3.5" />
          Recargar
        </button>
      </div>

      {/* Table */}
      <div className="rounded-xl border border-border bg-card overflow-hidden">
        {isLoading ? (
          <div className="p-8 text-center text-sm text-muted-foreground">Cargando DDS...</div>
        ) : rows.length === 0 ? (
          <div className="p-8 text-center text-sm text-muted-foreground">
            <AlertTriangle className="h-5 w-5 mx-auto mb-2 opacity-50" />
            No hay DDS que coincidan con los filtros.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-muted/30 text-xs text-muted-foreground">
                <tr>
                  <th className="text-left px-3 py-2 font-semibold">Registro</th>
                  <th className="text-left px-3 py-2 font-semibold">Commodity</th>
                  <th className="text-right px-3 py-2 font-semibold">Cantidad (kg)</th>
                  <th className="text-left px-3 py-2 font-semibold">Referencia TRACES</th>
                  <th className="text-left px-3 py-2 font-semibold">Estado</th>
                  <th className="text-left px-3 py-2 font-semibold">Enviada</th>
                  <th className="text-left px-3 py-2 font-semibold">Validada</th>
                  <th className="text-right px-3 py-2 font-semibold">Acciones</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {rows.map(r => (
                  <tr key={r.id} className="hover:bg-muted/20">
                    <td className="px-3 py-2">
                      <Link
                        to={`/cumplimiento/registros/${r.id}`}
                        className="font-mono text-xs text-blue-700 hover:underline"
                      >
                        {r.id.slice(0, 8)}
                      </Link>
                      {r.product_description && (
                        <div className="text-[11px] text-muted-foreground truncate max-w-[220px]">
                          {r.product_description}
                        </div>
                      )}
                    </td>
                    <td className="px-3 py-2 capitalize">{r.commodity_type || '—'}</td>
                    <td className="px-3 py-2 text-right font-mono">
                      {r.quantity_kg != null ? Number(r.quantity_kg).toLocaleString('es-CO') : '—'}
                    </td>
                    <td className="px-3 py-2 font-mono text-xs">
                      {r.declaration_reference || <span className="text-muted-foreground">—</span>}
                    </td>
                    <td className="px-3 py-2">
                      <StatusBadge status={r.declaration_status || 'not_required'} />
                    </td>
                    <td className="px-3 py-2 text-xs">
                      {r.declaration_submission_date
                        ? new Date(r.declaration_submission_date).toLocaleDateString('es-CO')
                        : '—'}
                    </td>
                    <td className="px-3 py-2 text-xs">
                      {r.declaration_validated_at
                        ? new Date(r.declaration_validated_at).toLocaleDateString('es-CO')
                        : '—'}
                    </td>
                    <td className="px-3 py-2 text-right">
                      {r.declaration_reference && (r.declaration_status === 'validated' || r.declaration_status === 'accepted') && (
                        <a
                          href={`https://webgate.ec.europa.eu/tracesnt/directory/dds/${r.declaration_reference}`}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="inline-flex items-center gap-1 text-[11px] text-emerald-700 hover:underline"
                        >
                          <ExternalLink className="h-3 w-3" /> TRACES NT
                        </a>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}

function KpiCard({
  label, value, color,
}: {
  label: string
  value: number
  color: 'muted' | 'amber' | 'emerald' | 'red' | 'purple'
}) {
  const clsMap = {
    muted: 'bg-muted/30 text-foreground border-border',
    amber: 'bg-amber-50 text-amber-800 border-amber-200',
    emerald: 'bg-emerald-50 text-emerald-800 border-emerald-200',
    red: 'bg-red-50 text-red-800 border-red-200',
    purple: 'bg-purple-50 text-purple-800 border-purple-200',
  }
  return (
    <div className={cn('rounded-xl border p-4', clsMap[color])}>
      <div className="text-[11px] uppercase tracking-wider font-semibold opacity-70">{label}</div>
      <div className="text-2xl font-bold mt-1">{value}</div>
    </div>
  )
}
