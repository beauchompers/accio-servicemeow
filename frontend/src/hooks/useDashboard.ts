import { useQuery } from '@tanstack/react-query'
import { apiClient } from '@/api/client'
import type { AuditLogEntry, PaginatedResponse } from '@/types'

interface DashboardSummary {
  total_tickets: number
  by_status: { status: string; count: number }[]
  by_priority: { priority: string; count: number }[]
  by_group: { group_name: string; count: number }[]
}

interface SlaMetrics {
  mtta_seconds: number | null
  mttr_seconds: number | null
  group_name: string | null
  priority: string | null
}

export function useDashboardSummary() {
  return useQuery({
    queryKey: ['dashboard', 'summary'],
    queryFn: () => apiClient<DashboardSummary>('/api/v1/dashboard/summary'),
    refetchInterval: 30000,
  })
}

export function useSlaMetrics() {
  return useQuery({
    queryKey: ['dashboard', 'sla'],
    queryFn: () => apiClient<SlaMetrics>('/api/v1/dashboard/sla'),
    refetchInterval: 30000,
  })
}

export function useRecentActivity(page = 1, pageSize = 50) {
  return useQuery({
    queryKey: ['dashboard', 'activity', page],
    queryFn: () =>
      apiClient<PaginatedResponse<AuditLogEntry>>(
        `/api/v1/dashboard/activity?page=${page}&page_size=${pageSize}`
      ),
    refetchInterval: 30000,
  })
}
