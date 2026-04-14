import { useState, useCallback } from 'react'
import {
  Plus, Trash2, GripVertical, ArrowRight, Sparkles, Settings2,
  Circle, CheckCircle, AlertTriangle, Loader2,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { cn } from '@/lib/utils'
import {
  DndContext,
  closestCenter,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  type DragEndEvent,
} from '@dnd-kit/core'
import {
  arrayMove,
  SortableContext,
  sortableKeyboardCoordinates,
  useSortable,
  verticalListSortingStrategy,
} from '@dnd-kit/sortable'
import { CSS } from '@dnd-kit/utilities'
import {
  useWorkflowStates,
  useCreateWorkflowState,
  useUpdateWorkflowState,
  useDeleteWorkflowState,
  useReorderWorkflowStates,
  useWorkflowTransitions,
  useCreateWorkflowTransition,
  useDeleteWorkflowTransition,
  useWorkflowEventTypes,
  useCreateWorkflowEventType,
  useUpdateWorkflowEventType,
  useDeleteWorkflowEventType,
  useWorkflowPresets,
  useSeedWorkflowPreset,
} from '@/hooks/useWorkflow'
import { useToast } from '@/store/toast'
import { useConfirm } from '@/store/confirm'
import type {
  WorkflowState, WorkflowTransition, WorkflowEventType,
  WorkflowStateCreate, WorkflowTransitionCreate, WorkflowEventTypeCreate,
} from '@/types/api'

/* ── Preset card icons ─────────────────────────────────────────── */

const PRESET_META: Record<string, { emoji: string; desc: string }> = {
  logistics:    { emoji: '\u{1F69A}', desc: 'Recibido, bodega, tránsito, reparto, entregado' },
  pharma:       { emoji: '\u{1F48A}', desc: 'Cuarentena, aprobado, distribución, dispensado' },
  coldchain:    { emoji: '\u{2744}\u{FE0F}', desc: 'Recepción, cámara fría, alistamiento, ruta, entregado' },
  retail:       { emoji: '\u{1F6D2}', desc: 'Proveedor, bodega, picking, despachado, recibido' },
  construction: { emoji: '\u{1F3D7}\u{FE0F}', desc: 'Solicitado, fabricación, obra, instalado, cerrado' },
}

/* ── Tabs ───────────────────────────────────────────────────────── */

type Tab = 'states' | 'transitions' | 'events' | 'presets'

export function WorkflowBuilderPage() {
  const [tab, setTab] = useState<Tab>('states')
  const toast = useToast()
  const confirm = useConfirm()

  const { data: states = [], isLoading: statesLoading } = useWorkflowStates()
  const { data: transitions = [], isLoading: transLoading } = useWorkflowTransitions()
  const { data: eventTypes = [], isLoading: eventsLoading } = useWorkflowEventTypes(false)
  const { data: presets } = useWorkflowPresets()

  const hasStates = states.length > 0

  const tabs: { key: Tab; label: string; count?: number }[] = [
    { key: 'states', label: 'Estados', count: states.length },
    { key: 'transitions', label: 'Transiciones', count: transitions.length },
    { key: 'events', label: 'Tipos de evento', count: eventTypes.length },
    { key: 'presets', label: 'Plantillas de industria' },
  ]

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Flujo de trabajo</h1>
        <p className="text-sm text-muted-foreground mt-0.5">
          Configura los estados, transiciones y eventos de tu negocio
        </p>
      </div>

      {/* Tab bar */}
      <div className="flex gap-1 border-b pb-px">
        {tabs.map(t => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className={cn(
              'px-4 py-2 text-sm rounded-t-md transition-colors',
              tab === t.key
                ? 'bg-background border border-b-transparent font-medium -mb-px'
                : 'text-muted-foreground hover:text-foreground',
            )}
          >
            {t.label}
            {t.count !== undefined && (
              <span className="ml-1.5 text-xs text-muted-foreground">({t.count})</span>
            )}
          </button>
        ))}
      </div>

      {/* Content */}
      {tab === 'states' && <StatesTab states={states} loading={statesLoading} />}
      {tab === 'transitions' && <TransitionsTab transitions={transitions} states={states} loading={transLoading} />}
      {tab === 'events' && <EventTypesTab eventTypes={eventTypes} loading={eventsLoading} />}
      {tab === 'presets' && <PresetsTab presets={presets} hasStates={hasStates} />}
    </div>
  )
}

