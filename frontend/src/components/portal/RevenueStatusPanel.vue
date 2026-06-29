<template>
  <section class="revenue-panel">
    <div class="revenue-subtabs">
      <button
        v-for="tab in tabs"
        :key="tab.key"
        type="button"
        :class="{ active: activeTab === tab.key }"
        @click="activeTab = tab.key"
      >
        {{ tab.label }}
      </button>
    </div>

    <div class="revenue-filters">
      <label>
        <span>월 선택</span>
        <input v-model="selectedMonth" type="month" />
      </label>
      <label>
        <span>업체 선택</span>
        <select v-model="selectedCompany">
          <option v-for="option in companyOptions" :key="option.code" :value="option.code">
            {{ option.name }}
          </option>
        </select>
      </label>
      <button type="button" :disabled="loading" @click="loadSales">
        {{ loading ? '조회 중' : '조회' }}
      </button>
    </div>

    <div v-if="errorMessage" class="revenue-error">
      {{ errorMessage }}
    </div>

    <template v-if="activeTab === 'monthly'">
      <div class="revenue-kpis">
        <article>
          <span>총매출</span>
          <strong>{{ formatWon(summary.total_revenue) }}</strong>
          <small :class="momClass">
            {{ monthOverMonthText }}
          </small>
        </article>
        <article>
          <span>총박스 수</span>
          <strong>{{ formatNumber(summary.total_boxes) }}박스</strong>
          <small>박스당 {{ formatWon(boxRate) }}</small>
        </article>
        <article>
          <span>일평균 매출</span>
          <strong>{{ formatWon(summary.average_daily_revenue) }}</strong>
          <small>{{ elapsedDayCount }}일 기준</small>
        </article>
      </div>

      <div class="revenue-table-card">
        <div class="card-head">
          <h3>업체별 월별 매출</h3>
          <span>{{ selectedMonth }}</span>
        </div>
        <table>
          <thead>
            <tr>
              <th>업체</th>
              <th class="right">박스 수</th>
              <th class="right">매출</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in monthlyRows" :key="row.company_code">
              <td>
                <strong>{{ row.company_name }}</strong>
                <small>{{ row.company_code }}</small>
              </td>
              <td class="right">{{ formatNumber(row.boxes) }}</td>
              <td class="right font-bold">{{ formatWon(row.revenue) }}</td>
            </tr>
            <tr v-if="!monthlyRows.length">
              <td colspan="3" class="empty-cell">선택한 조건의 매출 데이터가 없습니다.</td>
            </tr>
          </tbody>
        </table>
      </div>
    </template>

    <template v-else-if="activeTab === 'daily'">
      <div class="calendar-card">
        <div class="card-head">
          <h3>업체별 일별 매출</h3>
          <span>{{ selectedMonth }}</span>
        </div>
        <div class="calendar-weekdays">
          <span v-for="day in weekdays" :key="day">{{ day }}</span>
        </div>
        <div class="sales-calendar">
          <div v-for="blank in leadingBlankCount" :key="`blank-${blank}`" class="calendar-cell blank"></div>
          <button
            v-for="day in dailyRows"
            :key="day.date"
            type="button"
            class="calendar-cell"
            :class="{ weekend: !day.is_business_day, active: day.revenue > 0 }"
          >
            <span class="day-number">{{ day.day }}</span>
            <strong>{{ formatCompactWon(day.revenue) }}</strong>
            <small>{{ formatNumber(day.boxes) }}박스</small>
          </button>
        </div>
      </div>
    </template>

    <template v-else>
      <div class="revenue-kpis">
        <article>
          <span>예상 매출</span>
          <strong>{{ formatWon(expected.expected_monthly_revenue) }}</strong>
          <small>일평균 매출을 월 전체 날짜 수로 단순 확장</small>
        </article>
        <article>
          <span>일평균 매출</span>
          <strong>{{ formatWon(expected.average_daily_revenue) }}</strong>
          <small>{{ expected.basis_text || `${elapsedDayCount}일 기준` }}</small>
        </article>
        <article>
          <span>월 전체 일수</span>
          <strong>{{ formatNumber(monthDayCount) }}일</strong>
          <small>{{ selectedMonth }} 기준</small>
        </article>
      </div>

      <div class="expected-card">
        <h3>예상매출 산식</h3>
        <p>
          {{ formatWon(expected.average_daily_revenue) }}
          × {{ formatNumber(monthDayCount) }}일
          = <strong>{{ formatWon(expected.expected_monthly_revenue) }}</strong>
        </p>
      </div>
    </template>
  </section>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { fetchSalesOverview } from '@/api/dashboard'

