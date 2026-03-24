import { useState } from 'react'
import { useParams, Link, useNavigate } from 'react-router-dom'
import { ArrowLeft, Copy, Check, Package, Coins, Building2, RefreshCw } from 'lucide-react'
import { useQuery } from '@tanstack/react-query'
import { useWallet, useUpdateWallet } from '@/hooks/useWallets'
import { useOrganizations } from '@/hooks/useTaxonomy'
import { useAssetList } from '@/hooks/useAssets'
import { api } from '@/lib/api'
import { Topbar } from '@/components/layout/Topbar'
import { Button } from '@/components/ui/button'
import { WalletStatusBadge, StateBadge } from '@/components/domain-badges'
import { Spinner, EmptyState } from '@/components/ui/Misc'
import { useToast } from '@/store/toast'
import { copyToClipboard, fmtDateShort, shortPubkey } from '@/lib/utils'
import type { WalletStatus } from '@/types/api'

function lamportsToSol(lamports: number | null | undefined): string {
  if (lamports == null) return '—'
  return (lamports / 1_000_000_000).toFixed(4)
}

export function WalletDetailPage() {
  const { id = '' } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const toast = useToast()
  const [copied, setCopied] = useState(false)

  const { data: wallet, isLoading, refetch, isFetching } = useWallet(id)
  const updateWallet = useUpdateWallet()

  // Org lookup
  const { data: orgsData } = useOrganizations()
  const orgs = orgsData?.items ?? []
  const org = wallet?.organization_id ? orgs.find((o) => o.id === wallet.organization_id) : undefined

  // Solana balance
  const { data: accountData, isLoading: accountLoading, refetch: refetchAccount } = useQuery({
    queryKey: ['solana', 'account', wallet?.wallet_pubkey],
    queryFn: () => api.solana.account(wallet!.wallet_pubkey),
    enabled: Boolean(wallet?.wallet_pubkey),
    staleTime: 30_000,
  })

  // Assets in custody
  const { data: assetsData, isLoading: assetsLoading } = useAssetList(
    wallet ? { custodian: wallet.wallet_pubkey, limit: 200 } : undefined
  )
  const assets = assetsData?.items ?? []

  const handleCopy = async () => {
    if (!wallet) return
    await copyToClipboard(wallet.wallet_pubkey)
    setCopied(true)
    setTimeout(() => setCopied(false), 1500)
  }

  const handleStatusChange = async (status: WalletStatus) => {
    try {
      await updateWallet.mutateAsync({ id, data: { status } })
      toast.success(`Estado actualizado a ${status}`)
    } catch {
      toast.error('Error al actualizar estado')
    }
  }

  if (isLoading) {
    return (
      <div className="flex flex-col flex-1 overflow-hidden">
        <Topbar title="Wallet" />
        <div className="flex justify-center py-20"><Spinner /></div>
      </div>
    )
  }

  if (!wallet) {
    return (
      <div className="flex flex-col flex-1 overflow-hidden">
        <Topbar title="Wallet no encontrada" />
        <EmptyState
          title="Wallet no encontrada"
          action={<Link to="/wallets"><Button>Volver a Wallets</Button></Link>}
        />
      </div>
    )
  }

  return (
    <div className="flex flex-col flex-1 overflow-hidden">
      <Topbar
        title={wallet.name ?? shortPubkey(wallet.wallet_pubkey)}
        subtitle="Detalle de wallet custodio"
        actions={
          <Button variant="ghost" size="icon" onClick={() => { refetch(); refetchAccount() }} title="Actualizar">
            <RefreshCw className={`h-4 w-4 ${isFetching ? 'animate-spin' : ''}`} />
          </Button>
        }
      />

      <div className="flex-1 overflow-y-auto p-6 space-y-6">
        {/* Back */}
        <Link
          to="/wallets"
          className="inline-flex items-center gap-2 text-sm font-semibold text-slate-500 hover:text-primary transition-colors group"
        >
          <ArrowLeft className="h-4 w-4 transition-transform group-hover:-translate-x-1" />
          Volver a Wallets
        </Link>

        {/* Main info card */}
        <div className="rounded-2xl border border-white bg-white shadow-sm p-5">
          <div className="flex items-start justify-between gap-4 flex-wrap">
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-3 flex-wrap mb-2">
                <h1 className="text-xl font-bold text-slate-900">
                  {wallet.name ?? shortPubkey(wallet.wallet_pubkey)}
                </h1>
                <WalletStatusBadge status={wallet.status} />
              </div>

              {/* Pubkey row */}
              <div className="flex items-center gap-2 mb-2">
                <span className="font-mono text-sm text-primary break-all">{wallet.wallet_pubkey}</span>
                <button
                  onClick={handleCopy}
                  className="shrink-0 text-slate-400 hover:text-slate-700 transition-colors"
                  title="Copiar clave pública"
                >
                  {copied
                    ? <Check className="h-4 w-4 text-emerald-500" />
                    : <Copy className="h-4 w-4" />
                  }
                </button>
              </div>

              {/* Org link */}
              {org ? (
                <button
                  onClick={() => navigate(`/organizations/${org.id}`)}
                  className="flex items-center gap-1.5 text-sm text-slate-500 hover:text-primary transition-colors"
                >
                  <Building2 className="h-3.5 w-3.5" />
                  {org.name}
                </button>
              ) : (
                <span className="text-xs text-slate-400">Sin organización asignada</span>
              )}

              <p className="text-xs text-slate-400 mt-2">
                Creada {fmtDateShort(wallet.created_at)}
              </p>
            </div>

            {/* Status actions */}
            <div className="flex flex-col gap-1.5 shrink-0">
              <p className="text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-0.5">Cambiar estado</p>
              {wallet.status !== 'active' && (
                <Button size="sm" variant="ghost" onClick={() => handleStatusChange('active')} className="justify-start">
                  Activar
                </Button>
              )}
              {wallet.status !== 'suspended' && (
                <Button size="sm" variant="ghost" onClick={() => handleStatusChange('suspended')} className="justify-start text-amber-600 hover:bg-amber-50">
                  Suspender
                </Button>
              )}
              {wallet.status !== 'revoked' && (
                <Button size="sm" variant="ghost" onClick={() => handleStatusChange('revoked')} className="justify-start text-red-600 hover:bg-red-50">
                  Revocar
                </Button>
              )}
            </div>
          </div>
        </div>

        {/* Balance card */}
        <div className="rounded-2xl border border-slate-200 bg-white p-5">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <div className="h-8 w-8 rounded-xl bg-primary/10 flex items-center justify-center">
                <Coins className="h-4 w-4 text-primary" />
              </div>
              <p className="text-sm font-semibold text-slate-700">Balance Solana</p>
            </div>
            <button
              onClick={() => refetchAccount()}
              className="text-slate-400 hover:text-slate-600 transition-colors"
              title="Actualizar balance"
            >
              <RefreshCw className="h-3.5 w-3.5" />
            </button>
          </div>

          {accountLoading ? (
            <div className="flex items-center gap-2 text-slate-400">
              <Spinner className="h-4 w-4" />
              <span className="text-sm">Consultando red...</span>
            </div>
          ) : (
            <div className="flex items-baseline gap-2">
              <span className="text-3xl font-extrabold text-slate-900">
                {lamportsToSol(accountData?.lamports)}
              </span>
              <span className="text-sm font-medium text-slate-500">SOL</span>
              {accountData?.simulated && (
                <span className="text-xs text-amber-600 bg-amber-50 border border-amber-200 rounded-full px-2 py-0.5 font-medium ml-2">
                  Simulado
                </span>
              )}
            </div>
          )}

          {accountData && (
            <p className="text-xs text-slate-400 mt-1">
              {accountData.lamports?.toLocaleString() ?? '—'} lamports
            </p>
          )}
        </div>

        {/* Assets in custody */}
        <div>
          <div className="flex items-center gap-2 mb-4">
            <div className="h-8 w-8 rounded-xl bg-purple-50 flex items-center justify-center">
              <Package className="h-4 w-4 text-purple-500" />
            </div>
            <p className="text-sm font-semibold text-slate-700">Activos en custodia</p>
          </div>

          {assetsLoading ? (
            <div className="flex justify-center py-8"><Spinner /></div>
          ) : assets.length === 0 ? (
            <EmptyState
              title="Sin activos en custodia"
              description="Esta wallet no tiene activos en su poder actualmente."
            />
          ) : (
            <div className="flex flex-col gap-2">
              {assets.map((a) => (
                <button
                  key={a.id}
                  onClick={() => navigate(`/assets/${a.id}`)}
                  className="flex items-center gap-4 p-4 rounded-xl border border-slate-200 bg-white hover:border-primary/50 hover:shadow-sm transition-all text-left group"
                >
                  <div className="text-2xl shrink-0">
                    {a.product_type === 'cafe' || a.product_type === 'café' ? '☕' :
                     a.product_type === 'arroz' ? '🌾' :
                     a.product_type === 'maiz' || a.product_type === 'maíz' ? '🌽' :
                     a.product_type === 'cacao' ? '🍫' : '📦'}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-semibold text-slate-800 group-hover:text-primary transition-colors truncate">
                      {typeof a.metadata?.name === 'string' ? a.metadata.name : a.product_type}
                    </p>
                    <p className="text-xs text-slate-400 font-mono">{shortPubkey(a.asset_mint)}</p>
                  </div>
                  <StateBadge state={a.state} />
                  <p className="text-xs text-slate-400 whitespace-nowrap tabular-nums hidden sm:block">
                    {fmtDateShort(a.updated_at)}
                  </p>
                </button>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
