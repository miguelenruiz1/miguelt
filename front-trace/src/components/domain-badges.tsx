/**
 * Domain-specific badge components built on top of shadcn Badge.
 * 100% workflow-driven — no hardcoded state/event data.
 */
import { Badge } from '@/components/ui/badge'
import { useWorkflowStates, useWorkflowEventTypes } from '@/hooks/useWorkflow'
import type { AssetState, EventType, WalletStatus } from '@/types/api'

// ─── Asset State Badge ──────────────────────────────────────────────────────

export function StateBadge({ state }: { state: AssetState | string }) {
  const { data: wfStates } = useWorkflowStates()
  const ws = wfStates?.find(s => s.slug === state)

  if (ws) {
    return (
      <Badge className="border-0" style={{ backgroundColor: `${ws.color}20`, color: ws.color }}>
        {ws.label}
      </Badge>
    )
  }

  // Generic fallback — show slug as label
  return <Badge variant="outline">{state}</Badge>
}

// ─── Event Type Badge ───────────────────────────────────────────────────────

export function EventTypeBadge({ type }: { type: EventType | string }) {
  const { data: wfEventTypes } = useWorkflowEventTypes()
  const wfEvent = wfEventTypes?.find(e => e.slug === type)

  if (wfEvent) {
    return (
      <Badge className="border-0" style={{ backgroundColor: `${wfEvent.color}20`, color: wfEvent.color }}>
        {wfEvent.name}
      </Badge>
    )
  }

  return <Badge variant="outline">{type}</Badge>
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

export function BlockchainStatusBadge({ status }: { status: string }) {
  switch (status) {
    case 'CONFIRMED':  return <Badge className="bg-emerald-500/15 text-emerald-700 border-0">Certificado</Badge>
    case 'PENDING':    return <Badge className="bg-amber-500/15 text-amber-700 border-0">Certificando...</Badge>
    case 'FAILED':     return <Badge className="bg-red-500/15 text-red-700 border-0">Fallido</Badge>
    case 'SIMULATED':  return <Badge className="bg-blue-500/15 text-blue-700 border-0">Simulado</Badge>
    case 'SKIPPED':    return <Badge className="bg-muted0/10 text-muted-foreground border-0">Sin anclar</Badge>
    default:           return <Badge variant="outline">{status}</Badge>
  }
}
