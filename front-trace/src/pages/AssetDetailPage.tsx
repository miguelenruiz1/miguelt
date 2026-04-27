import { useState, useMemo, useEffect, useRef } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import type { LucideIcon } from 'lucide-react'
import {
  Anchor, ArrowUpRight, Check, CheckCircle2, ChevronDown, ChevronRight,
  ChevronUp, Circle, Clock, Copy, Download, ExternalLink, FileDown, FileText,
  Flag, FlaskConical, MapPin, Maximize2, MessageSquare, Package, PackageCheck,
  Paperclip, Plus, RefreshCw, Share2, ShieldAlert, ShieldCheck, ShieldOff,
  Sparkles, Trash2, Truck, UserPlus, X,
} from 'lucide-react'

import { useAsset, useAssetEvents, useDeleteAsset } from '@/hooks/useAssets'
import { useWalletList } from '@/hooks/useWallets'
import { useWorkflowStates, useAvailableActions } from '@/hooks/useWorkflow'
import { useAssetCompliance, useGenerateCertificate, useRecordCertificate, usePlot, useActivations, useFrameworks } from '@/hooks/useCompliance'
import { useIsModuleActive } from '@/hooks/useModules'
import { useSettingsStore, explorerAddressUrl, explorerTxUrl, xrayAssetUrl } from '@/store/settings'
import { useToast } from '@/store/toast'
import { authFetch } from '@/lib/auth-fetch'
import { fmtDate, shortPubkey, cn } from '@/lib/utils'
import { resolveIcon } from '@/lib/icon-map'
import { generateTraceabilityPDF } from '@/utils/generateTraceabilityPDF'

import { Topbar } from '@/components/layout/Topbar'
import { Button } from '@/components/ui/Button'
import { Spinner, EmptyState } from '@/components/ui/Misc'
import { WorkflowEventModal } from '@/components/events/WorkflowEventModal'
import type { Asset, AvailableAction, BlockchainStatus, CustodyEvent, WorkflowState } from '@/types/api'

const isSimulated = (s: string) => s.startsWith('sim') || s.startsWith('SIM_')

const nf = new Intl.NumberFormat('es-CO', { maximumFractionDigits: 0 })

const fmtRelative = (iso: string): string => {
  const m = Math.floor((Date.now() - new Date(iso).getTime()) / 60000)
  if (m < 1) return 'ahora'
  if (m < 60) return `hace ${m} min`
  const h = Math.floor(m / 60)
  if (h < 24) return `hace ${h} h`
  const d = Math.floor(h / 24)
  if (d < 7) return `hace ${d} d`
  return new Date(iso).toLocaleDateString('es-CO', { day: '2-digit', month: 'short' })
}

const fmtTime = (iso: string) =>
  new Date(iso).toLocaleTimeString('es-CO', { hour: '2-digit', minute: '2-digit', hour12: false })

const fmtDateLong = (iso: string): string => {
  const d = new Date(iso)
  const today = new Date()
  const yesterday = new Date(today.getTime() - 86400000)
  if (d.toDateString() === today.toDateString()) return 'Hoy'
  if (d.toDateString() === yesterday.toDateString()) return 'Ayer'
  return d.toLocaleDateString('es-CO', { weekday: 'long', day: '2-digit', month: 'long' })
}

type EventCategory = 'all' | 'movement' | 'quality' | 'system'

const MOVEMENT_TYPES = new Set([
  'handoff', 'arrived', 'loaded', 'released', 'released_admin',
  'pickup', 'delivered', 'departed', 'gate_in', 'gate_out',
  'consolidated', 'deconsolidated', 'sealed', 'unsealed', 'return',
])
const QUALITY_TYPES = new Set([
  'qc_passed', 'qc_failed', 'qc', 'inspection',
  'temperature_check', 'damaged', 'customs_cleared', 'customs_hold',
])
const SYSTEM_TYPES = new Set(['anchored', 'created', 'minted', 'note'])

const eventCategory = (type: string): EventCategory => {
  const k = normalizeEventType(type)
  if (MOVEMENT_TYPES.has(k)) return 'movement'
  if (QUALITY_TYPES.has(k)) return 'quality'
  if (SYSTEM_TYPES.has(k)) return 'system'
  return 'movement'
}

type Movement = { primary: CustodyEvent; attached: CustodyEvent[] }

// El backend a veces genera slugs `MOVE_TO_<STATE>` para transiciones del
// workflow. Los normalizamos al estado destino para que el mapping de
// label/icon/color/categoría funcione.
const normalizeEventType = (t: string): string => {
  const k = t.toLowerCase()
  return k.startsWith('move_to_') ? k.slice(8) : k
}

// Movimientos físicos reales (cambian la posesión o ubicación de la carga).
// El resto (qc, damaged, anchored, evidence, note, gps_ping, etc.) son
// EVENTOS que se anidan bajo el último movimiento.
const PRIMARY_EVENT_TYPES = new Set([
  'handoff', 'arrived', 'loaded', 'released', 'released_admin', 'delivered',
  'pickup', 'created', 'gate_in', 'gate_out', 'departed',
  'sealed', 'unsealed', 'consolidated', 'deconsolidated', 'return',
])

// Workflow states que representan progreso físico de la carga (happy path).
// Excluye estados de calidad/incidente (qc_failed, damaged, customs_hold,
// burned, devuelto) que son desvíos del flujo, no pasos lineales.
const MOVEMENT_STATE_SLUGS = new Set([
  'in_custody', 'in_transit', 'loaded', 'arrived',
  'sealed', 'qc_passed', 'released', 'delivered',
])

function buildMovements(events: CustodyEvent[]): Movement[] {
  const ascending = [...events].sort((a, b) =>
    +new Date(a.timestamp || a.created_at) - +new Date(b.timestamp || b.created_at),
  )
  const result: Movement[] = []
  let current: Movement | null = null
  for (const e of ascending) {
    if (PRIMARY_EVENT_TYPES.has(normalizeEventType(e.event_type))) {
      current = { primary: e, attached: [] }
      result.push(current)
    } else if (current) {
      current.attached.push(e)
    } else {
      result.push({ primary: e, attached: [] })
    }
  }
  return result.reverse()
}

const groupMovementsByDay = (movements: Movement[]) => {
  const groups: Record<string, { date: string; movements: Movement[] }> = {}
  movements.forEach(m => {
    const ts = m.primary.timestamp || m.primary.created_at
    const key = new Date(ts).toDateString()
    if (!groups[key]) groups[key] = { date: ts, movements: [] }
    groups[key].movements.push(m)
  })
  return Object.values(groups).sort((a, b) => +new Date(b.date) - +new Date(a.date))
}

// ────────────────────────────────────────────────────────────────────────────
// Page
// ────────────────────────────────────────────────────────────────────────────

