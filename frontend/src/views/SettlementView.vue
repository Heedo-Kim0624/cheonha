<template>
  <AppLayout>
    <div class="space-y-6">
      <div class="bg-white rounded-xl p-6 border border-gray-200">
        <div class="flex items-center justify-between mb-5">
          <h3 class="text-lg font-bold text-text">정산 내역</h3>
          <div class="flex items-center gap-3">
            <select v-model="selectedTeam"
              class="px-4 py-3 border border-gray-300 rounded-lg focus:border-primary outline-none bg-white min-w-[140px]">
              <option value="">전체</option>
              <option v-for="t in teamList" :key="t.id" :value="t.name">{{ t.name }}</option>
            </select>
            <RouterLink to="/dispatch"
              class="px-4 py-2 bg-primary text-white rounded-lg font-medium hover:opacity-90">
              배차 업로드로 정산 생성
            </RouterLink>
          </div>
        </div>

        <div v-if="loading" class="text-center py-12 text-gray-400">
          <div class="animate-spin w-8 h-8 border-2 border-primary border-t-transparent rounded-full mx-auto mb-3"></div>
          로딩 중...
        </div>

        <div v-else-if="filteredSettlements.length === 0" class="text-center py-12 text-gray-400">
          <p class="text-4xl mb-3">&#128203;</p>
          <p class="font-medium mb-1">정산 내역이 없습니다</p>
        </div>

        <div v-else class="space-y-4">
          <div v-for="settlement in filteredSettlements" :key="settlement.id"
            class="border border-gray-200 rounded-xl overflow-hidden hover:shadow-md transition-shadow">
            <div class="p-5 cursor-pointer" @click="toggleDetail(settlement.id)">
              <div class="flex items-center justify-between mb-4">
                <div class="flex items-center gap-3">
                  <div class="w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center">
                    <span class="text-blue-700 font-bold">{{ settlement.period_start ? settlement.period_start.substring(5, 10) : '-' }}</span>
                  </div>
                  <div>
                    <p class="font-bold text-text">{{ settlement.period_start }}</p>
                    <p class="text-gray-400">{{ settlement.team_name || '전체' }}</p>
                  </div>
                </div>
                <span class="text-gray-400">{{ expandedId === settlement.id ? '&#9650;' : '&#9660;' }}</span>
              </div>
              <div class="grid grid-cols-4 gap-4">
                <div class="p-3 bg-blue-50 rounded-lg">
                  <p class="text-blue-500">수신합계</p>
                  <p class="font-bold text-blue-800">{{ formatCurrency(Number(settlement.total_receive)) }}원</p>
                </div>
                <div class="p-3 bg-orange-50 rounded-lg">
                  <p class="text-orange-500">지급합계</p>
                  <p class="font-bold text-orange-800">{{ formatCurrency(Number(settlement.total_pay)) }}원</p>
                </div>
                <div class="p-3 bg-amber-50 rounded-lg">
                  <p class="text-amber-500">조정비용(특근 등)</p>
                  <p class="font-bold text-amber-800">{{ formatCurrency(Number(settlement.total_overtime)) }}원</p>
                </div>
                <div class="p-3 rounded-lg" :class="Number(settlement.total_profit) >= 0 ? 'bg-green-50' : 'bg-red-50'">
                  <p :class="Number(settlement.total_profit) >= 0 ? 'text-green-500' : 'text-red-500'">수익</p>
                  <p class="font-bold" :class="Number(settlement.total_profit) >= 0 ? 'text-green-800' : 'text-red-800'">
                    {{ formatCurrency(Number(settlement.total_profit)) }}원</p>
                </div>
              </div>
            </div>

            <!-- 상세 -->
            <div v-if="expandedId === settlement.id" class="border-t border-gray-200 bg-gray-50">
              <div v-if="loadingDetails" class="text-center py-6 text-gray-400">상세 로딩 중...</div>
              <div v-else-if="uploadGroups.length === 0" class="text-center py-6 text-gray-400">상세 내역이 없습니다.</div>
              <div v-else class="p-5 space-y-4">
                <div v-for="ug in uploadGroups" :key="ug.uploadId" class="border border-gray-200 rounded-xl overflow-hidden bg-white">
                  <div class="px-5 py-3 bg-blue-50 border-b border-blue-100 flex items-center justify-between">
                    <div class="flex items-center gap-3">
                      <span class="text-blue-700 font-bold">{{ ug.filename || '배차파일' }}</span>
                      <span class="text-blue-500">{{ formatTime(ug.uploadTime) }}</span>
                    </div>
                    <div class="flex items-center gap-4 text-blue-600">
                      <span>수신 {{ formatCurrency(ug.totalReceive) }}원</span>
                      <span>지급 {{ formatCurrency(ug.totalPay) }}원</span>
                      <span class="font-bold">수익 {{ formatCurrency(ug.totalProfit) }}원</span>
                    </div>
                  </div>
                  <table class="w-full">
                    <thead class="bg-gray-50 border-b border-gray-200">
                      <tr>
                        <th class="text-left px-4 py-2 font-semibold text-gray-600">배송원</th>
                        <th class="text-left px-4 py-2 font-semibold text-gray-600">권역</th>
                        <th class="text-right px-4 py-2 font-semibold text-gray-600">박스</th>
                        <th class="text-right px-4 py-2 font-semibold text-blue-600">수신</th>
                        <th class="text-right px-4 py-2 font-semibold text-orange-600">지급</th>
                        <th class="text-right px-4 py-2 font-semibold text-amber-600">조정비용</th>
                        <th class="text-right px-4 py-2 font-semibold text-green-600">수익</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr v-for="crew in ug.crewList" :key="crew.name"
                        class="border-b border-gray-100 hover:bg-gray-50 cursor-pointer"
                        @click.stop="openCrewPopup(crew, ug)">
                        <td class="px-4 py-3 font-bold text-primary-dark underline">{{ crew.name }}</td>
                        <td class="px-4 py-3">
                          <div class="flex flex-wrap gap-1">
                            <span v-for="r in crew.regions" :key="r"
                              class="px-2 py-0.5 bg-primary-light text-primary-dark rounded font-medium">{{ r }}</span>
                          </div>
                        </td>
                        <td class="px-4 py-3 text-right font-bold">{{ crew.totalBoxes }}</td>
                        <td class="px-4 py-3 text-right text-blue-700 font-medium">{{ formatCurrency(crew.totalReceive) }}원</td>
                        <td class="px-4 py-3 text-right text-orange-700 font-medium">{{ formatCurrency(crew.totalPay) }}원</td>
                        <td class="px-4 py-3 text-right text-amber-700">
                          <input type="number" :value="crew.totalOvertime" min="0"
                            class="w-24 px-2 py-1 border border-amber-300 rounded text-right bg-amber-50 focus:border-amber-400 outline-none"
                            @click.stop
                            @change="updateAdjustment(crew, $event)" />
                        </td>
                        <td class="px-4 py-3 text-right font-bold"
                          :class="crew.totalProfit >= 0 ? 'text-green-600' : 'text-red-600'">
                          {{ formatCurrency(crew.totalProfit) }}원
                        </td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 배송원 개인 정산 팝업 -->
      <div v-if="crewPopup" class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50" @click.self="crewPopup = null">
        <div class="bg-white rounded-xl w-full max-w-3xl max-h-[85vh] overflow-hidden flex flex-col">
          <div class="px-6 py-4 border-b border-gray-200">
            <div class="flex items-center justify-between mb-3">
              <h3 class="text-xl font-bold text-text">{{ crewPopup.name }}</h3>
              <button @click="crewPopup = null" class="text-gray-400 hover:text-gray-600 text-2xl">&times;</button>
            </div>
            <!-- 월 선택 -->
            <div class="flex items-center gap-3">
              <input v-model="popupMonth" type="month"
                class="px-4 py-2 border border-gray-300 rounded-lg focus:border-primary outline-none bg-white" />
              <p class="text-orange-600 font-bold text-lg ml-auto">
                총 지급액: {{ formatCurrency(popupFilteredTotals.pay + popupFilteredTotals.overtime) }}원
              </p>
            </div>
          </div>
          <div class="p-6 overflow-y-auto flex-1">
            <div v-if="crewPopup.loading" class="text-center py-8 text-gray-400">로딩 중...</div>
            <table v-else-if="popupFilteredRows.length > 0" class="w-full">
              <thead class="bg-gray-50 border-b border-gray-200 sticky top-0">
                <tr>
                  <th class="text-left px-4 py-2 font-semibold text-gray-600">날짜</th>
                  <th class="text-left px-4 py-2 font-semibold text-gray-600">권역</th>
                  <th class="text-right px-4 py-2 font-semibold text-gray-600">박스</th>
                  <th class="text-right px-4 py-2 font-semibold text-orange-600">지급</th>
                  <th class="text-right px-4 py-2 font-semibold text-amber-600">조정비용(특근 등)</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(row, idx) in popupFilteredRows" :key="idx" class="border-b border-gray-100">
                  <td class="px-4 py-3">{{ row.date }}</td>
                  <td class="px-4 py-3">{{ row.regions }}</td>
                  <td class="px-4 py-3 text-right font-bold">{{ row.boxes }}</td>
                  <td class="px-4 py-3 text-right text-orange-700 font-medium">{{ formatCurrency(row.pay) }}원</td>
                  <td class="px-4 py-3 text-right text-amber-700">{{ row.overtime > 0 ? formatCurrency(row.overtime) + '원' : '-' }}</td>
                </tr>
              </tbody>
              <tfoot class="bg-gray-50 font-bold sticky bottom-0">
                <tr>
                  <td class="px-4 py-3" colspan="2">합계 ({{ popupFilteredRows.length }}건)</td>
                  <td class="px-4 py-3 text-right">{{ popupFilteredTotals.boxes }}</td>
                  <td class="px-4 py-3 text-right text-orange-700">{{ formatCurrency(popupFilteredTotals.pay) }}원</td>
                  <td class="px-4 py-3 text-right text-amber-700">{{ popupFilteredTotals.overtime > 0 ? formatCurrency(popupFilteredTotals.overtime) + '원' : '-' }}</td>
                </tr>
              </tfoot>
            </table>
            <div v-else class="text-center py-8 text-gray-400">해당 월의 데이터가 없습니다.</div>
          </div>
        </div>
      </div>
    </div>
  </AppLayout>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { formatCurrency } from '@/utils/format'
