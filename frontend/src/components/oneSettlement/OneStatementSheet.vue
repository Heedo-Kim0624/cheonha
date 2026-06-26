<template>
  <div class="space-y-5">
    <div class="flex flex-wrap items-end gap-3 rounded-xl border border-slate-200 bg-slate-50 p-4">
      <label class="block">
        <span class="mb-1 block text-sm font-bold text-slate-600">지급 예정일</span>
        <input
          v-model="dueDate"
          type="date"
          class="rounded-lg border border-slate-300 bg-white px-3 py-2 font-semibold outline-none focus:border-primary"
        />
      </label>
      <div class="ml-auto flex gap-2">
        <button type="button" class="rounded-lg border border-slate-300 bg-white px-4 py-2 font-bold" @click="$emit('download-excel')">
          Excel
        </button>
        <button type="button" class="rounded-lg border border-slate-300 bg-white px-4 py-2 font-bold" @click="$emit('download-pdf')">
          PDF
        </button>
      </div>
    </div>

    <div class="rounded-xl border border-slate-200 bg-white p-4">
      <div class="mb-3 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h4 class="font-extrabold text-slate-900">상계 건 추가</h4>
          <p class="mt-1 text-sm text-slate-500">
            운송장번호, 사유, 금액, 상품명을 행 단위로 입력하면 명세서 우측 상단과 사고귀책 상계건에 반영됩니다.
          </p>
        </div>
        <div class="text-right text-sm">
          <div class="font-bold text-slate-900">{{ offsetRows.length.toLocaleString('ko-KR') }}건</div>
          <div :class="offsetTotal < 0 ? 'text-red-600' : 'text-slate-600'">{{ formatPlainNumber(offsetTotal) }}원</div>
        </div>
      </div>
      <div class="overflow-x-auto rounded-lg border border-slate-200">
        <table class="w-full min-w-[980px] border-collapse text-sm">
          <thead class="bg-slate-50 text-left text-xs font-extrabold uppercase tracking-wide text-slate-500">
            <tr>
              <th class="w-[180px] border-b border-slate-200 px-3 py-2">운송장번호</th>
              <th class="w-[150px] border-b border-slate-200 px-3 py-2">사유</th>
              <th class="w-[140px] border-b border-slate-200 px-3 py-2 text-right">금액</th>
              <th class="border-b border-slate-200 px-3 py-2">상품명</th>
              <th class="w-[88px] border-b border-slate-200 px-3 py-2 text-center">관리</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(row, index) in offsetDraftRows" :key="row.key" class="border-b border-slate-100 last:border-b-0">
              <td class="px-2 py-2">
                <input
                  v-model="row.waybill"
                  class="w-full rounded-md border border-slate-300 px-2 py-2 font-mono outline-none focus:border-primary"
                  placeholder="5056-5534-0946"
                />
              </td>
              <td class="px-2 py-2">
                <input
                  v-model="row.reason"
                  class="w-full rounded-md border border-slate-300 px-2 py-2 outline-none focus:border-primary"
                  placeholder="배송누락"
                />
              </td>
              <td class="px-2 py-2">
                <input
                  v-model="row.amount"
                  class="w-full rounded-md border border-slate-300 px-2 py-2 text-right font-mono outline-none focus:border-primary"
                  placeholder="-21,214"
                  inputmode="numeric"
                />
              </td>
              <td class="px-2 py-2">
                <input
                  v-model="row.product"
                  class="w-full rounded-md border border-slate-300 px-2 py-2 outline-none focus:border-primary"
                  placeholder="[SSGX치플레] 수플레 치즈케이크"
                />
              </td>
              <td class="px-2 py-2 text-center">
                <button
                  type="button"
                  class="rounded-md border border-slate-300 bg-white px-3 py-2 text-xs font-bold text-slate-700 disabled:opacity-40"
                  :disabled="offsetDraftRows.length <= 1"
                  @click="removeOffsetRow(index)"
                >
                  삭제
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <p v-if="offsetError" class="mt-2 text-sm font-semibold text-red-600">{{ offsetError }}</p>
      <div class="mt-3 flex flex-wrap justify-end gap-2">
        <button type="button" class="rounded-lg border border-slate-300 bg-white px-4 py-2 font-bold" @click="addOffsetRow">
          행 추가
        </button>
        <button type="button" class="rounded-lg border border-slate-300 bg-white px-4 py-2 font-bold" @click="clearOffsetItems">
          상계 건 삭제
        </button>
        <button
          type="button"
          class="rounded-lg bg-primary px-5 py-2 font-bold text-white disabled:opacity-50"
          :disabled="saving"
          @click="save"
        >
          {{ saving ? '저장 중...' : '저장' }}
        </button>
      </div>
    </div>

    <div class="one-statement-sheet overflow-x-auto rounded-xl border border-slate-200 bg-white p-6">
      <div class="statement-template-grid">
        <div
          v-for="cell in templateCells"
          :key="cell.key"
          class="statement-template-cell"
          :class="cell.className"
          :style="cellStyle(cell)"
        >
          <input
            v-if="cell.editKey"
            class="statement-template-input"
            type="number"
            :value="manualAmount(cell.editKey)"
            @click.stop
            @input="setManualAmount(cell.editKey, $event.target.value)"
          />
          <template v-else>
            {{ cell.value }}
          </template>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, ref, watch } from 'vue'

