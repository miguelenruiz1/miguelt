import { useState, useMemo } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import {
  ArrowLeft, Package, RefreshCw, ShieldOff, MapPin, Zap,
  CheckCircle2, ExternalLink, Link2, XCircle, FlaskConical, FileDown,
  ShieldCheck, Clock, ChevronDown, ChevronUp, User, Hash,
  Anchor,
} from 'lucide-react'
import { useSettingsStore, explorerAddressUrl, explorerTxUrl, xrayAssetUrl } from '@/store/settings'
import type { BlockchainStatus, AvailableAction } from '@/types/api'

const isSimulated = (s: string) => s.startsWith('sim') || s.startsWith('SIM_')
import { useAsset, useAssetEvents } from '@/hooks/useAssets'
import { useWalletList } from '@/hooks/useWallets'
import { useWorkflowStates, useWorkflowEventTypes, useAvailableActions } from '@/hooks/useWorkflow'
import { Topbar } from '@/components/layout/Topbar'
import { Button } from '@/components/ui/button'
import { StateBadge } from '@/components/domain-badges'
import { HashChip, Spinner, Card, EmptyState } from '@/components/ui/Misc'
import { EventTimeline } from '@/components/events/EventTimeline'
import { WorkflowEventModal } from '@/components/events/WorkflowEventModal'
import { fmtDate, shortPubkey } from '@/lib/utils'
import { useAssetCompliance, useRecordCertificate, useGenerateCertificate } from '@/hooks/useCompliance'
import { authFetch } from '@/lib/auth-fetch'
import { useIsModuleActive } from '@/hooks/useModules'
import { resolveIcon, colorStyle } from '@/lib/icon-map'

// ─── Page ────────────────────────────────────────────────────────────────────