export function AssetDetailPage() {
  const { id = '' } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const toast = useToast()
  const { solanaCluster } = useSettingsStore()

  const [activeAction, setActiveAction] = useState<AvailableAction | null>(null)
  const [actionPickerOpen, setActionPickerOpen] = useState(false)
  const [imageOpen, setImageOpen] = useState(false)
  const [bcExpanded, setBcExpanded] = useState(false)
  const [nftExpanded, setNftExpanded] = useState(false)
  const [downloadingTrace, setDownloadingTrace] = useState(false)
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false)
  const [filter, setFilter] = useState<EventCategory>('all')

  const deleteAsset = useDeleteAsset()
  const { data: asset, isLoading, refetch, isFetching } = useAsset(id)
  const { data: eventsData, isLoading: eventsLoading } = useAssetEvents(id)
  const { data: workflowStates } = useWorkflowStates()
  const { data: walletsData } = useWalletList({ limit: 200 })

  const currentWfState = workflowStates?.find(
    s => s.id === asset?.workflow_state_id || s.slug === asset?.state,
  )
  const effectiveStateSlug = currentWfState?.slug ?? asset?.state
  const { data: availableActions } = useAvailableActions(effectiveStateSlug)

  const walletMap = useMemo(() => {
    const m = new Map<string, { name: string; org?: string }>()
    walletsData?.items?.forEach(w => {
      m.set(w.wallet_pubkey, { name: w.name || shortPubkey(w.wallet_pubkey, 4) })
    })
    return m
  }, [walletsData])

  const events = eventsData?.items ?? []
  const isInactive = currentWfState?.is_terminal ?? false

  const progressSteps = useMemo(() => {
    if (!workflowStates?.length) return []
    return workflowStates
      .filter(s => MOVEMENT_STATE_SLUGS.has(s.slug))
      .sort((a, b) => a.sort_order - b.sort_order)
  }, [workflowStates])

  const primaryAction = useMemo(() => {
    if (!availableActions?.length || isInactive) return null
    return availableActions.find(a =>
      a.to_state && !a.to_state.is_terminal && !a.event_type?.is_informational,
    ) ?? null
  }, [availableActions, isInactive])

  const filteredEvents = useMemo(() => {
    if (filter === 'all') return events
    return events.filter(e => eventCategory(e.event_type) === filter)
  }, [events, filter])

  const movementGroups = useMemo(
    () => groupMovementsByDay(buildMovements(filteredEvents)),
    [filteredEvents],
  )

  if (isLoading) {
    return (
      <div className="flex flex-col flex-1 overflow-hidden">
        <Topbar title="Carga" />
        <div className="p-6 space-y-4">
          <div className="h-8 w-72 rounded bg-muted animate-pulse" />
          <div className="h-64 rounded-xl bg-muted animate-pulse" />
        </div>
      </div>
    )
  }

  if (!asset) {
    return (
      <div className="flex flex-col flex-1 overflow-hidden">
        <Topbar title="Carga no encontrada" />
        <EmptyState
          title="Carga no encontrada"
          action={<Button onClick={() => navigate('/assets')}>Volver a Cargas</Button>}
        />
      </div>
    )
  }

  const meta = asset.metadata as Record<string, unknown>
  const cargoName = (meta?.name as string | undefined) ?? asset.product_type
  const humanId = (meta?.human_id as string | undefined)
    ?? `CRG-${asset.id.replace(/-/g, '').slice(-6).toUpperCase()}`
  const weight = meta?.weight ?? meta?.peso_total_kg
  const weightUnit = (meta?.weightUnit as string | undefined) || 'kg'
  const batchNumber = (meta?.batch_number as string | undefined) || (meta?.lot_number as string | undefined)
  const moisture = meta?.moisture_pct as string | number | undefined
  const fermentation = meta?.fermentation_days as string | number | undefined
  const originRegion = meta?.origin_region as string | undefined
  const custodian = walletMap.get(asset.current_custodian_wallet)
  const custodianName = custodian?.name ?? shortPubkey(asset.current_custodian_wallet, 4)

  async function handleDownloadTraceability() {
    if (downloadingTrace || !asset) return
    setDownloadingTrace(true)
    try {
      const batchRef = batchNumber || asset.id
      const publicVerifyUrl = `${window.location.origin}/verificar/${encodeURIComponent(batchRef)}`
      const walletNames: Record<string, string> = {}
      walletMap.forEach((v, k) => { walletNames[k] = v.name })
      await generateTraceabilityPDF({
        asset,
        events,
        organization: custodianName ? { name: custodianName } : null,
        publicVerifyUrl,
        solanaCluster,
        walletNames,
      })
    } catch (err) {
      toast.error(`Error generando PDF: ${err instanceof Error ? err.message : String(err)}`)
    } finally {
      setDownloadingTrace(false)
    }
  }

  return (
    <div className="flex flex-col flex-1 overflow-hidden bg-background">
      {/* ─────────── Header ─────────── */}
      <header className="bg-card border-b border-border sticky top-0 z-30">
        {/* Breadcrumbs */}
        <div className="px-6 h-9 flex items-center text-xs text-muted-foreground border-b border-border/50">
          <Link to="/" className="hover:text-foreground transition">Trace</Link>
          <ChevronRight className="w-3 h-3 mx-1.5 text-muted-foreground/60" />
          <Link to="/assets" className="hover:text-foreground transition">Cargas</Link>
          <ChevronRight className="w-3 h-3 mx-1.5 text-muted-foreground/60" />
          <span className="text-foreground font-medium tabular-nums">{humanId}</span>
        </div>

        {/* Title + actions */}
        <div className="px-6 py-3 flex items-start gap-4">
          <button
            onClick={() => setImageOpen(true)}
            className="h-11 w-11 rounded-lg shrink-0 grid place-items-center text-white relative overflow-hidden hover:opacity-90 transition group"
            style={{ background: 'linear-gradient(135deg,#16A34A 0%, #0EA5E9 100%)' }}
            title="Ver imagen NFT"
          >
            <Package className="w-5 h-5" />
            <span className="absolute inset-0 bg-black/0 group-hover:bg-black/20 grid place-items-center transition">
              <Maximize2 className="w-3.5 h-3.5 opacity-0 group-hover:opacity-100" />
            </span>
          </button>

          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <h1 className="text-[17px] font-semibold text-foreground tracking-tight truncate">
                {cargoName}
              </h1>
              {currentWfState && <StatePill state={currentWfState} />}
              <BlockchainBadgeMini status={asset.blockchain_status ?? 'SKIPPED'} />
            </div>
            <div className="mt-1 flex items-center gap-3 text-xs text-muted-foreground flex-wrap">
              <span className="font-mono tabular-nums text-foreground/80 font-medium">{humanId}</span>
              <span>·</span>
              <span>{asset.product_type}</span>
              {weight !== undefined && weight !== null && (
                <>
                  <span>·</span>
                  <span className="tabular-nums">
                    {nf.format(Number(weight))} {weightUnit}
                  </span>
                </>
              )}
              <span>·</span>
              <span>actualizado {fmtRelative(asset.updated_at)}</span>
            </div>
          </div>

          <div className="flex items-center gap-1.5 shrink-0">
            <IconBtn icon={RefreshCw} onClick={() => refetch()} title="Refrescar" spinning={isFetching} />
            <IconBtn
              icon={FileDown}
              onClick={handleDownloadTraceability}
              title="Descargar PDF de trazabilidad"
              disabled={downloadingTrace || events.length === 0}
            />
            <CertificateDownloadIcon assetId={id} />
            <IconBtn icon={Share2} title="Compartir (próximamente)" disabled />
            <div className="h-5 w-px bg-border mx-1" />
            {primaryAction && (
              <button
                onClick={() => setActiveAction(primaryAction)}
                className="h-8 pl-2.5 pr-3 rounded-md text-xs font-semibold text-white inline-flex items-center gap-1.5 shadow-sm hover:shadow transition"
                style={{ background: primaryAction.event_type?.color || primaryAction.to_state?.color || '#16A34A' }}
              >
                {(() => {
                  const Icon = resolveIcon(primaryAction.event_type?.icon)
                  return <Icon className="w-3.5 h-3.5" />
                })()}
                {primaryAction.event_type?.name || primaryAction.label || primaryAction.event_type_slug}
              </button>
            )}
          </div>
        </div>

        {progressSteps.length > 0 && (
          <div className="px-6 pb-3">
            <Stepper states={progressSteps} current={currentWfState} />
          </div>
        )}
      </header>

      {/* ─────────── Main ─────────── */}
      <div className="flex-1 flex overflow-hidden">
        {/* Sidebar */}
        <aside className="w-[320px] shrink-0 border-r border-border bg-card overflow-y-auto">
          <div className="px-5 py-5 space-y-5">
            <PropertyGroup title="Detalles">
              <PropertyRow label="Estado">
                {currentWfState && <StatePill state={currentWfState} small />}
              </PropertyRow>
              <PropertyRow label="Custodio">
                <div className="inline-flex items-center gap-1.5 px-1.5 h-6 rounded -ml-1.5 max-w-full">
                  <span className="h-4 w-4 rounded-full bg-foreground text-background text-[9px] font-semibold inline-flex items-center justify-center shrink-0">
                    {custodianName[0]?.toUpperCase() ?? '?'}
                  </span>
                  <span className="text-xs text-foreground font-medium truncate">{custodianName}</span>
                </div>
              </PropertyRow>
              <PropertyRow label="Producto">
                <span className="text-xs text-foreground/80">{asset.product_type}</span>
              </PropertyRow>
              {weight !== undefined && weight !== null && (
                <PropertyRow label="Cantidad">
                  <span className="text-xs text-foreground font-medium tabular-nums">
                    {nf.format(Number(weight))} {weightUnit}
                  </span>
                </PropertyRow>
              )}
              {batchNumber && (
                <PropertyRow label="Lote">
                  <span className="text-xs text-foreground/80 font-mono tabular-nums">{batchNumber}</span>
                </PropertyRow>
              )}
              <PropertyRow label="Registrada">
                <span className="text-xs text-foreground/80 tabular-nums">{fmtDate(asset.created_at)}</span>
              </PropertyRow>
              <PropertyRow label="Eventos">
                <span className="text-xs text-foreground/80 tabular-nums">{eventsData?.total ?? events.length}</span>
              </PropertyRow>
            </PropertyGroup>

            <PlotOriginGroup plotId={asset.plot_id ?? null} />

            {(moisture !== undefined || fermentation !== undefined || originRegion) && (
              <PropertyGroup title="Calidad">
                {moisture !== undefined && moisture !== null && (
                  <PropertyRow label="Humedad">
                    <span className="text-xs text-foreground font-medium tabular-nums">{moisture}%</span>
                  </PropertyRow>
                )}
                {fermentation !== undefined && fermentation !== null && (
                  <PropertyRow label="Fermentación">
                    <span className="text-xs text-foreground/80 tabular-nums">{fermentation} días</span>
                  </PropertyRow>
                )}
                {originRegion && (
                  <PropertyRow label="Región">
                    <span className="text-xs text-foreground/80">{originRegion}</span>
                  </PropertyRow>
                )}
              </PropertyGroup>
            )}

            <ComplianceGroup assetId={id} />

            <PropertyGroup
              title="Blockchain"
              action={{
                label: bcExpanded ? 'Menos' : 'Detalles',
                icon: bcExpanded ? ChevronUp : ChevronDown,
                onClick: () => setBcExpanded(!bcExpanded),
              }}
            >
              <PropertyRow label="Estado">
                <BlockchainStatusBadge status={asset.blockchain_status ?? 'SKIPPED'} />
              </PropertyRow>
              {asset.last_event_hash && (
                <PropertyRow label="Hash">
                  <CopyChip value={asset.last_event_hash} />
                </PropertyRow>
              )}
              {bcExpanded && (
                <div className="space-y-1.5 pt-1.5 mt-1.5 border-t border-border">
                  {isSimulated(asset.asset_mint) ? (
                    <p className="text-[11px] text-amber-600 flex items-center gap-1.5">
                      <FlaskConical className="w-3 h-3" />
                      Modo simulación — sin registro real en blockchain
                    </p>
                  ) : (
                    <>
                      {asset.blockchain_tx_signature && (
                        <ExplorerLink
                          href={explorerTxUrl(asset.blockchain_tx_signature, solanaCluster)}
                          label="Solana Explorer (tx)"
                        />
                      )}
                      {asset.blockchain_asset_id && (
                        <ExplorerLink
                          href={xrayAssetUrl(asset.blockchain_asset_id, solanaCluster)}
                          label="XRAY (NFT preview)"
                        />
                      )}
                      {!asset.blockchain_tx_signature && !asset.blockchain_asset_id && (
                        <ExplorerLink
                          href={explorerAddressUrl(asset.asset_mint, solanaCluster)}
                          label="Solana Explorer (cuenta)"
                        />
                      )}
                    </>
                  )}
                  <p className="text-[10px] text-muted-foreground leading-relaxed pt-1">
                    Cada evento genera un hash criptográfico encadenado al anterior. Esto garantiza que la historia no puede ser alterada.
                  </p>
                </div>
              )}
            </PropertyGroup>

            <details
              className="group"
              open={nftExpanded}
              onToggle={e => setNftExpanded((e.currentTarget as HTMLDetailsElement).open)}
            >
              <summary className="text-[10.5px] font-semibold uppercase tracking-wider text-muted-foreground cursor-pointer hover:text-foreground inline-flex items-center gap-1 list-none">
                <ChevronRight className="w-3 h-3 transition-transform group-open:rotate-90" />
                Atributos NFT
              </summary>
              <div className="mt-2 grid grid-cols-2 gap-1.5">
                <NftAttribute label="Mint" value={shortPubkey(asset.asset_mint, 6)} mono />
                {asset.blockchain_asset_id && (
                  <NftAttribute label="Asset ID" value={shortPubkey(asset.blockchain_asset_id, 6)} mono />
                )}
                <NftAttribute label="Tipo" value={asset.product_type} />
                {batchNumber && <NftAttribute label="Lote" value={batchNumber} />}
                {Object.entries(meta)
                  .filter(([k]) => !['name', 'description', 'image_url', 'symbol', 'external_url', 'human_id', 'batch_number', 'lot_number', 'weight', 'weightUnit', 'peso_total_kg', 'moisture_pct', 'fermentation_days', 'origin_region'].includes(k))
                  .slice(0, 6)
                  .map(([k, v]) => (
                    <NftAttribute key={k} label={k.replace(/_/g, ' ')} value={String(v)} />
                  ))}
              </div>
            </details>

            {isInactive && (
              <div className="pt-3 border-t border-border">
                {!showDeleteConfirm ? (
                  <button
                    onClick={() => setShowDeleteConfirm(true)}
                    className="w-full h-8 rounded-md text-xs font-medium text-red-600 hover:bg-red-50 inline-flex items-center justify-center gap-1.5"
                  >
                    <Trash2 className="w-3.5 h-3.5" /> Eliminar carga
                  </button>
                ) : (
                  <div className="space-y-2">
                    <p className="text-[11px] text-muted-foreground">
                      Esta acción es irreversible. Se eliminará la carga y todos sus eventos.
                    </p>
                    <div className="flex gap-1.5">
                      <button
                        onClick={() => setShowDeleteConfirm(false)}
                        className="flex-1 h-7 rounded text-[11px] font-medium text-muted-foreground hover:bg-muted"
                      >
                        Cancelar
                      </button>
                      <button
                        disabled={deleteAsset.isPending}
                        onClick={async () => {
                          const adminKey = useSettingsStore.getState().adminKey || ''
                          try {
                            await deleteAsset.mutateAsync({ id: asset.id, adminKey })
                            toast.success('Carga eliminada')
                            navigate('/assets')
                          } catch (e) {
                            toast.error(e instanceof Error ? e.message : 'Error al eliminar')
                          }
                        }}
                        className="flex-1 h-7 rounded text-[11px] font-semibold text-white bg-red-600 hover:bg-red-700 disabled:opacity-50"
                      >
                        {deleteAsset.isPending ? 'Eliminando…' : 'Confirmar'}
                      </button>
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        </aside>

        {/* Main column */}
        <main className="flex-1 min-w-0 flex flex-col">
          <div className="px-8 py-4 flex items-center justify-between border-b border-border bg-card">
            <div className="flex items-center gap-3">
              <h2 className="text-sm font-semibold text-foreground">Actividad</h2>
              <span className="text-[11px] text-muted-foreground tabular-nums">
                {events.length} {events.length === 1 ? 'evento' : 'eventos'}
              </span>
            </div>
            <div className="flex items-center gap-1">
              <FilterChip active={filter === 'all'} onClick={() => setFilter('all')}>Todos</FilterChip>
              <FilterChip active={filter === 'movement'} onClick={() => setFilter('movement')}>Movimientos</FilterChip>
              <FilterChip active={filter === 'quality'} onClick={() => setFilter('quality')}>Calidad</FilterChip>
              <FilterChip active={filter === 'system'} onClick={() => setFilter('system')}>Sistema</FilterChip>
            </div>
          </div>

          <div className="flex-1 overflow-y-auto px-8 py-6 bg-muted/20">
            <div className="max-w-3xl">
              {eventsLoading ? (
                <div className="flex justify-center py-10"><Spinner /></div>
              ) : filteredEvents.length === 0 ? (
                <div className="rounded-xl border border-dashed border-border px-6 py-10 bg-card text-center">
                  <p className="text-sm text-foreground/80 font-medium">Sin eventos</p>
                  <p className="text-xs text-muted-foreground mt-1">
                    {filter === 'all'
                      ? 'Los eventos aparecerán aquí cuando se registren cambios de custodia, llegadas, inspecciones u otros movimientos.'
                      : 'Cambia el filtro para ver otros tipos de evento.'}
                  </p>
                </div>
              ) : (
                movementGroups.map((group, gi) => (
                  <div key={gi} className="mb-7 last:mb-2">
                    <div className="flex items-center gap-3 mb-3 sticky top-0 bg-muted/95 backdrop-blur-sm py-1 -mx-2 px-2 z-10">
                      <span className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                        {fmtDateLong(group.date)}
                      </span>
                      <span className="text-[10px] text-muted-foreground/70 tabular-nums">
                        {new Date(group.date).toLocaleDateString('es-CO', { day: '2-digit', month: 'short', year: 'numeric' })}
                      </span>
                      <div className="h-px bg-border flex-1" />
                    </div>
                    <div className="relative">
                      <div className="absolute left-[15px] top-0 bottom-0 w-px bg-border" />
                      {group.movements.map(m => (
                        <MovementBlock
                          key={m.primary.id}
                          movement={m}
                          walletMap={walletMap}
                          solanaCluster={solanaCluster}
                        />
                      ))}
                    </div>
                  </div>
                ))
              )}

              <div className="relative pl-10 pb-1 mt-2">
                <div className="absolute left-0 top-0 h-7 w-7 rounded-full bg-card border-2 border-border grid place-items-center">
                  <Flag className="w-3 h-3 text-muted-foreground" />
                </div>
                <p className="text-[11px] uppercase tracking-wider text-muted-foreground font-semibold">Inicio del registro</p>
                <p className="text-xs text-muted-foreground mt-0.5">
                  Esta carga fue registrada el {new Date(asset.created_at).toLocaleDateString('es-CO', { day: '2-digit', month: 'long', year: 'numeric' })}.
                </p>
              </div>
            </div>
          </div>

          {!isInactive && (
            <div className="border-t border-border bg-card">
              <ComposerBar
                actions={availableActions ?? []}
                open={actionPickerOpen}
                setOpen={setActionPickerOpen}
                onPick={action => {
                  setActionPickerOpen(false)
                  setActiveAction(action)
                }}
              />
            </div>
          )}
        </main>
      </div>

      {/* Image modal */}
      {imageOpen && (
        <div
          className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm grid place-items-center p-6"
          onClick={() => setImageOpen(false)}
        >
          <div
            className="bg-card rounded-2xl max-w-2xl w-full overflow-hidden"
            onClick={e => e.stopPropagation()}
          >
            <div className="px-6 py-3 border-b border-border flex items-center justify-between">
              <div>
                <p className="text-sm font-semibold">{cargoName}</p>
                <p className="text-[11px] text-muted-foreground font-mono tabular-nums mt-0.5">
                  NFT · {shortPubkey(asset.asset_mint, 6)}
                </p>
              </div>
              <button
                onClick={() => setImageOpen(false)}
                className="h-8 w-8 rounded inline-flex items-center justify-center hover:bg-muted"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
            <div
              className="aspect-square w-full grid place-items-center"
              style={{ background: 'linear-gradient(135deg,#16A34A 0%, #0EA5E9 100%)' }}
            >
              <Package className="w-32 h-32 text-white/80" strokeWidth={1.5} />
            </div>
            <div className="p-6 grid grid-cols-2 gap-2">
              <NftAttribute label="Mint" value={asset.asset_mint} mono />
              {asset.blockchain_asset_id && (
                <NftAttribute label="Asset ID" value={asset.blockchain_asset_id} mono />
              )}
              <NftAttribute label="Producto" value={asset.product_type} />
              {batchNumber && <NftAttribute label="Lote" value={batchNumber} />}
              {weight !== undefined && weight !== null && (
                <NftAttribute label="Cantidad" value={`${nf.format(Number(weight))} ${weightUnit}`} />
              )}
            </div>
          </div>
        </div>
      )}

      {asset && activeAction && (
        <WorkflowEventModal
          asset={asset}
          action={activeAction}
          open={true}
          onClose={() => setActiveAction(null)}
        />
      )}
    </div>
  )
}

// ────────────────────────────────────────────────────────────────────────────
// Subcomponents
// ────────────────────────────────────────────────────────────────────────────

function StatePill({ state, small }: { state: WorkflowState; small?: boolean }) {
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 rounded-full font-medium',
        small ? 'h-5 px-2 text-[10.5px]' : 'h-6 px-2.5 text-xs',
      )}
      style={{ background: state.color + '1A', color: state.color }}
    >
      <span className="h-1.5 w-1.5 rounded-full" style={{ background: state.color }} />
      {state.label}
    </span>
  )
}

