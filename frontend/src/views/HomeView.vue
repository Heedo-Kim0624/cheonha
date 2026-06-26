<template>
  <AppLayout>
    <div class="space-y-6">
      <div class="rounded-2xl bg-gradient-to-r from-gray-800 to-gray-700 p-6 text-white">
        <div class="flex flex-col gap-4 xl:flex-row xl:items-end xl:justify-between">
          <div>
            <h2 class="mb-1 text-2xl font-bold">{{ greeting }}, {{ userName }}</h2>
            <p class="text-sm text-gray-300">
              CLEVER {{ companyApp.displayName }} 정산관리 대시보드
            </p>
          </div>
          <div class="grid gap-3 rounded-xl border border-white/10 bg-white/5 p-4 sm:grid-cols-[auto,1fr] sm:items-center">
            <span class="text-xs font-semibold uppercase tracking-wide text-gray-300">조회 범위</span>
            <div class="flex flex-wrap items-center gap-2">
              <button
                v-for="preset in rangePresets"
                :key="preset.value"
                type="button"
                class="rounded-lg px-3 py-2 text-sm font-medium transition-colors"
                :class="rangeMode === preset.value ? 'bg-[#f4f7d6] text-gray-900' : 'bg-white/10 text-white hover:bg-white/15'"
                @click="applyRangePreset(preset.value)"
              >
                {{ preset.label }}
              </button>
              <div v-if="rangeMode === 'custom'" class="flex flex-wrap items-center gap-2">
                <input
                  v-model="rangeStart"
                  type="date"
                  class="rounded-lg border border-white/15 bg-white/10 px-3 py-2 text-sm text-white outline-none [color-scheme:dark]"
                />
                <span class="text-xs text-gray-300">~</span>
                <input
                  v-model="rangeEnd"
                  type="date"
                  class="rounded-lg border border-white/15 bg-white/10 px-3 py-2 text-sm text-white outline-none [color-scheme:dark]"
                />
              </div>
            </div>
            <span class="text-xs font-semibold uppercase tracking-wide text-gray-300">적용 기간</span>
            <p class="text-sm font-medium text-white">{{ rangeLabel }}</p>
          </div>
        </div>
      </div>

      <div class="rounded-2xl border border-gray-200 bg-white p-5">
        <div class="flex flex-col gap-4 xl:flex-row xl:items-end xl:justify-between">
          <div class="space-y-3">
            <div>
              <h3 class="text-lg font-bold text-text">조회 조건</h3>
              <p class="mt-1 text-sm text-gray-500">
                팀과 기간을 바꾸면 대시보드 수치가 다시 계산됩니다.
              </p>
            </div>
            <TeamFilter v-model="selectedTeam" />
          </div>
          <div class="grid gap-3 rounded-xl bg-gray-50 px-4 py-3 sm:grid-cols-3">
            <div>
              <p class="text-xs font-semibold uppercase tracking-wide text-gray-400">정산 건수</p>
              <p class="mt-1 text-lg font-bold text-text">{{ settlementCount }}건</p>
            </div>
            <div>
              <p class="text-xs font-semibold uppercase tracking-wide text-gray-400">조회 조</p>
              <p class="mt-1 text-lg font-bold text-text">{{ selectedTeam || '전체' }}</p>
            </div>
            <div>
              <p class="text-xs font-semibold uppercase tracking-wide text-gray-400">최근 기준일</p>
              <p class="mt-1 text-lg font-bold text-text">{{ latestSettlementDate }}</p>
            </div>
          </div>
        </div>
      </div>

      <div class="grid gap-4 md:grid-cols-2 xl:grid-cols-5">
        <button
          v-for="kpi in kpiCards"
          :key="kpi.key"
          type="button"
          class="rounded-2xl border p-5 text-left transition hover:-translate-y-0.5 hover:shadow-md"
          :class="kpi.bgClass"
          @click="openKpiModal(kpi)"
        >
          <p class="mb-2 text-sm font-medium" :class="kpi.labelClass">{{ kpi.label }}</p>
          <p class="text-2xl font-bold tracking-tight" :class="kpi.valueClass">
            {{ formatCurrency(kpi.value) }}원
          </p>
        </button>
      </div>

      <div class="rounded-2xl border border-gray-200 bg-white p-6">
        <div class="mb-4 flex items-center justify-between">
          <div>
            <h3 class="text-lg font-bold text-text">최근 정산</h3>
            <p class="text-sm text-gray-500">
              현재 조회 조건 기준으로 최근 정산 3일치를 보여줍니다.
            </p>
          </div>
        </div>

        <div
          v-if="recentSettlements.length === 0"
          class="rounded-xl bg-gray-50 py-10 text-center text-sm text-gray-400"
        >
          조건에 맞는 정산 이력이 없습니다.
        </div>

        <div v-else class="space-y-3">
          <div
            v-for="settlement in recentSettlements"
            :key="settlement.id"
            class="flex flex-col gap-3 rounded-xl border border-gray-100 px-4 py-4 lg:flex-row lg:items-center lg:justify-between"
          >
            <div class="min-w-0">
              <div class="flex flex-wrap items-center gap-2">
                <p class="text-base font-bold text-text">{{ settlement.team_name }}</p>
                <span class="rounded-full bg-gray-100 px-2.5 py-1 text-xs font-medium text-gray-500">
                  {{ settlement.period_start }} ~ {{ settlement.period_end }}
                </span>
              </div>
            </div>
            <div class="grid gap-3 text-sm sm:grid-cols-2 xl:grid-cols-5">
              <div>
                <p class="text-xs font-semibold uppercase tracking-wide text-gray-400">전체 수신</p>
                <p class="mt-1 font-bold text-blue-700">
                  {{ formatCurrency(settlementDashboardTotalReceive(settlement)) }}원
                </p>
              </div>
              <div>
                <p class="text-xs font-semibold uppercase tracking-wide text-gray-400">정규 지급</p>
                <p class="mt-1 font-bold text-indigo-700">
                  {{ formatCurrency(settlementDashboardRegularPay(settlement)) }}원
                </p>
              </div>
              <div>
                <p class="text-xs font-semibold uppercase tracking-wide text-gray-400">용차 지급</p>
                <p class="mt-1 font-bold text-fuchsia-700">
                  {{ formatCurrency(settlementDashboardYongchaPay(settlement)) }}원
                </p>
              </div>
              <div>
                <p class="text-xs font-semibold uppercase tracking-wide text-gray-400">정규 용차 지급</p>
                <p class="mt-1 font-bold text-purple-700">
                  {{ formatCurrency(settlementDashboardRegularYongchaPay(settlement)) }}원
                </p>
              </div>
              <div>
                <p class="text-xs font-semibold uppercase tracking-wide text-gray-400">수익</p>
                <p
                  class="mt-1 font-bold"
                  :class="settlementDashboardProfit(settlement) >= 0 ? 'text-green-700' : 'text-red-600'"
                >
                  {{ formatCurrency(settlementDashboardProfit(settlement)) }}원
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div class="rounded-2xl border border-gray-200 bg-white p-6">
        <div class="mb-4 flex flex-col gap-3 xl:flex-row xl:items-center xl:justify-between">
          <div>
            <h3 class="text-lg font-bold text-text">조별 배송원 목록</h3>
            <p class="text-sm text-gray-500">
              조를 선택하고 이름을 누르면 하단에 월별 정산 캘린더가 표시됩니다.
            </p>
          </div>
          <div class="flex flex-wrap gap-2">
            <button
              v-for="team in homeCrewTeams"
              :key="team.key"
              type="button"
              class="rounded-lg border px-4 py-2 text-sm font-extrabold transition"
              :class="activeCrewTeam === team.key ? 'border-gray-900 bg-gray-900 text-white' : 'border-gray-200 bg-white text-gray-700 hover:bg-gray-50'"
              @click="selectHomeCrewTeam(team.key)"
            >
              {{ team.name }}
            </button>
          </div>
        </div>

        <div v-if="homeCrewLoading" class="rounded-xl bg-gray-50 py-10 text-center text-sm font-semibold text-gray-500">
          배송원 목록을 불러오는 중입니다.
        </div>
        <div v-else-if="homeCrewRows.length === 0" class="rounded-xl bg-gray-50 py-10 text-center text-sm text-gray-400">
          등록된 배송원이 없습니다.
        </div>
        <template v-else>
          <div class="overflow-hidden rounded-xl border border-gray-200">
            <div class="grid grid-cols-2 bg-gray-50 text-center text-sm font-extrabold text-gray-700">
              <div class="border-r border-gray-200 px-4 py-3">정규</div>
              <div class="px-4 py-3">용차</div>
            </div>
            <div class="grid grid-cols-2 divide-x divide-gray-200">
              <div class="min-h-[160px] divide-y divide-gray-100">
                <button
                  v-for="member in pagedHomeRegularCrewRows"
                  :key="`home-regular-${member.id}`"
                  type="button"
                  class="flex w-full items-center justify-between gap-3 px-4 py-2.5 text-left hover:bg-gray-50"
                  :class="selectedHomeCrew?.id === member.id ? 'bg-blue-50' : ''"
                  @click="selectHomeCrew(member)"
                >
                  <span class="min-w-0 break-keep font-bold text-text">{{ member.name }}</span>
                  <span class="shrink-0 rounded-full bg-gray-100 px-2 py-0.5 text-[11px] font-bold text-gray-500">{{ member.team_name || '-' }}</span>
                </button>
                <div v-if="homeRegularCrewRows.length === 0" class="px-4 py-10 text-center text-sm text-gray-400">정규 배송원이 없습니다.</div>
              </div>
              <div class="min-h-[160px] divide-y divide-gray-100">
                <button
                  v-for="member in pagedHomeYongchaCrewRows"
                  :key="`home-yongcha-${member.id}`"
                  type="button"
                  class="flex w-full items-center justify-between gap-3 px-4 py-2.5 text-left hover:bg-gray-50"
                  :class="selectedHomeCrew?.id === member.id ? 'bg-red-50' : ''"
                  @click="selectHomeCrew(member)"
                >
                  <span class="min-w-0 break-keep font-bold text-text">{{ member.name }}</span>
                  <span class="shrink-0 rounded-full bg-red-50 px-2 py-0.5 text-[11px] font-bold text-red-600">{{ member.team_name || '-' }}</span>
                </button>
                <div v-if="homeYongchaCrewRows.length === 0" class="px-4 py-10 text-center text-sm text-gray-400">용차 배송원이 없습니다.</div>
              </div>
            </div>
          </div>

          <div
            v-if="homeCrewTotalPages > 1"
            class="mt-3 flex flex-col gap-2 rounded-xl bg-gray-50 px-4 py-3 sm:flex-row sm:items-center sm:justify-between"
          >
            <p class="text-sm font-semibold text-gray-500">
              {{ activeCrewTeam || '전체' }} 배송원 {{ homeCrewPage }}/{{ homeCrewTotalPages }}페이지 · 5명씩 표시
            </p>
            <div class="flex items-center gap-2">
              <button
                type="button"
                class="rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm font-bold text-gray-600 hover:bg-gray-50 disabled:opacity-40"
                :disabled="homeCrewPage <= 1"
                @click="setHomeCrewPage(homeCrewPage - 1)"
              >
                이전
              </button>
              <button
                v-for="page in homeCrewVisiblePages"
                :key="`home-crew-page-${page}`"
                type="button"
                class="rounded-lg px-3 py-2 text-sm font-extrabold"
                :class="homeCrewPage === page ? 'bg-gray-900 text-white' : 'border border-gray-200 bg-white text-gray-700 hover:bg-gray-50'"
                @click="setHomeCrewPage(page)"
              >
                {{ page }}
              </button>
              <button
                type="button"
                class="rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm font-bold text-gray-600 hover:bg-gray-50 disabled:opacity-40"
                :disabled="homeCrewPage >= homeCrewTotalPages"
                @click="setHomeCrewPage(homeCrewPage + 1)"
              >
                다음
              </button>
            </div>
          </div>

          <div v-if="selectedHomeCrew" ref="homeCrewCalendarRef" class="mt-5">
            <CrewSettlementCalendarModal
              embedded
              :crew="selectedHomeCrew"
              :month="homeSettlementMonth"
              @saved="handleHomeCalendarSaved"
            />
          </div>
        </template>
      </div>

      <div
        v-if="kpiModalOpen && activeKpi"
        class="fixed inset-0 z-50 flex items-center justify-center bg-black/45 p-4"
        @click.self="closeKpiModal"
      >
        <div class="flex max-h-[90vh] w-full max-w-6xl flex-col overflow-hidden rounded-2xl bg-white shadow-2xl">
          <div class="flex items-start justify-between gap-4 border-b border-gray-200 px-6 py-5">
            <div>
              <p class="text-sm font-semibold text-gray-500">{{ rangeLabel }}</p>
              <h3 class="mt-1 text-2xl font-extrabold text-text">{{ activeKpi.label }} 일별 상세</h3>
              <p class="mt-1 text-sm text-gray-500">날짜를 클릭하면 회차별 기사 상세를 확인할 수 있습니다.</p>
            </div>
            <button
              type="button"
              class="rounded-lg border border-gray-200 px-4 py-2 font-semibold text-gray-600 hover:bg-gray-50"
              @click="closeKpiModal"
            >
              닫기
            </button>
          </div>

          <div class="grid min-h-0 flex-1 lg:grid-cols-[320px_minmax(0,1fr)]">
            <div class="min-h-0 overflow-y-auto border-r border-gray-100 bg-gray-50 p-4">
              <div
                v-if="dailyBreakdown.length === 0"
                class="rounded-xl bg-white py-10 text-center text-sm text-gray-400"
              >
                조건에 맞는 일별 내역이 없습니다.
              </div>
              <template v-else>
                <button
                  v-for="row in dailyBreakdown"
                  :key="`${activeKpi.key}-${row.date}`"
                  type="button"
                  class="mb-2 flex w-full items-center justify-between gap-3 rounded-xl border px-4 py-3 text-left transition"
                  :class="selectedDetailDate === row.date ? 'border-gray-900 bg-white shadow-sm' : 'border-gray-100 bg-white hover:border-gray-300'"
                  @click="selectDailyDetail(row)"
                >
                  <span class="font-bold text-text">{{ row.date }}</span>
                  <span class="font-extrabold" :class="activeKpi.detailClass || activeKpi.valueClass">
                    {{ formatCurrency(row[activeKpi.detailField] || 0) }}원
                  </span>
                </button>
              </template>
            </div>

            <div class="min-h-0 overflow-y-auto p-5">
              <div v-if="!selectedDetailDate" class="flex h-full min-h-[320px] items-center justify-center rounded-xl bg-gray-50 text-gray-400">
                왼쪽에서 날짜를 선택하세요.
              </div>
              <div v-else-if="dailyDetailLoading" class="flex h-full min-h-[320px] items-center justify-center rounded-xl bg-gray-50 text-gray-500">
                상세를 불러오는 중입니다.
              </div>
              <div v-else-if="dailyDetailError" class="rounded-xl border border-red-100 bg-red-50 p-5 text-red-600">
                {{ dailyDetailError }}
              </div>
              <div v-else class="space-y-5">
                <div class="flex flex-col gap-3 rounded-xl border border-gray-100 bg-gray-50 p-4 sm:flex-row sm:items-center sm:justify-between">
                  <div>
                    <p class="text-sm font-semibold text-gray-500">{{ selectedDetailDate }}</p>
                    <h4 class="text-xl font-extrabold text-text">회차별 상세</h4>
                  </div>
                  <div class="grid grid-cols-2 gap-3 text-sm sm:grid-cols-3">
                    <div>
                      <p class="text-gray-400">가구</p>
                      <p class="font-bold text-text">{{ formatNumber(dailyDetail?.totals?.households) }}</p>
                    </div>
                    <div>
                      <p class="text-gray-400">박스</p>
                      <p class="font-bold text-text">{{ formatNumber(dailyDetail?.totals?.boxes) }}</p>
                    </div>
                    <div>
                      <p class="text-gray-400">{{ activeMetricLabel }}</p>
                      <p class="font-bold" :class="activeMetricAmountClass">
                        {{ formatCurrency(dailyDetail?.totals?.metric_amount || 0) }}원
                      </p>
                    </div>
                  </div>
                </div>

                <div
                  v-for="round in dailyDetailRounds"
                  :key="round.round_label"
                  class="overflow-hidden rounded-xl border border-gray-200"
                >
                  <div class="flex flex-col gap-2 border-b border-gray-100 bg-gray-50 px-4 py-3 sm:flex-row sm:items-center sm:justify-between">
                    <h5 class="font-extrabold text-text">{{ round.round_label }}</h5>
                    <p class="text-sm text-gray-500">
                      {{ round.rows.length }}명 · 가구 {{ formatNumber(round.totals.households) }} · 박스 {{ formatNumber(round.totals.boxes) }} · {{ activeMetricLabel }} {{ formatCurrency(round.totals.metric_amount || 0) }}원
                    </p>
                  </div>
                  <div class="overflow-x-auto">
                    <table class="w-full min-w-[760px] text-sm">
                      <thead class="bg-white text-left text-xs font-bold uppercase tracking-wide text-gray-500">
                        <tr>
                          <th class="px-4 py-3">조</th>
                          <th class="px-4 py-3">배송원</th>
                          <th class="px-4 py-3">구분</th>
                          <th class="px-4 py-3">용차</th>
                          <th class="px-4 py-3">용차팀</th>
                          <th class="px-4 py-3 text-right">가구</th>
                          <th class="px-4 py-3 text-right">박스</th>
                          <th class="px-4 py-3 text-right">{{ activeMetricLabel }}</th>
                        </tr>
                      </thead>
                      <tbody class="divide-y divide-gray-100">
                        <tr v-for="row in round.rows" :key="`${round.round_label}-${row.crew_member_id}-${row.crew_name}`">
                          <td class="px-4 py-3 font-semibold text-gray-600">{{ row.team_name || '-' }}</td>
                          <td class="px-4 py-3 font-bold text-text">{{ row.crew_name }}</td>
                          <td class="px-4 py-3">{{ row.crew_type }}</td>
                          <td class="px-4 py-3" :class="row.is_yongcha ? 'font-bold text-red-600' : 'text-gray-400'">
                            {{ row.is_yongcha ? 'O' : 'X' }}
                          </td>
                          <td class="px-4 py-3">
                            <strong v-if="row.yongcha_pay_group_name" class="text-fuchsia-700">{{ row.yongcha_pay_group_name }}</strong>
                            <span v-else class="text-gray-400">-</span>
                          </td>
                          <td class="px-4 py-3 text-right font-semibold">{{ formatNumber(row.households) }}</td>
                          <td class="px-4 py-3 text-right font-semibold">{{ formatNumber(row.boxes) }}</td>
                          <td class="px-4 py-3 text-right font-semibold" :class="activeMetricAmountClass">
                            {{ formatCurrency(row.metric_amount || 0) }}원
                          </td>
                        </tr>
                      </tbody>
                    </table>
                  </div>
                </div>

                <div v-if="dailyDetailRounds.length === 0" class="rounded-xl bg-gray-50 py-10 text-center text-sm text-gray-400">
                  이 날짜의 상세 정산 내역이 없습니다.
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </AppLayout>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import AppLayout from '@/components/common/AppLayout.vue'
import TeamFilter from '@/components/common/TeamFilter.vue'
import { fetchHomeDailyDetail, fetchHomeOverview } from '@/api/dashboard'
import { fetchCrewMembers } from '@/api/crew'
import CrewSettlementCalendarModal from '@/components/settlement/CrewSettlementCalendarModal.vue'
import { useAuthStore } from '@/stores/auth'
import { formatCurrency } from '@/utils/format'
import { getCompanyAppFromRoute } from '@/utils/companyApp'

