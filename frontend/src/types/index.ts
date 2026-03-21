export type Vendor = 'cisco_ios' | 'cisco_ios_xe' | 'juniper_junos' | 'mikrotik_routeros' | 'huawei' | 'arista_eos' | 'vyos' | 'frr_linux' | 'generic'
export type RouterStatus = 'online' | 'offline' | 'warning' | 'unknown'
export type JobType = 'backup' | 'command' | 'template' | 'ping'
export type JobStatus = 'pending' | 'running' | 'success' | 'failed'

export interface Router {
  id: number
  hostname: string
  ip_address: string
  port: number
  vendor: Vendor
  username: string
  password?: string
  ssh_key?: string
  location?: string
  tags: string[]
  notes?: string
  status: RouterStatus
  uptime_seconds?: number
  version?: string
  last_seen?: string
  created_at: string
  updated_at?: string
}

export interface ConfigBackup {
  id: number
  router_id: number
  content?: string
  checksum: string
  source: string
  size_bytes: number
  filename?: string
  created_at: string
}

export interface ConfigTemplate {
  id: number
  name: string
  description?: string
  category: TemplateCategory
  vendor: Vendor
  content: string
  variables: Record<string, any>
  is_builtin: boolean
  created_at: string
  updated_at?: string
}

export type TemplateCategory = 'ospf' | 'bgp' | 'vlan' | 'qos' | 'firewall' | 'nat' | 'routing' | 'security' | 'wireless' | 'vpn' | 'interface' | 'other'

export interface AISuggestion {
  suggestion: string
  configuration: string
  explanation?: string
}

export interface TemplateCategoryInfo {
  value: TemplateCategory
  label: string
  icon: string
}

export interface ScheduledJob {
  id: number
  name: string
  job_type: JobType
  router_id?: number
  template_id?: number
  command?: string
  schedule: string
  enabled: boolean
  last_run?: string
  last_status?: JobStatus
  last_output?: string
  ping_target?: string
  ping_source?: string
  ping_count?: number
  created_at: string
  updated_at?: string
}

export interface DashboardStats {
  total_routers: number
  online_routers: number
  offline_routers: number
  warning_routers: number
  backups_today: number
  backups_this_week: number
  failed_jobs: number
}

export interface CommandResponse {
  output: string
  success: boolean
  error?: string
}

export interface ConnectionTestResponse {
  success: boolean
  message: string
  latency_ms?: number
}

export interface PerformanceMetric {
  id: number
  router_id: number
  cpu_percent?: number
  memory_percent?: number
  memory_used_mb?: number
  memory_total_mb?: number
  disk_percent?: number
  uptime_seconds?: number
  collected_at: string
}

export interface RouterMetrics {
  router_id: number
  hostname: string
  cpu_percent?: number
  memory_percent?: number
  memory_used_mb?: number
  memory_total_mb?: number
  disk_percent?: number
  uptime_seconds?: number
  collected_at?: string
}

export interface MetricHistoryPoint {
  timestamp: string
  cpu_percent?: number
  memory_percent?: number
}

export interface PingMetric {
  id: number
  target: string
  latency_avg_ms?: number
  latency_min_ms?: number
  latency_max_ms?: number
  packet_loss_percent: number
  packets_sent: number
  packets_received: number
  collected_at: string
}

export interface PingMetricHistory {
  job_id: number
  hours: number
  data: PingMetric[]
}

export interface RouterGroup {
  id: number
  name: string
  description?: string
  router_ids: number[]
  tags: string[]
  created_at: string
  updated_at?: string
}

export interface BatchCommandResult {
  router_id: number
  hostname: string
  success: boolean
  output?: string
  error?: string
}

export interface BatchCommandResponse {
  results: BatchCommandResult[]
  total: number
  successful: number
  failed: number
}

export interface AuditLog {
  id: number
  action: string
  entity_type: string
  entity_id?: number
  details: Record<string, any>
  ip_address?: string
  created_at: string
}

export interface RemediationScript {
  id: number
  name: string
  description?: string
  trigger_condition: string
  commands: string[]
  enabled: boolean
  auto_execute: boolean
  created_at: string
  updated_at?: string
}

export interface NotificationChannel {
  id: number
  name: string
  channel_type: string
  config: Record<string, any>
  enabled: boolean
  events: string[]
  created_at: string
  updated_at?: string
}

export interface Webhook {
  id: number
  name: string
  url: string
  events: string[]
  headers: Record<string, string>
  enabled: boolean
  retry_count: number
  last_triggered?: string
  created_at: string
  updated_at?: string
}

export interface UptimeReport {
  router_id: number
  hostname: string
  uptime_percent: number
  total_checks: number
  successful_checks: number
  failed_checks: number
  avg_latency_ms?: number
}

export interface ConfigChange {
  id: number
  router_id: number
  backup_id?: number
  change_type: string
  detected_at: string
  details: Record<string, any>
}

export interface FirmwareInfo {
  router_id: number
  hostname: string
  version?: string
  os_type?: string
  collected_at: string
}

export interface RouterLog {
  id: number
  router_id: number
  level: string
  source: string
  message: string
  details: Record<string, any>
  created_at: string
}
