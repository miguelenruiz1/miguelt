import { Link } from 'react-router-dom'
import { Package, ArrowRight } from 'lucide-react'
import { StateBadge } from '@/components/domain-badges'
import { HashChip } from '@/components/ui/misc'
import { shortPubkey, fmtDateShort } from '@/lib/utils'
import type { Asset } from '@/types/api'

export function AssetCard({ asset }: { asset: Asset }) {
  return (
    <div className="relative group perspective-1000 h-full">
      <Link
        to={`/assets/${asset.id}`}
        className="block h-full rounded-3xl bg-card/70 backdrop-blur-xl border border-white/60  p-5 ring-1 ring-slate-900/5 transition-all duration-300 hover:-translate-y-1.5 hover:shadow-[0_10px_40px_-10px_rgba(79,70,229,0.15)] hover:bg-card/90 overflow-hidden"
      >
        {/* Header */}
        <div className="flex items-start justify-between gap-3 mb-5">
          <div className="flex items-center gap-3.5 min-w-0">
            <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-gradient-to-br from-primary/10 to-primary/5 shadow-inner shrink-0 group-hover:scale-110 group-hover:rotate-3 transition-transform duration-300">
              <Package className="h-5 w-5 text-primary drop-" />
            </div>
            <div className="min-w-0">
              <p className="font-mono text-sm text-foreground font-bold tracking-tight truncate group-hover:text-primary transition-colors" title={asset.asset_mint}>
                {asset.asset_mint.length > 20 ? `${asset.asset_mint.slice(0, 20)}…` : asset.asset_mint}
              </p>
              <p className="text-xs font-semibold text-muted-foreground mt-0.5 uppercase tracking-wider">{asset.product_type}</p>
            </div>
          </div>
          <div className="scale-90 origin-top-right">
            <StateBadge state={asset.state} />
          </div>
        </div>

        {/* Custodian */}
        <div className="flex flex-col gap-0.5 mt-2 mb-4 bg-muted/50 rounded-xl p-3 border border-border/50">
          <span className="text-[10px] font-bold text-muted-foreground uppercase tracking-widest">Custodio Actual</span>
          <span className="font-mono text-xs text-foreground font-medium">{shortPubkey(asset.current_custodian_wallet)}</span>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between mt-auto pt-4 border-t border-border/60">
          <div className="flex items-center gap-3">
            {asset.last_event_hash && (
              <HashChip hash={asset.last_event_hash} head={5} tail={4} />
            )}
            <span className="text-[11px] font-medium text-muted-foreground bg-secondary/50 px-2 py-0.5 rounded-md">{fmtDateShort(asset.updated_at)}</span>
          </div>
          <div className="flex h-6 w-6 items-center justify-center rounded-full bg-muted group-hover:bg-primary/10 transition-colors">
            <ArrowRight className="h-3.5 w-3.5 text-slate-300 group-hover:text-primary group-hover:translate-x-0.5 transition-all duration-300" />
          </div>
        </div>
      </Link>
    </div>
  )
}
