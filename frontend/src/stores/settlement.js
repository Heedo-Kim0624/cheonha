import { defineStore } from 'pinia'
import { ref } from 'vue'
import { fetchSettlements, createSettlement } from '@/api/settlement'

export const useSettlementStore = defineStore('settlement', () => {
  const settlements = ref([
    { id: 1, period: '2024-04', 수신: 2850000, 지급: 1950000, 특근: 450000, 수익: 450000, status: 'completed', createdAt: new Date() },
    { id: 2, period: '2024-03', 수신: 2650000, 지급: 1850000, 특근: 380000, 수익: 420000, status: 'completed', createdAt: new Date(Date.now() - 2592000000) }
  ])

  const settlementDetails = ref([])

  const fetchSettlementsData = async () => {
    try {
      const response = await fetchSettlements()
      settlements.value = response.data
    } catch (error) {
      console.error('Failed to fetch settlements:', error)
    }
  }

  const createNewSettlement = async (settlementData) => {
    try {
      const response = await createSettlement(settlementData)
      settlements.value.unshift(response.data)
      return response.data
    } catch (error) {
      console.error('Failed to create settlement:', error)
      throw error
    }
  }

  return {
    settlements,
    settlementDetails,
    fetchSettlementsData,
    createNewSettlement
  }
})
