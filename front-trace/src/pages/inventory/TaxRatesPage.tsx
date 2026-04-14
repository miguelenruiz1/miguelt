import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Receipt, Plus, Pencil, Trash2, ShieldCheck, Settings2, Info } from 'lucide-react'
import { useFormValidation } from '@/hooks/useFormValidation'
import {
  useTaxRates, useCreateTaxRate, useUpdateTaxRate,
  useDeactivateTaxRate, useTaxCategories,
} from '@/hooks/useInventory'
import type { TaxRate, TaxCategory } from '@/types/inventory'
import { useToast } from '@/store/toast'

function formatPct(rate: string | number): string {
  return `${(Number(rate) * 100).toFixed(2)}%`
}

const BEHAVIOR_BADGE: Record<string, { label: string; cls: string }> = {
  addition:    { label: 'suma',    cls: 'bg-blue-50 text-blue-700' },
  withholding: { label: 'retiene', cls: 'bg-amber-50 text-amber-800' },
}

export function TaxRatesPage() {
  const { data: rates = [], isLoading: ratesLoading } = useTaxRates({ is_active: true })
  const { data: categories = [], isLoading: catsLoading } = useTaxCategories()

  const [showCreate, setShowCreate] = useState(false)
  const [editingRate, setEditingRate] = useState<TaxRate | null>(null)

  const isLoading = ratesLoading || catsLoading

  // Group rates by category. A rate without category is "Sin clasificar".
  const grouped = categories.map((cat) => ({
    cat,
    rates: rates.filter((r) => r.category_id === cat.id),
  }))
  const orphanRates = rates.filter(
    (r) => !r.category_id || !categories.some((c) => c.id === r.category_id),
  )

  return (
    <div className="max-w-5xl mx-auto p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground flex items-center gap-2">
            <Receipt className="h-6 w-6 text-primary" /> Tarifas de Impuesto
          </h1>
          <p className="text-sm text-muted-foreground mt-1">
            Configurá tus categorías fiscales y las tarifas asociadas. El sistema soporta cualquier país: IVA/VAT/GST,
            retenciones (IRPF/Retefuente/withholding), e impuestos cumulativos (Brasil ICMS+IPI+PIS+COFINS+ISS).
          </p>
        </div>
        <div className="flex gap-2">
          <Link
            to="/inventario/configuracion/categorias-impuesto"
            className="flex items-center gap-2 rounded-2xl border border-border px-4 py-2.5 text-sm font-semibold text-foreground hover:bg-muted"
          >
            <Settings2 className="h-4 w-4" /> Categorías
          </Link>
          <button
            onClick={() => {
              setEditingRate(null)
              setShowCreate(true)
            }}
            disabled={categories.length === 0}
            title={categories.length === 0 ? 'Primero creá una categoría' : ''}
            className="flex items-center gap-2 rounded-2xl bg-primary px-4 py-2.5 text-sm font-semibold text-white hover:bg-primary/90 disabled:opacity-50"
          >
            <Plus className="h-4 w-4" /> Nueva tarifa
          </button>
        </div>
      </div>

      {isLoading ? (
        <div className="flex justify-center py-10">
          <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-primary" />
        </div>
      ) : categories.length === 0 ? (
        <EmptyState />
      ) : (
        <>
          {grouped.map(({ cat, rates: catRates }) => (
            <TaxSection
              key={cat.id}
              category={cat}
              rates={catRates}
              onEdit={(r) => {
                setEditingRate(r)
                setShowCreate(true)
              }}
            />
          ))}
          {orphanRates.length > 0 && (
            <TaxSection
              category={null}
              rates={orphanRates}
              onEdit={(r) => {
                setEditingRate(r)
                setShowCreate(true)
              }}
            />
          )}
        </>
      )}

      {showCreate && (
        <TaxRateModal
          rate={editingRate}
          categories={categories}
          onClose={() => {
            setShowCreate(false)
            setEditingRate(null)
          }}
        />
      )}
    </div>
  )
}

