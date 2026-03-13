import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { userApi } from '@/lib/user-api'

// ── Templates ────────────────────────────────────────────────────────────────

export function useRoleTemplates() {
  return useQuery({
    queryKey: ['admin', 'role-templates'],
    queryFn: () => userApi.roles.listTemplates(),
  })
}

export function useCreateTemplate() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: { name: string; slug: string; description?: string; icon?: string; permissions: string[] }) =>
      userApi.roles.createTemplate(data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['admin', 'role-templates'] }),
  })
}

export function useDeleteTemplate() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => userApi.roles.deleteTemplate(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['admin', 'role-templates'] }),
  })
}

export function useCreateFromTemplate() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (templateId: string) => userApi.roles.createFromTemplate(templateId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['admin', 'roles'] }),
  })
}

// ── Roles ────────────────────────────────────────────────────────────────────

export function useRoles() {
  return useQuery({
    queryKey: ['admin', 'roles'],
    queryFn: () => userApi.roles.list(),
  })
}

export function useCreateRole() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: { name: string; slug: string; description?: string }) =>
      userApi.roles.create(data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['admin', 'roles'] }),
  })
}

export function useUpdateRole() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<{ name: string; description: string }> }) =>
      userApi.roles.update(id, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['admin', 'roles'] }),
  })
}

export function useDeleteRole() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => userApi.roles.delete(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['admin', 'roles'] }),
  })
}

export function usePermissions() {
  return useQuery({
    queryKey: ['admin', 'permissions'],
    queryFn: () => userApi.permissions.list(),
    staleTime: 300_000,
  })
}

export function useRolePermissions(roleId: string) {
  return useQuery({
    queryKey: ['admin', 'roles', roleId, 'permissions'],
    queryFn: () => userApi.roles.getPermissions(roleId),
    enabled: !!roleId,
  })
}

export function useSetRolePermissions() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ roleId, permissionIds }: { roleId: string; permissionIds: string[] }) =>
      userApi.roles.setPermissions(roleId, permissionIds),
    onSuccess: (_data, { roleId }) => {
      qc.invalidateQueries({ queryKey: ['admin', 'roles', roleId, 'permissions'] })
      qc.invalidateQueries({ queryKey: ['admin', 'roles'] })
    },
  })
}
