<template>
  <div>
    <!-- Tab Buttons -->
    <div class="flex gap-2 border-b border-border mb-6">
      <button
        v-for="tab in tabs"
        :key="tab"
        @click="$emit('change', tab)"
        :class="{
          'border-b-2 border-primary text-primary font-medium': activeTab === tab,
          'text-text2 hover:text-text': activeTab !== tab
        }"
        class="px-4 py-3 transition-colors"
      >
        {{ tab }}
      </button>
    </div>

    <!-- Tab Content -->
    <slot></slot>
  </div>
</template>

<script setup>
defineProps({
  tabs: {
    type: Array,
    required: true
  },
  activeTab: {
    type: String,
    required: true
  }
})

defineEmits(['change'])
</script>
