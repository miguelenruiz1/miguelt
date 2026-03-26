/**
 * React Query hooks for the logistics module (trace-service).
 * Shipments, trade documents, anchor rules, public verification.
 */
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  logisticsShipmentsApi,
  logisticsTradeDocsApi,
  logisticsAnchorRulesApi,
  publicVerifyApi,
} from '@/lib/logistics-api'
import type {
  ShipmentDocCreate, ShipmentDocUpdate,
  TradeDocCreate, TradeDocUpdate,
  AnchorRuleCreate, AnchorRuleUpdate,
} from '@/types/logistics'

// ── Shipments ─────────────────────────────────────────────────────────────────

export function useShipmentDocuments(params?: { document_type?: string; reference_type?: string; reference_id?: string }) {
  return useQuery({
    queryKey: ['logistics', 'shipments', params],
    queryFn: () => logisticsShipmentsApi.list(params),
  })
}

export function useShipmentDocument(id: string) {
  return useQuery({
    queryKey: ['logistics', 'shipments', id],
    queryFn: () => logisticsShipmentsApi.get(id),
    enabled: !!id,
  })
}

export function useCreateShipment() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: ShipmentDocCreate) => logisticsShipmentsApi.create(data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['logistics', 'shipments'] }),
  })
}

export function useUpdateShipment() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: ShipmentDocUpdate }) => logisticsShipmentsApi.update(id, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['logistics', 'shipments'] }),
  })
}

export function useUpdateShipmentStatus() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, status }: { id: string; status: string }) => logisticsShipmentsApi.updateStatus(id, status),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['logistics', 'shipments'] }),
  })
}

export function useDeleteShipment() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => logisticsShipmentsApi.delete(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['logistics', 'shipments'] }),
  })
}

// ── Trade Documents ───────────────────────────────────────────────────────────

export function useTradeDocuments(params?: { document_type?: string; reference_type?: string; reference_id?: string; shipment_id?: string }) {
  return useQuery({
    queryKey: ['logistics', 'trade-docs', params],
    queryFn: () => logisticsTradeDocsApi.list(params),
  })
}

export function useTradeDocument(id: string) {
  return useQuery({
    queryKey: ['logistics', 'trade-docs', id],
    queryFn: () => logisticsTradeDocsApi.get(id),
    enabled: !!id,
  })
}

export function useCreateTradeDoc() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: TradeDocCreate) => logisticsTradeDocsApi.create(data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['logistics', 'trade-docs'] }),
  })
}

export function useUpdateTradeDoc() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: TradeDocUpdate }) => logisticsTradeDocsApi.update(id, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['logistics', 'trade-docs'] }),
  })
}

export function useApproveTradeDoc() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => logisticsTradeDocsApi.approve(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['logistics', 'trade-docs'] }),
  })
}

export function useRejectTradeDoc() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, reason }: { id: string; reason?: string }) => logisticsTradeDocsApi.reject(id, reason),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['logistics', 'trade-docs'] }),
  })
}

export function useDeleteTradeDoc() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => logisticsTradeDocsApi.delete(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['logistics', 'trade-docs'] }),
  })
}

// ── Anchor Rules ──────────────────────────────────────────────────────────────

export function useAnchorRules(entityType?: string) {
  return useQuery({
    queryKey: ['logistics', 'anchor-rules', entityType],
    queryFn: () => logisticsAnchorRulesApi.list(entityType),
  })
}

export function useCreateAnchorRule() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: AnchorRuleCreate) => logisticsAnchorRulesApi.create(data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['logistics', 'anchor-rules'] }),
  })
}

export function useUpdateAnchorRule() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: AnchorRuleUpdate }) => logisticsAnchorRulesApi.update(id, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['logistics', 'anchor-rules'] }),
  })
}

export function useDeleteAnchorRule() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => logisticsAnchorRulesApi.delete(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['logistics', 'anchor-rules'] }),
  })
}

export function useSeedAnchorRules() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: () => logisticsAnchorRulesApi.seedDefaults(),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['logistics', 'anchor-rules'] }),
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
