<template>
  <div class="flex h-screen bg-bg">
    <aside class="flex w-sidebar flex-col border-r border-gray-200 bg-white shadow-sm">
      <div class="border-b border-gray-200 p-5">
        <div class="flex items-center gap-3">
          <div
            v-if="companyApp.code === 'cheonha'"
            class="flex h-10 w-10 items-center justify-center overflow-hidden rounded-lg border border-gray-200 bg-white p-1"
          >
            <img src="/cheonha-logo.jpg" alt="천하운수" class="h-full w-full object-contain" />
          </div>
          <div v-else class="flex h-10 w-10 items-center justify-center rounded-lg bg-primary">
            <span class="font-bold text-white">{{ companyApp.mark }}</span>
          </div>
          <div class="min-w-0">
            <h1 class="leading-tight text-text">
              <span class="block text-sm font-extrabold">CLEVER</span>
              <span class="block truncate text-base font-bold">{{ companyApp.displayName }}</span>
            </h1>
            <p class="text-xs text-gray-400">정산관리</p>
          </div>
        </div>
        <div v-if="showShipperSwitcher" class="mt-4 rounded-xl border border-gray-200 bg-gray-50 p-3">
          <label class="block">
            <span class="mb-1 block text-xs font-extrabold text-gray-500">화주사</span>
            <select
              v-model="selectedShipper"
              class="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm font-bold text-text outline-none focus:border-primary"
            >
              <option v-for="shipper in shipperOptions" :key="shipper.code" :value="shipper.code">
                {{ shipper.name }}
              </option>
            </select>
          </label>
          <p class="mt-2 text-xs font-semibold text-gray-500">{{ selectedShipperName }} 기준 메뉴</p>
        </div>
      </div>

      <nav class="flex-1 overflow-y-auto py-3">
        <div v-if="isCompanyContextPending" class="px-3 py-4 text-sm font-semibold text-gray-400">
          회사 설정을 불러오는 중입니다.
        </div>
        <div v-else class="space-y-2 px-3">
          <ul v-if="visiblePrimaryNavItems.length" class="space-y-1 border-b border-gray-100 pb-2">
            <li v-for="item in visiblePrimaryNavItems" :key="navItemKey(item)">
              <RouterLink :to="navItemTo(item)" class="nav-link" :class="{ active: isNavItemActive(item) }">
                <span v-html="item.icon" class="h-5 w-5 flex-shrink-0"></span>
                <div class="flex-1">
                  <span class="block">{{ item.label }}</span>
                  <span class="block text-xs opacity-60">{{ item.desc }}</span>
                </div>
                <span
                  v-if="navItemBadge(item)"
                  class="rounded-full bg-red-500 px-2 py-0.5 text-xs font-bold text-white"
                >
                  {{ navItemBadge(item) }}
                </span>
              </RouterLink>
            </li>
          </ul>

          <ul class="space-y-1">
            <li v-for="item in visibleSecondaryNavItems" :key="navItemKey(item)">
              <RouterLink :to="navItemTo(item)" class="nav-link" :class="{ active: isNavItemActive(item) }">
                <span v-html="item.icon" class="h-5 w-5 flex-shrink-0"></span>
                <div class="flex-1">
                  <span class="block">{{ item.label }}</span>
                  <span class="block text-xs opacity-60">{{ item.desc }}</span>
                </div>
                <span
                  v-if="navItemBadge(item)"
                  class="rounded-full bg-red-500 px-2 py-0.5 text-xs font-bold text-white"
                >
                  {{ navItemBadge(item) }}
                </span>
              </RouterLink>
            </li>
          </ul>
        </div>
      </nav>

      <div v-if="authStore.isAuthenticated" class="border-t border-gray-200 p-3">
        <div class="mb-2 px-3 py-2 text-xs text-gray-400">
          {{ authStore.user?.username || '' }}
          <span class="ml-1 rounded bg-gray-100 px-1.5 py-0.5">{{ authStore.isAdmin ? '관리자' : '사용자' }}</span>
        </div>
        <button
          v-if="isCleverAdminSession"
          class="mb-2 flex w-full items-center gap-3 rounded-lg border border-blue-200 bg-blue-50 px-3 py-2.5 text-blue-700 transition-colors hover:bg-blue-100"
          @click="goToCleverPortal"
        >
          <span v-html="IconHome" class="h-4 w-4"></span>
          <span>운영 통합관리로 돌아가기</span>
        </button>
        <button
          class="flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-gray-500 transition-colors hover:bg-gray-100"
          @click="handleLogout"
        >
          <span v-html="IconLogout" class="h-4 w-4"></span>
          <span>로그아웃</span>
        </button>
      </div>
    </aside>

    <div class="flex min-w-0 flex-1 flex-col">
      <header class="flex items-center justify-between border-b border-gray-200 bg-white px-8 py-4 shadow-sm">
        <h2 class="text-xl font-bold text-text">{{ pageTitle }}</h2>
        <div class="flex items-center gap-3">
          <div v-if="showNotificationBell" class="relative" @click.stop>
            <button
              type="button"
              class="relative flex h-10 w-10 items-center justify-center rounded-full border border-gray-200 bg-white text-gray-600 transition hover:border-gray-300 hover:bg-gray-50"
              :class="notificationOpenCount > 0 ? 'text-red-600' : ''"
              aria-label="알림"
              @click="toggleInquiryDropdown"
            >
              <span v-html="IconBell" class="h-5 w-5"></span>
              <span
                v-if="notificationOpenCount > 0"
                class="absolute -right-1 -top-1 min-w-[20px] rounded-full bg-red-500 px-1.5 py-0.5 text-center text-[11px] font-extrabold leading-none text-white"
              >
                {{ notificationOpenCount > 99 ? '99+' : notificationOpenCount }}
              </span>
            </button>

            <div
              v-if="inquiryDropdownOpen"
              class="absolute right-0 top-12 z-50 w-[360px] overflow-hidden rounded-xl border border-gray-200 bg-white shadow-xl"
            >
              <div class="flex items-center justify-between border-b border-gray-100 px-4 py-3">
                <div>
                  <p class="text-sm font-extrabold text-text">알림</p>
                  <p class="text-xs text-gray-500">답변이 필요한 정산 문의</p>
                </div>
                <button
                  type="button"
                  class="rounded-md px-2 py-1 text-xs font-semibold text-gray-500 hover:bg-gray-50"
                  @click="refreshInquiryNotice"
                >
                  새로고침
                </button>
              </div>

              <div v-if="notificationOpenCount <= 0" class="px-4 py-8 text-center text-sm text-gray-400">
                새 정산 문의가 없습니다.
              </div>
              <div v-else class="max-h-[420px] overflow-y-auto">
                <div v-if="accountSignupItems.length" class="border-b border-gray-100">
                  <div class="bg-amber-50 px-4 py-2 text-xs font-extrabold text-amber-800">
                    회원가입 승인 요청
                  </div>
                  <div
                    v-for="item in accountSignupItems"
                    :key="`account-${item.id}`"
                    class="border-b border-amber-100 px-4 py-3 last:border-b-0"
                  >
                    <div class="flex items-start justify-between gap-3">
                      <div class="min-w-0">
                        <p class="truncate text-sm font-extrabold text-text">{{ item.username }}</p>
                        <p class="mt-1 text-xs text-gray-500">
                          관리자 계정 신청 · {{ formatNotificationTime(item.created_at) }}
                        </p>
                      </div>
                      <span class="shrink-0 rounded-full bg-amber-100 px-2 py-0.5 text-xs font-bold text-amber-800">승인 대기</span>
                    </div>
                    <div class="mt-3 flex gap-2">
                      <button
                        type="button"
                        class="flex-1 rounded-lg bg-emerald-600 px-3 py-2 text-xs font-bold text-white hover:bg-emerald-500"
                        @click.stop="approveAccountSignup(item)"
                      >
                        승인
                      </button>
                      <button
                        type="button"
                        class="flex-1 rounded-lg bg-red-500 px-3 py-2 text-xs font-bold text-white hover:bg-red-400"
                        @click.stop="rejectAccountSignup(item)"
                      >
                        거절
                      </button>
                    </div>
                  </div>
                </div>
                <button
                  v-for="item in inquiryNoticeItems"
                  :key="item.id"
                  type="button"
                  class="block w-full border-b border-gray-100 px-4 py-3 text-left transition last:border-b-0 hover:bg-red-50/50"
                  @click="goToInquiryNotice(item.id)"
                >
                  <div class="flex items-start justify-between gap-3">
                    <div class="min-w-0">
                      <p class="truncate text-sm font-extrabold text-text">
                        {{ item.crew_name || '배송원' }}
                        <span class="font-semibold text-gray-500">({{ item.team_name || '-' }})</span>
                      </p>
                      <p class="mt-1 text-xs text-gray-500">
                        정산일 {{ item.dispatch_date || '-' }} · {{ formatNotificationTime(item.latest_message_at || item.updated_at) }}
                      </p>
                    </div>
                    <span class="shrink-0 rounded-full bg-red-100 px-2 py-0.5 text-xs font-bold text-red-700">답변필요</span>
                  </div>
                  <p class="mt-2 line-clamp-2 text-sm leading-5 text-gray-600">
                    {{ item.latest_message || '정산 문의가 접수되었습니다.' }}
                  </p>
                </button>
              </div>

              <button
                type="button"
                class="block w-full border-t border-gray-100 bg-gray-50 px-4 py-3 text-center text-sm font-bold text-gray-700 hover:bg-gray-100"
                @click="goToInquiryNotice()"
              >
                정산 문의 전체 보기
              </button>
            </div>
          </div>
          <span class="text-gray-400">{{ currentDate }}</span>
        </div>
      </header>
      <main class="flex-1 overflow-x-hidden overflow-y-auto bg-gray-50 p-8">
        <div
          v-if="isCompanyContextPending"
          class="flex min-h-[360px] items-center justify-center rounded-2xl border border-gray-200 bg-white text-sm font-semibold text-gray-500"
        >
          회사 설정을 불러오는 중입니다.
        </div>
        <div v-else class="w-full max-w-full min-w-0 overflow-x-hidden">
          <slot></slot>
        </div>
      </main>
    </div>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  approveCompanyUserSignup,
  fetchPendingCompanyUserSignups,
  fetchPublicCompanyApp,
  fetchShippers,
  rejectCompanyUserSignup,
} from '@/api/companyAdmin'
import { fetchInquiryCounts } from '@/api/inquiry'
import { useAuthStore } from '@/stores/auth'
import { formatDate } from '@/utils/format'
import { IconHome, IconDispatch, IconCrew, IconSettlement, IconRegion, IconLogout, IconBell } from '@/utils/icons'
import { DEFAULT_COMPANY_TABS, buildCompanyApp, getCompanyAppFromRoute, setRuntimeCompanyApp } from '@/utils/companyApp'
import { ensureSelectedShipperCode, setSelectedShipperCode } from '@/utils/shipperContext'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
const inquiryNotice = ref({ total: 0, open: 0, latest_open_id: null, latest_open_items: [] })
const accountSignupNotice = ref({ count: 0, items: [] })
const inquiryDropdownOpen = ref(false)
const shipperCatalog = ref([{ code: 'kurly', name: '컬리', status: 'ACTIVE' }])
const selectedShipper = ref('kurly')
const companyConfigLoading = ref(false)
let inquiryPollTimer = null

