import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '@/lib/api'
import type { CustodianTypeCreate, CustodianTypeUpdate, OrganizationCreate, OrganizationUpdate } from '@/types/api'

const KEYS = {
  types: ['custodian-types'] as const,
  orgs: (p?: object) => ['organizations', p ?? {}] as const,
  org: (id: string) => ['organizations', id] as const,
  orgWallets: (id: string) => ['organizations', id, 'wallets'] as const,
  orgAssets: (id: string) => ['organizations', id, 'assets'] as const,
}

// ─── Custodian Types ───────────────────────────────────────────────────────────

export function useCustodianTypes() {
  return useQuery({
    queryKey: KEYS.types,
    queryFn: () => api.taxonomy.listTypes(),
    staleTime: 30_000,
  })
}

export function useCreateCustodianType() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: CustodianTypeCreate) => api.taxonomy.createType(data),
    onSuccess: () => qc.invalidateQueries({ queryKey: KEYS.types }),
  })
}

export function useUpdateCustodianType() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: CustodianTypeUpdate }) =>
      api.taxonomy.updateType(id, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: KEYS.types }),
  })
}

export function useDeleteCustodianType() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => api.taxonomy.deleteType(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: KEYS.types }),
  })
}

// ─── Organizations ─────────────────────────────────────────────────────────────

export function useOrganizations(params?: { custodian_type_id?: string; status?: string }) {
  return useQuery({
    queryKey: KEYS.orgs(params),
    queryFn: () => api.taxonomy.listOrgs(params),
    staleTime: 15_000,
  })
}

export function useOrganization(id: string) {
  return useQuery({
    queryKey: KEYS.org(id),
    queryFn: () => api.taxonomy.getOrg(id),
    enabled: Boolean(id),
  })
}

export function useCreateOrganization() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: OrganizationCreate) => api.taxonomy.createOrg(data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['organizations'] }),
  })
}

export function useUpdateOrganization() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: OrganizationUpdate }) =>
      api.taxonomy.updateOrg(id, data),
    onSuccess: (_, { id }) => {
      qc.invalidateQueries({ queryKey: ['organizations'] })
      qc.invalidateQueries({ queryKey: KEYS.org(id) })
    },
  })
}

export function useDeleteOrganization() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => api.taxonomy.deleteOrg(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['organizations'] }),
  })
}

export function useOrgWallets(id: string) {
  return useQuery({
    queryKey: KEYS.orgWallets(id),
    queryFn: () => api.taxonomy.getOrgWallets(id),
    enabled: Boolean(id),
  })
}

export function useOrgAssets(id: string) {
  return useQuery({
    queryKey: KEYS.orgAssets(id),
    queryFn: () => api.taxonomy.getOrgAssets(id),
    enabled: Boolean(id),
  })
}
