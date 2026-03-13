import { useParams, NavLink } from 'react-router-dom'
import {
  Package, Wallet, Building2, Kanban, Link2,
  BookOpen, ArrowRight, CheckCircle2, AlertCircle, Info,
  Zap, Server, Globe, Key, GitBranch, Layers, Shield,
} from 'lucide-react'
import { Topbar } from '@/components/layout/Topbar'

// ─── Shared UI helpers ───────────────────────────────────────────────────────

function SectionHeader({ icon: Icon, title, subtitle }: { icon: React.ElementType; title: string; subtitle: string }) {
  return (
    <div className="flex items-start gap-4 mb-8 pb-6 border-b border-slate-100">
      <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-gradient-to-br from-indigo-50 to-indigo-100/50 border border-indigo-100/50 shrink-0">
        <Icon className="h-6 w-6 text-indigo-600" />
      </div>
      <div>
        <h1 className="text-xl font-bold text-slate-800">{title}</h1>
        <p className="text-sm text-slate-500 mt-1">{subtitle}</p>
      </div>
    </div>
  )
}

function InfoBox({ type = 'info', children }: { type?: 'info' | 'warning' | 'success'; children: React.ReactNode }) {
  const styles = {
    info:    'bg-blue-50 border-blue-200 text-blue-800',
    warning: 'bg-amber-50 border-amber-200 text-amber-800',
    success: 'bg-emerald-50 border-emerald-200 text-emerald-800',
  }
  const icons = {
    info:    <Info className="h-4 w-4 shrink-0 mt-0.5" />,
    warning: <AlertCircle className="h-4 w-4 shrink-0 mt-0.5" />,
    success: <CheckCircle2 className="h-4 w-4 shrink-0 mt-0.5" />,
  }
  return (
    <div className={`flex gap-2.5 rounded-xl border p-3.5 text-sm ${styles[type]}`}>
      {icons[type]}
      <div>{children}</div>
    </div>
  )
}

function H2({ children }: { children: React.ReactNode }) {
  return <h2 className="text-base font-bold text-slate-700 mt-7 mb-3 flex items-center gap-2">{children}</h2>
}

function CodeBlock({ children }: { children: React.ReactNode }) {
  return (
    <pre className="rounded-xl bg-slate-900 text-slate-100 p-4 text-xs font-mono overflow-x-auto my-3 leading-relaxed">
      {children}
    </pre>
  )
}