const props = defineProps({
  statement: { type: Object, required: true },
  saving: { type: Boolean, default: false },
})

const emit = defineEmits(['save', 'download-excel', 'download-pdf'])

const serviceOrder = ['W12_DAY', 'N3_DAY', 'W4_DAWN']
const serviceLabels = {
  W12_DAY: 'W1,2_당일',
  N3_DAY: 'N3_당일',
  W4_DAWN: 'W4_새벽',
}
const categoryLabels = {
  SSG: 'SSG',
  COMMON: '공동배송',
  TRADERS: '트레이더스',
  YES24: 'YES24',
}
const templateStatementOrder = [
  ['W12_DAY', 'SSG'],
  ['W12_DAY', 'COMMON'],
  ['W12_DAY', 'TRADERS'],
  ['W12_DAY', 'YES24'],
  ['N3_DAY', 'SSG'],
  ['N3_DAY', 'YES24'],
  ['W4_DAWN', 'SSG'],
  ['W4_DAWN', 'COMMON'],
  ['W4_DAWN', 'YES24'],
]
const weekdayLabels = ['일', '월', '화', '수', '목', '금', '토']
const OFFSET_LABEL = '사고귀책 상계건'
const OFFSET_SOURCE = 'one_offset_items'
let offsetRowSequence = 0

const dueDate = ref(props.statement.payment_due_date)
const memo = ref(props.statement.memo || '')
const manualItems = ref(normalizeManualItems(props.statement.manual_items || []))
const offsetDraftRows = ref(makeOffsetDraftRows(manualItems.value))
const offsetError = ref('')

watch(
  () => props.statement,
  (next) => {
    dueDate.value = next.payment_due_date
    memo.value = next.memo || ''
    manualItems.value = normalizeManualItems(next.manual_items || [])
    offsetDraftRows.value = makeOffsetDraftRows(manualItems.value)
    offsetError.value = ''
  },
)

watch(
  offsetDraftRows,
  () => {
    applyOffsetDraft(false)
  },
  { deep: true },
)

const monthTitle = computed(() => {
  const [year, month] = String(props.statement.month || '').split('-')
  return `${year || ''}년 ${Number(month || 0)}월`
})

const periodText = computed(() => `${formatCompactDate(props.statement.period_start)} 부터 ${formatCompactDate(props.statement.period_end)} 까지`)
const dueDateText = computed(() => formatKoreanDate(dueDate.value))

const summaryRows = computed(() => {
  let previousService = ''
  return (props.statement.summary_rows || []).map((row) => {
    const serviceCode = row.service_code
    const isServiceStart = serviceCode !== previousService
    previousService = serviceCode
    return {
      ...row,
      key: `${row.service_code}:${row.category_code}`,
      serviceLabel: serviceLabels[row.service_code] || row.service_label || row.service_code,
      categoryLabel: row.category_label || row.category_code,
      isServiceStart,
    }
  })
})

