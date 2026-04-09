<template>
  <AppLayout>
    <div class="space-y-6">
      <!-- 팀 생성 -->
      <div class="flex items-center justify-between">
        <h3 class="text-xl font-bold text-text">팀 관리</h3>
        <button @click="showCreateModal = true"
          class="px-5 py-3 bg-primary text-white rounded-lg font-medium hover:opacity-90">
          + 팀 생성
        </button>
      </div>

      <!-- 팀 목록 -->
      <div v-if="teams.length === 0" class="bg-white rounded-xl p-12 border border-gray-200 text-center text-gray-400">
        <p class="text-5xl mb-4">&#128101;</p>
        <p class="text-lg font-medium mb-1">등록된 팀이 없습니다</p>
        <p>팀을 생성하여 단가를 설정하세요.</p>
      </div>

      <div v-for="team in teams" :key="team.id"
        class="bg-white rounded-xl p-6 border border-gray-200">
        <div class="flex items-center gap-4 mb-5">
          <div class="w-12 h-12 bg-primary-light rounded-full flex items-center justify-center">
            <span class="text-primary-dark text-lg font-bold">{{ team.code }}</span>
          </div>
          <div>
            <p class="text-xl font-bold text-text">{{ team.name }}</p>
            <p class="text-gray-400">코드: {{ team.code }}</p>
          </div>
        </div>

        <div class="grid grid-cols-3 gap-5 mb-4">
          <div>
            <label class="block text-gray-500 mb-2">수신단가 (박스당)</label>
            <input v-model.number="team._receive_price" type="number" placeholder="0"
              class="w-full px-4 py-3 border border-blue-200 rounded-lg text-right text-lg bg-blue-50 focus:border-blue-400 outline-none" />
          </div>
          <div>
            <label class="block text-gray-500 mb-2">지급단가 (박스당)</label>
            <input v-model.number="team._pay_price" type="number" placeholder="0"
              class="w-full px-4 py-3 border border-orange-200 rounded-lg text-right text-lg bg-orange-50 focus:border-orange-400 outline-none" />
          </div>
          <div>
            <label class="block text-gray-500 mb-2">특근비용 (1인당)</label>
            <input v-model.number="team._overtime_cost" type="number" placeholder="0"
              class="w-full px-4 py-3 border border-amber-200 rounded-lg text-right text-lg bg-amber-50 focus:border-amber-400 outline-none" />
          </div>
        </div>

        <div class="flex items-center justify-between">
          <span class="font-bold text-lg"
            :class="(team._receive_price || 0) - (team._pay_price || 0) >= 0 ? 'text-green-600' : 'text-red-600'">
            마진: {{ formatCurrency((team._receive_price || 0) - (team._pay_price || 0)) }}원/박스
          </span>
          <button @click="saveTeam(team)"
            class="px-6 py-3 bg-primary text-white rounded-lg font-medium hover:opacity-90">저장</button>
        </div>
      </div>

      <!-- 승인 대기 사용자 -->
      <div v-if="pendingUsers.length > 0" class="bg-white rounded-xl p-6 border border-amber-200">
        <h3 class="text-lg font-bold text-text mb-4">승인 대기 ({{ pendingUsers.length }}명)</h3>
        <div class="space-y-3">
          <div v-for="u in pendingUsers" :key="u.id"
            class="flex items-center justify-between p-4 bg-amber-50 rounded-lg">
            <div>
              <span class="font-bold text-text">{{ u.first_name || u.username }}</span>
              <span class="text-gray-500 ml-3">{{ u.email }}</span>
              <span class="text-gray-500 ml-3">{{ u.team_detail?.name || '-' }}</span>
            </div>
            <div class="flex gap-2">
              <button @click="approveUser(u.id)"
                class="px-4 py-2 bg-success text-white rounded-lg font-medium hover:opacity-90">승인</button>
              <button @click="rejectUser(u.id)"
                class="px-4 py-2 bg-red-500 text-white rounded-lg font-medium hover:opacity-90">거부</button>
            </div>
          </div>
        </div>
      </div>

      <!-- 팀 생성 모달 -->
      <div v-if="showCreateModal" class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
        <div class="bg-white rounded-xl p-6 w-full max-w-md">
          <h3 class="text-xl font-bold text-text mb-5">팀 생성</h3>
          <div class="space-y-4">
            <div>
              <label class="block text-gray-500 mb-2">팀 코드 (알파벳)</label>
              <input v-model="newTeam.code" type="text" placeholder="H, A, R 등" maxlength="5"
                class="w-full px-4 py-3 border border-gray-300 rounded-lg focus:border-primary outline-none uppercase" />
            </div>
            <div>
              <label class="block text-gray-500 mb-2">팀명</label>
              <input v-model="newTeam.name" type="text" placeholder="H조"
                class="w-full px-4 py-3 border border-gray-300 rounded-lg focus:border-primary outline-none" />
            </div>
          </div>
          <div class="flex justify-end gap-3 mt-6">
            <button @click="showCreateModal = false"
              class="px-5 py-3 border border-gray-300 rounded-lg hover:bg-gray-50">취소</button>
            <button @click="createTeam"
              class="px-5 py-3 bg-primary text-white rounded-lg font-medium hover:opacity-90">생성</button>
          </div>
        </div>
      </div>
    </div>
  </AppLayout>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { formatCurrency } from '@/utils/format'
