import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { MapPin, Plus, Check, X, Trash2, Satellite, Loader2, FileText } from 'lucide-react'
import { usePlots, useDeletePlot, useScreenDeforestation, usePlotDocuments } from '@/hooks/useCompliance'
import { useOrganizations } from '@/hooks/useTaxonomy'
import { useConfirm } from '@/store/confirm'
import { useToast } from '@/store/toast'
import { DataTable, type Column } from '@/components/ui/datatable'
import { SkeletonTable } from '@/components/ui/skeleton'
import { EmptyState } from '@/components/ui/EmptyState'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { PlotMap } from '@/components/compliance/PlotMap'
import type { CompliancePlot } from '@/types/compliance'
import { COMMODITY_LABEL, COMMODITY_COLOR, type CommodityType } from '@/types/commodity'

// ─── Risk badge ──────────────────────────────────────────────────────────────

const riskVariant: Record<string, 'success' | 'warning' | 'danger' | 'default'> = {
  low: 'success',
  standard: 'warning',
  high: 'danger',
  critical: 'danger',
}

const riskLabel: Record<string, string> = {
  low: 'Bajo',
  standard: 'Estandar',
  high: 'Alto',
  critical: 'Critico',
}

// ─── Compliance mini-badges ──────────────────────────────────────────────────

function ComplianceBadges({ plot }: { plot: CompliancePlot }) {
  return (
    <div className="flex items-center gap-1.5">
      <span
        className={`inline-flex items-center gap-0.5 rounded px-1.5 py-0.5 text-[10px] font-medium ${
          plot.deforestation_free
            ? 'bg-emerald-50 text-emerald-700'
            : 'bg-red-50 text-red-600'
        }`}
        title="Libre de deforestacion"
      >
        {plot.deforestation_free ? <Check className="h-2.5 w-2.5" /> : <X className="h-2.5 w-2.5" />}
        DF
      </span>
      <span
        className={`inline-flex items-center gap-0.5 rounded px-1.5 py-0.5 text-[10px] font-medium ${
          plot.legal_land_use
            ? 'bg-emerald-50 text-emerald-700'
            : 'bg-red-50 text-red-600'
        }`}
        title="Uso legal del suelo"
      >
        {plot.legal_land_use ? <Check className="h-2.5 w-2.5" /> : <X className="h-2.5 w-2.5" />}
        LL
      </span>
      <span
        className={`inline-flex items-center gap-0.5 rounded px-1.5 py-0.5 text-[10px] font-medium ${
          plot.cutoff_date_compliant
            ? 'bg-emerald-50 text-emerald-700'
            : 'bg-red-50 text-red-600'
        }`}
        title="Fecha de corte cumplida"
      >
        {plot.cutoff_date_compliant ? <Check className="h-2.5 w-2.5" /> : <X className="h-2.5 w-2.5" />}
        FC
      </span>
    </div>
  )
}

// ─── Doc count badge (fetches docs for a single plot) ───────────────────────

function PlotDocBadge({ plotId }: { plotId: string }) {
  const { data: docs } = usePlotDocuments(plotId)
  const count = docs?.length ?? 0
  if (count === 0) {
    return (
      <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-medium bg-red-50 text-red-500 border border-red-100">
        <FileText className="h-2.5 w-2.5" /> 0
      </span>
    )
  }
  return (
    <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-medium bg-blue-50 text-blue-600 border border-blue-100">
      <FileText className="h-2.5 w-2.5" /> {count}
    </span>
  )
}


// ─── Main Page ───────────────────────────────────────────────────────────────

