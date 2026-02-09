import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '@/api/client'
import type {
  Group,
  GroupDetail,
  GroupCreate,
  GroupUpdate,
  GroupMemberAdd,
  PaginatedResponse,
} from '@/types'

export function useGroups(page = 1, pageSize = 50) {
  return useQuery({
    queryKey: ['groups', page],
    queryFn: () =>
      apiClient<PaginatedResponse<Group>>(
        `/api/v1/groups/?page=${page}&page_size=${pageSize}`
      ),
  })
}

export function useGroup(id: string) {
  return useQuery({
    queryKey: ['group', id],
    queryFn: () => apiClient<GroupDetail>(`/api/v1/groups/${id}`),
    enabled: !!id,
  })
}

export function useCreateGroup() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: GroupCreate) =>
      apiClient<Group>('/api/v1/groups/', {
        method: 'POST',
        body: JSON.stringify(data),
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['groups'] })
    },
  })
}

export function useUpdateGroup(id: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: GroupUpdate) =>
      apiClient<Group>(`/api/v1/groups/${id}`, {
        method: 'PATCH',
        body: JSON.stringify(data),
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['groups'] })
      qc.invalidateQueries({ queryKey: ['group', id] })
    },
  })
}

export function useAddGroupMember(groupId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: GroupMemberAdd) =>
      apiClient<void>(`/api/v1/groups/${groupId}/members`, {
        method: 'POST',
        body: JSON.stringify(data),
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['group', groupId] })
    },
  })
}

export function useRemoveGroupMember(groupId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (userId: string) =>
      apiClient<void>(`/api/v1/groups/${groupId}/members/${userId}`, {
        method: 'DELETE',
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['group', groupId] })
    },
  })
}
