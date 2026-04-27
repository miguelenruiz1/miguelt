import { useEffect, useMemo, useRef, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import {
  Plus, Search, RefreshCw, Package, Sparkles,
  ChevronLeft, ChevronRight, ChevronsUpDown, ArrowDown, ArrowUp,
  X, Check, MoreHorizontal, History, UserPlus, Truck, PackageCheck,
  FlaskConical, CheckCircle, Paperclip, Link as LinkIcon, Trash2,
  ShieldCheck, ShieldAlert, ShieldOff, Clock, Box,
  Rows4, Rows3, Rows2,
} from 'lucide-react'
import { Topbar } from '@/components/layout/Topbar'
import { Button } from '@/components/ui/Button'
import { Spinner, EmptyState } from '@/components/ui/Misc'
import { CreateAssetModal } from '@/components/assets/CreateAssetModal'
import { MintNFTModal } from '@/components/assets/MintNFTModal'
import { useAssetList, useDeleteAsset } from '@/hooks/useAssets'
import { useOrganizations } from '@/hooks/useTaxonomy'
import { useWalletList } from '@/hooks/useWallets'
import { useWorkflowStates } from '@/hooks/useWorkflow'
import { shortPubkey, cn } from '@/lib/utils'
import type { Asset, AssetState, BlockchainStatus } from '@/types/api'

const nf = new Intl.NumberFormat('es-CO', { maximumFractionDigits: 0 })

const fmtRelative = (iso: string): string => {
  const m = Math.floor((Date.now() - new Date(iso).getTime()) / 60000)
  if (m < 1) return 'ahora'
  if (m < 60) return `hace ${m} min`
  const h = Math.floor(m / 60)
  if (h < 24) return `hace ${h} h`
  const d = Math.floor(h / 24)
  if (d === 1) return 'ayer'
  if (d < 7) return `hace ${d} d`
  return new Date(iso).toLocaleDateString('es-CO', { day: '2-digit', month: 'short' })
}

const getCargoName = (asset: Asset): string | null => {
  const meta = asset.metadata as Record<string, unknown> | undefined
  if (meta?.name && typeof meta.name === 'string') return meta.name
  return null
}

const getWeight = (asset: Asset): string => {
  const meta = asset.metadata as Record<string, unknown> | undefined
  const w = (meta?.weight ?? meta?.peso_total_kg) as string | number | undefined
  if (!w) return '—'
  const u = (meta?.weightUnit as string) || 'kg'
  const num = typeof w === 'string' ? Number(w) : w
  if (!Number.isFinite(num)) return `${w} ${u}`
  return `${nf.format(num)} ${u}`
}

const getHumanId = (asset: Asset): string => {
  const meta = asset.metadata as Record<string, unknown> | undefined
  if (meta?.human_id && typeof meta.human_id === 'string') return meta.human_id
  const tail = asset.id.replace(/-/g, '').slice(-6).toUpperCase()
  return `CRG-${tail}`
}

type SortKey = 'human_id' | 'product_type' | 'state' | 'updated_at'
type SortState = { key: SortKey; dir: 'asc' | 'desc' }

export function AssetsPage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const [showCreate, setShowCreate] = useState(false)
  const [showMint, setShowMint] = useState(false)

  const [search, setSearch] = useState(searchParams.get('q') ?? '')
  const [stateFilter, setStateFilter] = useState<AssetState | ''>(
    (searchParams.get('state') as AssetState) ?? '',
  )
  const [productType, setProductType] = useState(searchParams.get('product') ?? '')
  const [custodian, setCustodian] = useState(searchParams.get('custodian') ?? '')
  const [density, setDensity] = useState<'compact' | 'comfortable' | 'spacious'>('comfortable')
  const [sort, setSort] = useState<SortState>({ key: 'updated_at', dir: 'desc' })
  const [page, setPage] = useState(Number(searchParams.get('page') ?? 1))
  const [pageSize, setPageSize] = useState(15)
  const [actionFor, setActionFor] = useState<string | null>(null)

  useEffect(() => {
    const next = new URLSearchParams()
    if (search) next.set('q', search)
    if (stateFilter) next.set('state', stateFilter)
    if (productType) next.set('product', productType)
    if (custodian) next.set('custodian', custodian)
    if (page > 1) next.set('page', String(page))
    setSearchParams(next, { replace: true })
  }, [search, stateFilter, productType, custodian, page, setSearchParams])

  const { data, isLoading, isFetching, refetch } = useAssetList({
    state: stateFilter || undefined,
    product_type: productType || undefined,
    custodian: custodian || undefined,
    limit: pageSize,
    offset: (page - 1) * pageSize,
  })

  const { data: workflowStates } = useWorkflowStates()
  const { data: walletsData } = useWalletList({ limit: 200 })
  const { data: orgsData } = useOrganizations()

  const wallets = walletsData?.items ?? []
  const orgs = orgsData?.items ?? []
  const walletMap = useMemo(() => new Map(wallets.map(w => [w.wallet_pubkey, w])), [wallets])
  const orgMap = useMemo(() => new Map(orgs.map(o => [o.id, o])), [orgs])

  const getCustodianLabel = (pubkey: string): string => {
    const w = walletMap.get(pubkey)
    if (!w) return shortPubkey(pubkey)
    if (w.name) return w.name
    if (w.organization_id) {
      const org = orgMap.get(w.organization_id)
      if (org) return org.name
    }
    return shortPubkey(pubkey)
  }

  const items = data?.items ?? []
  const total = data?.total ?? 0
  const totalPages = Math.max(1, Math.ceil(total / pageSize))

  const filteredAndSorted = useMemo(() => {
    let xs = items
    if (search) {
      const q = search.toLowerCase()
      xs = xs.filter(a =>
        getHumanId(a).toLowerCase().includes(q)
        || a.asset_mint.toLowerCase().includes(q)
        || a.product_type.toLowerCase().includes(q)
        || (getCargoName(a) ?? '').toLowerCase().includes(q)
        || getCustodianLabel(a.current_custodian_wallet).toLowerCase().includes(q),
      )
    }
    const dir = sort.dir === 'asc' ? 1 : -1
    return [...xs].sort((a, b) => {
      const av = sort.key === 'human_id' ? getHumanId(a) : (a as any)[sort.key]
      const bv = sort.key === 'human_id' ? getHumanId(b) : (b as any)[sort.key]
      return av < bv ? -1 * dir : av > bv ? 1 * dir : 0
    })
  }, [items, search, sort])

  useEffect(() => { setPage(1) }, [stateFilter, productType, custodian])

  const activeFilters = [
    stateFilter && {
      key: 'state',
      label: `Estado: ${workflowStates?.find(s => s.slug === stateFilter)?.label ?? stateFilter}`,
      clear: () => setStateFilter(''),
    },
    productType && { key: 'product', label: `Producto: ${productType}`, clear: () => setProductType('') },
    custodian && { key: 'custodian', label: `Custodio: ${getCustodianLabel(custodian)}`, clear: () => setCustodian('') },
  ].filter(Boolean) as Array<{ key: string; label: string; clear: () => void }>

  const searchRef = useRef<HTMLInputElement>(null)
  useEffect(() => {
    const fn = (e: KeyboardEvent) => {
      if (e.key === '/' && document.activeElement?.tagName !== 'INPUT') {
        e.preventDefault()
        searchRef.current?.focus()
      }
      if (e.key === 'Escape' && actionFor) setActionFor(null)
    }
    window.addEventListener('keydown', fn)
    return () => window.removeEventListener('keydown', fn)
  }, [actionFor])

  useEffect(() => {
    if (!actionFor) return
    const fn = (e: MouseEvent) => {
      const target = e.target as HTMLElement | null
      if (target && !target.closest('[data-row-menu]')) {
        setActionFor(null)
      }
    }
    document.addEventListener('mousedown', fn)
    return () => document.removeEventListener('mousedown', fn)
  }, [actionFor])

  const productOptions = useMemo(
    () => Array.from(new Set(items.map(a => a.product_type))).sort(),
    [items],
  )
  const custodianOptions = useMemo(
    () => wallets
      .map(w => ({ value: w.wallet_pubkey, label: getCustodianLabel(w.wallet_pubkey) }))
      .sort((a, b) => a.label.localeCompare(b.label)),
    [wallets, walletMap, orgMap],
  )

  return (
    <div className="flex flex-col flex-1 overflow-hidden">
      <Topbar
        title="Cargas"
        subtitle={`${nf.format(total)} ${total === 1 ? 'carga' : 'cargas'}`}
        actions={
          <div className="flex gap-2">
            <Button size="sm" variant="secondary" onClick={() => setShowCreate(true)}>
              <Plus className="h-4 w-4" /> Registrar existente
            </Button>
            <Button size="sm" onClick={() => setShowMint(true)}>
              <Sparkles className="h-4 w-4" /> Nueva carga
            </Button>
          </div>
        }
      />

      <div className="flex-1 overflow-y-auto">
        <div className="flex items-center justify-between gap-3 flex-wrap px-6 py-3 bg-card border-b border-border">
          <div className="inline-flex items-center rounded-md p-0.5 bg-muted flex-wrap">
            <FilterTab
              active={stateFilter === ''}
              onClick={() => setStateFilter('')}
              count={total}
            >
              Todas
            </FilterTab>
            {(workflowStates ?? []).map(s => (
              <FilterTab
                key={s.slug}
                active={stateFilter === s.slug}
                onClick={() => setStateFilter(s.slug)}
                color={s.color}
              >
                {s.label}
              </FilterTab>
            ))}
          </div>

          <div className="flex items-center gap-2 flex-wrap">
            <SearchInput value={search} onChange={setSearch} inputRef={searchRef} />
            <Combobox
              value={productType}
              onChange={setProductType}
              options={productOptions.map(p => ({ value: p, label: p }))}
              placeholder="Producto"
              icon={<Box className="h-3 w-3 text-muted-foreground" />}
              width={160}
            />
            <Combobox
              value={custodian}
              onChange={setCustodian}
              options={custodianOptions}
              placeholder="Custodio"
              icon={<ShieldCheck className="h-3 w-3 text-muted-foreground" />}
              width={160}
            />
            <DensityToggle value={density} onChange={setDensity} />
            <Button
              size="icon"
              variant="ghost"
              onClick={() => refetch()}
              title="Actualizar"
            >
              <RefreshCw className={cn('h-4 w-4', isFetching && 'animate-spin')} />
            </Button>
          </div>
        </div>

        {activeFilters.length > 0 && (
          <div className="flex items-center gap-2 flex-wrap px-6 py-2.5 bg-muted/40 border-b border-border">
            <span className="text-xs text-muted-foreground">Filtros:</span>
            {activeFilters.map(f => (
              <button
                key={f.key}
                onClick={f.clear}
                className="inline-flex items-center gap-1 text-xs px-2 h-6 rounded-md bg-card border border-border text-foreground hover:bg-muted"
              >
                {f.label}
                <X className="h-3 w-3 text-muted-foreground" />
              </button>
            ))}
            <button
              onClick={() => { setStateFilter(''); setProductType(''); setCustodian('') }}
              className="text-xs text-primary hover:underline ml-1"
            >
              Limpiar todo
            </button>
            <span className="ml-auto text-xs text-muted-foreground tabular-nums">
              {nf.format(filteredAndSorted.length)} {filteredAndSorted.length === 1 ? 'resultado' : 'resultados'}
            </span>
          </div>
        )}

        {isLoading ? (
          <div className="flex justify-center py-20"><Spinner /></div>
        ) : filteredAndSorted.length === 0 ? (
          <EmptyState
            icon={<Package className="h-12 w-12" />}
            title="No hay cargas"
            description="Ajusta los filtros o registra tu primera carga."
            action={
              <Button size="sm" onClick={() => setShowMint(true)}>
                <Sparkles className="h-4 w-4" /> Nueva carga
              </Button>
            }
          />
        ) : (
          <>
            <div className="bg-card">
              <table className="w-full text-sm tabular-nums">
                <thead className="sticky top-0 bg-card z-10">
                  <tr className="border-b border-border">
                    <Th sortKey="human_id" sort={sort} onSort={setSort}>Carga</Th>
                    <Th sortKey="product_type" sort={sort} onSort={setSort}>Producto</Th>
                    <Th align="right">Cantidad</Th>
                    <Th>Custodio</Th>
                    <Th sortKey="state" sort={sort} onSort={setSort}>Estado</Th>
                    <Th sortKey="updated_at" sort={sort} onSort={setSort} align="right">Actualizado</Th>
                    <th className="w-10 bg-card" />
                  </tr>
                </thead>
                <tbody>
                  {filteredAndSorted.map(asset => (
                    <Row
                      key={asset.id}
                      asset={asset}
                      density={density}
                      custodianLabel={getCustodianLabel(asset.current_custodian_wallet)}
                      menuOpen={actionFor === asset.id}
                      onToggleMenu={() => setActionFor(actionFor === asset.id ? null : asset.id)}
                    />
                  ))}
                </tbody>
              </table>
            </div>

            <Pagination
              page={page}
              setPage={setPage}
              totalPages={totalPages}
              total={total}
              pageSize={pageSize}
              setPageSize={setPageSize}
            />
          </>
        )}
      </div>

      <CreateAssetModal open={showCreate} onClose={() => setShowCreate(false)} />
      <MintNFTModal open={showMint} onClose={() => setShowMint(false)} />
    </div>
  )
}

