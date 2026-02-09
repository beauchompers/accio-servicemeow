import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '@/api/client'
import type {
  Ticket,
  TicketDetail,
  TicketCreate,
  TicketUpdate,
  TicketNote,
  NoteCreate,
  Attachment,
  PaginatedResponse,
} from '@/types'

interface TicketFilters {
  status?: string
  priority?: string
  assigned_group_id?: string
  assigned_user_id?: string
  search?: string
  sla_breached?: boolean
  sort_by?: string
  sort_order?: string
  page?: number
  page_size?: number
}

function buildTicketParams(filters: TicketFilters): string {
  const params = new URLSearchParams()
  if (filters.status) params.set('status', filters.status)
  if (filters.priority) params.set('priority', filters.priority)
  if (filters.assigned_group_id) params.set('assigned_group_id', filters.assigned_group_id)
  if (filters.assigned_user_id) params.set('assigned_user_id', filters.assigned_user_id)
  if (filters.search) params.set('search', filters.search)
  if (filters.sla_breached !== undefined) params.set('sla_breached', String(filters.sla_breached))
  if (filters.sort_by) params.set('sort_by', filters.sort_by)
  if (filters.sort_order) params.set('sort_order', filters.sort_order)
  params.set('page', String(filters.page ?? 1))
  params.set('page_size', String(filters.page_size ?? 25))
  return params.toString()
}

export function useTickets(filters: TicketFilters = {}) {
  return useQuery({
    queryKey: ['tickets', filters],
    queryFn: () =>
      apiClient<PaginatedResponse<Ticket>>(
        `/api/v1/tickets/?${buildTicketParams(filters)}`
      ),
  })
}

export function useTicket(id: string) {
  return useQuery({
    queryKey: ['ticket', id],
    queryFn: () => apiClient<TicketDetail>(`/api/v1/tickets/${id}`),
    enabled: !!id,
  })
}

export function useCreateTicket() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: TicketCreate) =>
      apiClient<Ticket>('/api/v1/tickets/', {
        method: 'POST',
        body: JSON.stringify(data),
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['tickets'] })
    },
  })
}

export function useUpdateTicket(id: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: TicketUpdate) =>
      apiClient<Ticket>(`/api/v1/tickets/${id}`, {
        method: 'PATCH',
        body: JSON.stringify(data),
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['ticket', id] })
      qc.invalidateQueries({ queryKey: ['tickets'] })
    },
  })
}

export function useDeleteTicket() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) =>
      apiClient<void>(`/api/v1/tickets/${id}`, { method: 'DELETE' }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['tickets'] })
    },
  })
}

export function useCreateNote(ticketId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: NoteCreate) =>
      apiClient<TicketNote>(`/api/v1/tickets/${ticketId}/notes`, {
        method: 'POST',
        body: JSON.stringify(data),
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['ticket', ticketId] })
    },
  })
}

export function useUploadAttachment(ticketId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (file: File) => {
      const formData = new FormData()
      formData.append('file', file)
      return apiClient<Attachment>(`/api/v1/tickets/${ticketId}/attachments`, {
        method: 'POST',
        body: formData,
      })
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['ticket', ticketId] })
    },
  })
}

export function useDeleteAttachment(ticketId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (attachmentId: string) =>
      apiClient<void>(`/api/v1/tickets/attachments/${attachmentId}`, {
        method: 'DELETE',
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['ticket', ticketId] })
    },
  })
}

export function useUploadEditorImage() {
  return useMutation({
    mutationFn: async (file: File) => {
      const formData = new FormData()
      formData.append('file', file)
      return apiClient<{ url: string }>('/api/v1/tickets/images', {
        method: 'POST',
        body: formData,
      })
    },
  })
}
