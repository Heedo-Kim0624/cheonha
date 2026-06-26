<template>
  <div class="fleet-page">
    <aside class="fleet-sidebar">
      <RouterLink to="/portal/operations" class="back-link">운영 통합관리로 돌아가기</RouterLink>
      <div class="quick-links" aria-label="운영 바로가기">
        <RouterLink to="/portal/companies">회사 목록</RouterLink>
        <RouterLink to="/company/new/settlement?one_tab=upload">새회사 오네 정산</RouterLink>
      </div>

      <div class="brand">
        <span class="brand-mark">CL</span>
        <div>
          <p>CLEVER</p>
          <h1>차량관리</h1>
        </div>
      </div>

      <label class="company-select">
        <span>차량 회사</span>
        <select v-model="selectedCompany" @change="reload">
          <option v-for="company in companies" :key="company.code" :value="company.code">
            {{ company.name }}
          </option>
        </select>
      </label>

      <nav class="fleet-nav" aria-label="차량관리 메뉴">
        <button
          v-for="tab in tabs"
          :key="tab.key"
          type="button"
          :class="{ active: activeTab === tab.key }"
          @click="goTab(tab.key)"
        >
          <span>{{ tab.label }}</span>
          <small>{{ tab.caption }}</small>
        </button>
      </nav>

      <a class="legacy-link" :href="legacyUrl">기존 전체 기능 화면 열기</a>
    </aside>

    <main class="fleet-main">
      <header class="topbar">
        <div>
          <p class="eyebrow">FLEET MANAGEMENT</p>
          <h2>{{ currentTab?.label || '차량관리' }}</h2>
          <p>{{ currentTab?.caption || '차량 운영 데이터를 관리합니다.' }}</p>
        </div>
        <div class="top-actions">
          <input v-model="search" type="search" placeholder="차량번호, 차대번호, 고객명 검색" />
          <select v-model="statusFilter" aria-label="상태 필터">
            <option value="">전체 상태</option>
            <option v-for="status in statusChoices" :key="status" :value="status">{{ status }}</option>
          </select>
          <button type="button" class="btn" :disabled="loading" @click="reload">
            {{ loading ? '불러오는 중' : '새로고침' }}
          </button>
        </div>
      </header>

      <div v-if="error" class="alert">{{ error }}</div>

      <section v-if="activeTab === 'dashboard'" class="content-stack">
        <div class="metric-grid">
          <button
            v-for="metric in dashboardMetrics"
            :key="metric.key"
            type="button"
            class="metric-card"
            @click="focusMetric(metric.key)"
          >
            <span>{{ metric.label }}</span>
            <strong>{{ metric.value }}</strong>
            <small>{{ metric.caption }}</small>
          </button>
        </div>

        <section class="panel">
          <div class="panel-head">
            <div>
              <h3>차량 운영 현황</h3>
              <p>차량번호 기준으로 계약, 반납, 보험, 사고 이력을 묶어서 봅니다.</p>
            </div>
          </div>
          <FleetVehicleTable
            :groups="filteredGroups"
            :selected-plate="selectedPlate"
            :status-choices="statusChoices"
            @select="selectGroup"
            @status="saveStatus"
          />
        </section>
      </section>

      <section v-else-if="activeTab === 'vehicles'" class="content-stack">
        <section class="panel">
          <div class="panel-head">
            <div>
              <h3>차량 목록</h3>
              <p>차량번호 옆 상태값을 바로 바꾸고, 차량별 통합 이력을 확인합니다.</p>
            </div>
            <a class="btn primary" :href="legacyUrl">차량 추가/정보 변경</a>
          </div>
          <FleetVehicleTable
            :groups="filteredGroups"
            :selected-plate="selectedPlate"
            :status-choices="statusChoices"
            @select="selectGroup"
            @status="saveStatus"
          />
        </section>
      </section>

      <section v-else-if="activeTab === 'subscriptions'" class="panel">
        <div class="panel-head">
          <div>
            <h3>구독 전자계약</h3>
            <p>계약 기간, 구독료, 서명 상태를 차량번호 기준으로 확인합니다.</p>
          </div>
        </div>
        <SimpleTable :columns="subscriptionColumns" :rows="filteredSubscriptions" empty-text="구독 계약 이력이 없습니다." />
      </section>

      <section v-else-if="activeTab === 'returns'" class="panel">
        <div class="panel-head">
          <div>
            <h3>반납/수리비</h3>
            <p>반납 일정, 실제 반납일, 수리비 청구 이력을 확인합니다.</p>
          </div>
        </div>
        <SimpleTable :columns="returnColumns" :rows="filteredReturns" empty-text="반납/수리비 이력이 없습니다." />
      </section>

      <section v-else-if="activeTab === 'insurance'" class="panel">
        <div class="panel-head">
          <div>
            <h3>보험료 납부 현황</h3>
            <p>보험사, 증권번호, 가입 기간, 납부 상태를 관리합니다.</p>
          </div>
        </div>
        <SimpleTable :columns="insuranceColumns" :rows="filteredInsurances" empty-text="보험 이력이 없습니다." />
      </section>

      <section v-else-if="activeTab === 'accidents'" class="panel">
        <div class="panel-head">
          <div>
            <h3>사고 관리</h3>
            <p>사고관리대장과 보상상세내역을 하나의 사고 이력으로 봅니다.</p>
          </div>
          <button class="btn" type="button" @click="downloadAccidentTemplate">통합 양식 다운로드</button>
        </div>
        <SimpleTable :columns="accidentColumns" :rows="filteredAccidents" empty-text="사고 이력이 없습니다." />
      </section>

      <section v-else class="panel">
        <div class="panel-head">
          <div>
            <h3>엑셀 업로드</h3>
            <p>사고관리 통합 양식은 Vue에서 바로 다운로드하고, 대량 업로드는 기존 화면을 임시 연결합니다.</p>
          </div>
        </div>
        <div class="upload-bridge">
          <button class="btn" type="button" @click="downloadAccidentTemplate">사고 이력 통합 양식 다운로드</button>
          <a class="btn primary" :href="legacyUrl">기존 업로드 화면 열기</a>
        </div>
      </section>

      <section v-if="selectedGroup" class="detail-panel">
        <button type="button" class="detail-close" @click="selectedPlate = ''">×</button>
        <h3>{{ selectedGroup.plate }}</h3>
        <p>{{ selectedGroup.owner }} · {{ currentRecord(selectedGroup)?.vin || '차대번호 없음' }}</p>
        <div class="detail-grid">
          <div>
            <span>현재 상태</span>
            <strong>{{ fleetState(selectedGroup) }}</strong>
          </div>
          <div>
            <span>호기번호</span>
            <strong>{{ currentRecord(selectedGroup)?.unitNumber || '-' }}</strong>
          </div>
          <div>
            <span>구독</span>
            <strong>{{ selectedGroup.subscriptions?.length || 0 }}건</strong>
          </div>
          <div>
            <span>사고</span>
            <strong>{{ selectedGroup.accidents?.length || 0 }}건</strong>
          </div>
        </div>
      </section>
    </main>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import SimpleTable from '@/components/fleet/FleetSimpleTable.vue'
