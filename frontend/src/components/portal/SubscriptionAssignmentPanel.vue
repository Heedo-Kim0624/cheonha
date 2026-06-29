<template>
  <div class="space-y-4">
    <div class="rounded-xl border border-slate-200 bg-white px-5 py-4">
      <div class="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
        <div>
          <h3 class="text-lg font-bold text-slate-900">차량 배정</h3>
          <p class="mt-2 text-sm text-slate-500">
            차량관리에서 승인한 구독 요청을 가져와 실제 차량을 선택하고 배정 완료 처리합니다.
          </p>
        </div>
        <div class="shrink-0 whitespace-nowrap rounded-lg bg-slate-50 px-4 py-2 text-sm font-semibold text-slate-600">
          승인된 요청만 표시
        </div>
      </div>
    </div>

    <div class="grid gap-4 xl:grid-cols-[360px_minmax(0,1fr)]">
      <section class="overflow-hidden rounded-xl border border-slate-200 bg-white">
        <div class="flex items-start justify-between gap-3 border-b border-slate-200 px-4 py-3">
          <div class="min-w-0">
            <div class="flex items-center gap-2">
              <h4 class="text-sm font-bold text-slate-950">배정 대기 요청</h4>
              <span class="rounded bg-slate-100 px-2 py-0.5 text-[11px] font-semibold text-slate-500">{{ assignmentRows.length }}건</span>
            </div>
            <p class="mt-1 truncate text-xs text-slate-500">선택하면 오른쪽에서 차량을 배정합니다.</p>
          </div>
          <button
            type="button"
            class="shrink-0 whitespace-nowrap rounded-md border border-slate-300 px-2.5 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-50"
            @click="reload"
          >
            새로고침
          </button>
        </div>

        <div class="divide-y divide-slate-100">
          <button
            v-for="row in assignmentRows"
            :key="row.id"
            type="button"
            class="w-full px-4 py-3 text-left transition-colors hover:bg-slate-50"
            :class="selectedRequest?.id === row.id ? 'bg-lime-50 ring-1 ring-inset ring-lime-200' : ''"
            @click="selectRequest(row)"
          >
            <div class="flex items-center justify-between gap-3">
              <p class="text-sm font-bold text-slate-950">{{ row.team_code }}조</p>
              <p class="text-sm font-bold text-lime-700">{{ row.quantity }}대</p>
            </div>
            <div class="mt-1 flex items-center justify-between gap-3">
              <p class="min-w-0 truncate text-xs text-slate-500">{{ row.phone || '-' }}</p>
              <p class="shrink-0 text-xs text-slate-500">{{ row.requested_date }}</p>
            </div>
            <div class="mt-2 flex items-center justify-between gap-3">
              <span class="rounded-full px-2.5 py-1 text-[11px] font-bold" :class="statusClass(row.status)">
                {{ row.status_display }}
              </span>
              <span v-if="row.matched_vehicles?.length" class="text-[11px] font-semibold text-slate-500">
                {{ row.matched_vehicles.length }}대 선택
              </span>
            </div>

            <div v-if="row.matched_vehicles?.length" class="mt-2 flex flex-wrap gap-1.5">
              <span
                v-for="vehicle in row.matched_vehicles"
                :key="vehicle.id"
                class="rounded bg-slate-100 px-2 py-0.5 text-[11px] font-semibold text-slate-600"
              >
                {{ vehicle.vehicle_number }}
              </span>
            </div>
          </button>

          <div v-if="!assignmentRows.length" class="px-4 py-10 text-center text-sm text-slate-400">
            배정할 승인 요청이 없습니다.
          </div>
        </div>
      </section>

      <section class="rounded-xl border border-slate-200 bg-white">
        <div v-if="selectedRequest" class="space-y-4 p-5">
          <div class="flex flex-col gap-4 border-b border-gray-100 pb-4 lg:flex-row lg:items-start lg:justify-between">
            <div>
              <h4 class="font-bold text-slate-900">{{ selectedRequest.team_code }}조 차량 배정</h4>
              <p class="mt-1 text-sm text-slate-500">
                요청 대수 {{ selectedRequest.quantity }}대 · 현재 선택 {{ selectedVehicleIds.length }}대
              </p>
            </div>
            <div class="flex flex-wrap gap-2">
              <button
                type="button"
                class="rounded-lg border border-gray-300 px-4 py-2 text-sm font-semibold text-slate-700"
                :disabled="assignmentSaving"
                @click="reloadAvailableVehicles"
              >
                차량 목록 새로고침
              </button>
              <button
                v-if="selectedRequest.status === 'VEHICLES_SELECTED'"
                type="button"
                class="rounded-lg bg-slate-900 px-4 py-2 text-sm font-bold text-white"
                :disabled="assignmentSaving"
                @click="completeSelectedRequest"
              >
                배정 완료
              </button>
            </div>
          </div>

          <div class="rounded-xl border border-blue-100 bg-blue-50 px-4 py-3 text-sm text-blue-800">
            전체 차량 목록을 표시합니다. 요청 대수와 동일한 수만 선택한 뒤 <strong>차량 배정 저장</strong>을 누르세요.
          </div>

          <div class="rounded-xl border border-slate-200 bg-slate-50/70 p-3">
            <div class="grid gap-2 md:grid-cols-2">
              <input
                v-model="vehicleSearch"
                type="text"
                placeholder="차량번호, 플릿, 기사명 검색"
                class="w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm outline-none focus:border-slate-900"
              />
              <select
                v-model="vehicleDriverFilter"
                class="w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm font-semibold text-slate-700 outline-none focus:border-slate-900"
              >
                <option value="">기사 전체</option>
                <option value="WITH_DRIVER">기사 있음</option>
                <option value="NO_DRIVER">기사 없음</option>
              </select>
              <select
                v-model="vehiclePlacementFilter"
                class="w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm font-semibold text-slate-700 outline-none focus:border-slate-900"
              >
                <option value="">상태 전체</option>
                <option value="OPERATING">운영중</option>
                <option value="REPAIRING">수리/대기중</option>
                <option value="IDLE">휴지</option>
                <option value="NOT_SHIPPED">미출고</option>
              </select>
              <select
                v-model="vehicleFleetFilter"
                class="w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm font-semibold text-slate-700 outline-none focus:border-slate-900"
              >
                <option value="">플릿 전체</option>
                <option v-for="fleet in vehicleFleetOptions" :key="fleet" :value="fleet">{{ fleet }}</option>
              </select>
              <button
                type="button"
                class="whitespace-nowrap rounded-md border border-slate-300 bg-white px-3 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50"
                @click="resetVehicleFilters"
              >
                초기화
              </button>
            </div>
          </div>

          <div class="flex flex-col gap-3 rounded-xl border border-slate-200 px-4 py-3 lg:flex-row lg:items-center lg:justify-between">
            <p class="text-sm text-slate-500">
              표시 <strong class="text-slate-900">{{ filteredVehicles.length }}</strong>대 / 전체 {{ availableVehicles.length }}대 ·
              선택 <strong class="text-lime-700">{{ selectedVehicleIds.length }}</strong>대
            </p>
            <button
              type="button"
              class="rounded-md bg-lime-500 px-4 py-2 text-sm font-bold text-slate-900 hover:bg-lime-400"
              :disabled="assignmentSaving"
              @click="saveAssignment"
            >
              차량 배정 저장
            </button>
          </div>

          <div class="grid gap-3 md:grid-cols-2">
            <label
              v-for="vehicle in filteredVehicles"
              :key="vehicle.id"
              class="flex cursor-pointer items-start gap-3 rounded-2xl border border-gray-200 px-4 py-4 transition-colors hover:border-lime-400"
              :class="selectedVehicleIds.includes(vehicle.id) ? 'border-lime-400 bg-lime-50' : 'bg-white'"
            >
              <input
                type="checkbox"
                class="mt-1 h-4 w-4"
                :checked="selectedVehicleIds.includes(vehicle.id)"
                @change="toggleVehicle(vehicle.id)"
              />
              <div class="min-w-0">
                <div class="flex flex-wrap items-center gap-2">
                  <strong class="truncate text-slate-900">{{ vehicle.vehicle_number }}</strong>
                  <span class="rounded bg-slate-100 px-2 py-0.5 text-[11px] font-semibold text-slate-700">
                    {{ vehicle.fleet || '플릿 없음' }}
                  </span>
                </div>
                <p class="mt-1 text-xs text-slate-500">
                  기사 {{ vehicle.driver || '-' }} · 상태 {{ vehicle.placement_status_display || vehicle.placement_status }}
                </p>
              </div>
            </label>
          </div>

          <div
            v-if="!filteredVehicles.length"
            class="rounded-xl border border-dashed border-gray-300 px-4 py-10 text-center text-sm text-slate-400"
          >
            검색 조건에 맞는 차량이 없습니다.
          </div>
        </div>

        <div v-else class="flex min-h-[220px] items-center justify-center p-6 text-center">
          <div>
            <p class="text-sm font-semibold text-slate-500">배정 요청을 선택하세요</p>
            <p class="mt-1 text-xs text-slate-400">왼쪽 목록에서 요청을 누르면 차량 선택 화면이 열립니다.</p>
          </div>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import {
  assignSubscriptionVehicles,
  completeSubscription,
  fetchSubscriptions,
  fetchVehicles,
} from '@/api/vehicle'

