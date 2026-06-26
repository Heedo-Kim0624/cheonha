<template>
  <div class="space-y-5" @click="clearSelectedRow">
    <section class="overflow-hidden rounded-2xl border border-slate-200 bg-white">
      <div class="flex flex-wrap items-end justify-between gap-3 border-b border-slate-200 px-5 py-4">
        <div>
          <p class="text-xs font-extrabold uppercase tracking-wide text-slate-500">CJ대한통운 ONE</p>
          <h3 class="mt-1 text-2xl font-extrabold text-slate-950">{{ monthTitle }}</h3>
        </div>
        <div class="text-right text-xs font-bold text-slate-500">
          <p>{{ periodText }}</p>
          <p>미매핑 {{ formatNumber(summaryData.unmapped_order_count) }}건 · 업로드 {{ formatNumber(summaryData.upload_count) }}건</p>
        </div>
      </div>

      <div class="grid lg:grid-cols-4">
        <button
          v-for="item in overviewItems"
          :key="item.key"
          type="button"
          class="summary-tile"
          :class="{ 'summary-tile-active': activeView === item.key }"
          @click="activeView = item.key"
        >
          <div class="flex min-h-[250px] flex-col justify-between gap-4">
            <div>
              <p class="break-keep text-sm font-extrabold text-slate-950">{{ item.title }}</p>
              <div class="mt-3 flex items-baseline gap-1">
                <span class="text-3xl font-black tracking-tight text-slate-950">{{ item.value }}</span>
                <span class="text-sm font-extrabold text-slate-500">{{ item.unit }}</span>
              </div>
              <div class="mt-2 flex flex-wrap gap-x-3 gap-y-1 text-xs font-bold text-slate-500">
                <span v-for="meta in item.meta" :key="meta">{{ meta }}</span>
              </div>
            </div>

            <div v-if="item.chart === 'donut'" class="donut-card-visual">
              <svg class="h-28 w-28 shrink-0" viewBox="0 0 120 120" role="img" :aria-label="item.title">
                <circle class="donut-track" cx="60" cy="60" r="43" pathLength="100" />
                <circle
                  v-for="segment in item.segments"
                  :key="segment.label"
                  class="donut-segment"
                  cx="60"
                  cy="60"
                  r="43"
                  pathLength="100"
                  :stroke="segment.color"
                  :stroke-dasharray="`${segment.percent} ${100 - segment.percent}`"
                  :stroke-dashoffset="-segment.offset"
                />
                <text x="60" y="58" text-anchor="middle" class="donut-main">{{ item.center }}</text>
                <text x="60" y="76" text-anchor="middle" class="donut-sub">{{ item.centerSub }}</text>
              </svg>
              <div class="donut-legend">
                <div v-for="segment in item.segments" :key="`legend-${item.key}-${segment.label}`" class="donut-legend-row">
                  <span class="donut-legend-dot" :style="{ backgroundColor: segment.color }"></span>
                  <span class="min-w-0 truncate">{{ segment.label }}</span>
                  <strong>{{ item.legendFormatter(segment.value) }}</strong>
                </div>
              </div>
            </div>

            <div v-else class="summary-facts">
              <div v-for="fact in item.facts" :key="`${item.key}-${fact.label}`" class="summary-fact-row">
                <span>{{ fact.label }}</span>
                <strong>{{ fact.value }}</strong>
              </div>
            </div>
          </div>
        </button>
      </div>
    </section>

    <section class="overflow-hidden rounded-2xl border border-slate-200 bg-white">
      <div class="flex flex-wrap items-end justify-between gap-3 border-b border-slate-200 px-5 py-4">
        <div>
          <p class="text-xs font-extrabold uppercase tracking-wide text-slate-500">{{ activeDetail.kicker }}</p>
          <h4 class="mt-1 text-xl font-extrabold text-slate-950">{{ activeDetail.title }}</h4>
        </div>
        <p class="text-2xl font-black text-slate-950">{{ activeDetail.value }}</p>
      </div>

      <div v-if="activeView === 'delivery-qty'">
        <DataTable title="일자별 배송 수량">
          <thead>
            <tr>
              <th rowspan="2">일자</th>
              <th v-for="group in serviceGroups" :key="`qty-day-head-${group.code}`" :colspan="group.columns.length * 2" class="text-center">
                {{ group.label }}
              </th>
              <th rowspan="2" class="text-right">합계</th>
            </tr>
            <tr>
              <template v-for="group in serviceGroups" :key="`qty-day-sub-${group.code}`">
                <template v-for="column in group.columns" :key="`qty-day-sub-${group.code}-${column.category_code}`">
                  <th class="text-right">{{ column.category_short_label }} 착지</th>
                  <th class="text-right">{{ column.category_short_label }} 추가</th>
                </template>
              </template>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="row in dailyRows"
              :key="`qty-${row.date}`"
              :class="{ 'selected-data-row': isSelectedRow(`qty-${row.date}`) }"
              @click.stop="selectRow(`qty-${row.date}`)"
            >
              <td>{{ formatDayLabel(row.date) }}</td>
              <template v-for="group in serviceGroups" :key="`qty-day-row-${row.date}-${group.code}`">
                <template v-for="column in group.columns" :key="`qty-day-row-${row.date}-${group.code}-${column.category_code}`">
                  <td class="text-right">{{ formatNumber(matrixValue(dayMatrixMap[row.date], column).households) }}</td>
                  <td class="text-right text-slate-500">{{ formatNumber(matrixValue(dayMatrixMap[row.date], column).extra_boxes) }}</td>
                </template>
              </template>
              <td class="text-right font-extrabold">{{ formatNumber(row.households) }}</td>
            </tr>
          </tbody>
        </DataTable>
      </div>

      <div v-else-if="activeView === 'settlement'">
        <DataTable title="일자별 ONE 정산">
          <thead>
            <tr>
              <th rowspan="2">일자</th>
              <th v-for="group in serviceGroups" :key="`amt-day-head-${group.code}`" :colspan="group.columns.length * 2" class="text-center">
                {{ group.label }}
              </th>
              <th rowspan="2" class="text-right">합계</th>
            </tr>
            <tr>
              <template v-for="group in serviceGroups" :key="`amt-day-sub-${group.code}`">
                <template v-for="column in group.columns" :key="`amt-day-sub-${group.code}-${column.category_code}`">
                  <th class="text-right">{{ column.category_short_label }}</th>
                </template>
              </template>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="row in dailyRows"
              :key="`amt-${row.date}`"
              :class="{ 'selected-data-row': isSelectedRow(`amt-${row.date}`) }"
              @click.stop="selectRow(`amt-${row.date}`)"
            >
              <td>{{ formatDayLabel(row.date) }}</td>
              <template v-for="group in serviceGroups" :key="`amt-day-row-${row.date}-${group.code}`">
                <template v-for="column in group.columns" :key="`amt-day-row-${row.date}-${group.code}-${column.category_code}`">
                  <td class="text-right">{{ formatWon(matrixValue(dayMatrixMap[row.date], column).source_base_amount) }}</td>
                  <td class="text-right text-slate-500">{{ formatWon(matrixValue(dayMatrixMap[row.date], column).source_extra_amount) }}</td>
                </template>
              </template>
              <td class="text-right font-extrabold">{{ formatWon(row.source_amount) }}</td>
            </tr>
          </tbody>
        </DataTable>
      </div>

      <div v-else-if="activeView === 'driver-qty'">
        <DataTable title="기사별 배송 총량">
          <thead>
            <tr>
              <th rowspan="2" class="w-16 text-right">순위</th>
              <th rowspan="2">기사명</th>
              <th v-for="group in serviceGroups" :key="`driver-qty-head-${group.code}`" :colspan="group.columns.length * 2" class="text-center">
                {{ group.label }}
              </th>
              <th rowspan="2" class="text-right">합계</th>
            </tr>
            <tr>
              <template v-for="group in serviceGroups" :key="`driver-qty-sub-${group.code}`">
                <template v-for="column in group.columns" :key="`driver-qty-sub-${group.code}-${column.category_code}`">
                  <th class="text-right">{{ column.category_short_label }} 착지</th>
                  <th class="text-right">{{ column.category_short_label }} 추가</th>
                </template>
              </template>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="driver in driverQuantityRows"
              :key="`driver-qty-${driver.id}`"
              :class="{ 'selected-data-row': isSelectedRow(`driver-qty-${driver.id}`) }"
              @click.stop="selectRow(`driver-qty-${driver.id}`)"
            >
              <td class="text-right text-slate-500">{{ driver.rank }}</td>
              <td class="font-extrabold text-slate-950">{{ driver.name }}</td>
              <template v-for="group in serviceGroups" :key="`driver-qty-row-${driver.id}-${group.code}`">
                <template v-for="column in group.columns" :key="`driver-qty-row-${driver.id}-${group.code}-${column.category_code}`">
                  <td class="text-right">{{ formatNumber(matrixValue(driverMatrixMap[driver.id], column).households) }}</td>
                  <td class="text-right text-slate-500">{{ formatNumber(matrixValue(driverMatrixMap[driver.id], column).extra_boxes) }}</td>
                </template>
              </template>
              <td class="text-right font-extrabold">{{ formatNumber(driver.households) }}</td>
            </tr>
          </tbody>
        </DataTable>
      </div>

      <div v-else>
        <DataTable title="기사별 정산 총량">
          <thead>
            <tr>
              <th rowspan="2" class="w-16 text-right">순위</th>
              <th rowspan="2">기사명</th>
              <th v-for="group in serviceGroups" :key="`driver-amt-head-${group.code}`" :colspan="group.columns.length" class="text-center">
                {{ group.label }}
              </th>
              <th rowspan="2" class="text-right">운송료 외</th>
              <th rowspan="2" class="text-right">지급 합계</th>
              <th rowspan="2" class="text-right">구성비</th>
            </tr>
            <tr>
              <template v-for="group in serviceGroups" :key="`driver-amt-sub-${group.code}`">
                <template v-for="column in group.columns" :key="`driver-amt-sub-${group.code}-${column.category_code}`">
                  <th class="text-right">{{ column.category_short_label }}</th>
                </template>
              </template>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="driver in driverAmountRows"
              :key="`driver-amt-${driver.id}`"
              :class="{ 'selected-data-row': isSelectedRow(`driver-amt-${driver.id}`) }"
              @click.stop="selectRow(`driver-amt-${driver.id}`)"
            >
              <td class="text-right text-slate-500">{{ driver.rank }}</td>
              <td class="font-extrabold text-slate-950">{{ driver.name }}</td>
              <template v-for="group in serviceGroups" :key="`driver-amt-row-${driver.id}-${group.code}`">
                <template v-for="column in group.columns" :key="`driver-amt-row-${driver.id}-${group.code}-${column.category_code}`">
                  <td class="text-right">{{ formatWon(matrixValue(driverMatrixMap[driver.id], column).amount) }}</td>
                </template>
              </template>
              <td class="text-right text-slate-500">{{ formatWon(driverManualTotal(driver)) }}</td>
              <td class="text-right font-extrabold">{{ formatWon(driverStatementAmount(driver)) }}</td>
              <td class="text-right">{{ percent(driverStatementAmount(driver), statementTotalAmount) }}%</td>
            </tr>
          </tbody>
        </DataTable>
      </div>
    </section>

    <section class="grid gap-5 xl:grid-cols-2">
      <DataTable title="CJ대한통운 ONE 배송 수량 기준표">
        <thead>
          <tr>
            <th rowspan="2">명칭 / 구분</th>
            <th v-for="group in serviceGroups" :key="`month-qty-head-${group.code}`" :colspan="2" class="text-center">
              {{ group.label }}
            </th>
          </tr>
          <tr>
            <template v-for="group in serviceGroups" :key="`month-qty-sub-${group.code}`">
              <th class="text-right">착지 / 건</th>
              <th class="text-right">추가박스</th>
            </template>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="category in categoryRows"
            :key="`month-qty-${category.category_code}`"
            :class="{ 'selected-data-row': isSelectedRow(`month-qty-${category.category_code}`) }"
            @click.stop="selectRow(`month-qty-${category.category_code}`)"
          >
            <td class="font-extrabold text-slate-950">{{ category.category_label }}</td>
            <template v-for="group in serviceGroups" :key="`month-qty-${category.category_code}-${group.code}`">
              <td class="text-right">{{ formatNumber(monthMatrixValue(group.code, category.category_code).households) }}</td>
              <td class="text-right text-slate-500">{{ formatNumber(monthMatrixValue(group.code, category.category_code).extra_boxes) }}</td>
            </template>
          </tr>
        </tbody>
      </DataTable>

      <DataTable title="CJ대한통운 ONE 정산 기준표">
        <thead>
          <tr>
            <th rowspan="2">명칭 / 구분</th>
            <th v-for="group in serviceGroups" :key="`month-amt-head-${group.code}`" :colspan="2" class="text-center">
              {{ group.label }}
            </th>
            <th rowspan="2" class="text-right">합계</th>
          </tr>
          <tr>
            <template v-for="group in serviceGroups" :key="`month-amt-sub-${group.code}`">
              <th class="text-right">착지 / 건</th>
              <th class="text-right">추가박스</th>
            </template>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="category in categoryRows"
            :key="`month-amt-${category.category_code}`"
            :class="{ 'selected-data-row': isSelectedRow(`month-amt-${category.category_code}`) }"
            @click.stop="selectRow(`month-amt-${category.category_code}`)"
          >
            <td class="font-extrabold text-slate-950">{{ category.category_label }}</td>
            <template v-for="group in serviceGroups" :key="`month-amt-${category.category_code}-${group.code}`">
              <td class="text-right">{{ formatWon(monthMatrixValue(group.code, category.category_code).source_base_amount) }}</td>
              <td class="text-right text-slate-500">{{ formatWon(monthMatrixValue(group.code, category.category_code).source_extra_amount) }}</td>
            </template>
            <td class="text-right font-extrabold">{{ formatWon(categoryMonthTotal(category.category_code, 'source_amount')) }}</td>
          </tr>
        </tbody>
      </DataTable>
    </section>
  </div>