const props = defineProps({
  companyCode: {
    type: String,
    default: '',
  },
})

const tabs = [
  { key: 'monthly', label: '업체별 월별 매출' },
  { key: 'daily', label: '업체별 일별 매출' },
  { key: 'expected', label: '업체별 예상매출' },
]
const weekdays = ['월', '화', '수', '목', '금', '토', '일']

const activeTab = ref('monthly')
const selectedMonth = ref(toMonthInput(new Date()))
const selectedCompany = ref('all')
const loading = ref(false)
const errorMessage = ref('')
const boxRate = ref(40)
const companyOptions = ref([{ code: 'all', name: '전체' }])
const summary = ref({
  total_revenue: 0,
  previous_month_revenue: 0,
  month_over_month_percent: null,
  total_boxes: 0,
  average_daily_revenue: 0,
  business_days_elapsed: 0,
  business_days_in_month: 0,
  calendar_days_elapsed: 0,
  calendar_days_in_month: 0,
})
const monthlyRows = ref([])
const dailyRows = ref([])
const expected = ref({
  average_daily_revenue: 0,
  business_days_in_month: 0,
  calendar_days_elapsed: 0,
  calendar_days_in_month: 0,
  expected_monthly_revenue: 0,
  basis_text: '',
})

const leadingBlankCount = computed(() => {
  const first = dailyRows.value[0]
  return first ? Number(first.weekday || 0) : 0
})

const elapsedDayCount = computed(() => (
  summary.value.calendar_days_elapsed
  ?? summary.value.business_days_elapsed
  ?? 0
))

const monthDayCount = computed(() => (
  expected.value.calendar_days_in_month
  ?? expected.value.business_days_in_month
  ?? summary.value.calendar_days_in_month
  ?? summary.value.business_days_in_month
  ?? 0
))

const monthOverMonthText = computed(() => {
  const value = summary.value.month_over_month_percent
  if (value === null || value === undefined) return '전월 데이터 없음'
  const sign = value > 0 ? '+' : ''
  return `전월대비 ${sign}${value}%`
})

const momClass = computed(() => {
  const value = Number(summary.value.month_over_month_percent)
  if (!Number.isFinite(value)) return ''
  if (value > 0) return 'positive'
  if (value < 0) return 'negative'
  return ''
})

