<script setup lang="ts">
defineProps<{
  title: string
  subtitle?: string
}>()
</script>

<template>
  <header class="bg-slate-800 border-b border-slate-700 px-6 py-4">
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-xl font-semibold">{{ title }}</h1>
        <p v-if="subtitle" class="text-sm text-slate-400 mt-0.5">{{ subtitle }}</p>
      </div>
      <div class="flex items-center gap-3">
        <slot name="actions" />
      </div>
    </div>
  </header>
</template>
