import { computed, ref } from 'vue'
import { fetchFleetSite } from '@/api/fleetManagement'

export function useFleetSite() {
  const fleetPayload = ref({ groups: [] })
  const loading = ref(false)
  const error = ref('')

  const groups = computed(() => fleetPayload.value.groups || [])

  async function reload() {
    loading.value = true
    error.value = ''
    try {
      const response = await fetchFleetSite()
      fleetPayload.value = response.data || { groups: [] }
    } catch (err) {
      error.value = err?.response?.data?.detail || err?.message || '차량관리 데이터를 불러오지 못했습니다.'
    } finally {
      loading.value = false
    }
  }

  return {
    fleetPayload,
    groups,
    loading,
    error,
    reload,
  }
}
