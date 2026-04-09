<template>
  <div class="flex items-center justify-between mb-8">
    <div v-for="(step, idx) in steps" :key="idx" class="flex items-center flex-1">
      <!-- Step Number -->
      <div
        :class="{
          'bg-primary text-card': currentStep >= idx,
          'bg-border text-text2': currentStep < idx
        }"
        class="flex items-center justify-center w-10 h-10 rounded-full font-bold text-sm transition-all"
      >
        {{ idx + 1 }}
      </div>

      <!-- Step Label -->
      <div class="ml-3">
        <p
          :class="{
            'text-text font-medium': currentStep >= idx,
            'text-text2': currentStep < idx
          }"
          class="text-sm"
        >
          {{ step }}
        </p>
      </div>

      <!-- Connector Line -->
      <div
        v-if="idx < steps.length - 1"
        :class="{
          'bg-primary': currentStep > idx,
          'bg-border': currentStep <= idx
        }"
        class="flex-1 h-1 mx-4 transition-all"
      ></div>
    </div>
  </div>
</template>

<script setup>
defineProps({
  steps: {
    type: Array,
    required: true
  },
  currentStep: {
    type: Number,
    default: 0
  }
})
</script>
