import { useState, useMemo } from 'react'
import { Link } from 'react-router-dom'
import { ArrowRight, Search, Users, X } from 'lucide-react'
import { Topbar } from '@/components/layout/Topbar'
import { Spinner, EmptyState } from '@/components/ui/Misc'
import { Button } from '@/components/ui/Button'
import { usePartners } from '@/hooks/useInventory'
import { cn } from '@/lib/utils'

export function PortalListPage() {
  const [search, setSearch] = useState('')
  const { data, isLoading } = usePartners({ is_customer: true, is_active: true })

  const items = useMemo(() => {
    const all = data?.items ?? []
    if (!search) return all
    const q = search.toLowerCase()
    return all.filter(p =>
      p.name.toLowerCase().includes(q)
      || p.code.toLowerCase().includes(q)
      || (p.email ?? '').toLowerCase().includes(q),
    )
  }, [data, search])

  return (
    <div className="flex flex-col flex-1 overflow-hidden">
      <Topbar
        title="Portal de Clientes"
        subtitle="Vistas de autogestión por cliente — stock disponible y pedidos"
      />

      <div className="flex-1 overflow-y-auto p-6 space-y-4">
        <div className="relative max-w-md">
          <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground pointer-events-none" />
          <input
            value={search}
            onChange={e => setSearch(e.target.value)}
            placeholder="Buscar cliente por nombre, código o email…"
            className="h-9 pl-8 pr-8 w-full text-sm rounded-md border border-border bg-card outline-none focus:ring-2 focus:ring-ring/30 focus:border-primary"
          />
          {search && (
            <button
              onClick={() => setSearch('')}
              className="absolute right-2 top-1/2 -translate-y-1/2 h-5 w-5 rounded-full inline-flex items-center justify-center text-muted-foreground hover:bg-muted"
            >
              <X className="h-3 w-3" />
            </button>
          )}
        </div>

        {isLoading ? (
          <div className="flex justify-center py-20"><Spinner /></div>
        ) : items.length === 0 ? (
          <EmptyState
            icon={<Users className="h-12 w-12" />}
            title={search ? 'Sin coincidencias' : 'No hay clientes registrados'}
            description={
              search
                ? 'Probá con otro término.'
                : 'Marcá un socio como "cliente" desde Compras y Ventas › Socios para que aparezca acá.'
            }
            action={!search ? (
              <Link to="/inventario/socios">
                <Button size="sm">Ir a Socios</Button>
              </Link>
            ) : undefined}
          />
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            {items.map(p => (
              <Link
                key={p.id}
                to={`/inventario/portal/${p.id}`}
                className={cn(
                  'group rounded-xl border border-border bg-card p-4 hover:border-primary/40 hover:shadow-sm transition',
                )}
              >
                <div className="flex items-start gap-3">
                  <div className="h-10 w-10 rounded-full bg-primary/10 text-primary inline-flex items-center justify-center font-semibold shrink-0">
                    {p.name[0]?.toUpperCase() ?? '?'}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-semibold text-foreground truncate">{p.name}</p>
                    <p className="text-xs text-muted-foreground font-mono tabular-nums truncate">{p.code}</p>
                    {p.email && (
                      <p className="text-[11px] text-muted-foreground truncate mt-0.5">{p.email}</p>
                    )}
                  </div>
                  <ArrowRight className="h-4 w-4 text-muted-foreground/60 group-hover:text-primary group-hover:translate-x-0.5 transition" />
                </div>
              </Link>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
