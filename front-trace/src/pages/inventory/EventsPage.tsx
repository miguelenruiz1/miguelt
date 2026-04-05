import { useState, useEffect } from 'react'
import { useLocation } from 'react-router-dom'
import { AlertTriangle, Plus, Eye, Clock, MessageSquare, User } from 'lucide-react'
import { cn } from '@/lib/utils'
import { useFormValidation } from '@/hooks/useFormValidation'
import {
  useEvents, useEvent, useCreateEvent, useChangeEventStatus, useAddEventImpact,
  useEventTypes, useEventSeverities, useEventStatuses, useWarehouses, useProducts,
} from '@/hooks/useInventory'
import { useUserLookup } from '@/hooks/useUserLookup'
import { useAuthStore } from '@/store/auth'

interface ImpactLine { entity_id: string; quantity_impact: string; batch_id: string; serial_id: string; notes: string }

function CreateEventModal({ onClose }: { onClose: () => void }) {
  const { data: eventTypes = [] } = useEventTypes()
  const { data: severities = [] } = useEventSeverities()
  const { data: statuses = [] } = useEventStatuses()
  const { data: warehouses = [] } = useWarehouses()
  const { data: productsData } = useProducts({ limit: 200 })
  const create = useCreateEvent()
  const [error, setError] = useState('')
  const products = productsData?.items ?? []

  const defaultStatus = statuses.find(s => !s.is_final)?.id ?? ''

  const [form, setForm] = useState({
    title: '', description: '', event_type_id: '', severity_id: '',
    status_id: '', warehouse_id: '', occurred_at: new Date().toISOString().slice(0, 16),
    reference_type: '' as '' | 'purchase_order' | 'sales_order',
    reference_id: '',
  })
  const [impacts, setImpacts] = useState<ImpactLine[]>([])

  useEffect(() => {
    if (!form.status_id && defaultStatus) {
      setForm(f => ({ ...f, status_id: defaultStatus }))
    }
  }, [defaultStatus, form.status_id])

  function addImpact() {
    setImpacts(p => [...p, { entity_id: '', quantity_impact: '0', batch_id: '', serial_id: '', notes: '' }])
  }
  function removeImpact(i: number) {
    setImpacts(p => p.filter((_, idx) => idx !== i))
  }
  function updateImpact(i: number, key: keyof ImpactLine, value: string) {
    setImpacts(p => p.map((imp, idx) => idx === i ? { ...imp, [key]: value } : imp))
  }

  async function doSubmit() {
    setError('')
    try {
      const metadata: Record<string, string> = {}
      if (form.reference_type && form.reference_id) {
        metadata.reference_type = form.reference_type
        metadata.reference_id = form.reference_id
      }
      await create.mutateAsync({
        title: form.title,
        description: form.description || null,
        event_type_id: form.event_type_id,
        severity_id: form.severity_id,
        status_id: form.status_id,
        warehouse_id: form.warehouse_id || null,
        occurred_at: new Date(form.occurred_at).toISOString(),
        reported_by: useAuthStore.getState().user?.id ?? null,
        metadata,
        impacts: impacts
          .filter(imp => imp.entity_id)
          .map(imp => ({
            entity_id: imp.entity_id,
            quantity_impact: imp.quantity_impact || '0',
            batch_id: imp.batch_id || null,
            serial_id: imp.serial_id || null,
            notes: imp.notes || null,
          })),
      })
      onClose()
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Error al crear evento')
    }
  }

  const { formRef, handleSubmit: validateAndSubmit } = useFormValidation(doSubmit)
  const cls = 'w-full rounded-xl border border-border px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring'

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 backdrop-blur-sm">
      <div className="w-full max-w-2xl bg-card rounded-3xl shadow-2xl p-6 max-h-[90vh] overflow-y-auto">
        <h2 className="text-lg font-bold text-foreground mb-4">Nuevo Evento</h2>
        <form ref={formRef} onSubmit={validateAndSubmit} noValidate className="space-y-3">
          <input required value={form.title} onChange={e => setForm(f => ({ ...f, title: e.target.value }))}
            placeholder="Título del evento *" className={cls} />
          <div className="grid grid-cols-2 gap-3">
            <select required value={form.event_type_id} onChange={e => setForm(f => ({ ...f, event_type_id: e.target.value }))} className={cls}>
              <option value="">Tipo *</option>
              {eventTypes.map(t => <option key={t.id} value={t.id}>{t.name}</option>)}
            </select>
            <select required value={form.severity_id} onChange={e => setForm(f => ({ ...f, severity_id: e.target.value }))} className={cls}>
              <option value="">Severidad *</option>
              {severities.map(s => <option key={s.id} value={s.id}>{s.name}</option>)}
            </select>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <select required value={form.status_id} onChange={e => setForm(f => ({ ...f, status_id: e.target.value }))} className={cls}>
              <option value="">Estado *</option>
              {statuses.map(s => <option key={s.id} value={s.id}>{s.name}</option>)}
            </select>
            <select value={form.warehouse_id} onChange={e => setForm(f => ({ ...f, warehouse_id: e.target.value }))} className={cls}>
              <option value="">Bodega (opcional)</option>
              {warehouses.map(w => <option key={w.id} value={w.id}>{w.name}</option>)}
            </select>
          </div>
          <input type="datetime-local" value={form.occurred_at} onChange={e => setForm(f => ({ ...f, occurred_at: e.target.value }))} className={cls} />
          <textarea value={form.description} onChange={e => setForm(f => ({ ...f, description: e.target.value }))}
            placeholder="Descripción" rows={2} className={cls} />

          {/* Reference to PO/SO */}
          <div className="border-t border-border pt-3">
            <p className="text-xs font-semibold text-muted-foreground uppercase mb-2">Referencia (opcional)</p>
            <div className="grid grid-cols-2 gap-3">
              <select value={form.reference_type} onChange={e => setForm(f => ({ ...f, reference_type: e.target.value as any }))} className={cls}>
                <option value="">Sin referencia</option>
                <option value="purchase_order">Orden de compra</option>
                <option value="sales_order">Orden de venta</option>
              </select>
              {form.reference_type && (
                <input value={form.reference_id} onChange={e => setForm(f => ({ ...f, reference_id: e.target.value }))}
                  placeholder={form.reference_type === 'purchase_order' ? 'N° OC (ej: PO-2026-001)' : 'N° OV (ej: SO-2026-001)'}
                  className={cls} />
              )}
            </div>
          </div>

          {/* Impacts (products affected) */}
          <div className="border-t border-border pt-3">
            <div className="flex items-center justify-between mb-2">
              <p className="text-xs font-semibold text-muted-foreground uppercase">Productos afectados</p>
              <button type="button" onClick={addImpact} className="text-xs text-primary hover:text-primary/80 font-semibold">+ Agregar producto</button>
            </div>
            {impacts.length === 0 && (
              <p className="text-xs text-muted-foreground py-2">Sin productos afectados. Puedes agregarlos ahora o después.</p>
            )}
            {impacts.map((imp, i) => (
              <div key={i} className="flex gap-2 items-start mb-2">
                <select required value={imp.entity_id} onChange={e => updateImpact(i, 'entity_id', e.target.value)}
                  className="flex-1 rounded-xl border border-border px-2 py-1.5 text-xs focus:ring-2 focus:ring-ring">
                  <option value="">Producto *</option>
                  {products.map(p => <option key={p.id} value={p.id}>{p.sku} — {p.name}</option>)}
                </select>
                <input type="number" step="0.01" value={imp.quantity_impact} onChange={e => updateImpact(i, 'quantity_impact', e.target.value)}
                  placeholder="Cant." className="w-20 rounded-xl border border-border px-2 py-1.5 text-xs focus:ring-2 focus:ring-ring" />
                <input value={imp.notes} onChange={e => updateImpact(i, 'notes', e.target.value)}
                  placeholder="Nota" className="w-28 rounded-xl border border-border px-2 py-1.5 text-xs focus:ring-2 focus:ring-ring" />
                <button type="button" onClick={() => removeImpact(i)} className="text-red-400 hover:text-red-600 text-xs px-1 py-1.5">✕</button>
              </div>
            ))}
          </div>

          {error && (
            <div className="rounded-xl bg-red-50 border border-red-200 px-3 py-2 text-sm text-red-700">{error}</div>
          )}
          <div className="flex gap-3 pt-2">
            <button type="button" onClick={onClose} className="flex-1 rounded-xl border border-border px-4 py-2 text-sm text-muted-foreground hover:bg-muted">Cancelar</button>
            <button type="submit" disabled={create.isPending} className="flex-1 rounded-xl bg-primary px-4 py-2 text-sm font-semibold text-white hover:bg-primary/90 disabled:opacity-60">
              {create.isPending ? 'Guardando...' : 'Crear evento'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

function EventDrawer({ eventId, onClose }: { eventId: string; onClose: () => void }) {
  const { data: event } = useEvent(eventId)
  const { data: eventTypes = [] } = useEventTypes()
  const { data: severities = [] } = useEventSeverities()
  const { data: statuses = [] } = useEventStatuses()
  const { data: productsData } = useProducts()
  const changeStatus = useChangeEventStatus()
  const addImpact = useAddEventImpact()
  const [statusError, setStatusError] = useState('')
  const [statusNotes, setStatusNotes] = useState('')
  const [pendingStatusId, setPendingStatusId] = useState<string | null>(null)

  const [impactForm, setImpactForm] = useState({ entity_id: '', quantity_impact: '', notes: '' })

  // Gather user IDs for lookup
  const logUserIds = event?.status_logs?.map(l => l.changed_by) ?? []
  const { resolve } = useUserLookup([...(event?.reported_by ? [event.reported_by] : []), ...logUserIds])

  if (!event) return null

  const typeName = eventTypes.find(t => t.id === event.event_type_id)?.name
  const typeObj = eventTypes.find(t => t.id === event.event_type_id)
  const severityObj = severities.find(s => s.id === event.severity_id)
  const statusObj = statuses.find(s => s.id === event.status_id)
  const statusMap = Object.fromEntries(statuses.map(s => [s.id, s]))
  const productMap = Object.fromEntries((productsData?.items ?? []).map(p => [p.id, p.name]))
  const sortedStatuses = [...statuses].sort((a, b) => (a.sort_order ?? 0) - (b.sort_order ?? 0))

  async function handleStatusChange() {
    if (!pendingStatusId) return
    setStatusError('')
    try {
      const status = statuses.find(s => s.id === pendingStatusId)
      await changeStatus.mutateAsync({
        id: eventId,
        data: {
          status_id: pendingStatusId,
          notes: statusNotes || undefined,
          changed_by: useAuthStore.getState().user?.id ?? undefined,
          resolved_at: status?.is_final ? new Date().toISOString() : undefined,
        },
      })
      setStatusNotes('')
      setPendingStatusId(null)
    } catch (err: unknown) {
      setStatusError(err instanceof Error ? err.message : 'Error al cambiar estado')
    }
  }

  async function doAddImpact() {
    await addImpact.mutateAsync({ eventId, data: { ...impactForm, quantity_impact: impactForm.quantity_impact } })
    setImpactForm({ entity_id: '', quantity_impact: '', notes: '' })
  }

  const { formRef: impactFormRef, handleSubmit: validateAndSubmitImpact } = useFormValidation(doAddImpact)

  // Progress stepper
  const currentIdx = sortedStatuses.findIndex(s => s.id === event.status_id)

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-black/20 backdrop-blur-sm">
      <div className="w-full max-w-lg bg-card h-full shadow-2xl overflow-y-auto">
        {/* Header */}
        <div className="sticky top-0 bg-card z-10 border-b border-border px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex-1 min-w-0">
              <h2 className="font-bold text-foreground text-lg truncate">{event.title}</h2>
              <div className="flex flex-wrap gap-2 mt-2">
                {typeObj && (
                  <span className="rounded-full px-2.5 py-0.5 text-xs font-semibold text-white" style={{ backgroundColor: typeObj.color ?? '#6366f1' }}>
                    {typeObj.name}
                  </span>
                )}
                {severityObj && (
                  <span className="rounded-full px-2.5 py-0.5 text-xs font-semibold text-white" style={{ backgroundColor: severityObj.color ?? '#f59e0b' }}>
                    {severityObj.name}
                  </span>
                )}
                {statusObj && (
                  <span className="rounded-full px-2.5 py-0.5 text-xs font-semibold text-white" style={{ backgroundColor: statusObj.color ?? '#6366f1' }}>
                    {statusObj.name}
                  </span>
                )}
              </div>
            </div>
            <button onClick={onClose} className="ml-4 rounded-lg p-2 text-muted-foreground hover:text-muted-foreground hover:bg-secondary">
              <span className="text-xl font-bold leading-none">&times;</span>
            </button>
          </div>

          {/* Progress stepper */}
          {sortedStatuses.length > 1 && (
            <div className="flex items-center gap-0 mt-4">
              {sortedStatuses.map((s, i) => {
                const active = i <= currentIdx
                return (
                  <div key={s.id} className="flex items-center flex-1 last:flex-none">
                    <div
                      className={cn(
                        'h-7 w-7 rounded-full flex items-center justify-center text-[10px] font-bold border-2 transition-colors',
                        active ? 'text-white border-transparent' : 'bg-card text-muted-foreground border-border'
                      )}
                      style={active ? { backgroundColor: s.color ?? '#6366f1', borderColor: s.color ?? '#6366f1' } : undefined}
                      title={s.name}
                    >
                      {i + 1}
                    </div>
                    {i < sortedStatuses.length - 1 && (
                      <div className={cn('flex-1 h-0.5', i < currentIdx ? 'bg-primary' : 'bg-slate-200')} />
                    )}
                  </div>
                )
              })}
            </div>
          )}
        </div>

        <div className="px-6 py-5 space-y-6">
          {/* Info cards */}
          <div className="grid grid-cols-2 gap-3">
            <div className="bg-muted rounded-xl p-3">
              <p className="text-[10px] font-bold text-muted-foreground uppercase mb-1">Fecha del evento</p>
              <p className="text-sm font-medium text-foreground">{new Date(event.occurred_at).toLocaleString('es')}</p>
            </div>
            <div className="bg-muted rounded-xl p-3">
              <p className="text-[10px] font-bold text-muted-foreground uppercase mb-1">Reportado por</p>
              <p className="text-sm font-medium text-foreground">{resolve(event.reported_by)}</p>
            </div>
            {event.resolved_at && (
              <div className="bg-emerald-50 rounded-xl p-3 col-span-2">
                <p className="text-[10px] font-bold text-emerald-500 uppercase mb-1">Resuelto</p>
                <p className="text-sm font-medium text-emerald-700">{new Date(event.resolved_at).toLocaleString('es')}</p>
              </div>
            )}
          </div>

          {event.description && (
            <div className="bg-muted rounded-xl p-3">
              <p className="text-[10px] font-bold text-muted-foreground uppercase mb-1">Descripción</p>
              <p className="text-sm text-muted-foreground">{event.description}</p>
            </div>
          )}

          {/* Reference to PO/SO */}
          {event.metadata_?.reference_type && (
            <div className="bg-blue-50 rounded-xl p-3">
              <p className="text-[10px] font-bold text-blue-500 uppercase mb-1">
                {event.metadata_.reference_type === 'purchase_order' ? 'Orden de compra' : 'Orden de venta'}
              </p>
              <p className="text-sm font-semibold text-blue-700">{event.metadata_.reference_id}</p>
            </div>
          )}

          {/* ── Change status ── */}
          <div className="bg-card rounded-xl border border-border p-4 space-y-3">
            <h3 className="text-xs font-bold text-muted-foreground uppercase tracking-wide">Cambiar estado</h3>
            <div className="flex flex-wrap gap-2">
              {sortedStatuses.map(s => (
                <button key={s.id}
                  onClick={() => setPendingStatusId(s.id === pendingStatusId ? null : s.id)}
                  disabled={s.id === event.status_id || changeStatus.isPending}
                  className={cn(
                    'rounded-full px-3 py-1.5 text-xs font-semibold transition-all',
                    s.id === event.status_id
                      ? 'ring-2 ring-offset-1 text-white cursor-default'
                      : s.id === pendingStatusId
                        ? 'ring-2 ring-offset-1 ring-ring text-white'
                        : 'bg-secondary text-muted-foreground hover:bg-slate-200 disabled:opacity-40'
                  )}
                  style={
                    s.id === event.status_id
                      ? { backgroundColor: s.color ?? '#6366f1', ringColor: s.color ?? '#6366f1' }
                      : s.id === pendingStatusId
                        ? { backgroundColor: s.color ?? '#6366f1' }
                        : undefined
                  }
                >
                  {s.name}
                </button>
              ))}
            </div>

            {/* Notes form when a new status is selected */}
            {pendingStatusId && pendingStatusId !== event.status_id && (
              <div className="space-y-2 border-t border-border pt-3">
                <label className="text-xs font-medium text-muted-foreground">Notas del cambio (opcional)</label>
                <textarea
                  value={statusNotes}
                  onChange={e => setStatusNotes(e.target.value)}
                  placeholder="Describe la razón del cambio de estado..."
                  rows={2}
                  className="w-full rounded-lg border border-border px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                />
                <div className="flex gap-2">
                  <button
                    type="button"
                    onClick={() => { setPendingStatusId(null); setStatusNotes('') }}
                    className="flex-1 rounded-lg border border-border px-3 py-2 text-xs font-medium text-muted-foreground hover:bg-muted"
                  >
                    Cancelar
                  </button>
                  <button
                    type="button"
                    onClick={handleStatusChange}
                    disabled={changeStatus.isPending}
                    className="flex-1 rounded-lg px-3 py-2 text-xs font-semibold text-white hover:opacity-90 disabled:opacity-50 transition"
                    style={{ backgroundColor: statusMap[pendingStatusId]?.color ?? '#6366f1' }}
                  >
                    {changeStatus.isPending ? 'Guardando...' : `Cambiar a ${statusMap[pendingStatusId]?.name}`}
                  </button>
                </div>
              </div>
            )}

            {statusError && (
              <div className="rounded-lg bg-red-50 border border-red-200 px-3 py-2 text-xs text-red-700 flex items-start gap-2">
                <AlertTriangle className="h-3.5 w-3.5 text-red-500 mt-0.5 shrink-0" />
                {statusError}
              </div>
            )}
          </div>

          {/* ── Timeline ── */}
          {(event.status_logs?.length ?? 0) > 0 && (
            <div>
              <h3 className="text-xs font-bold text-muted-foreground uppercase tracking-wide mb-3">Historial de estados</h3>
              <div className="relative ml-3">
                <div className="absolute left-0 top-2 bottom-2 w-0.5 bg-slate-200" />
                <div className="space-y-0">
                  {[...event.status_logs].reverse().map((log, i) => {
                    const fromSt = log.from_status_id ? statusMap[log.from_status_id] : null
                    const toSt = statusMap[log.to_status_id]
                    return (
                      <div key={log.id} className="relative pl-6 pb-4">
                        <div
                          className="absolute left-[-4px] top-1.5 h-[10px] w-[10px] rounded-full border-2 border-white"
                          style={{ backgroundColor: toSt?.color ?? '#6366f1' }}
                        />
                        <div className="bg-muted rounded-xl p-3">
                          <div className="flex items-center gap-2 flex-wrap">
                            {fromSt && (
                              <>
                                <span className="rounded-full px-2 py-0.5 text-[10px] font-semibold text-white" style={{ backgroundColor: fromSt.color ?? '#6b7280' }}>
                                  {fromSt.name}
                                </span>
                                <span className="text-muted-foreground text-xs">&rarr;</span>
                              </>
                            )}
                            <span className="rounded-full px-2 py-0.5 text-[10px] font-semibold text-white" style={{ backgroundColor: toSt?.color ?? '#6366f1' }}>
                              {toSt?.name ?? 'Desconocido'}
                            </span>
                          </div>
                          {log.notes && (
                            <p className="text-xs text-muted-foreground mt-1.5 flex items-start gap-1.5">
                              <MessageSquare className="h-3 w-3 text-muted-foreground mt-0.5 shrink-0" />
                              {log.notes}
                            </p>
                          )}
                          <div className="flex items-center gap-3 mt-1.5 text-[10px] text-muted-foreground">
                            <span className="flex items-center gap-1">
                              <Clock className="h-3 w-3" />
                              {new Date(log.created_at).toLocaleString('es')}
                            </span>
                            {log.changed_by && (
                              <span className="flex items-center gap-1">
                                <User className="h-3 w-3" />
                                {resolve(log.changed_by)}
                              </span>
                            )}
                          </div>
                        </div>
                      </div>
                    )
                  })}
                </div>
              </div>
            </div>
          )}

          {/* ── Impacts ── */}
          <div>
            <h3 className="text-xs font-bold text-muted-foreground uppercase tracking-wide mb-2">Impactos ({event.impacts?.length ?? 0})</h3>
            {event.impacts?.map(imp => (
              <div key={imp.id} className="bg-muted rounded-xl p-3 mb-2">
                <div className="flex justify-between text-sm">
                  <span className="font-medium text-foreground">{productMap[imp.entity_id] ?? imp.entity_id.slice(0, 8)}</span>
                  <span className="font-bold text-foreground">{imp.quantity_impact}</span>
                </div>
                {imp.notes && <p className="text-xs text-muted-foreground mt-1">{imp.notes}</p>}
              </div>
            ))}
            <form ref={impactFormRef} onSubmit={validateAndSubmitImpact} noValidate className="border-t border-border pt-3 mt-3 space-y-2">
              <select required value={impactForm.entity_id} onChange={e => setImpactForm(f => ({ ...f, entity_id: e.target.value }))}
                className="w-full rounded-lg border border-border px-3 py-1.5 text-sm">
                <option value="">Producto *</option>
                {productsData?.items?.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
              </select>
              <input required type="number" step="0.01" value={impactForm.quantity_impact}
                onChange={e => setImpactForm(f => ({ ...f, quantity_impact: e.target.value }))}
                placeholder="Cantidad impactada *" className="w-full rounded-lg border border-border px-3 py-1.5 text-sm" />
              <button type="submit" disabled={addImpact.isPending}
                className="rounded-lg bg-primary px-3 py-1.5 text-xs font-semibold text-white hover:bg-primary/90 disabled:opacity-50">
                Agregar impacto
              </button>
            </form>
          </div>
        </div>
      </div>
    </div>
  )
}

export function EventsPage() {
  const [showCreate, setShowCreate] = useState(false)
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [typeFilter, setTypeFilter] = useState('')
  const [severityFilter, setSeverityFilter] = useState('')
  const location = useLocation()
  useEffect(() => { setShowCreate(false) }, [location.key])

  const { data, isLoading } = useEvents({
    event_type_id: typeFilter || undefined,
    severity_id: severityFilter || undefined,
  })
  const { data: eventTypes = [] } = useEventTypes()
  const { data: severities = [] } = useEventSeverities()
  const { data: statuses = [] } = useEventStatuses()

  const { resolve } = useUserLookup(data?.items.map(e => e.reported_by) ?? [])

  const typeMap = Object.fromEntries(eventTypes.map(t => [t.id, t]))
  const sevMap = Object.fromEntries(severities.map(s => [s.id, s]))
  const statusMap = Object.fromEntries(statuses.map(s => [s.id, s]))

  return (
    <div className="max-w-5xl mx-auto p-6 space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-foreground">Eventos</h1>
        <button onClick={() => setShowCreate(true)}
          className="flex items-center gap-2 rounded-2xl bg-primary px-4 py-2.5 text-sm font-semibold text-white hover:bg-primary/90 ">
          <Plus className="h-4 w-4" /> Nuevo evento
        </button>
      </div>

      <div className="flex gap-3">
        <select value={typeFilter} onChange={e => setTypeFilter(e.target.value)}
          className="rounded-2xl border border-border bg-card px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-ring">
          <option value="">Todos los tipos</option>
          {eventTypes.map(t => <option key={t.id} value={t.id}>{t.name}</option>)}
        </select>
        <select value={severityFilter} onChange={e => setSeverityFilter(e.target.value)}
          className="rounded-2xl border border-border bg-card px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-ring">
          <option value="">Todas las severidades</option>
          {severities.map(s => <option key={s.id} value={s.id}>{s.name}</option>)}
        </select>
      </div>

      <div className="bg-card rounded-2xl border border-border  overflow-hidden">
        {isLoading ? (
          <div className="p-8 text-center text-muted-foreground">Cargando...</div>
        ) : !data?.items?.length ? (
          <div className="p-8 text-center">
            <AlertTriangle className="h-10 w-10 text-slate-200 mx-auto mb-3" />
            <p className="text-sm text-muted-foreground">Sin eventos registrados</p>
          </div>
        ) : (<>
          {/* Mobile cards */}
          <div className="space-y-3 p-4 md:hidden">
            {data.items.map(ev => {
              const et = typeMap[ev.event_type_id]
              const sev = sevMap[ev.severity_id]
              const st = statusMap[ev.status_id]
              return (
                <div key={ev.id} onClick={() => setSelectedId(ev.id)}
                  className="rounded-xl border border-border bg-card p-4 space-y-2 cursor-pointer active:bg-muted">
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium text-foreground">{ev.title}</span>
                    <Eye className="h-4 w-4 text-muted-foreground" />
                  </div>
                  <div className="flex flex-wrap gap-1.5">
                    {et && <span className="rounded-full px-2 py-0.5 text-xs font-semibold text-white" style={{ backgroundColor: et.color ?? '#6366f1' }}>{et.name}</span>}
                    {sev && <span className="rounded-full px-2 py-0.5 text-xs font-semibold text-white" style={{ backgroundColor: sev.color ?? '#f59e0b' }}>{sev.name}</span>}
                    {st && <span className="rounded-full px-2 py-0.5 text-xs font-semibold text-white" style={{ backgroundColor: st.color ?? '#6366f1' }}>{st.name}</span>}
                  </div>
                  <div className="flex items-center justify-between text-xs text-muted-foreground">
                    <span>{new Date(ev.occurred_at).toLocaleDateString('es')}</span>
                    <span>{resolve(ev.reported_by)}</span>
                  </div>
                </div>
              )
            })}
          </div>
          {/* Desktop table */}
          <div className="hidden md:block overflow-x-auto">
          <table className="w-full text-sm min-w-[600px]">
            <thead className="bg-muted border-b border-border">
              <tr>
                {['Tipo', 'Severidad', 'Estado', 'Título', 'Fecha', 'Reportado por', ''].map(h => (
                  <th key={h} className="px-4 py-3 text-left text-xs font-semibold text-muted-foreground uppercase tracking-wide">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-50">
              {data.items.map(ev => {
                const et = typeMap[ev.event_type_id]
                const sev = sevMap[ev.severity_id]
                const st = statusMap[ev.status_id]
                return (
                  <tr key={ev.id} className="hover:bg-muted cursor-pointer" onClick={() => setSelectedId(ev.id)}>
                    <td className="px-4 py-3">
                      {et && <span className="rounded-full px-2 py-0.5 text-xs font-semibold text-white" style={{ backgroundColor: et.color ?? '#6366f1' }}>{et.name}</span>}
                    </td>
                    <td className="px-4 py-3">
                      {sev && <span className="rounded-full px-2 py-0.5 text-xs font-semibold text-white" style={{ backgroundColor: sev.color ?? '#f59e0b' }}>{sev.name}</span>}
                    </td>
                    <td className="px-4 py-3">
                      {st && <span className="rounded-full px-2 py-0.5 text-xs font-semibold text-white" style={{ backgroundColor: st.color ?? '#6366f1' }}>{st.name}</span>}
                    </td>
                    <td className="px-4 py-3 font-medium text-foreground">{ev.title}</td>
                    <td className="px-4 py-3 text-muted-foreground text-xs">{new Date(ev.occurred_at).toLocaleDateString('es')}</td>
                    <td className="px-4 py-3 text-muted-foreground text-xs">{resolve(ev.reported_by)}</td>
                    <td className="px-4 py-3">
                      <Eye className="h-4 w-4 text-muted-foreground hover:text-primary" />
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
          </div>
        </>)}
      </div>

      {showCreate && <CreateEventModal onClose={() => setShowCreate(false)} />}
      {selectedId && <EventDrawer eventId={selectedId} onClose={() => setSelectedId(null)} />}
    </div>
  )
}
