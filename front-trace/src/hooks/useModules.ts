import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { modulesApi } from '@/lib/modules-api'
import { useAuthStore } from '@/store/auth'

function useTenantId(): string {
  const user = useAuthStore((s) => s.user)
  return user?.tenant_id ?? 'default'
}

export function useModuleCatalog() {
  return useQuery({
    queryKey: ['modules', 'catalog'],
    queryFn: () => modulesApi.catalog(),
    staleTime: 5 * 60_000,
  })
}

export function useTenantModules(tenantId?: string) {
  const fallback = useTenantId()
  const tid = tenantId ?? fallback
  return useQuery({
    queryKey: ['modules', 'tenant', tid],
    queryFn: () => modulesApi.forTenant(tid),
    staleTime: 60_000,
  })
}

export function useIsModuleActive(slug: string, tenantId?: string): boolean {
  const fallback = useTenantId()
  const tid = tenantId ?? fallback
  const { data } = useQuery({
    queryKey: ['modules', 'check', tid, slug],
    queryFn: () => modulesApi.checkModule(tid, slug),
    staleTime: 5 * 60_000,
    retry: false,
  })
  return data?.is_active ?? false
}

export function useActivateModule() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ tenantId, slug }: { tenantId: string; slug: string }) =>
      modulesApi.activate(tenantId, slug),
    onSuccess: (_, { tenantId, slug }) => {
      qc.invalidateQueries({ queryKey: ['modules', 'tenant', tenantId] })
      qc.invalidateQueries({ queryKey: ['modules', 'check', tenantId, slug] })
    },
  })
}

export function useDeactivateModule() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ tenantId, slug }: { tenantId: string; slug: string }) =>
      modulesApi.deactivate(tenantId, slug),
    onSuccess: (_, { tenantId, slug }) => {
      qc.invalidateQueries({ queryKey: ['modules', 'tenant', tenantId] })
      qc.invalidateQueries({ queryKey: ['modules', 'check', tenantId, slug] })
    },
  })
}
