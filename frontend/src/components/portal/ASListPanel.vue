<template>
  <div class="space-y-4">
    <div class="rounded-2xl border border-gray-200 bg-white p-5">
      <div class="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
        <div>
          <h3 class="text-lg font-bold text-slate-900">A/S 관리</h3>
          <p class="mt-2 text-sm text-slate-500">
            접수 상태를 바꾸고 관리자 메모와 캘린더 메모를 함께 관리합니다.
          </p>
        </div>
        <button
          type="button"
          class="rounded-lg border border-gray-300 px-3 py-1.5 text-xs font-semibold text-slate-700"
          @click="reload"
        >
          새로고침
        </button>
      </div>
    </div>

    <div class="flex flex-wrap items-center gap-2 rounded-2xl border border-gray-200 bg-white p-3">
      <button
        v-for="item in filters"
        :key="item.value || 'all'"
        type="button"
        class="rounded-full px-3 py-1.5 text-xs font-semibold"
        :class="filter === item.value ? item.activeClass : 'bg-gray-100 text-slate-600 hover:bg-gray-200'"
        @click="filter = item.value; reload()"
      >
        {{ item.label }}
      </button>
    </div>

    <div class="rounded-2xl border border-gray-200 bg-white">
      <table class="w-full table-fixed text-sm">
        <thead class="bg-gray-50">
          <tr>
            <th class="w-[24%] px-4 py-3 text-left font-semibold text-slate-600">접수 정보</th>
            <th class="w-[22%] px-4 py-3 text-left font-semibold text-slate-600">차주 정보</th>
            <th class="w-[34%] px-4 py-3 text-left font-semibold text-slate-600">접수 사유</th>
            <th class="w-[20%] px-4 py-3 text-right font-semibold text-slate-600">상태 / 처리</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="row in items"
            :key="row.id"
            class="cursor-pointer border-t border-gray-100 align-top hover:bg-gray-50"
            @click="select(row)"
          >
            <td class="px-4 py-4">
              <div class="space-y-1">
                <p class="font-bold text-slate-900">{{ row.team_code }}조</p>
                <p class="font-semibold text-slate-700">{{ row.vehicle_number }}</p>
                <p class="break-all text-slate-500">{{ row.phone || '-' }}</p>
              </div>
            </td>
            <td class="px-4 py-4">
              <div class="space-y-1">
                <p class="font-medium text-slate-800">{{ row.owner_name || '-' }}</p>
                <p class="break-all text-slate-500">{{ row.owner_phone || '-' }}</p>
              </div>
            </td>
            <td class="px-4 py-4">
              <p class="break-words text-slate-700">{{ row.reason || '-' }}</p>
            </td>
            <td class="px-4 py-4">
              <div class="flex flex-col items-end gap-2">
                <span class="inline-flex rounded-full px-2.5 py-1 text-xs font-bold" :class="statusClass(row.status)">
                  {{ statusLabel(row.status) }}
                </span>
                <button
                  class="rounded-lg px-3 py-2 text-xs font-bold"
                  :class="row.status === 'REQUESTED' ? 'bg-lime-500 text-slate-900' : 'border border-gray-300 text-slate-700'"
                  @click.stop="select(row)"
                >
                  {{ row.status === 'REQUESTED' ? '처리' : '상세' }}
                </button>
              </div>
            </td>
          </tr>
          <tr v-if="!items.length">
            <td colspan="4" class="px-4 py-14 text-center text-sm text-slate-400">A/S 요청이 없습니다.</td>
          </tr>
        </tbody>
      </table>
    </div>

    <div v-if="selected" class="rounded-2xl border-2 border-lime-300 bg-white p-5">
      <div class="mb-4 flex items-center justify-between gap-3">
        <div>
          <h4 class="font-bold text-slate-900">{{ selected.team_code }}조 · {{ selected.vehicle_number }}</h4>
          <p class="mt-1 text-sm text-slate-500">선택한 요청의 상태와 관리자 메모를 수정합니다.</p>
        </div>
        <button class="text-sm font-semibold text-slate-500 hover:text-slate-700" @click="selected = null">닫기</button>
      </div>

      <div class="grid gap-3 md:grid-cols-2">
        <div class="rounded-xl bg-gray-50 p-4 text-sm">
          <p class="text-xs font-semibold text-slate-500">차량 차주</p>
          <p class="mt-1 font-semibold text-slate-900">{{ selected.owner_name || '-' }}</p>
        </div>
        <div class="rounded-xl bg-gray-50 p-4 text-sm">
          <p class="text-xs font-semibold text-slate-500">운영 차주 전화번호</p>
          <p class="mt-1 font-semibold text-slate-900">{{ selected.owner_phone || '-' }}</p>
        </div>
      </div>

      <div class="mt-4 rounded-xl bg-gray-50 p-4 text-sm text-slate-700">{{ selected.reason }}</div>

      <label class="mt-4 block">
        <span class="text-sm font-bold text-slate-700">처리 상태</span>
        <select
          v-model="form.status"
          class="mt-2 w-full rounded-xl border border-gray-300 px-3 py-2 text-sm outline-none focus:border-lime-500"
        >
          <option value="REPAIRING">수리 / 대기중</option>
          <option value="OPERATING">운영중</option>
        </select>
      </label>

      <label class="mt-4 block">
        <span class="text-sm font-bold text-slate-700">관리자 메모</span>
        <textarea
          v-model="form.admin_comment"
          rows="3"
          class="mt-2 w-full rounded-xl border border-gray-300 px-3 py-2 text-sm outline-none focus:border-lime-500"
        />
      </label>

      <label class="mt-4 block">
        <span class="text-sm font-bold text-slate-700">캘린더 메모</span>
        <textarea
          v-model="form.calendar_note"
          rows="2"
          class="mt-2 w-full rounded-xl border border-gray-300 px-3 py-2 text-sm outline-none focus:border-lime-500"
          placeholder="예: 2026-05-12 10:00 · 배터리 점검"
        />
      </label>

      <div class="mt-6 flex justify-end gap-2">
        <button class="rounded-xl border border-gray-300 px-4 py-2 text-sm font-semibold text-slate-700" @click="selected = null">
          취소
        </button>
        <button class="rounded-xl bg-lime-500 px-4 py-2 text-sm font-bold text-slate-900" @click="submit">
          저장
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { onMounted, ref, watch } from 'vue'
import { completeASRequest, fetchASRequests } from '@/api/vehicle'

