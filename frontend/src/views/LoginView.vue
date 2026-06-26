<template>
  <div class="flex min-h-screen">
    <div class="hidden w-1/2 bg-gradient-to-br from-gray-800 to-gray-700 md:flex md:flex-col md:items-center md:justify-center md:p-8">
      <div class="space-y-4 text-center">
        <h1 class="text-4xl font-bold text-white">CLEVER {{ companyApp.displayName }}</h1>
        <p class="text-lg text-gray-300">운영, 배차, 정산을 관리하는 정산관리 시스템</p>
      </div>
    </div>

    <div class="flex w-full flex-col items-center justify-center bg-white p-8 md:w-1/2">
      <div class="w-full max-w-md space-y-8">
        <div class="space-y-2 text-center md:hidden">
          <h1 class="text-3xl font-bold text-text">CLEVER {{ companyApp.displayName }}</h1>
          <p class="text-sm text-gray-500">정산관리 시스템</p>
        </div>

        <form class="space-y-5" @submit.prevent="handleLogin">
          <div>
            <label class="mb-2 block font-medium text-text">아이디</label>
            <input
              v-model="email"
              type="text"
              placeholder="아이디 입력"
              class="w-full rounded-lg border border-gray-300 px-4 py-3 focus:outline-none focus:ring-2 focus:ring-primary"
              required
            />
          </div>
          <div>
            <label class="mb-2 block font-medium text-text">비밀번호</label>
            <input
              v-model="password"
              type="password"
              placeholder="비밀번호 입력"
              class="w-full rounded-lg border border-gray-300 px-4 py-3 focus:outline-none focus:ring-2 focus:ring-primary"
              required
            />
          </div>
          <div v-if="errorMessage" class="rounded-lg bg-red-50 p-3 text-danger">{{ errorMessage }}</div>
          <button
            type="submit"
            :disabled="isLoading"
            class="w-full rounded-lg bg-primary py-3 font-bold text-white hover:opacity-90 disabled:opacity-50"
          >
            {{ isLoading ? '로그인 중...' : '로그인' }}
          </button>
          <RouterLink
            :to="signupPath"
            class="block w-full rounded-lg border border-primary px-4 py-3 text-center font-bold text-primary hover:bg-primary-light"
          >
            회원가입
          </RouterLink>
        </form>

        <div class="pt-2 text-center">
          <a
            href="/privacy/"
            target="_blank"
            rel="noreferrer"
            class="text-sm text-[#2a6db0] underline"
          >
            개인정보처리방침
          </a>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ref } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { getCompanyAppFromRoute } from '@/utils/companyApp'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
const companyApp = computed(() => getCompanyAppFromRoute(route))

const email = ref('')
const password = ref('')
const isLoading = ref(false)
const errorMessage = ref('')

const adminLandingPath = computed(() => (
  companyApp.value.enabledTabs?.includes('dashboard')
    ? companyApp.value.dashboardPath
    : companyApp.value.dispatchPath
))
const signupPath = computed(() => `${companyApp.value.routeBase}/signup`)

const handleLogin = async () => {
  isLoading.value = true
  errorMessage.value = ''
  try {
    await authStore.login(email.value, password.value)
    await router.push(authStore.isAdmin ? adminLandingPath.value : companyApp.value.dispatchPath)
  } catch (e) {
    errorMessage.value = e.response?.data?.detail || '로그인에 실패했습니다.'
  } finally {
    isLoading.value = false
  }
}
</script>
