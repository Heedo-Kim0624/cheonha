<template>
  <AppLayout>
    <div class="space-y-6">
      <!-- Header + Filter -->
      <div class="flex items-center justify-between">
        <h2 class="text-xl font-bold text-text">배송원 관리</h2>
        <select v-if="authStore.isAdmin" v-model="selectedTeam"
          class="px-4 py-3 border border-gray-300 rounded-lg focus:border-primary outline-none bg-white min-w-[140px]">
          <option value="">전체</option>
          <option v-for="t in teamList" :key="t.id" :value="t.code">{{ t.name }}</option>
        </select>
      </div>

      <!-- Search -->
      <div>
        <input v-model="searchQuery" type="text" placeholder="이름, 코드, 전화번호 검색..."
          class="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary outline-none" />
      </div>

      <!-- 팀 미배정 안내 -->
      <div v-if="!authStore.isAdmin && !authStore.user?.team" class="bg-amber-50 rounded-xl p-8 border border-amber-200 text-center">
        <p class="text-lg font-medium text-amber-700 mb-2">소속 팀이 배정되지 않았습니다</p>
        <p class="text-amber-600">관리자에게 팀 배정을 요청하세요.</p>
      </div>

      <div v-else-if="crewStore.loading" class="text-center py-8 text-gray-500">불러오는 중...</div>

      <div v-else class="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <table class="w-full">
          <thead class="bg-gray-50 border-b border-gray-200">
            <tr>
              <th class="px-5 py-3 text-left font-semibold text-gray-600">코드</th>
              <th class="px-5 py-3 text-left font-semibold text-gray-600">이름</th>
              <th class="px-5 py-3 text-left font-semibold text-gray-600">전화번호</th>
              <th class="px-5 py-3 text-left font-semibold text-gray-600">차량번호</th>
              <th class="px-5 py-3 text-center font-semibold text-gray-600">관리</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="member in filteredCrew" :key="member.id" class="border-b border-gray-100 hover:bg-gray-50">
              <td class="px-5 py-4 font-mono">{{ member.code }}</td>
              <td class="px-5 py-4 font-bold text-text">{{ member.name }}</td>
              <td class="px-5 py-4">{{ member.phone || '-' }}</td>
              <td class="px-5 py-4">{{ member.vehicle_number || '-' }}</td>
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
              <td colspan="5" class="px-5 py-12 text-center text-gray-400">배송원이 없습니다.</td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- Edit Modal -->
      <div v-if="showEditModal" class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
        <div class="bg-white rounded-xl p-6 w-full max-w-md">
          <h3 class="text-xl font-bold text-text mb-5">배송원 수정</h3>
          <div class="space-y-4">
            <div>
              <label class="block text-gray-500 mb-2">코드</label>
              <input :value="crewForm.code" type="text" disabled
                class="w-full px-4 py-3 border border-gray-200 rounded-lg bg-gray-50 text-gray-500" />
            </div>
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
import { ref, computed, reactive, onMounted } from 'vue'
import { useCrewStore } from '@/stores/crew'
import { useAuthStore } from '@/stores/auth'
import AppLayout from '@/components/common/AppLayout.vue'
import client from '@/api/client'

const authStore = useAuthStore()
const crewStore = useCrewStore()
const searchQuery = ref('')
const selectedTeam = ref('')
const teamList = ref([])
const showEditModal = ref(false)
const editingId = ref(null)
const crewForm = reactive({ code: '', name: '', phone: '', vehicle_number: '' })

const filteredCrew = computed(() => {
  let list = crewStore.crewMembers.filter(m => !m.is_new)
  if (selectedTeam.value) {
    list = list.filter(m => m.team_code === selectedTeam.value || m.team_name === selectedTeam.value + '조')
  }
  if (searchQuery.value) {
    const q = searchQuery.value.toLowerCase()
    list = list.filter(m =>
      (m.name && m.name.toLowerCase().includes(q)) ||
      (m.code && m.code.toLowerCase().includes(q)) ||
      (m.phone && m.phone.includes(q))
    )
  }
  return list
})

const loadTeams = async () => {
  try {
    const resp = await client.get('/accounts/teams')
    teamList.value = resp.data.results || resp.data || []
  } catch (e) {}
}

const editCrew = (member) => {
  editingId.value = member.id
  crewForm.code = member.code || ''
  crewForm.name = member.name || ''
  crewForm.phone = member.phone || ''
  crewForm.vehicle_number = member.vehicle_number || ''
  showEditModal.value = true
}

const submitEditCrew = async () => {
  try {
    await crewStore.updateCrew(editingId.value, {
      name: crewForm.name, phone: crewForm.phone, vehicle_number: crewForm.vehicle_number
    })
    showEditModal.value = false
  } catch (err) { alert('수정 실패') }
}

const deleteCrew = async (member) => {
  if (!confirm(`${member.name}을(를) 삭제하시겠습니까?`)) return
  try {
    await crewStore.removeCrew(member.id)
  } catch (err) { alert('삭제 실패') }
}

onMounted(() => { crewStore.fetchCrew(); loadTeams() })
</script>
