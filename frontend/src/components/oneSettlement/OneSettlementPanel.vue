<template>
  <section class="space-y-5">
    <div class="flex flex-wrap items-end justify-between gap-3 rounded-xl border border-slate-200 bg-slate-50 p-4">
      <div>
        <p class="text-xs font-bold uppercase tracking-wide text-slate-500">ONE Settlement</p>
        <h3 class="mt-1 text-xl font-extrabold text-slate-900">오네 정산</h3>
        <p class="mt-1 text-sm text-slate-500">RAW 시트 기준으로 가구, 박스, 지급액을 계산합니다.</p>
      </div>
      <label class="block">
        <span class="mb-1 block text-sm font-bold text-slate-600">정산 월</span>
        <input
          v-model="selectedMonth"
          type="month"
          class="rounded-lg border border-slate-300 bg-white px-4 py-2 font-semibold outline-none focus:border-primary"
        />
      </label>
    </div>

    <div v-if="error" class="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm font-bold text-red-700">
      {{ error }}
    </div>

    <section v-if="activeTab === 'upload'" class="space-y-4">
      <div
        data-testid="one-upload-card"
        class="rounded-xl border bg-white p-5 transition-colors"
        :class="isDraggingUpload ? 'border-primary bg-primary/5' : 'border-slate-200'"
        @dragenter.prevent="onUploadDragEnter"
        @dragover.prevent="onUploadDragOver"
        @dragleave.prevent="onUploadDragLeave"
        @drop.prevent="onUploadDrop"
      >
        <div class="mb-4 flex flex-wrap items-center justify-between gap-3">
          <div>
            <h4 class="text-lg font-extrabold text-slate-900">엑셀 업로드</h4>
            <p class="text-sm text-slate-500">여러 개의 .xlsx 파일을 한 번에 올릴 수 있습니다. RAW 내용이 같은 파일은 중복 처리됩니다.</p>
          </div>
          <input
            ref="fileInput"
            type="file"
            multiple
            accept=".xlsx,.xlsm"
            class="hidden"
            @change="onFileChange"
          />
          <button type="button" class="rounded-lg bg-primary px-4 py-2 font-bold text-white" @click="fileInput?.click()">
            파일 선택
          </button>
        </div>

        <div
          data-testid="one-upload-dropzone"
          class="mb-4 rounded-xl border-2 border-dashed px-4 py-8 text-center transition-colors"
          :class="isDraggingUpload ? 'border-primary bg-white text-primary-dark' : 'border-slate-300 bg-slate-50 text-slate-500'"
        >
          <p class="text-base font-extrabold text-slate-800">
            엑셀 파일을 여기에 끌어다 놓으세요
          </p>
          <p class="mt-1 text-sm">
            .xlsx, .xlsm 파일만 업로드됩니다. 여러 파일을 한 번에 드롭할 수 있습니다.
          </p>
        </div>

        <div v-if="selectedFiles.length" class="mb-4 rounded-lg border border-slate-200 bg-slate-50 p-3">
          <p class="mb-2 text-sm font-bold text-slate-600">선택된 파일 {{ selectedFiles.length }}개</p>
          <div class="max-h-32 overflow-y-auto text-sm text-slate-600">
            <div v-for="file in selectedFiles" :key="file.name" class="truncate">{{ file.name }}</div>
          </div>
          <button
            type="button"
            class="mt-3 rounded-lg bg-slate-900 px-4 py-2 font-bold text-white disabled:opacity-50"
            :disabled="uploading"
            @click="submitUpload"
          >
            {{ uploading ? '업로드 중...' : '업로드 실행' }}
          </button>
        </div>

        <div v-if="uploadResult" class="rounded-lg border border-slate-200 bg-white p-3 text-sm">
          <p class="font-bold text-slate-800">
            업로드 {{ uploadResult.imported_count }}개, 중복 {{ uploadResult.duplicate_count }}개, 실패 {{ uploadResult.error_count }}개
          </p>
          <div class="mt-2 max-h-44 overflow-y-auto space-y-1">
            <div
              v-for="item in uploadResult.results"
              :key="`${item.filename}-${item.detail || item.upload?.id}`"
              class="flex items-center justify-between gap-3 rounded border border-slate-100 px-3 py-2"
            >
              <span class="truncate">{{ item.filename }}</span>
              <span
                class="shrink-0 rounded-full px-2 py-0.5 text-xs font-bold"
                :class="item.ok ? (item.duplicate ? 'bg-amber-50 text-amber-700' : 'bg-green-50 text-green-700') : 'bg-red-50 text-red-700'"
              >
                {{ item.ok ? (item.duplicate ? '중복' : '완료') : '실패' }}
              </span>
            </div>
          </div>
        </div>
      </div>

      <UploadTable :uploads="uploads" :deleting-id="deletingUploadId" @delete="deleteUpload" />
    </section>

    <section v-else-if="activeTab === 'summary'" class="space-y-4">
      <OneMonthlySummaryDashboard :summary="summary" :drivers="drivers" :month="selectedMonth" />
    </section>

    <section v-else-if="activeTab === 'collection'" class="space-y-4">
      <div class="rounded-xl border border-slate-200 bg-white p-5">
        <div class="flex flex-wrap items-end justify-between gap-3">
          <div>
            <h4 class="text-lg font-extrabold text-slate-900">월별 취합</h4>
            <p class="mt-1 text-sm text-slate-500">
              업로드된 ONE 데이터를 월별 취합 양식으로 펼쳐 표시합니다.
              전체 {{ formatNumber(collection.total) }}행 중 {{ formatNumber(collection.rows.length) }}행 표시
            </p>
          </div>
          <button
            type="button"
            class="rounded-lg bg-slate-900 px-4 py-2 text-sm font-bold text-white disabled:opacity-50"
            :disabled="collectionDownloading || !collection.total"
            @click="downloadCollection"
          >
            {{ collectionDownloading ? '다운로드 중...' : 'Excel 다운로드' }}
          </button>
        </div>
      </div>

      <DataTable title="월별 취합 미리보기">
        <thead>
          <tr>
            <th
              v-for="column in collection.columns"
              :key="column.key"
              :class="column.type === 'money' ? 'text-right' : ''"
            >
              {{ column.label }}
            </th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="collectionLoading">
            <td :colspan="collection.columns.length || 1" class="py-10 text-center text-slate-400">
              취합 데이터를 불러오는 중입니다.
            </td>
          </tr>
          <tr v-else-if="!collection.rows.length">
            <td :colspan="collection.columns.length || 1" class="py-10 text-center text-slate-400">
              표시할 취합 데이터가 없습니다.
            </td>
          </tr>
          <template v-else>
            <tr v-for="(row, rowIndex) in collection.rows" :key="`collection-${collection.page}-${rowIndex}`">
              <td
                v-for="column in collection.columns"
                :key="`${rowIndex}-${column.key}`"
                :class="column.type === 'money' ? 'text-right tabular-nums' : ''"
              >
                {{ formatCollectionValue(row, column) }}
              </td>
            </tr>
          </template>
        </tbody>
      </DataTable>

      <div class="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-slate-200 bg-white px-4 py-3">
        <div class="text-sm font-bold text-slate-500">
          {{ formatNumber(collectionStartRow) }}-{{ formatNumber(collectionEndRow) }} / {{ formatNumber(collection.total) }}행
        </div>
        <div class="flex items-center gap-2">
          <select
            v-model.number="collectionPageSize"
            class="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm font-bold"
            @change="changeCollectionPageSize"
          >
            <option :value="100">100행</option>
            <option :value="200">200행</option>
            <option :value="500">500행</option>
          </select>
          <button
            type="button"
            class="rounded-lg border border-slate-300 px-3 py-2 text-sm font-bold disabled:opacity-40"
            :disabled="collection.page <= 1 || collectionLoading"
            @click="goCollectionPage(collection.page - 1)"
          >
            이전
          </button>
          <span class="min-w-[96px] text-center text-sm font-extrabold text-slate-700">
            {{ collection.page }} / {{ collectionTotalPages }}
          </span>
          <button
            type="button"
            class="rounded-lg border border-slate-300 px-3 py-2 text-sm font-bold disabled:opacity-40"
            :disabled="collection.page >= collectionTotalPages || collectionLoading"
            @click="goCollectionPage(collection.page + 1)"
          >
            다음
          </button>
        </div>
      </div>
    </section>

    <section v-else-if="activeTab === 'drivers'" class="space-y-4">
      <DataTable title="배송원 목록">
        <thead>
          <tr>
            <th>배송원</th>
            <th class="text-right">착지/건</th>
            <th class="text-right">박스</th>
            <th class="text-right">추가박스</th>
            <th class="text-right">지급액</th>
            <th class="w-24 text-right">관리</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="driver in drivers" :key="driver.id">
            <td class="font-bold text-slate-900">{{ driver.name }}</td>
            <td class="text-right">{{ formatNumber(driver.households) }}</td>
            <td class="text-right">{{ formatNumber(driver.boxes) }}</td>
            <td class="text-right">{{ formatNumber(driver.extra_boxes) }}</td>
            <td class="text-right font-bold">{{ formatWon(driverListPayAmount(driver)) }}</td>
            <td class="text-right">
              <button type="button" class="rounded bg-primary px-3 py-1 text-xs font-bold text-white" @click="openStatement(driver)">
                명세서
              </button>
            </td>
          </tr>
        </tbody>
      </DataTable>
    </section>

    <section v-else class="space-y-4">
      <div class="rounded-xl border border-slate-200 bg-white p-5">
        <div class="mb-4 flex flex-wrap items-center gap-3">
          <select v-model="selectedDriverId" class="rounded-lg border border-slate-300 bg-white px-4 py-2 font-semibold">
            <option value="">배송원 선택</option>
            <option v-for="driver in drivers" :key="driver.id" :value="driver.id">{{ driver.name }}</option>
          </select>
          <button type="button" class="rounded-lg bg-primary px-4 py-2 font-bold text-white" :disabled="!selectedDriverId" @click="loadStatement(selectedDriverId)">
            지급명세서 보기
          </button>
        </div>
        <StatementView
          v-if="statement"
          :statement="statement"
          :saving="savingStatement"
          @save="saveStatement"
          @download-excel="downloadStatement('excel')"
          @download-pdf="downloadStatement('pdf')"
        />
        <div v-else class="rounded-lg border border-dashed border-slate-200 py-12 text-center text-slate-400">
          배송원을 선택하면 지급명세서가 표시됩니다.
        </div>
      </div>
    </section>
  </section>
