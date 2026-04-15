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

// ─── Colombia-specific constants ────────────────────────────────────────────

const COMMODITIES = [
  { value: 'cafe',  label: 'Cafe',             scientific: 'Coffea arabica L.',        commodity: 'coffee' as const },
  { value: 'cacao', label: 'Cacao',            scientific: 'Theobroma cacao L.',       commodity: 'cacao'  as const },
  { value: 'palma', label: 'Palma de aceite',  scientific: 'Elaeis guineensis Jacq.',  commodity: 'palm'   as const },
] as const

const TENURE_TYPES = [
  { value: 'owned', label: 'Propietario (titulo registrado)' },
  { value: 'leased', label: 'Arrendatario' },
  { value: 'sharecropped', label: 'Aparcero / mediania' },
  { value: 'baldio_adjudicado', label: 'Baldio adjudicado (ANT)' },
  { value: 'indigenous_collective', label: 'Resguardo indigena' },
  { value: 'afro_collective', label: 'Territorio colectivo afro (Ley 70)' },
  { value: 'concession', label: 'Concesion' },
  { value: 'occupation', label: 'Ocupacion sin titulo (posesion)' },
  { value: 'other', label: 'Otro' },
] as const

const CAPTURE_METHODS = [
  { value: 'handheld_gps', label: 'GPS de mano / celular' },
  { value: 'rtk_gps', label: 'GPS RTK (centimetrico)' },
  { value: 'drone', label: 'Dron / fotogrametria' },
  { value: 'manual_map', label: 'Trazado manual sobre imagen satelital' },
  { value: 'cadastral', label: 'Importado de catastro IGAC' },
  { value: 'survey', label: 'Levantamiento topografico' },
] as const

const PRODUCER_SCALES = [
  { value: 'smallholder', label: 'Pequeno productor (<4 ha)', note: 'EUDR acepta solo punto GPS' },
  { value: 'medium', label: 'Mediano (4–50 ha)', note: 'Requiere poligono si >4 ha' },
  { value: 'industrial', label: 'Industrial (>50 ha)', note: 'Requiere poligono + docs adicionales' },
] as const

const FRONTERA_OPTIONS = [
  { value: 'dentro_no_condicionada', label: 'Dentro — sin condicionamiento', color: 'text-emerald-700' },
  { value: 'dentro_condicionada', label: 'Dentro — condicionada (etnica, ambiental o riesgo)', color: 'text-amber-700' },
  { value: 'restriccion_deforestacion', label: 'Restriccion — acuerdo cero deforestacion', color: 'text-red-700' },
  { value: 'restriccion_legal', label: 'Restriccion — legal (POF, reserva forestal)', color: 'text-red-700' },
  { value: 'restriccion_tecnica', label: 'Restriccion — tecnica (area no agropecuaria)', color: 'text-red-700' },
  { value: 'fuera', label: 'Fuera de frontera agricola', color: 'text-red-700' },
] as const

const ID_TYPES = ['CC', 'CE', 'NIT', 'TI', 'NUIP', 'PASAPORTE'] as const

// ─── Schema ─────────────────────────────────────────────────────────────────

