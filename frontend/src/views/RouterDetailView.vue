<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useRouterStore, useMetricsStore } from '@/stores'
import { metricsApi, routerApi } from '@/api'
import { ArrowLeft, Server, MapPin, Clock, Cpu, HardDrive, RefreshCw, Terminal, Database, AlertCircle, Network, Globe, Activity, Zap, Search, Download, FileText, Play, Plus, X, Pencil } from 'lucide-vue-next'
import PageHeader from '@/components/PageHeader.vue'
import AppButton from '@/components/AppButton.vue'
import type { NetworkInterface, BGPPeer, QuickCommand } from '@/types'

const route = useRoute()
const router = useRouter()
const routerStore = useRouterStore()
const metricsStore = useMetricsStore()

const routerId = Number(route.params.id)
const timeRange = ref<'1h' | '6h' | '24h' | '7d'>('24h')

const networkInfo = ref<{ interfaces: NetworkInterface[], bgp_peers: BGPPeer[] }>({ interfaces: [], bgp_peers: [] })
const loadingNetwork = ref(false)
const activeTab = ref<'interfaces' | 'bgp' | 'actions'>('interfaces')
const commandOutput = ref('')
const runningCommand = ref(false)

const customCommands = ref<{ id: string; name: string; command: string }[]>([])
const showAddForm = ref(false)
const newCmdName = ref('')
const newCmdCommand = ref('')
const editingId = ref<string | null>(null)
const editName = ref('')
const editCommand = ref('')

async function loadCustomCommands() {
  customCommands.value = routerStore.currentRouter?.custom_commands || []
}

function startEdit(cmd: { id: string; name: string; command: string }) {
  editingId.value = cmd.id
  editName.value = cmd.name
  editCommand.value = cmd.command
}

function saveEdit() {
  const idx = customCommands.value.findIndex(c => c.id === editingId.value)
  if (idx !== -1 && editName.value && editCommand.value) {
    customCommands.value[idx] = { id: editingId.value, name: editName.value, command: editCommand.value }
    saveCustomCommands()
  }
  editingId.value = null
}

function cancelEdit() {
  editingId.value = null
}

async function saveCustomCommands() {
  try {
    await routerApi.updateCustomCommands(routerId, customCommands.value)
    showAddForm.value = false
    newCmdName.value = ''
    newCmdCommand.value = ''
  } catch (e) {
    console.error('Failed to save custom commands:', e)
  }
}

function addCustomCommand() {
  if (!newCmdName.value || !newCmdCommand.value) return
  customCommands.value.push({
    id: Date.now().toString(),
    name: newCmdName.value,
    command: newCmdCommand.value
  })
  saveCustomCommands()
}

function deleteCustomCommand(id: string) {
  customCommands.value = customCommands.value.filter(c => c.id !== id)
  saveCustomCommands()
}

const quickCommands: QuickCommand[] = []

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

async function loadNetworkInfo() {
  loadingNetwork.value = true
  try {
    const res = await metricsApi.getNetworkInfo(routerId)
    networkInfo.value = res.data
  } catch (e) {
    console.error('Failed to load network info:', e)
  } finally {
    loadingNetwork.value = false
  }
}

async function runQuickCommand(cmd: any) {
  commandOutput.value = ''
  runningCommand.value = true
  try {
    const res = await fetch(`/api/routers/${routerId}/command`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ command: cmd.command })
    })
    const data = await res.json()
    commandOutput.value = data.output || data.error || 'No output'
  } catch (e: any) {
    commandOutput.value = `Error: ${e.message}`
  } finally {
    runningCommand.value = false
  }
}

async function changeTimeRange(range: '1h' | '6h' | '24h' | '7d') {
  timeRange.value = range
  await metricsStore.fetchHistory(routerId, timeRangeHours.value)
}

