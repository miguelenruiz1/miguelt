export interface EmailProviderField {
  key: string
  label: string
  type: 'text' | 'password'
  required: boolean
}

export interface EmailProviderCatalogItem {
  slug: string
  name: string
  description: string
  color: string
  fields: EmailProviderField[]
}

export interface EmailProviderConfigOut {
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
  fields?: EmailProviderField[]
}

export interface EmailProviderConfigSave {
  credentials: Record<string, string>
}

export interface TestEmailResult {
  ok: boolean
  provider?: string
  error?: string
}
