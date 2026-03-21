<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { reportsApi, routerApi } from '@/api'
import type { UptimeReport, FirmwareInfo, ConfigChange, Router } from '@/types'
import PageHeader from '@/components/PageHeader.vue'
import StatusBadge from '@/components/StatusBadge.vue'

const activeTab = ref('uptime')
const uptimeReports = ref<UptimeReport[]>([])
const firmwareInfo = ref<FirmwareInfo[]>([])
const configChanges = ref<ConfigChange[]>([])
const routers = ref<Router[]>([])
const loading = ref(false)
const uptimeDays = ref(30)

onMounted(async () => {
  await loadRouters()
  await loadUptimeReport()
})

async function loadRouters() {
  try {
    const res = await routerApi.list({ limit: 100 })
    routers.value = res.data
  } catch (error) {
    console.error('Failed to load routers:', error)
  }
}

async function loadUptimeReport() {
  loading.value = true
  try {
    const res = await reportsApi.getUptimeReport(uptimeDays.value)
    uptimeReports.value = res.data
  } catch (error) {
    console.error('Failed to load uptime report:', error)
  }
  loading.value = false
}

async function loadFirmwareInfo() {
  loading.value = true
  try {
    const res = await reportsApi.getFirmwareVersions()
    firmwareInfo.value = res.data
  } catch (error) {
    console.error('Failed to load firmware info:', error)
  }
  loading.value = false
}

async function loadConfigChanges() {
  loading.value = true
  try {
    const res = await reportsApi.getConfigChanges()
    configChanges.value = res.data
  } catch (error) {
    console.error('Failed to load config changes:', error)
  }
  loading.value = false
}

function switchTab(tab: string) {
  activeTab.value = tab
  if (tab === 'firmware' && firmwareInfo.value.length === 0) {
    loadFirmwareInfo()
  } else if (tab === 'changes' && configChanges.value.length === 0) {
    loadConfigChanges()
  }
}

function getRouterHostname(routerId: number): string {
  const router = routers.value.find(r => r.id === routerId)
  return router?.hostname || `Router #${routerId}`
}

function getUptimeColor(percent: number): string {
  if (percent >= 99) return 'text-green-400'
  if (percent >= 95) return 'text-yellow-400'
  return 'text-red-400'
}

function getUptimeBgColor(percent: number): string {
  if (percent >= 99) return 'bg-green-500'
  if (percent >= 95) return 'bg-yellow-500'
  return 'bg-red-500'
}
</script>

