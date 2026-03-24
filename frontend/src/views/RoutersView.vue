<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRouterStore, useMetricsStore } from '@/stores'
import { Plus, Search, RefreshCw, Trash2, Edit2, Terminal, Download, Cpu, HardDrive, Clock, Tag, FileDown, Folder } from 'lucide-vue-next'
import PageHeader from '@/components/PageHeader.vue'
import Modal from '@/components/Modal.vue'
import AppButton from '@/components/AppButton.vue'
import StatusBadge from '@/components/StatusBadge.vue'
import { routerGroupApi } from '@/api'
import type { Router, Vendor, RouterGroup } from '@/types'

const routerStore = useRouterStore()
const metricsStore = useMetricsStore()

const searchQuery = ref('')
const selectedVendor = ref('')
const selectedGroup = ref<number | ''>('')
const groups = ref<RouterGroup[]>([])
const showAddModal = ref(false)
const showEditModal = ref(false)
const editingRouter = ref<Router | null>(null)
const loading = ref(false)

async function loadGroups() {
  try {
    const res = await routerGroupApi.list()
    groups.value = res.data
  } catch (e) {
    console.error('Failed to load groups', e)
  }
}

async function loadRouters() {
  loading.value = true
  try {
    await routerStore.fetchRouters({
      search: searchQuery.value || undefined,
      vendor: selectedVendor.value || undefined,
      group_id: selectedGroup.value ? Number(selectedGroup.value) : undefined
    })
  } finally {
    loading.value = false
  }
}