export default function PlotsPage() {
  const { data: plots = [], isLoading } = usePlots()
  const { data: orgsData } = useOrganizations()
  const orgs = orgsData?.items ?? []
  const deletePlot = useDeletePlot()
  const screenDeforestation = useScreenDeforestation()
  const confirm = useConfirm()
  const toast = useToast()
  const navigate = useNavigate()
  const [selectedPlotId, setSelectedPlotId] = useState<string | undefined>()
  const [commodityFilter, setCommodityFilter] = useState<CommodityType | 'all'>('all')

  const filteredPlots = commodityFilter === 'all'
    ? plots
    : plots.filter((p) => (p.commodity_type ?? null) === commodityFilter)

  const orgMap = Object.fromEntries(orgs.map((o) => [o.id, o.name]))

  async function handleDelete(id: string) {
    const ok = await confirm({
      title: 'Eliminar parcela',
      message: 'Esta accion eliminara la parcela y sus vinculos de cumplimiento. Esta seguro?',
      confirmLabel: 'Eliminar',
    })
    if (!ok) return
    try {
      await deletePlot.mutateAsync(id)
      toast.success('Parcela eliminada')
    } catch (e: any) {
      toast.error(e.message ?? 'Error al eliminar')
    }
  }

  const columns: Column<CompliancePlot>[] = [
    {
      key: 'plot_code',
      header: 'Codigo',
      sortable: true,
      render: (row) => (
        <button onClick={() => navigate(`/cumplimiento/parcelas/${row.id}`)} className="font-medium text-primary hover:underline">
          {row.plot_code}
        </button>
      ),
    },
    {
      key: 'organization',
      header: 'Organizacion',
      render: (row) => (
        <span className="text-sm text-muted-foreground">
          {row.organization_id ? (orgMap[row.organization_id] ?? 'Desconocida') : '—'}
        </span>
      ),
    },
    {
      key: 'plot_area_ha',
      header: 'Area (ha)',
      sortable: true,
      render: (row) => (
        <span className="text-sm text-muted-foreground tabular-nums">
          {row.plot_area_ha != null ? Number(row.plot_area_ha).toFixed(2) : '—'}
        </span>
      ),
    },
    {
      key: 'commodity_type',
      header: 'Commodity',
      render: (row) => {
        const c = (row.commodity_type ?? null) as CommodityType | null
        if (!c) return <span className="text-xs text-muted-foreground">—</span>
        return (
          <span className={`inline-flex items-center rounded px-1.5 py-0.5 text-[10px] font-medium border ${COMMODITY_COLOR[c]}`}>
            {COMMODITY_LABEL[c]}
          </span>
        )
      },
    },
    {
      key: 'location',
      header: 'Municipio/Depto',
      render: (row) => (
        <span className="text-sm text-muted-foreground">
          {[row.municipality, row.region].filter(Boolean).join(', ') || '—'}
        </span>
      ),
    },
    {
      key: 'geolocation_type',
      header: 'Tipo',
      render: (row) => (
        <Badge variant="default">
          {row.geolocation_type === 'point' ? 'Punto' : row.geolocation_type === 'polygon' ? 'Poligono' : row.geolocation_type}
        </Badge>
      ),
    },
    {
      key: 'risk_level',
      header: 'Riesgo',
      sortable: true,
      render: (row) => (
        <Badge variant={riskVariant[row.risk_level] ?? 'default'} dot>
          {riskLabel[row.risk_level] ?? row.risk_level}
        </Badge>
      ),
    },
    {
      key: 'compliance',
      header: 'Cumplimiento',
      render: (row) => <ComplianceBadges plot={row} />,
    },
    {
      key: 'docs',
      header: 'Docs',
      render: (row) => (
        <button onClick={() => navigate(`/cumplimiento/parcelas/${row.id}`)} title="Ver documentos">
          <PlotDocBadge plotId={row.id} />
        </button>
      ),
    },
    {
      key: 'actions',
      header: '',
      render: (row) => (
        <div className="flex items-center gap-1 justify-end">
          <button
            onClick={async () => {
              try {
                const result = await screenDeforestation.mutateAsync(row.id)
                if (result.deforestation_free === true) {
                  toast.success(`${row.plot_code}: Libre de deforestacion (0 alertas)`)
                } else if (result.deforestation_free === false) {
                  toast.error(`${row.plot_code}: ${result.alerts_count} alertas de deforestacion detectadas`)
                } else {
                  toast.error(result.error || 'No se pudo verificar')
                }
              } catch (e: any) {
                toast.error(e.message ?? 'Error al verificar')
              }
            }}
            disabled={screenDeforestation.isPending}
            className="rounded-lg p-1.5 text-muted-foreground hover:text-emerald-600 hover:bg-emerald-50 transition-colors"
            title="Verificar deforestacion (Global Forest Watch)"
          >
            {screenDeforestation.isPending ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Satellite className="h-3.5 w-3.5" />}
          </button>
          <button
            onClick={() => handleDelete(row.id)}
            className="rounded-lg p-1.5 text-muted-foreground hover:text-red-600 hover:bg-red-50 transition-colors"
            title="Eliminar"
          >
            <Trash2 className="h-3.5 w-3.5" />
          </button>
        </div>
      ),
    },
  ]

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-amber-50">
            <MapPin className="h-5 w-5 text-amber-600" />
          </div>
          <div>
            <h1 className="text-lg font-semibold text-foreground">Parcelas de Produccion</h1>
            <p className="text-sm text-muted-foreground">Predios registrados para trazabilidad y cumplimiento</p>
          </div>
        </div>
        <Button
          variant="primary"
          size="sm"
          onClick={() => navigate('/cumplimiento/parcelas/nueva')}
        >
          <Plus className="h-4 w-4 mr-1.5" />
          Nueva Parcela
        </Button>
      </div>

      {/* Commodity filter */}
      <div className="flex items-center gap-2">
        <span className="text-xs font-medium text-muted-foreground">Commodity:</span>
        <select
          value={commodityFilter}
          onChange={(e) => setCommodityFilter(e.target.value as CommodityType | 'all')}
          className="h-8 rounded-md border border-input bg-background px-2 text-xs"
        >
          <option value="all">Todos</option>
          <option value="coffee">Cafe</option>
          <option value="cacao">Cacao</option>
          <option value="palm">Palma</option>
          <option value="other">Otro</option>
        </select>
      </div>

      {/* Map */}
      {filteredPlots.length > 0 && (
        <PlotMap
          plots={filteredPlots}
          height="350px"
          selectedPlotId={selectedPlotId}
          onPlotClick={(plot) => {
            setSelectedPlotId(plot.id)
            navigate(`/cumplimiento/parcelas/${plot.id}`)
          }}
        />
      )}

      {/* Table */}
      <DataTable
        columns={columns}
        data={filteredPlots}
        rowKey={(row) => row.id}
        isLoading={isLoading}
        loadingState={<SkeletonTable columns={6} rows={8} />}
        emptyState={
          <EmptyState
            icon={MapPin}
            title="Sin parcelas registradas"
            description="Crea una parcela para comenzar a gestionar tu cumplimiento EUDR."
            action={{ label: 'Nueva parcela', to: '/cumplimiento/parcelas/nueva', icon: Plus }}
          />
        }
        emptyMessage="No hay parcelas registradas. Crea una para comenzar."
      />

    </div>
  )
}
