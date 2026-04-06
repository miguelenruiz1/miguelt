import { useState, useEffect, useRef } from 'react'
import { useParams, Link } from 'react-router-dom'
import { ArrowLeft, MapPin, Satellite, Check, X, Loader2, Calendar, Sprout, Shield, AlertTriangle, FolderOpen } from 'lucide-react'
import { usePlot, useUpdatePlot, useScreenDeforestation, usePlotDocuments, useAttachPlotDocument, useDetachPlotDocument } from '@/hooks/useCompliance'
import { SinglePlotMap } from '@/components/compliance/PlotMap'
import { PlotPolygonEditor } from '@/components/compliance/PlotPolygonEditor'
import DocumentUploader from '@/components/compliance/DocumentUploader'
import { Badge } from '@/components/ui/badge'
import { useToast } from '@/store/toast'
import { mediaApi, mediaFileUrl } from '@/lib/media-api'
import MediaPickerModal from '@/components/compliance/MediaPickerModal'
import type { CompliancePlot } from '@/types/compliance'

const riskLabel: Record<string, string> = { low: 'Bajo', standard: 'Estandar', high: 'Alto' }
const riskColor: Record<string, string> = { low: 'bg-green-100 text-green-700', standard: 'bg-amber-100 text-amber-700', high: 'bg-red-100 text-red-700' }

function ComplianceFlag({ label, value }: { label: string; value: boolean }) {
  return (
    <div className={`flex items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium ${value ? 'bg-emerald-50 text-emerald-700' : 'bg-red-50 text-red-700'}`}>
      {value ? <Check className="h-4 w-4" /> : <X className="h-4 w-4" />}
      {label}
    </div>
  )
}

function InfoField({ label, value }: { label: string; value: string | null | undefined }) {
  return (
    <div>
      <dt className="text-xs font-medium text-muted-foreground uppercase tracking-wide">{label}</dt>
      <dd className="mt-0.5 text-sm text-foreground font-medium">{value || '—'}</dd>
    </div>
  )
}