function exportToCSV() {
  const headers = ['ID', 'Hostname', 'IP Address', 'Port', 'Vendor', 'Status', 'Location', 'Uptime', 'Last Seen']
  const rows = filteredRouters.value.map(r => {
    const metrics = metricsStore.allMetrics.find(m => m.router_id === r.id)
    return [
      r.id,
      r.hostname,
      r.ip_address,
      r.port,
      r.vendor,
      r.status,
      r.location || '',
      formatUptime(r.uptime_seconds),
      r.last_seen ? new Date(r.last_seen).toLocaleString() : 'Never'
    ]
  })
  
  const csv = [headers.join(','), ...rows.map(r => r.join(','))].join('\n')
  const blob = new Blob([csv], { type: 'text/csv' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `routers-export-${new Date().toISOString().split('T')[0]}.csv`
  a.click()
  URL.revokeObjectURL(url)
}

const form = ref({
  hostname: '',
  ip_address: '',
  port: 22,
  vendor: 'cisco_ios' as Vendor,
  username: '',
  password: '',
  ssh_key: '',
  sudo_password: '',
  location: '',
  tags: [] as string[],
  notes: ''
})

const vendors = [
  { value: 'cisco_ios', label: 'Cisco IOS' },
  { value: 'cisco_ios_xe', label: 'Cisco IOS-XE' },
  { value: 'juniper_junos', label: 'Juniper JunOS' },
  { value: 'mikrotik_routeros', label: 'MikroTik RouterOS' },
  { value: 'huawei', label: 'Huawei' },
  { value: 'arista_eos', label: 'Arista EOS' },
  { value: 'vyos', label: 'VyOS' },
  { value: 'frr_linux', label: 'FRR Linux' },
  { value: 'generic', label: 'Generic' }
]

const filteredRouters = computed(() => {
  return routerStore.routers.filter(router => {
    const matchesSearch = !searchQuery.value ||
      router.hostname.toLowerCase().includes(searchQuery.value.toLowerCase()) ||
      router.ip_address.toLowerCase().includes(searchQuery.value.toLowerCase())
    const matchesVendor = !selectedVendor.value || router.vendor === selectedVendor.value
    return matchesSearch && matchesVendor
  })
})

async function loadRouters() {
  await routerStore.fetchRouters()
  await metricsStore.fetchAllLatest()
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

function formatUptime(seconds?: number): string {
  if (!seconds) return '-'
  const days = Math.floor(seconds / 86400)
  const hours = Math.floor((seconds % 86400) / 3600)
  const mins = Math.floor((seconds % 3600) / 60)
  
  if (days > 0) return `${days}d ${hours}h`
  if (hours > 0) return `${hours}h ${mins}m`
  return `${mins}m`
}

async function handleAddRouter() {
  loading.value = true
  try {
    const result = await routerStore.createRouter(form.value)
    if (result) {
      showAddModal.value = false
      resetForm()
    }
  } finally {
    loading.value = false
  }
}

async function handleEditRouter() {
  if (!editingRouter.value) return
  loading.value = true
  try {
    const result = await routerStore.updateRouter(editingRouter.value.id, form.value)
    if (result) {
      showEditModal.value = false
      editingRouter.value = null
      resetForm()
    }
  } finally {
    loading.value = false
  }
}

function openEdit(router: Router) {
  editingRouter.value = router
  form.value = {
    hostname: router.hostname,
    ip_address: router.ip_address,
    port: router.port,
    vendor: router.vendor,
    username: router.username,
    password: '',
    ssh_key: router.ssh_key || '',
    location: router.location || '',
    tags: router.tags || [],
    notes: router.notes || ''
  }
  showEditModal.value = true
}

async function handleDelete(router: Router) {
  if (confirm(`Delete router ${router.hostname}?`)) {
    await routerStore.deleteRouter(router.id)
  }
}

async function handleBackup(router: Router) {
  if (confirm(`Backup ${router.hostname} now?`)) {
    try {
      await routerStore.backupRouter(router.id)
      alert('Backup completed successfully')
    } catch (e: any) {
      alert('Backup failed: ' + e.message)
    } finally {
      await loadRouters()
    }
  }
}

function resetForm() {
  form.value = {
    hostname: '',
    ip_address: '',
    port: 22,
    vendor: 'cisco_ios',
    username: '',
    password: '',
    ssh_key: '',
    location: '',
    tags: [],
    notes: ''
  }
}

onMounted(() => {
  loadRouters()
  loadGroups()
})
</script>

<template>
  <div>
    <PageHeader title="Routers" subtitle="Manage your network routers">
      <template #actions>
        <div class="flex items-center gap-3">
          <div class="relative">
            <Search class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
            <input
              v-model="searchQuery"
              type="text"
              placeholder="Search routers..."
              class="pl-10 pr-4 py-2 bg-slate-700 border border-slate-600 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 w-64"
            />
          </div>
          <select
            v-model="selectedVendor"
            class="px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="">All Vendors</option>
            <option v-for="v in vendors" :key="v.value" :value="v.value">{{ v.label }}</option>
          </select>
          <select
            v-model="selectedGroup"
            @change="loadRouters"
            class="px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option :value="''">All Groups</option>
            <option v-for="g in groups" :key="g.id" :value="g.id">{{ g.name }}</option>
          </select>
          <AppButton @click="loadRouters" variant="ghost" size="sm">
            <RefreshCw class="w-4 h-4" />
          </AppButton>
          <AppButton @click="exportToCSV" variant="ghost" size="sm" title="Export to CSV">
            <FileDown class="w-4 h-4" />
          </AppButton>
          <AppButton @click="showAddModal = true">
            <Plus class="w-4 h-4" />
            Add Router
          </AppButton>
        </div>
      </template>
    </PageHeader>

    <div class="p-6">
      <div class="bg-slate-800 rounded-xl border border-slate-700 overflow-hidden">
        <table class="w-full">
          <thead>
            <tr class="text-left text-sm text-slate-400 border-b border-slate-700 bg-slate-700/30">
              <th class="px-4 py-3 font-medium">Hostname</th>
              <th class="px-4 py-3 font-medium">IP Address</th>
              <th class="px-4 py-3 font-medium">Vendor</th>
              <th class="px-4 py-3 font-medium">Status</th>
              <th class="px-4 py-3 font-medium">Version</th>
              <th class="px-4 py-3 font-medium">Uptime</th>
              <th class="px-4 py-3 font-medium">CPU</th>
              <th class="px-4 py-3 font-medium">Memory</th>
              <th class="px-4 py-3 font-medium">Actions</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="router in filteredRouters"
              :key="router.id"
              class="border-b border-slate-700/50 hover:bg-slate-700/30 cursor-pointer"
              @click="$router.push(`/routers/${router.id}`)"
            >
              <td class="px-4 py-3 font-medium">{{ router.hostname }}</td>
              <td class="px-4 py-3 font-mono text-sm">{{ router.ip_address }}:{{ router.port }}</td>
              <td class="px-4 py-3 capitalize text-sm">{{ router.vendor.replace('_', ' ') }}</td>
              <td class="px-4 py-3" @click.stop>
                <StatusBadge :status="router.status" size="sm" />
              </td>
              <td class="px-4 py-3" @click.stop>
                <span v-if="router.version" class="px-2 py-0.5 bg-blue-500/20 text-blue-400 rounded text-xs font-mono">
                  {{ router.version }}
                </span>
                <span v-else class="text-slate-500 text-sm">-</span>
              </td>
              <td class="px-4 py-3" @click.stop>
                <div class="flex items-center gap-1.5">
                  <Clock class="w-4 h-4 text-slate-400" />
                  <span class="font-mono text-sm text-slate-300">
                    {{ formatUptime(router.uptime_seconds) }}
                  </span>
                </div>
              </td>
              <td class="px-4 py-3" @click.stop>
                <div class="flex items-center gap-1.5">
                  <Cpu class="w-4 h-4 text-blue-400" />
                  <span :class="['font-mono text-sm', getUsageColor(getRouterMetrics(router.id)?.cpu_percent ?? 0)]">
                    {{ getRouterMetrics(router.id)?.cpu_percent ?? 0 }}%
                  </span>
                </div>
              </td>
              <td class="px-4 py-3" @click.stop>
                <div class="flex items-center gap-1.5">
                  <HardDrive class="w-4 h-4 text-purple-400" />
                  <span :class="['font-mono text-sm', getUsageColor(getRouterMetrics(router.id)?.memory_percent ?? 0)]">
                    {{ getRouterMetrics(router.id)?.memory_percent ?? '-' }}%
                  </span>
                </div>
              </td>
              <td class="px-4 py-3" @click.stop>
                <div class="flex items-center gap-2">
                  <router-link
                    :to="`/terminal/${router.id}`"
                    class="p-1.5 hover:bg-slate-600 rounded-lg transition-colors"
                    title="Open Terminal"
                  >
                    <Terminal class="w-4 h-4" />
                  </router-link>
                  <button
                    @click="handleBackup(router)"
                    class="p-1.5 hover:bg-slate-600 rounded-lg transition-colors"
                    title="Backup"
                  >
                    <Download class="w-4 h-4" />
                  </button>
                  <button
                    @click="openEdit(router)"
                    class="p-1.5 hover:bg-slate-600 rounded-lg transition-colors"
                    title="Edit"
                  >
                    <Edit2 class="w-4 h-4" />
                  </button>
                  <button
                    @click="handleDelete(router)"
                    class="p-1.5 hover:bg-red-500/20 text-red-400 rounded-lg transition-colors"
                    title="Delete"
                  >
                    <Trash2 class="w-4 h-4" />
                  </button>
                </div>
              </td>
            </tr>
            <tr v-if="filteredRouters.length === 0">
              <td colspan="9" class="px-4 py-12 text-center text-slate-400">
                No routers found. <button @click="showAddModal = true" class="text-blue-400 hover:underline">Add one</button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <Modal :open="showAddModal" title="Add Router" @close="showAddModal = false; resetForm()">
      <form @submit.prevent="handleAddRouter" class="space-y-4">
        <div class="grid grid-cols-2 gap-4">
          <div>
            <label class="block text-sm font-medium mb-1">Hostname *</label>
            <input
              v-model="form.hostname"
              type="text"
              required
              class="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          <div>
            <label class="block text-sm font-medium mb-1">IP Address *</label>
            <input
              v-model="form.ip_address"
              type="text"
              required
              class="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
        </div>
        <div class="grid grid-cols-2 gap-4">
          <div>
            <label class="block text-sm font-medium mb-1">Port</label>
            <input
              v-model.number="form.port"
              type="number"
              class="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          <div>
            <label class="block text-sm font-medium mb-1">Vendor *</label>
            <select
              v-model="form.vendor"
              required
              class="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option v-for="v in vendors" :key="v.value" :value="v.value">{{ v.label }}</option>
            </select>
          </div>
        </div>
        <div class="grid grid-cols-2 gap-4">
          <div>
            <label class="block text-sm font-medium mb-1">Username *</label>
            <input
              v-model="form.username"
              type="text"
              required
              class="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          <div>
            <label class="block text-sm font-medium mb-1">Password</label>
            <input
              v-model="form.password"
              type="password"
              class="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
        </div>
        <div>
          <label class="block text-sm font-medium mb-1">Location</label>
          <input
            v-model="form.location"
            type="text"
            class="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
        <div>
          <label class="block text-sm font-medium mb-1">Sudo Password (for FRR vtysh)</label>
          <input
            v-model="form.sudo_password"
            type="password"
            placeholder="Required for FRR Linux"
            class="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          <p class="text-xs text-slate-400 mt-1">Needed for FRR routers to access vtysh</p>
        </div>
        <div>
          <label class="block text-sm font-medium mb-1">Notes</label>
          <textarea
            v-model="form.notes"
            rows="2"
            class="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
          />
        </div>
      </form>
      <template #footer>
        <AppButton variant="ghost" @click="showAddModal = false">Cancel</AppButton>
        <AppButton :loading="loading" @click="handleAddRouter">Add Router</AppButton>
      </template>
    </Modal>

    <Modal :open="showEditModal" title="Edit Router" @close="showEditModal = false; editingRouter = null; resetForm()" size="lg">
      <form @submit.prevent="handleEditRouter" class="space-y-4">
        <div class="grid grid-cols-2 gap-4">
          <div>
            <label class="block text-sm font-medium mb-1">Hostname *</label>
            <input
              v-model="form.hostname"
              type="text"
              required
              class="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          <div>
            <label class="block text-sm font-medium mb-1">IP Address *</label>
            <input
              v-model="form.ip_address"
              type="text"
              required
              class="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
        </div>
        <div class="grid grid-cols-2 gap-4">
          <div>
            <label class="block text-sm font-medium mb-1">Port</label>
            <input
              v-model.number="form.port"
              type="number"
              class="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          <div>
            <label class="block text-sm font-medium mb-1">Vendor *</label>
            <select
              v-model="form.vendor"
              required
              class="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option v-for="v in vendors" :key="v.value" :value="v.value">{{ v.label }}</option>
            </select>
          </div>
        </div>
        <div class="grid grid-cols-2 gap-4">
          <div>
            <label class="block text-sm font-medium mb-1">Username *</label>
            <input
              v-model="form.username"
              type="text"
              required
              class="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          <div>
            <label class="block text-sm font-medium mb-1">New Password (leave blank to keep)</label>
            <input
              v-model="form.password"
              type="password"
              class="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
        </div>
        <div>
          <label class="block text-sm font-medium mb-1">Location</label>
          <input
            v-model="form.location"
            type="text"
            class="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
        <div>
          <label class="block text-sm font-medium mb-1">Notes</label>
          <textarea
            v-model="form.notes"
            rows="2"
            class="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
          />
        </div>
      </form>
      <template #footer>
        <AppButton variant="ghost" @click="showEditModal = false">Cancel</AppButton>
        <AppButton :loading="loading" @click="handleEditRouter">Save Changes</AppButton>
      </template>
    </Modal>
  </div>
</template>
