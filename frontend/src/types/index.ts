// ─── Enums (string literal unions) ───────────────────────────────────────────

export type TicketStatus = 'open' | 'under_investigation' | 'resolved'

export type TicketPriority = 'critical' | 'high' | 'medium' | 'low'

export type UserRole = 'admin' | 'manager' | 'agent'

export type ActorType = 'user' | 'api_key' | 'system'

// ─── Auth ────────────────────────────────────────────────────────────────────

export interface LoginRequest {
  username: string
  password: string
}

export interface TokenResponse {
  access_token: string
  token_type: string
}

// ─── Users ───────────────────────────────────────────────────────────────────

export interface User {
  id: string
  username: string
  email: string
  full_name: string
  role: UserRole
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface UserCreate {
  username: string
  email: string
  full_name: string
  password: string
  role: UserRole
}

export interface UserUpdate {
  email?: string
  full_name?: string
  role?: UserRole
  is_active?: boolean
  password?: string
}

export interface ChangePasswordRequest {
  current_password: string
  new_password: string
}

// ─── Groups ──────────────────────────────────────────────────────────────────

export interface GroupMember {
  user_id: string
  username: string
  full_name: string
  is_lead: boolean
  joined_at: string
}

export interface Group {
  id: string
  name: string
  description: string
  member_count: number
  created_at: string
}

export interface GroupDetail extends Group {
  members: GroupMember[]
}

export interface GroupCreate {
  name: string
  description?: string
}

export interface GroupUpdate {
  name?: string
  description?: string
}

export interface GroupMemberAdd {
  user_id: string
  is_lead?: boolean
}

// ─── SLA ─────────────────────────────────────────────────────────────────────

export interface SlaStatus {
  target_minutes: number | null
  elapsed_minutes: number
  percentage: number
  is_breached: boolean
  is_at_risk: boolean
  remaining_minutes: number | null
  is_resolved: boolean
  outcome: 'within_sla' | 'over_sla' | null
}

export interface MttaStatus {
  target_minutes: number | null
  elapsed_minutes: number
  percentage: number
  is_breached: boolean
  is_met: boolean
  is_pending: boolean
}

// ─── Tickets ─────────────────────────────────────────────────────────────────

export interface Ticket {
  id: string
  ticket_number: string
  title: string
  status: TicketStatus
  priority: TicketPriority
  assigned_group_id?: string
  assigned_group_name?: string
  assigned_user_id?: string
  assigned_user_name?: string
  created_by_id: string
  created_by_name: string
  created_at: string
  updated_at: string
  sla_status?: SlaStatus | null
}

export interface TicketDetail extends Ticket {
  description: string
  resolved_at?: string
  first_assigned_at?: string
  sla_target_assign_minutes?: number | null
  mtta_status?: MttaStatus | null
  notes: TicketNote[]
  attachments: Attachment[]
  audit_log: AuditLogEntry[]
}

export interface TicketCreate {
  title: string
  description: string
  priority: TicketPriority
  assigned_group_id: string
  assigned_user_id?: string
}

export interface TicketUpdate {
  title?: string
  description?: string
  status?: TicketStatus
  priority?: TicketPriority
  assigned_group_id?: string
  assigned_user_id?: string | null
}

// ─── Notes ───────────────────────────────────────────────────────────────────

export interface TicketNote {
  id: string
  ticket_id: string
  author_id: string
  author_name: string
  content: string
  is_internal: boolean
  created_at: string
}

export interface NoteCreate {
  content: string
  is_internal?: boolean
}

// ─── Attachments ─────────────────────────────────────────────────────────────

export interface Attachment {
  id: string
  ticket_id: string
  filename: string
  original_filename: string
  file_size: number
  content_type: string
  uploaded_by_id: string
  uploaded_by_name: string
  uploaded_at: string
}

// ─── Audit Log ───────────────────────────────────────────────────────────────

export interface AuditLogEntry {
  id: string
  ticket_id: string
  ticket_number?: string
  actor_id?: string
  actor_type: ActorType
  actor_name?: string
  action: string
  field_changed?: string
  old_value?: string
  new_value?: string
  metadata?: Record<string, unknown>
  created_at: string
}

// ─── Dashboard ───────────────────────────────────────────────────────────────

export interface StatusCount {
  status: TicketStatus
  count: number
}

export interface PriorityCount {
  priority: TicketPriority
  count: number
}

export interface GroupSla {
  group_name: string
  mtta_minutes?: number
  mttr_minutes?: number
  breached_count: number
}

export interface DashboardSummary {
  status_counts: StatusCount[]
  priority_counts: PriorityCount[]
  total_open: number
}

export interface SlaMetrics {
  overall_mtta_minutes?: number
  overall_mttr_minutes?: number
  by_group: GroupSla[]
}

// ─── API Keys ────────────────────────────────────────────────────────────────

export interface ApiKey {
  id: string
  name: string
  key_prefix: string
  user_id: string
  is_active: boolean
  last_used_at?: string
  expires_at?: string
  created_at: string
}

export interface ApiKeyCreate {
  name: string
}

export interface ApiKeyCreateResponse {
  id: string
  name: string
  key_prefix: string
  plain_key: string
  created_at: string
}

// ─── SLA Config ──────────────────────────────────────────────────────────────

export interface SlaConfigItem {
  priority: TicketPriority
  target_assign_minutes: number
  target_resolve_minutes: number
}

// ─── Pagination ──────────────────────────────────────────────────────────────

export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  page_size: number
  pages: number
}
