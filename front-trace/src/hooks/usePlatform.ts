import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { platformApi } from '@/lib/platform-api'
import type { OnboardRequest } from '@/types/platform'

export function usePlatformDashboard() {
  return useQuery({
    queryKey: ['platform', 'dashboard'],
    queryFn: () => platformApi.dashboard(),
    staleTime: 30_000,
  })
}

export function usePlatformTenants(params?: {
  search?: string
  status?: string
  plan_slug?: string
  offset?: number
  limit?: number
}) {
  return useQuery({
    queryKey: ['platform', 'tenants', params],
    queryFn: () => platformApi.tenants(params),
    staleTime: 15_000,
  })
}

export function usePlatformTenantDetail(tenantId: string) {
  return useQuery({
    queryKey: ['platform', 'tenant', tenantId],
    queryFn: () => platformApi.tenantDetail(tenantId),
    enabled: !!tenantId,
    staleTime: 15_000,
  })
}

export function usePlatformAnalytics(months = 6) {
  return useQuery({
    queryKey: ['platform', 'analytics', months],
    queryFn: () => platformApi.analytics(months),
    staleTime: 60_000,
  })
}

export function usePlatformSales() {
  return useQuery({
    queryKey: ['platform', 'sales'],
    queryFn: () => platformApi.sales(),
    staleTime: 15_000,
    refetchInterval: 30_000,
  })
}

// ─── Mutations ──────────────────────────────────────────────────────────────

export function useOnboardTenant() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: OnboardRequest) => platformApi.onboardTenant(data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['platform'] })
    },
  })
}

export function useChangeTenantPlan(tenantId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (planSlug: string) => platformApi.changePlan(tenantId, planSlug),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['platform', 'tenant', tenantId] })
      qc.invalidateQueries({ queryKey: ['platform', 'dashboard'] })
    },
  })
}

export function useToggleTenantModule(tenantId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ slug, active }: { slug: string; active: boolean }) =>
      platformApi.toggleModule(tenantId, slug, active),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['platform', 'tenant', tenantId] })
    },
  })
}

export function useGenerateTenantInvoice(tenantId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: () => platformApi.generateInvoice(tenantId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['platform', 'tenant', tenantId] })
      qc.invalidateQueries({ queryKey: ['platform', 'sales'] })
    },
  })
}

export function useGeneratePaymentLink(tenantId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: () => platformApi.generatePaymentLink(tenantId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['platform', 'tenant', tenantId] })
    },
  })
}

export function useCancelTenantSubscription(tenantId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (reason?: string) => platformApi.cancelSubscription(tenantId, reason),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['platform'] })
    },
  })
}

export function useReactivateTenantSubscription(tenantId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: () => platformApi.reactivateSubscription(tenantId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['platform'] })
    },
  })
}

export function usePlatformUsers(params?: {
  search?: string
  tenant_id?: string
  offset?: number
  limit?: number
}) {
  return useQuery({
    queryKey: ['platform', 'users', params],
    queryFn: () => platformApi.users(params),
    staleTime: 15_000,
  })
}
