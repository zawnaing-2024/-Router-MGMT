<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { routerGroupApi } from '@/api'
import type { RouterGroup, Router } from '@/types'
import { routerApi } from '@/api'
import Modal from '@/components/Modal.vue'
import PageHeader from '@/components/PageHeader.vue'
import StatusBadge from '@/components/StatusBadge.vue'

const groups = ref<RouterGroup[]>([])
const routers = ref<Router[]>([])
const showModal = ref(false)
const editingGroup = ref<RouterGroup | null>(null)
const loading = ref(false)

const formData = ref({
  name: '',
  description: '',
  tags: [] as string[],
  router_ids: [] as number[]
})

onMounted(async () => {
  await loadData()
})

async function loadData() {
  loading.value = true
  try {
    const [groupsRes, routersRes] = await Promise.all([
      routerGroupApi.list(),
      routerApi.list()
    ])
    groups.value = groupsRes.data
    routers.value = routersRes.data
  } catch (error) {
    console.error('Failed to load data:', error)
  }
  loading.value = false
}

function openCreate() {
  editingGroup.value = null
  formData.value = { name: '', description: '', tags: [], router_ids: [] }
  showModal.value = true
}

function openEdit(group: RouterGroup) {
  editingGroup.value = group
  formData.value = {
    name: group.name,
    description: group.description || '',
    tags: [...group.tags],
    router_ids: [...group.router_ids]
  }
  showModal.value = true
}

async function saveGroup() {
  try {
    if (editingGroup.value) {
      await routerGroupApi.update(editingGroup.value.id, formData.value)
    } else {
      await routerGroupApi.create(formData.value)
    }
    showModal.value = false
    await loadData()
  } catch (error) {
    console.error('Failed to save group:', error)
  }
}

async function deleteGroup(id: number) {
  if (confirm('Are you sure you want to delete this group?')) {
    try {
      await routerGroupApi.delete(id)
      await loadData()
    } catch (error) {
      console.error('Failed to delete group:', error)
    }
  }
}

function getRouterName(id: number): string {
  const router = routers.value.find(r => r.id === id)
  return router?.hostname || `Router #${id}`
}
</script>

<template>
  <div class="p-6">
    <PageHeader title="Router Groups" description="Organize routers by region, site, or role">
      <template #actions>
        <button
          @click="openCreate"
          class="px-4 py-2 bg-blue-500 hover:bg-blue-600 text-white rounded-lg transition-colors"
        >
          Create Group
        </button>
      </template>
    </PageHeader>

    <div v-if="loading" class="text-center py-12 text-slate-400">Loading...</div>

    <div v-else-if="groups.length === 0" class="text-center py-12">
      <p class="text-slate-400 mb-4">No router groups yet</p>
      <button
        @click="openCreate"
        class="px-4 py-2 bg-blue-500 hover:bg-blue-600 text-white rounded-lg transition-colors"
      >
        Create your first group
      </button>
    </div>

    <div v-else class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      <div
        v-for="group in groups"
        :key="group.id"
        class="bg-slate-800 rounded-lg p-4 border border-slate-700"
      >
        <div class="flex items-start justify-between mb-3">
          <div>
            <h3 class="font-semibold text-lg">{{ group.name }}</h3>
            <p v-if="group.description" class="text-sm text-slate-400">{{ group.description }}</p>
          </div>
          <div class="flex gap-2">
            <button
              @click="openEdit(group)"
              class="p-1.5 hover:bg-slate-700 rounded transition-colors text-slate-400"
            >
              Edit
            </button>
            <button
              @click="deleteGroup(group.id)"
              class="p-1.5 hover:bg-red-500/20 rounded transition-colors text-red-400"
            >
              Delete
            </button>
          </div>
        </div>

        <div class="flex flex-wrap gap-2 mb-3">
          <span
            v-for="tag in group.tags"
            :key="tag"
            class="px-2 py-1 text-xs bg-slate-700 rounded"
          >
            {{ tag }}
          </span>
        </div>

        <div class="text-sm text-slate-400">
          {{ group.router_ids.length }} router{{ group.router_ids.length !== 1 ? 's' : '' }}
        </div>

        <div v-if="group.router_ids.length > 0" class="mt-2 space-y-1">
          <div
            v-for="routerId in group.router_ids.slice(0, 3)"
            :key="routerId"
            class="text-sm flex items-center gap-2"
          >
            <span class="w-2 h-2 rounded-full bg-green-500"></span>
            {{ getRouterName(routerId) }}
          </div>
          <p v-if="group.router_ids.length > 3" class="text-xs text-slate-500">
            +{{ group.router_ids.length - 3 }} more
          </p>
        </div>
      </div>
    </div>

    <Modal :show="showModal" :title="editingGroup ? 'Edit Group' : 'Create Group'" @close="showModal = false">
      <div class="space-y-4">
        <div>
          <label class="block text-sm font-medium text-slate-300 mb-1">Name</label>
          <input
            v-model="formData.name"
            type="text"
            class="w-full px-3 py-2 bg-slate-700 rounded-lg border border-slate-600 focus:border-blue-500 focus:outline-none"
          />
        </div>

        <div>
          <label class="block text-sm font-medium text-slate-300 mb-1">Description</label>
          <textarea
            v-model="formData.description"
            rows="2"
            class="w-full px-3 py-2 bg-slate-700 rounded-lg border border-slate-600 focus:border-blue-500 focus:outline-none"
          ></textarea>
        </div>

        <div>
          <label class="block text-sm font-medium text-slate-300 mb-1">Tags</label>
          <input
            :value="formData.tags.join(', ')"
            @input="formData.tags = ($event.target as HTMLInputElement).value.split(',').map(t => t.trim()).filter(Boolean)"
            type="text"
            placeholder="comma separated"
            class="w-full px-3 py-2 bg-slate-700 rounded-lg border border-slate-600 focus:border-blue-500 focus:outline-none"
          />
        </div>

        <div>
          <label class="block text-sm font-medium text-slate-300 mb-2">Routers</label>
          <div class="space-y-2 max-h-48 overflow-y-auto">
            <label
              v-for="router in routers"
              :key="router.id"
              class="flex items-center gap-2 p-2 bg-slate-700 rounded cursor-pointer hover:bg-slate-600"
            >
              <input
                type="checkbox"
                :checked="formData.router_ids.includes(router.id)"
                @change="
                  formData.router_ids.includes(router.id)
                    ? formData.router_ids = formData.router_ids.filter(id => id !== router.id)
                    : formData.router_ids.push(router.id)
                "
                class="rounded"
              />
              <span>{{ router.hostname }}</span>
              <StatusBadge :status="router.status" class="ml-auto" />
            </label>
          </div>
        </div>
      </div>

      <template #footer>
        <button
          @click="showModal = false"
          class="px-4 py-2 text-slate-300 hover:bg-slate-700 rounded-lg transition-colors"
        >
          Cancel
        </button>
        <button
          @click="saveGroup"
          class="px-4 py-2 bg-blue-500 hover:bg-blue-600 text-white rounded-lg transition-colors"
        >
          Save
        </button>
      </template>
    </Modal>
  </div>
</template>
