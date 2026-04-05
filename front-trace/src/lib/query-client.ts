import { QueryClient, MutationCache } from '@tanstack/react-query'
import { ApiError } from '@/lib/api'

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      gcTime:    5 * 60_000,
      retry: (failureCount, error) => {
        if (error instanceof ApiError && error.status < 500) return false
        return failureCount < 2
      },
      refetchOnWindowFocus: true,
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