function toMonthInput(date) {
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}`
}

function formatNumber(value) {
  return Number(value || 0).toLocaleString()
}

function formatWon(value) {
  return `${formatNumber(Math.round(Number(value || 0)))}원`
}

function formatCompactWon(value) {
  const amount = Number(value || 0)
  if (!amount) return '0원'
  if (Math.abs(amount) >= 10000) {
    const man = amount / 10000
    return `${Number.isInteger(man) ? man.toFixed(0) : man.toFixed(1)}만`
  }
  return `${formatNumber(amount)}원`
}

async function loadSales() {
  loading.value = true
  errorMessage.value = ''
  try {
    const response = await fetchSalesOverview({
      month: selectedMonth.value,
      company_code: selectedCompany.value,
    })
    const payload = response.data || {}
    boxRate.value = Number(payload.box_rate || 40)
    companyOptions.value = payload.company_options?.length
      ? payload.company_options
      : [{ code: 'all', name: '전체' }]
    summary.value = {
      ...summary.value,
      ...(payload.summary || {}),
    }
    monthlyRows.value = payload.monthly_by_company || []
    dailyRows.value = payload.daily_sales || []
    expected.value = {
      ...expected.value,
      ...(payload.expected || {}),
    }
    if (!companyOptions.value.some((item) => item.code === selectedCompany.value)) {
      selectedCompany.value = 'all'
    }
  } catch (error) {
    errorMessage.value = error.response?.data?.detail || '매출 현황을 불러오지 못했습니다.'
    summary.value = {
      total_revenue: 0,
      previous_month_revenue: 0,
      month_over_month_percent: null,
      total_boxes: 0,
      average_daily_revenue: 0,
      business_days_elapsed: 0,
      business_days_in_month: 0,
      calendar_days_elapsed: 0,
      calendar_days_in_month: 0,
    }
    monthlyRows.value = []
    dailyRows.value = []
  } finally {
    loading.value = false
  }
}

watch([selectedMonth, selectedCompany], loadSales)
watch(() => props.companyCode, () => {
  selectedCompany.value = 'all'
  void loadSales()
})

onMounted(loadSales)
</script>

<style scoped>
.revenue-panel {
  display: flex;
  flex-direction: column;
  gap: 16px;
  min-width: 0;
}

.revenue-subtabs,
.revenue-filters {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 10px;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  background: #ffffff;
  padding: 14px 16px;
}

.revenue-subtabs button,
.revenue-filters button {
  border-radius: 8px;
  border: 1px solid #dbe3ec;
  background: #ffffff;
  color: #334155;
  padding: 9px 13px;
  font-size: 13px;
  font-weight: 800;
}

.revenue-subtabs button.active,
.revenue-filters button {
  border-color: #84cc16;
  background: #84cc16;
  color: #111827;
}

.revenue-filters label {
  display: flex;
  min-width: 190px;
  flex-direction: column;
  gap: 5px;
}

.revenue-filters span {
  font-size: 12px;
  font-weight: 800;
  color: #64748b;
}

.revenue-filters input,
.revenue-filters select {
  height: 40px;
  border: 1px solid #d1d5db;
  border-radius: 8px;
  background: #ffffff;
  padding: 0 11px;
  outline: none;
}

.revenue-error {
  border: 1px solid #fecaca;
  border-radius: 8px;
  background: #fef2f2;
  padding: 12px 14px;
  color: #b91c1c;
  font-size: 13px;
  font-weight: 700;
}

.revenue-kpis {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 12px;
}

.revenue-kpis article,
.revenue-table-card,
.calendar-card,
.expected-card {
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  background: #ffffff;
}

.revenue-kpis article {
  padding: 18px;
}

.revenue-kpis span {
  display: block;
  font-size: 12px;
  font-weight: 800;
  color: #64748b;
}

.revenue-kpis strong {
  display: block;
  margin-top: 7px;
  font-size: 26px;
  line-height: 1.1;
  color: #0f172a;
}

.revenue-kpis small {
  display: block;
  margin-top: 7px;
  color: #64748b;
  font-size: 12px;
  font-weight: 700;
}

.revenue-kpis small.positive {
  color: #15803d;
}

.revenue-kpis small.negative {
  color: #dc2626;
}

.card-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  border-bottom: 1px solid #e2e8f0;
  padding: 14px 16px;
}

.card-head h3 {
  font-size: 16px;
  font-weight: 900;
  color: #0f172a;
}

.card-head span {
  color: #64748b;
  font-size: 12px;
  font-weight: 800;
}

table {
  width: 100%;
  border-collapse: collapse;
  font-size: 14px;
}

th,
td {
  border-bottom: 1px solid #edf2f7;
  padding: 12px 16px;
  text-align: left;
  vertical-align: middle;
}

th {
  background: #f8fafc;
  color: #64748b;
  font-size: 12px;
  font-weight: 900;
}

td strong {
  display: block;
  color: #0f172a;
}

td small {
  display: block;
  margin-top: 3px;
  color: #94a3b8;
  font-size: 11px;
  font-weight: 700;
}

.right {
  text-align: right;
}

.font-bold {
  font-weight: 900;
}

.empty-cell {
  padding: 28px 16px;
  text-align: center;
  color: #94a3b8;
}

.calendar-weekdays,
.sales-calendar {
  display: grid;
  grid-template-columns: repeat(7, minmax(0, 1fr));
}

.calendar-weekdays {
  border-bottom: 1px solid #e2e8f0;
  background: #f8fafc;
}

.calendar-weekdays span {
  padding: 10px 6px;
  text-align: center;
  color: #64748b;
  font-size: 12px;
  font-weight: 900;
}

.sales-calendar {
  padding: 10px;
  gap: 8px;
}

.calendar-cell {
  min-height: 94px;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  background: #ffffff;
  padding: 10px;
  text-align: left;
}

.calendar-cell.blank {
  visibility: hidden;
}

.calendar-cell.weekend {
  background: #f8fafc;
}

.calendar-cell.active {
  border-color: #84cc16;
  background: #f7fee7;
}

.day-number {
  display: block;
  color: #64748b;
  font-size: 12px;
  font-weight: 900;
}

.calendar-cell strong {
  display: block;
  margin-top: 10px;
  color: #0f172a;
  font-size: 16px;
  line-height: 1.1;
}

.calendar-cell small {
  display: block;
  margin-top: 6px;
  color: #64748b;
  font-size: 12px;
  font-weight: 800;
}

.expected-card {
  padding: 18px;
}

.expected-card h3 {
  font-size: 16px;
  font-weight: 900;
  color: #0f172a;
}

.expected-card p {
  margin-top: 8px;
  color: #475569;
  font-size: 15px;
  font-weight: 700;
}

@media (max-width: 760px) {
  .revenue-filters label {
    min-width: 100%;
  }

  .calendar-cell {
    min-height: 82px;
    padding: 8px;
  }
}
</style>
