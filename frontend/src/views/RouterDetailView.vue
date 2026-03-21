<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useRouterStore, useMetricsStore } from '@/stores'
import { ArrowLeft, Server, MapPin, Clock, Cpu, HardDrive, RefreshCw, Terminal, Database, AlertCircle } from 'lucide-vue-next'
import PageHeader from '@/components/PageHeader.vue'
import AppButton from '@/components/AppButton.vue'

const route = useRoute()
const router = useRouter()
const routerStore = useRouterStore()
const metricsStore = useMetricsStore()

const routerId = Number(route.params.id)
const timeRange = ref<'1h' | '6h' | '24h' | '7d'>('24h')

const timeRangeHours = computed(() => {
  const map = { '1h': 1, '6h': 6, '24h': 24, '7d': 168 }
  return map[timeRange.value]
})

const collecting = ref(false)

async function refreshMetrics() {
  collecting.value = true
  await metricsStore.collectMetrics(routerId)
  await metricsStore.fetchHistory(routerId, timeRangeHours.value)
  collecting.value = false
}

async function changeTimeRange(range: '1h' | '6h' | '24h' | '7d') {
  timeRange.value = range
  await metricsStore.fetchHistory(routerId, timeRangeHours.value)
}

const chartData = computed(() => {
  const history = [...metricsStore.history].reverse()
  if (history.length === 0) return { cpu: [], memory: [], labels: [] }
  
  const maxPoints = 50
  const step = Math.max(1, Math.floor(history.length / maxPoints))
  const sampled = history.filter((_, i) => i % step === 0)
  
  return {
    cpu: sampled.map(h => h.cpu_percent ?? 0),
    memory: sampled.map(h => h.memory_percent ?? 0),
    labels: sampled.map(h => {
      const d = new Date(h.collected_at)
      return timeRange.value === '1h' ? d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) 
        : d.toLocaleString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
    })
  }
})

function getChartPath(values: number[], width: number, height: number): string {
  if (values.length === 0) return ''
  
  const max = 100
  const points = values.map((v, i) => {
    const x = (i / (values.length - 1 || 1)) * width
    const y = height - (v / max) * height
    return `${x},${y}`
  })
  
  return `M${points.join(' L')}`
}

function getChartAreaPath(values: number[], width: number, height: number): string {
  if (values.length === 0) return ''
  
  const max = 100
  const points = values.map((v, i) => {
    const x = (i / (values.length - 1 || 1)) * width
    const y = height - (v / max) * height
    return `${x},${y}`
  })
  
  return `M0,${height} L${points.join(' L')} L${width},${height} Z`
}

function getUsageColor(percent?: number) {
  if (!percent) return 'text-slate-400'
  if (percent >= 90) return 'text-red-400'
  if (percent >= 70) return 'text-amber-400'
  return 'text-green-400'
}

function getUsageBarColor(percent?: number) {
  if (!percent) return 'bg-slate-600'
  if (percent >= 90) return 'bg-red-500'
  if (percent >= 70) return 'bg-amber-500'
  return 'bg-green-500'
}

function formatUptime(seconds?: number): string {
  if (!seconds) return 'N/A'
  const days = Math.floor(seconds / 86400)
  const hours = Math.floor((seconds % 86400) / 3600)
  const mins = Math.floor((seconds % 3600) / 60)
  if (days > 0) return `${days}d ${hours}h`
  if (hours > 0) return `${hours}h ${mins}m`
  return `${mins}m`
}

let refreshInterval: number | null = null

onMounted(async () => {
  await routerStore.fetchRouter(routerId)
  await metricsStore.fetchRouterMetrics(routerId)
  await metricsStore.fetchHistory(routerId, timeRangeHours.value)
  
  refreshInterval = window.setInterval(async () => {
    await metricsStore.fetchRouterMetrics(routerId)
  }, 30000)
})

onUnmounted(() => {
  if (refreshInterval) {
    clearInterval(refreshInterval)
  }
})
</script>

