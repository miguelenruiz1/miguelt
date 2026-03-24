import { Fragment, useState, useMemo } from 'react'
import { X, Loader2 } from 'lucide-react'
import { usePermissions, useCreateTemplate } from '@/hooks/useRoles'
import type { Permission } from '@/types/auth'
import { ICON_MAP } from './RoleTemplateModal'

const ICON_OPTIONS = Object.keys(ICON_MAP)

export function CreateTemplateModal({ open, onClose }: { open: boolean; onClose: () => void }) {
  const { data: allPerms = [] } = usePermissions()
  const createTemplate = useCreateTemplate()

  const [name, setName] = useState('')
  const [slug, setSlug] = useState('')
  const [description, setDescription] = useState('')
  const [icon, setIcon] = useState('shield')
  const [selected, setSelected] = useState<Set<string>>(new Set())
  const [saving, setSaving] = useState(false)

  const modules = useMemo(() => {
    const grouped: Record<string, Permission[]> = {}
    for (const p of allPerms) {
      if (!grouped[p.module]) grouped[p.module] = []
      grouped[p.module].push(p)
    }
    return grouped
  }, [allPerms])

  const toggle = (slug: string) => {
    setSelected((prev) => {
      const next = new Set(prev)
      if (next.has(slug)) next.delete(slug)
      else next.add(slug)
      return next
    })
  }

  const toggleModule = (perms: Permission[]) => {
    const slugs = perms.map((p) => p.slug)
    const allChecked = slugs.every((s) => selected.has(s))
    setSelected((prev) => {
      const next = new Set(prev)
      for (const s of slugs) {
        if (allChecked) next.delete(s)
        else next.add(s)
      }
      return next
    })
  }

  const reset = () => {
    setName('')
    setSlug('')
    setDescription('')
    setIcon('shield')
    setSelected(new Set())
  }

  const handleSave = async () => {
    if (!name || !slug || selected.size === 0) return
    setSaving(true)
    try {
      await createTemplate.mutateAsync({
        name,
        slug,
        description: description || undefined,
        icon,
        permissions: Array.from(selected),
      })
      reset()
      onClose()
    } catch {
      // stay open on error
    } finally {
      setSaving(false)
    }
  }

  if (!open) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm">
      <div className="w-full max-w-2xl rounded-2xl bg-white shadow-2xl flex flex-col max-h-[85vh]">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-slate-100 px-6 py-4 shrink-0">
          <div>
            <h2 className="text-lg font-bold text-slate-900">Crear plantilla de rol</h2>
            <p className="text-sm text-slate-500">
              Define un perfil reutilizable con permisos preconfigurados
            </p>
          </div>
          <button
            onClick={() => { reset(); onClose() }}
            className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-100 hover:text-slate-600"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Body */}
        <div className="p-6 overflow-y-auto flex-1 space-y-5">
          {/* Basic info */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs font-medium text-slate-600 mb-1 block">Nombre</label>
              <input
                value={name}
                onChange={(e) => {
                  setName(e.target.value)
                  setSlug(e.target.value.toLowerCase().replace(/\s+/g, '_').replace(/[^a-z0-9_]/g, ''))
                }}
                placeholder="Ej: Jefe de bodega"
                className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
              />
            </div>
            <div>
              <label className="text-xs font-medium text-slate-600 mb-1 block">Slug</label>
              <input
                value={slug}
                onChange={(e) => setSlug(e.target.value)}
                placeholder="jefe_bodega"
                className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-ring"
              />
            </div>
          </div>

          <div>
            <label className="text-xs font-medium text-slate-600 mb-1 block">Descripción</label>
            <input
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Breve descripción del perfil..."
              className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
            />
          </div>

          {/* Icon picker */}
          <div>
            <label className="text-xs font-medium text-slate-600 mb-1 block">Icono</label>
            <div className="flex flex-wrap gap-1.5">
              {ICON_OPTIONS.map((key) => {
                const Ic = ICON_MAP[key]
                return (
                  <button
                    key={key}
                    onClick={() => setIcon(key)}
                    className={`flex h-8 w-8 items-center justify-center rounded-lg border transition-all ${
                      icon === key
                        ? 'border-primary bg-primary/10 text-primary'
                        : 'border-slate-200 text-slate-400 hover:border-slate-300'
                    }`}
                    title={key}
                  >
                    <Ic className="h-4 w-4" />
                  </button>
                )
              })}
            </div>
          </div>

          {/* Permission picker */}
          <div>
            <label className="text-xs font-medium text-slate-600 mb-2 block">
              Permisos ({selected.size} seleccionados)
            </label>
            <div className="rounded-xl border border-slate-200 divide-y divide-slate-100 max-h-[40vh] overflow-y-auto">
              {Object.entries(modules).map(([module, perms]) => {
                const allChecked = perms.every((p) => selected.has(p.slug))
                const someChecked = perms.some((p) => selected.has(p.slug))
                return (
                  <Fragment key={module}>
                    <div
                      className="flex items-center gap-2 px-3 py-2 bg-slate-50 cursor-pointer hover:bg-slate-100"
                      onClick={() => toggleModule(perms)}
                    >
                      <input
                        type="checkbox"
                        checked={allChecked}
                        ref={(el) => { if (el) el.indeterminate = someChecked && !allChecked }}
                        onChange={() => toggleModule(perms)}
                        className="h-3.5 w-3.5 rounded border-slate-300 text-primary"
                      />
                      <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wider">{module}</span>
                    </div>
                    {perms.map((p) => (
                      <label
                        key={p.slug}
                        className="flex items-center gap-2 px-3 py-1.5 pl-7 cursor-pointer hover:bg-slate-50"
                      >
                        <input
                          type="checkbox"
                          checked={selected.has(p.slug)}
                          onChange={() => toggle(p.slug)}
                          className="h-3.5 w-3.5 rounded border-slate-300 text-primary"
                        />
                        <span className="text-xs text-slate-700">{p.name}</span>
                        <span className="text-[10px] text-slate-400 font-mono ml-auto">{p.slug}</span>
                      </label>
                    ))}
                  </Fragment>
                )
              })}
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="border-t border-slate-100 px-6 py-4 flex items-center justify-end gap-3 shrink-0">
          <button
            onClick={() => { reset(); onClose() }}
            className="rounded-lg px-4 py-2 text-sm text-slate-600 hover:bg-slate-100"
          >
            Cancelar
          </button>
          <button
            onClick={handleSave}
            disabled={saving || !name || !slug || selected.size === 0}
            className="flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-white hover:bg-primary/90 disabled:opacity-50 transition-colors"
          >
            {saving && <Loader2 className="h-4 w-4 animate-spin" />}
            Crear plantilla
          </button>
        </div>
      </div>
    </div>
  )
}
