<template>
  <AppLayout>
    <div class="space-y-6">
      <div class="flex items-center justify-between">
        <h3 class="text-xl font-bold text-text">조 관리</h3>
        <button
          @click="showCreateModal = true"
          class="rounded-lg bg-primary px-5 py-3 font-medium text-white hover:opacity-90"
        >
          + 조 생성
        </button>
      </div>

      <div
        v-if="teams.length === 0"
        class="rounded-xl border border-gray-200 bg-white p-12 text-center text-gray-400"
      >
        <p class="mb-4 text-5xl">&#128101;</p>
        <p class="mb-1 text-lg font-medium">등록된 조가 없습니다.</p>
        <p>조를 생성한 뒤 수신단가와 용차 단가를 설정하세요.</p>
      </div>

      <div
        v-for="team in teams"
        :key="team.id"
        class="rounded-xl border border-gray-200 bg-white p-6"
      >
        <div class="mb-5 flex items-center gap-4">
          <div class="flex h-12 w-12 items-center justify-center rounded-full bg-primary-light">
            <span class="text-lg font-bold text-primary-dark">{{ team.code }}</span>
          </div>
          <div>
            <p class="text-xl font-bold text-text">{{ team.name }}</p>
            <p class="text-gray-400">코드: {{ team.code }}</p>
          </div>
        </div>

        <div class="grid gap-6 xl:grid-cols-[minmax(0,1fr)_minmax(0,1.4fr)_minmax(0,1.4fr)]">
          <section class="rounded-xl border border-gray-200 p-4">
            <h4 class="mb-4 text-sm font-semibold text-gray-700">기본 단가</h4>
            <div class="space-y-4">
              <div>
                <label class="mb-2 block text-sm text-gray-500">수신단가 (박스당)</label>
                <input
                  v-model.number="team._receive_price"
                  type="number"
                  min="0"
                  placeholder="0"
                  class="w-full rounded-lg border border-blue-200 bg-blue-50 px-4 py-3 text-right text-lg outline-none focus:border-blue-400"
                />
              </div>
              <div>
                <label class="mb-2 block text-sm text-gray-500">조정비용 (1인당)</label>
                <input
                  v-model.number="team._overtime_cost"
                  type="number"
                  min="0"
                  placeholder="0"
                  class="w-full rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-right text-lg outline-none focus:border-amber-400"
                />
              </div>
            </div>
          </section>

          <section class="rounded-xl border border-rose-200 p-4">
            <h4 class="mb-1 text-sm font-semibold text-gray-700">정규 배송원 회차별 용차 단가</h4>
            <p class="mb-4 text-xs text-gray-500">
              정규 배송원이 특정 회차만 용차 처리되는 경우 적용할 가구당 지급 단가입니다.
            </p>
            <div class="grid gap-4 md:grid-cols-3">
              <div>
                <label class="mb-2 block text-sm text-gray-500">1회차</label>
                <input
                  v-model.number="team._round_1_yongcha_pay_price"
                  type="number"
                  min="0"
                  placeholder="3000"
                  class="w-full rounded-lg border border-rose-200 bg-rose-50 px-4 py-3 text-right text-lg outline-none focus:border-rose-400"
                />
              </div>
              <div>
                <label class="mb-2 block text-sm text-gray-500">2회차</label>
                <input
                  v-model.number="team._round_2_yongcha_pay_price"
                  type="number"
                  min="0"
                  placeholder="3000"
                  class="w-full rounded-lg border border-pink-200 bg-pink-50 px-4 py-3 text-right text-lg outline-none focus:border-pink-400"
                />
              </div>
              <div>
                <label class="mb-2 block text-sm text-gray-500">3회차</label>
                <input
                  v-model.number="team._round_3_yongcha_pay_price"
                  type="number"
                  min="0"
                  placeholder="3000"
                  class="w-full rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-right text-lg outline-none focus:border-red-400"
                />
              </div>
            </div>
          </section>

          <section class="rounded-xl border border-fuchsia-200 p-4">
            <h4 class="mb-1 text-sm font-semibold text-gray-700">용차 배송원 회차별 용차 단가</h4>
            <p class="mb-4 text-xs text-gray-500">
              애초에 용차 배송원으로 처리되는 기사에게 회차별로 적용할 가구당 지급 단가입니다.
            </p>
            <div class="grid gap-4 md:grid-cols-3">
              <div>
                <label class="mb-2 block text-sm text-gray-500">1회차</label>
                <input
                  v-model.number="team._yongcha_round_1_pay_price"
                  type="number"
                  min="0"
                  placeholder="3000"
                  class="w-full rounded-lg border border-fuchsia-200 bg-fuchsia-50 px-4 py-3 text-right text-lg outline-none focus:border-fuchsia-400"
                />
              </div>
              <div>
                <label class="mb-2 block text-sm text-gray-500">2회차</label>
                <input
                  v-model.number="team._yongcha_round_2_pay_price"
                  type="number"
                  min="0"
                  placeholder="3000"
                  class="w-full rounded-lg border border-violet-200 bg-violet-50 px-4 py-3 text-right text-lg outline-none focus:border-violet-400"
                />
              </div>
              <div>
                <label class="mb-2 block text-sm text-gray-500">3회차</label>
                <input
                  v-model.number="team._yongcha_round_3_pay_price"
                  type="number"
                  min="0"
                  placeholder="3000"
                  class="w-full rounded-lg border border-purple-200 bg-purple-50 px-4 py-3 text-right text-lg outline-none focus:border-purple-400"
                />
              </div>
            </div>
          </section>
        </div>

        <div class="mt-5 flex items-center justify-end gap-3">
          <button
            @click="deleteTeam(team)"
            class="rounded-lg bg-red-500 px-6 py-3 font-medium text-white hover:opacity-90"
          >
            삭제
          </button>
          <button
            @click="saveTeam(team)"
            class="rounded-lg bg-primary px-6 py-3 font-medium text-white hover:opacity-90"
          >
            저장
          </button>
        </div>
      </div>

      <div v-if="pendingUsers.length > 0" class="rounded-xl border border-amber-200 bg-white p-6">
        <h3 class="mb-4 text-lg font-bold text-text">승인 대기 계정 ({{ pendingUsers.length }}명)</h3>
        <div class="space-y-3">
          <div
            v-for="u in pendingUsers"
            :key="u.id"
            class="flex items-center justify-between rounded-lg bg-amber-50 p-4"
          >
            <div>
              <span class="font-bold text-text">{{ u.first_name || u.username }}</span>
              <span class="ml-3 text-gray-500">{{ u.email }}</span>
              <span class="ml-3 text-gray-500">{{ u.team_detail?.name || '-' }}</span>
            </div>
            <div class="flex gap-2">
              <button
                @click="approveUser(u.id)"
                class="rounded-lg bg-success px-4 py-2 font-medium text-white hover:opacity-90"
              >
                승인
              </button>
              <button
                @click="rejectUser(u.id)"
                class="rounded-lg bg-red-500 px-4 py-2 font-medium text-white hover:opacity-90"
              >
                거절
              </button>
            </div>
          </div>
        </div>
      </div>

      <div class="rounded-xl border border-gray-200 bg-white p-6">
        <h3 class="mb-4 text-lg font-bold text-text">조장 계정</h3>
        <div v-if="teamLeaders.length === 0" class="py-6 text-center text-gray-400">
          등록된 조장 계정이 없습니다.
        </div>
        <table v-else class="w-full">
          <thead class="border-b border-gray-200 bg-gray-50">
            <tr>
              <th class="px-4 py-3 text-left font-semibold text-gray-600">아이디</th>
              <th class="px-4 py-3 text-left font-semibold text-gray-600">이름</th>
              <th class="px-4 py-3 text-left font-semibold text-gray-600">소속 조</th>
              <th class="px-4 py-3 text-left font-semibold text-gray-600">상태</th>
              <th class="px-4 py-3 text-center font-semibold text-gray-600">관리</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="u in teamLeaders"
              :key="u.id"
              class="border-b border-gray-100 hover:bg-gray-50"
            >
              <td class="px-4 py-3 font-mono">{{ u.username }}</td>
              <td class="px-4 py-3 font-bold text-text">{{ u.first_name || '-' }}</td>
              <td class="px-4 py-3">{{ u.team_detail?.name || '미배정' }}</td>
              <td class="px-4 py-3">
                <span
                  class="rounded-full px-2 py-0.5 font-medium"
                  :class="u.is_active ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'"
                >
                  {{ u.is_active ? '활성' : '비활성' }}
                </span>
              </td>
              <td class="px-4 py-3 text-center">
                <button
                  @click="deleteUser(u)"
                  class="rounded-lg bg-red-500 px-4 py-2 font-medium text-white hover:opacity-90"
                >
                  삭제
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <div
        v-if="showCreateModal"
        class="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
      >
        <div class="w-full max-w-md rounded-xl bg-white p-6">
          <h3 class="mb-5 text-xl font-bold text-text">조 생성</h3>
          <div class="space-y-4">
            <div>
              <label class="mb-2 block text-gray-500">조 코드</label>
              <input
                v-model="newTeam.code"
                type="text"
                maxlength="5"
                placeholder="A, R, X"
                class="w-full rounded-lg border border-gray-300 px-4 py-3 uppercase outline-none focus:border-primary"
              />
            </div>
            <div>
              <label class="mb-2 block text-gray-500">조 이름</label>
              <input
                v-model="newTeam.name"
                type="text"
                placeholder="A조"
                class="w-full rounded-lg border border-gray-300 px-4 py-3 outline-none focus:border-primary"
              />
            </div>
          </div>
          <div class="mt-6 flex justify-end gap-3">
            <button
              @click="showCreateModal = false"
              class="rounded-lg border border-gray-300 px-5 py-3 hover:bg-gray-50"
            >
              취소
            </button>
            <button
              @click="createTeam"
              class="rounded-lg bg-primary px-5 py-3 font-medium text-white hover:opacity-90"
            >
              생성
            </button>
          </div>
        </div>
      </div>
    </div>
  </AppLayout>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import AppLayout from '@/components/common/AppLayout.vue'