import FleetVehicleTable from '@/components/fleet/FleetVehicleTable.vue'
import { useFleetSite } from '@/composables/useFleetSite'
import {
  downloadFleetAccidentTemplate,
  updateFleetRecordStatus,
  updateFleetVehicleStatus,
} from '@/api/fleetManagement'

const tabs = [
  { key: 'dashboard', label: '대시보드', caption: '차량 운영 요약' },
  { key: 'vehicles', label: '차량 목록', caption: '차량번호별 통합 상세' },
  { key: 'subscriptions', label: '구독 전자계약', caption: '계약과 월 구독료' },
  { key: 'returns', label: '반납/수리비', caption: '반납과 청구 이력' },
  { key: 'insurance', label: '보험', caption: '보험료 납부 현황' },
  { key: 'accidents', label: '사고 관리', caption: '사고와 보상 이력' },
  { key: 'upload', label: '엑셀 업로드', caption: '양식 다운로드와 업로드' },
]

const routeNames = {
  dashboard: 'CleverPortalVehicleDashboard',
  vehicles: 'CleverPortalVehicleVehicles',
  subscriptions: 'CleverPortalVehicleSubscriptions',
  returns: 'CleverPortalVehicleReturns',
  insurance: 'CleverPortalVehicleInsurance',
  accidents: 'CleverPortalVehicleAccidents',
  upload: 'CleverPortalVehicleUpload',
}