import AppLayout from '@/components/common/AppLayout.vue'
import { fetchSettlements, getSettlementDetails } from '@/api/settlement'
import client from '@/api/client'

const settlements = ref([])
const loading = ref(true)
const expandedId = ref(null)
const rawDetails = ref([])
const loadingDetails = ref(false)
const selectedTeam = ref('')
const teamList = ref([])
const crewPopup = ref(null)
const popupMonth = ref(new Date().toISOString().substring(0, 7))

const statusText = (s) => ({ 'DRAFT': '작성중', 'CONFIRMED': '확정', 'PAID': '지급완료' }[s] || s)
const formatTime = (dt) => {
  if (!dt) return ''
  const d = new Date(dt)
  return `${d.getHours()}시 ${String(d.getMinutes()).padStart(2, '0')}분`
}

const filteredSettlements = computed(() => {
  if (!selectedTeam.value) return settlements.value
  return settlements.value.filter(s => s.team_name === selectedTeam.value)
})

const uploadGroups = computed(() => {
  const ugMap = {}
  for (const d of rawDetails.value) {
    const uid = d.dispatch_upload || 'unknown'
    if (!ugMap[uid]) {
      ugMap[uid] = {
        uploadId: uid, filename: d.upload_filename || '배차파일',
        uploadTime: d.upload_time || null, crewMap: {},
        totalReceive: 0, totalPay: 0, totalOvertime: 0, totalProfit: 0,
      }
    }
    const ug = ugMap[uid]
    const name = d.crew_member_name || d.crew_member_code || '미지정'
    if (!ug.crewMap[name]) {
      ug.crewMap[name] = { name, regions: new Set(), totalBoxes: 0, totalReceive: 0, totalPay: 0, totalOvertime: 0, totalProfit: 0, detailIds: [] }
    }
    const cm = ug.crewMap[name]
    if (d.region) cm.regions.add(d.region)
    cm.totalBoxes += d.boxes || 0
    cm.totalReceive += Number(d.receive_amount || 0)
    cm.totalPay += Number(d.pay_amount || 0)
    cm.totalOvertime += Number(d.overtime_cost || 0)
    cm.totalProfit += Number(d.profit || 0)
    cm.detailIds.push(d.id)
    ug.totalReceive += Number(d.receive_amount || 0)
    ug.totalPay += Number(d.pay_amount || 0)
    ug.totalOvertime += Number(d.overtime_cost || 0)
    ug.totalProfit += Number(d.profit || 0)
  }
  return Object.values(ugMap).map(ug => ({
    ...ug,
    crewList: Object.values(ug.crewMap).map(c => ({ ...c, regions: Array.from(c.regions) })).sort((a, b) => b.totalReceive - a.totalReceive)
  })).sort((a, b) => (a.uploadTime || '') > (b.uploadTime || '') ? 1 : -1)
})

