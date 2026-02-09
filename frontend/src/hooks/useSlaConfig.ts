import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '@/api/client'
import type { SlaConfigItem } from '@/types'

export function useSlaConfig() {
  return useQuery({
    queryKey: ['sla-config'],
    queryFn: () => apiClient<SlaConfigItem[]>('/api/v1/sla-config'),
  })
}

export function useUpdateSlaConfig() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (configs: SlaConfigItem[]) =>
      apiClient<SlaConfigItem[]>('/api/v1/sla-config', {
        method: 'PATCH',
        body: JSON.stringify({ configs }),
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['sla-config'] })
    },
  })
}
