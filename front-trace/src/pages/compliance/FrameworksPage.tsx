import { useState } from 'react'
import { Shield, Check, X, Eye, Zap } from 'lucide-react'
import { useFrameworks, useActivations, useActivateFramework } from '@/hooks/useCompliance'
import { useToast } from '@/store/toast'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import type { ComplianceFramework } from '@/types/compliance'

// ─── Flag emoji mapping ──────────────────────────────────────────────────────

const marketFlags: Record<string, string> = {
  EU: '\u{1F1EA}\u{1F1FA}',
  US: '\u{1F1FA}\u{1F1F8}',
  JP: '\u{1F1EF}\u{1F1F5}',
  IN: '\u{1F1EE}\u{1F1F3}',
  CO: '\u{1F1E8}\u{1F1F4}',
  BR: '\u{1F1E7}\u{1F1F7}',
  UK: '\u{1F1EC}\u{1F1E7}',
}

function flagFor(markets: string[]): string {
  for (const m of markets) {
    const upper = m.toUpperCase()
    if (marketFlags[upper]) return marketFlags[upper]
  }
  return '\u{1F310}'
}

// ─── Commodity badge variant ─────────────────────────────────────────────────

const commodityVariant: Record<string, 'success' | 'warning' | 'info' | 'purple' | 'cyan' | 'default'> = {
  coffee: 'success',
  cocoa: 'warning',
  palm_oil: 'danger' as any,
  soy: 'info',
  rubber: 'purple',
  cattle: 'cyan',
  wood: 'default',
}

function commodityLabel(c: string): string {
  const labels: Record<string, string> = {
    coffee: 'Cafe',
    cocoa: 'Cacao',
    palm_oil: 'Palma',
    soy: 'Soya',
    rubber: 'Caucho',
    cattle: 'Ganado',
    wood: 'Madera',
  }
  return labels[c] ?? c
}

// ─── Component ───────────────────────────────────────────────────────────────

export default function FrameworksPage() {
  const { data: frameworks = [], isLoading } = useFrameworks()
  const { data: activations = [] } = useActivations()
  const activate = useActivateFramework()
  const toast = useToast()
  const [activating, setActivating] = useState<string | null>(null)

  const activeSlugs = new Set(activations.filter(a => a.is_active).map(a => a.framework_slug))

  async function handleActivate(fw: ComplianceFramework) {
    setActivating(fw.slug)
    try {
      await activate.mutateAsync({ framework_slug: fw.slug })
      toast.success(`${fw.name} activado correctamente`)
    } catch (e: any) {
      toast.error(e.message ?? 'Error al activar')
    } finally {
      setActivating(null)
    }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-primary/10">
            <Shield className="h-5 w-5 text-primary" />
          </div>
          <div>
            <h1 className="text-lg font-semibold text-foreground">Marcos Normativos</h1>
            <p className="text-sm text-muted-foreground">Regulaciones disponibles para trazabilidad y cumplimiento</p>
          </div>
        </div>
      </div>

      {/* Loading */}
      {isLoading && (
        <div className="flex items-center justify-center py-16">
          <div className="h-6 w-6 animate-spin rounded-full border-2 border-primary border-t-transparent" />
        </div>
      )}

      {/* Empty */}
      {!isLoading && frameworks.length === 0 && (
        <div className="rounded-xl bg-card  border border-border/60 py-16 text-center text-sm text-muted-foreground">
          No hay marcos normativos disponibles.
        </div>
      )}

      {/* Cards grid */}
      {!isLoading && frameworks.length > 0 && (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {frameworks.map((fw) => {
            const isActive = activeSlugs.has(fw.slug)
            return (
              <div
                key={fw.id}
                className="rounded-xl border border-border/60 bg-card  p-5 flex flex-col gap-4 transition-all hover:shadow-md"
              >
                {/* Title row */}
                <div className="flex items-start justify-between gap-2">
                  <div className="flex items-center gap-2 min-w-0">
                    <span className="text-xl shrink-0">{flagFor(fw.target_markets)}</span>
                    <div className="min-w-0">
                      <h3 className="text-sm font-semibold text-foreground truncate">{fw.name}</h3>
                      {fw.issuing_body && (
                        <p className="text-xs text-muted-foreground truncate">{fw.issuing_body}</p>
                      )}
                    </div>
                  </div>
                  {isActive && <Badge variant="success" dot>Activo</Badge>}
                </div>

                {/* Commodities */}
                {fw.applicable_commodities.length > 0 && (
                  <div className="flex flex-wrap gap-1.5">
                    {fw.applicable_commodities.map((c) => (
                      <Badge key={c} variant={commodityVariant[c] ?? 'default'}>
                        {commodityLabel(c)}
                      </Badge>
                    ))}
                  </div>
                )}

                {/* Requirements */}
                <div className="space-y-1.5">
                  <div className="flex items-center gap-2 text-xs text-muted-foreground">
                    {fw.requires_geolocation ? (
                      <Check className="h-3.5 w-3.5 text-emerald-500 shrink-0" />
                    ) : (
                      <X className="h-3.5 w-3.5 text-gray-300 shrink-0" />
                    )}
                    <span>Geolocalizacion requerida</span>
                  </div>
                  <div className="flex items-center gap-2 text-xs text-muted-foreground">
                    {fw.requires_dds ? (
                      <Check className="h-3.5 w-3.5 text-emerald-500 shrink-0" />
                    ) : (
                      <X className="h-3.5 w-3.5 text-gray-300 shrink-0" />
                    )}
                    <span>Due Diligence Statement (DDS)</span>
                  </div>
                </div>

                {/* Legal reference */}
                {fw.legal_reference && (
                  <p className="text-[11px] text-muted-foreground truncate" title={fw.legal_reference}>
                    {fw.legal_reference}
                  </p>
                )}

                {/* Action */}
                <div className="mt-auto pt-2">
                  {isActive ? (
                    <Button
                      variant="secondary"
                      size="sm"
                      className="w-full"
                      onClick={() => {/* navigate to detail */}}
                    >
                      <Eye className="h-3.5 w-3.5 mr-1.5" />
                      Ver detalle
                    </Button>
                  ) : (
                    <Button
                      variant="primary"
                      size="sm"
                      className="w-full"
                      loading={activating === fw.slug}
                      onClick={() => handleActivate(fw)}
                    >
                      <Zap className="h-3.5 w-3.5 mr-1.5" />
                      Activar
                    </Button>
                  )}
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
