<template>
  <AppLayout>
    <div class="space-y-6">
      <div class="flex items-center justify-between">
        <h3 class="text-xl font-bold text-text">운영 현황</h3>
        <input v-model="selectedDate" type="date"
          class="px-4 py-3 border border-gray-300 rounded-lg focus:border-primary outline-none bg-white"
          @change="loadData" />
      </div>
      <TeamFilter v-model="selectedTeam" @update:modelValue="loadChart" />

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
        <!-- 사용자 지정 기간 -->
        <div v-if="chartPeriod === 'custom'" class="flex items-center gap-3 mb-4">
          <input v-model="customStart" type="date" class="px-3 py-2 border border-gray-300 rounded-lg outline-none" />
          <span class="text-gray-400">~</span>
          <input v-model="customEnd" type="date" class="px-3 py-2 border border-gray-300 rounded-lg outline-none" />
          <button @click="loadChart" class="px-4 py-2 bg-primary text-white rounded-lg font-medium hover:opacity-90">조회</button>
        </div>
        <!-- 그래프 -->
        <div v-if="chartLoading" class="text-center py-8 text-gray-400">로딩 중...</div>
        <div v-else-if="chartData.length === 0" class="text-center py-8 text-gray-400">데이터가 없습니다.</div>
        <div v-else class="overflow-x-auto">
          <div class="min-w-[600px]">
            <!-- Y축 라벨 + 바 차트 -->
            <div class="flex items-end gap-1" style="height: 200px;">
              <div v-for="(d, idx) in chartData" :key="idx" class="flex-1 flex flex-col items-center justify-end h-full">
                <span class="text-gray-600 font-bold mb-1">{{ d.boxes.toLocaleString() }}</span>
                <div class="w-full rounded-t-lg transition-all"
                  :style="{ height: (d.boxes / chartMax * 160) + 'px', minHeight: d.boxes > 0 ? '4px' : '0' }"
                  :class="d.boxes > 0 ? 'bg-primary' : ''"></div>
              </div>
            </div>
            <!-- X축 라벨 -->
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

      <div v-else-if="filteredRecords.length === 0" class="bg-white rounded-xl p-12 border border-gray-200 text-center text-gray-400">
        <p class="text-4xl mb-3">&#128666;</p>
        <p class="font-medium mb-1">{{ selectedDate }}의 배차 데이터가 없습니다</p>
        <p>배차표를 먼저 업로드하세요.</p>
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
              <tr v-for="row in crewSummary" :key="row.name + row.teamName" class="border-b border-gray-100 hover:bg-gray-50">
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
import client from '@/api/client'

const today = new Date().toISOString().substring(0, 10)
const selectedDate = ref(today)
const selectedTeam = ref('')
const loading = ref(false)
const records = ref([])
const registeredCrew = ref(new Set())

// 차트
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
const chartLoading = ref(false)
const chartTotal = computed(() => chartData.value.reduce((s, d) => s + d.boxes, 0))
const chartMax = computed(() => Math.max(1, ...chartData.value.map(d => d.boxes)))

function getDateRange() {
  const end = new Date(selectedDate.value || today)
  let start
  if (chartPeriod.value === '1d') {
    start = new Date(end)
  } else if (chartPeriod.value === '1w') {
    start = new Date(end)
    start.setDate(start.getDate() - 6)
  } else if (chartPeriod.value === '1m') {
    start = new Date(end)
    start.setDate(start.getDate() - 29)
  } else {
    start = customStart.value ? new Date(customStart.value) : new Date(end)
    const customEndDate = customEnd.value ? new Date(customEnd.value) : end
    // 최대 1년
    const maxStart = new Date(customEndDate)
    maxStart.setFullYear(maxStart.getFullYear() - 1)
    if (start < maxStart) start = maxStart
    return { start, end: customEndDate }
  }
  return { start, end }
}

function formatLabel(dateStr) {
  const d = new Date(dateStr)
  return `${d.getMonth() + 1}/${d.getDate()}`
}

