<template>
  <div class="space-y-4">
    <div class="rounded-2xl border border-gray-200 bg-white p-5">
      <div class="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
        <div>
          <h3 class="text-lg font-bold text-slate-900">구독 관리</h3>
          <p class="mt-2 text-sm text-slate-500">
            구독 신청 승인과 반납 일정 조정을 한 화면에서 처리합니다.
          </p>
        </div>
        <div class="rounded-xl bg-slate-50 px-4 py-3 text-sm text-slate-600">
          승인된 신청은 <strong class="text-slate-800">차량 배정</strong> 탭으로 이동합니다.
        </div>
      </div>
    </div>

    <div class="flex flex-wrap items-center gap-2 rounded-2xl border border-gray-200 bg-white p-3">
      <button
        type="button"
        class="rounded-full px-4 py-2 text-sm font-semibold"
        :class="kind === 'request' ? 'bg-lime-500 text-slate-900' : 'bg-gray-100 text-slate-600 hover:bg-gray-200'"
        @click="kind = 'request'"
      >
        구독 신청
        <span class="ml-1.5 rounded-full bg-white/60 px-2 py-0.5 text-xs">{{ requestRows.length }}</span>
      </button>
      <button
        type="button"
        class="rounded-full px-4 py-2 text-sm font-semibold"
        :class="kind === 'return' ? 'bg-lime-500 text-slate-900' : 'bg-gray-100 text-slate-600 hover:bg-gray-200'"
        @click="kind = 'return'"
      >
        구독 반납
        <span class="ml-1.5 rounded-full bg-white/60 px-2 py-0.5 text-xs">{{ returnRows.length }}</span>
      </button>
      <button
        type="button"
        class="ml-auto rounded-lg border border-gray-300 px-3 py-1.5 text-xs font-semibold text-slate-700"
        @click="reload"
      >
        새로고침
      </button>
    </div>

    <div v-if="kind === 'request'" class="rounded-2xl border border-gray-200 bg-white">
      <table class="w-full table-fixed text-sm">
        <thead class="bg-gray-50">
          <tr>
            <th class="w-[34%] px-4 py-3 text-left font-semibold text-slate-600">신청 정보</th>
            <th class="w-[18%] px-4 py-3 text-left font-semibold text-slate-600">수량 / 상태</th>
            <th class="w-[28%] px-4 py-3 text-left font-semibold text-slate-600">거절 사유</th>
            <th class="w-[20%] px-4 py-3 text-right font-semibold text-slate-600">처리</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in requestRows" :key="row.id" class="border-t border-gray-100 align-top">
            <td class="px-4 py-4">
              <div class="space-y-1">
                <p class="font-bold text-slate-900">{{ row.team_code }}조</p>
                <p class="text-slate-700">{{ row.requested_date }}</p>
                <p class="break-all text-slate-500">{{ row.phone || '-' }}</p>
              </div>
            </td>
            <td class="px-4 py-4">
              <div class="space-y-2">
                <p class="font-bold text-lime-700">{{ row.quantity }}대</p>
                <span class="inline-flex rounded-full px-2.5 py-1 text-xs font-bold" :class="subscriptionStatusClass(row.status)">
                  {{ row.status_display || subscriptionStatusLabel(row.status) }}
                </span>
              </div>
            </td>
            <td class="px-4 py-4">
              <p class="break-words text-sm text-slate-600">
                {{ row.reject_reason || '-' }}
              </p>
            </td>
            <td class="px-4 py-4">
              <div class="flex flex-col items-end gap-2">
                <template v-if="row.status === 'REQUESTED'">
                  <button
                    type="button"
                    class="rounded-lg bg-lime-500 px-3 py-2 text-xs font-bold text-slate-900"
                    :disabled="subscriptionActionId === row.id"
                    @click="approveRow(row)"
                  >
                    승인
                  </button>
                  <button
                    type="button"
                    class="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-xs font-bold text-red-700"
                    :disabled="subscriptionActionId === row.id"
                    @click="openRejectModal(row)"
                  >
                    거절
                  </button>
                </template>
                <span v-else class="text-xs text-slate-400">차량 배정 단계로 이동</span>
              </div>
            </td>
          </tr>
          <tr v-if="!requestRows.length">
            <td colspan="4" class="px-4 py-14 text-center text-sm text-slate-400">처리할 구독 신청이 없습니다.</td>
          </tr>
        </tbody>
      </table>
    </div>

    <div v-else class="rounded-2xl border border-gray-200 bg-white">
      <table class="w-full table-fixed text-sm">
        <thead class="bg-gray-50">
          <tr>
            <th class="w-[28%] px-4 py-3 text-left font-semibold text-slate-600">반납 정보</th>
            <th class="w-[30%] px-4 py-3 text-left font-semibold text-slate-600">일정 / 사유</th>
            <th class="w-[22%] px-4 py-3 text-left font-semibold text-slate-600">사진 / 상태</th>
            <th class="w-[20%] px-4 py-3 text-right font-semibold text-slate-600">처리</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in returnRows" :key="row.id" class="border-t border-gray-100 align-top">
            <td class="px-4 py-4">
              <div class="space-y-1">
                <p class="font-bold text-slate-900">{{ row.team_code }}조</p>
                <p class="font-semibold text-slate-700">{{ row.vehicle_number }}</p>
                <p class="break-all text-slate-500">{{ row.phone || '-' }}</p>
              </div>
            </td>
            <td class="px-4 py-4">
              <div class="space-y-2">
                <p class="font-medium text-slate-700">
                  {{ row.hope_date || '-' }}
                  <span v-if="row.hope_time" class="text-slate-500">· {{ (row.hope_time || '').slice(0, 5) }}</span>
                </p>
                <p class="break-words text-slate-600">{{ row.reason || '-' }}</p>
              </div>
            </td>
            <td class="px-4 py-4">
              <div class="space-y-2">
                <button
                  type="button"
                  class="rounded-lg border border-gray-300 px-3 py-2 text-xs font-semibold text-slate-700"
                  @click="openPhotoModal(row)"
                >
                  사진 {{ row.photo_count || 0 }}장 보기
                </button>
                <span class="inline-flex rounded-full px-2.5 py-1 text-xs font-bold" :class="returnStatusClass(row.status)">
                  {{ row.status_display || returnStatusLabel(row.status) }}
                </span>
                <p v-if="row.block_reason" class="break-words text-xs text-amber-700">{{ row.block_reason }}</p>
                <p v-if="row.available_dates" class="break-words text-xs text-slate-500">가능 일정: {{ row.available_dates }}</p>
              </div>
            </td>
            <td class="px-4 py-4">
              <div class="flex flex-col items-end gap-2">
                <template v-if="row.status === 'REQUESTED'">
                  <button
                    type="button"
                    class="rounded-lg bg-lime-500 px-3 py-2 text-xs font-bold text-slate-900"
                    @click="openReturnModal(row, 'confirm')"
                  >
                    일정 확정
                  </button>
                  <button
                    type="button"
                    class="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs font-bold text-amber-700"
                    @click="openReturnModal(row, 'adjust')"
                  >
                    일정 조정
                  </button>
                </template>
                <span v-else class="text-xs text-slate-400">처리 완료</span>
              </div>
            </td>
          </tr>
          <tr v-if="!returnRows.length">
            <td colspan="4" class="px-4 py-14 text-center text-sm text-slate-400">반납 요청이 없습니다.</td>
          </tr>
        </tbody>
      </table>
    </div>

    <div v-if="selectedReturn" class="fixed inset-0 z-50 flex items-center justify-center bg-black/45 px-4">
      <div class="w-full max-w-lg rounded-2xl bg-white p-6 shadow-xl">
        <div class="flex items-start justify-between gap-4">
          <div>
            <h4 class="text-lg font-bold text-slate-900">
              {{ returnModalMode === 'confirm' ? '반납 일정 확정' : '반납 일정 조정' }}
            </h4>
            <p class="mt-1 text-sm text-slate-500">
              {{ selectedReturn.team_code }}조 · {{ selectedReturn.vehicle_number }}
            </p>
          </div>
          <button type="button" class="text-slate-400 hover:text-slate-700" @click="closeReturnModal">닫기</button>
        </div>

        <div v-if="returnModalMode === 'confirm'" class="mt-5 grid gap-4 md:grid-cols-2">
          <label class="flex flex-col gap-2">
            <span class="text-sm font-semibold text-slate-700">확정 날짜</span>
            <input
              v-model="returnConfirmForm.confirmed_date"
              type="date"
              class="rounded-xl border border-gray-300 px-3 py-2 text-sm outline-none focus:border-lime-500"
            />
          </label>
          <label class="flex flex-col gap-2">
            <span class="text-sm font-semibold text-slate-700">확정 시간</span>
            <input
              v-model="returnConfirmForm.confirmed_time"
              type="time"
              class="rounded-xl border border-gray-300 px-3 py-2 text-sm outline-none focus:border-lime-500"
            />
          </label>
        </div>

        <div v-else class="mt-5 space-y-4">
          <label class="flex flex-col gap-2">
            <span class="text-sm font-semibold text-slate-700">조정 사유</span>
            <textarea
              v-model="returnAdjustForm.block_reason"
              rows="3"
              class="rounded-xl border border-gray-300 px-3 py-2 text-sm outline-none focus:border-lime-500"
            />
          </label>
          <label class="flex flex-col gap-2">
            <span class="text-sm font-semibold text-slate-700">가능 일정</span>
            <input
              v-model="returnAdjustForm.available_dates"
              type="text"
              placeholder="예: 2026-05-12, 2026-05-13"
              class="rounded-xl border border-gray-300 px-3 py-2 text-sm outline-none focus:border-lime-500"
            />
          </label>
        </div>

        <div class="mt-6 flex justify-end gap-2">
          <button
            type="button"
            class="rounded-xl border border-gray-300 px-4 py-2 text-sm font-semibold text-slate-700"
            @click="closeReturnModal"
          >
            취소
          </button>
          <button
            type="button"
            class="rounded-xl bg-lime-500 px-4 py-2 text-sm font-bold text-slate-900"
            :disabled="returnActionId === selectedReturn.id"
            @click="submitReturnAction"
          >
            저장
          </button>
        </div>
      </div>
    </div>

    <div v-if="selectedPhotoReturn" class="fixed inset-0 z-50 flex items-center justify-center bg-black/50 px-4">
      <div class="w-full max-w-6xl rounded-2xl bg-white p-6 shadow-xl">
        <div class="flex items-start justify-between gap-4">
          <div>
            <h4 class="text-lg font-bold text-slate-900">반납 사진</h4>
            <p class="mt-1 text-sm text-slate-500">
              {{ selectedPhotoReturn.team_code }}조 · {{ selectedPhotoReturn.vehicle_number }}
            </p>
          </div>
          <button type="button" class="text-slate-400 hover:text-slate-700" @click="closePhotoModal">닫기</button>
        </div>

        <div class="mt-5 grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          <div
            v-for="photo in selectedPhotoReturn.photos || []"
            :key="photo.id"
            class="overflow-hidden rounded-xl border border-gray-200 bg-slate-50"
          >
            <div class="flex items-center justify-between gap-3 border-b bg-white px-4 py-3">
              <div>
                <p class="text-sm font-bold text-slate-900">{{ photo.kind_display }}</p>
                <p class="text-xs text-slate-500">{{ photo.file_name }}</p>
              </div>
              <a
                :href="photo.image_url"
                target="_blank"
                rel="noreferrer"
                class="rounded border border-gray-300 px-2.5 py-1 text-xs font-semibold text-slate-700"
              >
                원본
              </a>
            </div>
            <img :src="photo.image_url" :alt="photo.kind_display" class="h-56 w-full object-cover bg-white" />
          </div>
          <div
            v-if="!(selectedPhotoReturn.photos || []).length"
            class="rounded-xl border border-dashed border-gray-300 px-4 py-12 text-center text-sm text-slate-400 md:col-span-2 xl:col-span-3"
          >
            등록된 사진이 없습니다.
          </div>
        </div>
      </div>
    </div>

    <div v-if="rejectTarget" class="fixed inset-0 z-50 flex items-center justify-center bg-black/45 px-4">
      <div class="w-full max-w-lg rounded-2xl bg-white p-6 shadow-xl">
        <div class="flex items-start justify-between gap-4">
          <div>
            <h4 class="text-lg font-bold text-slate-900">구독 신청 거절</h4>
            <p class="mt-1 text-sm text-slate-500">
              {{ rejectTarget.team_code }}조 · {{ rejectTarget.requested_date }}
            </p>
          </div>
          <button type="button" class="text-slate-400 hover:text-slate-700" @click="closeRejectModal">닫기</button>
        </div>

        <label class="mt-5 flex flex-col gap-2">
          <span class="text-sm font-semibold text-slate-700">거절 사유</span>
          <textarea
            v-model="rejectReason"
            rows="4"
            class="rounded-xl border border-gray-300 px-3 py-2 text-sm outline-none focus:border-red-400"
            placeholder="예: 배정 가능한 차량이 부족합니다."
          />
        </label>

        <div class="mt-6 flex justify-end gap-2">
          <button
            type="button"
            class="rounded-xl border border-gray-300 px-4 py-2 text-sm font-semibold text-slate-700"
            @click="closeRejectModal"
          >
            취소
          </button>
          <button
            type="button"
            class="rounded-xl border border-red-200 bg-red-50 px-4 py-2 text-sm font-bold text-red-700"
            :disabled="subscriptionActionId === rejectTarget.id"
            @click="submitReject"
          >
            거절 저장
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import {
  adjustReturn,
  approveSubscription,
  confirmReturn,
  fetchReturns,
  fetchSubscriptions,
  rejectSubscription,
} from '@/api/vehicle'

