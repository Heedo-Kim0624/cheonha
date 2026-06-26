import { computed, ref } from 'vue'
import { fetchCompanies } from '@/api/vehicle'
import { fetchFleetSite } from '@/api/fleetManagement'

function normalizeCompanyList(payload) {
  const list = Array.isArray(payload) ? payload : payload?.results || payload?.companies || []
  return list.map((company) => ({
    code: company.code || company.company_code || company.id || 'CHEONHA',
    name: company.name || company.company_name || company.code || '차량 회사',
  }))
}

export function useFleetSite(defaultCompanyCode = 'CHEONHA') {
  const companies = ref([])
  const selectedCompany = ref(localStorage.getItem('fleetCompanyCode') || defaultCompanyCode)
  const fleetPayload = ref({ groups: [] })
  const loading = ref(false)
  const error = ref('')

  const groups = computed(() => fleetPayload.value.groups || [])

  async function loadCompanies() {
    try {
      const response = await fetchCompanies()
      companies.value = normalizeCompanyList(response.data)
    } catch (_) {
      companies.value = [{ code: defaultCompanyCode, name: '천하운수' }]
    }
    if (!companies.value.some((company) => company.code === selectedCompany.value) && companies.value[0]) {
      selectedCompany.value = companies.value[0].code
    }
  }

  async function reload() {
    loading.value = true
    error.value = ''
    localStorage.setItem('fleetCompanyCode', selectedCompany.value)
    try {
      const response = await fetchFleetSite({ company: selectedCompany.value })
      fleetPayload.value = response.data || { groups: [] }
    } catch (err) {
      error.value = err?.response?.data?.detail || err?.message || '차량관리 데이터를 불러오지 못했습니다.'
    } finally {
      loading.value = false
    }
  }

  return {
    companies,
    selectedCompany,
    fleetPayload,
    groups,
    loading,
    error,
    loadCompanies,
    reload,
  }
}