const publicCompanyConfig = ref(null)
const routeCompanyApp = computed(() => getCompanyAppFromRoute(route))
const companyApp = computed(() => {
  if (publicCompanyConfig.value?.code === routeCompanyApp.value.code) {
    return buildCompanyApp(publicCompanyConfig.value)
  }
  return routeCompanyApp.value
})
const companyBase = computed(() => companyApp.value.routeBase)
const cleverAdminUsernames = ['clever_admin', 'admin2']
const isDynamicCompanyContext = computed(() => Boolean(route.params.companyCode))
const isCompanyContextPending = computed(() =>
  isDynamicCompanyContext.value && companyConfigLoading.value && !publicCompanyConfig.value,
)
const enabledShipperTabsMap = computed(() => companyApp.value.enabledShipperTabs || companyApp.value.enabled_shipper_tabs || {})
const isTabEnabled = (tab) => enabledTabs.value.has(tab)
const normalizeList = (payload) => payload?.results || payload || []
const enabledShipperCodes = computed(() => {
  const codes = companyApp.value.enabledShippers || companyApp.value.enabled_shippers || ['kurly']
  const normalized = (codes || []).map((code) => String(code || '').trim().toLowerCase()).filter(Boolean)
  return normalized.length ? normalized : ['kurly']
})
const shipperOptions = computed(() => {
  const enabled = new Set(enabledShipperCodes.value)
  const rows = normalizeList(shipperCatalog.value)
    .map((shipper) => ({ ...shipper, code: String(shipper.code || '').trim().toLowerCase() }))
    .filter((shipper) => enabled.has(shipper.code) && shipper.status !== 'INACTIVE')
  if (rows.length > 0) return rows
  return enabledShipperCodes.value.map((code) => ({ code, name: code.toUpperCase(), status: 'ACTIVE' }))
})
const showShipperSwitcher = computed(() => shipperOptions.value.length > 1)
const isOneOnlyCompany = computed(() =>
  enabledShipperCodes.value.length === 1 && enabledShipperCodes.value[0] === 'one',
)
const isOneShipperContext = computed(() => selectedShipper.value === 'one' || isOneOnlyCompany.value)
const selectedShipperName = computed(() => (
  shipperOptions.value.find((shipper) => shipper.code === selectedShipper.value)?.name || selectedShipper.value
))
const selectedShipperTabs = computed(() => {
  const shipper = selectedShipper.value || enabledShipperCodes.value[0] || 'kurly'
  const tabs = enabledShipperTabsMap.value?.[shipper]
  if (Array.isArray(tabs) && tabs.length) return tabs
  if (shipper === 'one' || isOneOnlyCompany.value) return ['settlement']
  return companyApp.value.enabledTabs || DEFAULT_COMPANY_TABS
})
const enabledTabs = computed(() => new Set(selectedShipperTabs.value))
const oneSettlementTabKeys = ['upload', 'summary', 'collection', 'drivers', 'statements']
const normalizeOneSettlementTab = (value) => {
  const next = String(Array.isArray(value) ? value[0] : (value || '')).trim()
  return oneSettlementTabKeys.includes(next) ? next : 'upload'
}
const isTabAllowedForShipper = (tab) => {
  if (!isOneShipperContext.value) return true
  return tab === 'settlement'
}

