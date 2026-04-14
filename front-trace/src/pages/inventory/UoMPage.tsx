import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Ruler, Plus, Trash2, AlertTriangle, ArrowRight } from 'lucide-react'
import { inventoryUoMApi } from '@/lib/inventory-api'
import type { UnitOfMeasure, UoMConversion, UoMCatalogCategory } from '@/types/inventory'
import { useConfirm } from '@/store/confirm'
import { useToast } from '@/store/toast'
import { useAuthStore } from '@/store/auth'

// Display labels for known system categories. Any unknown category slug
// (e.g. tenant-defined "custom-foo") is rendered with the slug capitalized.
const CAT_LABELS: Record<string, string> = {
  weight: 'Peso',
  volume: 'Volumen',
  length: 'Longitud',
  area: 'Área',
  unit: 'Cantidad',
  time: 'Tiempo',
  energy: 'Energía',
  custom: 'Personalizado',
}
// Display order for known categories. Unknown ones go to the end.
const KNOWN_CATEGORIES = ['weight', 'volume', 'length', 'area', 'unit', 'time', 'energy', 'custom']

const labelFor = (cat: string) =>
  CAT_LABELS[cat] ?? cat.charAt(0).toUpperCase() + cat.slice(1)

export function UoMPage() {
  const qc = useQueryClient()
  const confirm = useConfirm()
  const toast = useToast()
  const { user, hasPermission } = useAuthStore()
  const isAdmin = (user?.is_superuser ?? false) || hasPermission('inventory.admin')

  const [showCreate, setShowCreate] = useState(false)
  const [showConvCreate, setShowConvCreate] = useState(false)
  const [form, setForm] = useState({ name: '', symbol: '', category: 'unit' })
  const [convForm, setConvForm] = useState({ from_uom_id: '', to_uom_id: '', factor: '' })

  // Change-base modal state
  const [changeBaseFor, setChangeBaseFor] = useState<{ category: string; currentBase: UnitOfMeasure } | null>(null)
  const [newBaseId, setNewBaseId] = useState('')
  const [confirmText, setConfirmText] = useState('')

  // Add-categories wizard modal
  const [showAddCategories, setShowAddCategories] = useState(false)

  const { data: uoms = [], isLoading } = useQuery({
    queryKey: ['inventory', 'uom'],
    queryFn: () => inventoryUoMApi.list(),
  })
  const { data: conversions = [] } = useQuery({
    queryKey: ['inventory', 'uom', 'conversions'],
    queryFn: () => inventoryUoMApi.listConversions(),
  })

  const createMut = useMutation({
    mutationFn: (data: typeof form) => inventoryUoMApi.create(data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['inventory', 'uom'] })
      setShowCreate(false)
      setForm({ name: '', symbol: '', category: 'unit' })
      toast.success('Unidad creada')
    },
    onError: (err: any) => {
      toast.error(err?.message ?? 'No se pudo crear la unidad')
    },
  })
  const createConvMut = useMutation({
    mutationFn: (data: { from_uom_id: string; to_uom_id: string; factor: number }) => inventoryUoMApi.createConversion(data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['inventory', 'uom', 'conversions'] })
      setShowConvCreate(false)
      setConvForm({ from_uom_id: '', to_uom_id: '', factor: '' })
      toast.success('Conversión creada')
    },
    onError: (err: any) => {
      toast.error(err?.message ?? 'No se pudo crear la conversión')
    },
  })
  const deleteMut = useMutation({
    mutationFn: (id: string) => inventoryUoMApi.delete(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['inventory', 'uom'] })
      qc.invalidateQueries({ queryKey: ['inventory', 'uom', 'conversions'] })
      toast.success('Unidad eliminada')
    },
    onError: (err: any) => {
      toast.error(err?.message ?? 'No se pudo eliminar la unidad')
    },
  })
  const deleteConvMut = useMutation({
    mutationFn: (id: string) => inventoryUoMApi.deleteConversion(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['inventory', 'uom', 'conversions'] })
      toast.success('Conversión eliminada')
    },
    onError: (err: any) => {
      toast.error(err?.message ?? 'No se pudo eliminar la conversión')
    },
  })
  const deleteCategoryMut = useMutation({
    mutationFn: (category: string) => inventoryUoMApi.deleteCategory(category),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['inventory', 'uom'] })
      qc.invalidateQueries({ queryKey: ['inventory', 'uom', 'conversions'] })
      toast.success('Categoría eliminada')
    },
    onError: (err: any) => {
      toast.error(err?.message ?? 'No se pudo eliminar la categoría')
    },
  })
  const changeBaseMut = useMutation({
    mutationFn: ({ category, new_base_id }: { category: string; new_base_id: string }) =>
      inventoryUoMApi.changeBase(category, { new_base_id }),
    onSuccess: (data) => {
      qc.invalidateQueries({ queryKey: ['inventory', 'uom'] })
      qc.invalidateQueries({ queryKey: ['inventory', 'uom', 'conversions'] })
      setChangeBaseFor(null)
      setNewBaseId('')
      setConfirmText('')
      toast.success(`Base cambiada de ${data.old_base} a ${data.new_base}`)
    },
    onError: (err: any) => {
      toast.error(err?.message ?? 'No se pudo cambiar la base')
    },
  })

  // Discover all category slugs present in the data, then sort known ones
  // first (in fixed order), unknowns alphabetically after.
  const presentCategories = Array.from(
    new Set((uoms as UnitOfMeasure[]).map((u) => u.category)),
  ).sort((a, b) => {
    const ai = KNOWN_CATEGORIES.indexOf(a)
    const bi = KNOWN_CATEGORIES.indexOf(b)
    if (ai !== -1 && bi !== -1) return ai - bi
    if (ai !== -1) return -1
    if (bi !== -1) return 1
    return a.localeCompare(b)
  })

  const grouped = presentCategories.reduce((acc, cat) => {
    acc[cat] = (uoms as UnitOfMeasure[]).filter((u) => u.category === cat)
    return acc
  }, {} as Record<string, UnitOfMeasure[]>)

  const baseOf = (cat: string): UnitOfMeasure | undefined =>
    grouped[cat]?.find((u) => u.is_base)

  const uomMap = Object.fromEntries((uoms as UnitOfMeasure[]).map((u) => [u.id, u]))

  // Standard categories that aren't configured yet (excluding 'custom').
  // Used to decide whether to show the "Agregar categoría estándar" button.
  const missingStandardCategories = KNOWN_CATEGORIES.filter(
    (c) => c !== 'custom' && !presentCategories.includes(c),
  )

  // Setup wizard: shown when no UoMs exist yet
  if (!isLoading && (uoms as UnitOfMeasure[]).length === 0) {
    return <SetupWizard onDone={() => qc.invalidateQueries({ queryKey: ['inventory', 'uom'] })} />
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Ruler className="h-6 w-6 text-foreground" />
          <h1 className="text-2xl font-bold">Unidades de Medida</h1>
        </div>
        <div className="flex items-center gap-2">
          {missingStandardCategories.length > 0 && (
            <button
              onClick={() => setShowAddCategories(true)}
              className="flex items-center gap-2 px-4 py-2 text-[13px] font-medium bg-secondary text-foreground rounded-xl hover:bg-gray-200 transition-colors"
              title={`Categorías estándar disponibles: ${missingStandardCategories.map(labelFor).join(', ')}`}
            >
              <Plus className="h-4 w-4" />
              Agregar categoría estándar
              <span className="ml-1 text-[10px] bg-blue-100 text-blue-700 px-1.5 py-0.5 rounded">
                {missingStandardCategories.length}
              </span>
            </button>
          )}
          <button
            onClick={() => setShowCreate(true)}
            className="flex items-center gap-2 px-4 py-2 text-[13px] font-medium bg-gray-900 text-white rounded-xl hover:bg-gray-800 transition-colors"
          >
            <Plus className="h-4 w-4" />
            Nueva UoM
          </button>
        </div>
      </div>

      {isLoading ? (
        <div className="text-center py-10 text-muted-foreground">Cargando...</div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {presentCategories.map(
            (cat) =>
              grouped[cat]?.length > 0 && (
                <div key={cat} className="bg-card rounded-xl border border-border p-5">
                  <div className="flex items-center justify-between mb-3">
                    <h3 className="font-semibold text-sm text-muted-foreground">{labelFor(cat)}</h3>
                    <div className="flex items-center gap-3">
                      {isAdmin && baseOf(cat) && grouped[cat].length > 1 && (
                        <button
                          onClick={() => {
                            setChangeBaseFor({ category: cat, currentBase: baseOf(cat)! })
                            setNewBaseId('')
                            setConfirmText('')
                          }}
                          className="text-[11px] text-amber-700 hover:text-amber-800 hover:underline"
                          title="Cambiar la unidad base de esta categoría"
                        >
                          Cambiar base
                        </button>
                      )}
                      <button
                        onClick={async () => {
                          const ok = await confirm({
                            title: `Eliminar categoría "${labelFor(cat)}"`,
                            message: `Se eliminarán las ${grouped[cat].length} unidades de esta categoría y todas sus conversiones. Si alguna unidad está en uso, no se podrá eliminar. Esta acción no se puede deshacer.`,
                            variant: 'danger',
                            confirmLabel: 'Eliminar categoría',
                          })
                          if (ok) deleteCategoryMut.mutate(cat)
                        }}
                        disabled={deleteCategoryMut.isPending}
                        className="text-[11px] text-red-600 hover:text-red-700 hover:underline disabled:opacity-50"
                        title="Eliminar toda la categoría"
                      >
                        Eliminar
                      </button>
                    </div>
                  </div>
                  <div className="space-y-1">
                    {grouped[cat].map((u) => (
                      <div
                        key={u.id}
                        className="group flex items-center justify-between py-1.5 px-2 rounded hover:bg-muted"
                      >
                        <span>
                          {u.name}{' '}
                          <span className="text-muted-foreground text-xs">({u.symbol})</span>
                        </span>
                        <div className="flex items-center gap-2">
                          {u.is_base && (
                            <span className="text-xs bg-blue-100 text-blue-700 px-1.5 py-0.5 rounded">
                              base
                            </span>
                          )}
                          <button
                            onClick={async () => {
                              const ok = await confirm({
                                title: `Eliminar "${u.name}"`,
                                message:
                                  'Esta acción no se puede deshacer. Si la unidad está en uso, no podrá eliminarse.',
                                variant: 'danger',
                                confirmLabel: 'Eliminar',
                              })
                              if (ok) deleteMut.mutate(u.id)
                            }}
                            disabled={deleteMut.isPending}
                            title="Eliminar"
                            className="opacity-0 group-hover:opacity-100 text-muted-foreground hover:text-red-600 transition-opacity disabled:opacity-50"
                          >
                            <Trash2 className="h-3.5 w-3.5" />
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              ),
          )}
        </div>
      )}

      <div className="bg-card rounded-xl border border-border p-5">
        <div className="flex items-center justify-between mb-4">
          <h3 className="font-semibold">Conversiones</h3>
          <button
            onClick={() => setShowConvCreate(true)}
            className="flex items-center gap-1 px-3 py-1.5 text-sm border rounded hover:bg-muted"
          >
            <Plus className="h-4 w-4" />
            Nueva conversión
          </button>
        </div>
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-muted">
              <th className="p-2 text-left">De</th>
              <th className="p-2 text-left">A</th>
              <th className="p-2 text-right">Factor</th>
              <th className="p-2 w-10"></th>
            </tr>
          </thead>
          <tbody>
            {(conversions as UoMConversion[]).map((c) => {
              const fromName = uomMap[c.from_uom_id]?.name ?? c.from_uom_id
              const toName = uomMap[c.to_uom_id]?.name ?? c.to_uom_id
              return (
                <tr key={c.id} className="group border-b">
                  <td className="p-2">
                    {fromName} ({uomMap[c.from_uom_id]?.symbol})
                  </td>
                  <td className="p-2">
                    {toName} ({uomMap[c.to_uom_id]?.symbol})
                  </td>
                  <td className="p-2 text-right font-mono">
                    {Math.round(Number(c.factor)).toLocaleString('es-CO')}
                  </td>
                  <td className="p-2 text-right">
                    <button
                      onClick={async () => {
                        const ok = await confirm({
                          title: 'Eliminar conversión',
                          message: `Se eliminará la conversión ${fromName} → ${toName}. Esta acción no se puede deshacer.`,
                          variant: 'danger',
                          confirmLabel: 'Eliminar',
                        })
                        if (ok) deleteConvMut.mutate(c.id)
                      }}
                      disabled={deleteConvMut.isPending}
                      title="Eliminar"
                      className="opacity-0 group-hover:opacity-100 text-muted-foreground hover:text-red-600 transition-opacity disabled:opacity-50"
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </button>
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>

      {/* Nueva UoM */}
      {showCreate && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
          <div className="bg-card rounded-2xl p-6 w-96 shadow-2xl">
            <h3 className="font-semibold mb-4">Nueva Unidad de Medida</h3>
            <div className="space-y-3">
              <input
                placeholder="Nombre (ej: Kilogramo)"
                value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
                className="w-full border rounded px-3 py-2 text-sm"
              />
              <input
                placeholder="Símbolo (ej: kg)"
                value={form.symbol}
                onChange={(e) => setForm({ ...form, symbol: e.target.value })}
                className="w-full border rounded px-3 py-2 text-sm"
              />
              <select
                value={form.category}
                onChange={(e) => setForm({ ...form, category: e.target.value })}
                className="w-full border rounded px-3 py-2 text-sm"
              >
                {KNOWN_CATEGORIES.map((c) => (
                  <option key={c} value={c}>
                    {labelFor(c)}
                  </option>
                ))}
                {/* Allow any unknown category that already exists in the data */}
                {presentCategories
                  .filter((c) => !KNOWN_CATEGORIES.includes(c))
                  .map((c) => (
                    <option key={c} value={c}>
                      {labelFor(c)}
                    </option>
                  ))}
              </select>
              {baseOf(form.category) ? (
                <div className="text-xs text-muted-foreground bg-muted/50 rounded px-3 py-2">
                  Base actual de {labelFor(form.category).toLowerCase()}:{' '}
                  <span className="font-medium text-foreground">
                    {baseOf(form.category)!.name} ({baseOf(form.category)!.symbol})
                  </span>
                  <div className="mt-1">
                    Esta unidad nueva no será la base. Para cambiar la base, usá la opción
                    "Cambiar base" en la sección de la categoría.
                  </div>
                </div>
              ) : (
                <div className="text-xs text-amber-700 bg-amber-50 border border-amber-200 rounded px-3 py-2">
                  No hay base definida en esta categoría. Esta unidad será marcada como base
                  automáticamente.
                </div>
              )}
            </div>
            <div className="flex justify-end gap-2 mt-4">
              <button
                onClick={() => {
                  setShowCreate(false)
                  setForm({ name: '', symbol: '', category: 'unit' })
                }}
                className="px-3 py-1.5 text-sm border rounded"
              >
                Cancelar
              </button>
              <button
                onClick={() =>
                  createMut.mutate({
                    ...form,
                    // Mark as base only if the category currently has none
                    is_base: !baseOf(form.category),
                  } as any)
                }
                disabled={createMut.isPending || !form.name || !form.symbol}
                className="px-3 py-1.5 text-sm bg-gray-900 text-white rounded disabled:opacity-50"
              >
                Crear
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Nueva Conversión */}
      {showConvCreate && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
          <div className="bg-card rounded-2xl p-6 w-96 shadow-2xl">
            <h3 className="font-semibold mb-4">Nueva Conversión</h3>
            <div className="space-y-3">
              <select
                value={convForm.from_uom_id}
                onChange={(e) => setConvForm({ ...convForm, from_uom_id: e.target.value })}
                className="w-full border rounded px-3 py-2 text-sm"
              >
                <option value="">De...</option>
                {(uoms as UnitOfMeasure[]).map((u) => (
                  <option key={u.id} value={u.id}>
                    {u.name} ({u.symbol})
                  </option>
                ))}
              </select>
              <select
                value={convForm.to_uom_id}
                onChange={(e) => setConvForm({ ...convForm, to_uom_id: e.target.value })}
                className="w-full border rounded px-3 py-2 text-sm"
              >
                <option value="">A...</option>
                {(uoms as UnitOfMeasure[]).map((u) => (
                  <option key={u.id} value={u.id}>
                    {u.name} ({u.symbol})
                  </option>
                ))}
              </select>
              <input
                type="number"
                step="1"
                min="1"
                placeholder="Factor (ej: 1000)"
                value={convForm.factor}
                onChange={(e) =>
                  setConvForm({ ...convForm, factor: e.target.value.replace(/[.,]/g, '') })
                }
                className="w-full border rounded px-3 py-2 text-sm"
              />
            </div>
            <div className="flex justify-end gap-2 mt-4">
              <button
                onClick={() => setShowConvCreate(false)}
                className="px-3 py-1.5 text-sm border rounded"
              >
                Cancelar
              </button>
              <button
                onClick={() =>
                  createConvMut.mutate({
                    from_uom_id: convForm.from_uom_id,
                    to_uom_id: convForm.to_uom_id,
                    factor: parseInt(convForm.factor, 10),
                  })
                }
                disabled={createConvMut.isPending}
                className="px-3 py-1.5 text-sm bg-gray-900 text-white rounded"
              >
                Crear
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Agregar categorías estándar — modal con wizard reusado */}
      {showAddCategories && (
        <div className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-black/60 backdrop-blur-sm py-10 px-4">
          <div className="bg-card rounded-2xl shadow-2xl w-full max-w-3xl p-6">
            <SetupWizard
              mode="add"
              excludeCategories={presentCategories}
              onCancel={() => setShowAddCategories(false)}
              onDone={() => {
                setShowAddCategories(false)
                qc.invalidateQueries({ queryKey: ['inventory', 'uom'] })
                qc.invalidateQueries({ queryKey: ['inventory', 'uom', 'conversions'] })
              }}
            />
          </div>
        </div>
      )}

      {/* Cambiar base — admin */}
      {changeBaseFor && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
          <div className="bg-card rounded-2xl p-6 w-[480px] max-w-full shadow-2xl">
            <div className="flex items-start gap-3 mb-4">
              <div className="flex-shrink-0 h-10 w-10 rounded-full bg-amber-100 flex items-center justify-center">
                <AlertTriangle className="h-5 w-5 text-amber-700" />
              </div>
              <div>
                <h3 className="font-semibold text-base">
                  Cambiar base de {labelFor(changeBaseFor.category)}
                </h3>
                <p className="text-xs text-muted-foreground mt-1">
                  Esta operación recalcula todas las cantidades históricas almacenadas en
                  unidades base (productos, stock, líneas de compra, líneas de venta y costos).
                  Es atómica pero <strong>no se puede deshacer</strong>.
                </p>
              </div>
            </div>

            <div className="space-y-3 mb-4">
              <div className="flex items-center gap-2 text-sm bg-muted/50 rounded p-3">
                <span className="text-muted-foreground">Base actual:</span>
                <span className="font-medium">
                  {changeBaseFor.currentBase.name} ({changeBaseFor.currentBase.symbol})
                </span>
                <ArrowRight className="h-4 w-4 text-muted-foreground mx-1" />
                <select
                  value={newBaseId}
                  onChange={(e) => setNewBaseId(e.target.value)}
                  className="flex-1 border rounded px-2 py-1 text-sm bg-background"
                >
                  <option value="">Elegir nueva base...</option>
                  {grouped[changeBaseFor.category]
                    .filter((u) => u.id !== changeBaseFor.currentBase.id)
                    .map((u) => (
                      <option key={u.id} value={u.id}>
                        {u.name} ({u.symbol})
                      </option>
                    ))}
                </select>
              </div>

              <div className="text-xs text-muted-foreground">
                Para confirmar, escribí el símbolo de la nueva base abajo:
              </div>
              <input
                value={confirmText}
                onChange={(e) => setConfirmText(e.target.value)}
                placeholder="Símbolo de la nueva base"
                className="w-full border rounded px-3 py-2 text-sm font-mono"
              />
            </div>

            <div className="flex justify-end gap-2">
              <button
                onClick={() => {
                  setChangeBaseFor(null)
                  setNewBaseId('')
                  setConfirmText('')
                }}
                className="px-3 py-1.5 text-sm border rounded"
              >
                Cancelar
              </button>
              <button
                onClick={() => {
                  const target = grouped[changeBaseFor.category].find((u) => u.id === newBaseId)
                  if (!target) return
                  if (confirmText.trim() !== target.symbol) {
                    toast.error('El símbolo no coincide. Confirmación cancelada.')
                    return
                  }
                  changeBaseMut.mutate({
                    category: changeBaseFor.category,
                    new_base_id: newBaseId,
                  })
                }}
                disabled={
                  changeBaseMut.isPending ||
                  !newBaseId ||
                  confirmText.trim() !==
                    (grouped[changeBaseFor.category].find((u) => u.id === newBaseId)?.symbol ?? '___')
                }
                className="px-3 py-1.5 text-sm bg-amber-600 text-white rounded hover:bg-amber-700 disabled:opacity-50"
              >
                {changeBaseMut.isPending ? 'Cambiando...' : 'Cambiar base'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

// ──────────────────────────────────────────────────────────────────────────
// Setup wizard — used both for initial setup (mode='initial') and for
// adding standard categories later (mode='add'). When `excludeCategories`
// is provided, those category slugs are filtered out of the catalog.
// ──────────────────────────────────────────────────────────────────────────

function SetupWizard({
  onDone,
  onCancel,
  excludeCategories = [],
  mode = 'initial',
}: {
  onDone: () => void
  onCancel?: () => void
  excludeCategories?: string[]
  mode?: 'initial' | 'add'
}) {
  const qc = useQueryClient()
  const toast = useToast()
  const [choices, setChoices] = useState<Record<string, string>>({})
  const [skipped, setSkipped] = useState<Record<string, boolean>>({})

  const { data: catalogRaw = [], isLoading } = useQuery({
    queryKey: ['inventory', 'uom', 'catalog'],
    queryFn: () => inventoryUoMApi.getCatalog(),
  })

  const catalog = (catalogRaw as UoMCatalogCategory[]).filter(
    (c) => !excludeCategories.includes(c.category),
  )

  // Initialize choices with the suggested defaults once the catalog loads
  if (catalog.length > 0 && Object.keys(choices).length === 0) {
    const initial: Record<string, string> = {}
    for (const cat of catalog) {
      const def = cat.options.find((o) => o.suggested_default) ?? cat.options[0]
      initial[cat.category] = def.symbol
    }
    setChoices(initial)
  }

  const setupMut = useMutation({
    mutationFn: () => {
      const bases = catalog
        .filter((c) => !skipped[c.category])
        .map((c) => ({ category: c.category, base_symbol: choices[c.category] }))
      return inventoryUoMApi.setup({ bases })
    },
    onSuccess: (data) => {
      qc.invalidateQueries({ queryKey: ['inventory', 'uom'] })
      qc.invalidateQueries({ queryKey: ['inventory', 'uom', 'conversions'] })
      const created = data.created
      const skippedNames = (data.skipped ?? []).join(', ')
      const msg =
        mode === 'initial'
          ? `Configuración inicial completada (${created} unidades creadas)`
          : `${created} unidades agregadas${skippedNames ? ` — saltadas: ${skippedNames}` : ''}`
      toast.success(msg)
      onDone()
    },
    onError: (err: any) => {
      toast.error(err?.message ?? 'No se pudo completar la configuración')
    },
  })

  if (isLoading) {
    return <div className="text-center py-10 text-muted-foreground">Cargando catálogo...</div>
  }

  if (catalog.length === 0) {
    return (
      <div className="text-center py-10 space-y-3">
        <p className="text-sm text-muted-foreground">
          Ya tenés todas las categorías estándar configuradas. Para agregar otras unidades,
          usá el botón "Nueva UoM".
        </p>
        {onCancel && (
          <button
            onClick={onCancel}
            className="px-4 py-2 text-sm border rounded-xl hover:bg-muted"
          >
            Cerrar
          </button>
        )}
      </div>
    )
  }

  const title = mode === 'initial' ? 'Configuración inicial de unidades' : 'Agregar categorías estándar'
  const subtitle =
    mode === 'initial' ? (
      <>
        Elegí la <strong>unidad base</strong> de cada categoría. Será la unidad interna en la
        que el sistema almacena cantidades, costos y stock. La elección depende de la escala de
        tu operación: si manejás toneladas, elegí <em>kg</em> o <em>ton</em>; si manejás
        gramos, elegí <em>g</em>. Esta decisión es difícil de cambiar después, así que pensala
        bien.
      </>
    ) : (
      <>
        Elegí la <strong>unidad base</strong> de cada nueva categoría. Solo se muestran las
        categorías estándar que aún no configuraste. Marcá "Omitir" en las que no querés agregar
        ahora.
      </>
    )

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <div className="text-center">
        <Ruler className="h-10 w-10 text-foreground mx-auto mb-3" />
        <h1 className="text-2xl font-bold">{title}</h1>
        <p className="text-sm text-muted-foreground mt-2 max-w-xl mx-auto">{subtitle}</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {catalog.map((cat) => (
          <div
            key={cat.category}
            className={`bg-card rounded-xl border p-5 ${
              skipped[cat.category] ? 'border-dashed opacity-60' : 'border-border'
            }`}
          >
            <div className="flex items-center justify-between mb-3">
              <h3 className="font-semibold">{cat.label}</h3>
              <label className="flex items-center gap-1.5 text-xs text-muted-foreground">
                <input
                  type="checkbox"
                  checked={!!skipped[cat.category]}
                  onChange={(e) =>
                    setSkipped({ ...skipped, [cat.category]: e.target.checked })
                  }
                />
                Omitir
              </label>
            </div>
            <div className="space-y-2">
              {cat.options.map((opt) => (
                <label
                  key={opt.symbol}
                  className={`flex items-center gap-2 px-3 py-2 rounded border cursor-pointer text-sm ${
                    choices[cat.category] === opt.symbol
                      ? 'border-blue-500 bg-blue-50'
                      : 'border-border hover:bg-muted'
                  } ${skipped[cat.category] ? 'pointer-events-none' : ''}`}
                >
                  <input
                    type="radio"
                    name={`base-${cat.category}`}
                    checked={choices[cat.category] === opt.symbol}
                    onChange={() => setChoices({ ...choices, [cat.category]: opt.symbol })}
                    disabled={!!skipped[cat.category]}
                  />
                  <span className="flex-1">
                    {opt.name} <span className="text-muted-foreground">({opt.symbol})</span>
                  </span>
                  {opt.suggested_default && (
                    <span className="text-[10px] text-blue-700 bg-blue-100 px-1.5 py-0.5 rounded">
                      sugerido
                    </span>
                  )}
                </label>
              ))}
            </div>
          </div>
        ))}
      </div>

      <div className="flex justify-center gap-3 pt-2">
        {onCancel && (
          <button
            onClick={onCancel}
            className="px-6 py-2.5 text-sm font-medium border rounded-xl hover:bg-muted"
          >
            Cancelar
          </button>
        )}
        <button
          onClick={() => setupMut.mutate()}
          disabled={
            setupMut.isPending || catalog.every((c) => skipped[c.category])
          }
          className="px-6 py-2.5 text-sm font-medium bg-gray-900 text-white rounded-xl hover:bg-gray-800 disabled:opacity-50"
        >
          {setupMut.isPending
            ? 'Configurando...'
            : mode === 'initial'
              ? 'Confirmar y configurar'
              : 'Agregar categorías'}
        </button>
      </div>

      {mode === 'initial' && (
        <p className="text-xs text-center text-muted-foreground">
          Después podés crear unidades adicionales y conversiones manualmente.
        </p>
      )}
    </div>
  )
}
