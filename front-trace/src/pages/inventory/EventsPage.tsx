import { useState } from 'react'
import { AlertTriangle, Plus, Eye, Clock, MessageSquare, User } from 'lucide-react'
import { cn } from '@/lib/utils'
import {
  useEvents, useEvent, useCreateEvent, useChangeEventStatus, useAddEventImpact,
  useEventTypes, useEventSeverities, useEventStatuses, useWarehouses, useProducts,
} from '@/hooks/useInventory'
import { useUserLookup } from '@/hooks/useUserLookup'
import { useAuthStore } from '@/store/auth'

function CreateEventModal({ onClose }: { onClose: () => void }) {
  const { data: eventTypes = [] } = useEventTypes()
  const { data: severities = [] } = useEventSeverities()
  const { data: statuses = [] } = useEventStatuses()
  const { data: warehouses = [] } = useWarehouses()
  const create = useCreateEvent()
  const [error, setError] = useState('')

  // Auto-select first "Abierto" status
  const defaultStatus = statuses.find(s => !s.is_final)?.id ?? ''

  const [form, setForm] = useState({
    title: '', description: '', event_type_id: '', severity_id: '',
    status_id: '', warehouse_id: '', occurred_at: new Date().toISOString().slice(0, 16),
  })

  // Set default status once loaded
  if (!form.status_id && defaultStatus) {
    setForm(f => ({ ...f, status_id: defaultStatus }))
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError('')
    try {
      await create.mutateAsync({
        ...form,
        warehouse_id: form.warehouse_id || null,
        occurred_at: new Date(form.occurred_at).toISOString(),
        reported_by: useAuthStore.getState().user?.id ?? null,
        impacts: [],
      })
      onClose()
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Error al crear evento')
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 backdrop-blur-sm">
      <div className="w-full max-w-lg bg-white rounded-3xl shadow-2xl p-6">
        <h2 className="text-lg font-bold text-slate-900 mb-4">Nuevo Evento</h2>
        <form onSubmit={handleSubmit} className="space-y-3">
          <input required value={form.title} onChange={e => setForm(f => ({ ...f, title: e.target.value }))}
            placeholder="Título *" className="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400" />
          <div className="grid grid-cols-2 gap-3">
            <select required value={form.event_type_id} onChange={e => setForm(f => ({ ...f, event_type_id: e.target.value }))}
              className="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400">
              <option value="">Tipo *</option>
              {eventTypes.map(t => <option key={t.id} value={t.id}>{t.name}</option>)}
            </select>
            <select required value={form.severity_id} onChange={e => setForm(f => ({ ...f, severity_id: e.target.value }))}
              className="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400">
              <option value="">Severidad *</option>
              {severities.map(s => <option key={s.id} value={s.id}>{s.name}</option>)}
            </select>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <select required value={form.status_id} onChange={e => setForm(f => ({ ...f, status_id: e.target.value }))}
              className="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400">
              <option value="">Estado *</option>
              {statuses.map(s => <option key={s.id} value={s.id}>{s.name}</option>)}
            </select>
            <select value={form.warehouse_id} onChange={e => setForm(f => ({ ...f, warehouse_id: e.target.value }))}
              className="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400">
              <option value="">Bodega (opcional)</option>
              {warehouses.map(w => <option key={w.id} value={w.id}>{w.name}</option>)}
            </select>
          </div>
          <input type="datetime-local" value={form.occurred_at} onChange={e => setForm(f => ({ ...f, occurred_at: e.target.value }))}
            className="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400" />
          <textarea value={form.description} onChange={e => setForm(f => ({ ...f, description: e.target.value }))}
            placeholder="Descripción" rows={2}
            className="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400" />
          {error && (
            <div className="rounded-xl bg-red-50 border border-red-200 px-3 py-2 text-sm text-red-700">{error}</div>
          )}
          <div className="flex gap-3 pt-2">
            <button type="button" onClick={onClose} className="flex-1 rounded-xl border border-slate-200 px-4 py-2 text-sm text-slate-600 hover:bg-slate-50">Cancelar</button>
            <button type="submit" disabled={create.isPending} className="flex-1 rounded-xl bg-indigo-600 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-700 disabled:opacity-60">
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

  async function handleAddImpact(e: React.FormEvent) {
    e.preventDefault()
    await addImpact.mutateAsync({ eventId, data: { ...impactForm, quantity_impact: impactForm.quantity_impact } })
    setImpactForm({ entity_id: '', quantity_impact: '', notes: '' })
  }

  // Progress stepper
  const currentIdx = sortedStatuses.findIndex(s => s.id === event.status_id)

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-black/20 backdrop-blur-sm">
      <div className="w-full max-w-lg bg-white h-full shadow-2xl overflow-y-auto">
        {/* Header */}
        <div className="sticky top-0 bg-white z-10 border-b border-slate-100 px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex-1 min-w-0">
              <h2 className="font-bold text-slate-900 text-lg truncate">{event.title}</h2>
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
            <button onClick={onClose} className="ml-4 rounded-lg p-2 text-slate-400 hover:text-slate-600 hover:bg-slate-100">
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
                        active ? 'text-white border-transparent' : 'bg-white text-slate-400 border-slate-200'
                      )}
                      style={active ? { backgroundColor: s.color ?? '#6366f1', borderColor: s.color ?? '#6366f1' } : undefined}
                      title={s.name}
                    >
                      {i + 1}
                    </div>
                    {i < sortedStatuses.length - 1 && (
                      <div className={cn('flex-1 h-0.5', i < currentIdx ? 'bg-indigo-500' : 'bg-slate-200')} />
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
            <div className="bg-slate-50 rounded-xl p-3">
              <p className="text-[10px] font-bold text-slate-400 uppercase mb-1">Fecha del evento</p>
              <p className="text-sm font-medium text-slate-700">{new Date(event.occurred_at).toLocaleString('es')}</p>
            </div>
            <div className="bg-slate-50 rounded-xl p-3">
              <p className="text-[10px] font-bold text-slate-400 uppercase mb-1">Reportado por</p>
              <p className="text-sm font-medium text-slate-700">{resolve(event.reported_by)}</p>
            </div>
            {event.resolved_at && (
              <div className="bg-emerald-50 rounded-xl p-3 col-span-2">
                <p className="text-[10px] font-bold text-emerald-500 uppercase mb-1">Resuelto</p>
                <p className="text-sm font-medium text-emerald-700">{new Date(event.resolved_at).toLocaleString('es')}</p>
              </div>
            )}
          </div>

          {event.description && (
            <div className="bg-slate-50 rounded-xl p-3">
              <p className="text-[10px] font-bold text-slate-400 uppercase mb-1">Descripción</p>
              <p className="text-sm text-slate-600">{event.description}</p>
            </div>
          )}

          {/* ── Change status ── */}
          <div className="bg-white rounded-xl border border-slate-200 p-4 space-y-3">
            <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wide">Cambiar estado</h3>
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
                        ? 'ring-2 ring-offset-1 ring-indigo-400 text-white'
                        : 'bg-slate-100 text-slate-600 hover:bg-slate-200 disabled:opacity-40'
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
              <div className="space-y-2 border-t border-slate-100 pt-3">
                <label className="text-xs font-medium text-slate-500">Notas del cambio (opcional)</label>
                <textarea
                  value={statusNotes}
                  onChange={e => setStatusNotes(e.target.value)}
                  placeholder="Describe la razón del cambio de estado..."
                  rows={2}
                  className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400"
                />
                <div className="flex gap-2">
                  <button
                    type="button"
                    onClick={() => { setPendingStatusId(null); setStatusNotes('') }}
                    className="flex-1 rounded-lg border border-slate-200 px-3 py-2 text-xs font-medium text-slate-600 hover:bg-slate-50"
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
              <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wide mb-3">Historial de estados</h3>
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
                        <div className="bg-slate-50 rounded-xl p-3">
                          <div className="flex items-center gap-2 flex-wrap">
                            {fromSt && (
                              <>
                                <span className="rounded-full px-2 py-0.5 text-[10px] font-semibold text-white" style={{ backgroundColor: fromSt.color ?? '#6b7280' }}>
                                  {fromSt.name}
                                </span>
                                <span className="text-slate-400 text-xs">&rarr;</span>
                              </>
                            )}
                            <span className="rounded-full px-2 py-0.5 text-[10px] font-semibold text-white" style={{ backgroundColor: toSt?.color ?? '#6366f1' }}>
                              {toSt?.name ?? 'Desconocido'}
                            </span>
                          </div>
                          {log.notes && (
                            <p className="text-xs text-slate-600 mt-1.5 flex items-start gap-1.5">
                              <MessageSquare className="h-3 w-3 text-slate-400 mt-0.5 shrink-0" />
                              {log.notes}
                            </p>
                          )}
                          <div className="flex items-center gap-3 mt-1.5 text-[10px] text-slate-400">
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
            <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wide mb-2">Impactos ({event.impacts?.length ?? 0})</h3>
            {event.impacts?.map(imp => (
              <div key={imp.id} className="bg-slate-50 rounded-xl p-3 mb-2">
                <div className="flex justify-between text-sm">
                  <span className="font-medium text-slate-700">{productMap[imp.entity_id] ?? imp.entity_id.slice(0, 8)}</span>
                  <span className="font-bold text-slate-900">{imp.quantity_impact}</span>
                </div>
                {imp.notes && <p className="text-xs text-slate-400 mt-1">{imp.notes}</p>}
              </div>
            ))}
            <form onSubmit={handleAddImpact} className="border-t border-slate-100 pt-3 mt-3 space-y-2">
              <select required value={impactForm.entity_id} onChange={e => setImpactForm(f => ({ ...f, entity_id: e.target.value }))}
                className="w-full rounded-lg border border-slate-200 px-3 py-1.5 text-sm">
                <option value="">Producto *</option>
                {productsData?.items?.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
              </select>
              <input required type="number" step="0.01" value={impactForm.quantity_impact}
                onChange={e => setImpactForm(f => ({ ...f, quantity_impact: e.target.value }))}
                placeholder="Cantidad impactada *" className="w-full rounded-lg border border-slate-200 px-3 py-1.5 text-sm" />
              <button type="submit" disabled={addImpact.isPending}
                className="rounded-lg bg-indigo-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-indigo-700 disabled:opacity-50">
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
        <h1 className="text-2xl font-bold text-slate-900">Eventos</h1>
        <button onClick={() => setShowCreate(true)}
          className="flex items-center gap-2 rounded-2xl bg-indigo-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-indigo-700 shadow-sm">
          <Plus className="h-4 w-4" /> Nuevo evento
        </button>
      </div>

      <div className="flex gap-3">
        <select value={typeFilter} onChange={e => setTypeFilter(e.target.value)}
          className="rounded-2xl border border-slate-200 bg-white px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400">
          <option value="">Todos los tipos</option>
          {eventTypes.map(t => <option key={t.id} value={t.id}>{t.name}</option>)}
        </select>
        <select value={severityFilter} onChange={e => setSeverityFilter(e.target.value)}
          className="rounded-2xl border border-slate-200 bg-white px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400">
          <option value="">Todas las severidades</option>
          {severities.map(s => <option key={s.id} value={s.id}>{s.name}</option>)}
        </select>
      </div>

      <div className="bg-white rounded-2xl border border-slate-100 shadow-sm overflow-hidden">
        {isLoading ? (
          <div className="p-8 text-center text-slate-400">Cargando...</div>
        ) : !data?.items?.length ? (
          <div className="p-8 text-center">
            <AlertTriangle className="h-10 w-10 text-slate-200 mx-auto mb-3" />
            <p className="text-sm text-slate-400">Sin eventos registrados</p>
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
                  className="rounded-xl border border-slate-200 bg-white p-4 space-y-2 cursor-pointer active:bg-slate-50">
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium text-slate-900">{ev.title}</span>
                    <Eye className="h-4 w-4 text-slate-400" />
                  </div>
                  <div className="flex flex-wrap gap-1.5">
                    {et && <span className="rounded-full px-2 py-0.5 text-xs font-semibold text-white" style={{ backgroundColor: et.color ?? '#6366f1' }}>{et.name}</span>}
                    {sev && <span className="rounded-full px-2 py-0.5 text-xs font-semibold text-white" style={{ backgroundColor: sev.color ?? '#f59e0b' }}>{sev.name}</span>}
                    {st && <span className="rounded-full px-2 py-0.5 text-xs font-semibold text-white" style={{ backgroundColor: st.color ?? '#6366f1' }}>{st.name}</span>}
                  </div>
                  <div className="flex items-center justify-between text-xs text-slate-400">
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
            <thead className="bg-slate-50 border-b border-slate-100">
              <tr>
                {['Tipo', 'Severidad', 'Estado', 'Título', 'Fecha', 'Reportado por', ''].map(h => (
                  <th key={h} className="px-4 py-3 text-left text-xs font-semibold text-slate-400 uppercase tracking-wide">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-50">
              {data.items.map(ev => {
                const et = typeMap[ev.event_type_id]
                const sev = sevMap[ev.severity_id]
                const st = statusMap[ev.status_id]
                return (
                  <tr key={ev.id} className="hover:bg-slate-50 cursor-pointer" onClick={() => setSelectedId(ev.id)}>
                    <td className="px-4 py-3">
                      {et && <span className="rounded-full px-2 py-0.5 text-xs font-semibold text-white" style={{ backgroundColor: et.color ?? '#6366f1' }}>{et.name}</span>}
                    </td>
                    <td className="px-4 py-3">
                      {sev && <span className="rounded-full px-2 py-0.5 text-xs font-semibold text-white" style={{ backgroundColor: sev.color ?? '#f59e0b' }}>{sev.name}</span>}
                    </td>
                    <td className="px-4 py-3">
                      {st && <span className="rounded-full px-2 py-0.5 text-xs font-semibold text-white" style={{ backgroundColor: st.color ?? '#6366f1' }}>{st.name}</span>}
                    </td>
                    <td className="px-4 py-3 font-medium text-slate-900">{ev.title}</td>
                    <td className="px-4 py-3 text-slate-400 text-xs">{new Date(ev.occurred_at).toLocaleDateString('es')}</td>
                    <td className="px-4 py-3 text-slate-400 text-xs">{resolve(ev.reported_by)}</td>
                    <td className="px-4 py-3">
                      <Eye className="h-4 w-4 text-slate-400 hover:text-indigo-600" />
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