import client from '@/api/client'

const teams = ref([])
const pendingUsers = ref([])
const teamLeaders = ref([])
const showCreateModal = ref(false)
const newTeam = reactive({ code: '', name: '' })

const normalizeTeam = (t) => ({
  ...t,
  _receive_price: Number(t.receive_price || 0),
  _overtime_cost: Number(t.default_overtime_cost || 0),
  _yongcha_pay_price: Number(t.yongcha_pay_price || t.current_yongcha_pay_price || 3000),
  _round_1_yongcha_pay_price: Number(t.round_1_yongcha_pay_price || 3000),
  _round_2_yongcha_pay_price: Number(t.round_2_yongcha_pay_price || 3000),
  _round_3_yongcha_pay_price: Number(t.round_3_yongcha_pay_price || 3000),
  _yongcha_round_1_pay_price: Number(t.yongcha_round_1_pay_price || 3000),
  _yongcha_round_2_pay_price: Number(t.yongcha_round_2_pay_price || 3000),
  _yongcha_round_3_pay_price: Number(t.yongcha_round_3_pay_price || 3000),
  _orig_receive_price: Number(t.receive_price || 0),
  _orig_overtime_cost: Number(t.default_overtime_cost || 0),
  _orig_yongcha_pay_price: Number(t.yongcha_pay_price || t.current_yongcha_pay_price || 3000),
  _orig_round_1_yongcha_pay_price: Number(t.round_1_yongcha_pay_price || 3000),
  _orig_round_2_yongcha_pay_price: Number(t.round_2_yongcha_pay_price || 3000),
  _orig_round_3_yongcha_pay_price: Number(t.round_3_yongcha_pay_price || 3000),
  _orig_yongcha_round_1_pay_price: Number(t.yongcha_round_1_pay_price || 3000),
  _orig_yongcha_round_2_pay_price: Number(t.yongcha_round_2_pay_price || 3000),
  _orig_yongcha_round_3_pay_price: Number(t.yongcha_round_3_pay_price || 3000),
})

