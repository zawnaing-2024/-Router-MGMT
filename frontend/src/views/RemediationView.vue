<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { remediationApi, routerApi } from '@/api'
import type { RemediationScript, Router } from '@/types'
import Modal from '@/components/Modal.vue'
import PageHeader from '@/components/PageHeader.vue'

const scripts = ref<RemediationScript[]>([])
const routers = ref<Router[]>([])
const loading = ref(false)
const showModal = ref(false)
const editingScript = ref<RemediationScript | null>(null)
const runningScript = ref<{ scriptId: number; routerId: number } | null>(null)
const runResults = ref<any>(null)

const formData = ref({
  name: '',
  description: '',
  trigger_condition: 'router.offline',
  commands: [] as string[],
  enabled: true,
  auto_execute: false
})

const triggerConditions = [
  { value: 'manual', label: 'Manual (Run on demand)' },
  { value: 'scheduled', label: 'Scheduled (Run on interval)' },
  { value: 'router.offline', label: 'Auto - Router goes offline' },
  { value: 'router.online', label: 'Auto - Router comes online' },
  { value: 'cpu.high', label: 'Auto - High CPU usage' },
  { value: 'memory.high', label: 'Auto - High memory usage' },
  { value: 'backup.failed', label: 'Auto - Backup failure' },
  { value: 'config.changed', label: 'Auto - Config changed' }
]

onMounted(async () => {
  await loadData()
})

async function loadData() {
  loading.value = true
  try {
    const [scriptsRes, routersRes] = await Promise.all([
      remediationApi.list(),
      routerApi.list({ limit: 100 })
    ])
    scripts.value = scriptsRes.data
    routers.value = routersRes.data
  } catch (error) {
    console.error('Failed to load data:', error)
  }
  loading.value = false
}

function openCreate() {
  editingScript.value = null
  formData.value = {
    name: '',
    description: '',
    trigger_condition: 'router.offline',
    commands: [],
    enabled: true,
    auto_execute: false
  }
  showModal.value = true
}

function openEdit(script: RemediationScript) {
  editingScript.value = script
  formData.value = {
    name: script.name,
    description: script.description || '',
    trigger_condition: script.trigger_condition,
    commands: [...script.commands],
    enabled: script.enabled,
    auto_execute: script.auto_execute
  }
  showModal.value = true
}

async function saveScript() {
  try {
    const data = {
      name: formData.value.name,
      description: formData.value.description,
      trigger_condition: formData.value.trigger_condition,
      commands: formData.value.commands,
      enabled: formData.value.enabled,
      auto_execute: formData.value.auto_execute
    }
    if (editingScript.value) {
      await remediationApi.update(editingScript.value.id, data)
    } else {
      await remediationApi.create(data)
    }
    showModal.value = false
    await loadData()
  } catch (error) {
    console.error('Failed to save script:', error)
    alert('Failed to save script: ' + (error as any).message)
  }
}

async function deleteScript(id: number) {
  if (confirm('Are you sure you want to delete this script?')) {
    try {
      await remediationApi.delete(id)
      await loadData()
    } catch (error) {
      console.error('Failed to delete script:', error)
    }
  }
}

async function runScript(scriptId: number, routerId: number) {
  runningScript.value = { scriptId, routerId }
  runResults.value = null
  try {
    const res = await remediationApi.run(scriptId, routerId)
    runResults.value = res.data
  } catch (error) {
    runResults.value = { success: false, error: 'Failed to run script' }
  }
  runningScript.value = null
}

function addCommand() {
  formData.value.commands.push('')
}

function removeCommand(index: number) {
  formData.value.commands.splice(index, 1)
}
</script>

