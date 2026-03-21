<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { routerApi } from '@/api'
import type { Router } from '@/types'
import PageHeader from '@/components/PageHeader.vue'

const routers = ref<Router[]>([])
const loading = ref(false)
const deviceLoading = ref(false)
const selectedRouterId = ref<number | null>(null)
const deviceLogs = ref<{ success: boolean; logs: string; error?: string; hostname?: string; vendor?: string } | null>(null)
const deviceInfo = ref<any>(null)

onMounted(async () => {
  await loadRouters()
})

async function loadRouters() {
  loading.value = true
  try {
    const res = await routerApi.list({ limit: 100 })
    routers.value = res.data
  } catch (error) {
    console.error('Failed to load routers:', error)
  }
  loading.value = false
}

async function fetchDeviceLogs(routerId: number) {
  deviceLoading.value = true
  deviceLogs.value = null
  deviceInfo.value = null
  selectedRouterId.value = routerId
  
  try {
    const res = await fetch(`/api/routers/${routerId}/device-logs`)
    deviceLogs.value = await res.json()
    
    const infoRes = await fetch(`/api/routers/${routerId}/device-info`)
    deviceInfo.value = await infoRes.json()
  } catch (error) {
    console.error('Failed to fetch device logs:', error)
    deviceLogs.value = { success: false, error: 'Failed to fetch', logs: '' }
  }
  deviceLoading.value = false
}

const onlineRouters = computed(() => routers.value.filter(r => r.status === 'online'))

function formatUptime(seconds?: number): string {
  if (!seconds) return '-'
  const days = Math.floor(seconds / 86400)
  const hours = Math.floor((seconds % 86400) / 3600)
  const mins = Math.floor((seconds % 3600) / 60)
  
  if (days > 0) return `${days}d ${hours}h ${mins}m`
  if (hours > 0) return `${hours}h ${mins}m`
  return `${mins}m`
}
</script>

<template>
  <div class="p-6">
    <PageHeader title="Router Logs" description="View system logs and device information from your routers" />

    <div class="bg-slate-800 rounded-lg border border-slate-700 p-4 mb-6">
      <h3 class="text-lg font-medium mb-4">Select Router to View Device Logs</h3>
      <div class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
        <button
          v-for="router in onlineRouters"
          :key="router.id"
          @click="fetchDeviceLogs(router.id)"
          :class="[
            'p-4 rounded-lg border transition-colors text-left',
            selectedRouterId === router.id
              ? 'border-blue-500 bg-blue-500/20'
              : 'border-slate-700 bg-slate-700/50 hover:border-slate-600'
          ]"
        >
          <div class="font-medium">{{ router.hostname }}</div>
          <div class="text-sm text-slate-400">{{ router.ip_address }}</div>
          <div class="flex items-center gap-2 mt-1">
            <span class="text-xs px-2 py-0.5 bg-slate-600 rounded">{{ router.vendor.replace('_', ' ') }}</span>
            <span v-if="router.uptime_seconds" class="text-xs text-slate-500">{{ formatUptime(router.uptime_seconds) }}</span>
          </div>
        </button>
      </div>
      <div v-if="onlineRouters.length === 0" class="text-center py-8 text-slate-400">
        No online routers found
      </div>
    </div>

    <div v-if="deviceLoading" class="text-center py-12 text-slate-400">
      Fetching device logs...
    </div>

    <div v-else-if="deviceLogs">
      <div v-if="deviceLogs.success" class="space-y-4">
        <div class="bg-slate-800 rounded-lg border border-slate-700 p-4">
          <h3 class="text-lg font-medium mb-2">
            <span class="text-green-400">●</span> {{ deviceLogs.hostname }}
          </h3>
          <div class="text-sm text-slate-400">
            Vendor: <span class="text-white">{{ deviceLogs.vendor?.replace('_', ' ') }}</span>
          </div>
        </div>

        <div v-if="deviceInfo && deviceInfo.success" class="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <div class="bg-slate-800 rounded-lg border border-slate-700 p-4">
            <h4 class="text-sm font-medium text-slate-400 mb-2">System Resources</h4>
            <div class="space-y-2 text-sm">
              <div v-if="deviceInfo.data.commands.version">
                <span class="text-slate-500">Version:</span>
                <span class="ml-2 px-2 py-0.5 bg-blue-500/20 text-blue-400 rounded font-mono text-xs">
                  {{ deviceInfo.data.commands.version.split('\n')[0] }}
                </span>
              </div>
              <div v-if="deviceInfo.data.commands.uptime">
                <span class="text-slate-500">Uptime:</span>
                <span class="ml-2 text-white">{{ deviceInfo.data.commands.uptime.split('\n').slice(0, 2).join(', ') }}</span>
              </div>
            </div>
          </div>

          <div v-if="deviceInfo.data.commands.interfaces" class="bg-slate-800 rounded-lg border border-slate-700 p-4">
            <h4 class="text-sm font-medium text-slate-400 mb-2">Interfaces</h4>
            <pre class="text-xs text-slate-300 bg-slate-900 rounded p-2 overflow-auto max-h-32">{{ deviceInfo.data.commands.interfaces }}</pre>
          </div>
        </div>

        <div class="bg-slate-800 rounded-lg border border-slate-700 p-4">
          <h4 class="text-lg font-medium mb-2">System Logs</h4>
          <div class="flex justify-between items-center mb-2">
            <span class="text-sm text-slate-400">Latest 100 log entries</span>
            <button
              @click="fetchDeviceLogs(selectedRouterId!)"
              class="px-3 py-1 text-sm bg-blue-500 hover:bg-blue-600 rounded transition-colors"
            >
              Refresh
            </button>
          </div>
          <pre class="text-sm text-slate-300 bg-slate-900 rounded p-4 overflow-auto max-h-96 font-mono">{{ deviceLogs.logs || 'No logs available' }}</pre>
        </div>
      </div>

      <div v-else class="bg-red-500/20 border border-red-500/50 rounded-lg p-4">
        <h3 class="text-lg font-medium text-red-400 mb-2">Failed to fetch device logs</h3>
        <p class="text-slate-300">{{ deviceLogs.error }}</p>
      </div>
    </div>

    <div v-else class="text-center py-12 text-slate-400">
      <p class="text-lg mb-2">Select a router above to view its logs and system information</p>
      <p class="text-sm text-slate-500">Click on any online router to see device logs, version, uptime, and interfaces</p>
    </div>
  </div>
</template>