export function AssetDetailPage() {
  const { id = '' } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [activeAction, setActiveAction] = useState<AvailableAction | null>(null)
  const [showBlockchainDetails, setShowBlockchainDetails] = useState(false)

  const { data: asset, isLoading, refetch, isFetching } = useAsset(id)
  const { data: eventsData, isLoading: eventsLoading } = useAssetEvents(id)
  const { solanaCluster } = useSettingsStore()

  // Workflow data
  const { data: workflowStates } = useWorkflowStates()
  const { data: wfEventTypes } = useWorkflowEventTypes()

  // Resolve current workflow state: try by workflow_state_id first, then by slug
  const currentWfState = workflowStates?.find(s =>
    s.id === asset?.workflow_state_id || s.slug === asset?.state
  )
  const effectiveStateSlug = currentWfState?.slug ?? asset?.state

  const { data: availableActions } = useAvailableActions(effectiveStateSlug)

  // Resolve wallet names
  const { data: walletsData } = useWalletList({ limit: 200 })
  const walletMap = new Map<string, string>()
  if (walletsData?.items) {
    for (const w of walletsData.items) {
      walletMap.set(w.wallet_pubkey, w.name || shortPubkey(w.wallet_pubkey, 4))
    }
  }

  const events = eventsData?.items ?? []

  const isInactive = currentWfState?.is_terminal ?? false

  // Build progress stepper from workflow states (non-terminal, sorted)
  const progressSteps = useMemo(() => {
    if (!workflowStates?.length) return []
    return workflowStates
      .filter(s => !s.is_terminal)
      .sort((a, b) => a.sort_order - b.sort_order)
  }, [workflowStates])

  // Separate actions: regular vs terminal
  const regularActions = useMemo(() =>
    (availableActions ?? []).filter(a =>
      !a.to_state?.is_terminal && !a.event_type?.is_informational
    ), [availableActions])
  const terminalActions = useMemo(() =>
    (availableActions ?? []).filter(a =>
      a.to_state?.is_terminal && !a.event_type?.is_informational
    ), [availableActions])

  if (isLoading) return (
    <div className="flex flex-col flex-1 overflow-hidden">
      <Topbar title="Carga" />
      <div className="flex justify-center py-20"><Spinner /></div>
    </div>
  )

  if (!asset) return (
    <div className="flex flex-col flex-1 overflow-hidden">
      <Topbar title="Carga no encontrada" />
      <EmptyState title="Carga no encontrada" action={<Button onClick={() => navigate('/assets')}>Volver a Cargas</Button>} />
    </div>
  )

  const meta = asset.metadata as Record<string, unknown>
  const cargoName = meta?.name as string | undefined
  const nftImageUrl = (meta?.image_url as string | undefined)
    || `https://api.dicebear.com/9.x/shapes/svg?seed=${asset.id}&backgroundColor=6366f1,3b82f6,22c55e,f59e0b,ef4444`
  const custodianName = walletMap.get(asset.current_custodian_wallet) || shortPubkey(asset.current_custodian_wallet, 4)

  // Progress step: find current state index in non-terminal states
  const currentStepIndex = progressSteps.findIndex(s => s.slug === effectiveStateSlug)
  const progressStep = isInactive
    ? progressSteps.length + 1
    : currentStepIndex >= 0
      ? currentStepIndex + 1
      : 1

  return (
    <div className="flex flex-col flex-1 overflow-hidden">
      <Topbar
        title={cargoName || asset.product_type}
        subtitle={cargoName ? asset.product_type : undefined}
        actions={
          <div className="flex gap-2">
            {events.length > 0 && (
              <CertificateDownloadButton assetId={id} />
            )}
            <Button variant="ghost" size="icon" onClick={() => refetch()} title="Actualizar">
              <RefreshCw className={`h-4 w-4 ${isFetching ? 'animate-spin' : ''}`} />
            </Button>
          </div>
        }
      />

      <div className="flex-1 overflow-y-auto p-6 space-y-6">
        {/* Back */}
        <Link to="/assets" className="inline-flex items-center gap-2 text-sm font-semibold text-slate-500 hover:text-primary transition-colors group">
          <ArrowLeft className="h-4 w-4 transition-transform group-hover:-translate-x-1" />
          Volver a Cargas
        </Link>

        {/* ─── Progress Stepper (workflow-driven) ──────────────────────── */}
        {progressSteps.length > 0 && (
        <Card>
          <div className="flex items-center justify-between gap-2 overflow-x-auto pb-1">
            {progressSteps.map((step, i) => {
              const stepNum = i + 1
              const isActive = stepNum === progressStep
              const isDone = stepNum < progressStep
              const StepIcon = resolveIcon(step.icon)

              return (
                <div key={step.slug} className="flex items-center gap-2 flex-1 min-w-0">
                  <div className="flex flex-col items-center gap-1.5 shrink-0">
                    <div
                      className="flex h-9 w-9 items-center justify-center rounded-full transition-all"
                      style={
                        isDone ? { backgroundColor: '#22c55e', color: '#fff' } :
                        isActive ? { backgroundColor: step.color, color: '#fff', boxShadow: `0 0 0 4px ${step.color}30` } :
                        { backgroundColor: '#f1f5f9', color: '#94a3b8' }
                      }
                    >
                      {isDone ? (
                        <CheckCircle2 className="h-4.5 w-4.5" />
                      ) : (
                        <StepIcon className="h-4 w-4" />
                      )}
                    </div>
                    <span
                      className="text-[10px] font-semibold whitespace-nowrap"
                      style={{
                        color: isDone ? '#16a34a' : isActive ? step.color : '#94a3b8',
                      }}
                    >
                      {step.label}
                    </span>
                  </div>
                  {i < progressSteps.length - 1 && (
                    <div className={[
                      'flex-1 h-0.5 rounded-full min-w-4',
                      isDone ? 'bg-emerald-300' : 'bg-slate-100',
                    ].join(' ')} />
                  )}
                </div>
              )
            })}
          </div>
        </Card>
        )}

        {/* ─── Status Banner (workflow-driven) ──────────────────────── */}
        {isInactive && currentWfState && (
          <div
            className="rounded-2xl border px-5 py-4 flex items-start gap-3"
            style={{ backgroundColor: `${currentWfState.color}10`, borderColor: `${currentWfState.color}30` }}
          >
            {(() => { const I = resolveIcon(currentWfState.icon); return <I className="h-5 w-5 mt-0.5 shrink-0" style={{ color: currentWfState.color }} /> })()}
            <div>
              <p className="text-sm font-bold" style={{ color: currentWfState.color }}>{currentWfState.label}</p>
              <p className="text-xs mt-0.5" style={{ color: `${currentWfState.color}99` }}>
                La cadena de custodia de esta carga ha sido cerrada. No se permiten mas movimientos.
              </p>
            </div>
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* ─── Left column ─────────────────────────────────────────── */}
          <div className="space-y-5">

            {/* Summary card — clean, human-readable */}
            <Card>
              {/* NFT Image */}
              {nftImageUrl && (
                <div className="mb-4 rounded-xl overflow-hidden border border-slate-100">
                  <img
                    src={nftImageUrl}
                    alt={cargoName || asset.product_type}
                    className="w-full h-40 object-cover"
                    onError={(e) => { (e.target as HTMLImageElement).style.display = 'none' }}
                  />
                </div>
              )}

              <div className="flex items-start gap-4 mb-5">
                <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-gradient-to-br from-primary/10 to-primary/5 border border-primary/20 shadow-inner shrink-0">
                  <Package className="h-6 w-6 text-primary drop-shadow-sm" />
                </div>
                <div className="min-w-0 flex-1">
                  {cargoName && (
                    <p className="text-sm font-bold text-slate-900">{cargoName}</p>
                  )}
                  <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider">{asset.product_type}</p>
                </div>
                <StateBadge state={asset.state} />
              </div>

              {/* State description (from workflow label) */}
              {currentWfState && (
                <p className="text-xs text-slate-500 leading-relaxed mb-4 bg-slate-50 rounded-xl px-3 py-2.5 border border-slate-100">
                  Estado actual: <span className="font-semibold" style={{ color: currentWfState.color }}>{currentWfState.label}</span>
                </p>
              )}

              <dl className="space-y-3">
                <InfoRow icon={User} label="Responsable actual">
                  <span className="font-medium text-slate-700 text-xs">{custodianName}</span>
                </InfoRow>
                <InfoRow icon={Hash} label="Eventos registrados">
                  <span className="text-slate-700 text-xs font-medium tabular-nums">{eventsData?.total ?? '0'}</span>
                </InfoRow>
                <InfoRow icon={Clock} label="Registrado">
                  <span className="text-slate-500 text-xs tabular-nums">{fmtDate(asset.created_at)}</span>
                </InfoRow>
                <InfoRow icon={Clock} label="Ultima actualizacion">
                  <span className="text-slate-500 text-xs tabular-nums">{fmtDate(asset.updated_at)}</span>
                </InfoRow>
              </dl>

              {/* Blockchain section — collapsible */}
              <div className="mt-4 pt-4 border-t border-slate-100">
                <button
                  onClick={() => setShowBlockchainDetails(!showBlockchainDetails)}
                  className="flex items-center justify-between w-full text-left"
                >
                  <div className="flex items-center gap-2">
                    <Anchor className="h-3.5 w-3.5 text-slate-400" />
                    <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">Blockchain</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <BlockchainBadge status={asset.blockchain_status ?? 'SKIPPED'} />
                    {showBlockchainDetails ? <ChevronUp className="h-3.5 w-3.5 text-slate-400" /> : <ChevronDown className="h-3.5 w-3.5 text-slate-400" />}
                  </div>
                </button>

                {showBlockchainDetails && (
                  <div className="mt-3 space-y-2 bg-slate-50/80 rounded-xl border border-slate-100 p-3">
                    {isSimulated(asset.asset_mint) ? (
                      <p className="text-xs text-amber-600 flex items-center gap-1.5">
                        <FlaskConical className="h-3.5 w-3.5" />
                        Modo simulacion — sin registro real en blockchain
                      </p>
                    ) : (
                      <div className="flex flex-col gap-1.5">
                        {asset.blockchain_tx_signature && (
                          <a
                            href={explorerTxUrl(asset.blockchain_tx_signature, solanaCluster)}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="inline-flex items-center gap-1.5 text-xs font-semibold text-emerald-600 hover:underline transition-colors"
                          >
                            <ExternalLink className="h-3.5 w-3.5" />
                            Ver transaccion en Solana Explorer
                          </a>
                        )}
                        {asset.blockchain_asset_id && (
                          <a
                            href={xrayAssetUrl(asset.blockchain_asset_id, solanaCluster)}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="inline-flex items-center gap-1.5 text-xs font-semibold text-violet-600 hover:underline transition-colors"
                          >
                            <ExternalLink className="h-3.5 w-3.5" />
                            Ver NFT en XRAY (imagen + metadata)
                          </a>
                        )}
                        {!asset.blockchain_tx_signature && !asset.blockchain_asset_id && (
                          <a
                            href={explorerAddressUrl(asset.asset_mint, solanaCluster)}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="inline-flex items-center gap-1.5 text-xs font-semibold text-primary hover:underline transition-colors"
                          >
                            <ExternalLink className="h-3.5 w-3.5" />
                            Ver cuenta en Solana Explorer
                          </a>
                        )}
                      </div>
                    )}
                    {asset.last_event_hash && (
                      <div className="flex items-center gap-2 text-xs">
                        <span className="text-slate-400 font-medium shrink-0">Ultimo hash:</span>
                        <HashChip hash={asset.last_event_hash} />
                      </div>
                    )}
                    <p className="text-[10px] text-slate-400 leading-relaxed">
                      Cada evento de custodia genera un hash criptografico encadenado al anterior, garantizando que la historia no puede ser alterada.
                    </p>
                  </div>
                )}
              </div>

              {/* NFT Attributes — shown like a real NFT marketplace */}
              {Object.keys(asset.metadata).length > 0 && (
                <div className="mt-4 pt-4 border-t border-slate-100">
                  <p className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-3">Atributos NFT</p>
                  <div className="grid grid-cols-2 gap-2">
                    <NftAttribute label="Tipo de Producto" value={asset.product_type} />
                    {Object.entries(meta).filter(([k]) => !['name', 'description', 'image_url', 'symbol', 'external_url'].includes(k)).map(([key, val]) => (
                      <NftAttribute
                        key={key}
                        label={key.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())}
                        value={String(val)}
                      />
                    ))}
                  </div>
                  {meta.description && (
                    <p className="mt-3 text-xs text-slate-500 bg-slate-50 rounded-lg px-3 py-2 border border-slate-100">
                      {String(meta.description)}
                    </p>
                  )}
                </div>
              )}
            </Card>

            {/* ─── Actions card (workflow-driven) ──────────────────────── */}
            {!isInactive && (availableActions?.length ?? 0) > 0 && (
              <Card>
                <h3 className="text-[11px] font-bold text-slate-400 uppercase tracking-widest mb-1">
                  Siguiente paso
                </h3>
                <p className="text-xs text-slate-500 mb-4">
                  Acciones disponibles desde el estado actual.
                </p>
                <div className="flex flex-col gap-2">
                  {regularActions.map(action => {
                    const Icon = resolveIcon(action.event_type?.icon)
                    return (
                      <button
                        key={action.transition_id}
                        onClick={() => setActiveAction(action)}
                        className="flex items-center gap-3 rounded-xl border px-3 py-2.5 text-left transition-all hover:shadow-sm"
                        style={colorStyle(action.event_type?.color || action.to_state?.color || '#6366f1')}
                      >
                        <Icon className="h-4.5 w-4.5 shrink-0" />
                        <div className="min-w-0">
                          <p className="text-xs font-semibold">{action.event_type?.name || action.label || action.event_type_slug}</p>
                          {action.to_state && (
                            <p className="text-[10px] opacity-70">→ {action.to_state.label}</p>
                          )}
                        </div>
                      </button>
                    )
                  })}

                  {terminalActions.length > 0 && regularActions.length > 0 && (
                    <div className="border-t border-slate-100 my-2" />
                  )}

                  {terminalActions.map(action => {
                    const Icon = resolveIcon(action.event_type?.icon)
                    const isRelease = action.event_type?.requires_admin ?? false
                    return (
                      <button
                        key={action.transition_id}
                        onClick={() => setActiveAction(action)}
                        className={`flex items-center gap-3 rounded-xl px-3 py-2.5 text-left transition-all ${
                          isRelease
                            ? 'text-red-600 hover:bg-red-50'
                            : 'border hover:shadow-sm'
                        }`}
                        style={isRelease ? undefined : colorStyle(action.event_type?.color || action.to_state?.color || '#6366f1')}
                      >
                        {isRelease ? <ShieldOff className="h-4 w-4 shrink-0" /> : <Icon className="h-4.5 w-4.5 shrink-0" />}
                        <div className="min-w-0">
                          <p className="text-xs font-semibold">
                            {action.event_type?.name || action.label || action.event_type_slug}
                            {isRelease && ' (admin)'}
                          </p>
                          {action.to_state && (
                            <p className={`text-[10px] ${isRelease ? 'text-red-400' : 'opacity-70'}`}>→ {action.to_state.label}</p>
                          )}
                        </div>
                      </button>
                    )
                  })}
                </div>
              </Card>
            )}
          </div>

          {/* ─── Right column: Timeline + Compliance ─────────────────── */}
          <div className="lg:col-span-2 space-y-6">
            <Card>
              <div className="flex items-center justify-between mb-5">
                <h3 className="text-sm font-semibold text-slate-800 flex items-center gap-2">
                  Historial de Movimientos
                  {eventsData && (
                    <span className="text-xs text-slate-400 font-normal">({eventsData.total} eventos)</span>
                  )}
                </h3>
              </div>
              {eventsLoading ? (
                <div className="flex justify-center py-10"><Spinner /></div>
              ) : events.length === 0 ? (
                <EmptyState
                  title="Sin movimientos"
                  description="Los movimientos apareceran aqui cuando se registren cambios de custodia, llegadas, inspecciones u otros eventos."
                />
              ) : (
                <EventTimeline events={events} assetId={id} blockchainAssetId={asset.blockchain_asset_id} />
              )}
            </Card>

            {/* Compliance section */}
            <ComplianceSection assetId={id} />
          </div>
        </div>
      </div>

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

// ─── Info Row ────────────────────────────────────────────────────────────────

function CertificateDownloadButton({ assetId }: { assetId: string }) {
  const { data: records = [] } = useAssetCompliance(assetId)
  const [downloading, setDownloading] = useState(false)
  const complianceUrl = import.meta.env.VITE_API_URL ?? 'http://localhost:9000'

  // Find the first record that has a certificate
  const recordWithCert = records.find(r =>
    ['ready', 'declared', 'compliant'].includes(r.compliance_status)
  )

  const handleDownload = async () => {
    if (!recordWithCert) return
    setDownloading(true)
    try {
      // First get the certificate for this record
      const certRes = await authFetch(`${complianceUrl}/api/v1/compliance/records/${recordWithCert.id}/certificate`)
      if (!certRes.ok) throw new Error('No certificate found')
      const cert = await certRes.json()

      // Download the PDF
      const pdfRes = await authFetch(`${complianceUrl}/api/v1/compliance/certificates/${cert.id}/download`)
      if (!pdfRes.ok) throw new Error('PDF not available')
      const blob = await pdfRes.blob()
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `${cert.certificate_number}.pdf`
      a.click()
      URL.revokeObjectURL(url)
    } catch {
      // No EUDR certificate — ignore silently
    } finally {
      setDownloading(false)
    }
  }

  if (!recordWithCert) return null

  return (
    <Button variant="secondary" size="sm" onClick={handleDownload} disabled={downloading}>
      <FileDown className="h-4 w-4" /> {downloading ? 'Descargando...' : 'Certificado EUDR'}
    </Button>
  )
}

function NftAttribute({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg bg-slate-50 border border-slate-100 px-3 py-2">
      <p className="text-[10px] text-slate-400 uppercase font-semibold tracking-wider">{label}</p>
      <p className="text-xs font-medium text-slate-700 mt-0.5 truncate" title={value}>{value}</p>
    </div>
  )
}

function InfoRow({ icon: Icon, label, children }: { icon: typeof Package; label: string; children: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between gap-3 py-1">
      <dt className="flex items-center gap-2 text-xs text-slate-400 shrink-0">
        <Icon className="h-3.5 w-3.5" />
        <span className="font-medium">{label}</span>
      </dt>
      <dd className="text-right">{children}</dd>
    </div>
  )
}

// ─── Blockchain Badge ────────────────────────────────────────────────────────

function BlockchainBadge({ status }: { status: BlockchainStatus }) {
  if (status === 'CONFIRMED') {
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
        <Link2 className="h-3 w-3" /> Certificado
      </span>
    )
  }
  if (status === 'PENDING') {
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-amber-50 text-amber-700 border border-amber-200">
        <RefreshCw className="h-3 w-3 animate-spin" /> Procesando
      </span>
    )
  }
  if (status === 'FAILED') {
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-red-50 text-red-700 border border-red-200">
        <XCircle className="h-3 w-3" /> Error
      </span>
    )
  }
  if (status === 'SIMULATED') {
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-slate-50 text-slate-500 border border-slate-200">
        <FlaskConical className="h-3 w-3" /> Simulado
      </span>
    )
  }
  return (
    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-slate-50 text-slate-400 border border-slate-200">
      Sin anclar
    </span>
  )
}