/* ════════════════════════════════════════════════════════════════════
   States Tab
   ════════════════════════════════════════════════════════════════════ */

/* ── Sortable state row ─────────────────────────────────────────── */

function SortableStateRow({
  state,
  onDelete,
}: {
  state: WorkflowState
  onDelete: (s: WorkflowState) => void
}) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id: state.id })

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    zIndex: isDragging ? 10 : undefined,
  }

  return (
    <div
      ref={setNodeRef}
      style={style}
      className={cn(
        'flex items-center gap-3 p-3 border rounded-lg hover:bg-muted/20 transition-colors',
        isDragging && 'shadow-lg bg-background ring-2 ring-primary/20',
      )}
    >
      <button
        type="button"
        className="cursor-grab active:cursor-grabbing touch-none"
        {...attributes}
        {...listeners}
      >
        <GripVertical className="h-4 w-4 text-muted-foreground/40" />
      </button>
      <div
        className="h-5 w-5 rounded-md shrink-0"
        style={{ backgroundColor: state.color }}
      />
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className="font-medium text-sm">{state.label}</span>
          <code className="text-[11px] text-muted-foreground bg-muted px-1.5 py-0.5 rounded">
            {state.slug}
          </code>
        </div>
      </div>
      <div className="flex items-center gap-1.5">
        {state.is_initial && (
          <Badge variant="outline" className="text-[10px] text-emerald-600 border-emerald-300">
            Inicial
          </Badge>
        )}
        {state.is_terminal && (
          <Badge variant="outline" className="text-[10px] text-red-500 border-red-300">
            Terminal
          </Badge>
        )}
      </div>
      <Button
        variant="ghost" size="icon"
        className="h-7 w-7 text-muted-foreground hover:text-red-500"
        onClick={() => onDelete(state)}
      >
        <Trash2 className="h-3.5 w-3.5" />
      </Button>
    </div>
  )
}

