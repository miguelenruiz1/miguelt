import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { MapPin, Plus, Check, X, Pencil, Trash2, Satellite, Loader2, FileText } from 'lucide-react'
import { useForm, Controller } from 'react-hook-form'
import { z } from 'zod'
import { zodResolver } from '@hookform/resolvers/zod'
import { usePlots, useCreatePlot, useDeletePlot, useScreenDeforestation, usePlotDocuments } from '@/hooks/useCompliance'
import { useOrganizations } from '@/hooks/useTaxonomy'
import { useConfirm } from '@/store/confirm'
import { useToast } from '@/store/toast'
import { DataTable, type Column } from '@/components/ui/datatable'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { LegacyDialog as Dialog } from '@/components/ui/legacy-dialog'
import { PlotMap } from '@/components/compliance/PlotMap'
import type { CompliancePlot, RiskLevel } from '@/types/compliance'

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

// ─── Create Plot Schema ──────────────────────────────────────────────────────

const plotSchema = z.object({
  plot_code: z.string().min(1, 'Codigo requerido'),
  organization_id: z.string().optional().nullable(),
  plot_area_ha: z.coerce.number().positive('Debe ser positivo').optional().nullable(),
  geolocation_type: z.enum(['point', 'polygon']).default('point'),
  lat: z.coerce.number().min(-90).max(90).optional().nullable(),
  lng: z.coerce.number().min(-180).max(180).optional().nullable(),
  country_code: z.string().default('CO'),
  region: z.string().optional().nullable(),
  municipality: z.string().optional().nullable(),
  deforestation_free: z.boolean().default(true),
  cutoff_date_compliant: z.boolean().default(true),
  legal_land_use: z.boolean().default(true),
  risk_level: z.enum(['low', 'standard', 'high']).default('low'),
  establishment_date: z.string().optional().nullable(),
  crop_type: z.string().optional().nullable(),
  renovation_date: z.string().optional().nullable(),
  renovation_type: z.string().optional().nullable(),
})

type PlotFormValues = z.infer<typeof plotSchema>

// ─── Create Plot Modal ───────────────────────────────────────────────────────

