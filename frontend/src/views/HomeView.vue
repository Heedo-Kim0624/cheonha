<template>
  <AppLayout>
    <div class="space-y-6">
      <!-- Header + Filter -->
      <div class="flex items-center justify-between">
        <div class="bg-gradient-to-r from-gray-800 to-gray-700 p-6 rounded-xl text-white flex-1 mr-4">
          <h2 class="text-2xl font-bold mb-1">{{ greeting }}, {{ userName }}님!</h2>
          <p class="text-gray-300">천하운수 정산관리 시스템</p>
        </div>
        <select v-model="selectedTeam" @change="fetchData"
          class="px-4 py-3 border border-gray-300 rounded-lg focus:border-primary outline-none bg-white min-w-[140px]">
          <option value="">전체</option>
          <option v-for="t in teamList" :key="t.id" :value="t.code">{{ t.name }}</option>
        </select>
      </div>

      <!-- Workflow -->
      <div class="bg-white rounded-xl p-6 border border-gray-200">
        <h3 class="text-lg font-bold text-text mb-5">업무 프로세스</h3>
        <div class="flex items-center justify-between">
          <div v-for="(step, idx) in workflowSteps" :key="idx" class="flex items-center" :class="idx < 3 ? 'flex-1' : ''">
            <RouterLink :to="step.link" class="flex items-center gap-3 p-3 rounded-lg hover:bg-gray-50 cursor-pointer">
              <div class="w-10 h-10 rounded-full flex items-center justify-center font-bold" :class="step.color">{{ idx + 1 }}</div>
              <div>
                <p class="font-medium text-text">{{ step.title }}</p>
                <p class="text-gray-400">{{ step.description }}</p>
              </div>
            </RouterLink>
            <div v-if="idx < 3" class="flex-1 flex items-center justify-center px-2">
              <div class="w-8 h-0.5 bg-gray-200 rounded"></div>
              <span class="text-gray-300 mx-1">&#8250;</span>
              <div class="w-8 h-0.5 bg-gray-200 rounded"></div>
            </div>
          </div>
        </div>
      </div>

      <!-- KPI -->
      <div class="grid grid-cols-4 gap-4">
        <div v-for="kpi in kpiCards" :key="kpi.label" class="p-5 rounded-xl border" :class="kpi.bgClass">
          <p class="mb-2" :class="kpi.labelClass">{{ kpi.label }}</p>
          <p class="text-xl font-bold" :class="kpi.valueClass">{{ formatCurrency(kpi.value) }}원</p>
        </div>
      </div>

      <!-- 최근 정산 -->
      <div class="bg-white rounded-xl p-6 border border-gray-200">
        <h3 class="text-lg font-bold text-text mb-4">최근 정산</h3>
        <div v-if="recentSettlements.length === 0" class="text-center py-8 text-gray-400">정산 내역이 없습니다.</div>
        <div v-else class="space-y-3">
          <div v-for="s in recentSettlements" :key="s.id"
            class="flex items-center justify-between py-3 border-b border-gray-100 last:border-0">
            <div>
              <span class="font-bold text-text">{{ s.period_start }}</span>
              <span class="text-gray-400 ml-3">{{ s.team_name }}</span>
            </div>
            <div class="flex gap-6">
              <span class="text-blue-600">수신 {{ formatCurrency(Number(s.total_receive)) }}원</span>
              <span class="font-bold" :class="Number(s.total_profit) >= 0 ? 'text-green-600' : 'text-red-600'">
                수익 {{ formatCurrency(Number(s.total_profit)) }}원
              </span>
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
import client from '@/api/client'
import { fetchKpi } from '@/api/dashboard'
import { fetchSettlements } from '@/api/settlement'

const selectedTeam = ref('')
const teamList = ref([])
const kpiRaw = ref({ total_revenue: 0, total_paid: 0, total_profit: 0 })
const recentSettlements = ref([])

const workflowSteps = [
  { title: '배차 데이터 업로드', description: '엑셀 파일 업로드', link: '/dispatch', color: 'bg-blue-100 text-blue-700' },
  { title: '특근 설정', description: '연장근무 비용 설정', link: '/dispatch', color: 'bg-orange-100 text-orange-700' },
  { title: '단가 확인', description: '팀 단가 확인', link: '/region', color: 'bg-purple-100 text-purple-700' },
  { title: '정산 처리', description: '정산 생성 및 확인', link: '/settlement', color: 'bg-green-100 text-green-700' },
]

const userName = computed(() => 'Admin')
const greeting = computed(() => {
  const h = new Date().getHours()
  return h < 12 ? '좋은 아침' : h < 18 ? '좋은 오후' : '좋은 저녁'
})

const kpiCards = computed(() => {
  const d = kpiRaw.value
  const overtime = Number(d.total_revenue || 0) - Number(d.total_paid || 0) - Number(d.total_profit || 0)
  return [
    { label: '수신합계', value: Number(d.total_revenue || 0), bgClass: 'bg-gray-800 border-gray-800', labelClass: 'text-gray-400', valueClass: 'text-white' },
    { label: '지급합계', value: Number(d.total_paid || 0), bgClass: 'bg-blue-50 border-blue-200', labelClass: 'text-blue-600', valueClass: 'text-blue-800' },
    { label: '특근비용', value: overtime, bgClass: 'bg-orange-50 border-orange-200', labelClass: 'text-orange-600', valueClass: 'text-orange-800' },
    { label: '수익', value: Number(d.total_profit || 0), bgClass: 'bg-green-50 border-green-200', labelClass: 'text-green-600', valueClass: 'text-green-800' },
  ]
})

const fetchData = async () => {
  try {
    const params = selectedTeam.value ? { team: selectedTeam.value } : {}
    const [kpiResp, settResp] = await Promise.allSettled([
      fetchKpi(),
      fetchSettlements(params)
    ])
    if (kpiResp.status === 'fulfilled') kpiRaw.value = kpiResp.value.data
    if (settResp.status === 'fulfilled') {
      let all = settResp.value.data.results || settResp.value.data || []
      if (selectedTeam.value) {
        all = all.filter(s => s.team_name === selectedTeam.value + '조')
      }
      recentSettlements.value = all.slice(0, 5)
    }
  } catch (e) {}
}

const loadTeams = async () => {
  try { const r = await client.get('/accounts/teams'); teamList.value = r.data.results || r.data || [] }
  catch (e) {}
}

onMounted(() => { loadTeams(); fetchData() })
</script>
