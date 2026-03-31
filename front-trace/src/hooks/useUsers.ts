import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { userApi } from '@/lib/user-api'
import type { InviteUserRequest } from '@/types/auth'

export function useUsers(params?: { offset?: number; limit?: number }) {
  return useQuery({
    queryKey: ['admin', 'users', params],
    queryFn: () => userApi.users.list(params),
  })
}

export function useInviteUser() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: InviteUserRequest) => userApi.users.invite(data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['admin', 'users'] }),
  })
}

export function useResendInvitation() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => userApi.users.resendInvitation(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['admin', 'users'] }),
  })
}

export function useUpdateUser() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: Record<string, unknown> }) =>
      userApi.users.update(id, data as any),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['admin', 'users'] }),
  })
}

export function useDeactivateUser() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => userApi.users.deactivate(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['admin', 'users'] }),
  })
}

export function useReactivateUser() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => userApi.users.reactivate(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['admin', 'users'] }),
  })
}

export function useAssignRole() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ userId, roleId }: { userId: string; roleId: string }) =>
      userApi.users.assignRole(userId, roleId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['admin', 'users'] }),
  })
}

export function useRemoveRole() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ userId, roleId }: { userId: string; roleId: string }) =>
      userApi.users.removeRole(userId, roleId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['admin', 'users'] }),
  })
}

export function useEmailTemplates() {
  return useQuery({
    queryKey: ['admin', 'email-templates'],
    queryFn: () => userApi.emailTemplates.list(),
  })
}

export function useEmailTemplate(id: string) {
  return useQuery({
    queryKey: ['admin', 'email-templates', id],
    queryFn: () => userApi.emailTemplates.get(id),
    enabled: !!id,
  })
}

export function useUpdateEmailTemplate() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<{ subject: string; html_body: string; description: string; is_active: boolean }> }) =>
      userApi.emailTemplates.update(id, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['admin', 'email-templates'] }),
  })
}

export function useTestEmailTemplate() {
  return useMutation({
    mutationFn: ({ id, to }: { id: string; to?: string }) =>
      userApi.emailTemplates.test(id, to),
  })
}

