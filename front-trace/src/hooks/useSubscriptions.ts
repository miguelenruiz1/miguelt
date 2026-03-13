import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { subscriptionApi, SubApiError } from '@/lib/subscription-api'
import type { Subscription, SubscriptionCreate } from '@/types/subscription'

export function useSubscriptions(params?: {
  status?: string
  plan_id?: string
  tenant_id?: string
  offset?: number
  limit?: number
}) {
  return useQuery({
    queryKey: ['subscriptions', params],
    queryFn: () => subscriptionApi.subscriptions.list(params),
  })
}

export function useSubscription(tenantId: string) {
  return useQuery<Subscription | null>({
    queryKey: ['subscriptions', tenantId],
    queryFn: async () => {
      try {
        return await subscriptionApi.subscriptions.get(tenantId)
      } catch (err) {
        if (err instanceof SubApiError && err.status === 404) return null
        throw err
      }
    },
    enabled: !!tenantId,
  })
}

export function useCreateSubscription() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: SubscriptionCreate) => subscriptionApi.subscriptions.create(data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['subscriptions'] }),
  })
}

export function useCancelSubscription() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ tenantId, reason }: { tenantId: string; reason?: string }) =>
      subscriptionApi.subscriptions.cancel(tenantId, reason),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['subscriptions'] }),
  })
}

export function useReactivateSubscription() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (tenantId: string) => subscriptionApi.subscriptions.reactivate(tenantId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['subscriptions'] }),
  })
}

export function useUpgradePlan() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ tenantId, planSlug }: { tenantId: string; planSlug: string }) =>
      subscriptionApi.subscriptions.upgrade(tenantId, planSlug),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['subscriptions'] }),
  })
}

export function useInvoices(tenantId: string) {
  return useQuery({
    queryKey: ['invoices', tenantId],
    queryFn: () => subscriptionApi.subscriptions.listInvoices(tenantId),
    enabled: !!tenantId,
  })
}

export function useCreateInvoice() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (tenantId: string) => subscriptionApi.subscriptions.generateInvoice(tenantId),
    onSuccess: (_, tenantId) => {
      qc.invalidateQueries({ queryKey: ['invoices', tenantId] })
      qc.invalidateQueries({ queryKey: ['subscriptions'] })
    },
  })
}

export function useMarkPaid() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ tenantId, invId, notes }: { tenantId: string; invId: string; notes?: string }) =>
      subscriptionApi.subscriptions.markPaid(tenantId, invId, notes),
    onSuccess: (_, { tenantId }) => qc.invalidateQueries({ queryKey: ['invoices', tenantId] }),
  })
}

export function useSubEvents(tenantId: string) {
  return useQuery({
    queryKey: ['sub-events', tenantId],
    queryFn: () => subscriptionApi.subscriptions.listEvents(tenantId),
    enabled: !!tenantId,
  })
}

export function useMetrics() {
  return useQuery({
    queryKey: ['sub-metrics'],
    queryFn: () => subscriptionApi.admin.getMetrics(),
    refetchInterval: 60_000,
  })
}