</template>

<script setup>
import { computed, defineComponent, h, onBeforeUnmount, onMounted, ref } from 'vue'

const props = defineProps({
  summary: { type: Object, default: () => ({ summary: {}, by_service: [], by_day: [], by_day_service: [], by_driver_service: [] }) },
  drivers: { type: Array, default: () => [] },
  month: { type: String, default: '' },
})

const activeView = ref('delivery-qty')
const selectedRowKey = ref('')
const waveOrder = ['W12_DAY', 'N3_DAY', 'W4_DAWN']
const waveLabels = {
  W12_DAY: '1,2W_당일',
  N3_DAY: 'N3_당일',
  W4_DAWN: '4W_새벽',
}
const categoryOrder = ['SSG', 'COMMON', 'TRADERS', 'YES24']
const categoryLabels = {
  SSG: 'SSG',
  COMMON: '공동배송',
  TRADERS: '트레이더스',
  YES24: 'YES24',
}
const categoryShortLabels = {
  SSG: 'SSG',
  COMMON: '공동',
  TRADERS: '트레',
  YES24: 'YES24',
}
const statementColumns = [
  ['W12_DAY', 'SSG'],
  ['W12_DAY', 'TRADERS'],
  ['W12_DAY', 'COMMON'],
  ['W12_DAY', 'YES24'],
  ['N3_DAY', 'SSG'],
  ['N3_DAY', 'YES24'],
  ['W4_DAWN', 'SSG'],
  ['W4_DAWN', 'COMMON'],
  ['W4_DAWN', 'YES24'],
].map(([serviceCode, categoryCode]) => ({
  key: matrixKey(serviceCode, categoryCode),
  service_code: serviceCode,
  service_label: waveLabels[serviceCode] || serviceCode,
  category_code: categoryCode,
  category_label: categoryLabels[categoryCode] || categoryCode,
  category_short_label: categoryShortLabels[categoryCode] || categoryLabels[categoryCode] || categoryCode,
}))
const chartColors = ['#111827', '#64748b', '#cbd5e1', '#94a3b8']
const weekdayLabels = ['일', '월', '화', '수', '목', '금', '토']

