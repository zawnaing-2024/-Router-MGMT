<script setup lang="ts">
import { onMounted } from 'vue'
import { useRouterStore } from '@/stores'
import { Terminal, Server } from 'lucide-vue-next'
import PageHeader from '@/components/PageHeader.vue'
import AppButton from '@/components/AppButton.vue'

const routerStore = useRouterStore()

onMounted(() => {
  routerStore.fetchRouters()
})
</script>

<template>
  <div>
    <PageHeader title="Terminal" subtitle="Select a router to open SSH terminal" />

    <div class="p-6">
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        <div
          v-for="r in routerStore.routers"
          :key="r.id"
          class="bg-slate-800 rounded-xl border border-slate-700 p-5 hover:border-blue-500 transition-colors"
        >
          <div class="flex items-center justify-between mb-4">
            <div class="flex items-center gap-3">
              <div class="p-2 bg-slate-700 rounded-lg">
                <Server class="w-5 h-5 text-blue-400" />
              </div>
              <div>
                <h3 class="font-semibold">{{ r.hostname }}</h3>
                <p class="text-sm text-slate-400 font-mono">{{ r.ip_address }}:{{ r.port }}</p>
              </div>
            </div>
            <span
              :class="[
                'px-2 py-0.5 rounded-full text-xs font-medium',
                r.status === 'online' ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'
              ]"
            >
              {{ r.status }}
            </span>
          </div>
          <div class="text-sm text-slate-400 mb-4">
            {{ r.vendor.replace('_', ' ') }}
          </div>
          <router-link :to="`/terminal/${r.id}`">
            <AppButton class="w-full">
              <Terminal class="w-4 h-4" />
              Open Terminal
            </AppButton>
          </router-link>
        </div>
      </div>

      <div v-if="routerStore.routers.length === 0" class="text-center py-12">
        <Server class="w-12 h-12 mx-auto text-slate-600 mb-4" />
        <p class="text-slate-400">No routers found.</p>
        <router-link to="/routers" class="text-blue-400 hover:underline mt-2 inline-block">
          Add a router first
        </router-link>
      </div>
    </div>
  </div>
</template>
