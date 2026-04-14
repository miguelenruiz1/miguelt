import { useState, useEffect } from 'react'
import { MapContainer, TileLayer, Marker, Polygon, Polyline, LayersControl, useMap, useMapEvents } from 'react-leaflet'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import { MapPin, Pencil, Trash2, Check, X, Loader2, Search, Navigation } from 'lucide-react'

const { BaseLayer } = LayersControl

// Smaller marker for vertices
const vertexIcon = L.divIcon({
  className: 'plot-vertex-marker',
  html: '<div style="width:14px;height:14px;background:#10b981;border:2px solid white;border-radius:50%;box-shadow:0 1px 3px rgba(0,0,0,.3)"></div>',
  iconSize: [14, 14],
  iconAnchor: [7, 7],
})

interface PlotPolygonEditorProps {
  initialLat?: number | null
  initialLng?: number | null
  initialGeojson?: any
  height?: string
  declaredAreaHa?: number | null
  onSave: (geojson: any, calculatedAreaHa?: number) => Promise<void> | void
  saving?: boolean
}

function ClickHandler({ enabled, onClick }: { enabled: boolean; onClick: (lat: number, lng: number) => void }) {
  useMapEvents({
    click: (e) => {
      if (enabled) onClick(e.latlng.lat, e.latlng.lng)
    },
  })
  return null
}

function FitToPoints({ points }: { points: [number, number][] }) {
  const map = useMap()
  useEffect(() => {
    if (points.length >= 2) {
      const bounds = L.latLngBounds(points)
      if (bounds.isValid()) map.fitBounds(bounds, { padding: [30, 30] })
    }
  }, [points, map])
  return null
}

function FlyTo({ target }: { target: [number, number] | null }) {
  const map = useMap()
  useEffect(() => {
    if (target) {
      map.flyTo(target, 16, { duration: 1.2 })
    }
  }, [target, map])
  return null
}

function geojsonToPoints(geojson: any): [number, number][] {
  if (!geojson) return []
  let coords: number[][] = []
  if (geojson.type === 'Polygon') {
    coords = geojson.coordinates[0] || []
  } else if (geojson.type === 'Feature' && geojson.geometry?.type === 'Polygon') {
    coords = geojson.geometry.coordinates[0] || []
  } else if (geojson.type === 'FeatureCollection' && geojson.features?.length) {
    const firstFeat = geojson.features[0]
    if (firstFeat?.geometry?.type === 'Polygon') {
      coords = firstFeat.geometry.coordinates[0] || []
    }
  }
  // GeoJSON uses [lng, lat] order. Strip the closing point.
  const result: [number, number][] = coords.map((c) => [c[1], c[0]])
  if (result.length > 1 && result[0][0] === result[result.length - 1][0] && result[0][1] === result[result.length - 1][1]) {
    result.pop()
  }
  return result
}

function pointsToGeojson(points: [number, number][]): any {
  if (points.length < 3) return null
  // Close the polygon
  const closed = [...points, points[0]]
  // Convert [lat, lng] → [lng, lat]
  const coords = closed.map(([lat, lng]) => [lng, lat])
  return {
    type: 'Polygon',
    coordinates: [coords],
  }
}

/** Calculate polygon area in hectares using the Shoelace formula with geodesic correction. */
function calcPolygonAreaHa(points: [number, number][]): number {
  if (points.length < 3) return 0
  const n = points.length
  // points are [lat, lng]
  const midLat = points.reduce((s, p) => s + p[0], 0) / n
  const mPerDegLat = 111_320
  const mPerDegLng = 111_320 * Math.cos((midLat * Math.PI) / 180)

  let area = 0
  for (let i = 0; i < n; i++) {
    const j = (i + 1) % n
    // Convert to meters for area calc
    const x0 = points[i][1] * mPerDegLng
    const y0 = points[i][0] * mPerDegLat
    const x1 = points[j][1] * mPerDegLng
    const y1 = points[j][0] * mPerDegLat
    area += x0 * y1 - x1 * y0
  }
  return Math.abs(area) / 2 / 10_000 // m² → ha
}

