<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useJobStore, useRouterStore } from '@/stores'
import { Plus, Edit2, Trash2, Play, Power, PowerOff, Search, Activity, Eye, BarChart3, Clock } from 'lucide-vue-next'
import PageHeader from '@/components/PageHeader.vue'
import Modal from '@/components/Modal.vue'
import AppButton from '@/components/AppButton.vue'
import { pingMetricsApi } from '@/api'
import type { ScheduledJob, JobType, PingMetric } from '@/types'

const jobStore = useJobStore()
const routerStore = useRouterStore()

const searchQuery = ref('')
const showAddModal = ref(false)
const showEditModal = ref(false)
const showResultModal = ref(false)
const editingJob = ref<ScheduledJob | null>(null)
const selectedJobResult = ref('')
const loading = ref(false)
const runningJobs = ref<Set<number>>(new Set())

const pingMetrics = ref<Record<number, PingMetric[]>>({})
const selectedPingJob = ref<number | null>(null)
const pingHistoryHours = ref(24)

const pingJobs = computed(() => jobStore.jobs.filter(j => j.job_type === 'ping'))

async function loadPingMetrics(jobId: number) {
  try {
    const response = await pingMetricsApi.getJobHistory(jobId, { hours: pingHistoryHours.value })
    pingMetrics.value[jobId] = response.data.data
    selectedPingJob.value = jobId
  } catch (e) {
    console.error('Failed to load ping metrics:', e)
  }
}

async function loadAllPingMetrics() {
  for (const job of pingJobs.value) {
    await loadPingMetrics(job.id)
  }
}

function formatTime(dateStr: string) {
  return new Date(dateStr).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}

function getLatencyPath(data: PingMetric[]) {
  if (data.length < 2) return ''
  const maxLatency = Math.max(...data.map(d => d.latency_max_ms || d.latency_avg_ms || 0), 100)
  const width = 400
  const height = 100
  const padding = 10
  
  const points = data.map((d, i) => {
    const x = padding + (i / (data.length - 1)) * (width - 2 * padding)
    const y = height - padding - ((d.latency_avg_ms || 0) / maxLatency) * (height - 2 * padding)
    return `${x},${y}`
  })
  
  return `M ${points.join(' L ')}`
}

function getPacketLossPath(data: PingMetric[]) {
  if (data.length < 2) return ''
  const width = 400
  const height = 50
  const padding = 5
  
  const points = data.map((d, i) => {
    const x = padding + (i / (data.length - 1)) * (width - 2 * padding)
    const y = height - padding - (d.packet_loss_percent / 100) * (height - 2 * padding)
    return `${x},${y}`
  })
  
  return `M ${points.join(' L ')}`
}

function getLatencyArea(data: PingMetric[]) {
  if (data.length < 2) return ''
  const maxLatency = Math.max(...data.map(d => d.latency_max_ms || d.latency_avg_ms || 0), 100)
  const width = 400
  const height = 100
  const padding = 10
  
  const points = data.map((d, i) => {
    const x = padding + (i / (data.length - 1)) * (width - 2 * padding)
    const y = height - padding - ((d.latency_avg_ms || 0) / maxLatency) * (height - 2 * padding)
    return `${x},${y}`
  })
  
  const firstX = padding
  const lastX = padding + ((data.length - 1) / (data.length - 1)) * (width - 2 * padding)
  
  return `M ${firstX},${height - padding} L ${points.join(' L ')} L ${lastX},${height - padding} Z`
}

function getAverageLatency(data: PingMetric[]) {
  const values = data.filter(d => d.latency_avg_ms).map(d => d.latency_avg_ms!)
  if (values.length === 0) return 0
  return Math.round(values.reduce((a, b) => a + b, 0) / values.length)
}

function getAveragePacketLoss(data: PingMetric[]) {
  const values = data.filter(d => d.packet_loss_percent !== undefined).map(d => d.packet_loss_percent)
  if (values.length === 0) return 0
  return Math.round(values.reduce((a, b) => a + b, 0) / values.length)
}

