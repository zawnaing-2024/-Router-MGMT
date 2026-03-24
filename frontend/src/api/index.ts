import axios from 'axios'
import type { Router, ConfigBackup, ConfigTemplate, ScheduledJob, DashboardStats, CommandResponse, ConnectionTestResponse, PingMetricHistory, RouterGroup, BatchCommandResponse, AuditLog, RemediationScript, NotificationChannel, Webhook, UptimeReport, ConfigChange, FirmwareInfo, RouterLog } from '@/types'

const api = axios.create({
  baseURL: '/api',
  headers: {
    'Content-Type': 'application/json'
  }
})

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token')
      localStorage.removeItem('user')
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

export const routerApi = {
  list: (params?: { skip?: number; limit?: number; vendor?: string; status?: string; search?: string; project_id?: number; group_id?: number }) =>
    api.get<Router[]>('/routers', { params }),

  get: (id: number) =>
    api.get<Router>(`/routers/${id}`),

  create: (data: Partial<Router>) =>
    api.post<Router>('/routers', data),

  update: (id: number, data: Partial<Router>) =>
    api.put<Router>(`/routers/${id}`, data),

  delete: (id: number) =>
    api.delete(`/routers/${id}`),

  backup: (id: number) =>
    api.post(`/routers/${id}/backup`),

  testConnection: (id: number) =>
    api.post<ConnectionTestResponse>(`/routers/${id}/connect`),

  executeCommand: (id: number, command: string) =>
    api.post<CommandResponse>(`/routers/${id}/command`, { command }),

  updateCustomCommands: (id: number, commands: { id: string; name: string; command: string }[]) =>
    api.put(`/routers/${id}/custom-commands`, { commands })
}

export const backupApi = {
  list: (params?: { skip?: number; limit?: number; router_id?: number }) =>
    api.get<ConfigBackup[]>('/backups', { params }),

  get: (id: number) =>
    api.get<ConfigBackup>(`/backups/${id}`),

  restore: (id: number) =>
    api.post(`/backups/${id}/restore`),

  delete: (id: number) =>
    api.delete(`/backups/${id}`),

  compare: (backupId1: number, backupId2: number) =>
    api.post('/backups/compare', { backup_id_1: backupId1, backup_id_2: backupId2 }),

  getRouterBackups: (routerId: number, limit?: number) =>
    api.get<ConfigBackup[]>(`/backups/router/${routerId}`, { params: { limit } })
}

export const templateApi = {
  list: (params?: { skip?: number; limit?: number; vendor?: string; category?: string }) =>
    api.get<ConfigTemplate[]>('/templates', { params }),

  get: (id: number) =>
    api.get<ConfigTemplate>(`/templates/${id}`),

  create: (data: Partial<ConfigTemplate>) =>
    api.post<ConfigTemplate>('/templates', data),

  update: (id: number, data: Partial<ConfigTemplate>) =>
    api.put<ConfigTemplate>(`/templates/${id}`, data),

  delete: (id: number) =>
    api.delete(`/templates/${id}`),

  render: (id: number, variables: Record<string, any>) =>
    api.post(`/templates/${id}/render`, { variables }),

  getAiSuggestion: (data: { category: string; vendor: string; description?: string; network_info?: string }) =>
    api.post<AISuggestion>('/templates/ai-suggest', data),

  generateFromPrompt: (data: { prompt: string; vendor: string }) =>
    api.post<PromptGenerateResult>('/templates/prompt/generate', data),

  applyConfig: (data: { configuration: string; router_id: number }) =>
    api.post<ApplyConfigResult>('/templates/prompt/apply', data)
}

export interface PromptGenerateResult {
  prompt: string
  vendor: string
  configuration: string
  explanation: string
}

export interface ApplyConfigResult {
  success: boolean
  output: string
  error?: string
}

