import { useQuery } from '@tanstack/react-query'
import { userApi } from '@/lib/user-api'

interface AuditFilters {
  action?: string
  user_id?: string
  resource_type?: string
  date_from?: string
  date_to?: string
  offset?: number
  limit?: number
}

export function useAuditLog(filters?: AuditFilters) {
  return useQuery({
    queryKey: ['admin', 'audit', filters],
    queryFn: () => userApi.audit.list(filters),
    staleTime: 30_000,
  })
}