function BlockchainBadgeMini({ status }: { status: BlockchainStatus | string }) {
  const map: Record<string, { label: string; Icon: typeof ShieldCheck }> = {
    CONFIRMED: { label: 'Anclado',    Icon: ShieldCheck },
    PENDING:   { label: 'Anclando',   Icon: Clock },
    FAILED:    { label: 'Fallo',      Icon: ShieldAlert },
    SIMULATED: { label: 'Simulado',   Icon: FlaskConical },
    SKIPPED:   { label: 'Sin anclar', Icon: ShieldOff },
  }
  const m = map[status] ?? map.PENDING
  const { Icon } = m
  return (
    <span className="inline-flex items-center gap-1 h-5 px-1.5 text-[10.5px] font-medium rounded text-foreground/80 bg-muted">
      <Icon className="w-3 h-3" />
      {m.label}
    </span>
  )
}

function BlockchainStatusBadge({ status }: { status: BlockchainStatus | string }) {
  const map: Record<string, { label: string; bg: string; fg: string; Icon: typeof ShieldCheck }> = {
    CONFIRMED: { label: 'Anclado',    bg: 'bg-emerald-50',  fg: 'text-emerald-700', Icon: ShieldCheck },
    PENDING:   { label: 'Anclando',   bg: 'bg-amber-50',    fg: 'text-amber-700',   Icon: Clock },
    FAILED:    { label: 'Fallo',      bg: 'bg-red-50',      fg: 'text-red-700',     Icon: ShieldAlert },
    SIMULATED: { label: 'Simulado',   bg: 'bg-violet-50',   fg: 'text-violet-700',  Icon: FlaskConical },
    SKIPPED:   { label: 'Sin anclar', bg: 'bg-muted',       fg: 'text-muted-foreground', Icon: ShieldOff },
  }
  const m = map[status] ?? map.SKIPPED
  const { Icon } = m
  return (
    <span className={cn('inline-flex items-center gap-1 px-1.5 h-5 rounded text-[10px] font-semibold', m.bg, m.fg)}>
      <Icon className="w-3 h-3" /> {m.label}
    </span>
  )
}