function StatesTab({ states, loading }: { states: WorkflowState[]; loading: boolean }) {
  const toast = useToast()
  const confirm = useConfirm()
  const createState = useCreateWorkflowState()
  const deleteState = useDeleteWorkflowState()
  const updateState = useUpdateWorkflowState()
  const reorderStates = useReorderWorkflowStates()

  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState<WorkflowStateCreate>({
    slug: '', label: '', color: '#6366f1', is_initial: false, is_terminal: false, sort_order: states.length,
  })

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 5 } }),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates }),
  )

  const handleDragEnd = useCallback(
    async (event: DragEndEvent) => {
      const { active, over } = event
      if (!over || active.id === over.id) return

      const oldIndex = states.findIndex(s => s.id === active.id)
      const newIndex = states.findIndex(s => s.id === over.id)
      if (oldIndex === -1 || newIndex === -1) return

      const reordered = arrayMove(states, oldIndex, newIndex)
      try {
        await reorderStates.mutateAsync(reordered.map(s => s.id))
        toast.success('Orden actualizado')
      } catch (e: any) {
        toast.error(e.message)
      }
    },
    [states, reorderStates, toast],
  )

  const handleCreate = async () => {
    if (!form.slug || !form.label) return
    try {
      await createState.mutateAsync(form)
      toast.success('Estado creado')
      setShowForm(false)
      setForm({ slug: '', label: '', color: '#6366f1', is_initial: false, is_terminal: false, sort_order: states.length + 1 })
    } catch (e: any) {
      toast.error(e.message)
    }
  }

  const handleDelete = async (s: WorkflowState) => {
    const ok = await confirm(`Eliminar estado "${s.label}"?`)
    if (!ok) return
    try {
      await deleteState.mutateAsync(s.id)
      toast.success('Estado eliminado')
    } catch (e: any) {
      toast.error(e.message)
    }
  }

  if (loading) return <LoadingSpinner />

  return (
    <div className="space-y-4">
      {/* Visual state flow */}
      {states.length > 0 && (
        <div className="flex items-center gap-2 flex-wrap p-4 bg-muted/30 rounded-lg">
          {states.map((s, i) => (
            <div key={s.id} className="flex items-center gap-2">
              <div
                className={cn(
                  'px-3 py-1.5 rounded-lg text-sm font-medium text-white',
                  s.is_initial && 'ring-2 ring-offset-2 ring-emerald-500',
                  s.is_terminal && 'ring-2 ring-offset-2 ring-red-400',
                )}
                style={{ backgroundColor: s.color }}
              >
                {s.label}
                {s.is_initial && <span className="ml-1 text-[10px] opacity-75">(inicio)</span>}
                {s.is_terminal && <span className="ml-1 text-[10px] opacity-75">(final)</span>}
              </div>
              {i < states.length - 1 && <ArrowRight className="h-4 w-4 text-muted-foreground" />}
            </div>
          ))}
        </div>
      )}

      {/* State list — sortable via drag & drop */}
      <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
        <SortableContext items={states.map(s => s.id)} strategy={verticalListSortingStrategy}>
          <div className="space-y-2">
            {states.map(s => (
              <SortableStateRow key={s.id} state={s} onDelete={handleDelete} />
            ))}
          </div>
        </SortableContext>
      </DndContext>

      {/* Add state form */}
      {showForm ? (
        <div className="border rounded-lg p-4 space-y-3 bg-muted/10">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs font-medium text-muted-foreground">Slug (identificador)</label>
              <input
                className="mt-1 w-full rounded-md border px-3 py-1.5 text-sm"
                placeholder="ej: en_reparto"
                value={form.slug}
                onChange={e => setForm(f => ({ ...f, slug: e.target.value.toLowerCase().replace(/[^a-z0-9_]/g, '_') }))}
              />
            </div>
            <div>
              <label className="text-xs font-medium text-muted-foreground">Label (nombre visible)</label>
              <input
                className="mt-1 w-full rounded-md border px-3 py-1.5 text-sm"
                placeholder="ej: En reparto"
                value={form.label}
                onChange={e => setForm(f => ({ ...f, label: e.target.value }))}
              />
            </div>
          </div>
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2">
              <label className="text-xs font-medium text-muted-foreground">Color</label>
              <input
                type="color"
                className="h-7 w-10 rounded cursor-pointer"
                value={form.color}
                onChange={e => setForm(f => ({ ...f, color: e.target.value }))}
              />
            </div>
            <label className="flex items-center gap-1.5 text-sm">
              <input
                type="checkbox"
                checked={form.is_initial}
                onChange={e => setForm(f => ({ ...f, is_initial: e.target.checked }))}
              />
              Estado inicial
            </label>
            <label className="flex items-center gap-1.5 text-sm">
              <input
                type="checkbox"
                checked={form.is_terminal}
                onChange={e => setForm(f => ({ ...f, is_terminal: e.target.checked }))}
              />
              Estado terminal
            </label>
          </div>
          <div className="flex gap-2">
            <Button size="sm" onClick={handleCreate} disabled={createState.isPending}>
              {createState.isPending ? <Loader2 className="h-3.5 w-3.5 animate-spin mr-1" /> : <Plus className="h-3.5 w-3.5 mr-1" />}
              Crear estado
            </Button>
            <Button variant="ghost" size="sm" onClick={() => setShowForm(false)}>Cancelar</Button>
          </div>
        </div>
      ) : (
        <Button variant="outline" size="sm" onClick={() => setShowForm(true)}>
          <Plus className="h-3.5 w-3.5 mr-1.5" />
          Agregar estado
        </Button>
      )}
    </div>
  )
}

/* ════════════════════════════════════════════════════════════════════
   Transitions Tab
   ════════════════════════════════════════════════════════════════════ */