const primaryNavItems = computed(() => [
  { path: `${companyBase.value}/dashboard`, tab: 'dashboard', label: '대시보드', desc: '정산 요약 현황', icon: IconHome, admin: true },
  { path: `${companyBase.value}/dispatch`, tab: 'dispatch', label: '배차표 업로드', desc: '업로드 및 정산', icon: IconDispatch, admin: false },
  { path: `${companyBase.value}/operations`, tab: 'operations', label: '운영 현황', desc: '날짜별 조별 지표', icon: IconDispatch, admin: false },
])

const oneSettlementNavItems = computed(() => [
  {
    key: 'one-upload',
    path: `${companyBase.value}/settlement`,
    query: { one_tab: 'upload' },
    tab: 'settlement',
    label: '파일 업로드',
    desc: 'RAW 등록',
    icon: IconSettlement,
    admin: true,
  },
  {
    key: 'one-summary',
    path: `${companyBase.value}/settlement`,
    query: { one_tab: 'summary' },
    tab: 'settlement',
    label: '월별 요약',
    desc: '월별 합계',
    icon: IconSettlement,
    admin: true,
  },
  {
    key: 'one-collection',
    path: `${companyBase.value}/settlement`,
    query: { one_tab: 'collection' },
    tab: 'settlement',
    label: '월별 취합',
    desc: '기사별 원장',
    icon: IconSettlement,
    admin: true,
  },
  {
    key: 'one-drivers',
    path: `${companyBase.value}/settlement`,
    query: { one_tab: 'drivers' },
    tab: 'settlement',
    label: '배송원 목록',
    desc: 'SM별 정산',
    icon: IconCrew,
    admin: true,
  },
  {
    key: 'one-statements',
    path: `${companyBase.value}/settlement`,
    query: { one_tab: 'statements' },
    tab: 'settlement',
    label: '배송원별 정산',
    desc: '명세서 수정',
    icon: IconSettlement,
    admin: true,
  },
])

