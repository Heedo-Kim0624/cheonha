<template>
  <section class="space-y-5">
    <div class="rounded-xl border border-slate-200 bg-white p-5">
      <div class="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h3 class="text-lg font-bold text-slate-900">회사 관리</h3>
          <p class="mt-1 text-sm text-slate-500">
            새 회사 초대 링크를 만들고, 신청 승인/거절과 탭 노출을 관리합니다.
          </p>
        </div>
        <button type="button" class="primary-btn" :disabled="saving" @click="createCompany">
          새 회사 추가
        </button>
      </div>

      <div class="mt-5 grid gap-4 md:grid-cols-3">
        <label>
          <span class="mb-2 block text-sm font-semibold text-slate-700">회사 코드</span>
          <input v-model.trim="form.code" class="form-input" placeholder="예: newco" />
        </label>
        <label class="md:col-span-2">
          <span class="mb-2 block text-sm font-semibold text-slate-700">초대 회사명</span>
          <input v-model.trim="form.name" class="form-input" placeholder="회사명" />
        </label>
      </div>

      <div class="mt-4">
        <p class="mb-2 text-sm font-bold text-slate-700">사용 화주사</p>
        <div class="grid gap-2 md:grid-cols-3">
          <label v-for="shipper in shippers" :key="shipper.code" class="flex cursor-pointer items-center justify-between gap-3 rounded-lg border border-slate-200 p-3">
            <span class="text-sm font-semibold text-slate-700">{{ shipper.name }}</span>
            <input type="checkbox" :checked="form.enabled_shippers.includes(shipper.code)" @change="toggleFormShipper(shipper.code)" />
          </label>
        </div>
      </div>

      <div v-if="notice" class="mt-4 rounded-lg p-3 text-sm" :class="notice.type === 'success' ? 'bg-emerald-50 text-emerald-700' : 'bg-red-50 text-red-700'">
        {{ notice.message }}
      </div>
    </div>

    <div class="rounded-xl border border-slate-200 bg-white p-5">
      <div class="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h3 class="text-lg font-bold text-slate-900">화주사 관리</h3>
          <p class="mt-1 text-sm text-slate-500">
            회사에 배정할 화주사를 추가하고 업로드 방식을 관리합니다.
          </p>
        </div>
        <button type="button" class="primary-btn" :disabled="savingShipper" @click="createShipperProfile">
          화주사 추가
        </button>
      </div>

      <div class="mt-5 grid gap-4 md:grid-cols-4">
        <label>
          <span class="mb-2 block text-sm font-semibold text-slate-700">화주 코드</span>
          <input v-model.trim="shipperForm.code" class="form-input" placeholder="예: coupang" />
        </label>
        <label class="md:col-span-2">
          <span class="mb-2 block text-sm font-semibold text-slate-700">화주사명</span>
          <input v-model.trim="shipperForm.name" class="form-input" placeholder="예: 쿠팡" />
        </label>
        <label>
          <span class="mb-2 block text-sm font-semibold text-slate-700">업로드 방식</span>
          <select v-model="shipperForm.upload_type" class="form-input">
            <option v-for="option in uploadTypeOptions" :key="option.value" :value="option.value">
              {{ option.label }}
            </option>
          </select>
        </label>
      </div>

      <div class="mt-5 overflow-x-auto rounded-lg border border-slate-200">
        <table class="min-w-[640px] divide-y divide-slate-200 text-sm">
          <thead class="bg-slate-50 text-left text-xs font-bold text-slate-500">
            <tr>
              <th class="w-[110px] px-4 py-3">코드</th>
              <th class="w-[180px] px-4 py-3">화주사명</th>
              <th class="w-[190px] px-4 py-3">업로드 방식</th>
              <th class="w-[150px] px-4 py-3 text-right">관리</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-100 bg-white">
            <tr v-for="shipper in shippers" :key="shipper.code" class="align-middle">
              <td class="px-4 py-4">
                <div class="font-mono text-sm font-bold text-slate-800">{{ shipper.code }}</div>
              </td>
              <td class="px-4 py-4">
                <input v-model.trim="shipper.edit_name" class="form-input" />
              </td>
              <td class="px-4 py-4">
                <div>
                  <label>
                    <span class="mb-1 block text-[11px] font-bold text-slate-500">업로드 방식</span>
                    <select v-model="shipper.edit_upload_type" class="form-input form-input-compact">
                      <option v-for="option in uploadTypeOptions" :key="option.value" :value="option.value">
                        {{ option.label }}
                      </option>
                    </select>
                  </label>
                </div>
              </td>
              <td class="px-4 py-4 text-right">
                <div class="flex justify-end gap-2">
                  <button type="button" class="secondary-btn shipper-action-btn" :disabled="savingShipper || !shipper.id" @click="saveShipperProfile(shipper)">
                    저장
                  </button>
                  <button
                    type="button"
                    class="secondary-btn danger shipper-action-btn"
                    :disabled="savingShipper || !shipper.id || shipper.code === 'kurly'"
                    @click="removeShipperProfile(shipper)"
                  >
                    삭제
                  </button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <p class="mt-2 text-xs text-slate-500">
        추가한 화주사는 아래 회사별 “사용 화주사” 체크 목록에 바로 표시됩니다.
      </p>
    </div>

    <div v-if="loading" class="empty-state">불러오는 중...</div>
    <div v-else-if="companies.length === 0" class="empty-state">등록된 회사가 없습니다.</div>
    <div v-else class="space-y-4">
      <article
        v-for="company in companies"
        :key="company.id"
        class="rounded-xl border border-slate-200 bg-white p-5"
        :class="{ 'opacity-70': company.status === 'DELETED' }"
      >
        <div class="flex flex-wrap items-start justify-between gap-4">
          <div>
            <div class="flex flex-wrap items-center gap-2">
              <h4 class="text-lg font-bold text-slate-900">{{ company.name }}</h4>
              <span class="rounded-full px-2 py-1 text-xs font-bold" :class="statusClass(company.status)">
                {{ statusLabel(company.status) }}
              </span>
              <span v-if="company.is_core_company" class="rounded-full bg-slate-100 px-2 py-1 text-xs font-bold text-slate-600">
                기본 회사
              </span>
            </div>
            <p class="mt-1 text-sm text-slate-500">코드: {{ company.code }}</p>
            <p v-if="company.representative_username" class="mt-1 text-sm text-slate-500">
              대표 계정: {{ company.representative_username }}
            </p>
            <p v-if="company.deleted_at" class="mt-1 text-sm text-red-600">
              삭제됨 · {{ formatDateTime(company.deleted_at) }} · 복구 가능 기한 {{ formatDateTime(company.delete_retention_until) }}
            </p>
          </div>

          <div class="flex flex-wrap gap-2">
            <button v-if="company.status === 'PENDING_APPROVAL'" type="button" class="primary-btn" @click="approve(company)">
              승인
            </button>
            <button v-if="company.status === 'PENDING_APPROVAL'" type="button" class="secondary-btn danger" @click="reject(company)">
              거절
            </button>
            <button v-if="company.status === 'DELETED'" type="button" class="secondary-btn" @click="restore(company)">
              복구
            </button>
            <button v-if="company.status === 'DELETED'" type="button" class="secondary-btn danger" @click="permanentlyRemove(company)">
              완전삭제
            </button>
            <button v-else type="button" class="secondary-btn" :disabled="company.is_core_company" @click="remove(company)">
              삭제
            </button>
          </div>
        </div>

        <div class="mt-4 rounded-lg border border-slate-200 bg-slate-50 p-3">
          <div class="flex flex-wrap items-center justify-between gap-3">
            <div class="min-w-0">
              <p class="text-xs font-bold text-slate-500">대표 회원가입 링크</p>
              <p class="truncate text-sm font-semibold text-slate-800">{{ company.signup_url }}</p>
            </div>
            <div class="flex gap-2">
              <button type="button" class="secondary-btn" @click="copySignupUrl(company)">복사</button>
              <button type="button" class="secondary-btn" @click="rotateToken(company)">링크 재발급</button>
            </div>
          </div>
        </div>

        <div class="mt-4">
          <p class="mb-2 text-sm font-bold text-slate-700">사용 화주사 및 탭 구성</p>
          <div class="grid gap-3 lg:grid-cols-2">
            <div
              v-for="shipper in shippers"
              :key="`${company.id}-${shipper.code}`"
              class="rounded-lg border border-slate-200 p-3"
              :class="isShipperEnabled(company, shipper.code) ? 'bg-white' : 'bg-slate-50'"
            >
              <label class="flex cursor-pointer items-center justify-between gap-3">
                <span class="text-sm font-bold text-slate-800">{{ shipper.name }}</span>
                <input
                  type="checkbox"
                  :checked="isShipperEnabled(company, shipper.code)"
                  :disabled="company.status === 'DELETED'"
                  @change="toggleShipper(company, shipper.code)"
                />
              </label>
              <div v-if="isShipperEnabled(company, shipper.code)" class="mt-3 border-t border-slate-100 pt-3">
                <p class="mb-2 text-xs font-bold text-slate-500">탭 구성</p>
                <div class="grid gap-2 sm:grid-cols-2">
                  <label
                    v-for="tab in shipperTabOptions(shipper)"
                    :key="`${company.id}-${shipper.code}-${tab.key}`"
                    class="flex cursor-pointer items-center justify-between gap-3 rounded-md border border-slate-200 bg-slate-50 px-3 py-2"
                  >
                    <span class="text-xs font-semibold text-slate-700">{{ tab.label }}</span>
                    <input
                      type="checkbox"
                      :checked="isShipperTabEnabled(company, shipper.code, tab.key)"
                      :disabled="company.status === 'DELETED' || isLastEnabledShipperTab(company, shipper.code, tab.key)"
                      @change="toggleShipperTab(company, shipper.code, tab.key)"
                    />
                  </label>
                </div>
              </div>
            </div>
          </div>
          <p class="mt-2 text-xs text-slate-500">
            선택한 화주사별로 좌측 메뉴와 기본 진입 화면이 달라집니다. 오네는 외부 탭 기준으로 정산 처리만 사용합니다.
          </p>
        </div>
      </article>
    </div>
  </section>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import {
  COMPANY_TAB_OPTIONS,
  DEFAULT_COMPANY_TABS,
  approveCompanyApp,
  createCompanyApp,
  createShipper,
  deleteCompanyApp,
  deleteShipper,
  fetchCompanyApps,
  fetchShippers,
  permanentlyDeleteCompanyApp,
  rejectCompanyApp,
  restoreCompanyApp,
  rotateCompanySignupToken,
  updateCompanyApp,
  updateShipper,
} from '@/api/companyAdmin'
import { setRuntimeCompanyApps } from '@/utils/companyApp'

