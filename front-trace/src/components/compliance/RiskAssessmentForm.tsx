import { useState, useEffect } from 'react'
import {
  ShieldAlert, Globe, Link2, TreePine, CheckCircle2, AlertTriangle,
  XCircle, Loader2, Plus, Trash2,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import {
  useRiskAssessment, useCreateRiskAssessment,
  useUpdateRiskAssessment, useCompleteRiskAssessment,
} from '@/hooks/useCompliance'
import type { RiskAssessment, UpdateRiskAssessmentInput, MitigationMeasure } from '@/types/compliance'
import { useToast } from '@/store/toast'

const RISK_LEVELS = [
  { value: 'low', label: 'Bajo', color: 'text-green-700 bg-green-50' },
  { value: 'standard', label: 'Estandar', color: 'text-amber-700 bg-amber-50' },
  { value: 'high', label: 'Alto', color: 'text-red-700 bg-red-50' },
]

const OVERALL_LEVELS = [
  { value: 'negligible', label: 'Negligible', color: 'text-green-700 bg-green-50' },
  { value: 'low', label: 'Bajo', color: 'text-emerald-700 bg-emerald-50' },
  { value: 'standard', label: 'Estandar', color: 'text-amber-700 bg-amber-50' },
  { value: 'high', label: 'Alto', color: 'text-red-700 bg-red-50' },
]

const CONCLUSIONS = [
  { value: 'approved', label: 'Aprobado — Riesgo negligible', icon: CheckCircle2, color: 'text-green-700' },
  { value: 'conditional', label: 'Condicional — Con mitigacion', icon: AlertTriangle, color: 'text-amber-700' },
  { value: 'rejected', label: 'Rechazado — Riesgo inaceptable', icon: XCircle, color: 'text-red-700' },
]

const VERIFICATION_STATUS = [
  { value: 'not_started', label: 'No iniciada' },
  { value: 'in_progress', label: 'En progreso' },
  { value: 'verified', label: 'Verificado' },
  { value: 'failed', label: 'Fallida' },
]

const TRACEABILITY = [
  { value: 'full', label: 'Completa' },
  { value: 'partial', label: 'Parcial' },
  { value: 'none', label: 'Sin trazabilidad' },
]

const PREVALENCE = [
  { value: 'low', label: 'Baja' },
  { value: 'medium', label: 'Media' },
  { value: 'high', label: 'Alta' },
]

interface Props {
  recordId: string
}

export default function RiskAssessmentForm({ recordId }: Props) {
  const { data: assessment, isLoading, isError } = useRiskAssessment(recordId)
  const createRA = useCreateRiskAssessment()
  const updateRA = useUpdateRiskAssessment(assessment?.id ?? '', recordId)
  const completeRA = useCompleteRiskAssessment(recordId)
  const toast = useToast()

  const [form, setForm] = useState<UpdateRiskAssessmentInput>({})
  // Each row carries a client-side `__key` so React can keep DOM nodes and
  // input focus stable across additions/removals. Using the array index
  // would re-key every row after a deletion, causing the wrong <input> to
  // hold focus when the user removes a measure from the middle.
  type MeasureRow = MitigationMeasure & { __key: string }
  const _mkKey = () =>
    (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function')
      ? crypto.randomUUID()
      : `m-${Math.random().toString(36).slice(2)}-${Date.now()}`
  const [measures, setMeasures] = useState<MeasureRow[]>([])

  useEffect(() => {
    if (assessment) {
      setForm({
        country_risk_level: assessment.country_risk_level,
        country_risk_notes: assessment.country_risk_notes,
        country_benchmarking_source: assessment.country_benchmarking_source,
        supply_chain_risk_level: assessment.supply_chain_risk_level,
        supply_chain_notes: assessment.supply_chain_notes,
        supplier_verification_status: assessment.supplier_verification_status,
        traceability_confidence: assessment.traceability_confidence,
        regional_risk_level: assessment.regional_risk_level,
        deforestation_prevalence: assessment.deforestation_prevalence,
        indigenous_rights_risk: assessment.indigenous_rights_risk,
        corruption_index_note: assessment.corruption_index_note,
        overall_risk_level: assessment.overall_risk_level,
        conclusion: assessment.conclusion,
        conclusion_notes: assessment.conclusion_notes,
        additional_info_requested: assessment.additional_info_requested,
        independent_audit_required: assessment.independent_audit_required,
      })
      setMeasures((assessment.mitigation_measures ?? []).map(m => ({ ...m, __key: _mkKey() })))
    }
  }, [assessment])

  const set = (key: string, value: unknown) => setForm(f => ({ ...f, [key]: value }))

  async function handleCreate() {
    await createRA.mutateAsync({ record_id: recordId })
  }

  async function handleSave() {
    if (!assessment) return
    await updateRA.mutateAsync({ ...form, mitigation_measures: measures.map(({ __key, ...m }) => m) })
    toast.success('Evaluacion guardada')
  }

  async function handleComplete() {
    if (!assessment) return
    try {
      // Save first
      await updateRA.mutateAsync({ ...form, mitigation_measures: measures.map(({ __key, ...m }) => m) })
      await completeRA.mutateAsync(assessment.id)
      toast.success('Evaluacion completada')
    } catch (e: any) {
      toast.error(e.message ?? 'Error al completar')
    }
  }

  if (isLoading) return <div className="text-sm text-muted-foreground py-6 text-center">Cargando...</div>

  // No assessment yet — create one
  if (isError || !assessment) {
    return (
      <div className="rounded-2xl border-2 border-dashed border-border p-10 text-center">
        <ShieldAlert className="h-10 w-10 text-slate-200 mx-auto mb-3" />
        <p className="text-sm font-medium text-muted-foreground mb-1">Sin evaluacion de riesgo</p>
        <p className="text-xs text-muted-foreground mb-5">EUDR Art. 10-11 requiere una evaluacion formal antes de declarar.</p>
        <button onClick={handleCreate} disabled={createRA.isPending}
          className="inline-flex items-center gap-2 rounded-lg bg-primary px-5 py-2 text-sm font-semibold text-white hover:bg-primary/90 disabled:opacity-50 transition-colors">
          {createRA.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <ShieldAlert className="h-4 w-4" />}
          Iniciar evaluacion
        </button>
      </div>
    )
  }

  const isCompleted = assessment.status === 'completed'

  return (
    <div className="space-y-8 max-w-2xl">
      {isCompleted && (
        <div className={cn(
          'rounded-xl p-4 flex items-start gap-3 border',
          assessment.conclusion === 'approved' ? 'bg-green-50 border-green-200' :
            assessment.conclusion === 'conditional' ? 'bg-amber-50 border-amber-200' :
              'bg-red-50 border-red-200',
        )}>
          <CheckCircle2 className={cn(
            'h-5 w-5 mt-0.5 shrink-0',
            assessment.conclusion === 'approved' ? 'text-green-600' :
              assessment.conclusion === 'conditional' ? 'text-amber-600' : 'text-red-600',
          )} />
          <div>
            <p className="text-sm font-bold text-foreground">Evaluacion completada</p>
            <p className="text-xs text-muted-foreground mt-0.5">
              Conclusion: {CONCLUSIONS.find(c => c.value === assessment.conclusion)?.label ?? assessment.conclusion}
              {assessment.assessed_at && ` — ${new Date(assessment.assessed_at).toLocaleDateString('es-CO')}`}
            </p>
          </div>
        </div>
      )}

      {/* Step 1: Country Risk */}
      <section>
        <div className="flex items-center gap-2 mb-3">
          <Globe className="h-4 w-4 text-blue-600" />
          <h3 className="text-sm font-bold text-foreground">Paso 1 — Riesgo pais (Art. 29)</h3>
        </div>
        <div className="space-y-3">
          <div>
            <label className="block text-xs font-medium text-muted-foreground mb-1.5">Nivel de riesgo del pais *</label>
            <div className="flex gap-2">
              {RISK_LEVELS.map(rl => (
                <button key={rl.value} type="button" disabled={isCompleted}
                  onClick={() => set('country_risk_level', rl.value)}
                  className={cn(
                    'px-4 py-2 rounded-lg text-sm font-medium border transition-colors',
                    form.country_risk_level === rl.value ? rl.color + ' border-current' : 'bg-card text-muted-foreground border-border hover:bg-muted',
                  )}>
                  {rl.label}
                </button>
              ))}
            </div>
          </div>
          <div>
            <label className="block text-xs font-medium text-muted-foreground mb-1.5">Fuente de clasificacion</label>
            <input disabled={isCompleted} value={form.country_benchmarking_source ?? ''} onChange={e => set('country_benchmarking_source', e.target.value)}
              placeholder="EU Commission Benchmarking List 2025"
              className="w-full rounded-lg border border-border px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring disabled:bg-muted" />
          </div>
          <div>
            <label className="block text-xs font-medium text-muted-foreground mb-1.5">Notas</label>
            <textarea disabled={isCompleted} value={form.country_risk_notes ?? ''} onChange={e => set('country_risk_notes', e.target.value)}
              rows={2} className="w-full rounded-lg border border-border px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring disabled:bg-muted" />
          </div>
        </div>
      </section>

      {/* Step 2: Supply Chain Risk */}
      <section>
        <div className="flex items-center gap-2 mb-3">
          <Link2 className="h-4 w-4 text-purple-600" />
          <h3 className="text-sm font-bold text-foreground">Paso 2 — Riesgo cadena de suministro</h3>
        </div>
        <div className="space-y-3">
          <div>
            <label className="block text-xs font-medium text-muted-foreground mb-1.5">Nivel de riesgo *</label>
            <div className="flex gap-2">
              {RISK_LEVELS.map(rl => (
                <button key={rl.value} type="button" disabled={isCompleted}
                  onClick={() => set('supply_chain_risk_level', rl.value)}
                  className={cn(
                    'px-4 py-2 rounded-lg text-sm font-medium border transition-colors',
                    form.supply_chain_risk_level === rl.value ? rl.color + ' border-current' : 'bg-card text-muted-foreground border-border hover:bg-muted',
                  )}>
                  {rl.label}
                </button>
              ))}
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium text-muted-foreground mb-1.5">Verificacion de proveedores</label>
              <select disabled={isCompleted} value={form.supplier_verification_status ?? 'not_started'} onChange={e => set('supplier_verification_status', e.target.value)}
                className="w-full rounded-lg border border-border px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring disabled:bg-muted">
                {VERIFICATION_STATUS.map(v => <option key={v.value} value={v.value}>{v.label}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium text-muted-foreground mb-1.5">Confianza en trazabilidad</label>
              <select disabled={isCompleted} value={form.traceability_confidence ?? 'none'} onChange={e => set('traceability_confidence', e.target.value)}
                className="w-full rounded-lg border border-border px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring disabled:bg-muted">
                {TRACEABILITY.map(t => <option key={t.value} value={t.value}>{t.label}</option>)}
              </select>
            </div>
          </div>
          <div>
            <label className="block text-xs font-medium text-muted-foreground mb-1.5">Notas</label>
            <textarea disabled={isCompleted} value={form.supply_chain_notes ?? ''} onChange={e => set('supply_chain_notes', e.target.value)}
              rows={2} className="w-full rounded-lg border border-border px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring disabled:bg-muted" />
          </div>
        </div>
      </section>

      {/* Step 3: Regional Risk */}
      <section>
        <div className="flex items-center gap-2 mb-3">
          <TreePine className="h-4 w-4 text-emerald-600" />
          <h3 className="text-sm font-bold text-foreground">Paso 3 — Riesgo regional / producto</h3>
        </div>
        <div className="space-y-3">
          <div>
            <label className="block text-xs font-medium text-muted-foreground mb-1.5">Nivel de riesgo regional *</label>
            <div className="flex gap-2">
              {RISK_LEVELS.map(rl => (
                <button key={rl.value} type="button" disabled={isCompleted}
                  onClick={() => set('regional_risk_level', rl.value)}
                  className={cn(
                    'px-4 py-2 rounded-lg text-sm font-medium border transition-colors',
                    form.regional_risk_level === rl.value ? rl.color + ' border-current' : 'bg-card text-muted-foreground border-border hover:bg-muted',
                  )}>
                  {rl.label}
                </button>
              ))}
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium text-muted-foreground mb-1.5">Prevalencia de deforestacion</label>
              <select disabled={isCompleted} value={form.deforestation_prevalence ?? ''} onChange={e => set('deforestation_prevalence', e.target.value)}
                className="w-full rounded-lg border border-border px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring disabled:bg-muted">
                <option value="">Seleccionar...</option>
                {PREVALENCE.map(p => <option key={p.value} value={p.value}>{p.label}</option>)}
              </select>
            </div>
            <div className="flex items-end pb-1">
              <label className="flex items-center gap-2 cursor-pointer">
                <input type="checkbox" disabled={isCompleted} checked={form.indigenous_rights_risk ?? false}
                  onChange={e => set('indigenous_rights_risk', e.target.checked)}
                  className="rounded border-slate-300" />
                <span className="text-sm text-foreground">Riesgo de derechos indigenas</span>
              </label>
            </div>
          </div>
          <div>
            <label className="block text-xs font-medium text-muted-foreground mb-1.5">Nota de indice de corrupcion</label>
            <input disabled={isCompleted} value={form.corruption_index_note ?? ''} onChange={e => set('corruption_index_note', e.target.value)}
              placeholder="Transparency International CPI score"
              className="w-full rounded-lg border border-border px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring disabled:bg-muted" />
          </div>
        </div>
      </section>

      {/* Mitigation measures */}
      <section>
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-sm font-bold text-foreground">Medidas de mitigacion (Art. 11)</h3>
          {!isCompleted && (
            <button type="button" onClick={() => setMeasures(m => [...m, { measure: '', status: 'pending', __key: _mkKey() }])}
              className="flex items-center gap-1 text-xs text-primary font-semibold hover:text-primary/80">
              <Plus className="h-3.5 w-3.5" /> Agregar medida
            </button>
          )}
        </div>
        <div className="space-y-2">
          {measures.map((m) => (
            <div key={m.__key} className="flex items-center gap-2 rounded-lg border border-border bg-card px-3 py-2">
              <input disabled={isCompleted} value={m.measure} onChange={e => {
                const val = e.target.value
                setMeasures(rows => rows.map(r => r.__key === m.__key ? { ...r, measure: val } : r))
              }}
                placeholder="Descripcion de la medida..."
                className="flex-1 text-sm border-none bg-transparent focus:outline-none disabled:bg-transparent" />
              <select disabled={isCompleted} value={m.status} onChange={e => {
                const val = e.target.value
                setMeasures(rows => rows.map(r => r.__key === m.__key ? { ...r, status: val } : r))
              }}
                className="rounded-lg border border-border px-2 py-1 text-xs focus:outline-none disabled:bg-muted">
                <option value="pending">Pendiente</option>
                <option value="in_progress">En progreso</option>
                <option value="completed">Completada</option>
              </select>
              {!isCompleted && (
                <button type="button" onClick={() => setMeasures(rows => rows.filter(r => r.__key !== m.__key))}
                  className="p-1 text-muted-foreground hover:text-red-500">
                  <Trash2 className="h-3.5 w-3.5" />
                </button>
              )}
            </div>
          ))}
          {measures.length === 0 && (
            <p className="text-xs text-muted-foreground py-2">Sin medidas de mitigacion. Agrega si el riesgo no es negligible.</p>
          )}
        </div>

        <div className="mt-3 space-y-2">
          <label className="flex items-center gap-2 cursor-pointer">
            <input type="checkbox" disabled={isCompleted} checked={form.additional_info_requested ?? false}
              onChange={e => set('additional_info_requested', e.target.checked)} className="rounded border-slate-300" />
            <span className="text-sm text-foreground">Informacion adicional solicitada</span>
          </label>
          <label className="flex items-center gap-2 cursor-pointer">
            <input type="checkbox" disabled={isCompleted} checked={form.independent_audit_required ?? false}
              onChange={e => set('independent_audit_required', e.target.checked)} className="rounded border-slate-300" />
            <span className="text-sm text-foreground">Auditoria independiente requerida</span>
          </label>
        </div>
      </section>

      {/* Conclusion */}
      <section>
        <h3 className="text-sm font-bold text-foreground mb-3">Conclusion</h3>
        <div className="space-y-3">
          <div>
            <label className="block text-xs font-medium text-muted-foreground mb-1.5">Nivel de riesgo global *</label>
            <div className="flex gap-2 flex-wrap">
              {OVERALL_LEVELS.map(ol => (
                <button key={ol.value} type="button" disabled={isCompleted}
                  onClick={() => set('overall_risk_level', ol.value)}
                  className={cn(
                    'px-4 py-2 rounded-lg text-sm font-medium border transition-colors',
                    form.overall_risk_level === ol.value ? ol.color + ' border-current' : 'bg-card text-muted-foreground border-border hover:bg-muted',
                  )}>
                  {ol.label}
                </button>
              ))}
            </div>
          </div>
          <div>
            <label className="block text-xs font-medium text-muted-foreground mb-1.5">Dictamen *</label>
            <div className="space-y-2">
              {CONCLUSIONS.map(c => {
                const Icon = c.icon
                return (
                  <button key={c.value} type="button" disabled={isCompleted}
                    onClick={() => set('conclusion', c.value)}
                    className={cn(
                      'flex items-center gap-2.5 w-full rounded-lg border px-4 py-2.5 text-left text-sm font-medium transition-colors',
                      form.conclusion === c.value ? 'border-primary bg-primary/5 text-foreground' : 'border-border text-muted-foreground hover:bg-muted',
                    )}>
                    <Icon className={cn('h-4 w-4 shrink-0', c.color)} />
                    {c.label}
                  </button>
                )
              })}
            </div>
          </div>
          <div>
            <label className="block text-xs font-medium text-muted-foreground mb-1.5">Notas de conclusion</label>
            <textarea disabled={isCompleted} value={form.conclusion_notes ?? ''} onChange={e => set('conclusion_notes', e.target.value)}
              rows={2} className="w-full rounded-lg border border-border px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring disabled:bg-muted" />
          </div>
        </div>
      </section>

      {/* Actions */}
      {!isCompleted && (
        <div className="flex items-center gap-3 pt-2">
          <button type="button" onClick={handleSave} disabled={updateRA.isPending}
            className="rounded-lg bg-primary px-5 py-2 text-sm font-semibold text-white hover:bg-primary/90 disabled:opacity-50 transition-colors">
            {updateRA.isPending ? 'Guardando...' : 'Guardar borrador'}
          </button>
          <button type="button" onClick={handleComplete} disabled={completeRA.isPending || !form.conclusion || !form.overall_risk_level}
            className="rounded-lg bg-emerald-600 px-5 py-2 text-sm font-semibold text-white hover:bg-emerald-700 disabled:opacity-50 transition-colors">
            {completeRA.isPending ? 'Completando...' : 'Completar evaluacion'}
          </button>
        </div>
      )}
    </div>
  )
}
