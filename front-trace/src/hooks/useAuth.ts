import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { userApi } from '@/lib/user-api'
import { useAuthStore } from '@/store/auth'
import { useConfirmStore } from '@/store/confirm'

export function useLogin() {
  const setAuth = useAuthStore((s) => s.setAuth)
  const navigate = useNavigate()
  return useMutation({
    mutationFn: (data: { email: string; password: string }) => userApi.auth.login(data),
    onSuccess: (resp) => {
      setAuth(resp.user, resp.access_token, resp.refresh_token, resp.permissions)
      navigate('/')
    },
  })
}

export function useRegister() {
  const navigate = useNavigate()
  return useMutation({
    mutationFn: (data: {
      email: string
      username: string
      full_name: string
      password: string
      phone?: string
      job_title?: string
      company?: string
      tenant_id?: string
    }) => userApi.auth.register(data),
    onSuccess: () => navigate('/login'),
  })
}

export function useLogout() {
  const clearAuth = useAuthStore((s) => s.clearAuth)
  const navigate = useNavigate()
  const qc = useQueryClient()
  return useMutation({
    mutationFn: () => userApi.auth.logout(),
    onSettled: () => {
      clearAuth()
      useConfirmStore.getState().cancel()
      document.body.style.overflow = ''
      qc.clear()
      navigate('/login')
    },
  })
}

export function useCurrentUser() {
  const accessToken = useAuthStore((s) => s.accessToken)
  return useQuery({
    queryKey: ['auth', 'me'],
    queryFn: () => userApi.auth.me(),
    enabled: !!accessToken,
    staleTime: 60_000,
  })
}

export function useUpdateProfile() {
  const qc = useQueryClient()
  const setAuth = useAuthStore((s) => s.setAuth)
  return useMutation({
    mutationFn: (data: Partial<{
      full_name: string; username: string; email: string; avatar_url: string;
      phone: string; job_title: string; company: string; bio: string;
      timezone: string; language: string;
    }>) => userApi.auth.updateMe(data),
    onSuccess: (updatedUser) => {
      // Read current tokens at callback time to avoid stale closure
      const { accessToken, refreshToken, permissions } = useAuthStore.getState()
      if (updatedUser && accessToken && refreshToken) {
        setAuth(updatedUser, accessToken, refreshToken, permissions)
      }
      qc.invalidateQueries({ queryKey: ['auth', 'me'] })
    },
  })
}

export function useChangePassword() {
  return useMutation({
    mutationFn: (data: { current_password: string; new_password: string }) =>
      userApi.auth.changePassword(data),
  })
}

export function useUploadAvatar() {
  const qc = useQueryClient()
  const setAuth = useAuthStore((s) => s.setAuth)
  return useMutation({
    mutationFn: (file: File) => userApi.auth.uploadAvatar(file),
    onSuccess: (updatedUser) => {
      const { accessToken, refreshToken, permissions } = useAuthStore.getState()
      if (updatedUser && accessToken && refreshToken) {
        setAuth(updatedUser, accessToken, refreshToken, permissions)
      }
      qc.invalidateQueries({ queryKey: ['auth', 'me'] })
    },
  })
}

export function useDeleteAvatar() {
  const qc = useQueryClient()
  const setAuth = useAuthStore((s) => s.setAuth)
  return useMutation({
    mutationFn: () => userApi.auth.deleteAvatar(),
    onSuccess: (updatedUser) => {
      const { accessToken, refreshToken, permissions } = useAuthStore.getState()
      if (updatedUser && accessToken && refreshToken) {
        setAuth(updatedUser, accessToken, refreshToken, permissions)
      }
      qc.invalidateQueries({ queryKey: ['auth', 'me'] })
    },
  })
}
