import { defineStore } from 'pinia'
import { ref } from 'vue'
import {
  fetchCrewMembers,
  createCrewMember,
  updateCrewMember as updateCrewAPI,
  deleteCrewMember,
  getNewMembers,
  markRegistered,
  getSettlementHistory
} from '@/api/crew'

export const useCrewStore = defineStore('crew', () => {
  const crewMembers = ref([])
  const newDetections = ref([])
  const loading = ref(false)
  const error = ref(null)

  const fetchCrew = async (params = {}) => {
    loading.value = true
    error.value = null
    try {
      const response = await fetchCrewMembers(params)
      crewMembers.value = response.data.results || response.data
    } catch (err) {
      console.error('Failed to fetch crew:', err)
      error.value = err.message
    } finally {
      loading.value = false
    }
  }

  const fetchNewMembers = async () => {
    try {
      const response = await getNewMembers()
      newDetections.value = response.data.results || response.data
    } catch (err) {
      console.error('Failed to fetch new members:', err)
    }
  }

  const addCrew = async (crewData) => {
    try {
      const response = await createCrewMember(crewData)
      crewMembers.value.push(response.data)
      return response.data
    } catch (err) {
      console.error('Failed to add crew:', err)
      throw err
    }
  }

  const updateCrew = async (id, crewData) => {
    try {
      const response = await updateCrewAPI(id, crewData)
      const index = crewMembers.value.findIndex(c => c.id === id)
      if (index !== -1) {
        crewMembers.value[index] = response.data
      }
      return response.data
    } catch (err) {
      console.error('Failed to update crew:', err)
      throw err
    }
  }

  const removeCrew = async (id) => {
    try {
      await deleteCrewMember(id)
      crewMembers.value = crewMembers.value.filter(c => c.id !== id)
    } catch (err) {
      console.error('Failed to delete crew:', err)
      throw err
    }
  }

  const registerNewMember = async (id) => {
    try {
      const response = await markRegistered(id)
      // Update in crewMembers list
      const index = crewMembers.value.findIndex(c => c.id === id)
      if (index !== -1) {
        crewMembers.value[index] = response.data
      }
      // Remove from newDetections
      newDetections.value = newDetections.value.filter(d => d.id !== id)
      return response.data
    } catch (err) {
      console.error('Failed to register member:', err)
      throw err
    }
  }

  const fetchSettlementHistory = async (crewId) => {
    try {
      const response = await getSettlementHistory(crewId)
      return response.data
    } catch (err) {
      console.error('Failed to fetch settlement history:', err)
      throw err
    }
  }

  const removeNewDetection = (phone) => {
    newDetections.value = newDetections.value.filter(d => d.phone !== phone)
  }

  return {
    crewMembers,
    newDetections,
    loading,
    error,
    fetchCrew,
    fetchNewMembers,
    addCrew,
    updateCrew,
    removeCrew,
    registerNewMember,
    fetchSettlementHistory,
    removeNewDetection
  }
})
