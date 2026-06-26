<template>
  <div class="space-y-3">
    <section class="rounded-xl border border-slate-200 bg-white">
      <div class="flex flex-col gap-3 border-b border-slate-200 px-4 py-3 lg:flex-row lg:items-center lg:justify-between">
        <div>
          <h3 class="text-base font-bold text-slate-950">피트 차량현황</h3>
          <p class="mt-1 text-sm text-slate-500">입고, 출고, 작업 상태와 저장 대기 건을 관리합니다.</p>
        </div>
        <div class="flex flex-wrap gap-2">
          <button
            type="button"
            class="rounded-md bg-slate-900 px-3 py-2 text-xs font-bold text-white hover:bg-slate-800"
            @click="addNewRow"
          >
            입고 등록
          </button>
          <button
            type="button"
            class="rounded-md border border-slate-300 px-3 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-50"
            @click="reload"
          >
            새로고침
          </button>
        </div>
      </div>

      <div class="grid border-b border-slate-200 bg-slate-50/70 sm:grid-cols-2 lg:grid-cols-4">
        <div class="border-b border-r border-slate-200 px-4 py-3">
          <p class="text-xs font-semibold text-slate-500">피트 입고 중</p>
          <p class="mt-1 text-xl font-bold text-slate-950">{{ inPitCount }}</p>
        </div>
        <div class="border-b border-r border-slate-200 px-4 py-3">
          <p class="text-xs font-semibold text-slate-500">수리 대기</p>
          <p class="mt-1 text-xl font-bold text-slate-950">{{ repairQueue.length }}</p>
        </div>
        <div class="border-b border-r border-slate-200 px-4 py-3">
          <p class="text-xs font-semibold text-slate-500">미저장 변경</p>
          <p class="mt-1 text-xl font-bold text-slate-950">{{ dirtyCount }}</p>
        </div>
        <div class="border-b border-slate-200 px-4 py-3">
          <p class="text-xs font-semibold text-slate-500">조회 이력</p>
          <p class="mt-1 text-xl font-bold text-slate-950">{{ rows.length }}</p>
        </div>
      </div>

      <div class="space-y-2 px-4 py-3">
        <div class="space-y-2">
          <div class="flex flex-wrap items-center gap-2 lg:flex-nowrap lg:whitespace-nowrap">
            <span class="shrink-0 text-xs font-semibold text-slate-500">입고 사유</span>
            <button
              v-for="reason in reasonFilters"
              :key="reason.v"
              type="button"
              class="shrink-0 rounded-md px-2.5 py-1.5 text-xs font-semibold"
              :class="filterReason === reason.v ? 'bg-slate-900 text-white' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'"
              @click="filterReason = reason.v; reload()"
            >
              {{ reason.label }}
            </button>
          </div>
          <div class="flex flex-wrap items-center gap-2">
            <span class="text-xs font-semibold text-slate-500">피트 상태</span>
            <button
              type="button"
              class="rounded-md px-3 py-1.5 text-xs font-semibold"
              :class="filterInPit === 'true' ? 'bg-slate-900 text-white' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'"
              @click="filterInPit = filterInPit === 'true' ? '' : 'true'; reload()"
            >
              피트중
            </button>
            <button
              type="button"
              class="rounded-md px-3 py-1.5 text-xs font-semibold"
              :class="filterInPit === 'false' ? 'bg-slate-900 text-white' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'"
              @click="filterInPit = filterInPit === 'false' ? '' : 'false'; reload()"
            >
              출고 완료
            </button>
          </div>
        </div>

        <label class="block max-w-[420px] xl:ml-auto">
          <span class="mb-1 block text-xs font-semibold text-slate-500">검색</span>
          <input
            v-model="search"
            type="text"
            placeholder="차량번호 또는 비고"
            class="w-full rounded-md border border-slate-300 px-3 py-2 text-sm outline-none focus:border-slate-900"
            @input="debouncedReload"
          />
        </label>
      </div>
    </section>

    <section class="overflow-hidden rounded-xl border border-slate-200 bg-white">
      <div class="flex flex-wrap items-center justify-between gap-3 border-b border-slate-200 px-4 py-3">
        <div>
          <h4 class="text-sm font-bold text-slate-950">수리 대기 차량</h4>
          <p class="mt-0.5 text-xs text-slate-500">차량관리에서 수리/대기중인 차량을 피트로 입고합니다.</p>
        </div>
        <div class="flex items-center gap-2">
          <span class="text-xs text-slate-500">{{ repairQueue.length }}대 대기</span>
          <button
            type="button"
            class="rounded-md border border-slate-300 px-3 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-50"
            @click="repairQueueCollapsed = !repairQueueCollapsed"
          >
            {{ repairQueueCollapsed ? '펼치기' : '접기' }}
          </button>
        </div>
      </div>

      <div v-if="!repairQueueCollapsed && repairQueue.length" class="divide-y divide-slate-100">
        <div
          v-for="vehicle in repairQueue"
          :key="vehicle.id"
          class="grid gap-3 px-4 py-3 md:grid-cols-[minmax(0,1fr)_auto] md:items-center"
        >
          <div class="min-w-0">
            <div class="flex flex-wrap items-center gap-2">
              <strong class="text-sm text-slate-950">{{ vehicle.vehicle_number }}</strong>
              <span class="rounded bg-slate-100 px-2 py-0.5 text-[11px] font-semibold text-slate-600">
                {{ vehicle.fleet || '플릿 없음' }}
              </span>
            </div>
            <p class="mt-1 text-xs text-slate-500">
              기사 {{ vehicle.driver || '-' }} · {{ vehicle.placement_status_display || '수리/대기중' }}
            </p>
          </div>
          <button
            type="button"
            class="rounded-md bg-slate-900 px-3 py-2 text-xs font-bold text-white hover:bg-slate-800"
            @click="handlePitIntake(vehicle)"
          >
            피트 입고
          </button>
        </div>
      </div>
      <div v-else-if="!repairQueueCollapsed" class="px-4 py-10 text-center text-sm text-slate-400">
        대기 중인 수리 차량이 없습니다.
      </div>
    </section>

    <div
      v-if="dirtyCount > 0"
      class="flex items-center gap-3 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3"
    >
      <p class="flex-1 text-sm font-semibold text-amber-800">저장되지 않은 변경 {{ dirtyCount }}건</p>
      <button class="rounded-md border border-slate-300 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700" @click="reload">
        되돌리기
      </button>
      <button class="rounded-md bg-slate-900 px-3 py-1.5 text-xs font-bold text-white" @click="saveAll">
        모두 저장
      </button>
    </div>

    <section class="overflow-hidden rounded-xl border border-slate-200 bg-white">
      <div class="flex flex-wrap items-center justify-between gap-3 border-b border-slate-200 px-4 py-3">
        <div>
          <h4 class="text-sm font-bold text-slate-950">피트 이력</h4>
          <p class="mt-0.5 text-xs text-slate-500">입고/출고, 사유, 상태, 비고를 행 단위로 저장합니다.</p>
        </div>
        <span class="text-xs text-slate-500">{{ rows.length }}건</span>
      </div>

      <div class="max-h-[700px] overflow-auto">
        <table class="w-full min-w-[900px] table-fixed text-sm">
          <colgroup>
            <col class="w-[160px]" />
            <col class="w-[220px]" />
            <col class="w-[220px]" />
            <col class="w-[220px]" />
            <col class="w-[80px]" />
          </colgroup>
          <thead class="sticky top-0 z-10 border-b border-slate-200 bg-slate-50">
            <tr>
              <th class="px-4 py-2.5 text-left text-xs font-bold text-slate-500">차량</th>
              <th class="px-4 py-2.5 text-left text-xs font-bold text-slate-500">입고 / 출고</th>
              <th class="px-4 py-2.5 text-left text-xs font-bold text-slate-500">사유 / 상태</th>
              <th class="px-4 py-2.5 text-left text-xs font-bold text-slate-500">비고</th>
              <th class="px-4 py-2.5 text-right text-xs font-bold text-slate-500">작업</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in rows" :key="row._key" class="border-t border-slate-100 hover:bg-slate-50" :class="row._row_bg">
              <td class="px-4 py-3 align-top">
                <span
                  class="rounded px-2 py-0.5 text-[11px] font-semibold"
                  :class="row._isNew ? 'bg-slate-900 text-white' : isDirty(row) ? 'bg-amber-100 text-amber-700' : 'bg-slate-100 text-slate-500'"
                >
                  {{ row._isNew ? '신규' : isDirty(row) ? '수정됨' : '저장됨' }}
                </span>
                <input
                  v-model="row.vehicle_number_short"
                  type="text"
                  maxlength="8"
                  class="mt-2 w-full rounded-md border border-slate-300 px-2.5 py-2 font-mono text-xs font-semibold outline-none focus:border-slate-900"
                  placeholder="차량번호"
                />
              </td>
              <td class="px-4 py-3 align-top">
                <input v-model="row.in_date" type="date" class="w-full rounded-md border border-slate-300 px-2.5 py-2 text-xs outline-none focus:border-slate-900" />
                <div class="mt-2 flex items-center gap-2">
                  <input v-model="row.out_date" type="date" class="w-full rounded-md border border-slate-300 px-2.5 py-2 text-xs outline-none focus:border-slate-900" />
                  <span v-if="!row.out_date && !row._isNew" class="shrink-0 text-[11px] font-semibold text-blue-600">피트중</span>
                </div>
              </td>
              <td class="px-4 py-3 align-top">
                <select v-model="row.reason" class="w-full rounded-md border border-slate-300 px-2.5 py-2 text-xs font-semibold outline-none focus:border-slate-900">
                  <option v-for="reason in reasonOptions" :key="reason.v" :value="reason.v">{{ reason.label }}</option>
                </select>
                <select
                  v-if="row.vehicle"
                  :value="row._placement"
                  class="mt-2 w-full rounded-md border border-slate-300 px-2.5 py-2 text-xs font-semibold outline-none focus:border-slate-900"
                  @change="changePlacement(row, $event.target.value)"
                >
                  <option value="IDLE">유휴</option>
                  <option value="REPAIRING">수리중</option>
                  <option value="OPERATING">운영중</option>
                </select>
                <span v-else class="mt-2 block text-xs text-slate-400">차량 미연결</span>
              </td>
              <td class="px-4 py-3 align-top">
                <input
                  v-model="row.note"
                  type="text"
                  class="w-full rounded-md border border-slate-300 px-3 py-2 text-xs outline-none focus:border-slate-900"
                  :class="row.note_highlight ? 'bg-amber-50' : ''"
                />
              </td>
              <td class="px-4 py-3 text-right align-top">
                <button
                  v-if="row._isNew"
                  type="button"
                  class="rounded-md bg-slate-900 px-3 py-2 text-[11px] font-bold text-white"
                  @click="confirmNewRow(row)"
                >
                  등록
                </button>
                <button
                  v-else
                  type="button"
                  class="rounded-md border border-red-200 px-3 py-2 text-[11px] font-semibold text-red-700"
                  @click="onDelete(row)"
                >
                  삭제
                </button>
                <button
                  v-if="row._isNew"
                  type="button"
                  class="mt-1 rounded-md border border-slate-300 px-3 py-2 text-[11px] font-semibold text-slate-600"
                  @click="cancelNewRow(row)"
                >
                  취소
                </button>
              </td>
            </tr>
            <tr v-if="!rows.length">
              <td colspan="5" class="px-4 py-12 text-center text-sm text-slate-400">조회된 피트 이력이 없습니다.</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import {
  createPitRecord,
  deletePitRecord,
  fetchCompanies,
  fetchPitRecords,
  fetchVehicles,
  updatePitRecord,
  updateVehicle,
} from '@/api/vehicle'

