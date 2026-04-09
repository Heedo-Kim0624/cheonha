<template>
  <Teleport to="body">
    <Transition name="toast" @enter="startAutoClose">
      <div
        v-if="isVisible"
        :class="[
          'fixed bottom-6 right-6 px-6 py-4 rounded-lg shadow-lg flex items-center gap-3 max-w-sm z-50',
          toastClass
        ]"
      >
        <div v-html="toastIcon" class="w-5 h-5 flex-shrink-0"></div>
        <p class="text-sm font-medium">{{ message }}</p>
        <button
          @click="close"
          class="ml-auto p-1 hover:opacity-70 transition-opacity"
        >
          <span v-html="IconClose" class="w-4 h-4"></span>
        </button>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
import { ref, computed } from 'vue'
import { IconClose, IconSuccess, IconError, IconWarning } from '@/utils/icons'

const props = defineProps({
  message: {
    type: String,
    required: true
  },
  type: {
    type: String,
    default: 'success',
    validator: (v) => ['success', 'error', 'warning'].includes(v)
  },
  duration: {
    type: Number,
    default: 3000
  }
})

const emit = defineEmits(['close'])

const isVisible = ref(true)
let timeout = null

const toastClass = computed(() => {
  const types = {
    success: 'bg-success text-white',
    error: 'bg-danger text-white',
    warning: 'bg-warning text-white'
  }
  return types[props.type]
})

const toastIcon = computed(() => {
  const icons = {
    success: IconSuccess,
    error: IconError,
    warning: IconWarning
  }
  return icons[props.type]
})

const startAutoClose = () => {
  timeout = setTimeout(() => {
    close()
  }, props.duration)
}

const close = () => {
  if (timeout) clearTimeout(timeout)
  isVisible.value = false
  emit('close')
}
</script>

<style scoped>
.toast-enter-active,
.toast-leave-active {
  transition: all 0.3s ease;
}

.toast-enter-from,
.toast-leave-to {
  opacity: 0;
  transform: translateX(100%);
}
</style>
