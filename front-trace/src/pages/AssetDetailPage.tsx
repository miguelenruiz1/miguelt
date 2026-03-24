import { useState } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import {
  ArrowLeft, Package, RefreshCw, Truck, MapPin, BarChart2, ShieldOff,
  CheckCircle2, ExternalLink, Link2, XCircle, FlaskConical, FileDown,
  ShieldCheck, Zap,
} from 'lucide-react'
import { useSettingsStore, explorerAddressUrl } from '@/store/settings'
import type { BlockchainStatus } from '@/types/api'

const isSimulated = (s: string) => s.startsWith('sim') || s.startsWith('SIM_')
import { useAsset, useAssetEvents } from '@/hooks/useAssets'
import { Topbar } from '@/components/layout/Topbar'
import { Button } from '@/components/ui/button'
import { StateBadge } from '@/components/domain-badges'
import { HashChip, Spinner, Card, EmptyState } from '@/components/ui/Misc'
import { EventTimeline } from '@/components/events/EventTimeline'
import { HandoffModal, ArrivedModal, LoadedModal, QCModal, ReleaseModal, BurnModal } from '@/components/events/EventModals'
import { fmtDate, shortPubkey } from '@/lib/utils'
import { generateTraceabilityCertificate } from '@/lib/certificate'
import { useAssetCompliance } from '@/hooks/useCompliance'
import { useIsModuleActive } from '@/hooks/useModules'

type Modal = 'handoff' | 'arrived' | 'loaded' | 'qc' | 'release' | 'burn' | null

const VALID_FROM_STATES: Record<string, string[]> = {
  handoff: ['in_custody', 'in_transit', 'loaded', 'qc_passed', 'qc_failed'],
  arrived: ['in_transit'],
  loaded: ['in_custody'],
  qc: ['loaded', 'qc_failed'],
  release: ['in_custody', 'in_transit', 'loaded', 'qc_passed', 'qc_failed'],
  burn: ['in_custody', 'in_transit', 'loaded', 'qc_passed', 'qc_failed'],
}

function canDoAction(action: string, state: string): boolean {
  return VALID_FROM_STATES[action]?.includes(state) ?? false
}

const STATE_LABELS: Record<string, string> = {
  in_custody: 'En Custodia',
  in_transit: 'En Tránsito',
  loaded: 'Cargado',
  qc_passed: 'QC Aprobado',
  qc_failed: 'QC Rechazado',
  released: 'Liberado',
  burned: 'Completado',
}

