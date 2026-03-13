import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { RefreshCw } from 'lucide-react'
import { Topbar } from '@/components/layout/Topbar'
import { Button } from '@/components/ui/Button'
import { Spinner } from '@/components/ui/Misc'
import { StateBadge } from '@/components/ui/Badge'
import { useQueries } from '@tanstack/react-query'
import { api } from '@/lib/api'
import { useWalletList } from '@/hooks/useWallets'
import { useOrganizations } from '@/hooks/useTaxonomy'
import { fmtDateShort, shortPubkey } from '@/lib/utils'
import type { Asset, AssetState } from '@/types/api'

const COLUMNS: { state: AssetState; label: string; color: string }[] = [
  { state: 'in_custody',  label: 'En Custodia',   color: 'border-indigo-300 bg-indigo-50/60' },
  { state: 'in_transit',  label: 'En Tránsito',   color: 'border-amber-300 bg-amber-50/60' },
  { state: 'loaded',      label: 'Cargado',       color: 'border-blue-300 bg-blue-50/60' },
  { state: 'qc_passed',   label: 'QC Aprobado',   color: 'border-emerald-300 bg-emerald-50/60' },
  { state: 'qc_failed',   label: 'QC Rechazado',  color: 'border-red-300 bg-red-50/60' },
  { state: 'released',    label: 'Liberado',      color: 'border-slate-300 bg-slate-50/60' },
  { state: 'burned',      label: 'Completado',    color: 'border-cyan-300 bg-cyan-50/60' },
]

function AssetCard({
  asset,
  orgName,
  onClick,
}: {
  asset: Asset
  orgName: string | null
  onClick: () => void
}) {
  return (
    <button
      onClick={onClick}
      className="w-full text-left rounded-xl border border-white bg-white shadow-sm hover:shadow-md hover:border-indigo-200 transition-all duration-200 p-3 group"
    >
      <div className="flex items-start justify-between gap-2 mb-2">
        <span className="font-mono text-xs text-indigo-600 font-semibold group-hover:text-indigo-800 truncate">
          {shortPubkey(asset.asset_mint)}
        </span>
        <StateBadge state={asset.state} />
      </div>
      <p className="text-xs font-medium text-slate-700 truncate">{asset.product_type}</p>
      {orgName && (
        <p className="text-[11px] text-slate-400 mt-1 truncate">{orgName}</p>
      )}
      <p className="text-[10px] text-slate-300 mt-1.5 tabular-nums">
        {fmtDateShort(asset.updated_at)}
      </p>
    </button>
  )
}

function KanbanColumn({
  label,
  color,
  assets,
  isLoading,
  orgName,
  onCardClick,
}: {
  label: string
  color: string
  assets: Asset[]
  isLoading: boolean
  orgName: (pubkey: string) => string | null
  onCardClick: (id: string) => void
}) {
  return (
    <div className={`flex flex-col rounded-2xl border ${color} min-w-[180px] w-[200px] sm:w-[220px] lg:w-[240px] shrink-0`}>
      <div className="flex items-center justify-between px-3 py-2.5 border-b border-white/60">
        <span className="text-xs font-bold text-slate-600 uppercase tracking-wide">{label}</span>
        <span className="text-xs bg-white/80 text-slate-500 rounded-full px-2 py-0.5 font-semibold">
          {isLoading ? '…' : assets.length}
        </span>
      </div>
      <div className="flex flex-col gap-2 p-2 overflow-y-auto flex-1" style={{ maxHeight: 'calc(100vh - 220px)' }}>
        {isLoading ? (
          <div className="flex justify-center py-6"><Spinner /></div>
        ) : assets.length === 0 ? (
          <p className="text-center text-[11px] text-slate-300 py-6">Vacío</p>
        ) : (
          assets.map((a) => (
            <AssetCard
              key={a.id}
              asset={a}
              orgName={orgName(a.current_custodian_wallet)}
              onClick={() => onCardClick(a.id)}
            />
          ))
        )}
      </div>
    </div>
  )
}