function Pill({ children, color = 'slate' }: { children: React.ReactNode; color?: string }) {
  const colors: Record<string, string> = {
    indigo:  'bg-indigo-100 text-indigo-700',
    emerald: 'bg-emerald-100 text-emerald-700',
    amber:   'bg-amber-100 text-amber-700',
    red:     'bg-red-100 text-red-700',
    blue:    'bg-blue-100 text-blue-700',
    purple:  'bg-purple-100 text-purple-700',
    slate:   'bg-slate-100 text-slate-600',
  }
  return (
    <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-semibold ${colors[color] ?? colors.slate}`}>
      {children}
    </span>
  )
}

// ─── Section: Overview ────────────────────────────────────────────────────────

function OverviewSection() {
  const modules = [
    { to: '/help/assets',        icon: Package,  label: 'Cargas',          desc: 'Registro, mint y trazabilidad de activos logisticos on-chain' },
    { to: '/help/wallets',       icon: Wallet,   label: 'Custodios',       desc: 'Wallets Solana en el allowlist de custodia' },
    { to: '/help/organizations', icon: Building2, label: 'Organizaciones', desc: 'Fincas, bodegas, transportistas y custodios' },
    { to: '/help/tracking',      icon: Kanban,   label: 'Tracking Board',  desc: 'Vista kanban de todos los activos por estado' },
    { to: '/help/security',      icon: Shield,   label: 'Seguridad',       desc: 'Tenant isolation, validaciones y headers de seguridad' },
    { to: '/help/integrations',  icon: Link2,    label: 'Integraciones',   desc: 'Solana, Helius, multi-tenancy y configuracion' },
  ]
  return (
    <div>
      <SectionHeader icon={BookOpen} title="Ayuda del Modulo de Logistica" subtitle="Documentacion completa de todas las funcionalidades" />
      <p className="text-sm text-slate-600 mb-6">
        El modulo de <strong>Logistica</strong> gestiona la trazabilidad de activos fisicos mediante cNFTs en Solana.
        Cada transferencia de custodia queda registrada de forma inmutable en blockchain. Selecciona una seccion para ver la documentacion detallada.
      </p>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        {modules.map(({ to, icon: Icon, label, desc }) => (
          <NavLink
            key={to}
            to={to}
            className="flex items-start gap-3 p-4 rounded-2xl border border-slate-200 bg-white hover:border-indigo-300 hover:shadow-md transition-all group"
          >
            <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-indigo-50 shrink-0">
              <Icon className="h-5 w-5 text-indigo-600" />
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-bold text-slate-700 group-hover:text-indigo-700">{label}</p>
              <p className="text-xs text-slate-400 mt-0.5">{desc}</p>
            </div>
            <ArrowRight className="h-4 w-4 text-slate-300 group-hover:text-indigo-400 mt-1 shrink-0" />
          </NavLink>
        ))}
      </div>
    </div>
  )
}

// ─── Section: Assets / Cargas ─────────────────────────────────────────────────

function AssetsSection() {
  return (
    <div>
      <SectionHeader icon={Package} title="Cargas" subtitle="Activos logisticos con trazabilidad on-chain" />

      <InfoBox type="success">
        Cada carga es un <strong>cNFT comprimido en Solana</strong>. Su historial de custodia es inmutable y verificable publicamente.
      </InfoBox>

      <H2><GitBranch className="h-4 w-4 text-indigo-400" /> Crear vs Mintear</H2>
      <div className="space-y-3">
        <div className="rounded-xl border border-slate-200 p-4">
          <p className="text-sm font-bold text-slate-700 mb-1">Registrar carga existente <Pill color="slate">POST /api/v1/assets</Pill></p>
          <p className="text-xs text-slate-500">Usa el <code className="bg-slate-100 rounded px-1">asset_mint</code> de un NFT ya existente en Solana. Ideal para vincular tokens pre-minteados.</p>
        </div>
        <div className="rounded-xl border border-indigo-200 bg-indigo-50/30 p-4">
          <p className="text-sm font-bold text-indigo-700 mb-1">Mintear nueva carga <Pill color="indigo">POST /api/v1/assets/mint</Pill></p>
          <p className="text-xs text-slate-500">Crea un nuevo cNFT Solana via <strong>Helius mintCompressedNft</strong> y lo registra automaticamente. El <code className="bg-slate-100 rounded px-1">asset_mint</code> se asigna tras el mint on-chain.</p>
        </div>
      </div>

      <H2>Crear una carga (Mint)</H2>
      <div className="flex flex-col gap-2 mt-1">
        {[
          'Ir a Logistica > Cargas',
          'Click en "Mint NFT"',
          'Seleccionar tipo de producto (chips visuales)',
          'Opcionalmente seleccionar organizacion de origen',
          'Completar metadata (peso, origen, destino, etc.)',
          'Indicar wallet custodio inicial (debe ser allowlisted y active)',
          'Click en "Mintear" — el cNFT se crea en Solana de forma fire-and-forget',
        ].map((step, i) => (
          <div key={i} className="flex items-start gap-3 text-xs text-slate-600">
            <span className="flex h-5 w-5 items-center justify-center rounded-full bg-indigo-100 text-indigo-600 font-bold shrink-0 text-[10px]">{i + 1}</span>
            {step}
          </div>
        ))}
      </div>

      <H2><Layers className="h-4 w-4 text-indigo-400" /> Maquina de Estados</H2>
      <p className="text-xs text-slate-500 mb-3">Los estados validos y sus transiciones permitidas:</p>
      <div className="grid grid-cols-2 gap-2 mb-4">
        {[
          { state: 'in_custody', desc: 'Activo bajo custodia de un custodio', color: 'indigo' },
          { state: 'in_transit', desc: 'En transito hacia el proximo custodio', color: 'amber' },
          { state: 'loaded', desc: 'Cargado en vehiculo/contenedor', color: 'indigo' },
          { state: 'qc_passed', desc: 'Control de calidad aprobado', color: 'emerald' },
          { state: 'qc_failed', desc: 'Control de calidad fallido (reinspeccion posible)', color: 'red' },
          { state: 'released', desc: 'Liberado fuera de la cadena (terminal)', color: 'slate' },
          { state: 'burned', desc: 'NFT quemado — destruido definitivamente (terminal)', color: 'red' },
        ].map(({ state, desc, color }) => (
          <div key={state} className="rounded-lg border border-slate-100 p-3">
            <Pill color={color}>{state}</Pill>
            <p className="text-[11px] text-slate-500 mt-1">{desc}</p>
          </div>
        ))}
      </div>

      <H2>Transiciones validas (VALID_FROM_STATES)</H2>
      <InfoBox type="warning">
        El backend valida estrictamente las transiciones de estado. Un evento que no sea valido para el estado actual sera rechazado con error <code className="bg-amber-100 rounded px-1">400</code>.
      </InfoBox>
      <div className="overflow-x-auto mt-3">
        <table className="w-full text-xs">
          <thead>
            <tr className="border-b border-slate-200">
              <th className="text-left py-2 pr-4 font-semibold text-slate-500">Evento</th>
              <th className="text-left py-2 pr-4 font-semibold text-slate-500">Estados de origen validos</th>
              <th className="text-left py-2 font-semibold text-slate-500">Estado resultante</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {[
              ['HANDOFF', 'in_custody, in_transit, loaded, qc_passed, qc_failed', 'in_transit'],
              ['ARRIVED', 'in_transit', 'in_custody'],
              ['LOADED', 'in_custody', 'loaded'],
              ['QC', 'loaded, qc_failed', 'qc_passed / qc_failed'],
              ['RELEASE', 'in_custody, in_transit, loaded, qc_passed, qc_failed', 'released'],
              ['BURN', 'in_custody, in_transit, loaded, qc_passed, qc_failed', 'burned'],
            ].map(([evt, from, result]) => (
              <tr key={evt}>
                <td className="py-2 pr-4 font-mono font-semibold text-slate-700">{evt}</td>
                <td className="py-2 pr-4 text-slate-500">{from}</td>
                <td className="py-2"><Pill>{result}</Pill></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <H2>Eventos de Custodia</H2>
      <div className="overflow-x-auto">
        <table className="w-full text-xs">
          <thead>
            <tr className="border-b border-slate-200">
              <th className="text-left py-2 pr-4 font-semibold text-slate-500">Evento</th>
              <th className="text-left py-2 pr-4 font-semibold text-slate-500">Endpoint</th>
              <th className="text-left py-2 font-semibold text-slate-500">Descripcion</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {[
              ['HANDOFF', 'POST /events/handoff', 'Transferir custodia a otro wallet (requiere to_wallet activo)'],
              ['ARRIVED', 'POST /events/arrived', 'Confirmar llegada al custodio actual'],
              ['LOADED', 'POST /events/loaded', 'Marcar como cargado en transporte'],
              ['QC', 'POST /events/qc', 'Registrar resultado de control de calidad (pass/fail)'],
              ['RELEASE', 'POST /events/release', 'Liberar a wallet externo (requiere X-Admin-Key)'],
              ['BURN', 'POST /events/burn', 'Destruir el activo de forma permanente'],
            ].map(([evt, ep, desc]) => (
              <tr key={evt}>
                <td className="py-2 pr-4 font-mono font-semibold text-slate-700">{evt}</td>
                <td className="py-2 pr-4 font-mono text-slate-500">{ep}</td>
                <td className="py-2 text-slate-500">{desc}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <H2>Estado Blockchain</H2>
      <div className="grid grid-cols-2 gap-2">
        {[
          { s: 'PENDING', d: 'Mint en progreso (fire-and-forget)', c: 'amber' },
          { s: 'CONFIRMED', d: 'cNFT confirmado on-chain', c: 'emerald' },
          { s: 'FAILED', d: 'Mint fallido — en cola de reintento (max 3)', c: 'red' },
          { s: 'SIMULATED', d: 'Creado en modo simulacion (no on-chain)', c: 'slate' },
          { s: 'SKIPPED', d: 'Sin blockchain (registro directo)', c: 'slate' },
        ].map(({ s, d, c }) => (
          <div key={s} className="flex gap-2 items-start rounded-lg border border-slate-100 p-2.5">
            <Pill color={c}>{s}</Pill>
            <p className="text-[11px] text-slate-500">{d}</p>
          </div>
        ))}
      </div>

      <H2>Idempotencia</H2>
      <p className="text-xs text-slate-500">
        Las operaciones de creacion, handoff, release y burn soportan <strong>idempotencia</strong> via el header
        <code className="bg-slate-100 rounded px-1 mx-1">Idempotency-Key</code>. Si se envia la misma key, la API retorna
        el resultado cacheado con <Pill color="blue">200</Pill> en lugar de <Pill color="emerald">201</Pill>.
      </p>
    </div>
  )
}

// ─── Section: Wallets / Custodios ─────────────────────────────────────────────

function WalletsSection() {
  return (
    <div>
      <SectionHeader icon={Wallet} title="Custodios" subtitle="Wallets Solana en el allowlist de custodia" />

      <InfoBox type="info">
        Solo wallets registrados en el <strong>allowlist</strong> pueden recibir custodia de activos.
        Un wallet <Pill color="red">revoked</Pill> o <Pill color="amber">suspended</Pill> no puede ser destino de un Handoff.
      </InfoBox>

      <H2>Generar vs Registrar</H2>
      <div className="space-y-3">
        <div className="rounded-xl border border-indigo-200 bg-indigo-50/30 p-4">
          <p className="text-sm font-bold text-indigo-700 mb-1">Generar nuevo wallet <Pill color="indigo">POST /registry/wallets/generate</Pill></p>
          <p className="text-xs text-slate-500 mb-2">El sistema crea un keypair nuevo en el backend, lo almacena de forma segura y hace un airdrop de prueba en devnet (1 SOL). Ideal para wallets operativos bajo control del sistema.</p>
          <CodeBlock>{`{
  "tags": ["transporte", "local"],
  "name": "Camion Norte",
  "organization_id": "uuid-de-la-org"
}`}</CodeBlock>
        </div>
        <div className="rounded-xl border border-slate-200 p-4">
          <p className="text-sm font-bold text-slate-700 mb-1">Registrar wallet externo <Pill color="slate">POST /registry/wallets</Pill></p>
          <p className="text-xs text-slate-500">Registra una pubkey de Solana ya existente (ej: Phantom, Ledger). El sistema no tiene acceso a la clave privada.</p>
          <CodeBlock>{`{
  "wallet_pubkey": "AaBbCc...pubkey",
  "tags": ["externo"],
  "status": "active"
}`}</CodeBlock>
        </div>
      </div>

      <H2>Crear un wallet</H2>
      <div className="flex flex-col gap-2 mt-1">
        {[
          'Ir a Logistica > Custodios',
          'Click en "Crear Wallet" (genera keypair) o "Registrar Externo"',
          'Asignar nombre, tags y opcionalmente una organizacion',
          'Al generar, se intenta un airdrop de 1 SOL en devnet (best-effort)',
          'El wallet queda con estado "active" y listo para recibir activos',
        ].map((step, i) => (
          <div key={i} className="flex items-start gap-3 text-xs text-slate-600">
            <span className="flex h-5 w-5 items-center justify-center rounded-full bg-indigo-100 text-indigo-600 font-bold shrink-0 text-[10px]">{i + 1}</span>
            {step}
          </div>
        ))}
      </div>

      <H2>Estados de Wallet</H2>
      <div className="space-y-2">
        {[
          { s: 'active', d: 'Puede recibir activos en custodia. Estado operativo normal.', c: 'emerald' },
          { s: 'suspended', d: 'Temporalmente inactivo. No puede recibir nuevos activos.', c: 'amber' },
          { s: 'revoked', d: 'Revocado permanentemente. No puede operar.', c: 'red' },
        ].map(({ s, d, c }) => (
          <div key={s} className="flex gap-3 items-start rounded-xl border border-slate-100 p-3">
            <Pill color={c}>{s}</Pill>
            <p className="text-xs text-slate-600">{d}</p>
          </div>
        ))}
      </div>

      <H2>Balance Solana</H2>
      <p className="text-xs text-slate-500">
        La pagina de detalle de cada custodio (<code className="bg-slate-100 rounded px-1">/wallets/:id</code>) muestra el balance SOL en tiempo real
        consultando el nodo RPC de Solana. En devnet, el saldo es de prueba. Para operaciones on-chain, el wallet firmante necesita SOL para pagar fees.
      </p>

      <H2>Campos del wallet</H2>
      <div className="overflow-x-auto">
        <table className="w-full text-xs">
          <thead>
            <tr className="border-b border-slate-200">
              <th className="text-left py-2 pr-4 font-semibold text-slate-500">Campo</th>
              <th className="text-left py-2 pr-4 font-semibold text-slate-500">Tipo</th>
              <th className="text-left py-2 font-semibold text-slate-500">Descripcion</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {[
              ['wallet_pubkey', 'texto', 'Clave publica de Solana (base58)'],
              ['name', 'texto', 'Nombre descriptivo del wallet'],
              ['tags', 'array', 'Etiquetas para filtrado (ej: transporte, local)'],
              ['status', 'enum', 'active / suspended / revoked'],
              ['organization_id', 'UUID', 'Organizacion a la que pertenece (opcional)'],
              ['encrypted_private_key', 'texto', 'Clave privada cifrada (solo wallets generados)'],
            ].map(([field, type, desc]) => (
              <tr key={field}>
                <td className="py-2 pr-4 font-mono font-semibold text-slate-700">{field}</td>
                <td className="py-2 pr-4"><Pill>{type}</Pill></td>
                <td className="py-2 text-slate-500">{desc}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

// ─── Section: Organizations ───────────────────────────────────────────────────

function OrganizationsSection() {
  return (
    <div>
      <SectionHeader icon={Building2} title="Organizaciones" subtitle="Fincas, bodegas, transportistas y otros custodios" />

      <p className="text-sm text-slate-600 mb-5">
        Las organizaciones agrupan wallets y activos bajo una entidad logica del mundo real
        (una finca, una bodega, una empresa transportista).
      </p>

      <H2>Tipos de Custodio</H2>
      <p className="text-xs text-slate-500 mb-3">
        Cada organizacion pertenece a un <strong>Tipo de Custodio</strong>, que define su rol en la cadena logistica.
        Los tipos se gestionan en la seccion "Gestionar tipos de custodio" al final de la pagina de Organizaciones.
      </p>
      <div className="grid grid-cols-2 gap-2 mb-4">
        {[
          { slug: 'farm', label: 'Finca', desc: 'Origen del producto agricola' },
          { slug: 'warehouse', label: 'Bodega', desc: 'Almacenamiento intermedio' },
          { slug: 'truck', label: 'Transporte', desc: 'Traslado entre custodios' },
          { slug: 'customs', label: 'Aduanas', desc: 'Control de importacion/exportacion' },
        ].map(({ slug, label, desc }) => (
          <div key={slug} className="rounded-xl border border-slate-100 p-3">
            <p className="text-xs font-bold text-slate-700">{label} <span className="font-mono font-normal text-slate-400 ml-1">/{slug}</span></p>
            <p className="text-[11px] text-slate-500 mt-0.5">{desc}</p>
          </div>
        ))}
      </div>
      <InfoBox type="info">
        Puedes crear tipos propios con nombre, color e icono personalizados desde la interfaz de administracion.
        El icono se selecciona de una grilla visual con 22 iconos de lucide-react.
      </InfoBox>

      <H2>Crear una organizacion</H2>
      <div className="flex flex-col gap-2 mt-1">
        {[
          'Ir a Logistica > Organizaciones',
          'Click en "Nueva Organizacion"',
          'Completar nombre y seleccionar tipo de custodio',
          'Opcionalmente agregar descripcion y tags',
          'Click en "Crear"',
        ].map((step, i) => (
          <div key={i} className="flex items-start gap-3 text-xs text-slate-600">
            <span className="flex h-5 w-5 items-center justify-center rounded-full bg-indigo-100 text-indigo-600 font-bold shrink-0 text-[10px]">{i + 1}</span>
            {step}
          </div>
        ))}
      </div>

      <H2>Detalle de organizacion</H2>
      <p className="text-xs text-slate-500 mb-3">
        La pagina de detalle (<code className="bg-slate-100 rounded px-1">/organizations/:id</code>) muestra dos tabs:
      </p>
      <div className="space-y-2">
        {[
          { tab: 'NFTs', desc: 'Activos (cargas) asociados a los wallets de la organizacion. Permite mintear directamente desde aqui.' },
          { tab: 'Wallets', desc: 'Wallets asignados a la organizacion. Permite generar nuevos wallets pre-asignados.' },
        ].map(({ tab, desc }) => (
          <div key={tab} className="flex gap-3 items-start rounded-xl border border-slate-100 p-3">
            <Pill color="indigo">{tab}</Pill>
            <p className="text-xs text-slate-600">{desc}</p>
          </div>
        ))}
      </div>

      <H2>Flujo tipico de custodia</H2>
      <div className="flex flex-col gap-2 mt-1">
        {[
          'Finca crea el activo (Genesis → in_custody)',
          'Finca hace Handoff al transportista (in_custody → in_transit)',
          'Transportista confirma llegada a bodega (in_transit → in_custody)',
          'Bodega carga en contenedor (in_custody → loaded)',
          'Control de calidad en destino (loaded → qc_passed)',
          'Release al comprador final (qc_passed → released)',
        ].map((step, i) => (
          <div key={i} className="flex items-start gap-3 text-xs text-slate-600">
            <span className="flex h-5 w-5 items-center justify-center rounded-full bg-indigo-100 text-indigo-600 font-bold shrink-0 text-[10px]">{i + 1}</span>
            {step}
          </div>
        ))}
      </div>
    </div>
  )
}

// ─── Section: Tracking Board ──────────────────────────────────────────────────

function TrackingSection() {
  return (
    <div>
      <SectionHeader icon={Kanban} title="Tracking Board" subtitle="Vista kanban en tiempo real de todos los activos" />

      <p className="text-sm text-slate-600 mb-5">
        El tablero muestra cada activo en la columna correspondiente a su estado actual.
        Cada columna se actualiza de forma independiente cada <strong>15 segundos</strong>.
      </p>

      <InfoBox type="success">
        Cada columna hace una consulta independiente filtrada por estado (<code className="bg-emerald-100 rounded px-1">useQueries</code>),
        garantizando que ningun activo quede oculto por limites de paginacion.
      </InfoBox>

      <H2>Columnas del tablero</H2>
      <div className="space-y-2 mt-2">
        {[
          { state: 'in_custody',  label: 'In Custody',  desc: 'Activos bajo custodia activa de un custodio registrado' },
          { state: 'in_transit',  label: 'In Transit',  desc: 'Activos en transito tras un Handoff, esperando llegada' },
          { state: 'loaded',      label: 'Loaded',      desc: 'Cargados en vehiculo o contenedor' },
          { state: 'qc_passed',   label: 'QC Passed',   desc: 'Aprobados por control de calidad' },
          { state: 'qc_failed',   label: 'QC Failed',   desc: 'Rechazados en QC — pueden reinspectarse' },
          { state: 'released',    label: 'Released',    desc: 'Liberados al comprador final (estado terminal)' },
          { state: 'burned',      label: 'Burned',      desc: 'NFT destruido (estado terminal irreversible)' },
        ].map(({ state, label, desc }) => (
          <div key={state} className="flex gap-3 items-start text-xs rounded-xl border border-slate-100 p-3">
            <Pill color="slate">{label}</Pill>
            <p className="text-slate-500">{desc}</p>
          </div>
        ))}
      </div>

      <H2>Filtros</H2>
      <p className="text-xs text-slate-500 mb-3">
        El selector de organizacion filtra todas las columnas por los wallets pertenecientes a esa organizacion.
        Solo se muestran activos cuyo custodio actual es un wallet asignado a la organizacion seleccionada.
      </p>

      <H2>Botones de accion</H2>
      <InfoBox type="info">
        En la pagina de detalle de cada activo, los botones de accion se habilitan/deshabilitan automaticamente
        segun el estado actual del activo y las transiciones validas (VALID_FROM_STATES). No se puede ejecutar
        una accion invalida desde la UI.
      </InfoBox>
    </div>
  )
}

// ─── Section: Security ────────────────────────────────────────────────────────

function SecuritySection() {
  return (
    <div>
      <SectionHeader icon={Shield} title="Seguridad" subtitle="Tenant isolation, validaciones y headers de seguridad" />

      <H2>Aislamiento por Tenant</H2>
      <p className="text-xs text-slate-500 mb-3">
        Todas las operaciones validan que el recurso pertenezca al tenant actual. Un tenant no puede ver ni modificar
        recursos de otro tenant, incluso si conoce el UUID.
      </p>
      <div className="space-y-2">
        {[
          { resource: 'Assets', desc: 'GET, eventos y transiciones validan asset.tenant_id' },
          { resource: 'Wallets', desc: 'GET, update y allowlist check validan wallet.tenant_id' },
          { resource: 'Organizations', desc: 'CRUD completo aislado por tenant_id' },
          { resource: 'Custodian Types', desc: 'Slug unico por tenant (no global)' },
        ].map(({ resource, desc }) => (
          <div key={resource} className="flex gap-3 items-start rounded-xl border border-slate-100 p-3">
            <Pill color="indigo">{resource}</Pill>
            <p className="text-xs text-slate-600">{desc}</p>
          </div>
        ))}
      </div>

      <H2>Headers de Seguridad</H2>
      <p className="text-xs text-slate-500 mb-3">
        El backend aplica automaticamente headers de seguridad en todas las respuestas:
      </p>
      <div className="overflow-x-auto">
        <table className="w-full text-xs">
          <thead>
            <tr className="border-b border-slate-200">
              <th className="text-left py-2 pr-4 font-semibold text-slate-500">Header</th>
              <th className="text-left py-2 font-semibold text-slate-500">Valor</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {[
              ['X-Content-Type-Options', 'nosniff'],
              ['X-Frame-Options', 'DENY'],
              ['X-XSS-Protection', '1; mode=block'],
              ['Referrer-Policy', 'strict-origin-when-cross-origin'],
            ].map(([header, value]) => (
              <tr key={header}>
                <td className="py-2 pr-4 font-mono font-semibold text-slate-700">{header}</td>
                <td className="py-2 font-mono text-slate-500">{value}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <H2>Validaciones del Tenant ID</H2>
      <InfoBox type="warning">
        El header <code className="bg-amber-100 rounded px-1">X-Tenant-Id</code> se valida con longitud maxima de 255 caracteres
        y formato slug (<code className="bg-amber-100 rounded px-1">{'[a-zA-Z0-9_-]+'}</code>) o UUID. Si el tenant no existe,
        el error es generico (<strong>"Invalid or inactive tenant"</strong>) para evitar enumeracion.
      </InfoBox>

      <H2>Control de Acceso</H2>
      <div className="space-y-2">
        {[
          { action: 'Handoff / Arrived / Loaded / QC / Burn', req: 'X-User-Id: 1 (Master Account)' },
          { action: 'Release', req: 'X-User-Id: 1 + X-Admin-Key valido' },
          { action: 'Wallet allowlist check', req: 'Wallet debe ser active + mismo tenant' },
        ].map(({ action, req }) => (
          <div key={action} className="flex gap-3 items-start rounded-xl border border-slate-100 p-3">
            <div>
              <p className="text-xs font-bold text-slate-700">{action}</p>
              <p className="text-[11px] text-slate-500 mt-0.5">{req}</p>
            </div>
          </div>
        ))}
      </div>

      <H2>Validaciones de Datos</H2>
      <div className="space-y-2">
        {[
          { field: 'LocationData.lat', rule: '-90 a 90' },
          { field: 'LocationData.lng', rule: '-180 a 180' },
          { field: 'QCRequest.result', rule: 'Literal: "pass" | "fail" (no string libre)' },
          { field: 'Wallet status', rule: 'Enum: active | suspended | revoked' },
        ].map(({ field, rule }) => (
          <div key={field} className="flex gap-3 items-center text-xs">
            <code className="font-mono text-slate-700 bg-slate-50 rounded px-2 py-1">{field}</code>
            <span className="text-slate-500">{rule}</span>
          </div>
        ))}
      </div>
    </div>
  )
}

// ─── Section: Integrations ────────────────────────────────────────────────────

function IntegrationsSection() {
  return (
    <div>
      <SectionHeader icon={Link2} title="Integraciones" subtitle="Solana, Helius, multi-tenancy y arquitectura de blockchain" />

      <H2><Globe className="h-4 w-4 text-indigo-400" /> Solana & Helius</H2>
      <p className="text-xs text-slate-500 mb-3">
        TraceLog usa <strong>Helius</strong> como proveedor RPC y de mint de cNFTs. Helius gestiona el arbol Merkle comprimido
        y expone la DAS API para verificar activos on-chain.
      </p>
      <div className="space-y-3">
        <div className="rounded-xl border border-slate-200 p-4">
          <p className="text-sm font-bold text-slate-700 mb-2">Mint de cNFT <Pill color="indigo">mintCompressedNft</Pill></p>
          <CodeBlock>{`// RPC call via Helius
POST https://devnet.helius-rpc.com/?api-key={KEY}
{
  "jsonrpc": "2.0",
  "method": "mintCompressedNft",
  "params": [{
    "name": "Carga de Cafe Q1",
    "symbol": "TRC",
    "owner": "wallet-pubkey...",
    "treeAddress": "tree-address...",
    "attributes": [
      {"trait_type": "Tipo de Producto", "value": "Cafe"},
      {"trait_type": "Peso", "value": "100"}
    ]
  }]
}`}</CodeBlock>
        </div>
        <div className="rounded-xl border border-slate-200 p-4">
          <p className="text-sm font-bold text-slate-700 mb-2">Verificar activo <Pill color="emerald">getAsset (DAS API)</Pill></p>
          <CodeBlock>{`// DAS API — verifica estado on-chain
POST https://mainnet.helius-rpc.com/?api-key={KEY}
{
  "jsonrpc": "2.0",
  "method": "getAsset",
  "params": ["asset-id..."]
}
// Respuesta incluye: compression.tree, ownership.owner,
// compression.leaf_id, compression.compressed`}</CodeBlock>
        </div>
      </div>

      <H2><Server className="h-4 w-4 text-indigo-400" /> Variables de Entorno del Backend</H2>
      <CodeBlock>{`# Proveedor de blockchain
HELIUS_API_KEY=tu-api-key-de-helius   # vacio = modo simulacion
HELIUS_RPC_URL=https://devnet.helius-rpc.com
HELIUS_NETWORK=devnet                 # devnet | mainnet-beta

# Forzar simulacion (sin Solana real)
SOLANA_SIMULATION=true

# Seguridad
TRACE_ADMIN_KEY=clave-secreta-admin   # requerido para release
JWT_SECRET=clave-jwt-compartida       # obligatorio en produccion

# Base de datos y Redis
DATABASE_URL=postgresql+asyncpg://...
REDIS_URL=redis://...`}</CodeBlock>

      <H2><Zap className="h-4 w-4 text-indigo-400" /> Arbol Merkle por Tenant</H2>
      <p className="text-xs text-slate-500 mb-3">
        Cada tenant necesita provisionar un arbol Merkle antes de poder mintear cNFTs.
        El arbol es compartido entre todos los activos del tenant.
      </p>
      <CodeBlock>{`# 1. Crear tenant
POST /api/v1/tenants
{"name": "Empresa A", "slug": "empresa-a"}

# 2. Provisionar arbol Merkle
POST /api/v1/tenants/{id}/provision-tree

# 3. Verificar estado del arbol
GET /api/v1/tenants/{id}/tree

# 4. Mintear activo (usando X-Tenant-Id)
POST /api/v1/assets/mint
X-Tenant-Id: empresa-a
{"product_type": "Cafe", "metadata": {...}, "initial_custodian_wallet": "..."}`}</CodeBlock>

      <H2><Key className="h-4 w-4 text-indigo-400" /> Multi-Tenancy</H2>
      <InfoBox type="warning">
        Todas las requests a la API deben incluir el header <code className="bg-amber-100 rounded px-1">X-Tenant-Id</code> con el slug o UUID del tenant.
        Sin este header, la API devuelve <strong>422 Unprocessable Entity</strong>.
      </InfoBox>
      <CodeBlock>{`# Frontend (.env)
VITE_TENANT_ID=default   # slug del tenant activo

# Todas las requests incluyen automaticamente:
X-Tenant-Id: default
X-User-Id: 1`}</CodeBlock>

      <H2>Patron Adapter (Blockchain Provider)</H2>
      <p className="text-xs text-slate-500 mb-3">
        La capa de blockchain usa el patron Strategy/Adapter. En produccion se usa <code className="bg-slate-100 rounded px-1">HeliusProvider</code>;
        en desarrollo/tests se usa <code className="bg-slate-100 rounded px-1">SimulationProvider</code> (sin red Solana real).
      </p>
      <div className="rounded-xl bg-slate-50 border border-slate-200 p-4 text-xs font-mono text-slate-600">
        <div className="text-slate-400 mb-1"># Seleccion automatica del proveedor</div>
        <div>HELIUS_API_KEY set → <span className="text-indigo-600">HeliusProvider</span> (produccion)</div>
        <div>HELIUS_API_KEY vacio → <span className="text-slate-500">SimulationProvider</span> (dev/tests)</div>
        <div>SOLANA_SIMULATION=true → <span className="text-slate-500">SimulationProvider</span> (override)</div>
      </div>

      <H2>Worker ARQ — Reintentos de Mint</H2>
      <p className="text-xs text-slate-500">
        Si un mint blockchain falla, el activo queda con <Pill color="red">blockchain_status: FAILED</Pill> y
        se encola un reintento automatico via el worker ARQ. Maximo 3 reintentos con backoff de 5 minutos.
        El activo es accesible en el sistema inmediatamente, independientemente del estado on-chain.
      </p>

      <H2>Indices de Rendimiento</H2>
      <p className="text-xs text-slate-500">
        La migracion <code className="bg-slate-100 rounded px-1">005_performance_indexes</code> agrega indices para consultas frecuentes:
      </p>
      <div className="space-y-1 mt-2">
        {[
          ['ix_custody_events_asset_id', 'custody_events(asset_id) — timeline de eventos'],
          ['ix_assets_tenant_state', 'assets(tenant_id, state) — tracking board por tenant'],
        ].map(([idx, desc]) => (
          <div key={idx} className="flex gap-2 items-start text-xs">
            <code className="font-mono text-indigo-600 bg-indigo-50 rounded px-2 py-0.5 shrink-0">{idx}</code>
            <span className="text-slate-500">{desc}</span>
          </div>
        ))}
      </div>
    </div>
  )
}

