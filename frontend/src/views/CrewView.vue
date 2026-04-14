<template>
  <AppLayout>
    <div class="space-y-6">
      <div class="flex items-center justify-between">
        <h2 class="text-xl font-bold text-text">배송원 관리</h2>
      </div>
      <TeamFilter v-if="authStore.isAdmin" v-model="selectedTeamName" />

      <div>
        <input v-model="searchQuery" type="text" placeholder="이름, 코드, 전화번호 검색..."
          class="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary outline-none" />
      </div>

      <div v-if="!authStore.isAdmin && !authStore.user?.team" class="bg-amber-50 rounded-xl p-8 border border-amber-200 text-center">
        <p class="text-lg font-medium text-amber-700 mb-2">소속 팀이 배정되지 않았습니다</p>
        <p class="text-amber-600">관리자에게 팀 배정을 요청하세요.</p>
      </div>

      <div v-else-if="crewStore.loading" class="text-center py-8 text-gray-500">불러오는 중...</div>

      <div v-else class="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <table class="w-full">
          <thead class="bg-gray-50 border-b border-gray-200">
            <tr>
              <th class="px-5 py-3 text-left font-semibold text-gray-600">이름</th>
              <th class="px-5 py-3 text-left font-semibold text-gray-600">조</th>
              <th class="px-5 py-3 text-left font-semibold text-gray-600">전화번호</th>
              <th class="px-5 py-3 text-left font-semibold text-gray-600">차량번호</th>
              <th class="px-5 py-3 text-right font-semibold text-orange-600">지급단가(박스당)</th>
              <th class="px-5 py-3 text-center font-semibold text-gray-600">관리</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="member in paginatedCrew" :key="member.id" class="border-b border-gray-100 hover:bg-gray-50">
              <td class="px-5 py-4 font-bold text-text">{{ member.name }}</td>
              <td class="px-5 py-4">
                <span class="px-2 py-0.5 bg-primary-light text-primary-dark rounded font-medium">{{ member.team_name || '-' }}</span>
              </td>
              <td class="px-5 py-4">{{ member.phone || '-' }}</td>
              <td class="px-5 py-4">{{ member.vehicle_number || '-' }}</td>
              <td class="px-5 py-4 text-right text-orange-700 font-bold">{{ Number(member.pay_price || 0).toLocaleString() }}원</td>
              <td class="px-5 py-4 text-center">
                <div class="flex justify-center gap-2">
                  <button @click="editCrew(member)"
                    class="px-4 py-2 bg-primary text-white rounded-lg font-medium hover:opacity-90">수정</button>
                  <button @click="deleteCrew(member)"
                    class="px-4 py-2 bg-red-500 text-white rounded-lg font-medium hover:opacity-90">삭제</button>
                </div>
              </td>
            </tr>
            <tr v-if="filteredCrew.length === 0">
              <td colspan="6" class="px-5 py-12 text-center text-gray-400">배송원이 없습니다.</td>
            </tr>
          </tbody>
        </table>

        <div v-if="totalPages > 1" class="flex items-center justify-between px-5 py-4 border-t border-gray-200">
          <span class="text-gray-500">총 {{ filteredCrew.length }}명 ({{ currentPage }}/{{ totalPages }}페이지)</span>
          <div class="flex gap-2">
            <button @click="currentPage = Math.max(1, currentPage - 1)" :disabled="currentPage === 1"
              class="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-30">이전</button>
            <button v-for="p in visiblePages" :key="p" @click="currentPage = p"
              class="px-4 py-2 rounded-lg font-medium"
              :class="p === currentPage ? 'bg-primary text-white' : 'border border-gray-300 hover:bg-gray-50'">{{ p }}</button>
            <button @click="currentPage = Math.min(totalPages, currentPage + 1)" :disabled="currentPage === totalPages"
              class="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-30">다음</button>
          </div>
        </div>
      </div>

      <div v-if="showEditModal" class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
        <div class="bg-white rounded-xl p-6 w-full max-w-md">
          <h3 class="text-xl font-bold text-text mb-5">배송원 수정</h3>
          <div class="space-y-4">
            <div>
              <label class="block text-gray-500 mb-2">이름</label>
              <input v-model="crewForm.name" type="text"
                class="w-full px-4 py-3 border border-gray-300 rounded-lg focus:border-primary outline-none" />
            </div>
            <div>
              <label class="block text-gray-500 mb-2">전화번호</label>
              <input v-model="crewForm.phone" type="tel" placeholder="010-0000-0000"
                class="w-full px-4 py-3 border border-gray-300 rounded-lg focus:border-primary outline-none" />
            </div>
            <div>
              <label class="block text-gray-500 mb-2">차량번호</label>
              <input v-model="crewForm.vehicle_number" type="text" placeholder="12가3456"
                class="w-full px-4 py-3 border border-gray-300 rounded-lg focus:border-primary outline-none" />
            </div>
            <div>
              <label class="block text-orange-600 font-medium mb-2">지급단가 (박스당)</label>
              <input v-model.number="crewForm.pay_price" type="number" placeholder="0" min="0"
                class="w-full px-4 py-3 border border-orange-300 rounded-lg text-right text-lg bg-orange-50 focus:border-orange-400 outline-none" />
            </div>
          </div>
          <div class="flex justify-end gap-3 mt-6">
            <button @click="showEditModal = false"
              class="px-5 py-3 border border-gray-300 rounded-lg hover:bg-gray-50">취소</button>
            <button @click="submitEditCrew"
              class="px-5 py-3 bg-primary text-white rounded-lg font-medium hover:opacity-90">저장</button>
          </div>
        </div>
      </div>
    </div>
  </AppLayout>
