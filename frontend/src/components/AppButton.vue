<script setup lang="ts">
defineProps<{
  variant?: 'primary' | 'success' | 'warning' | 'danger' | 'ghost'
  size?: 'sm' | 'md'
  loading?: boolean
  disabled?: boolean
}>()
</script>

<template>
  <button
    :disabled="disabled || loading"
    :class="[
      'inline-flex items-center justify-center gap-2 font-medium rounded-lg transition-colors',
      'disabled:opacity-50 disabled:cursor-not-allowed',
      variant === 'primary' && 'bg-blue-500 hover:bg-blue-600 text-white',
      variant === 'success' && 'bg-green-500 hover:bg-green-600 text-white',
      variant === 'warning' && 'bg-amber-500 hover:bg-amber-600 text-white',
      variant === 'danger' && 'bg-red-500 hover:bg-red-600 text-white',
      variant === 'ghost' && 'bg-transparent hover:bg-slate-700 text-slate-300',
      !variant && 'bg-blue-500 hover:bg-blue-600 text-white',
      size === 'sm' ? 'px-3 py-1.5 text-sm' : 'px-4 py-2 text-sm',
    ]"
  >
    <span v-if="loading" class="w-4 h-4 border-2 border-current border-t-transparent rounded-full animate-spin" />
    <slot />
  </button>
</template>