export const jobApi = {
  list: (params?: { skip?: number; limit?: number; enabled?: boolean; job_type?: string }) =>
    api.get<ScheduledJob[]>('/jobs', { params }),

  get: (id: number) =>
    api.get<ScheduledJob>(`/jobs/${id}`),

  create: (data: Partial<ScheduledJob>) =>
    api.post<ScheduledJob>('/jobs', data),

  update: (id: number, data: Partial<ScheduledJob>) =>
    api.put<ScheduledJob>(`/jobs/${id}`, data),

  delete: (id: number) =>
    api.delete(`/jobs/${id}`),

  runNow: (id: number) =>
    api.post(`/jobs/${id}/run`)
}

export const dashboardApi = {
  getStats: () =>
    api.get<DashboardStats>('/dashboard/stats')
}

export const metricsApi = {
  getLatest: (routerId: number) =>
    api.get(`/routers/${routerId}/metrics/latest`),

  getHistory: (routerId: number, params?: { hours?: number; limit?: number }) =>
    api.get(`/routers/${routerId}/metrics/history`, { params }),

  collect: (routerId: number) =>
    api.post(`/routers/${routerId}/metrics/collect`),

  getAllLatest: () =>
    api.get('/routers/metrics/all-latest'),

  collectAll: () =>
    api.post('/routers/metrics/collect-all'),

  cleanup: (days: number = 30) =>
    api.delete('/routers/metrics/cleanup', { params: { days } }),

  getNetworkInfo: (routerId: number) =>
    api.get(`/routers/${routerId}/network-info`)
}

export const pingMetricsApi = {
  getJobHistory: (jobId: number, params?: { hours?: number }) =>
    api.get<PingMetricHistory>(`/ping-metrics/job/${jobId}`, { params }),

  getRouterHistory: (routerId: number, params?: { hours?: number; target?: string }) =>
    api.get(`/ping-metrics/router/${routerId}`, { params })
}

export const routerGroupApi = {
  list: (params?: { skip?: number; limit?: number }) =>
    api.get<RouterGroup[]>('/router-groups', { params }),

  get: (id: number) =>
    api.get<RouterGroup>(`/router-groups/${id}`),

  create: (data: Partial<RouterGroup>) =>
    api.post<RouterGroup>('/router-groups', data),

  update: (id: number, data: Partial<RouterGroup>) =>
    api.put<RouterGroup>(`/router-groups/${id}`, data),

  delete: (id: number) =>
    api.delete(`/router-groups/${id}`),

  addRouter: (groupId: number, routerId: number) =>
    api.post(`/router-groups/${groupId}/routers/${routerId}`),

  removeRouter: (groupId: number, routerId: number) =>
    api.delete(`/router-groups/${groupId}/routers/${routerId}`)
}

export const batchApi = {
  executeCommand: (routerIds: number[], command: string) =>
    api.post<BatchCommandResponse>('/batch/command', { router_ids: routerIds, command })
}

export const auditLogApi = {
  list: (params?: { skip?: number; limit?: number; action?: string; entity_type?: string; entity_id?: number; start_date?: string; end_date?: string }) =>
    api.get<AuditLog[]>('/audit-logs', { params }),

  getActions: () =>
    api.get<string[]>('/audit-logs/actions'),

  getEntityTypes: () =>
    api.get<string[]>('/audit-logs/entity-types')
}

export const exportImportApi = {
  exportRoutersJson: () =>
    api.get('/export/routers/json'),

  exportRoutersCsv: () =>
    api.get('/export/routers/csv', { responseType: 'blob' }),

  exportAllJson: () =>
    api.get('/export/all/json'),

  importRouters: (data: { routers: any[] }) =>
    api.post('/export/import/routers', data),

  importAll: (data: any) =>
    api.post('/export/import/all', data)
}

