import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api'

export function useLiveness() {
  return useQuery({
    queryKey: ['health', 'liveness'],
    queryFn:  api.health.liveness,
    refetchInterval: 30_000,
    retry: false,
  })
}

export function useReadiness() {
  return useQuery({
    queryKey: ['health', 'readiness'],
    queryFn:  api.health.readiness,
    refetchInterval: 30_000,
    retry: false,
  })
}

export function useSolanaAccount(pubkey: string) {
  return useQuery({
    queryKey: ['solana', 'account', pubkey],
    queryFn:  () => api.solana.account(pubkey),
    enabled:  Boolean(pubkey),
    staleTime: 60_000,
  })
}

export function useSolanaTx(sig: string) {
  return useQuery({
    queryKey: ['solana', 'tx', sig],
    queryFn:  () => api.solana.tx(sig),
    enabled:  Boolean(sig),
    staleTime: 60_000,
  })
}
