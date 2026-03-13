import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  integrationCatalogApi,
  integrationConfigApi,
  integrationSyncApi,
  integrationInvoiceApi,
  resolutionApi,
} from '@/lib/integration-api'

// ─── Catalog ──────────────────────────────────────────────────────────────────

export function useIntegrationCatalog() {
  return useQuery({
    queryKey: ['integrations', 'catalog'],
    queryFn: () => integrationCatalogApi.list(),
    staleTime: 60_000,
  })
}

// ─── Configs ──────────────────────────────────────────────────────────────────

export function useIntegrationConfigs() {
  return useQuery({
    queryKey: ['integrations', 'configs'],
    queryFn: () => integrationConfigApi.list(),
  })
}

export function useIntegrationConfig(id: string) {
  return useQuery({
    queryKey: ['integrations', 'configs', id],
    queryFn: () => integrationConfigApi.get(id),
    enabled: !!id,
  })
}

export function useCreateIntegration() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: integrationConfigApi.create,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['integrations', 'configs'] }),
  })
}

export function useUpdateIntegration() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: Record<string, unknown> }) =>
      integrationConfigApi.update(id, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['integrations', 'configs'] }),
  })
}

export function useDeleteIntegration() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: integrationConfigApi.delete,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['integrations', 'configs'] }),
  })
}

export function useTestConnection() {
  return useMutation({
    mutationFn: ({ providerSlug, credentials }: { providerSlug: string; credentials?: Record<string, unknown> }) =>
      integrationConfigApi.testConnection(providerSlug, credentials),
  })
}

// ─── Sync ─────────────────────────────────────────────────────────────────────

export function useTriggerSync() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ providerSlug, direction, entityType }: { providerSlug: string; direction: string; entityType: string }) =>
      integrationSyncApi.trigger(providerSlug, { direction, entity_type: entityType }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['integrations', 'sync-jobs'] }),
  })
}

export function useSyncJobs(params?: Parameters<typeof integrationSyncApi.listJobs>[0]) {
  return useQuery({
    queryKey: ['integrations', 'sync-jobs', params],
    queryFn: () => integrationSyncApi.listJobs(params),
  })
}

export function useSyncJobLogs(jobId: string) {
  return useQuery({
    queryKey: ['integrations', 'sync-jobs', jobId, 'logs'],
    queryFn: () => integrationSyncApi.getJobLogs(jobId),
    enabled: !!jobId,
  })
}

// ─── Invoicing ────────────────────────────────────────────────────────────────

export function useCreateInvoice() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ providerSlug, data }: { providerSlug: string; data: Record<string, unknown> }) =>
      integrationInvoiceApi.create(providerSlug, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['integrations', 'sync-jobs'] }),
  })
}

export function useRemoteInvoices(providerSlug: string, params?: { page?: number; page_size?: number }) {
  return useQuery({
    queryKey: ['integrations', 'invoices', providerSlug, params],
    queryFn: () => integrationInvoiceApi.list(providerSlug, params),
    enabled: !!providerSlug,
  })
}

// ─── Resolutions ─────────────────────────────────────────────────────────────

export function useResolution(provider: string) {
  return useQuery({
    queryKey: ['integrations', 'resolutions', provider],
    queryFn: () => resolutionApi.get(provider),
    enabled: !!provider,
    retry: false,
  })
}

export function useCreateResolution() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ provider, data }: { provider: string; data: Record<string, unknown> }) =>
      resolutionApi.create(provider, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['integrations', 'resolutions'] }),
  })
}

export function useDeactivateResolution() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: resolutionApi.deactivate,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['integrations', 'resolutions'] }),
  })
}