function IconBtn({
  icon: Icon, onClick, title, disabled, spinning,
}: {
  icon: typeof RefreshCw
  onClick?: () => void
  title: string
  disabled?: boolean
  spinning?: boolean
}) {
  return (
    <button
      onClick={onClick}
      title={title}
      disabled={disabled}
      className="h-8 w-8 rounded-md inline-flex items-center justify-center text-muted-foreground hover:bg-muted hover:text-foreground disabled:opacity-40 disabled:cursor-not-allowed"
    >
      <Icon className={cn('w-4 h-4', spinning && 'animate-spin')} />
    </button>
  )
}

function Stepper({ states, current }: { states: WorkflowState[]; current?: WorkflowState }) {
  // Caso A: el estado actual está en el happy path → marcamos como active.
  // Caso B: el estado actual es un desvío (damaged, qc_failed, etc.) → mostramos
  // como done todos los pasos con sort_order ≤ al actual, sin "active" en el stepper
  // (la pill del header sigue mostrando el estado real).
  const idx = current ? states.findIndex(s => s.slug === current.slug) : -1
  const offTrack = idx === -1 && !!current
  const lastDone = offTrack
    ? states.reduce((acc, s, i) => (s.sort_order <= current!.sort_order ? i : acc), -1)
    : -1

  return (
    <div className="flex items-center gap-1">
      {states.map((s, i) => {
        const done = idx >= 0 ? i < idx : i <= lastDone
        const active = idx >= 0 && i === idx
        const StepIcon = resolveIcon(s.icon)
        return (
          <div key={s.slug} className="contents">
            <div className={cn('flex items-center gap-1.5', !done && !active && 'opacity-50')}>
              <span
                className="h-6 w-6 rounded-full grid place-items-center shrink-0"
                style={{
                  background: done ? '#16A34A' : active ? s.color : '#E2E8F0',
                  color: done || active ? '#fff' : '#64748B',
                }}
              >
                {done
                  ? <Check className="h-3.5 w-3.5" strokeWidth={3} />
                  : <StepIcon className="h-3.5 w-3.5" />}
              </span>
              <span className={cn(
                'text-[11.5px] font-medium whitespace-nowrap',
                active ? 'text-foreground' : 'text-muted-foreground',
              )}>
                {s.label}
              </span>
            </div>
            {i < states.length - 1 && (
              <div
                className="flex-1 h-px mx-1.5 min-w-4"
                style={{ background: (idx >= 0 ? i < idx : i < lastDone) ? '#16A34A' : '#E2E8F0' }}
              />
            )}
          </div>
        )
      })}
      {offTrack && (
        <span
          className="ml-2 inline-flex items-center gap-1.5 h-6 px-2 rounded-full text-[10.5px] font-medium"
          style={{ background: current!.color + '1A', color: current!.color }}
          title="Estado fuera del flujo lineal"
        >
          <span className="h-1.5 w-1.5 rounded-full" style={{ background: current!.color }} />
          {current!.label}
        </span>
      )}
    </div>
  )
}

