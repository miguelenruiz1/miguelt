// React Query hooks for Warehouse Management (WM).
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { wmApi } from '@/lib/wm-api'

export function useWMConfig(warehouseId: string | undefined) {
  return useQuery({
    queryKey: ['wm', 'config', warehouseId],
    queryFn: () => wmApi.getConfig(warehouseId!),
    enabled: !!warehouseId,
  })
}

export function useSetWMConfig(warehouseId: string | undefined) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: { receive_steps: number; deliver_steps: number; manufacture_steps: number }) =>
      wmApi.setConfig(warehouseId!, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['wm', 'config', warehouseId] })
      qc.invalidateQueries({ queryKey: ['wm', 'routes', warehouseId] })
    },
  })
}

export function useWMRoutes(warehouseId: string | undefined) {
  return useQuery({
    queryKey: ['wm', 'routes', warehouseId],
    queryFn: () => wmApi.listRoutes(warehouseId!),
    enabled: !!warehouseId,
  })
}

export function useStorageTypes(warehouseId: string | undefined) {
  return useQuery({
    queryKey: ['wm', 'storage-types', warehouseId],
    queryFn: () => wmApi.listStorageTypes(warehouseId!),
    enabled: !!warehouseId,
  })
}

export function useEmptyBinReport(warehouseId: string | undefined) {
  return useQuery({
    queryKey: ['wm', 'empty-report', warehouseId],
    queryFn: () => wmApi.emptyReport(warehouseId!),
    enabled: !!warehouseId,
  })
}

export function useOperationTypes() {
  return useQuery({ queryKey: ['wm', 'operation-types'], queryFn: () => wmApi.listOperationTypes() })
}

export function useMovementOrders(warehouseId: string | undefined, status?: string) {
  return useQuery({
    queryKey: ['wm', 'movement-orders', warehouseId, status],
    queryFn: () => wmApi.listMovementOrders(warehouseId!, status),
    enabled: !!warehouseId,
  })
}

export function useStockStatus(warehouseId: string | undefined) {
  return useQuery({
    queryKey: ['wm', 'stock-status', warehouseId],
    queryFn: () => wmApi.stockStatus(warehouseId!),
    enabled: !!warehouseId,
  })
}

export function useERI(warehouseId: string | undefined) {
  return useQuery({
    queryKey: ['wm', 'eri', warehouseId],
    queryFn: () => wmApi.eri(warehouseId!),
    enabled: !!warehouseId,
  })
}