const form = ref({
  name: '',
  job_type: 'backup' as JobType,
  router_id: null as number | null,
  command: '',
  schedule: '',
  ping_target: '',
  ping_source: '',
  ping_count: 4,
  enabled: true
})

const jobTypes = [
  { value: 'backup', label: 'Configuration Backup' },
  { value: 'command', label: 'Run Command' },
  { value: 'template', label: 'Apply Template' },
  { value: 'ping', label: 'Ping Monitor' }
]

const filteredJobs = computed(() => {
  if (!searchQuery.value) return jobStore.jobs
  const query = searchQuery.value.toLowerCase()
  return jobStore.jobs.filter(job => 
    job.name.toLowerCase().includes(query) ||
    job.job_type.toLowerCase().includes(query) ||
    getRouterName(job.router_id).toLowerCase().includes(query)
  )
})

async function loadJobs() {
  await jobStore.fetchJobs()
  await routerStore.fetchRouters()
}

function getRouterName(routerId: number | undefined | null) {
  if (!routerId) return '-'
  const router = routerStore.routers.find(r => r.id === routerId)
  return router?.hostname || `Router #${routerId}`
}

function formatDate(dateStr: string | undefined | null) {
  if (!dateStr) return 'Never'
  return new Date(dateStr).toLocaleString()
}

async function handleAddJob() {
  loading.value = true
  try {
    const jobData: any = { ...form.value }
    if (form.value.job_type !== 'ping') {
      delete jobData.ping_target
      delete jobData.ping_source
      delete jobData.ping_count
    }
    if (form.value.job_type !== 'command') {
      delete jobData.command
    }
    const result = await jobStore.createJob(jobData)
    if (result) {
      showAddModal.value = false
      resetForm()
    }
  } finally {
    loading.value = false
  }
}

async function handleEditJob() {
  if (!editingJob.value) return
  loading.value = true
  try {
    const jobData: any = { ...form.value }
    if (form.value.job_type !== 'ping') {
      delete jobData.ping_target
      delete jobData.ping_source
      delete jobData.ping_count
    }
    if (form.value.job_type !== 'command') {
      delete jobData.command
    }
    const result = await jobStore.updateJob(editingJob.value.id, jobData)
    if (result) {
      showEditModal.value = false
      editingJob.value = null
      resetForm()
    }
  } finally {
    loading.value = false
  }
}

function openEdit(job: ScheduledJob) {
  editingJob.value = job
  form.value = {
    name: job.name,
    job_type: job.job_type,
    router_id: job.router_id || null,
    command: job.command || '',
    schedule: job.schedule,
    ping_target: (job as any).ping_target || '',
    ping_source: (job as any).ping_source || '',
    ping_count: (job as any).ping_count || 4,
    enabled: job.enabled
  }
  showEditModal.value = true
}

function showResult(output: string | undefined | null) {
  selectedJobResult.value = output || 'No output'
  showResultModal.value = true
}

async function handleDelete(job: ScheduledJob) {
  if (confirm(`Delete job ${job.name}?`)) {
    await jobStore.deleteJob(job.id)
  }
}

async function toggleEnabled(job: ScheduledJob) {
  await jobStore.updateJob(job.id, { enabled: !job.enabled })
}

async function runNow(job: ScheduledJob) {
  runningJobs.value.add(job.id)
  try {
    await jobStore.runJobNow(job.id)
    await loadJobs()
  } catch (e: any) {
    alert('Job failed: ' + e.message)
  } finally {
    runningJobs.value.delete(job.id)
  }
}

function resetForm() {
  form.value = {
    name: '',
    job_type: 'backup',
    router_id: null,
    command: '',
    schedule: '0 2 * * *',
    ping_target: '',
    ping_source: '',
    ping_count: 4,
    enabled: true
  }
}

onMounted(async () => {
  await loadJobs()
  await loadAllPingMetrics()
})
</script>