const summaryData = computed(() => props.summary?.summary || {})
const statementTotalAmount = computed(() => Number(summaryData.value.statement_total_amount ?? summaryData.value.total_amount ?? 0))
const manualTotalAmount = computed(() => Number(summaryData.value.manual_total || 0))

const serviceRows = computed(() => [...(props.summary?.by_service || [])].sort((a, b) => {
  const serviceDiff = orderIndex(waveOrder, a.service_code) - orderIndex(waveOrder, b.service_code)
  if (serviceDiff !== 0) return serviceDiff
  const categoryDiff = orderIndex(categoryOrder, a.category_code) - orderIndex(categoryOrder, b.category_code)
  if (categoryDiff !== 0) return categoryDiff
  return String(a.category_label || '').localeCompare(String(b.category_label || ''), 'ko-KR')
}))

const serviceGroups = computed(() => waveOrder.map((code) => ({
  code,
  label: waveLabels[code] || code,
  columns: statementColumns.filter((column) => column.service_code === code),
})))

const categoryRows = computed(() => categoryOrder.map((code) => ({
  category_code: code,
  category_label: categoryLabels[code] || code,
})))

const dayMatrixMap = computed(() => buildMatrixMap(props.summary?.by_day_service || [], 'date'))
const driverMatrixMap = computed(() => buildMatrixMap(props.summary?.by_driver_service || [], 'driver_id'))
const monthMatrixMap = computed(() => {
  const map = {}
  for (const row of serviceRows.value) {
    map[matrixKey(row.service_code, row.category_code)] = normalizeMetric(row)
  }
  return map
})