const navGroups = computed(() => {
  if (isOneShipperContext.value) {
    return [
      {
        label: '오네 기준 메뉴',
        items: oneSettlementNavItems.value,
      },
    ]
  }

  return [
    {
      label: '배송원',
      items: [
        { path: `${companyBase.value}/crew`, tab: 'crew', label: '배송원 관리', desc: '정규와 용차 관리', icon: IconCrew, admin: false },
        { path: `${companyBase.value}/manpower`, tab: 'manpower', label: '인력풀', desc: '기사 후보 목록', icon: IconCrew, admin: false },
      ],
    },
    {
      label: '권역',
      items: [
        { path: `${companyBase.value}/tracking`, tab: 'tracking', label: '권역 관리', desc: '권역과 추적 이력', icon: IconRegion, admin: false },
        { path: `${companyBase.value}/region`, tab: 'region', label: '조관리', desc: '조와 권역 단가 설정', icon: IconRegion, admin: true },
      ],
    },
    {
      label: '정산',
      items: [
        {
          path: `${companyBase.value}/settlement`,
          tab: 'settlement',
          label: '정산 처리',
          desc: '정산 생성과 검토',
          icon: IconSettlement,
          admin: true,
        },
        { path: `${companyBase.value}/inquiry`, tab: 'inquiry', label: '정산 문의', desc: '문의와 답변 관리', icon: IconSettlement, admin: true },
      ],
    },
  ]
})