<template>
  <div>
    <PageHeader title="Scheduled Jobs" subtitle="Automate router tasks with scheduled jobs and ping monitoring">
      <template #actions>
        <div class="flex items-center gap-3">
          <div class="relative">
            <Search class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
            <input
              v-model="searchQuery"
              type="text"
              placeholder="Search jobs..."
              class="pl-10 pr-4 py-2 bg-slate-700 border border-slate-600 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 w-64"
            />
          </div>
          <AppButton @click="showAddModal = true">
            <Plus class="w-4 h-4" />
            New Job
          </AppButton>
        </div>
      </template>
    </PageHeader>

    <div class="p-6">
      <div class="bg-slate-800 rounded-xl border border-slate-700 overflow-hidden">
        <table class="w-full">
          <thead>
            <tr class="text-left text-sm text-slate-400 border-b border-slate-700 bg-slate-700/30">
              <th class="px-4 py-3 font-medium">Name</th>
              <th class="px-4 py-3 font-medium">Type</th>
              <th class="px-4 py-3 font-medium">Router</th>
              <th class="px-4 py-3 font-medium">Target</th>
              <th class="px-4 py-3 font-medium">Schedule</th>
              <th class="px-4 py-3 font-medium">Last Latency</th>
              <th class="px-4 py-3 font-medium">Last Status</th>
              <th class="px-4 py-3 font-medium">Last Run</th>
              <th class="px-4 py-3 font-medium">Actions</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="job in filteredJobs"
              :key="job.id"
              class="border-b border-slate-700/50 hover:bg-slate-700/30"
            >
              <td class="px-4 py-3 font-medium">
                <div class="flex items-center gap-2">
                  <span :class="job.enabled ? 'text-slate-200' : 'text-slate-500'">{{ job.name }}</span>
                </div>
              </td>
              <td class="px-4 py-3">
                <span
                  :class="[
                    'px-2 py-0.5 rounded-full text-xs font-medium',
                    job.job_type === 'backup' && 'bg-blue-500/20 text-blue-400',
                    job.job_type === 'command' && 'bg-purple-500/20 text-purple-400',
                    job.job_type === 'template' && 'bg-amber-500/20 text-amber-400',
                    job.job_type === 'ping' && 'bg-green-500/20 text-green-400'
                  ]"
                >
                  {{ job.job_type }}
                </span>
              </td>
              <td class="px-4 py-3 text-sm">{{ getRouterName(job.router_id) }}</td>
              <td class="px-4 py-3">
                <span v-if="job.job_type === 'ping' && job.ping_target" class="font-mono text-sm text-cyan-400">
                  {{ job.ping_target }}
                </span>
                <span v-else-if="job.job_type === 'command'" class="text-slate-500 text-xs truncate max-w-24" :title="job.command">
                  {{ job.command?.substring(0, 20) || '-' }}...
                </span>
                <span v-else class="text-slate-500">-</span>
              </td>
              <td class="px-4 py-3 font-mono text-sm">{{ job.schedule }}</td>
              <td class="px-4 py-3">
                <span
                  v-if="job.job_type === 'ping' && pingMetrics[job.id]?.[0]"
                  class="flex items-center gap-1.5"
                >
                  <span class="w-2 h-2 rounded-full" :class="pingMetrics[job.id][0].packet_loss_percent > 0 ? 'bg-red-400' : 'bg-green-400'" />
                  <span class="font-mono text-sm" :class="pingMetrics[job.id][0].packet_loss_percent > 0 ? 'text-red-400' : 'text-green-400'">
                    {{ pingMetrics[job.id][0].latency_avg_ms ?? '-' }}ms
                  </span>
                  <span v-if="pingMetrics[job.id][0].packet_loss_percent > 0" class="text-xs text-red-400">
                    ({{ pingMetrics[job.id][0].packet_loss_percent }}% loss)
                  </span>
                </span>
                <span v-else class="text-slate-500">-</span>
              </td>
              <td class="px-4 py-3">
                <span
                  v-if="job.last_status"
                  :class="[
                    'px-2 py-0.5 rounded-full text-xs font-medium cursor-pointer hover:opacity-80',
                    job.last_status === 'success' && 'bg-green-500/20 text-green-400',
                    job.last_status === 'failed' && 'bg-red-500/20 text-red-400',
                    job.last_status === 'running' && 'bg-blue-500/20 text-blue-400',
                    job.last_status === 'pending' && 'bg-slate-500/20 text-slate-400'
                  ]"
                  @click="showResult(job.last_output)"
                  :title="job.last_output ? 'Click to view output' : ''"
                >
                  {{ job.last_status }}
                </span>
                <span v-else class="text-slate-500">-</span>
              </td>
              <td class="px-4 py-3 text-sm text-slate-400">{{ formatDate(job.last_run) }}</td>
              <td class="px-4 py-3">
                <div class="flex items-center gap-1">
                  <button
                    @click="toggleEnabled(job)"
                    class="p-1.5 hover:bg-slate-700 rounded-lg transition-colors"
                    :title="job.enabled ? 'Disable' : 'Enable'"
                  >
                    <PowerOff v-if="job.enabled" class="w-4 h-4 text-green-400" />
                    <Power v-else class="w-4 h-4 text-slate-400" />
                  </button>
                  <button
                    @click="runNow(job)"
                    :disabled="runningJobs.has(job.id)"
                    class="p-1.5 hover:bg-green-500/20 text-green-400 rounded-lg transition-colors disabled:opacity-50"
                    title="Run Now"
                  >
                    <Play class="w-4 h-4" />
                  </button>
                  <button
                    v-if="job.last_output"
                    @click="showResult(job.last_output)"
                    class="p-1.5 hover:bg-slate-700 rounded-lg transition-colors"
                    title="View Result"
                  >
                    <Eye class="w-4 h-4" />
                  </button>
                  <button
                    v-if="job.job_type === 'ping'"
                    @click="loadPingMetrics(job.id)"
                    class="p-1.5 hover:bg-green-500/20 text-green-400 rounded-lg transition-colors"
                    title="View Ping History"
                  >
                    <BarChart3 class="w-4 h-4" />
                  </button>
                  <button
                    @click="openEdit(job)"
                    class="p-1.5 hover:bg-slate-700 rounded-lg transition-colors"
                    title="Edit"
                  >
                    <Edit2 class="w-4 h-4" />
                  </button>
                  <button
                    @click="handleDelete(job)"
                    class="p-1.5 hover:bg-red-500/20 text-red-400 rounded-lg transition-colors"
                    title="Delete"
                  >
                    <Trash2 class="w-4 h-4" />
                  </button>
                </div>
              </td>
            </tr>
            <tr v-if="filteredJobs.length === 0">
              <td colspan="9" class="px-4 py-12 text-center text-slate-400">
                No scheduled jobs found.
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <div v-if="pingJobs.length > 0" class="px-6 pb-6">
      <div class="bg-slate-800 rounded-xl border border-slate-700 overflow-hidden">
        <div class="p-4 border-b border-slate-700 flex items-center justify-between">
          <div class="flex items-center gap-2">
            <Activity class="w-5 h-5 text-green-400" />
            <h3 class="font-semibold">Ping Monitoring</h3>
          </div>
          <div class="flex items-center gap-2">
            <select
              v-model="pingHistoryHours"
              class="px-3 py-1.5 bg-slate-700 border border-slate-600 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-green-500"
              @change="selectedPingJob && loadPingMetrics(selectedPingJob)"
            >
              <option :value="6">Last 6 hours</option>
              <option :value="12">Last 12 hours</option>
              <option :value="24">Last 24 hours</option>
              <option :value="48">Last 48 hours</option>
              <option :value="168">Last 7 days</option>
            </select>
          </div>
        </div>
        <div class="p-4">
          <div v-if="selectedPingJob && pingMetrics[selectedPingJob]?.length > 0" class="space-y-6">
            <div class="grid grid-cols-1 md:grid-cols-4 gap-4">
              <div class="bg-slate-700/50 rounded-lg p-4">
                <div class="flex items-center gap-2 text-slate-400 text-sm mb-1">
                  <Activity class="w-4 h-4" />
                  Target
                </div>
                <p class="text-lg font-mono">{{ pingMetrics[selectedPingJob]?.[0]?.target }}</p>
              </div>
              <div class="bg-slate-700/50 rounded-lg p-4">
                <div class="flex items-center gap-2 text-slate-400 text-sm mb-1">
                  <Clock class="w-4 h-4" />
                  Avg Latency
                </div>
                <p class="text-lg font-mono text-green-400">{{ getAverageLatency(pingMetrics[selectedPingJob] || []) }} ms</p>
              </div>
              <div class="bg-slate-700/50 rounded-lg p-4">
                <div class="flex items-center gap-2 text-slate-400 text-sm mb-1">
                  <BarChart3 class="w-4 h-4" />
                  Avg Packet Loss
                </div>
                <p :class="['text-lg font-mono', getAveragePacketLoss(pingMetrics[selectedPingJob] || []) > 0 ? 'text-red-400' : 'text-green-400']">
                  {{ getAveragePacketLoss(pingMetrics[selectedPingJob] || []) }}%
                </p>
              </div>
              <div class="bg-slate-700/50 rounded-lg p-4">
                <div class="flex items-center gap-2 text-slate-400 text-sm mb-1">
                  <Activity class="w-4 h-4" />
                  Data Points
                </div>
                <p class="text-lg font-mono">{{ pingMetrics[selectedPingJob]?.length || 0 }}</p>
              </div>
            </div>

            <div class="bg-slate-900/50 rounded-lg p-4">
              <div class="flex items-center justify-between mb-4">
                <span class="text-sm text-slate-400">Latency (ms)</span>
                <span class="text-xs text-slate-500">
                  {{ pingMetrics[selectedPingJob]?.[0]?.target }}
                </span>
              </div>
              <svg viewBox="0 0 400 100" class="w-full h-24">
                <defs>
                  <linearGradient id="latencyGradient" x1="0%" y1="0%" x2="0%" y2="100%">
                    <stop offset="0%" style="stop-color:#22c55e;stop-opacity:0.3" />
                    <stop offset="100%" style="stop-color:#22c55e;stop-opacity:0" />
                  </linearGradient>
                </defs>
                <path
                  v-if="getLatencyArea(pingMetrics[selectedPingJob] || [])"
                  :d="getLatencyArea(pingMetrics[selectedPingJob] || [])"
                  fill="url(#latencyGradient)"
                />
                <path
                  :d="getLatencyPath(pingMetrics[selectedPingJob] || [])"
                  fill="none"
                  stroke="#22c55e"
                  stroke-width="2"
                  stroke-linecap="round"
                  stroke-linejoin="round"
                />
              </svg>
            </div>

            <div class="bg-slate-900/50 rounded-lg p-4">
              <div class="flex items-center justify-between mb-4">
                <span class="text-sm text-slate-400">Packet Loss (%)</span>
                <span class="text-xs text-slate-500">
                  {{ pingMetrics[selectedPingJob]?.[0]?.target }}
                </span>
              </div>
              <svg viewBox="0 0 400 50" class="w-full h-12">
                <path
                  :d="getPacketLossPath(pingMetrics[selectedPingJob] || [])"
                  fill="none"
                  stroke="#f97316"
                  stroke-width="2"
                  stroke-linecap="round"
                  stroke-linejoin="round"
                />
              </svg>
            </div>

            <div class="overflow-x-auto">
              <table class="w-full text-sm">
                <thead>
                  <tr class="text-left text-slate-400 border-b border-slate-700">
                    <th class="pb-2 font-medium">Time</th>
                    <th class="pb-2 font-medium">Avg (ms)</th>
                    <th class="pb-2 font-medium">Min (ms)</th>
                    <th class="pb-2 font-medium">Max (ms)</th>
                    <th class="pb-2 font-medium">Loss</th>
                    <th class="pb-2 font-medium">Sent</th>
                    <th class="pb-2 font-medium">Received</th>
                  </tr>
                </thead>
                <tbody>
                  <tr
                    v-for="metric in [...(pingMetrics[selectedPingJob] || [])].reverse().slice(0, 10)"
                    :key="metric.id"
                    class="border-b border-slate-700/50"
                  >
                    <td class="py-2 font-mono text-slate-400">{{ formatTime(metric.collected_at) }}</td>
                    <td class="py-2 font-mono text-green-400">{{ metric.latency_avg_ms ?? '-' }}</td>
                    <td class="py-2 font-mono">{{ metric.latency_min_ms ?? '-' }}</td>
                    <td class="py-2 font-mono">{{ metric.latency_max_ms ?? '-' }}</td>
                    <td class="py-2">
                      <span :class="metric.packet_loss_percent > 0 ? 'text-red-400' : 'text-green-400'">
                        {{ metric.packet_loss_percent }}%
                      </span>
                    </td>
                    <td class="py-2 font-mono">{{ metric.packets_sent }}</td>
                    <td class="py-2 font-mono">{{ metric.packets_received }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>

          <div v-else class="text-center py-12 text-slate-400">
            <Activity class="w-12 h-12 mx-auto mb-2 opacity-50" />
            <p v-if="selectedPingJob">No ping data available for this job.</p>
            <p v-else>Click the chart icon on a ping job to view its history.</p>
          </div>
        </div>
      </div>
    </div>

    <Modal :open="showAddModal" title="New Job" size="lg" @close="showAddModal = false; resetForm()">
      <form @submit.prevent="handleAddJob" class="space-y-4">
        <div class="grid grid-cols-2 gap-4">
          <div>
            <label class="block text-sm font-medium mb-1">Job Name *</label>
            <input
              v-model="form.name"
              type="text"
              required
              placeholder="e.g., Daily Backup, Ping Google DNS"
              class="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          <div>
            <label class="block text-sm font-medium mb-1">Job Type *</label>
            <select
              v-model="form.job_type"
              required
              class="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option v-for="t in jobTypes" :key="t.value" :value="t.value">{{ t.label }}</option>
            </select>
          </div>
        </div>

        <div class="grid grid-cols-2 gap-4">
          <div>
            <label class="block text-sm font-medium mb-1">Router *</label>
            <select
              v-model="form.router_id"
              required
              class="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option :value="null">Select router...</option>
              <option v-for="r in routerStore.routers" :key="r.id" :value="r.id">
                {{ r.hostname }} ({{ r.ip_address }})
              </option>
            </select>
          </div>
          <div>
            <label class="block text-sm font-medium mb-1">Schedule (Cron) *</label>
            <input
              v-model="form.schedule"
              type="text"
              required
              placeholder="0 2 * * *"
              class="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 font-mono"
            />
          </div>
        </div>

        <div v-if="form.job_type === 'ping'" class="space-y-4 p-4 bg-slate-700/50 rounded-lg border border-slate-600">
          <div class="flex items-center gap-2 mb-2">
            <Activity class="w-5 h-5 text-green-400" />
            <span class="font-medium text-green-400">Ping Monitor Settings</span>
          </div>
          <div class="grid grid-cols-2 gap-4">
            <div>
              <label class="block text-sm font-medium mb-1">Destination IP *</label>
              <input
                v-model="form.ping_target"
                type="text"
                required
                placeholder="e.g., 8.8.8.8 or google.com"
                class="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500"
              />
            </div>
            <div>
              <label class="block text-sm font-medium mb-1">Count</label>
              <input
                v-model.number="form.ping_count"
                type="number"
                min="1"
                max="100"
                class="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500"
              />
            </div>
          </div>
          <div>
            <label class="block text-sm font-medium mb-1">Source Interface/IP (optional)</label>
            <input
              v-model="form.ping_source"
              type="text"
              placeholder="e.g., 192.168.1.1 or ether1"
              class="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500"
            />
            <p class="text-xs text-slate-500 mt-1">Specify source IP address or interface name</p>
          </div>
        </div>

        <div v-if="form.job_type === 'command'">
          <label class="block text-sm font-medium mb-1">Command</label>
          <textarea
            v-model="form.command"
            rows="3"
            placeholder="e.g., show interfaces"
            class="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 font-mono text-sm resize-none"
          />
        </div>

        <div class="bg-slate-700/30 p-3 rounded-lg">
          <p class="text-xs text-slate-400">
            <strong>Cron Format:</strong> minute hour day month weekday<br />
            Examples: <code class="text-cyan-400">0 2 * * *</code> = Daily at 2 AM |
            <code class="text-cyan-400">*/5 * * * *</code> = Every 5 minutes |
            <code class="text-cyan-400">0 */6 * * *</code> = Every 6 hours
          </p>
        </div>
      </form>
      <template #footer>
        <AppButton variant="ghost" @click="showAddModal = false">Cancel</AppButton>
        <AppButton :loading="loading" @click="handleAddJob">Create Job</AppButton>
      </template>
    </Modal>

    <Modal :open="showEditModal" title="Edit Job" size="lg" @close="showEditModal = false; editingJob = null; resetForm()">
      <form @submit.prevent="handleEditJob" class="space-y-4">
        <div class="grid grid-cols-2 gap-4">
          <div>
            <label class="block text-sm font-medium mb-1">Job Name *</label>
            <input
              v-model="form.name"
              type="text"
              required
              class="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          <div>
            <label class="block text-sm font-medium mb-1">Job Type *</label>
            <select
              v-model="form.job_type"
              required
              class="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option v-for="t in jobTypes" :key="t.value" :value="t.value">{{ t.label }}</option>
            </select>
          </div>
        </div>

        <div class="grid grid-cols-2 gap-4">
          <div>
            <label class="block text-sm font-medium mb-1">Router *</label>
            <select
              v-model="form.router_id"
              required
              class="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option :value="null">Select router...</option>
              <option v-for="r in routerStore.routers" :key="r.id" :value="r.id">
                {{ r.hostname }} ({{ r.ip_address }})
              </option>
            </select>
          </div>
          <div>
            <label class="block text-sm font-medium mb-1">Schedule (Cron) *</label>
            <input
              v-model="form.schedule"
              type="text"
              required
              class="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 font-mono"
            />
          </div>
        </div>

        <div v-if="form.job_type === 'ping'" class="space-y-4 p-4 bg-slate-700/50 rounded-lg border border-slate-600">
          <div class="flex items-center gap-2 mb-2">
            <Activity class="w-5 h-5 text-green-400" />
            <span class="font-medium text-green-400">Ping Monitor Settings</span>
          </div>
          <div class="grid grid-cols-2 gap-4">
            <div>
              <label class="block text-sm font-medium mb-1">Destination IP *</label>
              <input
                v-model="form.ping_target"
                type="text"
                required
                class="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500"
              />
            </div>
            <div>
              <label class="block text-sm font-medium mb-1">Count</label>
              <input
                v-model.number="form.ping_count"
                type="number"
                min="1"
                max="100"
                class="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500"
              />
            </div>
          </div>
          <div>
            <label class="block text-sm font-medium mb-1">Source Interface/IP (optional)</label>
            <input
              v-model="form.ping_source"
              type="text"
              placeholder="e.g., 192.168.1.1 or ether1"
              class="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500"
            />
          </div>
        </div>

        <div v-if="form.job_type === 'command'">
          <label class="block text-sm font-medium mb-1">Command</label>
          <textarea
            v-model="form.command"
            rows="3"
            class="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 font-mono text-sm resize-none"
          />
        </div>
      </form>
      <template #footer>
        <AppButton variant="ghost" @click="showEditModal = false">Cancel</AppButton>
        <AppButton :loading="loading" @click="handleEditJob">Save Changes</AppButton>
      </template>
    </Modal>

    <Modal :open="showResultModal" title="Job Result" size="lg" @close="showResultModal = false">
      <pre class="p-4 bg-slate-900 rounded-lg text-xs font-mono whitespace-pre-wrap max-h-96 overflow-auto">{{ selectedJobResult }}</pre>
      <template #footer>
        <AppButton variant="ghost" @click="showResultModal = false">Close</AppButton>
      </template>
    </Modal>
  </div>
</template>