const props = defineProps({
  companyCode: {
    type: String,
    required: true,
  },
})

const kind = ref('request')
const subscriptionRows = ref([])
const returnRowsAll = ref([])
const subscriptionActionId = ref(null)
const returnActionId = ref(null)
const selectedReturn = ref(null)
const selectedPhotoReturn = ref(null)
const rejectTarget = ref(null)
const rejectReason = ref('')
const returnModalMode = ref('confirm')
const returnConfirmForm = ref({
  confirmed_date: '',
  confirmed_time: '10:00',
})
const returnAdjustForm = ref({
  block_reason: '',
  available_dates: '',
})

const requestRows = computed(() =>
  subscriptionRows.value.filter((row) => ['REQUESTED', 'REJECTED'].includes(row.status)),
)

const returnRows = computed(() => returnRowsAll.value)

const subscriptionStatusClass = (status) => ({
  REQUESTED: 'bg-amber-100 text-amber-700',
  REJECTED: 'bg-red-100 text-red-700',
  APPROVED: 'bg-blue-100 text-blue-700',
  VEHICLES_SELECTED: 'bg-lime-100 text-lime-700',
  COMPLETED: 'bg-green-100 text-green-700',
}[status] || 'bg-gray-100 text-slate-600')

const subscriptionStatusLabel = (status) => ({
  REQUESTED: '신청 접수',
  REJECTED: '거절됨',
  APPROVED: '승인됨',
  VEHICLES_SELECTED: '차량 선택 완료',
  COMPLETED: '완료',
}[status] || status)