const plotSchema = z.object({
  // Identificacion
  plot_code: z.string().min(1, 'Nombre o codigo de la finca requerido'),
  organization_id: z.string().optional().nullable(),
  // Ubicacion
  region: z.string().min(1, 'Departamento requerido'),
  municipality: z.string().min(1, 'Municipio requerido'),
  vereda: z.string().optional().nullable(),
  frontera_agricola_status: z.string().optional().nullable(),
  // Geolocalizacion
  plot_area_ha: z.coerce.number().positive('Debe ser mayor a 0').optional().nullable(),
  geolocation_type: z.enum(['point', 'polygon']).default('point'),
  lat: z.coerce.number().min(-4.23, 'Fuera de Colombia').max(13.39, 'Fuera de Colombia').optional().nullable(),
  lng: z.coerce.number().min(-81.73, 'Fuera de Colombia').max(-66.85, 'Fuera de Colombia').optional().nullable(),
  capture_method: z.string().optional().nullable(),
  capture_device: z.string().optional().nullable(),
  capture_date: z.string().optional().nullable(),
  gps_accuracy_m: z.coerce.number().nonnegative().optional().nullable(),
  // Cultivo
  crop_type: z.string().min(1, 'Seleccione el cultivo'),
  commodity_type: z.enum(['coffee', 'cacao', 'palm', 'other']).optional().nullable(),
  scientific_name: z.string().optional().nullable(),
  establishment_date: z.string().optional().nullable(),
  last_harvest_date: z.string().optional().nullable(),
  renovation_date: z.string().optional().nullable(),
  renovation_type: z.string().optional().nullable(),
  producer_scale: z.string().min(1, 'Seleccione la escala'),
  // Productor
  producer_name: z.string().min(1, 'Nombre del productor requerido'),
  producer_id_type: z.string().min(1, 'Tipo de documento requerido'),
  producer_id_number: z.string().min(1, 'Numero de documento requerido'),
  // Titular (opcional si es el mismo)
  owner_name: z.string().optional().nullable(),
  owner_id_type: z.string().optional().nullable(),
  owner_id_number: z.string().optional().nullable(),
  // Tenencia
  tenure_type: z.string().optional().nullable(),
  cadastral_id: z.string().optional().nullable(),
  land_title_number: z.string().optional().nullable(),
  tenure_start_date: z.string().optional().nullable(),
  tenure_end_date: z.string().optional().nullable(),
  indigenous_territory_flag: z.boolean().default(false),
  // EUDR declaraciones obligatorias (Art. 3.a / Art. 2.7)
  deforestation_free: z.literal(true, {
    errorMap: () => ({ message: 'Debe declarar que la parcela esta libre de deforestacion (EUDR Art. 3.a)' }),
  }),
  degradation_free: z.literal(true, {
    errorMap: () => ({ message: 'Debe declarar que la parcela esta libre de degradacion forestal (EUDR Art. 2.7)' }),
  }),
})

type PlotForm = z.infer<typeof plotSchema>

// ─── Page ───────────────────────────────────────────────────────────────────