<template>
  <div class="p-6">
    <PageHeader title="Reports" description="Network analytics and insights" />

    <div class="flex gap-2 mb-6 border-b border-slate-700 pb-4">
      <button
        @click="switchTab('uptime')"
        :class="[
          'px-4 py-2 rounded-lg transition-colors',
          activeTab === 'uptime' ? 'bg-blue-500 text-white' : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
        ]"
      >
        Uptime
      </button>
      <button
        @click="switchTab('firmware')"
        :class="[
          'px-4 py-2 rounded-lg transition-colors',
          activeTab === 'firmware' ? 'bg-blue-500 text-white' : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
        ]"
      >
        Firmware
      </button>
      <button
        @click="switchTab('changes')"
        :class="[
          'px-4 py-2 rounded-lg transition-colors',
          activeTab === 'changes' ? 'bg-blue-500 text-white' : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
        ]"
      >
        Config Changes
      </button>
    </div>

    <div v-if="activeTab === 'uptime'">
      <div class="flex items-center gap-4 mb-4">
        <label class="text-sm text-slate-400">Time Period:</label>
        <select
          v-model="uptimeDays"
          @change="loadUptimeReport"
          class="px-3 py-2 bg-slate-700 rounded-lg border border-slate-600"
        >
          <option :value="7">Last 7 days</option>
          <option :value="30">Last 30 days</option>
          <option :value="90">Last 90 days</option>
        </select>
      </div>

      <div v-if="loading" class="text-center py-12 text-slate-400">Loading...</div>

      <div v-else class="space-y-3">
        <div
          v-for="report in uptimeReports"
          :key="report.router_id"
          class="bg-slate-800 rounded-lg p-4 border border-slate-700"
        >
          <div class="flex items-center justify-between mb-3">
            <div>
              <span class="font-medium text-lg">{{ report.hostname }}</span>
            </div>
            <div class="text-right">
              <span :class="['text-2xl font-bold', getUptimeColor(report.uptime_percent)]">
                {{ report.uptime_percent.toFixed(2) }}%
              </span>
            </div>
          </div>
          <div class="w-full bg-slate-700 rounded-full h-2 mb-3">
            <div
              :class="['h-2 rounded-full transition-all', getUptimeBgColor(report.uptime_percent)]"
              :style="{ width: `${report.uptime_percent}%` }"
            ></div>
          </div>
          <div class="grid grid-cols-4 gap-4 text-sm text-slate-400">
            <div>
              <span class="block text-xs text-slate-500">Total Checks</span>
              {{ report.total_checks }}
            </div>
            <div>
              <span class="block text-xs text-slate-500">Successful</span>
              {{ report.successful_checks }}
            </div>
            <div>
              <span class="block text-xs text-slate-500">Failed</span>
              {{ report.failed_checks }}
            </div>
            <div>
              <span class="block text-xs text-slate-500">Avg Latency</span>
              {{ report.avg_latency_ms ? `${report.avg_latency_ms}ms` : 'N/A' }}
            </div>
          </div>
        </div>
      </div>
    </div>

    <div v-if="activeTab === 'firmware'">
      <div v-if="loading" class="text-center py-12 text-slate-400">Loading...</div>

      <div v-else class="bg-slate-800 rounded-lg border border-slate-700 overflow-hidden">
        <table class="w-full">
          <thead class="bg-slate-700/50">
            <tr>
              <th class="px-4 py-3 text-left text-sm font-medium text-slate-300">Router</th>
              <th class="px-4 py-3 text-left text-sm font-medium text-slate-300">OS Type</th>
              <th class="px-4 py-3 text-left text-sm font-medium text-slate-300">Version</th>
              <th class="px-4 py-3 text-left text-sm font-medium text-slate-300">Last Checked</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-700">
            <tr v-for="fw in firmwareInfo" :key="fw.router_id" class="hover:bg-slate-700/30">
              <td class="px-4 py-3 font-medium">{{ fw.hostname }}</td>
              <td class="px-4 py-3 text-slate-400">{{ fw.os_type }}</td>
              <td class="px-4 py-3">
                <span v-if="fw.version" class="px-2 py-1 bg-blue-500/20 text-blue-400 rounded text-sm">
                  {{ fw.version }}
                </span>
                <span v-else class="text-slate-500">Unknown</span>
              </td>
              <td class="px-4 py-3 text-slate-400 text-sm">
                {{ new Date(fw.collected_at).toLocaleString() }}
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <div v-if="activeTab === 'changes'">
      <div v-if="loading" class="text-center py-12 text-slate-400">Loading...</div>

      <div v-else-if="configChanges.length === 0" class="text-center py-12">
        <p class="text-slate-400">No config changes detected</p>
      </div>

      <div v-else class="space-y-3">
        <div
          v-for="change in configChanges"
          :key="change.id"
          class="bg-slate-800 rounded-lg p-4 border border-slate-700"
        >
          <div class="flex items-center justify-between">
            <div>
              <span class="font-medium">{{ getRouterHostname(change.router_id) }}</span>
              <span class="ml-2 px-2 py-1 bg-yellow-500/20 text-yellow-400 rounded text-xs">
                {{ change.change_type }}
              </span>
            </div>
            <span class="text-sm text-slate-400">
              {{ new Date(change.detected_at).toLocaleString() }}
            </span>
          </div>
          <div v-if="change.details" class="mt-2 text-sm text-slate-400">
            {{ JSON.stringify(change.details) }}
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