const route = useRoute()
const authStore = useAuthStore()
const companyApp = computed(() => getCompanyAppFromRoute(route))

const selectedTeam = ref('')
const overview = ref({
  settlement_count: 0,
  latest_settlement_date: '-',
  summary: {
    total_revenue: 0,
    total_paid: 0,
    total_overtime: 0,
    total_profit: 0,
    total_receive: 0,
    total_yongcha_receive: 0,
    total_yongcha_pay: 0,
    regular_yongcha_receive: 0,
    regular_yongcha_pay: 0,
  },
  daily_breakdown: [],
  recent_settlements: [],
})
const rangeMode = ref('thisMonth')
const rangeStart = ref('')
const rangeEnd = ref('')
const activeKpiKey = ref('')
const kpiModalOpen = ref(false)
const selectedDetailDate = ref('')
const dailyDetail = ref(null)
const dailyDetailLoading = ref(false)
const dailyDetailError = ref('')
const homeCrewRows = ref([])
const homeCrewLoading = ref(false)
const activeCrewTeam = ref('')
const selectedHomeCrew = ref(null)
const homeCrewCalendarRef = ref(null)
const homeCrewPage = ref(1)
const HOME_CREW_PAGE_SIZE = 5

let fetchTimer = null
let lastFetchId = 0

