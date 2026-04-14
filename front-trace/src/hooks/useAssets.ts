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

export function useDeleteAsset() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, adminKey }: { id: string; adminKey: string }) =>
      api.assets.delete(id, adminKey),
    onSuccess: () => qc.invalidateQueries({ queryKey: KEYS.all }),
  })
}

// ─── Event mutations ───────────────────────────────────────────────────────────

function invalidateAsset(qc: ReturnType<typeof useQueryClient>, id: string) {
  qc.invalidateQueries({ queryKey: KEYS.detail(id) })
  qc.invalidateQueries({ queryKey: KEYS.events(id) })
  qc.invalidateQueries({ queryKey: ['assets', 'board'] })
}

/** Generic event recorder — the only way to record custody events.
 *
 * Accepts either:
 *   - A `GenericEventRequest` directly (legacy callers — backwards compatible)
 *   - A wrapper `{ payload: GenericEventRequest, adminKey?: string }` for events
 *     that require X-Admin-Key (e.g. RELEASED).
 */
type RecordEventInput =
  | GenericEventRequest
  | { payload: GenericEventRequest; adminKey?: string }

function isWrapper(
  input: RecordEventInput,
): input is { payload: GenericEventRequest; adminKey?: string } {
  return (
    typeof input === 'object'
    && input !== null
    && 'payload' in input
    && typeof (input as { payload: unknown }).payload === 'object'
  )
}

export function useRecordEvent(assetId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (input: RecordEventInput) => {
      const payload = isWrapper(input) ? input.payload : input
      const adminKey = isWrapper(input) ? input.adminKey : undefined
      return api.assets.recordEvent(assetId, payload, newUUID(), adminKey)
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