function PropertyGroup({
  title, action, children,
}: {
  title: string
  action?: { label: string; icon: typeof ChevronDown; onClick?: () => void; href?: string }
  children: React.ReactNode
}) {
  return (
    <div>
      <div className="flex items-center justify-between mb-2">
        <h3 className="text-[10.5px] font-semibold uppercase tracking-wider text-muted-foreground">{title}</h3>
        {action && (
          action.href ? (
            <Link to={action.href} className="text-[10.5px] text-muted-foreground hover:text-foreground inline-flex items-center gap-0.5">
              {action.label} <action.icon className="w-2.5 h-2.5" />
            </Link>
          ) : (
            <button onClick={action.onClick} className="text-[10.5px] text-muted-foreground hover:text-foreground inline-flex items-center gap-0.5">
              {action.label} <action.icon className="w-2.5 h-2.5" />
            </button>
          )
        )}
      </div>
      <div className="space-y-0.5">{children}</div>
    </div>
  )
}

function PropertyRow({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between py-1 min-h-[26px]">
      <span className="text-xs text-muted-foreground">{label}</span>
      <div className="text-right max-w-[60%]">{children}</div>
    </div>
  )
}

function CopyChip({ value }: { value: string }) {
  const [copied, setCopied] = useState(false)
  const display = value.length > 12 ? `${value.slice(0, 6)}…${value.slice(-4)}` : value
  return (
    <button
      onClick={() => {
        navigator.clipboard?.writeText(value).then(() => {
          setCopied(true)
          setTimeout(() => setCopied(false), 1200)
        })
      }}
      className="text-[11px] text-foreground/80 font-mono tabular-nums bg-muted px-1.5 h-5 rounded inline-flex items-center gap-1 hover:bg-muted/70"
      title={value}
    >
      {display}
      <Copy className={cn('w-2.5 h-2.5', copied ? 'text-emerald-600' : 'text-muted-foreground')} />
    </button>
  )
}

function ExplorerLink({ href, label }: { href: string; label: string }) {
  return (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      className="flex items-center justify-between py-1 px-1 -mx-1 rounded hover:bg-muted text-[11px] text-foreground/80"
    >
      <span className="inline-flex items-center gap-1.5">
        <ExternalLink className="w-3 h-3" />
        {label}
      </span>
      <ArrowUpRight className="w-3 h-3 text-muted-foreground" />
    </a>
  )
}

function NftAttribute({ label, value, mono }: { label: string; value: string; mono?: boolean }) {
  return (
    <div className="rounded bg-muted border border-border px-2 py-1.5 min-w-0">
      <p className="text-[9.5px] text-muted-foreground uppercase font-semibold tracking-wider">{label}</p>
      <p className={cn('text-[11px] text-foreground truncate mt-0.5', mono && 'font-mono tabular-nums')} title={value}>{value}</p>
    </div>
  )
}

function FilterChip({ active, onClick, children }: { active?: boolean; onClick: () => void; children: React.ReactNode }) {
  return (
    <button
      onClick={onClick}
      className={cn(
        'h-7 px-2.5 rounded text-[11.5px] font-medium transition',
        active ? 'bg-foreground text-background' : 'text-muted-foreground hover:bg-muted',
      )}
    >
      {children}
    </button>
  )
}

// ────────────────────────────────────────────────────────────────────────────
// Plot origin (uses real usePlot hook)
// ────────────────────────────────────────────────────────────────────────────

function PlotOriginGroup({ plotId }: { plotId: string | null }) {
  const { data: plot } = usePlot(plotId ?? '')

  if (!plotId) {
    return (
      <PropertyGroup title="Origen" action={{ label: 'Vincular', icon: Plus, href: '/cumplimiento/parcelas' }}>
        <p className="text-[11px] text-muted-foreground py-1">Sin parcela origen vinculada.</p>
      </PropertyGroup>
    )
  }

  if (!plot) {
    return (
      <PropertyGroup title="Origen">
        <p className="text-[11px] text-muted-foreground py-1">Cargando…</p>
      </PropertyGroup>
    )
  }

  return (
    <PropertyGroup
      title="Origen"
      action={{ label: 'Ver parcela', icon: ExternalLink, href: `/cumplimiento/parcelas/${plotId}` }}
    >
      <div className="flex items-start gap-2.5 -mx-1 px-1 py-1.5 rounded hover:bg-muted/50">
        <div className="h-9 w-9 rounded-md bg-emerald-50 border border-emerald-200 grid place-items-center shrink-0">
          <MapPin className="w-4 h-4 text-emerald-700" />
        </div>
        <div className="min-w-0 flex-1">
          <p className="text-xs font-medium text-foreground">
            {plot.plot_code}{plot.vereda ? ` · ${plot.vereda}` : ''}
          </p>
          {(plot.municipality || plot.department) && (
            <p className="text-[11px] text-muted-foreground mt-0.5">
              {[plot.municipality, plot.department].filter(Boolean).join(', ')}
            </p>
          )}
          {plot.lat != null && plot.lng != null && (
            <p className="text-[10px] text-muted-foreground/80 mt-0.5 font-mono tabular-nums">
              {Number(plot.lat).toFixed(5)}, {Number(plot.lng).toFixed(5)}
              {plot.area_ha != null && ` · ${plot.area_ha} ha`}
            </p>
          )}
        </div>
      </div>
    </PropertyGroup>
  )
}

// ────────────────────────────────────────────────────────────────────────────
// Compliance group (uses real useAssetCompliance hook)
// ────────────────────────────────────────────────────────────────────────────

const COMPLIANCE_STATUS_LABELS: Record<string, string> = {
  incomplete: 'Incompleto', ready: 'Listo', declared: 'Declarado',
  compliant: 'Cumple', non_compliant: 'No cumple', partial: 'Parcial',
}
const COMPLIANCE_STATUS_BG: Record<string, string> = {
  incomplete: 'bg-amber-50 text-amber-700',
  ready: 'bg-emerald-50 text-emerald-700',
  declared: 'bg-blue-50 text-blue-700',
  compliant: 'bg-green-50 text-green-700',
  non_compliant: 'bg-red-50 text-red-700',
  partial: 'bg-orange-50 text-orange-700',
}
const FRAMEWORK_FLAGS: Record<string, string> = {
  eudr: '🇪🇺', 'usda-organic': '🇺🇸', fsma_204: '🇺🇸', fssai: '🇮🇳', 'jfs-2200': '🇯🇵',
}

function ComplianceGroup({ assetId }: { assetId: string }) {
  const isModuleActive = useIsModuleActive('compliance')
  const { data: records = [] } = useAssetCompliance(assetId)
  const { data: activations = [] } = useActivations()
  const { data: frameworks = [] } = useFrameworks()

  if (!isModuleActive) {
    return (
      <PropertyGroup title="Cumplimiento">
        <Link
          to="/marketplace"
          className="block w-full mt-1 h-7 px-2 rounded text-[11px] font-medium text-emerald-700 bg-emerald-50 hover:bg-emerald-100 inline-flex items-center justify-center gap-1"
        >
          <ShieldCheck className="w-3 h-3" /> Activar módulo
        </Link>
      </PropertyGroup>
    )
  }

  // Frameworks activados a nivel tenant (los que aplican).
  const activeFrameworkSlugs = activations.filter(a => a.is_active).map(a => a.framework_slug)
  const recordsBySlug = new Map(records.map(r => [r.framework_slug, r]))

  // Frameworks vigentes que aún no tienen record para esta carga.
  const unlinkedSlugs = activeFrameworkSlugs.filter(slug => !recordsBySlug.has(slug))

  if (records.length === 0 && unlinkedSlugs.length === 0) {
    return (
      <PropertyGroup title="Cumplimiento">
        <p className="text-[11px] text-muted-foreground py-1">
          No hay normas activas en tu tenant. <Link to="/cumplimiento/normativas" className="text-emerald-700 hover:underline">Activar una</Link>.
        </p>
      </PropertyGroup>
    )
  }

  return (
    <PropertyGroup title="Cumplimiento">
      {records.map(r => (
        <ComplianceRow key={r.id} record={r} />
      ))}
      {unlinkedSlugs.map(slug => {
        const fw = frameworks.find(f => f.slug === slug)
        return (
          <UnlinkedFrameworkRow
            key={slug}
            slug={slug}
            label={fw?.name || slug.toUpperCase()}
            assetId={assetId}
          />
        )
      })}
    </PropertyGroup>
  )
}

