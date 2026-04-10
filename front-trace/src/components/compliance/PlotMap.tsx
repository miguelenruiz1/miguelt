import { useEffect, useMemo } from 'react'
import { MapContainer, TileLayer, Marker, Popup, CircleMarker, GeoJSON, LayersControl, useMap } from 'react-leaflet'

const { BaseLayer } = LayersControl
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import type { CompliancePlot } from '@/types/compliance'

// Fix Leaflet default icon issue with bundlers
delete (L.Icon.Default.prototype as any)._getIconUrl
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon-2x.png',
  iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon.png',
  shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-shadow.png',
})

const RISK_COLORS: Record<string, string> = {
  low: '#22c55e',
  standard: '#f59e0b',
  high: '#ef4444',
}

function FitBounds({ plots }: { plots: CompliancePlot[] }) {
  const map = useMap()
  useEffect(() => {
    const allBounds = L.latLngBounds([])
    for (const p of plots) {
      // Include polygon bounds if available
      const gj = (p as any).geojson_data
      if (gj) {
        try {
          const layer = L.geoJSON(gj as any)
          const b = layer.getBounds()
          if (b.isValid()) allBounds.extend(b)
        } catch { /* ignore */ }
      } else if (p.lat != null && p.lng != null) {
        allBounds.extend([Number(p.lat), Number(p.lng)])
      }
    }
    if (allBounds.isValid()) {
      map.fitBounds(allBounds, { padding: [40, 40], maxZoom: 14 })
    }
  }, [plots, map])
  return null
}

interface PlotMapProps {
  plots: CompliancePlot[]
  height?: string
  onPlotClick?: (plot: CompliancePlot) => void
  selectedPlotId?: string
}

export function PlotMap({ plots, height = '400px', onPlotClick, selectedPlotId }: PlotMapProps) {
  const validPlots = plots.filter(p => p.lat != null && p.lng != null)

  if (validPlots.length === 0) {
    return (
      <div className="rounded-xl border-2 border-dashed border-border flex items-center justify-center text-muted-foreground text-sm" style={{ height }}>
        Sin parcelas con coordenadas para mostrar en el mapa
      </div>
    )
  }

  const center: [number, number] = [
    Number(validPlots[0].lat),
    Number(validPlots[0].lng),
  ]

  return (
    <div className="rounded-xl overflow-hidden border border-border  relative z-0" style={{ height }}>
      <MapContainer center={center} zoom={10} style={{ height: '100%', width: '100%' }}>
        <LayersControl position="topright">
          <BaseLayer checked name="Satélite">
            <TileLayer
              attribution='&copy; Esri, Maxar, Earthstar Geographics'
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
          <BaseLayer name="Calles">
            <TileLayer
              attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OSM</a>'
              url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
            />
          </BaseLayer>
        </LayersControl>
        <FitBounds plots={validPlots} />
        {validPlots.map(plot => {
          const lat = Number(plot.lat)
          const lng = Number(plot.lng)
          const color = RISK_COLORS[plot.risk_level] || RISK_COLORS.standard
          const fillColor = plot.deforestation_free ? color : '#ef4444'
          const isSelected = plot.id === selectedPlotId
          const geojson = (plot as any).geojson_data

          return geojson ? (
            <GeoJSON
              key={`${plot.id}-${isSelected}`}
              data={geojson}
              style={() => ({
                color: isSelected ? '#4f46e5' : color,
                fillColor,
                fillOpacity: isSelected ? 0.5 : 0.3,
                weight: isSelected ? 3 : 2,
              })}
              eventHandlers={{ click: () => onPlotClick?.(plot) }}
              onEachFeature={(_feature, layer) => {
                layer.bindPopup(`
                  <div style="font-size:12px;min-width:140px">
                    <p style="font-weight:bold;font-size:13px;margin:0 0 4px">${plot.plot_code}</p>
                    ${plot.municipality ? `<p style="margin:0">${plot.municipality}, ${plot.region || ''}</p>` : ''}
                    ${plot.plot_area_ha ? `<p style="margin:0">Area: ${Number(plot.plot_area_ha).toFixed(2)} ha</p>` : ''}
                    <p style="margin:2px 0 0">Deforestacion:
                      <strong style="color:${plot.deforestation_free ? '#16a34a' : '#dc2626'}">${plot.deforestation_free ? 'Libre' : 'Con alertas'}</strong>
                    </p>
                  </div>
                `)
              }}
            />
          ) : (
            <CircleMarker
              key={plot.id}
              center={[lat, lng]}
              radius={isSelected ? 14 : 10}
              pathOptions={{
                color: isSelected ? '#4f46e5' : color,
                fillColor,
                fillOpacity: isSelected ? 0.8 : 0.6,
                weight: isSelected ? 3 : 2,
              }}
              eventHandlers={{ click: () => onPlotClick?.(plot) }}
            >
              <Popup>
                <div className="text-xs space-y-1 min-w-40">
                  <p className="font-bold text-sm">{plot.plot_code}</p>
                  {plot.municipality && <p>{plot.municipality}, {plot.region}</p>}
                  {plot.plot_area_ha && <p>Area: {Number(plot.plot_area_ha).toFixed(2)} ha</p>}
                  <p>
                    Deforestacion: {' '}
                    <span className={plot.deforestation_free ? 'text-green-600 font-bold' : 'text-red-600 font-bold'}>
                      {plot.deforestation_free ? 'Libre' : 'Con alertas'}
                    </span>
                  </p>
                  <p>Riesgo: <span style={{ color }}>{plot.risk_level}</span></p>
                  <p className="text-muted-foreground">{lat.toFixed(6)}, {lng.toFixed(6)}</p>
                </div>
              </Popup>
            </CircleMarker>
          )
        })}
      </MapContainer>
    </div>
  )
}

