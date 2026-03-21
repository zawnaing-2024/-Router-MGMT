import { defineStore } from 'pinia'
import { ref } from 'vue'
import { routerApi, backupApi, templateApi, jobApi, dashboardApi, metricsApi } from '@/api'
import type { Router, ConfigBackup, ConfigTemplate, ScheduledJob, DashboardStats, RouterMetrics, PerformanceMetric } from '@/types'

export const useRouterStore = defineStore('router', () => {
  const routers = ref<Router[]>([])
  const currentRouter = ref<Router | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)

  async function fetchRouters(params?: { search?: string; vendor?: string; status?: string }) {
    loading.value = true
    error.value = null
    try {
      const response = await routerApi.list(params)
      routers.value = response.data
    } catch (e: any) {
      error.value = e.message
    } finally {
      loading.value = false
    }
  }

  async function fetchRouter(id: number) {
    loading.value = true
    error.value = null
    try {
      const response = await routerApi.get(id)
      currentRouter.value = response.data
      return response.data
    } catch (e: any) {
      error.value = e.message
      return null
    } finally {
      loading.value = false
    }
  }

  async function createRouter(data: Partial<Router>) {
    loading.value = true
    error.value = null
    try {
      const response = await routerApi.create(data)
      routers.value.unshift(response.data)
      return response.data
    } catch (e: any) {
      error.value = e.message
      return null
    } finally {
      loading.value = false
    }
  }

  async function updateRouter(id: number, data: Partial<Router>) {
    loading.value = true
    error.value = null
    try {
      const response = await routerApi.update(id, data)
      const index = routers.value.findIndex(r => r.id === id)
      if (index !== -1) {
        routers.value[index] = response.data
      }
      if (currentRouter.value?.id === id) {
        currentRouter.value = response.data
      }
      return response.data
    } catch (e: any) {
      error.value = e.message
      return null
    } finally {
      loading.value = false
    }
  }

  async function deleteRouter(id: number) {
    loading.value = true
    error.value = null
    try {
      await routerApi.delete(id)
      routers.value = routers.value.filter(r => r.id !== id)
      return true
    } catch (e: any) {
      error.value = e.message
      return false
    } finally {
      loading.value = false
    }
  }

  async function backupRouter(id: number) {
    try {
      const response = await routerApi.backup(id)
      return response.data
    } catch (e: any) {
      throw new Error(e.response?.data?.detail || e.message)
    }
  }

  async function testConnection(id: number) {
    try {
      const response = await routerApi.testConnection(id)
      return response.data
    } catch (e: any) {
      throw new Error(e.response?.data?.detail || e.message)
    }
  }

  async function executeCommand(id: number, command: string) {
    try {
      const response = await routerApi.executeCommand(id, command)
      return response.data
    } catch (e: any) {
      throw new Error(e.response?.data?.detail || e.message)
    }
  }

  return {
    routers,
    currentRouter,
    loading,
    error,
    fetchRouters,
    fetchRouter,
    createRouter,
    updateRouter,
    deleteRouter,
    backupRouter,
    testConnection,
    executeCommand
  }
})

export const useBackupStore = defineStore('backup', () => {
  const backups = ref<ConfigBackup[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)

  async function fetchBackups(routerId?: number) {
    loading.value = true
    error.value = null
    try {
      const response = await backupApi.list({ router_id: routerId })
      backups.value = response.data
    } catch (e: any) {
      error.value = e.message
    } finally {
      loading.value = false
    }
  }

  async function getBackup(id: number) {
    try {
      const response = await backupApi.get(id)
      return response.data
    } catch (e: any) {
      throw new Error(e.message)
    }
  }

  async function restoreBackup(id: number) {
    try {
      await backupApi.restore(id)
      return true
    } catch (e: any) {
      throw new Error(e.response?.data?.detail || e.message)
    }
  }

  async function deleteBackup(id: number) {
    try {
      await backupApi.delete(id)
      backups.value = backups.value.filter(b => b.id !== id)
      return true
    } catch (e: any) {
      throw new Error(e.message)
    }
  }

  async function compareBackups(id1: number, id2: number) {
    try {
      const response = await backupApi.compare(id1, id2)
      return response.data
    } catch (e: any) {
      throw new Error(e.message)
    }
  }

  return {
    backups,
    loading,
    error,
    fetchBackups,
    getBackup,
    restoreBackup,
    deleteBackup,
    compareBackups
  }
})