const monthTitle = computed(() => {
  const [year, month] = monthParts()
  if (!year || !month) return '선택 월'
  return `${year}년 ${Number(month)}월`
})

const periodText = computed(() => {
  const [year, month] = monthParts().map(Number)
  if (!year || !month) return '집계 기준 없음'
  const end = new Date(year, month, 0)
  return `${String(year).slice(2)}-${String(month).padStart(2, '0')}-01 ~ ${String(year).slice(2)}-${String(month).padStart(2, '0')}-${String(end.getDate()).padStart(2, '0')}`
})

const waveCards = computed(() => {
  const maxHouseholds = Math.max(...waveOrder.map((code) => sum(serviceRows.value.filter((row) => row.service_code === code), 'households')), 1)
  return waveOrder.map((code) => {
    const rows = serviceRows.value.filter((row) => row.service_code === code)
    const households = sum(rows, 'households')
    const amount = sum(rows, 'source_amount')
    return {
      code,
      label: waveLabels[code] || code,
      households,
      boxes: sum(rows, 'boxes'),
      extra_boxes: sum(rows, 'extra_boxes'),
      amount,
      householdPercent: clampPercent(households, maxHouseholds),
    }
  })
})

const quantitySegments = computed(() => buildSegments(waveCards.value, 'households', 'label'))
const amountSegments = computed(() => buildSegments(waveCards.value, 'amount', 'label'))

