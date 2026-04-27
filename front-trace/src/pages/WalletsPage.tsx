import { useEffect, useMemo, useRef, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import {
  Plus, KeyRound, Search, RefreshCw, Wallet, Copy, Check,
  ChevronLeft, ChevronRight, ChevronsUpDown, ArrowDown, ArrowUp,
  X, MoreHorizontal, ShieldCheck, ShieldOff, ShieldAlert,
  Building2, Tag, Rows4, Rows3, Rows2, ExternalLink,
} from 'lucide-react'

import { Topbar } from '@/components/layout/Topbar'
import { Button } from '@/components/ui/Button'
import { Spinner, EmptyState } from '@/components/ui/Misc'
import { RegisterWalletModal } from '@/components/wallets/RegisterWalletModal'
import { GenerateWalletModal } from '@/components/wallets/GenerateWalletModal'
import { useWalletList, useUpdateWallet } from '@/hooks/useWallets'
import { useOrganizations } from '@/hooks/useTaxonomy'
import { shortPubkey, copyToClipboard, cn } from '@/lib/utils'
import { useToast } from '@/store/toast'
import { useSettingsStore, explorerAddressUrl } from '@/store/settings'
import type { Wallet as WalletType, WalletStatus } from '@/types/api'

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

const STATUS_META: Record<WalletStatus, { label: string; color: string; bg: string; fg: string }> = {
  active:    { label: 'Activa',     color: '#16A34A', bg: 'bg-emerald-50', fg: 'text-emerald-700' },
  suspended: { label: 'Suspendida', color: '#F59E0B', bg: 'bg-amber-50',   fg: 'text-amber-700' },
  revoked:   { label: 'Revocada',   color: '#DC2626', bg: 'bg-red-50',     fg: 'text-red-700' },
}

const initials = (s: string): string => {
  const parts = s.trim().split(/\s+/).filter(Boolean)
  if (parts.length === 0) return '?'
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase()
  return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase()
}

type SortKey = 'name' | 'status' | 'created_at'
type SortState = { key: SortKey; dir: 'asc' | 'desc' }

export function WalletsPage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const [showRegister, setShowRegister] = useState(false)
  const [showGenerate, setShowGenerate] = useState(false)

  const [search, setSearch] = useState(searchParams.get('q') ?? '')
  const [statusFilter, setStatusFilter] = useState<WalletStatus | ''>(
    (searchParams.get('status') as WalletStatus) ?? '',
  )
  const [orgFilter, setOrgFilter] = useState(searchParams.get('org') ?? '')
  const [tagFilter, setTagFilter] = useState(searchParams.get('tag') ?? '')
  const [density, setDensity] = useState<'compact' | 'comfortable' | 'spacious'>('comfortable')
  const [sort, setSort] = useState<SortState>({ key: 'created_at', dir: 'desc' })
  const [page, setPage] = useState(Number(searchParams.get('page') ?? 1))
  const [pageSize, setPageSize] = useState(20)
  const [actionFor, setActionFor] = useState<string | null>(null)

  useEffect(() => {
    const next = new URLSearchParams()
    if (search) next.set('q', search)
    if (statusFilter) next.set('status', statusFilter)
    if (orgFilter) next.set('org', orgFilter)
    if (tagFilter) next.set('tag', tagFilter)
    if (page > 1) next.set('page', String(page))
    setSearchParams(next, { replace: true })
  }, [search, statusFilter, orgFilter, tagFilter, page, setSearchParams])

  const { data, isLoading, isFetching, refetch } = useWalletList({
    status: statusFilter || undefined,
    tag: tagFilter || undefined,
    limit: 200,
  })
  const { data: orgsData } = useOrganizations()
  const orgs = orgsData?.items ?? []
  const orgMap = useMemo(() => new Map(orgs.map(o => [o.id, o])), [orgs])

  const allWallets = data?.items ?? []
  const total = data?.total ?? 0

  // Filtros locales (search + org)
  const filtered = useMemo(() => {
    let xs: WalletType[] = allWallets
    if (orgFilter) xs = xs.filter(w => w.organization_id === orgFilter)
    if (search) {
      const q = search.toLowerCase()
      xs = xs.filter(w =>
        (w.name ?? '').toLowerCase().includes(q)
        || w.wallet_pubkey.toLowerCase().includes(q)
        || w.tags.some(t => t.toLowerCase().includes(q))
        || (w.organization_id ? (orgMap.get(w.organization_id)?.name ?? '').toLowerCase().includes(q) : false),
      )
    }
    const dir = sort.dir === 'asc' ? 1 : -1
    return [...xs].sort((a, b) => {
      const av = sort.key === 'name'
        ? (a.name ?? a.wallet_pubkey).toLowerCase()
        : (a as unknown as Record<string, string>)[sort.key]
      const bv = sort.key === 'name'
        ? (b.name ?? b.wallet_pubkey).toLowerCase()
        : (b as unknown as Record<string, string>)[sort.key]
      return av < bv ? -1 * dir : av > bv ? 1 * dir : 0
    })
  }, [allWallets, orgFilter, search, sort, orgMap])

  // Paginación local
  const totalPages = Math.max(1, Math.ceil(filtered.length / pageSize))
  const paged = filtered.slice((page - 1) * pageSize, page * pageSize)

  useEffect(() => { setPage(1) }, [statusFilter, orgFilter, tagFilter])

  // Conteos por status para los tabs
  const statusCounts = useMemo(() => {
    const c = { all: allWallets.length, active: 0, suspended: 0, revoked: 0 }
    allWallets.forEach(w => { c[w.status] += 1 })
    return c
  }, [allWallets])

  const tagOptions = useMemo(
    () => Array.from(new Set(allWallets.flatMap(w => w.tags))).sort(),
    [allWallets],
  )

  const orgOptions = useMemo(
    () => orgs.map(o => ({ value: o.id, label: o.name })).sort((a, b) => a.label.localeCompare(b.label)),
    [orgs],
  )

  const activeFilters = [
    statusFilter && {
      key: 'status',
      label: `Estado: ${STATUS_META[statusFilter].label}`,
      clear: () => setStatusFilter(''),
    },
    orgFilter && {
      key: 'org',
      label: `Organización: ${orgMap.get(orgFilter)?.name ?? orgFilter}`,
      clear: () => setOrgFilter(''),
    },
    tagFilter && {
      key: 'tag',
      label: `Tipo: ${tagFilter}`,
      clear: () => setTagFilter(''),
    },
  ].filter(Boolean) as Array<{ key: string; label: string; clear: () => void }>

  // Search shortcut
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

  // Click outside to close action menu
  useEffect(() => {
    if (!actionFor) return
    const fn = (e: MouseEvent) => {
      const target = e.target as HTMLElement | null
      if (target && !target.closest('[data-row-menu]')) setActionFor(null)
    }
    document.addEventListener('mousedown', fn)
    return () => document.removeEventListener('mousedown', fn)
  }, [actionFor])

  return (
    <div className="flex flex-col flex-1 overflow-hidden">
      <Topbar
        title="Custodios"
        subtitle={`${nf.format(total)} ${total === 1 ? 'wallet' : 'wallets'}`}
        actions={
          <div className="flex gap-2">
            <Button size="sm" variant="secondary" onClick={() => setShowRegister(true)}>
              <Plus className="h-4 w-4" /> Registrar externa
            </Button>
            <Button size="sm" onClick={() => setShowGenerate(true)}>
              <KeyRound className="h-4 w-4" /> Crear wallet
            </Button>
          </div>
        }
      />

      <div className="flex-1 overflow-y-auto">
        {/* Toolbar */}
        <div className="flex items-center justify-between gap-3 flex-wrap px-6 py-3 bg-card border-b border-border">
          <div className="inline-flex items-center rounded-md p-0.5 bg-muted flex-wrap">
            <FilterTab active={statusFilter === ''} onClick={() => setStatusFilter('')} count={statusCounts.all}>
              Todas
            </FilterTab>
            <FilterTab
              active={statusFilter === 'active'}
              onClick={() => setStatusFilter('active')}
              count={statusCounts.active}
              color={STATUS_META.active.color}
            >
              Activas
            </FilterTab>
            <FilterTab
              active={statusFilter === 'suspended'}
              onClick={() => setStatusFilter('suspended')}
              count={statusCounts.suspended}
              color={STATUS_META.suspended.color}
            >
              Suspendidas
            </FilterTab>
            <FilterTab
              active={statusFilter === 'revoked'}
              onClick={() => setStatusFilter('revoked')}
              count={statusCounts.revoked}
              color={STATUS_META.revoked.color}
            >
              Revocadas
            </FilterTab>
          </div>

          <div className="flex items-center gap-2 flex-wrap">
            <SearchInput value={search} onChange={setSearch} inputRef={searchRef} />
            <Combobox
              value={orgFilter}
              onChange={setOrgFilter}
              options={orgOptions}
              placeholder="Organización"
              icon={<Building2 className="h-3 w-3 text-muted-foreground" />}
              width={170}
            />
            <Combobox
              value={tagFilter}
              onChange={setTagFilter}
              options={tagOptions.map(t => ({ value: t, label: t }))}
              placeholder="Tipo"
              icon={<Tag className="h-3 w-3 text-muted-foreground" />}
              width={140}
            />
            <DensityToggle value={density} onChange={setDensity} />
            <Button size="icon" variant="ghost" onClick={() => refetch()} title="Actualizar">
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
              onClick={() => { setStatusFilter(''); setOrgFilter(''); setTagFilter('') }}
              className="text-xs text-primary hover:underline ml-1"
            >
              Limpiar todo
            </button>
            <span className="ml-auto text-xs text-muted-foreground tabular-nums">
              {nf.format(filtered.length)} {filtered.length === 1 ? 'resultado' : 'resultados'}
            </span>
          </div>
        )}

        {isLoading ? (
          <div className="flex justify-center py-20"><Spinner /></div>
        ) : filtered.length === 0 ? (
          <EmptyState
            icon={<Wallet className="h-12 w-12" />}
            title="Sin custodios"
            description="Crea una wallet para registrar un custodio logístico (Granja, Camión, Bodega, Aduana)."
            action={
              <Button size="sm" onClick={() => setShowGenerate(true)}>
                <KeyRound className="h-4 w-4" /> Crear primera wallet
              </Button>
            }
          />
        ) : (
          <>
            <div className="bg-card">
              <table className="w-full text-sm tabular-nums">
                <thead className="sticky top-0 bg-card z-10">
                  <tr className="border-b border-border">
                    <Th sortKey="name" sort={sort} onSort={setSort}>Custodio</Th>
                    <Th>Organización</Th>
                    <Th>Tipo</Th>
                    <Th sortKey="status" sort={sort} onSort={setSort}>Estado</Th>
                    <Th sortKey="created_at" sort={sort} onSort={setSort} align="right">Creado</Th>
                    <th className="w-10 bg-card" />
                  </tr>
                </thead>
                <tbody>
                  {paged.map(w => (
                    <Row
                      key={w.id}
                      wallet={w}
                      orgName={w.organization_id ? orgMap.get(w.organization_id)?.name ?? null : null}
                      density={density}
                      menuOpen={actionFor === w.id}
                      onToggleMenu={() => setActionFor(actionFor === w.id ? null : w.id)}
                    />
                  ))}
                </tbody>
              </table>
            </div>

            <Pagination
              page={page}
              setPage={setPage}
              totalPages={totalPages}
              total={filtered.length}
              pageSize={pageSize}
              setPageSize={setPageSize}
            />
          </>
        )}
      </div>

      <RegisterWalletModal open={showRegister} onClose={() => setShowRegister(false)} />
      <GenerateWalletModal open={showGenerate} onClose={() => setShowGenerate(false)} />
    </div>
  )
}

