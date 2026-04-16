<template>
  <AppLayout>
    <div class="space-y-6">
      <div class="flex items-center justify-between">
        <h3 class="text-xl font-bold text-text">정산 문의</h3>
        <div class="flex gap-2">
          <button v-for="f in statusFilters" :key="f.key" @click="statusFilter = f.key; loadList()"
            class="px-4 py-2 rounded-lg font-medium transition-all relative"
            :class="statusFilter === f.key ? 'bg-primary text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'">
            {{ f.label }}
            <span v-if="f.key === 'open' && counts.open > 0"
              class="ml-2 px-2 py-0.5 bg-red-500 text-white text-xs rounded-full">
              {{ counts.open }}
            </span>
          </button>
        </div>
      </div>

      <TeamFilter v-model="selectedTeam" @update:modelValue="loadList" />

      <div v-if="loading" class="text-center py-12 text-gray-400">로딩 중...</div>

      <div v-else-if="inquiries.length === 0" class="bg-white rounded-xl p-12 border border-gray-200 text-center text-gray-400">
        <p class="text-4xl mb-3">💬</p>
        <p>정산 문의가 없습니다.</p>
      </div>

      <div v-else class="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <table class="w-full">
          <thead class="bg-gray-50 border-b border-gray-200">
            <tr>
              <th class="text-left px-5 py-3 font-semibold text-gray-600">상태</th>
              <th class="text-left px-5 py-3 font-semibold text-gray-600">업로드일</th>
              <th class="text-left px-5 py-3 font-semibold text-gray-600">이름</th>
              <th class="text-left px-5 py-3 font-semibold text-gray-600">조</th>
              <th class="text-left px-5 py-3 font-semibold text-gray-600">선택 날짜</th>
              <th class="text-right px-5 py-3 font-semibold text-gray-600">박스수</th>
              <th class="text-right px-5 py-3 font-semibold text-gray-600">정산금액</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="iq in inquiries" :key="iq.id"
              class="border-b border-gray-100 hover:bg-gray-50 cursor-pointer"
              @click="openDetail(iq)">
              <td class="px-5 py-4">
                <span v-if="needsReply(iq)" class="px-2 py-0.5 bg-red-100 text-red-700 rounded font-medium">답변필요</span>
                <span v-else class="px-2 py-0.5 bg-green-100 text-green-700 rounded font-medium">완료</span>
              </td>
              <td class="px-5 py-4 text-gray-500">{{ formatDateTime(iq.created_at) }}</td>
              <td class="px-5 py-4 font-bold text-text">{{ iq.crew_name }}</td>
              <td class="px-5 py-4">
                <span class="px-2 py-0.5 bg-primary-light text-primary-dark rounded font-medium">{{ iq.team_name }}</span>
              </td>
              <td class="px-5 py-4">{{ iq.dispatch_date }}</td>
              <td class="px-5 py-4 text-right font-bold">{{ iq.boxes }}</td>
              <td class="px-5 py-4 text-right font-bold text-primary-dark">{{ Number(iq.total_amount).toLocaleString() }}원</td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- 상세 모달 -->
      <div v-if="selected" class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4"
        @click.self="closeDetail">
        <div class="bg-white rounded-xl w-full max-w-6xl max-h-[95vh] overflow-hidden flex flex-col">
          <div class="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
            <div>
              <h3 class="text-xl font-bold text-text">{{ selected.crew_name }} ({{ selected.team_name }})</h3>
              <p class="text-gray-500">{{ selected.dispatch_date }}</p>
            </div>
            <button @click="closeDetail" class="text-gray-400 hover:text-gray-600 text-2xl">×</button>
          </div>

          <div class="p-8 overflow-y-auto flex-1 space-y-6">
            <!-- 수정 필드들 -->
            <div class="grid grid-cols-5 gap-4">
              <div class="p-5 bg-blue-50 rounded-xl">
                <label class="block text-base text-blue-600 font-medium mb-2 whitespace-nowrap">박스수</label>
                <input v-model.number="form.boxes" type="number" min="0"
                  class="w-full px-3 py-2 bg-white rounded-lg text-right text-lg font-bold" />
              </div>
              <div class="p-5 bg-orange-50 rounded-xl">
                <label class="block text-base text-orange-600 font-medium mb-2 whitespace-nowrap">지급단가</label>
                <input v-model.number="form.pay_price" type="number" min="0"
                  class="w-full px-3 py-2 bg-white rounded-lg text-right text-lg font-bold" />
              </div>
              <div class="p-5 bg-purple-50 rounded-xl">
                <label class="block text-base text-purple-600 font-medium mb-2 whitespace-nowrap">조정금액</label>
                <input v-model.number="form.adjustment_amount" type="number"
                  class="w-full px-3 py-2 bg-white rounded-lg text-right text-lg font-bold" />
              </div>
              <div class="p-5 bg-rose-50 rounded-xl">
                <label class="block text-base text-rose-600 font-medium mb-2 whitespace-nowrap">기타지출</label>
                <input v-model.number="form.other_cost" type="number" min="0"
                  class="w-full px-3 py-2 bg-white rounded-lg text-right text-lg font-bold" />
              </div>
              <div class="p-5 bg-green-50 rounded-xl">
                <label class="block text-base text-green-600 font-medium mb-2 whitespace-nowrap">정산금액</label>
                <div class="w-full px-3 py-2 bg-white rounded-lg text-right text-lg font-bold text-green-800">
                  {{ computedTotal.toLocaleString() }}원
                </div>
              </div>
            </div>
            <div class="flex justify-end">
              <button @click="saveInquiry"
                class="px-6 py-3 bg-primary text-white rounded-lg text-lg font-medium hover:opacity-90">저장</button>
            </div>

            <!-- 대화 -->
            <div class="border-t border-gray-200 pt-5">
              <h4 class="font-bold text-text mb-3">대화</h4>
              <div class="space-y-3 max-h-[400px] overflow-y-auto bg-gray-50 p-5 rounded-lg">
                <div v-for="m in selected.messages" :key="m.id"
                  class="flex" :class="m.author_type === 'admin' ? 'justify-end' : 'justify-start'">
                  <div class="max-w-[70%]">
                    <div class="px-4 py-2 rounded-lg"
                      :class="m.author_type === 'admin' ? 'bg-primary text-white' : 'bg-white border border-gray-200 text-text'">
                      <p class="font-medium text-xs opacity-70 mb-1">{{ m.author_name }}</p>
                      <p class="whitespace-pre-wrap">{{ m.content }}</p>
                    </div>
                    <p class="text-xs text-gray-400 mt-1"
                      :class="m.author_type === 'admin' ? 'text-right' : 'text-left'">
                      {{ formatDateTime(m.created_at) }}
                    </p>
                  </div>
                </div>
                <div v-if="selected.messages.length === 0" class="text-center text-gray-400 py-4">아직 대화가 없습니다.</div>
              </div>

              <div class="flex gap-2 mt-3">
                <input v-model="newMessage" type="text" placeholder="답변 입력..."
                  @keyup.enter="sendMessage"
                  class="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:border-primary outline-none" />
                <button @click="sendMessage"
                  class="px-5 py-2 bg-primary text-white rounded-lg font-medium hover:opacity-90">전송</button>
                <button v-if="needsReply(selected)" @click="markRead"
                  class="px-5 py-2 bg-gray-500 text-white rounded-lg font-medium hover:opacity-90">읽음 처리</button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </AppLayout>