const loadChart = async () => {
  chartLoading.value = true
  chartData.value = []
  try {
    const { start, end } = getDateRange()
    const uploadsResp = await client.get('/dispatch/uploads/')
    const allUploads = uploadsResp.data.results || uploadsResp.data || []

    // 날짜별 박스수 집계
    const dateMap = {}
    const d = new Date(start)
    while (d <= end) {
      dateMap[d.toISOString().substring(0, 10)] = 0
      d.setDate(d.getDate() + 1)
    }

    const filteredUploads = allUploads.filter(u => {
      if (!u.dispatch_date) return false
      if (selectedTeam.value && u.team_name !== selectedTeam.value) return false
      return u.dispatch_date >= start.toISOString().substring(0, 10) && u.dispatch_date <= end.toISOString().substring(0, 10)
    })

    for (const u of filteredUploads) {
      try {
        const recResp = await client.get('/dispatch/records/', { params: { upload_id: u.id } })
        const recs = recResp.data.results || recResp.data || []
        const totalBoxes = recs.filter(r => r.manager_name && r.boxes > 0).reduce((s, r) => s + r.boxes, 0)
        if (u.dispatch_date in dateMap) {
          dateMap[u.dispatch_date] += totalBoxes
        }
      } catch (e) {}
    }

    chartData.value = Object.entries(dateMap)
      .sort(([a], [b]) => a.localeCompare(b))
      .map(([date, boxes]) => ({ date, boxes, label: formatLabel(date) }))
  } catch (e) {}
  finally { chartLoading.value = false }
}

// 기존 테이블 데이터
const filteredRecords = computed(() => {
  let list = records.value.filter(r => r.manager_name && registeredCrew.value.has(r._crewKey))
  if (selectedTeam.value) {
    list = list.filter(r => r._teamName === selectedTeam.value)
  }
  return list
})

const summary = computed(() => {
  const crews = new Set()
  const regions = new Set()
  let totalBoxes = 0
  for (const r of filteredRecords.value) {
    crews.add(r._crewKey)
    if (r.sub_region) {
      r.sub_region.split(',').map(s => s.trim()).filter(s => s && s !== '-').forEach(s => regions.add(s))
    }
    totalBoxes += r.boxes || 0
  }
  return { crewCount: crews.size, regionCount: regions.size, totalBoxes }
})

const crewSummary = computed(() => {
  const map = {}
  for (const r of filteredRecords.value) {
    const key = r._crewKey
    if (!map[key]) {
      map[key] = { name: r.manager_name, teamName: r._teamName, regions: new Set(), boxes: 0 }
    }
    if (r.sub_region) {
      r.sub_region.split(',').map(s => s.trim()).filter(s => s && s !== '-').forEach(s => map[key].regions.add(s))
    }
    map[key].boxes += r.boxes || 0
  }
  return Object.values(map)
    .map(c => ({ ...c, regions: Array.from(c.regions) }))
    .sort((a, b) => b.boxes - a.boxes)
})

const loadData = async () => {
  loading.value = true
  records.value = []
  try {
    const crewResp = await client.get('/crew/members/')
    const crewList = crewResp.data.results || crewResp.data || []
    const registered = crewList.filter(c => !c.is_new)
    const regKeys = new Set()
    for (const c of registered) {
      regKeys.add(`${c.code}|${c.team_name || ''}`)
    }
    registeredCrew.value = regKeys

    const uploadsResp = await client.get('/dispatch/uploads/')
    const uploads = (uploadsResp.data.results || uploadsResp.data || [])
      .filter(u => u.dispatch_date === selectedDate.value)

    const allRecords = []
    for (const u of uploads) {
      try {
        const recResp = await client.get('/dispatch/records/', { params: { upload_id: u.id } })
        const recs = recResp.data.results || recResp.data || []
        for (const r of recs) {
          if (r.manager_name && r.boxes > 0) {
            r._teamName = u.team_name || ''
            r._crewKey = `${r.manager_name}|${r._teamName}`
            allRecords.push(r)
          }
        }
      } catch (e) {}
    }
    records.value = allRecords
  } catch (e) {}
  finally { loading.value = false }
}

onMounted(() => { loadData(); loadChart() })
</script>