const statusChoices = ['유휴', 'A/S', '판매', '구독', '직영']

const route = useRoute()
const router = useRouter()
const {
  companies,
  selectedCompany,
  groups,
  loading,
  error,
  loadCompanies,
  reload,
} = useFleetSite('CHEONHA')
const search = ref('')
const statusFilter = ref('')
const selectedPlate = ref('')

const activeTab = computed(() => route.meta.fleetTab || 'dashboard')
const currentTab = computed(() => tabs.find((tab) => tab.key === activeTab.value))
const legacyUrl = computed(() => `/fleet-management/?company=${encodeURIComponent(selectedCompany.value)}`)
const selectedGroup = computed(() => groups.value.find((group) => group.plate === selectedPlate.value))

const filteredGroups = computed(() => {
  const q = search.value.trim().toLowerCase()
  return groups.value.filter((group) => {
    const record = currentRecord(group)
    const statusMatched = !statusFilter.value || fleetState(group) === statusFilter.value
    if (!statusMatched) return false
    if (!q) return true
    const haystack = [
      group.plate,
      group.owner,
      record?.vin,
      record?.model,
      record?.unitNumber,
      ...(group.subscriptions || []).map((item) => item.customer),
      ...(group.accidents || []).map((item) => item.driver),
    ].join(' ').toLowerCase()
    return haystack.includes(q)
  })
})

const allSubscriptions = computed(() => groups.value.flatMap((group) =>
  (group.subscriptions || []).map((item) => ({
    plate: group.plate,
    customer: item.customer,
    period: `${item.start || '-'} ~ ${item.end || '-'}`,
    monthlyFee: money(item.monthlyFee),
    deposit: money(item.deposit),
    status: item.status || '-',
    signStatus: item.signStatus || '-',
  })),
))

const allReturns = computed(() => groups.value.flatMap((group) =>
  (group.returns || []).map((item) => ({
    plate: group.plate,
    customer: item.customer || '-',
    scheduled: item.scheduled || '-',
    actual: item.actual || '-',
    location: item.location || '-',
    status: item.status || '-',
    repairCount: Array.isArray(item.repairs) ? `${item.repairs.length}건` : '0건',
  })),
))

const allInsurances = computed(() => groups.value.flatMap((group) =>
  (group.insurances || []).map((item) => ({
    plate: group.plate,
    insurer: item.insurer || '-',
    policyNo: item.policyNo || '-',
    period: `${item.start || '-'} ~ ${item.end || '-'}`,
    status: item.status || '-',
    rate: `${item.previousRate ?? 0}% → ${item.currentRate ?? 0}%`,
  })),
))

const allAccidents = computed(() => groups.value.flatMap((group) =>
  (group.accidents || []).map((item) => ({
    plate: group.plate,
    driver: item.driver || '-',
    date: item.date || '-',
    location: item.location || '-',
    coverage: item.coverage || '-',
    compensation: money(item.compensation),
    status: item.status || '-',
  })),
))

const filteredSubscriptions = computed(() => filterRows(allSubscriptions.value))
const filteredReturns = computed(() => filterRows(allReturns.value))
const filteredInsurances = computed(() => filterRows(allInsurances.value))
const filteredAccidents = computed(() => filterRows(allAccidents.value))

