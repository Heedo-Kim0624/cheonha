<template>
  <div class="overflow-x-auto">
    <table class="w-full">
      <thead class="bg-bg border-b border-border">
        <tr>
          <th
            v-for="col in columns"
            :key="col.key"
            class="px-6 py-3 text-left text-xs font-semibold text-text2 uppercase tracking-wider"
            :style="{ width: col.width }"
          >
            <div class="flex items-center gap-2">
              {{ col.label }}
              <button
                v-if="col.sortable"
                @click="toggleSort(col.key)"
                class="p-1 hover:bg-white rounded transition-colors"
              >
                <span class="text-text3 text-xs">
                  {{ sortKey === col.key ? (sortOrder === 'asc' ? '↑' : '↓') : '≡' }}
                </span>
              </button>
            </div>
          </th>
        </tr>
      </thead>
      <tbody>
        <tr
          v-for="(row, idx) in sortedData"
          :key="idx"
          class="border-b border-border hover:bg-bg transition-colors"
        >
          <td
            v-for="col in columns"
            :key="col.key"
            class="px-6 py-4 text-sm text-text"
            :style="{ width: col.width }"
          >
            <slot :name="`cell-${col.key}`" :row="row" :value="row[col.key]">
              {{ row[col.key] }}
            </slot>
          </td>
        </tr>
      </tbody>
    </table>
    <div v-if="data.length === 0" class="text-center py-8 text-text3">
      데이터가 없습니다.
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'

defineProps({
  columns: {
    type: Array,
    required: true
  },
  data: {
    type: Array,
    required: true
  }
})

const sortKey = ref(null)
const sortOrder = ref('asc')

const sortedData = computed(() => {
  if (!sortKey.value) return props.data
  const sorted = [...props.data].sort((a, b) => {
    const aVal = a[sortKey.value]
    const bVal = b[sortKey.value]
    if (aVal < bVal) return sortOrder.value === 'asc' ? -1 : 1
    if (aVal > bVal) return sortOrder.value === 'asc' ? 1 : -1
    return 0
  })
  return sorted
})

const toggleSort = (key) => {
  if (sortKey.value === key) {
    sortOrder.value = sortOrder.value === 'asc' ? 'desc' : 'asc'
  } else {
    sortKey.value = key
    sortOrder.value = 'asc'
  }
}
</script>