const dailyRows = computed(() => {
  const rows = props.summary?.by_day || []
  return rows.map((row) => ({ ...row }))
})

const driverQuantityRows = computed(() => rankedDrivers('households'))
const driverAmountRows = computed(() => rankedDrivers('statement_total_amount'))
const driverQuantityBars = computed(() => topBars(driverQuantityRows.value, 'households', (value) => `${formatNumber(value)}건`))
const driverAmountBars = computed(() => topBars(driverAmountRows.value, 'statement_total_amount', formatWon))

const overviewItems = computed(() => [
  {
    key: 'delivery-qty',
    title: 'CJ대한통운 ONE 배송 수량',
    value: formatNumber(summaryData.value.households),
    unit: '건',
    meta: [`박스 ${formatNumber(summaryData.value.boxes)}`, `추가 ${formatNumber(summaryData.value.extra_boxes)}`],
    chart: 'donut',
    segments: quantitySegments.value,
    center: formatNumber(summaryData.value.households),
    centerSub: '착지',
    legendFormatter: (value) => `${formatNumber(value)}건`,
  },
  {
    key: 'settlement',
    title: 'CJ대한통운 ONE 정산',
    value: formatWon(summaryData.value.source_total_amount),
    unit: '',
    meta: [`${formatNumber(summaryData.value.driver_count)}명`, 'W1,2 / N3 / W4'],
    chart: 'donut',
    segments: amountSegments.value,
    center: 'ONE',
    centerSub: '정산',
    legendFormatter: formatWon,
  },
  {
    key: 'driver-qty',
    title: '기사별 배송 총량',
    value: formatNumber(summaryData.value.driver_count),
    unit: '명',
    meta: [`착지 ${formatNumber(summaryData.value.households)}`, `박스 ${formatNumber(summaryData.value.boxes)}`],
    chart: 'facts',
    facts: [
      { label: '총 착지', value: `${formatNumber(summaryData.value.households)}건` },
      { label: '총 박스', value: `${formatNumber(summaryData.value.boxes)}박스` },
      { label: '추가박스', value: `${formatNumber(summaryData.value.extra_boxes)}박스` },
    ],
  },
  {
    key: 'driver-amount',
    title: '기사별 정산 총량',
    value: formatWon(statementTotalAmount.value),
    unit: '',
    meta: [`상위 ${Math.min(driverAmountRows.value.length, 4)}명`, `${formatNumber(driverAmountRows.value.length)}명 전체`],
    chart: 'facts',
    facts: [
      { label: '지급 합계', value: formatWon(statementTotalAmount.value) },
      { label: '운송료 외', value: formatWon(manualTotalAmount.value) },
      { label: '기사 수', value: `${formatNumber(summaryData.value.driver_count)}명` },
      { label: '평균 지급액', value: formatWon(Math.round(statementTotalAmount.value / Math.max(Number(summaryData.value.driver_count || 0), 1))) },
    ],
  },
])