const emit = defineEmits(['updated'])
const loading = ref(false)
const saving = ref(false)
const savingShipper = ref(false)
const companies = ref([])
const shippers = ref([])
const notice = ref(null)
const shipperSpecificTabOptions = [
  { key: 'dispatch', label: '배차표 업로드' },
  { key: 'crew', label: '배송원 관리' },
  { key: 'region', label: '조관리' },
  ...COMPANY_TAB_OPTIONS,
]
const form = reactive({ code: '', name: '', enabled_shippers: ['kurly'], enabled_shipper_tabs: { kurly: [...DEFAULT_COMPANY_TABS] } })
const shipperForm = reactive({
  code: '',
  name: '',
  upload_type: 'FILE',
})
const uploadTypeOptions = [
  { value: 'FILE', label: '파일 업로드' },
  { value: 'TEXT', label: '텍스트 붙여넣기' },
]
function statusLabel(status) {
  return {
    INVITED: '초대 생성',
    PENDING_APPROVAL: '승인 대기',
    ACTIVE: '운영 중',
    REJECTED: '거절',
    DELETED: '삭제 보관',
  }[status] || status
}

function statusClass(status) {
  return {
    INVITED: 'bg-blue-50 text-blue-700',
    PENDING_APPROVAL: 'bg-amber-50 text-amber-700',
    ACTIVE: 'bg-emerald-50 text-emerald-700',
    REJECTED: 'bg-red-50 text-red-700',
    DELETED: 'bg-slate-100 text-slate-600',
  }[status] || 'bg-slate-100 text-slate-600'
}

