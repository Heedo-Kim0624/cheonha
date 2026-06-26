<template>
  <div class="space-y-4">
    <div class="flex items-center gap-3 rounded-xl border border-gray-200 bg-white p-4">
      <span class="text-2xl">캘</span>
      <div class="min-w-0 flex-1">
        <h3 class="font-bold">통합 일정 캘린더</h3>
        <p class="text-xs text-slate-500">
          반납 불가일 등록과 구독 요청, 반납 요청, A/S, 피트 출고 일정을 함께 표시합니다.
        </p>
      </div>
      <span class="text-xs italic text-slate-400">날짜 클릭 시 반납 불가일 등록</span>
    </div>

    <div class="flex flex-wrap items-center gap-3 rounded-xl border border-gray-200 bg-white p-3 text-xs">
      <span class="font-bold">범례</span>
      <span class="flex items-center gap-1"><span class="h-3 w-3 rounded bg-red-500"></span>반납 불가일</span>
      <span class="flex items-center gap-1"><span class="h-3 w-3 rounded bg-amber-500"></span>구독 요청</span>
      <span class="flex items-center gap-1"><span class="h-3 w-3 rounded bg-blue-500"></span>반납 희망</span>
      <span class="flex items-center gap-1"><span class="h-3 w-3 rounded bg-green-500"></span>반납 확정</span>
      <span class="flex items-center gap-1"><span class="h-3 w-3 rounded bg-purple-500"></span>A/S 일정</span>
      <span class="flex items-center gap-1"><span class="h-3 w-3 rounded bg-cyan-500"></span>피트 출고 예정</span>
    </div>

    <div class="flex items-center justify-between rounded-xl border border-gray-200 bg-white p-3">
      <button class="rounded px-3 py-1 hover:bg-gray-100" @click="moveMonth(-1)">이전</button>
      <h3 class="font-bold">{{ year }}년 {{ month }}월</h3>
      <button class="rounded px-3 py-1 hover:bg-gray-100" @click="moveMonth(1)">다음</button>
    </div>

    <div class="overflow-hidden rounded-xl border border-gray-200 bg-white">
      <div class="grid grid-cols-7 bg-gray-50">
        <div
          v-for="day in ['월', '화', '수', '목', '금', '토', '일']"
          :key="day"
          class="px-2 py-2 text-center text-xs font-bold"
          :class="day === '일' ? 'text-red-500' : 'text-slate-500'"
        >
          {{ day }}
        </div>
      </div>

      <div class="grid grid-cols-7">
        <button
          v-for="cell in cells"
          :key="cell.key"
          type="button"
          :disabled="!cell.inMonth"
          class="min-h-[100px] border-r border-t border-gray-100 p-2 text-left text-xs transition-colors"
          :class="cell.inMonth ? 'cursor-pointer hover:bg-red-50' : 'cursor-default bg-gray-50 text-slate-300'"
          :title="cell.inMonth ? `${cell.dateStr} 클릭 시 반납 불가일 등록` : ''"
          @click="cell.inMonth && openBlockForDate(cell.dateStr)"
        >
          <div class="mb-1 flex items-center justify-between">
            <span class="font-bold">{{ cell.day }}</span>
            <span v-if="cell.inMonth && hasBlock(cell.events)" class="text-[10px] font-bold text-red-500">불가</span>
          </div>

          <div class="space-y-0.5">
            <div
              v-for="event in cell.events.slice(0, 3)"
              :key="event.id"
              class="truncate rounded px-1 py-0.5 text-[10px]"
              :class="kindClass(event.kind)"
            >
              {{ event.title }}
            </div>
            <div v-if="cell.events.length > 3" class="text-[10px] text-slate-500">
              +{{ cell.events.length - 3 }}건
            </div>
          </div>
        </button>
      </div>
    </div>

    <div v-if="showBlockModal" class="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div class="w-full max-w-md rounded-xl bg-white p-6">
        <h3 class="mb-3 text-lg font-bold">반납 불가일 등록</h3>

        <label class="mb-3 block">
          <span class="text-sm font-bold">날짜</span>
          <input
            v-model="blockForm.date"
            type="date"
            class="mt-1 w-full rounded border border-gray-300 px-3 py-2"
          />
        </label>

        <label class="mb-4 block">
          <span class="text-sm font-bold">사유</span>
          <input
            v-model="blockForm.title"
            type="text"
            placeholder="예: 정비일 / 내부 일정"
            class="mt-1 w-full rounded border border-gray-300 px-3 py-2"
          />
        </label>

        <div class="flex justify-end gap-2">
          <button class="rounded border border-gray-300 px-4 py-2 text-sm" @click="showBlockModal = false">취소</button>
          <button class="rounded bg-red-500 px-4 py-2 text-sm font-bold text-white" @click="submitBlock">등록</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { createCalendarEvent, fetchCalendarEvents, fetchCompanies } from '@/api/vehicle'

