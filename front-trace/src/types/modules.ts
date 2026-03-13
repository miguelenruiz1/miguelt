// Module marketplace type definitions

export interface ModuleDefinition {
  slug: string
  name: string
  description: string
}

export interface TenantModuleStatus extends ModuleDefinition {
  is_active: boolean
}
