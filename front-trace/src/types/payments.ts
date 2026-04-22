export interface GatewayField {
  key: string
  label: string
  type: 'text' | 'password'
  required: boolean
}

export interface GatewayCatalogItem {
  slug: string
  name: string
  description: string
  color: string
  fields: GatewayField[]
}

export interface GatewayConfigOut {
  slug: string
  display_name: string
  is_active: boolean
  configured: boolean
  credentials_masked: Record<string, string>
  updated_at: string | null
  // catalogue metadata included in list response
  name?: string
  description?: string
  color?: string
  fields?: GatewayField[]
}

export interface GatewayConfigSave {
  credentials: Record<string, string>
}

export interface ActiveGateway {
  slug: string
  display_name: string
  description: string
  color: string
}