const props = defineProps({
  companyCode: {
    type: String,
    required: true,
  },
})

const reasonFilters = [
  { v: '', label: '전체' },
  { v: 'SERVICE', label: '서비스 대기' },
  { v: 'REPAIR', label: '수리 입고' },
  { v: 'ACCIDENT', label: '사고 입고' },
  { v: 'RETURN', label: '구독 반납' },
]

const reasonOptions = [
  { v: 'SERVICE', label: '서비스 대기' },
  { v: 'REPAIR', label: '수리 입고' },
  { v: 'ACCIDENT', label: '사고 입고' },
  { v: 'RETURN', label: '구독 반납' },
]

const rows = ref([])
const repairQueue = ref([])
const repairQueueCollapsed = ref(true)
const original = ref({})
const filterReason = ref('')
const filterInPit = ref('')
const search = ref('')
const companyId = ref(null)
const dirtyCount = ref(0)
let debounceId = null

const currentPlacement = (item) => item.vehicle_placement_status || (item.out_date ? 'OPERATING' : 'IDLE')
const inPitCount = computed(() => rows.value.filter((row) => !row.out_date).length)

const recomputeDirty = () => {
  dirtyCount.value = rows.value.filter((row) => row._isNew || isDirty(row)).length
}

const isDirty = (row) => {
  if (!row.id) return false
  const origin = original.value[row.id]
  if (!origin) return false
  return ['in_date', 'out_date', 'vehicle_number_short', 'reason', 'note', 'note_highlight', '_placement']
    .some((key) => String(row[key] || '') !== String(origin[key] || ''))
}

