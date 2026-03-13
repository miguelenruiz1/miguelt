import { cn } from '@/lib/utils'
import type { AssetState, EventType, WalletStatus } from '@/types/api'

type Variant = 'default' | 'success' | 'warning' | 'danger' | 'info' | 'muted' | 'purple' | 'cyan'

interface BadgeProps {
  variant?: Variant
  dot?: boolean
  children: React.ReactNode
  className?: string
}

const variants: Record<Variant, string> = {
  default: 'bg-slate-100   text-slate-700  ring-1 ring-slate-200',
  success: 'bg-emerald-50  text-emerald-700 ring-1 ring-emerald-200',
  warning: 'bg-amber-50    text-amber-700   ring-1 ring-amber-200',
  danger:  'bg-red-50      text-red-700     ring-1 ring-red-200',
  info:    'bg-indigo-50   text-indigo-700  ring-1 ring-indigo-200',
  muted:   'bg-slate-100   text-slate-500   ring-1 ring-slate-200',
  purple:  'bg-violet-50   text-violet-700  ring-1 ring-violet-200',
  cyan:    'bg-cyan-50     text-cyan-700    ring-1 ring-cyan-200',
}

const dotColors: Record<Variant, string> = {
  default: 'bg-slate-400',
  success: 'bg-emerald-500',
  warning: 'bg-amber-500',
  danger:  'bg-red-500',
  info:    'bg-indigo-500',
  muted:   'bg-slate-400',
  purple:  'bg-violet-500',
  cyan:    'bg-cyan-500',
}

export function Badge({ variant = 'default', dot, children, className }: BadgeProps) {
  return (
    <span className={cn(
      'inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium',
      variants[variant],
      className,
    )}>
      {dot && <span className={cn('h-1.5 w-1.5 rounded-full shrink-0', dotColors[variant])} />}
      {children}
    </span>
  )
}

// ─── Domain-specific badges ────────────────────────────────────────────────────

const stateVariants: Record<AssetState, Variant> = {
  in_transit: 'info',
  in_custody: 'success',
  loaded:     'purple',
  qc_passed:  'success',
  qc_failed:  'danger',
  released:   'muted',
  burned:     'cyan',
}

const stateLabels: Record<AssetState, string> = {
  in_transit: 'En Tránsito',
  in_custody: 'En Custodia',
  loaded:     'Cargado',
  qc_passed:  'QC Aprobado',
  qc_failed:  'QC Rechazado',
  released:   'Liberado',
  burned:     'Completado',
}

export function StateBadge({ state }: { state: AssetState }) {
  return <Badge variant={stateVariants[state]} dot>{stateLabels[state]}</Badge>
}

const walletVariants: Record<WalletStatus, Variant> = {
  active:    'success',
  suspended: 'warning',
  revoked:   'danger',
}

export function WalletStatusBadge({ status }: { status: WalletStatus }) {
  return <Badge variant={walletVariants[status]} dot>{status}</Badge>
}

const eventVariants: Record<EventType, Variant> = {
  CREATED:  'success',
  HANDOFF:  'info',
  ARRIVED:  'cyan',
  LOADED:   'purple',
  QC:       'warning',
  RELEASED: 'muted',
  BURN:     'cyan',
}

const eventLabels: Record<EventType, string> = {
  CREATED:  'Registrado',
  HANDOFF:  'Transferencia',
  ARRIVED:  'Llegada',
  LOADED:   'Cargado',
  QC:       'Control de Calidad',
  RELEASED: 'Liberado',
  BURN:     'Entrega Completada',
}

export function EventTypeBadge({ type }: { type: EventType }) {
  return <Badge variant={eventVariants[type]}>{eventLabels[type] ?? type}</Badge>
}

export function AnchorBadge({ anchored, attempts }: { anchored: boolean; attempts: number }) {
  if (anchored)     return <Badge variant="success" dot>Certificado</Badge>
  if (attempts > 0) return <Badge variant="warning" dot>Certificando ({attempts})</Badge>
  return                   <Badge variant="muted"   dot>En cola</Badge>
}
