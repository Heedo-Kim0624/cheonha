<template>
  <AppLayout>
    <div class="space-y-6">
      <!-- 스텝 진행바 -->
      <div class="bg-white rounded-xl p-5 border border-gray-200">
        <div class="flex items-center justify-between">
          <div v-for="(step, idx) in stepLabels" :key="idx"
            class="flex items-center" :class="idx < stepLabels.length - 1 ? 'flex-1' : ''">
            <div class="flex items-center gap-3 cursor-pointer" @click="goToStep(idx)">
              <div class="w-10 h-10 rounded-full flex items-center justify-center font-bold transition-all"
                :class="idx < currentStep ? 'bg-success text-white'
                  : idx === currentStep ? 'bg-primary text-white'
                  : 'bg-gray-200 text-gray-500'">
                <span v-if="idx < currentStep">&#10003;</span>
                <span v-else>{{ idx + 1 }}</span>
              </div>
              <span class="font-medium whitespace-nowrap"
                :class="idx <= currentStep ? 'text-text' : 'text-gray-400'">
                {{ step }}
              </span>
            </div>
            <div v-if="idx < stepLabels.length - 1"
              class="flex-1 h-0.5 mx-4 rounded"
              :class="idx < currentStep ? 'bg-success' : 'bg-gray-200'"></div>
          </div>
        </div>
      </div>

      <!-- ============ STEP 0: 파일 업로드 ============ -->
      <div v-if="currentStep === 0" class="bg-white rounded-xl p-8 border border-gray-200">
        <h3 class="text-xl font-bold text-text mb-2">배차 파일 업로드</h3>
        <p class="text-gray-500 mb-6">배차현황 엑셀 파일을 업로드하면 자동으로 팀과 배송원 정보를 분석합니다.</p>

        <div @dragover.prevent="isDragging = true" @dragleave="isDragging = false" @drop.prevent="handleDrop"
          class="border-2 border-dashed rounded-xl p-16 text-center transition-all cursor-pointer"
          :class="isDragging ? 'border-primary bg-primary-light' : 'border-gray-300 hover:border-primary'"
          @click="$refs.fileInput.click()">
          <input ref="fileInput" type="file" accept=".xlsx,.xls" class="hidden" @change="handleFileSelect" />
          <div class="text-5xl mb-4 text-gray-400">&#128194;</div>
          <p class="text-lg font-medium text-text mb-1">파일을 여기에 끌어다 놓거나 클릭하세요</p>
          <p class="text-gray-400">.xlsx 파일</p>
        </div>

        <div v-if="isUploading" class="mt-6 flex items-center gap-3 text-primary">
          <div class="animate-spin w-5 h-5 border-2 border-primary border-t-transparent rounded-full"></div>
          <span class="font-medium">파일 분석 중...</span>
        </div>
        <div v-if="uploadError" class="mt-4 p-4 bg-red-50 border border-red-200 text-danger rounded-lg">{{ uploadError }}</div>

        <!-- 업로드 이력 -->
        <div v-if="uploadHistory.length > 0" class="mt-8">
          <h4 class="font-bold text-text mb-3">최근 업로드</h4>
          <div class="space-y-2">
            <div v-for="upload in uploadHistory.slice(0, 10)" :key="upload.id"
              class="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
              <div>
                <span class="font-medium text-text">{{ upload.original_filename || '배차파일' }}</span>
                <span v-if="upload.dispatch_date" class="text-blue-600 ml-3">{{ upload.dispatch_date }}</span>
                <span class="text-gray-400 ml-3">{{ upload.total_rows }}행</span>
              </div>
              <div class="flex items-center gap-2">
                <span class="px-2 py-0.5 rounded-full text-xs font-medium"
                  :class="upload.status === 'CONFIRMED' ? 'bg-green-100 text-green-700' : 'bg-blue-100 text-blue-700'">
                  {{ upload.status === 'CONFIRMED' ? '정산완료' : '대기중' }}
                </span>
                <button @click="deleteUpload(upload)"
                  class="px-3 py-1 bg-red-500 text-white rounded-lg text-xs font-medium hover:opacity-90">
                  삭제
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- ============ STEP 1: 데이터 확인 + 팀 단가 + 배송원 등록 ============ -->
      <div v-if="currentStep === 1" class="space-y-5">
        <!-- 업로드 요약 -->
        <div class="bg-white rounded-xl p-5 border border-gray-200">
          <div class="flex items-center justify-between mb-4">
            <h3 class="text-xl font-bold text-text">배차 데이터 확인</h3>
            <div class="flex gap-3">
              <span v-if="dispatchDate" class="px-3 py-1 bg-blue-50 text-blue-700 rounded-full font-medium">{{ dispatchDate }}</span>
              <span class="px-3 py-1 bg-gray-100 text-gray-700 rounded-full">{{ validRecordCount }}건</span>
            </div>
          </div>
          <div class="overflow-x-auto max-h-80 overflow-y-auto">
            <table class="w-full">
              <thead class="bg-gray-50 border-b border-gray-200 sticky top-0">
                <tr>
                  <th class="text-left px-4 py-3 font-semibold text-gray-600">담당자</th>
                  <th class="text-left px-4 py-3 font-semibold text-gray-600">권역</th>
                  <th class="text-right px-4 py-3 font-semibold text-gray-600">박스수</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="rec in visibleRecords" :key="rec.id" class="border-b border-gray-100 hover:bg-gray-50">
                  <td class="px-4 py-3 font-medium text-text">{{ rec.manager_name }}</td>
                  <td class="px-4 py-3">
                    <div class="flex flex-wrap gap-1">
                      <span v-for="r in rec.sub_region.split(',').map(s => s.trim()).filter(s => s && s !== '-')" :key="r"
                        class="px-2 py-0.5 bg-primary-light text-primary-dark rounded text-xs font-medium">{{ r }}</span>
                    </div>
                  </td>
                  <td class="px-4 py-3 text-right font-bold">{{ rec.boxes }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <!-- 팀 단가 설정 (관리자만) -->
        <div v-if="authStore.isAdmin" class="bg-white rounded-xl p-5 border border-gray-200">
          <h3 class="font-bold text-text mb-4">팀 단가 설정</h3>
          <div v-for="team in teamPricingList" :key="team.id"
            class="p-5 border border-gray-200 rounded-xl mb-3">
            <div class="flex items-center gap-3 mb-4">
              <div class="w-10 h-10 bg-primary-light rounded-full flex items-center justify-center">
                <span class="text-primary-dark font-bold">{{ team.code }}</span>
              </div>
              <span class="text-lg font-bold text-text">{{ team.name }}</span>
              <span v-if="team.has_price" class="px-2 py-0.5 bg-green-100 text-green-700 rounded text-xs">설정됨</span>
            </div>
            <div class="grid grid-cols-2 gap-4">
              <div>
                <label class="block text-sm text-gray-500 mb-1">수신단가 (박스당)</label>
                <input v-model.number="team._receive_price" type="number" placeholder="0"
                  class="w-full px-4 py-3 border border-blue-200 rounded-lg text-right text-lg bg-blue-50 focus:border-blue-400 outline-none" />
              </div>
              <div>
                <label class="block text-sm text-gray-500 mb-1">특근비용 (1인당)</label>
                <input v-model.number="team._overtime_cost" type="number" placeholder="0"
                  class="w-full px-4 py-3 border border-amber-200 rounded-lg text-right text-lg bg-amber-50 focus:border-amber-400 outline-none" />
              </div>
            </div>
          </div>
        </div>

        <!-- 배송원 확인 -->
        <div v-if="newCrewList.length > 0" class="bg-white rounded-xl p-5 border border-gray-200">
          <h3 class="font-bold text-text mb-1">신규 배송원 확인</h3>
          <p class="text-gray-500 mb-4">
            처음 보는 이름입니다. 용차이면 체크하세요. <span class="text-warning font-medium">용차는 정산에서 제외됩니다.</span>
          </p>

          <table class="w-full">
            <thead class="bg-gray-50 border-b border-gray-200">
              <tr>
                <th class="text-left px-4 py-3 font-semibold text-gray-600">이름</th>
                <th class="text-right px-4 py-3 font-semibold text-orange-600">지급단가 (박스당)</th>
                <th class="text-center px-4 py-3 font-semibold text-gray-600">용차 여부</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="crew in newCrewList" :key="crew.code" class="border-b border-gray-100">
                <td class="px-4 py-3 font-bold text-text">{{ crew.code }}</td>
                <td class="px-4 py-3 text-right">
                  <input v-if="!crew._isYongcha" v-model.number="crew._pay_price" type="number" placeholder="0" min="0"
                    class="w-32 px-3 py-2 border border-orange-300 rounded-lg text-right bg-orange-50 focus:border-orange-400 outline-none" />
                  <span v-else class="text-gray-300">-</span>
                </td>
                <td class="px-4 py-3 text-center">
                  <label class="inline-flex items-center gap-2 cursor-pointer">
                    <input type="checkbox" v-model="crew._isYongcha" class="w-5 h-5 rounded" />
                    <span :class="crew._isYongcha ? 'text-red-600 font-medium' : 'text-gray-400'">
                      {{ crew._isYongcha ? '용차' : '자사' }}
                    </span>
                  </label>
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <div v-if="existingCrewMembers.length > 0" class="bg-white rounded-xl p-5 border border-green-200">
          <h4 class="font-semibold text-success mb-2">기존 배송원 ({{ existingCrewMembers.length }}명)</h4>
          <div class="flex flex-wrap gap-2">
            <span v-for="c in existingCrewMembers" :key="c.code"
              class="px-3 py-1 bg-green-50 text-green-700 rounded-full font-medium">{{ c.code }}</span>
          </div>
        </div>
      </div>

      <!-- ============ STEP 2: 특근 설정 ============ -->
      <div v-if="currentStep === 2" class="space-y-5">
        <div class="bg-white rounded-xl p-5 border border-gray-200">
          <h3 class="text-xl font-bold text-text mb-1">특근 설정</h3>
          <p class="text-gray-500 mb-4">특근 대상 배송원을 선택하고 금액을 입력하세요.</p>

          <div v-if="dispatchDate" class="mb-4 px-4 py-2 bg-blue-50 rounded-lg text-blue-700 font-medium">
            배차일: {{ dispatchDate }}
          </div>

          <table class="w-full">
            <thead class="bg-gray-50 border-b border-gray-200">
              <tr>
                <th class="text-left px-4 py-3 font-semibold text-gray-600">배송원</th>
                <th class="text-left px-4 py-3 font-semibold text-gray-600">담당 권역</th>
                <th class="text-right px-4 py-3 font-semibold text-gray-600">박스수</th>
                <th class="text-center px-4 py-3 font-semibold text-gray-600">특근</th>
                <th class="text-right px-4 py-3 font-semibold text-gray-600">특근 금액(원)</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="person in crewOvertimeList" :key="person.name"
                class="border-b border-gray-100 hover:bg-gray-50">
                <td class="px-4 py-3 font-medium text-text">{{ person.name }}</td>
                <td class="px-4 py-3">
                  <div class="flex flex-wrap gap-1">
                    <span v-for="r in person.regions" :key="r"
                      class="px-2 py-0.5 bg-primary-light text-primary-dark rounded text-xs font-medium">{{ r }}</span>
                  </div>
                </td>
                <td class="px-4 py-3 text-right font-bold">{{ person.totalBoxes }}</td>
                <td class="px-4 py-3 text-center">
                  <input type="checkbox" v-model="person.isOvertime" class="w-5 h-5 rounded" />
                </td>
                <td class="px-4 py-3 text-right">
                  <input v-if="person.isOvertime" v-model.number="person.overtimeCost"
                    type="number" min="0" placeholder="0"
                    class="w-32 px-3 py-2 border border-orange-300 rounded-lg text-right bg-orange-50 focus:border-orange-400 outline-none" />
                  <span v-else class="text-gray-300">-</span>
                </td>
              </tr>
            </tbody>
          </table>
          <div class="mt-3 flex justify-between text-gray-500">
            <span>{{ crewOvertimeList.length }}명</span>
            <span>특근 {{ crewOvertimeList.filter(c => c.isOvertime).length }}명</span>
          </div>
        </div>
      </div>

      <!-- ============ STEP 3: 정산 확정 ============ -->
      <div v-if="currentStep === 3" class="space-y-5">
        <div v-if="!settlementResult" class="bg-white rounded-xl p-6 border border-gray-200">
          <h3 class="text-xl font-bold text-text mb-6">정산 확인</h3>
          <div class="grid grid-cols-4 gap-4 mb-6">
            <div class="p-5 bg-gray-50 rounded-xl text-center">
              <p class="text-sm text-gray-500 mb-1">등록 배송원</p>
              <p class="text-2xl font-bold text-text">{{ registeredCount }}명</p>
            </div>
            <div class="p-5 bg-gray-50 rounded-xl text-center">
              <p class="text-sm text-gray-500 mb-1">배차 건수</p>
              <p class="text-2xl font-bold text-text">{{ validRecordCount }}건</p>
            </div>
            <div class="p-5 bg-gray-50 rounded-xl text-center">
              <p class="text-sm text-gray-500 mb-1">특근</p>
              <p class="text-2xl font-bold text-warning">{{ crewOvertimeList.filter(c => c.isOvertime).length }}명</p>
            </div>
            <div class="p-5 bg-gray-50 rounded-xl text-center">
              <p class="text-sm text-gray-500 mb-1">배차일</p>
              <p class="text-2xl font-bold text-blue-700">{{ dispatchDate || '-' }}</p>
            </div>
          </div>
        </div>

        <!-- 정산 결과 -->
        <div v-if="settlementResult" class="space-y-5">
          <div class="bg-white rounded-xl p-8 border border-green-200 text-center">
            <div class="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center text-success text-3xl mx-auto mb-4">&#10003;</div>
            <p class="font-bold text-2xl text-text mb-2">정산이 생성되었습니다</p>
            <p class="text-gray-500">
              {{ settlementResult.settlement.period_start }} | {{ settlementResult.settlement.team }} |
              {{ settlementResult.crew_details?.length || 0 }}명 배송원
            </p>
            <div v-if="settlementResult.skipped_crew?.length > 0"
              class="mt-4 p-3 bg-amber-50 border border-amber-200 rounded-lg text-amber-700 text-left">
              미등록 제외: {{ settlementResult.skipped_crew.join(', ') }}
            </div>
          </div>

          <button @click="resetUpload" class="px-6 py-3 bg-primary text-white rounded-lg font-medium hover:opacity-90">
            새로 업로드
          </button>
        </div>
      </div>

      <!-- 하단 버튼 -->
      <div v-if="currentStep > 0 && !settlementResult"
        class="flex justify-between bg-white rounded-xl p-5 border border-gray-200">
        <button @click="currentStep--"
          class="px-5 py-3 border border-gray-300 rounded-lg text-text hover:bg-gray-50 font-medium">이전</button>
        <div class="flex gap-3">
          <button v-if="currentStep < 3" @click="handleNextStep" :disabled="isProcessing"
            class="px-8 py-3 bg-primary text-white rounded-lg font-medium hover:opacity-90 disabled:opacity-50">
            {{ isProcessing ? '처리 중...' : '다음' }}
          </button>
          <button v-if="currentStep === 3" @click="handleFinalize" :disabled="isProcessing"
            class="px-8 py-3 bg-success text-white rounded-lg font-medium hover:opacity-90 disabled:opacity-50">
            {{ isProcessing ? '정산 생성 중...' : '정산 생성' }}
          </button>
        </div>
      </div>

      <div v-if="processError" class="p-4 bg-red-50 border border-red-200 text-danger rounded-xl">{{ processError }}</div>
    </div>
  </AppLayout>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { formatDateTime, formatCurrency } from '@/utils/format'
import AppLayout from '@/components/common/AppLayout.vue'
import { useAuthStore } from '@/stores/auth'
import client from '@/api/client'

const authStore = useAuthStore()
import {
  uploadDispatchFile, getDetectedInfo, configureAll,
  setOvertime, finalizeUpload, fetchUploads, getRecords
} from '@/api/dispatch'

const currentStep = ref(0)
const stepLabels = ['배차표 업로드', '데이터 확인·단가 설정', '특근 설정', '정산 확정']

const isDragging = ref(false)
const isUploading = ref(false)
const isProcessing = ref(false)
const uploadError = ref('')
const processError = ref('')
const uploadId = ref(null)

const detectedInfo = ref(null)
const uploadRecords = ref([])
const uploadHistory = ref([])
const newCrewList = ref([])
const dispatchDate = ref(null)
const teamPricingList = ref([])
const crewOvertimeList = ref([])

const settlementResult = ref(null)
const expandedCrewCode = ref(null)

const existingCrewMembers = computed(() => {
  if (!detectedInfo.value) return []
  return detectedInfo.value.crew_members.filter(c => !c.is_new)
})

const visibleRecords = computed(() => {
  return uploadRecords.value.filter(r => r.manager_name && r.boxes > 0)
})

const validRecordCount = computed(() => visibleRecords.value.length)

const registeredCount = computed(() => {
  if (crewOvertimeList.value.length > 0) return crewOvertimeList.value.length
  return existingCrewMembers.value.length + newCrewList.value.filter(c => c._register).length
})

// Methods
const goToStep = (idx) => { if (idx < currentStep.value) currentStep.value = idx }

const handleDrop = (e) => { isDragging.value = false; const f = e.dataTransfer.files; if (f.length) processFile(f[0]) }
const handleFileSelect = (e) => { const f = e.target.files; if (f.length) processFile(f[0]) }

const processFile = async (file) => {
  if (!file.name.match(/\.xlsx?$/i)) { uploadError.value = '.xlsx 파일만 업로드 가능합니다.'; return }

  // 파일명에서 날짜 추출해서 같은 날짜 이력 확인
  const dateMatch = file.name.match(/(\d{4})-(\d{2})-(\d{2})/)
  if (dateMatch) {
    const fileDate = `${dateMatch[1]}-${dateMatch[2]}-${dateMatch[3]}`
    try {
      const checkResp = await client.get('/dispatch/uploads/check_date/', { params: { date: fileDate } })
      const existing = checkResp.data || []
      if (existing.length > 0) {
        const times = existing.map(e => {
          const d = new Date(e.upload_date)
          return `${d.getHours()}시 ${d.getMinutes()}분 ${d.getSeconds()}초`
        }).join(', ')
        if (!confirm(`${fileDate}에 배차표를 올린 이력이 있습니다.\n(${times})\n\n추가로 올리시겠습니까? 정산이 합산됩니다.`)) {
          return
        }
      }
    } catch (e) { /* 체크 실패시 그냥 진행 */ }
  }

  isUploading.value = true
  uploadError.value = ''

  try {
    const resp = await uploadDispatchFile(file)
    const data = resp.data
    uploadId.value = data.id
    detectedInfo.value = data.detected_info
    dispatchDate.value = data.dispatch_date || null

    // 팀 단가 리스트
    teamPricingList.value = (data.detected_info.teams || []).map(t => ({
      ...t,
      _receive_price: t.receive_price || 0,
      _pay_price: t.pay_price || 0,
      _overtime_cost: t.default_overtime_cost || 0,
    }))

    newCrewList.value = (data.detected_info.crew_members || [])
      .filter(c => c.is_new)
      .map(c => ({ ...c, _isYongcha: false, _pay_price: 0 }))

    // create 응답에 records 포함, 없으면 별도 조회
    if (data.records && data.records.length > 0) {
      uploadRecords.value = data.records
    } else {
      const recResp = await getRecords(data.id)
      uploadRecords.value = recResp.data.results || recResp.data || []
    }

    currentStep.value = 1
  } catch (e) {
    uploadError.value = e.response?.data?.detail || '업로드 실패'
  } finally {
    isUploading.value = false
  }
}

const buildCrewOvertimeList = () => {
  const registeredCodes = new Set()
  if (detectedInfo.value) {
    for (const c of detectedInfo.value.crew_members || []) {
      if (!c.is_new) registeredCodes.add(c.code)
    }
  }

  // 팀 기본 특근비
  const defaultOT = teamPricingList.value.length > 0 ? (teamPricingList.value[0]._overtime_cost || 0) : 0

  const crewMap = {}
  for (const rec of uploadRecords.value) {
    if (!rec.manager_name || !rec.sub_region) continue
    if (!registeredCodes.has(rec.manager_name)) continue
    if (!crewMap[rec.manager_name]) {
      crewMap[rec.manager_name] = { name: rec.manager_name, regions: new Set(), totalBoxes: 0, isOvertime: false, overtimeCost: defaultOT }
    }
    for (const r of rec.sub_region.split(',').map(s => s.trim()).filter(s => s && s !== '-')) {
      crewMap[rec.manager_name].regions.add(r)
    }
    crewMap[rec.manager_name].totalBoxes += rec.boxes || 0
  }

  crewOvertimeList.value = Object.values(crewMap)
    .filter(c => c.totalBoxes > 0)
    .map(c => ({ ...c, regions: Array.from(c.regions) }))
}

const handleNextStep = async () => {
  isProcessing.value = true
  processError.value = ''
  try {
    if (currentStep.value === 1) {
      // 팀 단가 + 배송원 등록
      const teams = teamPricingList.value.map(t => ({
        id: t.id, receive_price: t._receive_price || 0, pay_price: t._pay_price || 0, default_overtime_cost: t._overtime_cost || 0
      }))
      // 용차가 아닌 신규 배송원만 등록 + 지급단가
      const crew = newCrewList.value.filter(c => !c._isYongcha).map(c => ({
        code: c.code, name: c.name || c.code, phone: '', vehicle_number: '',
        pay_price: c._pay_price || 0
      }))

      await client.post(`/dispatch/uploads/${uploadId.value}/configure/`, { teams, crew })

      const infoResp = await getDetectedInfo(uploadId.value)
      detectedInfo.value = infoResp.data
      buildCrewOvertimeList()
      currentStep.value = 2
    } else if (currentStep.value === 2) {
      const crewData = crewOvertimeList.value.map(c => ({
        name: c.name, is_overtime: c.isOvertime, overtime_cost: c.isOvertime ? (c.overtimeCost || 0) : 0
      }))
      await setOvertime(uploadId.value, crewData)
      currentStep.value = 3
    }
  } catch (e) {
    processError.value = e.response?.data?.detail || '처리 오류'
  } finally {
    isProcessing.value = false
  }
}

const handleFinalize = async () => {
  isProcessing.value = true
  processError.value = ''
  try {
    const resp = await finalizeUpload(uploadId.value, {})
    settlementResult.value = resp.data
  } catch (e) {
    processError.value = e.response?.data?.detail || '정산 생성 실패'
  } finally {
    isProcessing.value = false
  }
}

const resetUpload = () => {
  currentStep.value = 0; uploadId.value = null; detectedInfo.value = null
  uploadRecords.value = []; newCrewList.value = []; dispatchDate.value = null
  teamPricingList.value = []; crewOvertimeList.value = []
  settlementResult.value = null; uploadError.value = ''; processError.value = ''
  expandedCrewCode.value = null; loadHistory()
}

const deleteUpload = async (upload) => {
  const name = upload.original_filename || '배차파일'
  if (!confirm(`"${name}" 업로드를 삭제하시겠습니까?\n연관된 정산 데이터도 함께 삭제됩니다.`)) return
  try {
    await client.delete(`/dispatch/uploads/${upload.id}`)
    loadHistory()
  } catch (e) {
    alert(e.response?.data?.detail || '삭제 실패')
  }
}

const loadHistory = async () => {
  try { const r = await fetchUploads(); uploadHistory.value = r.data.results || r.data || [] } catch (e) {}
}

onMounted(loadHistory)
</script>
