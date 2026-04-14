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

// EUDR Art. 8.2.f — tipos reconocidos de derecho de uso de la zona
export type TenureType =
  | 'owned'
  | 'leased'
  | 'sharecropped'
  | 'concession'
  | 'indigenous_collective'
  | 'afro_collective'
  | 'baldio_adjudicado'
  | 'occupation'
  | 'other'

// MITECO EFI Tomás — metadatos de captura del polígono
export type CaptureMethod =
  | 'handheld_gps'
  | 'rtk_gps'
  | 'drone'
  | 'manual_map'
  | 'cadastral'
  | 'survey'
  | 'unknown'

export type ProducerScale = 'smallholder' | 'medium' | 'industrial'

export interface CompliancePlot {
  id: string
  tenant_id: string
  organization_id: string | null
  plot_code: string
  plot_area_ha: number | null
  geolocation_type: GeolocationType
  lat: number | null
  lng: number | null
  geojson_data: Record<string, unknown> | null
  geojson_arweave_url: string | null
  geojson_hash: string | null
  country_code: string
  region: string | null
  municipality: string | null
  vereda: string | null
  frontera_agricola_status: string | null
  land_title_number: string | null
  land_title_hash: string | null
  // Tenencia y propiedad (EUDR Art. 8.2.f)
  owner_name: string | null
  owner_id_type: string | null
  owner_id_number: string | null
  producer_name: string | null
  producer_id_type: string | null
  producer_id_number: string | null
  cadastral_id: string | null
  tenure_type: TenureType | null
  tenure_start_date: string | null
  tenure_end_date: string | null
  indigenous_territory_flag: boolean
  // Capture metadata
  gps_accuracy_m: number | null
  capture_method: CaptureMethod | null
  capture_device: string | null
  capture_date: string | null
  // Producer scale
  crop_type: string | null
  scientific_name: string | null
  establishment_date: string | null
  renovation_date: string | null
  renovation_type: string | null
  last_harvest_date: string | null
  producer_scale: ProducerScale | null
  deforestation_free: boolean
  degradation_free: boolean
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

// ─── Multi-source EUDR screening ────────────────────────────────────────────

export type EudrRiskLevel = 'none' | 'low' | 'medium' | 'high'

export interface SourceResult {
  source: string
  name: string
  institution: string
  description: string
  eudr_role: string
  reference_url: string
  dataset: string
  checked_at: string
  error?: string | null
  // GFW-specific
  alerts_count?: number
  high_confidence_alerts?: number
  deforestation_free?: boolean | null
  cutoff_date?: string
  // Hansen-specific
  loss_pixels?: number
  has_loss?: boolean | null
  loss_by_year?: Record<number, number>
  cutoff_year?: number
  // JRC-specific
  forest_pixel_count?: number
  was_forest_2020?: boolean | null
}

export interface FullScreeningResult {
  plot_id: string
  plot_code: string
  eudr_compliant: boolean | null
  eudr_risk: EudrRiskLevel
  risk_reason: string
  checked_at: string
  elapsed_seconds: number
  failed_sources: string[]
  sources: Record<string, SourceResult>
  // Convergence (Fase A — G25)
  convergence_score?: number | null
  convergence_level?: 'low' | 'medium' | 'high' | null
  convergence_details?: string[] | null
  inside_protected_area?: boolean | null
  wdpa_warning?: string | null
}

// ─── Legal catalog (EUDR Art. 9.1 legalidad) ────────────────────────────────

export type LegalAmbito =
  | 'land_use_rights'
  | 'environmental_protection'
  | 'labor_rights'
  | 'human_rights'
  | 'third_party_rights_fpic'
  | 'fiscal_customs_anticorruption'

export type LegalAppliesToScale =
  | 'all'
  | 'smallholder'
  | 'medium'
  | 'industrial'
  | 'medium_or_industrial'

export type LegalComplianceStatus = 'satisfied' | 'missing' | 'na' | 'pending'

export interface LegalRequirement {
  id: string
  catalog_id: string
  ambito: LegalAmbito
  code: string
  title: string
  description: string | null
  legal_reference: string | null
  applies_to_scale: LegalAppliesToScale
  required_document_type: string | null
  is_blocking: boolean
  sort_order: number
}

export interface LegalCatalog {
  id: string
  country_code: string
  commodity: string
  version: string
  source: string | null
  source_url: string | null
  is_active: boolean
  created_at: string
  requirements?: LegalRequirement[]
}

export interface PlotLegalComplianceRow {
  id: string
  plot_id: string
  requirement_id: string
  status: LegalComplianceStatus
  evidence_media_id: string | null
  evidence_notes: string | null
  reviewed_at: string | null
  created_at: string
  updated_at: string
}

export interface PlotLegalComplianceItem {
  requirement: LegalRequirement
  compliance: PlotLegalComplianceRow | null
}

export interface PlotLegalComplianceSummary {
  plot_id: string
  catalog_id: string | null
  producer_scale: ProducerScale | null
  total_requirements: number
  applicable_requirements: number
  satisfied: number
  missing: number
  pending: number
  na: number
  blocking_missing: number
  items: PlotLegalComplianceItem[]
}

// ─── Certification schemes (MITECO EFI Alice credibility framework) ─────────

export type SchemeType = 'commodity_specific' | 'generic' | 'national'
export type SchemeScope = 'legality' | 'chain_of_custody' | 'sustainability' | 'full'

export interface CertificationScheme {
  id: string
  slug: string
  name: string
  scheme_type: SchemeType
  scope: SchemeScope
  commodities: string[]
  ownership_score: number
  transparency_score: number
  audit_score: number
  grievance_score: number
  total_score: number
  covers_eudr_ambitos: string[]
  reference_url: string | null
  notes: string | null
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface CertificationSchemeUpdate {
  name?: string
  scheme_type?: SchemeType
  scope?: SchemeScope
  commodities?: string[]
  ownership_score?: number
  transparency_score?: number
  audit_score?: number
  grievance_score?: number
  covers_eudr_ambitos?: string[]
  reference_url?: string | null
  notes?: string | null
  is_active?: boolean
}

// ─── Country risk benchmarks ────────────────────────────────────────────────

export type CountryRiskLevel = 'negligible' | 'low' | 'standard' | 'high' | 'critical'
export type DeforestationPrevalence = 'very_low' | 'low' | 'medium' | 'high' | 'very_high'

export interface CountryRiskBenchmark {
  id: string
  country_code: string
  risk_level: CountryRiskLevel
  cpi_score: number | null
  cpi_rank: number | null
  conflict_flag: boolean
  deforestation_prevalence: DeforestationPrevalence | null
  indigenous_risk_flag: boolean
  notes: string | null
  source: string
  as_of_date: string
  is_current: boolean
  created_at: string
}

// ─── Composite risk decision ────────────────────────────────────────────────

export type FinalRiskLabel = 'low' | 'medium' | 'high' | 'critical' | 'requires_field_visit'

export interface RiskDecisionResponse {
  plot_id: string
  plot_code: string
  final_risk: FinalRiskLabel
  drivers: string[]
  warnings: string[]
  positives: string[]
  recommended_action: string
  inputs: {
    eudr_risk?: string | null
    convergence_score?: number | null
    convergence_level?: 'low' | 'medium' | 'high' | null
    inside_protected_area?: boolean | null
    country_risk?: (Partial<CountryRiskBenchmark> & { as_of_date?: string }) | null
    legal_summary?: {
      satisfied: number
      missing: number
      blocking_missing: number
      applicable: number
    } | null
    producer_scale?: ProducerScale | null
    tenure_type?: string | null
    gps_accuracy_m?: number | null
    capture_method?: string | null
  }
}

// ─── Input types ────────────────────────────────────────────────────────────

export interface CreatePlotInput {
  plot_code: string
  organization_id?: string | null
  plot_area_ha?: number | null
  geolocation_type?: string
  lat?: number | null
  lng?: number | null
  geojson_data?: Record<string, unknown> | null
  geojson_arweave_url?: string | null
  geojson_hash?: string | null
  country_code?: string
  region?: string | null
  municipality?: string | null
  land_title_number?: string | null
  land_title_hash?: string | null
  // Tenencia y propiedad (EUDR Art. 8.2.f)
  owner_name?: string | null
  owner_id_type?: string | null
  owner_id_number?: string | null
  producer_name?: string | null
  producer_id_type?: string | null
  producer_id_number?: string | null
  cadastral_id?: string | null
  tenure_type?: TenureType | null
  tenure_start_date?: string | null
  tenure_end_date?: string | null
  indigenous_territory_flag?: boolean
  gps_accuracy_m?: number | null
  capture_method?: CaptureMethod | null
  capture_device?: string | null
  capture_date?: string | null
  producer_scale?: ProducerScale | null
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
  geojson_data?: Record<string, unknown> | null
  geojson_arweave_url?: string | null
  geojson_hash?: string | null
  // Tenencia y propiedad (EUDR Art. 8.2.f)
  owner_name?: string | null
  owner_id_type?: string | null
  owner_id_number?: string | null
  producer_name?: string | null
  producer_id_type?: string | null
  producer_id_number?: string | null
  cadastral_id?: string | null
  tenure_type?: TenureType | null
  tenure_start_date?: string | null
  tenure_end_date?: string | null
  indigenous_territory_flag?: boolean
  gps_accuracy_m?: number | null
  capture_method?: CaptureMethod | null
  capture_device?: string | null
  capture_date?: string | null
  producer_scale?: ProducerScale | null
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
  // Fase B — tipos especificos por ambito legal (MITECO EFI Alice)
  | 'eia_report'                    // Estudio impacto ambiental
  | 'fpic_record'                   // Consulta previa libre e informada
  | 'labor_contract'                // Contrato laboral escrito
  | 'pila_statement'                // Aportes seguridad social CO
  | 'plame_statement'               // Planilla electronica PE
  | 'iess_statement'                // Seguridad social EC
  | 'environmental_license'         // Licencia ambiental
  | 'child_labor_affidavit'         // Declaracion ausencia trabajo infantil
  | 'forced_labor_affidavit'        // Declaracion ausencia trabajo forzoso
  | 'epp_training_record'           // Formacion EPP / pesticidas
  | 'clmrs_enrollment'              // Child Labour Monitoring CI
  | 'community_agreement'           // Acuerdo con chefferie villageoise
  | 'rut'                           // Registro tributario
  | 'ruc'                           // Registro tributario PE/EC
  | 'ccc_registration'              // Conseil Cafe-Cacao CI
  | 'cadastral_certificate'         // Folio matricula / cadastre
  | 'ica_invoice'                   // Agroquimicos CO
  | 'protected_area_check'          // Cross-check WDPA/nacional
  | 'car_certificate'               // CAR Brasil
  | 'rl_app_declaration'            // Reserva Legal / APP Brasil
  | 'ibama_embargo_check'           // Lista suja IBAMA
  | 'mte_slave_labor_check'         // Lista suja MTE
  | 'soy_moratorium_declaration'    // Moratoria Soja Brasil
  | 'indigenous_quilombola_check'   // TI / Quilombola Brasil
  | 'zoning_certificate'            // Zonificacion
  | 'gre_document'                  // Guia remision electronica
  | string

// Metadata for display of evidence document types
export const EVIDENCE_DOC_LABELS: Record<string, string> = {
  land_title: 'Titulo / tenencia legal',
  legal_cert: 'Certificado legal generico',
  deforestation_report: 'Reporte deforestacion',
  satellite_image: 'Imagen satelital',
  supplier_declaration: 'Declaracion del proveedor',
  transport_doc: 'Documento de transporte',
  geojson_boundary: 'Poligono GeoJSON',
  eia_report: 'Estudio impacto ambiental (EIA)',
  fpic_record: 'Consulta previa (FPIC)',
  labor_contract: 'Contrato laboral',
  pila_statement: 'PILA (Seguridad Social CO)',
  plame_statement: 'PLAME (Seguridad Social PE)',
  iess_statement: 'IESS (Seguridad Social EC)',
  environmental_license: 'Licencia ambiental',
  child_labor_affidavit: 'Decl. ausencia trabajo infantil',
  forced_labor_affidavit: 'Decl. ausencia trabajo forzoso',
  epp_training_record: 'Formacion EPP / pesticidas',
  clmrs_enrollment: 'CLMRS (trabajo infantil CI)',
  community_agreement: 'Acuerdo comunitario',
  rut: 'RUT (Colombia)',
  ruc: 'RUC (Peru / Ecuador)',
  ccc_registration: 'Conseil Cafe-Cacao (CI)',
  cadastral_certificate: 'Certificado catastral',
  ica_invoice: 'Factura ICA (agroquimicos)',
  protected_area_check: 'Cross-check areas protegidas',
  car_certificate: 'CAR (Cadastro Ambiental Rural BR)',
  rl_app_declaration: 'Reserva Legal / APP (Brasil)',
  ibama_embargo_check: 'Lista suja IBAMA',
  mte_slave_labor_check: 'Lista suja MTE',
  soy_moratorium_declaration: 'Moratoria Soja (Brasil)',
  indigenous_quilombola_check: 'Cross-check TI / Quilombola',
  zoning_certificate: 'Certificado de zonificacion',
  gre_document: 'Guia de remision electronica',
  other: 'Otro',
}

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
