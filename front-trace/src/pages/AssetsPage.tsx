import { useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { Plus, Search, RefreshCw, Package, Sparkles, ExternalLink, ChevronRight } from 'lucide-react'
import { Topbar } from '@/components/layout/Topbar'
import { Button } from '@/components/ui/button'
import { Spinner, EmptyState } from '@/components/ui/misc'
import { StateBadge, BlockchainStatusBadge } from '@/components/domain-badges'
import { CreateAssetModal } from '@/components/assets/CreateAssetModal'
import { MintNFTModal } from '@/components/assets/MintNFTModal'
import { useAssetList } from '@/hooks/useAssets'
import { useOrganizations } from '@/hooks/useTaxonomy'
import { useWalletList } from '@/hooks/useWallets'
import { useWorkflowStates } from '@/hooks/useWorkflow'
import { shortPubkey, fmtDateShort } from '@/lib/utils'
import type { Asset, AssetState } from '@/types/api'

const fieldCls = 'rounded-xl border border-white/60 bg-card/50 backdrop-blur-md px-4 py-2.5 text-sm font-medium text-foreground placeholder:text-muted-foreground hover:bg-card/70 hover:border-primary/50 focus:bg-card focus:border-primary focus:ring-2 focus:ring-ring/20 focus:outline-none transition-all '

export function AssetsPage() {
  const [searchParams] = useSearchParams()
  const [showCreate, setShowCreate] = useState(false)
  const [showMint, setShowMint] = useState(false)
  const [search, setSearch] = useState(searchParams.get('q') || '')
  const [state, setState] = useState<AssetState | ''>('')
  const [productType, setProductType] = useState('')

  const { data, isLoading, isFetching, refetch } = useAssetList({
    state: state || undefined,
    product_type: productType || undefined,
    limit: 100,
  })

  // Load workflow states for dynamic filter dropdown
  const { data: workflowStates } = useWorkflowStates()

  // Load wallets + orgs to resolve custodian names
  const { data: walletsData } = useWalletList({ limit: 200 })
  const { data: orgsData } = useOrganizations()
  const wallets = walletsData?.items ?? []
  const orgs = orgsData?.items ?? []

  const walletMap = new Map(wallets.map(w => [w.wallet_pubkey, w]))
  const orgMap = new Map(orgs.map(o => [o.id, o]))

  const getCustodianLabel = (pubkey: string) => {
    const w = walletMap.get(pubkey)
    if (!w) return shortPubkey(pubkey)
    if (w.name) return w.name
    if (w.organization_id) {
      const org = orgMap.get(w.organization_id)
      if (org) return org.name
    }
    return shortPubkey(pubkey)
  }

  const getCargoName = (asset: Asset) => {
    const meta = asset.metadata as Record<string, unknown> | undefined
    if (meta?.name && typeof meta.name === 'string') return meta.name
    return null
  }

  const getWeight = (asset: Asset) => {
    const meta = asset.metadata as Record<string, unknown> | undefined
    if (meta?.weight && meta?.weightUnit) return `${meta.weight} ${meta.weightUnit}`
    if (meta?.weight) return `${meta.weight} kg`
    if (meta?.peso_total_kg) return `${meta.peso_total_kg} kg`
    return null
  }

  const assets = (data?.items ?? []).filter((a) =>
    !search ||
    a.asset_mint.toLowerCase().includes(search.toLowerCase()) ||
    a.current_custodian_wallet.toLowerCase().includes(search.toLowerCase()) ||
    a.product_type.toLowerCase().includes(search.toLowerCase()) ||
    (getCargoName(a) || '').toLowerCase().includes(search.toLowerCase())
  )

  return (
    <div className="flex flex-col flex-1 overflow-hidden">
      <Topbar
        title="Cargas"
        subtitle={`${data?.total ?? 0} total`}
        actions={
          <div className="flex gap-2">
            <Button size="sm" variant="secondary" onClick={() => setShowCreate(true)}>
              <Plus className="h-4 w-4" /> Registrar Existente
            </Button>
            <Button size="sm" onClick={() => setShowMint(true)}>
              <Sparkles className="h-4 w-4" /> Registrar Carga
            </Button>
          </div>
        }
      />

      <div className="flex-1 overflow-y-auto p-6">
        {/* Filters */}
        <div className="flex gap-3 mb-6 flex-wrap">
          <div className="relative flex-1 min-w-48 max-w-xs">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground pointer-events-none" />
            <input
              type="text"
              placeholder="Buscar por nombre, producto o custodio…"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className={`${fieldCls} pl-9 w-full`}
            />
          </div>
          <input
            type="text"
            placeholder="Tipo de producto…"
            value={productType}
            onChange={(e) => setProductType(e.target.value)}
            className={`${fieldCls} w-40`}
          />
          <select
            value={state}
            onChange={(e) => setState(e.target.value as AssetState | '')}
            className={fieldCls}
          >
            <option value="">Todos los estados</option>
            {(workflowStates ?? []).map((s) => (
              <option key={s.slug} value={s.slug}>{s.label}</option>
            ))}
          </select>
          <Button variant="ghost" size="icon" onClick={() => refetch()} title="Actualizar">
            <RefreshCw className={`h-4 w-4 ${isFetching ? 'animate-spin' : ''}`} />
          </Button>
        </div>

        {/* Table */}
        {isLoading ? (
          <div className="flex justify-center py-20"><Spinner /></div>
        ) : assets.length === 0 ? (
          <EmptyState
            icon={<Package className="h-12 w-12" />}
            title="No hay cargas registradas"
            description="Registra tu primera carga para comenzar el seguimiento de custodia."
            action={
              <Button size="sm" onClick={() => setShowMint(true)}>
                <Sparkles className="h-4 w-4" /> Registrar primera carga
              </Button>
            }
          />
        ) : (
          <div className="bg-card rounded-xl border overflow-hidden ">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-muted">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase">Carga</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase">Producto</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase">Cantidad</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase">Custodio</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase">Estado</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase">Blockchain</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase">Fecha</th>
                  <th className="px-4 py-3" />
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {assets.map((asset) => {
                  const cargoName = getCargoName(asset)
                  const weight = getWeight(asset)

                  return (
                    <tr key={asset.id} className="hover:bg-muted transition-colors">
                      <td className="px-4 py-3">
                        <Link to={`/assets/${asset.id}`} className="flex items-center gap-3 group">
                          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-primary/10 shrink-0">
                            <Package className="h-4 w-4 text-primary" />
                          </div>
                          <div className="min-w-0">
                            <p className="text-sm font-semibold text-foreground truncate max-w-48 group-hover:text-primary transition-colors">
                              {cargoName || shortPubkey(asset.asset_mint)}
                            </p>
                            <p className="text-xs text-muted-foreground font-mono">{shortPubkey(asset.asset_mint)}</p>
                          </div>
                        </Link>
                      </td>
                      <td className="px-4 py-3">
                        <span className="text-sm text-foreground font-medium">{asset.product_type}</span>
                      </td>
                      <td className="px-4 py-3">
                        <span className="text-sm text-muted-foreground">{weight || '—'}</span>
                      </td>
                      <td className="px-4 py-3">
                        <span className="text-sm text-foreground">{getCustodianLabel(asset.current_custodian_wallet)}</span>
                      </td>
                      <td className="px-4 py-3">
                        <StateBadge state={asset.state} />
                      </td>
                      <td className="px-4 py-3">
                        <BlockchainStatusBadge status={asset.blockchain_status} />
                      </td>
                      <td className="px-4 py-3">
                        <span className="text-xs text-muted-foreground">{fmtDateShort(asset.updated_at)}</span>
                      </td>
                      <td className="px-4 py-3">
                        <Link to={`/assets/${asset.id}`} className="flex h-7 w-7 items-center justify-center rounded-full hover:bg-secondary transition-colors">
                          <ChevronRight className="h-4 w-4 text-muted-foreground" />
                        </Link>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <CreateAssetModal open={showCreate} onClose={() => setShowCreate(false)} />
      <MintNFTModal open={showMint} onClose={() => setShowMint(false)} />
    </div>
  )
}
