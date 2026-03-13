import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { paymentsApi } from '@/lib/payments-api'
import type { GatewayConfigSave } from '@/types/payments'

const TENANT_ID = import.meta.env.VITE_TENANT_ID ?? 'default'

// ─── Queries ──────────────────────────────────────────────────────────────────

export function useGatewayCatalog() {
  return useQuery({
    queryKey: ['payments', 'catalog'],
    queryFn: () => paymentsApi.catalog(),
    staleTime: 60_000,
  })
}

export function useGatewayConfigs(tenantId = TENANT_ID) {
  return useQuery({
    queryKey: ['payments', 'configs', tenantId],
    queryFn: () => paymentsApi.listConfigs(tenantId),
  })
}

export function useActiveGateway(tenantId = TENANT_ID) {
  return useQuery({
    queryKey: ['payments', 'active', tenantId],
    queryFn: () => paymentsApi.getActive(tenantId),
    staleTime: 30_000,
  })
}

// ─── Mutations ────────────────────────────────────────────────────────────────

export function useSaveGatewayConfig(tenantId = TENANT_ID) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ slug, body }: { slug: string; body: GatewayConfigSave }) =>
      paymentsApi.saveConfig(tenantId, slug, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['payments', 'configs', tenantId] })
      qc.invalidateQueries({ queryKey: ['payments', 'active', tenantId] })
    },
  })
}

export function useSetActiveGateway(tenantId = TENANT_ID) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (slug: string) => paymentsApi.setActive(tenantId, slug),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['payments', 'configs', tenantId] })
      qc.invalidateQueries({ queryKey: ['payments', 'active', tenantId] })
    },
  })
}

export function useDeleteGatewayConfig(tenantId = TENANT_ID) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (slug: string) => paymentsApi.deleteConfig(tenantId, slug),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['payments', 'configs', tenantId] })
      qc.invalidateQueries({ queryKey: ['payments', 'active', tenantId] })
    },
  })
}
