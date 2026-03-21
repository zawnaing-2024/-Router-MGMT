<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed } from 'vue'
import { useRouterStore, useMetricsStore } from '@/stores'
import { Server, CheckCircle, XCircle, AlertTriangle, Database, Clock, AlertCircle, Activity, RefreshCw, Cpu, HardDrive } from 'lucide-vue-next'
import PageHeader from '@/components/PageHeader.vue'
import AppButton from '@/components/AppButton.vue'

const routerStore = useRouterStore()
const metricsStore = useMetricsStore()

const stats = ref([
  { label: 'Total Routers', value: 0, icon: Server, color: 'text-blue-400', bg: 'bg-blue-500/20' },
  { label: 'Online', value: 0, icon: CheckCircle, color: 'text-green-400', bg: 'bg-green-500/20' },
  { label: 'Offline', value: 0, icon: XCircle, color: 'text-red-400', bg: 'bg-red-500/20' },
  { label: 'Warning', value: 0, icon: AlertTriangle, color: 'text-amber-400', bg: 'bg-amber-500/20' },
])

const recentBackups = ref([
  { router: 'Router-01', time: '5 min ago', status: 'success' },
  { router: 'Router-02', time: '15 min ago', status: 'success' },
  { router: 'Router-03', time: '1 hour ago', status: 'failed' },
  { router: 'Router-04', time: '2 hours ago', status: 'success' },
])

const refreshing = ref(false)

async function refreshData() {
  refreshing.value = true
  await Promise.all([
    routerStore.fetchRouters(),
    metricsStore.fetchAllLatest()
  ])
  stats.value[0].value = routerStore.routers.length
  stats.value[1].value = routerStore.routers.filter(r => r.status === 'online').length
  stats.value[2].value = routerStore.routers.filter(r => r.status === 'offline').length
  stats.value[3].value = routerStore.routers.filter(r => r.status === 'warning').length
  refreshing.value = false
}

