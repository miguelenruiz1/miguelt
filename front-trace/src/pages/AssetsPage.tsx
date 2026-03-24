import { useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { Plus, Search, RefreshCw, Package, Sparkles } from 'lucide-react'
import { Topbar } from '@/components/layout/Topbar'
import { Button } from '@/components/ui/button'
import { Spinner, EmptyState } from '@/components/ui/Misc'
import { AssetCard } from '@/components/assets/AssetCard'
import { CreateAssetModal } from '@/components/assets/CreateAssetModal'
import { MintNFTModal } from '@/components/assets/MintNFTModal'
import { useAssetList } from '@/hooks/useAssets'
import type { AssetState } from '@/types/api'

const STATE_OPTIONS: { value: AssetState | ''; label: string }[] = [
  { value: '',              label: 'Todos los estados' },
  { value: 'in_custody',    label: 'En Custodia' },
  { value: 'in_transit',    label: 'En Tránsito' },
  { value: 'loaded',        label: 'Cargado' },
  { value: 'sealed',        label: 'Sellado' },
  { value: 'customs_hold',  label: 'Aduana' },
  { value: 'qc_passed',     label: 'QC Aprobado' },
  { value: 'qc_failed',     label: 'QC Rechazado' },
  { value: 'damaged',       label: 'Dañado' },
  { value: 'delivered',     label: 'Entregado' },
  { value: 'released',      label: 'Liberado' },
  { value: 'burned',        label: 'Completado' },
]

const fieldCls = 'rounded-xl border border-white/60 bg-white/50 backdrop-blur-md px-4 py-2.5 text-sm font-medium text-slate-800 placeholder:text-slate-400 hover:bg-white/70 hover:border-primary/50 focus:bg-white focus:border-primary focus:ring-2 focus:ring-ring/20 focus:outline-none transition-all shadow-sm'

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

  const assets = (data?.items ?? []).filter((a) =>
    !search ||
    a.asset_mint.toLowerCase().includes(search.toLowerCase()) ||
    a.current_custodian_wallet.toLowerCase().includes(search.toLowerCase())
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
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-slate-400 pointer-events-none" />
            <input
              type="text"
              placeholder="Buscar carga o custodio…"
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
            className={`${fieldCls} w-36`}
          />
          <select
            value={state}
            onChange={(e) => setState(e.target.value as AssetState | '')}
            className={fieldCls}
          >
            {STATE_OPTIONS.map((o) => (
              <option key={o.value} value={o.value}>{o.label}</option>
            ))}
          </select>
          <Button variant="ghost" size="icon" onClick={() => refetch()} title="Refresh">
            <RefreshCw className={`h-4 w-4 ${isFetching ? 'animate-spin' : ''}`} />
          </Button>
        </div>

        {/* Grid */}
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
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
            {assets.map((asset) => <AssetCard key={asset.id} asset={asset} />)}
          </div>
        )}
      </div>

      <CreateAssetModal open={showCreate} onClose={() => setShowCreate(false)} />
      <MintNFTModal open={showMint} onClose={() => setShowMint(false)} />
    </div>
  )
}