const dailyByDate = computed(() => {
  const lookup = new Map()
  for (const row of props.statement.daily_rows || []) {
    lookup.set(row.date, row.values || {})
  }
  return lookup
})

const dailyMatrixRows = computed(() => {
  const start = parseDate(props.statement.period_start)
  const end = parseDate(props.statement.period_end)
  if (!start || !end) return []
  const rows = []
  const cursor = new Date(start)
  while (cursor <= end) {
    const date = toIsoDate(cursor)
    rows.push({ date, values: dailyByDate.value.get(date) || {} })
    cursor.setDate(cursor.getDate() + 1)
  }
  return rows
})

const summaryByKey = computed(() => {
  const lookup = new Map()
  for (const row of props.statement.summary_rows || []) {
    lookup.set(`${row.service_code}:${row.category_code}`, row)
  }
  return lookup
})

const offsetRows = computed(() => {
  const rows = []
  for (const item of manualItems.value) {
    if (!isOffsetItem(item)) continue
    for (const row of item.rows || []) {
      rows.push({
        waybill: String(row.waybill || '').trim(),
        reason: String(row.reason || '').trim(),
        amount: Number(row.amount || 0),
        product: String(row.product || '').trim(),
      })
    }
  }
  return rows
})

const offsetTotal = computed(() => offsetRows.value.reduce((sum, row) => sum + Number(row.amount || 0), 0))

const manualTotal = computed(() => manualItems.value.reduce((sum, item) => sum + Number(item.amount || 0), 0))

const calculatedStatementTotal = computed(() => {
  if (props.statement.calculated_total !== undefined && props.statement.calculated_total !== null) {
    return Number(props.statement.calculated_total || 0)
  }
  return Number(props.statement.total_amount || 0) - Number(props.statement.manual_total || 0)
})

const statementTotal = computed(() => calculatedStatementTotal.value + manualTotal.value)

