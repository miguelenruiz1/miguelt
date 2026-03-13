import { Link } from 'react-router-dom'
import {
  ArrowLeft, DollarSign, Clock, AlertTriangle, XCircle, CreditCard,
  ChevronRight, CalendarClock, Receipt,
} from 'lucide-react'
import { usePlatformSales } from '@/hooks/usePlatform'
import { cn } from '@/lib/utils'

function KpiCard({ label, value, icon: Icon, color, subtext }: {
  label: string; value: string | number; icon: React.ElementType; color: string; subtext?: string
}) {
  return (
    <div className="bg-white rounded-2xl border border-slate-200/60 p-5 shadow-sm">
      <div className="flex items-center justify-between mb-3">
        <span className="text-xs font-semibold text-slate-500 uppercase tracking-wide">{label}</span>
        <div className={`h-9 w-9 rounded-xl flex items-center justify-center ${color}`}>
          <Icon className="h-4.5 w-4.5 text-white" />
        </div>
      </div>
      <div className="text-2xl font-bold text-slate-900">{value}</div>
      {subtext && <p className="text-xs text-slate-500 mt-1">{subtext}</p>}
    </div>
  )
}

export function PlatformSalesPage() {
  const { data, isLoading } = usePlatformSales()

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600" />
      </div>
    )
  }
  if (!data) return null

  return (
    <div className="space-y-6">
      <div>
        <Link to="/platform" className="inline-flex items-center gap-1 text-sm text-slate-500 hover:text-indigo-600 mb-2">
          <ArrowLeft className="h-4 w-4" /> Panel
        </Link>
        <h1 className="text-2xl font-bold text-slate-900">Ventas & Cobros</h1>
        <p className="text-sm text-slate-500 mt-1">
          Renovaciones proximas, facturas pendientes, bajas y seguimiento de cobros en tiempo real.
        </p>
      </div>

      {/* KPIs */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <KpiCard
          label="Renovaciones Proximas"
          value={data.upcoming_renewal_count}
          icon={CalendarClock}
          color="bg-blue-500"
          subtext="En los proximos 30 dias"
        />
        <KpiCard
          label="Vencidas"
          value={data.overdue_count}
          icon={AlertTriangle}
          color={data.overdue_count > 0 ? 'bg-red-500' : 'bg-emerald-500'}
          subtext="Periodo expirado sin pago"
        />
        <KpiCard
          label="Facturado Pendiente"
          value={`$${data.total_open_amount.toLocaleString()}`}
          icon={Receipt}
          color="bg-amber-500"
          subtext={`${data.open_invoices.length} facturas abiertas`}
        />
        <KpiCard
          label="Bajas Este Mes"
          value={data.canceled_this_month_count}
          icon={XCircle}
          color={data.canceled_this_month_count > 0 ? 'bg-red-500' : 'bg-emerald-500'}
          subtext={`${data.paid_this_month_count} facturas pagadas`}
        />
      </div>

      {/* Upcoming renewals */}
      <div className="bg-white rounded-2xl border border-slate-200/60 shadow-sm overflow-hidden">
        <div className="px-6 py-4 border-b border-slate-100 flex items-center gap-2">
          <Clock className="h-4 w-4 text-blue-500" />
          <h3 className="text-sm font-semibold text-slate-700">Renovaciones Proximas (30 dias)</h3>
          <span className="ml-auto text-xs text-slate-400">{data.upcoming_renewals.length} empresas</span>
        </div>
        {data.upcoming_renewals.length === 0 ? (
          <p className="px-6 py-8 text-sm text-slate-400 text-center">Sin renovaciones proximas</p>
        ) : (
          <div className="divide-y divide-slate-100">
            {data.upcoming_renewals.map(s => {
              const daysLeft = s.current_period_end
                ? Math.ceil((new Date(s.current_period_end).getTime() - Date.now()) / 86_400_000)
                : null
              return (
                <div key={s.tenant_id} className="px-6 py-3 flex items-center gap-4 hover:bg-slate-50/60">
                  <div className="flex-1 min-w-0">
                    <Link
                      to={`/platform/tenants/${encodeURIComponent(s.tenant_id)}`}
                      className="text-sm font-semibold text-indigo-600 hover:underline"
                    >
                      {s.tenant_id}
                    </Link>
                    <p className="text-xs text-slate-400">{s.plan_name} - ${s.price_monthly}/mes</p>
                  </div>
                  <div className="text-right">
                    <span className={cn(
                      'text-sm font-semibold',
                      daysLeft != null && daysLeft <= 7 ? 'text-red-600' : 'text-slate-700',
                    )}>
                      {daysLeft != null ? `${daysLeft} dias` : '-'}
                    </span>
                    <p className="text-xs text-slate-400">
                      {s.current_period_end ? new Date(s.current_period_end).toLocaleDateString('es') : '-'}
                    </p>
                  </div>
                  <Link to={`/platform/tenants/${encodeURIComponent(s.tenant_id)}`} className="text-slate-400 hover:text-indigo-600">
                    <ChevronRight className="h-4 w-4" />
                  </Link>
                </div>
              )
            })}
          </div>
        )}
      </div>

      {/* Overdue */}
      {data.overdue.length > 0 && (
        <div className="bg-white rounded-2xl border border-red-200 shadow-sm overflow-hidden">
          <div className="px-6 py-4 border-b border-red-100 bg-red-50/50 flex items-center gap-2">
            <AlertTriangle className="h-4 w-4 text-red-500" />
            <h3 className="text-sm font-semibold text-red-700">Vencidas — Accion Requerida</h3>
            <span className="ml-auto text-xs text-red-500">{data.overdue.length} empresas</span>
          </div>
          <div className="divide-y divide-red-100">
            {data.overdue.map(s => {
              const daysOverdue = s.current_period_end
                ? Math.ceil((Date.now() - new Date(s.current_period_end).getTime()) / 86_400_000)
                : null
              return (
                <div key={s.tenant_id} className="px-6 py-3 flex items-center gap-4 hover:bg-red-50/30">
                  <div className="flex-1 min-w-0">
                    <Link
                      to={`/platform/tenants/${encodeURIComponent(s.tenant_id)}`}
                      className="text-sm font-semibold text-red-600 hover:underline"
                    >
                      {s.tenant_id}
                    </Link>
                    <p className="text-xs text-slate-400">{s.plan_name} - ${s.price_monthly}/mes</p>
                  </div>
                  <span className="text-sm font-semibold text-red-600">
                    {daysOverdue != null ? `${daysOverdue} dias vencido` : '-'}
                  </span>
                  <Link to={`/platform/tenants/${encodeURIComponent(s.tenant_id)}`} className="text-red-400 hover:text-red-600">
                    <ChevronRight className="h-4 w-4" />
                  </Link>
                </div>
              )
            })}
          </div>
        </div>
      )}

      {/* Open invoices */}
      <div className="bg-white rounded-2xl border border-slate-200/60 shadow-sm overflow-hidden">
        <div className="px-6 py-4 border-b border-slate-100 flex items-center gap-2">
          <CreditCard className="h-4 w-4 text-amber-500" />
          <h3 className="text-sm font-semibold text-slate-700">Facturas Pendientes</h3>
          <span className="ml-auto text-xs text-slate-400">${data.total_open_amount.toLocaleString()} total</span>
        </div>
        {data.open_invoices.length === 0 ? (
          <p className="px-6 py-8 text-sm text-slate-400 text-center">Sin facturas pendientes</p>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-slate-50 border-b border-slate-100">
                <th className="text-left px-5 py-2.5 font-semibold text-slate-600">Factura</th>
                <th className="text-left px-5 py-2.5 font-semibold text-slate-600">Empresa</th>
                <th className="text-right px-5 py-2.5 font-semibold text-slate-600">Monto</th>
                <th className="text-left px-5 py-2.5 font-semibold text-slate-600">Creada</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {data.open_invoices.map(inv => (
                <tr key={inv.id} className="hover:bg-slate-50/60">
                  <td className="px-5 py-2.5 font-mono text-xs text-slate-700">{inv.invoice_number}</td>
                  <td className="px-5 py-2.5">
                    <Link
                      to={`/platform/tenants/${encodeURIComponent(inv.tenant_id)}`}
                      className="text-indigo-600 hover:underline"
                    >
                      {inv.tenant_id}
                    </Link>
                  </td>
                  <td className="px-5 py-2.5 text-right font-semibold">${inv.amount.toLocaleString()} {inv.currency}</td>
                  <td className="px-5 py-2.5 text-slate-500">
                    {inv.created_at ? new Date(inv.created_at).toLocaleDateString('es') : '-'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Recently canceled */}
      {data.recently_canceled.length > 0 && (
        <div className="bg-white rounded-2xl border border-slate-200/60 shadow-sm overflow-hidden">
          <div className="px-6 py-4 border-b border-slate-100 flex items-center gap-2">
            <XCircle className="h-4 w-4 text-red-400" />
            <h3 className="text-sm font-semibold text-slate-700">Bajas Recientes</h3>
          </div>
          <div className="divide-y divide-slate-100">
            {data.recently_canceled.map(s => (
              <div key={s.tenant_id} className="px-6 py-3 flex items-center gap-4 hover:bg-slate-50/60">
                <div className="flex-1 min-w-0">
                  <Link
                    to={`/platform/tenants/${encodeURIComponent(s.tenant_id)}`}
                    className="text-sm font-semibold text-slate-700 hover:text-indigo-600"
                  >
                    {s.tenant_id}
                  </Link>
                  <p className="text-xs text-slate-400">
                    {s.plan_name}
                    {s.cancellation_reason ? ` — "${s.cancellation_reason}"` : ''}
                  </p>
                </div>
                <div className="text-xs text-slate-400">
                  {s.canceled_at ? new Date(s.canceled_at).toLocaleDateString('es') : '-'}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