const dashboardMetrics = computed(() => {
  const activeContracts = allSubscriptions.value.filter((item) => item.status.includes('구독') || item.status.toLowerCase().includes('active')).length
  const dueReturns = groups.value.filter((group) => {
    return (group.returns || []).some((item) => withinDays(item.scheduled, 7))
  }).length
  const missingDocs = groups.value.filter((group) => !hasRequiredDocuments(group)).length
  const repairClaims = groups.value.reduce((sum, group) => sum + (group.returns || []).reduce((inner, item) => inner + (Array.isArray(item.repairs) ? item.repairs.length : 0), 0), 0)
  return [
    { key: 'all', label: '전체 차량', value: `${groups.value.length}대`, caption: '등록된 차량번호 기준' },
    { key: 'subscribed', label: '구독 중', value: `${activeContracts}건`, caption: '진행 계약 기준' },
    { key: 'returns_due', label: '7일 내 반납 예정', value: `${dueReturns}대`, caption: '예정일 기준' },
    { key: 'missing_docs', label: '필수 서류 미비', value: `${missingDocs}대`, caption: '등록증/보험 청약서' },
    { key: 'repair_claims', label: '수리비 청구', value: `${repairClaims}건`, caption: '반납·수리 이력 기준' },
  ]
})

const subscriptionColumns = [
  { key: 'plate', label: '차량번호' },
  { key: 'customer', label: '고객' },
  { key: 'period', label: '기간' },
  { key: 'monthlyFee', label: '월 구독료', align: 'right' },
  { key: 'deposit', label: '보증금', align: 'right' },
  { key: 'status', label: '상태' },
  { key: 'signStatus', label: '서명' },
]

const returnColumns = [
  { key: 'plate', label: '차량번호' },
  { key: 'customer', label: '고객' },
  { key: 'scheduled', label: '반납 예정' },
  { key: 'actual', label: '실제 반납' },
  { key: 'location', label: '반납 장소' },
  { key: 'status', label: '상태' },
  { key: 'repairCount', label: '수리비' },
]

const insuranceColumns = [
  { key: 'plate', label: '차량번호' },
  { key: 'insurer', label: '보험사' },
  { key: 'policyNo', label: '증권번호' },
  { key: 'period', label: '기간' },
  { key: 'rate', label: '보험요율' },
  { key: 'status', label: '상태' },
]

const accidentColumns = [
  { key: 'plate', label: '차량번호' },
  { key: 'driver', label: '운전자' },
  { key: 'date', label: '사고일' },
  { key: 'location', label: '장소' },
  { key: 'coverage', label: '담보' },
  { key: 'compensation', label: '보상금액', align: 'right' },
  { key: 'status', label: '상태' },
]

function filterRows(rows) {
  const q = search.value.trim().toLowerCase()
  return rows.filter((row) => {
    if (statusFilter.value && row.status !== statusFilter.value) return false
    if (!q) return true
    return Object.values(row).join(' ').toLowerCase().includes(q)
  })
}

function goTab(tabKey) {
  router.push({ name: routeNames[tabKey] || routeNames.dashboard })
}

function selectGroup(group) {
  selectedPlate.value = group.plate
}

function currentRecord(group) {
  const records = group?.records || []
  return records.find((record) => !record.end) || records[records.length - 1] || null
}

function fleetState(group) {
  const record = currentRecord(group)
  if (record?.status) return record.status
  if ((group?.subscriptions || []).some((item) => item.status?.includes('구독'))) return '구독'
  return '유휴'
}

