import { useState } from 'react'
import { Receipt, Plus, Pencil, Trash2, Zap, ShieldCheck } from 'lucide-react'
import { cn } from '@/lib/utils'
import {
  useTaxRates, useCreateTaxRate, useUpdateTaxRate,
  useDeactivateTaxRate, useInitializeTaxRates,
} from '@/hooks/useInventory'
import type { TaxRate } from '@/types/inventory'

const TYPE_LABELS: Record<string, string> = { iva: 'IVA', retention: 'Retención', ica: 'ICA' }

function formatPct(rate: string | number): string {
  return `${(Number(rate) * 100).toFixed(2)}%`
}

export function TaxRatesPage() {
  const { data: rates = [], isLoading } = useTaxRates({ is_active: true })
  const initialize = useInitializeTaxRates()
  const [showCreate, setShowCreate] = useState(false)
  const [editingRate, setEditingRate] = useState<TaxRate | null>(null)

  const ivaRates = rates.filter(r => r.tax_type === 'iva')
  const retentionRates = rates.filter(r => r.tax_type === 'retention')

  return (
    <div className="max-w-4xl mx-auto p-6 space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 flex items-center gap-2">
            <Receipt className="h-6 w-6 text-indigo-500" /> Tarifas de Impuesto
          </h1>
          <p className="text-sm text-slate-500 mt-1">Configura IVA, retención en la fuente y otros impuestos.</p>
        </div>
        <div className="flex gap-2">
          {rates.length === 0 && (
            <button onClick={async () => { await initialize.mutateAsync() }}
              disabled={initialize.isPending}
              className="flex items-center gap-2 rounded-2xl bg-emerald-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-emerald-700 shadow-sm disabled:opacity-60">
              <Zap className="h-4 w-4" /> {initialize.isPending ? 'Creando...' : 'Inicializar Colombia'}
            </button>
          )}
          <button onClick={() => { setEditingRate(null); setShowCreate(true) }}
            className="flex items-center gap-2 rounded-2xl bg-indigo-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-indigo-700 shadow-sm">
            <Plus className="h-4 w-4" /> Nueva tarifa
          </button>
        </div>
      </div>

      {isLoading ? (
        <div className="flex justify-center py-10">
          <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-indigo-600" />
        </div>
      ) : (
        <>
          <TaxSection title="IVA (Impuesto al Valor Agregado)" rates={ivaRates} onEdit={setEditingRate} />
          <TaxSection title="Retención en la Fuente" rates={retentionRates} onEdit={setEditingRate} />
        </>
      )}

      {(showCreate || editingRate) && (
        <TaxRateModal
          rate={editingRate}
          onClose={() => { setShowCreate(false); setEditingRate(null) }}
        />
      )}
    </div>
  )
}

