import { QueryClient, MutationCache } from '@tanstack/react-query'
import { ApiError } from '@/lib/api'

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      // 60s default staleTime — most data is not volatile enough to refetch
      // every time the user changes browser tab.
      staleTime: 60_000,
      gcTime:    5 * 60_000,
      retry: (failureCount, error) => {
        if (error instanceof ApiError && error.status < 500) return false
        return failureCount < 2
      },
      // Disabled: refetching on tab focus produces tons of unnecessary load
      // for slowly-changing data. Pages that need fresh data on focus should
      // opt in via per-query refetchOnWindowFocus: true.
      refetchOnWindowFocus: false,
    },
    mutations: {
      retry: false,
    },
  },
  mutationCache: new MutationCache({
    onError: (error) => {
      const msg = error instanceof Error ? error.message : 'Error inesperado'
      if (msg) {
        import('@/store/toast').then(({ useToast }) => {
          try { useToast.getState().error(msg) } catch {}
        }).catch(() => {})
      }
    },
  }),
})
