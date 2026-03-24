import { useState } from 'react'
import { useParams, Link, Navigate } from 'react-router-dom'
import {
  ChevronRight, Package, MapPin, ShieldCheck, FileText, Award,
  CheckCircle2, XCircle, AlertTriangle, Plus, Trash2, Download,
  Copy, ExternalLink, RefreshCw, Loader2,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { Tabs } from '@/components/ui/tabs'
import {
  useRecord, useUpdateRecord, useRecordPlots, usePlots, useLinkPlot,
  useUnlinkPlot, useValidateRecord, useUpdateDeclaration,
  useRecordCertificate, useGenerateCertificate, useRegenerateCertificate,
  useFramework,
} from '@/hooks/useCompliance'
import type {
  ComplianceRecord, UpdateRecordInput, ValidationResult,
  CompliancePlot, DeclarationUpdate, ComplianceCertificate,
} from '@/types/compliance'

// ─── Shared helpers ──────────────────────────────────────────────────────────

const STATUS_COLORS: Record<string, string> = {
  incomplete: 'bg-amber-50 text-amber-700 border-amber-200',
  ready: 'bg-emerald-50 text-emerald-700 border-emerald-200',
  declared: 'bg-blue-50 text-blue-700 border-blue-200',
  compliant: 'bg-green-50 text-green-700 border-green-200',
  non_compliant: 'bg-red-50 text-red-700 border-red-200',
  partial: 'bg-orange-50 text-orange-700 border-orange-200',
}

const STATUS_LABELS: Record<string, string> = {
  incomplete: 'Incompleto',
  ready: 'Listo',
  declared: 'Declarado',
  compliant: 'Cumple',
  non_compliant: 'No cumple',
  partial: 'Parcial',
}

const DECL_STATUS_LABELS: Record<string, string> = {
  not_required: 'No requerido',
  pending: 'Pendiente',
  submitted: 'Enviada',
  accepted: 'Aceptada',
  rejected: 'Rechazada',
}

const FRAMEWORK_FLAGS: Record<string, string> = {
  eudr: '🇪🇺',
  'usda-organic': '🇺🇸',
  fssai: '🇮🇳',
  'jfs-2200': '🇯🇵',
}

function ComplianceStatusBadge({ status, size = 'sm' }: { status: string; size?: 'sm' | 'lg' }) {
  return (
    <span className={cn(
      'inline-flex items-center rounded-full font-semibold border',
      size === 'lg' ? 'px-3 py-1 text-sm' : 'px-2 py-0.5 text-[11px]',
      STATUS_COLORS[status] ?? 'bg-slate-50 text-slate-600 border-slate-200',
    )}>
      {STATUS_LABELS[status] ?? status}
    </span>
  )
}

// ─── Tab 1: Producto ─────────────────────────────────────────────────────────

function ProductTab({ record }: { record: ComplianceRecord }) {
  const update = useUpdateRecord(record.id)
  const [saved, setSaved] = useState(false)
  const [form, setForm] = useState<UpdateRecordInput>({
    hs_code: record.hs_code ?? '',
    commodity_type: record.commodity_type ?? '',
    product_description: record.product_description ?? '',
    scientific_name: record.scientific_name ?? '',
    quantity_kg: record.quantity_kg,
    quantity_unit: record.quantity_unit ?? 'kg',
    country_of_production: record.country_of_production ?? '',
    production_period_start: record.production_period_start?.slice(0, 10) ?? '',
    production_period_end: record.production_period_end?.slice(0, 10) ?? '',
    supplier_name: record.supplier_name ?? '',
    supplier_address: record.supplier_address ?? '',
    supplier_email: record.supplier_email ?? '',
    buyer_name: record.buyer_name ?? '',
    buyer_address: record.buyer_address ?? '',
    buyer_email: record.buyer_email ?? '',
    operator_eori: record.operator_eori ?? '',
    deforestation_free_declaration: record.deforestation_free_declaration,
    legal_compliance_declaration: record.legal_compliance_declaration,
  })

  const set = (key: string, value: unknown) => setForm(f => ({ ...f, [key]: value }))

  async function submit(e: React.FormEvent) {
    e.preventDefault()
    const data: UpdateRecordInput = {
      ...form,
      hs_code: (form.hs_code as string) || null,
      commodity_type: (form.commodity_type as string) || null,
      product_description: (form.product_description as string) || null,
      scientific_name: (form.scientific_name as string) || null,
      quantity_kg: form.quantity_kg ? Number(form.quantity_kg) : null,
      quantity_unit: (form.quantity_unit as string) || null,
      country_of_production: (form.country_of_production as string) || null,
      production_period_start: (form.production_period_start as string) || null,
      production_period_end: (form.production_period_end as string) || null,
      supplier_name: (form.supplier_name as string) || null,
      supplier_address: (form.supplier_address as string) || null,
      supplier_email: (form.supplier_email as string) || null,
      buyer_name: (form.buyer_name as string) || null,
      buyer_address: (form.buyer_address as string) || null,
      buyer_email: (form.buyer_email as string) || null,
      operator_eori: (form.operator_eori as string) || null,
    }
    await update.mutateAsync(data)
    setSaved(true)
    setTimeout(() => setSaved(false), 2000)
  }

  return (
    <form onSubmit={submit} className="space-y-8 max-w-2xl">
      {/* Identificacion */}
      <section>
        <h3 className="text-sm font-bold text-slate-700 mb-3">Identificacion</h3>
        <div className="grid grid-cols-2 gap-4">
          <Field label="Codigo HS" value={form.hs_code as string} onChange={v => set('hs_code', v)} placeholder="0901.21" />
          <Field label="Commodity" value={form.commodity_type as string} onChange={v => set('commodity_type', v)} />
          <Field label="Descripcion del producto" value={form.product_description as string} onChange={v => set('product_description', v)} className="col-span-2" />
          {(form.commodity_type === 'wood' || record.commodity_type === 'wood') && (
            <Field label="Nombre cientifico" value={form.scientific_name as string} onChange={v => set('scientific_name', v)} className="col-span-2" />
          )}
          <Field label="Cantidad" type="number" value={String(form.quantity_kg ?? '')} onChange={v => set('quantity_kg', v ? Number(v) : null)} />
          <Field label="Unidad" value={form.quantity_unit as string} onChange={v => set('quantity_unit', v)} />
          <Field label="Pais de produccion" value={form.country_of_production as string} onChange={v => set('country_of_production', v)} placeholder="CO" />
        </div>
      </section>

      {/* Periodo */}
      <section>
        <h3 className="text-sm font-bold text-slate-700 mb-3">Periodo</h3>
        <div className="grid grid-cols-2 gap-4">
          <Field label="Inicio del periodo" type="date" value={form.production_period_start as string} onChange={v => set('production_period_start', v)} />
          <Field label="Fin del periodo" type="date" value={form.production_period_end as string} onChange={v => set('production_period_end', v)} />
        </div>
      </section>

      {/* Proveedor */}
      <section>
        <h3 className="text-sm font-bold text-slate-700 mb-3">Proveedor</h3>
        <div className="grid grid-cols-2 gap-4">
          <Field label="Nombre" value={form.supplier_name as string} onChange={v => set('supplier_name', v)} />
          <Field label="Email" type="email" value={form.supplier_email as string} onChange={v => set('supplier_email', v)} />
          <Field label="Direccion" value={form.supplier_address as string} onChange={v => set('supplier_address', v)} className="col-span-2" />
        </div>
      </section>

      {/* Comprador */}
      <section>
        <h3 className="text-sm font-bold text-slate-700 mb-3">Comprador</h3>
        <div className="grid grid-cols-2 gap-4">
          <Field label="Nombre" value={form.buyer_name as string} onChange={v => set('buyer_name', v)} />
          <Field label="Email" type="email" value={form.buyer_email as string} onChange={v => set('buyer_email', v)} />
          <Field label="Direccion" value={form.buyer_address as string} onChange={v => set('buyer_address', v)} className="col-span-2" />
        </div>
      </section>

      {/* Exportacion UE */}
      <section>
        <h3 className="text-sm font-bold text-slate-700 mb-3">Exportacion UE</h3>
        <div className="grid grid-cols-2 gap-4">
          <Field label="EORI del operador" value={form.operator_eori as string} onChange={v => set('operator_eori', v)} placeholder="DE123456789012345" />
        </div>
      </section>

      {/* Declaraciones */}
      <section>
        <h3 className="text-sm font-bold text-slate-700 mb-3">Declaraciones</h3>
        <div className="space-y-3">
          <label className="flex items-center gap-2.5 cursor-pointer">
            <input type="checkbox" checked={form.deforestation_free_declaration ?? false}
              onChange={e => set('deforestation_free_declaration', e.target.checked)}
              className="rounded border-slate-300" />
            <span className="text-sm text-slate-700">Declaracion libre de deforestacion</span>
          </label>
          <label className="flex items-center gap-2.5 cursor-pointer">
            <input type="checkbox" checked={form.legal_compliance_declaration ?? false}
              onChange={e => set('legal_compliance_declaration', e.target.checked)}
              className="rounded border-slate-300" />
            <span className="text-sm text-slate-700">Declaracion de cumplimiento legal</span>
          </label>
        </div>
      </section>

      <div className="flex items-center gap-3">
        <button type="submit" disabled={update.isPending}
          className="rounded-lg bg-primary px-5 py-2 text-sm font-semibold text-white hover:bg-primary/90 disabled:opacity-50 transition-colors">
          {update.isPending ? 'Guardando...' : 'Guardar cambios'}
        </button>
        {saved && <span className="text-xs font-medium text-emerald-600">Guardado</span>}
        {update.isError && <span className="text-xs text-red-600">{(update.error as Error).message}</span>}
      </div>
    </form>
  )
}

function Field({
  label, value, onChange, type = 'text', placeholder, className,
}: {
  label: string; value: string; onChange: (v: string) => void; type?: string; placeholder?: string; className?: string
}) {
  return (
    <div className={className}>
      <label className="block text-xs font-medium text-slate-600 mb-1.5">{label}</label>
      <input type={type} value={value} onChange={e => onChange(e.target.value)} placeholder={placeholder}
        className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring" />
    </div>
  )
}

// ─── Tab 2: Parcelas ─────────────────────────────────────────────────────────

function PlotsTab({ recordId, frameworkSlug }: { recordId: string; frameworkSlug: string }) {
  const { data: linkedPlots = [], isLoading } = useRecordPlots(recordId)
  const { data: allPlots = [] } = usePlots()
  const { data: framework } = useFramework(frameworkSlug)
  const linkPlot = useLinkPlot(recordId)
  const unlinkPlot = useUnlinkPlot(recordId)

  const [showLink, setShowLink] = useState(false)
  const [linkForm, setLinkForm] = useState({ plot_id: '', quantity_kg: '', percentage: '' })

  const linkedIds = new Set(linkedPlots.map(lp => lp.plot_id))
  const availablePlots = allPlots.filter(p => !linkedIds.has(p.id))

  async function submitLink(e: React.FormEvent) {
    e.preventDefault()
    await linkPlot.mutateAsync({
      plot_id: linkForm.plot_id,
      quantity_from_plot_kg: linkForm.quantity_kg ? Number(linkForm.quantity_kg) : undefined,
      percentage_from_plot: linkForm.percentage ? Number(linkForm.percentage) : undefined,
    })
    setLinkForm({ plot_id: '', quantity_kg: '', percentage: '' })
    setShowLink(false)
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <p className="text-sm text-slate-500">Parcelas vinculadas a este registro</p>
        <button onClick={() => setShowLink(!showLink)}
          className="flex items-center gap-1.5 rounded-xl bg-primary px-3 py-1.5 text-xs font-semibold text-white hover:bg-primary/90 transition-colors">
          <Plus className="h-3.5 w-3.5" /> Vincular Parcela
        </button>
      </div>

      {framework?.requires_geolocation && linkedPlots.length === 0 && (
        <div className="rounded-xl border border-amber-200 bg-amber-50 p-3 flex items-start gap-2">
          <AlertTriangle className="h-4 w-4 text-amber-500 mt-0.5 shrink-0" />
          <p className="text-xs text-amber-700">
            Este framework requiere geolocalizacion. Vincula al menos una parcela con coordenadas.
          </p>
        </div>
      )}

      {/* Link form */}
      {showLink && (
        <form onSubmit={submitLink} className="rounded-xl border border-primary/30 bg-primary/5 p-4 space-y-3">
          <div className="grid grid-cols-3 gap-3">
            <div>
              <label className="text-xs font-medium text-slate-600 mb-1 block">Parcela *</label>
              <select required value={linkForm.plot_id} onChange={e => setLinkForm(f => ({ ...f, plot_id: e.target.value }))}
                className="w-full rounded-lg border border-slate-200 px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-ring">
                <option value="">Seleccionar...</option>
                {availablePlots.map(p => (
                  <option key={p.id} value={p.id}>{p.plot_code} — {p.municipality ?? p.region ?? p.country_code}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="text-xs font-medium text-slate-600 mb-1 block">Cantidad (kg)</label>
              <input type="number" step="0.01" value={linkForm.quantity_kg}
                onChange={e => setLinkForm(f => ({ ...f, quantity_kg: e.target.value }))}
                className="w-full rounded-lg border border-slate-200 px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-ring" />
            </div>
            <div>
              <label className="text-xs font-medium text-slate-600 mb-1 block">Porcentaje (%)</label>
              <input type="number" step="0.1" min="0" max="100" value={linkForm.percentage}
                onChange={e => setLinkForm(f => ({ ...f, percentage: e.target.value }))}
                className="w-full rounded-lg border border-slate-200 px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-ring" />
            </div>
          </div>
          <div className="flex justify-end gap-2">
            <button type="button" onClick={() => setShowLink(false)} className="rounded-lg px-3 py-1.5 text-xs text-slate-600 hover:bg-slate-100">Cancelar</button>
            <button type="submit" disabled={linkPlot.isPending}
              className="rounded-lg bg-primary px-4 py-1.5 text-xs font-semibold text-white hover:bg-primary/90 disabled:opacity-50">
              {linkPlot.isPending ? 'Vinculando...' : 'Vincular'}
            </button>
          </div>
        </form>
      )}

      {/* Linked plots list */}
      {isLoading ? (
        <div className="text-sm text-slate-400 py-6 text-center">Cargando...</div>
      ) : linkedPlots.length === 0 ? (
        <div className="rounded-xl border-2 border-dashed border-slate-200 p-10 text-center">
          <MapPin className="h-8 w-8 text-slate-200 mx-auto mb-3" />
          <p className="text-sm font-medium text-slate-600 mb-1">Sin parcelas vinculadas</p>
          <p className="text-xs text-slate-400">Vincula parcelas de produccion a este registro.</p>
        </div>
      ) : (
        <div className="space-y-2">
          {linkedPlots.map(lp => {
            const plot = allPlots.find(p => p.id === lp.plot_id)
            return (
              <div key={lp.id} className="flex items-center gap-4 rounded-xl border border-slate-100 bg-white px-4 py-3">
                <MapPin className="h-4 w-4 text-emerald-500 shrink-0" />
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-slate-900">{plot?.plot_code ?? lp.plot_id.slice(0, 8)}</p>
                  <p className="text-xs text-slate-500">
                    {plot?.municipality ?? plot?.region ?? ''}{plot?.country_code ? ` (${plot.country_code})` : ''}
                    {plot?.plot_area_ha ? ` — ${plot.plot_area_ha} ha` : ''}
                  </p>
                </div>
                {lp.quantity_from_plot_kg != null && (
                  <span className="text-xs text-slate-600 tabular-nums">{Number(lp.quantity_from_plot_kg).toLocaleString('es-CO')} kg</span>
                )}
                {lp.percentage_from_plot != null && (
                  <span className="text-xs text-slate-500 tabular-nums">{lp.percentage_from_plot}%</span>
                )}
                {/* Compliance badges */}
                {plot && (
                  <div className="flex gap-1">
                    {plot.deforestation_free && <span className="px-1.5 py-0.5 rounded text-[10px] font-medium bg-green-50 text-green-700">DF</span>}
                    {plot.legal_land_use && <span className="px-1.5 py-0.5 rounded text-[10px] font-medium bg-blue-50 text-blue-700">Legal</span>}
                    {plot.cutoff_date_compliant && <span className="px-1.5 py-0.5 rounded text-[10px] font-medium bg-emerald-50 text-emerald-700">Cutoff</span>}
                  </div>
                )}
                <button onClick={() => unlinkPlot.mutate(lp.plot_id)} disabled={unlinkPlot.isPending}
                  className="rounded-lg p-1.5 text-slate-400 hover:text-red-500 hover:bg-red-50 transition-colors disabled:opacity-50">
                  <Trash2 className="h-3.5 w-3.5" />
                </button>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}

// ─── Tab 3: Validacion ───────────────────────────────────────────────────────

function ValidationTab({ recordId, record }: { recordId: string; record: ComplianceRecord }) {
  const validate = useValidateRecord(recordId)
  const [result, setResult] = useState<ValidationResult | null>(null)

  async function runValidation() {
    const res = await validate.mutateAsync()
    setResult(res)
  }

  const FIELD_LABELS: Record<string, string> = {
    hs_code: 'Codigo HS',
    commodity_type: 'Tipo de commodity',
    product_description: 'Descripcion del producto',
    scientific_name: 'Nombre cientifico',
    quantity_kg: 'Cantidad en kg',
    country_of_production: 'Pais de produccion',
    production_period_start: 'Inicio del periodo de produccion',
    production_period_end: 'Fin del periodo de produccion',
    supplier_name: 'Nombre del proveedor',
    buyer_name: 'Nombre del comprador',
    operator_eori: 'EORI del operador',
    deforestation_free_declaration: 'Declaracion libre de deforestacion',
    legal_compliance_declaration: 'Declaracion de cumplimiento legal',
    plots: 'Parcelas de produccion',
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <button onClick={runValidation} disabled={validate.isPending}
          className="flex items-center gap-2 rounded-xl bg-primary px-5 py-2.5 text-sm font-semibold text-white hover:bg-primary/90 disabled:opacity-50 transition-colors">
          {validate.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <ShieldCheck className="h-4 w-4" />}
          Validar ahora
        </button>
        <ComplianceStatusBadge status={record.compliance_status} size="lg" />
      </div>

      {record.last_validated_at && (
        <p className="text-xs text-slate-400">
          Ultima validacion: {new Date(record.last_validated_at).toLocaleString('es-CO')}
        </p>
      )}

      {result && (
        <div className="space-y-4">
          {/* Overall result */}
          <div className={cn(
            'rounded-2xl p-5 flex items-center gap-4',
            result.valid
              ? 'bg-green-50 border border-green-200'
              : 'bg-red-50 border border-red-200',
          )}>
            {result.valid
              ? <CheckCircle2 className="h-8 w-8 text-green-600" />
              : <XCircle className="h-8 w-8 text-red-500" />
            }
            <div>
              <p className={cn('text-base font-bold', result.valid ? 'text-green-800' : 'text-red-800')}>
                {result.valid ? 'Registro valido' : 'Registro incompleto'}
              </p>
              <p className="text-sm text-slate-600 mt-0.5">
                Framework: {result.framework} | Estado: {STATUS_LABELS[result.compliance_status] ?? result.compliance_status}
              </p>
            </div>
          </div>

          {/* Missing fields */}
          {result.missing_fields.length > 0 && (
            <div>
              <h4 className="text-sm font-semibold text-slate-700 mb-2">Campos faltantes</h4>
              <ul className="space-y-1.5">
                {result.missing_fields.map(f => (
                  <li key={f} className="flex items-center gap-2 text-sm text-red-700">
                    <XCircle className="h-3.5 w-3.5 shrink-0" />
                    {FIELD_LABELS[f] ?? f}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Warnings */}
          {result.warnings.length > 0 && (
            <div>
              <h4 className="text-sm font-semibold text-slate-700 mb-2">Advertencias</h4>
              <ul className="space-y-1.5">
                {result.warnings.map((w, i) => (
                  <li key={i} className="flex items-center gap-2 text-sm text-amber-700">
                    <AlertTriangle className="h-3.5 w-3.5 shrink-0" />
                    {w}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

// ─── Tab 4: Declaracion DDS ──────────────────────────────────────────────────

function DeclarationTab({ record }: { record: ComplianceRecord }) {
  const updateDecl = useUpdateDeclaration(record.id)
  const [saved, setSaved] = useState(false)
  const [form, setForm] = useState<DeclarationUpdate>({
    declaration_reference: record.declaration_reference ?? '',
    declaration_submission_date: record.declaration_submission_date?.slice(0, 10) ?? '',
    declaration_status: record.declaration_status ?? 'not_required',
    declaration_url: record.declaration_url ?? '',
  })

  async function submit(e: React.FormEvent) {
    e.preventDefault()
    await updateDecl.mutateAsync({
      declaration_reference: (form.declaration_reference as string) || null,
      declaration_submission_date: (form.declaration_submission_date as string) || null,
      declaration_status: form.declaration_status || null,
      declaration_url: (form.declaration_url as string) || null,
    })
    setSaved(true)
    setTimeout(() => setSaved(false), 2000)
  }

  return (
    <form onSubmit={submit} className="space-y-6 max-w-xl">
      <div className="space-y-4">
        <div>
          <label className="block text-xs font-medium text-slate-600 mb-1.5">Referencia de declaracion</label>
          <input value={form.declaration_reference ?? ''} onChange={e => setForm(f => ({ ...f, declaration_reference: e.target.value }))}
            placeholder="DDS-2026-XXXX"
            className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring" />
        </div>

        <div>
          <label className="block text-xs font-medium text-slate-600 mb-1.5">Fecha de envio</label>
          <input type="date" value={form.declaration_submission_date ?? ''} onChange={e => setForm(f => ({ ...f, declaration_submission_date: e.target.value }))}
            className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring" />
        </div>

        <div>
          <label className="block text-xs font-medium text-slate-600 mb-1.5">Estado de la declaracion</label>
          <select value={form.declaration_status ?? 'not_required'}
            onChange={e => setForm(f => ({ ...f, declaration_status: e.target.value }))}
            className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring">
            {Object.entries(DECL_STATUS_LABELS).map(([k, v]) => (
              <option key={k} value={k}>{v}</option>
            ))}
          </select>
        </div>

        <div>
          <label className="block text-xs font-medium text-slate-600 mb-1.5">URL de la declaracion</label>
          <input value={form.declaration_url ?? ''} onChange={e => setForm(f => ({ ...f, declaration_url: e.target.value }))}
            placeholder="https://webgate.ec.europa.eu/tracesnt/..."
            className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring" />
        </div>

        {form.declaration_url && (
          <a href={form.declaration_url as string} target="_blank" rel="noopener noreferrer"
            className="inline-flex items-center gap-1.5 text-xs font-semibold text-primary hover:text-primary">
            <ExternalLink className="h-3.5 w-3.5" /> Abrir en EU TRACES
          </a>
        )}

        {record.declaration_status && record.declaration_status !== 'not_required' && (
          <div className="rounded-lg bg-slate-50 p-3">
            <span className="text-xs font-medium text-slate-500 mr-2">Estado actual:</span>
            <span className={cn(
              'inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-semibold border',
              record.declaration_status === 'accepted' ? 'bg-green-50 text-green-700 border-green-200' :
                record.declaration_status === 'rejected' ? 'bg-red-50 text-red-700 border-red-200' :
                  record.declaration_status === 'submitted' ? 'bg-blue-50 text-blue-700 border-blue-200' :
                    'bg-amber-50 text-amber-700 border-amber-200',
            )}>
              {DECL_STATUS_LABELS[record.declaration_status] ?? record.declaration_status}
            </span>
          </div>
        )}
      </div>

      <div className="flex items-center gap-3">
        <button type="submit" disabled={updateDecl.isPending}
          className="rounded-lg bg-primary px-5 py-2 text-sm font-semibold text-white hover:bg-primary/90 disabled:opacity-50 transition-colors">
          {updateDecl.isPending ? 'Guardando...' : 'Guardar declaracion'}
        </button>
        {saved && <span className="text-xs font-medium text-emerald-600">Guardado</span>}
      </div>
    </form>
  )
}

// ─── Tab 5: Certificado ──────────────────────────────────────────────────────

function CertificateTab({ recordId, record }: { recordId: string; record: ComplianceRecord }) {
  const { data: certificate, isLoading, isError } = useRecordCertificate(recordId)
  const generate = useGenerateCertificate(recordId)
  const regenerate = useRegenerateCertificate()

  const isIncomplete = record.compliance_status === 'incomplete' || record.compliance_status === 'non_compliant'

  if (isLoading) {
    return <div className="text-sm text-slate-400 py-6 text-center">Cargando...</div>
  }

  // No certificate yet
  if (isError || !certificate) {
    return (
      <div className="rounded-2xl border-2 border-dashed border-slate-200 p-10 text-center">
        <Award className="h-10 w-10 text-slate-200 mx-auto mb-3" />
        <p className="text-sm font-medium text-slate-600 mb-1">Sin certificado</p>
        <p className="text-xs text-slate-400 mb-5">
          {isIncomplete
            ? 'Completa todos los campos requeridos y valida el registro antes de generar un certificado.'
            : 'Genera un certificado de cumplimiento para este registro.'}
        </p>
        <button onClick={() => generate.mutate()} disabled={isIncomplete || generate.isPending}
          className="inline-flex items-center gap-2 rounded-lg bg-emerald-600 px-5 py-2 text-sm font-semibold text-white hover:bg-emerald-700 disabled:opacity-50 transition-colors">
          {generate.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Award className="h-4 w-4" />}
          {generate.isPending ? 'Generando...' : 'Generar Certificado'}
        </button>
        {generate.isError && (
          <p className="text-xs text-red-600 mt-3">{(generate.error as Error).message}</p>
        )}
      </div>
    )
  }

  // Certificate exists
  const isRevoked = certificate.status === 'revoked'

  return (
    <div className="space-y-6">
      {isRevoked && (
        <div className="rounded-xl border border-red-200 bg-red-50 p-4 flex items-start gap-3">
          <XCircle className="h-5 w-5 text-red-500 mt-0.5 shrink-0" />
          <div>
            <p className="text-sm font-bold text-red-800">Certificado Revocado</p>
            <p className="text-xs text-red-600 mt-0.5">
              Este certificado ha sido revocado y ya no es valido.
            </p>
          </div>
        </div>
      )}

      <div className="grid grid-cols-2 gap-6">
        <div>
          <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wide mb-1">Numero</label>
          <p className="text-sm font-mono font-medium text-slate-900">{certificate.certificate_number}</p>
        </div>
        <div>
          <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wide mb-1">Estado</label>
          <span className={cn(
            'inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold border',
            certificate.status === 'active' ? 'bg-green-50 text-green-700 border-green-200' :
              certificate.status === 'revoked' ? 'bg-red-50 text-red-700 border-red-200' :
                certificate.status === 'expired' ? 'bg-amber-50 text-amber-700 border-amber-200' :
                  'bg-slate-50 text-slate-600 border-slate-200',
          )}>
            {certificate.status === 'active' ? 'Activo' : certificate.status === 'revoked' ? 'Revocado' : certificate.status === 'expired' ? 'Expirado' : certificate.status}
          </span>
        </div>
        <div>
          <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wide mb-1">Valido desde</label>
          <p className="text-sm text-slate-700">{new Date(certificate.valid_from).toLocaleDateString('es-CO')}</p>
        </div>
        <div>
          <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wide mb-1">Valido hasta</label>
          <p className="text-sm text-slate-700">{new Date(certificate.valid_until).toLocaleDateString('es-CO')}</p>
        </div>
      </div>

      {/* Blockchain info */}
      {(certificate.solana_cnft_address || certificate.solana_tx_sig) && (
        <div className="rounded-xl bg-slate-50 border border-slate-100 p-4 space-y-2">
          <h4 className="text-xs font-bold text-slate-500 uppercase tracking-wide">Blockchain</h4>
          {certificate.solana_cnft_address && (
            <p className="text-xs text-slate-600">cNFT: <code className="font-mono text-primary">{certificate.solana_cnft_address}</code></p>
          )}
          {certificate.solana_tx_sig && (
            <p className="text-xs text-slate-600">TX: <code className="font-mono text-primary">{certificate.solana_tx_sig}</code></p>
          )}
        </div>
      )}

      {/* Actions */}
      <div className="flex flex-wrap gap-3">
        {certificate.pdf_url && (
          <a href={certificate.pdf_url} target="_blank" rel="noopener noreferrer"
            className="inline-flex items-center gap-2 rounded-lg bg-emerald-600 px-4 py-2 text-sm font-semibold text-white hover:bg-emerald-700 transition-colors">
            <Download className="h-4 w-4" /> Descargar PDF
          </a>
        )}
        <button onClick={() => {
          navigator.clipboard.writeText(certificate.verify_url)
        }}
          className="inline-flex items-center gap-2 rounded-lg border border-slate-200 px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50 transition-colors">
          <Copy className="h-4 w-4" /> Copiar URL de verificacion
        </button>
        <button onClick={() => regenerate.mutate(certificate.id)} disabled={regenerate.isPending}
          className="inline-flex items-center gap-2 rounded-lg border border-slate-200 px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50 transition-colors disabled:opacity-50">
          <RefreshCw className={cn('h-4 w-4', regenerate.isPending && 'animate-spin')} /> Regenerar
        </button>
      </div>

      {/* QR preview */}
      {certificate.qr_code_url && (
        <div>
          <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wide mb-2">QR de verificacion</label>
          <img src={certificate.qr_code_url} alt="QR Code" className="h-32 w-32 rounded-lg border border-slate-200" />
        </div>
      )}
    </div>
  )
}

// ─── Main Page ───────────────────────────────────────────────────────────────

const TABS_DEF = [
  { key: 'product', label: 'Producto', icon: Package },
  { key: 'plots', label: 'Parcelas', icon: MapPin },
  { key: 'validation', label: 'Validacion', icon: ShieldCheck },
  { key: 'declaration', label: 'Declaracion DDS', icon: FileText },
  { key: 'certificate', label: 'Certificado', icon: Award },
]

export default function RecordDetailPage() {
  const { id = '' } = useParams<{ id: string }>()
  const { data: record, isLoading } = useRecord(id)
  const [activeTab, setActiveTab] = useState('product')

  if (isLoading) {
    return (
      <div className="max-w-5xl mx-auto p-6 lg:p-8">
        <div className="text-sm text-slate-400 py-12 text-center">Cargando...</div>
      </div>
    )
  }

  if (!record) return <Navigate to="/cumplimiento/registros" replace />

  return (
    <div className="p-6 lg:p-8 space-y-6 max-w-5xl mx-auto">
      {/* Breadcrumbs */}
      <nav className="flex items-center gap-1.5 text-xs text-slate-400">
        <Link to="/cumplimiento/activaciones" className="hover:text-slate-600 transition-colors">Cumplimiento</Link>
        <ChevronRight className="h-3 w-3" />
        <Link to="/cumplimiento/registros" className="hover:text-slate-600 transition-colors">Registros</Link>
        <ChevronRight className="h-3 w-3" />
        <span className="text-slate-700 font-medium">{record.id.slice(0, 8)}</span>
      </nav>

      {/* Header */}
      <div className="flex items-center gap-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-emerald-50">
          <ShieldCheck className="h-5 w-5 text-emerald-600" />
        </div>
        <div className="flex-1">
          <h1 className="text-xl font-bold text-slate-900">
            {FRAMEWORK_FLAGS[record.framework_slug] ?? ''} Registro {record.framework_slug.toUpperCase()}
          </h1>
          <p className="text-sm text-slate-500">
            Asset: <Link to={`/assets/${record.asset_id}`} className="text-primary hover:underline font-mono">{record.asset_id.slice(0, 12)}...</Link>
          </p>
        </div>
        <ComplianceStatusBadge status={record.compliance_status} size="lg" />
      </div>

      {/* Tabs */}
      <Tabs tabs={TABS_DEF} value={activeTab} onChange={setActiveTab} />

      {/* Tab content */}
      <div className="bg-white rounded-2xl border border-slate-100 shadow-sm p-6">
        {activeTab === 'product' && <ProductTab record={record} />}
        {activeTab === 'plots' && <PlotsTab recordId={record.id} frameworkSlug={record.framework_slug} />}
        {activeTab === 'validation' && <ValidationTab recordId={record.id} record={record} />}
        {activeTab === 'declaration' && <DeclarationTab record={record} />}
        {activeTab === 'certificate' && <CertificateTab recordId={record.id} record={record} />}
      </div>
    </div>
  )
}
