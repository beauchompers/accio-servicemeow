import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '@/api/client'
import type { User, UserCreate, UserUpdate, ChangePasswordRequest, PaginatedResponse } from '@/types'

export function useUsers(page = 1, pageSize = 50) {
  return useQuery({
    queryKey: ['users', page],
    queryFn: () =>
      apiClient<PaginatedResponse<User>>(
        `/api/v1/users/?page=${page}&page_size=${pageSize}`
      ),
  })
}

export function useUser(id: string) {
  return useQuery({
    queryKey: ['user', id],
    queryFn: () => apiClient<User>(`/api/v1/users/${id}`),
    enabled: !!id,
  })
}

export function useCreateUser() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: UserCreate) =>
      apiClient<User>('/api/v1/users/', {
        method: 'POST',
        body: JSON.stringify(data),
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['users'] })
    },
  })
}

export function useUpdateUser(id: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: UserUpdate) =>
      apiClient<User>(`/api/v1/users/${id}`, {
        method: 'PATCH',
        body: JSON.stringify(data),
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['users'] })
      qc.invalidateQueries({ queryKey: ['user', id] })
    },
  })
}

export function useChangePassword() {
  return useMutation({
    mutationFn: (data: ChangePasswordRequest) =>
      apiClient<void>('/api/v1/users/me/password', {
        method: 'POST',
        body: JSON.stringify(data),
      }),
  })
}
