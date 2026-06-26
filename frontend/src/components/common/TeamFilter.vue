<template>
  <div class="flex flex-wrap items-center gap-2">
    <button
      @click="$emit('update:modelValue', '')"
      class="rounded-lg px-4 py-2 font-medium transition-all"
      :class="modelValue === '' ? 'bg-gray-800 text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'"
    >
      전체
    </button>
    <button
      v-for="team in teams"
      :key="team.code"
      @click="$emit('update:modelValue', team.name)"
      class="rounded-lg px-4 py-2 font-medium transition-all"
      :class="modelValue === team.name ? 'bg-primary text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'"
    >
      {{ team.name }}
    </button>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import client from '@/api/client'

defineProps({
  modelValue: {
    type: String,
    default: '',
  },
})

defineEmits(['update:modelValue'])

const teams = ref([])

onMounted(async () => {
  try {
    const response = await client.get('/accounts/teams')
    teams.value = response.data.results || response.data || []
  } catch (_error) {
    teams.value = []
  }
})
</script>
