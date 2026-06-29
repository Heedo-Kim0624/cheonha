<template>
  <div class="min-h-screen bg-gray-50 text-text">
    <header class="border-b border-gray-200 bg-white">
      <div class="mx-auto flex max-w-7xl items-center justify-between px-6 py-4">
        <div class="flex items-center gap-3">
          <div class="flex h-10 w-10 items-center justify-center rounded-lg bg-gray-900 text-sm font-bold text-white">CL</div>
          <div>
            <h1 class="text-xl font-bold">CLEVER</h1>
            <p class="text-xs text-gray-500">운영 통합 관리</p>
          </div>
        </div>
        <div class="flex items-center gap-3">
          <RouterLink
            v-if="isCleverAdminSession"
            to="/cheonha"
            class="rounded-lg border border-gray-300 px-4 py-2 text-sm font-semibold text-gray-700 hover:bg-gray-50"
          >
            천하운수 페이지
          </RouterLink>
          <button
            v-if="authStore.isAuthenticated"
            @click="logout"
            class="rounded-lg bg-gray-900 px-4 py-2 text-sm font-semibold text-white hover:bg-gray-800"
          >
            로그아웃
          </button>
        </div>
      </div>
    </header>

    <main class="mx-auto max-w-7xl px-6 py-8">
      <section v-if="!isCleverAdminSession" class="mx-auto w-full max-w-md">
        <form @submit.prevent="login" class="rounded-xl border border-gray-200 bg-white p-6">
          <h2 class="text-xl font-bold">관리자 로그인</h2>
          <p class="mt-1 text-sm text-gray-500">CLEVER 관리자 계정으로 로그인하세요.</p>
          <div
            v-if="authStore.isAuthenticated && !isCleverAdminSession"
            class="mt-4 rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800"
          >
            현재 로그인된 계정은 CLEVER 관리자 권한이 없습니다. CLEVER 관리자 계정으로 다시 로그인하세요.
          </div>
          <label class="mt-6 block">
            <span class="mb-2 block text-sm font-semibold text-gray-600">아이디</span>
            <input v-model="loginId" type="text" required
              class="w-full rounded-lg border border-gray-300 px-4 py-3 outline-none focus:border-primary" />
          </label>
          <label class="mt-4 block">
            <span class="mb-2 block text-sm font-semibold text-gray-600">비밀번호</span>
            <input v-model="loginPassword" type="password" required
              class="w-full rounded-lg border border-gray-300 px-4 py-3 outline-none focus:border-primary" />
          </label>
          <div v-if="loginError" class="mt-4 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">
            {{ loginError }}
          </div>
          <button
            type="submit"
            :disabled="loginLoading"
            class="mt-5 w-full rounded-lg bg-primary px-4 py-3 font-bold text-white hover:opacity-90 disabled:opacity-50"
          >
            {{ loginLoading ? '로그인 중...' : '로그인' }}
          </button>
        </form>
      </section>

      <section v-else class="portal-layout">
        <aside class="portal-sidebar">
          <div class="sidebar-head">
            <span class="sidebar-mark">CL</span>
            <div>
              <p class="sidebar-kicker">CLEVER</p>
              <h2>통합 관리</h2>
            </div>
          </div>

          <nav class="sidebar-nav" aria-label="CLEVER 메뉴">
            <RouterLink
              :to="{ name: 'CleverPortal' }"
              class="sidebar-tab"
              :class="{ active: activeTab === 'operations' }"
            >
              <span>운영현황</span>
              <small>날짜별 운영 지표</small>
            </RouterLink>
            <RouterLink
              :to="{ name: 'CleverPortalTracking' }"
              class="sidebar-tab"
              :class="{ active: activeTab === 'tracking' }"
            >
              <span>근무기록 CSV</span>
              <small>앱 기록 다운로드</small>
            </RouterLink>
            <RouterLink
              :to="{ name: 'CleverPortalPoints' }"
              class="sidebar-tab"
              :class="{ active: activeTab === 'points' }"
            >
              <span>포인트 조회</span>
              <small>적립/사용 관리</small>
            </RouterLink>
          </nav>

          <RouterLink :to="companyLink" class="sidebar-link">
            회사 관리로 이동
          </RouterLink>
        </aside>

        <section class="portal-content">
          <header class="portal-topbar">
            <div>
              <p class="portal-kicker">{{ selectedCompanyName }}</p>
              <h2>{{ activeTabTitle }}</h2>
              <p class="portal-desc">회사와 조를 선택해 데이터를 확인합니다.</p>
            </div>
            <label class="portal-company">
              <span>회사</span>
              <select v-model="selectedCompany" @change="handleCompanyChange">
                <option v-for="company in companies" :key="company.code" :value="company.code">{{ company.name }}</option>
              </select>
            </label>
          </header>

          <section v-if="activeTab === 'operations'" class="space-y-5">
            <div class="team-button-panel">
              <span class="team-button-label">조 선택</span>
              <div class="team-buttons">
                <button
                  type="button"
                  @click="selectTeam('')"
                  :class="{ active: selectedTeamId === '' }"
                >
                  전체
                </button>
                <button
                  v-for="team in teams"
                  :key="team.id"
                  type="button"
                  @click="selectTeam(String(team.id))"
                  :class="{ active: selectedTeamId === String(team.id) }"
                >
                  {{ team.name }}
                </button>
              </div>
            </div>

            <OperationReportPanel
              :company-name="selectedCompanyName"
              :team-name="selectedTeamName"
              :show-company-select="false"
              :show-team-filter="false"
            />
          </section>

          <section v-else-if="activeTab === 'tracking'" class="space-y-4">
            <div class="tracking-toolbar">
              <label>
                <span>근무일</span>
                <input v-model="trackingDate" type="date" />
              </label>
              <label>
                <span>조</span>
                <select v-model="selectedTeamId" @change="loadTracking">
                  <option value="">전체</option>
                  <option v-for="team in teams" :key="team.id" :value="String(team.id)">{{ team.name }}</option>
                </select>
              </label>
              <button @click="loadTracking" :disabled="trackingLoading">조회</button>
            </div>

            <div class="overflow-hidden rounded-xl border border-gray-200 bg-white">
              <div v-if="trackingLoading" class="py-12 text-center text-gray-400">로딩 중...</div>
              <div v-else-if="trackingSessions.length === 0" class="py-12 text-center text-gray-400">근무기록 CSV 데이터가 없습니다.</div>
              <div v-else class="overflow-x-auto">
                <table class="w-full min-w-[900px] text-sm">
                  <thead class="border-b border-gray-200 bg-gray-50">
                    <tr>
                      <th class="px-4 py-3 text-left font-semibold text-gray-600">근무일</th>
                      <th class="px-4 py-3 text-left font-semibold text-gray-600">회사</th>
                      <th class="px-4 py-3 text-left font-semibold text-gray-600">조</th>
                      <th class="px-4 py-3 text-left font-semibold text-gray-600">배송원</th>
                      <th class="px-4 py-3 text-right font-semibold text-gray-600">이동거리</th>
                      <th class="px-4 py-3 text-right font-semibold text-gray-600">사이클</th>
                      <th class="px-4 py-3 text-center font-semibold text-gray-600">CSV</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="session in trackingSessions" :key="session.id" class="border-b border-gray-100">
                      <td class="px-4 py-3 font-semibold">{{ session.session_date }}</td>
                      <td class="px-4 py-3">{{ selectedCompanyName }}</td>
                      <td class="px-4 py-3">{{ session.team_name || '-' }}</td>
                      <td class="px-4 py-3">{{ session.crew_name || '-' }}</td>
                      <td class="px-4 py-3 text-right">{{ formatKm(session.distance_m) }}</td>
                      <td class="px-4 py-3 text-right">{{ formatNumber(session.cycle_count) }}</td>
                      <td class="px-4 py-3 text-center">
                        <button @click="downloadSessionCsv(session)"
                          class="rounded-lg bg-gray-900 px-3 py-2 text-xs font-semibold text-white hover:bg-gray-800">
                          다운로드
                        </button>
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>
          </section>

          <section v-else class="space-y-4">
            <div class="team-button-panel">
              <span class="team-button-label">조 선택</span>
              <div class="team-buttons">
                <button
                  type="button"
                  @click="selectTeam('')"
                  :class="{ active: selectedTeamId === '' }"
                >
                  전체
                </button>
                <button
                  v-for="team in teams"
                  :key="team.id"
                  type="button"
                  @click="selectTeam(String(team.id))"
                  :class="{ active: selectedTeamId === String(team.id) }"
                >
                  {{ team.name }}
                </button>
              </div>
              <button class="point-refresh-top" type="button" @click="loadPoints" :disabled="pointLoading">새로고침</button>
            </div>

            <div class="overflow-hidden rounded-xl border border-gray-200 bg-white">
              <div v-if="pointLoading" class="py-12 text-center text-gray-400">로딩 중...</div>
              <div v-else-if="pointRows.length === 0" class="py-12 text-center text-gray-400">포인트 데이터가 없습니다.</div>
              <div v-else class="overflow-x-auto">
                <table class="w-full min-w-[1080px] text-sm">
                  <thead class="border-b border-gray-200 bg-gray-50">
                    <tr>
                      <th class="px-4 py-3 text-left font-semibold text-gray-600">조</th>
                      <th class="px-4 py-3 text-left font-semibold text-gray-600">배송원</th>
                      <th class="px-4 py-3 text-left font-semibold text-gray-600">차량번호</th>
                      <th class="px-4 py-3 text-right font-semibold text-gray-600">보유 포인트</th>
                      <th class="px-4 py-3 text-right font-semibold text-gray-600">사용대기</th>
                      <th class="px-4 py-3 text-right font-semibold text-gray-600">사용가능</th>
                      <th class="px-4 py-3 text-left font-semibold text-gray-600">사용 요청</th>
                      <th class="px-4 py-3 text-left font-semibold text-gray-600">직접 수정</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr
                      v-for="row in pointRows"
                      :key="row.id"
                      class="border-b border-gray-100"
                      :class="{ 'point-row-pending': row.pending_redemptions?.length }"
                    >
                      <td class="px-4 py-3">{{ row.team_name || '-' }}</td>
                      <td class="px-4 py-3 font-semibold">{{ row.name }}</td>
                      <td class="px-4 py-3">{{ row.vehicle_number || '-' }}</td>
                      <td class="px-4 py-3 text-right font-semibold">{{ formatNumber(row.balance) }}P</td>
                      <td class="px-4 py-3 text-right">{{ formatNumber(row.pending_points) }}P</td>
                      <td class="px-4 py-3 text-right">{{ formatNumber(row.available_points) }}P</td>
                      <td class="px-4 py-3">
                        <div v-if="row.pending_redemptions?.length" class="point-request-list">
                          <div v-for="redemption in row.pending_redemptions" :key="redemption.id" class="point-request">
                            <div>
                              <strong>{{ redemption.item_name }}</strong>
                              <span>{{ formatNumber(redemption.cost_points) }}P</span>
                            </div>
                            <button type="button" @click="confirmRedemption(redemption.id)" :disabled="pointActionLoading === redemption.id">
                              사용 확인
                            </button>
                          </div>
                        </div>
                        <span v-else class="text-gray-400">-</span>
                      </td>
                      <td class="px-4 py-3">
                        <div class="point-edit">
                          <input v-model.number="pointDrafts[row.id]" type="number" min="0" />
                          <button type="button" @click="savePointBalance(row)" :disabled="pointSavingCrewId === row.id">
                            저장
                          </button>
                        </div>
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>
          </section>
        </section>
      </section>
    </main>
  </div>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import client from '@/api/client'
