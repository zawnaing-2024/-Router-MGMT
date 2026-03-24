<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  LayoutDashboard,
  Server,
  Database,
  FileCode,
  Clock,
  Terminal,
  Settings,
  Menu,
  X,
  ChevronRight,
  FolderOpen,
  Layers,
  Zap,
  BarChart3,
  FileText,
  Bell,
  Wrench,
  Download,
  Upload,
  History,
  LogOut
} from 'lucide-vue-next'

const route = useRoute()
const router = useRouter()
const isCollapsed = ref(false)

const currentUser = ref<{ username: string; role: string } | null>(null)

function loadUser() {
  const userStr = localStorage.getItem('user')
  if (userStr) {
    currentUser.value = JSON.parse(userStr)
  }
}

function logout() {
  localStorage.removeItem('token')
  localStorage.removeItem('user')
  router.push('/login')
}

loadUser()

const navItems = [
  { path: '/dashboard', name: 'Dashboard', icon: LayoutDashboard },
  { path: '/routers', name: 'Routers', icon: Server },
  { path: '/groups', name: 'Groups', icon: FolderOpen },
  { path: '/backups', name: 'Configs', icon: Database },
  { path: '/templates', name: 'Templates', icon: FileCode },
  { path: '/jobs', name: 'Jobs', icon: Clock },
  { path: '/batch', name: 'Batch Cmd', icon: Layers },
  { path: '/terminal', name: 'Terminal', icon: Terminal }
]

const toolItems = [
  { path: '/reports', name: 'Reports', icon: BarChart3 },
  { path: '/logs', name: 'Router Logs', icon: FileText },
  { path: '/audit', name: 'Audit Log', icon: History },
  { path: '/remediation', name: 'Remediation', icon: Wrench },
  { path: '/notifications', name: 'Notifications', icon: Bell }
]

const systemItems = [
  { path: '/settings', name: 'Settings', icon: Settings }
]

const breadcrumbs = computed(() => {
  const crumbs = [{ name: 'Home', path: '/' }]
  const allItems = [...navItems, ...toolItems, ...systemItems]
  const current = allItems.find(item => route.path.startsWith(item.path))
  if (current) {
    crumbs.push({ name: current.name, path: current.path })
  }
  return crumbs
})

const isActive = (path: string) => {
  if (path === '/') return route.path === '/'
  return route.path.startsWith(path)
}
</script>

<template>
  <aside
    :class="[
      'bg-slate-800 border-r border-slate-700 flex flex-col transition-all duration-200',
      isCollapsed ? 'w-16' : 'w-60'
    ]"
  >
    <div class="p-4 border-b border-slate-700 flex items-center justify-between">
      <div v-if="!isCollapsed" class="flex items-center gap-2">
        <div class="w-8 h-8 bg-blue-500 rounded-lg flex items-center justify-center">
          <Server class="w-5 h-5 text-white" />
        </div>
        <span class="font-semibold text-lg">Router MGMT</span>
      </div>
      <div v-else class="w-8 h-8 bg-blue-500 rounded-lg flex items-center justify-center mx-auto">
        <Server class="w-5 h-5 text-white" />
      </div>
      <button
        @click="isCollapsed = !isCollapsed"
        class="p-1.5 hover:bg-slate-700 rounded-lg transition-colors"
      >
        <Menu v-if="isCollapsed" class="w-5 h-5" />
        <X v-else class="w-5 h-5" />
      </button>
    </div>

    <nav class="flex-1 p-3 space-y-1">
      <router-link
        v-for="item in navItems"
        :key="item.path"
        :to="item.path"
        :class="[
          'flex items-center gap-3 px-3 py-2.5 rounded-lg transition-colors',
          isActive(item.path)
            ? 'bg-blue-500/20 text-blue-400'
            : 'text-slate-400 hover:bg-slate-700 hover:text-slate-200'
        ]"
      >
        <component :is="item.icon" class="w-5 h-5 shrink-0" />
        <span v-if="!isCollapsed">{{ item.name }}</span>
      </router-link>

      <div v-if="!isCollapsed" class="pt-4 pb-2">
        <p class="px-3 text-xs font-medium text-slate-500 uppercase tracking-wider">Tools</p>
      </div>
      <div v-else class="my-2 border-t border-slate-700"></div>

      <router-link
        v-for="item in toolItems"
        :key="item.path"
        :to="item.path"
        :class="[
          'flex items-center gap-3 px-3 py-2.5 rounded-lg transition-colors',
          isActive(item.path)
            ? 'bg-blue-500/20 text-blue-400'
            : 'text-slate-400 hover:bg-slate-700 hover:text-slate-200'
        ]"
      >
        <component :is="item.icon" class="w-5 h-5 shrink-0" />
        <span v-if="!isCollapsed">{{ item.name }}</span>
      </router-link>

      <div class="pt-4">
        <router-link
          v-for="item in systemItems"
          :key="item.path"
          :to="item.path"
          :class="[
            'flex items-center gap-3 px-3 py-2.5 rounded-lg transition-colors',
            isActive(item.path)
              ? 'bg-blue-500/20 text-blue-400'
              : 'text-slate-400 hover:bg-slate-700 hover:text-slate-200'
          ]"
        >
          <component :is="item.icon" class="w-5 h-5 shrink-0" />
          <span v-if="!isCollapsed">{{ item.name }}</span>
        </router-link>
      </div>
    </nav>

    <div class="p-3 border-t border-slate-700">
      <div class="px-3 py-2 flex items-center justify-between">
        <div v-if="!isCollapsed" class="text-xs">
          <p class="text-white font-medium">{{ currentUser?.username }}</p>
          <p class="text-slate-500">{{ currentUser?.role }}</p>
        </div>
        <button @click="logout" class="p-2 hover:bg-slate-700 rounded-lg text-slate-400 hover:text-red-400" :title="isCollapsed ? 'Logout' : ''">
          <LogOut class="w-5 h-5" />
        </button>
      </div>
    </div>

    <div class="p-3 border-t border-slate-700">
      <div v-if="!isCollapsed" class="px-3 py-2">
        <p class="text-xs text-slate-500">Version 0.2.0</p>
      </div>
    </div>
  </aside>
</template>