function formatDateTime(value) {
  if (!value) return '-'
  return new Date(value).toLocaleString('ko-KR')
}

function normalizeEnabledShippers(company) {
  const enabled = company.enabled_shippers || ['kurly']
  return enabled.length ? enabled : ['kurly']
}

function isShipperEnabled(company, shipperCode) {
  return normalizeEnabledShippers(company).includes(shipperCode)
}

function shipperByCode(shipperCode) {
  return shippers.value.find((shipper) => shipper.code === shipperCode)
}

function availableTabsForShipper(shipper) {
  const available = Array.isArray(shipper?.available_tabs) && shipper.available_tabs.length
    ? shipper.available_tabs
    : shipperSpecificTabOptions.map((tab) => tab.key)
  return available
}

function defaultTabsForShipper(shipperCode) {
  const shipper = shipperByCode(shipperCode)
  const defaults = Array.isArray(shipper?.default_enabled_tabs) && shipper.default_enabled_tabs.length
    ? shipper.default_enabled_tabs
    : (shipperCode === 'one' ? ['settlement'] : DEFAULT_COMPANY_TABS)
  const available = new Set(availableTabsForShipper(shipper))
  return defaults.filter((tab) => available.has(tab))
}

function shipperTabOptions(shipper) {
  const available = new Set(availableTabsForShipper(shipper))
  return shipperSpecificTabOptions.filter((tab) => available.has(tab.key))
}

