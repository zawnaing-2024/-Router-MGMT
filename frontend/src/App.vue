<script setup lang="ts">
import { computed } from 'vue'
import { RouterView, useRoute } from 'vue-router'
import AppSidebar from '@/components/AppSidebar.vue'

const route = useRoute()
const isLogin = computed(() => route.path === '/login')
</script>

<template>
  <div class="flex h-screen bg-slate-900">
    <AppSidebar v-if="!isLogin" />
    <main class="flex-1 overflow-auto" :class="{ 'w-full': isLogin }">
      <RouterView />
    </main>
  </div>
</template>