async function saveStatus(group, statusValue) {
  const record = currentRecord(group)
  const previous = record?.status
  if (record) record.status = statusValue
  try {
    if (record?.id?.startsWith('FVR-') && record.apiId) {
      await updateFleetRecordStatus(record.apiId, { status: statusValue })
    } else if (record?.vehicleApiId) {
      await updateFleetVehicleStatus(record.vehicleApiId, { status: statusValue })
    } else {
      throw new Error('차량 마스터 ID가 없어 상태를 변경할 수 없습니다.')
    }
    await reload()
  } catch (err) {
    if (record) record.status = previous
    error.value = err?.response?.data?.detail || err?.message || '상태 변경에 실패했습니다.'
  }
}

function focusMetric(metricKey) {
  if (metricKey === 'all') {
    statusFilter.value = ''
    selectedPlate.value = ''
    return
  }
  if (metricKey === 'subscribed') {
    statusFilter.value = '구독'
  } else if (metricKey === 'repair_claims') {
    statusFilter.value = 'A/S'
  } else {
    statusFilter.value = ''
  }
}

function hasRequiredDocuments(group) {
  const types = new Set((group.documents || []).map((doc) => doc.documentType || doc.document_type))
  return types.has('registration_certificate') && types.has('insurance_application')
}

function withinDays(value, days) {
  if (!value) return false
  const date = new Date(String(value).slice(0, 10))
  if (Number.isNaN(date.getTime())) return false
  const now = new Date()
  const diffDays = (date.getTime() - now.getTime()) / 86400000
  return diffDays >= 0 && diffDays <= days
}

function money(value) {
  const number = Number(value || 0)
  return `${number.toLocaleString('ko-KR')}원`
}

async function downloadAccidentTemplate() {
  try {
    const response = await downloadFleetAccidentTemplate({ company: selectedCompany.value })
    const blobUrl = URL.createObjectURL(response.data)
    const link = document.createElement('a')
    link.href = blobUrl
    link.download = '차량_사고관리_통합업로드_양식.xlsx'
    link.click()
    URL.revokeObjectURL(blobUrl)
  } catch (err) {
    error.value = err?.response?.data?.detail || err?.message || '양식 다운로드에 실패했습니다.'
  }
}

watch(selectedCompany, () => {
  selectedPlate.value = ''
})

onMounted(async () => {
  await loadCompanies()
  await reload()
})
</script>

<style scoped>
.fleet-page {
  min-height: 100vh;
  display: grid;
  grid-template-columns: 260px minmax(0, 1fr);
  background: #f3f6fa;
  color: #101827;
}

.fleet-sidebar {
  position: sticky;
  top: 0;
  height: 100vh;
  display: flex;
  flex-direction: column;
  gap: 18px;
  border-right: 1px solid #e4e8f0;
  background: #fff;
  padding: 22px 18px;
}

.back-link,
.legacy-link,
.btn {
  border: 1px solid #d7deea;
  border-radius: 10px;
  background: #fff;
  color: #1f2a44;
  font-weight: 800;
  text-decoration: none;
  padding: 10px 12px;
  text-align: center;
  cursor: pointer;
}

.quick-links {
  display: grid;
  gap: 8px;
  margin-top: -8px;
}

.quick-links a {
  display: block;
  border: 1px solid #e4e8f0;
  border-radius: 10px;
  background: #f8fafc;
  color: #475569;
  font-size: 13px;
  font-weight: 800;
  padding: 9px 11px;
  text-align: center;
  text-decoration: none;
}

.quick-links a:hover {
  border-color: #c5d941;
  color: #101827;
}

.btn.primary,
.brand-mark {
  border-color: #c5d941;
  background: #c5d941;
  color: #101827;
}

.brand {
  display: flex;
  align-items: center;
  gap: 12px;
}

.brand-mark {
  width: 44px;
  height: 44px;
  display: grid;
  place-items: center;
  border-radius: 12px;
  font-weight: 900;
}

.brand p {
  margin: 0;
  font-weight: 900;
  letter-spacing: .04em;
}

.brand h1 {
  margin: 2px 0 0;
  font-size: 18px;
}

.company-select span,
.company-select select {
  display: block;
  width: 100%;
}

