import { useState } from 'react'
import { Users, Plus, Pencil, Trash2, Cog, User, Loader2 } from 'lucide-react'
import { useProductionResources, useCreateProductionResource, useUpdateProductionResource, useDeleteProductionResource } from '@/hooks/useInventory'
import { useToast } from '@/store/toast'
import { useConfirm } from '@/store/confirm'
import { cn } from '@/lib/utils'

const TYPE_LABELS: Record<string, string> = { labor: 'Mano de obra', machine: 'Maquinaria', overhead: 'Costo indirecto' }
const TYPE_COLORS: Record<string, string> = { labor: 'bg-blue-100 text-blue-700', machine: 'bg-purple-100 text-purple-700', overhead: 'bg-amber-100 text-amber-700' }
const TYPE_ICONS: Record<string, typeof User> = { labor: User, machine: Cog, overhead: Users }

export default function ResourcesPage() {
  const { data: resources, isLoading } = useProductionResources()
  const create = useCreateProductionResource()
  const update = useUpdateProductionResource()
  const del = useDeleteProductionResource()
  const toast = useToast()
  const confirm = useConfirm()
  const [showCreate, setShowCreate] = useState(false)
  const [editId, setEditId] = useState<string | null>(null)

  const [form, setForm] = useState({
    name: '', resource_type: 'labor', cost_per_hour: '0', capacity_hours_per_day: '8',
    efficiency_pct: '100', shifts_per_day: '1', notes: '',
  })

  const inputCls = "w-full bg-muted border border-border rounded-xl px-3 py-2.5 text-sm outline-none focus:bg-card focus:ring-2 focus:ring-gray-900/10"

  function resetForm() {
    setForm({ name: '', resource_type: 'labor', cost_per_hour: '0', capacity_hours_per_day: '8', efficiency_pct: '100', shifts_per_day: '1', notes: '' })
  }

  async function handleSave() {
    if (!form.name) return
    try {
      if (editId) {
        await update.mutateAsync({ id: editId, data: form })
        toast.success('Recurso actualizado')
        setEditId(null)
      } else {
        await create.mutateAsync(form)
        toast.success('Recurso creado')
        setShowCreate(false)
      }
      resetForm()
    } catch (e: any) { toast.error(e.message) }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Users className="h-6 w-6 text-purple-600" />
          <div>
            <h1 className="text-2xl font-bold">Recursos / Centros de Trabajo</h1>
            <p className="text-sm text-muted-foreground">Mano de obra, maquinaria y costos indirectos de produccion</p>
          </div>
        </div>
        <button onClick={() => { resetForm(); setShowCreate(true); setEditId(null) }}
          className="flex items-center gap-1 px-4 py-2 text-sm bg-gray-900 text-white rounded-xl hover:bg-gray-800">
          <Plus className="h-4 w-4" /> Nuevo recurso
        </button>
      </div>

      {isLoading ? (
        <div className="text-center py-16"><Loader2 className="h-6 w-6 animate-spin mx-auto text-muted-foreground" /></div>
      ) : !resources || resources.length === 0 ? (
        <div className="text-center py-16 text-muted-foreground">Sin recursos — crea mano de obra o maquinaria para asignar a recetas</div>
      ) : (
        <div className="bg-card rounded-xl border overflow-hidden">
          <table className="w-full text-sm">
            <thead><tr className="bg-muted border-b text-xs text-muted-foreground uppercase">
              <th className="px-4 py-3 text-left">Nombre</th>
              <th className="px-4 py-3 text-left">Tipo</th>
              <th className="px-4 py-3 text-right">$/hora</th>
              <th className="px-4 py-3 text-right">Hrs/dia</th>
              <th className="px-4 py-3 text-right">Eficiencia</th>
              <th className="px-4 py-3 text-right">Turnos</th>
              <th className="px-4 py-3 text-center">Activo</th>
              <th className="px-4 py-3"></th>
            </tr></thead>
            <tbody>
              {resources.map(r => {
                const Icon = TYPE_ICONS[r.resource_type] ?? Cog
                return (
                  <tr key={r.id} className="border-b border-gray-50 hover:bg-muted/50">
                    <td className="px-4 py-2.5 font-medium">{r.name}</td>
                    <td className="px-4 py-2.5">
                      <span className={cn('inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold', TYPE_COLORS[r.resource_type])}>
                        <Icon className="h-2.5 w-2.5" /> {TYPE_LABELS[r.resource_type]}
                      </span>
                    </td>
                    <td className="px-4 py-2.5 text-right font-mono">${Number(r.cost_per_hour).toFixed(2)}</td>
                    <td className="px-4 py-2.5 text-right">{r.capacity_hours_per_day}</td>
                    <td className="px-4 py-2.5 text-right">{r.efficiency_pct}%</td>
                    <td className="px-4 py-2.5 text-right">{r.shifts_per_day}</td>
                    <td className="px-4 py-2.5 text-center">{r.is_active ? '✓' : '—'}</td>
                    <td className="px-4 py-2.5 text-right">
                      <button onClick={() => { setForm({ name: r.name, resource_type: r.resource_type, cost_per_hour: r.cost_per_hour, capacity_hours_per_day: r.capacity_hours_per_day, efficiency_pct: r.efficiency_pct, shifts_per_day: String(r.shifts_per_day), notes: r.notes ?? '' }); setEditId(r.id); setShowCreate(true) }}
                        className="p-1 text-muted-foreground hover:text-amber-600"><Pencil className="h-3.5 w-3.5" /></button>
                      <button onClick={async () => { const ok = await confirm({ title: 'Desactivar recurso', message: `Desactivar ${r.name}?`, confirmLabel: 'Desactivar', destructive: true }); if (ok) { await del.mutateAsync(r.id); toast.success('Desactivado') } }}
                        className="p-1 text-muted-foreground hover:text-red-500"><Trash2 className="h-3.5 w-3.5" /></button>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}

      {/* Create/Edit Modal */}
      {showCreate && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm" onClick={() => { setShowCreate(false); setEditId(null) }}>
          <div className="bg-card rounded-2xl p-6 w-full max-w-md shadow-2xl" onClick={e => e.stopPropagation()}>
            <h3 className="text-lg font-semibold mb-4">{editId ? 'Editar recurso' : 'Nuevo recurso'}</h3>
            <div className="grid grid-cols-2 gap-3">
              <div className="col-span-2"><label className="text-xs text-muted-foreground">Nombre *</label><input value={form.name} onChange={e => setForm(f => ({...f, name: e.target.value}))} className={inputCls} /></div>
              <div><label className="text-xs text-muted-foreground">Tipo</label>
                <select value={form.resource_type} onChange={e => setForm(f => ({...f, resource_type: e.target.value}))} className={inputCls}>
                  <option value="labor">Mano de obra</option>
                  <option value="machine">Maquinaria</option>
                  <option value="overhead">Costo indirecto</option>
                </select>
              </div>
              <div><label className="text-xs text-muted-foreground">Costo/hora ($)</label><input type="number" step="0.01" min="0" value={form.cost_per_hour} onChange={e => setForm(f => ({...f, cost_per_hour: e.target.value}))} className={inputCls} /></div>
              <div><label className="text-xs text-muted-foreground">Horas/dia</label><input type="number" step="0.5" min="0" value={form.capacity_hours_per_day} onChange={e => setForm(f => ({...f, capacity_hours_per_day: e.target.value}))} className={inputCls} /></div>
              <div><label className="text-xs text-muted-foreground">Eficiencia %</label><input type="number" min="0" max="100" value={form.efficiency_pct} onChange={e => setForm(f => ({...f, efficiency_pct: e.target.value}))} className={inputCls} /></div>
              <div><label className="text-xs text-muted-foreground">Turnos/dia</label><input type="number" min="1" value={form.shifts_per_day} onChange={e => setForm(f => ({...f, shifts_per_day: e.target.value}))} className={inputCls} /></div>
              <div className="col-span-2"><label className="text-xs text-muted-foreground">Notas</label><textarea value={form.notes} onChange={e => setForm(f => ({...f, notes: e.target.value}))} rows={2} className={inputCls} /></div>
            </div>
            <div className="flex gap-3 mt-4">
              <button onClick={() => { setShowCreate(false); setEditId(null); resetForm() }} className="flex-1 bg-secondary text-foreground rounded-xl px-4 py-2.5 text-sm">Cancelar</button>
              <button onClick={handleSave} disabled={create.isPending || update.isPending || !form.name}
                className="flex-1 bg-gray-900 text-white rounded-xl px-4 py-2.5 text-sm font-semibold disabled:opacity-50">
                {editId ? 'Guardar' : 'Crear'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