interface SinglePlotMapProps {
  plot: CompliancePlot
  height?: string
  geojsonData?: GeoJSON.GeoJsonObject | null
}

function FitGeoJSON({ geojson }: { geojson: GeoJSON.GeoJsonObject }) {
  const map = useMap()
  useEffect(() => {
    try {
      const layer = L.geoJSON(geojson as any)
      const bounds = layer.getBounds()
      if (bounds.isValid()) {
        map.fitBounds(bounds, { padding: [30, 30] })
      }
    } catch {
      // ignore invalid geojson
    }
  }, [geojson, map])
  return null
}

export function SinglePlotMap({ plot, height = '300px', geojsonData }: SinglePlotMapProps) {
  if (plot.lat == null || plot.lng == null) {
    return (
      <div className="rounded-xl border-2 border-dashed border-border flex items-center justify-center text-muted-foreground text-sm" style={{ height }}>
        Sin coordenadas
      </div>
    )
  }

  const lat = Number(plot.lat)
  const lng = Number(plot.lng)
  const color = RISK_COLORS[plot.risk_level] || RISK_COLORS.standard

  return (
    <div className="rounded-xl overflow-hidden border border-border  relative z-0" style={{ height }}>
      <MapContainer center={[lat, lng]} zoom={15} style={{ height: '100%', width: '100%' }}>
        <LayersControl position="topright">
          <BaseLayer checked name="Satélite">
            <TileLayer
              attribution='&copy; Esri, Maxar, Earthstar Geographics'
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
          <BaseLayer name="Calles">
            <TileLayer
              attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OSM</a>'
              url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
            />
          </BaseLayer>
        </LayersControl>
        {geojsonData ? (
          <>
            <FitGeoJSON geojson={geojsonData} />
            <GeoJSON
              data={geojsonData as any}
              style={() => ({
                color,
                fillColor: plot.deforestation_free ? color : '#ef4444',
                fillOpacity: 0.3,
                weight: 3,
              })}
            />
          </>
        ) : (
          <>
            <CircleMarker
              center={[lat, lng]}
              radius={15}
              pathOptions={{
                color,
                fillColor: plot.deforestation_free ? color : '#ef4444',
                fillOpacity: 0.6,
                weight: 3,
              }}
            />
            <Marker position={[lat, lng]} />
          </>
        )}
      </MapContainer>
    </div>
  )
}
