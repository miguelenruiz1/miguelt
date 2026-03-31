import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Plus, Search, RefreshCw, Wallet, KeyRound, Copy, Check, ChevronRight, ShieldCheck, ShieldOff, ShieldX, MoreHorizontal } from 'lucide-react'
import { Topbar } from '@/components/layout/Topbar'
import { Button } from '@/components/ui/button'
import { Spinner, EmptyState } from '@/components/ui/Misc'
import { WalletStatusBadge } from '@/components/domain-badges'
import { RegisterWalletModal } from '@/components/wallets/RegisterWalletModal'
import { GenerateWalletModal } from '@/components/wallets/GenerateWalletModal'
import { useWalletList, useUpdateWallet } from '@/hooks/useWallets'
import { useOrganizations } from '@/hooks/useTaxonomy'
import { shortPubkey, fmtDateShort, copyToClipboard } from '@/lib/utils'
import { useToast } from '@/store/toast'
import type { Wallet as WalletType, WalletStatus } from '@/types/api'

const fieldCls = 'rounded-xl border border-white/60 bg-white/50 backdrop-blur-md px-4 py-2.5 text-sm font-medium text-slate-800 placeholder:text-slate-400 hover:bg-white/70 hover:border-primary/50 focus:bg-white focus:border-primary focus:ring-2 focus:ring-ring/20 focus:outline-none transition-all shadow-sm'

