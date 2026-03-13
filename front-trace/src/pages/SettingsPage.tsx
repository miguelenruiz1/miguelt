import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  Settings, KeyRound, Globe, Server, Eye, EyeOff,
  Copy, Check, ChevronDown, ChevronRight, AlertTriangle,
} from 'lucide-react'
import { Topbar } from '@/components/layout/Topbar'
import { Button } from '@/components/ui/Button'
import { useAdminStore } from '@/store/admin'
import { useSettingsStore, type SolanaCluster } from '@/store/settings'
import { api } from '@/lib/api'
import { copyToClipboard } from '@/lib/utils'
import { useToast } from '@/store/toast'

// ─── Generated service keypair (generated 2026-02-22 via trace-api docker container) ──
const GENERATED_KEYPAIR = {
  pubkey:      'GadeKRisiiYcjcSqWLhdx8V2BfGoJXX6WPsmsExB8pkN',
  secretB58:   '5LNxySiHfiMQMxAhJn8TjZumUbwRkuYNVvhMdMXiA3j2cVGBJU1SDRTCsqpFFFX6KZHqRjZpcNixUWzX7xysotxN',
}

const ENV_SNIPPET = `# ─── Solana (producción con keypair real) ────────────────────────────────────
SOLANA_RPC_URL=https://api.devnet.solana.com
SOLANA_KEYPAIR=${GENERATED_KEYPAIR.secretB58}
SOLANA_SIMULATION=false
SOLANA_COMMITMENT=confirmed`

// ─── Helpers ──────────────────────────────────────────────────────────────────

function CopyButton({ text, label = 'Copiar' }: { text: string; label?: string }) {
  const [copied, setCopied] = useState(false)
  const handle = async () => {
    await copyToClipboard(text)
    setCopied(true)
    setTimeout(() => setCopied(false), 1500)
  }
  return (
    <button
      onClick={handle}
      className="inline-flex items-center gap-1.5 text-xs font-semibold text-indigo-600 hover:text-indigo-800 transition-colors"
    >
      {copied ? <Check className="h-3.5 w-3.5 text-emerald-500" /> : <Copy className="h-3.5 w-3.5" />}
      {copied ? 'Copiado!' : label}
    </button>
  )
}

function Section({ icon, title, children }: { icon: React.ReactNode; title: string; children: React.ReactNode }) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white overflow-hidden">
      <div className="flex items-center gap-3 px-6 py-4 border-b border-slate-100 bg-slate-50/50">
        <div className="h-8 w-8 rounded-xl bg-indigo-50 flex items-center justify-center text-indigo-500 shrink-0">
          {icon}
        </div>
        <h2 className="text-sm font-bold text-slate-800">{title}</h2>
      </div>
      <div className="px-6 py-5">{children}</div>
    </div>
  )
}

// ─── Admin Key section ────────────────────────────────────────────────────────

