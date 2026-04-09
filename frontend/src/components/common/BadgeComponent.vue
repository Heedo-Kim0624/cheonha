<template>
  <span
    :class="[
      'inline-flex items-center px-3 py-1 rounded-full text-xs font-medium',
      badgeClass
    ]"
  >
    {{ text }}
  </span>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  text: {
    type: String,
    required: true
  },
  variant: {
    type: String,
    default: 'primary',
    validator: (v) => ['primary', 'success', 'danger', 'warning', 'info', 'gray'].includes(v)
  }
})

const badgeClass = computed(() => {
  const variants = {
    primary: 'bg-primary-light text-primary-dark',
    success: 'bg-success bg-opacity-10 text-success',
    danger: 'bg-danger bg-opacity-10 text-danger',
    warning: 'bg-warning bg-opacity-10 text-warning',
    info: 'bg-info bg-opacity-10 text-info',
    gray: 'bg-bg text-text2'
  }
  return variants[props.variant]
})
</script>