import AppLayout from '@/components/common/AppLayout.vue'
import client from '@/api/client'

const teams = ref([])
const pendingUsers = ref([])
const showCreateModal = ref(false)
const newTeam = reactive({ code: '', name: '' })

const loadTeams = async () => {
  try {
    const resp = await client.get('/accounts/teams')
    teams.value = (resp.data.results || resp.data || []).map(t => ({
      ...t,
      _receive_price: Number(t.receive_price || 0),
      _pay_price: Number(t.pay_price || 0),
      _overtime_cost: Number(t.default_overtime_cost || 0),
    }))
  } catch (e) { teams.value = [] }
}

const loadPendingUsers = async () => {
  try {
    const resp = await client.get('/accounts/users', { params: { is_active: false } })
    const all = resp.data.results || resp.data || []
    pendingUsers.value = all.filter(u => !u.is_active && u.role === 'TEAM_LEADER')
  } catch (e) { pendingUsers.value = [] }
}

const saveTeam = async (team) => {
  try {
    await client.patch(`/accounts/teams/${team.id}`, {
      receive_price: team._receive_price || 0,
      pay_price: team._pay_price || 0,
      default_overtime_cost: team._overtime_cost || 0,
    })
    alert(`${team.name} 저장 완료`)
  } catch (e) { alert('저장 실패') }
}

const createTeam = async () => {
  if (!newTeam.code) { alert('팀 코드를 입력하세요'); return }
  try {
    await client.post('/accounts/teams', {
      code: newTeam.code.toUpperCase(),
      name: newTeam.name || `${newTeam.code.toUpperCase()}조`,
      is_active: true,
    })
    showCreateModal.value = false
    newTeam.code = ''; newTeam.name = ''
    loadTeams()
  } catch (e) { alert(e.response?.data?.code?.[0] || '팀 생성 실패') }
}

const approveUser = async (id) => {
  try {
    await client.patch(`/accounts/users/${id}`, { is_active: true })
    loadPendingUsers()
  } catch (e) { alert('승인 실패') }
}

const rejectUser = async (id) => {
  if (!confirm('이 사용자를 거부하시겠습니까?')) return
  try {
    await client.delete(`/accounts/users/${id}`)
    loadPendingUsers()
  } catch (e) { alert('거부 실패') }
}

onMounted(() => { loadTeams(); loadPendingUsers() })
</script>