function normalizeCompanyShipperTabs(company) {
  const enabled = normalizeEnabledShippers(company)
  const raw = company.enabled_shipper_tabs || {}
  const next = {}
  for (const shipperCode of enabled) {
    const shipper = shipperByCode(shipperCode)
    const available = new Set(availableTabsForShipper(shipper))
    const configured = Array.isArray(raw[shipperCode]) && raw[shipperCode].length
      ? raw[shipperCode]
      : defaultTabsForShipper(shipperCode)
    const tabs = configured.filter((tab) => available.has(tab))
    next[shipperCode] = tabs.length ? tabs : defaultTabsForShipper(shipperCode)
  }
  return next
}

function unionShipperTabs(shipperTabs) {
  const tabs = []
  for (const tabList of Object.values(shipperTabs || {})) {
    for (const tab of tabList || []) {
      if (!tabs.includes(tab)) tabs.push(tab)
    }
  }
  return tabs
}

function isShipperTabEnabled(company, shipperCode, tab) {
  const tabs = normalizeCompanyShipperTabs(company)[shipperCode] || []
  return tabs.includes(tab)
}

function isLastEnabledShipperTab(company, shipperCode, tab) {
  const tabs = normalizeCompanyShipperTabs(company)[shipperCode] || []
  return tabs.includes(tab) && tabs.length <= 1
}

function normalizeShipperRow(shipper) {
  return {
    ...shipper,
    edit_name: shipper.name || '',
    edit_upload_type: shipper.upload_type || 'FILE',
  }
}

async function reload() {
  loading.value = true
  try {
    const [companyResponse, shipperResponse] = await Promise.all([fetchCompanyApps(), fetchShippers()])
    shippers.value = (shipperResponse.data.results || shipperResponse.data || []).map(normalizeShipperRow)
    if (shippers.value.length === 0) {
      shippers.value = [normalizeShipperRow({ code: 'kurly', name: '컬리', upload_type: 'FILE', status: 'ACTIVE', sort_order: 10 })]
    }
    companies.value = companyResponse.data.results || companyResponse.data || []
    setRuntimeCompanyApps(companies.value)
    emit('updated', companies.value)
  } catch (error) {
    notice.value = { type: 'error', message: error.response?.data?.detail || '회사 목록을 불러오지 못했습니다.' }
  } finally {
    loading.value = false
  }
}

async function createShipperProfile() {
  const code = String(shipperForm.code || '').trim().toLowerCase()
  const name = String(shipperForm.name || '').trim()
  if (!code || !name) {
    notice.value = { type: 'error', message: '화주 코드와 화주사명을 입력해 주세요.' }
    return
  }

  savingShipper.value = true
  notice.value = null
  try {
    await createShipper({
      code,
      name,
      upload_type: shipperForm.upload_type,
      status: 'ACTIVE',
    })
    shipperForm.code = ''
    shipperForm.name = ''
    shipperForm.upload_type = 'FILE'
    notice.value = { type: 'success', message: '화주사를 추가했습니다.' }
    await reload()
  } catch (error) {
    notice.value = {
      type: 'error',
      message: error.response?.data?.detail || error.response?.data?.code?.[0] || '화주사 추가에 실패했습니다.',
    }
  } finally {
    savingShipper.value = false
  }
}