.company-select span {
  margin-bottom: 7px;
  font-size: 13px;
  font-weight: 900;
  color: #64748b;
}

select,
input {
  border: 1px solid #d7deea;
  border-radius: 10px;
  background: #fff;
  color: #101827;
  font: inherit;
  padding: 10px 12px;
}

.fleet-nav {
  display: grid;
  gap: 8px;
}

.fleet-nav button {
  border: 0;
  border-radius: 13px;
  background: #f6f8fb;
  color: #334155;
  padding: 14px;
  text-align: left;
  cursor: pointer;
}

.fleet-nav button span,
.fleet-nav button small {
  display: block;
}

.fleet-nav button span {
  font-weight: 900;
}

.fleet-nav button small {
  margin-top: 4px;
  color: #7b8794;
}

.fleet-nav button.active {
  background: #101827;
  color: #fff;
}

.fleet-nav button.active small {
  color: #cbd5e1;
}

.legacy-link {
  margin-top: auto;
}

.fleet-main {
  min-width: 0;
  padding: 28px 32px 48px;
}

.topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 24px;
  margin-bottom: 18px;
}

.eyebrow {
  margin: 0 0 6px;
  font-size: 12px;
  font-weight: 900;
  letter-spacing: .08em;
  color: #718096;
}

.topbar h2 {
  margin: 0;
  font-size: 28px;
}

.topbar p {
  margin: 6px 0 0;
  color: #667085;
}

.top-actions {
  width: min(720px, 55vw);
  display: grid;
  grid-template-columns: minmax(220px, 1fr) 150px auto;
  gap: 10px;
}

.content-stack {
  display: grid;
  gap: 18px;
}

.metric-grid {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 12px;
}

.metric-card {
  border: 1px solid #e4e8f0;
  border-radius: 14px;
  background: #fff;
  padding: 18px;
  text-align: left;
  cursor: pointer;
}

.metric-card span,
.metric-card small {
  display: block;
  color: #718096;
  font-weight: 800;
}

.metric-card strong {
  display: block;
  margin: 8px 0 6px;
  font-size: 26px;
}

.panel,
.detail-panel {
  border: 1px solid #e4e8f0;
  border-radius: 16px;
  background: #fff;
  padding: 18px;
}

.panel-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 14px;
}

.panel-head h3,
.detail-panel h3 {
  margin: 0;
  font-size: 20px;
}

.panel-head p,
.detail-panel p {
  margin: 6px 0 0;
  color: #667085;
}

.alert {
  margin-bottom: 16px;
  border: 1px solid #fecaca;
  border-radius: 12px;
  background: #fef2f2;
  color: #b91c1c;
  padding: 12px 14px;
  font-weight: 800;
}

.detail-panel {
  position: fixed;
  right: 28px;
  bottom: 28px;
  width: min(520px, calc(100vw - 320px));
  box-shadow: 0 18px 50px rgba(15, 23, 42, .18);
}

.detail-close {
  position: absolute;
  top: 10px;
  right: 12px;
  border: 0;
  background: transparent;
  font-size: 24px;
  cursor: pointer;
}

.detail-grid {
  margin-top: 16px;
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
}

.detail-grid div {
  border-radius: 12px;
  background: #f7f9fc;
  padding: 12px;
}

.detail-grid span {
  display: block;
  font-size: 12px;
  font-weight: 800;
  color: #7b8794;
}

.detail-grid strong {
  display: block;
  margin-top: 6px;
}

.upload-bridge {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

@media (max-width: 1100px) {
  .fleet-page {
    grid-template-columns: 1fr;
  }

  .fleet-sidebar {
    position: static;
    height: auto;
  }

  .fleet-nav {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .metric-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .topbar {
    align-items: stretch;
    flex-direction: column;
  }

  .top-actions {
    width: 100%;
    grid-template-columns: 1fr;
  }

  .detail-panel {
    position: static;
    width: auto;
    margin-top: 16px;
  }
}
</style>
