import { useState, useEffect, useRef, type ReactNode } from 'react'
import { useParams, Link } from 'react-router-dom'
import { ArrowLeft, MapPin, Check, X, Loader2, Calendar, Sprout, Shield, AlertTriangle, FolderOpen, ShieldCheck, ExternalLink, FileText } from 'lucide-react'
import { usePlot, useUpdatePlot, useScreenDeforestationFull, usePlotDocuments, useAttachPlotDocument, useDetachPlotDocument, usePlotLegalStatus, useUpdatePlotLegalRequirement, useCountryRisk, useRiskDecision } from '@/hooks/useCompliance'
import type { RiskDecisionResponse } from '@/types/compliance'
import { SinglePlotMap } from '@/components/compliance/PlotMap'
import { PlotPolygonEditor } from '@/components/compliance/PlotPolygonEditor'
import DocumentUploader from '@/components/compliance/DocumentUploader'
import { Badge } from '@/components/ui/badge'
import { useToast } from '@/store/toast'
import { mediaApi, mediaFileUrl } from '@/lib/media-api'
import MediaPickerModal from '@/components/compliance/MediaPickerModal'
import type { CompliancePlot, EudrRiskLevel, SourceResult } from '@/types/compliance'

const riskLabel: Record<string, string> = { low: 'Bajo', standard: 'Estandar', high: 'Alto' }
const riskColor: Record<string, string> = { low: 'bg-green-100 text-green-700', standard: 'bg-amber-100 text-amber-700', high: 'bg-red-100 text-red-700' }

const eudrRiskLabel: Record<EudrRiskLevel, string> = {
  none: 'No aplica (no bosque)',
  low: 'Bajo',
  medium: 'Medio (verificar)',
  high: 'Alto',
}
const eudrRiskColor: Record<EudrRiskLevel, string> = {
  none: 'bg-slate-100 text-slate-700 border-slate-300',
  low: 'bg-emerald-100 text-emerald-800 border-emerald-300',
  medium: 'bg-amber-100 text-amber-800 border-amber-300',
  high: 'bg-red-100 text-red-800 border-red-300',
}
const eudrRiskBorder: Record<EudrRiskLevel, string> = {
  none: 'border-slate-200',
  low: 'border-emerald-200',
  medium: 'border-amber-200',
  high: 'border-red-200',
}

function SourceCard({ src }: { src: SourceResult }) {
  const hasError = Boolean(src.error)
  const isJrc = src.source === 'jrc_global_forest_cover'
  const isClean = !hasError && (
    (src.source === 'gfw_integrated_alerts' && src.deforestation_free === true) ||
    (src.source === 'umd_tree_cover_loss' && src.has_loss === false) ||
    (isJrc && src.was_forest_2020 === false) // JRC: "clean" = NOT forest → EUDR doesn't apply
  )
  const isDetected = !hasError && !isClean && !isJrc
  const isForestConfirmed = !hasError && isJrc && src.was_forest_2020 === true
  const borderColor = hasError
    ? 'border-amber-300 bg-amber-50/50'
    : isForestConfirmed
      ? 'border-blue-200 bg-blue-50/50'
      : isClean
        ? 'border-emerald-200 bg-emerald-50/50'
        : 'border-red-200 bg-red-50/50'

  return (
    <div className={`rounded-xl border-2 ${borderColor} p-4 space-y-3`}>
      {/* Header */}
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <h4 className="text-sm font-bold text-foreground leading-tight">{src.name}</h4>
          <p className="text-[11px] text-muted-foreground mt-0.5">{src.institution}</p>
        </div>
        <div className="shrink-0">
          {hasError ? (
            <span className="inline-flex items-center gap-1 rounded-full bg-amber-100 px-2 py-0.5 text-xs font-semibold text-amber-700">
              <AlertTriangle className="h-3 w-3" /> Error
            </span>
          ) : isForestConfirmed ? (
            <span className="inline-flex items-center gap-1 rounded-full bg-blue-100 px-2 py-0.5 text-xs font-semibold text-blue-700">
              <Sprout className="h-3 w-3" /> Zona forestal
            </span>
          ) : isClean ? (
            <span className="inline-flex items-center gap-1 rounded-full bg-emerald-100 px-2 py-0.5 text-xs font-semibold text-emerald-700">
              <Check className="h-3 w-3" /> {isJrc ? 'No forestal — EUDR no aplica' : 'Sin deforestacion'}
            </span>
          ) : (
            <span className="inline-flex items-center gap-1 rounded-full bg-red-100 px-2 py-0.5 text-xs font-semibold text-red-700">
              <X className="h-3 w-3" /> Deforestacion detectada
            </span>
          )}
        </div>
      </div>

      {/* Source-specific metrics */}
      {hasError ? (
        <p className="text-xs text-amber-700 bg-amber-100 rounded-lg p-2">{src.error}</p>
      ) : (
        <div className="space-y-2">
          {src.source === 'gfw_integrated_alerts' && (
            <>
              <div className="grid grid-cols-2 gap-2 text-xs">
                <div className="bg-muted/50 rounded-lg p-2.5">
                  <span className="text-muted-foreground block text-[10px] uppercase tracking-wide font-medium">Alertas post-corte EUDR</span>
                  <p className={`font-bold text-xl mt-0.5 ${(src.alerts_count ?? 0) > 0 ? 'text-red-600' : 'text-emerald-600'}`}>
                    {(src.alerts_count ?? 0).toLocaleString('es-CO')}
                  </p>
                  <p className="text-[10px] text-muted-foreground mt-0.5">Posteriores al 31 dic 2020</p>
                </div>
                <div className="bg-muted/50 rounded-lg p-2.5">
                  <span className="text-muted-foreground block text-[10px] uppercase tracking-wide font-medium">Alta confianza</span>
                  <p className={`font-bold text-xl mt-0.5 ${(src.high_confidence_alerts ?? 0) > 0 ? 'text-red-600' : 'text-emerald-600'}`}>
                    {(src.high_confidence_alerts ?? 0).toLocaleString('es-CO')}
                  </p>
                  <p className="text-[10px] text-muted-foreground mt-0.5">Confidence: high + highest</p>
                </div>
              </div>
              <div className="bg-muted/30 rounded-lg px-3 py-2 space-y-1">
                <p className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wide">Ficha tecnica</p>
                <dl className="grid grid-cols-2 gap-x-4 gap-y-0.5 text-[11px]">
                  <dt className="text-muted-foreground">Sensores</dt><dd className="font-medium">GLAD-L (Landsat 8/9), GLAD-S2 (Sentinel-2), RADD (Sentinel-1 SAR)</dd>
                  <dt className="text-muted-foreground">Resolucion temporal</dt><dd className="font-medium">Semanal (~5-8 dias de latencia)</dd>
                  <dt className="text-muted-foreground">Resolucion espacial</dt><dd className="font-medium">30m (Landsat) / 10m (Sentinel-2)</dd>
                  <dt className="text-muted-foreground">Fecha de corte EUDR</dt><dd className="font-medium">{src.cutoff_date ?? '2020-12-31'} (Art. 2 Reg. 2023/1115)</dd>
                  <dt className="text-muted-foreground">Cobertura</dt><dd className="font-medium">Global, tropicos y subtropicos</dd>
                </dl>
              </div>
              <div className={`text-[11px] rounded-lg px-3 py-2 leading-relaxed ${isDetected ? 'text-red-800 bg-red-50 border border-red-200' : 'text-emerald-800 bg-emerald-50 border border-emerald-200'}`}>
                <p className="font-semibold mb-0.5">{isDetected ? 'Resultado: DEFORESTACION DETECTADA' : 'Resultado: SIN DEFORESTACION'}</p>
                {isDetected ? (
                  <p>Se identificaron {src.alerts_count} alertas satelitales de perdida de cobertura forestal posteriores a la fecha de corte del EUDR. {src.high_confidence_alerts} de ellas tienen nivel de confianza alto/muy alto, lo que indica deteccion confirmada por multiples sensores independientes. Segun Art. 3(1) del Reglamento EUDR, productos derivados de esta parcela no podrian comercializarse en la UE sin due diligence adicional.</p>
                ) : (
                  <p>Ninguna alerta de deforestacion registrada despues del 31/12/2020. Los tres sistemas de sensores (optico Landsat, optico Sentinel-2 y radar SAR) coinciden en ausencia de cambio de cobertura.</p>
                )}
              </div>
            </>
          )}
          {src.source === 'umd_tree_cover_loss' && (() => {
            const lossHa = ((src.loss_pixels ?? 0) * 900) / 10000
            return (
            <>
              <div className="grid grid-cols-3 gap-2 text-xs">
                <div className="bg-muted/50 rounded-lg p-2.5">
                  <span className="text-muted-foreground block text-[10px] uppercase tracking-wide font-medium">Pixeles perdidos</span>
                  <p className={`font-bold text-xl mt-0.5 ${(src.loss_pixels ?? 0) > 0 ? 'text-red-600' : 'text-emerald-600'}`}>
                    {(src.loss_pixels ?? 0).toLocaleString('es-CO')}
                  </p>
                </div>
                <div className="bg-muted/50 rounded-lg p-2.5">
                  <span className="text-muted-foreground block text-[10px] uppercase tracking-wide font-medium">Area afectada</span>
                  <p className={`font-bold text-xl mt-0.5 ${lossHa > 0 ? 'text-red-600' : 'text-emerald-600'}`}>
                    {lossHa.toFixed(2)} ha
                  </p>
                </div>
                <div className="bg-muted/50 rounded-lg p-2.5">
                  <span className="text-muted-foreground block text-[10px] uppercase tracking-wide font-medium">Post {src.cutoff_year ?? 2021}</span>
                  <p className={`font-bold text-xl mt-0.5 ${src.has_loss ? 'text-red-600' : 'text-emerald-600'}`}>
                    {src.has_loss ? 'SI' : 'NO'}
                  </p>
                </div>
              </div>
              {src.loss_by_year && Object.keys(src.loss_by_year).length > 0 && (
                <div className="bg-muted/30 rounded-lg px-3 py-2">
                  <span className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wide block mb-1.5">Desglose anual de perdida</span>
                  <div className="flex gap-2 flex-wrap">
                    {Object.entries(src.loss_by_year).map(([yr, px]) => {
                      const ha = (Number(px) * 900 / 10000).toFixed(2)
                      return (
                        <div key={yr} className="bg-background rounded-lg px-2.5 py-1.5 text-center border border-red-200">
                          <span className="text-[10px] text-muted-foreground block font-medium">{yr}</span>
                          <span className="text-xs font-bold text-red-600 block">{Number(px).toLocaleString('es-CO')} px</span>
                          <span className="text-[10px] text-red-500">{ha} ha</span>
                        </div>
                      )
                    })}
                  </div>
                </div>
              )}
              <div className="bg-muted/30 rounded-lg px-3 py-2 space-y-1">
                <p className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wide">Ficha tecnica</p>
                <dl className="grid grid-cols-2 gap-x-4 gap-y-0.5 text-[11px]">
                  <dt className="text-muted-foreground">Fuente cientifica</dt><dd className="font-medium">Hansen et al. (Science, 2013) — actualizado anualmente</dd>
                  <dt className="text-muted-foreground">Sensor</dt><dd className="font-medium">Landsat 7 ETM+ / Landsat 8 OLI</dd>
                  <dt className="text-muted-foreground">Resolucion</dt><dd className="font-medium">30m/pixel (1 pixel = 900 m² = 0.09 ha)</dd>
                  <dt className="text-muted-foreground">Periodo cubierto</dt><dd className="font-medium">2001 — presente (corte EUDR: {'>'}= {src.cutoff_year ?? 2021})</dd>
                  <dt className="text-muted-foreground">Definicion de perdida</dt><dd className="font-medium">Remocion completa del dosel {'>'} 5m de altura</dd>
                </dl>
              </div>
              <div className={`text-[11px] rounded-lg px-3 py-2 leading-relaxed ${isDetected ? 'text-red-800 bg-red-50 border border-red-200' : 'text-emerald-800 bg-emerald-50 border border-emerald-200'}`}>
                <p className="font-semibold mb-0.5">{isDetected ? 'Resultado: PERDIDA DE COBERTURA DETECTADA' : 'Resultado: COBERTURA INTACTA'}</p>
                {isDetected ? (
                  <p>Se cuantifico perdida de {(src.loss_pixels ?? 0).toLocaleString('es-CO')} pixeles ({lossHa.toFixed(2)} hectareas) de cobertura arborea despues de {src.cutoff_year ?? 2021}. Cada pixel Landsat (30x30m) indica remocion total del dosel forestal. Esta evidencia historica, combinada con las alertas GFW, constituye indicador de riesgo bajo Art. 10 del Reglamento EUDR.</p>
                ) : (
                  <p>El analisis historico de imagenes Landsat no registra eliminacion de dosel forestal en la parcela despues de {src.cutoff_year ?? 2021}. La cobertura arborea se ha mantenido estable segun el dataset Hansen v1.11.</p>
                )}
              </div>
            </>
            )
          })()}
          {src.source === 'jrc_global_forest_cover' && (() => {
            const forestHa = ((src.forest_pixel_count ?? 0) * 100) / 10000
            return (
            <>
              <div className="grid grid-cols-3 gap-2 text-xs">
                <div className="bg-muted/50 rounded-lg p-2.5">
                  <span className="text-muted-foreground block text-[10px] uppercase tracking-wide font-medium">Pixeles de bosque</span>
                  <p className="font-bold text-xl mt-0.5 text-foreground">
                    {(src.forest_pixel_count ?? 0).toLocaleString('es-CO')}
                  </p>
                </div>
                <div className="bg-muted/50 rounded-lg p-2.5">
                  <span className="text-muted-foreground block text-[10px] uppercase tracking-wide font-medium">Cobertura forestal</span>
                  <p className="font-bold text-xl mt-0.5 text-foreground">
                    {forestHa.toFixed(2)} ha
                  </p>
                </div>
                <div className="bg-muted/50 rounded-lg p-2.5">
                  <span className="text-muted-foreground block text-[10px] uppercase tracking-wide font-medium">Clasificacion 2020</span>
                  <p className={`font-bold text-xl mt-0.5 ${src.was_forest_2020 ? 'text-blue-600' : 'text-emerald-600'}`}>
                    {src.was_forest_2020 ? 'BOSQUE' : 'NO BOSQUE'}
                  </p>
                </div>
              </div>
              <div className="bg-muted/30 rounded-lg px-3 py-2 space-y-1">
                <p className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wide">Ficha tecnica</p>
                <dl className="grid grid-cols-2 gap-x-4 gap-y-0.5 text-[11px]">
                  <dt className="text-muted-foreground">Institucion</dt><dd className="font-medium">Joint Research Centre (JRC), Comision Europea</dd>
                  <dt className="text-muted-foreground">Mandato legal</dt><dd className="font-medium">Art. 2(6) Reg. (UE) 2023/1115 — definicion de bosque</dd>
                  <dt className="text-muted-foreground">Sensor</dt><dd className="font-medium">Sentinel-2 MSI (Copernicus)</dd>
                  <dt className="text-muted-foreground">Resolucion</dt><dd className="font-medium">10m/pixel (1 pixel = 100 m² = 0.01 ha)</dd>
                  <dt className="text-muted-foreground">Ano de referencia</dt><dd className="font-medium">2020 (linea base oficial EUDR)</dd>
                  <dt className="text-muted-foreground">Definicion de bosque</dt><dd className="font-medium">Terreno {'>'} 0.5 ha, dosel {'>'} 10%, arboles {'>'} 5m (FAO)</dd>
                </dl>
              </div>
              <div className={`text-[11px] rounded-lg px-3 py-2 leading-relaxed border ${src.was_forest_2020 ? 'text-blue-800 bg-blue-50 border-blue-200' : 'text-emerald-800 bg-emerald-50 border-emerald-200'}`}>
                <p className="font-semibold mb-0.5">{src.was_forest_2020 ? 'Clasificacion: ZONA FORESTAL — EUDR aplica' : 'Clasificacion: ZONA NO FORESTAL — EUDR no aplica'}</p>
                {src.was_forest_2020 ? (
                  <p>El JRC clasifico {(src.forest_pixel_count ?? 0).toLocaleString('es-CO')} pixeles Sentinel-2 ({forestHa.toFixed(2)} ha) como cobertura forestal en 2020. Segun Art. 2(6) del Reglamento EUDR, esta parcela esta sujeta a las restricciones de deforestacion: se debe demostrar que no hubo conversion forestal despues del 31/12/2020 para comercializar productos derivados en la UE.</p>
                ) : (
                  <p>El mapa JRC 2020 no clasifico esta area como bosque. Segun la definicion FAO adoptada por el EUDR (terreno {'>'} 0.5 ha, dosel {'>'} 10%, arboles {'>'} 5m), la parcela no era forestal en la fecha de referencia. Las restricciones de deforestacion del Art. 3(1) no aplican.</p>
                )}
              </div>
            </>
            )
          })()}
        </div>
      )}

      {/* Footer: timestamp + optional methodology link */}
      <div className="flex items-center justify-between pt-2 border-t border-border/50">
        {src.reference_url ? (
          <a
            href={src.reference_url}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1 text-[10px] text-muted-foreground hover:text-primary hover:underline"
          >
            Metodologia <ExternalLink className="h-3 w-3" />
          </a>
        ) : <span />}
        {src.checked_at && (
          <span className="text-[10px] text-muted-foreground tabular-nums">
            Verificado: {new Date(src.checked_at).toLocaleString('es-CO')}
          </span>
        )}
      </div>
    </div>
  )
}

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