// ─────────────────────────────────────────────────────────────────────────────

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
  wallet, orgName, density, menuOpen, onToggleMenu,
}: {
  wallet: WalletType
  orgName: string | null
  density: 'compact' | 'comfortable' | 'spacious'
  menuOpen: boolean
  onToggleMenu: () => void
}) {
  const py = density === 'compact' ? 'py-1.5' : density === 'spacious' ? 'py-3.5' : 'py-2.5'
  const displayName = wallet.name || orgName || 'Sin nombre'
  const meta = STATUS_META[wallet.status]

  return (
    <tr className="hover:bg-muted/50 transition-colors border-b border-border/50">
      <td className={cn(py, 'px-4')}>
        <Link to={`/wallets/${wallet.id}`} className="block group">
          <div className="flex items-center gap-3">
            <div
              className="h-9 w-9 rounded-full inline-flex items-center justify-center shrink-0 text-[11px] font-semibold"
              style={{ background: meta.color + '1A', color: meta.color }}
            >
              {initials(displayName)}
            </div>
            <div className="min-w-0">
              <div className="text-sm font-semibold text-foreground group-hover:text-primary tracking-tight truncate">
                {displayName}
              </div>
              <div className="mt-0.5 inline-flex items-center gap-1">
                <PubkeyChip pubkey={wallet.wallet_pubkey} />
              </div>
            </div>
          </div>
        </Link>
      </td>
      <td className={cn(py, 'px-4 text-foreground/80')}>
        {orgName ?? <span className="text-muted-foreground">—</span>}
      </td>
      <td className={cn(py, 'px-4')}>
        <div className="flex flex-wrap gap-1">
          {wallet.tags.length === 0
            ? <span className="text-muted-foreground text-xs">—</span>
            : wallet.tags.slice(0, 3).map(t => (
              <span key={t} className="rounded bg-muted px-1.5 h-5 inline-flex items-center text-[10.5px] font-medium text-foreground/80">
                {t}
              </span>
            ))
          }
          {wallet.tags.length > 3 && (
            <span className="text-[10.5px] text-muted-foreground tabular-nums">+{wallet.tags.length - 3}</span>
          )}
        </div>
      </td>
      <td className={cn(py, 'px-4')}>
        <span className={cn('inline-flex items-center gap-1.5 h-6 px-2.5 rounded-full text-xs font-medium', meta.bg, meta.fg)}>
          <span className="h-1.5 w-1.5 rounded-full" style={{ background: meta.color }} />
          {meta.label}
        </span>
      </td>
      <td className={cn(py, 'px-4 text-right text-xs text-muted-foreground')}>
        {fmtRelative(wallet.created_at)}
      </td>
      <td className={cn(py, 'px-2 relative')} data-row-menu>
        <button
          onClick={e => { e.stopPropagation(); e.preventDefault(); onToggleMenu() }}
          className="h-7 w-7 inline-flex items-center justify-center rounded-md text-muted-foreground hover:bg-muted"
          aria-label="Acciones de wallet"
          aria-haspopup="menu"
          aria-expanded={menuOpen}
        >
          <MoreHorizontal className="h-4 w-4" />
        </button>
        {menuOpen && <RowActionsMenu wallet={wallet} onClose={onToggleMenu} />}
      </td>
    </tr>
  )
}

