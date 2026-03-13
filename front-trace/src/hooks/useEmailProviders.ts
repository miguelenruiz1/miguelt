import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { emailProvidersApi } from '@/lib/email-providers-api'
import type { EmailProviderConfigSave } from '@/types/email-providers'

// ─── Queries ──────────────────────────────────────────────────────────────────

export function useEmailProviderCatalog() {
  return useQuery({
    queryKey: ['email-providers', 'catalog'],
    queryFn: () => emailProvidersApi.catalog(),
    staleTime: 60_000,
  })
}

export function useEmailProviderConfigs() {
  return useQuery({
    queryKey: ['email-providers', 'configs'],
    queryFn: () => emailProvidersApi.listConfigs(),
  })
}

// ─── Mutations ────────────────────────────────────────────────────────────────

export function useSaveEmailProviderConfig() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ slug, body }: { slug: string; body: EmailProviderConfigSave }) =>
      emailProvidersApi.saveConfig(slug, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['email-providers', 'configs'] })
    },
  })
}

export function useSetActiveEmailProvider() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (slug: string) => emailProvidersApi.setActive(slug),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['email-providers', 'configs'] })
    },
  })
}

export function useDeleteEmailProviderConfig() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (slug: string) => emailProvidersApi.deleteConfig(slug),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['email-providers', 'configs'] })
    },
  })
}

export function useTestEmailProvider() {
  return useMutation({
    mutationFn: ({ slug, to }: { slug: string; to: string }) =>
      emailProvidersApi.testProvider(slug, to),
  })
}