const openCrewPopup = async (crew, ug) => {
  crewPopup.value = { ...crew, allRows: [], loading: true }

  // 전체 정산에서 이 배송원의 모든 detail 가져오기
  const allRows = []
  for (const s of settlements.value) {
    try {
      const resp = await getSettlementDetails(s.id)
      const details = resp.data.results || resp.data || []
      const myDetails = details.filter(d => (d.crew_member_name || d.crew_member_code) === crew.name)

      // 업로드별 합산
      const uploadMap = {}
      for (const d of myDetails) {
        const uid = d.dispatch_upload || 'unknown'
        if (!uploadMap[uid]) {
          uploadMap[uid] = { date: d.dispatch_date || s.period_start || '-', regions: new Set(), boxes: 0, pay: 0, overtime: 0 }
        }
        if (d.region) uploadMap[uid].regions.add(d.region)
        uploadMap[uid].boxes += d.boxes || 0
        uploadMap[uid].pay += Number(d.pay_amount || 0)
        uploadMap[uid].overtime += Number(d.overtime_cost || 0)
      }
      for (const r of Object.values(uploadMap)) {
        allRows.push({ ...r, regions: Array.from(r.regions).join(', ') })
      }
    } catch (e) {}
  }

  allRows.sort((a, b) => (a.date > b.date ? 1 : -1))
  crewPopup.value = { ...crew, allRows, loading: false }
}

