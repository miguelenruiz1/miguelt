import {
  Package, MapPin, Link2, Paperclip, ShieldAlert, FileText, Award,
  CheckCircle2, AlertCircle, Circle,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import type { ComplianceRecord, DocumentLink, RiskAssessment, SupplyChainNode, PlotLink } from '@/types/compliance'

interface Step {
  key: string
  label: string
  icon: typeof Package
  status: 'complete' | 'partial' | 'missing' | 'disabled'
  tooltip?: string
}

interface Props {
  record: ComplianceRecord
  plots: PlotLink[]
  supplyChain: SupplyChainNode[]
  documents: DocumentLink[]
  riskAssessment: RiskAssessment | null
  activeTab: string
  onTabChange: (tab: string) => void
}

export default function ComplianceProgressTracker({
  record, plots, supplyChain, documents, riskAssessment, activeTab, onTabChange,
}: Props) {
  // Evaluate each step
  const steps: Step[] = [
    {
      key: 'product',
      label: 'Producto',
      icon: Package,
      status: (record.hs_code && record.commodity_type && record.quantity_kg && record.country_of_production)
        ? 'complete'
        : (record.hs_code || record.commodity_type) ? 'partial' : 'missing',
    },
    {
      key: 'plots',
      label: 'Parcelas',
      icon: MapPin,
      status: plots.length > 0 ? 'complete' : 'missing',
      tooltip: plots.length === 0 ? 'Vincula al menos 1 parcela' : undefined,
    },
    {
      key: 'supply_chain',
      label: 'Cadena',
      icon: Link2,
      status: (() => {
        const roles = supplyChain.map(n => n.role)
        const hasProducer = roles.includes('producer')
        const hasExporter = roles.includes('exporter') || roles.includes('importer')
        if (hasProducer && hasExporter) return 'complete'
        if (supplyChain.length > 0) return 'partial'
        return 'missing'
      })(),
      tooltip: supplyChain.length === 0 ? 'Agrega al menos productor + exportador' : undefined,
    },
    {
      key: 'documents',
      label: 'Documentos',
      icon: Paperclip,
      status: documents.length > 0 ? 'complete' : 'missing',
      tooltip: documents.length === 0 ? 'Adjunta al menos 1 documento de evidencia' : undefined,
    },
    {
      key: 'risk',
      label: 'Riesgo',
      icon: ShieldAlert,
      status: (() => {
        if (!riskAssessment) return 'missing'
        if (riskAssessment.status === 'completed' && (riskAssessment.conclusion === 'approved' || riskAssessment.conclusion === 'conditional')) return 'complete'
        if (riskAssessment.status === 'draft') return 'partial'
        return 'missing'
      })(),
    },
    {
      key: 'declaration',
      label: 'Declaraciones',
      icon: FileText,
      status: (record.deforestation_free_declaration && record.legal_compliance_declaration &&
        (record as any).signatory_name)
        ? 'complete'
        : (record.deforestation_free_declaration || record.legal_compliance_declaration) ? 'partial' : 'missing',
    },
    {
      key: 'certificate',
      label: 'Certificado',
      icon: Award,
      status: record.compliance_status === 'compliant' ? 'complete' : 'disabled',
    },
  ]

  const completedCount = steps.filter(s => s.status === 'complete').length
  const totalSteps = steps.length - 1 // exclude certificate step from progress
  const progress = Math.round((completedCount / totalSteps) * 100)

  return (
    <div className="space-y-3">
      {/* Progress bar */}
      <div className="flex items-center gap-3">
        <div className="flex-1 h-2 bg-slate-100 rounded-full overflow-hidden">
          <div
            className={cn(
              'h-full rounded-full transition-all duration-500',
              progress === 100 ? 'bg-green-500' : progress >= 60 ? 'bg-amber-500' : 'bg-primary',
            )}
            style={{ width: `${progress}%` }}
          />
        </div>
        <span className="text-xs font-semibold text-slate-500 tabular-nums">{progress}%</span>
      </div>

      {/* Steps */}
      <div className="flex gap-1">
        {steps.map((step) => {
          const Icon = step.icon
          const isActive = activeTab === step.key
          const StatusIcon = step.status === 'complete' ? CheckCircle2
            : step.status === 'partial' ? AlertCircle
              : Circle

          return (
            <button
              key={step.key}
              onClick={() => onTabChange(step.key)}
              title={step.tooltip ?? step.label}
              className={cn(
                'flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-medium transition-all',
                isActive
                  ? 'bg-primary/10 text-primary ring-1 ring-primary/30'
                  : 'hover:bg-slate-50 text-slate-500',
              )}
            >
              <StatusIcon className={cn(
                'h-3.5 w-3.5 shrink-0',
                step.status === 'complete' ? 'text-green-500' :
                  step.status === 'partial' ? 'text-amber-500' :
                    step.status === 'disabled' ? 'text-slate-300' : 'text-slate-300',
              )} />
              <Icon className="h-3.5 w-3.5 shrink-0" />
              <span className="hidden md:inline">{step.label}</span>
            </button>
          )
        })}
      </div>
    </div>
  )
}
