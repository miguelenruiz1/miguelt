import { useState } from 'react'
import {
  Building2, Plus, Pencil, Trash2, Wallet, X, Check, ChevronDown, ChevronRight,
  Truck, Package, Warehouse, Shield, Sprout, Factory, Ship, Plane, Train,
  MapPin, Users, Store, Box, Archive, Globe, Layers, Scale, FlaskConical, BarChart2,
  Leaf, PackageOpen,
} from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { Topbar } from '@/components/layout/Topbar'
import { Button } from '@/components/ui/Button'
import { Dialog } from '@/components/ui/Dialog'
import { Spinner, EmptyState } from '@/components/ui/Misc'
import { useToast } from '@/store/toast'
import { useConfirm } from '@/store/confirm'
import {
  useCustodianTypes,
  useCreateCustodianType,
  useUpdateCustodianType,
  useDeleteCustodianType,
  useOrganizations,
  useCreateOrganization,
} from '@/hooks/useTaxonomy'
import type { CustodianType } from '@/types/api'

const fieldCls =
  'w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 placeholder:text-slate-400 hover:border-slate-400 focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 transition-colors'
const labelCls = 'text-xs font-medium text-slate-700 block mb-1.5'

// ─── Icon picker ──────────────────────────────────────────────────────────────

const ICON_OPTIONS: { name: string; Icon: React.ElementType }[] = [
  { name: 'sprout',        Icon: Sprout },
  { name: 'building2',     Icon: Building2 },
  { name: 'truck',         Icon: Truck },
  { name: 'package',       Icon: Package },
  { name: 'warehouse',     Icon: Warehouse },
  { name: 'shield',        Icon: Shield },
  { name: 'factory',       Icon: Factory },
  { name: 'ship',          Icon: Ship },
  { name: 'plane',         Icon: Plane },
  { name: 'train',         Icon: Train },
  { name: 'map-pin',       Icon: MapPin },
  { name: 'users',         Icon: Users },
  { name: 'store',         Icon: Store },
  { name: 'box',           Icon: Box },
  { name: 'archive',       Icon: Archive },
  { name: 'globe',         Icon: Globe },
  { name: 'layers',        Icon: Layers },
  { name: 'scale',         Icon: Scale },
  { name: 'flask-conical', Icon: FlaskConical },
  { name: 'bar-chart-2',   Icon: BarChart2 },
  { name: 'leaf',          Icon: Leaf },
  { name: 'package-open',  Icon: PackageOpen },
]

export function renderCustodianIcon(name: string, cls = 'h-4 w-4') {
  const found = ICON_OPTIONS.find((o) => o.name === name)
  if (!found) return null
  const { Icon } = found
  return <Icon className={cls} />
}

function IconPicker({ value, onChange }: { value: string; onChange: (name: string) => void }) {
  return (
    <div className="col-span-2">
      <label className={labelCls}>Icono</label>
      <div className="grid grid-cols-11 gap-1 p-2 bg-white rounded-lg border border-slate-200">
        {ICON_OPTIONS.map(({ name, Icon }) => (
          <button
            key={name}
            type="button"
            title={name}
            onClick={() => onChange(name)}
            className={`flex items-center justify-center h-8 w-8 rounded-lg transition-all ${
              value === name
                ? 'bg-indigo-600 text-white shadow-sm'
                : 'text-slate-400 hover:bg-indigo-50 hover:text-indigo-600'
            }`}
          >
            <Icon className="h-4 w-4" />
          </button>
        ))}
      </div>
    </div>
  )
}

// ─── Custodian Type Form (for manage-types section) ───────────────────────────

