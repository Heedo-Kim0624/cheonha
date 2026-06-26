<template>
  <div
    v-if="isVisible"
    :class="outerClass"
    @click.self="handleBackdropClick"
  >
    <section :class="panelClass">
      <header class="flex flex-col gap-4 border-b border-gray-200 px-5 py-4 lg:flex-row lg:items-start lg:justify-between">
        <div class="min-w-0">
          <p class="text-sm font-semibold text-gray-500">{{ activeMonth }} 월별 정산</p>
          <h3 class="mt-1 break-keep text-2xl font-extrabold text-text">
            {{ crew?.name || '배송원' }} 정산 캘린더
          </h3>
          <p class="mt-1 text-sm text-gray-500">
            날짜를 선택하면 회차별 가구, 박스, 수신금액, 지급금액을 확인하고 수정할 수 있습니다.
          </p>
        </div>
        <div class="flex flex-wrap items-center gap-2">
          <input
            v-model="activeMonth"
            type="month"
            class="rounded-lg border border-gray-300 px-3 py-2 text-sm font-semibold text-gray-700 outline-none focus:border-primary"
          />
          <button
            type="button"
            class="rounded-lg border px-3 py-2 text-sm font-bold transition"
            :class="insurancePanelOpen ? 'border-gray-900 bg-gray-900 text-white' : 'border-gray-200 bg-white text-gray-700 hover:bg-gray-50'"
            @click="insurancePanelOpen = !insurancePanelOpen"
          >
            2대보험
          </button>
          <button
            v-if="!embedded"
            type="button"
            class="rounded-lg border border-gray-200 px-3 py-2 text-sm font-bold text-gray-600 hover:bg-gray-50"
            @click="$emit('close')"
          >
            닫기
          </button>
        </div>
      </header>

      <div class="min-h-0 overflow-y-auto px-5 py-4">
        <div v-if="insurancePanelOpen" class="mb-4 rounded-xl border border-gray-200 bg-gray-50 p-4">
          <label class="block text-sm font-bold text-text" for="insurance-percent">2대보험 공제율</label>
          <div class="mt-2 flex flex-wrap items-center gap-2">
            <input
              id="insurance-percent"
              v-model.number="insurancePercent"
              type="number"
              min="0"
              max="100"
              step="0.1"
              class="w-32 rounded-lg border border-gray-300 px-3 py-2 text-right text-sm font-semibold outline-none focus:border-primary"
            />
            <span class="text-sm font-semibold text-gray-600">%</span>
            <button
              type="button"
              class="rounded-lg bg-gray-900 px-4 py-2 text-sm font-bold text-white hover:bg-gray-800 disabled:cursor-not-allowed disabled:opacity-50"
              :disabled="insuranceSaving"
              @click="saveInsurancePercent"
            >
              {{ insuranceSaving ? '저장 중...' : '저장' }}
            </button>
            <label class="inline-flex items-center gap-2 rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm font-bold text-gray-700">
              <input
                v-model="insuranceApplyAll"
                type="checkbox"
                class="h-4 w-4 rounded border-gray-300 text-gray-900 focus:ring-gray-900"
              />
              전체 적용(용차팀 제외)
            </label>
          </div>
          <p class="mt-2 text-sm text-gray-500">
            지급금액에서 입력한 비율만큼 공제한 실지급금액을 캘린더에 함께 표시합니다.
          </p>
          <p v-if="insuranceMessage" class="mt-2 rounded-lg bg-green-50 px-3 py-2 text-sm font-semibold text-green-700">
            {{ insuranceMessage }}
          </p>
          <p v-if="insuranceError" class="mt-2 rounded-lg bg-red-50 px-3 py-2 text-sm font-semibold text-red-600">
            {{ insuranceError }}
          </p>
        </div>

        <div v-if="loading" class="rounded-xl bg-gray-50 py-16 text-center text-sm font-semibold text-gray-500">
          정산 캘린더를 불러오는 중입니다.
        </div>
        <div v-else-if="errorMessage" class="rounded-xl border border-red-100 bg-red-50 p-4 text-sm font-semibold text-red-600">
          {{ errorMessage }}
        </div>
        <template v-else>
          <div class="mb-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
            <SummaryCard label="월 전체 가구수" :value="formatNumber(totals.households)" />
            <SummaryCard label="월 전체 박스수" :value="formatNumber(totals.boxes)" />
            <SummaryCard label="월 전체 수신금액" :value="`${formatCurrency(totals.receive_amount)}원`" value-class="text-blue-700" />
            <SummaryCard label="월 전체 지급금액" :value="`${formatCurrency(totals.pay_amount)}원`" value-class="text-primary" />
            <SummaryCard
              v-if="hasInsurance"
              label="월 전체 실지급금액"
              :value="`${formatCurrency(netPay(totals.pay_amount))}원`"
              value-class="text-red-600"
            />
          </div>

          <div class="overflow-hidden rounded-xl border border-gray-200 bg-white">
            <div class="grid grid-cols-7 border-b border-gray-200 bg-gray-50 text-center text-xs font-bold text-gray-500">
              <div v-for="day in weekDays" :key="day" class="px-2 py-2">{{ day }}</div>
            </div>
            <div class="grid grid-cols-7">
              <button
                v-for="day in calendarDays"
                :key="day.date"
                type="button"
                class="min-h-[118px] border-b border-r border-gray-100 p-2 text-left transition last:border-r-0 hover:bg-gray-50"
                :class="[
                  day.inMonth ? 'bg-white' : 'bg-gray-50/60 text-gray-400',
                  selectedDate === day.date ? 'ring-2 ring-inset ring-gray-900' : '',
                  day.row ? 'cursor-pointer' : 'cursor-default',
                ]"
                @click="selectDate(day)"
              >
                <span class="text-xs font-extrabold">{{ day.day }}</span>
                <div v-if="day.row" class="mt-2 space-y-1 text-[11px] leading-4">
                  <p class="truncate text-gray-700">가구 {{ formatNumber(day.row.households) }}</p>
                  <p class="truncate text-gray-700">박스 {{ formatNumber(day.row.boxes) }}</p>
                  <p class="truncate font-semibold text-blue-700">수신 {{ formatCurrency(day.row.receive_amount) }}원</p>
                  <p class="truncate font-semibold text-primary">지급 {{ formatCurrency(day.row.pay_amount) }}원</p>
                  <p v-if="hasInsurance" class="truncate font-semibold text-red-600">
                    실지급 {{ formatCurrency(netPay(day.row.pay_amount)) }}원
                  </p>
                </div>
              </button>
            </div>
          </div>

          <section class="mt-4 rounded-xl border border-gray-200 bg-white">
            <div class="flex flex-col gap-2 border-b border-gray-100 px-4 py-3 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <p class="text-sm font-semibold text-gray-500">{{ selectedDate || '날짜 미선택' }}</p>
                <h4 class="text-lg font-extrabold text-text">회차별 정보</h4>
              </div>
              <p v-if="selectedDateRow" class="text-sm font-semibold text-gray-500">
                가구 {{ formatNumber(selectedDateRow.households) }} · 박스 {{ formatNumber(selectedDateRow.boxes) }} · 지급 {{ formatCurrency(selectedDateRow.pay_amount) }}원
              </p>
            </div>

            <div v-if="!selectedDateRow" class="px-4 py-10 text-center text-sm text-gray-400">
              캘린더에서 정산 내역이 있는 날짜를 선택하세요.
            </div>
            <div v-else class="overflow-x-auto">
              <table class="w-full min-w-[760px] text-sm">
                <thead class="bg-gray-50 text-xs font-bold uppercase tracking-wide text-gray-500">
                  <tr>
                    <th class="px-4 py-3 text-left">회차</th>
                    <th class="px-4 py-3 text-left">조</th>
                    <th class="px-4 py-3 text-center">용차</th>
                    <th class="px-4 py-3 text-right">가구</th>
                    <th class="px-4 py-3 text-right">박스</th>
                    <th class="px-4 py-3 text-right">수신금액</th>
                    <th class="px-4 py-3 text-right">지급금액</th>
                    <th class="px-4 py-3 text-right">관리</th>
                  </tr>
                </thead>
                <tbody class="divide-y divide-gray-100">
                  <tr v-for="round in selectedRounds" :key="`${selectedDate}-${round.round_label}`">
                    <td class="px-4 py-3 font-extrabold text-text">{{ round.round_label }}</td>
                    <td class="px-4 py-3 text-gray-600">{{ round.team_name || '-' }}</td>
                    <td class="px-4 py-3 text-center">
                      <span
                        class="rounded-full px-2 py-1 text-xs font-bold"
                        :class="round.is_yongcha ? 'bg-red-50 text-red-600' : 'bg-gray-100 text-gray-500'"
                      >
                        {{ round.is_yongcha_label || (round.is_yongcha ? 'O' : 'X') }}
                      </span>
                    </td>
                    <td class="px-4 py-3 text-right font-semibold">{{ formatNumber(round.households) }}</td>
                    <td class="px-4 py-3 text-right font-semibold">{{ formatNumber(round.boxes) }}</td>
                    <td class="px-4 py-3 text-right font-bold text-blue-700">{{ formatCurrency(round.receive_amount) }}원</td>
                    <td class="px-4 py-3 text-right font-bold text-primary">
                      {{ formatCurrency(round.pay_amount) }}원
                      <span v-if="hasInsurance" class="mt-1 block text-xs text-red-600">
                        실 {{ formatCurrency(netPay(round.pay_amount)) }}원
                      </span>
                    </td>
                    <td class="px-4 py-3 text-right">
                      <button
                        type="button"
                        class="rounded-lg border border-gray-200 px-3 py-1.5 text-xs font-bold text-gray-700 hover:bg-gray-50"
                        @click="openEdit(round)"
                      >
                        수정
                      </button>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </section>
        </template>
      </div>

      <div
        v-if="editPanelOpen"
        class="fixed inset-0 z-[70] flex items-center justify-center bg-black/40 p-4"
        @click.self="closeEdit"
      >
        <form class="w-full max-w-lg rounded-2xl bg-white p-5 shadow-2xl" @submit.prevent="saveRound">
          <div class="flex items-start justify-between gap-3">
            <div>
              <p class="text-sm font-semibold text-gray-500">{{ selectedDate }}</p>
              <h4 class="text-xl font-extrabold text-text">{{ editingRound?.round_label }} 수정</h4>
            </div>
            <button type="button" class="rounded-lg border border-gray-200 px-3 py-2 text-sm font-bold text-gray-600" @click="closeEdit">
              닫기
            </button>
          </div>

          <div class="mt-5 grid gap-4 sm:grid-cols-3">
            <label class="text-sm font-bold text-gray-700">
              박스 수
              <input v-model.number="editForm.boxes" type="number" min="0" class="mt-2 w-full rounded-lg border border-gray-300 px-3 py-2 text-right outline-none focus:border-primary" />
            </label>
            <label class="text-sm font-bold text-gray-700">
              총 수신금액
              <input v-model.number="editForm.receive_amount" type="number" min="0" class="mt-2 w-full rounded-lg border border-gray-300 px-3 py-2 text-right outline-none focus:border-primary" />
            </label>
            <label class="text-sm font-bold text-gray-700">
              지급금액
              <input v-model.number="editForm.pay_amount" type="number" min="0" class="mt-2 w-full rounded-lg border border-gray-300 px-3 py-2 text-right outline-none focus:border-primary" />
            </label>
          </div>

          <p class="mt-3 text-xs leading-5 text-gray-500">
            같은 날짜/회차에 여러 정산 detail이 있으면 첫 항목에 합계를 반영하고 나머지 항목은 0으로 정리한 뒤 정산을 재계산합니다.
          </p>
          <p v-if="saveError" class="mt-3 rounded-lg bg-red-50 px-3 py-2 text-sm font-semibold text-red-600">{{ saveError }}</p>

          <div class="mt-5 flex justify-end gap-2">
            <button type="button" class="rounded-lg border border-gray-200 px-4 py-2 font-bold text-gray-600 hover:bg-gray-50" @click="closeEdit">
              취소
            </button>
            <button type="submit" class="rounded-lg bg-primary px-4 py-2 font-bold text-white hover:opacity-90 disabled:opacity-50" :disabled="saving">
              {{ saving ? '저장 중...' : '저장' }}
            </button>
          </div>
        </form>
      </div>
    </section>
  </div>
