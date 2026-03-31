/**
 * React Query hooks for the logistics module (trace-service).
 * Transport analytics and public verification.
 */
import { useQuery } from '@tanstack/react-query'
import {
  logisticsAnalyticsApi,
  publicVerifyApi,
} from '@/lib/logistics-api'

// ── Transport Analytics ──────────────────────────────────────────────────────

export function useTransportAnalytics(period: string = 'month') {
  return useQuery({
    queryKey: ['logistics', 'analytics', 'transport', period],
    queryFn: () => logisticsAnalyticsApi.transport(period),
  })
}

// ── Public Verification ───────────────────────────────────────────────────────

export function usePublicBatchVerification(batchNumber: string, tenantId?: string) {
  return useQuery({
    queryKey: ['public', 'verify', batchNumber],
    queryFn: () => publicVerifyApi.verifyBatch(batchNumber, tenantId),
    enabled: !!batchNumber,
  })
}