import OperationReportPanel from '@/components/operations/OperationReportPanel.vue'
import { useAuthStore } from '@/stores/auth'
import { fetchTrackingSessions, downloadTrackingCsv } from '@/api/tracking'
import {
  confirmPointRedemption,
  fetchPointSummaries,
  setCrewPointBalance
} from '@/api/points'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

const companies = [{ code: 'cheonha', name: '천하운수', path: '/cheonha' }]
const cleverAdminUsernames = ['clever_admin']
const selectedCompany = ref('cheonha')
const loginId = ref('')
const loginPassword = ref('')
const loginLoading = ref(false)
const loginError = ref('')

const teams = ref([])
const selectedTeamId = ref('')

const trackingDate = ref('')
const trackingLoading = ref(false)
const trackingSessions = ref([])
const pointLoading = ref(false)
const pointRows = ref([])
const pointDrafts = ref({})
const pointSavingCrewId = ref(null)
const pointActionLoading = ref(null)

const selectedCompanyItem = computed(() => companies.find(company => company.code === selectedCompany.value) || companies[0])
const selectedCompanyName = computed(() => selectedCompanyItem.value.name)
const companyLink = computed(() => selectedCompanyItem.value.path)
const selectedTeamName = computed(() => teams.value.find(team => String(team.id) === String(selectedTeamId.value))?.name || '')
const activeTab = computed(() => route.meta.portalTab || 'operations')
const activeTabTitle = computed(() => {
  if (activeTab.value === 'tracking') return '근무기록 CSV'
  if (activeTab.value === 'points') return '포인트 조회'
  return '운영현황'
})
const isCleverAdminSession = computed(() => {
  const username = authStore.user?.username || ''
  return authStore.isAuthenticated && cleverAdminUsernames.includes(username)
})

