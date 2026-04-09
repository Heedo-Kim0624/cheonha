import { defineStore } from 'pinia'
import { ref } from 'vue'
import {
  uploadDispatchFile,
  getDetectedInfo,
  configureRegions,
  registerCrew,
  setOvertime,
  finalizeUpload,
  fetchUploads,
  getUpload,
  getRecords
} from '@/api/dispatch'

export const useDispatchStore = defineStore('dispatch', () => {
  const uploads = ref([])
  const currentUpload = ref(null)
  const records = ref([])
  const loading = ref(false)

  const fetchUploadsData = async () => {
    loading.value = true
    try {
      const response = await fetchUploads()
      uploads.value = response.data.results || response.data
    } catch (error) {
      console.error('Failed to fetch uploads:', error)
    } finally {
      loading.value = false
    }
  }

  const uploadFile = async (file) => {
    try {
      const response = await uploadDispatchFile(file)
      return response.data
    } catch (error) {
      console.error('Failed to upload dispatch:', error)
      throw error
    }
  }

  const fetchDetectedInfo = async (uploadId) => {
    try {
      const response = await getDetectedInfo(uploadId)
      return response.data
    } catch (error) {
      console.error('Failed to get detected info:', error)
      throw error
    }
  }

  const submitRegions = async (uploadId, regions) => {
    try {
      const response = await configureRegions(uploadId, regions)
      return response.data
    } catch (error) {
      console.error('Failed to configure regions:', error)
      throw error
    }
  }

  const submitCrew = async (uploadId, crew) => {
    try {
      const response = await registerCrew(uploadId, crew)
      return response.data
    } catch (error) {
      console.error('Failed to register crew:', error)
      throw error
    }
  }

  const submitOvertime = async (uploadId, overtimeRecords) => {
    try {
      const response = await setOvertime(uploadId, overtimeRecords)
      return response.data
    } catch (error) {
      console.error('Failed to set overtime:', error)
      throw error
    }
  }

  const submitFinalize = async (uploadId, data = {}) => {
    try {
      const response = await finalizeUpload(uploadId, data)
      return response.data
    } catch (error) {
      console.error('Failed to finalize:', error)
      throw error
    }
  }

  const fetchRecords = async (uploadId) => {
    try {
      const response = await getRecords(uploadId)
      records.value = response.data.results || response.data
      return records.value
    } catch (error) {
      console.error('Failed to fetch records:', error)
      throw error
    }
  }

  return {
    uploads,
    currentUpload,
    records,
    loading,
    fetchUploadsData,
    uploadFile,
    fetchDetectedInfo,
    submitRegions,
    submitCrew,
    submitOvertime,
    submitFinalize,
    fetchRecords
  }
})