const activeDetail = computed(() => {
  const map = {
    'delivery-qty': {
      kicker: 'Delivery quantity',
      title: 'CJ대한통운 ONE 배송 수량',
      value: `${formatNumber(summaryData.value.households)}건`,
    },
    settlement: {
      kicker: 'Settlement',
      title: 'CJ대한통운 ONE 정산',
      value: formatWon(summaryData.value.source_total_amount),
    },
    'driver-qty': {
      kicker: 'Driver quantity',
      title: '기사별 배송 총량',
      value: `${formatNumber(summaryData.value.driver_count)}명`,
    },
    'driver-amount': {
      kicker: 'Driver settlement',
      title: '기사별 정산 총량',
      value: formatWon(statementTotalAmount.value),
    },
  }
  return map[activeView.value] || map['delivery-qty']
})

function selectRow(key) {
  selectedRowKey.value = key
}

function clearSelectedRow() {
  selectedRowKey.value = ''
}

function isSelectedRow(key) {
  return selectedRowKey.value === key
}

onMounted(() => {
  document.addEventListener('click', clearSelectedRow)
})

onBeforeUnmount(() => {
  document.removeEventListener('click', clearSelectedRow)
})

function matrixKey(serviceCode, categoryCode) {
  return `${serviceCode}:${categoryCode}`
}

function emptyMetric() {
  return { households: 0, boxes: 0, extra_boxes: 0, amount: 0, source_amount: 0, source_base_amount: 0, source_extra_amount: 0 }
}

function normalizeMetric(row = {}) {
  return {
    households: Number(row.households || 0),
    boxes: Number(row.boxes || 0),
    extra_boxes: Number(row.extra_boxes || 0),
    amount: Number(row.amount || 0),
    source_amount: Number(row.source_amount ?? row.amount ?? 0),
    source_base_amount: Number(row.source_base_amount ?? row.source_amount ?? row.amount ?? 0),
    source_extra_amount: Number(row.source_extra_amount || 0),
  }
}

