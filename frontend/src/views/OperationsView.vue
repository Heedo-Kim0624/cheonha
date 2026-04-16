<template>
  <AppLayout>
    <div class="space-y-6">
      <div class="flex items-center justify-between">
        <h3 class="text-xl font-bold text-text">운영 현황</h3>
        <input v-model="selectedDate" type="date"
          class="px-4 py-3 border border-gray-300 rounded-lg focus:border-primary outline-none bg-white"
          @change="loadAll" />
      </div>
      <TeamFilter v-model="selectedTeam" @update:modelValue="loadAll" />

      <!-- 박스수 그래프 -->
      <div class="bg-white rounded-xl p-6 border border-gray-200">
        <div class="flex items-center justify-between mb-4">
          <h4 class="font-bold text-text">총 박스수 추이</h4>
          <div class="flex gap-2">
            <button v-for="p in chartPeriods" :key="p.key" @click="chartPeriod = p.key; loadChart()"
              class="px-4 py-2 rounded-lg font-medium transition-all"
              :class="chartPeriod === p.key ? 'bg-primary text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'">
              {{ p.label }}
            </button>
          </div>
        </div>
        <div v-if="chartPeriod === 'custom'" class="flex items-center gap-3 mb-4">
          <input v-model="customStart" type="date" class="px-3 py-2 border border-gray-300 rounded-lg outline-none" />
          <span class="text-gray-400">~</span>
          <input v-model="customEnd" type="date" class="px-3 py-2 border border-gray-300 rounded-lg outline-none" />
          <button @click="loadChart" class="px-4 py-2 bg-primary text-white rounded-lg font-medium hover:opacity-90">조회</button>
        </div>
        <div v-if="loading" class="text-center py-8 text-gray-400">로딩 중...</div>
        <div v-else-if="chartData.length === 0" class="text-center py-8 text-gray-400">데이터가 없습니다.</div>
        <div v-else class="overflow-x-auto">
          <div class="min-w-[600px]">
            <div class="flex items-end gap-1" style="height: 200px;">
              <div v-for="(d, idx) in chartData" :key="idx" class="flex-1 flex flex-col items-center justify-end h-full">
                <span class="text-gray-600 font-bold mb-1">{{ d.boxes.toLocaleString() }}</span>
                <div class="w-full rounded-t-lg transition-all"
                  :style="{ height: (d.boxes / chartMax * 160) + 'px', minHeight: d.boxes > 0 ? '4px' : '0' }"
                  :class="d.boxes > 0 ? 'bg-primary' : ''"></div>
              </div>
            </div>
            <div class="flex gap-1 mt-2">
              <div v-for="(d, idx) in chartData" :key="idx" class="flex-1 text-center text-gray-500 truncate">
                {{ d.label }}
              </div>
            </div>
          </div>
        </div>
        <div v-if="chartData.length > 0" class="mt-3 text-right text-gray-500">
          합계: <span class="font-bold text-text">{{ chartTotal.toLocaleString() }}박스</span>
        </div>
      </div>

      <div v-if="loading" class="text-center py-12 text-gray-400">
        <div class="animate-spin w-8 h-8 border-2 border-primary border-t-transparent rounded-full mx-auto mb-3"></div>
        로딩 중...
      </div>

      <div v-else-if="dailyRecords.length === 0" class="bg-white rounded-xl p-12 border border-gray-200 text-center text-gray-400">
        <p class="text-4xl mb-3">🚚</p>
        <p class="font-medium mb-1">{{ selectedDate }}의 정산 데이터가 없습니다</p>
        <p>배차표 업로드 → 정산 생성 후 표시됩니다.</p>
      </div>

      <template v-else>
        <div class="grid grid-cols-3 gap-4">
          <div class="bg-white rounded-xl p-5 border border-gray-200 text-center">
            <p class="text-gray-500 mb-1">배송원</p>
            <p class="text-2xl font-bold text-text">{{ summary.crewCount }}명</p>
          </div>
          <div class="bg-white rounded-xl p-5 border border-gray-200 text-center">
            <p class="text-gray-500 mb-1">권역</p>
            <p class="text-2xl font-bold text-text">{{ summary.regionCount }}개</p>
          </div>
          <div class="bg-white rounded-xl p-5 border border-gray-200 text-center">
            <p class="text-gray-500 mb-1">총 박스</p>
            <p class="text-2xl font-bold text-primary-dark">{{ summary.totalBoxes.toLocaleString() }}박스</p>
          </div>
        </div>

        <div class="bg-white rounded-xl border border-gray-200 overflow-hidden">
          <table class="w-full">
            <thead class="bg-gray-50 border-b border-gray-200">
              <tr>
                <th class="text-left px-5 py-3 font-semibold text-gray-600">배송원</th>
                <th class="text-left px-5 py-3 font-semibold text-gray-600">조</th>
                <th class="text-left px-5 py-3 font-semibold text-gray-600">권역</th>
                <th class="text-right px-5 py-3 font-semibold text-gray-600">박스수</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="row in crewSummary" :key="row.key" class="border-b border-gray-100 hover:bg-gray-50">
                <td class="px-5 py-4 font-bold text-text">{{ row.name }}</td>
                <td class="px-5 py-4">
                  <span v-if="row.teamName" class="px-2 py-0.5 bg-primary-light text-primary-dark rounded font-medium">{{ row.teamName }}</span>
                </td>
                <td class="px-5 py-4">
                  <div class="flex flex-wrap gap-1">
                    <span v-for="r in row.regions" :key="r"
                      class="px-2 py-0.5 bg-primary-light text-primary-dark rounded font-medium">{{ r }}</span>
                  </div>
                </td>
                <td class="px-5 py-4 text-right font-bold text-lg">{{ row.boxes.toLocaleString() }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </template>
    </div>
  </AppLayout>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import AppLayout from '@/components/common/AppLayout.vue'
import TeamFilter from '@/components/common/TeamFilter.vue'
import { fetchSettlements } from '@/api/settlement'

const today = new Date().toISOString().substring(0, 10)
const selectedDate = ref(today)
const selectedTeam = ref('')
const loading = ref(false)
const allSettlements = ref([])  // 모든 정산 + details

const chartPeriod = ref('1w')
const chartPeriods = [
  { key: '1d', label: '1일' },
  { key: '1w', label: '1주일' },
  { key: '1m', label: '1달' },
  { key: 'custom', label: '사용자 지정' },
]
const customStart = ref('')
const customEnd = ref('')
const chartData = ref([])
const chartTotal = computed(() => chartData.value.reduce((s, d) => s + d.boxes, 0))
const chartMax = computed(() => Math.max(1, ...chartData.value.map(d => d.boxes)))

// 선택된 날짜 + 조의 detail 집계
const dailyRecords = computed(() => {
  const records = []
  for (const s of allSettlements.value) {
    if (s.period_start !== selectedDate.value) continue
    if (selectedTeam.value && s.team_name !== selectedTeam.value) continue
    for (const d of (s.details || [])) {
      if (!d.boxes) continue
      records.push({
        name: d.crew_member_name || d.crew_member_code || '',
        teamName: s.team_name || '',
        region: d.region || '',
        boxes: d.boxes || 0,
      })
    }
  }
  return records
})

const summary = computed(() => {
  const crews = new Set()
  const regions = new Set()
  let totalBoxes = 0
  for (const r of dailyRecords.value) {
    if (r.name) crews.add(`${r.name}|${r.teamName}`)
    if (r.region) regions.add(r.region)
    totalBoxes += r.boxes
  }
  return { crewCount: crews.size, regionCount: regions.size, totalBoxes }
})

const crewSummary = computed(() => {
  const map = {}
  for (const r of dailyRecords.value) {
    if (!r.name) continue
    const key = `${r.name}|${r.teamName}`
    if (!map[key]) {
      map[key] = { key, name: r.name, teamName: r.teamName, regions: new Set(), boxes: 0 }
    }
    if (r.region) map[key].regions.add(r.region)
    map[key].boxes += r.boxes
  }
  return Object.values(map)
    .map(c => ({ ...c, regions: Array.from(c.regions) }))
    .sort((a, b) => b.boxes - a.boxes)
})

function getDateRange() {
  const end = new Date(selectedDate.value || today)
  let start
  if (chartPeriod.value === '1d') start = new Date(end)
  else if (chartPeriod.value === '1w') { start = new Date(end); start.setDate(start.getDate() - 6) }
  else if (chartPeriod.value === '1m') { start = new Date(end); start.setDate(start.getDate() - 29) }
  else {
    start = customStart.value ? new Date(customStart.value) : new Date(end)
    const customEndDate = customEnd.value ? new Date(customEnd.value) : end
    const maxStart = new Date(customEndDate)
    maxStart.setFullYear(maxStart.getFullYear() - 1)
    if (start < maxStart) start = maxStart
    return { start, end: customEndDate }
  }
  return { start, end }
}

const loadChart = () => {
  const { start, end } = getDateRange()
  const dateMap = {}
  const d = new Date(start)
  while (d <= end) {
    dateMap[d.toISOString().substring(0, 10)] = 0
    d.setDate(d.getDate() + 1)
  }
  const startStr = start.toISOString().substring(0, 10)
  const endStr = end.toISOString().substring(0, 10)

  for (const s of allSettlements.value) {
    if (!s.period_start || s.period_start < startStr || s.period_start > endStr) continue
    if (selectedTeam.value && s.team_name !== selectedTeam.value) continue
    const sum = (s.details || []).reduce((acc, d) => acc + (d.boxes || 0), 0)
    if (s.period_start in dateMap) dateMap[s.period_start] += sum
  }

  chartData.value = Object.entries(dateMap)
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([date, boxes]) => {
      const d = new Date(date)
      return { date, boxes, label: `${d.getMonth() + 1}/${d.getDate()}` }
    })
}

const loadAll = async () => {
  loading.value = true
  try {
    const r = await fetchSettlements()
    allSettlements.value = r.data.results || r.data || []
    loadChart()
  } catch (e) { allSettlements.value = [] }
  finally { loading.value = false }
}

onMounted(loadAll)
</script>