function FilterTab({
  active, onClick, count, color, children,
}: {
  active: boolean; onClick: () => void; count?: number; color?: string; children: React.ReactNode
}) {
  return (
    <button
      onClick={onClick}
      className={cn(
        'inline-flex items-center gap-1.5 px-3 h-7 text-xs font-medium rounded transition-all whitespace-nowrap',
        active ? 'bg-card text-foreground shadow-sm' : 'text-muted-foreground hover:text-foreground',
      )}
    >
      {color && <span className="h-1.5 w-1.5 rounded-full" style={{ background: color }} />}
      {children}
      {typeof count === 'number' && (
        <span className={cn(
          'text-[10.5px] tabular-nums px-1.5 h-4 rounded inline-flex items-center font-mono',
          active ? 'bg-muted text-muted-foreground' : 'text-muted-foreground/70',
        )}>
          {count}
        </span>
      )}
    </button>
  )
}

function SearchInput({
  value, onChange, inputRef,
}: {
  value: string; onChange: (v: string) => void; inputRef: React.RefObject<HTMLInputElement>
}) {
  return (
    <div className="relative">
      <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3 w-3 text-muted-foreground pointer-events-none" />
      <input
        ref={inputRef}
        value={value}
        onChange={e => onChange(e.target.value)}
        placeholder="Buscar  ·  /"
        className="h-8 pl-7 pr-7 w-60 text-xs rounded-md border border-border bg-card outline-none focus:ring-2 focus:ring-ring/30 focus:border-primary"
      />
      {value && (
        <button
          onClick={() => onChange('')}
          className="absolute right-1.5 top-1/2 -translate-y-1/2 h-5 w-5 rounded-full inline-flex items-center justify-center text-muted-foreground hover:bg-muted"
        >
          <X className="h-3 w-3" />
        </button>
      )}
    </div>
  )
}

