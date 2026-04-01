import { Link, useParams, Navigate } from 'react-router-dom'
import { ChevronRight, Settings2 } from 'lucide-react'
import { CONFIG_SECTIONS, CONFIG_SECTION_COMPONENTS } from './InventoryConfigPage'
import type { ConfigSectionId } from './InventoryConfigPage'

export function ConfigSectionPage() {
  const { section } = useParams<{ section: string }>()

  const sectionConfig = CONFIG_SECTIONS.find(s => s.id === section)
  if (!sectionConfig) return <Navigate to="/inventario/configuracion" replace />

  const component = CONFIG_SECTION_COMPONENTS[sectionConfig.id as ConfigSectionId]

  return (
    <div className="p-8 space-y-6 max-w-5xl mx-auto">
      {/* Breadcrumbs */}
      <nav className="flex items-center gap-1.5 text-xs text-muted-foreground">
        <Link to="/inventario/configuracion" className="hover:text-muted-foreground transition-colors">Configuración</Link>
        <ChevronRight className="h-3 w-3" />
        <span className="text-foreground font-medium">{sectionConfig.label}</span>
      </nav>

      {/* Header */}
      <div className="flex items-center gap-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-secondary">
          <sectionConfig.icon className="h-5 w-5 text-muted-foreground" />
        </div>
        <div>
          <h1 className="text-xl font-bold text-foreground">{sectionConfig.label}</h1>
          <p className="text-sm text-muted-foreground">{sectionConfig.description}</p>
        </div>
      </div>

      {/* Content */}
      <div className="bg-card rounded-2xl border border-border  p-6">
        {component}
      </div>
    </div>
  )
}