function AdminKeySection() {
  const { adminKey, setAdminKey } = useAdminStore()
  const [draft, setDraft] = useState(adminKey)
  const [show, setShow] = useState(false)
  const [saved, setSaved] = useState(false)
  const toast = useToast()

  const handleSave = () => {
    setAdminKey(draft.trim())
    setSaved(true)
    setTimeout(() => setSaved(false), 2000)
    toast.success('Clave de administrador guardada')
  }

  return (
    <Section icon={<KeyRound className="h-4 w-4" />} title="Clave de Administrador">
      <p className="text-sm text-slate-500 mb-4">
        Requerida para operaciones de <strong>Release</strong> (liberar un activo del sistema).
        Debe coincidir con <code className="bg-slate-100 px-1.5 py-0.5 rounded text-xs font-mono">TRACE_ADMIN_KEY</code> en el <code className="bg-slate-100 px-1.5 py-0.5 rounded text-xs font-mono">.env</code> del servidor.
      </p>

      <div className="bg-amber-50 border border-amber-200 rounded-xl px-4 py-3 mb-4">
        <p className="text-xs text-amber-800 font-semibold">Valor actual en el servidor:</p>
        <code className="text-sm font-mono text-amber-900 break-all">super-secret-admin-key-change-me</code>
        <p className="text-[11px] text-amber-600 mt-1">
          Cambia este valor en <code className="font-mono">.env</code> antes de producción real.
        </p>
      </div>

      <div className="flex flex-col gap-3">
        <div>
          <label className="text-xs font-semibold text-slate-600 block mb-1.5">TRACE_ADMIN_KEY</label>
          <div className="relative">
            <input
              type={show ? 'text' : 'password'}
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSave()}
              placeholder="Ingresa la clave admin..."
              className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 pr-10 text-sm font-mono text-slate-800 placeholder:text-slate-400 focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 transition-colors"
            />
            <button
              type="button"
              className="absolute right-3 top-2.5 text-slate-400 hover:text-slate-700 transition-colors"
              onClick={() => setShow((s) => !s)}
            >
              {show ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
            </button>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <Button size="sm" onClick={handleSave}>
            {saved ? <><Check className="h-3.5 w-3.5" /> Guardado</> : 'Guardar en sesión'}
          </Button>
          {adminKey && (
            <span className="flex items-center gap-1.5 text-xs text-emerald-600 font-semibold">
              <Check className="h-3.5 w-3.5" /> Clave activa
            </span>
          )}
        </div>
        <p className="text-xs text-slate-400">
          Se guarda en <code className="font-mono">localStorage</code> del navegador. No se envía al servidor excepto cuando se usa en Release.
        </p>
      </div>
    </Section>
  )
}

// ─── Solana environment section ───────────────────────────────────────────────

function EnvironmentSection() {
  const { solanaCluster, setSolanaCluster } = useSettingsStore()

  const options: { value: SolanaCluster; label: string; desc: string; color: string }[] = [
    {
      value: 'devnet',
      label: 'Devnet',
      desc: 'Red de pruebas. SOL gratis, NFTs no tienen valor real.',
      color: 'border-indigo-300 bg-indigo-50 ring-2 ring-indigo-300',
    },
    {
      value: 'mainnet-beta',
      label: 'Mainnet Beta',
      desc: 'Red principal de Solana. SOL real, NFTs tienen valor real.',
      color: 'border-emerald-300 bg-emerald-50 ring-2 ring-emerald-300',
    },
  ]

  return (
    <Section icon={<Globe className="h-4 w-4" />} title="Entorno de Solana">
      <p className="text-sm text-slate-500 mb-4">
        Selecciona el cluster de Solana. Afecta los links del explorador en el detalle de cada NFT y en los eventos de la cadena de custodia.
      </p>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        {options.map((opt) => (
          <button
            key={opt.value}
            onClick={() => setSolanaCluster(opt.value)}
            className={`text-left p-4 rounded-xl border transition-all ${
              solanaCluster === opt.value
                ? opt.color
                : 'border-slate-200 bg-white hover:border-slate-300'
            }`}
          >
            <div className="flex items-center gap-2 mb-1">
              <span className={`h-2 w-2 rounded-full ${opt.value === 'devnet' ? 'bg-indigo-500' : 'bg-emerald-500'}`} />
              <span className="text-sm font-bold text-slate-800">{opt.label}</span>
              {solanaCluster === opt.value && (
                <span className="ml-auto">
                  <Check className="h-4 w-4 text-slate-600" />
                </span>
              )}
            </div>
            <p className="text-xs text-slate-500">{opt.desc}</p>
          </button>
        ))}
      </div>
      <p className="mt-3 text-xs text-slate-400">
        Activo: <strong>{solanaCluster}</strong> — links apuntarán a{' '}
        <code className="font-mono text-xs">https://explorer.solana.com/?cluster={solanaCluster}</code>
      </p>
    </Section>
  )
}

