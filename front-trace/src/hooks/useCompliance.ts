import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { complianceApi } from '@/lib/compliance-api'
import type {
  ActivationInput,
  ActivationUpdateInput,
  CreatePlotInput,
  CreateRecordInput,
  DeclarationUpdate,
  PlotLinkInput,
  UpdatePlotInput,
  UpdateRecordInput,
} from '@/types/compliance'

const KEYS = {
  frameworks: ['compliance', 'frameworks'] as const,
  framework: (slug: string) => ['compliance', 'frameworks', slug] as const,
  activations: ['compliance', 'activations'] as const,
  plots: ['compliance', 'plots'] as const,
  plotList: (p: object) => ['compliance', 'plots', 'list', p] as const,
  plot: (id: string) => ['compliance', 'plots', id] as const,
  records: ['compliance', 'records'] as const,
  recordList: (p: object) => ['compliance', 'records', 'list', p] as const,
  record: (id: string) => ['compliance', 'records', id] as const,
  recordPlots: (id: string) => ['compliance', 'records', id, 'plots'] as const,
  recordCertificate: (id: string) => ['compliance', 'records', id, 'certificate'] as const,
  assetCompliance: (assetId: string) => ['compliance', 'assets', assetId] as const,
  certificates: ['compliance', 'certificates'] as const,
  certificateList: (p: object) => ['compliance', 'certificates', 'list', p] as const,
  certificate: (id: string) => ['compliance', 'certificates', id] as const,
  verify: (num: string) => ['compliance', 'verify', num] as const,
}

// ─── Frameworks ──────────────────────────────────────────────────────────────

export function useFrameworks(params?: { target_market?: string; commodity?: string }) {
  return useQuery({
    queryKey: [...KEYS.frameworks, params ?? {}],
    queryFn: () => complianceApi.frameworks.list(params),
  })
}

export function useFramework(slug: string) {
  return useQuery({
    queryKey: KEYS.framework(slug),
    queryFn: () => complianceApi.frameworks.get(slug),
    enabled: Boolean(slug),
  })
}

// ─── Activations ─────────────────────────────────────────────────────────────

export function useActivations() {
  return useQuery({
    queryKey: KEYS.activations,
    queryFn: () => complianceApi.activations.list(),
  })
}

export function useActivateFramework() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: ActivationInput) => complianceApi.activations.activate(data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: KEYS.activations })
    },
  })
}

export function useUpdateActivation() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ slug, data }: { slug: string; data: ActivationUpdateInput }) =>
      complianceApi.activations.update(slug, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: KEYS.activations })
    },
  })
}

export function useDeactivateFramework() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (slug: string) => complianceApi.activations.deactivate(slug),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: KEYS.activations })
    },
  })
}

// ─── Plots ───────────────────────────────────────────────────────────────────

export function usePlots(params?: { organization_id?: string; risk_level?: string; is_active?: boolean }) {
  return useQuery({
    queryKey: KEYS.plotList(params ?? {}),
    queryFn: () => complianceApi.plots.list(params),
  })
}

export function usePlot(id: string) {
  return useQuery({
    queryKey: KEYS.plot(id),
    queryFn: () => complianceApi.plots.get(id),
    enabled: Boolean(id),
  })
}

export function useCreatePlot() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: CreatePlotInput) => complianceApi.plots.create(data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: KEYS.plots })
    },
  })
}

export function useUpdatePlot(id: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: UpdatePlotInput) => complianceApi.plots.update(id, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: KEYS.plots })
      qc.invalidateQueries({ queryKey: KEYS.plot(id) })
    },
  })
}

export function useDeletePlot() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => complianceApi.plots.delete(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: KEYS.plots })
    },
  })
}

// ─── Records ─────────────────────────────────────────────────────────────────

export function useRecords(params?: {
  framework_slug?: string
  asset_id?: string
  status?: string
  commodity_type?: string
}) {
  return useQuery({
    queryKey: KEYS.recordList(params ?? {}),
    queryFn: () => complianceApi.records.list(params),
  })
}

