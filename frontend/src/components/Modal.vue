<script setup lang="ts">
import { X } from 'lucide-vue-next'

const props = defineProps<{
  show?: boolean
  open?: boolean
  title: string
  size?: 'sm' | 'md' | 'lg' | 'xl'
}>()

const emit = defineEmits<{
  close: []
}>()

const sizeClasses = {
  sm: 'max-w-md',
  md: 'max-w-lg',
  lg: 'max-w-2xl',
  xl: 'max-w-4xl'
}
</script>

<template>
  <Teleport to="body">
    <Transition name="modal">
      <div
        v-if="show || open"
        class="fixed inset-0 z-50 flex items-center justify-center p-4"
      >
        <div
          class="absolute inset-0 bg-black/60 backdrop-blur-sm"
          @click="emit('close')"
        />
        <div
          :class="[
            'relative bg-slate-800 rounded-xl shadow-2xl border border-slate-700 w-full',
            size ? sizeClasses[size] : sizeClasses.md
          ]"
        >
          <div class="flex items-center justify-between p-4 border-b border-slate-700">
            <h2 class="text-lg font-semibold">{{ title }}</h2>
            <button
              @click="emit('close')"
              class="p-1.5 hover:bg-slate-700 rounded-lg transition-colors"
            >
              <X class="w-5 h-5" />
            </button>
          </div>
          <div class="p-4">
            <slot />
          </div>
          <div v-if="$slots.footer" class="p-4 border-t border-slate-700 flex justify-end gap-3">
            <slot name="footer" />
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.modal-enter-active,
.modal-leave-active {
  transition: opacity 0.2s ease;
}

.modal-enter-active > div:last-child,
.modal-leave-active > div:last-child {
  transition: transform 0.2s ease;
}

.modal-enter-from,
.modal-leave-to {
  opacity: 0;
}

.modal-enter-from > div:last-child,
.modal-leave-to > div:last-child {
  transform: scale(0.95);
}
</style>