export default function CreatePlotPage() {
  const navigate = useNavigate()
  const create = useCreatePlot()
  const toast = useToast()
  const { data: orgsData } = useOrganizations()
  const orgs = orgsData?.items ?? []
  const [polygonData, setPolygonData] = useState<any>(null)

  const {
    register, handleSubmit, control, watch, setValue,
    formState: { errors, isSubmitting },
  } = useForm<PlotForm>({
    resolver: zodResolver(plotSchema),
    defaultValues: {
      plot_code: '', organization_id: null,
      region: '', municipality: '', vereda: null, frontera_agricola_status: null,
      plot_area_ha: null, geolocation_type: 'point', lat: null, lng: null,
      capture_method: null, capture_device: null, capture_date: null, gps_accuracy_m: null,
      crop_type: '', commodity_type: null, scientific_name: null, establishment_date: null, last_harvest_date: null,
      renovation_date: null, renovation_type: null, producer_scale: '',
      producer_name: '', producer_id_type: '', producer_id_number: '',
      owner_name: null, owner_id_type: null, owner_id_number: null,
      tenure_type: null, cadastral_id: null, land_title_number: null,
      tenure_start_date: null, tenure_end_date: null, indigenous_territory_flag: false,
      deforestation_free: false as any, degradation_free: false as any,
    },
  })

  async function onSubmit(values: PlotForm) {
    if (values.geolocation_type === 'polygon' && !polygonData) {
      toast.error('Dibuja el poligono en el mapa antes de guardar')
      return
    }
    try {
      let lat = values.lat
      let lng = values.lng
      if (values.geolocation_type === 'polygon' && polygonData?.coordinates?.[0]?.length) {
        const ring: number[][] = polygonData.coordinates[0]
        const pts = ring.length > 1 && ring[0][0] === ring[ring.length - 1][0] && ring[0][1] === ring[ring.length - 1][1]
          ? ring.slice(0, -1) : ring
        if (pts.length >= 3) {
          let area = 0, cx = 0, cy = 0
          for (let i = 0; i < pts.length; i++) {
            const [x0, y0] = pts[i], [x1, y1] = pts[(i + 1) % pts.length]
            const cross = x0 * y1 - x1 * y0; area += cross; cx += (x0 + x1) * cross; cy += (y0 + y1) * cross
          }
          area /= 2
          if (Math.abs(area) > 1e-9) { cx /= 6 * area; cy /= 6 * area; lng = cx; lat = cy }
          else { lng = pts.reduce((s, p) => s + p[0], 0) / pts.length; lat = pts.reduce((s, p) => s + p[1], 0) / pts.length }
        }
      }
      await create.mutateAsync({
        plot_code: values.plot_code,
        organization_id: values.organization_id || null,
        country_code: 'CO',
        region: values.region, municipality: values.municipality,
        vereda: values.vereda || null, frontera_agricola_status: values.frontera_agricola_status || null,
        plot_area_ha: values.plot_area_ha ?? null,
        geolocation_type: values.geolocation_type, lat: lat ?? null, lng: lng ?? null,
        geojson_data: polygonData,
        capture_method: values.capture_method || null, capture_device: values.capture_device || null,
        capture_date: values.capture_date || null, gps_accuracy_m: values.gps_accuracy_m ?? null,
        crop_type: values.crop_type,
        commodity_type: values.commodity_type || null,
        scientific_name: values.scientific_name || null,
        establishment_date: values.establishment_date || null, last_harvest_date: values.last_harvest_date || null,
        renovation_date: values.renovation_date || null, renovation_type: values.renovation_type || null,
        producer_scale: values.producer_scale || null,
        producer_name: values.producer_name, producer_id_type: values.producer_id_type,
        producer_id_number: values.producer_id_number,
        owner_name: values.owner_name || null, owner_id_type: values.owner_id_type || null,
        owner_id_number: values.owner_id_number || null,
        tenure_type: values.tenure_type || null, cadastral_id: values.cadastral_id || null,
        land_title_number: values.land_title_number || null,
        tenure_start_date: values.tenure_start_date || null, tenure_end_date: values.tenure_end_date || null,
        indigenous_territory_flag: values.indigenous_territory_flag,
        deforestation_free: values.deforestation_free,
        degradation_free: values.degradation_free,
        cutoff_date_compliant: true, legal_land_use: true,
        risk_level: 'standard',
      })
      toast.success('Parcela creada')
      navigate('/cumplimiento/parcelas')
    } catch (e: any) { toast.error(e.message ?? 'Error al crear parcela') }
  }

  const cls = 'w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-primary focus:ring-1 focus:ring-ring outline-none'
  const lbl = 'block text-sm font-medium text-foreground mb-1'
  const err = 'mt-0.5 text-xs text-red-500'
  const section = 'bg-card rounded-xl border border-border p-5 space-y-4'
  const hint = 'mt-0.5 text-[10px] text-muted-foreground'

  return (
    <div className="space-y-6 pb-24">
      {/* Header */}
      <div>
        <Link to="/cumplimiento/parcelas" className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-primary mb-3">
          <ArrowLeft className="h-3.5 w-3.5" /> Volver a Parcelas
        </Link>
        <div className="flex items-center gap-3">
          <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-primary/10">
            <MapPin className="h-5 w-5 text-primary" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-foreground">Registrar Parcela</h1>
            <p className="text-sm text-muted-foreground">
              Registro de predio para cumplimiento EUDR — Colombia
            </p>
          </div>
        </div>
      </div>

      <form onSubmit={handleSubmit(onSubmit)} className="space-y-5">

        {/* ── 1. Productor ── */}
        <div className={section}>
          <h2 className="text-sm font-bold text-foreground uppercase tracking-wide">Productor</h2>
          <p className="text-xs text-muted-foreground -mt-2">Datos del productor o cultivador que trabaja la parcela.</p>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className={lbl}>Nombre completo del productor *</label>
              <input {...register('producer_name')} className={cls} placeholder="ej. Juan Carlos Perez Lopez" />
              {errors.producer_name && <p className={err}>{errors.producer_name.message}</p>}
            </div>
            <div className="grid grid-cols-3 gap-2">
              <div>
                <label className={lbl}>Tipo doc *</label>
                <select {...register('producer_id_type')} className={cls}>
                  <option value="">—</option>
                  {ID_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
                </select>
                {errors.producer_id_type && <p className={err}>Requerido</p>}
              </div>
              <div className="col-span-2">
                <label className={lbl}>Numero *</label>
                <input {...register('producer_id_number')} className={cls} placeholder="1.234.567.890" />
                {errors.producer_id_number && <p className={err}>{errors.producer_id_number.message}</p>}
              </div>
            </div>
          </div>
          <div>
            <label className={lbl}>Cooperativa / asociacion / organizacion</label>
            <select {...register('organization_id')} className={cls}>
              <option value="">Productor independiente</option>
              {orgs.map(o => <option key={o.id} value={o.id}>{o.name}</option>)}
            </select>
            <p className={hint}>Si el productor pertenece a una cooperativa, seleccionela. Si no, deje "Productor independiente".</p>
          </div>
          <div>
            <label className={lbl}>Escala del productor *</label>
            <select {...register('producer_scale')} className={cls}>
              <option value="">— Seleccionar —</option>
              {PRODUCER_SCALES.map(s => <option key={s.value} value={s.value}>{s.label}</option>)}
            </select>
            {errors.producer_scale && <p className={err}>Requerido</p>}
            {watch('producer_scale') && (
              <p className={hint}>{PRODUCER_SCALES.find(s => s.value === watch('producer_scale'))?.note}</p>
            )}
          </div>
        </div>

        {/* ── 2. Finca ── */}
        <div className={section}>
          <h2 className="text-sm font-bold text-foreground uppercase tracking-wide">Finca / Parcela</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className={lbl}>Nombre de la finca *</label>
              <input {...register('plot_code')} className={cls} placeholder="ej. Finca La Esperanza" />
              {errors.plot_code && <p className={err}>{errors.plot_code.message}</p>}
            </div>
            <div>
              <label className={lbl}>Area total del lote (hectareas)</label>
              <input {...register('plot_area_ha')} type="number" step="0.01" className={cls} placeholder="ej. 3.5" />
              <p className={hint}>El 85% de los predios de cafe y cacao en Colombia son menores a 4 ha.</p>
            </div>
          </div>
        </div>

        {/* ── 3. Ubicacion ── */}
        <div className={section}>
          <h2 className="text-sm font-bold text-foreground uppercase tracking-wide">Ubicacion</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label className={lbl}>Departamento *</label>
              <input {...register('region')} className={cls} placeholder="ej. Huila" />
              {errors.region && <p className={err}>{errors.region.message}</p>}
            </div>
            <div>
              <label className={lbl}>Municipio *</label>
              <input {...register('municipality')} className={cls} placeholder="ej. Planadas" />
              {errors.municipality && <p className={err}>{errors.municipality.message}</p>}
            </div>
            <div>
              <label className={lbl}>Vereda</label>
              <input {...register('vereda')} className={cls} placeholder="ej. La España" />
            </div>
          </div>
          <div>
            <label className={lbl}>Frontera agricola (UPRA / CIPRA)</label>
            <select {...register('frontera_agricola_status')} className={cls}>
              <option value="">— Sin verificar —</option>
              {FRONTERA_OPTIONS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
            </select>
            <p className={hint}>Consulte en cipra.upra.gov.co. Es la respuesta oficial de Colombia a derechos de uso del suelo (EUDR Art. 9).</p>
          </div>
          {watch('frontera_agricola_status') === 'fuera' && (
            <div className="rounded-md bg-red-50 border border-red-200 px-3 py-2 text-xs text-red-800">
              Predio fuera de frontera agricola. La produccion agropecuaria puede no cumplir con derechos de uso del suelo. Consulte con la CAR de su region.
            </div>
          )}
          {watch('frontera_agricola_status')?.startsWith('restriccion') && (
            <div className="rounded-md bg-amber-50 border border-amber-200 px-3 py-2 text-xs text-amber-800">
              Predio con restriccion. Puede requerir autorizacion de la autoridad ambiental o revision del POT/EOT municipal. Adjunte certificado de uso del suelo en documentos.
            </div>
          )}
        </div>

        {/* ── 4. Geolocalizacion ── */}
        <div className={section}>
          <h2 className="text-sm font-bold text-foreground uppercase tracking-wide">Geolocalizacion</h2>
          <p className="text-xs text-muted-foreground -mt-2">
            EUDR Art. 2(28): predios menores a 4 ha solo necesitan un punto (latitud/longitud). Predios mayores a 4 ha requieren poligono.
          </p>
          <div>
            <label className={lbl}>Tipo de geolocalizacion</label>
            <Controller name="geolocation_type" control={control} render={({ field }) => (
              <div className="flex gap-4 pt-1">
                <label className="flex items-center gap-1.5 text-sm text-foreground cursor-pointer">
                  <input type="radio" value="point" checked={field.value === 'point'} onChange={() => field.onChange('point')} className="accent-primary" />
                  Punto GPS
                </label>
                <label className="flex items-center gap-1.5 text-sm text-foreground cursor-pointer">
                  <input type="radio" value="polygon" checked={field.value === 'polygon'} onChange={() => field.onChange('polygon')} className="accent-primary" />
                  Poligono
                </label>
              </div>
            )} />
          </div>

          {watch('geolocation_type') === 'point' && (
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className={lbl}>Latitud</label>
                <input {...register('lat')} type="number" step="0.000001" className={cls} placeholder="ej. 2.927" />
              </div>
              <div>
                <label className={lbl}>Longitud</label>
                <input {...register('lng')} type="number" step="0.000001" className={cls} placeholder="ej. -75.989" />
              </div>
              <p className="col-span-2 text-[10px] text-muted-foreground">
                Puede tomar las coordenadas con el GPS de su celular. Encienda la ubicacion, tome una foto y copie latitud/longitud.
              </p>
            </div>
          )}

          {watch('geolocation_type') === 'polygon' && (
            <div>
              <p className="text-xs text-muted-foreground mb-2">
                Dibuje el poligono en el mapa: click para agregar vertices (minimo 3), luego "Guardar poligono".
              </p>
              <PlotPolygonEditor
                initialGeojson={polygonData}
                declaredAreaHa={watch('plot_area_ha') ?? null}
                height="450px"
                onSave={(geojson, calculatedAreaHa) => {
                  setPolygonData(geojson)
                  if (calculatedAreaHa) {
                    const declared = watch('plot_area_ha')
                    if (!declared || Math.abs(Number(declared) - calculatedAreaHa) / calculatedAreaHa > 0.5) {
                      setValue('plot_area_ha', Math.round(calculatedAreaHa * 100) / 100)
                      toast.success(`Poligono listo. Area: ${calculatedAreaHa.toFixed(2)} ha`)
                    } else { toast.success(`Poligono listo (${calculatedAreaHa.toFixed(2)} ha)`) }
                  } else { toast.success('Poligono listo') }
                }}
              />
              {polygonData && (
                <div className="mt-2 inline-flex items-center gap-1.5 rounded-full bg-emerald-50 px-2.5 py-0.5 text-xs font-semibold text-emerald-700">
                  <Check className="h-3 w-3" /> Poligono dibujado
                </div>
              )}
            </div>
          )}

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 pt-2 border-t border-border">
            <div>
              <label className={lbl}>Metodo de captura</label>
              <select {...register('capture_method')} className={cls}>
                <option value="">— Seleccionar —</option>
                {CAPTURE_METHODS.map(m => <option key={m.value} value={m.value}>{m.label}</option>)}
              </select>
            </div>
            <div>
              <label className={lbl}>Dispositivo</label>
              <input {...register('capture_device')} className={cls} placeholder="ej. Samsung A14 / Garmin eTrex" />
            </div>
            <div>
              <label className={lbl}>Fecha de captura</label>
              <input type="date" {...register('capture_date')} className={cls} />
            </div>
          </div>
          <div className="w-1/3">
            <label className={lbl}>Exactitud GPS (metros)</label>
            <input {...register('gps_accuracy_m')} type="number" step="0.1" min="0" className={cls} placeholder="ej. 5" />
            <p className={hint}>Celular tipico: 3–10 m. GPS profesional: 0.01–0.05 m.</p>
          </div>
        </div>

        {/* ── 5. Cultivo ── */}
        <div className={section}>
          <h2 className="text-sm font-bold text-foreground uppercase tracking-wide">Cultivo</h2>
          <p className="text-xs text-muted-foreground -mt-2">
            Colombia exporta a la UE principalmente cafe, cacao y palma de aceite. Solo estos 3 commodities requieren cumplimiento EUDR.
          </p>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className={lbl}>Cultivo principal *</label>
              <select {...register('crop_type', {
                onChange: (e) => {
                  const c = COMMODITIES.find(c => c.value === e.target.value)
                  if (c) {
                    setValue('scientific_name', c.scientific)
                    setValue('commodity_type', c.commodity)
                  }
                },
              })} className={cls}>
                <option value="">— Seleccionar —</option>
                {COMMODITIES.map(c => <option key={c.value} value={c.value}>{c.label}</option>)}
              </select>
              {errors.crop_type && <p className={err}>{errors.crop_type.message}</p>}
            </div>
            <div>
              <label className={lbl}>Nombre cientifico</label>
              <input {...register('scientific_name')} className={`${cls} bg-muted/30`} readOnly />
              <p className={hint}>Se completa automaticamente. EUDR Art. 9(1)(a).</p>
            </div>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label className={lbl}>Fecha de siembra</label>
              <input type="date" {...register('establishment_date')} className={cls} />
            </div>
            <div>
              <label className={lbl}>Ultima cosecha</label>
              <input type="date" {...register('last_harvest_date')} className={cls} />
              <p className={hint}>EUDR Art. 9(1)(d) — periodo de produccion.</p>
            </div>
            <div>
              <label className={lbl}>Renovacion / soca</label>
              <input type="date" {...register('renovation_date')} className={cls} />
            </div>
          </div>
        </div>

        {/* ── 6. Tenencia ── */}
        <div className={section}>
          <h2 className="text-sm font-bold text-foreground uppercase tracking-wide">Tenencia del predio</h2>
          <p className="text-xs text-muted-foreground -mt-2">
            EUDR Art. 10(h) — derecho legal de uso del suelo. Adjunte el certificado de tradicion y libertad en la seccion de documentos.
          </p>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className={lbl}>Tipo de tenencia</label>
              <select {...register('tenure_type')} className={cls}>
                <option value="">— Seleccionar —</option>
                {TENURE_TYPES.map(t => <option key={t.value} value={t.value}>{t.label}</option>)}
              </select>
            </div>
            <div>
              <label className={lbl}>Cedula catastral (IGAC)</label>
              <input {...register('cadastral_id')} className={cls} placeholder="ej. 000-00000-00-000" />
              <p className={hint}>Numero de identificacion predial del IGAC.</p>
            </div>
          </div>
          <div>
            <label className={lbl}>Folio de matricula inmobiliaria (SNR)</label>
            <input {...register('land_title_number')} className={cls} placeholder="ej. 350-12345" />
            <p className={hint}>Certificado de tradicion y libertad de la Superintendencia de Notariado y Registro.</p>
          </div>

          {/* Titular legal (si difiere) */}
          <div className="border-t border-border pt-4 space-y-3">
            <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">
              Titular legal del predio (si es diferente al productor)
            </p>
            <input {...register('owner_name')} className={cls} placeholder="Nombre del propietario registrado" />
            <div className="grid grid-cols-3 gap-2">
              <select {...register('owner_id_type')} className={cls}>
                <option value="">—</option>
                {ID_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
              </select>
              <input {...register('owner_id_number')} className={`${cls} col-span-2`} placeholder="Numero de documento" />
            </div>
          </div>

          <label className="flex items-start gap-2 text-sm cursor-pointer pt-3 border-t border-border">
            <input type="checkbox" {...register('indigenous_territory_flag')} className="accent-amber-600 h-4 w-4 mt-0.5" />
            <span className="text-foreground">
              Resguardo indigena o territorio colectivo afro
              <span className="block text-[11px] text-muted-foreground mt-0.5">
                Requiere consulta previa (FPIC). La Constitucion reconoce autonomia territorial de resguardos y consejos comunitarios (Ley 70/93).
              </span>
            </span>
          </label>
        </div>

        {/* ── Declaraciones EUDR (obligatorias) ─────────────────────── */}
        <div className={section}>
          <div>
            <h2 className="text-base font-semibold text-foreground">Declaraciones EUDR</h2>
            <p className="text-xs text-muted-foreground mt-0.5">
              Ambas declaraciones son obligatorias para enviar el DDS a TRACES NT (Reglamento UE 2023/1115).
            </p>
          </div>

          <label className="flex items-start gap-2 text-sm cursor-pointer">
            <input
              type="checkbox"
              {...register('deforestation_free')}
              className="accent-emerald-600 h-4 w-4 mt-0.5"
            />
            <span className="text-foreground">
              Libre de deforestacion (Art. 3.a)
              <span className="block text-[11px] text-muted-foreground mt-0.5">
                Declaro que esta parcela no fue deforestada despues del 31 de diciembre de 2020.
              </span>
            </span>
          </label>
          {errors.deforestation_free && (
            <p className={err}>{errors.deforestation_free.message as string}</p>
          )}

          <label className="flex items-start gap-2 text-sm cursor-pointer">
            <input
              type="checkbox"
              {...register('degradation_free')}
              className="accent-emerald-600 h-4 w-4 mt-0.5"
            />
            <span className="text-foreground">
              Libre de degradacion forestal (Art. 2.7)
              <span className="block text-[11px] text-muted-foreground mt-0.5">
                Declaro que no hubo degradacion forestal en la parcela despues del 31 de diciembre de 2020.
              </span>
            </span>
          </label>
          {errors.degradation_free && (
            <p className={err}>{errors.degradation_free.message as string}</p>
          )}
        </div>
      </form>

      {/* Sticky footer */}
      <div className="fixed bottom-0 left-0 right-0 z-30 border-t border-border bg-card/95 backdrop-blur supports-[backdrop-filter]:bg-card/80">
        <div className="container max-w-6xl mx-auto px-6 py-3 flex items-center justify-end gap-3">
          <Button variant="secondary" onClick={() => navigate('/cumplimiento/parcelas')}>Cancelar</Button>
          <Button variant="primary" loading={create.isPending || isSubmitting} onClick={handleSubmit(onSubmit)}>
            Crear parcela
          </Button>
        </div>
      </div>
    </div>
  )
}