const templateCells = computed(() => {
  const cells = []
  const occupied = new Set()
  const addCell = (row, col, value = '', options = {}) => {
    const rowspan = options.rowspan || 1
    const colspan = options.colspan || 1
    for (let r = row; r < row + rowspan; r += 1) {
      for (let c = col; c < col + colspan; c += 1) {
        occupied.add(`${r}:${c}`)
      }
    }
    cells.push({
      key: `${row}:${col}`,
      row,
      col,
      rowspan,
      colspan,
      value,
      className: options.className || '',
      editKey: options.editKey || '',
    })
  }
  const fillRange = (startRow, startCol, endRow, endCol, className = 'bordered') => {
    for (let row = startRow; row <= endRow; row += 1) {
      for (let col = startCol; col <= endCol; col += 1) {
        if (!occupied.has(`${row}:${col}`)) {
          addCell(row, col, '', { className })
        }
      }
    }
  }

  addCell(1, 1, monthTitle.value, { colspan: 4, className: 'month-title bold' })
  addCell(2, 1, '운송료 지급명세서', { colspan: 5, className: 'sheet-title bold' })
  addCell(4, 1, '수수료 명.', { className: 'label bold' })
  addCell(4, 2, 'CJ 대한통운 ONE 배송건', { colspan: 5, className: 'label-value bold' })
  addCell(5, 1, '지급 대상자.', { className: 'label bold' })
  addCell(5, 2, props.statement.driver?.name || '-', { colspan: 5, className: 'label-value bold' })
  addCell(6, 1, '정산 기간일.', { className: 'label bold' })
  addCell(6, 2, periodText.value, { colspan: 5, className: 'label-value bold' })
  addCell(7, 1, '지급 예정일.', { className: 'label bold' })
  addCell(7, 2, dueDateText.value, { colspan: 5, className: 'label-value bold' })

  addCell(9, 1, '지급내역', { colspan: 9, className: 'bordered black center bold' })
  addCell(10, 2, '구 분', { colspan: 2, className: 'bordered center bold' })
  addCell(10, 4, '착지 / 건', { colspan: 2, className: 'bordered center bold' })
  addCell(10, 6, '추가박스', { colspan: 2, className: 'bordered center bold' })
  addCell(10, 8, '금액 (부가세 포함)', { colspan: 2, className: 'bordered center bold' })
  addCell(11, 1, '전체 운송료', { rowspan: 9, className: 'bordered center bold' })
  addCell(11, 2, 'W1,2_당일', { rowspan: 4, className: 'bordered center bold service-start' })
  addCell(15, 2, 'N3_당일', { rowspan: 2, className: 'bordered center bold service-start' })
  addCell(17, 2, 'W4_새벽', { rowspan: 3, className: 'bordered center bold service-start' })

  for (let index = 0; index < templateStatementOrder.length; index += 1) {
    const [serviceCode, categoryCode] = templateStatementOrder[index]
    const row = 11 + index
    const data = summaryByKey.value.get(`${serviceCode}:${categoryCode}`) || {
      service_code: serviceCode,
      category_code: categoryCode,
      category_label: categoryLabels[categoryCode] || categoryCode,
      households: 0,
      extra_boxes: 0,
      amount: 0,
    }
    const serviceStartClass = [0, 4, 6].includes(index) ? ' service-start' : ''
    addCell(row, 3, data.category_label || categoryLabels[categoryCode] || categoryCode, { className: `bordered${serviceStartClass}` })
    addCell(row, 4, formatNumber(data.households), { colspan: 2, className: `bordered right${serviceStartClass}` })
    addCell(row, 6, formatExtraBox(data), { colspan: 2, className: `bordered right${serviceStartClass}` })
    addCell(row, 8, formatPlainNumber(data.amount), { colspan: 2, className: `bordered right${serviceStartClass}` })
  }

  addCell(20, 2, '통 합', { className: 'bordered center bold' })
  addCell(20, 3, '생수', { className: 'bordered' })
  addCell(20, 4, '0', { colspan: 2, className: 'bordered right' })
  addCell(20, 6, '0', { colspan: 2, className: 'bordered right' })
  addCell(20, 8, formatPlainNumber(manualAmount('생수')), { colspan: 2, className: 'bordered right' })
  addCell(21, 2, '운송료 외', { rowspan: 2, className: 'bordered center bold' })
  addCell(21, 3, '추가 전달', { className: 'bordered' })
  addCell(21, 4, '0', { colspan: 2, className: 'bordered right' })
  addCell(21, 6, '-', { colspan: 2, className: 'bordered right' })
  addCell(21, 8, formatPlainNumber(manualAmount('추가 전달')), { colspan: 2, className: 'bordered right' })
  addCell(22, 3, '수당', { className: 'bordered' })
  addCell(22, 4, '-', { colspan: 2, className: 'bordered right' })
  addCell(22, 6, '-', { colspan: 2, className: 'bordered right' })
  addCell(22, 8, formatPlainNumber(manualAmount('수당')), { colspan: 2, className: 'bordered right' })
  addCell(23, 1, '사고귀책 상계건', { colspan: 3, className: 'bordered gray center bold' })
  addCell(23, 7, '-', { className: 'bordered gray right' })
  addCell(23, 8, formatPlainNumber(manualAmount('사고귀책')), { colspan: 2, className: 'bordered gray right' })
  addCell(24, 1, '', { colspan: 9, className: 'bordered black spacer' })
  addCell(25, 1, '지급 합계', { colspan: 3, className: 'bordered center bold total' })
  addCell(25, 8, formatPlainNumber(statementTotal.value), { colspan: 2, className: 'bordered right bold total' })
  fillRange(9, 1, 25, 9)

  const displayedOffsetRows = offsetRows.value.slice(0, 24)
  displayedOffsetRows.forEach((row, index) => {
    const gridRow = index + 1
    addCell(gridRow, 10, row.waybill, { colspan: 2, className: 'offset-cell' })
    addCell(gridRow, 12, row.reason, { className: 'offset-cell' })
    addCell(gridRow, 13, formatPlainNumber(row.amount), { className: 'offset-cell right' })
    addCell(gridRow, 14, row.product, { colspan: 2, className: 'offset-cell offset-product' })
  })
  if (offsetRows.value.length > displayedOffsetRows.length) {
    addCell(25, 10, `외 ${formatPlainNumber(offsetRows.value.length - displayedOffsetRows.length)}건`, { colspan: 5, className: 'offset-cell offset-muted' })
  }
  if (offsetRows.value.length) {
    addCell(26, 13, formatPlainNumber(offsetTotal.value), { colspan: 2, className: 'offset-cell offset-total right' })
  }

  addCell(27, 1, '일 자', { rowspan: 3, className: 'bordered black center bold' })
  addCell(27, 2, '구 분', { className: 'bordered center bold' })
  addCell(27, 3, 'W1.2_당일', { colspan: 5, className: 'bordered black center bold' })
  addCell(27, 8, '구 분', { className: 'bordered center bold' })
  addCell(27, 9, 'N3_당일', { colspan: 2, className: 'bordered black center bold' })
  addCell(27, 11, '구 분', { className: 'bordered center bold' })
  addCell(27, 12, '4W_새벽', { colspan: 4, className: 'bordered black center bold' })
  addCell(28, 2, 'SSG', { colspan: 2, className: 'bordered center bold' })
  addCell(28, 4, '트레이더스', { colspan: 2, className: 'bordered center bold' })
  addCell(28, 6, '공동배송', { className: 'bordered center bold' })
  addCell(28, 7, 'YES24', { className: 'bordered center bold' })
  addCell(28, 8, 'SSG', { colspan: 2, className: 'bordered center bold' })
  addCell(28, 10, 'YES24', { className: 'bordered center bold' })
  addCell(28, 11, 'SSG', { colspan: 2, className: 'bordered center bold' })
  addCell(28, 13, '공동배송', { colspan: 2, className: 'bordered center bold' })
  addCell(28, 15, 'YES24', { className: 'bordered center bold' })
  const dailyHeaders = [
    '착지/건', '추가박스', '착지/건', '추가박스', '착지/건', '착지 / 건',
    '착지/건', '추가박스', '착지 / 건', '착지/건', '추가박스', '착지/건',
    '추가박스', '착지 / 건',
  ]
  dailyHeaders.forEach((label, offset) => {
    addCell(29, offset + 2, label, { className: 'bordered center bold small' })
  })

  for (const row of dailyMatrixRows.value) {
    const day = Number(String(row.date || '').slice(-2))
    if (!day) continue
    const gridRow = 29 + day
    addCell(gridRow, 1, formatShortDate(row.date), { className: 'bordered center date-cell' })
    const values = [
      cellValue(row, 'W12_DAY:SSG', 'households'),
      cellValue(row, 'W12_DAY:SSG', 'extra_boxes'),
      cellValue(row, 'W12_DAY:TRADERS', 'households'),
      cellValue(row, 'W12_DAY:TRADERS', 'extra_boxes'),
      cellValue(row, 'W12_DAY:COMMON', 'households'),
      cellValue(row, 'W12_DAY:YES24', 'households'),
      cellValue(row, 'N3_DAY:SSG', 'households'),
      cellValue(row, 'N3_DAY:SSG', 'extra_boxes'),
      cellValue(row, 'N3_DAY:YES24', 'households'),
      cellValue(row, 'W4_DAWN:SSG', 'households'),
      cellValue(row, 'W4_DAWN:SSG', 'extra_boxes'),
      cellValue(row, 'W4_DAWN:COMMON', 'households'),
      cellValue(row, 'W4_DAWN:COMMON', 'extra_boxes'),
      cellValue(row, 'W4_DAWN:YES24', 'households'),
    ]
    values.forEach((value, offset) => {
      addCell(gridRow, offset + 2, value, { className: 'bordered right' })
    })
  }
  fillRange(27, 1, 60, 15)

  return cells
})