</template>

<script setup>
import { computed, defineComponent, h, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { formatCurrency } from '@/utils/format'
import OneMonthlySummaryDashboard from './OneMonthlySummaryDashboard.vue'
import StatementView from './OneStatementSheet.vue'
import {
  deleteOneUpload,
  downloadOneCollectionExcel,
  downloadOneStatementExcel,
  downloadOneStatementPdf,
  fetchOneCollection,
  fetchOneDriverStatement,
  fetchOneDrivers,
  fetchOneSummary,
  fetchOneUploads,
  updateOneStatement,
  uploadOneFiles,
} from '@/api/oneSettlement'

const tabKeys = new Set(['upload', 'summary', 'collection', 'drivers', 'statements'])

const props = defineProps({
  companyCode: { type: String, default: 'new' },
})

const route = useRoute()
const router = useRouter()
const normalizeTab = (value) => {
  const next = String(Array.isArray(value) ? value[0] : (value || '')).trim()
  return tabKeys.has(next) ? next : 'upload'
}

const activeTab = ref(normalizeTab(route.query.one_tab))
const selectedMonth = ref(new Date().toISOString().slice(0, 7))
const selectedFiles = ref([])
const fileInput = ref(null)
const isDraggingUpload = ref(false)
const uploadDragDepth = ref(0)
const uploads = ref([])
const drivers = ref([])
const summary = ref({ summary: {}, by_service: [], by_day: [] })
const collection = ref({ columns: [], rows: [], page: 1, page_size: 200, total: 0 })
const collectionPageSize = ref(200)
const selectedDriverId = ref('')
const statement = ref(null)
const uploading = ref(false)
const deletingUploadId = ref('')
const loading = ref(false)
const collectionLoading = ref(false)
const collectionDownloading = ref(false)
const savingStatement = ref(false)
const uploadResult = ref(null)
const error = ref('')
const loaded = ref({
  uploads: false,
  summary: false,
  drivers: false,
})

const apiParams = computed(() => ({ company_app: props.companyCode || 'new' }))
const monthParams = computed(() => ({ ...apiParams.value, month: selectedMonth.value }))

const formatWon = (value) => `${formatCurrency(Number(value || 0))}원`
const formatNumber = (value) => Number(value || 0).toLocaleString('ko-KR')
const driverListPayAmount = (driver) => {
  if (driver?.statement_total_amount !== undefined && driver?.statement_total_amount !== null) {
    return driver.statement_total_amount
  }
  return driver?.amount || 0
}
const collectionTotalPages = computed(() => Math.max(1, Math.ceil(Number(collection.value.total || 0) / Number(collection.value.page_size || collectionPageSize.value || 1))))
const collectionStartRow = computed(() => collection.value.total ? ((collection.value.page - 1) * collection.value.page_size) + 1 : 0)
const collectionEndRow = computed(() => Math.min(collection.value.total || 0, collection.value.page * collection.value.page_size))

const resetLoadedData = () => {
  loaded.value = {
    uploads: false,
    summary: false,
    drivers: false,
  }
  collection.value = { columns: [], rows: [], page: 1, page_size: collectionPageSize.value, total: 0 }
}

const isAcceptedExcelFile = (file) => /\.(xlsx|xlsm)$/i.test(file?.name || '')

const setUploadFiles = (files) => {
  const rawFiles = Array.from(files || [])
  const acceptedFiles = rawFiles.filter(isAcceptedExcelFile)
  selectedFiles.value = acceptedFiles
  uploadResult.value = null

  if (rawFiles.length && acceptedFiles.length !== rawFiles.length) {
    error.value = '.xlsx 또는 .xlsm 파일만 업로드할 수 있습니다.'
  } else {
    error.value = ''
  }
}

const onFileChange = (event) => {
  setUploadFiles(event.target.files)
}

const onUploadDragEnter = () => {
  uploadDragDepth.value += 1
  isDraggingUpload.value = true
}

const onUploadDragOver = (event) => {
  if (event.dataTransfer) {
    event.dataTransfer.dropEffect = 'copy'
  }
  isDraggingUpload.value = true
}

const onUploadDragLeave = () => {
  uploadDragDepth.value = Math.max(0, uploadDragDepth.value - 1)
  if (uploadDragDepth.value === 0) {
    isDraggingUpload.value = false
  }
}

const onUploadDrop = (event) => {
  uploadDragDepth.value = 0
  isDraggingUpload.value = false
  setUploadFiles(event.dataTransfer?.files)
}

const submitUpload = async () => {
  if (!selectedFiles.value.length) return
  uploading.value = true
  error.value = ''
  try {
    const response = await uploadOneFiles(selectedFiles.value, apiParams.value)
    uploadResult.value = response.data
    selectedFiles.value = []
    if (fileInput.value) fileInput.value.value = ''
    resetLoadedData()
    await reloadAll({ force: true })
  } catch (err) {
    error.value = err.response?.data?.detail || 'ONE 파일 업로드에 실패했습니다.'
  } finally {
    uploading.value = false
  }
}

const deleteUpload = async (upload) => {
  if (!upload?.id || deletingUploadId.value) return
  const confirmed = window.confirm(`"${upload.original_filename}" 업로드 이력을 삭제할까요?\n해당 파일로 생성된 주문 데이터와 자동 생수 항목도 함께 다시 계산됩니다.`)
  if (!confirmed) return
  deletingUploadId.value = upload.id
  error.value = ''
  try {
    await deleteOneUpload(upload.id, apiParams.value)
    uploadResult.value = null
    if (statement.value && selectedDriverId.value) {
      statement.value = null
    }
    resetLoadedData()
    await reloadAll({ force: true })
  } catch (err) {
    error.value = err.response?.data?.detail || 'ONE 업로드 이력 삭제에 실패했습니다.'
  } finally {
    deletingUploadId.value = ''
  }
}

const loadUploads = async (force = false) => {
  if (loaded.value.uploads && !force) return
  const response = await fetchOneUploads(monthParams.value)
  uploads.value = response.data || []
  loaded.value.uploads = true
}

const loadDrivers = async (force = false) => {
  if (loaded.value.drivers && !force) return
  const response = await fetchOneDrivers(monthParams.value)
  drivers.value = response.data || []
  loaded.value.drivers = true
}

const loadSummaryAndDrivers = async (force = false) => {
  if (loaded.value.summary && loaded.value.drivers && !force) return
  const [summaryResp, driverResp] = await Promise.all([
    fetchOneSummary(monthParams.value),
    fetchOneDrivers(monthParams.value),
  ])
  summary.value = summaryResp.data || { summary: {}, by_service: [], by_day: [] }
  drivers.value = driverResp.data || []
  loaded.value.summary = true
  loaded.value.drivers = true
}

const reloadAll = async ({ force = false } = {}) => {
  loading.value = true
  error.value = ''
  try {
    if (activeTab.value === 'upload') {
      await loadUploads(force)
    } else if (activeTab.value === 'summary') {
      await loadSummaryAndDrivers(force)
    } else if (activeTab.value === 'drivers') {
      await loadDrivers(force)
    } else if (activeTab.value === 'collection') {
      await loadCollection(collection.value.page || 1)
    } else {
      await loadDrivers(force)
      if (selectedDriverId.value) await loadStatement(selectedDriverId.value)
    }
  } catch (err) {
    error.value = err.response?.data?.detail || 'ONE 정산 데이터를 불러오지 못했습니다.'
  } finally {
    loading.value = false
  }
}

const setActiveTab = async (tab) => {
  const next = normalizeTab(tab)
  activeTab.value = next
  if (route.query.one_tab !== next) {
    await router.replace({
      query: { ...route.query, one_tab: next },
    })
    return
  }
  await reloadAll()
}

const loadCollection = async (page = 1) => {
  collectionLoading.value = true
  error.value = ''
  try {
    const response = await fetchOneCollection({
      ...monthParams.value,
      page,
      page_size: collectionPageSize.value,
    })
    collection.value = response.data || { columns: [], rows: [], page, page_size: collectionPageSize.value, total: 0 }
  } catch (err) {
    error.value = err.response?.data?.detail || 'ONE 월별 취합 데이터를 불러오지 못했습니다.'
  } finally {
    collectionLoading.value = false
  }
}

const goCollectionPage = async (page) => {
  const next = Math.max(1, Math.min(collectionTotalPages.value, Number(page || 1)))
  await loadCollection(next)
}

const changeCollectionPageSize = async () => {
  await loadCollection(1)
}

const formatCollectionValue = (row, column) => {
  const value = row?.[column.key]
  if (value === null || value === undefined || value === '') return ''
  if (column.type === 'money') return formatNumber(value)
  return value
}

const downloadCollection = async () => {
  collectionDownloading.value = true
  error.value = ''
  try {
    const response = await downloadOneCollectionExcel(monthParams.value)
    saveBlob(response.data, `ONE_${selectedMonth.value}_취합B_기사.xlsx`)
  } catch (err) {
    error.value = err.response?.data?.detail || 'ONE 월별 취합 Excel 다운로드에 실패했습니다.'
  } finally {
    collectionDownloading.value = false
  }
}

const openStatement = async (driver) => {
  await setActiveTab('statements')
  selectedDriverId.value = driver.id
  await loadStatement(driver.id)
}

const loadStatement = async (driverId) => {
  if (!driverId) return
  const response = await fetchOneDriverStatement(driverId, monthParams.value)
  statement.value = response.data
}

const saveStatement = async (payload) => {
  if (!statement.value?.id) return
  savingStatement.value = true
  try {
    const response = await updateOneStatement(statement.value.id, payload, apiParams.value)
    statement.value = response.data
    resetLoadedData()
    await reloadAll({ force: true })
  } finally {
    savingStatement.value = false
  }
}

const saveBlob = (blob, filename) => {
  const url = window.URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  window.URL.revokeObjectURL(url)
}

const downloadStatement = async (type) => {
  if (!statement.value?.id) return
  const response = type === 'excel'
    ? await downloadOneStatementExcel(statement.value.id, apiParams.value)
    : await downloadOneStatementPdf(statement.value.id, apiParams.value)
  const ext = type === 'excel' ? 'xlsx' : 'pdf'
  saveBlob(response.data, `ONE_${statement.value.month}_${statement.value.driver.name}.${ext}`)
}

watch(selectedMonth, () => {
  statement.value = null
  selectedDriverId.value = ''
  resetLoadedData()
  void reloadAll({ force: true })
})

watch(
  () => route.query.one_tab,
  (tab) => {
    activeTab.value = normalizeTab(tab)
    void reloadAll()
  },
  { immediate: true },
)

const MetricCard = defineComponent({
  props: { label: String, value: [String, Number] },
  setup(props) {
    return () => h('div', { class: 'rounded-xl border border-slate-200 bg-white p-4' }, [
      h('p', { class: 'text-sm font-bold text-slate-500' }, props.label),
      h('p', { class: 'mt-2 text-2xl font-extrabold text-slate-900' }, props.value || '-'),
    ])
  },
})

const DataTable = defineComponent({
  props: { title: String },
  setup(props, { slots }) {
    return () => h('div', { class: 'overflow-hidden rounded-xl border border-slate-200 bg-white' }, [
      h('div', { class: 'border-b border-slate-200 bg-slate-50 px-4 py-3 font-extrabold text-slate-900' }, props.title),
      h('div', { class: 'overflow-x-auto' }, [
        h('table', { class: 'one-table min-w-full' }, slots.default?.()),
      ]),
    ])
  },
})

const UploadTable = defineComponent({
  props: {
    uploads: { type: Array, default: () => [] },
    deletingId: { type: [String, Number], default: '' },
  },
  emits: ['delete'],
  setup(props, { emit }) {
    return () => h(DataTable, { title: '업로드 이력' }, {
      default: () => [
        h('thead', [
          h('tr', [
            h('th', '파일명'),
            h('th', '배송일'),
            h('th', '상태'),
            h('th', { class: 'text-right' }, '주문그룹'),
            h('th', { class: 'text-right' }, '미매핑'),
            h('th', { class: 'text-right' }, '금액'),
            h('th', { class: 'one-upload-action-cell text-right' }, '관리'),
          ]),
        ]),
        h('tbody', props.uploads.map((upload) => h('tr', { key: upload.id }, [
          h('td', { class: 'max-w-[220px] truncate font-semibold' }, upload.original_filename),
          h('td', upload.delivery_date || '-'),
          h('td', [
            h('span', {
              class: [
                'rounded-full px-2 py-0.5 text-xs font-bold',
                upload.status === 'IMPORTED' ? 'bg-green-50 text-green-700' : 'bg-amber-50 text-amber-700',
              ],
            }, upload.status === 'IMPORTED' ? '완료' : '검토 필요'),
          ]),
          h('td', { class: 'text-right' }, formatNumber(upload.order_count)),
          h('td', { class: 'text-right' }, formatNumber(upload.unmapped_order_count)),
          h('td', { class: 'text-right font-bold' }, formatWon(upload.total_amount)),
          h('td', { class: 'one-upload-action-cell text-right' }, [
            h('button', {
              type: 'button',
              class: 'rounded-lg border border-red-200 bg-white px-3 py-1 text-xs font-extrabold text-red-600 hover:bg-red-50 disabled:cursor-not-allowed disabled:opacity-50',
              disabled: String(props.deletingId || '') === String(upload.id),
              onClick: () => emit('delete', upload),
            }, String(props.deletingId || '') === String(upload.id) ? '삭제 중' : '삭제'),
          ]),
        ]))),
      ],
    })
  },
})
</script>

<style scoped>
.one-table th {
  white-space: nowrap;
  padding: 10px 12px;
  border-bottom: 1px solid #e5e7eb;
  border-right: 1px solid #e8edf3;
  background: #f8fafc;
  color: #475569;
  font-weight: 800;
  text-align: left;
}

.one-table td {
  white-space: nowrap;
  padding: 10px 12px;
  border-bottom: 1px solid #f1f5f9;
  border-right: 1px solid #eef2f7;
  color: #334155;
}

.one-table th:last-child,
.one-table td:last-child {
  border-right: 0;
}

.one-upload-action-cell {
  position: sticky;
  right: 0;
  z-index: 2;
  min-width: 88px;
  width: 88px;
  box-shadow: -10px 0 14px -14px rgba(15, 23, 42, 0.35);
}

.one-table th.one-upload-action-cell {
  z-index: 3;
  background: #f8fafc;
}

.one-table td.one-upload-action-cell {
  background: #fff;
}

.one-table tr:hover td.one-upload-action-cell {
  background: #f8fafc;
}
</style>