function buildMatrixMap(rows, ownerField) {
  return rows.reduce((acc, row) => {
    const owner = row?.[ownerField]
    if (owner === undefined || owner === null || owner === '') return acc
    if (!acc[owner]) acc[owner] = {}
    acc[owner][matrixKey(row.service_code, row.category_code)] = normalizeMetric(row)
    return acc
  }, {})
}

function matrixValue(values, column) {
  return values?.[column.key] || emptyMetric()
}

function monthMatrixValue(serviceCode, categoryCode) {
  return monthMatrixMap.value[matrixKey(serviceCode, categoryCode)] || emptyMetric()
}

function categoryMonthTotal(categoryCode, field) {
  return waveOrder.reduce((total, serviceCode) => total + Number(monthMatrixValue(serviceCode, categoryCode)[field] || 0), 0)
}

function monthParts() {
  return String(props.month || props.summary?.month || '').split('-')
}

function orderIndex(order, value) {
  const index = order.indexOf(value)
  return index === -1 ? 999 : index
}

function sum(rows, field) {
  return rows.reduce((total, row) => total + Number(row[field] || 0), 0)
}

function buildSegments(rows, valueField, labelField) {
  const total = sum(rows, valueField)
  let offset = 0
  return rows
    .filter((row) => Number(row[valueField] || 0) > 0)
    .map((row, index) => {
      const percentValue = total ? (Number(row[valueField] || 0) / total) * 100 : 0
      const segment = {
        label: row[labelField],
        value: Number(row[valueField] || 0),
        percent: Math.max(0.5, percentValue),
        offset,
        color: chartColors[index % chartColors.length],
      }
      offset += percentValue
      return segment
    })
}

function rankedDrivers(field) {
  return [...props.drivers]
    .sort((a, b) => metricValue(b, field) - metricValue(a, field))
    .map((row, index) => ({ ...row, rank: index + 1 }))
}

function topBars(rows, field, formatter) {
  const maxValue = Math.max(...rows.map((row) => metricValue(row, field)), 1)
  return rows.slice(0, 8).map((row) => ({
    ...row,
    percent: clampPercent(metricValue(row, field), maxValue),
    display: formatter(metricValue(row, field)),
  }))
}

function metricValue(row, field) {
  if (field === 'statement_total_amount') return driverStatementAmount(row)
  return Number(row?.[field] || 0)
}

function driverManualTotal(driver) {
  return Number(driver?.manual_total || 0)
}

function driverStatementAmount(driver) {
  return Number(driver?.statement_total_amount ?? driver?.amount ?? 0)
}

function clampPercent(value, total) {
  const denominator = Number(total || 0)
  if (!denominator) return 0
  return Math.max(2, Math.min(100, Math.round((Number(value || 0) / denominator) * 100)))
}

function formatNumber(value) {
  return Number(value || 0).toLocaleString('ko-KR')
}

function formatWon(value) {
  return `${formatNumber(value)}원`
}

function percent(value, total) {
  const denominator = Number(total || 0)
  if (!denominator) return '0.0'
  return ((Number(value || 0) / denominator) * 100).toFixed(1)
}

function formatDayLabel(value) {
  if (!value) return '-'
  const date = new Date(`${value}T00:00:00`)
  if (Number.isNaN(date.getTime())) return value
  return `${String(date.getMonth() + 1).padStart(2, '0')}.${String(date.getDate()).padStart(2, '0')} ${weekdayLabels[date.getDay()]}`
}

const DataTable = defineComponent({
  props: { title: String },
  setup(componentProps, { slots }) {
    return () => h('div', { class: 'overflow-hidden bg-white' }, [
      h('div', { class: 'px-5 pb-0 pt-3 text-sm font-extrabold text-slate-950' }, componentProps.title),
      h('div', { class: 'max-h-[560px] overflow-y-auto overflow-x-auto' }, [
        h('table', {
          class: 'one-dashboard-table w-full',
          style: { borderCollapse: 'separate', borderSpacing: '0' },
        }, slots.default?.()),
      ]),
    ])
  },
})
</script>

