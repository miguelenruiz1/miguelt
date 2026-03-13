import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '@/lib/api'
import { newUUID } from '@/lib/utils'
import type { WalletCreate, WalletGenerateRequest, WalletUpdate } from '@/types/api'

const KEYS = {
  all:    ['wallets'] as const,
  list:   (p: object) => ['wallets', 'list', p] as const,
  detail: (id: string) => ['wallets', id] as const,
}

export function useWalletList(params?: { tag?: string; status?: string; offset?: number; limit?: number }) {
  return useQuery({
    queryKey: KEYS.list(params ?? {}),
    queryFn:  () => api.wallets.list(params),
  })
}

export function useWallet(id: string) {
  return useQuery({
    queryKey: KEYS.detail(id),
    queryFn:  () => api.wallets.get(id),
    enabled:  Boolean(id),
  })
}

export function useRegisterWallet() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: WalletCreate) => api.wallets.register(data, newUUID()),
    onSuccess: () => qc.invalidateQueries({ queryKey: KEYS.all }),
  })
}

export function useGenerateWallet() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: WalletGenerateRequest) => api.wallets.generate(data),
    onSuccess: () => qc.invalidateQueries({ queryKey: KEYS.all }),
  })
}

export function useUpdateWallet() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: WalletUpdate }) =>
      api.wallets.update(id, data),
    onSuccess: (_, { id }) => {
      qc.invalidateQueries({ queryKey: KEYS.all })
      qc.invalidateQueries({ queryKey: KEYS.detail(id) })
    },
  })
}