function CreatePlotModal({ onClose }: { onClose: () => void }) {
  const create = useCreatePlot()
  const toast = useToast()
  const { data: orgsData } = useOrganizations()
  const orgs = orgsData?.items ?? []

  const {
    register,
    handleSubmit,
    control,
    formState: { errors },
  } = useForm<PlotFormValues>({
    resolver: zodResolver(plotSchema),
    defaultValues: {
      plot_code: '',
      organization_id: null,
      plot_area_ha: null,
      geolocation_type: 'point',
      lat: null,
      lng: null,
      country_code: 'CO',
      region: null,
      municipality: null,
      deforestation_free: true,
      cutoff_date_compliant: true,
      legal_land_use: true,
      risk_level: 'low',
      establishment_date: null,
      crop_type: null,
      renovation_date: null,
      renovation_type: null,
    },
  })

  async function onSubmit(values: PlotFormValues) {
    try {
      await create.mutateAsync({
        plot_code: values.plot_code,
        organization_id: values.organization_id || null,
        plot_area_ha: values.plot_area_ha ?? null,
        geolocation_type: values.geolocation_type,
        lat: values.lat ?? null,
        lng: values.lng ?? null,
        country_code: values.country_code,
        region: values.region || null,
        municipality: values.municipality || null,
        deforestation_free: values.deforestation_free,
        cutoff_date_compliant: values.cutoff_date_compliant,
        legal_land_use: values.legal_land_use,
        risk_level: values.risk_level,
        establishment_date: values.establishment_date || null,
        crop_type: values.crop_type || null,
        renovation_date: values.renovation_date || null,
        renovation_type: values.renovation_type || null,
      })
      toast.success('Parcela creada')
      onClose()
    } catch (e: any) {
      toast.error(e.message ?? 'Error al crear parcela')
    }
  }

  const inputCls =
    'w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-primary focus:ring-1 focus:ring-ring outline-none'
  const labelCls = 'block text-sm font-medium text-foreground mb-1'
  const errCls = 'mt-0.5 text-xs text-red-500'

  return (
    <Dialog
      open
      onClose={onClose}
      title="Nueva Parcela"
      description="Registra un predio de produccion para trazabilidad"
      size="lg"
      footer={
        <>
          <Button variant="secondary" onClick={onClose}>Cancelar</Button>
          <Button variant="primary" loading={create.isPending} onClick={handleSubmit(onSubmit)}>
            Crear parcela
          </Button>
        </>
      }
    >
      <form className="space-y-4" onSubmit={handleSubmit(onSubmit)}>
        {/* Row 1 */}
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className={labelCls}>Codigo de parcela *</label>
            <input {...register('plot_code')} className={inputCls} placeholder="FINCA-001" />
            {errors.plot_code && <p className={errCls}>{errors.plot_code.message}</p>}
          </div>
          <div>
            <label className={labelCls}>Organizacion</label>
            <select {...register('organization_id')} className={inputCls}>
              <option value="">Sin asignar</option>
              {orgs.map((o) => (
                <option key={o.id} value={o.id}>{o.name}</option>
              ))}
            </select>
          </div>
        </div>

        {/* Row 2 */}
        <div className="grid grid-cols-3 gap-4">
          <div>
            <label className={labelCls}>Area (ha)</label>
            <input {...register('plot_area_ha')} type="number" step="0.01" className={inputCls} placeholder="12.5" />
          </div>
          <div>
            <label className={labelCls}>Tipo geolocalizacion</label>
            <Controller
              name="geolocation_type"
              control={control}
              render={({ field }) => (
                <div className="flex gap-3 pt-2">
                  <label className="flex items-center gap-1.5 text-sm text-foreground">
                    <input
                      type="radio"
                      value="point"
                      checked={field.value === 'point'}
                      onChange={() => field.onChange('point')}
                      className="accent-primary"
                    />
                    Punto
                  </label>
                  <label className="flex items-center gap-1.5 text-sm text-foreground">
                    <input
                      type="radio"
                      value="polygon"
                      checked={field.value === 'polygon'}
                      onChange={() => field.onChange('polygon')}
                      className="accent-primary"
                    />
                    Poligono
                  </label>
                </div>
              )}
            />
          </div>
          <div>
            <label className={labelCls}>Nivel de riesgo</label>
            <select {...register('risk_level')} className={inputCls}>
              <option value="low">Bajo</option>
              <option value="standard">Estandar</option>
              <option value="high">Alto</option>
            </select>
          </div>
        </div>

        {/* Row 3: Coordinates */}
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className={labelCls}>Latitud</label>
            <input {...register('lat')} type="number" step="0.000001" className={inputCls} placeholder="4.710989" />
          </div>
          <div>
            <label className={labelCls}>Longitud</label>
            <input {...register('lng')} type="number" step="0.000001" className={inputCls} placeholder="-74.072092" />
          </div>
        </div>

        {/* Row 4: Location */}
        <div className="grid grid-cols-3 gap-4">
          <div>
            <label className={labelCls}>Pais</label>
            <input {...register('country_code')} className={inputCls} placeholder="CO" maxLength={2} />
          </div>
          <div>
            <label className={labelCls}>Region / Depto</label>
            <input {...register('region')} className={inputCls} placeholder="Antioquia" />
          </div>
          <div>
            <label className={labelCls}>Municipio</label>
            <input {...register('municipality')} className={inputCls} placeholder="Jardin" />
          </div>
        </div>

        {/* Row 5: Crop establishment (EUDR Colombia gap) */}
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className={labelCls}>Tipo de cultivo</label>
            <select {...register('crop_type')} className={inputCls}>
              <option value="">— Seleccionar —</option>
              <option value="cafe">Cafe</option>
              <option value="cacao">Cacao</option>
              <option value="palma">Palma de aceite</option>
              <option value="caucho">Caucho</option>
              <option value="soya">Soya</option>
              <option value="madera">Madera</option>
              <option value="ganado">Ganado bovino</option>
            </select>
          </div>
          <div>
            <label className={labelCls}>Fecha de establecimiento</label>
            <input type="date" {...register('establishment_date')} className={inputCls} />
          </div>
          <div>
            <label className={labelCls}>Fecha de renovacion/soca</label>
            <input type="date" {...register('renovation_date')} className={inputCls} />
          </div>
          <div>
            <label className={labelCls}>Tipo de renovacion</label>
            <select {...register('renovation_type')} className={inputCls}>
              <option value="">— Sin renovacion —</option>
              <option value="renovacion">Renovacion</option>
              <option value="soca">Soca (corte para rebrote)</option>
              <option value="resiembra">Resiembra</option>
            </select>
          </div>
        </div>

        {/* Row 6: Compliance checkboxes */}
        <div className="rounded-lg border border-border p-4 space-y-3">
          <p className="text-sm font-medium text-foreground">Declaraciones de cumplimiento</p>
          <label className="flex items-center gap-2 text-sm text-muted-foreground">
            <input type="checkbox" {...register('deforestation_free')} className="accent-emerald-600 h-4 w-4" />
            Libre de deforestacion
          </label>
          <label className="flex items-center gap-2 text-sm text-muted-foreground">
            <input type="checkbox" {...register('cutoff_date_compliant')} className="accent-emerald-600 h-4 w-4" />
            Cumple fecha de corte
          </label>
          <label className="flex items-center gap-2 text-sm text-muted-foreground">
            <input type="checkbox" {...register('legal_land_use')} className="accent-emerald-600 h-4 w-4" />
            Uso legal del suelo
          </label>
        </div>
      </form>
    </Dialog>
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
  const [showCreate, setShowCreate] = useState(false)
  const [selectedPlotId, setSelectedPlotId] = useState<string | undefined>()

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
        <Button variant="primary" size="sm" onClick={() => setShowCreate(true)}>
          <Plus className="h-4 w-4 mr-1.5" />
          Nueva Parcela
        </Button>
      </div>

      {/* Map */}
      {plots.length > 0 && (
        <PlotMap
          plots={plots}
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
        data={plots}
        rowKey={(row) => row.id}
        isLoading={isLoading}
        emptyMessage="No hay parcelas registradas. Crea una para comenzar."
      />

      {/* Create Modal */}
      {showCreate && <CreatePlotModal onClose={() => setShowCreate(false)} />}
    </div>
  )
}
