<template>
  <div class="grid grid-cols-4 gap-4">
    <div
      v-for="(step, idx) in steps"
      :key="idx"
      @click="$emit('step-click', idx)"
      :class="{
        'border-primary-dark bg-primary-light': isActive(idx),
        'border-border hover:border-primary': !isActive(idx)
      }"
      class="p-6 border-2 rounded-lg cursor-pointer transition-all hover:shadow-md"
    >
      <!-- Step Number -->
      <div
        :class="{
          'bg-primary-dark text-primary-light': isActive(idx),
          'bg-border text-text2': !isActive(idx)
        }"
        class="inline-flex items-center justify-center w-10 h-10 rounded-full font-bold text-sm mb-4"
      >
        {{ idx + 1 }}
      </div>

      <!-- Content -->
      <h3 class="font-bold text-text mb-2">{{ step.title }}</h3>
      <p class="text-sm text-text2">{{ step.description }}</p>

      <!-- Icon -->
      <div v-if="step.icon" class="mt-4 text-4xl">{{ step.icon }}</div>
    </div>
  </div>
</template>

<script setup>
defineProps({
  steps: {
    type: Array,
    required: true
  },
  activeStep: {
    type: Number,
    default: -1
  }
})

defineEmits(['step-click'])

const isActive = (idx) => {
  return idx === activeStep
}
</script>
