// Compliance service type definitions

export type FrameworkSlug = 'eudr' | 'usda-organic' | 'fssai' | 'jfs-2200' | string

export type CommodityType =
  | 'coffee'
  | 'cocoa'
  | 'palm_oil'
  | 'soy'
  | 'rubber'
  | 'cattle'
  | 'wood'
  | string

export type RiskLevel = 'low' | 'standard' | 'high' | 'critical' | string

export type GeolocationType = 'point' | 'polygon' | 'multipolygon' | string

export type ComplianceStatus = 'compliant' | 'partial' | 'incomplete' | 'non_compliant' | string

export type DeclarationStatus =
  | 'not_required'
  | 'pending'
  | 'submitted'
  | 'accepted'
  | 'rejected'
  | string

export type CertificateStatus = 'active' | 'revoked' | 'superseded' | 'expired' | string

// ─── Responses ──────────────────────────────────────────────────────────────

export interface ComplianceFramework {
  id: string
  slug: string
  name: string
  description: string | null
  issuing_body: string | null
  target_markets: string[]
  applicable_commodities: string[]
  requires_geolocation: boolean
  requires_dds: boolean
  requires_scientific_name: boolean
  document_retention_years: number
  cutoff_date: string | null
  legal_reference: string | null
  validation_rules: Record<string, unknown>
  is_active: boolean
  version: string
  created_at: string
  updated_at: string
}

export interface TenantFrameworkActivation {
  id: string
  tenant_id: string
  framework_id: string
  is_active: boolean
  export_destination: string[] | null
  activated_at: string
  activated_by: string | null
  metadata_: Record<string, unknown>
  framework_slug: string
}

export interface CompliancePlot {
  id: string
  tenant_id: string
  organization_id: string | null
  plot_code: string
  plot_area_ha: number | null
  geolocation_type: GeolocationType
  lat: number | null
  lng: number | null
  geojson_arweave_url: string | null
  geojson_hash: string | null
  country_code: string
  region: string | null
  municipality: string | null
  land_title_number: string | null
  land_title_hash: string | null
  deforestation_free: boolean
  cutoff_date_compliant: boolean
  legal_land_use: boolean
  risk_level: RiskLevel
  satellite_report_url: string | null
  satellite_report_hash: string | null
  satellite_verified_at: string | null
  is_active: boolean
  metadata_: Record<string, unknown>
  created_at: string
  updated_at: string
}

export interface ComplianceRecord {
  id: string
  tenant_id: string
  asset_id: string
  framework_id: string
  framework_slug: string
  hs_code: string | null
  commodity_type: string | null
  product_description: string | null
  scientific_name: string | null
  quantity_kg: number | null
  quantity_unit: string
  country_of_production: string | null
  production_period_start: string | null
  production_period_end: string | null
  supplier_name: string | null
  supplier_address: string | null
  supplier_email: string | null
  buyer_name: string | null
  buyer_address: string | null
  buyer_email: string | null
  operator_eori: string | null
  deforestation_free_declaration: boolean
  legal_compliance_declaration: boolean
  legal_cert_hash: string | null
  deforestation_evidence_hash: string | null
  declaration_reference: string | null
  declaration_submission_date: string | null
  declaration_status: DeclarationStatus
  declaration_url: string | null
  compliance_status: ComplianceStatus
  last_validated_at: string | null
  validation_result: Record<string, unknown> | null
  missing_fields: string[] | null
  documents_retention_until: string | null
  metadata_: Record<string, unknown>
  created_at: string
  updated_at: string
}

export interface PlotLink {
  id: string
  tenant_id: string
  record_id: string
  plot_id: string
  quantity_from_plot_kg: number | null
  percentage_from_plot: number | null
}

export interface ValidationResult {
  valid: boolean
  compliance_status: ComplianceStatus
  missing_fields: string[]
  missing_plots: boolean
  warnings: string[]
  framework: string
  checked_at: string
}

export interface ComplianceCertificate {
  id: string
  tenant_id: string
  record_id: string
  certificate_number: string
  framework_slug: string
  asset_id: string
  status: CertificateStatus
  pdf_url: string | null
  pdf_hash: string | null
  pdf_size_bytes: number | null
  verify_url: string
  qr_code_url: string | null
  valid_from: string
  valid_until: string
  generated_at: string | null
  generated_by: string | null
  generation_error: string | null
  solana_cnft_address: string | null
  solana_tx_sig: string | null
  metadata: Record<string, unknown>
  created_at: string
  updated_at: string
}

export interface CertificateListResponse {
  items: ComplianceCertificate[]
  total: number
}

