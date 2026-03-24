import { useState } from 'react'
import { RefreshCw, ChevronDown, ChevronUp, MapPin, ExternalLink, ShieldCheck } from 'lucide-react'
import { useSettingsStore, explorerTxUrl } from '@/store/settings'

const isSimSig = (s: string) => s.startsWith('SIM_') || s.startsWith('sim')
import { EventTypeBadge, AnchorBadge } from '@/components/domain-badges'
import { HashChip } from '@/components/ui/Misc'
import { Button } from '@/components/ui/button'
import { useAnchorEvent } from '@/hooks/useAssets'
import { useToast } from '@/store/toast'
import { fmtDate, shortPubkey } from '@/lib/utils'
import type { CustodyEvent } from '@/types/api'

interface EventTimelineProps {
  events: CustodyEvent[]
  assetId: string
}

export function EventTimeline({ events, assetId }: EventTimelineProps) {
  const sorted = [...events].sort(
    (a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime()
  )

  return (
    <div className="relative">
      {/* Vertical line */}
      <div className="absolute left-[11px] top-5 bottom-5 w-px bg-slate-200" />
      <div className="space-y-0">
        {sorted.map((event, i) => (
          <EventRow key={event.id} event={event} assetId={assetId} isFirst={i === 0} />
        ))}
      </div>
    </div>
  )
}

function EventRow({ event, assetId, isFirst }: { event: CustodyEvent; assetId: string; isFirst: boolean }) {
  const [expanded, setExpanded] = useState(isFirst)
  const anchor = useAnchorEvent(assetId)
  const toast  = useToast()
  const { solanaCluster } = useSettingsStore()

  const handleAnchor = async () => {
    try {
      await anchor.mutateAsync(event.id)
      toast.success('Anchor job triggered')
    } catch {
      toast.error('Failed to trigger anchor')
    }
  }

  const hasExtra = event.data && Object.keys(event.data).length > 0

  return (
    <div className="relative flex gap-5 pb-6">
      {/* Dot */}
      <div className="relative z-10 mt-1 shrink-0">
        <div className={[
          'flex h-[22px] w-[22px] items-center justify-center rounded-full border-2 bg-white',
          isFirst ? 'border-primary' : 'border-slate-300',
        ].join(' ')}>
          <span className={[
            'h-2 w-2 rounded-full',
            isFirst ? 'bg-primary' : 'bg-slate-300',
          ].join(' ')} />
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 min-w-0">
        {/* Header */}
        <div className="flex flex-wrap items-start gap-2">
          <EventTypeBadge type={event.event_type} />
          <AnchorBadge anchored={event.anchored} attempts={event.anchor_attempts} />
          <span className="text-xs text-slate-400 ml-auto whitespace-nowrap tabular-nums">{fmtDate(event.timestamp)}</span>
        </div>

        {/* From → To */}
        <div className="mt-2 flex items-center gap-2 text-xs">
          {event.from_wallet && (
            <>
              <span className="text-slate-400">de</span>
              <span className="font-mono text-slate-600 font-medium">{shortPubkey(event.from_wallet)}</span>
            </>
          )}
          {event.from_wallet && event.to_wallet && (
            <span className="text-slate-300">→</span>
          )}
          {event.to_wallet && (
            <>
              <span className="text-slate-400">a</span>
              <span className="font-mono text-slate-600 font-medium">{shortPubkey(event.to_wallet)}</span>
            </>
          )}
        </div>

        {/* Hashes + location */}
        <div className="mt-2 flex flex-wrap items-center gap-2">
          <HashChip hash={event.event_hash} head={10} tail={4} />
          {event.location?.label && (
            <span className="inline-flex items-center gap-1 text-xs text-slate-400">
              <MapPin className="h-3 w-3" /> {event.location.label}
            </span>
          )}
        </div>

        {/* Solana tx — prominent verification link */}
        {event.solana_tx_sig && (
          <div className="mt-2">
            {isSimSig(event.solana_tx_sig) ? (
              <div className="inline-flex items-center gap-1.5 text-xs text-slate-400">
                <span>Simulación:</span>
                <HashChip hash={event.solana_tx_sig} head={10} tail={4} />
              </div>
            ) : (
              <a
                href={explorerTxUrl(event.solana_tx_sig, solanaCluster)}
                target="_blank"
                rel="noopener noreferrer"
                title={event.solana_tx_sig}
                className="inline-flex items-center gap-2 rounded-xl bg-emerald-50 border border-emerald-200 px-3 py-1.5 text-xs font-semibold text-emerald-700 hover:bg-emerald-100 hover:text-emerald-800 transition-colors"
              >
                <ShieldCheck className="h-3.5 w-3.5" />
                Verificar en Solana
                <span className="font-mono text-emerald-600 text-[11px]">
                  {event.solana_tx_sig.slice(0, 8)}…{event.solana_tx_sig.slice(-4)}
                </span>
                <ExternalLink className="h-3 w-3 shrink-0" />
              </a>
            )}
          </div>
        )}

        {/* Expandable data */}
        {hasExtra && (
          <div className="mt-2">
            <button
              onClick={() => setExpanded((e) => !e)}
              className="flex items-center gap-1 text-xs text-slate-500 hover:text-slate-800 transition-colors"
            >
              {expanded ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
              {expanded ? 'Ocultar datos' : 'Ver datos'}
            </button>
            {expanded && (
              <pre className="mt-2 rounded-xl bg-slate-50 border border-slate-200 p-3 text-xs text-slate-600 overflow-x-auto font-mono">
                {JSON.stringify(event.data, null, 2)}
              </pre>
            )}
          </div>
        )}

        {/* Anchor error */}
        {event.anchor_last_error && !event.anchored && (
          <div className="mt-2 rounded-xl bg-red-50 border border-red-200 px-3 py-2 text-xs text-red-700">
            {event.anchor_last_error}
          </div>
        )}
        {!event.anchored && (
          <div className="mt-2">
            <Button variant="ghost" size="sm" loading={anchor.isPending} onClick={handleAnchor}>
              <RefreshCw className="h-3.5 w-3.5" />
              Reintentar certificación
            </Button>
          </div>
        )}
      </div>
    </div>
  )
}
