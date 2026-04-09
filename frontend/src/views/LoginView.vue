<template>
  <div class="flex h-screen">
    <div class="w-1/2 bg-gradient-to-br from-gray-800 to-gray-700 flex flex-col items-center justify-center p-8">
      <div class="text-center space-y-4">
        <h1 class="text-4xl font-bold text-white">천하운수</h1>
        <p class="text-gray-300 text-lg">정산관리 시스템</p>
      </div>
    </div>

    <div class="w-1/2 bg-white flex flex-col items-center justify-center p-8">
      <div class="w-full max-w-md space-y-8">
        <!-- 탭 -->
        <div class="flex gap-4 justify-center">
          <button @click="mode = 'login'" class="px-6 py-2 rounded-lg font-bold transition-all"
            :class="mode === 'login' ? 'bg-primary text-white' : 'text-gray-400 hover:text-gray-600'">로그인</button>
          <button @click="mode = 'signup'" class="px-6 py-2 rounded-lg font-bold transition-all"
            :class="mode === 'signup' ? 'bg-primary text-white' : 'text-gray-400 hover:text-gray-600'">회원가입</button>
        </div>

        <!-- 로그인 -->
        <form v-if="mode === 'login'" @submit.prevent="handleLogin" class="space-y-5">
          <div>
            <label class="block font-medium text-text mb-2">아이디</label>
            <input v-model="email" type="text" placeholder="아이디 입력"
              class="w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary" required />
          </div>
          <div>
            <label class="block font-medium text-text mb-2">비밀번호</label>
            <input v-model="password" type="password" placeholder="비밀번호 입력"
              class="w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary" required />
          </div>
          <div v-if="errorMessage" class="p-3 bg-red-50 text-danger rounded-lg">{{ errorMessage }}</div>
          <button type="submit" :disabled="isLoading"
            class="w-full py-3 bg-primary text-white font-bold rounded-lg hover:opacity-90 disabled:opacity-50">
            {{ isLoading ? '로그인 중...' : '로그인' }}
          </button>
        </form>

        <!-- 회원가입 (팀장) -->
        <form v-if="mode === 'signup'" @submit.prevent="handleSignup" class="space-y-5">
          <div>
            <label class="block font-medium text-text mb-2">아이디</label>
            <input v-model="signupForm.username" type="text" placeholder="아이디"
              class="w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary" required />
          </div>
          <div>
            <label class="block font-medium text-text mb-2">이름</label>
            <input v-model="signupForm.name" type="text" placeholder="실명"
              class="w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary" required />
          </div>
          <div>
            <label class="block font-medium text-text mb-2">소속 팀</label>
            <select v-model="signupForm.team_code"
              class="w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary" required>
              <option value="">팀 선택</option>
              <option v-for="t in availableTeams" :key="t.id" :value="t.code">{{ t.name }} ({{ t.code }})</option>
            </select>
          </div>
          <div>
            <label class="block font-medium text-text mb-2">비밀번호</label>
            <input v-model="signupForm.password" type="password" placeholder="8자 이상"
              class="w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary" required />
          </div>
          <div>
            <label class="block font-medium text-text mb-2">비밀번호 확인</label>
            <input v-model="signupForm.password_confirm" type="password" placeholder="비밀번호 재입력"
              class="w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary" required />
          </div>
          <div v-if="signupMessage" class="p-3 rounded-lg" :class="signupSuccess ? 'bg-green-50 text-green-700' : 'bg-red-50 text-danger'">
            {{ signupMessage }}
          </div>
          <button type="submit" :disabled="isLoading"
            class="w-full py-3 bg-primary text-white font-bold rounded-lg hover:opacity-90 disabled:opacity-50">
            {{ isLoading ? '처리 중...' : '회원가입 (관리자 승인 필요)' }}
          </button>
        </form>
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
  } catch (e) {
    availableTeams.value = []
  }
}

const handleLogin = async () => {
  isLoading.value = true; errorMessage.value = ''
  try {
    await authStore.login(email.value, password.value)
    await router.push(authStore.isAdmin ? '/' : '/dispatch')
  } catch (e) {
    errorMessage.value = e.response?.data?.detail || '로그인 실패'
  } finally { isLoading.value = false }
}

const handleSignup = async () => {
  if (signupForm.password !== signupForm.password_confirm) {
    signupMessage.value = '비밀번호가 일치하지 않습니다'; signupSuccess.value = false; return
  }
  isLoading.value = true; signupMessage.value = ''
  try {
    await client.post('/accounts/signup/', {
      username: signupForm.username,
      first_name: signupForm.name,
      password: signupForm.password,
      password_confirm: signupForm.password_confirm,
      team_code: signupForm.team_code,
    })
    signupMessage.value = '회원가입이 완료되었습니다. 관리자 승인 후 로그인 가능합니다.'
    signupSuccess.value = true
  } catch (e) {
    signupMessage.value = e.response?.data?.detail || e.response?.data?.username?.[0] || '회원가입 실패'
    signupSuccess.value = false
  } finally { isLoading.value = false }
}

onMounted(loadTeams)
</script>
