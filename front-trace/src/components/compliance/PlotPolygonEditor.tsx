import { useState, useEffect } from 'react'
import { MapContainer, TileLayer, Marker, Polygon, Polyline, useMap, useMapEvents } from 'react-leaflet'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import { MapPin, Pencil, Trash2, Check, X, Loader2 } from 'lucide-react'

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
  onSave: (geojson: any) => Promise<void> | void
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

export function PlotPolygonEditor({ initialLat, initialLng, initialGeojson, height = '400px', onSave, saving }: PlotPolygonEditorProps) {
  const [points, setPoints] = useState<[number, number][]>(() => geojsonToPoints(initialGeojson))
  const [editing, setEditing] = useState(false)
  const [hasChanges, setHasChanges] = useState(false)

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
    await onSave(geojson)
    setEditing(false)
    setHasChanges(false)
  }

  const handleCancel = () => {
    setPoints(geojsonToPoints(initialGeojson))
    setEditing(false)
    setHasChanges(false)
  }

  const canSave = points.length >= 3

  return (
    <div className="space-y-3">
      <div className="rounded-xl overflow-hidden border border-border relative z-0" style={{ height }}>
        <MapContainer center={center} zoom={15} style={{ height: '100%', width: '100%' }}>
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OSM</a>'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />
          {/* Satellite layer toggle (Esri free) */}
          <ClickHandler enabled={editing} onClick={handleAddPoint} />
          <FitToPoints points={points} />
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

      <div className="flex items-center justify-between flex-wrap gap-2">
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          <MapPin className="h-3.5 w-3.5" />
          <span>{points.length} {points.length === 1 ? 'punto' : 'puntos'}</span>
          {points.length > 0 && points.length < 3 && (
            <span className="text-amber-600">— Mínimo 3 puntos para formar polígono</span>
          )}
          {editing && (
            <span className="text-emerald-600 font-medium">— Haz clic en el mapa para agregar puntos</span>
          )}
        </div>

        <div className="flex items-center gap-2">
          {!editing ? (
            <button
              onClick={() => setEditing(true)}
              className="inline-flex items-center gap-1.5 rounded-lg bg-emerald-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-emerald-700"
            >
              <Pencil className="h-3.5 w-3.5" />
              {points.length > 0 ? 'Editar polígono' : 'Dibujar polígono'}
            </button>
          ) : (
            <>
              <button
                onClick={handleRemoveLast}
                disabled={points.length === 0}
                className="inline-flex items-center gap-1 rounded-lg border border-border bg-card px-2.5 py-1.5 text-xs font-medium text-muted-foreground hover:bg-muted disabled:opacity-50"
                title="Quitar último punto"
              >
                ↶ Deshacer
              </button>
              <button
                onClick={handleClear}
                disabled={points.length === 0}
                className="inline-flex items-center gap-1 rounded-lg border border-border bg-card px-2.5 py-1.5 text-xs font-medium text-red-600 hover:bg-red-50 disabled:opacity-50"
              >
                <Trash2 className="h-3.5 w-3.5" />
                Limpiar
              </button>
              <button
                onClick={handleCancel}
                className="inline-flex items-center gap-1 rounded-lg border border-border bg-card px-2.5 py-1.5 text-xs font-medium text-muted-foreground hover:bg-muted"
              >
                <X className="h-3.5 w-3.5" />
                Cancelar
              </button>
              <button
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