const TENURE_TYPE_LABELS: Record<string, string> = {
  owned: 'Propietario',
  leased: 'Arrendatario',
  sharecropped: 'Aparcero',
  concession: 'Concesion',
  indigenous_collective: 'Territorio indigena colectivo',
  afro_collective: 'Territorio afrocolectivo',
  baldio_adjudicado: 'Baldio adjudicado (ANT)',
  occupation: 'Ocupacion sin titulo',
  other: 'Otro',
}

const ID_TYPE_OPTIONS = ['CC', 'CE', 'NIT', 'RUT', 'PASAPORTE', 'OTRO']

function TenureSection({
  plot,
  onSave,
  saving,
}: {
  plot: CompliancePlot
  onSave: (updates: Partial<CompliancePlot>) => Promise<void>
  saving: boolean
}) {
  const [editing, setEditing] = useState(false)
  const [form, setForm] = useState<Partial<CompliancePlot>>({})

  function startEdit() {
    setForm({
      owner_name: plot.owner_name ?? '',
      owner_id_type: plot.owner_id_type ?? '',
      owner_id_number: plot.owner_id_number ?? '',
      producer_name: plot.producer_name ?? '',
      producer_id_type: plot.producer_id_type ?? '',
      producer_id_number: plot.producer_id_number ?? '',
      cadastral_id: plot.cadastral_id ?? '',
      tenure_type: plot.tenure_type ?? null,
      tenure_start_date: plot.tenure_start_date ?? '',
      tenure_end_date: plot.tenure_end_date ?? '',
      indigenous_territory_flag: plot.indigenous_territory_flag ?? false,
      land_title_number: plot.land_title_number ?? '',
    })
    setEditing(true)
  }

  function cancelEdit() {
    setForm({})
    setEditing(false)
  }

  async function saveEdit() {
    // Convertir empty strings a null para que el backend los limpie correctamente
    const cleaned: Partial<CompliancePlot> = {}
    for (const [k, v] of Object.entries(form)) {
      if (v === '' || v === undefined) {
        ;(cleaned as any)[k] = null
      } else {
        ;(cleaned as any)[k] = v
      }
    }
    await onSave(cleaned)
    setEditing(false)
  }

  const update = (k: keyof CompliancePlot) => (v: any) => setForm(f => ({ ...f, [k]: v }))

  if (!editing) {
    return (
      <div className="bg-card rounded-xl border border-border p-5 space-y-3">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-bold text-foreground uppercase tracking-wide">
            Tenencia y Propiedad
          </h3>
          <button
            onClick={startEdit}
            className="text-xs text-primary hover:underline font-semibold"
          >
            Editar
          </button>
        </div>
        <p className="text-[10px] text-muted-foreground leading-relaxed -mt-1">
          EUDR Art. 8.2.f exige evidencia del derecho legal de uso de la zona.
        </p>
        <dl className="space-y-3">
          <InfoField
            label="Tipo de tenencia"
            value={plot.tenure_type ? TENURE_TYPE_LABELS[plot.tenure_type] || plot.tenure_type : null}
          />
          {plot.tenure_start_date && (
            <InfoField
              label="Vigencia"
              value={`${plot.tenure_start_date}${plot.tenure_end_date ? ` → ${plot.tenure_end_date}` : ''}`}
            />
          )}
          <InfoField label="Identificador catastral" value={plot.cadastral_id} />
          <div className="border-t border-border pt-3">
            <p className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wide mb-2">
              Productor (quien cultiva)
            </p>
            <InfoField label="Nombre" value={plot.producer_name} />
            {plot.producer_id_number && (
              <InfoField
                label="Identificacion"
                value={`${plot.producer_id_type || ''} ${plot.producer_id_number}`.trim()}
              />
            )}
          </div>
          <div className="border-t border-border pt-3">
            <p className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wide mb-2">
              Titular legal del predio
            </p>
            <InfoField label="Nombre" value={plot.owner_name} />
            {plot.owner_id_number && (
              <InfoField
                label="Identificacion"
                value={`${plot.owner_id_type || ''} ${plot.owner_id_number}`.trim()}
              />
            )}
            <InfoField label="Folio matricula / titulo" value={plot.land_title_number} />
          </div>
          {plot.indigenous_territory_flag && (
            <div className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-800 flex items-start gap-1.5">
              <AlertTriangle className="h-3.5 w-3.5 mt-0.5 shrink-0" />
              <span>
                Territorio indigena/colectivo — Art. 10 EUDR exige due diligence reforzado.
              </span>
            </div>
          )}
        </dl>
      </div>
    )
  }

  return (
    <div className="bg-card rounded-xl border border-primary/40 p-5 space-y-4">
      <h3 className="text-sm font-bold text-foreground uppercase tracking-wide">
        Editar Tenencia y Propiedad
      </h3>

      <div>
        <label className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
          Tipo de tenencia
        </label>
        <select
          value={form.tenure_type || ''}
          onChange={e => update('tenure_type')(e.target.value || null)}
          className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
        >
          <option value="">— Seleccionar —</option>
          {Object.entries(TENURE_TYPE_LABELS).map(([k, v]) => (
            <option key={k} value={k}>{v}</option>
          ))}
        </select>
      </div>

      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
            Vigencia desde
          </label>
          <input
            type="date"
            value={form.tenure_start_date || ''}
            onChange={e => update('tenure_start_date')(e.target.value)}
            className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
          />
        </div>
        <div>
          <label className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
            Vigencia hasta
          </label>
          <input
            type="date"
            value={form.tenure_end_date || ''}
            onChange={e => update('tenure_end_date')(e.target.value)}
            className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
          />
        </div>
      </div>

      <div>
        <label className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
          Identificador catastral (folio matricula SNR / catastro IGAC)
        </label>
        <input
          type="text"
          value={form.cadastral_id || ''}
          onChange={e => update('cadastral_id')(e.target.value)}
          placeholder="ej. 50N-12345"
          className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
        />
      </div>

      <div className="border-t border-border pt-3 space-y-3">
        <p className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wide">
          Productor (quien cultiva)
        </p>
        <input
          type="text"
          value={form.producer_name || ''}
          onChange={e => update('producer_name')(e.target.value)}
          placeholder="Nombre del productor"
          className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
        />
        <div className="grid grid-cols-3 gap-2">
          <select
            value={form.producer_id_type || ''}
            onChange={e => update('producer_id_type')(e.target.value)}
            className="rounded-lg border border-border bg-background px-2 py-2 text-sm"
          >
            <option value="">— Tipo —</option>
            {ID_TYPE_OPTIONS.map(t => <option key={t} value={t}>{t}</option>)}
          </select>
          <input
            type="text"
            value={form.producer_id_number || ''}
            onChange={e => update('producer_id_number')(e.target.value)}
            placeholder="Numero"
            className="col-span-2 rounded-lg border border-border bg-background px-3 py-2 text-sm"
          />
        </div>
      </div>

      <div className="border-t border-border pt-3 space-y-3">
        <p className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wide">
          Titular legal del predio (si difiere del productor)
        </p>
        <input
          type="text"
          value={form.owner_name || ''}
          onChange={e => update('owner_name')(e.target.value)}
          placeholder="Nombre del titular"
          className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
        />
        <div className="grid grid-cols-3 gap-2">
          <select
            value={form.owner_id_type || ''}
            onChange={e => update('owner_id_type')(e.target.value)}
            className="rounded-lg border border-border bg-background px-2 py-2 text-sm"
          >
            <option value="">— Tipo —</option>
            {ID_TYPE_OPTIONS.map(t => <option key={t} value={t}>{t}</option>)}
          </select>
          <input
            type="text"
            value={form.owner_id_number || ''}
            onChange={e => update('owner_id_number')(e.target.value)}
            placeholder="Numero"
            className="col-span-2 rounded-lg border border-border bg-background px-3 py-2 text-sm"
          />
        </div>
        <input
          type="text"
          value={form.land_title_number || ''}
          onChange={e => update('land_title_number')(e.target.value)}
          placeholder="Numero de titulo / folio"
          className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
        />
      </div>

      <label className="flex items-start gap-2 text-xs cursor-pointer">
        <input
          type="checkbox"
          checked={form.indigenous_territory_flag || false}
          onChange={e => update('indigenous_territory_flag')(e.target.checked)}
          className="mt-0.5"
        />
        <span className="text-foreground">
          Territorio indigena o colectivo afro
          <span className="block text-[10px] text-muted-foreground mt-0.5">
            Activa due diligence reforzado bajo Art. 10 EUDR.
          </span>
        </span>
      </label>

      <div className="flex items-center justify-end gap-2 pt-2 border-t border-border">
        <button
          onClick={cancelEdit}
          disabled={saving}
          className="rounded-lg border border-border bg-card px-4 py-2 text-sm font-semibold text-muted-foreground hover:bg-muted"
        >
          Cancelar
        </button>
        <button
          onClick={saveEdit}
          disabled={saving}
          className="rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-white hover:bg-primary/90 disabled:opacity-50 inline-flex items-center gap-2"
        >
          {saving && <Loader2 className="h-4 w-4 animate-spin" />}
          Guardar cambios
        </button>
      </div>
    </div>
  )
}

