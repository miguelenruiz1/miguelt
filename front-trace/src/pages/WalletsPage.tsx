import { useState } from 'react'
import { Plus, Search, RefreshCw, Wallet, KeyRound } from 'lucide-react'
import { Topbar } from '@/components/layout/Topbar'
import { Button } from '@/components/ui/Button'
import { Spinner, EmptyState, Card } from '@/components/ui/Misc'
import { WalletTable } from '@/components/wallets/WalletTable'
import { RegisterWalletModal } from '@/components/wallets/RegisterWalletModal'
import { GenerateWalletModal } from '@/components/wallets/GenerateWalletModal'
import { useWalletList } from '@/hooks/useWallets'
import { useOrganizations } from '@/hooks/useTaxonomy'
import type { Wallet as WalletType } from '@/types/api'

const fieldCls = 'rounded-xl border border-white/60 bg-white/50 backdrop-blur-md px-4 py-2.5 text-sm font-medium text-slate-800 placeholder:text-slate-400 hover:bg-white/70 hover:border-indigo-300 focus:bg-white focus:border-indigo-500 focus:ring-4 focus:ring-indigo-500/10 focus:outline-none transition-all shadow-sm'

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

  const wallets: WalletType[] = (data?.items ?? []).filter((w) =>
    !search ||
    w.wallet_pubkey.toLowerCase().includes(search.toLowerCase()) ||
    (w.name ?? '').toLowerCase().includes(search.toLowerCase()) ||
    w.tags.some((t) => t.toLowerCase().includes(search.toLowerCase()))
  )

  // Group wallets by organization
  const orgMap = new Map(orgs.map((o) => [o.id, o]))
  const byOrg = new Map<string | null, WalletType[]>()

  for (const w of wallets) {
    const key = w.organization_id ?? null
    if (!byOrg.has(key)) byOrg.set(key, [])
    byOrg.get(key)!.push(w)
  }

  // Sort: orgs with name first, ungrouped last
  const sections: { label: string; wallets: WalletType[] }[] = []
  for (const [orgId, ws] of byOrg) {
    if (orgId === null) continue
    const org = orgMap.get(orgId)
    sections.push({ label: org?.name ?? orgId, wallets: ws })
  }
  sections.sort((a, b) => a.label.localeCompare(b.label))

  const unassigned = byOrg.get(null) ?? []

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
        <div className="flex gap-3 mb-5 flex-wrap">
          <div className="relative flex-1 min-w-48 max-w-xs">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-slate-400 pointer-events-none" />
            <input
              type="text"
              placeholder="Buscar nombre, llave o etiqueta..."
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
          <div className="flex flex-col gap-6">
            {/* Grouped sections */}
            {sections.map(({ label, wallets: ws }) => (
              <div key={label}>
                <p className="text-xs font-bold text-slate-500 uppercase tracking-widest mb-2 px-1">{label}</p>
                <Card className="p-0 overflow-hidden bg-white/70 shadow-[0_8px_30px_rgb(0,0,0,0.06)] border-none">
                  <WalletTable wallets={ws} orgs={orgs} />
                </Card>
              </div>
            ))}

            {/* Unassigned wallets */}
            {unassigned.length > 0 && (
              <div>
                <p className="text-xs font-bold text-slate-400 uppercase tracking-widest mb-2 px-1">Sin asignar</p>
                <Card className="p-0 overflow-hidden bg-white/70 shadow-[0_8px_30px_rgb(0,0,0,0.06)] border-none">
                  <WalletTable wallets={unassigned} orgs={orgs} />
                </Card>
              </div>
            )}
          </div>
        )}
      </div>

      <RegisterWalletModal open={showRegister} onClose={() => setShowRegister(false)} />
      <GenerateWalletModal open={showGenerate} onClose={() => setShowGenerate(false)} />
    </div>
  )
}