async function saveShipperProfile(shipper) {
  if (!shipper?.id) return
  const name = String(shipper.edit_name || '').trim()
  if (!name) {
    notice.value = { type: 'error', message: '화주사명을 입력해 주세요.' }
    return
  }

  savingShipper.value = true
  notice.value = null
  try {
    await updateShipper(shipper.id, {
      name,
      upload_type: shipper.edit_upload_type || 'FILE',
      status: 'ACTIVE',
    })
    notice.value = { type: 'success', message: '화주사 설정을 저장했습니다.' }
    await reload()
  } catch (error) {
    notice.value = { type: 'error', message: error.response?.data?.detail || '화주사 설정 저장에 실패했습니다.' }
  } finally {
    savingShipper.value = false
  }
}

async function removeShipperProfile(shipper) {
  if (!shipper?.id) return
  if (shipper.code === 'kurly') {
    notice.value = { type: 'error', message: '기본 화주사 컬리는 삭제할 수 없습니다.' }
    return
  }
  const confirmed = window.confirm(
    `${shipper.name} 화주사를 삭제할까요?\n\n회사별 사용 화주사 목록에서도 함께 제거됩니다. 기존 업로드/정산 데이터의 화주 코드는 보존됩니다.`
  )
  if (!confirmed) return

  savingShipper.value = true
  notice.value = null
  try {
    await deleteShipper(shipper.id)
    form.enabled_shippers = form.enabled_shippers.filter((code) => code !== shipper.code)
    if (form.enabled_shippers.length === 0) form.enabled_shippers = ['kurly']
    notice.value = { type: 'success', message: '화주사를 삭제했습니다.' }
    await reload()
  } catch (error) {
    notice.value = { type: 'error', message: error.response?.data?.detail || '화주사 삭제에 실패했습니다.' }
  } finally {
    savingShipper.value = false
  }
}

async function createCompany() {
  if (!form.code || !form.name) {
    notice.value = { type: 'error', message: '회사 코드와 회사명을 입력해 주세요.' }
    return
  }
  saving.value = true
  notice.value = null
  try {
    await createCompanyApp({
      code: form.code,
      name: form.name,
      enabled_tabs: unionShipperTabs(form.enabled_shipper_tabs),
      enabled_shippers: form.enabled_shippers.length ? [...form.enabled_shippers] : ['kurly'],
      enabled_shipper_tabs: { ...form.enabled_shipper_tabs },
    })
    form.code = ''
    form.name = ''
    form.enabled_shippers = ['kurly']
    form.enabled_shipper_tabs = { kurly: [...DEFAULT_COMPANY_TABS] }
    notice.value = { type: 'success', message: '회사 초대 링크를 생성했습니다.' }
    await reload()
  } catch (error) {
    notice.value = { type: 'error', message: error.response?.data?.detail || error.response?.data?.code?.[0] || '회사 추가에 실패했습니다.' }
  } finally {
    saving.value = false
  }
}

async function saveCompany(company, payload) {
  try {
    await updateCompanyApp(company.id, payload)
    await reload()
  } catch (error) {
    notice.value = { type: 'error', message: error.response?.data?.detail || '회사 설정 저장에 실패했습니다.' }
  }
}

async function toggleShipper(company, shipperCode) {
  const enabled = normalizeEnabledShippers(company)
  let next = enabled.includes(shipperCode)
    ? enabled.filter((item) => item !== shipperCode)
    : [...enabled, shipperCode]
  if (next.length === 0) next = ['kurly']
  const nextMap = { ...normalizeCompanyShipperTabs(company) }
  if (next.includes(shipperCode)) {
    nextMap[shipperCode] = nextMap[shipperCode]?.length ? nextMap[shipperCode] : defaultTabsForShipper(shipperCode)
  } else {
    delete nextMap[shipperCode]
  }
  for (const code of Object.keys(nextMap)) {
    if (!next.includes(code)) delete nextMap[code]
  }
  await saveCompany(company, {
    enabled_shippers: next,
    enabled_shipper_tabs: nextMap,
    enabled_tabs: unionShipperTabs(nextMap),
  })
}