const returnStatusClass = (status) => ({
  REQUESTED: 'bg-amber-100 text-amber-700',
  CONFIRMED: 'bg-green-100 text-green-700',
  NEEDS_ADJUST: 'bg-red-100 text-red-700',
  COMPLETED: 'bg-slate-100 text-slate-700',
}[status] || 'bg-gray-100 text-slate-600')

const returnStatusLabel = (status) => ({
  REQUESTED: '반납 요청',
  CONFIRMED: '일정 확정',
  NEEDS_ADJUST: '일정 조정 요청',
  COMPLETED: '처리 완료',
}[status] || status)

const reload = async () => {
  const params = props.companyCode ? { company: props.companyCode } : {}
  try {
    const [subscriptionsResponse, returnsResponse] = await Promise.all([
      fetchSubscriptions(params),
      fetchReturns(params),
    ])
    subscriptionRows.value = subscriptionsResponse.data?.results || subscriptionsResponse.data || []
    returnRowsAll.value = returnsResponse.data?.results || returnsResponse.data || []
  } catch {
    subscriptionRows.value = []
    returnRowsAll.value = []
  }
}

const approveRow = async (row) => {
  subscriptionActionId.value = row.id
  try {
    await approveSubscription(row.id)
    await reload()
  } catch (error) {
    alert(error.response?.data?.detail || '승인 처리에 실패했습니다.')
  } finally {
    subscriptionActionId.value = null
  }
}

