import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import {
  inventoryBatchOriginsApi,
  inventoryQualityTestsApi,
  type BatchPlotOrigin,
  type QualityTest,
} from '@/lib/inventory-api'

export function useBatchQualityTests(batchId: string | undefined) {
  return useQuery<QualityTest[]>({
    queryKey: ['inventory', 'quality-tests', batchId],
    queryFn: () => inventoryQualityTestsApi.listForBatch(batchId!),
    enabled: !!batchId,
  })
}

export function useCreateQualityTest() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: inventoryQualityTestsApi.create,
    onSuccess: (row) => {
      qc.invalidateQueries({ queryKey: ['inventory', 'quality-tests', row.batch_id] })
    },
  })
}

export function useBatchOrigins(batchId: string | undefined) {
  return useQuery<BatchPlotOrigin[]>({
    queryKey: ['inventory', 'batch-origins', batchId],
    queryFn: () => inventoryBatchOriginsApi.listForBatch(batchId!),
    enabled: !!batchId,
  })
}

export function useCreateBatchOrigin() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({
      batchId,
      data,
    }: {
      batchId: string
      data: { plot_id: string; plot_code?: string | null; origin_quantity_kg: number }
    }) => inventoryBatchOriginsApi.create(batchId, data),
    onSuccess: (row) => {
      qc.invalidateQueries({ queryKey: ['inventory', 'batch-origins', row.batch_id] })
    },
  })
}
