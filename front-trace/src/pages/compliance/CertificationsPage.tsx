import { useMemo, useState } from 'react'
import { Award, ShieldCheck, ExternalLink } from 'lucide-react'
import { useCertifications } from '@/hooks/useCompliance'
import type { CertificationScheme } from '@/types/compliance'

const AMBITO_LABELS: Record<string, string> = {
  land_use_rights: 'Uso suelo',
  environmental_protection: 'Ambiente',
  labor_rights: 'Laboral',
  human_rights: 'DDHH',
  third_party_rights_fpic: 'Terceros / FPIC',
  fiscal_customs_anticorruption: 'Fiscal',
}

const SCOPE_LABELS: Record<string, string> = {
  legality: 'Legalidad',
  chain_of_custody: 'Cadena de custodia',
  sustainability: 'Sostenibilidad',
  full: 'Completo',
}

function ScoreBadge({ label, value }: { label: string; value: number }) {
  const color =
    value >= 3 ? 'bg-emerald-100 text-emerald-800 border-emerald-300'
    : value >= 2 ? 'bg-lime-100 text-lime-800 border-lime-300'
    : value >= 1 ? 'bg-amber-100 text-amber-800 border-amber-300'
    : 'bg-red-100 text-red-800 border-red-300'
  return (
    <div className={`flex-1 rounded-md border px-2 py-1 ${color}`}>
      <div className="text-[9px] font-semibold uppercase tracking-wide">{label}</div>
      <div className="text-sm font-bold">{value}/3</div>
    </div>
  )
}

function SchemeCard({ scheme }: { scheme: CertificationScheme }) {
  const totalColor =
    scheme.total_score >= 10 ? 'text-emerald-700'
    : scheme.total_score >= 7 ? 'text-lime-700'
    : scheme.total_score >= 4 ? 'text-amber-700'
    : 'text-red-700'

  return (
    <div className="bg-card rounded-xl border border-border p-5 space-y-4">
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <ShieldCheck className="h-4 w-4 text-indigo-600 shrink-0" />
            <h3 className="text-sm font-bold text-foreground truncate">{scheme.name}</h3>
          </div>
          <div className="flex flex-wrap gap-1 text-[10px]">
            <span className="inline-flex rounded-full bg-muted px-2 py-0.5 text-muted-foreground">
              {SCOPE_LABELS[scheme.scope] ?? scheme.scope}
            </span>
            {scheme.commodities.map((c) => (
              <span key={c} className="inline-flex rounded-full bg-indigo-50 px-2 py-0.5 text-indigo-700">
                {c}
              </span>
            ))}
          </div>
        </div>
        <div className={`text-right ${totalColor}`}>
          <div className="text-[10px] font-semibold uppercase">Score</div>
          <div className="text-2xl font-bold leading-none">{scheme.total_score}<span className="text-xs text-muted-foreground">/12</span></div>
        </div>
      </div>

      <div className="flex gap-1.5">
        <ScoreBadge label="Ownership" value={scheme.ownership_score} />
        <ScoreBadge label="Transp." value={scheme.transparency_score} />
        <ScoreBadge label="Audit" value={scheme.audit_score} />
        <ScoreBadge label="Quejas" value={scheme.grievance_score} />
      </div>

      {scheme.covers_eudr_ambitos.length > 0 && (
        <div>
          <div className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wide mb-1">
            Ambitos EUDR cubiertos
          </div>
          <div className="flex flex-wrap gap-1">
            {scheme.covers_eudr_ambitos.map((a) => (
              <span key={a} className="inline-flex rounded-full bg-slate-100 px-2 py-0.5 text-[10px] font-medium text-slate-700">
                {AMBITO_LABELS[a] ?? a}
              </span>
            ))}
          </div>
        </div>
      )}

      {scheme.notes && (
        <p className="text-xs text-muted-foreground leading-snug">{scheme.notes}</p>
      )}

      {scheme.reference_url && (
        <a
          href={scheme.reference_url}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-1 text-xs text-indigo-600 hover:underline"
        >
          Mas informacion <ExternalLink className="h-3 w-3" />
        </a>
      )}
    </div>
  )
}

export default function CertificationsPage() {
  const { data, isLoading } = useCertifications()
  const [commodityFilter, setCommodityFilter] = useState<string>('all')

  const commodities = useMemo(() => {
    const set = new Set<string>()
    for (const s of data ?? []) for (const c of s.commodities) set.add(c)
    return Array.from(set).sort()
  }, [data])

  const filtered = useMemo(() => {
    if (commodityFilter === 'all') return data ?? []
    return (data ?? []).filter((s) => s.commodities.includes(commodityFilter))
  }, [data, commodityFilter])

  return (
    <div className="space-y-6">
      <div>
        <div className="flex items-center gap-3 mb-2">
          <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-indigo-50">
            <Award className="h-5 w-5 text-indigo-600" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-foreground">Esquemas de certificacion</h1>
            <p className="text-sm text-muted-foreground">
              Registro de credibilidad de esquemas de certificacion segun criterios EFI/MITECO
            </p>
          </div>
        </div>
        <div className="rounded-lg bg-indigo-50 border border-indigo-200 px-4 py-3 text-xs text-indigo-900 leading-relaxed">
          <strong>Marco de credibilidad:</strong> cada esquema se evalua en 4 ejes
          (0-3 por eje, total 0-12): ownership (quien lo gobierna),
          transparencia (acceso publico a auditorias y reglas), audit independence
          (auditores externos vs internos), grievance mechanism (quejas + remediacion).
          Un esquema puede aceptarse como evidencia parcial de legalidad EUDR, pero
          no sustituye la debida diligencia del operador.
        </div>
      </div>

      {commodities.length > 0 && (
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-xs text-muted-foreground">Commodity:</span>
          {['all', ...commodities].map((c) => (
            <button
              key={c}
              onClick={() => setCommodityFilter(c)}
              className={`text-xs px-3 py-1 rounded-full border transition ${
                commodityFilter === c
                  ? 'bg-indigo-600 text-white border-indigo-600'
                  : 'bg-card text-muted-foreground border-border hover:border-indigo-300'
              }`}
            >
              {c === 'all' ? 'Todos' : c}
            </button>
          ))}
        </div>
      )}

      {isLoading ? (
        <div className="flex justify-center py-12 text-muted-foreground">Cargando...</div>
      ) : filtered.length === 0 ? (
        <div className="flex justify-center py-12 text-muted-foreground">
          No hay esquemas que coincidan con el filtro.
        </div>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {filtered.map((s) => <SchemeCard key={s.id} scheme={s} />)}
        </div>
      )}
    </div>
  )
}
