<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { routerApi, batchApi } from '@/api'
import type { Router, BatchCommandResult } from '@/types'
import PageHeader from '@/components/PageHeader.vue'
import StatusBadge from '@/components/StatusBadge.vue'

const routers = ref<Router[]>([])
const selectedRouters = ref<number[]>([])
const command = ref('')
const results = ref<BatchCommandResult[]>([])
const loading = ref(false)
const executing = ref(false)

onMounted(async () => {
  loading.value = true
  try {
    const res = await routerApi.list({ limit: 100 })
    routers.value = res.data
  } catch (error) {
    console.error('Failed to load routers:', error)
  }
  loading.value = false
})

const selectedRoutersInfo = computed(() => {
  return routers.value.filter(r => selectedRouters.value.includes(r.id))
})

function toggleRouter(id: number) {
  if (selectedRouters.value.includes(id)) {
    selectedRouters.value = selectedRouters.value.filter(r => r !== id)
  } else {
    selectedRouters.value.push(id)
  }
}

function selectAll() {
  selectedRouters.value = routers.value.filter(r => r.status === 'online').map(r => r.id)
}

function clearSelection() {
  selectedRouters.value = []
}

async function executeCommand() {
  if (!command.value || selectedRouters.value.length === 0) return
  
  executing.value = true
  results.value = []
  try {
    const res = await batchApi.executeCommand(selectedRouters.value, command.value)
    results.value = res.data.results
  } catch (error) {
    console.error('Failed to execute command:', error)
  }
  executing.value = false
}
</script>

<template>
  <div class="p-6">
    <PageHeader title="Batch Command" description="Execute commands on multiple routers at once" />

    <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <div class="bg-slate-800 rounded-lg border border-slate-700 p-4">
        <div class="flex items-center justify-between mb-4">
          <h2 class="text-lg font-semibold">Select Routers</h2>
          <div class="flex gap-2">
            <button
              @click="selectAll"
              class="text-sm text-blue-400 hover:text-blue-300"
            >
              Select Online
            </button>
            <button
              @click="clearSelection"
              class="text-sm text-slate-400 hover:text-slate-300"
            >
              Clear
            </button>
          </div>
        </div>

        <div v-if="loading" class="text-center py-8 text-slate-400">Loading routers...</div>

        <div v-else class="space-y-2 max-h-96 overflow-y-auto">
          <label
            v-for="router in routers"
            :key="router.id"
            class="flex items-center gap-3 p-3 bg-slate-700/50 rounded-lg cursor-pointer hover:bg-slate-700 transition-colors"
          >
            <input
              type="checkbox"
              :checked="selectedRouters.includes(router.id)"
              @change="toggleRouter(router.id)"
              class="rounded"
            />
            <div class="flex-1">
              <div class="font-medium">{{ router.hostname }}</div>
              <div class="text-sm text-slate-400">{{ router.ip_address }}</div>
            </div>
            <StatusBadge :status="router.status" />
          </label>
        </div>
      </div>

      <div class="space-y-4">
        <div class="bg-slate-800 rounded-lg border border-slate-700 p-4">
          <h2 class="text-lg font-semibold mb-4">Command</h2>
          <textarea
            v-model="command"
            rows="4"
            placeholder="Enter command to execute on selected routers..."
            class="w-full px-3 py-2 bg-slate-700 rounded-lg border border-slate-600 focus:border-blue-500 focus:outline-none font-mono text-sm"
          ></textarea>
          <button
            @click="executeCommand"
            :disabled="!command || selectedRouters.length === 0 || executing"
            class="mt-4 w-full px-4 py-2 bg-blue-500 hover:bg-blue-600 disabled:bg-slate-600 disabled:cursor-not-allowed text-white rounded-lg transition-colors"
          >
            {{ executing ? 'Executing...' : `Execute on ${selectedRouters.length} Router(s)` }}
          </button>
        </div>

        <div v-if="results.length > 0" class="bg-slate-800 rounded-lg border border-slate-700 p-4">
          <h2 class="text-lg font-semibold mb-4">Results</h2>
          <div class="space-y-4 max-h-96 overflow-y-auto">
            <div
              v-for="result in results"
              :key="result.router_id"
              class="bg-slate-700/50 rounded-lg p-3"
            >
              <div class="flex items-center justify-between mb-2">
                <span class="font-medium">{{ result.hostname }}</span>
                <span
                  :class="result.success ? 'text-green-400' : 'text-red-400'"
                  class="text-sm"
                >
                  {{ result.success ? 'Success' : 'Failed' }}
                </span>
              </div>
              <pre
                v-if="result.output"
                class="text-sm text-slate-300 overflow-x-auto whitespace-pre-wrap"
              >{{ result.output }}</pre>
              <p v-if="result.error" class="text-sm text-red-400">{{ result.error }}</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
