import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { mediaApi, fetchMediaReferenceCounts } from '@/lib/media-api'

const KEYS = {
  all: ['media'] as const,
  list: (p: object) => ['media', 'list', p] as const,
  detail: (id: string) => ['media', id] as const,
}

export function useMediaFiles(params?: {
  category?: string; document_type?: string; search?: string; offset?: number; limit?: number
}) {
  return useQuery({
    queryKey: KEYS.list(params ?? {}),
    queryFn: () => mediaApi.list(params),
  })
}

export function useMediaFile(id: string) {
  return useQuery({
    queryKey: KEYS.detail(id),
    queryFn: () => mediaApi.get(id),
    enabled: Boolean(id),
  })
}

export function useUploadMedia() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (vars: { file: File; category?: string; document_type?: string; title?: string; description?: string; tags?: string }) =>
      mediaApi.upload(vars.file, vars),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: KEYS.all })
    },
  })
}

export function useUploadMediaBatch() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (vars: { files: File[]; category?: string; document_type?: string }) =>
      mediaApi.uploadBatch(vars.files, vars),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: KEYS.all })
    },
  })
}

export function useUpdateMedia() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (vars: { id: string; title?: string; description?: string; category?: string; document_type?: string; tags?: string }) =>
      mediaApi.update(vars.id, vars),
    onSuccess: (_, vars) => {
      qc.invalidateQueries({ queryKey: KEYS.detail(vars.id) })
      qc.invalidateQueries({ queryKey: KEYS.all })
    },
  })
}

export function useMediaReferenceCounts(fileIds: string[]) {
  return useQuery({
    queryKey: ['media', 'references', fileIds],
    queryFn: () => fetchMediaReferenceCounts(fileIds),
    enabled: fileIds.length > 0,
    staleTime: 30_000,
  })
}

export function useDeleteMedia() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => mediaApi.delete(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: KEYS.all })
    },
  })
}