const props = defineProps({
  companyCode: {
    type: String,
    required: true,
  },
})

const assignmentRows = ref([])
const availableVehicles = ref([])
const selectedRequest = ref(null)
const selectedVehicleIds = ref([])
const vehicleSearch = ref('')
const vehicleDriverFilter = ref('')
const vehiclePlacementFilter = ref('')
const vehicleFleetFilter = ref('')
const assignmentSaving = ref(false)

const statusClass = (status) => ({
  APPROVED: 'bg-blue-100 text-blue-700',
  VEHICLES_SELECTED: 'bg-lime-100 text-lime-700',
  COMPLETED: 'bg-green-100 text-green-700',
}[status] || 'bg-gray-100 text-slate-600')

const vehicleFleetOptions = computed(() =>
  [...new Set(availableVehicles.value.map((vehicle) => vehicle.fleet).filter(Boolean))]
    .sort((a, b) => String(a).localeCompare(String(b), 'ko')),
)

const hasDriver = (vehicle) => Boolean(String(vehicle.driver || '').trim())

const filteredVehicles = computed(() => {
  const keyword = vehicleSearch.value.trim().toLowerCase()
  return availableVehicles.value.filter((vehicle) =>
    (!keyword ||
      [vehicle.vehicle_number, vehicle.fleet, vehicle.driver]
        .filter(Boolean)
        .some((value) => String(value).toLowerCase().includes(keyword))) &&
    (!vehicleDriverFilter.value ||
      (vehicleDriverFilter.value === 'WITH_DRIVER' ? hasDriver(vehicle) : !hasDriver(vehicle))) &&
    (!vehiclePlacementFilter.value || vehicle.placement_status === vehiclePlacementFilter.value) &&
    (!vehicleFleetFilter.value || vehicle.fleet === vehicleFleetFilter.value),
  )
})