function getRouterMetrics(routerId: number) {
  return metricsStore.allMetrics.find(m => m.router_id === routerId)
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

let refreshInterval: number | null = null

onMounted(async () => {
  await refreshData()
  refreshInterval = window.setInterval(refreshData, 30000)
})

onUnmounted(() => {
  if (refreshInterval) {
    clearInterval(refreshInterval)
  }
})
</script>

<template>
  <div>
    <PageHeader title="Dashboard" subtitle="Network overview and quick actions">
      <template #actions>
        <AppButton @click="refreshData" variant="ghost" size="sm" :loading="refreshing">
          <RefreshCw class="w-4 h-4" />
          Refresh
        </AppButton>
      </template>
    </PageHeader>

    <div class="p-6 space-y-6">
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <div
          v-for="stat in stats"
          :key="stat.label"
          class="bg-slate-800 rounded-xl border border-slate-700 p-5"
        >
          <div class="flex items-center justify-between">
            <div>
              <p class="text-slate-400 text-sm">{{ stat.label }}</p>
              <p class="text-3xl font-bold mt-1">{{ stat.value }}</p>
            </div>
            <div :class="['p-3 rounded-xl', stat.bg]">
              <component :is="stat.icon" :class="['w-6 h-6', stat.color]" />
            </div>
          </div>
        </div>
      </div>

      <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div class="bg-slate-800 rounded-xl border border-slate-700">
          <div class="p-4 border-b border-slate-700 flex items-center justify-between">
            <h3 class="font-semibold">Recent Backups</h3>
            <router-link to="/backups" class="text-blue-400 text-sm hover:underline">View all</router-link>
          </div>
          <div class="p-4">
            <div v-for="(backup, index) in recentBackups" :key="index" class="flex items-center justify-between py-3 border-b border-slate-700 last:border-0">
              <div class="flex items-center gap-3">
                <CheckCircle v-if="backup.status === 'success'" class="w-5 h-5 text-green-400" />
                <XCircle v-else class="w-5 h-5 text-red-400" />
                <div>
                  <p class="font-medium">{{ backup.router }}</p>
                  <p class="text-sm text-slate-400">{{ backup.time }}</p>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div class="bg-slate-800 rounded-xl border border-slate-700">
          <div class="p-4 border-b border-slate-700 flex items-center justify-between">
            <h3 class="font-semibold">Quick Actions</h3>
          </div>
          <div class="p-4 grid grid-cols-2 gap-3">
            <router-link
              to="/routers"
              class="flex items-center gap-3 p-4 bg-slate-700/50 rounded-lg hover:bg-slate-700 transition-colors"
            >
              <Server class="w-5 h-5 text-blue-400" />
              <span>Add Router</span>
            </router-link>
            <router-link
              to="/backups"
              class="flex items-center gap-3 p-4 bg-slate-700/50 rounded-lg hover:bg-slate-700 transition-colors"
            >
              <Database class="w-5 h-5 text-green-400" />
              <span>Backup All</span>
            </router-link>
            <router-link
              to="/jobs"
              class="flex items-center gap-3 p-4 bg-slate-700/50 rounded-lg hover:bg-slate-700 transition-colors"
            >
              <Clock class="w-5 h-5 text-amber-400" />
              <span>Schedule Job</span>
            </router-link>
            <div class="flex items-center gap-3 p-4 bg-slate-700/50 rounded-lg text-slate-400 cursor-not-allowed">
              <AlertCircle class="w-5 h-5" />
              <span>No Alerts</span>
            </div>
          </div>
        </div>
      </div>

      <div class="bg-slate-800 rounded-xl border border-slate-700">
        <div class="p-4 border-b border-slate-700">
          <h3 class="font-semibold">Router Status</h3>
        </div>
        <div class="overflow-x-auto">
          <table class="w-full">
            <thead>
              <tr class="text-left text-sm text-slate-400 border-b border-slate-700">
                <th class="px-4 py-3 font-medium">Hostname</th>
                <th class="px-4 py-3 font-medium">IP Address</th>
                <th class="px-4 py-3 font-medium">Vendor</th>
                <th class="px-4 py-3 font-medium">Status</th>
                <th class="px-4 py-3 font-medium">Last Seen</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="router in routerStore.routers.slice(0, 5)"
                :key="router.id"
                class="border-b border-slate-700/50 hover:bg-slate-700/30"
              >
                <td class="px-4 py-3 font-medium">{{ router.hostname }}</td>
                <td class="px-4 py-3 font-mono text-sm">{{ router.ip_address }}</td>
                <td class="px-4 py-3 capitalize">{{ router.vendor.replace('_', ' ') }}</td>
                <td class="px-4 py-3">
                  <span
                    :class="[
                      'inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs font-medium',
                      router.status === 'online' && 'bg-green-500/20 text-green-400',
                      router.status === 'offline' && 'bg-red-500/20 text-red-400',
                      router.status === 'warning' && 'bg-amber-500/20 text-amber-400',
                      router.status === 'unknown' && 'bg-slate-500/20 text-slate-400'
                    ]"
                  >
                    <span class="w-1.5 h-1.5 rounded-full bg-current" />
                    {{ router.status }}
                  </span>
                </td>
                <td class="px-4 py-3 text-slate-400">{{ router.last_seen || 'Never' }}</td>
              </tr>
              <tr v-if="routerStore.routers.length === 0">
                <td colspan="5" class="px-4 py-8 text-center text-slate-400">
                  No routers configured. <router-link to="/routers" class="text-blue-400 hover:underline">Add one</router-link>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <div class="bg-slate-800 rounded-xl border border-slate-700">
      <div class="p-4 border-b border-slate-700 flex items-center justify-between">
        <div class="flex items-center gap-2">
          <Activity class="w-5 h-5 text-cyan-400" />
          <h3 class="font-semibold">Performance Monitoring</h3>
        </div>
        <router-link to="/routers" class="text-blue-400 text-sm hover:underline">View all routers</router-link>
      </div>
      <div class="p-4">
        <div v-if="metricsStore.allMetrics.length === 0" class="text-center py-8 text-slate-400">
          <Activity class="w-12 h-12 mx-auto mb-2 opacity-50" />
          <p>No performance data yet</p>
          <AppButton @click="metricsStore.collectAllMetrics" variant="outline" size="sm" class="mt-3">
            Collect Metrics Now
          </AppButton>
        </div>
        <div v-else class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          <div
            v-for="metrics in metricsStore.allMetrics"
            :key="metrics.router_id"
            class="bg-slate-700/50 rounded-lg p-4 hover:bg-slate-700/70 transition-colors cursor-pointer"
            @click="$router.push(`/routers/${metrics.router_id}`)"
          >
            <div class="flex items-center justify-between mb-3">
              <span class="font-medium">{{ metrics.hostname }}</span>
              <span v-if="metrics.collected_at" class="text-xs text-slate-400">
                {{ new Date(metrics.collected_at).toLocaleTimeString() }}
              </span>
            </div>
            
            <div class="space-y-3">
              <div>
                <div class="flex items-center justify-between text-sm mb-1">
                  <div class="flex items-center gap-1.5">
                    <Cpu class="w-4 h-4 text-blue-400" />
                    <span class="text-slate-400">CPU</span>
                  </div>
                  <span :class="['font-mono font-medium', getUsageColor(metrics.cpu_percent)]">
                    {{ metrics.cpu_percent ?? '-' }}%
                  </span>
                </div>
                <div class="h-2 bg-slate-600 rounded-full overflow-hidden">
                  <div
                    class="h-full rounded-full transition-all duration-300"
                    :class="getUsageBarColor(metrics.cpu_percent)"
                    :style="{ width: `${metrics.cpu_percent ?? 0}%` }"
                  />
                </div>
              </div>
              
              <div>
                <div class="flex items-center justify-between text-sm mb-1">
                  <div class="flex items-center gap-1.5">
                    <HardDrive class="w-4 h-4 text-purple-400" />
                    <span class="text-slate-400">Memory</span>
                  </div>
                  <span :class="['font-mono font-medium', getUsageColor(metrics.memory_percent)]">
                    {{ metrics.memory_percent ?? '-' }}%
                  </span>
                </div>
                <div class="h-2 bg-slate-600 rounded-full overflow-hidden">
                  <div
                    class="h-full rounded-full transition-all duration-300"
                    :class="getUsageBarColor(metrics.memory_percent)"
                    :style="{ width: `${metrics.memory_percent ?? 0}%` }"
                  />
                </div>
                <div v-if="metrics.memory_used_mb && metrics.memory_total_mb" class="text-xs text-slate-500 mt-1">
                  {{ metrics.memory_used_mb }} MB / {{ metrics.memory_total_mb }} MB
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
