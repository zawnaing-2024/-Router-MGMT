<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  status: 'online' | 'offline' | 'warning' | 'unknown'
  size?: 'sm' | 'md'
}>()

const statusConfig = {
  online: { bg: 'bg-green-500/20', text: 'text-green-400', label: 'Online' },
  offline: { bg: 'bg-red-500/20', text: 'text-red-400', label: 'Offline' },
  warning: { bg: 'bg-amber-500/20', text: 'text-amber-400', label: 'Warning' },
  unknown: { bg: 'bg-slate-500/20', text: 'text-slate-400', label: 'Unknown' }
}

const config = computed(() => statusConfig[props.status])
</script>

<template>
  <span
    :class="[
      'inline-flex items-center gap-1.5 rounded-full font-medium',
      config.bg,
      config.text,
      size === 'sm' ? 'px-2 py-0.5 text-xs' : 'px-2.5 py-1 text-xs'
    ]"
  >
    <span class="w-1.5 h-1.5 rounded-full bg-current" />
    {{ config.label }}
  </span>
</template>