function TypeForm({ initial, onSave, onCancel }: {
  initial?: CustodianType
  onSave: (d: { name: string; slug: string; color: string; icon: string; description: string }) => void
  onCancel: () => void
}) {
  const [name, setName] = useState(initial?.name ?? '')
  const [slug, setSlug] = useState(initial?.slug ?? '')
  const [color, setColor] = useState(initial?.color ?? '#6366f1')
  const [icon, setIcon] = useState(initial?.icon ?? 'sprout')
  const [description, setDescription] = useState(initial?.description ?? '')

  return (
    <div className="flex flex-col gap-3 p-4 bg-slate-50 rounded-xl border border-slate-200">
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className={labelCls}>Nombre *</label>
          <input type="text" value={name} onChange={(e) => setName(e.target.value)} placeholder="Finca" className={fieldCls} />
        </div>
        {!initial && (
          <div>
            <label className={labelCls}>Slug *</label>
            <input type="text" value={slug} onChange={(e) => setSlug(e.target.value)} placeholder="finca" className={fieldCls} />
          </div>
        )}
        <div className="flex flex-col gap-1">
          <label className={labelCls}>Color</label>
          <div className="flex items-center gap-2">
            <input type="color" value={color} onChange={(e) => setColor(e.target.value)}
              className="h-9 w-14 cursor-pointer rounded-lg border border-slate-200 p-0.5"
            />
            <span className="text-xs text-slate-500 font-mono">{color}</span>
          </div>
        </div>
        <IconPicker value={icon} onChange={setIcon} />
      </div>
      <div>
        <label className={labelCls}>Descripción</label>
        <input type="text" value={description} onChange={(e) => setDescription(e.target.value)} placeholder="Descripción opcional" className={fieldCls} />
      </div>
      <div className="flex gap-2 justify-end">
        <Button size="sm" variant="ghost" onClick={onCancel}><X className="h-3.5 w-3.5" /> Cancelar</Button>
        <Button size="sm" onClick={() => onSave({ name, slug, color, icon, description })}>
          <Check className="h-3.5 w-3.5" /> Guardar
        </Button>
      </div>
    </div>
  )
}

// ─── Manage Types section (collapsible) ───────────────────────────────────────

