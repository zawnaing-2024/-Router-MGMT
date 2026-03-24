<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { exportImportApi, routerApi, templateApi, authApi, projectApi } from '@/api'
import PageHeader from '@/components/PageHeader.vue'
import { Plus, Pencil, X, Trash2 } from 'lucide-vue-next'

const activeTab = ref('export')
const importing = ref(false)
const exporting = ref(false)
const importData = ref('')
const importResult = ref<any>(null)
const exportData = ref<any>(null)

const projects = ref<any[]>([])
const users = ref<any[]>([])
const routers = ref<any[]>([])
const showProjectForm = ref(false)
const showUserForm = ref(false)
const editingProject = ref<any>(null)
const editingUser = ref<any>(null)
const projectForm = ref({
  name: '',
  description: ''
})
const userForm = ref({
  username: '',
  email: '',
  password: '',
  role: 'VIEWER',
  router_ids: [] as number[],
  is_active: true,
  project_id: null as number | null
})

const currentUser = ref<any>(null)

function loadUser() {
  const userStr = localStorage.getItem('user')
  if (userStr) {
    currentUser.value = JSON.parse(userStr)
  }
}

async function loadProjects() {
  try {
    const res = await projectApi.list()
    projects.value = res.data
  } catch (e) {
    console.error('Failed to load projects:', e)
  }
}

async function loadUsers() {
  try {
    const res = await authApi.listUsers()
    users.value = res.data
  } catch (e) {
    console.error('Failed to load users:', e)
  }
}

async function loadRouters() {
  try {
    const res = await routerApi.list()
    routers.value = res.data
  } catch (e) {
    console.error('Failed to load routers:', e)
  }
}

function openProjectForm(project?: any) {
  if (project) {
    editingProject.value = project
    projectForm.value = {
      name: project.name,
      description: project.description || ''
    }
  } else {
    editingProject.value = null
    projectForm.value = {
      name: '',
      description: ''
    }
  }
  showProjectForm.value = true
}

async function saveProject() {
  try {
    if (editingProject.value) {
      await projectApi.update(editingProject.value.id, projectForm.value)
    } else {
      await projectApi.create(projectForm.value)
    }
    showProjectForm.value = false
    await loadProjects()
  } catch (e: any) {
    alert(e.response?.data?.detail || 'Failed to save project')
  }
}

async function deleteProject(id: number) {
  if (!confirm('Are you sure you want to delete this project?')) return
  try {
    await projectApi.delete(id)
    await loadProjects()
  } catch (e: any) {
    alert(e.response?.data?.detail || 'Failed to delete project')
  }
}

function openUserForm(user?: any) {
  if (user) {
    editingUser.value = user
    userForm.value = {
      username: user.username,
      email: user.email,
      password: '',
      role: user.role,
      router_ids: user.router_ids || [],
      is_active: user.is_active,
      project_id: user.project_id || null
    }
  } else {
    editingUser.value = null
    userForm.value = {
      username: '',
      email: '',
      password: '',
      role: 'VIEWER',
      router_ids: [],
      is_active: true,
      project_id: null
    }
  }
  showUserForm.value = true
}

async function saveUser() {
  try {
    if (editingUser.value) {
      await authApi.updateUser(editingUser.value.id, userForm.value)
    } else {
      await authApi.register(userForm.value)
    }
    showUserForm.value = false
    await loadUsers()
  } catch (e: any) {
    alert(e.response?.data?.detail || 'Failed to save user')
  }
}

async function deleteUser(id: number) {
  if (!confirm('Are you sure you want to delete this user?')) return
  try {
    await authApi.deleteUser(id)
    await loadUsers()
  } catch (e: any) {
    alert(e.response?.data?.detail || 'Failed to delete user')
  }
}

function toggleRouter(routerId: number) {
  const idx = userForm.value.router_ids.indexOf(routerId)
  if (idx === -1) {
    userForm.value.router_ids.push(routerId)
  } else {
    userForm.value.router_ids.splice(idx, 1)
  }
}

function switchTab(tab: string) {
  activeTab.value = tab
  if (tab === 'projects') {
    loadProjects()
  }
  if (tab === 'users') {
    loadUsers()
    loadRouters()
  }
}

