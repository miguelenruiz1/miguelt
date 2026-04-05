import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  cmsApi, getPublicPage,
  type CreatePageRequest, type UpdatePageRequest,
  type AddSectionRequest, type UpdateSectionRequest,
  type CreateScriptRequest, type UpdateScriptRequest,
} from '@/lib/cms-api'

const KEYS = {
  all: ['cms'] as const,
  pages: ['cms', 'pages'] as const,
  page: (id: string) => ['cms', 'page', id] as const,
  publicPage: (slug: string) => ['cms', 'public', slug] as const,
}

// ─── Pages ──────────────────────────────────────────────────────────────────

export function useCmsPages() {
  return useQuery({
    queryKey: KEYS.pages,
    queryFn: cmsApi.listPages,
  })
}

export function useCmsPage(id: string) {
  return useQuery({
    queryKey: KEYS.page(id),
    queryFn: () => cmsApi.getPage(id),
    enabled: Boolean(id),
  })
}

export function useCmsPublicPage(slug: string) {
  return useQuery({
    queryKey: KEYS.publicPage(slug),
    queryFn: () => getPublicPage(slug),
    enabled: Boolean(slug),
    retry: false,
  })
}

export function useCreateCmsPage() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: CreatePageRequest) => cmsApi.createPage(data),
    onSuccess: () => qc.invalidateQueries({ queryKey: KEYS.pages }),
  })
}

export function useUpdateCmsPage(id: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: UpdatePageRequest) => cmsApi.updatePage(id, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: KEYS.page(id) })
      qc.invalidateQueries({ queryKey: KEYS.pages })
    },
  })
}

export function useDeleteCmsPage() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => cmsApi.deletePage(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: KEYS.pages }),
  })
}

export function usePublishCmsPage() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => cmsApi.publishPage(id),
    onSuccess: (_, id) => {
      qc.invalidateQueries({ queryKey: KEYS.page(id) })
      qc.invalidateQueries({ queryKey: KEYS.pages })
    },
  })
}

export function useUnpublishCmsPage() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => cmsApi.unpublishPage(id),
    onSuccess: (_, id) => {
      qc.invalidateQueries({ queryKey: KEYS.page(id) })
      qc.invalidateQueries({ queryKey: KEYS.pages })
    },
  })
}

export function useDuplicateCmsPage() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => cmsApi.duplicatePage(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: KEYS.pages }),
  })
}

// ─── Sections ───────────────────────────────────────────────────────────────

export function useAddCmsSection(pageId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: AddSectionRequest) => cmsApi.addSection(pageId, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: KEYS.page(pageId) }),
  })
}

export function useUpdateCmsSection(pageId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ sectionId, data }: { sectionId: string; data: UpdateSectionRequest }) =>
      cmsApi.updateSection(pageId, sectionId, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: KEYS.page(pageId) }),
  })
}

export function useDeleteCmsSection(pageId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (sectionId: string) => cmsApi.deleteSection(pageId, sectionId),
    onSuccess: () => qc.invalidateQueries({ queryKey: KEYS.page(pageId) }),
  })
}

export function useReorderCmsSections(pageId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (sectionIds: string[]) => cmsApi.reorderSections(pageId, sectionIds),
    onSuccess: () => qc.invalidateQueries({ queryKey: KEYS.page(pageId) }),
  })
}

// ─── Scripts ────────────────────────────────────────────────────────────────

export function useCreateCmsScript(pageId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: CreateScriptRequest) => cmsApi.createScript(pageId, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: KEYS.page(pageId) }),
  })
}

export function useUpdateCmsScript(pageId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ scriptId, data }: { scriptId: string; data: UpdateScriptRequest }) =>
      cmsApi.updateScript(pageId, scriptId, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: KEYS.page(pageId) }),
  })
}

export function useDeleteCmsScript(pageId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (scriptId: string) => cmsApi.deleteScript(pageId, scriptId),
    onSuccess: () => qc.invalidateQueries({ queryKey: KEYS.page(pageId) }),
  })
}