const props = defineProps({
  companyCode: {
    type: String,
    required: true,
  },
})

const filters = [
  { value: '', label: '전체', activeClass: 'bg-lime-500 text-slate-900' },
  { value: 'REQUESTED', label: '요청 접수', activeClass: 'bg-amber-100 text-amber-700' },
  { value: 'REPAIRING', label: '수리 / 대기중', activeClass: 'bg-rose-100 text-rose-700' },
  { value: 'OPERATING', label: '운영중', activeClass: 'bg-green-100 text-green-700' },
]

const items = ref([])
const filter = ref('')
const selected = ref(null)
const form = ref({ status: 'REPAIRING', admin_comment: '', calendar_note: '' })

const statusClass = (status) => ({
  REQUESTED: 'bg-amber-100 text-amber-700',
  REPAIRING: 'bg-rose-100 text-rose-700',
  OPERATING: 'bg-green-100 text-green-700',
  COMPLETED: 'bg-green-100 text-green-700',
}[status] || 'bg-gray-100 text-slate-600')

const statusLabel = (status) => ({
  REQUESTED: '요청 접수',
  REPAIRING: '수리 / 대기중',
  OPERATING: '운영중',
  COMPLETED: '처리 완료',
}[status] || status)

const reload = async () => {
  const params = { company: props.companyCode }
  if (filter.value) params.status = filter.value
  try {
    const response = await fetchASRequests(params)
    items.value = response.data?.results || response.data || []
  } catch {
    items.value = []
  }
}

const select = (row) => {
  selected.value = row
  form.value = {
    status: row.status === 'OPERATING' ? 'OPERATING' : 'REPAIRING',
    admin_comment: row.admin_comment || '',
    calendar_note: row.calendar_note || '',
  }
}

const submit = async () => {
  try {
    await completeASRequest(selected.value.id, form.value)
    selected.value = null
    await reload()
  } catch {
    alert('저장에 실패했습니다.')
  }
}

watch(() => props.companyCode, reload)
onMounted(reload)
</script>