// ─── Nav sidebar + Section map ────────────────────────────────────────────────

const NAV_ITEMS = [
  { section: '',              icon: BookOpen,   label: 'Inicio' },
  { section: 'assets',        icon: Package,    label: 'Cargas' },
  { section: 'wallets',       icon: Wallet,     label: 'Custodios' },
  { section: 'organizations', icon: Building2,  label: 'Organizaciones' },
  { section: 'tracking',      icon: Kanban,     label: 'Tracking Board' },
  { section: 'security',      icon: Shield,     label: 'Seguridad' },
  { section: 'integrations',  icon: Link2,      label: 'Integraciones' },
]

const SECTION_COMPONENTS: Record<string, React.ReactNode> = {
  '':              <OverviewSection />,
  'assets':        <AssetsSection />,
  'wallets':       <WalletsSection />,
  'organizations': <OrganizationsSection />,
  'tracking':      <TrackingSection />,
  'security':      <SecuritySection />,
  'integrations':  <IntegrationsSection />,
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export function HelpPage() {
  const { section = '' } = useParams<{ section?: string }>()
  const currentItem = NAV_ITEMS.find((n) => n.section === section) ?? NAV_ITEMS[0]
  const Content = SECTION_COMPONENTS[section] ?? SECTION_COMPONENTS['']

  return (
    <div className="flex flex-col flex-1 overflow-hidden">
      <Topbar title="Logistica — Ayuda" subtitle={currentItem.label} />
      <div className="flex flex-1 overflow-hidden">
        {/* Sidebar nav */}
        <nav className="w-52 shrink-0 border-r border-slate-100 overflow-y-auto py-4 px-2 bg-slate-50/50">
          {NAV_ITEMS.map(({ section: s, icon: Icon, label }) => (
            <NavLink
              key={s}
              to={s ? `/help/${s}` : '/help'}
              end={!s}
              className={({ isActive }) =>
                `flex items-center gap-2.5 rounded-xl px-3 py-2 text-xs font-semibold transition-all mb-0.5 ${
                  isActive
                    ? 'text-indigo-700 bg-white shadow-sm ring-1 ring-indigo-100'
                    : 'text-slate-500 hover:bg-white/70 hover:text-slate-700'
                }`
              }
            >
              <Icon className="h-4 w-4 shrink-0" />
              {label}
            </NavLink>
          ))}
        </nav>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-8">
          <div className="max-w-3xl">
            {Content}
          </div>
        </div>
      </div>
    </div>
  )
}
