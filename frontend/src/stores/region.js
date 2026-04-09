import { defineStore } from 'pinia'
import { ref } from 'vue'
import { fetchRegions, fetchTeams, updatePrice } from '@/api/region'

export const useRegionStore = defineStore('region', () => {
  const teams = ref([
    { id: 1, name: 'A조', leader: '김철수', defaultOvertimeCost: 50000 },
    { id: 2, name: 'X조', leader: '이영희', defaultOvertimeCost: 45000 },
    { id: 3, name: 'R조', leader: '박민준', defaultOvertimeCost: 55000 }
  ])

  const regions = ref([
    { id: 1, name: '서울', receivingPrice: 15000, paymentPrice: 12000, margin: 3000 },
    { id: 2, name: '인천', receivingPrice: 14000, paymentPrice: 11000, margin: 3000 },
    { id: 3, name: '대전', receivingPrice: 13000, paymentPrice: 10000, margin: 3000 },
    { id: 4, name: '대구', receivingPrice: 12000, paymentPrice: 9500, margin: 2500 },
    { id: 5, name: '부산', receivingPrice: 14500, paymentPrice: 11500, margin: 3000 },
    { id: 6, name: '광주', receivingPrice: 13500, paymentPrice: 10500, margin: 3000 }
  ])

  const fetchRegionsData = async () => {
    try {
      const response = await fetchRegions()
      regions.value = response.data
    } catch (error) {
      console.error('Failed to fetch regions:', error)
    }
  }

  const fetchTeamsData = async () => {
    try {
      const response = await fetchTeams()
      teams.value = response.data
    } catch (error) {
      console.error('Failed to fetch teams:', error)
    }
  }

  const updateRegionPrice = async (regionId, priceData) => {
    try {
      const response = await updatePrice(regionId, priceData)
      const index = regions.value.findIndex(r => r.id === regionId)
      if (index !== -1) {
        regions.value[index] = response.data
      }
      return response.data
    } catch (error) {
      console.error('Failed to update price:', error)
      throw error
    }
  }

  return {
    teams,
    regions,
    fetchRegionsData,
    fetchTeamsData,
    updateRegionPrice
  }
})
