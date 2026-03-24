import { useState } from 'react'
import { Clock, ChevronDown, ChevronUp } from 'lucide-react'
import { useEntityTimeline } from '@/hooks/useInventory'
import { format } from 'date-fns'

interface ActivityTimelineProps {
  resourceType: string
  resourceId: string
}

const ACTION_LABELS: Record<string, string> = {
  create: 'Creado',
  update: 'Actualizado',
  delete: 'Eliminado',
  start: 'Iniciado',
  complete: 'Completado',
  approve: 'Aprobado',
  cancel: 'Cancelado',
  count: 'Contado',
  recount: 'Recontado',
  send: 'Enviado',
  confirm: 'Confirmado',
  receive: 'Recibido',
  execute: 'Ejecutado',
  update_status: 'Estado actualizado',
  add_impact: 'Impacto agregado',
  assign: 'Asignado',
}

function getActionLabel(action: string): string {
  const parts = action.split('.')
  const verb = parts[parts.length - 1]
  return ACTION_LABELS[verb] ?? verb
}

export function ActivityTimeline({ resourceType, resourceId }: ActivityTimelineProps) {
  const [limit, setLimit] = useState(10)
  const { data, isLoading } = useEntityTimeline(resourceType, resourceId, { limit })

  if (isLoading) return <div className="text-sm text-slate-400 py-4">Cargando actividad...</div>

  const items = data?.items ?? []
  if (items.length === 0) return <div className="text-sm text-slate-400 py-4">Sin actividad registrada</div>

  return (
    <div className="space-y-3">
      <h3 className="text-sm font-semibold text-slate-700 flex items-center gap-2">
        <Clock className="h-4 w-4 text-slate-400" />
        Actividad reciente
      </h3>
      <div className="relative pl-4 border-l-2 border-slate-200 space-y-4">
        {items.map((entry) => (
          <div key={entry.id} className="relative">
            <div className="absolute -left-[21px] top-1.5 w-2.5 h-2.5 rounded-full bg-primary/70 border-2 border-white" />
            <div className="text-xs text-slate-500 mb-0.5">
              {format(new Date(entry.created_at), 'dd/MM/yyyy HH:mm')}
            </div>
            <div className="text-sm text-slate-700">
              <span className="font-mono text-xs bg-slate-100 text-slate-600 rounded px-1 py-0.5 mr-1.5">
                {getActionLabel(entry.action)}
              </span>
              {entry.user_email && (
                <span className="text-slate-500">por {entry.user_email}</span>
              )}
            </div>
          </div>
        ))}
      </div>
      {data && data.total > limit && (
        <button
          onClick={() => setLimit((l) => l + 10)}
          className="text-xs text-primary hover:text-primary flex items-center gap-1"
        >
          <ChevronDown className="h-3 w-3" />
          Mostrar más ({data.total - limit} restantes)
        </button>
      )}
      {limit > 10 && (
        <button
          onClick={() => setLimit(10)}
          className="text-xs text-slate-400 hover:text-slate-600 flex items-center gap-1"
        >
          <ChevronUp className="h-3 w-3" />
          Mostrar menos
        </button>
      )}
    </div>
  )
}
