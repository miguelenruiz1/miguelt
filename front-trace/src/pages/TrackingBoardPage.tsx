import { useState, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import { RefreshCw, ChevronRight, Package, Plus } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from '@/components/ui/table'
import { useQueries, useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api'
import { useWalletList } from '@/hooks/useWallets'
import { useOrganizations } from '@/hooks/useTaxonomy'
import { useWorkflowStates } from '@/hooks/useWorkflow'
import { cn } from '@/lib/utils'
import type { Asset, WorkflowState } from '@/types/api'

// Fallback when the tenant has no workflow states yet
const FALLBACK_STATES = [
  { slug: 'in_custody', label: 'En custodia', color: '#10b981' },
  { slug: 'in_transit', label: 'En tránsito', color: '#f59e0b' },
  { slug: 'loaded',     label: 'Cargado',     color: '#6366f1' },
  { slug: 'qc_passed',  label: 'QC aprobado', color: '#22c55e' },
  { slug: 'qc_failed',  label: 'QC rechazado',color: '#ef4444' },
  { slug: 'released',   label: 'Liberado',    color: '#0ea5e9' },
  { slug: 'burned',     label: 'Quemado',     color: '#71717a' },
]

/* ── (Legacy states removed — columns are now 100% workflow-driven) ── */

/* ── Dynamic badge using workflow state color ──────────────────── */

function DynamicStateBadge({ state, stateMap }: { state: string; stateMap: Map<string, { label: string; color: string }> }) {
  const cfg = stateMap.get(state)
  if (cfg) {
    return (
      <Badge
        className="border-0"
        style={{ backgroundColor: `${cfg.color}20`, color: cfg.color }}
      >
        {cfg.label}
      </Badge>
    )
  }
  return <Badge variant="secondary">{state}</Badge>
}

/* ── Blockchain dot ─────────────────────────────────────────────── */

function BlockchainDot({ status }: { status: string }) {
  const cfg: Record<string, { dot: string; label: string }> = {
    CONFIRMED: { dot: 'bg-emerald-500', label: 'Confirmado' },
    PENDING:   { dot: 'bg-amber-500 animate-pulse', label: 'Pendiente' },
    FAILED:    { dot: 'bg-red-500', label: 'Fallido' },
    SIMULATED: { dot: 'bg-blue-400', label: 'Simulado' },
    SKIPPED:   { dot: 'bg-gray-300', label: 'Sin anclar' },
  }
  const c = cfg[status] ?? cfg.SKIPPED
  return (
    <div className="flex items-center gap-1.5" title={c.label}>
      <div className={cn('h-2 w-2 rounded-full shrink-0', c.dot)} />
      <span className="text-xs text-muted-foreground">{c.label}</span>
    </div>
  )
}

/* ── Time helper ────────────────────────────────────────────────── */

function relativeTime(iso: string): string {
  const ms = Date.now() - new Date(iso).getTime()
  const mins = Math.floor(ms / 60000)
  if (mins < 1) return 'ahora'
  if (mins < 60) return `${mins}m`
  const hrs = Math.floor(mins / 60)
  if (hrs < 24) return `${hrs}h`
  const days = Math.floor(hrs / 24)
  return `${days}d`
}

/* ── Page ────────────────────────────────────────────────────────── */

export function TrackingBoardPage() {
  const navigate = useNavigate()
  const [stateFilter, setStateFilter] = useState<string>('all')
  const [filterOrgId, setFilterOrgId] = useState('')

  // Load workflow states (dynamic) — falls back to legacy if empty
  const { data: workflowStates } = useWorkflowStates()

  const columns = useMemo(() => {
    if (workflowStates?.length) {
      return workflowStates.map(ws => ({
        slug: ws.slug,
        label: ws.label,
        color: ws.color,
      }))
    }
    return FALLBACK_STATES
  }, [workflowStates])

  const usingFallback = !workflowStates?.length

  // Build a lookup map for badge rendering
  const stateMap = useMemo(() => {
    const m = new Map<string, { label: string; color: string }>()
    for (const c of columns) {
      m.set(c.slug, { label: c.label, color: c.color })
    }
    return m
  }, [columns])

  // One query per state column — same polling logic
  const stateResults = useQueries({
    queries: columns.map((col) => ({
      queryKey: ['assets', 'board', col.slug],
      queryFn: () => api.assets.list({ state: col.slug, limit: 200 }),
      refetchInterval: 15_000,
    })),
  })

  const { data: walletsData } = useWalletList({ limit: 500 })
  const { data: orgsData } = useOrganizations()

  const wallets = walletsData?.items ?? []
  const orgs = orgsData?.items ?? []

  const isFetching = stateResults.some((r) => r.isFetching)
  const isLoading = stateResults.some((r) => r.isLoading && !r.data)

  // Build counts per state
  const countByState: Record<string, number> = {}
  let allAssets: Asset[] = []
  columns.forEach((s, i) => {
    const items = stateResults[i]?.data?.items ?? []
    countByState[s.slug] = items.length
    allAssets = allAssets.concat(items)
  })
  const totalCount = allAssets.length

  const refetchAll = () => stateResults.forEach((r) => r.refetch())

  // Org lookup
  const walletOrgMap = new Map<string, string>()
  for (const w of wallets) {
    if (w.organization_id) {
      const org = orgs.find((o) => o.id === w.organization_id)
      if (org) walletOrgMap.set(w.wallet_pubkey, org.name)
    }
  }
  const getOrgName = (pubkey: string) => walletOrgMap.get(pubkey) ?? null

  // Apply filters
  const orgWalletPubkeys = filterOrgId
    ? new Set(wallets.filter((w) => w.organization_id === filterOrgId).map((w) => w.wallet_pubkey))
    : null

  let filtered = stateFilter === 'all'
    ? allAssets
    : allAssets.filter(a => a.state === stateFilter)

  if (orgWalletPubkeys) {
    filtered = filtered.filter(a => orgWalletPubkeys.has(a.current_custodian_wallet))
  }

  // Sort by most recent first
  filtered.sort((a, b) => new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime())

  // Smart column visibility — hide Custodio if all empty
  const hasCustodianData = filtered.some(a => getOrgName(a.current_custodian_wallet) !== null)
  const colSpan = hasCustodianData ? 7 : 6

  // Tabs — show top states + "Todos"
  const tabs = [
    { label: 'Todos', value: 'all', count: totalCount, color: undefined as string | undefined },
    ...columns
      .filter(s => countByState[s.slug] > 0)
      .map(s => ({ label: s.label, value: s.slug, count: countByState[s.slug], color: s.color })),
  ]

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Panel de Seguimiento</h1>
          <p className="text-sm text-muted-foreground mt-0.5">{totalCount} cargas activas</p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={refetchAll}>
            <RefreshCw className={cn('h-3.5 w-3.5 mr-1.5', isFetching && 'animate-spin')} />
            Actualizar
          </Button>
          <span className="text-xs text-muted-foreground hidden sm:inline">Cada 15s</span>
        </div>
      </div>

      {/* Filters: state tabs + org select */}
      <div className="flex items-center justify-between gap-4 flex-wrap">
        <div className="flex gap-1 flex-wrap">
          {tabs.map(tab => (
            <button
              key={tab.value}
              onClick={() => setStateFilter(tab.value)}
              className={cn(
                'flex items-center gap-1.5 rounded-md px-3 py-1.5 text-sm transition-colors duration-150',
                stateFilter === tab.value
                  ? 'font-medium'
                  : 'bg-muted text-muted-foreground hover:bg-muted/80',
              )}
              style={
                stateFilter === tab.value && tab.color
                  ? { backgroundColor: tab.color, color: '#fff' }
                  : stateFilter === tab.value
                    ? { backgroundColor: 'hsl(var(--primary))', color: 'hsl(var(--primary-foreground))' }
                    : undefined
              }
            >
              {tab.label}
              {tab.count > 0 && (
                <span className={cn(
                  'text-[10px] font-medium rounded-full px-1.5',
                  stateFilter === tab.value
                    ? 'bg-card/20 text-white'
                    : 'bg-background text-muted-foreground',
                )}>
                  {tab.count}
                </span>
              )}
            </button>
          ))}
        </div>

        <select
          value={filterOrgId}
          onChange={(e) => setFilterOrgId(e.target.value)}
          className="h-8 rounded-md border border-input bg-transparent px-3 text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-ring"
        >
          <option value="">Todas las orgs</option>
          {orgs.map((o) => (
            <option key={o.id} value={o.id}>{o.name}</option>
          ))}
        </select>
      </div>

      {/* Table */}
      <div className="rounded-lg border border-border overflow-hidden">
        <Table>
          <TableHeader>
            <TableRow className="bg-muted/50 hover:bg-muted/50">
              <TableHead className="w-[140px]">Producto</TableHead>
              <TableHead className="w-[100px]">Cantidad</TableHead>
              <TableHead className="w-[130px]">Estado</TableHead>
              {hasCustodianData && <TableHead>Custodio</TableHead>}
              <TableHead className="w-[120px]">Blockchain</TableHead>
              <TableHead className="w-[80px] text-right">Hace</TableHead>
              <TableHead className="w-[40px]" />
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading ? (
              <TableRow>
                <TableCell colSpan={colSpan} className="h-32 text-center">
                  <div className="flex items-center justify-center gap-2 text-muted-foreground">
                    <div className="h-4 w-4 animate-spin rounded-full border-2 border-primary border-t-transparent" />
                    Cargando...
                  </div>
                </TableCell>
              </TableRow>
            ) : filtered.length === 0 ? (
              <TableRow>
                <TableCell colSpan={colSpan} className="h-48 text-center">
                  <div className="flex flex-col items-center gap-3">
                    <div className="h-12 w-12 rounded-xl bg-muted flex items-center justify-center">
                      <Package className="h-6 w-6 text-muted-foreground/50" />
                    </div>
                    <div>
                      <p className="text-sm font-medium">Sin cargas activas</p>
                      <p className="text-xs text-muted-foreground mt-1">Crea una nueva carga para comenzar el seguimiento</p>
                    </div>
                    <Button size="sm" onClick={() => navigate('/assets')}>
                      <Plus className="h-3.5 w-3.5 mr-1.5" />
                      Nueva carga
                    </Button>
                  </div>
                </TableCell>
              </TableRow>
            ) : (
              filtered.map(asset => {
                const meta = asset.metadata as Record<string, unknown> | undefined
                const qty = meta?.weight ?? meta?.quantity ?? meta?.quantity_kg
                return (
                  <TableRow
                    key={asset.id}
                    className="cursor-pointer hover:bg-muted/40 transition-colors group"
                    onClick={() => navigate(`/assets/${asset.id}`)}
                  >
                    <TableCell className="font-medium capitalize">
                      {asset.product_type}
                    </TableCell>
                    <TableCell className="text-sm text-muted-foreground">
                      {qty != null ? `${Number(qty).toLocaleString('es')} ${(meta?.weight_unit as string) ?? 'kg'}` : '—'}
                    </TableCell>
                    <TableCell>
                      <DynamicStateBadge state={asset.state} stateMap={stateMap} />
                    </TableCell>
                    {hasCustodianData && (
                      <TableCell className="text-muted-foreground text-sm">
                        {getOrgName(asset.current_custodian_wallet) ?? '—'}
                      </TableCell>
                    )}
                    <TableCell>
                      <BlockchainDot status={asset.blockchain_status} />
                    </TableCell>
                    <TableCell className="text-xs text-muted-foreground text-right tabular-nums">
                      {relativeTime(asset.updated_at)}
                    </TableCell>
                    <TableCell>
                      <ChevronRight className="h-4 w-4 text-muted-foreground/0 group-hover:text-muted-foreground transition-colors" />
                    </TableCell>
                  </TableRow>
                )
              })
            )}
          </TableBody>
        </Table>
      </div>

      {/* Footer count */}
      {filtered.length > 0 && (
        <p className="text-xs text-muted-foreground text-right">
          {filtered.length} de {totalCount} cargas
        </p>
      )}
    </div>
  )
}