export interface PublicVerification {
  valid: boolean
  status: string
  certificate_number: string
  framework: string | null
  commodity_type: string | null
  quantity_kg: number | null
  country_of_production: string | null
  valid_from: string | null
  valid_until: string | null
  deforestation_free: boolean | null
  legal_compliance: boolean | null
  plots_count: number | null
  blockchain: {
    cnft_address: string | null
    tx_signature: string | null
  } | null
  pdf_url: string | null
  generated_at: string | null
  message: string | null
}

// ─── Input types ────────────────────────────────────────────────────────────

export interface CreatePlotInput {
  plot_code: string
  organization_id?: string | null
  plot_area_ha?: number | null
  geolocation_type?: string
  lat?: number | null
  lng?: number | null
  geojson_arweave_url?: string | null
  geojson_hash?: string | null
  country_code?: string
  region?: string | null
  municipality?: string | null
  land_title_number?: string | null
  land_title_hash?: string | null
  deforestation_free?: boolean
  cutoff_date_compliant?: boolean
  legal_land_use?: boolean
  risk_level?: string
  satellite_report_url?: string | null
  satellite_report_hash?: string | null
  metadata?: Record<string, unknown> | null
}

export interface UpdatePlotInput {
  plot_code?: string | null
  organization_id?: string | null
  plot_area_ha?: number | null
  geolocation_type?: string | null
  lat?: number | null
  lng?: number | null
  geojson_arweave_url?: string | null
  geojson_hash?: string | null
  country_code?: string | null
  region?: string | null
  municipality?: string | null
  land_title_number?: string | null
  land_title_hash?: string | null
  deforestation_free?: boolean | null
  cutoff_date_compliant?: boolean | null
  legal_land_use?: boolean | null
  risk_level?: string | null
  satellite_report_url?: string | null
  satellite_report_hash?: string | null
  metadata?: Record<string, unknown> | null
}

export interface CreateRecordInput {
  asset_id: string
  framework_slug: string
  hs_code?: string | null
  commodity_type?: string | null
  product_description?: string | null
  scientific_name?: string | null
  quantity_kg?: number | null
  quantity_unit?: string | null
  country_of_production?: string | null
  production_period_start?: string | null
  production_period_end?: string | null
  supplier_name?: string | null
  supplier_address?: string | null
  supplier_email?: string | null
  buyer_name?: string | null
  buyer_address?: string | null
  buyer_email?: string | null
  operator_eori?: string | null
  deforestation_free_declaration?: boolean
  legal_compliance_declaration?: boolean
  metadata?: Record<string, unknown> | null
}

export interface UpdateRecordInput {
  hs_code?: string | null
  commodity_type?: string | null
  product_description?: string | null
  scientific_name?: string | null
  quantity_kg?: number | null
  quantity_unit?: string | null
  country_of_production?: string | null
  production_period_start?: string | null
  production_period_end?: string | null
  supplier_name?: string | null
  supplier_address?: string | null
  supplier_email?: string | null
  buyer_name?: string | null
  buyer_address?: string | null
  buyer_email?: string | null
  operator_eori?: string | null
  deforestation_free_declaration?: boolean | null
  legal_compliance_declaration?: boolean | null
  metadata?: Record<string, unknown> | null
}

export interface ActivationInput {
  framework_slug: string
  export_destination?: string[] | null
  metadata?: Record<string, unknown> | null
}

export interface ActivationUpdateInput {
  export_destination?: string[] | null
  metadata?: Record<string, unknown> | null
  is_active?: boolean | null
}

export interface DeclarationUpdate {
  declaration_reference?: string | null
  declaration_submission_date?: string | null
  declaration_status?: string | null
  declaration_url?: string | null
}

export interface PlotLinkInput {
  plot_id: string
  quantity_from_plot_kg?: number | null
  percentage_from_plot?: number | null
}

// ─── Document Links ─────────────────────────────────────────────────────────

export type EvidenceDocumentType =
  | 'land_title'
  | 'legal_cert'
  | 'deforestation_report'
  | 'satellite_image'
  | 'supplier_declaration'
  | 'transport_doc'
  | 'geojson_boundary'
  | 'other'
  | string

export interface DocumentLink {
  id: string
  tenant_id: string
  record_id?: string | null
  plot_id?: string | null
  media_file_id: string
  document_type: EvidenceDocumentType
  file_hash: string | null
  filename: string | null
  description: string | null
  uploaded_at: string
  metadata_: Record<string, unknown>
  url?: string | null
}

export interface DocumentLinkInput {
  media_file_id: string
  document_type: EvidenceDocumentType
  description?: string | null
}