// ─── Compliance Section ──────────────────────────────────────────────────────

const COMPLIANCE_STATUS_COLORS: Record<string, string> = {
  incomplete: 'bg-amber-50 text-amber-700 border-amber-200',
  ready: 'bg-emerald-50 text-emerald-700 border-emerald-200',
  declared: 'bg-blue-50 text-blue-700 border-blue-200',
  compliant: 'bg-green-50 text-green-700 border-green-200',
  non_compliant: 'bg-red-50 text-red-700 border-red-200',
  partial: 'bg-orange-50 text-orange-700 border-orange-200',
}

const COMPLIANCE_STATUS_LABELS: Record<string, string> = {
  incomplete: 'Incompleto', ready: 'Listo', declared: 'Declarado',
  compliant: 'Cumple', non_compliant: 'No cumple', partial: 'Parcial',
}

const FRAMEWORK_FLAGS: Record<string, string> = {
  eudr: '🇪🇺', 'usda-organic': '🇺🇸', fssai: '🇮🇳', 'jfs-2200': '🇯🇵',
}

function ComplianceSection({ assetId }: { assetId: string }) {
  const isComplianceModuleActive = useIsModuleActive('compliance')
  const { data: records = [], isLoading } = useAssetCompliance(assetId)
  const navigate = useNavigate()

  if (!isComplianceModuleActive) {
    return (
      <Card>
        <div className="flex items-start gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-emerald-50 shrink-0">
            <ShieldCheck className="h-4.5 w-4.5 text-emerald-400" />
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-semibold text-slate-700">Exportas a Europa?</p>
            <p className="text-xs text-slate-500 mt-0.5">Activa Cumplimiento Normativo para certificar tus cargas bajo EUDR.</p>
          </div>
          <Link to="/marketplace"
            className="inline-flex items-center gap-1.5 rounded-lg bg-emerald-50 px-3 py-1.5 text-xs font-semibold text-emerald-700 hover:bg-emerald-100 transition-colors shrink-0">
            <Zap className="h-3.5 w-3.5" /> Activar
          </Link>
        </div>
      </Card>
    )
  }

  if (isLoading) return null

  if (records.length === 0) {
    return (
      <Card>
        <div className="flex items-start gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-emerald-50 shrink-0">
            <ShieldCheck className="h-4.5 w-4.5 text-emerald-500" />
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-semibold text-slate-700">Cumplimiento Normativo</p>
            <p className="text-xs text-slate-500 mt-0.5">Crea un registro EUDR para esta carga.</p>
          </div>
          <button onClick={() => navigate(`/cumplimiento/registros?create=${assetId}`)}
            className="inline-flex items-center gap-1.5 rounded-lg bg-primary px-3 py-1.5 text-xs font-semibold text-white hover:bg-primary/90 transition-colors shrink-0">
            Crear registro EUDR
          </button>
        </div>
      </Card>
    )
  }

  return (
    <Card>
      <h3 className="text-sm font-semibold text-slate-800 mb-4 flex items-center gap-2">
        <ShieldCheck className="h-4 w-4 text-emerald-500" />
        Cumplimiento Normativo
        <span className="text-xs text-slate-400 font-normal">({records.length})</span>
      </h3>
      <div className="space-y-3">
        {records.map(r => (
          <ComplianceRecordCard key={r.id} record={r} />
        ))}
      </div>
    </Card>
  )
}