const loadTeams = async () => {
  try {
    const resp = await client.get('/accounts/teams')
    teams.value = (resp.data.results || resp.data || []).map(normalizeTeam)
  } catch (_error) {
    teams.value = []
  }
}

const loadPendingUsers = async () => {
  try {
    const resp = await client.get('/accounts/users', { params: { is_active: false } })
    const all = resp.data.results || resp.data || []
    pendingUsers.value = all.filter((u) => !u.is_active && u.role === 'TEAM_LEADER')
  } catch (_error) {
    pendingUsers.value = []
  }
}

const saveTeam = async (team) => {
  try {
    await client.patch(`/accounts/teams/${team.id}`, {
      receive_price: team._receive_price || 0,
      default_overtime_cost: team._overtime_cost || 0,
      yongcha_pay_price: team._yongcha_pay_price || 0,
      round_1_yongcha_pay_price: team._round_1_yongcha_pay_price || 0,
      round_2_yongcha_pay_price: team._round_2_yongcha_pay_price || 0,
      round_3_yongcha_pay_price: team._round_3_yongcha_pay_price || 0,
      yongcha_round_1_pay_price: team._yongcha_round_1_pay_price || 0,
      yongcha_round_2_pay_price: team._yongcha_round_2_pay_price || 0,
      yongcha_round_3_pay_price: team._yongcha_round_3_pay_price || 0,
    })

    const receivePriceChanged = Number(team._receive_price) !== Number(team._orig_receive_price)
    const regularRoundChanged =
      Number(team._round_1_yongcha_pay_price) !== Number(team._orig_round_1_yongcha_pay_price) ||
      Number(team._round_2_yongcha_pay_price) !== Number(team._orig_round_2_yongcha_pay_price) ||
      Number(team._round_3_yongcha_pay_price) !== Number(team._orig_round_3_yongcha_pay_price)
    const yongchaRoundChanged =
      Number(team._yongcha_round_1_pay_price) !== Number(team._orig_yongcha_round_1_pay_price) ||
      Number(team._yongcha_round_2_pay_price) !== Number(team._orig_yongcha_round_2_pay_price) ||
      Number(team._yongcha_round_3_pay_price) !== Number(team._orig_yongcha_round_3_pay_price)

    const shouldApplyHistory = (receivePriceChanged || regularRoundChanged || yongchaRoundChanged)
      ? confirm('단가가 변경되었습니다.\n기존 정산 이력에도 반영할까요?')
      : false

    if (shouldApplyHistory) {
      try {
        await client.post(`/accounts/teams/${team.id}/recalc_settlements/`)
      } catch (_error) {
        // no-op
      }
    }

    Object.assign(team, normalizeTeam({
      ...team,
      receive_price: team._receive_price,
      default_overtime_cost: team._overtime_cost,
      yongcha_pay_price: team._yongcha_pay_price,
      round_1_yongcha_pay_price: team._round_1_yongcha_pay_price,
      round_2_yongcha_pay_price: team._round_2_yongcha_pay_price,
      round_3_yongcha_pay_price: team._round_3_yongcha_pay_price,
      yongcha_round_1_pay_price: team._yongcha_round_1_pay_price,
      yongcha_round_2_pay_price: team._yongcha_round_2_pay_price,
      yongcha_round_3_pay_price: team._yongcha_round_3_pay_price,
    }))

    alert(`${team.name} 저장 완료`)
    await loadTeams()
  } catch (error) {
    alert(error.response?.data?.detail || '저장에 실패했습니다.')
  }
}