const reasonRowBg = (reason) => (reason === 'SERVICE' ? 'bg-cyan-50/50' : '')

const loadCompanyId = async () => {
  try {
    const response = await fetchCompanies()
    const items = response.data?.results || response.data || []
    const found = items.find((company) => company.code === props.companyCode)
    companyId.value = found?.id || items[0]?.id || null
  } catch {
    companyId.value = null
  }
}

const loadRepairQueue = async () => {
  const pitResponse = await fetchPitRecords({
    company: props.companyCode,
    in_pit: 'true',
    ordering: '-in_date',
  }).catch(() => ({ data: [] }))

  const activeShortNumbers = new Set(
    (pitResponse.data?.results || pitResponse.data || []).map((row) => row.vehicle_number_short),
  )

  const vehicleResponse = await fetchVehicles({
    company: props.companyCode,
    category: 'REPAIRING',
    ordering: 'vehicle_number',
  }).catch(() => ({ data: [] }))

  repairQueue.value = (vehicleResponse.data?.results || vehicleResponse.data || []).filter(
    (vehicle) => !activeShortNumbers.has(vehicle.vehicle_number_short),
  )
}

const reload = async () => {
  const params = { company: props.companyCode, ordering: '-in_date' }
  if (filterReason.value) params.reason = filterReason.value
  if (filterInPit.value) params.in_pit = filterInPit.value
  if (search.value) params.search = search.value

  try {
    const response = await fetchPitRecords(params)
    const items = response.data?.results || response.data || []
    rows.value = items.map((item) => ({
      ...item,
      _key: item.id,
      _isNew: false,
      _row_bg: reasonRowBg(item.reason),
      _placement: currentPlacement(item),
      company: companyId.value,
    }))
    original.value = Object.fromEntries(rows.value.map((item) => [item.id, { ...item }]))
    recomputeDirty()
  } catch {
    rows.value = []
  }

  await loadRepairQueue()
}