function UnlinkedFrameworkRow({
  slug, label, assetId,
}: {
  slug: string
  label: string
  assetId: string
}) {
  return (
    <div className="py-1 px-1 -mx-1 rounded hover:bg-muted/50">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2 min-w-0">
          <span className="text-[14px]">{FRAMEWORK_FLAGS[slug] ?? '🌐'}</span>
          <span className="text-xs font-medium text-foreground truncate">{label}</span>
        </div>
        <span className="inline-flex items-center px-1.5 h-5 rounded text-[10px] font-medium bg-muted text-muted-foreground border border-border">
          Sin vincular
        </span>
      </div>
      <Link
        to={`/cumplimiento/registros?create=${assetId}&framework=${encodeURIComponent(slug)}`}
        className="mt-1.5 w-full h-7 px-2 rounded text-[11px] font-medium text-emerald-700 bg-emerald-50 hover:bg-emerald-100 inline-flex items-center justify-center gap-1"
      >
        <Plus className="w-3 h-3" /> Vincular a esta carga
      </Link>
    </div>
  )
}

function ComplianceRow({ record: r }: { record: { id: string; framework_slug: string; compliance_status: string } }) {
  const navigate = useNavigate()
  const toast = useToast()
  const { data: cert } = useRecordCertificate(r.id)
  const generate = useGenerateCertificate(r.id)
  const complianceUrl = import.meta.env.VITE_API_URL ?? 'http://localhost:9000'
  const canGenerate = ['ready', 'declared', 'compliant'].includes(r.compliance_status)
  const statusClass = COMPLIANCE_STATUS_BG[r.compliance_status] ?? 'bg-muted text-muted-foreground'

  async function tryDownload(certId: string, certNumber: string): Promise<{ ok: true } | { ok: false; status: number; detail: string }> {
    const res = await authFetch(`${complianceUrl}/api/v1/compliance/certificates/${certId}/download`)
    if (!res.ok) {
      const txt = await res.text().catch(() => '')
      return { ok: false, status: res.status, detail: txt.slice(0, 200) }
    }
    const blob = await res.blob()
    if (blob.size === 0) {
      return { ok: false, status: 0, detail: 'PDF vacío' }
    }
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${certNumber}.pdf`
    a.click()
    URL.revokeObjectURL(url)
    return { ok: true }
  }

  async function handleDownload() {
    if (!cert) return
    try {
      const first = await tryDownload(cert.id, cert.certificate_number)
      if (first.ok) return

      const isMissingPdf = first.status === 404 && /PDF (file )?not /i.test(first.detail)
      if (!isMissingPdf) {
        toast.error(`No se pudo descargar (${first.status}): ${first.detail || 'sin detalle'}`)
        return
      }

      // PDF perdido en disco — regenerar y reintentar.
      const regenRes = await authFetch(
        `${complianceUrl}/api/v1/compliance/certificates/${cert.id}/regenerate`,
        { method: 'POST' },
      )
      if (!regenRes.ok) {
        const txt = await regenRes.text().catch(() => '')
        toast.error(`No se pudo regenerar (${regenRes.status}): ${txt.slice(0, 200) || 'sin detalle'}`)
        return
      }
      const newCert = await regenRes.json() as { id: string; certificate_number: string }
      const second = await tryDownload(newCert.id, newCert.certificate_number)
      if (second.ok) {
        toast.success('PDF regenerado y descargado')
      } else {
        toast.error(`Regenerado pero no descarga (${second.status}): ${second.detail}`)
      }
    } catch (e) {
      toast.error(`Error de red: ${e instanceof Error ? e.message : String(e)}`)
    }
  }

  async function handleGenerate() {
    try {
      await generate.mutateAsync()
      toast.success('Certificado generado')
    } catch (e) {
      toast.error(`No se pudo generar: ${e instanceof Error ? e.message : String(e)}`)
    }
  }

  return (
    <div className="py-1 px-1 -mx-1 rounded hover:bg-muted/50">
      <Link to={`/cumplimiento/registros/${r.id}`} className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-[14px]">{FRAMEWORK_FLAGS[r.framework_slug] ?? '🌐'}</span>
          <span className="text-xs font-medium text-foreground">{r.framework_slug.toUpperCase()}</span>
        </div>
        <span className={cn('inline-flex items-center px-1.5 h-5 rounded text-[10px] font-semibold', statusClass)}>
          {COMPLIANCE_STATUS_LABELS[r.compliance_status] ?? r.compliance_status}
        </span>
      </Link>
      <div className="mt-1.5">
        {cert && cert.status === 'active' ? (
          <button
            onClick={handleDownload}
            className="w-full h-7 px-2 rounded text-[11px] font-semibold text-white bg-emerald-600 hover:bg-emerald-700 inline-flex items-center justify-center gap-1"
          >
            <FileDown className="w-3 h-3" /> Descargar certificado
          </button>
        ) : canGenerate ? (
          <button
            onClick={handleGenerate}
            disabled={generate.isPending}
            className="w-full h-7 px-2 rounded text-[11px] font-semibold text-emerald-700 bg-emerald-50 hover:bg-emerald-100 disabled:opacity-50 inline-flex items-center justify-center gap-1"
          >
            {generate.isPending ? 'Generando…' : 'Generar certificado'}
          </button>
        ) : (
          <button
            onClick={() => navigate(`/cumplimiento/registros/${r.id}`)}
            className="w-full h-7 px-2 rounded text-[11px] font-medium text-muted-foreground border border-border hover:bg-muted inline-flex items-center justify-center"
          >
            Completar registro
          </button>
        )}
      </div>
    </div>
  )
}

function CertificateDownloadIcon({ assetId }: { assetId: string }) {
  const { data: records = [] } = useAssetCompliance(assetId)
  const [downloading, setDownloading] = useState(false)
  const toast = useToast()
  const complianceUrl = import.meta.env.VITE_API_URL ?? 'http://localhost:9000'
  const recordWithCert = records.find(r => ['ready', 'declared', 'compliant'].includes(r.compliance_status))
  if (!recordWithCert) return null

  const downloadOrRegenerate = async (certId: string, certNumber: string) => {
    const pdfRes = await authFetch(`${complianceUrl}/api/v1/compliance/certificates/${certId}/download`)
    if (pdfRes.ok) {
      const blob = await pdfRes.blob()
      if (blob.size === 0) {
        toast.error('PDF vacío — el certificado no tiene archivo asociado')
        return
      }
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `${certNumber}.pdf`
      a.click()
      URL.revokeObjectURL(url)
      return
    }
    const txt = await pdfRes.text().catch(() => '')
    const isMissingPdf = pdfRes.status === 404 && /PDF (file )?not /i.test(txt)
    if (!isMissingPdf) {
      toast.error(`No se pudo descargar (${pdfRes.status}): ${txt.slice(0, 200) || 'sin detalle'}`)
      return
    }
    const regen = await authFetch(
      `${complianceUrl}/api/v1/compliance/certificates/${certId}/regenerate`,
      { method: 'POST' },
    )
    if (!regen.ok) {
      const t2 = await regen.text().catch(() => '')
      toast.error(`No se pudo regenerar (${regen.status}): ${t2.slice(0, 200) || 'sin detalle'}`)
      return
    }
    const fresh = await regen.json() as { id: string; certificate_number: string }
    const final = await authFetch(`${complianceUrl}/api/v1/compliance/certificates/${fresh.id}/download`)
    if (!final.ok) {
      toast.error(`Regenerado pero no descarga (${final.status})`)
      return
    }
    const blob = await final.blob()
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${fresh.certificate_number}.pdf`
    a.click()
    URL.revokeObjectURL(url)
    toast.success('PDF regenerado y descargado')
  }

  const onClick = async () => {
    if (downloading) return
    setDownloading(true)
    try {
      const certRes = await authFetch(`${complianceUrl}/api/v1/compliance/records/${recordWithCert.id}/certificate`)
      if (!certRes.ok) {
        if (certRes.status === 404) {
          toast.error('Aún no hay certificado generado. Generalo desde el sidebar.')
        } else {
          const txt = await certRes.text().catch(() => '')
          toast.error(`No se encontró certificado (${certRes.status}): ${txt.slice(0, 120)}`)
        }
        return
      }
      const cert = await certRes.json()
      await downloadOrRegenerate(cert.id, cert.certificate_number)
    } catch (e) {
      toast.error(`Error de red: ${e instanceof Error ? e.message : String(e)}`)
    } finally {
      setDownloading(false)
    }
  }

  return (
    <IconBtn
      icon={ShieldCheck}
      onClick={onClick}
      title="Descargar certificado EUDR"
      disabled={downloading}
    />
  )
}

