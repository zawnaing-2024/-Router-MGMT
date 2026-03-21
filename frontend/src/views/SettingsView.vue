<script setup lang="ts">
import { ref } from 'vue'
import { exportImportApi, routerApi, templateApi } from '@/api'
import PageHeader from '@/components/PageHeader.vue'

const activeTab = ref('export')
const importing = ref(false)
const exporting = ref(false)
const importData = ref('')
const importResult = ref<any>(null)
const exportData = ref<any>(null)

async function exportRouters() {
  exporting.value = true
  try {
    const res = await exportImportApi.exportRoutersJson()
    exportData.value = res.data
  } catch (error) {
    console.error('Export failed:', error)
  }
  exporting.value = false
}

async function exportAll() {
  exporting.value = true
  try {
    const res = await exportImportApi.exportAllJson()
    exportData.value = res.data
  } catch (error) {
    console.error('Export failed:', error)
  }
  exporting.value = false
}

function downloadExport() {
  const blob = new Blob([JSON.stringify(exportData.value, null, 2)], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `router-mgmt-export-${new Date().toISOString().split('T')[0]}.json`
  a.click()
  URL.revokeObjectURL(url)
}

async function importDataSubmit() {
  importing.value = true
  importResult.value = null
  try {
    const data = JSON.parse(importData.value)
    const res = await exportImportApi.importAll(data)
    importResult.value = res.data
    importData.value = ''
  } catch (error: any) {
    importResult.value = { error: error.message || 'Import failed' }
  }
  importing.value = false
}
</script>

<template>
  <div class="p-6">
    <PageHeader title="Settings" description="Export, import, and system settings" />

    <div class="flex gap-2 mb-6">
      <button
        @click="activeTab = 'export'"
        :class="[
          'px-4 py-2 rounded-lg transition-colors',
          activeTab === 'export' ? 'bg-blue-500 text-white' : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
        ]"
      >
        Export
      </button>
      <button
        @click="activeTab = 'import'"
        :class="[
          'px-4 py-2 rounded-lg transition-colors',
          activeTab === 'import' ? 'bg-blue-500 text-white' : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
        ]"
      >
        Import
      </button>
    </div>

    <div v-if="activeTab === 'export'" class="space-y-6">
      <div class="bg-slate-800 rounded-lg p-6 border border-slate-700">
        <h2 class="text-lg font-semibold mb-4">Export Data</h2>
        <p class="text-slate-400 mb-4">
          Export your router inventory, groups, and templates to a JSON file for backup or migration.
        </p>
        <div class="flex gap-3">
          <button
            @click="exportRouters"
            :disabled="exporting"
            class="px-4 py-2 bg-blue-500 hover:bg-blue-600 disabled:bg-slate-600 text-white rounded-lg transition-colors"
          >
            {{ exporting ? 'Exporting...' : 'Export Routers Only' }}
          </button>
          <button
            @click="exportAll"
            :disabled="exporting"
            class="px-4 py-2 bg-green-500 hover:bg-green-600 disabled:bg-slate-600 text-white rounded-lg transition-colors"
          >
            {{ exporting ? 'Exporting...' : 'Export All Data' }}
          </button>
        </div>

        <div v-if="exportData" class="mt-6">
          <div class="flex items-center justify-between mb-2">
            <h3 class="font-medium">Preview</h3>
            <button
              @click="downloadExport"
              class="px-3 py-1.5 bg-slate-700 hover:bg-slate-600 rounded text-sm transition-colors"
            >
              Download JSON
            </button>
          </div>
          <pre class="bg-slate-900 rounded-lg p-4 text-sm text-slate-300 overflow-x-auto max-h-96">{{ JSON.stringify(exportData, null, 2) }}</pre>
        </div>
      </div>
    </div>

    <div v-if="activeTab === 'import'" class="space-y-6">
      <div class="bg-slate-800 rounded-lg p-6 border border-slate-700">
        <h2 class="text-lg font-semibold mb-4">Import Data</h2>
        <p class="text-slate-400 mb-4">
          Import routers, groups, and templates from a previously exported JSON file.
        </p>

        <div class="mb-4">
          <label class="block text-sm font-medium text-slate-300 mb-2">Paste JSON Data</label>
          <textarea
            v-model="importData"
            rows="10"
            placeholder='{"routers": [...], "groups": [...], "templates": [...]}'
            class="w-full px-3 py-2 bg-slate-700 rounded-lg border border-slate-600 font-mono text-sm focus:border-blue-500 focus:outline-none"
          ></textarea>
        </div>

        <button
          @click="importDataSubmit"
          :disabled="!importData || importing"
          class="px-4 py-2 bg-green-500 hover:bg-green-600 disabled:bg-slate-600 disabled:cursor-not-allowed text-white rounded-lg transition-colors"
        >
          {{ importing ? 'Importing...' : 'Import Data' }}
        </button>

        <div v-if="importResult" class="mt-6">
          <div
            v-if="importResult.error"
            class="p-4 bg-red-500/20 border border-red-500/50 rounded-lg text-red-400"
          >
            {{ importResult.error }}
          </div>

          <div v-else class="space-y-2">
            <h3 class="font-medium mb-3">Import Results</h3>
            
            <div class="bg-slate-700/50 rounded-lg p-4">
              <h4 class="text-sm text-slate-400 mb-2">Routers</h4>
              <div class="flex gap-4">
                <span class="text-green-400">Imported: {{ importResult.routers?.imported || 0 }}</span>
                <span class="text-yellow-400">Skipped: {{ importResult.routers?.skipped || 0 }}</span>
              </div>
            </div>

            <div class="bg-slate-700/50 rounded-lg p-4">
              <h4 class="text-sm text-slate-400 mb-2">Groups</h4>
              <div class="flex gap-4">
                <span class="text-green-400">Imported: {{ importResult.groups?.imported || 0 }}</span>
                <span class="text-yellow-400">Skipped: {{ importResult.groups?.skipped || 0 }}</span>
              </div>
            </div>

            <div class="bg-slate-700/50 rounded-lg p-4">
              <h4 class="text-sm text-slate-400 mb-2">Templates</h4>
              <div class="flex gap-4">
                <span class="text-green-400">Imported: {{ importResult.templates?.imported || 0 }}</span>
                <span class="text-yellow-400">Skipped: {{ importResult.templates?.skipped || 0 }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