<template>
  <div class="p-6">
    <PageHeader title="Remediation Scripts" description="Auto-remediation for common issues">
      <template #actions>
        <button
          @click="openCreate"
          class="px-4 py-2 bg-blue-500 hover:bg-blue-600 text-white rounded-lg transition-colors"
        >
          Create Script
        </button>
      </template>
    </PageHeader>

    <div v-if="loading" class="text-center py-12 text-slate-400">Loading...</div>

    <div v-else-if="scripts.length === 0" class="text-center py-12">
      <p class="text-slate-400 mb-4">No remediation scripts configured</p>
      <button
        @click="openCreate"
        class="px-4 py-2 bg-blue-500 hover:bg-blue-600 text-white rounded-lg transition-colors"
      >
        Create your first script
      </button>
    </div>

    <div v-else class="space-y-4">
      <div
        v-for="script in scripts"
        :key="script.id"
        class="bg-slate-800 rounded-lg p-4 border border-slate-700"
      >
        <div class="flex items-start justify-between mb-3">
          <div>
            <div class="flex items-center gap-3">
              <h3 class="font-semibold text-lg">{{ script.name }}</h3>
              <span
                :class="[
                  'px-2 py-0.5 rounded text-xs',
                  script.enabled ? 'bg-green-500/20 text-green-400' : 'bg-slate-500/20 text-slate-400'
                ]"
              >
                {{ script.enabled ? 'Enabled' : 'Disabled' }}
              </span>
            </div>
            <p v-if="script.description" class="text-sm text-slate-400 mt-1">{{ script.description }}</p>
          </div>
          <div class="flex gap-2">
            <button
              @click="openEdit(script)"
              class="px-3 py-1.5 text-sm bg-slate-700 hover:bg-slate-600 rounded transition-colors"
            >
              Edit
            </button>
            <button
              @click="deleteScript(script.id)"
              class="px-3 py-1.5 text-sm text-red-400 hover:bg-red-500/20 rounded transition-colors"
            >
              Delete
            </button>
          </div>
        </div>

        <div class="grid grid-cols-2 gap-4 mb-4">
          <div>
            <span class="text-xs text-slate-500 block">Trigger</span>
            <span class="text-sm">{{ script.trigger_condition }}</span>
          </div>
          <div>
            <span class="text-xs text-slate-500 block">Commands</span>
            <span class="text-sm">{{ script.commands.length }} command(s)</span>
          </div>
        </div>

        <div class="bg-slate-700/50 rounded-lg p-3 mb-4">
          <div class="text-xs text-slate-500 mb-2">Commands:</div>
          <div class="space-y-1">
            <div
              v-for="(cmd, idx) in script.commands.slice(0, 3)"
              :key="idx"
              class="font-mono text-sm text-slate-300"
            >
              {{ idx + 1 }}. {{ cmd }}
            </div>
            <div v-if="script.commands.length > 3" class="text-sm text-slate-500">
              +{{ script.commands.length - 3 }} more...
            </div>
          </div>
        </div>

        <div class="flex items-center gap-2">
          <select
            class="flex-1 px-3 py-2 bg-slate-700 rounded-lg border border-slate-600 text-sm"
            @change="runScript(script.id, Number(($event.target as HTMLSelectElement).value))"
          >
            <option value="">Run on router...</option>
            <option v-for="router in routers" :key="router.id" :value="router.id">
              {{ router.hostname }}
            </option>
          </select>
        </div>
      </div>
    </div>

    <Modal :show="showModal" :title="editingScript ? 'Edit Script' : 'Create Script'" size="lg" @close="showModal = false">
      <div class="space-y-4">
        <div class="grid grid-cols-2 gap-4">
          <div>
            <label class="block text-sm font-medium text-slate-300 mb-1">Name</label>
            <input
              v-model="formData.name"
              type="text"
              class="w-full px-3 py-2 bg-slate-700 rounded-lg border border-slate-600"
            />
          </div>
          <div>
            <label class="block text-sm font-medium text-slate-300 mb-1">Trigger Condition</label>
            <select
              v-model="formData.trigger_condition"
              class="w-full px-3 py-2 bg-slate-700 rounded-lg border border-slate-600"
            >
              <option v-for="cond in triggerConditions" :key="cond.value" :value="cond.value">
                {{ cond.label }}
              </option>
            </select>
          </div>
        </div>

        <div>
          <label class="block text-sm font-medium text-slate-300 mb-1">Description</label>
          <textarea
            v-model="formData.description"
            rows="2"
            class="w-full px-3 py-2 bg-slate-700 rounded-lg border border-slate-600"
          ></textarea>
        </div>

        <div>
          <div class="flex items-center justify-between mb-2">
            <label class="text-sm font-medium text-slate-300">Commands</label>
            <button @click="addCommand" class="text-sm text-blue-400 hover:text-blue-300">
              + Add Command
            </button>
          </div>
          <div class="space-y-2">
            <div v-for="(cmd, idx) in formData.commands" :key="idx" class="flex gap-2">
              <input
                v-model="formData.commands[idx]"
                type="text"
                placeholder="Enter command..."
                class="flex-1 px-3 py-2 bg-slate-700 rounded-lg border border-slate-600 font-mono text-sm"
              />
              <button
                @click="removeCommand(idx)"
                class="px-3 py-2 text-red-400 hover:bg-red-500/20 rounded transition-colors"
              >
                Remove
              </button>
            </div>
          </div>
        </div>

        <div class="flex gap-4">
          <label class="flex items-center gap-2">
            <input v-model="formData.enabled" type="checkbox" class="rounded" />
            <span class="text-sm">Enabled</span>
          </label>
          <label class="flex items-center gap-2">
            <input v-model="formData.auto_execute" type="checkbox" class="rounded" />
            <span class="text-sm">Auto-execute when triggered</span>
          </label>
        </div>
      </div>

      <template #footer>
        <button @click="showModal = false" class="px-4 py-2 text-slate-300 hover:bg-slate-700 rounded-lg">
          Cancel
        </button>
        <button @click="saveScript" class="px-4 py-2 bg-blue-500 hover:bg-blue-600 text-white rounded-lg">
          Save
        </button>
      </template>
    </Modal>

    <Modal :show="!!runResults" title="Script Results" @close="runResults = null">
      <div v-if="runResults">
        <div
          :class="[
            'p-3 rounded-lg mb-4',
            runResults.success ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'
          ]"
        >
          {{ runResults.success ? 'Script executed successfully' : 'Script execution failed' }}
        </div>

        <div v-if="runResults.results" class="space-y-3">
          <div
            v-for="(result, idx) in runResults.results"
            :key="idx"
            class="bg-slate-700/50 rounded-lg p-3"
          >
            <div class="flex items-center justify-between mb-2">
              <span class="font-mono text-sm">{{ result.command }}</span>
              <span
                :class="result.success ? 'text-green-400' : 'text-red-400'"
                class="text-sm"
              >
                {{ result.success ? 'Success' : 'Failed' }}
              </span>
            </div>
            <pre v-if="result.output" class="text-sm text-slate-300 whitespace-pre-wrap">{{ result.output }}</pre>
            <p v-if="result.error" class="text-sm text-red-400">{{ result.error }}</p>
          </div>
        </div>
      </div>

      <template #footer>
        <button @click="runResults = null" class="px-4 py-2 bg-slate-700 hover:bg-slate-600 rounded-lg">
          Close
        </button>
      </template>
    </Modal>
  </div>
</template>
