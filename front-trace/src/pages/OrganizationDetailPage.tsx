import { useState } from 'react'
import { useParams, Link, useNavigate } from 'react-router-dom'
import { ArrowLeft, Package, Wallet, Plus, Sparkles, RefreshCw } from 'lucide-react'
import { useOrganization, useOrgAssets, useOrgWallets, useCustodianTypes } from '@/hooks/useTaxonomy'
import { Topbar } from '@/components/layout/Topbar'
import { Button } from '@/components/ui/button'
import { StateBadge, WalletStatusBadge } from '@/components/domain-badges'
import { Spinner, EmptyState } from '@/components/ui/Misc'
import { MintNFTModal } from '@/components/assets/MintNFTModal'
import { GenerateWalletModal } from '@/components/wallets/GenerateWalletModal'
import { fmtDateShort, shortPubkey } from '@/lib/utils'
import type { Asset } from '@/types/api'

// ─── Product emoji map ────────────────────────────────────────────────────────

const PRODUCT_EMOJI: Record<string, string> = {
  cafe: '☕', 'café': '☕',
  arroz: '🌾',
  maiz: '🌽', 'maíz': '🌽',
  cacao: '🍫',
  'caña': '🎋',
  soya: '🫘',
  'algodón': '🧶',
}

function productEmoji(type: string): string {
  return PRODUCT_EMOJI[type.toLowerCase()] ?? '📦'
}

// ─── Asset card ───────────────────────────────────────────────────────────────

function AssetCard({ asset, onClick }: { asset: Asset; onClick: () => void }) {
  const name = typeof asset.metadata?.name === 'string' ? asset.metadata.name : null
  const weight = asset.metadata?.weight
  const unit = asset.metadata?.weight_unit

  return (
    <button
      onClick={onClick}
      className="text-left rounded-2xl border border-slate-200 bg-white hover:border-primary/50 hover:shadow-md transition-all duration-200 p-4 group"
    >
      <div className="flex items-center justify-between gap-2 mb-2">
        <span className="text-2xl">{productEmoji(asset.product_type)}</span>
        <StateBadge state={asset.state} />
      </div>
      <p className="font-semibold text-slate-800 text-sm truncate group-hover:text-primary transition-colors">
        {name ?? asset.product_type}
      </p>
      {name && (
        <p className="text-xs text-slate-400 truncate">{asset.product_type}</p>
      )}
      {weight && (
        <p className="text-xs text-slate-500 mt-1">{String(weight)} {unit ?? ''}</p>
      )}
      <p className="text-[10px] text-slate-300 mt-2 font-mono">
        {shortPubkey(asset.asset_mint)}
      </p>
      <p className="text-[10px] text-slate-300 tabular-nums">{fmtDateShort(asset.updated_at)}</p>
    </button>
  )
}

// ─── Wallets tab ──────────────────────────────────────────────────────────────

function WalletsTab({ orgId, onAddWallet }: { orgId: string; onAddWallet: () => void }) {
  const navigate = useNavigate()
  const { data, isLoading, refetch, isFetching } = useOrgWallets(orgId)
  const wallets = data?.items ?? []

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <p className="text-sm font-semibold text-slate-600">{wallets.length} wallet{wallets.length !== 1 ? 's' : ''}</p>
        <div className="flex gap-2">
          <Button variant="ghost" size="icon" onClick={() => refetch()} title="Actualizar">
            <RefreshCw className={`h-4 w-4 ${isFetching ? 'animate-spin' : ''}`} />
          </Button>
          <Button size="sm" onClick={onAddWallet}>
            <Plus className="h-4 w-4" /> Nueva Wallet
          </Button>
        </div>
      </div>

      {isLoading ? (
        <div className="flex justify-center py-12"><Spinner /></div>
      ) : wallets.length === 0 ? (
        <EmptyState
          icon={<Wallet className="h-10 w-10" />}
          title="Sin wallets"
          description="Esta organización aún no tiene wallets vinculadas."
          action={<Button onClick={onAddWallet}><Plus className="h-4 w-4" /> Nueva Wallet</Button>}
        />
      ) : (
        <div className="flex flex-col gap-2">
          {wallets.map((w) => (
            <button
              key={w.id}
              onClick={() => navigate(`/wallets/${w.id}`)}
              className="flex items-center gap-4 p-4 rounded-xl border border-slate-200 bg-white hover:border-primary/50 hover:shadow-sm transition-all text-left group"
            >
              <div className="h-9 w-9 rounded-xl bg-primary/10 flex items-center justify-center shrink-0">
                <Wallet className="h-4 w-4 text-primary" />
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-semibold text-slate-800 group-hover:text-primary transition-colors truncate">
                  {w.name ?? shortPubkey(w.wallet_pubkey)}
                </p>
                <p className="text-xs text-slate-400 font-mono">{shortPubkey(w.wallet_pubkey)}</p>
              </div>
              <WalletStatusBadge status={w.status} />
              <p className="text-xs text-slate-400 whitespace-nowrap tabular-nums hidden sm:block">
                {fmtDateShort(w.created_at)}
              </p>
            </button>
          ))}
        </div>
      )}
    </div>
  )
}

// ─── NFTs tab ─────────────────────────────────────────────────────────────────