<style scoped>
.summary-tile {
  display: block;
  min-width: 0;
  border-right: 1px solid #e2e8f0;
  border-bottom: 1px solid #e2e8f0;
  padding: 18px;
  text-align: left;
  transition: background-color 0.15s ease, box-shadow 0.15s ease;
}

.summary-tile:nth-child(4n) {
  border-right: 0;
}

.summary-tile:hover {
  background: #f8fafc;
}

.summary-tile-active {
  background: #f8fafc;
  box-shadow: inset 0 -4px 0 #111827;
}

.donut-card-visual {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 14px;
  min-width: 0;
}

.donut-legend {
  display: grid;
  min-width: 0;
  gap: 6px;
}

.donut-legend-row {
  display: grid;
  grid-template-columns: 10px minmax(0, 1fr) auto;
  align-items: center;
  gap: 6px;
  color: #475569;
  font-size: 11px;
  font-weight: 800;
}

.donut-legend-row strong {
  color: #0f172a;
  font-size: 11px;
  font-weight: 900;
}

.donut-legend-dot {
  display: inline-block;
  width: 8px;
  height: 8px;
  border-radius: 9999px;
}

.summary-facts {
  display: grid;
  gap: 8px;
  border-top: 1px solid #e2e8f0;
  padding-top: 12px;
}

.summary-fact-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  color: #64748b;
  font-size: 12px;
  font-weight: 800;
}

.summary-fact-row strong {
  color: #0f172a;
  font-weight: 900;
}

.donut-track,
.donut-segment {
  fill: none;
  stroke-width: 13;
  transform: rotate(-90deg);
  transform-origin: 60px 60px;
}

.donut-track {
  stroke: #eef2f7;
}

.donut-segment {
  stroke-linecap: butt;
}

.donut-main {
  fill: #111827;
  font-size: 13px;
  font-weight: 900;
}

.donut-sub {
  fill: #64748b;
  font-size: 9px;
  font-weight: 800;
}

.detail-panel {
  padding: 20px;
}

.detail-panel h5 {
  color: #0f172a;
  font-size: 15px;
  font-weight: 900;
}

.one-dashboard-table {
  border-collapse: separate;
  border-spacing: 0;
}

.one-dashboard-table thead {
  position: sticky;
  top: 0;
  z-index: 10;
  background: #111827;
}

.one-dashboard-table th {
  white-space: nowrap;
  word-break: keep-all;
  border: 0;
  border-right: 1px solid rgba(255, 255, 255, 0.14);
  background: #111827;
  padding: 8px 6px;
  color: #fff;
  font-size: 11px;
  font-weight: 900;
  line-height: 1.25;
  text-align: center;
}

.one-dashboard-table thead tr:first-child th {
  border-bottom: 0;
}

.one-dashboard-table thead tr:nth-child(2) th {
  border-bottom: 1px solid #111827;
}

.one-dashboard-table thead th[rowspan] {
  vertical-align: middle;
  border-bottom: 1px solid #111827;
}

.one-dashboard-table td {
  white-space: nowrap;
  border-bottom: 1px solid #e5e7eb;
  border-right: 1px solid #e8edf3;
  padding: 7px 7px;
  color: #334155;
  font-size: 12px;
  line-height: 1.25;
}

.one-dashboard-table th:last-child,
.one-dashboard-table td:last-child {
  border-right: 0;
}

.one-dashboard-table tbody tr:nth-child(even) td {
  background: #f8fafc;
}

.one-dashboard-table tbody tr {
  cursor: pointer;
}

.one-dashboard-table tbody tr:hover td {
  background: #eef2ff;
}

.one-dashboard-table tbody tr.selected-data-row td,
.one-dashboard-table tbody tr.selected-data-row:nth-child(even) td {
  background: #dbeafe;
  color: #0f172a;
  font-weight: 800;
}

@media (max-width: 1023px) {
  .summary-tile {
    border-right: 0;
  }
}
</style>
