<template>
  <div class="ops-panel">
    <section class="ops-hero">
      <div v-if="showHeading">
        <p class="ops-eyebrow">CLEVER {{ activeCompanyName }}</p>
        <h3 class="mt-1 text-2xl font-bold text-gray-950">운영 현황</h3>
        <p class="mt-2 text-sm text-gray-600">날짜별 조 운영 지표</p>
      </div>

      <div class="ops-toolbar">
        <label v-if="showCompanySelect" class="ops-control">
          <span>회사</span>
          <select v-model="selectedCompany" class="ops-input min-w-[132px]">
            <option v-for="company in companies" :key="company.code" :value="company.code">
              {{ company.name }}
            </option>
          </select>
        </label>

        <label class="ops-control">
          <span>시작일</span>
          <input v-model="startDate" type="date" class="ops-input" />
        </label>

        <label class="ops-control">
          <span>종료일</span>
          <input v-model="endDate" type="date" class="ops-input" />
        </label>

        <div class="ops-presets">
          <button type="button" @click="applyPreset('week')">이번 주</button>
          <button type="button" @click="applyPreset('month')">이번 달</button>
          <button type="button" @click="applyPreset('today')">오늘</button>
        </div>

        <label class="ops-control">
          <span>화주사</span>
          <select v-model="selectedShipper" class="ops-input min-w-[120px]">
            <option value="">전체</option>
            <option v-for="shipper in shipperOptions" :key="shipper.code" :value="shipper.code">
              {{ shipper.name }}
            </option>
          </select>
        </label>

        <button type="button" class="ops-primary-btn" :disabled="loading" @click="loadReport({ force: true })">
          <span v-html="IconSearch" class="h-5 w-5"></span>
          조회
        </button>

        <button
          type="button"
          class="ops-dark-btn"
          :disabled="loading || rows.length === 0"
          @click="downloadFormattedCsv"
        >
          <span v-html="IconDownload" class="h-5 w-5"></span>
          CSV
        </button>

        <button
          type="button"
          class="ops-dark-btn ops-png-btn"
          :disabled="loading || pngDownloading || rows.length === 0"
          @click="downloadTablePng"
        >
          <span v-html="IconDownload" class="h-5 w-5"></span>
          {{ pngDownloading ? 'PNG 저장중' : 'PNG' }}
        </button>
      </div>
    </section>

    <section v-if="showTeamFilter" class="ops-team-row">
      <span class="ops-team-label">조</span>
      <TeamFilter :model-value="selectedTeam" @update:modelValue="updateTeam" />
    </section>

    <section class="ops-map">
      <header class="map-header">
        <div>
          <p class="map-kicker">용차 권역 분포</p>
          <h4 class="map-title">{{ normalizedStartDate }} - {{ normalizedEndDate }}</h4>
        </div>
        <div class="map-summary">
          <span>용차 회차 {{ formatNumber(yongchaMapSummary.total_yongcha_rounds || yongchaMapSummary.total_yongcha_visits) }}회</span>
          <span>권역 {{ formatNumber(yongchaMapSummary.active_territory_count) }}개</span>
          <strong v-if="yongchaMapSummary.top_territory">
            최다 {{ yongchaMapSummary.top_territory.code }} {{ formatNumber(yongchaMapSummary.top_territory.yongcha_count) }}회
          </strong>
          <button
            type="button"
            class="map-scroll-toggle"
            :class="{ active: mapScrollZoomEnabled }"
            @click="toggleYongchaScrollZoom"
          >
            {{ mapScrollZoomEnabled ? '스크롤 확대/축소 켜짐' : '스크롤 확대/축소' }}
          </button>
        </div>
      </header>

      <div class="map-body">
        <div :id="mapTargetId" ref="mapEl" class="ops-yongcha-map"></div>
        <div ref="mapPopupEl" class="map-popup-shell">
          <div v-if="selectedYongchaTerritory" class="map-popup">
            <header>
              <div>
                <strong>{{ selectedYongchaTerritory.code }}</strong>
                <span>{{ selectedYongchaTerritory.team_name || selectedYongchaTerritory.group_letter }}</span>
              </div>
              <button type="button" @click="closeYongchaPopup">닫기</button>
            </header>
            <p class="map-popup-total">
              조회기간 총 용차 횟수 {{ formatNumber(selectedYongchaTerritory.yongcha_round_count || selectedYongchaTerritory.yongcha_count) }}회
            </p>
            <div v-if="selectedYongchaTerritory.yongcha_dates?.length" class="map-popup-days">
              <section v-for="day in selectedYongchaTerritory.yongcha_dates" :key="day.date">
                <strong>{{ day.date }}</strong>
                <div v-for="round in day.rounds" :key="`${day.date}-${round.round_label}`" class="map-popup-round">
                  <span>{{ round.round_label }}</span>
                  <p>{{ (round.drivers || []).join(', ') }}</p>
                </div>
              </section>
            </div>
            <div v-else class="map-popup-empty">조회기간 용차 회차가 없습니다.</div>
          </div>
        </div>
        <div v-if="mapError" class="map-overlay">
          <div>{{ mapError }}</div>
        </div>
        <div v-else-if="mapLoading" class="map-overlay">
          <div>지도 데이터를 불러오는 중입니다.</div>
        </div>
        <div v-else-if="!yongchaMapRows.length" class="map-overlay">
          <div>표시할 권역 경계가 없습니다.</div>
        </div>
        <div class="map-legend">
        <span>용차 회차</span>
          <div class="legend-steps">
            <i v-for="level in 5" :key="level" :style="{ background: mapLevelColor(level) }"></i>
          </div>
          <span>낮음 - 높음</span>
        </div>
      </div>
    </section>

    <section class="ops-chart" :class="{ collapsed: !chartOpen }">
      <header class="chart-header">
        <div>
          <p class="chart-kicker">날짜별 추이</p>
          <h4 class="chart-title">{{ selectedChartMetricOption.label }}</h4>
        </div>
        <div class="chart-actions">
          <label v-if="chartOpen" class="ops-control">
            <span>Y 값</span>
            <select v-model="selectedChartMetric" class="ops-input min-w-[180px]">
              <option v-for="metric in chartMetricOptions" :key="metric.key" :value="metric.key">
                {{ metric.label }}
              </option>
            </select>
          </label>
          <button type="button" class="chart-toggle" :aria-expanded="chartOpen" @click="chartOpen = !chartOpen">
            {{ chartOpen ? '접기' : '열기' }}
          </button>
        </div>
      </header>

      <div v-if="chartOpen && loading" class="chart-empty">그래프 데이터를 불러오는 중입니다.</div>
      <div v-else-if="chartOpen && rows.length === 0" class="chart-empty">표시할 그래프 데이터가 없습니다.</div>
      <div v-else-if="chartOpen" class="chart-canvas">
        <svg
          viewBox="0 0 760 260"
          preserveAspectRatio="none"
          role="img"
          :aria-label="`${selectedChartMetricOption.label} 날짜별 꺾은선 그래프`"
        >
          <defs>
            <linearGradient id="opsLineArea" x1="0" x2="0" y1="0" y2="1">
              <stop offset="0%" stop-color="#c8d530" stop-opacity="0.32" />
              <stop offset="100%" stop-color="#c8d530" stop-opacity="0.03" />
            </linearGradient>
          </defs>

          <g class="chart-grid">
            <g v-for="tick in chartYTicks" :key="`${tick.y}-${tick.label}`">
              <line :x1="chartBounds.left" :x2="chartBounds.right" :y1="tick.y" :y2="tick.y" />
              <text :x="chartBounds.left - 10" :y="tick.y + 4" text-anchor="end">{{ tick.label }}</text>
            </g>
          </g>

          <path v-if="chartAreaPath" :d="chartAreaPath" fill="url(#opsLineArea)" />
          <path v-if="chartLinePath" :d="chartLinePath" class="chart-line" />

          <g v-for="(point, index) in chartPoints" :key="point.key">
            <circle :cx="point.x" :cy="point.y" r="4.5" class="chart-point" />
            <text
              v-if="shouldShowChartLabel(index)"
              :x="point.x"
              :y="chartBounds.bottom + 22"
              text-anchor="middle"
              class="chart-x-label"
            >
              {{ point.shortLabel }}
            </text>
          </g>
        </svg>

        <div class="chart-summary">
          <span>{{ normalizedStartDate }} - {{ normalizedEndDate }}</span>
          <strong>{{ formatChartValue(chartTotalValue) }}</strong>
        </div>
      </div>
    </section>

    <div v-if="errorMessage" class="rounded-xl border border-red-200 bg-red-50 p-4 text-red-700">
      {{ errorMessage }}
    </div>

    <section class="sheet-shell">
      <header class="sheet-header">
        <div>
          <p class="sheet-kicker">컬리 일일 운영 현황</p>
          <h4 class="sheet-title">{{ normalizedStartDate }} - {{ normalizedEndDate }}</h4>
        </div>
        <div class="sheet-side">
          <div class="volume-toggle" aria-label="운영현황 기준">
            <button
              v-for="option in volumeMetricOptions"
              :key="option.key"
              type="button"
              :class="{ active: volumeMetric === option.key }"
              @click="setVolumeMetric(option.key)"
            >
              {{ option.label }}
            </button>
          </div>
          <div class="sheet-meta">
            <span>{{ dateColumns.length }}일</span>
            <span>{{ teamBlocks.length }}개 조</span>
            <span>{{ formatNumber(summary.total_boxes) }}{{ metricUnit }}</span>
          </div>
        </div>
      </header>

      <div v-if="loading" class="py-16 text-center text-gray-400">
        <div class="mx-auto mb-3 h-8 w-8 animate-spin rounded-full border-2 border-primary border-t-transparent"></div>
        로딩 중...
      </div>

      <div v-else-if="rows.length === 0" class="py-16 text-center text-gray-400">
        <p class="mb-1 font-medium">조회 기간에 운영 데이터가 없습니다.</p>
        <p class="text-sm">배차표 업로드 여부와 날짜, 조 선택을 다시 확인해주세요.</p>
      </div>

      <div v-else>
        <div class="date-strip-shell">
          <div class="date-strip">
            <div
              v-for="day in dayCards"
              :key="day.key"
              class="date-chip"
              :class="{ active: day.totalVolume > 0, compact: isDenseDateRange }"
            >
              <span>{{ day.shortLabel }}</span>
              <strong>{{ formatNumber(day.totalVolume) }}{{ metricUnit }}</strong>
              <small>{{ day.weekday }}</small>
            </div>
          </div>
        </div>

        <div class="sheet-scroll">
          <div
            ref="sheetTableCaptureEl"
            class="sheet-table-wrap"
            :class="{ 'single-day-sheet': isSingleDayView }"
            :style="{ minWidth: sheetMinWidth, '--ops-day-col-width': `${sheetColumnWidth}px` }"
          >
            <table v-if="isSingleDayView" class="operation-sheet">
              <thead>
                <tr>
                  <th class="label-col" colspan="2">{{ singleDayColumn?.label || normalizedStartDate }}</th>
                  <th
                    v-for="team in teamBlocks"
                    :key="team.id"
                    class="date-col"
                    :title="team.name"
                  >
                    {{ team.name }}
                  </th>
                </tr>
                <tr>
                  <th class="label-col" colspan="2">{{ singleDayColumn?.weekday || '' }}</th>
                  <th
                    v-for="team in teamBlocks"
                    :key="`${team.id}-code`"
                    class="date-col weekday-col"
                    :title="team.code || team.name"
                  >
                    {{ team.code || team.name }}
                  </th>
                </tr>
              </thead>
              <tbody>
                <tr
                  v-for="line in sheetRows"
                  :key="`single-${line.key}`"
                  :class="{ 'summary-line': line.spanLabel, 'block-start': line.firstInGroup, 'yongcha-line': isYongchaSheetLine(line) }"
                >
                  <td v-if="line.spanLabel" class="label-cell" colspan="2">{{ line.label }}</td>
                  <template v-else>
                    <td v-if="line.firstInGroup" class="round-cell" :rowspan="line.groupRowspan">
                      {{ line.group }}
                    </td>
                    <td class="metric-cell">{{ line.metric }}</td>
                  </template>

                  <td
                    v-for="team in teamBlocks"
                    :key="`${team.id}-${line.key}`"
                    class="value-cell"
                    :class="{ 'percent-cell': line.format === 'percent', 'empty-cell': !hasSingleDayTeamValue(team) }"
                  >
                    {{ getSingleDayTeamValue(team, line) }}
                  </td>
                </tr>
              </tbody>
            </table>

            <table v-else class="operation-sheet">
              <thead>
                <tr>
                  <th class="team-col"></th>
                  <th class="label-col" colspan="2">날짜 (배송일 기준)</th>
                  <th class="total-col" rowspan="2">총계</th>
                  <th
                    v-for="day in dateColumns"
                    :key="day.key"
                    class="date-col"
                    :title="day.label"
                  >
                    {{ day.shortLabel }}
                  </th>
                </tr>
                <tr>
                  <th class="team-col"></th>
                  <th class="label-col" colspan="2">요일 (배송일 기준)</th>
                  <th
                    v-for="day in dateColumns"
                    :key="`${day.key}-weekday`"
                    class="date-col weekday-col"
                  >
                    {{ day.weekday }}
                  </th>
                </tr>
              </thead>
              <tbody>
                <template v-for="team in teamBlocks" :key="team.id">
                  <tr
                    v-for="(line, lineIndex) in sheetRows"
                    :key="`${team.id}-${line.key}`"
                    :class="{ 'block-start': lineIndex === 0, 'summary-line': line.spanLabel, 'yongcha-line': isYongchaSheetLine(line) }"
                  >
                    <td v-if="lineIndex === 0" class="team-cell" :rowspan="sheetRows.length">
                      <span>{{ team.name }}</span>
                    </td>

                    <td v-if="line.spanLabel" class="label-cell" colspan="2">{{ line.label }}</td>
                    <template v-else>
                      <td v-if="line.firstInGroup" class="round-cell" :rowspan="line.groupRowspan">
                        {{ line.group }}
                      </td>
                      <td class="metric-cell">{{ line.metric }}</td>
                    </template>

                    <td
                      class="total-cell"
                      :class="{ 'percent-cell': line.format === 'percent', 'empty-cell': !hasTotalValue(team, line) }"
                    >
                      {{ getTotalValue(team, line) }}
                    </td>

                    <td
                      v-for="day in dateColumns"
                      :key="`${team.id}-${line.key}-${day.key}`"
                      class="value-cell"
                      :class="{ 'percent-cell': line.format === 'percent', 'empty-cell': !hasSheetValue(team, day.key) }"
                    >
                      {{ getSheetValue(team, day.key, line) }}
                    </td>
                  </tr>
                </template>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { toPng } from 'html-to-image'