// ────────────────────────────────────────────────────────────────────────────
// Event item (timeline)
// ────────────────────────────────────────────────────────────────────────────

function MovementBlock({
  movement, walletMap, solanaCluster,
}: {
  movement: Movement
  walletMap: Map<string, { name: string; org?: string }>
  solanaCluster: string
}) {
  const { primary, attached } = movement
  const ts = primary.timestamp || primary.created_at
  const Icon = eventIcon(primary.event_type)
  const color = eventColor(primary.event_type)
  const actor = primary.from_wallet
    ? walletMap.get(primary.from_wallet)?.name ?? shortPubkey(primary.from_wallet, 4)
    : 'Sistema'

  return (
    <div className="relative pl-10 pb-4 last:pb-0 group">
      {/* Primary node */}
      <div
        className="absolute left-2 top-0.5 h-7 w-7 rounded-full grid place-items-center bg-card"
        style={{ border: `2px solid ${color}`, boxShadow: '0 0 0 3px hsl(var(--background))' }}
      >
        <Icon className="w-3.5 h-3.5" style={{ color }} />
      </div>

      <div className="flex items-baseline gap-1.5 flex-wrap">
        <span className="text-[13px] text-foreground">
          <span className="font-semibold">{actor}</span>
          {' · '}
          <span className="text-foreground/70">{eventTypeLabel(primary.event_type)}</span>
        </span>
        <span className="text-[10.5px] text-muted-foreground tabular-nums ml-auto group-hover:text-foreground/70 transition">
          {fmtTime(ts)}
        </span>
      </div>

      <PrimaryDestinationLine event={primary} walletMap={walletMap} />

      {attached.length > 0 && (
        <div className="mt-2 ml-1 pl-3 border-l border-border/70 space-y-1.5">
          {attached.map(ev => (
            <SubEventItem key={ev.id} event={ev} walletMap={walletMap} solanaCluster={solanaCluster} />
          ))}
        </div>
      )}
    </div>
  )
}

function PrimaryDestinationLine({
  event, walletMap,
}: {
  event: CustodyEvent
  walletMap: Map<string, { name: string; org?: string }>
}) {
  // En el header del movimiento solo mostramos info contextual mínima.
  // Todo lo demás (tx, evidencia, notas, ubicación) queda como sub-evento.
  const t = normalizeEventType(event.event_type)
  if (t !== 'handoff' || !event.to_wallet) return null
  const to = walletMap.get(event.to_wallet)?.name ?? shortPubkey(event.to_wallet, 4)
  return (
    <div className="mt-1.5 inline-flex items-center gap-2 text-[11.5px] bg-card border border-border rounded-md px-2 py-1">
      <span className="text-muted-foreground">→</span>
      <span className="h-4 w-4 rounded-full bg-foreground text-background text-[9px] font-semibold inline-flex items-center justify-center">
        {to[0]?.toUpperCase() ?? '?'}
      </span>
      <span className="text-foreground font-medium">{to}</span>
    </div>
  )
}

function SubEventItem({
  event, walletMap, solanaCluster,
}: {
  event: CustodyEvent
  walletMap: Map<string, { name: string; org?: string }>
  solanaCluster: string
}) {
  const ts = event.timestamp || event.created_at
  const Icon = eventIcon(event.event_type)
  const color = eventColor(event.event_type)
  return (
    <div className="flex items-start gap-2">
      <Icon className="w-3 h-3 mt-1 shrink-0" style={{ color }} />
      <div className="flex-1 min-w-0">
        <div className="flex items-baseline gap-1.5">
          <span className="text-[11.5px] text-foreground/80">{eventTypeLabel(event.event_type)}</span>
          <span className="text-[10px] text-muted-foreground tabular-nums ml-auto">{fmtTime(ts)}</span>
        </div>
        <EventBody event={event} walletMap={walletMap} solanaCluster={solanaCluster} />
      </div>
    </div>
  )
}

function EventBody({
  event, walletMap, solanaCluster,
}: {
  event: CustodyEvent
  walletMap: Map<string, { name: string; org?: string }>
  solanaCluster: string
}) {
  const data = event.data ?? {}
  const t = event.event_type

  if (t === 'handoff') {
    const to = event.to_wallet
      ? walletMap.get(event.to_wallet)?.name ?? shortPubkey(event.to_wallet, 4)
      : null
    return (
      <div className="mt-1.5 inline-flex items-center gap-2 text-[11.5px] bg-card border border-border rounded-md px-2 py-1">
        <span className="text-muted-foreground">→</span>
        {to && (
          <>
            <span className="h-4 w-4 rounded-full bg-foreground text-background text-[9px] font-semibold inline-flex items-center justify-center">
              {to[0]?.toUpperCase() ?? '?'}
            </span>
            <span className="text-foreground font-medium">{to}</span>
          </>
        )}
        {event.notes && (
          <>
            <span className="text-muted-foreground/50">|</span>
            <span className="text-foreground/70 italic">{event.notes}</span>
          </>
        )}
      </div>
    )
  }

  if (t === 'qc_passed' || t === 'qc_failed' || t === 'qc') {
    const moisture = data.moisture as string | undefined
    const fermentation = data.fermentation as string | undefined
    const score = data.score as string | undefined
    if (!moisture && !fermentation && !score && !event.notes) return null
    return (
      <div className="mt-1.5 grid grid-cols-3 gap-1.5 max-w-md">
        {moisture && <Mini label="Humedad" value={String(moisture)} good={t === 'qc_passed'} />}
        {fermentation && <Mini label="Fermentación" value={String(fermentation)} />}
        {score && <Mini label="Score" value={String(score)} good={t === 'qc_passed'} />}
        {event.notes && (
          <p className="col-span-3 text-[11px] text-foreground/70 mt-1">{event.notes}</p>
        )}
      </div>
    )
  }

  if (event.evidence_url) {
    return (
      <a
        href={event.evidence_url}
        target="_blank"
        rel="noopener noreferrer"
        className="mt-1.5 inline-flex items-center gap-2 bg-card border border-border rounded-md px-2 py-1.5 hover:border-foreground/30 hover:bg-muted/50"
      >
        <span className="h-7 w-7 rounded bg-muted grid place-items-center">
          <FileText className="w-3.5 h-3.5 text-muted-foreground" />
        </span>
        <span className="text-left">
          <span className="block text-[11.5px] font-medium text-foreground">
            {(event.evidence_type as string | undefined) || 'Evidencia'}
          </span>
          {event.evidence_hash && (
            <span className="block text-[10px] text-muted-foreground tabular-nums font-mono">
              {event.evidence_hash.slice(0, 12)}…
            </span>
          )}
        </span>
        <Download className="w-3 h-3 text-muted-foreground ml-2" />
      </a>
    )
  }

  if (event.notes) {
    return (
      <p className="text-[12px] text-foreground/80 mt-1 leading-relaxed bg-amber-50 border border-amber-100 rounded-md px-2.5 py-1.5 max-w-prose">
        {event.notes}
      </p>
    )
  }

  if (event.solana_tx_sig) {
    return (
      <div className="mt-0.5 inline-flex items-center gap-1.5 text-[10.5px] text-muted-foreground">
        <code className="bg-muted px-1 py-0.5 rounded font-mono tabular-nums text-foreground/80">
          {event.solana_tx_sig.slice(0, 6)}…{event.solana_tx_sig.slice(-4)}
        </code>
        <a
          href={explorerTxUrl(event.solana_tx_sig, solanaCluster)}
          target="_blank"
          rel="noopener noreferrer"
          className="hover:text-foreground inline-flex items-center gap-0.5"
        >
          ver en explorer <ExternalLink className="w-2.5 h-2.5" />
        </a>
      </div>
    )
  }

  if (event.location) {
    const { lat, lng } = event.location
    if (lat != null && lng != null) {
      return (
        <p className="text-[11.5px] text-muted-foreground mt-0.5 font-mono tabular-nums">
          {Number(lat).toFixed(4)}, {Number(lng).toFixed(4)}
        </p>
      )
    }
  }

  return null
}