</template>

<script setup>
import { ref, computed, onMounted, reactive } from 'vue'
import AppLayout from '@/components/common/AppLayout.vue'
import TeamFilter from '@/components/common/TeamFilter.vue'
import { fetchInquiries, getInquiry, updateInquiry, addInquiryMessage, markInquiryRead, fetchInquiryCounts } from '@/api/inquiry'
import client from '@/api/client'

const statusFilter = ref('all')
const selectedTeam = ref('')
const inquiries = ref([])
const counts = ref({ total: 0, open: 0 })
const loading = ref(false)
const selected = ref(null)
const newMessage = ref('')
const form = reactive({ boxes: 0, pay_price: 0, is_overtime: false, adjustment_amount: 0, other_cost: 0 })

const statusFilters = [
  { key: 'all', label: '전체' },
  { key: 'open', label: '답변필요' },
]

const needsReply = (iq) => iq.last_by === 'crew' && iq.status !== 'READ'

const computedTotal = computed(() => {
  return (form.boxes || 0) * (form.pay_price || 0) + (form.adjustment_amount || 0)
})

const formatDateTime = (dt) => {
  if (!dt) return ''
  const d = new Date(dt)
  return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')} ${String(d.getHours()).padStart(2,'0')}:${String(d.getMinutes()).padStart(2,'0')}`
}

const loadList = async () => {
  loading.value = true
  try {
    const params = {}
    if (selectedTeam.value) params.team_name = selectedTeam.value
    const r = await fetchInquiries(params)
    let list = r.data.results || r.data || []
    if (statusFilter.value === 'open') {
      list = list.filter(needsReply)
    }
    inquiries.value = list

    const cr = await fetchInquiryCounts(selectedTeam.value ? { team_name: selectedTeam.value } : {})
    counts.value = cr.data
  } catch (e) { console.error(e); inquiries.value = [] }
  finally { loading.value = false }
}

const openDetail = async (iq) => {
  try {
    const r = await getInquiry(iq.id)
    selected.value = r.data
    form.boxes = Number(r.data.boxes || 0)
    form.pay_price = Number(r.data.pay_price || 0)
    form.is_overtime = !!r.data.is_overtime
    form.adjustment_amount = Number(r.data.adjustment_amount || 0)
    form.other_cost = Number(r.data.other_cost || 0)
  } catch (e) { alert('조회 실패') }
}

const closeDetail = () => { selected.value = null; loadList() }

const saveInquiry = async () => {
  try {
    const resp = await updateInquiry(selected.value.id, {
      boxes: form.boxes, pay_price: form.pay_price,
      is_overtime: form.is_overtime, adjustment_amount: form.adjustment_amount,
      other_cost: form.other_cost,
    })
    const { pay_price_changed, crew_member_id } = resp.data

    // 지급단가 변경 시 과거 정산에도 적용할지 확인
    if (pay_price_changed && crew_member_id) {
      if (confirm('지급단가가 변경되었습니다.\n이전 정산에도 적용하시겠습니까?\n(확인: 과거 전체 재계산 / 취소: 현재 포함 이후에만)')) {
        try {
          await client.post(`/crew/members/${crew_member_id}/recalc_settlements/`)
        } catch (e) { /* 정산 없으면 무시 */ }
      }
    }

    alert('저장 완료')
    const r = await getInquiry(selected.value.id)
    selected.value = r.data
  } catch (e) { alert('저장 실패') }
}

const sendMessage = async () => {
  const content = newMessage.value.trim()
  if (!content) return
  try {
    await addInquiryMessage(selected.value.id, content, 'admin')
    newMessage.value = ''
    const r = await getInquiry(selected.value.id)
    selected.value = r.data
  } catch (e) { alert('전송 실패') }
}

const markRead = async () => {
  try {
    await markInquiryRead(selected.value.id)
    const r = await getInquiry(selected.value.id)
    selected.value = r.data
  } catch (e) { alert('처리 실패') }
}

onMounted(loadList)
</script>