const debouncedReload = () => {
  clearTimeout(debounceId)
  debounceId = setTimeout(reload, 300)
}

const addNewRow = () => {
  rows.value.unshift({
    _key: `new_${Date.now()}`,
    _isNew: true,
    company: companyId.value,
    in_date: new Date().toISOString().slice(0, 10),
    out_date: '',
    vehicle_number_short: '',
    reason: 'REPAIR',
    note: '',
    note_highlight: false,
    _row_bg: '',
    _placement: 'IDLE',
  })
  recomputeDirty()
}

const cancelNewRow = (row) => {
  rows.value = rows.value.filter((item) => item._key !== row._key)
  recomputeDirty()
}

const confirmNewRow = async (row) => {
  if (!row.vehicle_number_short || !row.reason || !row.in_date) {
    alert('차량번호, 입고일, 입고 사유는 필수입니다.')
    return
  }
  try {
    await createPitRecord({
      company: companyId.value,
      vehicle_number_short: row.vehicle_number_short,
      in_date: row.in_date,
      out_date: row.out_date || null,
      reason: row.reason,
      note: row.note || '',
      note_highlight: !!row.note_highlight,
    })
    await reload()
  } catch (error) {
    alert(`입고 등록에 실패했습니다: ${error.response?.data?.detail || error.message}`)
  }
}