export function PlotDetailPage() {
  const { plotId } = useParams<{ plotId: string }>()
  const { data: plot, isLoading } = usePlot(plotId!)
  const updatePlot = useUpdatePlot(plotId!)
  const screenFull = useScreenDeforestationFull()
  const { data: plotDocs = [], isLoading: docsLoading } = usePlotDocuments(plotId!)
  const attachDoc = useAttachPlotDocument(plotId!)
  const detachDoc = useDetachPlotDocument(plotId!)
  const toast = useToast()
  const [geojsonData, setGeojsonData] = useState<any>(null)
  const [showGeojsonPicker, setShowGeojsonPicker] = useState(false)
  const [linkingGeojson, setLinkingGeojson] = useState(false)
  const [uploadingGeojson, setUploadingGeojson] = useState(false)
  const [activeTab, setActiveTab] = useState<'info' | 'tenencia' | 'riesgo' | 'docs'>('info')
  const fileInputRef = useRef<HTMLInputElement>(null)

  // Sync geojson_data from plot API response
  useEffect(() => {
    if (plot && (plot as any).geojson_data) {
      setGeojsonData((plot as any).geojson_data)
    }
  }, [plot?.id])

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

  if (isLoading) return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <div className="h-8 w-8 rounded-full bg-muted animate-pulse" />
        <div className="h-6 w-48 rounded bg-muted animate-pulse" />
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-4">
          <div className="h-64 rounded-xl bg-muted animate-pulse" />
          <div className="h-32 rounded-xl bg-muted animate-pulse" />
        </div>
        <div className="space-y-4">
          <div className="h-40 rounded-xl bg-muted animate-pulse" />
          <div className="h-40 rounded-xl bg-muted animate-pulse" />
        </div>
      </div>
    </div>
  )
  if (!plot) return <div className="flex justify-center py-20 text-muted-foreground">Parcela no encontrada</div>

  const fullScreening = (plot as any).metadata_?.eudr_full_screening
  const fullSources = (plot as any).metadata_ ? {
    gfw: (plot as any).metadata_?.gfw_screening,
    hansen: (plot as any).metadata_?.hansen_screening,
    jrc: (plot as any).metadata_?.jrc_screening,
  } : null

  async function handleScreenFull() {
    try {
      const result = await screenFull.mutateAsync(plotId!)
      const risk = result.eudr_risk as EudrRiskLevel
      if (risk === 'none' || risk === 'low') {
        toast.success(`Verificacion multi-fuente completada: riesgo ${eudrRiskLabel[risk]}`)
      } else if (risk === 'high') {
        toast.error(`Riesgo ALTO: ${result.risk_reason}`)
      } else {
        toast.error(`Verificacion incompleta: ${result.risk_reason}`)
      }
    } catch (e: any) {
      toast.error(e.message ?? 'Error en screening multi-fuente')
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
              onClick={handleScreenFull}
              disabled={screenFull.isPending}
              className="inline-flex items-center gap-2 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-700 disabled:opacity-50 transition-colors"
            >
              {screenFull.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <ShieldCheck className="h-4 w-4" />}
              Verificar EUDR (3 fuentes)
            </button>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left: Map */}
        <div className="lg:col-span-2 space-y-4">
          <PlotPolygonEditor
            key={geojsonData ? JSON.stringify(geojsonData).slice(0, 40) : 'empty'}
            initialLat={plot.lat ? Number(plot.lat) : null}
            initialLng={plot.lng ? Number(plot.lng) : null}
            initialGeojson={geojsonData}
            declaredAreaHa={plot.plot_area_ha ? Number(plot.plot_area_ha) : null}
            height="400px"
            saving={updatePlot.isPending}
            onSave={async (geojson, _calculatedAreaHa) => {
              try {
                // El backend valida geometria estricta (EUDR Art. 2.28),
                // chequea que el area del poligono concuerde con la declarada,
                // y sobreescribe plot_area_ha con el area real calculada en
                // servidor. Nosotros solo enviamos la geometria.
                await updatePlot.mutateAsync({ geojson_data: geojson } as any)
                setGeojsonData(geojson)
                toast.success('Poligono guardado y area sincronizada')
              } catch (e: any) {
                toast.error(e.message || 'Error al guardar poligono')
              }
            }}
          />

          {/* Compliance flags */}
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
            <ComplianceFlag label="Libre de deforestacion" value={plot.deforestation_free} />
            <ComplianceFlag label="Sin degradacion" value={plot.degradation_free} />
            <ComplianceFlag label="Cumple fecha de corte" value={plot.cutoff_date_compliant} />
            <ComplianceFlag label="Uso legal del suelo" value={plot.legal_land_use} />
          </div>

          {/* Multi-source EUDR screening results */}
          {fullScreening && (
            <div className="space-y-4">
              {/* Overall EUDR risk + consolidated summary */}
              <div className={`rounded-xl border-2 ${eudrRiskBorder[fullScreening.eudr_risk as EudrRiskLevel] || 'border-slate-200'} p-5 space-y-4`}>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <ShieldCheck className="h-5 w-5 text-indigo-600" />
                    <h3 className="text-sm font-bold text-foreground">Screening Multi-Fuente EUDR</h3>
                  </div>
                  <span className={`inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-bold ${eudrRiskColor[fullScreening.eudr_risk as EudrRiskLevel] || eudrRiskColor.medium}`}>
                    <Shield className="h-3 w-3" />
                    Riesgo: {eudrRiskLabel[fullScreening.eudr_risk as EudrRiskLevel] || fullScreening.eudr_risk}
                  </span>
                </div>

                {/* Convergencia multi-fuente (G25) + WDPA (G28) */}
                {typeof fullScreening.convergence_score === 'number' && (
                  <div className="flex flex-wrap items-center gap-3 text-[11px]">
                    {(() => {
                      const score = fullScreening.convergence_score as number
                      const level = (fullScreening.convergence_level as 'low' | 'medium' | 'high') ?? 'medium'
                      const color =
                        level === 'high'
                          ? 'bg-emerald-100 text-emerald-800 border-emerald-300'
                          : level === 'medium'
                          ? 'bg-amber-100 text-amber-800 border-amber-300'
                          : 'bg-red-100 text-red-800 border-red-300'
                      const label =
                        level === 'high' ? 'Alta' : level === 'medium' ? 'Media' : 'Baja'
                      return (
                        <span className={`inline-flex items-center gap-1.5 rounded-full border px-3 py-1 font-bold ${color}`}>
                          Convergencia: {label} ({score}/5)
                        </span>
                      )
                    })()}
                    {fullScreening.inside_protected_area === true && (
                      <span className="inline-flex items-center gap-1.5 rounded-full border border-amber-300 bg-amber-50 px-3 py-1 font-semibold text-amber-800">
                        <AlertTriangle className="h-3 w-3" /> Dentro de area protegida (WDPA)
                      </span>
                    )}
                    {fullScreening.inside_protected_area === false && (
                      <span className="inline-flex items-center gap-1.5 rounded-full border border-emerald-300 bg-emerald-50 px-3 py-1 font-semibold text-emerald-800">
                        <Check className="h-3 w-3" /> Fuera de areas protegidas
                      </span>
                    )}
                  </div>
                )}
                {fullScreening.wdpa_warning && (
                  <div className="rounded-md border border-amber-300 bg-amber-50 px-3 py-2 text-[11px] text-amber-900">
                    {fullScreening.wdpa_warning}
                  </div>
                )}
                {Array.isArray(fullScreening.convergence_details) && fullScreening.convergence_details.length > 0 && (
                  <details className="text-[10px] text-muted-foreground">
                    <summary className="cursor-pointer select-none hover:text-foreground">
                      Detalle de convergencia
                    </summary>
                    <ul className="mt-1 list-disc pl-5 space-y-0.5">
                      {fullScreening.convergence_details.map((d: string, i: number) => (
                        <li key={i}>{d}</li>
                      ))}
                    </ul>
                  </details>
                )}

                {/* Per-source summary lines */}
                <div className="bg-background rounded-lg border p-3 space-y-1.5">
                  {(() => {
                    const gfw = fullSources?.gfw
                    const hansen = fullSources?.hansen
                    const jrc = fullSources?.jrc
                    const lines: { icon: 'check' | 'x' | 'info' | 'warn'; label: string; detail: string }[] = []
                    if (jrc) {
                      lines.push(jrc.was_forest_2020
                        ? { icon: 'info', label: 'JRC 2020', detail: `Zona forestal confirmada — ${(jrc.forest_pixel_count ?? 0).toLocaleString('es-CO')} pixeles (${((jrc.forest_pixel_count ?? 0) * 100 / 10000).toFixed(2)} ha) clasificados como bosque` }
                        : { icon: 'check', label: 'JRC 2020', detail: 'No forestal — EUDR no aplica restricciones de deforestacion a esta parcela' }
                      )
                    }
                    if (gfw) {
                      lines.push(gfw.alerts_count
                        ? { icon: 'x', label: 'GFW Alerts', detail: `${gfw.alerts_count} alertas post-corte (${gfw.high_confidence ?? 0} alta confianza) — sensores GLAD-L, GLAD-S2, RADD` }
                        : { icon: 'check', label: 'GFW Alerts', detail: 'Sin alertas de deforestacion post 31/12/2020' }
                      )
                    }
                    if (hansen) {
                      const ha = ((hansen.loss_pixels ?? 0) * 900 / 10000).toFixed(2)
                      lines.push(hansen.has_loss
                        ? { icon: 'x', label: 'Hansen/UMD', detail: `${(hansen.loss_pixels ?? 0).toLocaleString('es-CO')} pixeles de perdida (${ha} ha) — Landsat 30m` }
                        : { icon: 'check', label: 'Hansen/UMD', detail: 'Sin perdida de cobertura arborea post-2021' }
                      )
                    }
                    if (fullScreening.failed_sources?.length > 0) {
                      lines.push({ icon: 'warn', label: 'Errores', detail: `No se pudieron consultar: ${fullScreening.failed_sources.join(', ')}` })
                    }
                    return lines.map((l, i) => (
                      <div key={i} className="flex items-start gap-2 text-[11px]">
                        {l.icon === 'check' && <Check className="h-3.5 w-3.5 text-emerald-500 mt-0.5 shrink-0" />}
                        {l.icon === 'x' && <X className="h-3.5 w-3.5 text-red-500 mt-0.5 shrink-0" />}
                        {l.icon === 'info' && <Sprout className="h-3.5 w-3.5 text-blue-500 mt-0.5 shrink-0" />}
                        {l.icon === 'warn' && <AlertTriangle className="h-3.5 w-3.5 text-amber-500 mt-0.5 shrink-0" />}
                        <span><strong className="text-foreground">{l.label}:</strong> <span className="text-muted-foreground">{l.detail}</span></span>
                      </div>
                    ))
                  })()}
                </div>

                {/* Risk explanation */}
                <p className="text-xs text-muted-foreground leading-relaxed">{fullScreening.risk_reason}</p>

                {/* Legal reference */}
                <div className="bg-muted/30 rounded-lg px-3 py-2 text-[11px] text-muted-foreground leading-relaxed">
                  <span className="font-semibold text-foreground">Base legal: </span>
                  {fullScreening.eudr_risk === 'high'
                    ? 'Art. 3(1) y Art. 10 del Reglamento (UE) 2023/1115 — los productos no pueden comercializarse en la UE si provienen de tierras deforestadas despues del 31/12/2020. Se requiere due diligence reforzado (Art. 8) y potencialmente verificacion en terreno.'
                    : fullScreening.eudr_risk === 'none'
                    ? 'Art. 2(6) del Reglamento (UE) 2023/1115 — la definicion de "bosque" (FAO: >0.5 ha, dosel >10%, arboles >5m) no aplica a esta parcela segun la linea base JRC 2020. Las restricciones de deforestacion del EUDR no son aplicables.'
                    : fullScreening.eudr_risk === 'low'
                    ? 'Art. 4(1) del Reglamento (UE) 2023/1115 — las tres fuentes satelitales confirman ausencia de deforestacion. El operador cumple con la obligacion de due diligence del Art. 8. Se recomienda documentar este resultado como evidencia de cumplimiento.'
                    : 'Art. 8 del Reglamento (UE) 2023/1115 — verificacion incompleta. Se requiere reintento o verificacion manual complementaria para determinar cumplimiento.'
                  }
                </div>

                <div className="flex items-center gap-4 text-[10px] text-muted-foreground">
                  <span>Verificado: {new Date(fullScreening.checked_at).toLocaleString('es-CO')}</span>
                  {fullScreening.elapsed_seconds && <span>Tiempo de consulta: {fullScreening.elapsed_seconds}s</span>}
                </div>
              </div>

              {/* Per-source cards */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {Object.values((plot as any).metadata_?.eudr_full_screening_sources ?? {}).length > 0
                  ? Object.values((plot as any).metadata_.eudr_full_screening_sources).map((src: any) => (
                      <SourceCard key={src.source} src={src} />
                    ))
                  : /* Reconstruct from individual screening keys */
                    ['gfw_integrated_alerts', 'umd_tree_cover_loss', 'jrc_global_forest_cover'].map(key => {
                      const screeningKey = key === 'gfw_integrated_alerts' ? 'gfw_screening'
                        : key === 'umd_tree_cover_loss' ? 'hansen_screening'
                        : 'jrc_screening'
                      const data = (plot as any).metadata_?.[screeningKey]
                      if (!data) return null
                      // Merge with static source metadata for display
                      const meta: Record<string, Record<string, string>> = {
                        gfw_integrated_alerts: {
                          name: 'GFW Integrated Deforestation Alerts',
                          institution: 'Global Forest Watch — World Resources Institute (WRI)',
                          description: 'Sistema de alertas satelitales casi en tiempo real que combina GLAD-L (Landsat), GLAD-S2 (Sentinel-2) y RADD (radar). Reconocido por la Comision Europea como herramienta de referencia para due diligence bajo el EUDR.',
                          eudr_role: 'Deteccion de deforestacion post-fecha de corte (31 dic 2020). Evalua si hubo alertas de perdida de cobertura forestal en la parcela despues de la fecha limite del EUDR.',
                          reference_url: 'https://www.globalforestwatch.org/blog/data-and-research/integrated-deforestation-alerts/',
                        },
                        umd_tree_cover_loss: {
                          name: 'Hansen Global Forest Change (UMD)',
                          institution: 'University of Maryland — Hansen, Potapov, Moore et al.',
                          description: 'Dataset cientifico peer-reviewed de perdida anual de cobertura arborea a resolucion de 30m. Publicado en Science y actualizado anualmente. Base cientifica del monitoreo global de deforestacion.',
                          eudr_role: 'Verificacion historica de perdida de cobertura arborea ano a ano desde 2001. Perdida en anos >= 2021 indica cambio post-fecha de corte EUDR.',
                          reference_url: 'https://glad.earthengine.app/view/global-forest-change',
                        },
                        jrc_global_forest_cover: {
                          name: 'JRC Global Map of Forest Cover 2020',
                          institution: 'Joint Research Centre — Comision Europea (EU Forest Observatory)',
                          description: 'Mapa oficial de cobertura forestal a 10m creado por el brazo cientifico de la Union Europea, especificamente para soportar la implementacion del EUDR. Cobertura global, no solo bosque tropical.',
                          eudr_role: 'Establece la linea base: era bosque la parcela en 2020? Si NO era bosque, el EUDR no aplica restricciones de deforestacion. Si SI era bosque, se requiere verificar que no hubo perdida posterior.',
                          reference_url: 'https://forest-observatory.ec.europa.eu/',
                        },
                      }
                      const srcResult: SourceResult = {
                        source: key,
                        dataset: key,
                        checked_at: data.checked_at ?? '',
                        error: data.error ?? null,
                        ...meta[key],
                        // GFW
                        ...(key === 'gfw_integrated_alerts' ? {
                          alerts_count: data.alerts_count,
                          high_confidence_alerts: data.high_confidence,
                          deforestation_free: data.alerts_count === 0,
                        } : {}),
                        // Hansen
                        ...(key === 'umd_tree_cover_loss' ? {
                          has_loss: data.has_loss,
                          loss_pixels: data.loss_pixels,
                          loss_by_year: data.loss_by_year,
                          cutoff_year: 2021,
                        } : {}),
                        // JRC
                        ...(key === 'jrc_global_forest_cover' ? {
                          was_forest_2020: data.was_forest_2020,
                          forest_pixel_count: data.forest_pixel_count,
                        } : {}),
                      } as SourceResult
                      return <SourceCard key={key} src={srcResult} />
                    })
                }
              </div>

              {/* Blockchain anchor status */}
              {fullScreening.anchor && (
                <div className={`rounded-xl border p-4 ${
                  fullScreening.anchor.anchor_status === 'anchored'
                    ? 'border-violet-200 bg-violet-50'
                    : fullScreening.anchor.anchor_status === 'pending'
                    ? 'border-amber-200 bg-amber-50'
                    : 'border-red-200 bg-red-50'
                }`}>
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <Shield className="h-4 w-4 text-violet-600" />
                      <h4 className="text-sm font-bold">Inmutabilidad Blockchain (Solana)</h4>
                    </div>
                    <span className={`inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-semibold ${
                      fullScreening.anchor.anchor_status === 'anchored'
                        ? 'bg-violet-100 text-violet-700'
                        : fullScreening.anchor.anchor_status === 'pending'
                        ? 'bg-amber-100 text-amber-700'
                        : 'bg-red-100 text-red-700'
                    }`}>
                      {fullScreening.anchor.anchor_status === 'anchored' ? 'Anclado' :
                       fullScreening.anchor.anchor_status === 'pending' ? 'Pendiente' : 'Error'}
                    </span>
                  </div>
                  <div className="space-y-1.5 text-xs">
                    <div className="flex items-center gap-2">
                      <span className="text-muted-foreground">Hash de evidencia:</span>
                      <code className="bg-black/5 px-1.5 py-0.5 rounded font-mono text-[10px]">
                        {fullScreening.anchor.compliance_hash}
                      </code>
                    </div>
                    {fullScreening.anchor.solana_tx_sig && (
                      <div className="flex items-center gap-2">
                        <span className="text-muted-foreground">Transaccion Solana:</span>
                        <a
                          href={`https://explorer.solana.com/tx/${fullScreening.anchor.solana_tx_sig}?cluster=devnet`}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="inline-flex items-center gap-1 text-primary hover:underline font-mono text-[10px]"
                        >
                          {fullScreening.anchor.solana_tx_sig.slice(0, 20)}...
                          <ExternalLink className="h-3 w-3" />
                        </a>
                      </div>
                    )}
                    {fullScreening.anchor.anchored_at && (
                      <div className="flex items-center gap-2">
                        <span className="text-muted-foreground">Anclado:</span>
                        <span>{new Date(fullScreening.anchor.anchored_at).toLocaleString('es-CO')}</span>
                      </div>
                    )}
                    <p className="text-muted-foreground mt-1 leading-relaxed">
                      El hash SHA-256 de esta verificacion fue registrado en la blockchain de Solana.
                      Cualquier auditor puede verificar que los resultados no fueron alterados
                      comparando el hash almacenado con los datos originales.
                      Retencion minima: 5 anos (EUDR Art. 4.2).
                    </p>
                  </div>
                </div>
              )}

              {/* Technology disclaimer */}
              <div className="rounded-lg bg-indigo-50 border border-indigo-200 p-3">
                <p className="text-xs text-indigo-700 leading-relaxed">
                  <strong>Tecnologia de verificacion:</strong> Este screening utiliza tres fuentes
                  satelitales reconocidas por la Union Europea y la comunidad cientifica internacional
                  para el cumplimiento del Reglamento EUDR (EU 2023/1115): Global Forest Watch (WRI),
                  Hansen/UMD Global Forest Change (University of Maryland) y JRC Global Forest Cover
                  (Comision Europea). Los datos se consultan en tiempo real via la API de GFW Data.
                  {fullScreening.anchor?.compliance_hash && (
                    <> El hash criptografico (SHA-256) de los resultados se ancla en Solana para
                    garantizar la inmutabilidad de la evidencia por el periodo de retencion requerido.</>
                  )}
                </p>
              </div>
            </div>
          )}

          {!fullScreening && (
            <div className="rounded-xl border border-amber-200 bg-amber-50 p-4 flex items-start gap-3">
              <AlertTriangle className="h-5 w-5 text-amber-500 mt-0.5 shrink-0" />
              <div>
                <p className="text-sm font-medium text-amber-800">Sin verificacion satelital</p>
                <p className="text-xs text-amber-600 mt-0.5">
                  Usa "Verificar EUDR (3 fuentes)" para ejecutar el screening
                  multi-fuente con GFW, Hansen/UMD y JRC.
                </p>
              </div>
            </div>
          )}
        </div>

        {/* Right: Details — organized in tabs */}
        <div>
          {/* Tab buttons */}
          <div className="flex gap-1 mb-4 bg-muted rounded-lg p-1">
            {([
              { key: 'info', label: 'Informacion' },
              { key: 'tenencia', label: 'Tenencia y Legal' },
              { key: 'riesgo', label: 'Riesgo' },
              { key: 'docs', label: 'Documentos' },
            ] as const).map(tab => (
              <button
                key={tab.key}
                onClick={() => setActiveTab(tab.key)}
                className={`flex-1 rounded-md px-3 py-1.5 text-xs font-medium transition-all ${
                  activeTab === tab.key
                    ? 'bg-background text-foreground shadow-sm'
                    : 'text-muted-foreground hover:text-foreground'
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>

          {/* Tab: Informacion */}
          {activeTab === 'info' && (
            <div className="space-y-4">
              <div className="bg-card rounded-xl border border-border p-5 space-y-4">
                <h3 className="text-sm font-bold text-foreground uppercase tracking-wide">Informacion de la Parcela</h3>
                <dl className="space-y-3">
                  <InfoField label="Codigo" value={plot.plot_code} />
                  <InfoField label="Area" value={plot.plot_area_ha ? `${Number(plot.plot_area_ha).toFixed(2)} ha` : null} />
                  <InfoField label="Tipo geolocalizacion" value={plot.geolocation_type === 'point' ? 'Punto' : 'Poligono'} />
                  <InfoField label="Latitud" value={plot.lat ? `${Number(plot.lat).toFixed(6)}` : null} />
                  <InfoField label="Longitud" value={plot.lng ? `${Number(plot.lng).toFixed(6)}` : null} />
                  <InfoField label="Pais" value={plot.country_code} />
                  <InfoField label={plot.country_code === 'CO' ? 'Departamento' : 'Region'} value={plot.region} />
                  <InfoField label="Municipio" value={plot.municipality} />
                  {plot.vereda && <InfoField label="Vereda" value={plot.vereda} />}
                  {plot.frontera_agricola_status && (
                    <InfoField label="Frontera agricola" value={
                      plot.frontera_agricola_status === 'dentro_no_condicionada' ? 'Dentro — sin condicionamiento' :
                      plot.frontera_agricola_status === 'dentro_condicionada' ? 'Dentro — condicionada' :
                      plot.frontera_agricola_status === 'restriccion_deforestacion' ? 'Restriccion — cero deforestacion' :
                      plot.frontera_agricola_status === 'restriccion_legal' ? 'Restriccion — legal' :
                      plot.frontera_agricola_status === 'restriccion_tecnica' ? 'Restriccion — tecnica' :
                      plot.frontera_agricola_status === 'fuera' ? 'Fuera de frontera agricola' :
                      plot.frontera_agricola_status
                    } />
                  )}
                </dl>
              </div>

              <div className="bg-card rounded-xl border border-border p-5 space-y-3">
                <h3 className="text-sm font-bold text-foreground uppercase tracking-wide">Cultivo y Produccion</h3>
                <dl className="space-y-3">
                  <InfoField label="Tipo de cultivo" value={plot.crop_type} />
                  <InfoField label="Nombre cientifico" value={plot.scientific_name} />
                  <InfoField label="Fecha de establecimiento" value={plot.establishment_date} />
                  <InfoField label="Fecha de renovacion" value={plot.renovation_date} />
                  <InfoField label="Tipo de renovacion" value={plot.renovation_type} />
                  <InfoField label="Ultima cosecha" value={plot.last_harvest_date} />
                </dl>
              </div>

              <CaptureMetadataSection plot={plot} />

              <div className="bg-card rounded-xl border border-border p-5 space-y-3">
                <h3 className="text-sm font-bold text-foreground uppercase tracking-wide">Poligono GeoJSON</h3>
                {((plot as any).geojson_data || geojsonData) ? (
                  <div className="space-y-2">
                    <p className="text-xs text-emerald-600 font-medium flex items-center gap-1">
                      <Check className="h-3 w-3" /> Poligono cargado
                    </p>
                    {plot.geojson_hash && (
                      <p className="text-xs text-muted-foreground font-mono">SHA: {plot.geojson_hash.slice(0, 16)}...</p>
                    )}
                    <button onClick={() => setShowGeojsonPicker(true)} className="text-xs text-muted-foreground hover:text-primary hover:underline">
                      Reemplazar desde Media
                    </button>
                  </div>
                ) : plot.geojson_arweave_url ? (
                  <div className="space-y-2">
                    <p className="text-xs text-emerald-600 font-medium">Poligono cargado (Media)</p>
                    <button onClick={() => setShowGeojsonPicker(true)} className="text-xs text-muted-foreground hover:text-primary hover:underline">
                      Cambiar archivo
                    </button>
                  </div>
                ) : (
                  <div className="space-y-2">
                    {Number(plot.plot_area_ha) > 4 && (
                      <div className="rounded-lg border border-red-200 bg-red-50 p-2 text-xs text-red-700 flex items-start gap-1.5">
                        <AlertTriangle className="h-3.5 w-3.5 mt-0.5 shrink-0" />
                        EUDR Art. 2(28): parcelas mayores a 4 ha requieren poligono completo.
                      </div>
                    )}
                    <button onClick={() => setShowGeojsonPicker(true)} disabled={linkingGeojson}
                      className="w-full flex items-center justify-center gap-2 rounded-lg border border-dashed border-slate-300 bg-muted px-4 py-3 text-sm text-muted-foreground hover:border-primary hover:bg-primary/5 transition-colors">
                      <FolderOpen className="h-4 w-4" />
                      {linkingGeojson ? 'Vinculando...' : 'Seleccionar desde Media'}
                    </button>
                  </div>
                )}
              </div>

              {/* Audit trail basico — Art. 9(4) */}
              <div className="bg-card rounded-xl border border-border p-5 space-y-3">
                <h3 className="text-sm font-bold text-foreground uppercase tracking-wide">Registro de cambios</h3>
                <dl className="space-y-3">
                  <InfoField label="Creada" value={plot.created_at ? new Date(plot.created_at).toLocaleString('es-CO') : null} />
                  <InfoField label="Ultima modificacion" value={plot.updated_at ? new Date(plot.updated_at).toLocaleString('es-CO') : null} />
                </dl>
                <p className="text-[10px] text-muted-foreground">
                  Art. 9(4) EUDR — el operador debe revisar y actualizar la DDS.
                  Retencion obligatoria: 5 anos desde la fecha de la declaracion.
                </p>
              </div>
            </div>
          )}

          {/* Tab: Tenencia y Legal */}
          {activeTab === 'tenencia' && (
            <div className="space-y-4">
              <TenureSection plot={plot} onSave={async (updates) => {
                try {
                  await updatePlot.mutateAsync(updates as any)
                  toast.success('Datos de tenencia guardados')
                } catch (e: any) {
                  toast.error(e.message || 'Error al guardar tenencia')
                }
              }} saving={updatePlot.isPending} />

              <LegalComplianceSection plotId={plot.id} />

              {plot.satellite_report_url && (
                <div className="bg-card rounded-xl border border-border p-5 space-y-3">
                  <h3 className="text-sm font-bold text-foreground uppercase tracking-wide">Reporte Satelital</h3>
                  <a href={plot.satellite_report_url} target="_blank" rel="noopener noreferrer"
                    className="text-sm text-primary hover:underline">Ver reporte</a>
                  {plot.satellite_verified_at && (
                    <p className="text-xs text-muted-foreground">Verificado: {new Date(plot.satellite_verified_at).toLocaleString('es-CO')}</p>
                  )}
                </div>
              )}
            </div>
          )}

          {/* Tab: Riesgo */}
          {activeTab === 'riesgo' && (
            <div className="space-y-4">
              <div className="bg-card rounded-xl border border-border p-5 space-y-3">
                <h3 className="text-sm font-bold text-foreground uppercase tracking-wide">Nivel de Riesgo EUDR</h3>
                {fullScreening ? (
                  <>
                    <span className={`inline-flex items-center px-3 py-1.5 rounded-full text-sm font-bold ${eudrRiskColor[fullScreening.eudr_risk as EudrRiskLevel] || eudrRiskColor.medium}`}>
                      {eudrRiskLabel[fullScreening.eudr_risk as EudrRiskLevel] || fullScreening.eudr_risk}
                    </span>
                    {/* Alerta screening obsoleto (>6 meses) */}
                    {(() => {
                      const checkedAt = new Date(fullScreening.checked_at)
                      const monthsAgo = (Date.now() - checkedAt.getTime()) / (1000 * 60 * 60 * 24 * 30)
                      if (monthsAgo >= 6) return (
                        <div className="rounded-lg border border-red-200 bg-red-50 p-3 flex items-start gap-2">
                          <AlertTriangle className="h-4 w-4 text-red-500 mt-0.5 shrink-0" />
                          <div>
                            <p className="text-xs font-semibold text-red-800">Screening vencido — {Math.floor(monthsAgo)} meses</p>
                            <p className="text-[11px] text-red-700 mt-0.5">
                              Art. 10 EUDR exige que la verificacion sea vigente al momento de cada DDS.
                              Re-ejecuta "Verificar EUDR (3 fuentes)" antes del proximo envio.
                            </p>
                          </div>
                        </div>
                      )
                      if (monthsAgo >= 3) return (
                        <div className="rounded-lg border border-amber-200 bg-amber-50 p-3 flex items-start gap-2">
                          <AlertTriangle className="h-4 w-4 text-amber-500 mt-0.5 shrink-0" />
                          <div>
                            <p className="text-xs font-semibold text-amber-800">Screening proximo a vencer — {Math.floor(monthsAgo)} meses</p>
                            <p className="text-[11px] text-amber-700 mt-0.5">
                              Se recomienda re-verificar antes de los 6 meses para mantener vigencia.
                            </p>
                          </div>
                        </div>
                      )
                      return (
                        <p className="text-[11px] text-muted-foreground">
                          Verificado: {checkedAt.toLocaleString('es-CO')} ({Math.floor(monthsAgo)} {Math.floor(monthsAgo) === 1 ? 'mes' : 'meses'})
                        </p>
                      )
                    })()}
                  </>
                ) : (
                  <span className="inline-flex items-center px-3 py-1.5 rounded-full text-sm font-bold bg-slate-100 text-slate-600">
                    Sin verificar
                  </span>
                )}
              </div>
              {/* Art. 13/29 — DDS simplificado para paises low-risk */}
              {fullScreening && (fullScreening.eudr_risk === 'none' || fullScreening.eudr_risk === 'low') && (
                <div className="rounded-lg border border-emerald-200 bg-emerald-50 p-3 flex items-start gap-2">
                  <ShieldCheck className="h-4 w-4 text-emerald-600 mt-0.5 shrink-0" />
                  <div>
                    <p className="text-xs font-semibold text-emerald-800">Due diligence simplificado aplicable</p>
                    <p className="text-[11px] text-emerald-700 mt-0.5">
                      Art. 13 / Art. 29 EUDR — para commodities de paises clasificados como riesgo bajo,
                      el operador puede aplicar due diligence simplificado: solo recopilacion de informacion
                      (Art. 9) sin evaluacion de riesgo completa (Art. 10) ni mitigacion (Art. 11).
                    </p>
                  </div>
                </div>
              )}

              {/* Art. 2(7) — Degradacion forestal (no implementado aun) */}
              <div className="rounded-lg border border-blue-200 bg-blue-50 p-3 flex items-start gap-2">
                <AlertTriangle className="h-4 w-4 text-blue-500 mt-0.5 shrink-0" />
                <div>
                  <p className="text-xs font-semibold text-blue-800">Degradacion forestal — pendiente</p>
                  <p className="text-[11px] text-blue-700 mt-0.5">
                    Art. 2(7) EUDR distingue deforestacion de degradacion (cambios estructurales al bosque
                    sin eliminacion total). La verificacion actual cubre deforestacion pero no degradacion.
                    Fuente pendiente: JRC Tropical Moist Forest (TMF).
                  </p>
                </div>
              </div>

              <CountryRiskSection countryCode={plot.country_code} />
              <RiskDecisionSection plotId={plot.id} />
            </div>
          )}

          {/* Tab: Documentos */}
          {activeTab === 'docs' && (
            <div className="space-y-4">
              <EudrDocChecklist
                riskLevel={fullScreening?.eudr_risk as EudrRiskLevel | undefined}
                indigenousFlag={plot.indigenous_territory_flag}
                countryCode={plot.country_code}
                documents={plotDocs}
                onAttach={async (data) => { await attachDoc.mutateAsync(data) }}
                onDetach={async (docId) => { await detachDoc.mutateAsync(docId) }}
                isPending={detachDoc.isPending}
              />
            </div>
          )}

          {/* GeoJSON MediaPicker (modal) */}
          <MediaPickerModal
            open={showGeojsonPicker}
            onClose={() => setShowGeojsonPicker(false)}
            onSelect={async (mediaFileId, _docType, _desc) => {
              setLinkingGeojson(true)
              try {
                const mediaFile = await mediaApi.get(mediaFileId)
                const fullUrl = mediaFileUrl(mediaFile.url)
                const resp = await fetch(fullUrl)
                const text = await resp.text()
                try { setGeojsonData(JSON.parse(text)) } catch { /* not valid JSON */ }
                const encoder = new TextEncoder()
                const data = encoder.encode(text)
                const hashBuffer = await crypto.subtle.digest('SHA-256', data)
                const hashArray = Array.from(new Uint8Array(hashBuffer))
                const hash = hashArray.map(b => b.toString(16).padStart(2, '0')).join('')
                await updatePlot.mutateAsync({ geojson_arweave_url: mediaFile.url, geojson_hash: hash, geolocation_type: 'polygon' })
                toast.success('Poligono GeoJSON vinculado desde media')
                setShowGeojsonPicker(false)
              } catch (err: any) {
                toast.error(err.message ?? 'Error al vincular GeoJSON')
              } finally { setLinkingGeojson(false) }
            }}
          />
        </div>
      </div>
    </div>
  )
}


// ─── Capture metadata section ───────────────────────────────────────────────
const CAPTURE_METHOD_LABELS: Record<string, string> = {
  handheld_gps: 'GPS de mano / smartphone',
  rtk_gps: 'GPS RTK (centimetrico)',
  drone: 'Dron / fotogrametria',
  manual_map: 'Trazado manual sobre imagen satelital',
  cadastral: 'Importado de catastro',
  survey: 'Levantamiento topografico',
  unknown: 'Desconocido',
}
const PRODUCER_SCALE_LABELS: Record<string, string> = {
  smallholder: 'Pequeno productor (<4 ha)',
  medium: 'Mediano (4-50 ha)',
  industrial: 'Industrial (>50 ha)',
}

function CaptureMetadataSection({ plot }: { plot: any }) {
  const method = plot.capture_method as string | null
  const scale = plot.producer_scale as string | null
  const accuracy = plot.gps_accuracy_m != null ? Number(plot.gps_accuracy_m) : null
  const device = plot.capture_device as string | null
  const captureDate = plot.capture_date as string | null

  const hasAny = method || scale || accuracy != null || device || captureDate
  const accuracyWarn = accuracy != null && accuracy > 10
  return (
    <div className="bg-card rounded-xl border border-border p-5 space-y-3">
      <h3 className="text-sm font-bold text-foreground uppercase tracking-wide">
        Metodo de Captura
      </h3>
      <p className="text-xs text-muted-foreground">
        EFI / MITECO: un poligono sin metadata de captura es indefendible ante
        un inspector EUDR.
      </p>
      {!hasAny ? (
        <div className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-700">
          Sin metadata de captura. Editalo desde el boton "Editar" de la parcela
          para agregar metodo, dispositivo y exactitud GPS.
        </div>
      ) : (
        <dl className="space-y-2 text-xs">
          <div className="flex justify-between gap-4">
            <dt className="text-muted-foreground">Metodo</dt>
            <dd className="font-medium text-foreground text-right">
              {method ? CAPTURE_METHOD_LABELS[method] ?? method : '—'}
            </dd>
          </div>
          <div className="flex justify-between gap-4">
            <dt className="text-muted-foreground">Escala</dt>
            <dd className="font-medium text-foreground text-right">
              {scale ? PRODUCER_SCALE_LABELS[scale] ?? scale : '—'}
            </dd>
          </div>
          <div className="flex justify-between gap-4">
            <dt className="text-muted-foreground">Exactitud GPS</dt>
            <dd className={`font-medium text-right ${accuracyWarn ? 'text-amber-700' : 'text-foreground'}`}>
              {accuracy != null ? `${accuracy.toFixed(2)} m` : '—'}
              {accuracyWarn && <span className="ml-1 text-[10px]">(alta)</span>}
            </dd>
          </div>
          <div className="flex justify-between gap-4">
            <dt className="text-muted-foreground">Dispositivo</dt>
            <dd className="font-medium text-foreground text-right">{device ?? '—'}</dd>
          </div>
          <div className="flex justify-between gap-4">
            <dt className="text-muted-foreground">Fecha captura</dt>
            <dd className="font-medium text-foreground text-right">{captureDate ?? '—'}</dd>
          </div>
        </dl>
      )}
    </div>
  )
}


// ─── Country risk section ───────────────────────────────────────────────────
const COUNTRY_RISK_COLORS: Record<string, string> = {
  negligible: 'bg-emerald-100 text-emerald-800 border-emerald-300',
  low: 'bg-lime-100 text-lime-800 border-lime-300',
  standard: 'bg-amber-100 text-amber-800 border-amber-300',
  high: 'bg-orange-100 text-orange-800 border-orange-300',
  critical: 'bg-red-100 text-red-800 border-red-300',
}

const COUNTRY_RISK_LABELS: Record<string, string> = {
  negligible: 'Negligible',
  low: 'Bajo',
  standard: 'Estandar',
  high: 'Alto',
  critical: 'Critico',
}

const DEF_PREV_LABELS: Record<string, string> = {
  very_low: 'Muy baja',
  low: 'Baja',
  medium: 'Media',
  high: 'Alta',
  very_high: 'Muy alta',
}

function CountryRiskSection({ countryCode }: { countryCode: string }) {
  const { data: bench, isLoading, error } = useCountryRisk(countryCode)
  return (
    <div className="bg-card rounded-xl border border-border p-5 space-y-3">
      <h3 className="text-sm font-bold text-foreground uppercase tracking-wide">
        Riesgo de Pais ({countryCode})
      </h3>
      {isLoading ? (
        <div className="text-xs text-muted-foreground">Cargando benchmark...</div>
      ) : error || !bench ? (
        <div className="text-xs text-muted-foreground">
          No hay benchmark disponible para este pais.
        </div>
      ) : (
        <>
          <div className="flex items-center gap-2">
            <span className={`inline-flex items-center rounded-full border px-3 py-1 text-xs font-bold ${COUNTRY_RISK_COLORS[bench.risk_level] ?? ''}`}>
              {COUNTRY_RISK_LABELS[bench.risk_level] ?? bench.risk_level}
            </span>
            {bench.conflict_flag && (
              <span className="inline-flex items-center rounded-full border border-red-300 bg-red-50 px-2 py-0.5 text-[10px] font-bold text-red-700">
                Conflicto activo
              </span>
            )}
            {bench.indigenous_risk_flag && (
              <span className="inline-flex items-center rounded-full border border-purple-300 bg-purple-50 px-2 py-0.5 text-[10px] font-bold text-purple-700">
                Riesgo indigena
              </span>
            )}
          </div>
          <dl className="grid grid-cols-2 gap-2 text-xs">
            {bench.cpi_score != null && (
              <>
                <dt className="text-muted-foreground">CPI Transparency Intl.</dt>
                <dd className="text-right font-semibold text-foreground">
                  {bench.cpi_score}/100 {bench.cpi_rank ? `(rank ${bench.cpi_rank})` : ''}
                </dd>
              </>
            )}
            {bench.deforestation_prevalence && (
              <>
                <dt className="text-muted-foreground">Prevalencia deforestacion</dt>
                <dd className="text-right font-semibold text-foreground">
                  {DEF_PREV_LABELS[bench.deforestation_prevalence] ?? bench.deforestation_prevalence}
                </dd>
              </>
            )}
            <dt className="text-muted-foreground">Actualizado</dt>
            <dd className="text-right font-medium text-foreground">{bench.as_of_date}</dd>
          </dl>
          {bench.notes && (
            <p className="text-[11px] text-muted-foreground leading-snug">{bench.notes}</p>
          )}
          <p className="text-[10px] text-muted-foreground italic">Fuente: {bench.source}</p>
        </>
      )}
    </div>
  )
}

// ─── Risk decision tree section ─────────────────────────────────────────────
const FINAL_RISK_COLORS: Record<string, string> = {
  low: 'bg-emerald-100 text-emerald-800 border-emerald-400',
  medium: 'bg-amber-100 text-amber-800 border-amber-400',
  high: 'bg-orange-100 text-orange-800 border-orange-400',
  critical: 'bg-red-100 text-red-800 border-red-400',
  requires_field_visit: 'bg-blue-100 text-blue-800 border-blue-400',
}

const FINAL_RISK_LABELS: Record<string, string> = {
  low: 'BAJO',
  medium: 'MEDIO',
  high: 'ALTO',
  critical: 'CRITICO',
  requires_field_visit: 'REQUIERE VISITA EN TERRENO',
}

function RiskDecisionSection({ plotId }: { plotId: string }) {
  const decision = useRiskDecision()
  const [result, setResult] = useState<RiskDecisionResponse | null>(null)

  async function run() {
    try {
      const res = await decision.mutateAsync(plotId)
      setResult(res)
    } catch (e: any) {
      console.error(e)
    }
  }

  return (
    <div className="bg-card rounded-xl border border-border p-5 space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-sm font-bold text-foreground uppercase tracking-wide">
            Decision de Riesgo Compuesta
          </h3>
          <p className="text-xs text-muted-foreground">
            Composicion final: screening + legalidad + pais + escala + tenencia.
          </p>
        </div>
        <button
          onClick={run}
          disabled={decision.isPending}
          className="inline-flex items-center gap-1.5 rounded-lg bg-indigo-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-indigo-700 disabled:opacity-50"
        >
          {decision.isPending ? 'Calculando...' : 'Calcular decision'}
        </button>
      </div>

      {result && (
        <div className="space-y-3">
          <div className="flex items-center gap-3">
            <span className={`inline-flex items-center rounded-full border-2 px-4 py-1.5 text-sm font-bold ${FINAL_RISK_COLORS[result.final_risk] ?? ''}`}>
              {FINAL_RISK_LABELS[result.final_risk] ?? result.final_risk}
            </span>
          </div>

          <div className="rounded-md bg-muted/40 border border-border px-3 py-2 text-xs text-foreground">
            <strong>Accion recomendada: </strong>
            {result.recommended_action}
          </div>

          {result.drivers.length > 0 && (
            <div>
              <div className="text-[11px] font-semibold text-red-700 uppercase tracking-wide mb-1">
                Drivers bloqueantes
              </div>
              <ul className="list-disc pl-5 space-y-0.5 text-xs text-red-800">
                {result.drivers.map((d, i) => <li key={i}>{d}</li>)}
              </ul>
            </div>
          )}

          {result.warnings.length > 0 && (
            <div>
              <div className="text-[11px] font-semibold text-amber-700 uppercase tracking-wide mb-1">
                Advertencias
              </div>
              <ul className="list-disc pl-5 space-y-0.5 text-xs text-amber-800">
                {result.warnings.map((w, i) => <li key={i}>{w}</li>)}
              </ul>
            </div>
          )}

          {result.positives.length > 0 && (
            <div>
              <div className="text-[11px] font-semibold text-emerald-700 uppercase tracking-wide mb-1">
                Positivos
              </div>
              <ul className="list-disc pl-5 space-y-0.5 text-xs text-emerald-800">
                {result.positives.map((p, i) => <li key={i}>{p}</li>)}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

// ─── Legal compliance checklist section ────────────────────────────────────
const AMBITO_LABELS: Record<string, string> = {
  land_use_rights: 'Uso de suelo',
  environmental_protection: 'Medio ambiente',
  labor_rights: 'Laboral',
  human_rights: 'Derechos humanos',
  third_party_rights_fpic: 'Terceros / FPIC',
  fiscal_customs_anticorruption: 'Fiscal / aduanero',
}

const STATUS_LABELS: Record<string, string> = {
  satisfied: 'Cumple',
  missing: 'Falta',
  na: 'No aplica',
  pending: 'Pendiente',
}

function LegalComplianceSection({ plotId }: { plotId: string }) {
  const { data: summary, isLoading, error } = usePlotLegalStatus(plotId)
  const update = useUpdatePlotLegalRequirement(plotId)

  if (isLoading) {
    return (
      <div className="bg-card rounded-xl border border-border p-5">
        <div className="text-sm text-muted-foreground">Cargando checklist legal...</div>
      </div>
    )
  }
  if (error || !summary) {
    return (
      <div className="bg-card rounded-xl border border-border p-5">
        <h3 className="text-sm font-bold text-foreground uppercase tracking-wide mb-2">
          Legalidad EUDR
        </h3>
        <div className="text-xs text-muted-foreground">
          No se pudo cargar el catalogo legal.
        </div>
      </div>
    )
  }
  if (!summary.catalog_id || summary.items.length === 0) {
    return (
      <div className="bg-card rounded-xl border border-border p-5">
        <h3 className="text-sm font-bold text-foreground uppercase tracking-wide mb-2">
          Legalidad EUDR
        </h3>
        <div className="text-xs text-muted-foreground">
          No hay catalogo legal para ({(summary as any).country_code ?? 'este pais'} / {(summary as any).commodity ?? 'este commodity'}).
          Defini el tipo de cultivo en la parcela para activar el checklist.
        </div>
      </div>
    )
  }

  // Group items by ambito
  const groups: Record<string, typeof summary.items> = {}
  for (const it of summary.items) {
    const key = it.requirement.ambito
    if (!groups[key]) groups[key] = []
    groups[key].push(it)
  }

  const pct = summary.applicable_requirements > 0
    ? Math.round((summary.satisfied / summary.applicable_requirements) * 100)
    : 0

  return (
    <div className="bg-card rounded-xl border border-border p-5 space-y-4">
      <div>
        <h3 className="text-sm font-bold text-foreground uppercase tracking-wide">
          Legalidad EUDR
        </h3>
        <p className="text-xs text-muted-foreground">
          Art. 9.1 — 6 ambitos legales. Los requisitos aplicables dependen de la
          escala del productor.
        </p>
      </div>

      {/* Summary bar */}
      <div className="space-y-2">
        <div className="flex items-center justify-between text-xs">
          <span className="text-muted-foreground">
            {summary.satisfied} / {summary.applicable_requirements} cumplidos
            {summary.blocking_missing > 0 && (
              <span className="ml-2 text-red-700 font-semibold">
                · {summary.blocking_missing} bloqueantes faltando
              </span>
            )}
          </span>
          <span className="font-semibold text-foreground">{pct}%</span>
        </div>
        <div className="h-2 w-full rounded-full bg-muted overflow-hidden">
          <div
            className={`h-full transition-all ${
              summary.blocking_missing > 0 ? 'bg-red-500' : pct >= 80 ? 'bg-emerald-500' : 'bg-amber-500'
            }`}
            style={{ width: `${pct}%` }}
          />
        </div>
      </div>

      {/* Grouped requirements */}
      <div className="space-y-4">
        {Object.entries(groups).map(([ambito, items]) => (
          <div key={ambito} className="space-y-2">
            <h4 className="text-[11px] font-bold uppercase tracking-wide text-muted-foreground">
              {AMBITO_LABELS[ambito] ?? ambito}
            </h4>
            {items.map((it) => {
              const status = it.compliance?.status ?? 'pending'
              const applies =
                it.requirement.applies_to_scale === 'all' ||
                (summary.producer_scale &&
                  (it.requirement.applies_to_scale === summary.producer_scale ||
                    (it.requirement.applies_to_scale === 'medium_or_industrial' &&
                      (summary.producer_scale === 'medium' ||
                        summary.producer_scale === 'industrial'))))
              const statusColor =
                status === 'satisfied'
                  ? 'bg-emerald-100 text-emerald-800 border-emerald-300'
                  : status === 'missing'
                  ? 'bg-red-100 text-red-800 border-red-300'
                  : status === 'na'
                  ? 'bg-slate-100 text-slate-700 border-slate-300'
                  : 'bg-amber-100 text-amber-800 border-amber-300'
              return (
                <div
                  key={it.requirement.id}
                  className={`rounded-lg border px-3 py-2 space-y-1 ${
                    !applies ? 'opacity-50' : ''
                  }`}
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex-1">
                      <div className="flex items-center gap-1.5">
                        <span className="text-[10px] font-mono text-muted-foreground">
                          {it.requirement.code}
                        </span>
                        {it.requirement.is_blocking && (
                          <span className="inline-flex rounded-full bg-red-50 px-1.5 py-[1px] text-[9px] font-semibold text-red-700">
                            BLOQUEANTE
                          </span>
                        )}
                      </div>
                      <div className="text-xs font-semibold text-foreground leading-snug">
                        {it.requirement.title}
                      </div>
                      {it.requirement.description && (
                        <p className="mt-1 text-[11px] text-muted-foreground leading-snug">
                          {it.requirement.description}
                        </p>
                      )}
                      {it.requirement.legal_reference && (
                        <p className="mt-0.5 text-[10px] text-muted-foreground italic">
                          {it.requirement.legal_reference}
                        </p>
                      )}
                    </div>
                    <select
                      disabled={!applies || update.isPending}
                      value={status}
                      onChange={(e) =>
                        update.mutate({
                          requirementId: it.requirement.id,
                          body: {
                            status: e.target.value as any,
                            evidence_media_id: it.compliance?.evidence_media_id ?? null,
                            evidence_notes: it.compliance?.evidence_notes ?? null,
                          },
                        })
                      }
                      className={`text-[10px] font-bold rounded-full border px-2 py-1 ${statusColor}`}
                    >
                      <option value="pending">{STATUS_LABELS.pending}</option>
                      <option value="satisfied">{STATUS_LABELS.satisfied}</option>
                      <option value="missing">{STATUS_LABELS.missing}</option>
                      <option value="na">{STATUS_LABELS.na}</option>
                    </select>
                  </div>
                </div>
              )
            })}
          </div>
        ))}
      </div>
    </div>
  )
}

// ─── EUDR Document Checklist — Art. 9, 10, 12 ────────────────────────────────

type DocReq = {
  type: string
  label: string
  article: string
  minRisk: 'any' | 'standard' | 'high'
  indigenous?: boolean
  countries?: string[] // si se especifica, solo aplica para estos country_code
}

// Solo documentos FIJOS a la parcela (se adjuntan una vez).
// Docs por envío (DDS, declaracion proveedor, screening satelital,
// transporte) van en el ComplianceRecord, no aquí.
const EUDR_REQUIRED_DOCS: DocReq[] = [
  // ── Siempre requeridos — tenencia y georreferenciacion ──
  { type: 'land_title',            label: 'Titulo de propiedad / certificado de tradicion', article: 'Art. 9(1)(d), 10(h)', minRisk: 'any' },
  { type: 'cadastral_certificate', label: 'Certificado catastral (IGAC/SNR)',               article: 'Art. 2(28)',           minRisk: 'any' },
  { type: 'geojson_boundary',      label: 'Poligono GeoJSON del predio',                    article: 'Art. 2(28)',           minRisk: 'any' },
  { type: 'zoning_certificate',    label: 'Certificado de uso de suelo / zonificacion',      article: 'Anexo II — Uso suelo', minRisk: 'any' },

  // ── Riesgo standard — permisos y laboral ──
  { type: 'environmental_license', label: 'Licencia ambiental / plan de manejo',             article: 'Art. 10(2)(b), Anexo II', minRisk: 'standard' },
  { type: 'labor_contract',        label: 'Contrato laboral / declaracion empleo',           article: 'Art. 10(2)(i), Anexo II', minRisk: 'standard' },
  { type: 'child_labor_affidavit', label: 'Declaracion ausencia trabajo infantil',           article: 'Anexo II — Laboral',      minRisk: 'standard' },
  { type: 'protected_area_check',  label: 'Cross-check areas protegidas (WDPA)',             article: 'Art. 10(2)(b)',           minRisk: 'standard' },

  // ── Riesgo alto — due diligence reforzado ──
  { type: 'eia_report',              label: 'Estudio de impacto ambiental (EIA)',            article: 'Art. 11(b)',              minRisk: 'high' },
  { type: 'forced_labor_affidavit',  label: 'Declaracion ausencia trabajo forzoso',          article: 'Art. 11, Anexo II',       minRisk: 'high' },

  // ── Solo si territorio indigena/colectivo ──
  { type: 'fpic_record',           label: 'Consulta previa libre e informada (FPIC)',        article: 'Art. 10(2)(i), UNDRIP',   minRisk: 'any', indigenous: true },
  { type: 'community_agreement',   label: 'Acuerdo con comunidad indigena/afro',             article: 'Art. 10(2)(i)',           minRisk: 'any', indigenous: true },

  // ── Colombia ──
  { type: 'rut',                   label: 'RUT (Registro Unico Tributario — DIAN)',          article: 'Anexo II — Fiscal',       minRisk: 'standard', countries: ['CO'] },
  { type: 'pila_statement',        label: 'PILA (Planilla Integrada Seguridad Social)',      article: 'Anexo II — Laboral',      minRisk: 'standard', countries: ['CO'] },
  { type: 'ica_invoice',           label: 'Factura ICA (registro agroquimicos)',             article: 'Anexo II — Ambiental',    minRisk: 'standard', countries: ['CO'] },
]

const RISK_ORDER: Record<string, number> = { any: 0, standard: 1, high: 2 }
const EUDR_RISK_TO_MIN: Record<string, number> = { none: 0, low: 0, medium: 1, high: 2 }

function EudrDocChecklist({ riskLevel, indigenousFlag, countryCode, documents, onAttach, onDetach, isPending }: {
  riskLevel?: EudrRiskLevel
  indigenousFlag: boolean
  countryCode: string
  documents: import('@/types/compliance').DocumentLink[]
  onAttach: (data: import('@/types/compliance').DocumentLinkInput) => Promise<void>
  onDetach: (docId: string) => Promise<void>
  isPending?: boolean
}) {
  const [pickerFor, setPickerFor] = useState<string | null>(null)
  const riskNum = riskLevel ? (EUDR_RISK_TO_MIN[riskLevel] ?? 0) : 0
  const applicable = EUDR_REQUIRED_DOCS.filter(d => {
    if (d.indigenous && !indigenousFlag) return false
    if (d.countries && !d.countries.includes(countryCode)) return false
    return RISK_ORDER[d.minRisk] <= riskNum
  })

  const attachedTypes = documents.map(d => d.document_type)
  const attached = applicable.filter(d => attachedTypes.includes(d.type))
  const pct = applicable.length > 0 ? Math.round((attached.length / applicable.length) * 100) : 0

  return (
    <div className="bg-card rounded-xl border border-border p-5 space-y-4">
      <div>
        <h3 className="text-sm font-bold text-foreground uppercase tracking-wide">Documentos fijos del predio</h3>
        <p className="text-xs text-muted-foreground mt-1">
          Documentos que se adjuntan una vez a la parcela. Los documentos por envio (DDS, screening, transporte) van en cada declaracion de cumplimiento.
        </p>
      </div>

      {/* Progress bar */}
      <div className="space-y-1.5">
        <div className="flex items-center justify-between text-xs">
          <span className="text-muted-foreground">{attached.length} de {applicable.length} adjuntos</span>
          <span className="font-semibold text-foreground">{pct}%</span>
        </div>
        <div className="h-2 w-full rounded-full bg-muted overflow-hidden">
          <div
            className={`h-full transition-all ${pct === 100 ? 'bg-emerald-500' : pct >= 60 ? 'bg-amber-500' : 'bg-red-500'}`}
            style={{ width: `${pct}%` }}
          />
        </div>
      </div>

      {/* Each doc as independent input */}
      <div className="space-y-3">
        {applicable.map(doc => {
          const linkedDoc = documents.find(d => d.document_type === doc.type)
          const isAttached = Boolean(linkedDoc)
          return (
            <div key={doc.type} className={`rounded-lg border p-3 ${isAttached ? 'border-emerald-200 bg-emerald-50/50' : 'border-border'}`}>
              <div className="flex items-start justify-between gap-2 mb-1">
                <div className="flex items-start gap-2 min-w-0">
                  <div className={`flex h-5 w-5 items-center justify-center rounded-full shrink-0 mt-0.5 ${
                    isAttached ? 'bg-emerald-100 text-emerald-600' : 'bg-muted text-muted-foreground'
                  }`}>
                    {isAttached ? <Check className="h-3 w-3" /> : <span className="text-[10px] font-bold">?</span>}
                  </div>
                  <div className="min-w-0">
                    <p className="text-xs font-semibold text-foreground">{doc.label}</p>
                    <p className="text-[10px] text-muted-foreground">{doc.article}</p>
                  </div>
                </div>
              </div>

              {isAttached && linkedDoc ? (
                <div className="flex items-center gap-2 mt-2 ml-7">
                  <FileText className="h-3.5 w-3.5 text-emerald-600 shrink-0" />
                  <span className="text-xs text-foreground truncate flex-1">{linkedDoc.filename ?? 'Archivo adjunto'}</span>
                  {linkedDoc.url && (
                    <a href={mediaFileUrl(linkedDoc.url)} target="_blank" rel="noopener noreferrer"
                      className="text-xs text-primary hover:underline shrink-0">
                      Ver
                    </a>
                  )}
                  <button onClick={() => onDetach(linkedDoc.id)} disabled={isPending}
                    className="text-xs text-red-500 hover:underline shrink-0 disabled:opacity-50">
                    Quitar
                  </button>
                </div>
              ) : (
                <button
                  onClick={() => setPickerFor(doc.type)}
                  className="mt-2 ml-7 inline-flex items-center gap-1.5 rounded-lg border border-dashed border-border px-3 py-1.5 text-xs text-muted-foreground hover:border-primary hover:text-primary transition-colors"
                >
                  <FolderOpen className="h-3.5 w-3.5" />
                  Adjuntar documento
                </button>
              )}
            </div>
          )
        })}
      </div>

      {applicable.length === 0 && (
        <p className="text-xs text-muted-foreground text-center py-4">
          Ejecuta la verificacion EUDR para determinar los documentos requeridos segun el nivel de riesgo.
        </p>
      )}

      {/* Media picker — one for each doc type */}
      <MediaPickerModal
        open={pickerFor !== null}
        onClose={() => setPickerFor(null)}
        onSelect={async (mediaFileId, _docType, description) => {
          if (!pickerFor) return
          await onAttach({ media_file_id: mediaFileId, document_type: pickerFor as any, description: description ?? null })
          setPickerFor(null)
        }}
      />
    </div>
  )
}
