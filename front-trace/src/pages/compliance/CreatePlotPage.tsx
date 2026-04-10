import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { ArrowLeft, MapPin, Check } from 'lucide-react'
import { useForm, Controller } from 'react-hook-form'
import { z } from 'zod'
import { zodResolver } from '@hookform/resolvers/zod'
import { useCreatePlot } from '@/hooks/useCompliance'
import { useOrganizations } from '@/hooks/useTaxonomy'
import { useToast } from '@/store/toast'
import { Button } from '@/components/ui/button'
import { PlotPolygonEditor } from '@/components/compliance/PlotPolygonEditor'

// ─── Schema ──────────────────────────────────────────────────────────────────

const TENURE_TYPES = [
  'owned', 'leased', 'sharecropped', 'concession',
  'indigenous_collective', 'afro_collective', 'baldio_adjudicado',
  'occupation', 'other',
] as const

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
  // EUDR Art. 8.2.f — Tenencia y propiedad
  owner_name: z.string().optional().nullable(),
  owner_id_type: z.string().optional().nullable(),
  owner_id_number: z.string().optional().nullable(),
  producer_name: z.string().optional().nullable(),
  producer_id_type: z.string().optional().nullable(),
  producer_id_number: z.string().optional().nullable(),
  cadastral_id: z.string().optional().nullable(),
  tenure_type: z.enum(TENURE_TYPES).optional().nullable(),
  tenure_start_date: z.string().optional().nullable(),
  tenure_end_date: z.string().optional().nullable(),
  indigenous_territory_flag: z.boolean().default(false),
  land_title_number: z.string().optional().nullable(),
})

type PlotFormValues = z.infer<typeof plotSchema>

// ─── Page ────────────────────────────────────────────────────────────────────