async function toggleShipperTab(company, shipperCode, tab) {
  const nextMap = { ...normalizeCompanyShipperTabs(company) }
  const tabs = nextMap[shipperCode] || defaultTabsForShipper(shipperCode)
  const nextTabs = tabs.includes(tab)
    ? tabs.filter((item) => item !== tab)
    : [...tabs, tab]
  if (nextTabs.length === 0) return
  nextMap[shipperCode] = nextTabs
  await saveCompany(company, {
    enabled_shipper_tabs: nextMap,
    enabled_tabs: unionShipperTabs(nextMap),
  })
}

function toggleFormShipper(shipperCode) {
  const enabled = form.enabled_shippers || []
  form.enabled_shippers = enabled.includes(shipperCode)
    ? enabled.filter((item) => item !== shipperCode)
    : [...enabled, shipperCode]
  if (form.enabled_shippers.length === 0) form.enabled_shippers = ['kurly']
  const nextMap = { ...form.enabled_shipper_tabs }
  if (form.enabled_shippers.includes(shipperCode)) {
    nextMap[shipperCode] = nextMap[shipperCode]?.length ? nextMap[shipperCode] : defaultTabsForShipper(shipperCode)
  } else {
    delete nextMap[shipperCode]
  }
  for (const code of Object.keys(nextMap)) {
    if (!form.enabled_shippers.includes(code)) delete nextMap[code]
  }
  form.enabled_shipper_tabs = nextMap
}

async function approve(company) {
  await approveCompanyApp(company.id)
  await reload()
}

async function reject(company) {
  if (!window.confirm(`${company.name} 신청을 거절할까요?`)) return
  await rejectCompanyApp(company.id)
  await reload()
}

async function remove(company) {
  if (!window.confirm(`${company.name} 회사를 삭제 보관 상태로 전환할까요?`)) return
  await deleteCompanyApp(company.id)
  await reload()
}

async function restore(company) {
  await restoreCompanyApp(company.id)
  await reload()
}

async function permanentlyRemove(company) {
  const confirmed = window.confirm(
    `${company.name} 회사를 완전삭제할까요?\n\n완전삭제 후에는 회사 관리 목록에서 사라지며 복구할 수 없습니다.`
  )
  if (!confirmed) return
  try {
    await permanentlyDeleteCompanyApp(company.id)
    notice.value = { type: 'success', message: '회사를 완전삭제했습니다.' }
    await reload()
  } catch (error) {
    notice.value = { type: 'error', message: error.response?.data?.detail || '회사 완전삭제에 실패했습니다.' }
  }
}

async function rotateToken(company) {
  if (!window.confirm(`${company.name} 회원가입 링크를 재발급할까요? 기존 링크는 사용할 수 없습니다.`)) return
  await rotateCompanySignupToken(company.id)
  await reload()
}

async function copySignupUrl(company) {
  try {
    await navigator.clipboard.writeText(company.signup_url)
    notice.value = { type: 'success', message: '회원가입 링크를 복사했습니다.' }
  } catch {
    window.prompt('회원가입 링크', company.signup_url)
  }
}

onMounted(reload)
</script>

<style scoped>
.form-input {
  width: 100%;
  border: 1px solid #d1d5db;
  border-radius: 10px;
  padding: 10px 12px;
  outline: none;
}

.form-input:focus {
  border-color: #84cc16;
  box-shadow: 0 0 0 3px rgba(132, 204, 22, 0.18);
}

.form-input:disabled {
  background: #f8fafc;
  color: #94a3b8;
}

.form-input-compact {
  min-height: 42px;
  padding: 8px 10px;
}

.primary-btn,
.secondary-btn {
  border-radius: 10px;
  padding: 10px 14px;
  font-size: 14px;
  font-weight: 700;
  white-space: nowrap;
  transition: all 0.15s ease;
}

.primary-btn {
  background: #84cc16;
  color: #111827;
}

.primary-btn:disabled {
  cursor: not-allowed;
  opacity: 0.55;
}

.secondary-btn {
  border: 1px solid #d1d5db;
  color: #334155;
}

.secondary-btn.danger {
  border-color: #fecaca;
  color: #b91c1c;
}

.secondary-btn:disabled {
  cursor: not-allowed;
  opacity: 0.45;
}

.shipper-action-btn {
  min-width: 58px;
}

.empty-state {
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  background: #ffffff;
  padding: 48px 16px;
  text-align: center;
  color: #94a3b8;
}
</style>