const openRejectModal = (row) => {
  rejectTarget.value = row
  rejectReason.value = row.reject_reason || ''
}

const closeRejectModal = () => {
  rejectTarget.value = null
  rejectReason.value = ''
}

const submitReject = async () => {
  if (!rejectTarget.value) return
  subscriptionActionId.value = rejectTarget.value.id
  try {
    await rejectSubscription(rejectTarget.value.id, { reject_reason: rejectReason.value.trim() })
    closeRejectModal()
    await reload()
  } catch (error) {
    alert(error.response?.data?.detail || '거절 처리에 실패했습니다.')
  } finally {
    subscriptionActionId.value = null
  }
}

const openReturnModal = (row, mode) => {
  selectedReturn.value = row
  returnModalMode.value = mode
  returnConfirmForm.value = {
    confirmed_date: row.confirmed_date || row.hope_date || '',
    confirmed_time: (row.confirmed_time || row.hope_time || '10:00').slice(0, 5),
  }
  returnAdjustForm.value = {
    block_reason: row.block_reason || '',
    available_dates: row.available_dates || '',
  }
}

const closeReturnModal = () => {
  selectedReturn.value = null
}

const openPhotoModal = (row) => {
  selectedPhotoReturn.value = row
}

const closePhotoModal = () => {
  selectedPhotoReturn.value = null
}

const submitReturnAction = async () => {
  if (!selectedReturn.value) return
  returnActionId.value = selectedReturn.value.id
  try {
    if (returnModalMode.value === 'confirm') {
      await confirmReturn(selectedReturn.value.id, returnConfirmForm.value)
    } else {
      await adjustReturn(selectedReturn.value.id, returnAdjustForm.value)
    }
    closeReturnModal()
    await reload()
  } catch (error) {
    alert(error.response?.data?.detail || '반납 요청 처리에 실패했습니다.')
  } finally {
    returnActionId.value = null
  }
}

watch(() => props.companyCode, reload)
onMounted(reload)
</script>