import TeamFilter from '@/components/common/TeamFilter.vue'
import { fetchPublicCompanyApp, fetchShippers } from '@/api/companyAdmin'
import {
  fetchOperationReport,
  fetchOperationReportTerritories,
  fetchOperationReportYongchaMap,
} from '@/api/dispatch'
import { IconDownload, IconSearch } from '@/utils/icons'
import { getCompanyAppFromRoute } from '@/utils/companyApp'
import { loadVWorld } from '@/utils/vworld'

const props = defineProps({
  companyName: { type: String, default: '천하운수' },
  companyCode: { type: String, default: '' },
  teamName: { type: String, default: '' },
  showHeading: { type: Boolean, default: true },
  showCompanySelect: { type: Boolean, default: true },
  showTeamFilter: { type: Boolean, default: true },
})

const route = useRoute()
const today = new Date()

const toDateInput = (date) => {
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

const getWeekStart = (date) => {
  const start = new Date(date)
  const day = start.getDay() || 7
  start.setDate(start.getDate() - day + 1)
  return start
}

const parseDateInput = (value) => {
  const [year, month, day] = String(value || '').split('-').map(Number)
  if (!year || !month || !day) return null
  return new Date(year, month - 1, day)
}

const addDays = (date, days) => {
  const next = new Date(date)
  next.setDate(next.getDate() + days)
  return next
}

const weekStart = getWeekStart(today)
const defaultSummary = () => ({
  row_count: 0,
  total_boxes: 0,
  total_volume: 0,
  round_1_boxes: 0,
  round_2_boxes: 0,
  round_3_boxes: 0,
  round_1_input_count: 0,
  round_2_input_count: 0,
  round_3_input_count: 0,
})

const startDate = ref(toDateInput(weekStart))
const endDate = ref(toDateInput(today))
const selectedCompany = ref(props.companyCode || getCompanyAppFromRoute(route).code || 'cheonha')
const selectedTeam = ref(props.teamName || '')
const selectedShipper = ref('')
const enabledShipperCodes = ref(['kurly'])
const shipperCatalog = ref([{ code: 'kurly', name: '컬리', status: 'ACTIVE' }])
const loading = ref(false)
const errorMessage = ref('')
const rows = ref([])
const selectedChartMetric = ref('actual_total_boxes')
const chartOpen = ref(false)
const volumeMetric = ref('boxes')
const summary = ref(defaultSummary())
const sheetTableCaptureEl = ref(null)
const pngDownloading = ref(false)
const mapTargetId = `ops-yongcha-map-${Math.random().toString(36).slice(2, 9)}`
const mapEl = ref(null)
const mapPopupEl = ref(null)
const mapLoading = ref(false)
const mapError = ref('')
const mapScrollZoomEnabled = ref(false)
const yongchaMapRows = ref([])
const selectedYongchaTerritory = ref(null)
const yongchaMapSummary = ref({
  territory_count: 0,
  active_territory_count: 0,
  total_yongcha_records: 0,
  total_yongcha_visits: 0,
  total_yongcha_rounds: 0,
  max_yongcha_count: 0,
  top_territory: null,
  unmatched_region_count: 0,
})
let yongchaMap = null
let yongchaOl = null
let yongchaTerritoryLayer = null
let yongchaPopupOverlay = null
let yongchaPopupCoordinate = null
let yongchaLayerExtent = null
let yongchaResizeObserver = null
let yongchaMouseWheelInteraction = null
let yongchaFitTimers = []
let reportLoadSeq = 0
const territoryGeometryCache = new Map()
const reportPayloadCache = new Map()
const yongchaMapPayloadCache = new Map()
const reportRequestCache = new Map()
const yongchaMapRequestCache = new Map()
const payloadCacheTtlMs = 60 * 1000

const companies = computed(() => [{ code: 'cheonha', name: props.companyName }])
const normalizeList = (payload) => payload?.results || payload || []
const shipperOptions = computed(() => {
  const enabled = new Set(enabledShipperCodes.value.length ? enabledShipperCodes.value : ['kurly'])
  const rows = normalizeList(shipperCatalog.value)
    .filter((item) => enabled.has(item.code) && item.status !== 'INACTIVE')
  if (rows.length > 0) return rows
  return [{ code: 'kurly', name: '컬리', status: 'ACTIVE' }]
})

const volumeMetricOptions = [
  { key: 'households', label: '가구' },
  { key: 'boxes', label: '박스' },
]

const averageTotalKeys = new Set([
  'boxes_per_household',
  'round_1_boxes',
  'round_2_boxes',
  'round_3_boxes',
  'round_1_productivity',
  'round_3_productivity',
  'multi_round_productivity',
  'round_1_input_count',
  'round_1_manager_count',
  'round_1_yongcha_count',
  'round_1_yongcha_ratio',
  'round_2_input_count',
  'round_2_manager_count',
  'round_2_yongcha_count',
  'round_2_yongcha_ratio',
  'round_3_input_count',
  'round_3_manager_count',
  'round_3_yongcha_count',
  'round_3_yongcha_ratio',
])

const rawSheetRows = [
  { key: 'actual_total_boxes', label: '실제 처리 물량', spanLabel: true, format: 'number' },
  { key: 'amount_total_receive', label: '전체수신', spanLabel: true, format: 'currency' },
  { key: 'amount_regular_pay', label: '정규지급', spanLabel: true, format: 'currency' },
  { key: 'amount_yongcha_pay', label: '용차지급', spanLabel: true, format: 'currency' },
  { key: 'amount_profit', label: '수익', spanLabel: true, format: 'currency' },
  { key: 'boxes_per_household', label: '가구당 박스수', spanLabel: true, format: 'decimal' },
  { key: 'round_1_boxes', label: '1회차 물량', spanLabel: true, format: 'number' },
  { key: 'round_2_boxes', label: '2회차 물량', spanLabel: true, format: 'number' },
  { key: 'round_3_boxes', label: '3회차 물량', spanLabel: true, format: 'number' },
  { key: 'round_1_productivity', label: '1회차 생산성', spanLabel: true, format: 'decimal' },
  { key: 'round_3_productivity', label: '3회차 생산성', spanLabel: true, format: 'decimal' },
  { key: 'multi_round_productivity', label: '다회차 생산성', spanLabel: true, format: 'decimal' },
  { key: 'round_1_input_count', group: '1회차', metric: '투입 대수', firstInGroup: true, groupRowspan: 4, format: 'number' },
  { key: 'round_1_manager_count', group: '1회차', metric: '매니저', format: 'number' },
  { key: 'round_1_yongcha_count', group: '1회차', metric: '용차', format: 'number' },
  { key: 'round_1_yongcha_ratio', group: '1회차', metric: '용차 비율', format: 'percent' },
  { key: 'round_2_input_count', group: '2회차', metric: '투입 대수', firstInGroup: true, groupRowspan: 4, format: 'number' },
  { key: 'round_2_manager_count', group: '2회차', metric: '매니저', format: 'number' },
  { key: 'round_2_yongcha_count', group: '2회차', metric: '용차', format: 'number' },
  { key: 'round_2_yongcha_ratio', group: '2회차', metric: '용차 비율', format: 'percent' },
  { key: 'round_3_input_count', group: '3회차', metric: '투입 대수', firstInGroup: true, groupRowspan: 4, format: 'number' },
  { key: 'round_3_manager_count', group: '3회차', metric: '매니저', format: 'number' },
  { key: 'round_3_yongcha_count', group: '3회차', metric: '용차', format: 'number' },
  { key: 'round_3_yongcha_ratio', group: '3회차', metric: '용차 비율', format: 'percent' },
]

const rawChartMetricOptions = [
  { key: 'actual_total_boxes', label: '실제 처리 물량', format: 'number', aggregate: 'sum' },
  { key: 'amount_total_receive', label: '전체수신', format: 'currency', aggregate: 'sum' },
  { key: 'amount_regular_pay', label: '정규지급', format: 'currency', aggregate: 'sum' },
  { key: 'amount_yongcha_pay', label: '용차지급', format: 'currency', aggregate: 'sum' },
  { key: 'amount_profit', label: '수익', format: 'currency', aggregate: 'sum' },
  { key: 'round_1_boxes', label: '1회차 물량', format: 'number', aggregate: 'sum' },
  { key: 'round_2_boxes', label: '2회차 물량', format: 'number', aggregate: 'sum' },
  { key: 'round_3_boxes', label: '3회차 물량', format: 'number', aggregate: 'sum' },
  { key: 'round_1_productivity', label: '1회차 생산성', format: 'decimal', aggregate: 'average' },
  { key: 'round_3_productivity', label: '3회차 생산성', format: 'decimal', aggregate: 'average' },
  { key: 'multi_round_productivity', label: '다회차 생산성', format: 'decimal', aggregate: 'average' },
  { key: 'round_1_input_count', label: '1회차 투입 대수', format: 'number', aggregate: 'sum' },
  { key: 'round_2_input_count', label: '2회차 투입 대수', format: 'number', aggregate: 'sum' },
  { key: 'round_3_input_count', label: '3회차 투입 대수', format: 'number', aggregate: 'sum' },
  { key: 'round_1_yongcha_ratio', label: '1회차 용차 비율', format: 'percent', aggregate: 'average' },
  { key: 'round_2_yongcha_ratio', label: '2회차 용차 비율', format: 'percent', aggregate: 'average' },
  { key: 'round_3_yongcha_ratio', label: '3회차 용차 비율', format: 'percent', aggregate: 'average' },
]

const metricUnit = computed(() => (volumeMetric.value === 'households' ? '가구' : '박스'))
const metricVolumeLabel = computed(() => (volumeMetric.value === 'households' ? '가구수' : '박스수'))

const sheetLineOverrides = computed(() => ({
  actual_total_boxes: { label: `실제 처리 ${metricVolumeLabel.value}` },
  round_1_boxes: { label: `1회차 ${metricVolumeLabel.value}` },
  round_2_boxes: { label: `2회차 ${metricVolumeLabel.value}` },
  round_3_boxes: { label: `3회차 ${metricVolumeLabel.value}` },
  round_1_productivity: { label: `1회차 생산성(${metricUnit.value}/대)` },
  round_3_productivity: { label: `3회차 생산성(${metricUnit.value}/대)` },
  multi_round_productivity: { label: `다회차 생산성(${metricUnit.value}/명)` },
}))

const chartMetricLabelOverrides = computed(() => ({
  actual_total_boxes: `실제 처리 ${metricVolumeLabel.value}`,
  round_1_boxes: `1회차 ${metricVolumeLabel.value}`,
  round_2_boxes: `2회차 ${metricVolumeLabel.value}`,
  round_3_boxes: `3회차 ${metricVolumeLabel.value}`,
  round_1_productivity: `1회차 생산성(${metricUnit.value}/대)`,
  round_3_productivity: `3회차 생산성(${metricUnit.value}/대)`,
  multi_round_productivity: `다회차 생산성(${metricUnit.value}/명)`,
}))

const sheetRows = computed(() => rawSheetRows.map((line) => ({
  ...line,
  ...(sheetLineOverrides.value[line.key] || {}),
})))

const isYongchaSheetLine = (line) => String(line?.key || '').includes('yongcha')

const chartMetricOptions = computed(() => rawChartMetricOptions.map((metric) => ({
  ...metric,
  label: chartMetricLabelOverrides.value[metric.key] || metric.label,
})))

const chartBounds = {
  left: 96,
  right: 738,
  top: 24,
  bottom: 236,
}

const weekdayFull = ['일요일', '월요일', '화요일', '수요일', '목요일', '금요일', '토요일']

const activeCompanyName = computed(() => {
  return companies.value.find((company) => company.code === selectedCompany.value)?.name || props.companyName
})

const normalizedDateBounds = computed(() => {
  const start = parseDateInput(startDate.value) || today
  const end = parseDateInput(endDate.value) || start
  return start <= end ? { start, end } : { start: end, end: start }
})

const normalizedStartDate = computed(() => toDateInput(normalizedDateBounds.value.start))
const normalizedEndDate = computed(() => toDateInput(normalizedDateBounds.value.end))

const buildParams = () => ({
  start: normalizedStartDate.value,
  end: normalizedEndDate.value,
  team: selectedTeam.value || undefined,
  shipper_code: selectedShipper.value || undefined,
  metric: volumeMetric.value,
})

const cacheKeyFromParams = (params = {}) => {
  return Object.entries(params)
    .filter(([, value]) => value !== undefined && value !== null && value !== '')
    .sort(([left], [right]) => left.localeCompare(right))
    .map(([key, value]) => `${key}=${value}`)
    .join('&')
}

const getCachedPayload = (cache, key) => {
  const cached = cache.get(key)
  if (!cached) return null
  if (Date.now() - cached.createdAt > payloadCacheTtlMs) {
    cache.delete(key)
    return null
  }
  return cached.payload
}

const setCachedPayload = (cache, key, payload) => {
  cache.set(key, { createdAt: Date.now(), payload })
}

const fetchOperationReportPayload = async (params, { force = false } = {}) => {
  const key = cacheKeyFromParams(params)
  if (!force) {
    const cached = getCachedPayload(reportPayloadCache, key)
    if (cached) return cached
    const pending = reportRequestCache.get(key)
    if (pending) return pending
  }
  const request = fetchOperationReport(params)
    .then((response) => {
      const payload = response.data || {}
      setCachedPayload(reportPayloadCache, key, payload)
      return payload
    })
    .finally(() => {
      reportRequestCache.delete(key)
    })
  reportRequestCache.set(key, request)
  return request
}

const fetchYongchaMapPayload = async (params, { force = false } = {}) => {
  const key = cacheKeyFromParams(params)
  if (!force) {
    const cached = getCachedPayload(yongchaMapPayloadCache, key)
    if (cached) return cached
    const pending = yongchaMapRequestCache.get(key)
    if (pending) return pending
  }
  const request = fetchOperationReportYongchaMap(params)
    .then((response) => {
      const payload = response.data || {}
      setCachedPayload(yongchaMapPayloadCache, key, payload)
      return payload
    })
    .finally(() => {
      yongchaMapRequestCache.delete(key)
    })
  yongchaMapRequestCache.set(key, request)
  return request
}

const loadShipperOptions = async () => {
  try {
    const companyCode = props.companyCode || selectedCompany.value || getCompanyAppFromRoute(route).code
    const [companyResp, shipperResp] = await Promise.all([
      fetchPublicCompanyApp(companyCode),
      fetchShippers(),
    ])
    enabledShipperCodes.value = companyResp.data?.enabled_shippers?.length
      ? companyResp.data.enabled_shippers
      : ['kurly']
    shipperCatalog.value = normalizeList(shipperResp.data)
    if (selectedShipper.value && !enabledShipperCodes.value.includes(selectedShipper.value)) {
      selectedShipper.value = ''
    }
  } catch {
    enabledShipperCodes.value = ['kurly']
    shipperCatalog.value = [{ code: 'kurly', name: '컬리', status: 'ACTIVE' }]
    if (selectedShipper.value && selectedShipper.value !== 'kurly') {
      selectedShipper.value = ''
    }
  }
}

const territoryCacheKey = () => `${selectedCompany.value || 'cheonha'}|all`

const normalizeTeamToken = (value) => String(value || '').trim().replace(/조$/, '').toUpperCase()

const matchesSelectedTeam = (territory) => {
  if (!selectedTeam.value) return true
  const target = normalizeTeamToken(selectedTeam.value)
  return [
    territory.team_name,
    territory.team_code,
    territory.group_letter,
    territory.team_id,
  ].some((value) => normalizeTeamToken(value) === target)
}

const loadTerritoryGeometryRows = async () => {
  const key = territoryCacheKey()
  if (!territoryGeometryCache.has(key)) {
    const response = await fetchOperationReportTerritories({})
    territoryGeometryCache.set(key, response.data?.results || [])
  }
  return territoryGeometryCache.get(key) || []
}

const mapStatKey = (row) => `${row.team_id || ''}|${row.code || ''}`

const mergeYongchaMapRows = (statsPayload = {}, geometryRows = []) => {
  const statRows = statsPayload.results || []
  const statsByKey = new Map(statRows.map((row) => [mapStatKey(row), row]))
  const fallbackGeometries = statRows.some((row) => row.geometry) ? statRows : geometryRows

  return fallbackGeometries
    .filter(matchesSelectedTeam)
    .map((territory) => {
      const stat = statsByKey.get(mapStatKey(territory)) || {}
      const count = Number(stat.yongcha_count || 0)
      return {
        ...territory,
        ...stat,
        id: territory.id,
        code: territory.code,
        group_letter: territory.group_letter,
        team_id: territory.team_id,
        team_code: territory.team_code,
        team_name: territory.team_name,
        geometry: territory.geometry,
        centroid_lat: territory.centroid_lat,
        centroid_lon: territory.centroid_lon,
        yongcha_count: count,
        yongcha_round_count: Number(stat.yongcha_round_count || count),
        yongcha_dates: stat.yongcha_dates || [],
        level: Number(stat.level || 0),
      }
    })
}

const yongchaMapColors = {
  0: 'rgba(248, 250, 252, 0.3)',
  1: 'rgba(252, 231, 243, 0.72)',
  2: 'rgba(251, 207, 232, 0.78)',
  3: 'rgba(253, 164, 175, 0.82)',
  4: 'rgba(248, 113, 113, 0.86)',
  5: 'rgba(220, 38, 38, 0.9)',
}

const mapLevelColor = (level) => yongchaMapColors[Number(level || 0)] || yongchaMapColors[0]

const isYongchaMouseWheelInteraction = (interaction) => {
  if (!interaction || !yongchaOl?.interaction?.MouseWheelZoom) return false
  if (interaction instanceof yongchaOl.interaction.MouseWheelZoom) return true
  return interaction.constructor?.name === 'MouseWheelZoom'
}

const getYongchaMouseWheelInteraction = () => {
  if (!yongchaMap) return null
  if (yongchaMouseWheelInteraction) return yongchaMouseWheelInteraction
  const interactions = yongchaMap.getInteractions?.()
  interactions?.forEach?.((interaction) => {
    if (!yongchaMouseWheelInteraction && isYongchaMouseWheelInteraction(interaction)) {
      yongchaMouseWheelInteraction = interaction
    }
  })
  return yongchaMouseWheelInteraction
}

const setYongchaScrollZoom = (enabled) => {
  if (!yongchaMap || !yongchaOl?.interaction?.MouseWheelZoom) return
  let interaction = getYongchaMouseWheelInteraction()
  if (!interaction && enabled) {
    interaction = new yongchaOl.interaction.MouseWheelZoom()
    yongchaMouseWheelInteraction = interaction
    yongchaMap.addInteraction?.(interaction)
  }
  interaction?.setActive?.(Boolean(enabled))
}

const toggleYongchaScrollZoom = () => {
  mapScrollZoomEnabled.value = !mapScrollZoomEnabled.value
  setYongchaScrollZoom(mapScrollZoomEnabled.value)
}

const dateColumns = computed(() => {
  const columns = []
  let cursor = new Date(normalizedDateBounds.value.start)
  const end = normalizedDateBounds.value.end
  while (cursor <= end) {
    const key = toDateInput(cursor)
    columns.push({
      key,
      label: key,
      shortLabel: `${cursor.getMonth() + 1}/${cursor.getDate()}`,
      weekday: weekdayFull[cursor.getDay()],
    })
    cursor = addDays(cursor, 1)
  }
  return columns
})

const isSingleDayView = computed(() => dateColumns.value.length === 1)
const singleDayColumn = computed(() => dateColumns.value[0] || null)
const singleDayKey = computed(() => singleDayColumn.value?.key || normalizedStartDate.value)

const isDenseDateRange = computed(() => dateColumns.value.length >= 14)

const dayColumnWidth = computed(() => {
  const count = dateColumns.value.length
  if (count >= 31) return 60
  if (count >= 24) return 66
  if (count >= 18) return 74
  if (count >= 14) return 84
  return 104
})

const singleDayTeamColumnWidth = computed(() => {
  const count = teamBlocks.value.length
  if (count >= 16) return 82
  if (count >= 12) return 90
  return 104
})

const sheetColumnWidth = computed(() => (
  isSingleDayView.value ? singleDayTeamColumnWidth.value : dayColumnWidth.value
))

const rowDateKey = (row) => row.delivery_date || row.work_date

const dayCards = computed(() => {
  return dateColumns.value.map((day) => ({
    ...day,
    totalVolume: rows.value
      .filter((row) => rowDateKey(row) === day.key)
      .reduce((sum, row) => sum + Number(row.actual_total_boxes || 0), 0),
  }))
})

const teamBlocks = computed(() => {
  const map = new Map()
  for (const row of rows.value) {
    const id = String(row.team_id || row.team_code || row.team_name || 'unknown')
    if (!map.has(id)) {
      map.set(id, {
        id,
        code: row.team_code || '',
        name: row.team_name || row.team_code || '미지정',
      })
    }
  }
  return Array.from(map.values()).sort((a, b) => {
    const left = a.code || a.name
    const right = b.code || b.name
    return left.localeCompare(right, 'ko', { numeric: true })
  })
})

const rowLookup = computed(() => {
  const map = new Map()
  for (const row of rows.value) {
    const id = String(row.team_id || row.team_code || row.team_name || 'unknown')
    map.set(`${id}|${rowDateKey(row)}`, row)
  }
  return map
})

const sheetMinWidth = computed(() => {
  if (isSingleDayView.value) {
    return `${220 + (teamBlocks.value.length * singleDayTeamColumnWidth.value)}px`
  }
  return `${470 + (dateColumns.value.length * dayColumnWidth.value)}px`
})

const selectedChartMetricOption = computed(() => {
  return chartMetricOptions.value.find((metric) => metric.key === selectedChartMetric.value) || chartMetricOptions.value[0]
})

const aggregateChartRows = (dayRows) => {
  const option = selectedChartMetricOption.value
  if (!option || dayRows.length === 0) return 0
  const values = dayRows.map((row) => Number(row[option.key] || 0))
  if (option.aggregate === 'average') {
    const activeValues = values.filter((value) => value > 0)
    if (activeValues.length === 0) return 0
    return activeValues.reduce((sum, value) => sum + value, 0) / activeValues.length
  }
  return values.reduce((sum, value) => sum + value, 0)
}

const chartValues = computed(() => {
  return dateColumns.value.map((day) => ({
    key: day.key,
    label: day.label,
    shortLabel: day.shortLabel,
    value: aggregateChartRows(rows.value.filter((row) => rowDateKey(row) === day.key)),
  }))
})

const chartTotalValue = computed(() => {
  const values = chartValues.value.map((point) => point.value)
  if (selectedChartMetricOption.value?.aggregate === 'average') {
    const activeValues = values.filter((value) => value > 0)
    if (activeValues.length === 0) return 0
    return activeValues.reduce((sum, value) => sum + value, 0) / activeValues.length
  }
  return values.reduce((sum, value) => sum + value, 0)
})

const chartDomain = computed(() => {
  const values = chartValues.value.map((point) => point.value)
  const rawMin = Math.min(...values, 0)
  const rawMax = Math.max(...values, 0)
  if (rawMin === rawMax) return { min: 0, max: 1 }

  const span = rawMax - rawMin
  return {
    min: rawMin < 0 ? rawMin - (span * 0.12) : 0,
    max: rawMax > 0 ? rawMax + (span * 0.12) : 0,
  }
})

const chartValueToY = (value) => {
  const { min, max } = chartDomain.value
  const span = max - min || 1
  const height = chartBounds.bottom - chartBounds.top
  return chartBounds.bottom - (((value - min) / span) * height)
}

const chartZeroY = computed(() => chartValueToY(0))

const chartPoints = computed(() => {
  const count = chartValues.value.length
  const width = chartBounds.right - chartBounds.left

  return chartValues.value.map((point, index) => {
    const x = count <= 1
      ? chartBounds.left + width / 2
      : chartBounds.left + (width * index / (count - 1))
    const y = chartValueToY(point.value)
    return { ...point, x, y }
  })
})

const chartLinePath = computed(() => {
  return chartPoints.value
    .map((point, index) => `${index === 0 ? 'M' : 'L'} ${point.x.toFixed(2)} ${point.y.toFixed(2)}`)
    .join(' ')
})

const chartAreaPath = computed(() => {
  if (chartPoints.value.length === 0) return ''
  const first = chartPoints.value[0]
  const last = chartPoints.value[chartPoints.value.length - 1]
  const zeroY = chartZeroY.value
  return `${chartLinePath.value} L ${last.x.toFixed(2)} ${zeroY.toFixed(2)} L ${first.x.toFixed(2)} ${zeroY.toFixed(2)} Z`
})

const chartYTicks = computed(() => {
  const { min, max } = chartDomain.value
  const span = max - min || 1
  return [0, 0.25, 0.5, 0.75, 1].map((ratio) => {
    const value = min + (span * ratio)
    const y = chartBounds.bottom - ((chartBounds.bottom - chartBounds.top) * ratio)
    return { y, label: formatChartValue(value) }
  })
})

const formatNumber = (value) => Number(value || 0).toLocaleString()
const formatDecimal = (value) => Number(value || 0).toLocaleString(undefined, { maximumFractionDigits: 2 })
const formatPercent = (value) => `${Number(value || 0).toLocaleString(undefined, { maximumFractionDigits: 1 })}%`
const formatCurrencyValue = (value) => `${Math.round(Number(value || 0)).toLocaleString()}원`

const formatChartValue = (value) => {
  const option = selectedChartMetricOption.value
  if (option?.format === 'currency') return formatCurrencyValue(value)
  if (option?.format === 'percent') return formatPercent(value)
  if (option?.format === 'decimal') return formatDecimal(value)
  return formatNumber(value)
}

const formatSheetValue = (value, line) => {
  if (line.format === 'currency') return formatCurrencyValue(value)
  if (line.format === 'percent') return formatPercent(value)
  if (line.format === 'decimal') return formatDecimal(value)
  return formatNumber(value)
}

const getTeamPeriodRows = (team) => {
  return dateColumns.value
    .map((day) => rowLookup.value.get(`${team.id}|${day.key}`))
    .filter(Boolean)
}

const getTotalRawValue = (team, line) => {
  const periodRows = getTeamPeriodRows(team)
  if (periodRows.length === 0) return null

  const values = periodRows.map((row) => Number(row[line.key] || 0))
  if (averageTotalKeys.has(line.key)) {
    return values.reduce((sum, value) => sum + value, 0) / values.length
  }
  return values.reduce((sum, value) => sum + value, 0)
}

const hasTotalValue = (team, line) => getTotalRawValue(team, line) !== null

const getTotalValue = (team, line) => {
  const value = getTotalRawValue(team, line)
  if (value === null) return ''
  return formatSheetValue(value, line)
}

const getSheetValue = (team, dateKey, line) => {
  const row = rowLookup.value.get(`${team.id}|${dateKey}`)
  if (!row) return ''
  return formatSheetValue(row[line.key], line)
}

const hasSheetValue = (team, dateKey) => rowLookup.value.has(`${team.id}|${dateKey}`)
const hasSingleDayTeamValue = (team) => hasSheetValue(team, singleDayKey.value)
const getSingleDayTeamValue = (team, line) => getSheetValue(team, singleDayKey.value, line)

const shouldShowChartLabel = (index) => {
  const count = chartPoints.value.length
  if (count <= 8) return true
  const step = Math.ceil(count / 6)
  return index === 0 || index === count - 1 || index % step === 0
}

const geometryToOl = (geometry) => {
  if (!geometry || !geometry.type || !yongchaOl) return null
  if (geometry.type === 'Polygon') {
    const coords = geometry.coordinates.map((ring) => ring.map((point) => yongchaOl.proj.fromLonLat(point)))
    return new yongchaOl.geom.Polygon(coords)
  }
  if (geometry.type === 'MultiPolygon') {
    const coords = geometry.coordinates.map((polygon) =>
      polygon.map((ring) => ring.map((point) => yongchaOl.proj.fromLonLat(point))),
    )
    return new yongchaOl.geom.MultiPolygon(coords)
  }
  return null
}

const renderYongchaMap = () => {
  if (!yongchaTerritoryLayer || !yongchaOl) return
  const source = yongchaTerritoryLayer.getSource()
  source.clear()
  yongchaLayerExtent = null

  for (const row of yongchaMapRows.value) {
    const geometry = geometryToOl(row.geometry)
    if (!geometry) continue
    const count = Number(row.yongcha_count || 0)
    const level = Number(row.level || 0)
    const feature = new yongchaOl.Feature({ geometry })
    feature.set('territoryCode', row.code)
    feature.setStyle(new yongchaOl.style.Style({
      stroke: new yongchaOl.style.Stroke({
        color: count ? '#7f1d1d' : '#94a3b8',
        width: count ? 1.8 : 1,
      }),
      fill: new yongchaOl.style.Fill({
        color: mapLevelColor(level),
      }),
      text: new yongchaOl.style.Text({
        text: row.code,
        font: '800 12px sans-serif',
        fill: new yongchaOl.style.Fill({ color: count ? '#111827' : '#475569' }),
        stroke: new yongchaOl.style.Stroke({ color: '#ffffff', width: 4 }),
        overflow: true,
      }),
    }))
    source.addFeature(feature)
    const featureExtent = geometry.getExtent()
    if (featureExtent && Number.isFinite(featureExtent[0])) {
      if (!yongchaLayerExtent) {
        yongchaLayerExtent = featureExtent.slice()
      } else {
        yongchaLayerExtent[0] = Math.min(yongchaLayerExtent[0], featureExtent[0])
        yongchaLayerExtent[1] = Math.min(yongchaLayerExtent[1], featureExtent[1])
        yongchaLayerExtent[2] = Math.max(yongchaLayerExtent[2], featureExtent[2])
        yongchaLayerExtent[3] = Math.max(yongchaLayerExtent[3], featureExtent[3])
      }
    }
  }
  scheduleYongchaMapFit()
}

const fitYongchaMap = () => {
  if (!yongchaMap || !yongchaTerritoryLayer) return
  const extent = yongchaLayerExtent || yongchaTerritoryLayer.getSource().getExtent()
  if (!extent || !Number.isFinite(extent[0])) return

  yongchaMap.updateSize()
  const size = yongchaMap.getSize?.()
  const rect = mapEl.value?.getBoundingClientRect()
  const width = size?.[0] || rect?.width || 0
  const height = size?.[1] || rect?.height || 0
  if (width < 160 || height < 160) return

  const horizontalPadding = Math.max(18, Math.min(34, Math.round(width * 0.035)))
  const verticalPadding = Math.max(18, Math.min(34, Math.round(height * 0.045)))
  const usableWidth = Math.max(1, width - (horizontalPadding * 2))
  const usableHeight = Math.max(1, height - (verticalPadding * 2) - 18)
  const view = yongchaMap.getView()
  const center = [
    (extent[0] + extent[2]) / 2,
    (extent[1] + extent[3]) / 2,
  ]

  let resolution = null
  if (typeof view.getResolutionForExtent === 'function') {
    resolution = view.getResolutionForExtent(extent, [usableWidth, usableHeight])
  }
  if (!resolution || !Number.isFinite(resolution)) {
    const extentWidth = Math.max(1, extent[2] - extent[0])
    const extentHeight = Math.max(1, extent[3] - extent[1])
    resolution = Math.max(extentWidth / usableWidth, extentHeight / usableHeight)
  }

  if (typeof view.getZoomForResolution === 'function' && typeof view.getResolutionForZoom === 'function') {
    const zoom = view.getZoomForResolution(resolution)
    if (Number.isFinite(zoom)) {
      resolution = view.getResolutionForZoom(Math.min(zoom, 13))
    }
  }

  view.setCenter(center)
  if (typeof view.setResolution === 'function') {
    view.setResolution(resolution)
  } else if (typeof view.getZoomForResolution === 'function') {
    view.setZoom(Math.min(view.getZoomForResolution(resolution), 13))
  }
}

const clearYongchaFitTimers = () => {
  for (const timer of yongchaFitTimers) {
    clearTimeout(timer)
  }
  yongchaFitTimers = []
}

const scheduleYongchaMapFit = () => {
  clearYongchaFitTimers()
  requestAnimationFrame(fitYongchaMap)
  for (const delay of [80, 220, 520]) {
    yongchaFitTimers.push(setTimeout(fitYongchaMap, delay))
  }
}

const closeYongchaPopup = () => {
  selectedYongchaTerritory.value = null
  yongchaPopupCoordinate = null
  if (yongchaPopupOverlay) {
    yongchaPopupOverlay.setPosition(undefined)
  }
}

const panYongchaPopupIntoView = () => {
  if (!yongchaMap || !mapEl.value || !yongchaPopupCoordinate) return
  const popup = mapPopupEl.value?.querySelector?.('.map-popup')
  if (!popup) return

  const mapRect = mapEl.value.getBoundingClientRect()
  const popupRect = popup.getBoundingClientRect()
  const margin = 16
  let shiftX = 0
  let shiftY = 0

  if (popupRect.left < mapRect.left + margin) {
    shiftX = (mapRect.left + margin) - popupRect.left
  } else if (popupRect.right > mapRect.right - margin) {
    shiftX = (mapRect.right - margin) - popupRect.right
  }

  if (popupRect.top < mapRect.top + margin) {
    shiftY = (mapRect.top + margin) - popupRect.top
  } else if (popupRect.bottom > mapRect.bottom - margin) {
    shiftY = (mapRect.bottom - margin) - popupRect.bottom
  }

  if (Math.abs(shiftX) < 1 && Math.abs(shiftY) < 1) return

  const currentPixel = yongchaMap.getPixelFromCoordinate(yongchaPopupCoordinate)
  const size = yongchaMap.getSize?.()
  if (!currentPixel || !size) return
  const desiredPixel = [currentPixel[0] + shiftX, currentPixel[1] + shiftY]
  const view = yongchaMap.getView()

  if (typeof view.centerOn === 'function') {
    view.centerOn(yongchaPopupCoordinate, size, desiredPixel)
    return
  }

  const resolution = view.getResolution?.()
  if (!resolution) return
  const centerPixel = [size[0] / 2, size[1] / 2]
  view.setCenter([
    yongchaPopupCoordinate[0] - ((desiredPixel[0] - centerPixel[0]) * resolution),
    yongchaPopupCoordinate[1] + ((desiredPixel[1] - centerPixel[1]) * resolution),
  ])
}

const scheduleYongchaPopupPan = () => {
  requestAnimationFrame(() => {
    panYongchaPopupIntoView()
    setTimeout(panYongchaPopupIntoView, 60)
  })
}

const openYongchaPopup = (territory, coordinate) => {
  selectedYongchaTerritory.value = territory
  yongchaPopupCoordinate = coordinate
  nextTick(() => {
    if (yongchaPopupOverlay) {
      yongchaPopupOverlay.setPosition(coordinate)
    }
    scheduleYongchaPopupPan()
  })
}

const initYongchaMap = async () => {
  if (yongchaMap) return
  try {
    const { vw, ol } = await loadVWorld()
    yongchaOl = ol
    yongchaMap = new vw.ol3.Map(mapTargetId, {
      basemapType: vw.ol3.BasemapType.GRAPHIC,
      controlDensity: vw.ol3.DensityType.EMPTY,
      interactionDensity: vw.ol3.DensityType.BASIC,
      controlsAutoArrange: true,
      homePosition: vw.ol3.CameraPosition,
      initPosition: vw.ol3.CameraPosition,
    })
    yongchaMap.getView().setCenter(ol.proj.fromLonLat([126.9784, 37.5665]))
    yongchaMap.getView().setZoom(11)
    setYongchaScrollZoom(mapScrollZoomEnabled.value)
    yongchaTerritoryLayer = new ol.layer.Vector({ source: new ol.source.Vector(), zIndex: 5 })
    yongchaMap.addLayer(yongchaTerritoryLayer)
    if (mapPopupEl.value) {
      yongchaPopupOverlay = new ol.Overlay({
        element: mapPopupEl.value,
        positioning: 'bottom-center',
        offset: [0, -14],
        stopEvent: true,
      })
      yongchaMap.addOverlay(yongchaPopupOverlay)
    }
    yongchaMap.on('click', (evt) => {
      let hit = null
      yongchaMap.forEachFeatureAtPixel(evt.pixel, (feature) => {
        if (feature.get('territoryCode')) {
          hit = feature
          return true
        }
        return false
      }, { hitTolerance: 6 })

      if (!hit) {
        closeYongchaPopup()
        return
      }
      const code = hit.get('territoryCode')
      const territory = yongchaMapRows.value.find((row) => row.code === code)
      if (territory) {
        openYongchaPopup(territory, evt.coordinate)
      }
    })
    yongchaMap.on('pointermove', (evt) => {
      let hit = false
      yongchaMap.forEachFeatureAtPixel(evt.pixel, (feature) => {
        if (feature.get('territoryCode')) {
          hit = true
          return true
        }
        return false
      }, { hitTolerance: 6 })
      yongchaMap.getTargetElement().style.cursor = hit ? 'pointer' : ''
    })
    if (typeof ResizeObserver !== 'undefined' && mapEl.value) {
      yongchaResizeObserver = new ResizeObserver(() => scheduleYongchaMapFit())
      yongchaResizeObserver.observe(mapEl.value)
    }
    renderYongchaMap()
    scheduleYongchaMapFit()
  } catch (error) {
    mapError.value = error.message || '지도를 불러오지 못했습니다.'
  }
}

const applyYongchaMapPayload = (payload = {}, geometryRows = []) => {
  closeYongchaPopup()
  yongchaMapRows.value = mergeYongchaMapRows(payload, geometryRows)
  yongchaMapSummary.value = {
    territory_count: 0,
    active_territory_count: 0,
    total_yongcha_records: 0,
    total_yongcha_visits: 0,
    total_yongcha_rounds: 0,
    max_yongcha_count: 0,
    top_territory: null,
    unmatched_region_count: 0,
    ...(payload.summary || {}),
  }
  nextTick(renderYongchaMap)
}

const applyReportPayload = (payload = {}) => {
  rows.value = payload.results || []
  summary.value = {
    ...defaultSummary(),
    ...(payload.summary || {}),
  }
}

const resetYongchaMapPayload = () => {
  yongchaMapRows.value = []
  yongchaMapSummary.value = {
    territory_count: 0,
    active_territory_count: 0,
    total_yongcha_records: 0,
    total_yongcha_visits: 0,
    total_yongcha_rounds: 0,
    max_yongcha_count: 0,
    top_territory: null,
    unmatched_region_count: 0,
  }
}

const updateTeam = (team) => {
  selectedTeam.value = team || ''
  loadReport()
}

const setVolumeMetric = (metric) => {
  if (volumeMetric.value === metric) return
  volumeMetric.value = metric
  loadReport()
}

const applyPreset = (preset) => {
  const base = new Date()
  if (preset === 'today') {
    startDate.value = toDateInput(base)
    endDate.value = toDateInput(base)
  } else if (preset === 'week') {
    startDate.value = toDateInput(getWeekStart(base))
    endDate.value = toDateInput(base)
  } else if (preset === 'month') {
    startDate.value = toDateInput(new Date(base.getFullYear(), base.getMonth(), 1))
    endDate.value = toDateInput(base)
  }
  loadReport()
}

const loadReport = async (options = {}) => {
  const force = Boolean(options?.force)
  const seq = ++reportLoadSeq
  const params = buildParams()
  const reportCacheKey = cacheKeyFromParams(params)
  const cachedReport = force ? null : getCachedPayload(reportPayloadCache, reportCacheKey)
  loading.value = !cachedReport
  mapLoading.value = true
  errorMessage.value = ''
  mapError.value = ''

  if (cachedReport) {
    applyReportPayload(cachedReport)
  }

  const reportPromise = fetchOperationReportPayload(params, { force })
    .then((payload) => {
      if (seq !== reportLoadSeq) return
      applyReportPayload(payload)
    })
    .catch((error) => {
      if (seq !== reportLoadSeq) return
      rows.value = []
      summary.value = defaultSummary()
      errorMessage.value = error.response?.data?.detail || '운영현황을 불러오지 못했습니다.'
    })
    .finally(() => {
      if (seq === reportLoadSeq) {
        loading.value = false
      }
    })

  Promise.allSettled([
    loadTerritoryGeometryRows(),
    fetchYongchaMapPayload({ ...params, include_geometry: false }, { force }),
  ]).then(([geometryResult, mapResult]) => {
    if (seq !== reportLoadSeq) return

    if (mapResult.status === 'fulfilled') {
      const geometryRows = geometryResult.status === 'fulfilled' ? geometryResult.value : []
      applyYongchaMapPayload(mapResult.value || {}, geometryRows)
    } else {
      resetYongchaMapPayload()
      mapError.value = mapResult.reason?.response?.data?.detail || '용차 권역 지도를 불러오지 못했습니다.'
      nextTick(renderYongchaMap)
    }
  }).finally(() => {
    if (seq === reportLoadSeq) {
      mapLoading.value = false
    }
  })

  await reportPromise
}

const loadReportLegacy = async () => {
  loading.value = true
  mapLoading.value = true
  errorMessage.value = ''
  mapError.value = ''
  try {
    const response = await fetchOperationReport(buildParams())
    rows.value = response.data.results || []
    summary.value = {
      ...defaultSummary(),
      ...(response.data.summary || {}),
    }
  } catch (error) {
    rows.value = []
    summary.value = defaultSummary()
    errorMessage.value = error.response?.data?.detail || '운영현황을 불러오지 못했습니다.'
  } finally {
    loading.value = false
  }
  try {
    const response = await fetchOperationReportYongchaMap(buildParams())
    applyYongchaMapPayload(response.data || {})
  } catch (error) {
    yongchaMapRows.value = []
    yongchaMapSummary.value = {
      territory_count: 0,
      active_territory_count: 0,
      total_yongcha_records: 0,
      total_yongcha_visits: 0,
      total_yongcha_rounds: 0,
      max_yongcha_count: 0,
      top_territory: null,
      unmatched_region_count: 0,
    }
    mapError.value = error.response?.data?.detail || '용차 권역 지도를 불러오지 못했습니다.'
    nextTick(renderYongchaMap)
  } finally {
    mapLoading.value = false
  }
}

const escapeCsv = (value) => {
  const text = String(value ?? '')
  if (/[",\n]/.test(text)) return `"${text.replace(/"/g, '""')}"`
  return text
}

const operationReportFilename = (extension) =>
  `operation_report_${volumeMetric.value}_${normalizedStartDate.value}_${normalizedEndDate.value}.${extension}`

const downloadFormattedCsv = () => {
  const lines = []
  if (isSingleDayView.value) {
    lines.push([
      singleDayColumn.value?.label || normalizedStartDate.value,
      '',
      ...teamBlocks.value.map((team) => team.name),
    ])
    lines.push([
      singleDayColumn.value?.weekday || '',
      '',
      ...teamBlocks.value.map((team) => team.code || team.name),
    ])

    for (const line of sheetRows.value) {
      lines.push([
        line.spanLabel ? line.label : (line.firstInGroup ? line.group : ''),
        line.spanLabel ? '' : line.metric,
        ...teamBlocks.value.map((team) => getSingleDayTeamValue(team, line)),
      ])
    }
  } else {
  lines.push(['', '날짜 (배송일 기준)', '', '총계', ...dateColumns.value.map((day) => day.label)])
  lines.push(['', '요일 (배송일 기준)', '', '', ...dateColumns.value.map((day) => day.weekday)])

  for (const team of teamBlocks.value) {
    sheetRows.value.forEach((line, index) => {
      lines.push([
        index === 0 ? team.name : '',
        line.spanLabel ? line.label : (line.firstInGroup ? line.group : ''),
        line.spanLabel ? '' : line.metric,
        getTotalValue(team, line),
        ...dateColumns.value.map((day) => getSheetValue(team, day.key, line)),
      ])
    })
  }
  }

  const csv = `\ufeff${lines.map((line) => line.map(escapeCsv).join(',')).join('\n')}`
  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' })
  const url = window.URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = operationReportFilename('csv')
  document.body.appendChild(link)
  link.click()
  link.remove()
  window.URL.revokeObjectURL(url)
}

const downloadTablePng = async () => {
  if (!sheetTableCaptureEl.value || rows.value.length === 0 || pngDownloading.value) return

  pngDownloading.value = true
  try {
    await nextTick()
    const node = sheetTableCaptureEl.value
    const width = Math.ceil(Math.max(node.scrollWidth, node.offsetWidth))
    const height = Math.ceil(Math.max(node.scrollHeight, node.offsetHeight))
    const dataUrl = await toPng(node, {
      backgroundColor: '#ffffff',
      cacheBust: true,
      fontEmbedCSS: '',
      pixelRatio: 2,
      skipFonts: true,
      width,
      height,
      style: {
        width: `${width}px`,
        height: `${height}px`,
        maxWidth: 'none',
        overflow: 'visible',
      },
    })
    const link = document.createElement('a')
    link.href = dataUrl
    link.download = operationReportFilename('png')
    document.body.appendChild(link)
    link.click()
    link.remove()
  } catch (error) {
    console.error('Failed to download operation report PNG', error)
    alert('PNG 다운로드에 실패했습니다. 잠시 후 다시 시도해주세요.')
  } finally {
    pngDownloading.value = false
  }
}

watch(() => props.teamName, (teamName) => {
  selectedTeam.value = teamName || ''
  loadReport()
})

watch(selectedCompany, async () => {
  await loadShipperOptions()
  loadReport()
})

watch(selectedShipper, () => {
  loadReport()
})

onMounted(async () => {
  await nextTick()
  await loadShipperOptions()
  await initYongchaMap()
  await loadReport()
})

onBeforeUnmount(() => {
  clearYongchaFitTimers()
  if (yongchaResizeObserver) {
    yongchaResizeObserver.disconnect()
    yongchaResizeObserver = null
  }
  if (yongchaMap?.setTarget) {
    yongchaMap.setTarget(null)
  }
})
</script>

<style scoped>
.ops-hero {
  width: 100%;
  max-width: 100%;
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 24px;
  min-width: 0;
  padding: 22px;
  border: 1px solid #d7dde5;
  border-radius: 8px;
  background:
    linear-gradient(135deg, rgba(248, 250, 252, 0.96), rgba(255, 255, 255, 0.9)),
    linear-gradient(90deg, rgba(17, 24, 39, 0.08), rgba(200, 213, 48, 0.14));
}

.ops-eyebrow {
  color: #64748b;
  font-size: 13px;
  font-weight: 800;
  letter-spacing: 0;
}

.ops-toolbar {
  display: flex;
  align-items: flex-end;
  justify-content: flex-end;
  gap: 10px;
  flex-wrap: wrap;
  min-width: 0;
}

.ops-control {
  display: flex;
  flex-direction: column;
  gap: 6px;
  color: #64748b;
  font-size: 12px;
  font-weight: 800;
}

.ops-input {
  height: 42px;
  border: 1px solid #cfd7e3;
  border-radius: 8px;
  background: #ffffff;
  padding: 0 12px;
  color: #111827;
  outline: none;
}

.ops-input:focus {
  border-color: #8fa000;
  box-shadow: 0 0 0 3px rgba(200, 213, 48, 0.22);
}

.ops-presets {
  display: flex;
  gap: 4px;
  height: 42px;
  align-items: center;
  padding: 4px;
  border: 1px solid #d7dde5;
  border-radius: 8px;
  background: #ffffff;
}

.ops-presets button {
  height: 32px;
  padding: 0 10px;
  border-radius: 6px;
  color: #475569;
  font-size: 12px;
  font-weight: 800;
}

.ops-presets button:hover {
  background: #f1f5f9;
  color: #111827;
}

.ops-primary-btn,
.ops-dark-btn {
  height: 42px;
  display: inline-flex;
  align-items: center;
  gap: 7px;
  border-radius: 8px;
  padding: 0 15px;
  font-weight: 800;
}

.ops-primary-btn {
  background: #c8d530;
  color: #1f2937;
}

.ops-dark-btn {
  background: #111827;
  color: #ffffff;
}

.ops-png-btn {
  background: #334155;
}

.ops-primary-btn:disabled,
.ops-dark-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.ops-team-row {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px 16px;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  background: #ffffff;
}

.ops-team-label {
  min-width: 28px;
  color: #64748b;
  font-weight: 800;
}

.ops-panel {
  display: flex;
  flex-direction: column;
  gap: 20px;
  width: 100%;
  max-width: 100%;
  min-width: 0;
  overflow-x: hidden;
}

.ops-map {
  order: 20;
  width: 100%;
  max-width: 100%;
  min-width: 0;
  overflow: hidden;
  border: 1px solid #d7dde5;
  border-radius: 8px;
  background: #ffffff;
}

.map-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 18px 20px;
  border-bottom: 1px solid #e2e8f0;
  background: #fff7fb;
}

.map-kicker {
  color: #be123c;
  font-size: 12px;
  font-weight: 900;
}

.map-title {
  margin-top: 3px;
  color: #111827;
  font-size: 20px;
  font-weight: 900;
}

.map-summary {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 8px;
  flex-wrap: wrap;
}

.map-summary span,
.map-summary strong {
  border: 1px solid #fecdd3;
  border-radius: 999px;
  background: #ffffff;
  padding: 6px 10px;
  color: #881337;
  font-size: 12px;
  font-weight: 900;
}

.map-scroll-toggle {
  border: 1px solid #fecdd3;
  border-radius: 999px;
  background: #ffffff;
  padding: 6px 10px;
  color: #881337;
  font-size: 12px;
  font-weight: 900;
}

.map-scroll-toggle.active {
  border-color: #be123c;
  background: #be123c;
  color: #ffffff;
}

.map-body {
  position: relative;
  height: clamp(420px, 58vh, 680px);
  min-height: 420px;
  background: #eef2f7;
}

.ops-yongcha-map {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
}

.map-overlay {
  position: absolute;
  inset: 0;
  z-index: 6;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(255, 255, 255, 0.72);
  color: #475569;
  font-size: 13px;
  font-weight: 900;
  text-align: center;
}

.map-overlay > div {
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  background: #ffffff;
  padding: 10px 14px;
}

.map-legend {
  position: absolute;
  right: 16px;
  bottom: 16px;
  z-index: 5;
  display: flex;
  align-items: center;
  gap: 8px;
  border: 1px solid #fecdd3;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.96);
  padding: 8px 10px;
  color: #881337;
  font-size: 11px;
  font-weight: 900;
  box-shadow: 0 8px 20px rgba(15, 23, 42, 0.12);
}

.legend-steps {
  display: inline-flex;
  overflow: hidden;
  border: 1px solid #fecdd3;
  border-radius: 999px;
}

.legend-steps i {
  display: block;
  width: 18px;
  height: 12px;
}

.map-popup-shell {
  pointer-events: auto;
}

.map-popup {
  position: relative;
  width: min(340px, calc(100vw - 48px));
  max-height: 340px;
  overflow: hidden;
  border: 1px solid #fecdd3;
  border-radius: 10px;
  background: #ffffff;
  box-shadow: 0 16px 36px rgba(15, 23, 42, 0.2);
}

.map-popup::after {
  content: "";
  position: absolute;
  left: 50%;
  bottom: -8px;
  width: 14px;
  height: 14px;
  transform: translateX(-50%) rotate(45deg);
  border-right: 1px solid #fecdd3;
  border-bottom: 1px solid #fecdd3;
  background: #ffffff;
}

.map-popup header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  padding: 12px 14px 10px;
  border-bottom: 1px solid #ffe4e6;
  background: #fff7fb;
}

.map-popup header strong {
  display: block;
  color: #111827;
  font-size: 16px;
  font-weight: 900;
}

.map-popup header span {
  display: block;
  margin-top: 2px;
  color: #be123c;
  font-size: 11px;
  font-weight: 900;
}

.map-popup header button {
  flex: 0 0 auto;
  border: 1px solid #fecdd3;
  border-radius: 7px;
  background: #ffffff;
  padding: 5px 8px;
  color: #881337;
  font-size: 11px;
  font-weight: 900;
}

.map-popup-total {
  padding: 10px 14px;
  color: #881337;
  font-size: 13px;
  font-weight: 900;
}

.map-popup-days {
  max-height: 226px;
  overflow-y: auto;
  border-top: 1px solid #ffe4e6;
}

.map-popup-days section {
  padding: 10px 14px;
  border-top: 1px solid #fff1f2;
}

.map-popup-days section:first-child {
  border-top: 0;
}

.map-popup-days section > strong {
  display: block;
  margin-bottom: 6px;
  color: #111827;
  font-size: 12px;
  font-weight: 900;
}

.map-popup-round {
  display: grid;
  grid-template-columns: 58px minmax(0, 1fr);
  gap: 8px;
  align-items: start;
  margin-top: 5px;
}

.map-popup-round span {
  border-radius: 999px;
  background: #fee2e2;
  padding: 3px 6px;
  color: #991b1b;
  font-size: 10px;
  font-weight: 900;
  text-align: center;
}

.map-popup-round p {
  min-width: 0;
  color: #334155;
  font-size: 12px;
  font-weight: 800;
  line-height: 1.45;
  white-space: normal;
  word-break: keep-all;
}

.map-popup-empty {
  border-top: 1px solid #ffe4e6;
  padding: 12px 14px;
  color: #94a3b8;
  font-size: 12px;
  font-weight: 800;
}

.ops-chart {
  width: 100%;
  max-width: 100%;
  min-width: 0;
  overflow: hidden;
  border: 1px solid #d7dde5;
  border-radius: 8px;
  background: #ffffff;
}

.chart-header {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 16px;
  padding: 18px 20px 12px;
  border-bottom: 1px solid #e2e8f0;
}

.ops-chart.collapsed .chart-header {
  align-items: center;
  padding-bottom: 18px;
  border-bottom: 0;
}

.chart-actions {
  display: flex;
  align-items: flex-end;
  justify-content: flex-end;
  gap: 10px;
  flex-wrap: wrap;
}

.chart-toggle {
  height: 42px;
  min-width: 64px;
  border: 1px solid #cfd7e3;
  border-radius: 8px;
  background: #111827;
  color: #ffffff;
  padding: 0 14px;
  font-size: 13px;
  font-weight: 900;
}

.chart-kicker {
  color: #64748b;
  font-size: 12px;
  font-weight: 900;
}

.chart-title {
  margin-top: 3px;
  color: #111827;
  font-size: 20px;
  font-weight: 900;
}

.chart-canvas {
  width: 100%;
  max-width: 100%;
  overflow: hidden;
  min-width: 0;
  padding: 16px 20px 18px;
}

.chart-canvas svg {
  display: block;
  width: 100%;
  max-width: 1180px;
  margin: 0 auto;
  min-width: 0;
  height: clamp(320px, 34vw, 380px);
}

.chart-grid line {
  stroke: #e2e8f0;
  stroke-width: 1;
}

.chart-grid text,
.chart-x-label {
  fill: #64748b;
  font-size: 11px;
  font-weight: 800;
}

.chart-line {
  fill: none;
  stroke: #111827;
  stroke-width: 3;
  stroke-linecap: round;
  stroke-linejoin: round;
}

.chart-point {
  fill: #c8d530;
  stroke: #111827;
  stroke-width: 2;
}

.chart-summary {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 12px;
  max-width: 1180px;
  margin: 8px auto 0;
  color: #64748b;
  font-size: 12px;
  font-weight: 800;
}

.chart-summary strong {
  color: #111827;
  font-size: 16px;
  font-weight: 900;
}

.chart-empty {
  padding: 44px 20px;
  color: #94a3b8;
  text-align: center;
  font-weight: 800;
}

.sheet-shell {
  width: 100%;
  max-width: 100%;
  min-width: 0;
  overflow: hidden;
  border: 1px solid #d7dde5;
  border-radius: 8px;
  background: #ffffff;
}

.sheet-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 18px 20px;
  border-bottom: 1px solid #e2e8f0;
  background: #f8fafc;
}

.sheet-kicker {
  color: #64748b;
  font-size: 12px;
  font-weight: 900;
}

.sheet-title {
  margin-top: 3px;
  color: #111827;
  font-size: 20px;
  font-weight: 900;
}

.sheet-side {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 10px;
  flex-wrap: wrap;
}

.volume-toggle {
  display: inline-flex;
  gap: 4px;
  padding: 4px;
  border: 1px solid #d7dde5;
  border-radius: 8px;
  background: #ffffff;
}

.volume-toggle button {
  height: 30px;
  min-width: 54px;
  border-radius: 6px;
  padding: 0 10px;
  color: #64748b;
  font-size: 12px;
  font-weight: 900;
}

.volume-toggle button.active {
  background: #111827;
  color: #ffffff;
}

.sheet-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.sheet-meta span {
  border: 1px solid #d7dde5;
  border-radius: 999px;
  background: #ffffff;
  padding: 6px 10px;
  color: #475569;
  font-size: 12px;
  font-weight: 800;
}

.date-strip-shell {
  width: 100%;
  max-width: 100%;
  overflow-x: auto;
  scrollbar-gutter: stable both-edges;
  border-bottom: 1px solid #e2e8f0;
  background: #ffffff;
}

.date-strip {
  display: flex;
  gap: 8px;
  width: max-content;
  min-width: 100%;
  padding: 14px 16px;
}

.date-chip {
  min-width: 88px;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 9px 10px;
  background: #f8fafc;
  flex: 0 0 auto;
}

.date-chip.compact {
  min-width: 76px;
  padding: 8px 9px;
}

.date-chip.active {
  border-color: #c8d530;
  background: #fbfdec;
}

.date-chip span,
.date-chip small {
  display: block;
  color: #64748b;
  font-size: 11px;
  font-weight: 800;
}

.date-chip strong {
  display: block;
  margin: 4px 0;
  color: #111827;
  font-size: 16px;
  font-weight: 900;
}

.date-chip.compact strong {
  font-size: 14px;
}

.sheet-scroll {
  width: 100%;
  overflow-x: auto;
  overflow-y: hidden;
  max-width: 100%;
  background: #eef2f7;
  scrollbar-gutter: stable both-edges;
  overscroll-behavior-x: contain;
}

.sheet-table-wrap {
  display: inline-block;
  width: max-content;
  min-width: 100%;
  padding: 14px;
  box-sizing: border-box;
  --ops-team-col-width: 76px;
  --ops-label-col-width: 94px;
  --ops-left-label-width: 188px;
  --ops-total-col-width: 112px;
}

.sheet-table-wrap.single-day-sheet {
  --ops-team-col-width: 0px;
  --ops-total-col-width: 0px;
}

.operation-sheet {
  border-collapse: collapse;
  table-layout: fixed;
  min-width: 100%;
  width: auto;
  color: #111827;
  font-size: 12px;
  border: 1px solid #cbd5e1;
  box-shadow: 0 8px 20px rgba(15, 23, 42, 0.08);
}

.operation-sheet th,
.operation-sheet td {
  border: 1px solid #d7dde5;
  height: 32px;
  padding: 5px 8px;
  white-space: nowrap;
  vertical-align: middle;
  background: #ffffff;
}

.operation-sheet thead th {
  position: sticky;
  top: 0;
  z-index: 2;
  background: #e9eef6;
  color: #334155;
  font-weight: 900;
}

.operation-sheet .team-col,
.operation-sheet .team-cell,
.operation-sheet .label-col,
.operation-sheet .label-cell,
.operation-sheet .round-cell,
.operation-sheet .metric-cell,
.operation-sheet .total-col,
.operation-sheet .total-cell {
  position: sticky;
}

.team-col,
.team-cell {
  left: 0;
  width: var(--ops-team-col-width);
  min-width: var(--ops-team-col-width);
  text-align: left;
  font-weight: 900;
  z-index: 4;
}

.label-col,
.label-cell {
  left: var(--ops-team-col-width);
  width: var(--ops-left-label-width);
  min-width: var(--ops-left-label-width);
  text-align: left;
  z-index: 4;
}

.round-cell {
  left: var(--ops-team-col-width);
  width: var(--ops-label-col-width);
  min-width: var(--ops-label-col-width);
  text-align: left;
  background: #eef6f8 !important;
  color: #0f766e;
  font-weight: 900;
  z-index: 4;
}

.metric-cell {
  left: calc(var(--ops-team-col-width) + var(--ops-label-col-width));
  width: var(--ops-label-col-width);
  min-width: var(--ops-label-col-width);
  text-align: left;
  background: #fbfdff !important;
  color: #475569;
  font-weight: 800;
  z-index: 4;
}

.total-col,
.total-cell {
  left: calc(var(--ops-team-col-width) + var(--ops-left-label-width));
  width: var(--ops-total-col-width);
  min-width: var(--ops-total-col-width);
  text-align: right;
  z-index: 4;
}

.total-col {
  background: #e9eef6 !important;
  color: #111827;
  font-weight: 900;
}

.total-cell {
  background: #f8fafc !important;
  color: #111827;
  font-variant-numeric: tabular-nums;
  font-weight: 900;
}

.date-col,
.value-cell {
  width: var(--ops-day-col-width, 112px);
  min-width: var(--ops-day-col-width, 112px);
  text-align: right;
}

.single-day-sheet .date-col {
  overflow: hidden;
  text-align: center;
  text-overflow: ellipsis;
}

.single-day-sheet .value-cell {
  font-size: 11px;
}

.weekday-col {
  color: #64748b;
}

.team-cell {
  background: #111827 !important;
  color: #ffffff;
  vertical-align: top;
  z-index: 5;
}

.team-cell span {
  display: inline-flex;
  margin-top: 4px;
  border-radius: 6px;
  background: rgba(255, 255, 255, 0.1);
  padding: 5px 7px;
}

.label-cell {
  background: #fbfdec !important;
  color: #334155;
  font-weight: 900;
}

.operation-sheet thead .team-col,
.operation-sheet thead .label-col,
.operation-sheet thead .total-col {
  z-index: 7;
}

.label-col,
.label-cell,
.metric-cell,
.total-col,
.total-cell {
  box-shadow: 6px 0 10px -8px rgba(15, 23, 42, 0.58);
}

.summary-line .total-cell,
.summary-line .value-cell {
  background: #fffef7;
  font-weight: 800;
}

.block-start td {
  border-top-width: 2px;
  border-top-color: #94a3b8;
}

.value-cell {
  color: #111827;
  font-variant-numeric: tabular-nums;
  font-weight: 800;
}

.operation-sheet tr.yongcha-line .label-cell,
.operation-sheet tr.yongcha-line .round-cell,
.operation-sheet tr.yongcha-line .metric-cell,
.operation-sheet tr.yongcha-line .total-cell,
.operation-sheet tr.yongcha-line .value-cell {
  color: #dc2626;
}

.empty-cell {
  background: #f8fafc !important;
  color: transparent;
}

.percent-cell {
  text-align: right;
}

@media (max-width: 1024px) {
  .ops-hero {
    align-items: stretch;
    flex-direction: column;
  }

  .ops-toolbar {
    justify-content: flex-start;
  }
}

@media (max-width: 640px) {
  .sheet-header {
    align-items: flex-start;
    flex-direction: column;
  }

  .sheet-side {
    justify-content: flex-start;
    width: 100%;
  }

  .chart-header {
    align-items: flex-start;
    flex-direction: column;
  }

  .chart-canvas svg {
    height: 260px;
  }
}
</style>