// ─── Risk Assessment (EUDR Art. 10-11) ──────────────────────────────────────

export type OverallRiskLevel = 'negligible' | 'low' | 'standard' | 'high' | string
export type RiskConclusion = 'approved' | 'conditional' | 'rejected' | string
export type VerificationStatus = 'not_started' | 'in_progress' | 'verified' | 'failed' | string
export type TraceabilityConfidence = 'full' | 'partial' | 'none' | string
export type RiskAssessmentStatus = 'draft' | 'completed' | string

export interface MitigationMeasure {
  measure: string
  status: string
  evidence_doc_id?: string | null
}

export interface RiskAssessment {
  id: string
  tenant_id: string
  record_id: string
  assessed_by: string | null
  assessed_at: string | null
  country_risk_level: RiskLevel | null
  country_risk_notes: string | null
  country_benchmarking_source: string | null
  supply_chain_risk_level: RiskLevel | null
  supply_chain_notes: string | null
  supplier_verification_status: VerificationStatus
  traceability_confidence: TraceabilityConfidence
  regional_risk_level: RiskLevel | null
  deforestation_prevalence: string | null
  indigenous_rights_risk: boolean
  corruption_index_note: string | null
  mitigation_measures: MitigationMeasure[] | null
  additional_info_requested: boolean
  independent_audit_required: boolean
  overall_risk_level: OverallRiskLevel | null
  conclusion: RiskConclusion | null
  conclusion_notes: string | null
  status: RiskAssessmentStatus
  metadata_: Record<string, unknown>
  created_at: string
  updated_at: string
}

export interface CreateRiskAssessmentInput {
  record_id: string
  country_risk_level?: string | null
  country_risk_notes?: string | null
  country_benchmarking_source?: string | null
  supply_chain_risk_level?: string | null
  supply_chain_notes?: string | null
  supplier_verification_status?: string
  traceability_confidence?: string
  regional_risk_level?: string | null
  deforestation_prevalence?: string | null
  indigenous_rights_risk?: boolean
  corruption_index_note?: string | null
  mitigation_measures?: MitigationMeasure[] | null
  additional_info_requested?: boolean
  independent_audit_required?: boolean
  overall_risk_level?: string | null
  conclusion?: string | null
  conclusion_notes?: string | null
}

export interface UpdateRiskAssessmentInput {
  country_risk_level?: string | null
  country_risk_notes?: string | null
  country_benchmarking_source?: string | null
  supply_chain_risk_level?: string | null
  supply_chain_notes?: string | null
  supplier_verification_status?: string | null
  traceability_confidence?: string | null
  regional_risk_level?: string | null
  deforestation_prevalence?: string | null
  indigenous_rights_risk?: boolean | null
  corruption_index_note?: string | null
  mitigation_measures?: MitigationMeasure[] | null
  additional_info_requested?: boolean | null
  independent_audit_required?: boolean | null
  overall_risk_level?: string | null
  conclusion?: string | null
  conclusion_notes?: string | null
}

// ─── Supply Chain Nodes (EUDR Art. 9.1.e-f) ────────────────────────────────

export type SupplyChainRole =
  | 'producer'
  | 'collector'
  | 'processor'
  | 'exporter'
  | 'importer'
  | 'trader'
  | string

export type NodeVerificationStatus = 'unverified' | 'verified' | 'flagged' | string

export interface SupplyChainNode {
  id: string
  tenant_id: string
  record_id: string
  sequence_order: number
  role: SupplyChainRole
  actor_name: string
  actor_address: string | null
  actor_country: string | null
  actor_tax_id: string | null
  actor_eori: string | null
  handoff_date: string | null
  quantity_kg: number | null
  verification_status: NodeVerificationStatus
  notes: string | null
  metadata_: Record<string, unknown>
  created_at: string
  updated_at: string
}

export interface CreateSupplyChainNodeInput {
  sequence_order: number
  role: string
  actor_name: string
  actor_address?: string | null
  actor_country?: string | null
  actor_tax_id?: string | null
  actor_eori?: string | null
  handoff_date?: string | null
  quantity_kg?: number | null
  verification_status?: string
  notes?: string | null
}

export interface UpdateSupplyChainNodeInput {
  sequence_order?: number | null
  role?: string | null
  actor_name?: string | null
  actor_address?: string | null
  actor_country?: string | null
  actor_tax_id?: string | null
  actor_eori?: string | null
  handoff_date?: string | null
  quantity_kg?: number | null
  verification_status?: string | null
  notes?: string | null
}

export interface ReorderNodesInput {
  order: { node_id: string; sequence_order: number }[]
}
