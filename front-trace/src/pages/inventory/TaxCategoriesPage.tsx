import { useState } from 'react'
import { Link } from 'react-router-dom'
import {
  Tags,
  Plus,
  Pencil,
  Trash2,
  Lock,
  ArrowLeft,
  Info,
} from 'lucide-react'
import {
  useTaxCategories,
  useCreateTaxCategory,
  useUpdateTaxCategory,
  useDeleteTaxCategory,
} from '@/hooks/useInventory'
import type { TaxCategory, TaxBehavior, TaxBaseKind } from '@/types/inventory'
import { useToast } from '@/store/toast'
import { useConfirm } from '@/store/confirm'

const BEHAVIOR_LABEL: Record<string, string> = {
  addition: 'Suma al total',
  withholding: 'Retiene del pagar',
}
const BASE_LABEL: Record<string, string> = {
  subtotal: 'Subtotal',
  subtotal_with_other_additions: 'Subtotal + otras sumas (cumulativo)',
}

export function TaxCategoriesPage() {
  const { data: categories = [], isLoading } = useTaxCategories()
  const [editing, setEditing] = useState<TaxCategory | null>(null)
  const [showCreate, setShowCreate] = useState(false)

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
            <Tags className="h-6 w-6 text-primary" /> Categorías de impuesto
          </h1>
          <p className="text-sm text-muted-foreground mt-1">
            Cada categoría agrupa tarifas relacionadas y declara cómo se aplican: suman al total
            (IVA, VAT, GST, ICA, ICMS) o retienen del pagar (Retefuente, IRPF, ReteIVA).
          </p>
        </div>
        <button
          onClick={() => {
            setEditing(null)
            setShowCreate(true)
          }}
          className="flex items-center gap-2 rounded-2xl bg-primary px-4 py-2.5 text-sm font-semibold text-white hover:bg-primary/90"
        >
          <Plus className="h-4 w-4" /> Nueva categoría
        </button>
      </div>

      <InfoBanner />

      {isLoading ? (
        <div className="flex justify-center py-10">
          <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-primary" />
        </div>
      ) : categories.length === 0 ? (
        <div className="bg-card rounded-2xl border border-dashed border-border p-10 text-center text-sm text-muted-foreground">
          No hay categorías todavía. Creá la primera con el botón de arriba.
        </div>
      ) : (
        <div className="bg-card rounded-2xl border border-border overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-muted border-b border-border">
              <tr>
                {['Nombre', 'Slug', 'Comportamiento', 'Base de cálculo', 'Tarifas', ''].map((h) => (
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
                  onEdit={() => {
                    setEditing(c)
                    setShowCreate(true)
                  }}
                />
              ))}
            </tbody>
          </table>
        </div>
      )}

      {showCreate && (
        <CategoryModal
          category={editing}
          onClose={() => {
            setShowCreate(false)
            setEditing(null)
          }}
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
          <strong>Comportamiento:</strong> "Suma" agrega al total de la factura (IVA, VAT, GST,
          ICMS, IPI, ISS, etc.). "Retiene" descuenta del pagar (Retefuente, IRPF, withholding tax).
        </p>
        <p>
          <strong>Base de cálculo:</strong> "Subtotal" es lo común. "Cumulativo" significa que la
          tarifa se calcula sobre el subtotal <em>más</em> las sumas previas — necesario para Brasil
          (IPI sobre ICMS) y otros sistemas con impuestos en cascada.
        </p>
      </div>
    </div>
  )
}

function CategoryRow({ cat, onEdit }: { cat: TaxCategory; onEdit: () => void }) {
  const remove = useDeleteTaxCategory()
  const toast = useToast()
  const confirm = useConfirm()

  const onDelete = async () => {
    if (cat.is_system) {
      toast.error('Las categorías del sistema no se pueden eliminar')
      return
    }
    const ok = await confirm({
      title: `Eliminar categoría "${cat.name}"`,
      message: `Si la categoría tiene tarifas activas, no se podrá eliminar. Esta acción no se puede deshacer.`,
      variant: 'danger',
      confirmLabel: 'Eliminar',
    })
    if (!ok) return
    try {
      await remove.mutateAsync(cat.id)
      toast.success('Categoría eliminada')
    } catch (err: any) {
      toast.error(err?.message ?? 'No se pudo eliminar')
    }
  }

  return (
    <tr className="hover:bg-muted">
      <td className="px-4 py-3">
        <div className="flex items-center gap-2 font-semibold text-foreground">
          {cat.is_system && <Lock className="h-3 w-3 text-muted-foreground" />}
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
      <td className="px-4 py-3 text-xs text-muted-foreground">
        {BASE_LABEL[cat.base_kind] ?? cat.base_kind}
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
          title="Editar"
        >
          <Pencil className="h-3.5 w-3.5" />
        </button>
        {!cat.is_system && (
          <button
            onClick={onDelete}
            disabled={remove.isPending}
            className="p-1 text-muted-foreground hover:text-red-600 ml-1 disabled:opacity-50"
            title="Eliminar"
          >
            <Trash2 className="h-3.5 w-3.5" />
          </button>
        )}
      </td>
    </tr>
  )
}

function CategoryModal({
  category,
  onClose,
}: {
  category: TaxCategory | null
  onClose: () => void
}) {
  const create = useCreateTaxCategory()
  const update = useUpdateTaxCategory()
  const toast = useToast()
  const isEdit = !!category

  const [form, setForm] = useState({
    slug: category?.slug ?? '',
    name: category?.name ?? '',
    behavior: (category?.behavior ?? 'addition') as TaxBehavior,
    base_kind: (category?.base_kind ?? 'subtotal') as TaxBaseKind,
    description: category?.description ?? '',
    color: category?.color ?? 'blue',
    sort_order: category?.sort_order ?? 0,
  })

  const slugFromName = (name: string) =>
    name
      .toLowerCase()
      .normalize('NFD')
      .replace(/[\u0300-\u036f]/g, '')
      .replace(/[^a-z0-9]+/g, '-')
      .replace(/^-+|-+$/g, '')
      .slice(0, 50)

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!form.slug || !form.name) {
      toast.error('Slug y nombre son obligatorios')
      return
    }
    try {
      if (isEdit) {
        // System rows have a restricted set of editable fields
        const payload: any = {
          name: form.name,
          description: form.description || null,
          color: form.color || null,
          sort_order: form.sort_order,
        }
        if (!category!.is_system) {
          payload.behavior = form.behavior
          payload.base_kind = form.base_kind
        }
        await update.mutateAsync({ id: category!.id, data: payload })
        toast.success('Categoría actualizada')
      } else {
        await create.mutateAsync({
          slug: form.slug,
          name: form.name,
          behavior: form.behavior,
          base_kind: form.base_kind,
          description: form.description || null,
          color: form.color || null,
          sort_order: form.sort_order,
        })
        toast.success('Categoría creada')
      }
      onClose()
    } catch (err: any) {
      toast.error(err?.message ?? 'Error al guardar')
    }
  }

  const pending = create.isPending || update.isPending
  const isSystem = category?.is_system === true

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm p-4">
      <form
        onSubmit={onSubmit}
        className="w-full max-w-md bg-card rounded-3xl shadow-2xl p-6 space-y-3"
      >
        <h2 className="text-lg font-bold text-foreground">
          {isEdit ? 'Editar categoría' : 'Nueva categoría'}
        </h2>

        {isSystem && (
          <div className="text-xs text-amber-800 bg-amber-50 border border-amber-200 rounded-lg p-2">
            Esta es una categoría del sistema. Solo podés editar nombre y descripción.
          </div>
        )}

        <div>
          <label className="block text-xs font-semibold text-muted-foreground mb-1">Nombre *</label>
          <input
            required
            value={form.name}
            onChange={(e) => {
              const name = e.target.value
              setForm((f) => ({
                ...f,
                name,
                slug: isEdit || f.slug ? f.slug : slugFromName(name),
              }))
            }}
            placeholder="ej: IVA, IRPF, ICMS, VAT"
            className="w-full rounded-xl border border-border px-3 py-2 text-sm"
          />
        </div>

        <div>
          <label className="block text-xs font-semibold text-muted-foreground mb-1">Slug *</label>
          <input
            required
            value={form.slug}
            onChange={(e) => setForm((f) => ({ ...f, slug: e.target.value.toLowerCase() }))}
            disabled={isEdit}
            pattern="[a-z0-9_-]+"
            placeholder="ej: iva, irpf, icms"
            className="w-full rounded-xl border border-border px-3 py-2 text-sm font-mono disabled:opacity-60"
          />
          <p className="text-[10px] text-muted-foreground mt-1">
            Identificador interno. Solo minúsculas, números, guiones. No se puede cambiar después.
          </p>
        </div>

        <div>
          <label className="block text-xs font-semibold text-muted-foreground mb-1">Comportamiento *</label>
          <div className="grid grid-cols-2 gap-2">
            {(['addition', 'withholding'] as TaxBehavior[]).map((b) => (
              <button
                key={b}
                type="button"
                disabled={isSystem}
                onClick={() => setForm((f) => ({ ...f, behavior: b }))}
                className={`px-3 py-2 rounded-xl text-sm font-medium border ${
                  form.behavior === b
                    ? b === 'addition'
                      ? 'bg-blue-50 border-blue-500 text-blue-800'
                      : 'bg-amber-50 border-amber-500 text-amber-800'
                    : 'border-border text-muted-foreground'
                } ${isSystem ? 'opacity-60 cursor-not-allowed' : ''}`}
              >
                {BEHAVIOR_LABEL[b]}
              </button>
            ))}
          </div>
        </div>

        <div>
          <label className="block text-xs font-semibold text-muted-foreground mb-1">Base de cálculo</label>
          <select
            value={form.base_kind}
            disabled={isSystem}
            onChange={(e) => setForm((f) => ({ ...f, base_kind: e.target.value as TaxBaseKind }))}
            className="w-full rounded-xl border border-border px-3 py-2 text-sm disabled:opacity-60"
          >
            <option value="subtotal">{BASE_LABEL.subtotal}</option>
            <option value="subtotal_with_other_additions">{BASE_LABEL.subtotal_with_other_additions}</option>
          </select>
          <p className="text-[10px] text-muted-foreground mt-1">
            Cumulativo solo se usa en sistemas como Brasil (IPI calculado sobre subtotal+ICMS).
          </p>
        </div>

        <div>
          <label className="block text-xs font-semibold text-muted-foreground mb-1">Descripción</label>
          <textarea
            value={form.description ?? ''}
            onChange={(e) => setForm((f) => ({ ...f, description: e.target.value }))}
            rows={2}
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
            disabled={pending}
            className="flex-1 rounded-xl bg-primary px-4 py-2 text-sm font-semibold text-white hover:bg-primary/90 disabled:opacity-60"
          >
            {pending ? 'Guardando...' : 'Guardar'}
          </button>
        </div>
      </form>
    </div>
  )
}
