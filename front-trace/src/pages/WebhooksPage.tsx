import { useState } from 'react'
import {
  Webhook, Plus, Trash2, Pencil, Play, CheckCircle2, XCircle, Clock,
  AlertTriangle, Loader2, Copy, Eye, ChevronDown, ChevronUp,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import {
  useEventsCatalog, useWebhookSubscriptions,
  useCreateWebhookSubscription, useUpdateWebhookSubscription,
  useDeleteWebhookSubscription, useTestWebhookSubscription,
  useWebhookDeliveries,
} from '@/hooks/useIntegrations'
import { useToast } from '@/store/toast'
import { useConfirm } from '@/store/confirm'
import type { WebhookSubscription } from '@/lib/integration-api'

const STATUS_COLORS: Record<string, string> = {
  pending: 'bg-amber-100 text-amber-700',
  delivered: 'bg-emerald-100 text-emerald-700',
  failed: 'bg-red-100 text-red-700',
}

const SOURCE_COLORS: Record<string, string> = {
  inventory: 'bg-blue-50 text-blue-600 border-blue-200',
  trace: 'bg-purple-50 text-purple-600 border-purple-200',
  compliance: 'bg-emerald-50 text-emerald-600 border-emerald-200',
  media: 'bg-amber-50 text-amber-600 border-amber-200',
}

export default function WebhooksPage() {
  const { data: subs, isLoading } = useWebhookSubscriptions()
  const { data: catalog } = useEventsCatalog()
  const create = useCreateWebhookSubscription()
  const update = useUpdateWebhookSubscription()
  const del = useDeleteWebhookSubscription()
  const test = useTestWebhookSubscription()
  const toast = useToast()
  const confirm = useConfirm()

  const [showCreate, setShowCreate] = useState(false)
  const [editSub, setEditSub] = useState<WebhookSubscription | null>(null)
  const [viewDeliveries, setViewDeliveries] = useState<string | null>(null)

  const [form, setForm] = useState({
    name: '', target_url: '', events: [] as string[], is_active: true, max_retries: 5,
  })

  function resetForm() {
    setForm({ name: '', target_url: '', events: [], is_active: true, max_retries: 5 })
  }

  function openEdit(s: WebhookSubscription) {
    setForm({ name: s.name, target_url: s.target_url, events: s.events, is_active: s.is_active, max_retries: s.max_retries })
    setEditSub(s)
    setShowCreate(true)
  }

  async function handleSave() {
    if (!form.name || !form.target_url) return
    try {
      if (editSub) {
        await update.mutateAsync({ id: editSub.id, data: form })
        toast.success('Webhook actualizado')
        setEditSub(null)
      } else {
        await create.mutateAsync(form)
        toast.success('Webhook creado — secret generado automaticamente')
      }
      setShowCreate(false)
      resetForm()
    } catch (e: any) { toast.error(e.message) }
  }

  async function handleTest(id: string) {
    try {
      const r = await test.mutateAsync(id)
      if (r.success) toast.success(`Test exitoso (HTTP ${r.http_status})`)
      else toast.error(`Test fallido: HTTP ${r.http_status ?? 'timeout'}`)
    } catch (e: any) { toast.error(e.message) }
  }

  async function handleDelete(id: string, name: string) {
    const ok = await confirm({ title: 'Eliminar webhook', message: `Eliminar "${name}"? Se perdera el historial de entregas.`, confirmLabel: 'Eliminar', destructive: true })
    if (ok) { await del.mutateAsync(id); toast.success('Eliminado') }
  }

  async function handleToggle(s: WebhookSubscription) {
    await update.mutateAsync({ id: s.id, data: { is_active: !s.is_active } })
    toast.success(s.is_active ? 'Desactivado' : 'Activado')
  }

  const inputCls = "w-full bg-muted border border-border rounded-xl px-3 py-2.5 text-sm outline-none focus:bg-card focus:ring-2 focus:ring-gray-900/10"

  // Group catalog by source
  const catalogBySource = (catalog ?? []).reduce((acc, item) => {
    acc[item.source] = acc[item.source] || []
    acc[item.source].push(item)
    return acc
  }, {} as Record<string, typeof catalog>)

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Webhook className="h-6 w-6 text-indigo-600" />
          <div>
            <h1 className="text-2xl font-bold">Webhooks</h1>
            <p className="text-sm text-muted-foreground">Configura a donde enviar eventos cuando algo pasa en Trace</p>
          </div>
        </div>
        <button onClick={() => { resetForm(); setEditSub(null); setShowCreate(true) }}
          className="flex items-center gap-1 px-4 py-2 text-sm bg-gray-900 text-white rounded-xl hover:bg-gray-800">
          <Plus className="h-4 w-4" /> Nuevo webhook
        </button>
      </div>

      {/* Subscriptions list */}
      {isLoading ? (
        <div className="text-center py-16"><Loader2 className="h-6 w-6 animate-spin mx-auto text-muted-foreground" /></div>
      ) : !subs || subs.length === 0 ? (
        <div className="text-center py-16 text-muted-foreground">
          <Webhook className="h-10 w-10 mx-auto mb-3 text-gray-200" />
          <p className="font-medium">Sin webhooks configurados</p>
          <p className="text-sm mt-1">Crea uno para recibir eventos en tiempo real cuando algo pase en el sistema</p>
        </div>
      ) : (
        <div className="space-y-3">
          {subs.map(s => (
            <div key={s.id} className="bg-card rounded-xl border overflow-hidden">
              <div className="px-5 py-4 flex items-center gap-4">
                {/* Status dot */}
                <div className={cn('h-2.5 w-2.5 rounded-full shrink-0', s.is_active ? 'bg-emerald-500' : 'bg-gray-300')} />

                {/* Info */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <p className="font-semibold text-foreground">{s.name}</p>
                    <span className={cn('text-[10px] px-1.5 py-0.5 rounded-full font-medium', s.is_active ? 'bg-emerald-100 text-emerald-700' : 'bg-secondary text-muted-foreground')}>
                      {s.is_active ? 'Activo' : 'Inactivo'}
                    </span>
                  </div>
                  <p className="text-xs text-muted-foreground font-mono truncate mt-0.5">{s.target_url}</p>
                  <div className="flex gap-1.5 mt-1.5 flex-wrap">
                    {s.events.length === 0 ? (
                      <span className="text-[10px] px-1.5 py-0.5 bg-secondary text-muted-foreground rounded">Todos los eventos</span>
                    ) : s.events.map(ev => (
                      <span key={ev} className="text-[10px] px-1.5 py-0.5 bg-indigo-50 text-indigo-600 rounded border border-indigo-100">{ev}</span>
                    ))}
                  </div>
                </div>

                {/* Secret */}
                <div className="text-right shrink-0">
                  {s.secret && <p className="text-[10px] font-mono text-muted-foreground">{s.secret}</p>}
                  {s.last_triggered_at && <p className="text-[10px] text-muted-foreground mt-0.5">Ultimo: {new Date(s.last_triggered_at).toLocaleString('es-CO')}</p>}
                </div>

                {/* Actions */}
                <div className="flex items-center gap-1 shrink-0">
                  <button onClick={() => handleTest(s.id)} disabled={test.isPending} title="Enviar test"
                    className="p-1.5 text-muted-foreground hover:text-emerald-600 hover:bg-emerald-50 rounded-lg">
                    <Play className="h-3.5 w-3.5" />
                  </button>
                  <button onClick={() => setViewDeliveries(viewDeliveries === s.id ? null : s.id)} title="Ver entregas"
                    className="p-1.5 text-muted-foreground hover:text-blue-600 hover:bg-blue-50 rounded-lg">
                    <Eye className="h-3.5 w-3.5" />
                  </button>
                  <button onClick={() => handleToggle(s)} title={s.is_active ? 'Desactivar' : 'Activar'}
                    className={cn('p-1.5 rounded-lg', s.is_active ? 'text-muted-foreground hover:text-amber-600 hover:bg-amber-50' : 'text-muted-foreground hover:text-emerald-600 hover:bg-emerald-50')}>
                    {s.is_active ? <XCircle className="h-3.5 w-3.5" /> : <CheckCircle2 className="h-3.5 w-3.5" />}
                  </button>
                  <button onClick={() => openEdit(s)} title="Editar"
                    className="p-1.5 text-muted-foreground hover:text-amber-600 hover:bg-amber-50 rounded-lg">
                    <Pencil className="h-3.5 w-3.5" />
                  </button>
                  <button onClick={() => handleDelete(s.id, s.name)} title="Eliminar"
                    className="p-1.5 text-muted-foreground hover:text-red-500 hover:bg-red-50 rounded-lg">
                    <Trash2 className="h-3.5 w-3.5" />
                  </button>
                </div>
              </div>

              {/* Deliveries expandable */}
              {viewDeliveries === s.id && <DeliveriesPanel subId={s.id} />}
            </div>
          ))}
        </div>
      )}

      {/* Create/Edit Modal */}
      {showCreate && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm" onClick={() => { setShowCreate(false); setEditSub(null) }}>
          <div className="bg-card rounded-2xl p-6 w-full max-w-lg max-h-[90vh] overflow-y-auto shadow-2xl" onClick={e => e.stopPropagation()}>
            <h3 className="text-lg font-semibold mb-4">{editSub ? 'Editar webhook' : 'Nuevo webhook'}</h3>

            <div className="space-y-4">
              <div>
                <label className="text-xs text-muted-foreground">Nombre *</label>
                <input value={form.name} onChange={e => setForm(f => ({...f, name: e.target.value}))} placeholder="Ej: Siigo — Facturas" className={inputCls} />
              </div>
              <div>
                <label className="text-xs text-muted-foreground">URL destino * (HTTPS recomendado)</label>
                <input value={form.target_url} onChange={e => setForm(f => ({...f, target_url: e.target.value}))} placeholder="https://mi-sistema.com/webhooks/trace" className={inputCls} />
              </div>
              <div>
                <label className="text-xs text-muted-foreground">Reintentos maximos</label>
                <input type="number" min="0" max="10" value={form.max_retries} onChange={e => setForm(f => ({...f, max_retries: Number(e.target.value)}))} className={inputCls} />
              </div>

              {/* Events selector */}
              <div>
                <label className="text-xs text-muted-foreground mb-2 block">Eventos (dejar vacio = todos)</label>
                {Object.entries(catalogBySource).map(([source, items]) => (
                  <div key={source} className="mb-3">
                    <p className="text-[10px] font-bold text-muted-foreground uppercase tracking-wider mb-1">{source}</p>
                    <div className="flex flex-wrap gap-1.5">
                      {(items ?? []).map(item => {
                        const selected = form.events.includes(item.event)
                        return (
                          <button key={item.event} type="button"
                            onClick={() => setForm(f => ({
                              ...f,
                              events: selected ? f.events.filter(e => e !== item.event) : [...f.events, item.event],
                            }))}
                            className={cn(
                              'px-2.5 py-1 text-[11px] font-medium rounded-lg border transition-colors',
                              selected ? 'bg-indigo-600 text-white border-indigo-600' : `${SOURCE_COLORS[source] ?? 'bg-muted text-muted-foreground border-border'} hover:border-indigo-300`,
                            )}>
                            {item.label}
                          </button>
                        )
                      })}
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <div className="flex gap-3 mt-6">
              <button onClick={() => { setShowCreate(false); setEditSub(null); resetForm() }}
                className="flex-1 bg-secondary text-foreground rounded-xl px-4 py-2.5 text-sm">Cancelar</button>
              <button onClick={handleSave} disabled={create.isPending || update.isPending || !form.name || !form.target_url}
                className="flex-1 bg-gray-900 text-white rounded-xl px-4 py-2.5 text-sm font-semibold disabled:opacity-50">
                {editSub ? 'Guardar' : 'Crear'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

function DeliveriesPanel({ subId }: { subId: string }) {
  const { data: deliveries, isLoading } = useWebhookDeliveries(subId)

  if (isLoading) return <div className="px-5 py-4 border-t text-center text-muted-foreground text-sm">Cargando entregas...</div>

  if (!deliveries || deliveries.length === 0) {
    return <div className="px-5 py-4 border-t text-center text-muted-foreground text-sm">Sin entregas registradas</div>
  }

  return (
    <div className="border-t">
      <table className="w-full text-xs">
        <thead><tr className="bg-muted text-muted-foreground">
          <th className="px-4 py-2 text-left">Evento</th>
          <th className="px-4 py-2 text-center">Estado</th>
          <th className="px-4 py-2 text-center">HTTP</th>
          <th className="px-4 py-2 text-right">Intentos</th>
          <th className="px-4 py-2 text-left">Fecha</th>
        </tr></thead>
        <tbody>
          {deliveries.slice(0, 20).map(d => (
            <tr key={d.id} className="border-t border-gray-50 hover:bg-muted/50">
              <td className="px-4 py-1.5 font-mono">{d.event_type}</td>
              <td className="px-4 py-1.5 text-center">
                <span className={cn('px-1.5 py-0.5 rounded-full text-[10px] font-semibold', STATUS_COLORS[d.status])}>
                  {d.status}
                </span>
              </td>
              <td className="px-4 py-1.5 text-center font-mono">{d.http_status ?? '—'}</td>
              <td className="px-4 py-1.5 text-right">{d.attempts}</td>
              <td className="px-4 py-1.5 text-muted-foreground">{new Date(d.created_at).toLocaleString('es-CO')}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