function AssetsTab({ orgId, onMintNFT }: { orgId: string; onMintNFT: () => void }) {
  const navigate = useNavigate()
  const { data, isLoading, refetch, isFetching } = useOrgAssets(orgId)
  const assets = data?.items ?? []

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <p className="text-sm font-semibold text-slate-600">{assets.length} activo{assets.length !== 1 ? 's' : ''}</p>
        <div className="flex gap-2">
          <Button variant="ghost" size="icon" onClick={() => refetch()} title="Actualizar">
            <RefreshCw className={`h-4 w-4 ${isFetching ? 'animate-spin' : ''}`} />
          </Button>
          <Button size="sm" onClick={onMintNFT}>
            <Sparkles className="h-4 w-4" /> Registrar NFT
          </Button>
        </div>
      </div>

      {isLoading ? (
        <div className="flex justify-center py-12"><Spinner /></div>
      ) : assets.length === 0 ? (
        <EmptyState
          icon={<Package className="h-10 w-10" />}
          title="Sin activos"
          description="Esta organización no tiene NFTs registrados actualmente."
          action={<Button onClick={onMintNFT}><Sparkles className="h-4 w-4" /> Registrar NFT</Button>}
        />
      ) : (
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3">
          {assets.map((a) => (
            <AssetCard
              key={a.id}
              asset={a}
              onClick={() => navigate(`/assets/${a.id}`)}
            />
          ))}
        </div>
      )}
    </div>
  )
}

// ─── Main Page ─────────────────────────────────────────────────────────────────

type Tab = 'assets' | 'wallets'

export function OrganizationDetailPage() {
  const { id = '' } = useParams<{ id: string }>()
  const [tab, setTab] = useState<Tab>('assets')
  const [showMint, setShowMint] = useState(false)
  const [showGenWallet, setShowGenWallet] = useState(false)

  const { data: org, isLoading } = useOrganization(id)
  const { data: types = [] } = useCustodianTypes()

  const type = org ? types.find((t) => t.id === org.custodian_type_id) : undefined

  if (isLoading) {
    return (
      <div className="flex flex-col flex-1 overflow-hidden">
        <Topbar title="Organización" />
        <div className="flex justify-center py-20"><Spinner /></div>
      </div>
    )
  }

  if (!org) {
    return (
      <div className="flex flex-col flex-1 overflow-hidden">
        <Topbar title="Organización no encontrada" />
        <EmptyState
          title="Organización no encontrada"
          action={<Link to="/organizations"><Button>Volver a Organizaciones</Button></Link>}
        />
      </div>
    )
  }

  return (
    <div className="flex flex-col flex-1 overflow-hidden">
      <Topbar
        title={org.name}
        subtitle={type?.name ?? 'Organización'}
      />

      <div className="flex-1 overflow-y-auto p-6 space-y-6">
        {/* Back */}
        <Link
          to="/organizations"
          className="inline-flex items-center gap-2 text-sm font-semibold text-slate-500 hover:text-primary transition-colors group"
        >
          <ArrowLeft className="h-4 w-4 transition-transform group-hover:-translate-x-1" />
          Volver a Organizaciones
        </Link>

        {/* Org header card */}
        <div className="rounded-2xl border border-white bg-white shadow-sm p-5 flex items-start gap-4">
          {type && (
            <div
              className="h-12 w-12 rounded-2xl shrink-0 flex items-center justify-center text-white text-xl font-bold shadow-sm"
              style={{ backgroundColor: type.color }}
            >
              {org.name[0].toUpperCase()}
            </div>
          )}
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-3 flex-wrap">
              <h1 className="text-xl font-bold text-slate-900">{org.name}</h1>
              {type && (
                <span
                  className="inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold text-white"
                  style={{ backgroundColor: type.color }}
                >
                  {type.name}
                </span>
              )}
              <span className={`text-xs px-2 py-0.5 rounded-full font-semibold ${
                org.status === 'active' ? 'bg-emerald-100 text-emerald-700' : 'bg-slate-100 text-slate-500'
              }`}>
                {org.status}
              </span>
            </div>
            {org.description && (
              <p className="text-sm text-slate-500 mt-1">{org.description}</p>
            )}
            <p className="text-xs text-slate-400 mt-1">
              {org.wallet_count} wallet{org.wallet_count !== 1 ? 's' : ''} · Creada {fmtDateShort(org.created_at)}
            </p>
          </div>
        </div>

        {/* Tabs */}
        <div className="flex gap-1 p-1 bg-slate-100 rounded-xl w-fit">
          {([
            { key: 'assets',  label: 'Colección NFT', icon: <Package className="h-4 w-4" /> },
            { key: 'wallets', label: 'Wallets',        icon: <Wallet className="h-4 w-4" /> },
          ] as { key: Tab; label: string; icon: React.ReactNode }[]).map(({ key, label, icon }) => (
            <button
              key={key}
              onClick={() => setTab(key)}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-semibold transition-all ${
                tab === key
                  ? 'bg-white text-slate-900 shadow-sm'
                  : 'text-slate-500 hover:text-slate-700'
              }`}
            >
              {icon}
              {label}
            </button>
          ))}
        </div>

        {/* Tab content */}
        {tab === 'assets' ? (
          <AssetsTab orgId={id} onMintNFT={() => setShowMint(true)} />
        ) : (
          <WalletsTab orgId={id} onAddWallet={() => setShowGenWallet(true)} />
        )}
      </div>

      <MintNFTModal
        open={showMint}
        onClose={() => setShowMint(false)}
        preSelectedOrgId={id}
      />

      <GenerateWalletModal
        open={showGenWallet}
        onClose={() => setShowGenWallet(false)}
        preSelectedOrgId={id}
      />
    </div>
  )
}