function EmptyState() {
  return (
    <div className="bg-card rounded-2xl border border-border p-10 text-center space-y-4">
      <Info className="h-10 w-10 text-blue-600 mx-auto" />
      <div>
        <h3 className="font-semibold text-base">Aún no tenés categorías de impuesto</h3>
        <p className="text-sm text-muted-foreground mt-2 max-w-xl mx-auto">
          Empezá creando las categorías que usa tu país: IVA, Retención en la fuente, IRPF, etc.
          Cada categoría declara su comportamiento (suma al total o retiene del pagar) y podés
          asociarle múltiples tarifas (ej: IVA con tasas 19%, 5%, 0%).
        </p>
      </div>
      <Link
        to="/inventario/configuracion/categorias-impuesto"
        className="inline-flex items-center gap-2 rounded-xl bg-primary px-4 py-2 text-sm font-semibold text-white hover:bg-primary/90"
      >
        <Plus className="h-4 w-4" /> Crear categorías
      </Link>
    </div>
  )
}

function TaxSection({
  category,
  rates,
  onEdit,
}: {
  category: TaxCategory | null
  rates: TaxRate[]
  onEdit: (r: TaxRate) => void
}) {
  const deactivate = useDeactivateTaxRate()
  const toast = useToast()

  if (!rates.length && category) {
    // Show empty section for categories with no rates
    return (
      <div>
        <div className="flex items-center gap-2 mb-2">
          <h2 className="text-base font-bold text-foreground">{category.name}</h2>
          <span className={`text-[10px] uppercase tracking-wider px-1.5 py-0.5 rounded ${BEHAVIOR_BADGE[category.behavior]?.cls ?? ''}`}>
            {BEHAVIOR_BADGE[category.behavior]?.label ?? category.behavior}
          </span>
        </div>
        <div className="bg-card rounded-2xl border border-dashed border-border p-6 text-center text-sm text-muted-foreground">
          Sin tarifas. Creá la primera con el botón "Nueva tarifa".
        </div>
      </div>
    )
  }
  if (!rates.length) return null

  return (
    <div>
      <div className="flex items-center gap-2 mb-2">
        <h2 className="text-base font-bold text-foreground">{category?.name ?? 'Sin clasificar'}</h2>
        {category && (
          <span className={`text-[10px] uppercase tracking-wider px-1.5 py-0.5 rounded ${BEHAVIOR_BADGE[category.behavior]?.cls ?? ''}`}>
            {BEHAVIOR_BADGE[category.behavior]?.label ?? category.behavior}
          </span>
        )}
        {category?.base_kind === 'subtotal_with_other_additions' && (
          <span className="text-[10px] uppercase tracking-wider px-1.5 py-0.5 rounded bg-purple-50 text-purple-700">
            cumulativo
          </span>
        )}
      </div>
      <div className="bg-card rounded-2xl border border-border overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-muted border-b border-border">
            <tr>
              {['Nombre', 'Tarifa', 'Código fiscal', 'Por defecto', 'Descripción', ''].map((h) => (
                <th
                  key={h}
                  className="px-4 py-3 text-left text-xs font-semibold text-muted-foreground uppercase tracking-wide"
                >
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-50">
            {rates.map((r) => (
              <tr key={r.id} className="hover:bg-muted">
                <td className="px-4 py-3 font-semibold text-foreground">{r.name}</td>
                <td className="px-4 py-3 font-mono text-primary font-bold">{formatPct(r.rate)}</td>
                <td className="px-4 py-3 text-muted-foreground font-mono text-xs">{r.dian_code ?? '—'}</td>
                <td className="px-4 py-3">
                  {r.is_default && (
                    <span className="inline-flex items-center gap-1 rounded-full bg-emerald-50 px-2 py-0.5 text-xs font-semibold text-emerald-700">
                      <ShieldCheck className="h-3 w-3" /> Default
                    </span>
                  )}
                </td>
                <td className="px-4 py-3 text-muted-foreground text-xs max-w-[200px] truncate">
                  {r.description ?? '—'}
                </td>
                <td className="px-4 py-3 text-right">
                  <button
                    onClick={() => onEdit(r)}
                    className="p-1 text-muted-foreground hover:text-primary"
                    title="Editar"
                  >
                    <Pencil className="h-3.5 w-3.5" />
                  </button>
                  {!r.is_default && (
                    <button
                      onClick={async () => {
                        if (confirm(`¿Desactivar tarifa "${r.name}"?`)) {
                          try {
                            await deactivate.mutateAsync(r.id)
                          } catch (err: any) {
                            toast.error(err?.message ?? 'No se pudo desactivar')
                          }
                        }
                      }}
                      className="p-1 text-muted-foreground hover:text-red-600 ml-1"
                      title="Desactivar"
                    >
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

function TaxRateModal({
  rate,
  categories,
  onClose,
}: {
  rate: TaxRate | null
  categories: TaxCategory[]
  onClose: () => void
}) {
  const create = useCreateTaxRate()
  const update = useUpdateTaxRate()
  const toast = useToast()
  const isEdit = !!rate

  const [form, setForm] = useState({
    name: rate?.name ?? '',
    category_id: rate?.category_id ?? categories[0]?.id ?? '',
    rate: rate ? String(Number(rate.rate) * 100) : '',
    dian_code: rate?.dian_code ?? '',
    is_default: rate?.is_default ?? false,
    description: rate?.description ?? '',
  })

  async function doSubmit() {
    const payload: any = {
      name: form.name,
      category_id: form.category_id,
      rate: Number(form.rate) / 100,
      dian_code: form.dian_code || null,
      is_default: form.is_default,
      description: form.description || null,
    }
    try {
      if (isEdit) {
        await update.mutateAsync({ id: rate!.id, data: payload })
        toast.success('Tarifa actualizada')
      } else {
        await create.mutateAsync(payload)
        toast.success('Tarifa creada')
      }
      onClose()
    } catch (err: any) {
      toast.error(err?.message ?? 'Error al guardar')
    }
  }

  const { formRef, handleSubmit: validateAndSubmit } = useFormValidation(doSubmit)
  const pending = create.isPending || update.isPending

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 backdrop-blur-sm p-4">
      <div className="w-full max-w-md bg-card rounded-3xl shadow-2xl p-6">
        <h2 className="text-lg font-bold text-foreground mb-4">
          {isEdit ? 'Editar Tarifa' : 'Nueva Tarifa'}
        </h2>
        <form ref={formRef} onSubmit={validateAndSubmit} noValidate className="space-y-3">
          <input
            required
            value={form.name}
            onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
            placeholder="Nombre (ej: IVA 19%) *"
            className="w-full rounded-xl border border-border px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
          />

          <div>
            <label className="block text-xs font-semibold text-muted-foreground mb-1">
              Categoría *
            </label>
            <select
              required
              value={form.category_id}
              onChange={(e) => setForm((f) => ({ ...f, category_id: e.target.value }))}
              className="w-full rounded-xl border border-border px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
            >
              {categories.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name} ({c.behavior === 'addition' ? 'suma' : 'retiene'})
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-xs font-semibold text-muted-foreground mb-1">
              Tarifa (%) *
            </label>
            <input
              required
              type="number"
              step="0.01"
              min="0"
              max="100"
              value={form.rate}
              onChange={(e) => setForm((f) => ({ ...f, rate: e.target.value }))}
              placeholder="Ej: 19"
              className="w-full rounded-xl border border-border px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
            />
          </div>

          <input
            value={form.dian_code}
            onChange={(e) => setForm((f) => ({ ...f, dian_code: e.target.value }))}
            placeholder="Código fiscal (DIAN, SAT, AEAT, etc.)"
            className="w-full rounded-xl border border-border px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
          />

          <input
            value={form.description}
            onChange={(e) => setForm((f) => ({ ...f, description: e.target.value }))}
            placeholder="Descripción (opcional)"
            className="w-full rounded-xl border border-border px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
          />

          <label className="flex items-center gap-2 text-sm text-foreground">
            <input
              type="checkbox"
              checked={form.is_default}
              onChange={(e) => setForm((f) => ({ ...f, is_default: e.target.checked }))}
              className="rounded border-slate-300"
            />
            Tarifa por defecto (para esta categoría)
          </label>

          <div className="flex gap-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 rounded-xl border border-border px-4 py-2 text-sm text-muted-foreground hover:bg-muted"
            >
              Cancelar
            </button>
            <button
              type="submit"
              disabled={pending}
              className="flex-1 rounded-xl bg-primary px-4 py-2 text-sm font-semibold text-white hover:bg-primary/90 disabled:opacity-60"
            >
              {pending ? 'Guardando...' : 'Guardar'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
