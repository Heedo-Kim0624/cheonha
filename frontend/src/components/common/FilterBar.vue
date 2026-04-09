<template>
  <div class="bg-card rounded-lg p-4 border border-border flex flex-wrap gap-4 items-end">
    <!-- Date Range -->
    <div v-if="showDateRange" class="space-y-2">
      <label class="text-sm text-text2 font-medium">기간</label>
      <div class="flex gap-2">
        <input
          v-model="dateStart"
          type="date"
          class="px-3 py-2 border border-border rounded-lg text-sm"
        />
        <span class="text-text2">~</span>
        <input
          v-model="dateEnd"
          type="date"
          class="px-3 py-2 border border-border rounded-lg text-sm"
        />
      </div>
    </div>

    <!-- Dropdowns -->
    <div v-for="(filter, key) in filters" :key="key" class="space-y-2">
      <label class="text-sm text-text2 font-medium">{{ filter.label }}</label>
      <select
        v-model="selectedFilters[key]"
        @change="emitChange"
        class="px-3 py-2 border border-border rounded-lg text-sm bg-card"
      >
        <option v-for="option in filter.options" :key="option" :value="option">
          {{ option }}
        </option>
      </select>
    </div>

    <!-- Search -->
    <div v-if="showSearch" class="space-y-2 flex-1 min-w-64">
      <label class="text-sm text-text2 font-medium">검색</label>
      <div class="flex">
        <input
          v-model="searchQuery"
          type="text"
          placeholder="검색어 입력..."
          class="flex-1 px-3 py-2 border border-border rounded-lg text-sm"
          @input="emitChange"
        />
        <button class="ml-2 px-4 py-2 bg-primary text-card rounded-lg font-medium hover:opacity-90 transition">
          검색
        </button>
      </div>
    </div>

    <!-- Reset Button -->
    <button
      @click="resetFilters"
      class="px-4 py-2 border border-border rounded-lg text-sm text-text2 hover:bg-bg transition-colors"
    >
      초기화
    </button>
  </div>
</template>

<script setup>
import { ref, reactive, watch } from 'vue'

const props = defineProps({
  filters: {
    type: Object,
    default: () => ({})
  },
  showDateRange: {
    type: Boolean,
    default: false
  },
  showSearch: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['filter-change'])

const dateStart = ref('')
const dateEnd = ref('')
const searchQuery = ref('')
const selectedFilters = reactive({})

watch(
  () => props.filters,
  (newFilters) => {
    Object.keys(newFilters).forEach((key) => {
      if (!selectedFilters[key]) {
        selectedFilters[key] = newFilters[key].options?.[0] || ''
      }
    })
  },
  { immediate: true }
)

const emitChange = () => {
  emit('filter-change', {
    dateStart: dateStart.value,
    dateEnd: dateEnd.value,
    search: searchQuery.value,
    filters: { ...selectedFilters }
  })
}

const resetFilters = () => {
  dateStart.value = ''
  dateEnd.value = ''
  searchQuery.value = ''
  Object.keys(selectedFilters).forEach((key) => {
    selectedFilters[key] = props.filters[key].options?.[0] || ''
  })
  emitChange()
}
</script>
