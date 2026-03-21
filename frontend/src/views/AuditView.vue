<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { auditLogApi } from '@/api'
import type { AuditLog } from '@/types'
import PageHeader from '@/components/PageHeader.vue'

const logs = ref<AuditLog[]>([])
const loading = ref(false)
const actions = ref<string[]>([])
const entityTypes = ref<string[]>([])

const filters = ref({
  action: '',
  entity_type: '',
  start_date: '',
  end_date: ''
})

onMounted(async () => {
  await loadData()
})

async function loadData() {
  loading.value = true
  try {
    const params: any = {}
    if (filters.value.action) params.action = filters.value.action
    if (filters.value.entity_type) params.entity_type = filters.value.entity_type
    if (filters.value.start_date) params.start_date = filters.value.start_date
    if (filters.value.end_date) params.end_date = filters.value.end_date
    
    const [logsRes, actionsRes, typesRes] = await Promise.all([
      auditLogApi.list(params),
      auditLogApi.getActions(),
      auditLogApi.getEntityTypes()
    ])
    logs.value = logsRes.data
    actions.value = actionsRes.data
    entityTypes.value = typesRes.data
  } catch (error) {
    console.error('Failed to load audit logs:', error)
  }
  loading.value = false
}

function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleString()
}

function getActionColor(action: string): string {
  if (action.includes('create') || action.includes('add')) return 'text-green-400 bg-green-400/10'
  if (action.includes('delete') || action.includes('remove')) return 'text-red-400 bg-red-400/10'
  if (action.includes('update') || action.includes('edit')) return 'text-yellow-400 bg-yellow-400/10'
  return 'text-blue-400 bg-blue-400/10'
}
</script>

<template>
  <div class="p-6">
    <PageHeader title="Audit Log" description="History of all changes and actions" />

    <div class="bg-slate-800 rounded-lg border border-slate-700 p-4 mb-6">
      <div class="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div>
          <label class="block text-sm text-slate-400 mb-1">Action</label>
          <select
            v-model="filters.action"
            @change="loadData"
            class="w-full px-3 py-2 bg-slate-700 rounded-lg border border-slate-600 focus:border-blue-500 focus:outline-none"
          >
            <option value="">All Actions</option>
            <option v-for="action in actions" :key="action" :value="action">{{ action }}</option>
          </select>
        </div>

        <div>
          <label class="block text-sm text-slate-400 mb-1">Entity Type</label>
          <select
            v-model="filters.entity_type"
            @change="loadData"
            class="w-full px-3 py-2 bg-slate-700 rounded-lg border border-slate-600 focus:border-blue-500 focus:outline-none"
          >
            <option value="">All Types</option>
            <option v-for="type in entityTypes" :key="type" :value="type">{{ type }}</option>
          </select>
        </div>

        <div>
          <label class="block text-sm text-slate-400 mb-1">From Date</label>
          <input
            v-model="filters.start_date"
            type="datetime-local"
            @change="loadData"
            class="w-full px-3 py-2 bg-slate-700 rounded-lg border border-slate-600 focus:border-blue-500 focus:outline-none"
          />
        </div>

        <div>
          <label class="block text-sm text-slate-400 mb-1">To Date</label>
          <input
            v-model="filters.end_date"
            type="datetime-local"
            @change="loadData"
            class="w-full px-3 py-2 bg-slate-700 rounded-lg border border-slate-600 focus:border-blue-500 focus:outline-none"
          />
        </div>
      </div>
    </div>

    <div v-if="loading" class="text-center py-12 text-slate-400">Loading...</div>

    <div v-else-if="logs.length === 0" class="text-center py-12">
      <p class="text-slate-400">No audit logs found</p>
    </div>

    <div v-else class="bg-slate-800 rounded-lg border border-slate-700 overflow-hidden">
      <table class="w-full">
        <thead class="bg-slate-700/50">
          <tr>
            <th class="px-4 py-3 text-left text-sm font-medium text-slate-300">Timestamp</th>
            <th class="px-4 py-3 text-left text-sm font-medium text-slate-300">Action</th>
            <th class="px-4 py-3 text-left text-sm font-medium text-slate-300">Entity</th>
            <th class="px-4 py-3 text-left text-sm font-medium text-slate-300">Details</th>
            <th class="px-4 py-3 text-left text-sm font-medium text-slate-300">IP</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-slate-700">
          <tr v-for="log in logs" :key="log.id" class="hover:bg-slate-700/30">
            <td class="px-4 py-3 text-sm text-slate-400">{{ formatDate(log.created_at) }}</td>
            <td class="px-4 py-3">
              <span :class="['px-2 py-1 text-xs rounded', getActionColor(log.action)]">
                {{ log.action }}
              </span>
            </td>
            <td class="px-4 py-3 text-sm">
              <span class="text-slate-300">{{ log.entity_type }}</span>
              <span v-if="log.entity_id" class="text-slate-500 ml-1">#{{ log.entity_id }}</span>
            </td>
            <td class="px-4 py-3 text-sm text-slate-400 max-w-xs truncate">
              {{ JSON.stringify(log.details) }}
            </td>
            <td class="px-4 py-3 text-sm text-slate-400">{{ log.ip_address || '-' }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>