export function TrackingBoardPage() {
  const navigate = useNavigate()
  const [filterOrgId, setFilterOrgId] = useState('')

  // One independent query per state column — no stale-cache issues, no limit problems
  const stateResults = useQueries({
    queries: COLUMNS.map((col) => ({
      queryKey: ['assets', 'board', col.state],
      queryFn: () => api.assets.list({ state: col.state, limit: 200 }),
      refetchInterval: 15_000,
    })),
  })

  const { data: walletsData } = useWalletList({ limit: 500 })
  const { data: orgsData } = useOrganizations()

  const wallets = walletsData?.items ?? []
  const orgs = orgsData?.items ?? []

  const isFetching = stateResults.some((r) => r.isFetching)
  const totalCount = stateResults.reduce((sum, r) => sum + (r.data?.total ?? 0), 0)

  const refetchAll = () => stateResults.forEach((r) => r.refetch())

  // Build lookup: pubkey → org name
  const walletOrgMap = new Map<string, string>()
  for (const w of wallets) {
    if (w.organization_id) {
      const org = orgs.find((o) => o.id === w.organization_id)
      if (org) walletOrgMap.set(w.wallet_pubkey, org.name)
    }
  }

  const getOrgName = (pubkey: string) => walletOrgMap.get(pubkey) ?? null

  // Filter by org if selected
  const orgWalletPubkeys = filterOrgId
    ? new Set(wallets.filter((w) => w.organization_id === filterOrgId).map((w) => w.wallet_pubkey))
    : null

  const getColumnAssets = (idx: number): Asset[] => {
    const items = stateResults[idx].data?.items ?? []
    if (!orgWalletPubkeys) return items
    return items.filter((a) => orgWalletPubkeys.has(a.current_custodian_wallet))
  }

  return (
    <div className="flex flex-col flex-1 overflow-hidden">
      <Topbar
        title="Panel de Seguimiento"
        subtitle={`${totalCount} cargas en seguimiento`}
        actions={
          <Button variant="ghost" size="icon" onClick={refetchAll} title="Refresh">
            <RefreshCw className={`h-4 w-4 ${isFetching ? 'animate-spin' : ''}`} />
          </Button>
        }
      />

      {/* Filter bar */}
      <div className="flex flex-wrap items-center gap-2 sm:gap-3 px-4 sm:px-6 py-3 border-b border-slate-100 bg-white/50">
        <span className="text-xs font-semibold text-slate-500 hidden sm:inline">Filtrar por organización:</span>
        <select
          value={filterOrgId}
          onChange={(e) => setFilterOrgId(e.target.value)}
          className="rounded-xl border border-slate-200 bg-white px-3 py-1.5 text-sm text-slate-700 focus:border-indigo-400 focus:outline-none focus:ring-2 focus:ring-indigo-200"
        >
          <option value="">Todas las organizaciones</option>
          {orgs.map((o) => (
            <option key={o.id} value={o.id}>{o.name}</option>
          ))}
        </select>
        {filterOrgId && (
          <Button size="sm" variant="ghost" onClick={() => setFilterOrgId('')}>Limpiar</Button>
        )}
        <span className="ml-auto text-xs text-slate-400">Se actualiza cada 15s</span>
      </div>

      {/* Board */}
      <div className="flex-1 overflow-x-auto p-3 sm:p-6">
        <div className="flex gap-4 h-full">
          {COLUMNS.map(({ state, label, color }, i) => (
            <KanbanColumn
              key={state}
              label={label}
              color={color}
              assets={getColumnAssets(i)}
              isLoading={stateResults[i].isLoading && !stateResults[i].data}
              orgName={getOrgName}
              onCardClick={(id) => navigate(`/assets/${id}`)}
            />
          ))}
        </div>
      </div>
    </div>
  )
}
