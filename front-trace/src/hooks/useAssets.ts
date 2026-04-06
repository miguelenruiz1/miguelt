import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '@/lib/api'
import { newUUID } from '@/lib/utils'
import type { AssetCreate, AssetMintRequest, AssetState, GenericEventRequest } from '@/types/api'

const KEYS = {
  all: ['assets'] as const,
  list: (p: object) => ['assets', 'list', p] as const,
  detail: (id: string) => ['assets', id] as const,
  events: (id: string) => ['assets', id, 'events'] as const,
}

export function useAssetList(params?: {
  product_type?: string; custodian?: string; state?: AssetState | ''; offset?: number; limit?: number
}) {
  return useQuery({
    queryKey: KEYS.list(params ?? {}),
    queryFn: () => api.assets.list(params),
  })
}

export function useAsset(id: string) {
  return useQuery({
    queryKey: KEYS.detail(id),
    queryFn: () => api.assets.get(id),
    enabled: Boolean(id),
  })
}

export function useAssetEvents(id: string) {
  return useQuery({
    queryKey: KEYS.events(id),
    queryFn: () => api.assets.events(id, { limit: 200 }),
    enabled: Boolean(id),
    refetchInterval: 15_000,
  })
}

export function useCreateAsset() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: AssetCreate) => api.assets.create(data, newUUID()),
    onSuccess: () => qc.invalidateQueries({ queryKey: KEYS.all }),
  })
}

export function useMintAsset() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: AssetMintRequest) => api.assets.mint(data, newUUID()),
    onSuccess: () => qc.invalidateQueries({ queryKey: KEYS.all }),
  })
}

// ─── Event mutations ───────────────────────────────────────────────────────────

function invalidateAsset(qc: ReturnType<typeof useQueryClient>, id: string) {
  qc.invalidateQueries({ queryKey: KEYS.detail(id) })
  qc.invalidateQueries({ queryKey: KEYS.events(id) })
  qc.invalidateQueries({ queryKey: ['assets', 'board'] })
}

/** Generic event recorder — the only way to record custody events. */
export function useRecordEvent(assetId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (input: GenericEventRequest | { data: GenericEventRequest; adminKey?: string }) => {
      const { data, adminKey } =
        'data' in input ? input : { data: input, adminKey: undefined }
      return api.assets.recordEvent(assetId, data, newUUID(), adminKey)
    },
    onSuccess: () => invalidateAsset(qc, assetId),
  })
}

export function useAnchorEvent(assetId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (eventId: string) => api.assets.anchor(assetId, eventId),
    onSuccess: () => invalidateAsset(qc, assetId),
  })
}
