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
    // 60s staleTime — post-activation the Sidebar needs to reveal the module
    // promptly. The old 5min window left users staring at a missing nav
    // section after they'd just toggled a module in /marketplace.
    staleTime: 60_000,
    retry: false,
  })
  return data?.is_active ?? false
}

export function useActivateModule() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ tenantId, slug }: { tenantId: string; slug: string }) =>
      modulesApi.activate(tenantId, slug),
    onSuccess: (_, { tenantId }) => {
      // Blast every module cache for this tenant so Sidebar, guards and the
      // marketplace all re-read without hunting for the exact queryKey.
      qc.invalidateQueries({ queryKey: ['modules'] })
      qc.invalidateQueries({ queryKey: ['modules', 'tenant', tenantId] })
    },
  })
}

export function useDeactivateModule() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ tenantId, slug }: { tenantId: string; slug: string }) =>
      modulesApi.deactivate(tenantId, slug),
    onSuccess: (_, { tenantId }) => {
      qc.invalidateQueries({ queryKey: ['modules'] })
      qc.invalidateQueries({ queryKey: ['modules', 'tenant', tenantId] })
    },
  })
}
