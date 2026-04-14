<template>
  <div class="flex items-center gap-2 flex-wrap">
    <button @click="$emit('update:modelValue', '')"
      class="px-4 py-2 rounded-lg font-medium transition-all"
      :class="modelValue === '' ? 'bg-gray-800 text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'">
      전체
    </button>
    <button v-for="t in teams" :key="t.code" @click="$emit('update:modelValue', t.name)"
      class="px-4 py-2 rounded-lg font-medium transition-all"
      :class="modelValue === t.name ? 'bg-primary text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'">
      {{ t.name }}
    </button>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import client from '@/api/client'

defineProps({ modelValue: { type: String, default: '' } })
defineEmits(['update:modelValue'])

const teams = ref([])
onMounted(async () => {
  try {
    const r = await client.get('/accounts/teams')
    teams.value = r.data.results || r.data || []
  } catch (e) {}
})
</script>