const deleteTeam = async (team) => {
  if (!confirm(`${team.name} 조를 삭제할까요? 관련 데이터도 함께 정리됩니다.`)) return
  try {
    await client.delete(`/accounts/teams/${team.id}`)
    await loadTeams()
  } catch (_error) {
    alert('삭제에 실패했습니다.')
  }
}

const createTeam = async () => {
  if (!newTeam.code) {
    alert('조 코드를 입력하세요.')
    return
  }

  try {
    await client.post('/accounts/teams', {
      code: newTeam.code.toUpperCase(),
      name: newTeam.name || `${newTeam.code.toUpperCase()}조`,
      is_active: true,
    })
    showCreateModal.value = false
    newTeam.code = ''
    newTeam.name = ''
    await loadTeams()
  } catch (error) {
    alert(error.response?.data?.code?.[0] || '조 생성에 실패했습니다.')
  }
}

const approveUser = async (id) => {
  try {
    await client.patch(`/accounts/users/${id}`, { is_active: true })
    await loadPendingUsers()
  } catch (_error) {
    alert('승인에 실패했습니다.')
  }
}

const rejectUser = async (id) => {
  if (!confirm('이 사용자를 거절할까요?')) return
  try {
    await client.delete(`/accounts/users/${id}`)
    await loadPendingUsers()
  } catch (_error) {
    alert('거절에 실패했습니다.')
  }
}

const loadTeamLeaders = async () => {
  try {
    const resp = await client.get('/accounts/users')
    const all = resp.data.results || resp.data || []
    teamLeaders.value = all.filter((u) => u.role === 'TEAM_LEADER' && u.is_active)
  } catch (_error) {
    teamLeaders.value = []
  }
}

const deleteUser = async (u) => {
  if (!confirm(`${u.first_name || u.username} 계정을 삭제할까요?`)) return
  try {
    await client.delete(`/accounts/users/${u.id}`)
    await loadTeamLeaders()
    await loadPendingUsers()
  } catch (_error) {
    alert('삭제에 실패했습니다.')
  }
}

onMounted(() => {
  loadTeams()
  loadPendingUsers()
  loadTeamLeaders()
})
</script>