const popupFilteredRows = computed(() => {
  if (!crewPopup.value?.allRows) return []
  if (!popupMonth.value) return crewPopup.value.allRows
  return crewPopup.value.allRows.filter(r => r.date && r.date.startsWith(popupMonth.value))
})

const popupFilteredTotals = computed(() => {
  const t = { boxes: 0, pay: 0, overtime: 0 }
  for (const r of popupFilteredRows.value) {
    t.boxes += r.boxes || 0
    t.pay += r.pay || 0
    t.overtime += r.overtime || 0
  }
  return t
})

const updateAdjustment = async (crew, event) => {
  const newCost = Number(event.target.value) || 0
  try {
    // 첫 번째 detail에 조정비용, 나머지는 0
    for (let i = 0; i < crew.detailIds.length; i++) {
      const cost = i === 0 ? newCost : 0
      await client.patch(`/settlement/details/${crew.detailIds[i]}`, {
        overtime_cost: cost,
        profit: undefined  // 서버에서 재계산
      })
    }
    // settlement 합계 재계산 요청
    if (expandedId.value) {
      await client.post(`/settlement/settlements/${expandedId.value}/recalc/`)
    }
  } catch (e) { console.error('조정비용 업데이트 실패:', e) }
  // 리로드
  if (expandedId.value) {
    const r = await getSettlementDetails(expandedId.value)
    rawDetails.value = r.data.results || r.data || []
  }
  loadSettlements()
}

const toggleDetail = async (id) => {
  if (expandedId.value === id) { expandedId.value = null; return }
  expandedId.value = id; loadingDetails.value = true
  try { const r = await getSettlementDetails(id); rawDetails.value = r.data.results || r.data || [] }
  catch (e) { rawDetails.value = [] }
  finally { loadingDetails.value = false }
}

const loadTeams = async () => {
  try { const r = await client.get('/accounts/teams'); teamList.value = r.data.results || r.data || [] }
  catch (e) {}
}

const loadSettlements = async () => {
  loading.value = true
  try { const r = await fetchSettlements(); settlements.value = r.data.results || r.data || [] }
  catch (e) { settlements.value = [] }
  finally { loading.value = false }
}

onMounted(() => { loadSettlements(); loadTeams() })
</script>