export function WalletsPage() {
  const [showRegister, setShowRegister] = useState(false)
  const [showGenerate, setShowGenerate] = useState(false)
  const [search, setSearch] = useState('')
  const [status, setStatus] = useState('')

  const { data, isLoading, isFetching, refetch } = useWalletList({
    status: status || undefined,
    limit: 200,
  })
  const { data: orgsData } = useOrganizations()
  const orgs = orgsData?.items ?? []
  const orgMap = new Map(orgs.map((o) => [o.id, o]))

  const wallets: WalletType[] = (data?.items ?? []).filter((w) =>
    !search ||
    w.wallet_pubkey.toLowerCase().includes(search.toLowerCase()) ||
    (w.name ?? '').toLowerCase().includes(search.toLowerCase()) ||
    w.tags.some((t) => t.toLowerCase().includes(search.toLowerCase())) ||
    (w.organization_id && orgMap.get(w.organization_id)?.name.toLowerCase().includes(search.toLowerCase()))
  )

  return (
    <div className="flex flex-col flex-1 overflow-hidden">
      <Topbar
        title="Custodios"
        subtitle={`${data?.total ?? 0} wallets`}
        actions={
          <div className="flex gap-2">
            <Button size="sm" variant="secondary" onClick={() => setShowRegister(true)}>
              <Plus className="h-4 w-4" /> Registrar Externa
            </Button>
            <Button size="sm" onClick={() => setShowGenerate(true)}>
              <KeyRound className="h-4 w-4" /> Crear Wallet
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
              placeholder="Buscar nombre, llave, organización o etiqueta..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className={`${fieldCls} pl-9 w-full`}
            />
          </div>
          <select
            value={status}
            onChange={(e) => setStatus(e.target.value)}
            className={fieldCls}
          >
            <option value="">Todos los estados</option>
            <option value="active">Activa</option>
            <option value="suspended">Suspendida</option>
            <option value="revoked">Revocada</option>
          </select>
          <Button variant="ghost" size="icon" onClick={() => refetch()} title="Actualizar">
            <RefreshCw className={`h-4 w-4 ${isFetching ? 'animate-spin' : ''}`} />
          </Button>
        </div>

        {/* Table */}
        {isLoading ? (
          <div className="flex justify-center py-16"><Spinner /></div>
        ) : wallets.length === 0 ? (
          <EmptyState
            icon={<Wallet className="h-10 w-10" />}
            title="Sin custodios"
            description="Crea una wallet para registrar un custodio logístico (Granja, Camión, Bodega, Aduana)."
            action={
              <Button size="sm" onClick={() => setShowGenerate(true)}>
                <KeyRound className="h-4 w-4" /> Crear primera wallet
              </Button>
            }
          />
        ) : (
          <div className="bg-white rounded-xl border overflow-hidden shadow-sm">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Nombre</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Llave Pública</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Organización</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Etiquetas</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Estado</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Creación</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Acciones</th>
                  <th className="px-4 py-3" />
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {wallets.map((w) => (
                  <WalletRow key={w.id} wallet={w} orgMap={orgMap} />
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <RegisterWalletModal open={showRegister} onClose={() => setShowRegister(false)} />
      <GenerateWalletModal open={showGenerate} onClose={() => setShowGenerate(false)} />
    </div>
  )
}

function WalletRow({ wallet: w, orgMap }: { wallet: WalletType; orgMap: Map<string, { name: string }> }) {
  const [copied, setCopied] = useState(false)
  const [menuOpen, setMenuOpen] = useState(false)
  const update = useUpdateWallet()
  const toast = useToast()

  const org = w.organization_id ? orgMap.get(w.organization_id) : undefined

  const handleCopy = async () => {
    await copyToClipboard(w.wallet_pubkey)
    setCopied(true)
    setTimeout(() => setCopied(false), 1500)
  }

  const handleStatus = async (status: WalletStatus) => {
    try {
      await update.mutateAsync({ id: w.id, data: { status } })
      const labels: Record<string, string> = { active: 'activada', suspended: 'suspendida', revoked: 'revocada' }
      toast.success(`Wallet ${labels[status] ?? status}`)
    } catch {
      toast.error('Error al actualizar estado')
    }
    setMenuOpen(false)
  }

  return (
    <tr className="hover:bg-gray-50 transition-colors group">
      <td className="px-4 py-3">
        <Link to={`/wallets/${w.id}`} className="flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-primary/10 shrink-0">
            <Wallet className="h-4 w-4 text-primary" />
          </div>
          <span className="text-sm font-semibold text-gray-900 group-hover:text-primary transition-colors truncate max-w-40">
            {w.name || shortPubkey(w.wallet_pubkey)}
          </span>
        </Link>
      </td>
      <td className="px-4 py-3">
        <div className="flex items-center gap-2">
          <span className="font-mono text-xs text-gray-600" title={w.wallet_pubkey}>
            {shortPubkey(w.wallet_pubkey)}
          </span>
          <button onClick={handleCopy} className="opacity-0 group-hover:opacity-100 transition-opacity text-gray-400 hover:text-gray-700">
            {copied ? <Check className="h-3.5 w-3.5 text-emerald-500" /> : <Copy className="h-3.5 w-3.5" />}
          </button>
        </div>
      </td>
      <td className="px-4 py-3">
        {org ? (
          <span className="text-sm text-gray-700">{org.name}</span>
        ) : (
          <span className="text-gray-300 text-sm">—</span>
        )}
      </td>
      <td className="px-4 py-3">
        <div className="flex flex-wrap gap-1">
          {w.tags.length > 0
            ? w.tags.map((t) => (
              <span key={t} className="rounded-md bg-gray-100 px-2 py-0.5 text-xs font-medium text-gray-600">
                {t}
              </span>
            ))
            : <span className="text-gray-300 text-sm">—</span>
          }
        </div>
      </td>
      <td className="px-4 py-3">
        <WalletStatusBadge status={w.status} />
      </td>
      <td className="px-4 py-3">
        <span className="text-xs text-gray-500">{fmtDateShort(w.created_at)}</span>
      </td>
      <td className="px-4 py-3">
        <div className="relative">
          <button onClick={() => setMenuOpen(o => !o)} className="flex h-8 w-8 items-center justify-center rounded-lg hover:bg-gray-100 transition-colors">
            <MoreHorizontal className="h-4 w-4 text-gray-400" />
          </button>
          {menuOpen && (
            <>
              <div className="fixed inset-0 z-10" onClick={() => setMenuOpen(false)} />
              <div className="absolute right-0 top-10 z-20 w-40 rounded-lg border bg-white shadow-lg py-1">
                {w.status !== 'active' && (
                  <button onClick={() => handleStatus('active')} className="flex items-center gap-2 w-full px-3 py-2 text-sm text-gray-700 hover:bg-gray-50">
                    <ShieldCheck className="h-4 w-4 text-emerald-600" /> Activar
                  </button>
                )}
                {w.status !== 'suspended' && (
                  <button onClick={() => handleStatus('suspended')} className="flex items-center gap-2 w-full px-3 py-2 text-sm text-gray-700 hover:bg-gray-50">
                    <ShieldOff className="h-4 w-4 text-amber-600" /> Suspender
                  </button>
                )}
                {w.status !== 'revoked' && (
                  <button onClick={() => handleStatus('revoked')} className="flex items-center gap-2 w-full px-3 py-2 text-sm text-red-600 hover:bg-red-50">
                    <ShieldX className="h-4 w-4" /> Revocar
                  </button>
                )}
              </div>
            </>
          )}
        </div>
      </td>
      <td className="px-4 py-3">
        <Link to={`/wallets/${w.id}`} className="flex h-7 w-7 items-center justify-center rounded-full hover:bg-gray-100 transition-colors">
          <ChevronRight className="h-4 w-4 text-gray-400" />
        </Link>
      </td>
    </tr>
  )
}