const visiblePrimaryNavItems = computed(() => {
  if (isOneShipperContext.value) return []
  const items = primaryNavItems.value.filter((item) => isTabEnabled(item.tab) && isTabAllowedForShipper(item.tab))
  if (authStore.isAdmin) return items
  return items.filter((item) => !item.admin)
})

const visibleNavGroups = computed(() =>
  navGroups.value
    .map((group) => ({
      ...group,
      items: (authStore.isAdmin ? group.items : group.items.filter((item) => !item.admin))
        .filter((item) => isTabEnabled(item.tab) && isTabAllowedForShipper(item.tab)),
    }))
    .filter((group) => group.items.length),
)

const visibleSecondaryNavItems = computed(() => visibleNavGroups.value.flatMap((group) => group.items))

const pageTitle = computed(() => {
  const titles = {
    [`${companyBase.value}/dashboard`]: '대시보드',
    [`${companyBase.value}/dispatch`]: '배차표 업로드',
    [`${companyBase.value}/crew`]: '배송원 관리',
    [`${companyBase.value}/operations`]: '운영 현황',
    [`${companyBase.value}/tracking`]: '권역 관리',
    [`${companyBase.value}/manpower`]: '인력풀',
    [`${companyBase.value}/settlement`]: '정산 처리',
    [`${companyBase.value}/inquiry`]: '정산 문의',
    [`${companyBase.value}/region`]: '조관리',
  }
  if (isOneShipperContext.value && route.path === `${companyBase.value}/settlement`) return '오네 정산'
  return titles[route.path] || `CLEVER ${companyApp.value.displayName}`
})

const currentRouteTab = computed(() => {
  const pathToTab = {
    [`${companyBase.value}/dashboard`]: 'dashboard',
    [`${companyBase.value}/dispatch`]: 'dispatch',
    [`${companyBase.value}/operations`]: 'operations',
    [`${companyBase.value}/crew`]: 'crew',
    [`${companyBase.value}/manpower`]: 'manpower',
    [`${companyBase.value}/tracking`]: 'tracking',
    [`${companyBase.value}/region`]: 'region',
    [`${companyBase.value}/settlement`]: 'settlement',
    [`${companyBase.value}/inquiry`]: 'inquiry',
  }
  return pathToTab[route.path] || ''
})