export function useRecord(id: string) {
  return useQuery({
    queryKey: KEYS.record(id),
    queryFn: () => complianceApi.records.get(id),
    enabled: Boolean(id),
  })
}

export function useCreateRecord() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: CreateRecordInput) => complianceApi.records.create(data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: KEYS.records })
    },
  })
}

export function useUpdateRecord(id: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: UpdateRecordInput) => complianceApi.records.update(id, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: KEYS.records })
      qc.invalidateQueries({ queryKey: KEYS.record(id) })
    },
  })
}

export function useDeleteRecord() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => complianceApi.records.delete(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: KEYS.records })
    },
  })
}

export function useValidateRecord(id: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: () => complianceApi.records.validate(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: KEYS.record(id) })
      qc.invalidateQueries({ queryKey: KEYS.records })
    },
  })
}

export function useRecordPlots(recordId: string) {
  return useQuery({
    queryKey: KEYS.recordPlots(recordId),
    queryFn: () => complianceApi.records.plots(recordId),
    enabled: Boolean(recordId),
  })
}

export function useLinkPlot(recordId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: PlotLinkInput) => complianceApi.records.linkPlot(recordId, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: KEYS.recordPlots(recordId) })
      qc.invalidateQueries({ queryKey: KEYS.record(recordId) })
    },
  })
}

export function useUnlinkPlot(recordId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (plotId: string) => complianceApi.records.unlinkPlot(recordId, plotId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: KEYS.recordPlots(recordId) })
      qc.invalidateQueries({ queryKey: KEYS.record(recordId) })
    },
  })
}

export function useUpdateDeclaration(recordId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: DeclarationUpdate) => complianceApi.records.updateDeclaration(recordId, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: KEYS.record(recordId) })
      qc.invalidateQueries({ queryKey: KEYS.records })
    },
  })
}

// ─── Asset compliance ────────────────────────────────────────────────────────

export function useAssetCompliance(assetId: string) {
  return useQuery({
    queryKey: KEYS.assetCompliance(assetId),
    queryFn: () => complianceApi.assets.compliance(assetId),
    enabled: Boolean(assetId),
  })
}

// ─── Certificates ────────────────────────────────────────────────────────────

export function useGenerateCertificate(recordId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: () => complianceApi.records.generateCertificate(recordId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: KEYS.recordCertificate(recordId) })
      qc.invalidateQueries({ queryKey: KEYS.record(recordId) })
      qc.invalidateQueries({ queryKey: KEYS.certificates })
    },
  })
}

export function useRecordCertificate(recordId: string) {
  return useQuery({
    queryKey: KEYS.recordCertificate(recordId),
    queryFn: () => complianceApi.records.getCertificate(recordId),
    enabled: Boolean(recordId),
  })
}

export function useCertificates(params?: {
  framework_slug?: string
  status?: string
  year?: number
  offset?: number
  limit?: number
}) {
  return useQuery({
    queryKey: KEYS.certificateList(params ?? {}),
    queryFn: () => complianceApi.certificates.list(params),
  })
}

export function useCertificate(id: string) {
  return useQuery({
    queryKey: KEYS.certificate(id),
    queryFn: () => complianceApi.certificates.get(id),
    enabled: Boolean(id),
  })
}

export function useRegenerateCertificate() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => complianceApi.certificates.regenerate(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: KEYS.certificates })
    },
  })
}

export function useRevokeCertificate() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, reason }: { id: string; reason: string }) =>
      complianceApi.certificates.revoke(id, reason),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: KEYS.certificates })
    },
  })
}

// ─── Public verification (no auth) ──────────────────────────────────────────

export function useVerifyCertificate(certificateNumber: string) {
  return useQuery({
    queryKey: KEYS.verify(certificateNumber),
    queryFn: () => complianceApi.verify(certificateNumber),
    enabled: Boolean(certificateNumber),
  })
}