function Mini({ label, value, good }: { label: string; value: string; good?: boolean }) {
  return (
    <div className={cn(
      'rounded border px-2 py-1',
      good ? 'bg-emerald-50 border-emerald-200' : 'bg-muted border-border',
    )}>
      <p className="text-[9.5px] uppercase font-semibold tracking-wider text-muted-foreground">{label}</p>
      <p className={cn(
        'text-[11.5px] mt-0.5 font-medium tabular-nums',
        good ? 'text-emerald-800' : 'text-foreground',
      )}>{value}</p>
    </div>
  )
}

const eventTypeLabel = (t: string): string => {
  const map: Record<string, string> = {
    handoff: 'cambio de custodia',
    arrived: 'llegada a destino',
    loaded: 'cargada en vehículo',
    released: 'liberación',
    released_admin: 'liberación admin',
    qc_passed: 'QC aprobado',
    qc_failed: 'QC fallido',
    qc: 'inspección de calidad',
    anchored: 'anclado en blockchain',
    created: 'carga registrada',
    minted: 'NFT acuñado',
    note: 'nota interna',
    evidence: 'evidencia adjunta',
    gps_ping: 'ping GPS',
    pickup: 'recogida',
    delivered: 'entregada',
    customs_cleared: 'aduana liberada',
    customs_hold: 'aduana retenida',
    damaged: 'daño reportado',
    consolidated: 'consolidada',
    deconsolidated: 'desconsolidada',
    departed: 'salida',
    gate_in: 'ingreso a gate',
    gate_out: 'salida de gate',
    inspection: 'inspección',
    return: 'devolución',
    sealed: 'sellada',
    unsealed: 'desellada',
    temperature_check: 'control de temperatura',
    burn: 'quemada',
  }
  const k = normalizeEventType(t)
  return map[k] ?? k.replace(/_/g, ' ')
}

const eventIcon = (t: string): LucideIcon => {
  const map: Record<string, LucideIcon> = {
    handoff: UserPlus,
    arrived: PackageCheck,
    loaded: Truck,
    released: CheckCircle2,
    released_admin: ShieldOff,
    qc_passed: FlaskConical,
    qc_failed: ShieldAlert,
    qc: FlaskConical,
    anchored: Anchor,
    created: Package,
    minted: Sparkles,
    note: MessageSquare,
    evidence: Paperclip,
    gps_ping: MapPin,
    pickup: PackageCheck,
    delivered: CheckCircle2,
    customs_cleared: ShieldCheck,
    customs_hold: ShieldAlert,
    damaged: ShieldAlert,
    inspection: FlaskConical,
  }
  return map[normalizeEventType(t)] ?? Circle
}

const eventColor = (t: string): string => {
  const map: Record<string, string> = {
    handoff: '#0EA5E9',
    arrived: '#7C3AED',
    loaded: '#0EA5E9',
    released: '#15803D',
    released_admin: '#DC2626',
    qc_passed: '#16A34A',
    qc_failed: '#DC2626',
    qc: '#16A34A',
    anchored: '#7C3AED',
    created: '#64748B',
    minted: '#7C3AED',
    note: '#94A3B8',
    evidence: '#94A3B8',
    gps_ping: '#94A3B8',
    pickup: '#0EA5E9',
    delivered: '#15803D',
    customs_cleared: '#16A34A',
    customs_hold: '#F97316',
    damaged: '#DC2626',
    inspection: '#16A34A',
  }
  return map[normalizeEventType(t)] ?? '#64748B'
}

// ────────────────────────────────────────────────────────────────────────────
// Composer (sticky bottom)
// ────────────────────────────────────────────────────────────────────────────

function ComposerBar({
  actions, open, setOpen, onPick,
}: {
  actions: AvailableAction[]
  open: boolean
  setOpen: (v: boolean) => void
  onPick: (action: AvailableAction) => void
}) {
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!open) return
    const fn = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false)
    }
    document.addEventListener('mousedown', fn)
    return () => document.removeEventListener('mousedown', fn)
  }, [open, setOpen])

  // Movimientos: la transición lleva a un estado del happy path.
  // Eventos: marcas/incidentes (qc, damaged, customs_hold, notas, evidencias)
  // o acciones meramente informacionales que no cambian la posición física.
  const isMovement = (a: AvailableAction): boolean => {
    if (a.event_type?.is_informational) return false
    if (a.to_state && MOVEMENT_STATE_SLUGS.has(a.to_state.slug)) return true
    if (a.to_state?.is_terminal) return false
    return false
  }

  const movements = actions.filter(isMovement)
  const events = actions.filter(a => !isMovement(a))

  if (actions.length === 0) {
    return (
      <div className="px-8 py-3 text-xs text-muted-foreground">
        No hay acciones disponibles desde el estado actual.
      </div>
    )
  }

  return (
    <div className="px-8 py-3 flex items-center gap-2 relative" ref={ref}>
      <button
        onClick={() => setOpen(!open)}
        className="flex-1 h-9 rounded-md border border-border bg-muted/50 hover:bg-card hover:border-foreground/30 text-left px-3 text-xs text-muted-foreground inline-flex items-center gap-2 transition"
      >
        <Plus className="w-3.5 h-3.5" />
        Registrar un evento sobre esta carga…
      </button>

      {open && (
        <div className="absolute bottom-full mb-2 left-8 right-8 z-30 rounded-lg overflow-hidden bg-card border border-border shadow-xl py-1 max-h-[60vh] overflow-y-auto">
          {movements.length > 0 && (
            <ActionGroup
              label="Movimientos"
              hint="Cambia la posesión o ubicación física de la carga"
              actions={movements}
              onPick={onPick}
            />
          )}
          {movements.length > 0 && events.length > 0 && (
            <div className="my-1 border-t border-border" />
          )}
          {events.length > 0 && (
            <ActionGroup
              label="Eventos"
              hint="Marca incidentes, calidad, evidencias y notas — no mueve la carga"
              actions={events}
              onPick={onPick}
            />
          )}
        </div>
      )}
    </div>
  )
}

function ActionGroup({
  label, hint, actions, onPick,
}: {
  label: string
  hint: string
  actions: AvailableAction[]
  onPick: (action: AvailableAction) => void
}) {
  return (
    <div className="py-1">
      <div className="px-3 pt-1 pb-1.5">
        <p className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">{label}</p>
        <p className="text-[10.5px] text-muted-foreground/70 mt-0.5">{hint}</p>
      </div>
      {actions.map(a => {
        const Icon = resolveIcon(a.event_type?.icon)
        const color = a.event_type?.color || a.to_state?.color || '#64748B'
        const isTerminal = a.to_state?.is_terminal
        return (
          <button
            key={a.transition_id || a.event_type_slug}
            onClick={() => onPick(a)}
            className="w-full px-3 h-10 inline-flex items-center gap-2.5 hover:bg-muted text-left"
          >
            <span
              className="h-6 w-6 rounded grid place-items-center shrink-0"
              style={{ background: color + '1A' }}
            >
              <Icon className="w-3.5 h-3.5" style={{ color }} />
            </span>
            <span className="flex-1 min-w-0">
              <span className="block text-[12.5px] font-medium text-foreground truncate">
                {a.event_type?.name || a.label || a.event_type_slug}
              </span>
              {a.to_state && (
                <span className="block text-[10.5px] text-muted-foreground truncate">
                  {isTerminal ? 'Cierra el flujo' : `→ ${a.to_state.label}`}
                </span>
              )}
            </span>
            {a.event_type?.requires_admin && (
              <span className="text-[10px] font-semibold text-red-600">admin</span>
            )}
          </button>
        )
      })}
    </div>
  )
}