function ManageTypesSection() {
  const [open, setOpen] = useState(false)
  const [showCreate, setShowCreate] = useState(false)
  const [editingId, setEditingId] = useState<string | null>(null)
  const { data: types = [], isLoading } = useCustodianTypes()
  const createType = useCreateCustodianType()
  const updateType = useUpdateCustodianType()
  const deleteType = useDeleteCustodianType()
  const toast = useToast()

  const handleCreate = async (d: { name: string; slug: string; color: string; icon: string; description: string }) => {
    try {
      await createType.mutateAsync({ name: d.name, slug: d.slug, color: d.color, icon: d.icon, description: d.description || undefined })
      toast.success('Tipo creado')
      setShowCreate(false)
    } catch (err: unknown) { toast.error(err instanceof Error ? err.message : 'Error') }
  }

  const handleUpdate = async (id: string, d: { name: string; slug: string; color: string; icon: string; description: string }) => {
    try {
      await updateType.mutateAsync({ id, data: { name: d.name, color: d.color, icon: d.icon, description: d.description || undefined } })
      toast.success('Tipo actualizado')
      setEditingId(null)
    } catch (err: unknown) { toast.error(err instanceof Error ? err.message : 'Error') }
  }

  const confirm = useConfirm()

  const handleDelete = async (id: string, name: string) => {
    const ok = await confirm({ message: `¿Eliminar tipo "${name}"? Las organizaciones de este tipo deben eliminarse primero.`, variant: 'warning', confirmLabel: 'Eliminar' })
    if (!ok) return
    try {
      await deleteType.mutateAsync(id)
      toast.success('Tipo eliminado')
    } catch (err: unknown) { toast.error(err instanceof Error ? err.message : 'Error') }
  }

  return (
    <div className="rounded-2xl border border-slate-200 bg-white overflow-hidden">
      <button
        onClick={() => setOpen((o) => !o)}
        className="flex w-full items-center justify-between px-5 py-4 text-sm font-semibold text-slate-600 hover:bg-slate-50 transition-colors"
      >
        <span className="flex items-center gap-2">
          {open ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
          Gestionar tipos de custodio
          {!isLoading && <span className="text-xs font-normal text-slate-400">({types.length} tipos)</span>}
        </span>
      </button>

      {open && (
        <div className="border-t border-slate-100 px-5 py-4 flex flex-col gap-3">
          {showCreate && (
            <TypeForm onSave={handleCreate} onCancel={() => setShowCreate(false)} />
          )}

          {isLoading ? <Spinner className="mx-auto" /> : (
            <div className="flex flex-col gap-2">
              {types.map((ct) => (
                editingId === ct.id ? (
                  <TypeForm
                    key={ct.id}
                    initial={ct}
                    onSave={(d) => handleUpdate(ct.id, d)}
                    onCancel={() => setEditingId(null)}
                  />
                ) : (
                  <div key={ct.id} className="flex items-center gap-3 p-3 rounded-xl border border-slate-100 hover:border-slate-200 bg-slate-50">
                    <div className="h-7 w-7 rounded-lg shrink-0 flex items-center justify-center text-white" style={{ backgroundColor: ct.color }}>
                      {renderCustodianIcon(ct.icon, 'h-4 w-4') ?? <span className="text-xs font-bold">{ct.name[0]}</span>}
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-semibold text-slate-700">{ct.name}</p>
                      <p className="text-xs text-slate-400 font-mono">{ct.slug}</p>
                    </div>
                    <Button size="icon" variant="ghost" onClick={() => setEditingId(ct.id)}>
                      <Pencil className="h-3.5 w-3.5" />
                    </Button>
                    <Button size="icon" variant="ghost" onClick={() => handleDelete(ct.id, ct.name)}>
                      <Trash2 className="h-3.5 w-3.5 text-red-400" />
                    </Button>
                  </div>
                )
              ))}
            </div>
          )}

          <Button size="sm" variant="ghost" onClick={() => setShowCreate(true)} className="self-start">
            <Plus className="h-3.5 w-3.5" /> Nuevo tipo
          </Button>
        </div>
      )}
    </div>
  )
}

// ─── Main Page ─────────────────────────────────────────────────────────────────

export function TaxonomyPage() {
  const navigate = useNavigate()
  const toast = useToast()

  const [filterTypeId, setFilterTypeId] = useState<string | null>(null)
  const [showCreate, setShowCreate] = useState(false)

  // Create org dialog state
  const [orgName, setOrgName] = useState('')
  const [orgTypeId, setOrgTypeId] = useState('')
  const [orgDescription, setOrgDescription] = useState('')

  const { data: types = [], isLoading: typesLoading } = useCustodianTypes()
  const { data: orgsData, isLoading: orgsLoading } = useOrganizations(
    filterTypeId ? { custodian_type_id: filterTypeId } : undefined
  )
  const orgs = orgsData?.items ?? []
  const createOrg = useCreateOrganization()

  const getType = (typeId: string) => types.find((t) => t.id === typeId)

  const handleCreateOrg = async () => {
    if (!orgName.trim() || !orgTypeId) return
    try {
      const org = await createOrg.mutateAsync({
        name: orgName.trim(),
        custodian_type_id: orgTypeId,
        description: orgDescription.trim() || undefined,
      })
      toast.success(`Organización "${org.name}" creada`)
      setShowCreate(false)
      setOrgName(''); setOrgTypeId(''); setOrgDescription('')
      navigate(`/organizations/${org.id}`)
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : 'Error al crear organización')
    }
  }

  const handleCloseCreate = () => {
    setShowCreate(false)
    setOrgName(''); setOrgTypeId(''); setOrgDescription('')
  }

  return (
    <div className="flex flex-col flex-1 overflow-hidden">
      <Topbar
        title="Organizaciones"
        subtitle="Fincas, bodegas, transportistas y otros custodios"
        actions={
          <Button size="sm" onClick={() => setShowCreate(true)}>
            <Plus className="h-4 w-4" /> Nueva Organización
          </Button>
        }
      />

      <div className="flex-1 overflow-y-auto p-6 space-y-6">

        {/* Type filter chips */}
        {!typesLoading && types.length > 0 && (
          <div className="flex flex-wrap gap-2 items-center">
            <span className="text-xs font-semibold text-slate-500 mr-1">Tipo:</span>
            <button
              onClick={() => setFilterTypeId(null)}
              className={`px-3 py-1 rounded-xl text-xs font-semibold border transition-all ${
                !filterTypeId
                  ? 'bg-slate-800 text-white border-slate-800 shadow-sm'
                  : 'bg-white text-slate-600 border-slate-200 hover:border-slate-400'
              }`}
            >
              Todos
            </button>
            {types.map((t) => (
              <button
                key={t.id}
                onClick={() => setFilterTypeId(t.id === filterTypeId ? null : t.id)}
                className={`flex items-center gap-1.5 px-3 py-1 rounded-xl text-xs font-semibold border transition-all ${
                  filterTypeId === t.id
                    ? 'text-white border-transparent shadow-sm'
                    : 'bg-white text-slate-600 border-slate-200 hover:border-slate-300'
                }`}
                style={filterTypeId === t.id ? { backgroundColor: t.color, borderColor: t.color } : {}}
              >
                <span
                  className="h-2 w-2 rounded-full shrink-0"
                  style={{ backgroundColor: filterTypeId === t.id ? 'rgba(255,255,255,0.8)' : t.color }}
                />
                {t.name}
              </button>
            ))}
          </div>
        )}

        {/* Org grid */}
        {orgsLoading ? (
          <div className="flex justify-center py-20"><Spinner /></div>
        ) : orgs.length === 0 ? (
          <EmptyState
            icon={<Building2 className="h-12 w-12" />}
            title="Sin organizaciones"
            description={filterTypeId ? 'No hay organizaciones para este tipo. Crea una nueva.' : 'Crea tu primera organización para gestionar wallets y cargas.'}
            action={<Button onClick={() => setShowCreate(true)}><Plus className="h-4 w-4" /> Nueva Organización</Button>}
          />
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {orgs.map((org) => {
              const type = getType(org.custodian_type_id)
              return (
                <button
                  key={org.id}
                  onClick={() => navigate(`/organizations/${org.id}`)}
                  className="text-left rounded-2xl border border-slate-200 bg-white hover:border-indigo-300 hover:shadow-lg transition-all duration-200 p-5 group"
                >
                  {/* Type badge row */}
                  <div className="flex items-center gap-2 mb-3">
                    {type ? (
                      <span
                        className="inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-[11px] font-semibold text-white"
                        style={{ backgroundColor: type.color }}
                      >
                        {renderCustodianIcon(type.icon, 'h-3 w-3')}
                        {type.name}
                      </span>
                    ) : null}
                    <span className={`ml-auto text-[10px] px-1.5 py-0.5 rounded font-semibold ${
                      org.status === 'active' ? 'bg-emerald-100 text-emerald-700' : 'bg-slate-100 text-slate-500'
                    }`}>{org.status}</span>
                  </div>

                  <p className="font-bold text-slate-800 text-base group-hover:text-indigo-700 transition-colors truncate">
                    {org.name}
                  </p>
                  {org.description && (
                    <p className="text-sm text-slate-400 mt-1 truncate">{org.description}</p>
                  )}

                  <div className="flex items-center gap-1 mt-3 text-xs text-slate-500">
                    <Wallet className="h-3.5 w-3.5 shrink-0" />
                    <span>{org.wallet_count} wallet{org.wallet_count !== 1 ? 's' : ''}</span>
                  </div>
                </button>
              )
            })}
          </div>
        )}

        {/* Collapsible custodian type management */}
        <ManageTypesSection />
      </div>

      {/* Create org dialog */}
      <Dialog
        open={showCreate}
        onClose={handleCloseCreate}
        title="Nueva Organización"
        description="Crea una organización para agrupar wallets y activos"
        footer={
          <>
            <Button variant="ghost" onClick={handleCloseCreate}>Cancelar</Button>
            <Button
              loading={createOrg.isPending}
              onClick={handleCreateOrg}
              disabled={!orgName.trim() || !orgTypeId}
            >
              <Plus className="h-4 w-4" /> Crear
            </Button>
          </>
        }
      >
        <div className="flex flex-col gap-4">
          <div>
            <label className={labelCls}>Nombre *</label>
            <input
              type="text"
              placeholder="Ej: Finca El Paraíso"
              value={orgName}
              onChange={(e) => setOrgName(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleCreateOrg()}
              className={fieldCls}
              autoFocus
            />
          </div>
          <div>
            <label className={labelCls}>Tipo de custodio *</label>
            <select value={orgTypeId} onChange={(e) => setOrgTypeId(e.target.value)} className={fieldCls}>
              <option value="">Selecciona el tipo...</option>
              {types.map((t) => (
                <option key={t.id} value={t.id}>{t.name}</option>
              ))}
            </select>
          </div>
          <div>
            <label className={labelCls}>Descripción (opcional)</label>
            <input
              type="text"
              placeholder="Breve descripción"
              value={orgDescription}
              onChange={(e) => setOrgDescription(e.target.value)}
              className={fieldCls}
            />
          </div>
        </div>
      </Dialog>
    </div>
  )
}