const handlePitIntake = async (vehicle) => {
  if (!confirm(`${vehicle.vehicle_number} 차량을 피트로 입고하시겠습니까?`)) return
  try {
    await createPitRecord({
      company: vehicle.company || companyId.value,
      vehicle: vehicle.id,
      vehicle_number_short: vehicle.vehicle_number_short,
      in_date: new Date().toISOString().slice(0, 10),
      reason: 'REPAIR',
      note: `${vehicle.vehicle_number} 피트 입고`,
    })
    await reload()
  } catch (error) {
    alert(`피트 입고에 실패했습니다: ${error.response?.data?.detail || error.message}`)
  }
}

const changePlacement = async (row, newStatus) => {
  if (!row.vehicle) return
  try {
    await updateVehicle(row.vehicle, { placement_status: newStatus })
    if (newStatus === 'OPERATING') {
      const today = new Date().toISOString().slice(0, 10)
      row.out_date = row.out_date || today
      await updatePitRecord(row.id, { out_date: row.out_date })
    } else if (row.out_date) {
      row.out_date = ''
      await updatePitRecord(row.id, { out_date: null })
    }
    row._placement = newStatus
    await reload()
  } catch (error) {
    alert(`작업 상태 변경에 실패했습니다: ${error.response?.data?.detail || error.message}`)
  }
}

const onDelete = async (row) => {
  if (!confirm(`${row.vehicle_number_short} 이력을 삭제하시겠습니까?`)) return
  try {
    await deletePitRecord(row.id)
    await reload()
  } catch {
    alert('삭제에 실패했습니다.')
  }
}

const saveAll = async () => {
  for (const row of rows.value) {
    if (row._isNew || !isDirty(row)) continue
    try {
      await updatePitRecord(row.id, {
        in_date: row.in_date,
        out_date: row.out_date || null,
        vehicle_number_short: row.vehicle_number_short,
        reason: row.reason,
        note: row.note || '',
        note_highlight: !!row.note_highlight,
      })
      if (row.vehicle) {
        await updateVehicle(row.vehicle, { placement_status: row._placement })
      }
    } catch {
      alert(`${row.vehicle_number_short} 저장에 실패했습니다.`)
      return
    }
  }
  await reload()
}

watch(
  () => [rows.value, ...rows.value.map((row) => `${row.in_date}|${row.out_date}|${row.vehicle_number_short}|${row.reason}|${row.note}|${row._placement}`)],
  recomputeDirty,
  { deep: true },
)

watch(() => props.companyCode, async () => {
  await loadCompanyId()
  await reload()
})

onMounted(async () => {
  await loadCompanyId()
  await reload()
})
</script>
