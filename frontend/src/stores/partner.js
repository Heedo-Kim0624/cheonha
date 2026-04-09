import { defineStore } from 'pinia'
import { ref } from 'vue'
import { fetchPartners, createPartner } from '@/api/partner'

export const usePartnerStore = defineStore('partner', () => {
  const partners = ref([
    { id: 1, name: '파트너A', contact: '010-1111-1111', region: '서울', status: 'active' },
    { id: 2, name: '파트너B', contact: '010-2222-2222', region: '인천', status: 'active' },
    { id: 3, name: '파트너C', contact: '010-3333-3333', region: '대전', status: 'active' }
  ])

  const fetchPartnersData = async () => {
    try {
      const response = await fetchPartners()
      partners.value = response.data
    } catch (error) {
      console.error('Failed to fetch partners:', error)
    }
  }

  const addPartner = async (partnerData) => {
    try {
      const response = await createPartner(partnerData)
      partners.value.push(response.data)
      return response.data
    } catch (error) {
      console.error('Failed to add partner:', error)
      throw error
    }
  }

  return {
    partners,
    fetchPartnersData,
    addPartner
  }
})