function ComplianceRecordCard({ record: r }: { record: { id: string; framework_slug: string; compliance_status: string } }) {
  const navigate = useNavigate()
  const { data: cert } = useRecordCertificate(r.id)
  const generate = useGenerateCertificate(r.id)
  const complianceUrl = import.meta.env.VITE_API_URL ?? 'http://localhost:9000'
  const canGenerate = ['ready', 'declared', 'compliant'].includes(r.compliance_status)

  return (
    <div className="rounded-xl border border-slate-100 px-4 py-3 space-y-2">
      <Link to={`/cumplimiento/registros/${r.id}`}
        className="flex items-center gap-3 hover:opacity-80 transition-opacity">
        <span className="text-sm">{FRAMEWORK_FLAGS[r.framework_slug] ?? ''}</span>
        <span className="text-sm font-medium text-slate-900 flex-1">{r.framework_slug.toUpperCase()}</span>
        <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-semibold border ${COMPLIANCE_STATUS_COLORS[r.compliance_status] ?? 'bg-slate-50 text-slate-600 border-slate-200'}`}>
          {COMPLIANCE_STATUS_LABELS[r.compliance_status] ?? r.compliance_status}
        </span>
      </Link>

      {/* Certificate actions */}
      <div className="flex gap-2 pt-1">
        {cert && cert.status === 'active' ? (
          <>
            <button
              onClick={async () => {
                const res = await authFetch(`${complianceUrl}/api/v1/compliance/certificates/${cert.id}/download`)
                if (!res.ok) return
                const blob = await res.blob()
                const url = URL.createObjectURL(blob)
                const a = document.createElement('a')
                a.href = url
                a.download = `${cert.certificate_number}.pdf`
                a.click()
                URL.revokeObjectURL(url)
              }}
              className="inline-flex items-center gap-1.5 rounded-lg bg-emerald-600 px-3 py-1.5 text-[11px] font-semibold text-white hover:bg-emerald-700 transition-colors"
            >
              <FileDown className="h-3.5 w-3.5" /> Descargar Certificado EUDR
            </button>
            <span className="text-[10px] text-emerald-600 font-medium self-center">{cert.certificate_number}</span>
          </>
        ) : canGenerate ? (
          <button
            onClick={() => generate.mutate()}
            disabled={generate.isPending}
            className="inline-flex items-center gap-1.5 rounded-lg bg-emerald-600 px-3 py-1.5 text-[11px] font-semibold text-white hover:bg-emerald-700 disabled:opacity-50 transition-colors"
          >
            {generate.isPending ? 'Generando...' : 'Generar Certificado'}
          </button>
        ) : (
          <button
            onClick={() => navigate(`/cumplimiento/registros/${r.id}`)}
            className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 px-3 py-1.5 text-[11px] font-semibold text-slate-600 hover:bg-slate-50 transition-colors"
          >
            Completar registro
          </button>
        )}
      </div>
    </div>
  )
}
