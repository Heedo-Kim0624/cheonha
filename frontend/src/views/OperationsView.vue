<template>
  <AppLayout>
    <div class="space-y-6">
      <div class="flex items-center justify-between">
        <h3 class="text-xl font-bold text-text">운영 현황</h3>
        <input v-model="selectedDate" type="date"
          class="px-4 py-3 border border-gray-300 rounded-lg focus:border-primary outline-none bg-white"
          @change="loadData" />
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
        <!-- 요약 카드 -->
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

        <!-- 배송원별 테이블 -->
        <div class="bg-white rounded-xl border border-gray-200 overflow-hidden">
          <table class="w-full">
            <thead class="bg-gray-50 border-b border-gray-200">
              <tr>
                <th class="text-left px-5 py-3 font-semibold text-gray-600">배송원</th>
                <th class="text-left px-5 py-3 font-semibold text-gray-600">권역</th>
                <th class="text-right px-5 py-3 font-semibold text-gray-600">박스수</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="row in crewSummary" :key="row.name" class="border-b border-gray-100 hover:bg-gray-50">
                <td class="px-5 py-4 font-bold text-text">{{ row.name }}</td>
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
import client from '@/api/client'

const today = new Date().toISOString().substring(0, 10)
const selectedDate = ref(today)
const loading = ref(false)
const records = ref([])
const registeredCrew = ref(new Set())

const filteredRecords = computed(() => {
  return records.value.filter(r => r.manager_name && registeredCrew.value.has(r.manager_name))
})

const summary = computed(() => {
  const crews = new Set()
  const regions = new Set()
  let totalBoxes = 0
  for (const r of filteredRecords.value) {
    crews.add(r.manager_name)
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
    if (!map[r.manager_name]) {
      map[r.manager_name] = { name: r.manager_name, regions: new Set(), boxes: 0 }
    }
    if (r.sub_region) {
      r.sub_region.split(',').map(s => s.trim()).filter(s => s && s !== '-').forEach(s => map[r.manager_name].regions.add(s))
    }
    map[r.manager_name].boxes += r.boxes || 0
  }
  return Object.values(map)
    .map(c => ({ ...c, regions: Array.from(c.regions) }))
    .sort((a, b) => b.boxes - a.boxes)
})

const loadData = async () => {
  loading.value = true
  records.value = []
  try {
    // 등록된 배송원 목록 가져오기
    const crewResp = await client.get('/crew/members/')
    const crewList = crewResp.data.results || crewResp.data || []
    registeredCrew.value = new Set(crewList.filter(c => !c.is_new).map(c => c.code))

    // 해당 날짜의 업로드 찾기
    const uploadsResp = await client.get('/dispatch/uploads/')
    const uploads = (uploadsResp.data.results || uploadsResp.data || [])
      .filter(u => u.dispatch_date === selectedDate.value)

    // 각 업로드의 레코드 합치기
    const allRecords = []
    for (const u of uploads) {
      try {
        const recResp = await client.get('/dispatch/records/', { params: { upload_id: u.id } })
        const recs = recResp.data.results || recResp.data || []
        allRecords.push(...recs.filter(r => r.manager_name && r.boxes > 0))
      } catch (e) {}
    }
    records.value = allRecords
  } catch (e) {}
  finally { loading.value = false }
}

onMounted(loadData)
</script>
