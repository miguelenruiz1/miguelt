import { useState } from 'react'
import { Topbar } from '@/components/layout/Topbar'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card, Spinner } from '@/components/ui/misc'
import { useLiveness, useReadiness, useSolanaAccount, useSolanaTx } from '@/hooks/useHealth'
import { useAdminStore } from '@/store/admin'
import { CheckCircle2, AlertCircle, Search, RefreshCw, Link2, KeyRound, Eye, EyeOff, Check, Shield } from 'lucide-react'
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
        subtitle="Configuración de plataforma, blockchain y herramientas Solana"
        actions={
          <Button variant="ghost" size="sm" onClick={() => { refetchH(); refetchR(); }}>
            <RefreshCw className="h-4 w-4" /> Actualizar
          </Button>
        }
      />

      <div className="flex-1 overflow-y-auto p-6 space-y-6">

        {/* Blockchain Admin Key */}
        <BlockchainConfigCard />

        {/* Health */}
        <Card>
          <h2 className="text-sm font-semibold text-foreground mb-4">Verificaciones de Salud</h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <HealthRow label="API activa" value={health?.status} loading={hLoading} />
            {ready?.checks && Object.entries(ready.checks).map(([k, v]) => (
              <HealthRow key={k} label={k} value={v} loading={rLoading} />
            ))}
          </div>
        </Card>

        {/* Solana account */}
        <Card>
          <h2 className="text-sm font-semibold text-foreground mb-4 flex items-center gap-2">
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
          <h2 className="text-sm font-semibold text-foreground mb-4 flex items-center gap-2">
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

/* ─── Blockchain Config Card ──────────────────────────────────────────────── */

function BlockchainConfigCard() {
  const { adminKey, setAdminKey } = useAdminStore()
  const [draft, setDraft] = useState('')
  const [showKey, setShowKey] = useState(false)
  const [saved, setSaved] = useState(false)

  function handleSave() {
    setAdminKey(draft.trim())
    setDraft('')
    setSaved(true)
    setTimeout(() => setSaved(false), 3000)
  }

  function handleClear() {
    setAdminKey('')
    setDraft('')
  }

  return (
    <Card>
      <div className="flex items-center gap-3 mb-4">
        <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-amber-100">
          <Shield className="h-5 w-5 text-amber-600" />
        </div>
        <div>
          <h2 className="text-sm font-semibold text-foreground">Clave de Blockchain</h2>
          <p className="text-xs text-muted-foreground">Requerida para operaciones de liberación y anclaje en Solana</p>
        </div>
        {adminKey && (
          <span className="ml-auto inline-flex items-center gap-1 rounded-full bg-emerald-50 px-2.5 py-0.5 text-xs font-semibold text-emerald-600">
            <Check className="h-3 w-3" /> Configurada
          </span>
        )}
      </div>

      <div className="flex gap-2">
        <div className="relative flex-1">
          <input
            type={showKey ? 'text' : 'password'}
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            placeholder={adminKey ? '(dejar vacío para mantener)' : 'Ingresa TRACE_ADMIN_KEY...'}
            className="h-10 w-full rounded-xl border border-border bg-card px-3 pr-10 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-ring/20 focus:border-ring"
          />
          <button
            type="button"
            onClick={() => setShowKey(v => !v)}
            className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-muted-foreground"
          >
            {showKey ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
          </button>
        </div>
        <Button size="md" onClick={handleSave} disabled={!draft.trim()}>
          <KeyRound className="h-4 w-4" /> Guardar
        </Button>
        {adminKey && (
          <Button size="md" variant="ghost" onClick={handleClear} className="text-red-500 hover:text-red-700 hover:bg-red-50">
            Limpiar
          </Button>
        )}
      </div>

      {saved && (
        <p className="mt-2 text-xs text-emerald-600 flex items-center gap-1">
          <Check className="h-3.5 w-3.5" /> Clave guardada en localStorage
        </p>
      )}

      <p className="mt-2 text-xs text-muted-foreground">
        Debe coincidir con TRACE_ADMIN_KEY en el .env del backend. Se almacena en localStorage del navegador.
      </p>
    </Card>
  )
}

/* ─── Helpers ──────────────────────────────────────────────────────────────── */

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
        <span className="text-sm text-foreground">{label}</span>
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
      <p className="text-xs text-muted-foreground mb-2">{badge}</p>
      <pre className="rounded-xl bg-muted border border-border p-4 text-xs text-foreground overflow-x-auto font-mono">
        {JSON.stringify(data, null, 2)}
      </pre>
    </div>
  )
}