</template>

<script setup>
import { computed, defineComponent, h, reactive, ref, watch } from 'vue'

import { getCrewMonthlySettlement, setCrewInsurancePercent } from '@/api/crew'
import { recalcSettlement, updateSettlementDetail } from '@/api/settlement'
import { formatCurrency } from '@/utils/format'

const SummaryCard = defineComponent({
  props: {
    label: { type: String, required: true },
    value: { type: String, required: true },
    valueClass: { type: String, default: 'text-text' },
  },
  setup(props) {
    return () => h('div', { class: 'rounded-xl border border-gray-100 bg-gray-50 px-4 py-3' }, [
      h('p', { class: 'text-xs font-bold uppercase tracking-wide text-gray-400' }, props.label),
      h('p', { class: `mt-1 text-lg font-extrabold ${props.valueClass}` }, props.value),
    ])
  },
})

const props = defineProps({
  show: { type: Boolean, default: false },
  embedded: { type: Boolean, default: false },
  crew: { type: Object, default: null },
  month: { type: String, default: '' },
})

const emit = defineEmits(['close', 'saved'])

const weekDays = ['일', '월', '화', '수', '목', '금', '토']
const activeMonth = ref(new Date().toISOString().slice(0, 7))
const loading = ref(false)
const errorMessage = ref('')
const rows = ref([])
const totals = ref({ households: 0, boxes: 0, receive_amount: 0, pay_amount: 0 })
const selectedDate = ref('')
const insurancePanelOpen = ref(false)
const insurancePercent = ref(0)
const insuranceApplyAll = ref(false)
const insuranceSaving = ref(false)
const insuranceMessage = ref('')
const insuranceError = ref('')
const editPanelOpen = ref(false)
const editingRound = ref(null)
const saving = ref(false)
const saveError = ref('')
const editForm = reactive({
  boxes: 0,
  receive_amount: 0,
  pay_amount: 0,
})

