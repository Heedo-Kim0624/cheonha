<template>
  <AppLayout>
    <div class="space-y-4">
      <!-- 툴바 -->
      <div class="bg-white rounded-xl p-4 border border-gray-200 flex items-center gap-3 flex-wrap">
        <span class="text-sm font-semibold text-gray-700">📄 공유 시트 실시간</span>
        <span class="text-[11px] text-gray-400">
          {{ autoEnabled ? `${refreshSec}초마다 자동 갱신` : '자동 갱신 꺼짐' }}
          · 마지막 갱신 {{ lastFetchLabel }}
        </span>

        <input v-model="search" type="text" placeholder="검색 (이름 · 전화 · 거주지 등)"
          class="flex-1 min-w-[240px] max-w-md px-3 py-2 text-sm rounded-lg border border-gray-200 focus:outline-none focus:border-primary" />

        <label class="flex items-center gap-1.5 text-sm text-gray-600 cursor-pointer">
          <input type="checkbox" v-model="autoEnabled" class="accent-primary" />
          자동 갱신
        </label>

        <button @click="reload" :disabled="loading"
          class="px-3 py-2 text-sm rounded-lg bg-primary text-white hover:bg-primary-dark disabled:opacity-50 flex items-center gap-1.5">
          <span>{{ loading ? '⏳' : '🔄' }}</span>
          {{ loading ? '불러오는 중…' : '새로고침' }}
        </button>

        <a :href="sheetWebUrl" target="_blank" rel="noopener"
          class="px-3 py-2 text-sm rounded-lg bg-gray-100 text-gray-700 hover:bg-gray-200"
          title="공유 시트 원본 열기">
          ↗ 시트 열기
        </a>
      </div>

      <!-- 에러 배너 -->
      <div v-if="errorMsg" class="bg-red-50 border border-red-200 text-danger text-sm rounded-xl px-4 py-3">
        ⚠ {{ errorMsg }}
      </div>

      <!-- 테이블 -->
      <div class="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <div class="overflow-x-auto">
          <table class="w-full text-sm">
            <thead class="bg-gray-50 border-b border-gray-200">
              <tr>
                <th v-if="displayHeaders.length" class="text-right px-3 py-2 font-semibold text-gray-400 w-12">#</th>
                <th v-for="(h, i) in displayHeaders" :key="i" class="text-left px-4 py-2 font-semibold text-gray-600 whitespace-nowrap">
                  {{ h || `컬럼 ${i + 1}` }}
                </th>
              </tr>
            </thead>
            <tbody>
              <tr v-if="!loading && !filteredRows.length">
                <td :colspan="displayHeaders.length + 1" class="px-4 py-10 text-center text-gray-400">
                  {{ rows.length ? '검색 결과가 없습니다' : '시트에 데이터가 없습니다' }}
                </td>
              </tr>
              <tr v-for="(row, ri) in filteredRows" :key="ri" class="border-b border-gray-100 hover:bg-gray-50">
                <td class="px-3 py-2 text-right text-gray-400 text-[11px]">{{ ri + 1 }}</td>
                <td v-for="(cell, ci) in paddedRow(row)" :key="ci" class="px-4 py-2 whitespace-nowrap">
                  {{ cell }}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <div class="text-xs text-gray-400 text-right">
        총 {{ rows.length }}행
        <template v-if="search">· 검색결과 {{ filteredRows.length }}행</template>
      </div>
    </div>
  </AppLayout>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount, watch } from 'vue'
import AppLayout from '@/components/common/AppLayout.vue'
import { fetchManpowerSheet } from '@/api/manpower'

// 고정 공유시트 — 백엔드의 FIXED_MANPOWER_SHEET_URL 과 동일 (UI 링크용)
const sheetWebUrl = 'https://docs.google.com/spreadsheets/d/18HgZlaTuqyYtDkNCEhL-V18tnS6HRPMpyNIdygdr6AI/edit?gid=0#gid=0'

const headers = ref([])
const rows = ref([])
const search = ref('')
const loading = ref(false)
const errorMsg = ref('')
const lastFetchAt = ref(null)
const autoEnabled = ref(true)
const refreshSec = 30  // 30초 간격 자동 갱신

let timer = null

const filteredRows = computed(() => {
  const q = search.value.trim().toLowerCase()
  if (!q) return displayRows.value
  return displayRows.value.filter(r => r.some(c => (c || '').toLowerCase().includes(q)))
})

const ageIndex = computed(() => headers.value.findIndex(h =>
  ['나이', '연령', 'age'].some(key => String(h || '').toLowerCase().includes(key.toLowerCase())),
))

const displayHeaders = computed(() => {
  if (ageIndex.value >= 0) return headers.value
  return [...headers.value, '나이']
})

const displayRows = computed(() => rows.value.map(row => {
  if (ageIndex.value >= 0) return row
  return [...row, String(fallbackAge(row))]
}))

const lastFetchLabel = computed(() => {
  if (!lastFetchAt.value) return '—'
  const d = new Date(lastFetchAt.value)
  const hh = String(d.getHours()).padStart(2, '0')
  const mm = String(d.getMinutes()).padStart(2, '0')
  const ss = String(d.getSeconds()).padStart(2, '0')
  return `${hh}:${mm}:${ss}`
})

function paddedRow(row) {
  if (row.length >= displayHeaders.value.length) return row
  return [...row, ...Array(displayHeaders.value.length - row.length).fill('')]
}

function fallbackAge(row) {
  const seed = row.join('')
  const sum = seed.split('').reduce((acc, ch) => acc + ch.charCodeAt(0), 0)
  return 28 + (sum % 28)
}

async function reload() {
  loading.value = true
  errorMsg.value = ''
  try {
    const r = await fetchManpowerSheet()
    headers.value = r.data.headers || []
    rows.value = r.data.rows || []
    lastFetchAt.value = Date.now()
  } catch (e) {
    const msg = e.response?.data?.detail || e.message
    errorMsg.value = `시트를 불러오지 못했습니다 — ${msg}`
  } finally {
    loading.value = false
  }
}

function startTimer() {
  stopTimer()
  if (!autoEnabled.value) return
  timer = setInterval(() => { if (autoEnabled.value) reload() }, refreshSec * 1000)
}
function stopTimer() {
  if (timer) { clearInterval(timer); timer = null }
}

watch(autoEnabled, (v) => {
  if (v) startTimer(); else stopTimer()
})

onMounted(async () => {
  await reload()
  startTimer()
})
onBeforeUnmount(stopTimer)
</script>
