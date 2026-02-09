import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '@/api/client'
import type { ApiKey, ApiKeyCreate, ApiKeyCreateResponse } from '@/types'

export function useApiKeys() {
  return useQuery({
    queryKey: ['api-keys'],
    queryFn: () =>
      apiClient<ApiKey[]>('/api/v1/api-keys/'),
  })
}

export function useCreateApiKey() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: ApiKeyCreate) =>
      apiClient<ApiKeyCreateResponse>('/api/v1/api-keys/', {
        method: 'POST',
        body: JSON.stringify(data),
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['api-keys'] })
    },
  })
}

export function useRevokeApiKey() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) =>
      apiClient<void>(`/api/v1/api-keys/${id}`, { method: 'DELETE' }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['api-keys'] })
    },
  })
}