const currentDate = ref(formatDate(new Date()))

const isCleverAdminSession = computed(() => {
  const username = authStore.user?.username || ''
  return cleverAdminUsernames.includes(username)
})
const notificationOpenCount = computed(() =>
  Number(inquiryNotice.value.open || 0) + Number(accountSignupNotice.value.count || 0)
)
const showNotificationBell = computed(() =>
  authStore.isAuthenticated
  && authStore.isAdmin
  && ((isTabEnabled('inquiry') && isTabAllowedForShipper('inquiry')) || accountSignupNotice.value.count > 0)
)
const inquiryNoticeItems = computed(() => inquiryNotice.value.latest_open_items || [])
const accountSignupItems = computed(() => accountSignupNotice.value.items || [])

const goToCleverPortal = async () => {
  await router.push('/')
}

function navItemKey(item) {
  return item.key || `${item.path}:${item.query?.one_tab || ''}`
}

function navItemTo(item) {
  if (!item.query) return item.path
  return {
    path: item.path,
    query: { ...route.query, ...item.query },
  }
}

function isNavItemActive(item) {
  if (route.path !== item.path) return false
  if (item.query?.one_tab) {
    return normalizeOneSettlementTab(route.query.one_tab) === item.query.one_tab
  }
  return true
}

function navItemBadge(item) {
  if (item.tab !== 'inquiry') return 0
  return Number(inquiryNotice.value.open || 0)
}

async function refreshInquiryNotice() {
  if (!authStore.isAuthenticated || !authStore.isAdmin) {
    inquiryNotice.value = { total: 0, open: 0, latest_open_id: null, latest_open_items: [] }
    accountSignupNotice.value = { count: 0, items: [] }
    inquiryDropdownOpen.value = false
    return
  }

  if (isTabEnabled('inquiry')) {
    try {
      const response = await fetchInquiryCounts()
      inquiryNotice.value = response.data || { total: 0, open: 0, latest_open_id: null, latest_open_items: [] }
    } catch {
      inquiryNotice.value = { total: 0, open: 0, latest_open_id: null, latest_open_items: [] }
    }
  } else {
    inquiryNotice.value = { total: 0, open: 0, latest_open_id: null, latest_open_items: [] }
  }

  try {
    const response = await fetchPendingCompanyUserSignups()
    accountSignupNotice.value = response.data || { count: 0, items: [] }
  } catch {
    accountSignupNotice.value = { count: 0, items: [] }
  }
}

function startInquiryPolling() {
  if (inquiryPollTimer) clearInterval(inquiryPollTimer)
  void refreshInquiryNotice()
  inquiryPollTimer = setInterval(refreshInquiryNotice, 60000)
}

function toggleInquiryDropdown() {
  inquiryDropdownOpen.value = !inquiryDropdownOpen.value
  if (inquiryDropdownOpen.value) {
    void refreshInquiryNotice()
  }
}

function goToInquiryNotice(id = null) {
  inquiryDropdownOpen.value = false
  const targetId = id || inquiryNotice.value.latest_open_id
  const query = targetId
    ? { id: String(targetId) }
    : undefined
  router.push({ path: `${companyBase.value}/inquiry`, query })
}

async function approveAccountSignup(item) {
  if (!item?.id) return
  try {
    await approveCompanyUserSignup(item.id)
    await refreshInquiryNotice()
  } catch (error) {
    window.alert(error.response?.data?.detail || '회원가입 신청 승인에 실패했습니다.')
  }
}

async function rejectAccountSignup(item) {
  if (!item?.id) return
  if (!window.confirm(`${item.username} 회원가입 신청을 거절할까요?`)) return
  try {
    await rejectCompanyUserSignup(item.id)
    await refreshInquiryNotice()
  } catch (error) {
    window.alert(error.response?.data?.detail || '회원가입 신청 거절에 실패했습니다.')
  }
}

function formatNotificationTime(value) {
  if (!value) return ''
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return ''
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  const hour = String(date.getHours()).padStart(2, '0')
  const minute = String(date.getMinutes()).padStart(2, '0')
  return `${month}.${day} ${hour}:${minute}`
}

