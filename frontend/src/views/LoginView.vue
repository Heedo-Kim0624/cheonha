<template>
  <div class="flex min-h-screen">
    <div class="hidden w-1/2 bg-gradient-to-br from-gray-800 to-gray-700 md:flex md:flex-col md:items-center md:justify-center md:p-8">
      <div class="space-y-4 text-center">
        <h1 class="text-4xl font-bold text-white">CLEVER_CH</h1>
        <p class="text-lg text-gray-300">천하운수 정산관리 서비스</p>
      </div>
    </div>

    <div class="flex w-full flex-col items-center justify-center bg-white p-8 md:w-1/2">
      <div class="w-full max-w-md space-y-8">
        <div class="flex justify-center gap-4">
          <button
            @click="mode = 'login'"
            class="rounded-lg px-6 py-2 font-bold transition-all"
            :class="mode === 'login' ? 'bg-primary text-white' : 'text-gray-400 hover:text-gray-600'"
          >
            로그인
          </button>
          <button
            @click="mode = 'signup'"
            class="rounded-lg px-6 py-2 font-bold transition-all"
            :class="mode === 'signup' ? 'bg-primary text-white' : 'text-gray-400 hover:text-gray-600'"
          >
            회원가입
          </button>
        </div>

        <form v-if="mode === 'login'" @submit.prevent="handleLogin" class="space-y-5">
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
        </form>

        <form v-if="mode === 'signup'" @submit.prevent="handleSignup" class="space-y-5">
          <div>
            <label class="mb-2 block font-medium text-text">아이디</label>
            <input
              v-model="signupForm.username"
              type="text"
              placeholder="아이디"
              class="w-full rounded-lg border border-gray-300 px-4 py-3 focus:outline-none focus:ring-2 focus:ring-primary"
              required
            />
          </div>
          <div>
            <label class="mb-2 block font-medium text-text">이름</label>
            <input
              v-model="signupForm.name"
              type="text"
              placeholder="이름"
              class="w-full rounded-lg border border-gray-300 px-4 py-3 focus:outline-none focus:ring-2 focus:ring-primary"
              required
            />
          </div>
          <div>
            <label class="mb-2 block font-medium text-text">소속 조</label>
            <select
              v-model="signupForm.team_code"
              class="w-full rounded-lg border border-gray-300 px-4 py-3 focus:outline-none focus:ring-2 focus:ring-primary"
              required
            >
              <option value="">조 선택</option>
              <option v-for="t in availableTeams" :key="t.id" :value="t.code">{{ t.name }} ({{ t.code }})</option>
            </select>
          </div>
          <div>
            <label class="mb-2 block font-medium text-text">비밀번호</label>
            <input
              v-model="signupForm.password"
              type="password"
              placeholder="8자 이상"
              class="w-full rounded-lg border border-gray-300 px-4 py-3 focus:outline-none focus:ring-2 focus:ring-primary"
              required
            />
          </div>
          <div>
            <label class="mb-2 block font-medium text-text">비밀번호 확인</label>
            <input
              v-model="signupForm.password_confirm"
              type="password"
              placeholder="비밀번호 재입력"
              class="w-full rounded-lg border border-gray-300 px-4 py-3 focus:outline-none focus:ring-2 focus:ring-primary"
              required
            />
          </div>
          <div
            v-if="signupMessage"
            class="rounded-lg p-3"
            :class="signupSuccess ? 'bg-green-50 text-green-700' : 'bg-red-50 text-danger'"
          >
            {{ signupMessage }}
          </div>
          <button
            type="submit"
            :disabled="isLoading"
            class="w-full rounded-lg bg-primary py-3 font-bold text-white hover:opacity-90 disabled:opacity-50"
          >
            {{ isLoading ? '처리 중...' : '회원가입 (관리자 확인 필요)' }}
          </button>
        </form>

        <div class="pt-2 text-center">
          <a href="/privacy" target="_blank" rel="noreferrer" class="text-sm text-[#2a6db0] underline">
            개인정보처리방침
          </a>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import client from '@/api/client'

const router = useRouter()
const authStore = useAuthStore()

const mode = ref('login')
const email = ref('')
const password = ref('')
const isLoading = ref(false)
const errorMessage = ref('')

const signupForm = reactive({ username: '', name: '', team_code: '', password: '', password_confirm: '' })
const signupMessage = ref('')
const signupSuccess = ref(false)
const availableTeams = ref([])

const loadTeams = async () => {
  try {
    const resp = await client.get('/accounts/teams/')
    availableTeams.value = resp.data.results || resp.data || []
  } catch {
    availableTeams.value = []
  }
}

const handleLogin = async () => {
  isLoading.value = true
  errorMessage.value = ''
  try {
    await authStore.login(email.value, password.value)
    await router.push(authStore.isAdmin ? '/' : '/dispatch')
  } catch (e) {
    errorMessage.value = e.response?.data?.detail || '로그인에 실패했습니다.'
  } finally {
    isLoading.value = false
  }
}

const handleSignup = async () => {
  if (signupForm.password !== signupForm.password_confirm) {
    signupMessage.value = '비밀번호가 일치하지 않습니다.'
    signupSuccess.value = false
    return
  }
  isLoading.value = true
  signupMessage.value = ''
  try {
    await client.post('/accounts/signup/', {
      username: signupForm.username,
      first_name: signupForm.name,
      password: signupForm.password,
      password_confirm: signupForm.password_confirm,
      team_code: signupForm.team_code,
    })
    signupMessage.value = '회원가입이 완료되었습니다. 관리자 확인 후 로그인할 수 있습니다.'
    signupSuccess.value = true
  } catch (e) {
    signupMessage.value =
      e.response?.data?.detail ||
      e.response?.data?.username?.[0] ||
      '회원가입에 실패했습니다.'
    signupSuccess.value = false
  } finally {
    isLoading.value = false
  }
}

onMounted(loadTeams)
</script>