</template>

<script setup>
import { ref, computed, reactive, onMounted, watch } from 'vue'
import { useCrewStore } from '@/stores/crew'
import { useAuthStore } from '@/stores/auth'
import AppLayout from '@/components/common/AppLayout.vue'
import TeamFilter from '@/components/common/TeamFilter.vue'
import client from '@/api/client'

const authStore = useAuthStore()
const crewStore = useCrewStore()
const searchQuery = ref('')
const selectedTeamName = ref('')
const showEditModal = ref(false)
const editingId = ref(null)
const crewForm = reactive({ name: '', phone: '', vehicle_number: '', pay_price: 0 })
const originalPayPrice = ref(0)
const currentPage = ref(1)
const pageSize = 20

const filteredCrew = computed(() => {
  let list = crewStore.crewMembers.filter(m => !m.is_new)
  if (selectedTeamName.value) list = list.filter(m => m.team_name === selectedTeamName.value)
  if (searchQuery.value) {
    const q = searchQuery.value.toLowerCase()
    list = list.filter(m => (m.name && m.name.toLowerCase().includes(q)) || (m.code && m.code.toLowerCase().includes(q)) || (m.phone && m.phone.includes(q)))
  }
  return list
})

// 검색/필터 변경 시 1페이지로
watch([searchQuery, selectedTeamName], () => { currentPage.value = 1 })

const totalPages = computed(() => Math.ceil(filteredCrew.value.length / pageSize) || 1)
const paginatedCrew = computed(() => {
  const s = (currentPage.value - 1) * pageSize
  return filteredCrew.value.slice(s, s + pageSize)
})
const visiblePages = computed(() => {
  const pages = []
  const start = Math.max(1, currentPage.value - 2)
  for (let i = start; i <= Math.min(totalPages.value, start + 4); i++) pages.push(i)
  return pages
})

const editCrew = (m) => {
  editingId.value = m.id
  crewForm.name = m.name || ''; crewForm.phone = m.phone || ''
  crewForm.vehicle_number = m.vehicle_number || ''; crewForm.pay_price = Number(m.pay_price || 0)
  originalPayPrice.value = Number(m.pay_price || 0)
  showEditModal.value = true
}

const submitEditCrew = async () => {
  try {
    const result = await crewStore.updateCrew(editingId.value, {
      name: crewForm.name, phone: crewForm.phone,
      vehicle_number: crewForm.vehicle_number, pay_price: crewForm.pay_price || 0
    })

    // 지급단가가 변경됐으면 기존 정산 재계산 여부 확인
    if (Number(crewForm.pay_price) !== Number(originalPayPrice.value)) {
      if (confirm('지급 단가가 변경되었습니다.\n기존 정산에도 적용하시겠습니까?')) {
        try {
          await client.post(`/crew/members/${editingId.value}/recalc_settlements/`)
        } catch (e) { /* 정산 없으면 무시 */ }
      }
    }

    showEditModal.value = false
  } catch (err) {
    console.error('수정 에러:', err, err?.response?.data)
    alert('수정 실패: ' + (err?.response?.data ? JSON.stringify(err.response.data) : err.message))
  }
}

const deleteCrew = async (m) => {
  if (!confirm(`${m.name}을(를) 삭제하시겠습니까?`)) return
  try { await crewStore.removeCrew(m.id) } catch (err) { alert('삭제 실패') }
}

onMounted(() => { crewStore.fetchCrew() })
</script>
