import { useQuery } from '@tanstack/react-query'
import { useMemo } from 'react'
import { userApi } from '@/lib/user-api'

export interface UserInfo {
  full_name: string
  email: string
}

/**
 * Resolves user IDs to names/emails via user-service.
 * Deduplicates IDs and caches results with a long staleTime.
 */
export function useUserLookup(userIds: (string | null | undefined)[]) {
  const uniqueIds = useMemo(
    () => [...new Set(userIds.filter((id): id is string => !!id))],
    [JSON.stringify(userIds)],
  )

  const { data, isLoading } = useQuery({
    queryKey: ['users', 'lookup', uniqueIds],
    queryFn: async () => {
      if (uniqueIds.length === 0) return new Map<string, UserInfo>()
      const res = await userApi.users.list({ offset: 0, limit: 200 })
      const map = new Map<string, UserInfo>()
      for (const u of res.items) {
        if (uniqueIds.includes(u.id)) {
          map.set(u.id, { full_name: u.full_name ?? u.username, email: u.email })
        }
      }
      return map
    },
    enabled: uniqueIds.length > 0,
    staleTime: 10 * 60_000,
  })

  return {
    users: data ?? new Map<string, UserInfo>(),
    isLoading,
    resolve: (id: string | null | undefined): string => {
      if (!id) return '—'
      const u = data?.get(id)
      return u ? u.full_name : id.slice(0, 8) + '…'
    },
  }
}
