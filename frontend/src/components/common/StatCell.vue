<template>
  <div class="text-center">
    <div class="text-[10px] text-gray-400">{{ label }}</div>
    <div class="text-sm font-bold" :class="color">{{ value }}</div>
  </div>
</template>

<script setup>
defineProps({
  label: { type: String, required: true },
  value: { type: [String, Number], required: true },
  color: { type: String, default: 'text-text' },
})
</script>