function TransitionsTab({
  transitions,
  states,
  loading,
}: {
  transitions: WorkflowTransition[]
  states: WorkflowState[]
  loading: boolean
}) {
  const toast = useToast()
  const createTrans = useCreateWorkflowTransition()
  const deleteTrans = useDeleteWorkflowTransition()

  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState<WorkflowTransitionCreate>({
    from_state_id: null,
    to_state_id: '',
    label: '',
  })

  const handleCreate = async () => {
    if (!form.to_state_id) return
    try {
      await createTrans.mutateAsync({
        ...form,
        from_state_id: form.from_state_id || null,
      })
      toast.success('Transicion creada')
      setShowForm(false)
      setForm({ from_state_id: null, to_state_id: '', label: '' })
    } catch (e: any) {
      toast.error(e.message)
    }
  }

  const handleDelete = async (id: string) => {
    try {
      await deleteTrans.mutateAsync(id)
      toast.success('Transicion eliminada')
    } catch (e: any) {
      toast.error(e.message)
    }
  }

  if (loading) return <LoadingSpinner />

  return (
    <div className="space-y-4">
      {states.length === 0 && (
        <div className="text-center py-8 text-muted-foreground text-sm">
          Primero crea estados en la tab "Estados" para poder definir transiciones.
        </div>
      )}

      {/* Transition list */}
      <div className="space-y-2">
        {transitions.map(t => (
          <div
            key={t.id}
            className="flex items-center gap-3 p-3 border rounded-lg hover:bg-muted/20 transition-colors"
          >
            <div className="flex items-center gap-2 flex-1 min-w-0">
              {t.from_state ? (
                <Badge style={{ backgroundColor: `${t.from_state.color}20`, color: t.from_state.color, border: 'none' }}>
                  {t.from_state.label}
                </Badge>
              ) : (
                <Badge variant="outline" className="text-muted-foreground">Cualquiera</Badge>
              )}
              <ArrowRight className="h-4 w-4 text-muted-foreground shrink-0" />
              {t.to_state && (
                <Badge style={{ backgroundColor: `${t.to_state.color}20`, color: t.to_state.color, border: 'none' }}>
                  {t.to_state.label}
                </Badge>
              )}
              {t.label && (
                <span className="text-xs text-muted-foreground ml-2">({t.label})</span>
              )}
            </div>
            <Button
              variant="ghost" size="icon"
              className="h-7 w-7 text-muted-foreground hover:text-red-500"
              onClick={() => handleDelete(t.id)}
            >
              <Trash2 className="h-3.5 w-3.5" />
            </Button>
          </div>
        ))}
      </div>

      {/* Add transition form */}
      {showForm && states.length > 0 ? (
        <div className="border rounded-lg p-4 space-y-3 bg-muted/10">
          <div className="grid grid-cols-3 gap-3">
            <div>
              <label className="text-xs font-medium text-muted-foreground">Desde estado</label>
              <select
                className="mt-1 w-full rounded-md border px-3 py-1.5 text-sm bg-transparent"
                value={form.from_state_id ?? ''}
                onChange={e => setForm(f => ({ ...f, from_state_id: e.target.value || null }))}
              >
                <option value="">Cualquiera (wildcard)</option>
                {states.filter(s => !s.is_terminal).map(s => (
                  <option key={s.id} value={s.id}>{s.label}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="text-xs font-medium text-muted-foreground">Hacia estado</label>
              <select
                className="mt-1 w-full rounded-md border px-3 py-1.5 text-sm bg-transparent"
                value={form.to_state_id}
                onChange={e => setForm(f => ({ ...f, to_state_id: e.target.value }))}
              >
                <option value="">Seleccionar...</option>
                {states.map(s => (
                  <option key={s.id} value={s.id}>{s.label}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="text-xs font-medium text-muted-foreground">Label (opcional)</label>
              <input
                className="mt-1 w-full rounded-md border px-3 py-1.5 text-sm"
                placeholder="ej: Entregar"
                value={form.label ?? ''}
                onChange={e => setForm(f => ({ ...f, label: e.target.value }))}
              />
            </div>
          </div>
          <div className="flex gap-2">
            <Button size="sm" onClick={handleCreate} disabled={createTrans.isPending}>
              {createTrans.isPending ? <Loader2 className="h-3.5 w-3.5 animate-spin mr-1" /> : <Plus className="h-3.5 w-3.5 mr-1" />}
              Crear transicion
            </Button>
            <Button variant="ghost" size="sm" onClick={() => setShowForm(false)}>Cancelar</Button>
          </div>
        </div>
      ) : states.length > 0 ? (
        <Button variant="outline" size="sm" onClick={() => setShowForm(true)}>
          <Plus className="h-3.5 w-3.5 mr-1.5" />
          Agregar transicion
        </Button>
      ) : null}
    </div>
  )
}

/* ════════════════════════════════════════════════════════════════════
   Event Types Tab
   ════════════════════════════════════════════════════════════════════ */

function EventTypesTab({ eventTypes, loading }: { eventTypes: WorkflowEventType[]; loading: boolean }) {
  const toast = useToast()
  const createET = useCreateWorkflowEventType()
  const deleteET = useDeleteWorkflowEventType()
  const updateET = useUpdateWorkflowEventType()

  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState<WorkflowEventTypeCreate>({
    slug: '', name: '', icon: 'circle', color: '#6366f1', is_informational: false,
    requires_wallet: false, requires_notes: false, requires_reason: false, requires_admin: false,
  })

  const handleCreate = async () => {
    if (!form.slug || !form.name) return
    try {
      await createET.mutateAsync(form)
      toast.success('Tipo de evento creado')
      setShowForm(false)
      setForm({ slug: '', name: '', icon: 'circle', color: '#6366f1', is_informational: false,
        requires_wallet: false, requires_notes: false, requires_reason: false, requires_admin: false })
    } catch (e: any) {
      toast.error(e.message)
    }
  }

  const handleDelete = async (et: WorkflowEventType) => {
    try {
      await deleteET.mutateAsync(et.id)
      toast.success('Tipo de evento eliminado')
    } catch (e: any) {
      toast.error(e.message)
    }
  }

  const toggleActive = async (et: WorkflowEventType) => {
    try {
      await updateET.mutateAsync({ id: et.id, data: { is_active: !et.is_active } })
    } catch (e: any) {
      toast.error(e.message)
    }
  }

  if (loading) return <LoadingSpinner />

  return (
    <div className="space-y-4">
      <div className="space-y-2">
        {eventTypes.map(et => (
          <div
            key={et.id}
            className={cn(
              'flex items-center gap-3 p-3 border rounded-lg transition-colors',
              et.is_active ? 'hover:bg-muted/20' : 'opacity-50 bg-muted/10',
            )}
          >
            <div
              className="h-8 w-8 rounded-md flex items-center justify-center shrink-0"
              style={{ backgroundColor: `${et.color}20` }}
            >
              <Circle className="h-4 w-4" style={{ color: et.color }} />
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2">
                <span className="font-medium text-sm">{et.name}</span>
                <code className="text-[11px] text-muted-foreground bg-muted px-1.5 py-0.5 rounded">
                  {et.slug}
                </code>
              </div>
              {et.description && (
                <p className="text-xs text-muted-foreground mt-0.5">{et.description}</p>
              )}
            </div>
            <div className="flex items-center gap-1.5 flex-wrap">
              {et.is_informational && (
                <Badge variant="outline" className="text-[10px]">Info</Badge>
              )}
              {et.requires_wallet && (
                <Badge variant="outline" className="text-[10px]">Wallet</Badge>
              )}
              {et.requires_notes && (
                <Badge variant="outline" className="text-[10px]">Notas</Badge>
              )}
              {et.requires_reason && (
                <Badge variant="outline" className="text-[10px]">Razon</Badge>
              )}
              {et.requires_admin && (
                <Badge variant="outline" className="text-[10px] text-amber-600 border-amber-300">Admin</Badge>
              )}
            </div>
            <Button
              variant="ghost" size="sm"
              className="text-xs"
              onClick={() => toggleActive(et)}
            >
              {et.is_active ? 'Desactivar' : 'Activar'}
            </Button>
            <Button
              variant="ghost" size="icon"
              className="h-7 w-7 text-muted-foreground hover:text-red-500"
              onClick={() => handleDelete(et)}
            >
              <Trash2 className="h-3.5 w-3.5" />
            </Button>
          </div>
        ))}
      </div>

      {showForm ? (
        <div className="border rounded-lg p-4 space-y-3 bg-muted/10">
          <div className="grid grid-cols-3 gap-3">
            <div>
              <label className="text-xs font-medium text-muted-foreground">Slug</label>
              <input
                className="mt-1 w-full rounded-md border px-3 py-1.5 text-sm"
                placeholder="ej: DESPACHO"
                value={form.slug}
                onChange={e => setForm(f => ({ ...f, slug: e.target.value.toUpperCase().replace(/[^A-Z0-9_]/g, '_') }))}
              />
            </div>
            <div>
              <label className="text-xs font-medium text-muted-foreground">Nombre</label>
              <input
                className="mt-1 w-full rounded-md border px-3 py-1.5 text-sm"
                placeholder="ej: Despacho"
                value={form.name}
                onChange={e => setForm(f => ({ ...f, name: e.target.value }))}
              />
            </div>
            <div className="flex items-end gap-2">
              <div>
                <label className="text-xs font-medium text-muted-foreground">Color</label>
                <input
                  type="color"
                  className="mt-1 h-[34px] w-10 rounded cursor-pointer"
                  value={form.color}
                  onChange={e => setForm(f => ({ ...f, color: e.target.value }))}
                />
              </div>
            </div>
          </div>
          <div className="flex items-center gap-4 flex-wrap">
            <label className="flex items-center gap-1.5 text-sm">
              <input type="checkbox" checked={form.is_informational} onChange={e => setForm(f => ({ ...f, is_informational: e.target.checked }))} />
              Informacional
            </label>
            <label className="flex items-center gap-1.5 text-sm">
              <input type="checkbox" checked={form.requires_wallet} onChange={e => setForm(f => ({ ...f, requires_wallet: e.target.checked }))} />
              Requiere wallet
            </label>
            <label className="flex items-center gap-1.5 text-sm">
              <input type="checkbox" checked={form.requires_notes} onChange={e => setForm(f => ({ ...f, requires_notes: e.target.checked }))} />
              Requiere notas
            </label>
            <label className="flex items-center gap-1.5 text-sm">
              <input type="checkbox" checked={form.requires_reason} onChange={e => setForm(f => ({ ...f, requires_reason: e.target.checked }))} />
              Requiere razon
            </label>
            <label className="flex items-center gap-1.5 text-sm">
              <input type="checkbox" checked={form.requires_admin} onChange={e => setForm(f => ({ ...f, requires_admin: e.target.checked }))} />
              Solo admin
            </label>
          </div>
          <div className="flex gap-2">
            <Button size="sm" onClick={handleCreate} disabled={createET.isPending}>
              {createET.isPending ? <Loader2 className="h-3.5 w-3.5 animate-spin mr-1" /> : <Plus className="h-3.5 w-3.5 mr-1" />}
              Crear tipo de evento
            </Button>
            <Button variant="ghost" size="sm" onClick={() => setShowForm(false)}>Cancelar</Button>
          </div>
        </div>
      ) : (
        <Button variant="outline" size="sm" onClick={() => setShowForm(true)}>
          <Plus className="h-3.5 w-3.5 mr-1.5" />
          Agregar tipo de evento
        </Button>
      )}
    </div>
  )
}

/* ════════════════════════════════════════════════════════════════════
   Presets Tab
   ════════════════════════════════════════════════════════════════════ */

function PresetsTab({
  presets,
  hasStates,
}: {
  presets: Record<string, { states: number; transitions: number; event_types: number }> | undefined
  hasStates: boolean
}) {
  const toast = useToast()
  const seedPreset = useSeedWorkflowPreset()

  const handleSeed = async (name: string) => {
    try {
      const result = await seedPreset.mutateAsync(name)
      toast.success(
        `Plantilla "${name}" aplicada: ${result.states_created} estados, ${result.transitions_created} transiciones, ${result.event_types_created} tipos de evento`
      )
    } catch (e: any) {
      toast.error(e.message)
    }
  }

  return (
    <div className="space-y-4">
      {hasStates && (
        <div className="flex items-start gap-2 p-3 rounded-lg border border-amber-200 bg-amber-50 text-amber-800 text-sm">
          <AlertTriangle className="h-4 w-4 mt-0.5 shrink-0" />
          <div>
            Ya tienes estados configurados. Para aplicar una plantilla, primero elimina todos los estados existentes.
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {presets && Object.entries(presets).map(([name, info]) => {
          const meta = PRESET_META[name]
          return (
            <div
              key={name}
              className="border rounded-lg p-4 space-y-3 hover: transition-shadow"
            >
              <div className="flex items-center gap-2">
                <span className="text-2xl">{meta?.emoji ?? '\u{1F4E6}'}</span>
                <h3 className="font-semibold capitalize text-sm">{name}</h3>
              </div>
              <p className="text-xs text-muted-foreground">{meta?.desc ?? ''}</p>
              <div className="flex gap-3 text-xs text-muted-foreground">
                <span>{info.states} estados</span>
                <span>{info.transitions} transiciones</span>
                <span>{info.event_types} eventos</span>
              </div>
              <Button
                size="sm"
                variant="outline"
                className="w-full"
                disabled={hasStates || seedPreset.isPending}
                onClick={() => handleSeed(name)}
              >
                {seedPreset.isPending ? (
                  <Loader2 className="h-3.5 w-3.5 animate-spin mr-1.5" />
                ) : (
                  <Sparkles className="h-3.5 w-3.5 mr-1.5" />
                )}
                Aplicar plantilla
              </Button>
            </div>
          )
        })}
      </div>
    </div>
  )
}

/* ── Shared ─────────────────────────────────────────────────────── */

function LoadingSpinner() {
  return (
    <div className="flex items-center justify-center py-12">
      <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
    </div>
  )
}