export default function CreatePlotPage() {
  const navigate = useNavigate()
  const create = useCreatePlot()
  const toast = useToast()
  const { data: orgsData } = useOrganizations()
  const orgs = orgsData?.items ?? []
  const [polygonData, setPolygonData] = useState<any>(null)

  const {
    register,
    handleSubmit,
    control,
    watch,
    setValue,
    formState: { errors, isSubmitting },
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
      owner_name: null,
      owner_id_type: null,
      owner_id_number: null,
      producer_name: null,
      producer_id_type: null,
      producer_id_number: null,
      cadastral_id: null,
      tenure_type: null,
      tenure_start_date: null,
      tenure_end_date: null,
      indigenous_territory_flag: false,
      land_title_number: null,
    },
  })

  async function onSubmit(values: PlotFormValues) {
    if (values.geolocation_type === 'polygon' && !polygonData) {
      toast.error('Dibuja el poligono en el mapa antes de guardar')
      return
    }
    try {
      // Centroide ponderado por area (Shoelace) para que el punto caiga dentro del poligono
      let lat = values.lat
      let lng = values.lng
      if (values.geolocation_type === 'polygon' && polygonData?.coordinates?.[0]?.length) {
        const ring: number[][] = polygonData.coordinates[0]
        const pts = ring.length > 1 && ring[0][0] === ring[ring.length - 1][0] && ring[0][1] === ring[ring.length - 1][1]
          ? ring.slice(0, -1)
          : ring
        if (pts.length >= 3) {
          let area = 0
          let cx = 0
          let cy = 0
          for (let i = 0; i < pts.length; i++) {
            const [x0, y0] = pts[i]
            const [x1, y1] = pts[(i + 1) % pts.length]
            const cross = x0 * y1 - x1 * y0
            area += cross
            cx += (x0 + x1) * cross
            cy += (y0 + y1) * cross
          }
          area /= 2
          if (Math.abs(area) > 1e-9) {
            cx /= 6 * area
            cy /= 6 * area
            lng = cx
            lat = cy
          } else {
            lng = pts.reduce((s, p) => s + p[0], 0) / pts.length
            lat = pts.reduce((s, p) => s + p[1], 0) / pts.length
          }
        }
      }
      await create.mutateAsync({
        plot_code: values.plot_code,
        organization_id: values.organization_id || null,
        plot_area_ha: values.plot_area_ha ?? null,
        geolocation_type: values.geolocation_type,
        lat: lat ?? null,
        lng: lng ?? null,
        geojson_data: polygonData,
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
        owner_name: values.owner_name || null,
        owner_id_type: values.owner_id_type || null,
        owner_id_number: values.owner_id_number || null,
        producer_name: values.producer_name || null,
        producer_id_type: values.producer_id_type || null,
        producer_id_number: values.producer_id_number || null,
        cadastral_id: values.cadastral_id || null,
        tenure_type: values.tenure_type || null,
        tenure_start_date: values.tenure_start_date || null,
        tenure_end_date: values.tenure_end_date || null,
        indigenous_territory_flag: values.indigenous_territory_flag,
        land_title_number: values.land_title_number || null,
      })
      toast.success('Parcela creada')
      navigate('/cumplimiento/parcelas')
    } catch (e: any) {
      toast.error(e.message ?? 'Error al crear parcela')
    }
  }

  const inputCls =
    'w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-primary focus:ring-1 focus:ring-ring outline-none'
  const labelCls = 'block text-sm font-medium text-foreground mb-1'
  const errCls = 'mt-0.5 text-xs text-red-500'
  const sectionCls = 'bg-card rounded-xl border border-border p-5 space-y-4'

  return (
    <div className="space-y-6 pb-24">
      {/* Header */}
      <div>
        <Link
          to="/cumplimiento/parcelas"
          className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-primary mb-3"
        >
          <ArrowLeft className="h-3.5 w-3.5" /> Volver a Parcelas
        </Link>
        <div className="flex items-center gap-3">
          <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-amber-50">
            <MapPin className="h-5 w-5 text-amber-600" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-foreground">Nueva Parcela</h1>
            <p className="text-sm text-muted-foreground">
              Registra un predio de produccion para trazabilidad EUDR
            </p>
          </div>
        </div>
      </div>

      <form onSubmit={handleSubmit(onSubmit)} className="space-y-5">
        {/* Datos básicos */}
        <div className={sectionCls}>
          <h2 className="text-sm font-bold text-foreground uppercase tracking-wide">
            Datos basicos
          </h2>
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

          <div className="grid grid-cols-3 gap-4">
            <div>
              <label className={labelCls}>Area (ha)</label>
              <input
                {...register('plot_area_ha')}
                type="number"
                step="0.01"
                className={inputCls}
                placeholder="12.5"
              />
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
        </div>

        {/* Geolocalización */}
        <div className={sectionCls}>
          <h2 className="text-sm font-bold text-foreground uppercase tracking-wide">
            Geolocalizacion
          </h2>

          {watch('geolocation_type') === 'point' && (
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className={labelCls}>Latitud</label>
                <input
                  {...register('lat')}
                  type="number"
                  step="0.000001"
                  className={inputCls}
                  placeholder="4.710989"
                />
              </div>
              <div>
                <label className={labelCls}>Longitud</label>
                <input
                  {...register('lng')}
                  type="number"
                  step="0.000001"
                  className={inputCls}
                  placeholder="-74.072092"
                />
              </div>
            </div>
          )}

          {watch('geolocation_type') === 'polygon' && (
            <div>
              <p className="text-xs text-muted-foreground mb-2">
                Click en "Dibujar poligono" → haz clic en el mapa para agregar vertices (minimo 3) → "Guardar poligono"
              </p>
              <PlotPolygonEditor
                initialGeojson={polygonData}
                declaredAreaHa={watch('plot_area_ha') ?? null}
                height="450px"
                onSave={(geojson, calculatedAreaHa) => {
                  setPolygonData(geojson)
                  // Auto-fill area si esta vacia o si difiere mucho del declarado
                  if (calculatedAreaHa) {
                    const declared = watch('plot_area_ha')
                    if (!declared || Math.abs(Number(declared) - calculatedAreaHa) / calculatedAreaHa > 0.5) {
                      setValue('plot_area_ha', Math.round(calculatedAreaHa * 100) / 100)
                      toast.success(`Poligono listo. Area auto-completada: ${calculatedAreaHa.toFixed(2)} ha`)
                    } else {
                      toast.success(`Poligono listo (${calculatedAreaHa.toFixed(2)} ha)`)
                    }
                  } else {
                    toast.success('Poligono listo')
                  }
                }}
              />
              {polygonData && (
                <div className="mt-2 inline-flex items-center gap-1.5 rounded-full bg-emerald-50 px-2.5 py-0.5 text-xs font-semibold text-emerald-700">
                  <Check className="h-3 w-3" /> Poligono dibujado
                </div>
              )}
            </div>
          )}
        </div>

        {/* Ubicación */}
        <div className={sectionCls}>
          <h2 className="text-sm font-bold text-foreground uppercase tracking-wide">
            Ubicacion administrativa
          </h2>
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
        </div>

        {/* Cultivo */}
        <div className={sectionCls}>
          <h2 className="text-sm font-bold text-foreground uppercase tracking-wide">
            Cultivo
          </h2>
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
              <label className={labelCls}>Fecha de renovacion / soca</label>
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
        </div>

        {/* Tenencia y Propiedad — EUDR Art. 8.2.f */}
        <div className={sectionCls}>
          <div>
            <h2 className="text-sm font-bold text-foreground uppercase tracking-wide">
              Tenencia y Propiedad
            </h2>
            <p className="text-[11px] text-muted-foreground mt-0.5">
              EUDR Art. 8.2.f exige evidencia del derecho legal de uso de la zona.
            </p>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className={labelCls}>Tipo de tenencia</label>
              <select {...register('tenure_type')} className={inputCls}>
                <option value="">— Seleccionar —</option>
                <option value="owned">Propietario</option>
                <option value="leased">Arrendatario</option>
                <option value="sharecropped">Aparcero</option>
                <option value="concession">Concesion</option>
                <option value="indigenous_collective">Territorio indigena colectivo</option>
                <option value="afro_collective">Territorio afrocolectivo</option>
                <option value="baldio_adjudicado">Baldio adjudicado (ANT)</option>
                <option value="occupation">Ocupacion sin titulo</option>
                <option value="other">Otro</option>
              </select>
            </div>
            <div>
              <label className={labelCls}>Identificador catastral</label>
              <input
                {...register('cadastral_id')}
                className={inputCls}
                placeholder="Folio matricula SNR / catastro IGAC"
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className={labelCls}>Vigencia desde</label>
              <input type="date" {...register('tenure_start_date')} className={inputCls} />
            </div>
            <div>
              <label className={labelCls}>Vigencia hasta</label>
              <input type="date" {...register('tenure_end_date')} className={inputCls} />
            </div>
          </div>

          <div className="border-t border-border pt-4 space-y-3">
            <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">
              Productor (quien cultiva)
            </p>
            <input
              {...register('producer_name')}
              className={inputCls}
              placeholder="Nombre del productor"
            />
            <div className="grid grid-cols-3 gap-2">
              <select {...register('producer_id_type')} className={inputCls}>
                <option value="">— Tipo —</option>
                <option value="CC">CC</option>
                <option value="CE">CE</option>
                <option value="NIT">NIT</option>
                <option value="RUT">RUT</option>
                <option value="PASAPORTE">Pasaporte</option>
                <option value="OTRO">Otro</option>
              </select>
              <input
                {...register('producer_id_number')}
                className={`${inputCls} col-span-2`}
                placeholder="Numero de documento"
              />
            </div>
          </div>

          <div className="border-t border-border pt-4 space-y-3">
            <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">
              Titular legal (si difiere del productor)
            </p>
            <input
              {...register('owner_name')}
              className={inputCls}
              placeholder="Nombre del titular"
            />
            <div className="grid grid-cols-3 gap-2">
              <select {...register('owner_id_type')} className={inputCls}>
                <option value="">— Tipo —</option>
                <option value="CC">CC</option>
                <option value="CE">CE</option>
                <option value="NIT">NIT</option>
                <option value="RUT">RUT</option>
                <option value="PASAPORTE">Pasaporte</option>
                <option value="OTRO">Otro</option>
              </select>
              <input
                {...register('owner_id_number')}
                className={`${inputCls} col-span-2`}
                placeholder="Numero de documento"
              />
            </div>
            <input
              {...register('land_title_number')}
              className={inputCls}
              placeholder="Numero de titulo / folio matricula"
            />
          </div>

          <label className="flex items-start gap-2 text-sm cursor-pointer pt-3 border-t border-border">
            <input
              type="checkbox"
              {...register('indigenous_territory_flag')}
              className="accent-amber-600 h-4 w-4 mt-0.5"
            />
            <span className="text-foreground">
              Territorio indigena o colectivo afro
              <span className="block text-[11px] text-muted-foreground mt-0.5">
                Activa due diligence reforzado bajo Art. 10 EUDR.
              </span>
            </span>
          </label>
        </div>

        {/* Declaraciones de cumplimiento */}
        <div className={sectionCls}>
          <h2 className="text-sm font-bold text-foreground uppercase tracking-wide">
            Declaraciones de cumplimiento
          </h2>
          <label className="flex items-center gap-2 text-sm text-foreground">
            <input type="checkbox" {...register('deforestation_free')} className="accent-emerald-600 h-4 w-4" />
            Libre de deforestacion
          </label>
          <label className="flex items-center gap-2 text-sm text-foreground">
            <input type="checkbox" {...register('cutoff_date_compliant')} className="accent-emerald-600 h-4 w-4" />
            Cumple fecha de corte
          </label>
          <label className="flex items-center gap-2 text-sm text-foreground">
            <input type="checkbox" {...register('legal_land_use')} className="accent-emerald-600 h-4 w-4" />
            Uso legal del suelo
          </label>
        </div>
      </form>

      {/* Sticky footer con acciones */}
      <div className="fixed bottom-0 left-0 right-0 z-30 border-t border-border bg-card/95 backdrop-blur supports-[backdrop-filter]:bg-card/80">
        <div className="container max-w-6xl mx-auto px-6 py-3 flex items-center justify-end gap-3">
          <Button variant="secondary" onClick={() => navigate('/cumplimiento/parcelas')}>
            Cancelar
          </Button>
          <Button
            variant="primary"
            loading={create.isPending || isSubmitting}
            onClick={handleSubmit(onSubmit)}
          >
            Crear parcela
          </Button>
        </div>
      </div>
    </div>
  )
}