const props = defineProps({
  companyCode: {
    type: String,
    required: true,
  },
})

const today = new Date()
const year = ref(today.getFullYear())
const month = ref(today.getMonth() + 1)
const events = ref([])
const showBlockModal = ref(false)
const blockForm = ref({ date: '', title: '' })
const companyId = ref(null)

const moveMonth = (delta) => {
  const next = new Date(year.value, month.value - 1 + delta, 1)
  year.value = next.getFullYear()
  month.value = next.getMonth() + 1
  reload()
}

const cells = computed(() => {
  const firstDay = new Date(year.value, month.value - 1, 1)
  const startDow = (firstDay.getDay() + 6) % 7
  const daysInMonth = new Date(year.value, month.value, 0).getDate()
  const rows = []

  for (let index = 0; index < startDow; index += 1) {
    const date = new Date(year.value, month.value - 1, -startDow + index + 1)
    rows.push({
      key: `prev-${index}`,
      day: date.getDate(),
      inMonth: false,
      events: [],
      dateStr: '',
    })
  }

  for (let day = 1; day <= daysInMonth; day += 1) {
    const dateStr = `${year.value}-${String(month.value).padStart(2, '0')}-${String(day).padStart(2, '0')}`
    const dayEvents = events.value.filter((event) => event.event_date === dateStr)
    rows.push({
      key: `day-${day}`,
      day,
      inMonth: true,
      events: dayEvents,
      dateStr,
    })
  }

  while (rows.length % 7) {
    const index = rows.length - daysInMonth - startDow
    rows.push({
      key: `next-${index}`,
      day: index + 1,
      inMonth: false,
      events: [],
      dateStr: '',
    })
  }

  return rows
})

const hasBlock = (items) => items.some((event) => event.kind === 'BLOCK')

const openBlockForDate = (dateStr) => {
  blockForm.value = { date: dateStr, title: '' }
  showBlockModal.value = true
}

const kindClass = (kind) =>
  ({
    BLOCK: 'bg-red-100 text-red-700',
    REQ_HOPE: 'bg-amber-100 text-amber-700',
    RET_HOPE: 'bg-blue-100 text-blue-700',
    RET_CONFIRM: 'bg-green-100 text-green-700',
    AS_SCHED: 'bg-purple-100 text-purple-700',
    PIT_OUT: 'bg-cyan-100 text-cyan-700',
  }[kind] || 'bg-gray-100')

const reload = async () => {
  const from = `${year.value}-${String(month.value).padStart(2, '0')}-01`
  const lastDay = new Date(year.value, month.value, 0).getDate()
  const to = `${year.value}-${String(month.value).padStart(2, '0')}-${String(lastDay).padStart(2, '0')}`
  const params = { from, to }
  if (props.companyCode) params.company = props.companyCode

  try {
    const response = await fetchCalendarEvents(params)
    events.value = response.data?.results || response.data || []
  } catch {
    events.value = []
  }
}

const loadCompanyId = async () => {
  try {
    const response = await fetchCompanies()
    const items = response.data?.results || response.data || []
    companyId.value = items.find((item) => item.code === props.companyCode)?.id || null
  } catch {
    companyId.value = null
  }
}

const submitBlock = async () => {
  if (!blockForm.value.date || !blockForm.value.title) {
    alert('날짜와 사유를 입력해주세요.')
    return
  }

  const payload = {
    kind: 'BLOCK',
    event_date: blockForm.value.date,
    title: `불가 ${blockForm.value.title}`,
    body: blockForm.value.title,
  }

  if (companyId.value) {
    payload.company = companyId.value
  }

  try {
    await createCalendarEvent(payload)
    showBlockModal.value = false
    blockForm.value = { date: '', title: '' }
    await reload()
  } catch (error) {
    const detail =
      error.response?.data?.detail ||
      (typeof error.response?.data === 'object' ? JSON.stringify(error.response.data) : null) ||
      error.message
    alert(`등록 실패: ${detail}`)
  }
}

watch(
  () => props.companyCode,
  async () => {
    await loadCompanyId()
    await reload()
  },
)

onMounted(async () => {
  await loadCompanyId()
  await reload()
})
</script>
