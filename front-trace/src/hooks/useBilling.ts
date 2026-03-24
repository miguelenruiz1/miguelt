import { useMutation, useQuery } from '@tanstack/react-query'
import { subscriptionApi } from '@/lib/subscription-api'
import type { CheckoutRequest, Invoice, UsageSummary } from '@/types/subscription'

export function useUsageSummary(tenantId: string) {
  return useQuery<UsageSummary>({
    queryKey: ['usage', tenantId],
    queryFn: () => subscriptionApi.usage.get(tenantId),
    enabled: !!tenantId,
    staleTime: 60_000,
  })
}

export function useCheckout() {
  return useMutation({
    mutationFn: (data: CheckoutRequest) => subscriptionApi.checkout.create(data),
  })
}

export function useTenantInvoices(tenantId: string) {
  return useQuery<Invoice[]>({
    queryKey: ['tenant-invoices', tenantId],
    queryFn: () => subscriptionApi.checkout.getInvoices(tenantId),
    enabled: !!tenantId,
  })
}
