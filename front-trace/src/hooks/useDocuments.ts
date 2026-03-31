import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '@/lib/api'

const KEYS = {
  eventDocs: (assetId: string, eventId: string) => ['documents', assetId, eventId] as const,
  requirements: (assetId: string, eventType: string) => ['doc-requirements', assetId, eventType] as const,
}

export function useEventDocuments(assetId: string, eventId: string) {
  return useQuery({
    queryKey: KEYS.eventDocs(assetId, eventId),
    queryFn: () => api.documents.list(assetId, eventId),
    enabled: Boolean(assetId && eventId),
  })
}

export function useDocumentRequirements(assetId: string, eventType: string) {
  return useQuery({
    queryKey: KEYS.requirements(assetId, eventType),
    queryFn: () => api.documents.requirements(assetId, eventType),
    enabled: Boolean(assetId && eventType),
  })
}

export function useUploadEventDocuments(assetId: string, eventId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (vars: { files: File[]; documentType: string; title?: string }) =>
      api.documents.upload(assetId, eventId, vars.files, vars.documentType, vars.title),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: KEYS.eventDocs(assetId, eventId) })
      qc.invalidateQueries({ queryKey: ['assets', assetId, 'events'] })
    },
  })
}

export function useLinkMediaToEvent(assetId: string, eventId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (vars: { mediaFileId: string; documentType: string }) =>
      api.documents.linkExisting(assetId, eventId, vars.mediaFileId, vars.documentType),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: KEYS.eventDocs(assetId, eventId) })
    },
  })
}

export function useUnlinkDocument(assetId: string, eventId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (linkId: string) => api.documents.unlink(assetId, eventId, linkId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: KEYS.eventDocs(assetId, eventId) })
    },
  })
}
