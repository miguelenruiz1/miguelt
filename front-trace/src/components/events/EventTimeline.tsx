import { useState, useMemo } from 'react'
import {
  ChevronDown, ChevronUp, MapPin, ExternalLink, ShieldCheck,
  Package, Anchor, Clock, ArrowRight, FileText, Image,
} from 'lucide-react'
import { useSettingsStore, explorerTxUrl, xrayAssetUrl, xrayTxUrl } from '@/store/settings'

const isSimSig = (s: string) => s.startsWith('SIM_') || s.startsWith('sim')
import { EventTypeBadge } from '@/components/domain-badges'
import { HashChip } from '@/components/ui/misc'
import { Button } from '@/components/ui/button'
import { useAnchorEvent } from '@/hooks/useAssets'
import { useEventDocuments } from '@/hooks/useDocuments'
import { useWalletList } from '@/hooks/useWallets'
import { useWorkflowEventTypes } from '@/hooks/useWorkflow'
import { resolveIcon } from '@/lib/icon-map'
import { useToast } from '@/store/toast'
import { fmtDate, shortPubkey } from '@/lib/utils'
import type { CustodyEvent } from '@/types/api'

interface EventTimelineProps {
  events: CustodyEvent[]
  assetId: string
  blockchainAssetId?: string | null
}

// Default icon/color when no workflow data available
const DEFAULT_ICON = Package
const DEFAULT_COLOR = '#94a3b8'

function resolveWalletName(pubkey: string | null, walletMap: Map<string, string>): string {
  if (!pubkey) return ''
  return walletMap.get(pubkey) || shortPubkey(pubkey, 4)
}

/**
 * Build a human-readable description from event data.
 * No hardcoded event types — constructs from wallets, location, notes, and data.
 */
function buildDescription(
  event: CustodyEvent,
  walletMap: Map<string, string>,
  eventNameMap: Map<string, string>,
): string {
  const from = resolveWalletName(event.from_wallet, walletMap)
  const to = resolveWalletName(event.to_wallet, walletMap)
  const location = event.location?.label
  const notes = event.data?.notes as string | undefined
  const reason = event.data?.reason as string | undefined
  const result = event.data?.result as string | undefined
  const eventName = eventNameMap.get(event.event_type) || event.event_type

  const parts: string[] = []

  // Transfer: from → to
  if (from && to && from !== to) {
    parts.push(`${from} → ${to}`)
  } else if (to && !from) {
    parts.push(`Asignado a ${to}`)
  } else if (to) {
    parts.push(`Custodio: ${to}`)
  }

  // Location
  if (location) parts.push(location)

  // Result (QC or similar)
  if (result) parts.push(`Resultado: ${result}`)

  // Reason
  if (reason) parts.push(reason)

  // Notes
  if (notes) parts.push(notes)

  // If we have context, use it; otherwise just use the event name
  if (parts.length > 0) {
    return `${eventName} — ${parts.join('. ')}`
  }
  return eventName
}

// ─── Main component ──────────────────────────────────────────────────────────

