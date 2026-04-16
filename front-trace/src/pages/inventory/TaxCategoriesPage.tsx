import { useState } from 'react'
import { Link } from 'react-router-dom'
import {
  Tags,
  Pencil,
  Lock,
  ArrowLeft,
  Info,
} from 'lucide-react'
import {
  useTaxCategories,
  useUpdateTaxCategory,
} from '@/hooks/useInventory'
import type { TaxCategory } from '@/types/inventory'
import { useToast } from '@/store/toast'

const BEHAVIOR_LABEL: Record<string, string> = {
  addition: 'Suma al total',
  withholding: 'Retiene del pagar',
}

export function TaxCategoriesPage() {
  const { data: categories = [], isLoading } = useTaxCategories()
  const [editing, setEditing] = useState<TaxCategory | null>(null)

  return (
    <div className="max-w-5xl mx-auto p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <Link
            to="/inventario/impuestos"
            className="inline-flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground mb-1"
          >
            <ArrowLeft className="h-3 w-3" /> Volver a tarifas
          </Link>
          <h1 className="text-2xl font-bold text-foreground flex items-center gap-2">
            <Tags className="h-6 w-6 text-primary" /> Impuestos DIAN (Colombia)
          </h1>
          <p className="text-sm text-muted-foreground mt-1">
            Trace soporta dos impuestos en esta versión: <strong>IVA</strong> (suma al total) y{' '}
            <strong>Retefuente</strong> (retención en la fuente). Son categorías del sistema y no
            se pueden eliminar ni renombrar el slug.
          </p>
        </div>
      </div>

      <InfoBanner />

      {isLoading ? (
        <div className="flex justify-center py-10">
          <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-primary" />
        </div>
      ) : categories.length === 0 ? (
        <div className="bg-card rounded-2xl border border-dashed border-border p-10 text-center text-sm text-muted-foreground">
          No hay categorías configuradas. Corré las migraciones del servicio para inicializar IVA y Retefuente.
        </div>
      ) : (
        <div className="bg-card rounded-2xl border border-border overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-muted border-b border-border">
              <tr>
                {['Nombre', 'Slug', 'Comportamiento', 'Tarifas', ''].map((h) => (
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
              {categories.map((c) => (
                <CategoryRow
                  key={c.id}
                  cat={c}
                  onEdit={() => setEditing(c)}
                />
              ))}
            </tbody>
          </table>
        </div>
      )}

      {editing && (
        <CategoryEditModal
          category={editing}
          onClose={() => setEditing(null)}
        />
      )}
    </div>
  )
}

function InfoBanner() {
  return (
    <div className="bg-blue-50 border border-blue-200 rounded-2xl p-4 text-sm text-blue-900 flex gap-3">
      <Info className="h-5 w-5 text-blue-700 flex-shrink-0 mt-0.5" />
      <div className="space-y-1">
        <p>
          <strong>IVA</strong>: tarifas 19% / 5% / 0% (exento). Se suma al subtotal de la factura.
        </p>
        <p>
          <strong>Retefuente</strong>: retención en la fuente. La tarifa se elige al momento de facturar
          según el concepto (servicios, honorarios, compras, etc.).
        </p>
        <p className="text-xs opacity-80">
          El soporte de INC, ICA, ReteIVA, ReteICA y Autorretención se agregará cuando un cliente lo requiera.
        </p>
      </div>
    </div>
  )
}

function CategoryRow({ cat, onEdit }: { cat: TaxCategory; onEdit: () => void }) {
  return (
    <tr className="hover:bg-muted">
      <td className="px-4 py-3">
        <div className="flex items-center gap-2 font-semibold text-foreground">
          <Lock className="h-3 w-3 text-muted-foreground" />
          {cat.name}
        </div>
        {cat.description && (
          <div className="text-xs text-muted-foreground mt-0.5">{cat.description}</div>
        )}
      </td>
      <td className="px-4 py-3 font-mono text-xs text-muted-foreground">{cat.slug}</td>
      <td className="px-4 py-3">
        <span
          className={`text-xs px-2 py-0.5 rounded-full ${
            cat.behavior === 'addition'
              ? 'bg-blue-50 text-blue-700'
              : 'bg-amber-50 text-amber-800'
          }`}
        >
          {BEHAVIOR_LABEL[cat.behavior] ?? cat.behavior}
        </span>
      </td>
      <td className="px-4 py-3 text-sm">
        <span className="inline-flex items-center justify-center min-w-[24px] h-6 rounded-full bg-muted text-foreground text-xs font-semibold px-2">
          {cat.rate_count}
        </span>
      </td>
      <td className="px-4 py-3 text-right">
        <button
          onClick={onEdit}
          className="p-1 text-muted-foreground hover:text-primary"
          title="Editar nombre / descripción"
        >
          <Pencil className="h-3.5 w-3.5" />
        </button>
      </td>
    </tr>
  )
}

function CategoryEditModal({
  category,
  onClose,
}: {
  category: TaxCategory
  onClose: () => void
}) {
  const update = useUpdateTaxCategory()
  const toast = useToast()

  const [form, setForm] = useState({
    name: category.name,
    description: category.description ?? '',
  })

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!form.name.trim()) {
      toast.error('El nombre es obligatorio')
      return
    }
    try {
      await update.mutateAsync({
        id: category.id,
        data: {
          name: form.name,
          description: form.description || null,
        },
      })
      toast.success('Categoría actualizada')
      onClose()
    } catch (err: any) {
      toast.error(err?.message ?? 'Error al guardar')
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm p-4">
      <form
        onSubmit={onSubmit}
        className="w-full max-w-md bg-card rounded-3xl shadow-2xl p-6 space-y-3"
      >
        <h2 className="text-lg font-bold text-foreground">Editar categoría</h2>

        <div className="text-xs text-amber-800 bg-amber-50 border border-amber-200 rounded-lg p-2">
          Categoría del sistema. Solo podés editar el nombre visible y la descripción —
          el slug (<code>{category.slug}</code>) y el comportamiento están bloqueados.
        </div>

        <div>
          <label className="block text-xs font-semibold text-muted-foreground mb-1">Nombre *</label>
          <input
            required
            value={form.name}
            onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
            className="w-full rounded-xl border border-border px-3 py-2 text-sm"
          />
        </div>

        <div>
          <label className="block text-xs font-semibold text-muted-foreground mb-1">Descripción</label>
          <textarea
            value={form.description ?? ''}
            onChange={(e) => setForm((f) => ({ ...f, description: e.target.value }))}
            rows={3}
            className="w-full rounded-xl border border-border px-3 py-2 text-sm"
            placeholder="Opcional"
          />
        </div>

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
            disabled={update.isPending}
            className="flex-1 rounded-xl bg-primary px-4 py-2 text-sm font-semibold text-white hover:bg-primary/90 disabled:opacity-60"
          >
            {update.isPending ? 'Guardando...' : 'Guardar'}
          </button>
        </div>
      </form>
    </div>
  )
}