<template>
  <div class="h-full flex flex-col">
    <PageHeader :title="routerStore.currentRouter?.hostname || 'Router'" :subtitle="`Router Details - ${routerId}`">
      <template #actions>
        <AppButton @click="router.push('/terminal/' + routerId)" variant="ghost" size="sm">
          <Terminal class="w-4 h-4" />
          SSH Terminal
        </AppButton>
        <AppButton @click="refreshMetrics" variant="ghost" size="sm" :loading="collecting">
          <RefreshCw class="w-4 h-4" />
          Refresh
        </AppButton>
        <AppButton @click="router.push('/routers')" variant="ghost" size="sm">
          <ArrowLeft class="w-4 h-4" />
          Back
        </AppButton>
      </template>
    </PageHeader>

    <div class="flex-1 p-6 space-y-6 overflow-auto">
      <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div class="bg-slate-800 rounded-xl border border-slate-700 p-6">
          <div class="flex items-center gap-3 mb-4">
            <div class="p-2 bg-blue-500/20 rounded-lg">
              <Server class="w-5 h-5 text-blue-400" />
            </div>
            <div>
              <p class="text-sm text-slate-400">Status</p>
              <p :class="['font-semibold capitalize', 
                routerStore.currentRouter?.status === 'online' ? 'text-green-400' : 
                routerStore.currentRouter?.status === 'offline' ? 'text-red-400' : 'text-slate-400']">
                {{ routerStore.currentRouter?.status || 'unknown' }}
              </p>
            </div>
          </div>
          <div class="space-y-2 text-sm">
            <div class="flex justify-between">
              <span class="text-slate-400">IP Address</span>
              <span class="font-mono">{{ routerStore.currentRouter?.ip_address }}:{{ routerStore.currentRouter?.port }}</span>
            </div>
            <div class="flex justify-between">
              <span class="text-slate-400">Vendor</span>
              <span class="capitalize">{{ routerStore.currentRouter?.vendor?.replace('_', ' ') }}</span>
            </div>
            <div class="flex justify-between">
              <span class="text-slate-400">Location</span>
              <span>{{ routerStore.currentRouter?.location || 'N/A' }}</span>
            </div>
            <div class="flex justify-between">
              <span class="text-slate-400">Last Seen</span>
              <span>{{ routerStore.currentRouter?.last_seen ? new Date(routerStore.currentRouter.last_seen).toLocaleString() : 'Never' }}</span>
            </div>
          </div>
        </div>

        <div class="bg-slate-800 rounded-xl border border-slate-700 p-6">
          <div class="flex items-center gap-3 mb-4">
            <div class="p-2 bg-green-500/20 rounded-lg">
              <Cpu class="w-5 h-5 text-green-400" />
            </div>
            <div>
              <p class="text-sm text-slate-400">CPU Usage</p>
              <p :class="['text-3xl font-bold', getUsageColor(metricsStore.currentRouterMetrics?.cpu_percent)]">
                {{ metricsStore.currentRouterMetrics?.cpu_percent ?? '-' }}%
              </p>
            </div>
          </div>
          <div class="h-2 bg-slate-700 rounded-full overflow-hidden">
            <div
              class="h-full rounded-full transition-all duration-500"
              :class="getUsageBarColor(metricsStore.currentRouterMetrics?.cpu_percent)"
              :style="{ width: `${metricsStore.currentRouterMetrics?.cpu_percent ?? 0}%` }"
            />
          </div>
          <p class="text-xs text-slate-500 mt-2">Real-time CPU utilization</p>
        </div>

        <div class="bg-slate-800 rounded-xl border border-slate-700 p-6">
          <div class="flex items-center gap-3 mb-4">
            <div class="p-2 bg-purple-500/20 rounded-lg">
              <HardDrive class="w-5 h-5 text-purple-400" />
            </div>
            <div>
              <p class="text-sm text-slate-400">Memory Usage</p>
              <p :class="['text-3xl font-bold', getUsageColor(metricsStore.currentRouterMetrics?.memory_percent)]">
                {{ metricsStore.currentRouterMetrics?.memory_percent ?? '-' }}%
              </p>
            </div>
          </div>
          <div class="h-2 bg-slate-700 rounded-full overflow-hidden">
            <div
              class="h-full rounded-full transition-all duration-500"
              :class="getUsageBarColor(metricsStore.currentRouterMetrics?.memory_percent)"
              :style="{ width: `${metricsStore.currentRouterMetrics?.memory_percent ?? 0}%` }"
            />
          </div>
          <p class="text-xs text-slate-500 mt-2">
            {{ metricsStore.currentRouterMetrics?.memory_used_mb ?? 0 }} MB / {{ metricsStore.currentRouterMetrics?.memory_total_mb ?? 0 }} MB
          </p>
        </div>
      </div>

      <div class="bg-slate-800 rounded-xl border border-slate-700">
        <div class="p-4 border-b border-slate-700 flex items-center justify-between">
          <div class="flex items-center gap-2">
            <AlertCircle class="w-5 h-5 text-cyan-400" />
            <h3 class="font-semibold">Performance History</h3>
          </div>
          <div class="flex gap-2">
            <button
              v-for="range in ['1h', '6h', '24h', '7d'] as const"
              :key="range"
              @click="changeTimeRange(range)"
              :class="[
                'px-3 py-1 rounded text-sm transition-colors',
                timeRange === range ? 'bg-blue-500 text-white' : 'bg-slate-700 text-slate-400 hover:bg-slate-600'
              ]"
            >
              {{ range }}
            </button>
          </div>
        </div>
        <div class="p-6">
          <div v-if="chartData.cpu.length === 0" class="text-center py-12 text-slate-400">
            <AlertCircle class="w-12 h-12 mx-auto mb-2 opacity-50" />
            <p>No historical data available</p>
            <AppButton @click="refreshMetrics" variant="outline" size="sm" class="mt-3">
              Collect Metrics Now
            </AppButton>
          </div>
          <div v-else class="space-y-6">
            <div>
              <div class="flex items-center justify-between mb-2">
                <span class="text-sm text-slate-400 flex items-center gap-2">
                  <span class="w-3 h-3 rounded-full bg-blue-500" />
                  CPU Usage
                </span>
                <span class="text-sm font-mono">{{ metricsStore.currentRouterMetrics?.cpu_percent ?? 0 }}%</span>
              </div>
              <svg class="w-full h-24" viewBox="0 0 400 80" preserveAspectRatio="none">
                <defs>
                  <linearGradient id="cpuGradient" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stop-color="rgb(59, 130, 246)" stop-opacity="0.3" />
                    <stop offset="100%" stop-color="rgb(59, 130, 246)" stop-opacity="0" />
                  </linearGradient>
                </defs>
                <path :d="getChartAreaPath(chartData.cpu, 400, 80)" fill="url(#cpuGradient)" />
                <path :d="getChartPath(chartData.cpu, 400, 80)" fill="none" stroke="#3b82f6" stroke-width="2" />
              </svg>
            </div>
            
            <div>
              <div class="flex items-center justify-between mb-2">
                <span class="text-sm text-slate-400 flex items-center gap-2">
                  <span class="w-3 h-3 rounded-full bg-purple-500" />
                  Memory Usage
                </span>
                <span class="text-sm font-mono">{{ metricsStore.currentRouterMetrics?.memory_percent ?? 0 }}%</span>
              </div>
              <svg class="w-full h-24" viewBox="0 0 400 80" preserveAspectRatio="none">
                <defs>
                  <linearGradient id="memGradient" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stop-color="rgb(168, 85, 247)" stop-opacity="0.3" />
                    <stop offset="100%" stop-color="rgb(168, 85, 247)" stop-opacity="0" />
                  </linearGradient>
                </defs>
                <path :d="getChartAreaPath(chartData.memory, 400, 80)" fill="url(#memGradient)" />
                <path :d="getChartPath(chartData.memory, 400, 80)" fill="none" stroke="#a855f7" stroke-width="2" />
              </svg>
            </div>

            <div class="text-xs text-slate-500 text-center">
              Showing {{ chartData.labels.length }} data points
            </div>
          </div>
        </div>
      </div>

      <div v-if="routerStore.currentRouter?.notes" class="bg-slate-800 rounded-xl border border-slate-700 p-6">
        <h3 class="font-semibold mb-3">Notes</h3>
        <p class="text-slate-400 whitespace-pre-wrap">{{ routerStore.currentRouter.notes }}</p>
      </div>
    </div>
  </div>
</template>
