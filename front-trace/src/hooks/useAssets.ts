import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '@/lib/api'
import { newUUID } from '@/lib/utils'
import type {
  AssetCreate, AssetMintRequest, AssetState, HandoffRequest, ArrivedRequest,
  LoadedRequest, QCRequest, ReleaseRequest, BurnRequest,
} from '@/types/api'

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
    refetchInterval: 15_000, // poll every 15s to catch anchor updates
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

export function useHandoff(assetId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: HandoffRequest) => api.assets.handoff(assetId, data, newUUID()),
    onSuccess: () => invalidateAsset(qc, assetId),
  })
}

export function useArrived(assetId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: ArrivedRequest) => api.assets.arrived(assetId, data),
    onSuccess: () => invalidateAsset(qc, assetId),
  })
}

export function useLoaded(assetId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: LoadedRequest) => api.assets.loaded(assetId, data),
    onSuccess: () => invalidateAsset(qc, assetId),
  })
}

export function useQC(assetId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: QCRequest) => api.assets.qc(assetId, data),
    onSuccess: () => invalidateAsset(qc, assetId),
  })
}

export function useRelease(assetId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ data, adminKey }: { data: ReleaseRequest; adminKey: string }) =>
      api.assets.release(assetId, data, adminKey, newUUID()),
    onSuccess: () => invalidateAsset(qc, assetId),
  })
}

export function useBurn(assetId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: BurnRequest) => api.assets.burn(assetId, data, newUUID()),
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