const formatNumber = (value) => Number(value || 0).toLocaleString()
const formatKm = (meters) => `${(Number(meters || 0) / 1000).toLocaleString(undefined, { maximumFractionDigits: 2 })}km`

const loadTeams = async () => {
  try {
    const response = await client.get('/accounts/teams/')
    teams.value = response.data.results || response.data || []
  } catch {
    teams.value = []
  }
}

const loadTracking = async () => {
  trackingLoading.value = true
  try {
    const params = {}
    if (trackingDate.value) params.date = trackingDate.value
    if (selectedTeamId.value) params.team = selectedTeamId.value
    const response = await fetchTrackingSessions(params)
    trackingSessions.value = response.data.results || response.data || []
  } catch {
    trackingSessions.value = []
  } finally {
    trackingLoading.value = false
  }
}

const loadPoints = async () => {
  pointLoading.value = true
  try {
    const params = {}
    if (selectedTeamId.value) params.team = selectedTeamId.value
    const response = await fetchPointSummaries(params)
    const rows = response.data.results || response.data || []
    pointRows.value = rows
    pointDrafts.value = rows.reduce((acc, row) => {
      acc[row.id] = row.balance || 0
      return acc
    }, {})
  } catch {
    pointRows.value = []
    pointDrafts.value = {}
  } finally {
    pointLoading.value = false
  }
}

