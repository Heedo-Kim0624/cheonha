<template>
  <div class="bg-card rounded-lg p-6 border border-border hover:shadow-md transition-shadow">
    <div class="space-y-2">
      <p class="text-sm text-text2">{{ label }}</p>
      <p class="text-2xl font-bold text-text">{{ formattedValue }}</p>
      <div class="flex items-center gap-2">
        <span
          :class="{
            'text-success': change > 0,
            'text-danger': change < 0,
            'text-text3': change === 0
          }"
          class="text-sm font-medium"
        >
          <span v-if="change > 0">+</span>{{ change.toFixed(1) }}%
        </span>
        <span class="text-xs text-text3">{{ subText }}</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { formatCurrency } from '@/utils/format'

defineProps({
  label: {
    type: String,
    required: true
  },
  value: {
    type: Number,
    required: true
  },
  change: {
    type: Number,
    default: 0
  },
  subText: {
    type: String,
    default: '전월 대비'
  }
})

const formattedValue = computed(() => formatCurrency(value))
</script>