function Combobox({
  value, onChange, options, placeholder, icon, width = 160,
}: {
  value: string
  onChange: (v: string) => void
  options: { value: string; label: string }[]
  placeholder: string
  icon?: React.ReactNode
  width?: number
}) {
  const [open, setOpen] = useState(false)
  const [q, setQ] = useState('')
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const fn = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false)
    }
    document.addEventListener('mousedown', fn)
    return () => document.removeEventListener('mousedown', fn)
  }, [])

  const filtered = q ? options.filter(o => o.label.toLowerCase().includes(q.toLowerCase())) : options
  const selected = options.find(o => o.value === value)

  return (
    <div ref={ref} className="relative" style={{ width }}>
      <button
        onClick={() => setOpen(!open)}
        className={cn(
          'h-8 px-2.5 w-full text-xs rounded-md border border-border bg-card inline-flex items-center gap-1.5 hover:bg-muted/40',
          selected ? 'text-foreground' : 'text-muted-foreground',
        )}
      >
        {icon}
        <span className="flex-1 text-left truncate">{selected?.label ?? placeholder}</span>
        <ChevronsUpDown className="h-3 w-3 text-muted-foreground" />
      </button>
      {open && (
        <div className="absolute top-full mt-1 left-0 z-30 rounded-lg overflow-hidden bg-card border border-border shadow-lg" style={{ minWidth: 220 }}>
          <div className="p-1.5 border-b border-border">
            <input
              autoFocus
              placeholder="Buscar…"
              value={q}
              onChange={e => setQ(e.target.value)}
              className="w-full h-7 px-2 text-xs rounded border border-border outline-none"
            />
          </div>
          <div className="max-h-56 overflow-y-auto py-1">
            {value && (
              <button
                onClick={() => { onChange(''); setOpen(false) }}
                className="w-full text-left px-2.5 h-7 text-xs text-red-600 hover:bg-red-50 inline-flex items-center gap-1.5"
              >
                <X className="h-3 w-3" /> Quitar filtro
              </button>
            )}
            {filtered.length === 0 ? (
              <div className="px-2.5 py-2 text-xs text-muted-foreground">Sin coincidencias</div>
            ) : (
              filtered.map(o => (
                <button
                  key={o.value}
                  onClick={() => { onChange(o.value); setOpen(false); setQ('') }}
                  className={cn(
                    'w-full text-left px-2.5 h-7 text-xs inline-flex items-center justify-between hover:bg-muted',
                    o.value === value ? 'text-primary font-medium' : 'text-foreground',
                  )}
                >
                  <span className="truncate">{o.label}</span>
                  {o.value === value && <Check className="h-3 w-3" />}
                </button>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  )
}

function DensityToggle({
  value, onChange,
}: {
  value: 'compact' | 'comfortable' | 'spacious'
  onChange: (v: 'compact' | 'comfortable' | 'spacious') => void
}) {
  const opts: Array<{ k: 'compact' | 'comfortable' | 'spacious'; label: string; Icon: typeof Rows4 }> = [
    { k: 'compact',     label: 'Compacta',  Icon: Rows4 },
    { k: 'comfortable', label: 'Normal',    Icon: Rows3 },
    { k: 'spacious',    label: 'Espaciosa', Icon: Rows2 },
  ]
  return (
    <div className="flex items-center rounded-md p-0.5 bg-muted">
      {opts.map(d => {
        const { Icon } = d
        return (
          <button
            key={d.k}
            onClick={() => onChange(d.k)}
            title={d.label}
            aria-label={d.label}
            className={cn(
              'h-7 w-7 inline-flex items-center justify-center rounded',
              value === d.k ? 'bg-card text-foreground shadow-sm' : 'text-muted-foreground hover:text-foreground',
            )}
          >
            <Icon className="h-3.5 w-3.5" />
          </button>
        )
      })}
    </div>
  )
}

function Th({
  children, align = 'left', sortKey, sort, onSort,
}: {
  children: React.ReactNode
  align?: 'left' | 'right'
  sortKey?: SortKey
  sort?: SortState
  onSort?: (s: SortState) => void
}) {
  const sortable = !!sortKey && !!onSort && !!sort
  const isActive = sortable && sort!.key === sortKey
  const dir = isActive ? sort!.dir : null

  return (
    <th
      className={cn(
        'font-medium text-[11px] uppercase tracking-wider text-muted-foreground py-2.5 px-4 bg-card group',
        sortable && 'cursor-pointer hover:text-foreground',
      )}
      style={{ textAlign: align }}
      onClick={() => sortable && onSort!({ key: sortKey!, dir: isActive && dir === 'desc' ? 'asc' : 'desc' })}
    >
      <span className={cn('inline-flex items-center gap-1', align === 'right' && 'flex-row-reverse')}>
        {children}
        {sortable && (
          dir
            ? (dir === 'desc' ? <ArrowDown className="h-3 w-3 text-primary" /> : <ArrowUp className="h-3 w-3 text-primary" />)
            : <ChevronsUpDown className="h-3 w-3 text-muted-foreground/40 opacity-0 group-hover:opacity-100 transition" />
        )}
      </span>
    </th>
  )
}

function Row({
  asset, density, custodianLabel, menuOpen, onToggleMenu,
}: {
  asset: Asset
  density: 'compact' | 'comfortable' | 'spacious'
  custodianLabel: string
  menuOpen: boolean
  onToggleMenu: () => void
}) {
  const py = density === 'compact' ? 'py-1.5' : density === 'spacious' ? 'py-3.5' : 'py-2.5'
  const name = getCargoName(asset)

  return (
    <tr className="hover:bg-muted/50 transition-colors border-b border-border/50">
      <td className={cn(py, 'px-4')}>
        <Link to={`/assets/${asset.id}`} className="block group">
          <div className="flex items-center gap-2">
            <span className="text-sm font-semibold text-foreground tabular-nums tracking-tight group-hover:text-primary">
              {getHumanId(asset)}
            </span>
            <BlockchainIcon status={asset.blockchain_status} />
          </div>
          {name && <div className="text-xs text-muted-foreground mt-0.5 truncate max-w-[280px]">{name}</div>}
        </Link>
      </td>
      <td className={cn(py, 'px-4 text-foreground')}>{asset.product_type}</td>
      <td className={cn(py, 'px-4 text-right font-medium text-foreground')}>{getWeight(asset)}</td>
      <td className={cn(py, 'px-4 text-muted-foreground')}>{custodianLabel}</td>
      <td className={cn(py, 'px-4')}>
        <DynamicStatePill state={asset.state} />
      </td>
      <td className={cn(py, 'px-4 text-right text-xs text-muted-foreground')}>
        {fmtRelative(asset.updated_at)}
      </td>
      <td className={cn(py, 'px-2 relative')} data-row-menu>
        <button
          onClick={e => { e.stopPropagation(); e.preventDefault(); onToggleMenu() }}
          className="h-7 w-7 inline-flex items-center justify-center rounded-md text-muted-foreground hover:bg-muted"
          aria-label="Acciones de carga"
          aria-haspopup="menu"
          aria-expanded={menuOpen}
        >
          <MoreHorizontal className="h-4 w-4" />
        </button>
        {menuOpen && <RowActionsMenu asset={asset} onClose={onToggleMenu} />}
      </td>
    </tr>
  )
}

function DynamicStatePill({ state }: { state: AssetState | string }) {
  const { data: wfStates } = useWorkflowStates()
  const ws = wfStates?.find(s => s.slug === state)
  if (!ws) {
    return <span className="text-xs text-muted-foreground">{state}</span>
  }
  return (
    <span
      className="inline-flex items-center gap-1.5 h-6 px-2 rounded-full text-xs font-medium"
      style={{ background: `${ws.color}1A`, color: ws.color }}
    >
      <span className="h-1.5 w-1.5 rounded-full" style={{ background: ws.color }} />
      {ws.label}
    </span>
  )
}

function BlockchainIcon({ status }: { status: BlockchainStatus | string }) {
  const map: Record<string, { Icon: typeof ShieldCheck; color: string; tip: string }> = {
    CONFIRMED: { Icon: ShieldCheck, color: '#16A34A', tip: 'Anclado en blockchain' },
    PENDING:   { Icon: Clock,       color: '#94A3B8', tip: 'Pendiente de anclaje' },
    FAILED:    { Icon: ShieldAlert, color: '#DC2626', tip: 'Fallo en anclaje' },
    SIMULATED: { Icon: FlaskConical,color: '#7C3AED', tip: 'Simulado (devnet)' },
    SKIPPED:   { Icon: ShieldOff,   color: '#94A3B8', tip: 'Anclaje omitido' },
  }
  const m = map[status] ?? map.PENDING
  const { Icon } = m
  return (
    <span title={m.tip} aria-label={m.tip}>
      <Icon className="h-3 w-3" style={{ color: m.color }} />
    </span>
  )
}

function RowActionsMenu({ asset, onClose }: { asset: Asset; onClose: () => void }) {
  const deleteMut = useDeleteAsset()

  const items: Array<
    | { type: 'header'; label: string }
    | { type: 'item'; icon: React.ReactNode; label: string; onClick: () => void; danger?: boolean; href?: string }
  > = [
    { type: 'item', icon: <ChevronRight className="h-3.5 w-3.5" />, label: 'Ver detalle', onClick: () => {}, href: `/assets/${asset.id}` },
    { type: 'item', icon: <History className="h-3.5 w-3.5" />,      label: 'Línea de tiempo', onClick: () => {}, href: `/assets/${asset.id}#timeline` },
    { type: 'header', label: 'Registrar evento' },
    { type: 'item', icon: <UserPlus className="h-3.5 w-3.5" />,     label: 'Entregar a custodio…', onClick: () => alert('TODO: HandoffModal') },
    { type: 'item', icon: <Truck className="h-3.5 w-3.5" />,        label: 'Marcar como cargada', onClick: () => alert('TODO: LoadedModal') },
    { type: 'item', icon: <PackageCheck className="h-3.5 w-3.5" />, label: 'Marcar como recibida', onClick: () => alert('TODO: ArrivedModal') },
    { type: 'item', icon: <FlaskConical className="h-3.5 w-3.5" />, label: 'Registrar QC…', onClick: () => alert('TODO: QCModal') },
    { type: 'item', icon: <CheckCircle className="h-3.5 w-3.5" />,  label: 'Liberar / Entregar…', onClick: () => alert('TODO: ReleasedModal') },
    { type: 'header', label: 'Otros' },
    { type: 'item', icon: <Paperclip className="h-3.5 w-3.5" />,    label: 'Adjuntar evidencia…', onClick: () => alert('TODO: EvidenceModal') },
    {
      type: 'item',
      icon: <LinkIcon className="h-3.5 w-3.5" />,
      label: 'Copiar hash blockchain',
      onClick: () => { navigator.clipboard?.writeText(asset.asset_mint) },
    },
    {
      type: 'item',
      icon: <Trash2 className="h-3.5 w-3.5" />,
      label: 'Eliminar carga',
      danger: true,
      onClick: () => {
        const adminKey = window.prompt('X-Admin-Key para eliminar:')
        if (adminKey) deleteMut.mutate({ id: asset.id, adminKey })
      },
    },
  ]

  return (
    <div
      onClick={e => e.stopPropagation()}
      className="absolute right-2 top-9 z-40 rounded-lg overflow-hidden bg-card border border-border shadow-xl py-1"
      style={{ minWidth: 240 }}
      role="menu"
    >
      {items.map((it, i) => {
        if (it.type === 'header') {
          return (
            <div key={i} className="px-2.5 pt-2 pb-1 text-[10.5px] font-medium uppercase tracking-wider text-muted-foreground">
              {it.label}
            </div>
          )
        }
        const inner = (
          <span className={cn('w-full inline-flex items-center gap-2 px-2.5 h-8 text-xs hover:bg-muted', it.danger ? 'text-red-600' : 'text-foreground')}>
            <span className={cn('shrink-0', it.danger ? 'text-red-600' : 'text-muted-foreground')}>{it.icon}</span>
            <span className="flex-1 truncate">{it.label}</span>
          </span>
        )
        if (it.href) {
          return (
            <Link key={i} to={it.href} onClick={onClose} role="menuitem" className="block">
              {inner}
            </Link>
          )
        }
        return (
          <button key={i} onClick={() => { it.onClick(); onClose() }} role="menuitem" className="w-full text-left">
            {inner}
          </button>
        )
      })}
    </div>
  )
}

function Pagination({
  page, setPage, totalPages, total, pageSize, setPageSize,
}: {
  page: number; setPage: (p: number) => void
  totalPages: number; total: number
  pageSize: number; setPageSize: (n: number) => void
}) {
  const start = (page - 1) * pageSize + 1
  const end = Math.min(page * pageSize, total)

  const set = new Set<number>()
  ;[1, 2, page - 1, page, page + 1, totalPages - 1, totalPages].forEach(n => {
    if (n >= 1 && n <= totalPages) set.add(n)
  })
  const sorted = [...set].sort((a, b) => a - b)
  const items: (number | '…')[] = []
  sorted.forEach((n, i) => {
    if (i > 0 && n - sorted[i - 1] > 1) items.push('…')
    items.push(n)
  })

  return (
    <div className="px-6 py-3 flex items-center justify-between bg-card border-t border-border text-xs">
      <div className="text-muted-foreground tabular-nums">
        Mostrando <span className="text-foreground font-medium">{nf.format(start)}–{nf.format(end)}</span> de{' '}
        <span className="text-foreground font-medium">{nf.format(total)}</span>
      </div>
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-1.5 text-muted-foreground">
          <span>Por página</span>
          <select
            value={pageSize}
            onChange={e => setPageSize(Number(e.target.value))}
            className="h-7 px-1.5 rounded border border-border bg-card outline-none text-xs tabular-nums"
          >
            {[10, 15, 25, 50, 100].map(n => <option key={n} value={n}>{n}</option>)}
          </select>
        </div>
        <div className="flex items-center gap-1">
          <button
            onClick={() => setPage(Math.max(1, page - 1))}
            disabled={page === 1}
            className="h-7 px-2 inline-flex items-center gap-1 rounded text-foreground/70 hover:bg-muted disabled:opacity-40 disabled:cursor-not-allowed"
          >
            <ChevronLeft className="h-3 w-3" /> Anterior
          </button>
          {items.map((p, i) =>
            p === '…' ? (
              <span key={`gap-${i}`} className="px-1.5 text-muted-foreground">…</span>
            ) : (
              <button
                key={p}
                onClick={() => setPage(p)}
                className={cn(
                  'h-7 min-w-7 px-2 tabular-nums rounded',
                  p === page ? 'bg-foreground text-background font-medium' : 'text-foreground/70 hover:bg-muted',
                )}
              >
                {p}
              </button>
            ),
          )}
          <button
            onClick={() => setPage(Math.min(totalPages, page + 1))}
            disabled={page === totalPages}
            className="h-7 px-2 inline-flex items-center gap-1 rounded text-foreground/70 hover:bg-muted disabled:opacity-40 disabled:cursor-not-allowed"
          >
            Siguiente <ChevronRight className="h-3 w-3" />
          </button>
        </div>
      </div>
    </div>
  )
}