export function PlotPolygonEditor({ initialLat, initialLng, initialGeojson, height = '400px', declaredAreaHa, onSave, saving }: PlotPolygonEditorProps) {
  const [points, setPoints] = useState<[number, number][]>(() => geojsonToPoints(initialGeojson))
  const [editing, setEditing] = useState(false)
  const [hasChanges, setHasChanges] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const [searching, setSearching] = useState(false)
  const [flyTarget, setFlyTarget] = useState<[number, number] | null>(null)
  const [searchError, setSearchError] = useState<string | null>(null)

  async function handleSearch(e?: React.FormEvent | React.MouseEvent | React.KeyboardEvent) {
    e?.preventDefault?.()
    if (!searchQuery.trim()) return
    setSearching(true)
    setSearchError(null)
    try {
      // Nominatim free geocoding (OSM)
      const url = `https://nominatim.openstreetmap.org/search?format=json&limit=1&q=${encodeURIComponent(searchQuery)}`
      const resp = await fetch(url, { headers: { 'Accept-Language': 'es' } })
      const data = await resp.json()
      if (data && data.length > 0) {
        const lat = parseFloat(data[0].lat)
        const lng = parseFloat(data[0].lon)
        setFlyTarget([lat, lng])
      } else {
        setSearchError('No se encontraron resultados')
      }
    } catch (err: any) {
      setSearchError('Error de búsqueda')
    } finally {
      setSearching(false)
    }
  }

  function handleUseMyLocation() {
    if (!navigator.geolocation) {
      setSearchError('Geolocalización no disponible')
      return
    }
    setSearching(true)
    setSearchError(null)
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setFlyTarget([pos.coords.latitude, pos.coords.longitude])
        setSearching(false)
      },
      (err) => {
        setSearchError(err.message || 'No se pudo obtener ubicación')
        setSearching(false)
      },
      { enableHighAccuracy: true, timeout: 10000 }
    )
  }

  // Initial position
  const center: [number, number] = points.length > 0
    ? points[0]
    : initialLat != null && initialLng != null
      ? [Number(initialLat), Number(initialLng)]
      : [4.711, -74.0721]  // Bogotá default

  const handleAddPoint = (lat: number, lng: number) => {
    setPoints((prev) => [...prev, [lat, lng]])
    setHasChanges(true)
  }

  const handleRemoveLast = () => {
    setPoints((prev) => prev.slice(0, -1))
    setHasChanges(true)
  }

  const handleClear = () => {
    setPoints([])
    setHasChanges(true)
  }

  const handleSave = async () => {
    const geojson = pointsToGeojson(points)
    if (!geojson) return
    const areaHa = calcPolygonAreaHa(points)
    await onSave(geojson, areaHa)
    setEditing(false)
    setHasChanges(false)
  }

  const handleCancel = () => {
    setPoints(geojsonToPoints(initialGeojson))
    setEditing(false)
    setHasChanges(false)
  }

  const canSave = points.length >= 3
  const calculatedArea = points.length >= 3 ? calcPolygonAreaHa(points) : 0
  const areaRatio = declaredAreaHa && calculatedArea > 0 ? calculatedArea / declaredAreaHa : null
  const areaWarning = areaRatio !== null && (areaRatio > 3 || areaRatio < 0.1)

  return (
    <div className="space-y-3">
      {/* Search bar — usamos div en vez de form para no anidar forms HTML
          (los forms anidados no son validos y el button submit del form interno
          dispararia el submit del form padre cuando el editor se renderiza
          dentro de una pagina con <form>, ej. CreatePlotPage). */}
      <div className="flex items-center gap-2">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter') {
                e.preventDefault()
                e.stopPropagation()
                handleSearch(e)
              }
            }}
            placeholder="Buscar dirección, ciudad, finca... (ej: Jardín Antioquia)"
            className="w-full rounded-lg border border-border bg-card pl-9 pr-3 py-2 text-sm focus:border-primary/50 focus:outline-none focus:ring-2 focus:ring-ring/20"
          />
        </div>
        <button
          type="button"
          onClick={(e) => handleSearch(e)}
          disabled={searching || !searchQuery.trim()}
          className="inline-flex items-center gap-1 rounded-lg bg-primary px-3 py-2 text-xs font-semibold text-white hover:bg-primary/90 disabled:opacity-50"
        >
          {searching ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Search className="h-3.5 w-3.5" />}
          Buscar
        </button>
        <button
          type="button"
          onClick={handleUseMyLocation}
          disabled={searching}
          className="inline-flex items-center gap-1 rounded-lg border border-border bg-card px-3 py-2 text-xs font-semibold text-muted-foreground hover:bg-muted disabled:opacity-50"
          title="Usar mi ubicación actual"
        >
          <Navigation className="h-3.5 w-3.5" />
          Mi ubicación
        </button>
      </div>
      {searchError && (
        <p className="text-xs text-red-600">{searchError}</p>
      )}

      <div className="rounded-xl overflow-hidden border border-border relative z-0" style={{ height }}>
        <MapContainer center={center} zoom={15} style={{ height: '100%', width: '100%' }}>
          <LayersControl position="topright">
            <BaseLayer checked name="Satélite (Esri)">
              <TileLayer
                attribution='&copy; Esri, Maxar, Earthstar Geographics'
                url="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
                maxZoom={19}
              />
            </BaseLayer>
            <BaseLayer name="Híbrido (Satélite + Calles)">
              <TileLayer
                attribution='&copy; Esri, Maxar'
                url="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
                maxZoom={19}
              />
            </BaseLayer>
            <BaseLayer name="Topográfico">
              <TileLayer
                attribution='&copy; <a href="https://opentopomap.org">OpenTopoMap</a>'
                url="https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png"
                maxZoom={17}
              />
            </BaseLayer>
            <BaseLayer name="Calles (OSM)">
              <TileLayer
                attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OSM</a>'
                url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
              />
            </BaseLayer>
          </LayersControl>
          <ClickHandler enabled={editing} onClick={handleAddPoint} />
          <FitToPoints points={points} />
          <FlyTo target={flyTarget} />
          {points.length >= 3 && (
            <Polygon
              positions={points}
              pathOptions={{ color: '#10b981', fillColor: '#10b981', fillOpacity: 0.25, weight: 2 }}
            />
          )}
          {points.length === 2 && (
            <Polyline positions={points} pathOptions={{ color: '#10b981', weight: 2, dashArray: '6 4' }} />
          )}
          {points.map((p, i) => (
            <Marker key={i} position={p} icon={vertexIcon} />
          ))}
        </MapContainer>
      </div>

      {/* Area validation */}
      {points.length >= 3 && (
        <div className={`flex items-center gap-3 rounded-lg px-3 py-2 text-xs ${
          areaWarning ? 'bg-red-50 border border-red-200' : 'bg-muted/50'
        }`}>
          <div>
            <span className="text-muted-foreground">Area del poligono: </span>
            <span className="font-bold text-foreground">{calculatedArea.toFixed(2)} ha</span>
          </div>
          {declaredAreaHa != null && (
            <div>
              <span className="text-muted-foreground">Area declarada: </span>
              <span className="font-bold text-foreground">{Number(declaredAreaHa).toFixed(2)} ha</span>
            </div>
          )}
          {areaWarning && (
            <span className="text-red-600 font-semibold">
              El poligono dibujado ({calculatedArea.toFixed(1)} ha) no coincide con el area declarada ({Number(declaredAreaHa).toFixed(1)} ha).
              Verifica los vertices — el screening satelital sera impreciso si el poligono es incorrecto.
            </span>
          )}
          {areaRatio !== null && !areaWarning && (
            <span className="text-emerald-600 font-medium">Area consistente</span>
          )}
        </div>
      )}

      <div className="flex items-center justify-between flex-wrap gap-2">
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          <MapPin className="h-3.5 w-3.5" />
          <span>{points.length} {points.length === 1 ? 'punto' : 'puntos'}</span>
          {points.length > 0 && points.length < 3 && (
            <span className="text-amber-600">— Minimo 3 puntos para formar poligono</span>
          )}
          {editing && (
            <span className="text-emerald-600 font-medium">— Haz clic en el mapa para agregar puntos</span>
          )}
        </div>

        <div className="flex items-center gap-2">
          {!editing ? (
            <button
              type="button"
              onClick={() => setEditing(true)}
              className="inline-flex items-center gap-1.5 rounded-lg bg-emerald-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-emerald-700"
            >
              <Pencil className="h-3.5 w-3.5" />
              {points.length > 0 ? 'Editar polígono' : 'Dibujar polígono'}
            </button>
          ) : (
            <>
              <button
                type="button"
                onClick={handleRemoveLast}
                disabled={points.length === 0}
                className="inline-flex items-center gap-1 rounded-lg border border-border bg-card px-2.5 py-1.5 text-xs font-medium text-muted-foreground hover:bg-muted disabled:opacity-50"
                title="Quitar último punto"
              >
                ↶ Deshacer
              </button>
              <button
                type="button"
                onClick={handleClear}
                disabled={points.length === 0}
                className="inline-flex items-center gap-1 rounded-lg border border-border bg-card px-2.5 py-1.5 text-xs font-medium text-red-600 hover:bg-red-50 disabled:opacity-50"
              >
                <Trash2 className="h-3.5 w-3.5" />
                Limpiar
              </button>
              <button
                type="button"
                onClick={handleCancel}
                className="inline-flex items-center gap-1 rounded-lg border border-border bg-card px-2.5 py-1.5 text-xs font-medium text-muted-foreground hover:bg-muted"
              >
                <X className="h-3.5 w-3.5" />
                Cancelar
              </button>
              <button
                type="button"
                onClick={handleSave}
                disabled={!canSave || saving || !hasChanges}
                className="inline-flex items-center gap-1.5 rounded-lg bg-emerald-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-emerald-700 disabled:opacity-50"
              >
                {saving ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Check className="h-3.5 w-3.5" />}
                Guardar polígono
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  )
}
