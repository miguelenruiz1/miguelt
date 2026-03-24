/**
 * Domain-specific badge components built on top of shadcn Badge.
 * These provide the same API as the old custom badges.
 */
import { Badge } from '@/components/ui/badge'
import type { AssetState, EventType, WalletStatus } from '@/types/api'

// ─── Asset State Badge ──────────────────────────────────────────────────────

const stateStyles: Record<AssetState, string> = {
  in_transit:    'bg-blue-500/15 text-blue-700 border-0',
  in_custody:    'bg-emerald-500/15 text-emerald-700 border-0',
  loaded:        'bg-violet-500/15 text-violet-700 border-0',
  qc_passed:     'bg-emerald-500/15 text-emerald-700 border-0',
  qc_failed:     'bg-red-500/15 text-red-700 border-0',
  released:      '',  // uses variant="outline"
  burned:        'bg-cyan-500/15 text-cyan-700 border-0',
  customs_hold:  'bg-amber-500/15 text-amber-700 border-0',
  damaged:       'bg-red-500/15 text-red-700 border-0',
  delivered:     'bg-emerald-500/15 text-emerald-700 border-0',
  sealed:        'bg-violet-500/15 text-violet-700 border-0',
}

const stateLabels: Record<AssetState, string> = {
  in_transit:    'En Tránsito',
  in_custody:    'En Custodia',
  loaded:        'Cargado',
  qc_passed:     'QC Aprobado',
  qc_failed:     'QC Rechazado',
  released:      'Liberado',
  burned:        'Completado',
  customs_hold:  'Aduana',
  damaged:       'Dañado',
  delivered:     'Entregado',
  sealed:        'Sellado',
}

export function StateBadge({ state }: { state: AssetState }) {
  const style = stateStyles[state]
  if (state === 'released') return <Badge variant="outline">{stateLabels[state]}</Badge>
  return <Badge className={style}>{stateLabels[state] ?? state}</Badge>
}

// ─── Event Type Badge ───────────────────────────────────────────────────────

const eventStyles: Record<string, string> = {
  CREATED:           'bg-emerald-500/15 text-emerald-700 border-0',
  HANDOFF:           'bg-blue-500/15 text-blue-700 border-0',
  ARRIVED:           'bg-cyan-500/15 text-cyan-700 border-0',
  LOADED:            'bg-violet-500/15 text-violet-700 border-0',
  QC:                'bg-amber-500/15 text-amber-700 border-0',
  RELEASED:          '',
  BURN:              'bg-cyan-500/15 text-cyan-700 border-0',
  PICKUP:            'bg-blue-500/15 text-blue-700 border-0',
  GATE_IN:           'bg-emerald-500/15 text-emerald-700 border-0',
  GATE_OUT:          'bg-blue-500/15 text-blue-700 border-0',
  DEPARTED:          'bg-blue-500/15 text-blue-700 border-0',
  CUSTOMS_HOLD:      'bg-amber-500/15 text-amber-700 border-0',
  CUSTOMS_CLEARED:   'bg-emerald-500/15 text-emerald-700 border-0',
  DAMAGED:           'bg-red-500/15 text-red-700 border-0',
  DELIVERED:         'bg-emerald-500/15 text-emerald-700 border-0',
  SEALED:            'bg-violet-500/15 text-violet-700 border-0',
  UNSEALED:          'bg-violet-500/15 text-violet-700 border-0',
  TEMPERATURE_CHECK: 'bg-cyan-500/15 text-cyan-700 border-0',
  INSPECTION:        'bg-amber-500/15 text-amber-700 border-0',
  CONSOLIDATED:      '',
  DECONSOLIDATED:    '',
  NOTE:              '',
}

const eventLabels: Record<string, string> = {
  CREATED:           'Registrado',
  HANDOFF:           'Transferencia',
  ARRIVED:           'Llegada',
  LOADED:            'Cargado',
  QC:                'Control de Calidad',
  RELEASED:          'Liberado',
  BURN:              'Entrega Completada',
  PICKUP:            'Recolección',
  GATE_IN:           'Ingreso',
  GATE_OUT:          'Salida',
  DEPARTED:          'Despachado',
  CUSTOMS_HOLD:      'Retención Aduana',
  CUSTOMS_CLEARED:   'Aduana Liberada',
  DAMAGED:           'Daño Reportado',
  DELIVERED:         'Entregado',
  SEALED:            'Sellado',
  UNSEALED:          'Sello Removido',
  TEMPERATURE_CHECK: 'Temp. Check',
  INSPECTION:        'Inspección',
  CONSOLIDATED:      'Consolidado',
  DECONSOLIDATED:    'Desconsolidado',
  NOTE:              'Nota',
}

export function EventTypeBadge({ type }: { type: EventType | string }) {
  const style = eventStyles[type] ?? ''
  const label = eventLabels[type] ?? type
  if (!style) return <Badge variant="outline">{label}</Badge>
  return <Badge className={style}>{label}</Badge>
}

// ─── Anchor Badge ───────────────────────────────────────────────────────────

export function AnchorBadge({ anchored, attempts }: { anchored: boolean; attempts: number }) {
  if (anchored)
    return <Badge className="bg-emerald-500/15 text-emerald-700 border-0">Certificado</Badge>
  if (attempts > 0)
    return <Badge className="bg-amber-500/15 text-amber-700 border-0">Certificando ({attempts})</Badge>
  return <Badge variant="secondary">En cola</Badge>
}

// ─── Wallet Status Badge ────────────────────────────────────────────────────

export function WalletStatusBadge({ status }: { status: WalletStatus }) {
  switch (status) {
    case 'active':    return <Badge className="bg-emerald-500/15 text-emerald-700 border-0">Activo</Badge>
    case 'suspended': return <Badge className="bg-amber-500/15 text-amber-700 border-0">Suspendido</Badge>
    case 'revoked':   return <Badge className="bg-red-500/15 text-red-700 border-0">Revocado</Badge>
    default:          return <Badge variant="outline">{status}</Badge>
  }
}