export function EventTimeline({ events, assetId, blockchainAssetId }: EventTimelineProps) {
  const sorted = [...events].sort(
    (a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime()
  )

  // Fetch all wallets to resolve names
  const { data: walletsData } = useWalletList({ limit: 200 })
  const walletMap = new Map<string, string>()
  if (walletsData?.items) {
    for (const w of walletsData.items) {
      walletMap.set(w.wallet_pubkey, w.name || shortPubkey(w.wallet_pubkey, 4))
    }
  }

  // Build dynamic icon/color maps from workflow event types
  const { data: wfEventTypes } = useWorkflowEventTypes()
  const eventIconMap = useMemo(() => {
    const m = new Map<string, typeof Package>()
    if (wfEventTypes) {
      for (const et of wfEventTypes) {
        m.set(et.slug, resolveIcon(et.icon))
      }
    }
    return m
  }, [wfEventTypes])

  const eventColorMap = useMemo(() => {
    const m = new Map<string, string>()
    if (wfEventTypes) {
      for (const et of wfEventTypes) {
        m.set(et.slug, et.color)
      }
    }
    return m
  }, [wfEventTypes])

  const eventNameMap = useMemo(() => {
    const m = new Map<string, string>()
    if (wfEventTypes) {
      for (const et of wfEventTypes) {
        m.set(et.slug, et.name)
      }
    }
    return m
  }, [wfEventTypes])

  return (
    <div className="relative">
      {/* Vertical line */}
      <div className="absolute left-5 top-6 bottom-6 w-0.5 bg-gradient-to-b from-slate-200 via-slate-200 to-transparent" />
      <div className="space-y-1">
        {sorted.map((event, i) => (
          <EventRow
            key={event.id}
            event={event}
            assetId={assetId}
            isFirst={i === 0}
            isLast={i === sorted.length - 1}
            eventIconMap={eventIconMap}
            eventColorMap={eventColorMap}
            eventNameMap={eventNameMap}
            blockchainAssetId={blockchainAssetId}
            walletMap={walletMap}
          />
        ))}
      </div>
    </div>
  )
}

// ─── Single event row ────────────────────────────────────────────────────────

function EventRow({
  event, assetId, isFirst, isLast, walletMap, eventIconMap, eventColorMap, eventNameMap, blockchainAssetId,
}: {
  event: CustodyEvent
  assetId: string
  isFirst: boolean
  isLast: boolean
  walletMap: Map<string, string>
  eventIconMap: Map<string, typeof Package>
  eventColorMap: Map<string, string>
  eventNameMap: Map<string, string>
  blockchainAssetId?: string | null
}) {
  const [showTechnical, setShowTechnical] = useState(false)
  const [showDocs, setShowDocs] = useState(false)
  const anchor = useAnchorEvent(assetId)
  const toast = useToast()
  const { solanaCluster } = useSettingsStore()
  const { data: docsData } = useEventDocuments(assetId, event.id)
  const documents = docsData?.documents ?? []
  const docCount = documents.length

  const handleAnchor = async () => {
    try {
      await anchor.mutateAsync(event.id)
      toast.success('Certificación blockchain iniciada')
    } catch {
      toast.error('Error al iniciar certificación')
    }
  }

  const description = buildDescription(event, walletMap, eventNameMap)
  const Icon = eventIconMap.get(event.event_type) || DEFAULT_ICON
  const hexColor = eventColorMap.get(event.event_type) || DEFAULT_COLOR
  const hasExtra = event.data && Object.keys(event.data).length > 0
  const hasTechnicalData = event.event_hash || event.solana_tx_sig || hasExtra

  return (
    <div className={`relative flex gap-4 px-2 py-3 rounded-xl transition-colors ${isFirst ? 'bg-primary/[0.03]' : 'hover:bg-muted/50'}`}>
      {/* Icon dot */}
      <div className="relative z-10 shrink-0 mt-0.5">
        <div
          className="flex h-10 w-10 items-center justify-center rounded-xl"
          style={isFirst
            ? { backgroundColor: hexColor, color: '#fff' }
            : { backgroundColor: '#fff', border: '2px solid #e2e8f0' }
          }
        >
          <Icon className="h-4.5 w-4.5" style={{ color: isFirst ? '#fff' : '#94a3b8' }} />
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 min-w-0 pt-0.5">
        {/* Header: type badge + timestamp */}
        <div className="flex flex-wrap items-center gap-2">
          <EventTypeBadge type={event.event_type} />
          {event.anchored && (
            <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded-md text-[10px] font-semibold bg-emerald-50 text-emerald-600 border border-emerald-100">
              <ShieldCheck className="h-3 w-3" /> Verificado
            </span>
          )}
          {docCount > 0 && (
            <button
              type="button"
              onClick={() => setShowDocs(!showDocs)}
              className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded-md text-[10px] font-semibold bg-blue-50 text-blue-600 border border-blue-100 hover:bg-blue-100 transition-colors cursor-pointer"
            >
              <FileText className="h-3 w-3" /> {docCount} doc{docCount !== 1 ? 's' : ''}
            </button>
          )}
          <span className="text-[11px] text-muted-foreground ml-auto whitespace-nowrap tabular-nums flex items-center gap-1">
            <Clock className="h-3 w-3" />
            {fmtDate(event.timestamp)}
          </span>
        </div>

        {/* Human-readable description */}
        <p className="mt-1.5 text-sm text-foreground leading-relaxed">
          {description}
        </p>

        {/* Location pill */}
        {event.location?.label && (
          <span className="inline-flex items-center gap-1 mt-2 text-xs text-muted-foreground bg-muted border border-border rounded-lg px-2 py-0.5">
            <MapPin className="h-3 w-3 text-muted-foreground" /> {event.location.label}
          </span>
        )}

        {/* Transfer visual: from → to */}
        {event.from_wallet && event.to_wallet && (
          <div className="mt-2 flex items-center gap-2 text-xs">
            <span className="inline-flex items-center gap-1 bg-muted border border-border rounded-lg px-2 py-1 font-medium text-muted-foreground">
              {resolveWalletName(event.from_wallet, walletMap)}
            </span>
            <ArrowRight className="h-3.5 w-3.5 text-slate-300 shrink-0" />
            <span className="inline-flex items-center gap-1 bg-primary/5 border border-primary/10 rounded-lg px-2 py-1 font-medium text-primary">
              {resolveWalletName(event.to_wallet, walletMap)}
            </span>
          </div>
        )}

        {/* Documents expandable */}
        {showDocs && documents.length > 0 && (
          <div className="mt-2 space-y-1">
            {documents.map(link => {
              const f = link.file
              const isImg = f.content_type.startsWith('image/')
              const DocIcon = isImg ? Image : FileText
              const sizeStr = f.file_size < 1024 * 1024
                ? `${(f.file_size / 1024).toFixed(0)}KB`
                : `${(f.file_size / (1024 * 1024)).toFixed(1)}MB`

              return (
                <a
                  key={link.id}
                  href={f.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-2 rounded-lg bg-card border border-border px-2.5 py-1.5 text-xs text-muted-foreground hover:bg-muted transition-colors"
                >
                  <DocIcon className="h-3.5 w-3.5 text-muted-foreground shrink-0" />
                  <span className="truncate flex-1 font-medium">{f.title || f.original_filename}</span>
                  <span className="text-[10px] text-muted-foreground shrink-0">{link.document_type}</span>
                  <span className="text-[10px] text-muted-foreground shrink-0">{sizeStr}</span>
                  {link.compliance_source && (
                    <span className="text-[9px] px-1 py-0.5 bg-indigo-50 text-indigo-600 rounded border border-indigo-200 font-medium shrink-0">
                      EUDR
                    </span>
                  )}
                  <ExternalLink className="h-2.5 w-2.5 text-slate-300 shrink-0" />
                </a>
              )
            })}
          </div>
        )}

        {/* Blockchain verification links */}
        {event.anchored && event.solana_tx_sig && !isSimSig(event.solana_tx_sig) && (
          <div className="mt-2 flex flex-wrap gap-2">
            {/* 1. Ver NFT — only when a real blockchain asset ID exists */}
            {blockchainAssetId && !blockchainAssetId.startsWith('sim') && (
              <a
                href={xrayAssetUrl(blockchainAssetId, solanaCluster)}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1.5 rounded-lg bg-violet-50 border border-violet-100 px-2.5 py-1 text-[11px] font-semibold text-violet-700 hover:bg-violet-100 transition-colors"
              >
                <Package className="h-3 w-3" />
                Ver NFT
                <ExternalLink className="h-2.5 w-2.5 ml-0.5" />
              </a>
            )}
            {/* 2. Solana Explorer — transaction details */}
            <a
              href={explorerTxUrl(event.solana_tx_sig, solanaCluster)}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1.5 rounded-lg bg-emerald-50 border border-emerald-100 px-2.5 py-1 text-[11px] font-semibold text-emerald-700 hover:bg-emerald-100 transition-colors"
            >
              <ShieldCheck className="h-3 w-3" />
              Solana Explorer
              <ExternalLink className="h-2.5 w-2.5 ml-0.5" />
            </a>
            {/* 3. XRAY — tx viewer with decoded instructions */}
            <a
              href={xrayTxUrl(event.solana_tx_sig, solanaCluster)}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1.5 rounded-lg bg-blue-50 border border-blue-100 px-2.5 py-1 text-[11px] font-semibold text-blue-700 hover:bg-blue-100 transition-colors"
            >
              <Anchor className="h-3 w-3" />
              XRAY
              <ExternalLink className="h-2.5 w-2.5 ml-0.5" />
            </a>
          </div>
        )}

        {/* Technical details — collapsible */}
        {hasTechnicalData && (
          <div className="mt-2">
            <button
              onClick={() => setShowTechnical(!showTechnical)}
              className="flex items-center gap-1 text-[11px] text-muted-foreground hover:text-muted-foreground transition-colors"
            >
              {showTechnical ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
              {showTechnical ? 'Ocultar detalles técnicos' : 'Detalles técnicos'}
            </button>
            {showTechnical && (
              <div className="mt-2 rounded-xl bg-muted/80 border border-border p-3 space-y-2">
                {event.event_hash && (
                  <div className="flex items-center gap-2 text-xs">
                    <span className="text-muted-foreground font-medium shrink-0">Hash:</span>
                    <HashChip hash={event.event_hash} head={10} tail={4} />
                  </div>
                )}
                {event.prev_event_hash && (
                  <div className="flex items-center gap-2 text-xs">
                    <span className="text-muted-foreground font-medium shrink-0">Hash anterior:</span>
                    <HashChip hash={event.prev_event_hash} head={10} tail={4} />
                  </div>
                )}
                {event.solana_tx_sig && (
                  <div className="flex items-center gap-2 text-xs">
                    <span className="text-muted-foreground font-medium shrink-0">TX Solana:</span>
                    {isSimSig(event.solana_tx_sig) ? (
                      <span className="text-muted-foreground font-mono text-[11px]">Simulación</span>
                    ) : (
                      <HashChip hash={event.solana_tx_sig} head={10} tail={4} />
                    )}
                  </div>
                )}
                {event.from_wallet && (
                  <div className="flex items-center gap-2 text-xs">
                    <span className="text-muted-foreground font-medium shrink-0">Wallet origen:</span>
                    <span className="font-mono text-[11px] text-muted-foreground">{event.from_wallet}</span>
                  </div>
                )}
                {event.to_wallet && (
                  <div className="flex items-center gap-2 text-xs">
                    <span className="text-muted-foreground font-medium shrink-0">Wallet destino:</span>
                    <span className="font-mono text-[11px] text-muted-foreground">{event.to_wallet}</span>
                  </div>
                )}
                {hasExtra && (
                  <div>
                    <span className="text-muted-foreground font-medium text-xs">Datos del evento:</span>
                    <pre className="mt-1 rounded-lg bg-card border border-border p-2 text-[11px] text-muted-foreground overflow-x-auto font-mono">
                      {JSON.stringify(event.data, null, 2)}
                    </pre>
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {/* Anchor error + retry */}
        {event.anchor_last_error && !event.anchored && (
          <div className="mt-2 rounded-lg bg-red-50 border border-red-100 px-3 py-2 text-[11px] text-red-600">
            {event.anchor_last_error}
          </div>
        )}
        {!event.anchored && (
          <div className="mt-1.5">
            <Button variant="ghost" size="sm" className="h-7 text-[11px] text-muted-foreground hover:text-muted-foreground" loading={anchor.isPending} onClick={handleAnchor}>
              <Anchor className="h-3 w-3" />
              Certificar en blockchain
            </Button>
          </div>
        )}
      </div>
    </div>
  )
}