// ─── Solana keypair section ───────────────────────────────────────────────────

function KeypairSection() {
  const [showSecret, setShowSecret] = useState(false)
  const [expanded, setExpanded] = useState(false)

  return (
    <Section icon={<Settings className="h-4 w-4" />} title="Keypair del Servicio Solana">
      <p className="text-sm text-slate-500 mb-4">
        Este es el keypair que el backend usa para <strong>firmar transacciones de anclaje</strong> (Memo Program) en Solana.
        Se generó automáticamente para este entorno. Agrégalo al <code className="bg-slate-100 px-1.5 py-0.5 rounded text-xs font-mono">.env</code> y reinicia los contenedores.
      </p>

      <div className="flex flex-col gap-3 mb-4">
        {/* Public key */}
        <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">
          <div className="flex items-center justify-between mb-1">
            <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wider">Clave Pública</span>
            <CopyButton text={GENERATED_KEYPAIR.pubkey} />
          </div>
          <code className="text-sm font-mono text-slate-800 break-all">{GENERATED_KEYPAIR.pubkey}</code>
          <p className="text-xs text-slate-400 mt-1">
            Dirección en Solana donde se reciben fondos para pagar fees.{' '}
            <a
              href={`https://explorer.solana.com/address/${GENERATED_KEYPAIR.pubkey}?cluster=devnet`}
              target="_blank"
              rel="noopener noreferrer"
              className="text-indigo-500 hover:underline"
            >
              Ver en devnet Explorer ↗
            </a>
          </p>
        </div>

        {/* Secret key */}
        <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">
          <div className="flex items-center justify-between mb-1">
            <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wider">Clave Privada (base58)</span>
            <div className="flex items-center gap-3">
              <button onClick={() => setShowSecret((s) => !s)} className="text-xs text-slate-400 hover:text-slate-700 flex items-center gap-1">
                {showSecret ? <><EyeOff className="h-3.5 w-3.5" /> Ocultar</> : <><Eye className="h-3.5 w-3.5" /> Mostrar</>}
              </button>
              <CopyButton text={GENERATED_KEYPAIR.secretB58} label="Copiar clave" />
            </div>
          </div>
          {showSecret ? (
            <code className="text-sm font-mono text-red-700 break-all">{GENERATED_KEYPAIR.secretB58}</code>
          ) : (
            <div className="flex items-center gap-2 text-slate-400">
              <span className="font-mono text-sm">{'•'.repeat(40)}</span>
            </div>
          )}
          <div className="flex items-center gap-1.5 mt-2 text-xs text-red-600 bg-red-50 border border-red-100 rounded-lg px-3 py-2">
            <AlertTriangle className="h-3.5 w-3.5 shrink-0" />
            Nunca compartas esta clave. Quien la tenga puede firmar transacciones en tu nombre.
          </div>
        </div>
      </div>

      {/* .env snippet */}
      <div>
        <button
          onClick={() => setExpanded((e) => !e)}
          className="flex items-center gap-2 text-sm font-semibold text-slate-700 hover:text-indigo-600 transition-colors mb-2"
        >
          {expanded ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
          Ver snippet para el .env
        </button>
        {expanded && (
          <div>
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs text-slate-500">Copia esto en <code className="font-mono">C:\Users\me.ruiz42\Desktop\Trace\.env</code> y reinicia:</span>
              <CopyButton text={ENV_SNIPPET} label="Copiar todo" />
            </div>
            <pre className="rounded-xl bg-slate-900 text-slate-100 p-4 text-xs font-mono overflow-x-auto whitespace-pre-wrap">
              {ENV_SNIPPET}
            </pre>
            <div className="mt-3 rounded-xl bg-blue-50 border border-blue-200 px-4 py-3 text-xs text-blue-800">
              <strong>Después de editar el .env:</strong>
              <pre className="mt-1 font-mono text-blue-700">docker-compose restart api worker</pre>
              El sistema saldrá del modo simulación y anclará eventos reales en Solana devnet.
              Asegúrate de tener SOL en devnet:{' '}
              <a href="https://faucet.solana.com" target="_blank" rel="noopener noreferrer" className="underline">
                faucet.solana.com ↗
              </a>
            </div>
          </div>
        )}
      </div>
    </Section>
  )
}

// ─── Backend status section ───────────────────────────────────────────────────

function BackendStatusSection() {
  const { data: ready, isLoading, refetch, isFetching } = useQuery({
    queryKey: ['system', 'ready'],
    queryFn: () => api.health.readiness(),
    staleTime: 10_000,
  })

  const simMode = ready?.checks?.solana_simulation === 'true' || ready?.checks?.solana_simulation === true

  return (
    <Section icon={<Server className="h-4 w-4" />} title="Estado del Backend">
      <div className="flex items-center justify-between mb-4">
        <p className="text-sm text-slate-500">Estado actual del servidor y sus conexiones.</p>
        <button onClick={() => refetch()} className={`text-slate-400 hover:text-slate-600 transition-colors ${isFetching ? 'animate-spin' : ''}`}>
          <Settings className="h-4 w-4" />
        </button>
      </div>

      {isLoading ? (
        <p className="text-sm text-slate-400">Consultando...</p>
      ) : !ready ? (
        <div className="rounded-xl bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-700">
          Backend no disponible. Verifica que el contenedor Docker esté corriendo.
        </div>
      ) : (
        <div className="flex flex-col gap-2">
          {/* Simulation mode highlight */}
          <div className={`rounded-xl border px-4 py-3 flex items-center gap-3 ${
            simMode
              ? 'border-amber-200 bg-amber-50'
              : 'border-emerald-200 bg-emerald-50'
          }`}>
            <span className={`h-2.5 w-2.5 rounded-full shrink-0 ${simMode ? 'bg-amber-500' : 'bg-emerald-500'}`} />
            <div>
              <p className={`text-sm font-bold ${simMode ? 'text-amber-800' : 'text-emerald-800'}`}>
                {simMode ? 'Modo Simulación activo' : 'Modo Producción activo'}
              </p>
              <p className={`text-xs ${simMode ? 'text-amber-600' : 'text-emerald-600'}`}>
                {simMode
                  ? 'SOLANA_SIMULATION=true — los NFTs no están en blockchain real'
                  : 'SOLANA_SIMULATION=false — los NFTs se anclan en Solana real'}
              </p>
            </div>
          </div>

          {/* All checks */}
          <div className="rounded-xl border border-slate-200 overflow-hidden">
            {Object.entries(ready.checks).map(([key, val], i, arr) => (
              <div key={key} className={`flex items-center justify-between px-4 py-2.5 text-sm ${i < arr.length - 1 ? 'border-b border-slate-100' : ''}`}>
                <span className="text-slate-600 font-mono text-xs">{key}</span>
                <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${
                  String(val) === 'ok' || String(val) === 'true'
                    ? 'bg-emerald-100 text-emerald-700'
                    : String(val) === 'false'
                    ? 'bg-amber-100 text-amber-700'
                    : 'bg-slate-100 text-slate-600'
                }`}>
                  {String(val)}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </Section>
  )
}

// ─── Main Page ─────────────────────────────────────────────────────────────────

export function SettingsPage() {
  return (
    <div className="flex flex-col flex-1 overflow-hidden">
      <Topbar
        title="Blockchain"
        subtitle="Configuración global de Solana y claves del sistema"
      />
      <div className="flex-1 overflow-y-auto p-6">
        <div className="max-w-2xl mx-auto space-y-5">
          <AdminKeySection />
          <EnvironmentSection />
          <KeypairSection />
          <BackendStatusSection />
        </div>
      </div>
    </div>
  )
}
