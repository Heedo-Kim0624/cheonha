<template>
  <div class="min-h-screen bg-slate-50 px-6 py-10 text-slate-900">
    <main class="mx-auto max-w-2xl rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
      <div class="mb-6">
        <p class="text-sm font-bold text-lime-600">CLEVER 관리자 회원가입</p>
        <h1 class="mt-1 text-2xl font-bold">{{ companyName }}</h1>
        <p class="mt-2 text-sm text-slate-500">
          회사명은 접속 주소 기준으로 자동 지정됩니다. 신청 후 대표자 계정의 승인 알림에서 승인되어야 로그인할 수 있습니다.
        </p>
      </div>

      <div v-if="loading" class="rounded-lg border border-slate-200 bg-slate-50 p-8 text-center text-slate-500">
        불러오는 중...
      </div>

      <form v-else class="space-y-5" @submit.prevent="submit">
        <div class="rounded-xl border border-slate-200 bg-slate-50 p-4">
          <p class="text-xs font-bold text-slate-500">회사</p>
          <p class="mt-1 text-lg font-extrabold text-slate-900">{{ companyName }}</p>
        </div>

        <label class="block">
          <span class="mb-2 block text-sm font-semibold text-slate-700">아이디</span>
          <input v-model.trim="form.username" required autocomplete="username" class="form-input" />
        </label>

        <div class="grid gap-4 md:grid-cols-2">
          <label class="block">
            <span class="mb-2 block text-sm font-semibold text-slate-700">비밀번호</span>
            <input v-model="form.password" type="password" required autocomplete="new-password" class="form-input" />
          </label>
          <label class="block">
            <span class="mb-2 block text-sm font-semibold text-slate-700">비밀번호 확인</span>
            <input v-model="form.password_confirm" type="password" required autocomplete="new-password" class="form-input" />
          </label>
        </div>

        <section class="rounded-xl border border-slate-200 bg-slate-50 p-4">
          <button type="button" class="mb-3 flex w-full items-center gap-3 rounded-lg bg-white p-3 text-left font-bold" @click="toggleAll">
            <input type="checkbox" :checked="allAgreed" readonly />
            <span>전체 동의</span>
          </button>

          <div class="space-y-2">
            <div
              v-for="agreement in agreements"
              :key="agreement.key"
              class="flex flex-wrap items-center justify-between gap-3 rounded-lg bg-white p-3"
            >
              <label class="flex min-w-0 flex-1 cursor-pointer items-center gap-3">
                <input v-model="form[agreement.key]" type="checkbox" />
                <span class="text-sm font-semibold text-slate-700">{{ agreement.label }}</span>
              </label>
              <a :href="agreement.url" target="_blank" rel="noreferrer" class="text-sm font-bold text-blue-600 underline">
                자세히
              </a>
            </div>
          </div>
        </section>

        <div v-if="notice" class="rounded-lg p-3 text-sm" :class="notice.type === 'success' ? 'bg-emerald-50 text-emerald-700' : 'bg-red-50 text-red-700'">
          {{ notice.message }}
        </div>

        <div class="grid gap-3 md:grid-cols-2">
          <RouterLink
            :to="loginPath"
            class="block rounded-lg border border-slate-300 bg-white px-4 py-3 text-center font-bold text-slate-700 hover:bg-slate-50"
          >
            로그인으로 돌아가기
          </RouterLink>
          <button type="submit" class="rounded-lg bg-lime-500 px-4 py-3 font-bold text-slate-900 hover:bg-lime-400 disabled:opacity-50" :disabled="saving || submitted">
            {{ saving ? '신청 중...' : submitted ? '신청 완료' : '회원가입 신청' }}
          </button>
        </div>
      </form>
    </main>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute } from 'vue-router'
import { fetchCompanyUserSignup, submitCompanyUserSignup } from '@/api/companyAdmin'
import { getCompanyAppFromRoute } from '@/utils/companyApp'

const route = useRoute()
const companyApp = computed(() => getCompanyAppFromRoute(route))
const companyCode = computed(() => company.value?.code || companyApp.value.code)
const companyName = computed(() => company.value?.name || companyApp.value.displayName)
const loginPath = computed(() => companyApp.value.loginPath)

const loading = ref(true)
const saving = ref(false)
const submitted = ref(false)
const notice = ref(null)
const company = ref(null)
const agreements = ref([])

const form = reactive({
  username: '',
  password: '',
  password_confirm: '',
  agree_terms: false,
  agree_privacy_policy: false,
  agree_location_terms: false,
  agree_data_processing: false,
  agree_marketing: false,
})

const requiredAgreements = computed(() => agreements.value.filter((item) => item.required))
const allAgreed = computed(() => agreements.value.length > 0 && agreements.value.every((item) => Boolean(form[item.key])))

function toggleAll() {
  const next = !allAgreed.value
  for (const agreement of agreements.value) {
    form[agreement.key] = next
  }
}

async function loadSignup() {
  loading.value = true
  notice.value = null
  submitted.value = false
  try {
    const response = await fetchCompanyUserSignup(companyApp.value.code)
    company.value = response.data.company
    agreements.value = response.data.agreements || []
  } catch (error) {
    notice.value = { type: 'error', message: error.response?.data?.detail || '회사 회원가입 정보를 불러오지 못했습니다.' }
  } finally {
    loading.value = false
  }
}

async function submit() {
  if (form.password !== form.password_confirm) {
    notice.value = { type: 'error', message: '비밀번호가 일치하지 않습니다.' }
    return
  }
  const missingRequired = requiredAgreements.value.some((item) => !form[item.key])
  if (missingRequired) {
    notice.value = { type: 'error', message: '필수 약관에 모두 동의해 주세요.' }
    return
  }
  saving.value = true
  notice.value = null
  try {
    const response = await submitCompanyUserSignup(companyCode.value, { ...form })
    submitted.value = true
    notice.value = { type: 'success', message: response.data.detail || '회원가입 신청이 완료되었습니다.' }
  } catch (error) {
    notice.value = {
      type: 'error',
      message:
        error.response?.data?.detail ||
        error.response?.data?.username?.[0] ||
        error.response?.data?.password?.[0] ||
        '회원가입 신청에 실패했습니다.',
    }
  } finally {
    saving.value = false
  }
}

onMounted(loadSignup)
</script>

<style scoped>
.form-input {
  width: 100%;
  border: 1px solid #cbd5e1;
  border-radius: 10px;
  padding: 12px 14px;
  outline: none;
}

.form-input:focus {
  border-color: #84cc16;
  box-shadow: 0 0 0 3px rgba(132, 204, 22, 0.18);
}
</style>