const isVisible = computed(() => Boolean(props.crew && (props.embedded || props.show)))
const outerClass = computed(() =>
  props.embedded
    ? 'w-full'
    : 'fixed inset-0 z-50 flex items-center justify-center bg-black/45 p-4'
)
const panelClass = computed(() =>
  props.embedded
    ? 'w-full overflow-hidden rounded-2xl border border-gray-200 bg-white'
    : 'flex max-h-[92vh] w-full max-w-7xl flex-col overflow-hidden rounded-2xl bg-white shadow-2xl'
)
const rowByDate = computed(() => {
  const map = new Map()
  rows.value.forEach((row) => {
    if (row?.date) map.set(row.date, row)
  })
  return map
})
const selectedDateRow = computed(() => rows.value.find((row) => row.date === selectedDate.value) || null)
const selectedRounds = computed(() => selectedDateRow.value?.rounds || [])
const hasInsurance = computed(() => insurancePercentNumber.value > 0)
const insurancePercentNumber = computed(() => Math.min(100, Math.max(0, Number(insurancePercent.value || 0))))

const calendarDays = computed(() => {
  const [year, month] = activeMonth.value.split('-').map((value) => Number(value))
  if (!year || !month) return []
  const firstDay = new Date(year, month - 1, 1)
  const start = new Date(firstDay)
  start.setDate(firstDay.getDate() - firstDay.getDay())

  return Array.from({ length: 42 }, (_, index) => {
    const date = new Date(start)
    date.setDate(start.getDate() + index)
    const dateKey = formatDateKey(date)
    return {
      date: dateKey,
      day: date.getDate(),
      inMonth: date.getMonth() === month - 1,
      row: rowByDate.value.get(dateKey) || null,
    }
  })
})