const loadPortalTabData = async (tab = activeTab.value) => {
  if (tab === 'tracking') {
    await loadTracking()
  } else if (tab === 'points') {
    await loadPoints()
  }
}

const handleCompanyChange = async () => {
  await loadPortalTabData()
}

const selectTeam = async (teamId) => {
  selectedTeamId.value = teamId || ''
  if (activeTab.value === 'tracking') {
    await loadTracking()
  } else if (activeTab.value === 'points') {
    await loadPoints()
  }
}

const savePointBalance = async (row) => {
  const balance = Number(pointDrafts.value[row.id] || 0)
  if (!Number.isFinite(balance) || balance < 0) {
    window.alert('포인트는 0 이상 숫자로 입력해주세요.')
    return
  }
  pointSavingCrewId.value = row.id
  try {
    await setCrewPointBalance(row.id, {
      balance,
      memo: 'CLEVER 포인트 조회 탭 직접 수정'
    })
    await loadPoints()
  } catch (error) {
    window.alert(error.response?.data?.detail || '포인트 수정에 실패했습니다.')
  } finally {
    pointSavingCrewId.value = null
  }
}

const confirmRedemption = async (redemptionId) => {
  pointActionLoading.value = redemptionId
  try {
    await confirmPointRedemption(redemptionId)
    await loadPoints()
  } catch (error) {
    window.alert(error.response?.data?.detail || '사용 확인에 실패했습니다.')
  } finally {
    pointActionLoading.value = null
  }
}

