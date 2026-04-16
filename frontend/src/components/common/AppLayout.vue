<template>
  <div class="flex h-screen bg-bg">
    <!-- Sidebar -->
    <aside class="w-sidebar bg-white border-r border-gray-200 flex flex-col shadow-sm">
      <div class="p-5 border-b border-gray-200">
        <div class="flex items-center gap-3">
          <div class="w-10 h-10 bg-primary rounded-lg flex items-center justify-center">
            <span class="text-white font-bold">천하</span>
          </div>
          <div>
            <h1 class="text-lg font-bold text-text">천하운수</h1>
            <p class="text-xs text-gray-400">정산관리</p>
          </div>
        </div>
      </div>

      <nav class="flex-1 overflow-y-auto py-3">
        <ul class="px-3 space-y-1">
          <li v-for="item in visibleNavItems" :key="item.path">
            <RouterLink :to="item.path" class="nav-link" :class="{ 'active': route.path === item.path }">
              <span v-html="item.icon" class="w-5 h-5 flex-shrink-0"></span>
              <div class="flex-1">
                <span class="block">{{ item.label }}</span>
                <span class="block text-xs opacity-60">{{ item.desc }}</span>
              </div>
            </RouterLink>
          </li>
        </ul>
      </nav>

      <div class="p-3 border-t border-gray-200">
        <div class="px-3 py-2 mb-2 text-xs text-gray-400">
          {{ authStore.user?.username || '' }}
          <span class="ml-1 px-1.5 py-0.5 bg-gray-100 rounded">{{ authStore.isAdmin ? '관리자' : '팀장' }}</span>
        </div>
        <button @click="handleLogout"
          class="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-gray-500 hover:bg-gray-100 transition-colors">
          <span v-html="IconLogout" class="w-4 h-4"></span>
          <span>로그아웃</span>
        </button>
      </div>
    </aside>

    <div class="flex-1 flex flex-col min-w-0">
      <header class="bg-white border-b border-gray-200 px-8 py-4 flex items-center justify-between shadow-sm">
        <h2 class="text-xl font-bold text-text">{{ pageTitle }}</h2>
        <span class="text-gray-400">{{ currentDate }}</span>
      </header>
      <main class="flex-1 overflow-y-auto p-8 bg-gray-50">
        <slot></slot>
      </main>
    </div>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { formatDate } from '@/utils/format'
import { IconHome, IconDispatch, IconCrew, IconSettlement, IconRegion, IconLogout } from '@/utils/icons'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

const allNavItems = [
  { path: '/', label: '홈', desc: '현황 요약', icon: IconHome, admin: true },
  { path: '/dispatch', label: '배차 데이터', desc: '업로드 · 정산', icon: IconDispatch, admin: false },
  { path: '/crew', label: '배송원 관리', desc: '매니저 등록', icon: IconCrew, admin: false },
  { path: '/operations', label: '운영 현황', desc: '날짜별 현황', icon: IconDispatch, admin: false },
  { path: '/settlement', label: '정산 처리', desc: '정산 관리', icon: IconSettlement, admin: true },
  { path: '/inquiry', label: '정산 문의', desc: '문의/대화', icon: IconSettlement, admin: true },
  { path: '/region', label: '팀 관리', desc: '단가 설정', icon: IconRegion, admin: true },
]

const visibleNavItems = computed(() => {
  if (authStore.isAdmin) return allNavItems
  return allNavItems.filter(item => !item.admin)
})

const pageTitle = computed(() => {
  const titles = { '/': '대시보드', '/dispatch': '배차 데이터', '/crew': '배송원 관리', '/operations': '운영 현황', '/settlement': '정산 처리', '/inquiry': '정산 문의', '/region': '팀 관리' }
  return titles[route.path] || '천하운수'
})

const currentDate = ref(formatDate(new Date()))
const handleLogout = async () => { authStore.logout(); await router.push('/login') }
</script>

<style scoped>
.nav-link {
  display: flex; align-items: center; gap: 0.75rem;
  padding: 0.625rem 0.75rem; border-radius: 0.5rem;
  color: #666; transition: all 0.15s;
}
.nav-link:hover { background-color: #F5F5F5; color: #1A1A1A; }
.nav-link.active { background-color: #F4F7D6; color: #1A1A1A; font-weight: 500; }
</style>