function formatDateKey(date) {
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

function formatNumber(value) {
  return Number(value || 0).toLocaleString()
}

function netPay(value) {
  const amount = Number(value || 0)
  return Math.round(amount * (1 - insurancePercentNumber.value / 100))
}

function syncInsurancePercent(value) {
  const numericValue = Number(value)
  insurancePercent.value = Number.isFinite(numericValue) ? numericValue : 0
}

function handleBackdropClick() {
  if (!props.embedded) emit('close')
}

function selectDate(day) {
  if (!day?.row) return
  selectedDate.value = day.date
}

async function loadSettlement() {
  if (!props.crew?.id || !activeMonth.value || !isVisible.value) return
  loading.value = true
  errorMessage.value = ''
  try {
    const response = await getCrewMonthlySettlement(props.crew.id, { month: activeMonth.value })
    rows.value = response.data?.results || []
    totals.value = response.data?.totals || { households: 0, boxes: 0, receive_amount: 0, pay_amount: 0 }
    syncInsurancePercent(response.data?.crew?.two_insurance_percent ?? props.crew?.two_insurance_percent)
    if (!rows.value.some((row) => row.date === selectedDate.value)) {
      selectedDate.value = rows.value[0]?.date || ''
    }
  } catch {
    rows.value = []
    totals.value = { households: 0, boxes: 0, receive_amount: 0, pay_amount: 0 }
    selectedDate.value = ''
    errorMessage.value = '월별 정산 내역을 불러오지 못했습니다.'
  } finally {
    loading.value = false
  }
}

async function saveInsurancePercent() {
  if (!props.crew?.id) return

  insuranceSaving.value = true
  insuranceError.value = ''
  insuranceMessage.value = ''
  try {
    const response = await setCrewInsurancePercent(props.crew.id, {
      percent: insurancePercentNumber.value,
      apply_all: insuranceApplyAll.value,
    })
    syncInsurancePercent(response.data?.current_percent ?? response.data?.percent ?? insurancePercentNumber.value)
    insuranceMessage.value = response.data?.detail || '2대보험 공제율을 저장했습니다.'
    emit('saved')
  } catch (error) {
    insuranceError.value = error?.response?.data?.detail || '2대보험 공제율을 저장하지 못했습니다.'
  } finally {
    insuranceSaving.value = false
  }
}

function openEdit(round) {
  editingRound.value = round
  editForm.boxes = Number(round?.boxes || 0)
  editForm.receive_amount = Number(round?.receive_amount || 0)
  editForm.pay_amount = Number(round?.pay_amount || 0)
  saveError.value = ''
  editPanelOpen.value = true
}

function closeEdit() {
  editPanelOpen.value = false
  editingRound.value = null
  saveError.value = ''
}

async function saveRound() {
  const detailIds = Array.isArray(editingRound.value?.detail_ids) ? editingRound.value.detail_ids : []
  if (detailIds.length === 0) {
    saveError.value = '수정할 정산 상세 ID가 없습니다.'
    return
  }

  saving.value = true
  saveError.value = ''
  try {
    const firstPayload = {
      boxes: Number(editForm.boxes || 0),
      receive_amount: Number(editForm.receive_amount || 0),
      pay_amount: Number(editForm.pay_amount || 0),
    }
    await updateSettlementDetail(detailIds[0], firstPayload)

    for (const detailId of detailIds.slice(1)) {
      await updateSettlementDetail(detailId, {
        boxes: 0,
        receive_amount: 0,
        pay_amount: 0,
      })
    }

    const settlementIds = new Set([
      ...(Array.isArray(editingRound.value?.settlement_ids) ? editingRound.value.settlement_ids : []),
      ...(Array.isArray(selectedDateRow.value?.settlement_ids) ? selectedDateRow.value.settlement_ids : []),
    ])
    for (const settlementId of settlementIds) {
      await recalcSettlement(settlementId)
    }

    closeEdit()
    await loadSettlement()
    emit('saved')
  } catch {
    saveError.value = '저장하지 못했습니다. 잠시 후 다시 시도하세요.'
  } finally {
    saving.value = false
  }
}

watch(() => props.month, (value) => {
  if (value) activeMonth.value = value
}, { immediate: true })

watch(() => props.crew?.two_insurance_percent, (value) => {
  syncInsurancePercent(value)
}, { immediate: true })

watch(() => props.crew?.id, () => {
  insuranceApplyAll.value = false
  insuranceMessage.value = ''
  insuranceError.value = ''
})

watch([() => props.crew?.id, activeMonth, isVisible], () => {
  if (isVisible.value) void loadSettlement()
}, { immediate: true })
</script>
