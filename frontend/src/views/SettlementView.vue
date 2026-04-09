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
          <p>배차 데이터를 업로드하여 정산을 생성하세요.</p>
        </div>

        <div v-else class="space-y-4">
          <div v-for="settlement in filteredSettlements" :key="settlement.id"
            class="border border-gray-200 rounded-xl overflow-hidden hover:shadow-md transition-shadow">
            <div class="p-5 cursor-pointer" @click="toggleDetail(settlement.id)">
              <div class="flex items-center justify-between mb-4">
                <div class="flex items-center gap-3">
                  <div class="w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center">
                    <span class="text-blue-700 font-bold">
                      {{ settlement.period_start ? settlement.period_start.substring(5, 10) : '-' }}
                    </span>
                  </div>
                  <div>
                    <p class="font-bold text-text">
                      {{ settlement.period_start }}
                      <span v-if="settlement.period_start !== settlement.period_end"> ~ {{ settlement.period_end }}</span>
                    </p>
                    <p class="text-gray-400">
                      {{ settlement.team_name || '전체' }} |
                      <span class="px-1.5 py-0.5 rounded font-medium"
                        :class="settlement.status === 'CONFIRMED' ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-600'">
                        {{ statusText(settlement.status) }}
                      </span>
                    </p>
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
                  <p class="text-amber-500">특근비</p>
                  <p class="font-bold text-amber-800">{{ formatCurrency(Number(settlement.total_overtime)) }}원</p>
                </div>
                <div class="p-3 rounded-lg" :class="Number(settlement.total_profit) >= 0 ? 'bg-green-50' : 'bg-red-50'">
                  <p :class="Number(settlement.total_profit) >= 0 ? 'text-green-500' : 'text-red-500'">수익</p>
                  <p class="font-bold" :class="Number(settlement.total_profit) >= 0 ? 'text-green-800' : 'text-red-800'">
                    {{ formatCurrency(Number(settlement.total_profit)) }}원
                  </p>
                </div>
              </div>
            </div>

            <!-- 상세: 사람별 -->
            <div v-if="expandedId === settlement.id" class="border-t border-gray-200 bg-gray-50">
              <div v-if="loadingDetails" class="text-center py-6 text-gray-400">상세 로딩 중...</div>
              <div v-else-if="groupedDetails.length === 0" class="text-center py-6 text-gray-400">상세 내역이 없습니다.</div>
              <div v-else class="p-5">
                <table class="w-full">
                  <thead class="bg-gray-50 border-b border-gray-200">
                    <tr>
                      <th class="text-left px-4 py-3 font-semibold text-gray-600">배송원</th>
                      <th class="text-left px-4 py-3 font-semibold text-gray-600">권역</th>
                      <th class="text-right px-4 py-3 font-semibold text-gray-600">박스</th>
                      <th class="text-right px-4 py-3 font-semibold text-blue-600">수신</th>
                      <th class="text-right px-4 py-3 font-semibold text-orange-600">지급</th>
                      <th class="text-right px-4 py-3 font-semibold text-amber-600">특근</th>
                      <th class="text-right px-4 py-3 font-semibold text-green-600">수익</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="crew in groupedDetails" :key="crew.name" class="border-b border-gray-100 hover:bg-gray-50">
                      <td class="px-4 py-3 font-bold text-text">{{ crew.name }}</td>
                      <td class="px-4 py-3">
                        <div class="flex flex-wrap gap-1">
                          <span v-for="r in crew.regions" :key="r"
                            class="px-2 py-0.5 bg-primary-light text-primary-dark rounded font-medium">{{ r }}</span>
                        </div>
                      </td>
                      <td class="px-4 py-3 text-right font-bold">{{ crew.totalBoxes }}</td>
                      <td class="px-4 py-3 text-right text-blue-700 font-medium">{{ formatCurrency(crew.totalReceive) }}원</td>
                      <td class="px-4 py-3 text-right text-orange-700 font-medium">{{ formatCurrency(crew.totalPay) }}원</td>
                      <td class="px-4 py-3 text-right text-amber-700">{{ crew.totalOvertime > 0 ? formatCurrency(crew.totalOvertime) + '원' : '-' }}</td>
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

const statusText = (s) => ({ 'DRAFT': '작성중', 'CONFIRMED': '확정', 'PAID': '지급완료' }[s] || s)

const filteredSettlements = computed(() => {
  if (!selectedTeam.value) return settlements.value
  return settlements.value.filter(s => s.team_name === selectedTeam.value)
})

const groupedDetails = computed(() => {
  const crewMap = {}
  for (const d of rawDetails.value) {
    const name = d.crew_member_name || d.crew_member_code || '미지정'
    if (!crewMap[name]) {
      crewMap[name] = { name, regions: new Set(), totalBoxes: 0, totalReceive: 0, totalPay: 0, totalOvertime: 0, totalProfit: 0 }
    }
    if (d.region) crewMap[name].regions.add(d.region)
    crewMap[name].totalBoxes += d.boxes || 0
    crewMap[name].totalReceive += Number(d.receive_amount || 0)
    crewMap[name].totalPay += Number(d.pay_amount || 0)
    crewMap[name].totalOvertime += Number(d.overtime_cost || 0)
    crewMap[name].totalProfit += Number(d.profit || 0)
  }
  return Object.values(crewMap).map(c => ({ ...c, regions: Array.from(c.regions) })).sort((a, b) => b.totalReceive - a.totalReceive)
})

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
