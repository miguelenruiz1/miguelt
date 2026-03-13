import { useState } from 'react'
import { Link } from 'react-router-dom'
import {
  FlaskConical, AlertTriangle, ChevronRight, Copy, Check, RefreshCw, FileDown,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { useSalesOrders } from '@/hooks/useInventory'
import { useCreateInvoice } from '@/hooks/useIntegrations'
import { useAuthStore } from '@/store/auth'
import { generateSandboxInvoicePDF } from '@/utils/generateSandboxInvoicePDF'
import type { SalesOrder } from '@/types/inventory'

export function EInvoicingSandboxPage() {
  const { data: deliveredData, refetch } = useSalesOrders({ limit: 200 })
  const createInvoiceMut = useCreateInvoice()
  const user = useAuthStore((s) => s.user)

  const [showSimModal, setShowSimModal] = useState(false)
  const [selectedSO, setSelectedSO] = useState<SalesOrder | null>(null)
  const [simResult, setSimResult] = useState<Record<string, unknown> | null>(null)
  const [copiedCufe, setCopiedCufe] = useState<string | null>(null)

  const allOrders = deliveredData?.items ?? []
  const sandboxOrders = allOrders.filter(o => o.invoice_provider === 'sandbox')
  const invoiceableStatuses = ['confirmed', 'picking', 'shipped', 'delivered']
  const uninvoicedOrders = allOrders.filter(o => !o.cufe && !o.invoice_status && invoiceableStatuses.includes(o.status))

  function copyCufe(cufe: string) {
    navigator.clipboard.writeText(cufe)
    setCopiedCufe(cufe)
    setTimeout(() => setCopiedCufe(null), 2000)
  }

  function downloadPDF(order: SalesOrder) {
    generateSandboxInvoicePDF({
      company_name: user?.company ?? 'Mi Empresa',
      company_nit: user?.tenant_id ?? '000000000',
      company_email: user?.email,
      customer_name: order.customer_name ?? 'Cliente',
      customer_nit: '222222222',
      invoice_number: order.order_number,
      invoice_date: order.confirmed_at
        ? new Date(order.confirmed_at).toLocaleDateString('es-CO')
        : new Date().toLocaleDateString('es-CO'),
      cufe: order.cufe ?? '',
      items: order.lines.map(l => ({
        description: l.product_name ?? l.product_id.slice(0, 8),
        quantity: l.qty_shipped,
        unit_price: l.unit_price,
        original_unit_price: l.original_unit_price,
        price_source: l.price_source,
        tax_rate: l.tax_rate ? l.tax_rate / 100 : 0.19,
        total: l.line_total,
      })),
      subtotal: order.subtotal,
      tax_amount: order.tax_amount,
      total: order.total,
      special_price_savings: order.lines.reduce((acc, l) => {
        if (l.price_source === 'customer_special' && l.original_unit_price != null && l.original_unit_price > l.unit_price) {
          return acc + (l.original_unit_price - l.unit_price) * l.qty_ordered
        }
        return acc
      }, 0),
    })
  }

  async function handleSimulate() {
    if (!selectedSO) return
    setSimResult(null)
    const result = await createInvoiceMut.mutateAsync({
      providerSlug: 'sandbox',
      data: {
        number: selectedSO.order_number,
        date: selectedSO.confirmed_at ?? selectedSO.created_at,
        customer: {
          nit: '222222222',
          name: selectedSO.customer_name ?? '',
          email: '',
        },
        items: selectedSO.lines.map(l => ({
          description: l.product_name ?? l.product_id.slice(0, 8),
          quantity: l.qty_shipped,
          unit_price: l.unit_price,
          tax_rate: 0.19,
          total: l.line_total,
        })),
        subtotal: selectedSO.subtotal,
        tax_amount: selectedSO.tax_amount,
        total: selectedSO.total,
      },
    })
    setSimResult(result)
    refetch()
  }

  return (
    <div className="space-y-6">
      {/* Breadcrumb */}
      <nav className="mb-4">
        <ol className="flex items-center gap-2 text-sm">
          <li className="text-gray-500">Inicio</li>
          <li><ChevronRight className="h-4 w-4 text-gray-400" /></li>
          <li className="text-indigo-500">Facturación Electrónica — Sandbox</li>
        </ol>
      </nav>

      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold text-gray-800 flex items-center gap-2">
            <FlaskConical className="h-6 w-6 text-amber-500" />
            Facturación Electrónica — Sandbox
          </h1>
          <p className="text-sm text-gray-500 mt-1">
            Simula el flujo completo de facturación electrónica sin conexión a la DIAN.
          </p>
        </div>
        <button
          onClick={() => { setShowSimModal(true); setSimResult(null); setSelectedSO(null) }}
          className="rounded-lg bg-amber-500 px-4 py-2 text-sm font-medium text-white shadow-sm transition hover:bg-amber-600"
        >
          Simular factura manualmente
        </button>
      </div>

      {/* Warning banner */}
      <div className="flex items-center gap-3 rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
        <AlertTriangle className="h-5 w-5 text-amber-500 shrink-0" />
        <span className="font-medium">Modo Sandbox — Las facturas generadas aquí no tienen validez ante la DIAN</span>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div className="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm">
          <p className="text-xs font-medium text-gray-400 uppercase">Facturas Simuladas</p>
          <p className="text-2xl font-bold text-amber-600 mt-1">{sandboxOrders.length}</p>
        </div>
        <div className="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm">
          <p className="text-xs font-medium text-gray-400 uppercase">SOs sin factura</p>
          <p className="text-2xl font-bold text-gray-600 mt-1">{uninvoicedOrders.length}</p>
        </div>
      </div>

      {/* Invoice history table */}
      <div className="space-y-4">
        <h2 className="text-lg font-semibold text-gray-800">Historial de Facturas Simuladas</h2>
        {sandboxOrders.length === 0 ? (
          <div className="rounded-2xl border border-gray-200 bg-white p-8 text-center text-sm text-gray-400">
            No hay facturas simuladas aún. Usa el botón &quot;Simular factura manualmente&quot; o entrega una Sales Order con el módulo sandbox activo.
          </div>
        ) : (
          <div className="rounded-2xl border border-gray-200 bg-white shadow-sm overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-gray-100">
                    <th className="px-5 py-3.5 text-left text-xs font-medium text-gray-500 uppercase">Orden</th>
                    <th className="px-5 py-3.5 text-left text-xs font-medium text-gray-500 uppercase">Nº Factura</th>
                    <th className="px-5 py-3.5 text-left text-xs font-medium text-gray-500 uppercase">Cliente</th>
                    <th className="px-5 py-3.5 text-right text-xs font-medium text-gray-500 uppercase">Total</th>
                    <th className="px-5 py-3.5 text-left text-xs font-medium text-gray-500 uppercase">CUFE Simulado</th>
                    <th className="px-5 py-3.5 text-left text-xs font-medium text-gray-500 uppercase">Fecha</th>
                    <th className="px-5 py-3.5 text-left text-xs font-medium text-gray-500 uppercase">Estado</th>
                    <th className="px-5 py-3.5 text-left text-xs font-medium text-gray-500 uppercase">Nota Crédito</th>
                    <th className="px-5 py-3.5 text-left text-xs font-medium text-gray-500 uppercase">Acciones</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {sandboxOrders.map(order => (
                    <tr key={order.id} className="hover:bg-gray-50/60">
                      <td className="px-5 py-3">
                        <Link to={`/inventario/ventas/${order.id}`} className="font-medium text-indigo-600 hover:text-indigo-700">
                          {order.order_number}
                        </Link>
                      </td>
                      <td className="px-5 py-3 font-mono text-xs text-amber-700">{order.invoice_number ?? '—'}</td>
                      <td className="px-5 py-3 text-gray-700">{order.customer_name ?? '—'}</td>
                      <td className="px-5 py-3 text-right font-mono text-gray-700">${order.total.toLocaleString()} {order.currency}</td>
                      <td className="px-5 py-3">
                        {order.cufe ? (
                          <div className="flex items-center gap-1.5">
                            <span className="font-mono text-xs text-gray-500" title={order.cufe}>
                              {order.cufe.slice(0, 20)}...
                            </span>
                            <button
                              onClick={() => copyCufe(order.cufe!)}
                              className="text-gray-400 hover:text-indigo-600 transition"
                              title="Copiar CUFE completo"
                            >
                              {copiedCufe === order.cufe ? <Check className="h-3.5 w-3.5 text-emerald-500" /> : <Copy className="h-3.5 w-3.5" />}
                            </button>
                          </div>
                        ) : '—'}
                      </td>
                      <td className="px-5 py-3 text-gray-500 text-xs">
                        {order.confirmed_at ? new Date(order.confirmed_at).toLocaleDateString() : '—'}
                      </td>
                      <td className="px-5 py-3">
                        <span className="inline-flex rounded-full bg-amber-50 px-2 py-0.5 text-xs font-medium text-amber-700">
                          SIMULADO
                        </span>
                      </td>
                      <td className="px-5 py-3">
                        {order.credit_note_number ? (
                          <span className="font-mono text-xs text-orange-700">{order.credit_note_number}</span>
                        ) : order.credit_note_status === 'failed' ? (
                          <span className="inline-flex rounded-full bg-red-50 px-2 py-0.5 text-xs font-medium text-red-600">Fallida</span>
                        ) : order.credit_note_status === 'pending' ? (
                          <span className="inline-flex rounded-full bg-gray-100 px-2 py-0.5 text-xs font-medium text-gray-500">Pendiente</span>
                        ) : '—'}
                      </td>
                      <td className="px-5 py-3">
                        {order.cufe && (
                          <button
                            onClick={() => downloadPDF(order)}
                            className="inline-flex items-center gap-1 text-xs font-medium text-indigo-600 hover:text-indigo-700 transition"
                          >
                            <FileDown className="h-3.5 w-3.5" /> Ver PDF
                          </button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>

      {/* Simulate modal */}
      {showSimModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4" role="dialog" aria-modal="true">
          <div className="absolute inset-0 bg-gray-900/50" onClick={() => setShowSimModal(false)} />
          <div
            onClick={e => e.stopPropagation()}
            className="relative w-full max-w-lg rounded-2xl border border-gray-200 bg-white p-6 shadow-xl space-y-5"
          >
            <div>
              <h3 className="text-lg font-semibold text-gray-800">Simular Factura Electrónica</h3>
              <p className="text-sm text-gray-500 mt-1">Selecciona una Sales Order entregada sin CUFE para simular su factura.</p>
            </div>

            {simResult ? (
              <div className="space-y-4">
                <div className="rounded-lg bg-emerald-50 border border-emerald-200 px-4 py-3 text-sm text-emerald-700">
                  Simulación exitosa
                </div>
                <div>
                  <p className="text-xs font-bold text-gray-400 uppercase mb-1">CUFE Generado</p>
                  <p className="text-xs font-mono text-gray-600 break-all bg-gray-50 rounded-lg p-3">{String(simResult.cufe ?? '')}</p>
                </div>
                <p className="text-xs text-gray-400 italic">{String(simResult.message ?? '')}</p>
                <button
                  onClick={() => setShowSimModal(false)}
                  className="w-full rounded-lg bg-indigo-500 px-4 py-2.5 text-sm font-medium text-white transition hover:bg-indigo-600"
                >
                  Cerrar
                </button>
              </div>
            ) : (
              <div className="space-y-4">
                {uninvoicedOrders.length === 0 ? (
                  <p className="text-sm text-gray-400 text-center py-4">No hay Sales Orders entregadas sin factura.</p>
                ) : (
                  <div className="max-h-60 overflow-y-auto space-y-1.5">
                    {uninvoicedOrders.map(o => (
                      <button
                        key={o.id}
                        onClick={() => setSelectedSO(o)}
                        className={cn(
                          'w-full text-left rounded-lg border px-4 py-3 text-sm transition',
                          selectedSO?.id === o.id
                            ? 'border-indigo-400 bg-indigo-50 text-indigo-700'
                            : 'border-gray-200 hover:bg-gray-50 text-gray-700',
                        )}
                      >
                        <span className="font-medium">{o.order_number}</span>
                        <span className="text-gray-400 ml-2">— {o.customer_name ?? 'Sin nombre'}</span>
                        <span className="float-right font-mono">${o.total.toLocaleString()}</span>
                      </button>
                    ))}
                  </div>
                )}

                <div className="flex justify-end gap-3 pt-1">
                  <button
                    type="button"
                    onClick={() => setShowSimModal(false)}
                    className="rounded-lg border border-gray-300 px-4 py-2.5 text-sm font-medium text-gray-700 transition hover:bg-gray-50"
                  >
                    Cancelar
                  </button>
                  <button
                    onClick={handleSimulate}
                    disabled={!selectedSO || createInvoiceMut.isPending}
                    className="rounded-lg bg-amber-500 px-5 py-2.5 text-sm font-medium text-white shadow-sm transition hover:bg-amber-600 disabled:opacity-50 flex items-center gap-2"
                  >
                    <RefreshCw className={cn('h-4 w-4', createInvoiceMut.isPending && 'animate-spin')} />
                    {createInvoiceMut.isPending ? 'Simulando...' : 'Simular'}
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