export const useTemplateStore = defineStore('template', () => {
  const templates = ref<ConfigTemplate[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)

  async function fetchTemplates(vendor?: string) {
    loading.value = true
    error.value = null
    try {
      const response = await templateApi.list({ vendor })
      templates.value = response.data
    } catch (e: any) {
      error.value = e.message
    } finally {
      loading.value = false
    }
  }

  async function createTemplate(data: Partial<ConfigTemplate>) {
    loading.value = true
    error.value = null
    try {
      const response = await templateApi.create(data)
      templates.value.unshift(response.data)
      return response.data
    } catch (e: any) {
      error.value = e.response?.data?.detail || e.message
      return null
    } finally {
      loading.value = false
    }
  }

  async function updateTemplate(id: number, data: Partial<ConfigTemplate>) {
    loading.value = true
    error.value = null
    try {
      const response = await templateApi.update(id, data)
      const index = templates.value.findIndex(t => t.id === id)
      if (index !== -1) {
        templates.value[index] = response.data
      }
      return response.data
    } catch (e: any) {
      error.value = e.message
      return null
    } finally {
      loading.value = false
    }
  }

  async function deleteTemplate(id: number) {
    loading.value = true
    error.value = null
    try {
      await templateApi.delete(id)
      templates.value = templates.value.filter(t => t.id !== id)
      return true
    } catch (e: any) {
      error.value = e.message
      return false
    } finally {
      loading.value = false
    }
  }

  async function renderTemplate(id: number, variables: Record<string, any>) {
    try {
      const response = await templateApi.render(id, variables)
      return response.data.rendered
    } catch (e: any) {
      throw new Error(e.message)
    }
  }

  return {
    templates,
    loading,
    error,
    fetchTemplates,
    createTemplate,
    updateTemplate,
    deleteTemplate,
    renderTemplate
  }
})

export const useJobStore = defineStore('job', () => {
  const jobs = ref<ScheduledJob[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)

  async function fetchJobs(params?: { enabled?: boolean; job_type?: string }) {
    loading.value = true
    error.value = null
    try {
      const response = await jobApi.list(params)
      jobs.value = response.data
    } catch (e: any) {
      error.value = e.message
    } finally {
      loading.value = false
    }
  }

  async function createJob(data: Partial<ScheduledJob>) {
    loading.value = true
    error.value = null
    try {
      const response = await jobApi.create(data)
      jobs.value.unshift(response.data)
      return response.data
    } catch (e: any) {
      error.value = e.message
      return null
    } finally {
      loading.value = false
    }
  }

  async function updateJob(id: number, data: Partial<ScheduledJob>) {
    loading.value = true
    error.value = null
    try {
      const response = await jobApi.update(id, data)
      const index = jobs.value.findIndex(j => j.id === id)
      if (index !== -1) {
        jobs.value[index] = response.data
      }
      return response.data
    } catch (e: any) {
      error.value = e.message
      return null
    } finally {
      loading.value = false
    }
  }

  async function deleteJob(id: number) {
    loading.value = true
    error.value = null
    try {
      await jobApi.delete(id)
      jobs.value = jobs.value.filter(j => j.id !== id)
      return true
    } catch (e: any) {
      error.value = e.message
      return false
    } finally {
      loading.value = false
    }
  }

  async function runJobNow(id: number) {
    try {
      const response = await jobApi.runNow(id)
      return response.data
    } catch (e: any) {
      throw new Error(e.message)
    }
  }

  return {
    jobs,
    loading,
    error,
    fetchJobs,
    createJob,
    updateJob,
    deleteJob,
    runJobNow
  }
})

export const useDashboardStore = defineStore('dashboard', () => {
  const stats = ref<DashboardStats | null>(null)
  const loading = ref(false)

  async function fetchStats() {
    loading.value = true
    try {
      const response = await dashboardApi.getStats()
      stats.value = response.data
    } finally {
      loading.value = false
    }
  }

  return {
    stats,
    loading,
    fetchStats
  }
})

export const useMetricsStore = defineStore('metrics', () => {
  const allMetrics = ref<RouterMetrics[]>([])
  const currentRouterMetrics = ref<RouterMetrics | null>(null)
  const history = ref<PerformanceMetric[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)

  async function fetchAllLatest() {
    loading.value = true
    error.value = null
    try {
      const response = await metricsApi.getAllLatest()
      allMetrics.value = response.data
    } catch (e: any) {
      error.value = e.message
    } finally {
      loading.value = false
    }
  }

  async function fetchRouterMetrics(routerId: number) {
    loading.value = true
    error.value = null
    try {
      const response = await metricsApi.getLatest(routerId)
      currentRouterMetrics.value = response.data
      return response.data
    } catch (e: any) {
      error.value = e.message
      return null
    } finally {
      loading.value = false
    }
  }

  async function fetchHistory(routerId: number, hours: number = 24) {
    loading.value = true
    error.value = null
    try {
      const response = await metricsApi.getHistory(routerId, { hours })
      history.value = response.data
    } catch (e: any) {
      error.value = e.message
    } finally {
      loading.value = false
    }
  }

  async function collectMetrics(routerId: number) {
    loading.value = true
    error.value = null
    try {
      const response = await metricsApi.collect(routerId)
      if (response.data.success) {
        await fetchRouterMetrics(routerId)
      }
      return response.data
    } catch (e: any) {
      error.value = e.message
      return null
    } finally {
      loading.value = false
    }
  }

  async function collectAllMetrics() {
    loading.value = true
    error.value = null
    try {
      const response = await metricsApi.collectAll()
      await fetchAllLatest()
      return response.data
    } catch (e: any) {
      error.value = e.message
      return null
    } finally {
      loading.value = false
    }
  }

  return {
    allMetrics,
    currentRouterMetrics,
    history,
    loading,
    error,
    fetchAllLatest,
    fetchRouterMetrics,
    fetchHistory,
    collectMetrics,
    collectAllMetrics
  }
})
