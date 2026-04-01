import { useState } from 'react'
import { ShieldCheck, Pencil, Trash2, Plus } from 'lucide-react'
import {
  useActivations, useFrameworks, useUpdateActivation, useDeactivateFramework,
} from '@/hooks/useCompliance'
import { useConfirm } from '@/store/confirm'
import { useToast } from '@/store/toast'
import { DataTable, type Column } from '@/components/ui/datatable'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { LegacyDialog as Dialog } from '@/components/ui/legacy-dialog'
import type { TenantFrameworkActivation } from '@/types/compliance'

// ─── Flag emoji mapping ──────────────────────────────────────────────────────

const marketFlags: Record<string, string> = {
  EU: '\u{1F1EA}\u{1F1FA}',
  US: '\u{1F1FA}\u{1F1F8}',
  JP: '\u{1F1EF}\u{1F1F5}',
  IN: '\u{1F1EE}\u{1F1F3}',
  CO: '\u{1F1E8}\u{1F1F4}',
  BR: '\u{1F1E7}\u{1F1F7}',
  UK: '\u{1F1EC}\u{1F1E7}',
}

// ─── Edit Destinations Modal ─────────────────────────────────────────────────

function EditDestinationsModal({
  activation,
  onClose,
}: {
  activation: TenantFrameworkActivation
  onClose: () => void
}) {
  const update = useUpdateActivation()
  const toast = useToast()
  const [destinations, setDestinations] = useState(
    (activation.export_destination ?? []).join(', '),
  )

  async function handleSave() {
    const arr = destinations
      .split(',')
      .map((s) => s.trim())
      .filter(Boolean)
    try {
      await update.mutateAsync({
        slug: activation.framework_slug,
        data: { export_destination: arr },
      })
      toast.success('Destinos actualizados')
      onClose()
    } catch (e: any) {
      toast.error(e.message ?? 'Error al actualizar')
    }
  }

  return (
    <Dialog
      open
      onClose={onClose}
      title="Editar destinos de exportacion"
      description={`Framework: ${activation.framework_slug}`}
      footer={
        <>
          <Button variant="secondary" onClick={onClose}>Cancelar</Button>
          <Button variant="primary" loading={update.isPending} onClick={handleSave}>
            Guardar
          </Button>
        </>
      }
    >
      <div className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-foreground mb-1">
            Destinos de exportacion (separados por coma)
          </label>
          <input
            type="text"
            value={destinations}
            onChange={(e) => setDestinations(e.target.value)}
            placeholder="EU, US, JP"
            className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-primary focus:ring-1 focus:ring-ring outline-none"
          />
          <p className="mt-1 text-xs text-muted-foreground">Ej: EU, US, JP, IN</p>
        </div>
      </div>
    </Dialog>
  )
}

// ─── Main Page ───────────────────────────────────────────────────────────────

export default function ActivationsPage() {
  const { data: activations = [], isLoading } = useActivations()
  const { data: frameworks = [] } = useFrameworks()
  const deactivate = useDeactivateFramework()
  const confirm = useConfirm()
  const toast = useToast()
  const [editingActivation, setEditingActivation] = useState<TenantFrameworkActivation | null>(null)

  const fwBySlug = Object.fromEntries(frameworks.map((f) => [f.slug, f]))

  async function handleDeactivate(slug: string) {
    const ok = await confirm({
      title: 'Desactivar norma',
      message: 'Se desactivara este marco normativo para tu organizacion. Los registros existentes se conservan.',
      variant: 'warning',
      confirmLabel: 'Desactivar',
    })
    if (!ok) return
    try {
      await deactivate.mutateAsync(slug)
      toast.success('Marco desactivado')
    } catch (e: any) {
      toast.error(e.message ?? 'Error al desactivar')
    }
  }

  function frameworkName(slug: string) {
    return fwBySlug[slug]?.name ?? slug
  }

  function flagForSlug(slug: string) {
    const fw = fwBySlug[slug]
    if (!fw) return ''
    for (const m of fw.target_markets) {
      if (marketFlags[m.toUpperCase()]) return marketFlags[m.toUpperCase()] + ' '
    }
    return ''
  }

  const columns: Column<TenantFrameworkActivation>[] = [
    {
      key: 'framework',
      header: 'Framework',
      sortable: true,
      render: (row) => (
        <span className="font-medium text-foreground">
          {flagForSlug(row.framework_slug)}{frameworkName(row.framework_slug)}
        </span>
      ),
    },
    {
      key: 'export_destination',
      header: 'Destinos exportacion',
      render: (row) => (
        <div className="flex flex-wrap gap-1">
          {(row.export_destination ?? []).length > 0
            ? row.export_destination!.map((d) => (
                <Badge key={d} variant="info">{d}</Badge>
              ))
            : <span className="text-xs text-muted-foreground">Sin destinos</span>
          }
        </div>
      ),
    },
    {
      key: 'activated_at',
      header: 'Fecha activacion',
      sortable: true,
      render: (row) => (
        <span className="text-sm text-muted-foreground tabular-nums">
          {new Date(row.activated_at).toLocaleDateString('es-CO', {
            year: 'numeric', month: 'short', day: 'numeric',
          })}
        </span>
      ),
    },
    {
      key: 'is_active',
      header: 'Estado',
      render: (row) => (
        row.is_active
          ? <Badge variant="success" dot>Activo</Badge>
          : <Badge variant="muted" dot>Inactivo</Badge>
      ),
    },
    {
      key: 'actions',
      header: '',
      render: (row) => (
        <div className="flex items-center gap-1 justify-end">
          <button
            onClick={() => setEditingActivation(row)}
            className="rounded-lg p-1.5 text-muted-foreground hover:text-muted-foreground hover:bg-secondary transition-colors"
            title="Editar destinos"
          >
            <Pencil className="h-3.5 w-3.5" />
          </button>
          <button
            onClick={() => handleDeactivate(row.framework_slug)}
            className="rounded-lg p-1.5 text-muted-foreground hover:text-red-600 hover:bg-red-50 transition-colors"
            title="Desactivar"
          >
            <Trash2 className="h-3.5 w-3.5" />
          </button>
        </div>
      ),
    },
  ]

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-emerald-50">
            <ShieldCheck className="h-5 w-5 text-emerald-600" />
          </div>
          <div>
            <h1 className="text-lg font-semibold text-foreground">Normas Activas</h1>
            <p className="text-sm text-muted-foreground">Marcos normativos activados para tu organizacion</p>
          </div>
        </div>
      </div>

      {/* Table */}
      <DataTable
        columns={columns}
        data={activations}
        rowKey={(row) => row.id}
        isLoading={isLoading}
        emptyMessage="No tienes normas activas. Ve al Marketplace para activar."
      />

      {/* Edit Modal */}
      {editingActivation && (
        <EditDestinationsModal
          activation={editingActivation}
          onClose={() => setEditingActivation(null)}
        />
      )}
    </div>
  )
}