export function PlotDetailPage() {
  const { plotId } = useParams<{ plotId: string }>()
  const { data: plot, isLoading } = usePlot(plotId!)
  const updatePlot = useUpdatePlot(plotId!)
  const screen = useScreenDeforestation()
  const { data: plotDocs = [], isLoading: docsLoading } = usePlotDocuments(plotId!)
  const attachDoc = useAttachPlotDocument(plotId!)
  const detachDoc = useDetachPlotDocument(plotId!)
  const toast = useToast()
  const [geojsonData, setGeojsonData] = useState<any>(null)
  const [showGeojsonPicker, setShowGeojsonPicker] = useState(false)
  const [linkingGeojson, setLinkingGeojson] = useState(false)
  const [uploadingGeojson, setUploadingGeojson] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)

  // Load existing geojson_data from plot when available
  useEffect(() => {
    if (plot && (plot as any).geojson_data && !geojsonData) {
      setGeojsonData((plot as any).geojson_data)
    }
  }, [plot])

  async function handleGeojsonFileUpload(file: File) {
    setUploadingGeojson(true)
    try {
      const text = await file.text()
      const parsed = JSON.parse(text)
      // Validate it's GeoJSON
      const validTypes = ['Polygon', 'MultiPolygon', 'Feature', 'FeatureCollection']
      if (!parsed.type || !validTypes.includes(parsed.type)) {
        throw new Error(`Tipo GeoJSON inválido. Debe ser uno de: ${validTypes.join(', ')}`)
      }
      // Save to backend
      await updatePlot.mutateAsync({ geojson_data: parsed } as any)
      setGeojsonData(parsed)
      toast.success('Polígono cargado correctamente')
    } catch (e: any) {
      toast.error(e.message || 'Error al procesar el archivo GeoJSON')
    } finally {
      setUploadingGeojson(false)
      if (fileInputRef.current) fileInputRef.current.value = ''
    }
  }

  if (isLoading) return <div className="flex justify-center py-20 text-muted-foreground">Cargando...</div>
  if (!plot) return <div className="flex justify-center py-20 text-muted-foreground">Parcela no encontrada</div>

  const gfwScreening = (plot as any).metadata_?.gfw_screening

  async function handleScreen() {
    try {
      const result = await screen.mutateAsync(plotId!)
      if (result.deforestation_free === true) {
        toast.success(`Libre de deforestacion (0 alertas)`)
      } else if (result.deforestation_free === false) {
        toast.error(`${result.alerts_count} alertas de deforestacion detectadas`)
      } else {
        toast.error(result.error || 'No se pudo verificar')
      }
    } catch (e: any) {
      toast.error(e.message ?? 'Error')
    }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <Link to="/cumplimiento/parcelas" className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-primary mb-3">
          <ArrowLeft className="h-3.5 w-3.5" /> Volver a Parcelas
        </Link>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-amber-50">
              <MapPin className="h-5 w-5 text-amber-600" />
            </div>
            <div>
              <h1 className="text-xl font-bold text-foreground">{plot.plot_code}</h1>
              <p className="text-sm text-muted-foreground">
                {[plot.municipality, plot.region, plot.country_code].filter(Boolean).join(', ')}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <input
              ref={fileInputRef}
              type="file"
              accept=".geojson,.json,application/json,application/geo+json"
              className="hidden"
              onChange={e => {
                const f = e.target.files?.[0]
                if (f) handleGeojsonFileUpload(f)
              }}
            />
            <button
              onClick={() => fileInputRef.current?.click()}
              disabled={uploadingGeojson}
              className="inline-flex items-center gap-2 rounded-lg border border-border bg-card px-4 py-2 text-sm font-semibold text-muted-foreground hover:bg-muted disabled:opacity-50 transition-colors"
              title="Subir polígono GeoJSON"
            >
              {uploadingGeojson ? <Loader2 className="h-4 w-4 animate-spin" /> : <FolderOpen className="h-4 w-4" />}
              {geojsonData ? 'Cambiar polígono' : 'Subir polígono'}
            </button>
            <button
              onClick={handleScreen}
              disabled={screen.isPending}
              className="inline-flex items-center gap-2 rounded-lg bg-emerald-600 px-4 py-2 text-sm font-semibold text-white hover:bg-emerald-700 disabled:opacity-50 transition-colors"
            >
              {screen.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Satellite className="h-4 w-4" />}
              Verificar Deforestacion (GFW)
            </button>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left: Map */}
        <div className="lg:col-span-2 space-y-4">
          <PlotPolygonEditor
            initialLat={plot.lat ? Number(plot.lat) : null}
            initialLng={plot.lng ? Number(plot.lng) : null}
            initialGeojson={geojsonData}
            height="400px"
            saving={updatePlot.isPending}
            onSave={async (geojson) => {
              try {
                await updatePlot.mutateAsync({ geojson_data: geojson } as any)
                setGeojsonData(geojson)
                toast.success('Polígono guardado')
              } catch (e: any) {
                toast.error(e.message || 'Error al guardar polígono')
              }
            }}
          />

          {/* Compliance flags */}
          <div className="grid grid-cols-3 gap-3">
            <ComplianceFlag label="Libre de deforestacion" value={plot.deforestation_free} />
            <ComplianceFlag label="Cumple fecha de corte" value={plot.cutoff_date_compliant} />
            <ComplianceFlag label="Uso legal del suelo" value={plot.legal_land_use} />
          </div>

          {/* GFW Screening Results */}
          {gfwScreening && (
            <div className={`rounded-xl border p-4 ${gfwScreening.alerts_count === 0 ? 'border-emerald-200 bg-emerald-50' : 'border-red-200 bg-red-50'}`}>
              <div className="flex items-center gap-2 mb-2">
                <Satellite className="h-4 w-4" />
                <h3 className="text-sm font-bold">Resultado Global Forest Watch</h3>
              </div>
              <div className="grid grid-cols-4 gap-4 text-sm">
                <div>
                  <span className="text-xs text-muted-foreground">Alertas</span>
                  <p className="font-bold text-lg">{gfwScreening.alerts_count}</p>
                </div>
                <div>
                  <span className="text-xs text-muted-foreground">Alta confianza</span>
                  <p className="font-bold text-lg">{gfwScreening.high_confidence}</p>
                </div>
                <div>
                  <span className="text-xs text-muted-foreground">Fuente</span>
                  <p className="font-medium">{gfwScreening.source}</p>
                </div>
                <div>
                  <span className="text-xs text-muted-foreground">Fecha corte</span>
                  <p className="font-medium">{gfwScreening.cutoff_date}</p>
                </div>
              </div>
              <p className="text-xs text-muted-foreground mt-2">Verificado: {new Date(gfwScreening.checked_at).toLocaleString('es-CO')}</p>
            </div>
          )}

          {!gfwScreening && (
            <div className="rounded-xl border border-amber-200 bg-amber-50 p-4 flex items-start gap-3">
              <AlertTriangle className="h-5 w-5 text-amber-500 mt-0.5 shrink-0" />
              <div>
                <p className="text-sm font-medium text-amber-800">Sin verificacion satelital</p>
                <p className="text-xs text-amber-600 mt-0.5">
                  Haz click en "Verificar Deforestacion (GFW)" para consultar automaticamente
                  las alertas de deforestacion de Global Forest Watch para esta parcela.
                </p>
              </div>
            </div>
          )}
        </div>

        {/* Right: Details */}
        <div className="space-y-4">
          {/* Info card */}
          <div className="bg-card rounded-xl border border-border  p-5 space-y-4">
            <h3 className="text-sm font-bold text-foreground uppercase tracking-wide">Informacion de la Parcela</h3>
            <dl className="space-y-3">
              <InfoField label="Codigo" value={plot.plot_code} />
              <InfoField label="Area" value={plot.plot_area_ha ? `${Number(plot.plot_area_ha).toFixed(2)} ha` : null} />
              <InfoField label="Tipo geolocalizacion" value={plot.geolocation_type === 'point' ? 'Punto' : 'Poligono'} />
              <InfoField label="Latitud" value={plot.lat ? `${Number(plot.lat).toFixed(6)}` : null} />
              <InfoField label="Longitud" value={plot.lng ? `${Number(plot.lng).toFixed(6)}` : null} />
              <InfoField label="Pais" value={plot.country_code} />
              <InfoField label="Region" value={plot.region} />
              <InfoField label="Municipio" value={plot.municipality} />
            </dl>
          </div>

          {/* Risk */}
          <div className="bg-card rounded-xl border border-border  p-5 space-y-3">
            <h3 className="text-sm font-bold text-foreground uppercase tracking-wide">Nivel de Riesgo</h3>
            <span className={`inline-flex items-center px-3 py-1.5 rounded-full text-sm font-bold ${riskColor[plot.risk_level] || riskColor.standard}`}>
              {riskLabel[plot.risk_level] || plot.risk_level}
            </span>
          </div>

          {/* Crop info */}
          <div className="bg-card rounded-xl border border-border  p-5 space-y-3">
            <h3 className="text-sm font-bold text-foreground uppercase tracking-wide">Cultivo</h3>
            <dl className="space-y-3">
              <InfoField label="Tipo de cultivo" value={(plot as any).crop_type} />
              <InfoField label="Fecha de establecimiento" value={(plot as any).establishment_date} />
              <InfoField label="Fecha de renovacion" value={(plot as any).renovation_date} />
              <InfoField label="Tipo de renovacion" value={(plot as any).renovation_type} />
            </dl>
          </div>

          {/* Land title */}
          <div className="bg-card rounded-xl border border-border  p-5 space-y-3">
            <h3 className="text-sm font-bold text-foreground uppercase tracking-wide">Titulo de Propiedad</h3>
            <dl className="space-y-3">
              <InfoField label="Numero de titulo" value={plot.land_title_number} />
              <InfoField label="Hash del titulo" value={plot.land_title_hash} />
            </dl>
          </div>

          {/* Satellite */}
          {plot.satellite_report_url && (
            <div className="bg-card rounded-xl border border-border  p-5 space-y-3">
              <h3 className="text-sm font-bold text-foreground uppercase tracking-wide">Reporte Satelital</h3>
              <a href={plot.satellite_report_url} target="_blank" rel="noopener noreferrer"
                className="text-sm text-primary hover:underline">
                Ver reporte
              </a>
              {plot.satellite_verified_at && (
                <p className="text-xs text-muted-foreground">Verificado: {new Date(plot.satellite_verified_at).toLocaleString('es-CO')}</p>
              )}
            </div>
          )}

          {/* GeoJSON — pick from media library */}
          <div className="bg-card rounded-xl border border-border  p-5 space-y-3">
            <h3 className="text-sm font-bold text-foreground uppercase tracking-wide">Poligono GeoJSON</h3>
            {plot.geojson_arweave_url ? (
              <div className="space-y-2">
                <p className="text-xs text-emerald-600 font-medium">Poligono cargado</p>
                <a
                  href={mediaFileUrl(plot.geojson_arweave_url)}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-xs text-primary hover:underline font-mono truncate block"
                >
                  {plot.geojson_arweave_url}
                </a>
                {plot.geojson_hash && (
                  <p className="text-xs text-muted-foreground">SHA: {plot.geojson_hash.slice(0, 16)}...</p>
                )}
                <button
                  onClick={() => setShowGeojsonPicker(true)}
                  className="text-xs text-muted-foreground hover:text-primary hover:underline"
                >
                  Cambiar archivo
                </button>
              </div>
            ) : (
              <div className="space-y-2">
                {Number(plot.plot_area_ha) >= 4 && (
                  <div className="rounded-lg border border-red-200 bg-red-50 p-2 text-xs text-red-700 flex items-start gap-1.5">
                    <AlertTriangle className="h-3.5 w-3.5 mt-0.5 shrink-0" />
                    {"EUDR Art. 2.28: Parcelas >= 4 ha requieren poligono completo."}
                  </div>
                )}
                <button
                  onClick={() => setShowGeojsonPicker(true)}
                  disabled={linkingGeojson}
                  className="w-full flex items-center justify-center gap-2 rounded-lg border border-dashed border-slate-300 bg-muted px-4 py-3 text-sm text-muted-foreground hover:border-primary hover:bg-primary/5 transition-colors"
                >
                  <FolderOpen className="h-4 w-4" />
                  {linkingGeojson ? 'Vinculando...' : 'Seleccionar desde Media'}
                </button>
              </div>
            )}
          </div>

          {/* GeoJSON MediaPicker */}
          <MediaPickerModal
            open={showGeojsonPicker}
            onClose={() => setShowGeojsonPicker(false)}
            onSelect={async (mediaFileId, _docType, _desc) => {
              setLinkingGeojson(true)
              try {
                // Fetch the media file to get its URL and compute hash
                const mediaFile = await mediaApi.get(mediaFileId)

                // Fetch the actual file content to parse GeoJSON and compute hash
                const fullUrl = mediaFileUrl(mediaFile.url)
                const resp = await fetch(fullUrl)
                const text = await resp.text()

                // Try to parse as GeoJSON for map preview
                try {
                  const parsed = JSON.parse(text)
                  setGeojsonData(parsed)
                } catch { /* not valid JSON — still link it */ }

                // Compute SHA256
                const encoder = new TextEncoder()
                const data = encoder.encode(text)
                const hashBuffer = await crypto.subtle.digest('SHA-256', data)
                const hashArray = Array.from(new Uint8Array(hashBuffer))
                const hash = hashArray.map(b => b.toString(16).padStart(2, '0')).join('')

                // Update plot with reference to media file
                await updatePlot.mutateAsync({
                  geojson_arweave_url: mediaFile.url,
                  geojson_hash: hash,
                  geolocation_type: 'polygon',
                })

                toast.success('Poligono GeoJSON vinculado desde media')
                setShowGeojsonPicker(false)
              } catch (err: any) {
                toast.error(err.message ?? 'Error al vincular GeoJSON')
              } finally {
                setLinkingGeojson(false)
              }
            }}
          />
        </div>
      </div>

      {/* Evidence Documents */}
      <div className="bg-card rounded-xl border border-border  p-5">
        <DocumentUploader
          documents={plotDocs}
          isLoading={docsLoading}
          onAttach={async (data) => { await attachDoc.mutateAsync(data) }}
          onDetach={async (docId) => { await detachDoc.mutateAsync(docId) }}
          isPending={detachDoc.isPending}
        />
      </div>
    </div>
  )
}