const downloadBlob = (blob, filename) => {
  const url = window.URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  link.remove()
  window.URL.revokeObjectURL(url)
}

const downloadSessionCsv = async (session) => {
  const response = await downloadTrackingCsv(session.id)
  const blob = new Blob([response.data], { type: 'text/csv;charset=utf-8;' })
  downloadBlob(blob, `CLEVER_${selectedCompanyName.value}_근무기록_${session.session_date}_${session.crew_name || session.id}.csv`)
}

const login = async () => {
  loginLoading.value = true
  loginError.value = ''
  try {
    await authStore.cleverLogin(loginId.value, loginPassword.value)
  } catch (error) {
    loginError.value = error.response?.data?.detail || '로그인에 실패했습니다.'
  } finally {
    loginLoading.value = false
  }
}

const logout = async () => {
  authStore.logout()
  trackingSessions.value = []
  pointRows.value = []
  await router.push('/')
}

watch(isCleverAdminSession, async (isEnabled) => {
  if (isEnabled) {
    await loadTeams()
    await loadPortalTabData()
    return
  }
  trackingSessions.value = []
  pointRows.value = []
  pointDrafts.value = {}
}, { immediate: true })

watch(activeTab, async (tab, previousTab) => {
  if (!isCleverAdminSession.value || tab === previousTab) return
  await loadPortalTabData(tab)
})
</script>

<style scoped>
.portal-layout {
  display: grid;
  grid-template-columns: 240px minmax(0, 1fr);
  gap: 20px;
  align-items: start;
}

.portal-layout > * {
  min-width: 0;
}

.portal-sidebar {
  position: sticky;
  top: 24px;
  display: flex;
  flex-direction: column;
  gap: 18px;
  border: 1px solid #d7dde5;
  border-radius: 8px;
  background: #ffffff;
  padding: 16px;
}

.sidebar-head {
  display: flex;
  align-items: center;
  gap: 12px;
  padding-bottom: 14px;
  border-bottom: 1px solid #e2e8f0;
}

.sidebar-mark {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 42px;
  height: 42px;
  border-radius: 8px;
  background: #111827;
  color: #ffffff;
  font-size: 13px;
  font-weight: 900;
}

.sidebar-kicker {
  color: #64748b;
  font-size: 11px;
  font-weight: 900;
}

.sidebar-head h2 {
  color: #111827;
  font-size: 18px;
  font-weight: 900;
}

.sidebar-nav {
  display: grid;
  gap: 8px;
}

.sidebar-tab {
  display: grid;
  gap: 3px;
  width: 100%;
  border-radius: 8px;
  padding: 12px;
  text-align: left;
  text-decoration: none;
  color: #475569;
  transition: background 0.15s ease, color 0.15s ease;
}

.sidebar-tab:hover {
  background: #f1f5f9;
}

.sidebar-tab.active {
  background: #111827;
  color: #ffffff;
}

.sidebar-tab span {
  font-size: 14px;
  font-weight: 900;
}

.sidebar-tab small {
  color: currentColor;
  font-size: 11px;
  font-weight: 700;
  opacity: 0.72;
}

.sidebar-link {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 42px;
  border: 1px solid #d7dde5;
  border-radius: 8px;
  color: #334155;
  font-size: 13px;
  font-weight: 900;
}

.sidebar-link:hover {
  background: #f8fafc;
}

.portal-content {
  min-width: 0;
  display: grid;
  gap: 16px;
}

.portal-topbar {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 16px;
  border: 1px solid #d7dde5;
  border-radius: 8px;
  background: #ffffff;
  padding: 18px 20px;
}

.portal-kicker {
  color: #64748b;
  font-size: 12px;
  font-weight: 900;
}

.portal-topbar h2 {
  margin-top: 2px;
  color: #111827;
  font-size: 24px;
  font-weight: 900;
}

