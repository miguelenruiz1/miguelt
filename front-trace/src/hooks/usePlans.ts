import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { subscriptionApi } from '@/lib/subscription-api'
import type { PlanCreate, PlanUpdate } from '@/types/subscription'

export function usePlans(includeArchived = false) {
  return useQuery({
    queryKey: ['plans', includeArchived],
    queryFn: () => subscriptionApi.plans.list(includeArchived),
  })
}

export function useCreatePlan() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: PlanCreate) => subscriptionApi.plans.create(data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['plans'] }),
  })
}

export function useUpdatePlan() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: PlanUpdate }) =>
      subscriptionApi.plans.update(id, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['plans'] }),
  })
}

export function useArchivePlan() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => subscriptionApi.plans.archive(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['plans'] }),
  })
}
