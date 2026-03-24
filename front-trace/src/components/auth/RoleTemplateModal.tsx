import { useState } from 'react'
import {
  X,
  ClipboardCheck,
  Warehouse,
  PackageCheck,
  ShoppingCart,
  Factory,
  Eye,
  BarChart3,
  FileSearch,
  Shield,
  Loader2,
  Trash2,
} from 'lucide-react'
import { useRoleTemplates, useCreateFromTemplate, useDeleteTemplate } from '@/hooks/useRoles'
import type { RoleTemplate } from '@/types/auth'
import type { LucideIcon } from 'lucide-react'

export const ICON_MAP: Record<string, LucideIcon> = {
  'clipboard-check': ClipboardCheck,
  warehouse: Warehouse,
  'package-check': PackageCheck,
  'shopping-cart': ShoppingCart,
  factory: Factory,
  eye: Eye,
  'bar-chart-3': BarChart3,
  'file-search': FileSearch,
  shield: Shield,
}

function TemplateCard({
  template,
  onSelect,
  onDelete,
  disabled,
}: {
  template: RoleTemplate
  onSelect: () => void
  onDelete?: () => void
  disabled: boolean
}) {
  const Icon = ICON_MAP[template.icon] ?? Shield

  return (
    <div className="group relative flex flex-col items-start gap-2 rounded-xl border border-slate-200 bg-white p-4 transition-all hover:border-primary/30 hover:shadow-md">
      <div className="flex items-center gap-3 w-full">
        <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-primary/10">
          <Icon className="h-4 w-4 text-primary" />
        </div>
        <div className="min-w-0 flex-1">
          <div className="font-semibold text-sm text-slate-900 truncate">{template.name}</div>
          <div className="text-[11px] text-slate-400 font-mono">{template.slug}</div>
        </div>
        {onDelete && (
          <button
            onClick={(e) => { e.stopPropagation(); onDelete() }}
            className="opacity-0 group-hover:opacity-100 p-1 rounded text-slate-400 hover:text-red-500 hover:bg-red-50 transition-all"
            title="Eliminar plantilla"
          >
            <Trash2 className="h-3.5 w-3.5" />
          </button>
        )}
      </div>
      {template.description && (
        <p className="text-xs text-slate-500 leading-relaxed">{template.description}</p>
      )}
      <div className="flex items-center gap-2 w-full">
        <span className="text-[10px] font-medium text-primary bg-primary/10 rounded-full px-2 py-0.5">
          {template.permissions.length} permisos
        </span>
        {template.is_default && (
          <span className="text-[10px] font-medium text-emerald-600 bg-emerald-50 rounded-full px-2 py-0.5">
            ejemplo
          </span>
        )}
        <div className="flex-1" />
        <button
          onClick={onSelect}
          disabled={disabled}
          className="rounded-lg bg-primary px-3 py-1 text-xs font-semibold text-white hover:bg-primary/90 disabled:opacity-50 transition-colors"
        >
          Usar
        </button>
      </div>
    </div>
  )
}

export function RoleTemplateModal({ open, onClose }: { open: boolean; onClose: () => void }) {
  const { data: templates = [], isLoading } = useRoleTemplates()
  const createFromTemplate = useCreateFromTemplate()
  const deleteTemplate = useDeleteTemplate()
  const [creating, setCreating] = useState<string | null>(null)

  if (!open) return null

  const handleSelect = async (id: string) => {
    setCreating(id)
    try {
      await createFromTemplate.mutateAsync(id)
      onClose()
    } catch {
      // conflict or error — stays open
    } finally {
      setCreating(null)
    }
  }

  const handleDelete = async (id: string) => {
    await deleteTemplate.mutateAsync(id)
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm">
      <div className="w-full max-w-2xl rounded-2xl bg-white shadow-2xl">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-slate-100 px-6 py-4">
          <div>
            <h2 className="text-lg font-bold text-slate-900">Crear rol desde plantilla</h2>
            <p className="text-sm text-slate-500">
              Selecciona una plantilla para crear un rol con permisos preconfigurados
            </p>
          </div>
          <button
            onClick={onClose}
            className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-100 hover:text-slate-600"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Body */}
        <div className="p-6 max-h-[60vh] overflow-y-auto">
          {isLoading ? (
            <div className="flex items-center justify-center py-12 text-slate-400">
              <Loader2 className="h-5 w-5 animate-spin" />
            </div>
          ) : templates.length === 0 ? (
            <div className="text-center py-12 text-slate-400 text-sm">
              No hay plantillas. Crea una desde el botón "Crear plantilla".
            </div>
          ) : (
            <div className="grid grid-cols-2 gap-3">
              {templates.map((t) => (
                <TemplateCard
                  key={t.id}
                  template={t}
                  onSelect={() => handleSelect(t.id)}
                  onDelete={!t.is_default ? () => handleDelete(t.id) : undefined}
                  disabled={creating !== null}
                />
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
