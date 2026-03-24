import { useState, useEffect } from 'react'
import { useNavigate, Link, useSearchParams } from 'react-router-dom'
import {
  Plus, FileText, FileDown, X, ChevronRight,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import {
  useRecords, useCreateRecord, useActivations, useFrameworks,
} from '@/hooks/useCompliance'
import { useAssetList } from '@/hooks/useAssets'
import type { ComplianceRecord, CreateRecordInput, ComplianceStatus } from '@/types/compliance'

// ─── Status badge ────────────────────────────────────────────────────────────

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

function ComplianceStatusBadge({ status }: { status: string }) {
  return (
    <span className={cn(
      'inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-semibold border',
      STATUS_COLORS[status] ?? 'bg-slate-50 text-slate-600 border-slate-200',
    )}>
      {STATUS_LABELS[status] ?? status}
    </span>
  )
}

// ─── Commodity badge ─────────────────────────────────────────────────────────

const COMMODITY_COLORS: Record<string, string> = {
  coffee: 'bg-amber-100 text-amber-800',
  cocoa: 'bg-yellow-100 text-yellow-800',
  palm_oil: 'bg-orange-100 text-orange-800',
  soy: 'bg-lime-100 text-lime-800',
  rubber: 'bg-slate-100 text-slate-700',
  cattle: 'bg-rose-100 text-rose-800',
  wood: 'bg-emerald-100 text-emerald-800',
}

const COMMODITY_LABELS: Record<string, string> = {
  coffee: 'Cafe',
  cocoa: 'Cacao',
  palm_oil: 'Aceite de palma',
  soy: 'Soja',
  rubber: 'Caucho',
  cattle: 'Ganado',
  wood: 'Madera',
}

// ─── Framework flag helpers ──────────────────────────────────────────────────

const FRAMEWORK_FLAGS: Record<string, string> = {
  eudr: '🇪🇺',
  'usda-organic': '🇺🇸',
  fssai: '🇮🇳',
  'jfs-2200': '🇯🇵',
}

// ─── Create Record Modal ─────────────────────────────────────────────────────

function CreateRecordModal({ onClose, onCreated, lockedAssetId }: { onClose: () => void; onCreated: (id: string) => void; lockedAssetId?: string }) {
  const { data: activations = [] } = useActivations()
  const { data: frameworks = [] } = useFrameworks()
  const { data: assetsData } = useAssetList({ limit: 200 })
  const create = useCreateRecord()

  const assets = assetsData?.items ?? []

  const activeFrameworks = activations
    .filter(a => a.is_active)
    .map(a => {
      const fw = frameworks.find(f => f.slug === a.framework_slug)
      return { slug: a.framework_slug, name: fw?.name ?? a.framework_slug, commodities: fw?.applicable_commodities ?? [] }
    })

  const [form, setForm] = useState({
    asset_id: lockedAssetId ?? '',
    framework_slug: '',
    commodity_type: '',
    quantity_kg: '',
    country_of_production: '',
  })

  const selectedFramework = activeFrameworks.find(f => f.slug === form.framework_slug)
  const selectedAsset = assets.find(a => a.id === form.asset_id)

  async function submit(e: React.FormEvent) {
    e.preventDefault()
    if (!form.asset_id) return
    const data: CreateRecordInput = {
      asset_id: form.asset_id,
      framework_slug: form.framework_slug,
      commodity_type: form.commodity_type || selectedAsset?.product_type || undefined,
      quantity_kg: form.quantity_kg ? Number(form.quantity_kg) : (selectedAsset?.metadata as any)?.weight ? Number((selectedAsset.metadata as any).weight) : undefined,
      country_of_production: form.country_of_production || 'CO',
    }
    const record = await create.mutateAsync(data)
    onCreated(record.id)
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm" onClick={onClose}>
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-lg mx-4" onClick={e => e.stopPropagation()}>
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-100">
          <h2 className="text-base font-bold text-slate-900">Nuevo Registro de Cumplimiento</h2>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-600"><X className="h-5 w-5" /></button>
        </div>
        <form onSubmit={submit} className="px-6 py-5 space-y-4">
          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1.5">Carga *</label>
            {lockedAssetId ? (
              <>
                <div className="w-full rounded-lg border border-primary/30 bg-primary/5 px-3 py-2 text-sm">
                  {selectedAsset
                    ? <><span className="font-medium capitalize">{selectedAsset.product_type}</span> — {(selectedAsset.metadata as any)?.name || selectedAsset.state}</>
                    : <span className="font-mono text-xs">{lockedAssetId}</span>}
                </div>
                <p className="text-xs text-muted-foreground mt-1">Carga vinculada desde el detalle del asset</p>
              </>
            ) : (
              <>
                <select required value={form.asset_id}
                  onChange={e => setForm(f => ({ ...f, asset_id: e.target.value }))}
                  className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring">
                  <option value="">Seleccionar carga...</option>
                  {assets.map(a => (
                    <option key={a.id} value={a.id}>
                      {a.product_type} — {(a.metadata as any)?.name || a.asset_mint?.slice(0, 16) + '...'} ({a.state})
                    </option>
                  ))}
                </select>
                {assets.length === 0 && (
                  <p className="text-xs text-amber-600 mt-1">No hay cargas registradas. Primero crea una carga en Logística → Cargas.</p>
                )}
              </>
            )}
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1.5">Framework *</label>
            <select required value={form.framework_slug}
              onChange={e => setForm(f => ({ ...f, framework_slug: e.target.value, commodity_type: '' }))}
              className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring">
              <option value="">Seleccionar framework</option>
              {activeFrameworks.map(fw => (
                <option key={fw.slug} value={fw.slug}>
                  {FRAMEWORK_FLAGS[fw.slug] ?? ''} {fw.name}
                </option>
              ))}
            </select>
          </div>

          {selectedFramework && selectedFramework.commodities.length > 0 && (
            <div>
              <label className="block text-xs font-medium text-slate-600 mb-1.5">Commodity</label>
              <select value={form.commodity_type}
                onChange={e => setForm(f => ({ ...f, commodity_type: e.target.value }))}
                className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring">
                <option value="">Seleccionar commodity</option>
                {selectedFramework.commodities.map(c => (
                  <option key={c} value={c}>{COMMODITY_LABELS[c] ?? c}</option>
                ))}
              </select>
            </div>
          )}

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-medium text-slate-600 mb-1.5">Cantidad (kg)</label>
              <input type="number" step="0.01" min="0" value={form.quantity_kg}
                onChange={e => setForm(f => ({ ...f, quantity_kg: e.target.value }))}
                className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring" />
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-600 mb-1.5">Pais de produccion</label>
              <input value={form.country_of_production}
                onChange={e => setForm(f => ({ ...f, country_of_production: e.target.value }))}
                placeholder="CO"
                className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring" />
            </div>
          </div>

          <div className="flex justify-end gap-2 pt-2">
            <button type="button" onClick={onClose}
              className="rounded-lg px-4 py-2 text-sm text-slate-600 hover:bg-slate-100 transition-colors">Cancelar</button>
            <button type="submit" disabled={create.isPending}
              className="rounded-lg bg-primary px-5 py-2 text-sm font-semibold text-white hover:bg-primary/90 disabled:opacity-50 transition-colors">
              {create.isPending ? 'Creando...' : 'Crear registro'}
            </button>
          </div>
          {create.isError && (
            <p className="text-xs text-red-600">{(create.error as Error).message}</p>
          )}
        </form>
      </div>
    </div>
  )
}

// ─── Records Page ────────────────────────────────────────────────────────────

export default function RecordsPage() {
  const navigate = useNavigate()
  const [searchParams, setSearchParams] = useSearchParams()
  const createForAsset = searchParams.get('create') // asset_id from query param
  const [showCreate, setShowCreate] = useState(false)

  // Auto-open modal if ?create=<asset_id> is in URL
  useEffect(() => {
    if (createForAsset) setShowCreate(true)
  }, [createForAsset])

  // Filters
  const [frameworkSlug, setFrameworkSlug] = useState('')
  const [status, setStatus] = useState('')
  const [commodity, setCommodity] = useState('')

  const { data: records = [], isLoading } = useRecords({
    framework_slug: frameworkSlug || undefined,
    status: status || undefined,
    commodity_type: commodity || undefined,
  })
  const { data: activations = [] } = useActivations()
  const { data: frameworks = [] } = useFrameworks()

  function shortId(uuid: string) {
    return uuid.slice(0, 8) + '...'
  }

  return (
    <div className="p-6 lg:p-8 space-y-6 max-w-7xl mx-auto">
      {/* Breadcrumbs */}
      <nav className="flex items-center gap-1.5 text-xs text-slate-400">
        <Link to="/cumplimiento/activaciones" className="hover:text-slate-600 transition-colors">Cumplimiento</Link>
        <ChevronRight className="h-3 w-3" />
        <span className="text-slate-700 font-medium">Registros</span>
      </nav>

      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-slate-900">Registros de Cumplimiento</h1>
          <p className="text-sm text-slate-500 mt-0.5">Gestiona los registros de due diligence por carga</p>
        </div>
        <button onClick={() => setShowCreate(true)}
          className="flex items-center gap-2 rounded-xl bg-primary px-4 py-2.5 text-sm font-semibold text-white hover:bg-primary/90 shadow-sm transition-colors">
          <Plus className="h-4 w-4" /> Nuevo Registro
        </button>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap items-center gap-3">
        <select value={frameworkSlug}
          onChange={e => setFrameworkSlug(e.target.value)}
          className="rounded-lg border border-slate-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring">
          <option value="">Todos los frameworks</option>
          {frameworks.map(fw => (
            <option key={fw.slug} value={fw.slug}>
              {FRAMEWORK_FLAGS[fw.slug] ?? ''} {fw.name}
            </option>
          ))}
        </select>

        <select value={status}
          onChange={e => setStatus(e.target.value)}
          className="rounded-lg border border-slate-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring">
          <option value="">Todos los estados</option>
          {Object.entries(STATUS_LABELS).map(([k, v]) => (
            <option key={k} value={k}>{v}</option>
          ))}
        </select>

        <select value={commodity}
          onChange={e => setCommodity(e.target.value)}
          className="rounded-lg border border-slate-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring">
          <option value="">Todas las commodities</option>
          {Object.entries(COMMODITY_LABELS).map(([k, v]) => (
            <option key={k} value={k}>{v}</option>
          ))}
        </select>

        {(frameworkSlug || status || commodity) && (
          <button onClick={() => { setFrameworkSlug(''); setStatus(''); setCommodity('') }}
            className="text-xs text-slate-500 hover:text-slate-700 underline">
            Limpiar filtros
          </button>
        )}
      </div>

      {/* Table */}
      {isLoading ? (
        <div className="text-sm text-slate-400 py-12 text-center">Cargando...</div>
      ) : records.length === 0 ? (
        <div className="rounded-2xl border-2 border-dashed border-slate-200 p-14 text-center">
          <FileText className="h-10 w-10 text-slate-200 mx-auto mb-3" />
          <p className="text-sm font-medium text-slate-600 mb-1">Sin registros</p>
          <p className="text-xs text-slate-400 mb-5">Crea un registro de cumplimiento para una carga.</p>
          <button onClick={() => setShowCreate(true)}
            className="inline-flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-xs font-semibold text-white hover:bg-primary/90">
            <Plus className="h-3.5 w-3.5" /> Nuevo Registro
          </button>
        </div>
      ) : (
        <div className="bg-white rounded-2xl border border-slate-100 shadow-sm overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-slate-50 border-b border-slate-100">
              <tr>
                <th className="px-5 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide">Asset ID</th>
                <th className="px-5 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide">Framework</th>
                <th className="px-5 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide">Commodity</th>
                <th className="px-5 py-3 text-right text-xs font-semibold text-slate-500 uppercase tracking-wide">Cantidad kg</th>
                <th className="px-5 py-3 text-center text-xs font-semibold text-slate-500 uppercase tracking-wide">Estado</th>
                <th className="px-5 py-3 text-center text-xs font-semibold text-slate-500 uppercase tracking-wide">Parcelas</th>
                <th className="px-5 py-3 text-center text-xs font-semibold text-slate-500 uppercase tracking-wide">Certificado</th>
                <th className="px-5 py-3 text-right text-xs font-semibold text-slate-500 uppercase tracking-wide">Acciones</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-50">
              {records.map(r => {
                const fw = frameworks.find(f => f.slug === r.framework_slug)
                return (
                  <tr key={r.id} className="hover:bg-slate-50/50 transition-colors">
                    <td className="px-5 py-3">
                      <Link to={`/assets/${r.asset_id}`}
                        className="font-mono text-xs text-primary hover:underline" title={r.asset_id}>
                        {shortId(r.asset_id)}
                      </Link>
                    </td>
                    <td className="px-5 py-3">
                      <span className="text-sm">
                        {FRAMEWORK_FLAGS[r.framework_slug] ?? ''}{' '}
                        {fw?.name ?? r.framework_slug}
                      </span>
                    </td>
                    <td className="px-5 py-3">
                      {r.commodity_type ? (
                        <span className={cn(
                          'inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-medium',
                          COMMODITY_COLORS[r.commodity_type] ?? 'bg-slate-100 text-slate-600',
                        )}>
                          {COMMODITY_LABELS[r.commodity_type] ?? r.commodity_type}
                        </span>
                      ) : (
                        <span className="text-slate-300">--</span>
                      )}
                    </td>
                    <td className="px-5 py-3 text-right tabular-nums text-slate-700">
                      {r.quantity_kg != null ? Number(r.quantity_kg).toLocaleString('es-CO') : '--'}
                    </td>
                    <td className="px-5 py-3 text-center">
                      <ComplianceStatusBadge status={r.compliance_status} />
                    </td>
                    <td className="px-5 py-3 text-center text-xs text-slate-500">
                      {(r.missing_fields ?? []).length === 0 ? '--' : '--'}
                    </td>
                    <td className="px-5 py-3 text-center">
                      {r.validation_result && (r.compliance_status === 'compliant' || r.compliance_status === 'declared') ? (
                        <FileDown className="h-4 w-4 text-emerald-500 mx-auto" title="Certificado disponible" />
                      ) : (
                        <span className="text-slate-300">--</span>
                      )}
                    </td>
                    <td className="px-5 py-3 text-right">
                      <button onClick={() => navigate(`/cumplimiento/registros/${r.id}`)}
                        className="text-xs font-semibold text-primary hover:text-primary hover:underline transition-colors">
                        Ver detalle
                      </button>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}

      {/* Create modal */}
      {showCreate && (
        <CreateRecordModal
          lockedAssetId={createForAsset || undefined}
          onClose={() => {
            setShowCreate(false)
            if (createForAsset) setSearchParams({})
          }}
          onCreated={(id) => {
            setShowCreate(false)
            if (createForAsset) setSearchParams({})
            navigate(`/cumplimiento/registros/${id}`)
          }}
        />
      )}
    </div>
  )
}