onMounted(() => {
  loadUser()
  loadProjects()
  loadUsers()
  loadRouters()
})

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
      <button
        @click="switchTab('projects')"
        :class="[
          'px-4 py-2 rounded-lg transition-colors',
          activeTab === 'projects' ? 'bg-blue-500 text-white' : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
        ]"
      >
        Projects
      </button>
      <button
        @click="switchTab('users')"
        :class="[
          'px-4 py-2 rounded-lg transition-colors',
          activeTab === 'users' ? 'bg-blue-500 text-white' : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
        ]"
      >
        Users
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

    <div v-if="activeTab === 'projects'" class="space-y-6">
      <div class="bg-slate-800 rounded-lg p-6 border border-slate-700">
        <div class="flex items-center justify-between mb-4">
          <h2 class="text-lg font-semibold text-white">Projects ({{ projects.length }})</h2>
          <button @click="openProjectForm()" class="flex items-center gap-2 bg-blue-500 hover:bg-blue-600 px-4 py-2 rounded-lg text-white font-medium text-sm">
            <Plus class="w-5 h-5" />
            Add Project
          </button>
        </div>
        
        <div v-if="projects.length > 0" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          <div v-for="project in projects" :key="project.id" class="bg-slate-700/50 rounded-lg p-4 relative">
            <div class="flex items-start justify-between">
              <div>
                <h3 class="font-medium">{{ project.name }}</h3>
                <p class="text-sm text-slate-400 mt-1">{{ project.description || 'No description' }}</p>
              </div>
              <div class="flex gap-1">
                <button @click="openProjectForm(project)" class="p-1 hover:bg-slate-600 rounded text-slate-400 hover:text-white">
                  <Pencil class="w-4 h-4" />
                </button>
                <button @click="deleteProject(project.id)" class="p-1 hover:bg-slate-600 rounded text-slate-400 hover:text-red-400">
                  <Trash2 class="w-4 h-4" />
                </button>
              </div>
            </div>
          </div>
        </div>
        <div v-else class="text-slate-500 text-center py-8">
          No projects yet. Click "Add Project" to create one.
        </div>
      </div>
    </div>

    <div v-if="activeTab === 'users'" class="space-y-6">
      <div class="bg-slate-800 rounded-lg p-6 border border-slate-700">
        <div class="flex items-center justify-between mb-4">
          <h2 class="text-lg font-semibold">User Management</h2>
          <button @click="openUserForm()" class="flex items-center gap-2 bg-blue-500 hover:bg-blue-600 px-3 py-1.5 rounded-lg text-sm">
            <Plus class="w-4 h-4" />
            Add User
          </button>
        </div>
        
        <div class="overflow-x-auto">
          <table class="w-full">
            <thead>
              <tr class="text-left text-slate-400 text-sm border-b border-slate-700">
                <th class="pb-3">Username</th>
                <th class="pb-3">Email</th>
                <th class="pb-3">Role</th>
                <th class="pb-3">Routers</th>
                <th class="pb-3">Status</th>
                <th class="pb-3">Actions</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="user in users" :key="user.id" class="border-b border-slate-700/50">
                <td class="py-3">{{ user.username }}</td>
                <td class="py-3 text-slate-400">{{ user.email }}</td>
                <td class="py-3">
                  <span :class="['px-2 py-0.5 rounded text-xs', user.role === 'ADMIN' ? 'bg-purple-500/20 text-purple-400' : user.role === 'OPERATOR' ? 'bg-blue-500/20 text-blue-400' : 'bg-slate-600 text-slate-300']">
                    {{ user.role }}
                  </span>
                </td>
                <td class="py-3 text-sm text-slate-400">
                  {{ user.router_ids?.length || 0 }} routers
                </td>
                <td class="py-3">
                  <span :class="['px-2 py-0.5 rounded text-xs', user.is_active ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400']">
                    {{ user.is_active ? 'Active' : 'Inactive' }}
                  </span>
                </td>
                <td class="py-3">
                  <div class="flex gap-2">
                    <button @click="openUserForm(user)" class="p-1.5 hover:bg-slate-600 rounded text-slate-400 hover:text-white">
                      <Pencil class="w-4 h-4" />
                    </button>
                    <button @click="deleteUser(user.id)" class="p-1.5 hover:bg-slate-600 rounded text-slate-400 hover:text-red-400">
                      <Trash2 class="w-4 h-4" />
                    </button>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <div v-if="showProjectForm" class="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div class="bg-slate-800 rounded-xl p-6 w-full max-w-md border border-slate-700">
        <div class="flex items-center justify-between mb-4">
          <h3 class="text-lg font-semibold">{{ editingProject ? 'Edit Project' : 'Add Project' }}</h3>
          <button @click="showProjectForm = false" class="text-slate-400 hover:text-white">
            <X class="w-5 h-5" />
          </button>
        </div>
        
        <div class="space-y-4">
          <div>
            <label class="block text-sm text-slate-400 mb-1">Project Name</label>
            <input v-model="projectForm.name" class="w-full bg-slate-700 border border-slate-600 rounded-lg px-3 py-2" />
          </div>
          <div>
            <label class="block text-sm text-slate-400 mb-1">Description</label>
            <textarea v-model="projectForm.description" rows="3" class="w-full bg-slate-700 border border-slate-600 rounded-lg px-3 py-2"></textarea>
          </div>
        </div>
        
        <div class="flex gap-2 mt-6">
          <button @click="saveProject" class="flex-1 bg-blue-500 hover:bg-blue-600 py-2 rounded-lg">
            {{ editingProject ? 'Update' : 'Create' }}
          </button>
          <button @click="showProjectForm = false" class="px-4 py-2 bg-slate-700 hover:bg-slate-600 rounded-lg">
            Cancel
          </button>
        </div>
      </div>
    </div>

    <div v-if="showUserForm" class="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div class="bg-slate-800 rounded-xl p-6 w-full max-w-lg border border-slate-700">
        <div class="flex items-center justify-between mb-4">
          <h3 class="text-lg font-semibold">{{ editingUser ? 'Edit User' : 'Add User' }}</h3>
          <button @click="showUserForm = false" class="text-slate-400 hover:text-white">
            <X class="w-5 h-5" />
          </button>
        </div>
        
        <div class="space-y-4">
          <div>
            <label class="block text-sm text-slate-400 mb-1">Username</label>
            <input v-model="userForm.username" class="w-full bg-slate-700 border border-slate-600 rounded-lg px-3 py-2" />
          </div>
          <div>
            <label class="block text-sm text-slate-400 mb-1">Email</label>
            <input v-model="userForm.email" type="email" class="w-full bg-slate-700 border border-slate-600 rounded-lg px-3 py-2" />
          </div>
          <div>
            <label class="block text-sm text-slate-400 mb-1">
              Password {{ editingUser ? '(leave blank to keep current)' : '' }}
            </label>
            <input v-model="userForm.password" type="password" class="w-full bg-slate-700 border border-slate-600 rounded-lg px-3 py-2" />
          </div>
          <div>
            <label class="block text-sm text-slate-400 mb-1">Role</label>
            <select v-model="userForm.role" class="w-full bg-slate-700 border border-slate-600 rounded-lg px-3 py-2">
              <option value="ADMIN">Admin</option>
              <option value="MANAGER">Manager</option>
              <option value="OPERATOR">Operator</option>
              <option value="VIEWER">Viewer</option>
            </select>
          </div>
          <div>
            <label class="block text-sm text-slate-400 mb-1">Project</label>
            <select v-model="userForm.project_id" class="w-full bg-slate-700 border border-slate-600 rounded-lg px-3 py-2">
              <option :value="null">No Project</option>
              <option v-for="project in projects" :key="project.id" :value="project.id">{{ project.name }}</option>
            </select>
          </div>
          <div>
            <label class="block text-sm text-slate-400 mb-1">Assigned Routers</label>
            <div class="bg-slate-700/50 rounded-lg p-3 max-h-40 overflow-y-auto">
              <label v-for="router in routers" :key="router.id" class="flex items-center gap-2 py-1">
                <input 
                  type="checkbox" 
                  :checked="userForm.router_ids.includes(router.id)"
                  @change="toggleRouter(router.id)"
                  class="rounded"
                />
                <span class="text-sm">{{ router.hostname }} ({{ router.ip_address }})</span>
              </label>
            </div>
          </div>
          <div>
            <label class="flex items-center gap-2">
              <input v-model="userForm.is_active" type="checkbox" class="rounded" />
              <span class="text-sm">Active</span>
            </label>
          </div>
        </div>
        
        <div class="flex gap-2 mt-6">
          <button @click="saveUser" class="flex-1 bg-blue-500 hover:bg-blue-600 py-2 rounded-lg">
            {{ editingUser ? 'Update' : 'Create' }}
          </button>
          <button @click="showUserForm = false" class="px-4 py-2 bg-slate-700 hover:bg-slate-600 rounded-lg">
            Cancel
          </button>
        </div>
      </div>
    </div>
  </div>
</template>