export const reportsApi = {
  getUptimeReport: (days: number = 30) =>
    api.get<UptimeReport[]>('/reports/uptime', { params: { days } }),

  getFirmwareVersions: () =>
    api.get<FirmwareInfo[]>('/reports/firmware'),

  getConfigChanges: (routerId?: number) =>
    api.get<ConfigChange[]>('/reports/config-changes', { params: { router_id: routerId } }),

  checkConfigChanges: (routerId: number) =>
    api.post(`/reports/check-config-changes/${routerId}`)
}

export const remediationApi = {
  list: (params?: { skip?: number; limit?: number }) =>
    api.get<RemediationScript[]>('/remediation', { params }),

  get: (id: number) =>
    api.get<RemediationScript>(`/remediation/${id}`),

  create: (data: Partial<RemediationScript>) =>
    api.post<RemediationScript>('/remediation', data),

  update: (id: number, data: Partial<RemediationScript>) =>
    api.put<RemediationScript>(`/remediation/${id}`, data),

  delete: (id: number) =>
    api.delete(`/remediation/${id}`),

  run: (scriptId: number, routerId: number) =>
    api.post(`/remediation/${scriptId}/run/${routerId}`)
}

export const notificationApi = {
  listChannels: (params?: { skip?: number; limit?: number }) =>
    api.get<NotificationChannel[]>('/notifications/channels', { params }),

  createChannel: (data: Partial<NotificationChannel>) =>
    api.post<NotificationChannel>('/notifications/channels', data),

  updateChannel: (id: number, data: Partial<NotificationChannel>) =>
    api.put<NotificationChannel>(`/notifications/channels/${id}`, data),

  deleteChannel: (id: number) =>
    api.delete(`/notifications/channels/${id}`),

  testChannel: (id: number) =>
    api.post(`/notifications/channels/${id}/test`),

  listWebhooks: (params?: { skip?: number; limit?: number }) =>
    api.get<Webhook[]>('/notifications/webhooks', { params }),

  createWebhook: (data: Partial<Webhook>) =>
    api.post<Webhook>('/notifications/webhooks', data),

  updateWebhook: (id: number, data: Partial<Webhook>) =>
    api.put<Webhook>(`/notifications/webhooks/${id}`, data),

  deleteWebhook: (id: number) =>
    api.delete(`/notifications/webhooks/${id}`),

  testWebhook: (id: number) =>
    api.post(`/notifications/webhooks/${id}/test`)
}

export const routerLogsApi = {
  getLogs: (routerId: number, params?: { skip?: number; limit?: number; level?: string; hours?: number }) =>
    api.get<RouterLog[]>(`/routers/${routerId}/logs`, { params }),

  getAllLogs: (params?: { skip?: number; limit?: number; level?: string; hours?: number }) =>
    api.get<RouterLog[]>('/routers/logs/all', { params }),

  createLog: (routerId: number, data: { level: string; source: string; message: string; details?: any }) =>
    api.post<RouterLog>(`/routers/${routerId}/logs`, data),

  clearLogs: (routerId: number) =>
    api.delete(`/routers/${routerId}/logs`)
}

export const authApi = {
  login: (username: string, password: string) =>
    api.post<{ token: string; user: any }>('/auth/login', { username, password }),
  
  register: (data: { username: string; email: string; password: string; role?: string; router_ids?: number[]; project_id?: number | null }) =>
    api.post('/auth/register', data),
  
  listUsers: () =>
    api.get<any[]>('/auth/users'),
  
  updateUser: (id: number, data: { username?: string; email?: string; password?: string; role?: string; router_ids?: number[]; is_active?: boolean; project_id?: number | null }) =>
    api.put(`/auth/users/${id}`, data),
  
  deleteUser: (id: number) =>
    api.delete(`/auth/users/${id}`)
}

export const projectApi = {
  list: () =>
    api.get<any[]>('/projects'),
  
  create: (data: { name: string; description?: string }) =>
    api.post('/projects', data),
  
  update: (id: number, data: { name: string; description?: string }) =>
    api.put(`/projects/${id}`, data),
  
  delete: (id: number) =>
    api.delete(`/projects/${id}`)
}

export default api