function closeInquiryDropdown() {
  inquiryDropdownOpen.value = false
}

const handleLogout = async () => {
  authStore.logout()
  await router.push(companyApp.value.loginPath)
}

function syncSelectedShipper(preferred = selectedShipper.value) {
  selectedShipper.value = ensureSelectedShipperCode(
    companyApp.value.code,
    enabledShipperCodes.value,
    preferred || enabledShipperCodes.value[0] || 'kurly',
  )
}

function redirectToOneSettlementIfNeeded() {
  if (isCompanyContextPending.value) return
  if (!isOneShipperContext.value) return

  const oneTab = normalizeOneSettlementTab(route.query.one_tab)
  const settlementPath = `${companyBase.value}/settlement`
  const location = {
    path: settlementPath,
    query: { ...route.query, one_tab: oneTab },
  }

  if (route.path !== settlementPath) {
    void router.replace(location)
  } else if (route.query.one_tab !== oneTab) {
    void router.replace(location)
  }
}

function fallbackRouteForCurrentShipper() {
  if (isOneShipperContext.value) {
    return {
      path: `${companyBase.value}/settlement`,
      query: { ...route.query, one_tab: normalizeOneSettlementTab(route.query.one_tab) },
    }
  }

  const firstItem = [...visiblePrimaryNavItems.value, ...visibleSecondaryNavItems.value][0]
  return firstItem ? navItemTo(firstItem) : `${companyBase.value}/dispatch`
}

function redirectToAllowedTabIfNeeded() {
  if (isCompanyContextPending.value) return
  if (isOneShipperContext.value) {
    redirectToOneSettlementIfNeeded()
    return
  }
  const tab = currentRouteTab.value
  if (!tab || isTabEnabled(tab)) return
  void router.replace(fallbackRouteForCurrentShipper())
}

watch(
  [() => authStore.isAuthenticated, () => authStore.isAdmin, () => companyApp.value.code],
  () => {
    startInquiryPolling()
  },
  { immediate: true },
)

watch(
  () => routeCompanyApp.value.code,
  async (code) => {
    publicCompanyConfig.value = null
    companyConfigLoading.value = true
    try {
      const [companyResponse, shipperResponse] = await Promise.all([
        fetchPublicCompanyApp(code),
        fetchShippers(),
      ])
      publicCompanyConfig.value = companyResponse.data
      setRuntimeCompanyApp(companyResponse.data)
      shipperCatalog.value = normalizeList(shipperResponse.data)
      syncSelectedShipper()
    } catch {
      publicCompanyConfig.value = null
      shipperCatalog.value = [{ code: 'kurly', name: '컬리', status: 'ACTIVE' }]
      syncSelectedShipper('kurly')
    } finally {
      companyConfigLoading.value = false
      redirectToAllowedTabIfNeeded()
    }
  },
  { immediate: true },
)

watch(
  selectedShipper,
  (shipper) => {
    setSelectedShipperCode(companyApp.value.code, shipper)
    redirectToAllowedTabIfNeeded()
  },
)

watch(
  [
    isOneShipperContext,
    enabledTabs,
    companyBase,
    () => route.path,
    () => route.query.one_tab,
  ],
  () => {
    redirectToAllowedTabIfNeeded()
  },
  { immediate: true },
)

watch(
  enabledShipperCodes,
  () => {
    syncSelectedShipper()
    redirectToAllowedTabIfNeeded()
  },
)

watch(
  () => route.fullPath,
  () => {
    inquiryDropdownOpen.value = false
  },
)

onMounted(() => {
  window.addEventListener('click', closeInquiryDropdown)
})

onBeforeUnmount(() => {
  if (inquiryPollTimer) clearInterval(inquiryPollTimer)
  window.removeEventListener('click', closeInquiryDropdown)
})
</script>

<style scoped>
.nav-link {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  border-radius: 0.75rem;
  padding: 0.75rem;
  color: #4b5563;
  transition: all 0.15s;
}

.nav-link:hover {
  background: #f9fafb;
  color: #111827;
}

.nav-link.active {
  background: #111827;
  color: #ffffff;
  box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.04);
}
</style>