export function AssetDetailPage() {
  const { id = '' } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [modal, setModal] = useState<Modal>(null)

  const { data: asset, isLoading, refetch, isFetching } = useAsset(id)
  const { data: eventsData, isLoading: eventsLoading } = useAssetEvents(id)
  const { solanaCluster } = useSettingsStore()

  const events = eventsData?.items ?? []
  const released = asset?.state === 'released'
  const burned = asset?.state === 'burned'
  const isInactive = released || burned
  const isCompleted = burned

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

  const cargoName = (asset.metadata as Record<string, unknown>)?.name as string | undefined

  return (
    <div className="flex flex-col flex-1 overflow-hidden">
      <Topbar
        title={cargoName || asset.product_type}
        subtitle={cargoName ? asset.product_type : undefined}
        actions={
          <div className="flex gap-2">
            {events.length > 0 && (
              <Button
                variant="secondary"
                size="sm"
                onClick={() => generateTraceabilityCertificate(asset, events, solanaCluster)}
                title="Descargar certificado de trazabilidad"
              >
                <FileDown className="h-4 w-4" /> Certificado PDF
              </Button>
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

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left */}
          <div className="space-y-5">

            {/* Info card */}
            <Card>
              <div className="flex items-start gap-4 mb-6">
                <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-gradient-to-br from-primary/10 to-primary/5 border border-primary/20/50 shadow-inner shrink-0">
                  <Package className="h-6 w-6 text-primary drop-shadow-sm" />
                </div>
                <div className="min-w-0">
                  {cargoName && (
                    <p className="text-sm font-bold text-slate-900 mb-1">{cargoName}</p>
                  )}
                  <p className="text-xs font-semibold text-slate-400 mt-0.5 uppercase tracking-wider">{asset.product_type}</p>
                  {isSimulated(asset.asset_mint) ? (
                    <span className="inline-block mt-2 text-xs text-amber-600 bg-amber-50 border border-amber-200 px-2 py-0.5 rounded-full font-medium">
                      Modo simulación
                    </span>
                  ) : (
                    <a
                      href={explorerAddressUrl(asset.asset_mint, solanaCluster)}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-1.5 mt-2 text-xs font-semibold text-primary hover:text-primary hover:underline transition-colors"
                    >
                      <ExternalLink className="h-3.5 w-3.5" />
                      Ver en Solana Explorer
                    </a>
                  )}
                </div>
              </div>

              <dl className="space-y-3">
                <Row label="Estado"><StateBadge state={asset.state} /></Row>
                <Row label="Blockchain">
                  <BlockchainBadge status={asset.blockchain_status ?? 'SKIPPED'} />
                </Row>
                <Row label="Custodio">
                  <span className="font-mono text-xs text-slate-700 font-medium" title={asset.current_custodian_wallet}>
                    {shortPubkey(asset.current_custodian_wallet)}
                  </span>
                </Row>
                <Row label="Último hash">
                  {asset.last_event_hash
                    ? <HashChip hash={asset.last_event_hash} />
                    : <span className="text-slate-300 text-xs">—</span>
                  }
                </Row>
                <Row label="Eventos">
                  <span className="text-slate-700 text-xs font-medium tabular-nums">{eventsData?.total ?? '—'}</span>
                </Row>
                <Row label="Registrado">
                  <span className="text-slate-500 text-xs tabular-nums">{fmtDate(asset.created_at)}</span>
                </Row>
                <Row label="Actualizado">
                  <span className="text-slate-500 text-xs tabular-nums">{fmtDate(asset.updated_at)}</span>
                </Row>
              </dl>

              {Object.keys(asset.metadata).length > 0 && (
                <details className="mt-4">
                  <summary className="text-xs text-slate-500 cursor-pointer hover:text-slate-800 transition-colors font-medium">
                    Ver metadatos
                  </summary>
                  <pre className="mt-2 rounded-xl bg-slate-50 border border-slate-200 p-3 text-xs text-slate-600 overflow-x-auto font-mono">
                    {JSON.stringify(asset.metadata, null, 2)}
                  </pre>
                </details>
              )}
            </Card>

            {/* Actions */}
            {!isInactive && (
              <Card>
                <h3 className="text-[11px] font-bold text-slate-400 uppercase tracking-widest mb-4">Acciones</h3>
                <div className="flex flex-col gap-2">
                  {canDoAction('handoff', asset.state) && (
                    <Button variant="secondary" size="sm" className="justify-start h-10 shadow-sm" onClick={() => setModal('handoff')}>
                      <Truck className="h-4 w-4 text-primary mr-1" /> Transferir Custodia
                    </Button>
                  )}
                  {canDoAction('arrived', asset.state) && (
                    <Button variant="secondary" size="sm" className="justify-start h-10 shadow-sm" onClick={() => setModal('arrived')}>
                      <MapPin className="h-4 w-4 text-cyan-500 mr-1" /> Registrar Llegada
                    </Button>
                  )}
                  {canDoAction('loaded', asset.state) && (
                    <Button variant="secondary" size="sm" className="justify-start h-10 shadow-sm" onClick={() => setModal('loaded')}>
                      <Package className="h-4 w-4 text-violet-500 mr-1" /> Cargar en Transporte
                    </Button>
                  )}
                  {canDoAction('qc', asset.state) && (
                    <Button variant="secondary" size="sm" className="justify-start h-10 shadow-sm" onClick={() => setModal('qc')}>
                      <BarChart2 className="h-4 w-4 text-amber-500 mr-1" /> Control de Calidad
                    </Button>
                  )}

                  {/* Separador antes de acciones finales */}
                  {(canDoAction('burn', asset.state) || canDoAction('release', asset.state)) && (
                    <div className="border-t border-slate-100/50 my-2" />
                  )}

                  {canDoAction('burn', asset.state) && (
                    <Button variant="secondary" size="sm" className="justify-start h-10 shadow-sm text-cyan-700 hover:bg-cyan-50" onClick={() => setModal('burn')}>
                      <CheckCircle2 className="h-4 w-4 text-cyan-500 mr-1" /> Completar Entrega
                    </Button>
                  )}

                  {canDoAction('release', asset.state) && (
                    <Button
                      variant="ghost"
                      size="sm"
                      className="justify-start h-10 font-semibold text-red-600 hover:text-red-700 hover:bg-red-50/80 transition-all"
                      onClick={() => setModal('release')}
                    >
                      <ShieldOff className="h-4 w-4 mr-1" /> Liberar (admin)
                    </Button>
                  )}
                </div>
              </Card>
            )}

            {isCompleted && (
              <div className="rounded-2xl border border-cyan-200 bg-cyan-50 px-4 py-3 text-xs text-cyan-700 text-center space-y-2">
                <div className="flex items-center justify-center gap-2">
                  <CheckCircle2 className="h-4 w-4" />
                  <span className="font-bold">Entrega completada</span>
                </div>
                <p>La cadena de custodia de esta carga ha sido finalizada y certificada en blockchain.</p>
              </div>
            )}

            {released && !burned && (
              <div className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-xs text-slate-500 text-center">
                Esta carga ha sido liberada y ya no está en la cadena de custodia activa.
              </div>
            )}
          </div>

          {/* Right: timeline */}
          <div className="lg:col-span-2">
            <Card>
              <h3 className="text-sm font-semibold text-slate-800 mb-5">
                Cadena de Custodia
                {eventsData && (
                  <span className="ml-2 text-xs text-slate-400 font-normal">({eventsData.total} eventos)</span>
                )}
              </h3>
              {eventsLoading ? (
                <div className="flex justify-center py-10"><Spinner /></div>
              ) : events.length === 0 ? (
                <EmptyState title="Sin eventos" description="Los eventos aparecerán aquí a medida que ocurran cambios de custodia." />
              ) : (
                <EventTimeline events={events} assetId={id} />
              )}
            </Card>

            {/* Compliance section */}
            <ComplianceSection assetId={id} />
          </div>
        </div>
      </div>

      {asset && (
        <>
          <HandoffModal asset={asset} open={modal === 'handoff'} onClose={() => setModal(null)} />
          <ArrivedModal asset={asset} open={modal === 'arrived'} onClose={() => setModal(null)} />
          <LoadedModal asset={asset} open={modal === 'loaded'} onClose={() => setModal(null)} />
          <QCModal asset={asset} open={modal === 'qc'} onClose={() => setModal(null)} />
          <ReleaseModal asset={asset} open={modal === 'release'} onClose={() => setModal(null)} />
          <BurnModal asset={asset} open={modal === 'burn'} onClose={() => setModal(null)} />
        </>
      )}
    </div>
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
      <div className="space-y-2">
        {records.map(r => (
          <Link key={r.id} to={`/cumplimiento/registros/${r.id}`}
            className="flex items-center gap-3 rounded-xl border border-slate-100 px-4 py-3 hover:bg-slate-50/50 transition-colors">
            <span className="text-sm">{FRAMEWORK_FLAGS[r.framework_slug] ?? ''}</span>
            <span className="text-sm font-medium text-slate-900 flex-1">{r.framework_slug.toUpperCase()}</span>
            <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-semibold border ${COMPLIANCE_STATUS_COLORS[r.compliance_status] ?? 'bg-slate-50 text-slate-600 border-slate-200'}`}>
              {COMPLIANCE_STATUS_LABELS[r.compliance_status] ?? r.compliance_status}
            </span>
          </Link>
        ))}
      </div>
    </Card>
  )
}

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between gap-3 py-1">
      <dt className="text-xs font-semibold text-slate-400 tracking-wide uppercase shrink-0">{label}</dt>
      <dd className="text-right">{children}</dd>
    </div>
  )
}

function BlockchainBadge({ status }: { status: BlockchainStatus }) {
  if (status === 'CONFIRMED') {
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
        <Link2 className="h-3 w-3" /> Certificado
      </span>
    )
  }
  if (status === 'PENDING') {
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-semibold bg-amber-50 text-amber-700 border border-amber-200">
        <RefreshCw className="h-3 w-3 animate-spin" /> Certificando
      </span>
    )
  }
  if (status === 'FAILED') {
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-semibold bg-red-50 text-red-700 border border-red-200">
        <XCircle className="h-3 w-3" /> Fallido
      </span>
    )
  }
  if (status === 'SIMULATED') {
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-semibold bg-slate-50 text-slate-500 border border-slate-200">
        <FlaskConical className="h-3 w-3" /> Simulado
      </span>
    )
  }
  return (
    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-semibold bg-slate-50 text-slate-400 border border-slate-200">
      Fuera de cadena
    </span>
  )
}