function cellStyle(cell) {
  return {
    gridColumn: `${cell.col} / span ${cell.colspan}`,
    gridRow: `${cell.row} / span ${cell.rowspan}`,
  }
}

function parseDate(value) {
  if (!value) return null
  const date = new Date(`${value}T00:00:00`)
  return Number.isNaN(date.getTime()) ? null : date
}

function toIsoDate(date) {
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

function formatNumber(value) {
  return Number(value || 0).toLocaleString('ko-KR')
}

function formatPlainNumber(value) {
  return Number(value || 0).toLocaleString('ko-KR')
}

function formatCompactDate(value) {
  const date = parseDate(value)
  if (!date) return '-'
  return `${String(date.getFullYear()).slice(2)}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`
}

function formatShortDate(value) {
  const date = parseDate(value)
  if (!date) return value || '-'
  return `${formatCompactDate(value)}-${weekdayLabels[date.getDay()]}`
}

function formatKoreanDate(value) {
  const date = parseDate(value)
  if (!date) return '-'
  return `${date.getFullYear()}년 ${date.getMonth() + 1}월 ${date.getDate()}일`
}

function formatExtraBox(row) {
  if (row.category_code === 'YES24') return '-'
  if (row.service_code === 'W12_DAY' && row.category_code === 'COMMON') return '-'
  if (row.service_code === 'N3_DAY' && row.category_code === 'YES24') return '-'
  return formatNumber(row.extra_boxes)
}

function normalizeManualItems(items) {
  return (items || []).map((item) => ({
    ...item,
    amount: Number(item.amount || 0),
    rows: Array.isArray(item.rows)
      ? item.rows.map((row) => ({
        waybill: String(row.waybill || '').trim(),
        reason: String(row.reason || '').trim(),
        amount: Number(row.amount || 0),
        product: String(row.product || '').trim(),
      }))
      : undefined,
  }))
}

function createOffsetDraftRow(row = {}) {
  offsetRowSequence += 1
  const amount = row.amount === undefined || row.amount === null || row.amount === 0 ? '' : formatPlainNumber(row.amount)
  return {
    key: `offset-row-${offsetRowSequence}`,
    waybill: String(row.waybill || '').trim(),
    reason: String(row.reason || '').trim(),
    amount,
    product: String(row.product || '').trim(),
  }
}

function makeOffsetDraftRows(items) {
  const rows = []
  for (const item of items || []) {
    if (!isOffsetItem(item)) continue
    for (const row of item.rows || []) {
      rows.push(createOffsetDraftRow(row))
    }
  }
  return rows.length ? rows : [createOffsetDraftRow()]
}

function isOffsetItem(item) {
  return item?.source === OFFSET_SOURCE || String(item?.label || '').includes(OFFSET_LABEL)
}

function manualAmount(keyword) {
  return manualItems.value
    .filter((item) => String(item.label || '').includes(keyword))
    .reduce((sum, item) => sum + Number(item.amount || 0), 0)
}

function setManualAmount(label, rawValue) {
  const amount = Number(rawValue || 0)
  const next = manualItems.value.filter((item) => !String(item.label || '').includes(label))
  if (amount !== 0) {
    next.push({ label, amount })
  }
  manualItems.value = next
}

function cellValue(row, key, field) {
  return formatNumber(row.values?.[key]?.[field] || 0)
}

function parseOffsetAmount(rawValue) {
  const normalized = String(rawValue || '').replace(/,/g, '').trim()
  if (!normalized) return 0
  const amount = Number(normalized)
  if (!Number.isFinite(amount)) {
    throw new Error(`금액을 숫자로 읽을 수 없습니다: ${rawValue}`)
  }
  return amount
}

function draftRowsToOffsetRows({ strict = false } = {}) {
  const rows = []
  offsetDraftRows.value.forEach((row, index) => {
    const waybill = String(row.waybill || '').trim()
    const reason = String(row.reason || '').trim()
    const amountText = String(row.amount || '').trim()
    const product = String(row.product || '').trim()
    const hasAnyValue = Boolean(waybill || reason || amountText || product)
    if (!hasAnyValue) return
    if (strict && (!waybill || !reason || !amountText || !product)) {
      throw new Error(`${index + 1}번째 행은 운송장번호, 사유, 금액, 상품명을 모두 입력해야 합니다.`)
    }
    const amount = parseOffsetAmount(amountText)
    if (strict && amount === 0) {
      throw new Error(`${index + 1}번째 행의 금액은 0원이 아닌 숫자로 입력해야 합니다.`)
    }
    rows.push({ waybill, reason, amount, product })
  })
  return rows
}

function setOffsetRows(rows) {
  const normalizedRows = rows.map((row) => ({
    waybill: String(row.waybill || '').trim(),
    reason: String(row.reason || '').trim(),
    amount: Number(row.amount || 0),
    product: String(row.product || '').trim(),
  }))
  const next = manualItems.value.filter((item) => !isOffsetItem(item))
  const amount = normalizedRows.reduce((sum, row) => sum + Number(row.amount || 0), 0)
  if (normalizedRows.length) {
    next.push({
      label: OFFSET_LABEL,
      source: OFFSET_SOURCE,
      amount,
      rows: normalizedRows,
    })
  }
  manualItems.value = next
}

function applyOffsetDraft(strict = false) {
  offsetError.value = ''
  try {
    setOffsetRows(draftRowsToOffsetRows({ strict }))
    return true
  } catch (error) {
    offsetError.value = error?.message || '상계 건 입력값을 확인해 주세요.'
    return false
  }
}

function addOffsetRow() {
  offsetDraftRows.value.push(createOffsetDraftRow())
}

function removeOffsetRow(index) {
  offsetDraftRows.value.splice(index, 1)
  if (!offsetDraftRows.value.length) {
    offsetDraftRows.value.push(createOffsetDraftRow())
  }
}

function clearOffsetItems() {
  offsetError.value = ''
  offsetDraftRows.value = [createOffsetDraftRow()]
  setOffsetRows([])
}

function save() {
  if (!applyOffsetDraft(true)) return
  emit('save', {
    payment_due_date: dueDate.value,
    memo: memo.value,
    manual_items: manualItems.value,
  })
}
</script>

<style scoped>
.one-statement-sheet {
  color: #000;
}

.statement-template-grid {
  display: grid;
  grid-template-columns: 112px repeat(14, 92px);
  grid-template-rows:
    28px 38px 14px
    repeat(4, 24px)
    14px
    repeat(17, 24px)
    14px
    repeat(34, 22px);
  min-width: 1400px;
  color: #000;
  font-size: 13px;
  line-height: 1.1;
}

.statement-template-cell {
  display: flex;
  align-items: center;
  overflow: hidden;
  padding: 1px 4px;
  white-space: nowrap;
}

.statement-template-cell.bordered {
  border: 1px solid #111;
}

.statement-template-cell.black {
  background: #000;
  color: #fff;
}

.statement-template-cell.gray {
  background: #d9d9d9;
}

.statement-template-cell.center {
  justify-content: center;
  text-align: center;
}

.statement-template-cell.right {
  justify-content: flex-end;
  text-align: right;
}

.statement-template-cell.editable {
  padding: 0;
}

.statement-template-input {
  width: 100%;
  height: 100%;
  border: 0;
  background: transparent;
  padding: 1px 4px;
  text-align: right;
  font: inherit;
  line-height: inherit;
  color: inherit;
  outline: none;
}

.statement-template-input:focus {
  background: #fff8cc;
  box-shadow: inset 0 0 0 2px #2563eb;
}

.statement-template-cell.bold {
  font-weight: 800;
}

.statement-template-cell.month-title {
  align-items: flex-start;
  font-size: 24px;
  line-height: 1;
}

.statement-template-cell.sheet-title {
  align-items: flex-start;
  font-size: 34px;
  line-height: 1;
}

.statement-template-cell.label,
.statement-template-cell.label-value {
  font-size: 18px;
}

.statement-template-cell.month-title,
.statement-template-cell.sheet-title,
.statement-template-cell.label,
.statement-template-cell.label-value {
  overflow: visible;
}

.statement-template-cell.small {
  font-size: 11px;
}

.statement-template-cell.service-start {
  border-top-width: 2px;
}

.statement-template-cell.total {
  border-top-width: 2px;
}

.statement-template-cell.spacer {
  min-height: 100%;
}

.statement-template-cell.offset-cell {
  align-items: flex-start;
  overflow: hidden;
  padding: 1px 5px;
  font-size: 12px;
  line-height: 1.15;
}

.statement-template-cell.offset-product {
  overflow: visible;
}

.statement-template-cell.offset-muted {
  color: #64748b;
  font-weight: 700;
}

.statement-template-cell.offset-total {
  border-top: 1px solid #111;
  font-weight: 800;
}

.date-cell {
  font-weight: 600;
}
</style>