const rangePresets = [
  { value: 'thisMonth', label: '이번달' },
  { value: 'prevMonth', label: '저번달' },
  { value: 'custom', label: '기간선택' },
]

const userName = computed(() => {
  return (
    authStore.user?.name ||
    authStore.user?.full_name ||
    authStore.user?.username ||
    '사용자'
  )
})

const greeting = computed(() => {
  const hour = new Date().getHours()
  if (hour < 12) return '좋은 아침입니다'
  if (hour < 18) return '좋은 오후입니다'
  return '좋은 저녁입니다'
})

function formatDateInput(date) {
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

function normalizeDate(value) {
  if (!value) return null
  const parsed = new Date(`${value}T00:00:00`)
  if (Number.isNaN(parsed.getTime())) return null
  return parsed
}

function applyRangePreset(mode) {
  rangeMode.value = mode
  const today = new Date()

  if (mode === 'thisMonth') {
    const monthStart = new Date(today.getFullYear(), today.getMonth(), 1)
    rangeStart.value = formatDateInput(monthStart)
    rangeEnd.value = formatDateInput(today)
    return
  }

  if (mode === 'prevMonth') {
    const prevMonthStart = new Date(today.getFullYear(), today.getMonth() - 1, 1)
    const prevMonthEnd = new Date(today.getFullYear(), today.getMonth(), 0)
    rangeStart.value = formatDateInput(prevMonthStart)
    rangeEnd.value = formatDateInput(prevMonthEnd)
    return
  }

  if (!rangeStart.value || !rangeEnd.value) {
    rangeStart.value = formatDateInput(new Date(today.getFullYear(), today.getMonth(), 1))
    rangeEnd.value = formatDateInput(today)
  }
}

const selectedRange = computed(() => {
  const start = normalizeDate(rangeStart.value)
  const end = normalizeDate(rangeEnd.value)
  if (!start || !end) return null
  return start.getTime() <= end.getTime() ? { start, end } : { start: end, end: start }
})

const rangeLabel = computed(() => {
  if (!selectedRange.value) return '기간 미선택'
  return `${rangeStart.value} ~ ${rangeEnd.value}`
})

const settlementCount = computed(() => Number(overview.value.settlement_count || 0))
const recentSettlements = computed(() => overview.value.recent_settlements || [])
const latestSettlementDate = computed(() => overview.value.latest_settlement_date || '-')
const dailyBreakdown = computed(() => overview.value.daily_breakdown || [])
const homeCrewTeams = computed(() => {
  const map = new Map()
  homeCrewRows.value.forEach((member) => {
    const key = member.team_name || '미지정'
    if (!map.has(key)) map.set(key, { key, name: key })
  })
  return Array.from(map.values())
})
const activeHomeCrewRows = computed(() => {
  if (!activeCrewTeam.value) return homeCrewRows.value
  return homeCrewRows.value.filter((member) => (member.team_name || '미지정') === activeCrewTeam.value)
})
const homeRegularCrewRows = computed(() =>
  activeHomeCrewRows.value.filter((member) => !member.is_yongcha)
)
const homeYongchaCrewRows = computed(() =>
  activeHomeCrewRows.value.filter((member) => member.is_yongcha)
)
const homeCrewTotalPages = computed(() =>
  Math.max(
    1,
    Math.ceil(Math.max(homeRegularCrewRows.value.length, homeYongchaCrewRows.value.length) / HOME_CREW_PAGE_SIZE),
  )
)
const pagedHomeRegularCrewRows = computed(() => {
  const start = (homeCrewPage.value - 1) * HOME_CREW_PAGE_SIZE
  return homeRegularCrewRows.value.slice(start, start + HOME_CREW_PAGE_SIZE)
})
const pagedHomeYongchaCrewRows = computed(() => {
  const start = (homeCrewPage.value - 1) * HOME_CREW_PAGE_SIZE
  return homeYongchaCrewRows.value.slice(start, start + HOME_CREW_PAGE_SIZE)
})
const homeCrewVisiblePages = computed(() => {
  const pages = []
  const start = Math.max(1, homeCrewPage.value - 2)
  for (let page = start; page <= Math.min(homeCrewTotalPages.value, start + 4); page += 1) {
    pages.push(page)
  }
  return pages
})
const homeSettlementMonth = computed(() => {
  const source = rangeStart.value || new Date().toISOString().slice(0, 10)
  return source.slice(0, 7)
})

const kpiCards = computed(() => {
  const summary = overview.value.summary || {}
  return [
    {
      key: 'total_receive',
      label: '전체 수신',
      detailField: 'total_receive',
      value: Number(summary.total_receive ?? (
        Number(summary.total_revenue || 0) +
        Number(summary.total_yongcha_receive || 0) +
        Number(summary.regular_yongcha_receive || 0)
      )),
      bgClass: 'border-gray-800 bg-gray-800',
      labelClass: 'text-gray-300',
      valueClass: 'text-white',
      detailClass: 'text-gray-900',
    },
    {
      key: 'total_paid',
      label: '정규 지급',
      detailField: 'total_paid',
      value: Number(summary.total_paid || 0),
      bgClass: 'border-blue-200 bg-blue-50',
      labelClass: 'text-blue-600',
      valueClass: 'text-blue-800',
    },
    {
      key: 'total_yongcha_pay',
      label: '용차 지급',
      detailField: 'total_yongcha_pay',
      value: Number(summary.total_yongcha_pay || 0),
      bgClass: 'border-fuchsia-200 bg-fuchsia-50',
      labelClass: 'text-fuchsia-600',
      valueClass: 'text-fuchsia-800',
    },
    {
      key: 'regular_yongcha_pay',
      label: '정규 용차 지급',
      detailField: 'regular_yongcha_pay',
      value: Number(summary.regular_yongcha_pay || 0),
      bgClass: 'border-purple-200 bg-purple-50',
      labelClass: 'text-purple-600',
      valueClass: 'text-purple-800',
    },
    {
      key: 'total_profit',
      label: '수익',
      detailField: 'total_profit',
      value: Number(summary.total_profit || 0),
      bgClass: 'border-green-200 bg-green-50',
      labelClass: 'text-green-600',
      valueClass: 'text-green-800',
    },
  ]
})

const activeKpi = computed(() =>
  kpiCards.value.find((kpi) => kpi.key === activeKpiKey.value) || null
)
const activeMetricLabel = computed(() => dailyDetail.value?.metric_label || activeKpi.value?.label || '금액')
const activeMetricAmountClass = computed(() => {
  if (activeKpi.value?.key === 'total_profit') {
    return Number(dailyDetail.value?.totals?.metric_amount || 0) >= 0 ? 'text-green-700' : 'text-red-600'
  }
  return activeKpi.value?.detailClass || activeKpi.value?.valueClass || 'text-gray-900'
})
const dailyDetailRounds = computed(() => dailyDetail.value?.rounds || [])

function formatNumber(value) {
  return Number(value || 0).toLocaleString()
}

function openKpiModal(kpi) {
  activeKpiKey.value = kpi.key
  kpiModalOpen.value = true
  selectedDetailDate.value = ''
  dailyDetail.value = null
  dailyDetailError.value = ''
}

function closeKpiModal() {
  kpiModalOpen.value = false
  selectedDetailDate.value = ''
  dailyDetail.value = null
  dailyDetailError.value = ''
}

async function selectDailyDetail(row) {
  selectedDetailDate.value = row.date
  dailyDetail.value = null
  dailyDetailError.value = ''
  dailyDetailLoading.value = true
  try {
    const response = await fetchHomeDailyDetail({
      date: row.date,
      team_name: selectedTeam.value || undefined,
      metric: activeKpiKey.value || undefined,
    })
    dailyDetail.value = response.data || null
  } catch {
    dailyDetailError.value = '상세 내역을 불러오지 못했습니다.'
  } finally {
    dailyDetailLoading.value = false
  }
}

function settlementDashboardTotalReceive(settlement) {
  if (settlement.detail_total_receive !== undefined && settlement.detail_total_receive !== null) {
    return Number(settlement.detail_total_receive || 0)
  }
  return (
    Number(settlement.regular_total_receive ?? settlement.total_receive ?? 0) +
    Number(settlement.yongcha_total_receive ?? 0) +
    Number(settlement.regular_yongcha_total_receive ?? 0)
  )
}

function settlementDashboardRegularPay(settlement) {
  return Number(settlement.regular_total_pay ?? settlement.total_pay ?? 0)
}

function settlementDashboardProfit(settlement) {
  return Number(settlement.total_profit ?? 0)
}

function settlementDashboardYongchaPay(settlement) {
  return Number(settlement.yongcha_total_pay ?? 0)
}

function settlementDashboardRegularYongchaPay(settlement) {
  return Number(settlement.regular_yongcha_total_pay ?? 0)
}

async function fetchData() {
  const fetchId = ++lastFetchId
  try {
    const response = await fetchHomeOverview({
      team_name: selectedTeam.value || undefined,
      start: rangeStart.value || undefined,
      end: rangeEnd.value || undefined,
    })
    if (fetchId !== lastFetchId) return
    overview.value = response.data || overview.value
  } catch {
    if (fetchId !== lastFetchId) return
    overview.value = {
      settlement_count: 0,
      latest_settlement_date: '-',
      summary: {
        total_revenue: 0,
        total_paid: 0,
        total_overtime: 0,
        total_profit: 0,
        total_receive: 0,
        total_yongcha_receive: 0,
        total_yongcha_pay: 0,
        regular_yongcha_receive: 0,
        regular_yongcha_pay: 0,
      },
      daily_breakdown: [],
      recent_settlements: [],
    }
  }
}

async function loadHomeCrewRows() {
  homeCrewLoading.value = true
  try {
    const response = await fetchCrewMembers()
    homeCrewRows.value = Array.isArray(response.data) ? response.data : response.data?.results || []
    if (selectedTeam.value && homeCrewTeams.value.some((team) => team.key === selectedTeam.value)) {
      activeCrewTeam.value = selectedTeam.value
    }
    if (
      (!activeCrewTeam.value || !homeCrewTeams.value.some((team) => team.key === activeCrewTeam.value)) &&
      homeCrewTeams.value.length > 0
    ) {
      activeCrewTeam.value = homeCrewTeams.value[0].key
    }
    if (selectedHomeCrew.value && !homeCrewRows.value.some((member) => member.id === selectedHomeCrew.value.id)) {
      selectedHomeCrew.value = null
    }
  } catch {
    homeCrewRows.value = []
    selectedHomeCrew.value = null
  } finally {
    homeCrewLoading.value = false
  }
}

function selectHomeCrewTeam(teamKey) {
  activeCrewTeam.value = teamKey
  setHomeCrewPage(1)
  if (selectedHomeCrew.value && (selectedHomeCrew.value.team_name || '미지정') !== teamKey) {
    selectedHomeCrew.value = null
  }
}

function setHomeCrewPage(page) {
  homeCrewPage.value = Math.min(homeCrewTotalPages.value, Math.max(1, Number(page || 1)))
}

async function selectHomeCrew(member) {
  selectedHomeCrew.value = member
  await nextTick()
  const target = homeCrewCalendarRef.value
  if (!target) return

  const scroller = target.closest('main') || document.scrollingElement
  if (scroller && typeof scroller.scrollTo === 'function') {
    const scrollerRect = scroller.getBoundingClientRect()
    const targetRect = target.getBoundingClientRect()
    scroller.scrollTo({
      top: scroller.scrollTop + targetRect.top - scrollerRect.top - 16,
      behavior: 'smooth',
    })
    return
  }

  target.scrollIntoView({
    behavior: 'smooth',
    block: 'start',
  })
}

async function handleHomeCalendarSaved() {
  await fetchData()
}

function scheduleFetch() {
  if (!rangeStart.value || !rangeEnd.value) return
  if (fetchTimer) clearTimeout(fetchTimer)
  fetchTimer = setTimeout(() => {
    fetchTimer = null
    void fetchData()
  }, 120)
}

onMounted(() => {
  applyRangePreset('thisMonth')
  void loadHomeCrewRows()
})

onBeforeUnmount(() => {
  if (fetchTimer) clearTimeout(fetchTimer)
})

watch([selectedTeam, rangeStart, rangeEnd], () => {
  if (selectedTeam.value && homeCrewTeams.value.some((team) => team.key === selectedTeam.value)) {
    selectHomeCrewTeam(selectedTeam.value)
  }
  if (kpiModalOpen.value) {
    selectedDetailDate.value = ''
    dailyDetail.value = null
    dailyDetailError.value = ''
  }
  scheduleFetch()
}, { immediate: true })

watch(homeCrewTotalPages, () => {
  setHomeCrewPage(homeCrewPage.value)
})
</script>