.portal-desc {
  margin-top: 4px;
  color: #64748b;
  font-size: 13px;
  font-weight: 700;
}

.portal-company,
.tracking-toolbar label {
  display: flex;
  flex-direction: column;
  gap: 6px;
  color: #64748b;
  font-size: 12px;
  font-weight: 900;
}

.portal-company select,
.tracking-toolbar select,
.tracking-toolbar input {
  height: 42px;
  min-width: 150px;
  border: 1px solid #cfd7e3;
  border-radius: 8px;
  background: #ffffff;
  padding: 0 12px;
  color: #111827;
  outline: none;
}

.portal-company select:focus,
.tracking-toolbar select:focus,
.tracking-toolbar input:focus {
  border-color: #8fa000;
  box-shadow: 0 0 0 3px rgba(200, 213, 48, 0.22);
}

.team-button-panel {
  display: flex;
  align-items: center;
  gap: 12px;
  border: 1px solid #d7dde5;
  border-radius: 8px;
  background: #ffffff;
  padding: 14px 16px;
}

.team-button-label {
  flex: 0 0 auto;
  color: #64748b;
  font-size: 12px;
  font-weight: 900;
}

.team-buttons {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.team-buttons button {
  min-height: 36px;
  border-radius: 8px;
  background: #f1f5f9;
  padding: 0 14px;
  color: #475569;
  font-size: 13px;
  font-weight: 900;
}

.team-buttons button:hover {
  background: #e2e8f0;
  color: #111827;
}

.team-buttons button.active {
  background: #c8d530;
  color: #1f2937;
}

.tracking-toolbar {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-end;
  gap: 12px;
  border: 1px solid #d7dde5;
  border-radius: 8px;
  background: #ffffff;
  padding: 16px;
}

.tracking-toolbar button {
  height: 42px;
  border-radius: 8px;
  background: #111827;
  padding: 0 18px;
  color: #ffffff;
  font-weight: 900;
}

.tracking-toolbar button:disabled {
  opacity: 0.5;
}

.point-refresh-top {
  margin-left: auto;
  min-height: 36px;
  border-radius: 8px;
  background: #111827;
  padding: 0 14px;
  color: #ffffff;
  font-size: 13px;
  font-weight: 900;
}

.point-refresh-top:disabled {
  opacity: 0.5;
}

.point-row-pending {
  background: #fffbeb;
}

.point-request-list {
  display: grid;
  gap: 8px;
}

.point-request {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  border: 1px solid #f59e0b;
  border-radius: 8px;
  background: #ffffff;
  padding: 8px 10px;
}

.point-request div {
  display: grid;
  gap: 2px;
}

.point-request strong {
  color: #111827;
  font-size: 13px;
}

.point-request span {
  color: #92400e;
  font-size: 12px;
  font-weight: 800;
}

.point-request button,
.point-edit button {
  min-height: 34px;
  border-radius: 8px;
  background: #111827;
  padding: 0 12px;
  color: #ffffff;
  font-size: 12px;
  font-weight: 900;
}

.point-request button:disabled,
.point-edit button:disabled {
  opacity: 0.5;
}

.point-edit {
  display: flex;
  align-items: center;
  gap: 8px;
}

.point-edit input {
  width: 108px;
  height: 36px;
  border: 1px solid #cfd7e3;
  border-radius: 8px;
  padding: 0 10px;
  text-align: right;
  outline: none;
}

.point-edit input:focus {
  border-color: #8fa000;
  box-shadow: 0 0 0 3px rgba(200, 213, 48, 0.22);
}

@media (max-width: 1024px) {
  .portal-layout {
    grid-template-columns: 1fr;
  }

  .portal-sidebar {
    position: static;
  }

  .sidebar-nav {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 640px) {
  .portal-topbar,
  .team-button-panel {
    align-items: flex-start;
    flex-direction: column;
  }

  .portal-company,
  .portal-company select {
    width: 100%;
  }

  .point-refresh-top {
    margin-left: 0;
  }

  .sidebar-nav {
    grid-template-columns: 1fr;
  }
}
</style>
