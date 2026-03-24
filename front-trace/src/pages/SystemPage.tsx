import { useState } from 'react'
import { Topbar } from '@/components/layout/Topbar'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card, Spinner } from '@/components/ui/Misc'
import { useLiveness, useReadiness, useSolanaAccount, useSolanaTx } from '@/hooks/useHealth'
import { CheckCircle2, AlertCircle, Search, RefreshCw, Link2 } from 'lucide-react'
import { cn } from '@/lib/utils'

export function SystemPage() {
  const { data: health, isLoading: hLoading, refetch: refetchH } = useLiveness()
  const { data: ready,  isLoading: rLoading, refetch: refetchR } = useReadiness()

  const [pubkey,      setPubkey]      = useState('')
  const [pubkeyInput, setPubkeyInput] = useState('')
  const [sig,         setSig]         = useState('')
  const [sigInput,    setSigInput]    = useState('')

  const { data: account, isLoading: aLoading } = useSolanaAccount(pubkey)
  const { data: tx,      isLoading: tLoading  } = useSolanaTx(sig)

  return (
    <div className="flex flex-col flex-1 overflow-hidden">
      <Topbar
        title="Sistema"
        subtitle="Verificaciones de salud y herramientas Solana"
        actions={
          <Button variant="ghost" size="sm" onClick={() => { refetchH(); refetchR(); }}>
            <RefreshCw className="h-4 w-4" /> Actualizar
          </Button>
        }
      />

      <div className="flex-1 overflow-y-auto p-6 space-y-6">

        {/* Health */}
        <Card>
          <h2 className="text-sm font-semibold text-slate-800 mb-4">Verificaciones de Salud</h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <HealthRow label="API activa" value={health?.status} loading={hLoading} />
            {ready?.checks && Object.entries(ready.checks).map(([k, v]) => (
              <HealthRow key={k} label={k} value={v} loading={rLoading} />
            ))}
          </div>
        </Card>

        {/* Solana account */}
        <Card>
          <h2 className="text-sm font-semibold text-slate-800 mb-4 flex items-center gap-2">
            <Link2 className="h-4 w-4 text-primary" />
            Consulta de Cuenta Solana
          </h2>
          <div className="flex gap-2 mb-4">
            <Input className="flex-1" placeholder="Ingresa llave pública Solana..." value={pubkeyInput} onChange={(e) => setPubkeyInput(e.target.value)} />
            <Button size="md" variant="secondary" onClick={() => setPubkey(pubkeyInput.trim())}>
              <Search className="h-4 w-4" /> Consultar
            </Button>
          </div>
          {aLoading && <Spinner />}
          {account && <JsonBlock data={account} badge={account.simulated ? '⚡ Simulado' : '🔗 En vivo'} />}
        </Card>

        {/* Solana TX */}
        <Card>
          <h2 className="text-sm font-semibold text-slate-800 mb-4 flex items-center gap-2">
            <Link2 className="h-4 w-4 text-primary" />
            Estado de Transacción
          </h2>
          <div className="flex gap-2 mb-4">
            <Input className="flex-1" placeholder="Ingresa firma de transacción..." value={sigInput} onChange={(e) => setSigInput(e.target.value)} />
            <Button size="md" variant="secondary" onClick={() => setSig(sigInput.trim())}>
              <Search className="h-4 w-4" /> Consultar
            </Button>
          </div>
          {tLoading && <Spinner />}
          {tx && (
            <JsonBlock
              data={tx}
              badge={tx.simulated ? '⚡ Simulado' : (tx.err ? '❌ Error' : `✅ ${tx.confirmations ?? 0} confirmaciones`)}
            />
          )}
        </Card>
      </div>
    </div>
  )
}

function HealthRow({ label, value, loading }: { label: string; value?: string; loading: boolean }) {
  const ok = value === 'ok'
  return (
    <div className={cn(
      'flex items-center justify-between rounded-xl px-4 py-3 border',
      ok ? 'bg-emerald-50 border-emerald-200' : 'bg-red-50 border-red-200',
    )}>
      <div className="flex items-center gap-2">
        {loading
          ? <div className="h-4 w-4 rounded-full bg-slate-200 animate-pulse" />
          : ok
            ? <CheckCircle2 className="h-4 w-4 text-emerald-600" />
            : <AlertCircle  className="h-4 w-4 text-red-600" />
        }
        <span className="text-sm text-slate-700">{label}</span>
      </div>
      <span className={cn('text-xs font-mono font-medium', ok ? 'text-emerald-700' : 'text-red-700')}>
        {loading ? '…' : (value ?? 'desconocido')}
      </span>
    </div>
  )
}

function JsonBlock({ data, badge }: { data: unknown; badge: string }) {
  return (
    <div>
      <p className="text-xs text-slate-400 mb-2">{badge}</p>
      <pre className="rounded-xl bg-slate-50 border border-slate-200 p-4 text-xs text-slate-700 overflow-x-auto font-mono">
        {JSON.stringify(data, null, 2)}
      </pre>
    </div>
  )
}