const resetVehicleFilters = () => {
  vehicleSearch.value = ''
  vehicleDriverFilter.value = ''
  vehiclePlacementFilter.value = ''
  vehicleFleetFilter.value = ''
}

const reloadAvailableVehicles = async () => {
  const params = { ordering: 'vehicle_number' }
  if (props.companyCode) params.company = props.companyCode
  try {
    const response = await fetchVehicles(params)
    availableVehicles.value = response.data?.results || response.data || []
  } catch {
    availableVehicles.value = []
  }
}

const reload = async () => {
  const params = props.companyCode ? { company: props.companyCode } : {}
  try {
    const response = await fetchSubscriptions(params)
    assignmentRows.value = (response.data?.results || response.data || []).filter((row) =>
      ['APPROVED', 'VEHICLES_SELECTED'].includes(row.status),
    )
  } catch {
    assignmentRows.value = []
  }

  if (selectedRequest.value) {
    const next = assignmentRows.value.find((row) => row.id === selectedRequest.value.id) || null
    selectedRequest.value = next
    selectedVehicleIds.value = next?.matched_vehicles?.map((item) => item.vehicle) || []
  }
}

const selectRequest = (row) => {
  selectedRequest.value = row
  selectedVehicleIds.value = row.matched_vehicles?.map((item) => item.vehicle) || []
}

const toggleVehicle = (vehicleId) => {
  if (!selectedRequest.value) return

  if (selectedVehicleIds.value.includes(vehicleId)) {
    selectedVehicleIds.value = selectedVehicleIds.value.filter((id) => id !== vehicleId)
    return
  }

  if (selectedVehicleIds.value.length >= Number(selectedRequest.value.quantity || 0)) {
    alert(`요청 대수 ${selectedRequest.value.quantity}대까지만 선택할 수 있습니다.`)
    return
  }

  selectedVehicleIds.value = [...selectedVehicleIds.value, vehicleId]
}

const saveAssignment = async () => {
  if (!selectedRequest.value) return
  if (selectedVehicleIds.value.length !== Number(selectedRequest.value.quantity || 0)) {
    alert(`요청 대수 ${selectedRequest.value.quantity}대와 동일하게 선택해야 합니다.`)
    return
  }

  assignmentSaving.value = true
  try {
    await assignSubscriptionVehicles(selectedRequest.value.id, selectedVehicleIds.value)
    await reload()
  } catch (error) {
    alert(error.response?.data?.detail || '차량 배정 저장에 실패했습니다.')
  } finally {
    assignmentSaving.value = false
  }
}

const completeSelectedRequest = async () => {
  if (!selectedRequest.value) return
  assignmentSaving.value = true
  try {
    await completeSubscription(selectedRequest.value.id)
    selectedRequest.value = null
    selectedVehicleIds.value = []
    await reload()
  } catch (error) {
    alert(error.response?.data?.detail || '배정 완료 처리에 실패했습니다.')
  } finally {
    assignmentSaving.value = false
  }
}

watch(() => props.companyCode, async () => {
  selectedRequest.value = null
  selectedVehicleIds.value = []
  await Promise.all([reload(), reloadAvailableVehicles()])
})

onMounted(async () => {
  await Promise.all([reload(), reloadAvailableVehicles()])
})
</script>
