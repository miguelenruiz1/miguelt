import { useState } from 'react'
import { Copy, Check, MoreHorizontal, ShieldOff, ShieldCheck, ShieldX } from 'lucide-react'
import { useUpdateWallet } from '@/hooks/useWallets'
import { useToast } from '@/store/toast'
import { copyToClipboard, fmtDateShort, shortPubkey } from '@/lib/utils'
import { Link } from 'react-router-dom'
import { WalletStatusBadge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import type { Organization, Wallet, WalletStatus } from '@/types/api'

export function WalletTable({ wallets, orgs = [] }: { wallets: Wallet[]; orgs?: Organization[] }) {
  const update = useUpdateWallet()
  const toast = useToast()
  const orgMap = new Map(orgs.map((o) => [o.id, o]))

  const handleStatusChange = async (id: string, status: WalletStatus) => {
    try {
      await update.mutateAsync({ id, data: { status } })
      const labels: Record<string, string> = { active: 'activada', suspended: 'suspendida', revoked: 'revocada' }
      toast.success(`Wallet ${labels[status] ?? status}`)
    } catch {
      toast.error('Error al actualizar estado de wallet')
    }
  }

  if (!wallets.length) return (
    <div className="text-center py-12 text-slate-400 text-sm">Sin wallets registradas.</div>
  )

  return (
    <>
      {/* Mobile cards */}
      <div className="space-y-3 p-4 md:hidden">
        {wallets.map((w) => (
          <WalletCard key={w.id} wallet={w} orgMap={orgMap} onStatusChange={handleStatusChange} />
        ))}
      </div>

      {/* Desktop table */}
      <div className="hidden md:block overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-slate-50/50 backdrop-blur-sm border-b border-slate-100/50">
              {['Nombre', 'Llave Pública', 'Organización', 'Etiquetas', 'Estado', 'Creación', 'Acciones'].map((h) => (
                <th key={h} className="px-4 py-3 text-left text-[10px] font-semibold text-slate-500 uppercase tracking-widest whitespace-nowrap">
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100/40">
            {wallets.map((w) => (
              <WalletRow key={w.id} wallet={w} orgMap={orgMap} onStatusChange={handleStatusChange} />
            ))}
          </tbody>
        </table>
      </div>
    </>
  )
}

function WalletRow({
  wallet: w,
  orgMap,
  onStatusChange,
}: {
  wallet: Wallet
  orgMap: Map<string, Organization>
  onStatusChange: (id: string, status: WalletStatus) => void
}) {
  const [copied, setCopied] = useState(false)
  const [menuOpen, setMenuOpen] = useState(false)

  const org = w.organization_id ? orgMap.get(w.organization_id) : undefined

  const handleCopy = async () => {
    await copyToClipboard(w.wallet_pubkey)
    setCopied(true)
    setTimeout(() => setCopied(false), 1500)
  }

  return (
    <tr className="hover:bg-white transition-all duration-300 group hover:shadow-[0_2px_10px_-4px_rgba(0,0,0,0.05)]">
      {/* Name */}
      <td className="px-4 py-3">
        <Link to={`/wallets/${w.id}`} className="text-sm font-medium text-indigo-600 hover:text-indigo-800 hover:underline truncate max-w-[120px] block">
          {w.name ?? shortPubkey(w.wallet_pubkey)}
        </Link>
      </td>

      {/* Pubkey */}
      <td className="px-4 py-3">
        <div className="flex items-center gap-2">
          <Link to={`/assets?q=${w.wallet_pubkey}`} className="font-mono text-xs text-indigo-600 hover:text-indigo-800 font-medium hover:underline" title={w.wallet_pubkey}>
            {shortPubkey(w.wallet_pubkey)}
          </Link>
          <button
            onClick={handleCopy}
            className="opacity-0 group-hover:opacity-100 transition-opacity text-slate-400 hover:text-slate-700"
          >
            {copied
              ? <Check className="h-3.5 w-3.5 text-emerald-500" />
              : <Copy className="h-3.5 w-3.5" />
            }
          </button>
        </div>
      </td>

      {/* Organization */}
      <td className="px-4 py-3">
        {org ? (
          <span className="text-xs text-slate-600 font-medium">{org.name}</span>
        ) : (
          <span className="text-slate-300 text-xs">—</span>
        )}
      </td>

      {/* Tags */}
      <td className="px-4 py-3">
        <div className="flex flex-wrap gap-1.5">
          {w.tags.length > 0
            ? w.tags.map((t) => (
              <span key={t} className="rounded-md bg-white border border-slate-200/60 shadow-sm px-2 py-0.5 text-xs font-medium text-slate-600">
                {t}
              </span>
            ))
            : <span className="text-slate-300 text-xs">—</span>
          }
        </div>
      </td>

      {/* Status */}
      <td className="px-4 py-3"><WalletStatusBadge status={w.status} /></td>

      {/* Created */}
      <td className="px-4 py-3 text-xs text-slate-400 whitespace-nowrap tabular-nums">
        {fmtDateShort(w.created_at)}
      </td>

      {/* Actions */}
      <td className="px-4 py-3">
        <div className="relative">
          <Button variant="ghost" size="icon" onClick={() => setMenuOpen((o) => !o)}>
            <MoreHorizontal className="h-4 w-4" />
          </Button>

          {menuOpen && (
            <>
              <div className="fixed inset-0 z-10" onClick={() => setMenuOpen(false)} />
              <div className="absolute right-0 top-10 z-20 w-44 rounded-xl border border-slate-200 bg-white shadow-card-lg py-1 overflow-hidden">
                {w.status !== 'active' && (
                  <MenuItem icon={<ShieldCheck className="h-4 w-4 text-emerald-600" />} label="Activar" onClick={() => { onStatusChange(w.id, 'active'); setMenuOpen(false) }} />
                )}
                {w.status !== 'suspended' && (
                  <MenuItem icon={<ShieldOff className="h-4 w-4 text-amber-600" />} label="Suspender" onClick={() => { onStatusChange(w.id, 'suspended'); setMenuOpen(false) }} />
                )}
                {w.status !== 'revoked' && (
                  <MenuItem icon={<ShieldX className="h-4 w-4 text-red-600" />} label="Revocar" onClick={() => { onStatusChange(w.id, 'revoked'); setMenuOpen(false) }} />
                )}
              </div>
            </>
          )}
        </div>
      </td>
    </tr>
  )
}

function WalletCard({
  wallet: w,
  orgMap,
  onStatusChange,
}: {
  wallet: Wallet
  orgMap: Map<string, Organization>
  onStatusChange: (id: string, status: WalletStatus) => void
}) {
  const [menuOpen, setMenuOpen] = useState(false)
  const org = w.organization_id ? orgMap.get(w.organization_id) : undefined

  return (
    <div className="rounded-xl border border-gray-200 bg-white p-4 shadow-sm space-y-2">
      <div className="flex items-center justify-between">
        <Link to={`/wallets/${w.id}`} className="text-sm font-medium text-indigo-600 hover:text-indigo-800 hover:underline truncate">
          {w.name ?? shortPubkey(w.wallet_pubkey)}
        </Link>
        <WalletStatusBadge status={w.status} />
      </div>
      <div className="flex items-center justify-between text-xs">
        <span className="text-slate-500">Llave Pública</span>
        <Link to={`/assets?q=${w.wallet_pubkey}`} className="font-mono text-indigo-600 hover:text-indigo-800 hover:underline" title={w.wallet_pubkey}>
          {shortPubkey(w.wallet_pubkey)}
        </Link>
      </div>
      {org && (
        <div className="flex items-center justify-between text-xs">
          <span className="text-slate-500">Organización</span>
          <span className="text-slate-600 font-medium">{org.name}</span>
        </div>
      )}
      {w.tags.length > 0 && (
        <div className="flex flex-wrap gap-1">
          {w.tags.map((t) => (
            <span key={t} className="rounded-md bg-white border border-slate-200/60 shadow-sm px-2 py-0.5 text-xs font-medium text-slate-600">
              {t}
            </span>
          ))}
        </div>
      )}
      <div className="flex items-center justify-between text-xs">
        <span className="text-slate-400">{fmtDateShort(w.created_at)}</span>
        <div className="relative">
          <Button variant="ghost" size="icon" onClick={() => setMenuOpen((o) => !o)}>
            <MoreHorizontal className="h-4 w-4" />
          </Button>
          {menuOpen && (
            <>
              <div className="fixed inset-0 z-10" onClick={() => setMenuOpen(false)} />
              <div className="absolute right-0 bottom-10 z-20 w-44 rounded-xl border border-slate-200 bg-white shadow-card-lg py-1 overflow-hidden">
                {w.status !== 'active' && (
                  <MenuItem icon={<ShieldCheck className="h-4 w-4 text-emerald-600" />} label="Activar" onClick={() => { onStatusChange(w.id, 'active'); setMenuOpen(false) }} />
                )}
                {w.status !== 'suspended' && (
                  <MenuItem icon={<ShieldOff className="h-4 w-4 text-amber-600" />} label="Suspender" onClick={() => { onStatusChange(w.id, 'suspended'); setMenuOpen(false) }} />
                )}
                {w.status !== 'revoked' && (
                  <MenuItem icon={<ShieldX className="h-4 w-4 text-red-600" />} label="Revocar" onClick={() => { onStatusChange(w.id, 'revoked'); setMenuOpen(false) }} />
                )}
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  )
}

function MenuItem({ icon, label, onClick }: { icon: React.ReactNode; label: string; onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      className="flex items-center gap-2.5 w-full px-3 py-2.5 text-sm text-slate-700 hover:bg-slate-50 transition-colors"
    >
      {icon}
      {label}
    </button>
  )
}
