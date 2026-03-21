<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useBackupStore, useRouterStore } from '@/stores'
import { RefreshCw, Trash2, RotateCcw, Download, Search } from 'lucide-vue-next'
import PageHeader from '@/components/PageHeader.vue'
import Modal from '@/components/Modal.vue'
import AppButton from '@/components/AppButton.vue'
import { backupApi } from '@/api'
import type { ConfigBackup } from '@/types'

const backupStore = useBackupStore()
const routerStore = useRouterStore()

const searchQuery = ref('')
const selectedBackup = ref<ConfigBackup | null>(null)
const showDetailModal = ref(false)
const showDiffModal = ref(false)
const diffResult = ref<{ diff: string; added: number; removed: number } | null>(null)
const compareBackup1 = ref<number | null>(null)
const compareBackup2 = ref<number | null>(null)

function formatDate(dateStr: string) {
  return new Date(dateStr).toLocaleString()
}

function formatSize(bytes: number) {
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
}

async function loadBackups() {
  await backupStore.fetchBackups()
  await routerStore.fetchRouters()
}

function getRouterName(routerId: number) {
  const router = routerStore.routers.find(r => r.id === routerId)
  return router?.hostname || `Router #${routerId}`
}

function openDetail(backup: ConfigBackup) {
  selectedBackup.value = backup
  showDetailModal.value = true
}

async function handleRestore(backup: ConfigBackup) {
  if (confirm('Restore this configuration to the router?')) {
    try {
      await backupStore.restoreBackup(backup.id)
      alert('Configuration restored successfully')
    } catch (e: any) {
      alert('Restore failed: ' + e.message)
    }
  }
}

async function handleDelete(backup: ConfigBackup) {
  if (confirm('Delete this backup?')) {
    await backupStore.deleteBackup(backup.id)
  }
}

async function handleDownload(backup: ConfigBackup) {
  try {
    const response = await fetch(`/api/backups/${backup.id}/download`)
    const blob = await response.blob()
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = backup.filename || `backup_${backup.id}.cfg`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    window.URL.revokeObjectURL(url)
  } catch (e: any) {
    alert('Download failed: ' + e.message)
  }
}

async function compareBackups() {
  if (!compareBackup1.value || !compareBackup2.value) {
    alert('Please select two backups to compare')
    return
  }
  try {
    diffResult.value = await backupStore.compareBackups(compareBackup1.value, compareBackup2.value)
    showDiffModal.value = true
  } catch (e: any) {
    alert('Compare failed: ' + e.message)
  }
}

onMounted(() => {
  loadBackups()
})
</script>