function formatBytes(bytes: number): string {
  if (!bytes) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
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
  await loadNetworkInfo()
  await loadCustomCommands()
  
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
            <div class="flex justify-between">
              <span class="text-slate-400">Uptime</span>
              <span class="font-mono">{{ metricsStore.currentRouterMetrics?.uptime_seconds ? formatUptime(metricsStore.currentRouterMetrics.uptime_seconds) : 'N/A' }}</span>
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

        <div class="bg-slate-800 rounded-xl border border-slate-700 p-6">
          <div class="flex items-center gap-3 mb-4">
            <div class="p-2 bg-cyan-500/20 rounded-lg">
              <Clock class="w-5 h-5 text-cyan-400" />
            </div>
            <div>
              <p class="text-sm text-slate-400">Uptime</p>
              <p class="text-3xl font-bold text-slate-200">
                {{ metricsStore.currentRouterMetrics?.uptime_seconds ? formatUptime(metricsStore.currentRouterMetrics.uptime_seconds) : '-' }}
              </p>
            </div>
          </div>
          <p class="text-xs text-slate-500">System uptime since last boot</p>
        </div>
      </div>

      <div class="bg-slate-800 rounded-xl border border-slate-700">
        <div class="p-4 border-b border-slate-700 flex items-center justify-between">
          <div class="flex items-center gap-4">
            <button
              @click="activeTab = 'interfaces'"
              :class="['flex items-center gap-2 px-3 py-1.5 rounded text-sm transition-colors', activeTab === 'interfaces' ? 'bg-blue-500 text-white' : 'text-slate-400 hover:text-white']"
            >
              <Network class="w-4 h-4" />
              Interfaces ({{ networkInfo.interfaces.length }})
            </button>
            <button
              v-if="routerStore.currentRouter?.vendor === 'frr_linux'"
              @click="activeTab = 'bgp'"
              :class="['flex items-center gap-2 px-3 py-1.5 rounded text-sm transition-colors', activeTab === 'bgp' ? 'bg-green-500 text-white' : 'text-slate-400 hover:text-white']"
            >
              <Globe class="w-4 h-4" />
              BGP Peers ({{ networkInfo.bgp_peers.length }})
            </button>
            <button
              @click="activeTab = 'actions'"
              :class="['flex items-center gap-2 px-3 py-1.5 rounded text-sm transition-colors', activeTab === 'actions' ? 'bg-purple-500 text-white' : 'text-slate-400 hover:text-white']"
            >
              <Zap class="w-4 h-4" />
              Quick Actions
            </button>
          </div>
          <button @click="loadNetworkInfo" class="p-1.5 hover:bg-slate-600 rounded-lg" title="Refresh">
            <RefreshCw :class="['w-4 h-4', loadingNetwork ? 'animate-spin' : '']" />
          </button>
        </div>
        
        <div class="p-4">
          <div v-if="activeTab === 'interfaces'" class="space-y-2">
            <div v-if="networkInfo.interfaces.length === 0" class="text-center py-8 text-slate-400">
              <Network class="w-8 h-8 mx-auto mb-2 opacity-50" />
              <p>No interfaces found</p>
            </div>
            <div
              v-for="iface in networkInfo.interfaces"
              :key="iface.name"
              class="bg-slate-700/50 rounded-lg p-4"
            >
              <div class="flex items-center justify-between mb-3">
                <div class="flex items-center gap-3">
                  <div :class="['w-3 h-3 rounded-full', iface.state === 'UP' ? 'bg-green-500 animate-pulse' : 'bg-slate-500']" />
                  <div>
                    <div class="flex items-center gap-2">
                      <p class="font-mono font-bold text-lg">{{ iface.name }}</p>
                      <span v-if="iface.speed_mbps" class="px-2 py-0.5 bg-blue-500/20 text-blue-400 rounded text-xs">
                        {{ iface.speed_mbps }} Mbps {{ iface.duplex || '' }}
                      </span>
                      <span v-if="iface.port" class="px-2 py-0.5 bg-purple-500/20 text-purple-400 rounded text-xs">
                        {{ iface.port }}
                      </span>
                    </div>
                    <p class="text-xs text-slate-400">{{ iface.ip }}</p>
                  </div>
                </div>
                <span :class="['px-3 py-1 rounded-full text-xs font-bold', iface.state === 'UP' ? 'bg-green-500/20 text-green-400' : 'bg-slate-600 text-slate-400']">
                  {{ iface.state }}
                </span>
              </div>
              
              <div class="grid grid-cols-2 md:grid-cols-5 gap-3">
                <div class="bg-slate-800/50 rounded-lg p-3">
                  <p class="text-xs text-slate-400 mb-1">TX Bytes</p>
                  <p class="font-mono text-green-400 font-bold">{{ formatBytes(iface.tx_bytes) }}</p>
                </div>
                <div class="bg-slate-800/50 rounded-lg p-3">
                  <p class="text-xs text-slate-400 mb-1">RX Bytes</p>
                  <p class="font-mono text-blue-400 font-bold">{{ formatBytes(iface.rx_bytes) }}</p>
                </div>
                <div class="bg-slate-800/50 rounded-lg p-3">
                  <p class="text-xs text-slate-400 mb-1">TX Packets</p>
                  <p class="font-mono text-white">{{ (iface.tx_packets || 0).toLocaleString() }}</p>
                </div>
                <div class="bg-slate-800/50 rounded-lg p-3">
                  <p class="text-xs text-slate-400 mb-1">RX Packets</p>
                  <p class="font-mono text-white">{{ (iface.rx_packets || 0).toLocaleString() }}</p>
                </div>
                <div v-if="iface.speed_mbps" class="bg-slate-800/50 rounded-lg p-3">
                  <p class="text-xs text-slate-400 mb-1">Speed</p>
                  <p class="font-mono text-yellow-400 font-bold">{{ iface.speed_mbps }} Mbps</p>
                </div>
              </div>
              
              <div v-if="iface.duplex || iface.port || (iface.tx_errors || 0) > 0 || (iface.rx_errors || 0) > 0" class="mt-3 flex flex-wrap gap-4 text-xs">
                <span v-if="iface.duplex" class="px-2 py-1 bg-purple-500/20 text-purple-400 rounded">
                  {{ iface.duplex }}
                </span>
                <span v-if="iface.port" class="px-2 py-1 bg-cyan-500/20 text-cyan-400 rounded">
                  {{ iface.port }}
                </span>
                <span v-if="(iface.tx_errors || 0) > 0" class="px-2 py-1 bg-red-500/20 text-red-400 rounded">
                  TX Errors: {{ iface.tx_errors?.toLocaleString() }}
                </span>
                <span v-if="(iface.rx_errors || 0) > 0" class="px-2 py-1 bg-red-500/20 text-red-400 rounded">
                  RX Errors: {{ iface.rx_errors?.toLocaleString() }}
                </span>
              </div>
              
              <div v-if="(iface.tx_errors || 0) > 0 || (iface.rx_errors || 0) > 0" class="mt-3 flex gap-4 text-xs">
                <span v-if="(iface.tx_errors || 0) > 0" class="text-red-400">TX Errors: {{ iface.tx_errors?.toLocaleString() }}</span>
                <span v-if="(iface.rx_errors || 0) > 0" class="text-red-400">RX Errors: {{ iface.rx_errors?.toLocaleString() }}</span>
              </div>
            </div>
          </div>

          <div v-if="activeTab === 'bgp'" class="space-y-2">
            <div v-if="networkInfo.bgp_peers.length === 0" class="text-center py-8 text-slate-400">
              <Globe class="w-8 h-8 mx-auto mb-2 opacity-50" />
              <p>No BGP peers configured</p>
            </div>
            <div
              v-for="peer in networkInfo.bgp_peers"
              :key="peer.neighbor"
              class="bg-slate-700/50 rounded-lg p-4"
            >
              <div class="flex items-center justify-between mb-2">
                <div class="flex items-center gap-3">
                  <div :class="['w-3 h-3 rounded-full', peer.state === 'Established' ? 'bg-green-500 animate-pulse' : 'bg-red-500']" />
                  <div>
                    <p class="font-mono font-bold text-lg">{{ peer.neighbor }}</p>
                    <p class="text-xs text-slate-400">{{ peer.description || 'No description' }}</p>
                  </div>
                </div>
                <span :class="['px-3 py-1 rounded-full text-xs font-bold', 
                  peer.state === 'Established' ? 'bg-green-500/20 text-green-400' : 
                  peer.state === 'Connect' || peer.state === 'Active' ? 'bg-yellow-500/20 text-yellow-400' : 
                  'bg-red-500/20 text-red-400']">
                  {{ peer.state }}
                </span>
              </div>
              <div class="flex flex-wrap gap-4 text-sm">
                <div v-if="peer.asn" class="flex items-center gap-2">
                  <span class="text-slate-400">AS:</span>
                  <span class="font-mono text-blue-400 font-bold">{{ peer.asn }}</span>
                </div>
                <div v-if="peer.uptime" class="flex items-center gap-2">
                  <span class="text-slate-400">Uptime:</span>
                  <span class="font-mono text-cyan-400">{{ peer.uptime }}</span>
                </div>
              </div>
            </div>
            <div v-if="networkInfo.bgp_peers.length > 0" class="text-center text-sm text-slate-400 mt-3">
              Total: {{ networkInfo.bgp_peers.length }} peers | 
              <span class="text-green-400">{{ networkInfo.bgp_peers.filter(p => p.state === 'Established').length }} Established</span> |
              <span class="text-yellow-400">{{ networkInfo.bgp_peers.filter(p => p.state === 'Connect' || p.state === 'Active').length }} Connecting</span> |
              <span class="text-red-400">{{ networkInfo.bgp_peers.filter(p => !['Established', 'Connect', 'Active'].includes(p.state)).length }} Idle</span>
            </div>
          </div>

          <div v-if="activeTab === 'actions'" class="space-y-4">
            <div class="grid grid-cols-2 md:grid-cols-4 gap-2">
              <button
                v-for="cmd in quickCommands.filter(c => c.vendor === 'all' || c.vendor === routerStore.currentRouter?.vendor)"
                :key="cmd.id"
                @click="runQuickCommand(cmd)"
                :disabled="runningCommand"
                class="bg-slate-700/50 hover:bg-slate-600 rounded-lg p-3 text-left transition-colors disabled:opacity-50"
              >
                <Play class="w-4 h-4 text-blue-400 mb-1" />
                <p class="text-sm font-medium truncate">{{ cmd.name }}</p>
                <p class="text-xs text-slate-400 truncate">{{ cmd.description }}</p>
              </button>
            </div>

            <div class="border-t border-slate-700 pt-4">
              <div class="flex items-center justify-between mb-3">
                <h4 class="font-medium text-slate-300">Custom Commands</h4>
                <button @click="showAddForm = !showAddForm" class="flex items-center gap-1 text-xs text-blue-400 hover:text-blue-300">
                  <Plus class="w-4 h-4" />
                  Add
                </button>
              </div>
              
              <div v-if="showAddForm" class="bg-slate-700/50 rounded-lg p-3 mb-3 space-y-2">
                <input v-model="newCmdName" placeholder="Command name" class="w-full bg-slate-800 border border-slate-600 rounded px-3 py-2 text-sm" />
                <input v-model="newCmdCommand" placeholder="Command to run" class="w-full bg-slate-800 border border-slate-600 rounded px-3 py-2 text-sm font-mono" />
                <div class="flex gap-2">
                  <button @click="addCustomCommand" class="flex-1 bg-blue-500 hover:bg-blue-600 rounded py-1.5 text-sm">Save</button>
                  <button @click="showAddForm = false" class="px-3 py-1.5 text-sm text-slate-400 hover:text-white">Cancel</button>
                </div>
              </div>
              
              <div v-if="customCommands.length > 0" class="space-y-2">
                <div
                  v-for="cmd in customCommands"
                  :key="cmd.id"
                  class="bg-slate-700/50 hover:bg-slate-600 rounded-lg p-3"
                >
                  <div v-if="editingId === cmd.id" class="space-y-2">
                    <input v-model="editName" class="w-full bg-slate-800 border border-slate-600 rounded px-3 py-2 text-sm" />
                    <input v-model="editCommand" class="w-full bg-slate-800 border border-slate-600 rounded px-3 py-2 text-sm font-mono" />
                    <div class="flex gap-2">
                      <button @click="saveEdit" class="flex-1 bg-green-500 hover:bg-green-600 rounded py-1.5 text-sm">Save</button>
                      <button @click="cancelEdit" class="px-3 py-1.5 text-sm text-slate-400 hover:text-white">Cancel</button>
                    </div>
                  </div>
                  <div v-else class="flex items-start justify-between">
                    <button @click="runQuickCommand({ id: cmd.id, name: cmd.name, command: cmd.command, vendor: 'all', category: 'custom' })" :disabled="runningCommand" class="text-left disabled:opacity-50">
                      <Play class="w-4 h-4 text-green-400 mb-1" />
                      <p class="text-sm font-medium">{{ cmd.name }}</p>
                      <p class="text-xs text-slate-400 font-mono">{{ cmd.command }}</p>
                    </button>
                    <div class="flex gap-1 ml-2">
                      <button @click="startEdit(cmd)" class="p-1.5 text-slate-400 hover:text-blue-400">
                        <Pencil class="w-4 h-4" />
                      </button>
                      <button @click="deleteCustomCommand(cmd.id)" class="p-1.5 text-slate-400 hover:text-red-400">
                        <X class="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                </div>
              </div>
              <p v-else class="text-sm text-slate-500">No custom commands. Click "Add" to create one.</p>
            </div>
            
            <div class="bg-slate-900 rounded-lg p-4">
              <div class="flex items-center justify-between mb-2">
                <p class="text-xs text-slate-400">Command Output</p>
                <div class="flex items-center gap-2">
                  <span v-if="runningCommand" class="text-xs text-blue-400 animate-pulse">Running...</span>
                  <button @click="commandOutput = ''" class="text-slate-400 hover:text-white text-xs">Clear</button>
                </div>
              </div>
              <pre v-if="commandOutput" class="text-xs font-mono text-green-400 overflow-x-auto whitespace-pre-wrap">{{ commandOutput }}</pre>
              <p v-else class="text-xs text-slate-500">Click a command to run it</p>
            </div>
          </div>
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