function TaxSection({ title, rates, onEdit }: {
  title: string
  rates: TaxRate[]
  onEdit: (r: TaxRate) => void
}) {
  const deactivate = useDeactivateTaxRate()

  if (!rates.length) return null

  return (
    <div>
      <h2 className="text-lg font-bold text-slate-800 mb-3">{title}</h2>
      <div className="bg-white rounded-2xl border border-slate-100 shadow-sm overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-slate-50 border-b border-slate-100">
            <tr>
              {['Nombre', 'Tarifa', 'Código DIAN', 'Por defecto', 'Descripción', 'Acciones'].map(h => (
                <th key={h} className="px-4 py-3 text-left text-xs font-semibold text-slate-400 uppercase tracking-wide">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-50">
            {rates.map(r => (
              <tr key={r.id} className="hover:bg-slate-50">
                <td className="px-4 py-3 font-semibold text-slate-900">{r.name}</td>
                <td className="px-4 py-3 font-mono text-indigo-700 font-bold">{formatPct(r.rate)}</td>
                <td className="px-4 py-3 text-slate-500 font-mono text-xs">{r.dian_code ?? '—'}</td>
                <td className="px-4 py-3">
                  {r.is_default && (
                    <span className="inline-flex items-center gap-1 rounded-full bg-emerald-50 px-2 py-0.5 text-xs font-semibold text-emerald-700">
                      <ShieldCheck className="h-3 w-3" /> Default
                    </span>
                  )}
                </td>
                <td className="px-4 py-3 text-slate-400 text-xs max-w-[200px] truncate">{r.description ?? '—'}</td>
                <td className="px-4 py-3 text-right">
                  <button onClick={() => onEdit(r)} className="p-1 text-slate-400 hover:text-indigo-600">
                    <Pencil className="h-3.5 w-3.5" />
                  </button>
                  {!r.is_default && (
                    <button
                      onClick={async () => { if (confirm(`¿Desactivar tarifa "${r.name}"?`)) await deactivate.mutateAsync(r.id) }}
                      className="p-1 text-slate-400 hover:text-red-600 ml-1">
                      <Trash2 className="h-3.5 w-3.5" />
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

function TaxRateModal({ rate, onClose }: { rate: TaxRate | null; onClose: () => void }) {
  const create = useCreateTaxRate()
  const update = useUpdateTaxRate()
  const isEdit = !!rate

  const [form, setForm] = useState({
    name: rate?.name ?? '',
    tax_type: rate?.tax_type ?? 'iva',
    rate: rate ? String(Number(rate.rate) * 100) : '',
    dian_code: rate?.dian_code ?? '',
    is_default: rate?.is_default ?? false,
    description: rate?.description ?? '',
  })

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    const payload = {
      name: form.name,
      tax_type: form.tax_type,
      rate: Number(form.rate) / 100,
      dian_code: form.dian_code || null,
      is_default: form.is_default,
      description: form.description || null,
    }
    if (isEdit) {
      await update.mutateAsync({ id: rate!.id, data: payload })
    } else {
      await create.mutateAsync(payload)
    }
    onClose()
  }

  const pending = create.isPending || update.isPending

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 backdrop-blur-sm">
      <div className="w-full max-w-md bg-white rounded-3xl shadow-2xl p-6">
        <h2 className="text-lg font-bold text-slate-900 mb-4">
          {isEdit ? 'Editar Tarifa' : 'Nueva Tarifa'}
        </h2>
        <form onSubmit={handleSubmit} className="space-y-3">
          <input required value={form.name} onChange={e => setForm(f => ({ ...f, name: e.target.value }))}
            placeholder="Nombre *" className="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400" />
          <div className="grid grid-cols-2 gap-3">
            <select value={form.tax_type} onChange={e => setForm(f => ({ ...f, tax_type: e.target.value }))}
              disabled={isEdit}
              className="rounded-xl border border-slate-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400 disabled:opacity-60">
              <option value="iva">IVA</option>
              <option value="retention">Retención</option>
              <option value="ica">ICA</option>
            </select>
            <input required type="number" step="0.01" min="0" max="100" value={form.rate}
              onChange={e => setForm(f => ({ ...f, rate: e.target.value }))}
              placeholder="Tarifa % *" className="rounded-xl border border-slate-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400" />
          </div>
          <input value={form.dian_code} onChange={e => setForm(f => ({ ...f, dian_code: e.target.value }))}
            placeholder="Código DIAN (opcional)" className="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400" />
          <input value={form.description} onChange={e => setForm(f => ({ ...f, description: e.target.value }))}
            placeholder="Descripción (opcional)" className="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400" />
          <label className="flex items-center gap-2 text-sm text-slate-700">
            <input type="checkbox" checked={form.is_default} onChange={e => setForm(f => ({ ...f, is_default: e.target.checked }))}
              className="rounded border-slate-300" />
            Tarifa por defecto (para este tipo)
          </label>
          <div className="flex gap-3 pt-2">
            <button type="button" onClick={onClose}
              className="flex-1 rounded-xl border border-slate-200 px-4 py-2 text-sm text-slate-600 hover:bg-slate-50">Cancelar</button>
            <button type="submit" disabled={pending}
              className="flex-1 rounded-xl bg-indigo-600 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-700 disabled:opacity-60">
              {pending ? 'Guardando...' : 'Guardar'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