<template>
  <div>
    <PageHeader title="Configuration Backups" subtitle="View and manage router configurations">
      <template #actions>
        <div class="flex items-center gap-3">
          <div class="relative">
            <Search class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
            <input
              v-model="searchQuery"
              type="text"
              placeholder="Search..."
              class="pl-10 pr-4 py-2 bg-slate-700 border border-slate-600 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 w-48"
            />
          </div>
          <AppButton @click="loadBackups" variant="ghost" size="sm">
            <RefreshCw class="w-4 h-4" />
          </AppButton>
        </div>
      </template>
    </PageHeader>

    <div class="p-6">
      <div class="bg-slate-800 rounded-xl border border-slate-700 overflow-hidden">
        <table class="w-full">
          <thead>
            <tr class="text-left text-sm text-slate-400 border-b border-slate-700 bg-slate-700/30">
              <th class="px-4 py-3 font-medium">Router</th>
              <th class="px-4 py-3 font-medium">Filename</th>
              <th class="px-4 py-3 font-medium">Source</th>
              <th class="px-4 py-3 font-medium">Date</th>
              <th class="px-4 py-3 font-medium">Size</th>
              <th class="px-4 py-3 font-medium">Actions</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="backup in backupStore.backups"
              :key="backup.id"
              class="border-b border-slate-700/50 hover:bg-slate-700/30"
            >
              <td class="px-4 py-3 font-medium">{{ getRouterName(backup.router_id) }}</td>
              <td class="px-4 py-3">
                <code class="text-sm text-cyan-400 bg-slate-700/50 px-2 py-1 rounded">
                  {{ backup.filename || 'N/A' }}
                </code>
              </td>
              <td class="px-4 py-3">
                <span class="px-2 py-0.5 rounded-full text-xs font-medium"
                  :class="backup.source === 'manual' ? 'bg-blue-500/20 text-blue-400' : 'bg-amber-500/20 text-amber-400'">
                  {{ backup.source }}
                </span>
              </td>
              <td class="px-4 py-3 text-sm">{{ formatDate(backup.created_at) }}</td>
              <td class="px-4 py-3 text-sm font-mono">{{ formatSize(backup.size_bytes) }}</td>
              <td class="px-4 py-3">
                <div class="flex items-center gap-2">
                  <button
                    @click="handleDownload(backup)"
                    class="p-1.5 hover:bg-cyan-500/20 text-cyan-400 rounded-lg transition-colors"
                    title="Download"
                  >
                    <Download class="w-4 h-4" />
                  </button>
                  <button
                    @click="openDetail(backup)"
                    class="px-2 py-1 text-xs hover:bg-slate-600 rounded transition-colors"
                  >
                    View
                  </button>
                  <button
                    @click="handleRestore(backup)"
                    class="p-1.5 hover:bg-green-500/20 text-green-400 rounded-lg transition-colors"
                    title="Restore"
                  >
                    <RotateCcw class="w-4 h-4" />
                  </button>
                  <button
                    @click="handleDelete(backup)"
                    class="p-1.5 hover:bg-red-500/20 text-red-400 rounded-lg transition-colors"
                    title="Delete"
                  >
                    <Trash2 class="w-4 h-4" />
                  </button>
                </div>
              </td>
            </tr>
            <tr v-if="backupStore.backups.length === 0">
              <td colspan="6" class="px-4 py-12 text-center text-slate-400">
                No backups found. Go to Routers to create backups.
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <Modal :open="showDetailModal" title="Backup Details" size="lg" @close="showDetailModal = false">
      <div v-if="selectedBackup" class="space-y-4">
        <div class="grid grid-cols-2 gap-4 text-sm">
          <div>
            <span class="text-slate-400">Router:</span>
            <span class="ml-2 font-medium">{{ getRouterName(selectedBackup.router_id) }}</span>
          </div>
          <div>
            <span class="text-slate-400">Filename:</span>
            <code class="ml-2 text-cyan-400 bg-slate-700/50 px-2 py-0.5 rounded text-xs">
              {{ selectedBackup.filename || 'N/A' }}
            </code>
          </div>
          <div>
            <span class="text-slate-400">Source:</span>
            <span class="ml-2 font-medium capitalize">{{ selectedBackup.source }}</span>
          </div>
          <div>
            <span class="text-slate-400">Date:</span>
            <span class="ml-2 font-medium">{{ formatDate(selectedBackup.created_at) }}</span>
          </div>
          <div>
            <span class="text-slate-400">Size:</span>
            <span class="ml-2 font-medium">{{ formatSize(selectedBackup.size_bytes) }}</span>
          </div>
        </div>
        <div>
          <p class="text-slate-400 text-sm mb-2">Checksum</p>
          <code class="block p-3 bg-slate-900 rounded-lg text-xs font-mono break-all">
            {{ selectedBackup.checksum }}
          </code>
        </div>
        <div>
          <p class="text-slate-400 text-sm mb-2">Configuration Content</p>
          <pre class="p-4 bg-slate-900 rounded-lg text-xs font-mono overflow-auto max-h-96">{{ selectedBackup.content || 'Loading...' }}</pre>
        </div>
      </div>
      <template #footer>
        <AppButton variant="ghost" @click="showDetailModal = false">Close</AppButton>
        <AppButton @click="handleDownload(selectedBackup!)">
          <Download class="w-4 h-4" />
          Download
        </AppButton>
      </template>
    </Modal>

    <Modal :open="showDiffModal" title="Compare Backups" size="xl" @close="showDiffModal = false">
      <div v-if="diffResult" class="space-y-4">
        <div class="flex items-center gap-4 text-sm">
          <span class="text-green-400">+ {{ diffResult.added }} lines added</span>
          <span class="text-red-400">- {{ diffResult.removed }} lines removed</span>
        </div>
        <pre class="p-4 bg-slate-900 rounded-lg text-xs font-mono overflow-auto max-h-96">{{ diffResult.diff }}</pre>
      </div>
    </Modal>
  </div>
</template>