function PubkeyChip({ pubkey }: { pubkey: string }) {
  const [copied, setCopied] = useState(false)
  const handleCopy = async (e: React.MouseEvent) => {
    e.preventDefault()
    e.stopPropagation()
    await copyToClipboard(pubkey)
    setCopied(true)
    setTimeout(() => setCopied(false), 1200)
  }
  return (
    <button
      onClick={handleCopy}
      title={pubkey}
      className="inline-flex items-center gap-1 px-1.5 h-5 rounded bg-muted hover:bg-muted/70 text-[10.5px] text-muted-foreground font-mono tabular-nums"
    >
      <KeyRound className="h-2.5 w-2.5" />
      {shortPubkey(pubkey, 4)}
      {copied
        ? <Check className="h-2.5 w-2.5 text-emerald-600" />
        : <Copy className="h-2.5 w-2.5 opacity-50" />}
    </button>
  )
}

function RowActionsMenu({ wallet, onClose }: { wallet: WalletType; onClose: () => void }) {
  const update = useUpdateWallet()
  const toast = useToast()
  const { solanaCluster } = useSettingsStore()

  const setStatus = async (status: WalletStatus) => {
    try {
      await update.mutateAsync({ id: wallet.id, data: { status } })
      const labels: Record<WalletStatus, string> = {
        active: 'activada', suspended: 'suspendida', revoked: 'revocada',
      }
      toast.success(`Wallet ${labels[status]}`)
    } catch (e) {
      toast.error(e instanceof Error ? e.message : 'Error al actualizar')
    }
    onClose()
  }

  return (
    <div
      onClick={e => e.stopPropagation()}
      className="absolute right-2 top-9 z-40 rounded-lg overflow-hidden bg-card border border-border shadow-xl py-1"
      style={{ minWidth: 220 }}
      role="menu"
    >
      <Link to={`/wallets/${wallet.id}`} onClick={onClose} className="block">
        <span className="w-full inline-flex items-center gap-2 px-2.5 h-8 text-xs hover:bg-muted text-foreground">
          <ChevronRight className="h-3.5 w-3.5 text-muted-foreground" />
          Ver detalle
        </span>
      </Link>
      <a
        href={explorerAddressUrl(wallet.wallet_pubkey, solanaCluster)}
        target="_blank"
        rel="noopener noreferrer"
        onClick={onClose}
        className="block"
      >
        <span className="w-full inline-flex items-center gap-2 px-2.5 h-8 text-xs hover:bg-muted text-foreground">
          <ExternalLink className="h-3.5 w-3.5 text-muted-foreground" />
          Ver en Solana Explorer
        </span>
      </a>
      <button
        onClick={() => { copyToClipboard(wallet.wallet_pubkey); toast.success('Pubkey copiada'); onClose() }}
        className="w-full text-left"
      >
        <span className="w-full inline-flex items-center gap-2 px-2.5 h-8 text-xs hover:bg-muted text-foreground">
          <Copy className="h-3.5 w-3.5 text-muted-foreground" />
          Copiar pubkey completa
        </span>
      </button>
      <div className="my-1 border-t border-border" />
      <div className="px-2.5 pt-1 pb-0.5 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
        Cambiar estado
      </div>
      {wallet.status !== 'active' && (
        <button onClick={() => setStatus('active')} className="w-full text-left">
          <span className="w-full inline-flex items-center gap-2 px-2.5 h-8 text-xs hover:bg-muted text-foreground">
            <ShieldCheck className="h-3.5 w-3.5 text-emerald-600" /> Activar
          </span>
        </button>
      )}
      {wallet.status !== 'suspended' && (
        <button onClick={() => setStatus('suspended')} className="w-full text-left">
          <span className="w-full inline-flex items-center gap-2 px-2.5 h-8 text-xs hover:bg-muted text-foreground">
            <ShieldAlert className="h-3.5 w-3.5 text-amber-600" /> Suspender
          </span>
        </button>
      )}
      {wallet.status !== 'revoked' && (
        <button onClick={() => setStatus('revoked')} className="w-full text-left">
          <span className="w-full inline-flex items-center gap-2 px-2.5 h-8 text-xs hover:bg-red-50 text-red-600">
            <ShieldOff className="h-3.5 w-3.5 text-red-600" /> Revocar
          </span>
        </button>
      )}
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
  const start = total === 0 ? 0 : (page - 1) * pageSize + 1
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
            {[10, 20, 50, 100].map(n => <option key={n} value={n}>{n}</option>)}
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
