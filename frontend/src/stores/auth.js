import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { login as apiLogin } from '@/api/auth'

export const useAuthStore = defineStore('auth', () => {
  const user = ref(JSON.parse(localStorage.getItem('user') || 'null'))
  const token = ref(localStorage.getItem('token') || null)
  const teamFilter = ref('전체')

  const isAuthenticated = computed(() => !!token.value)
  const isAdmin = computed(() => user.value?.role === 'ADMIN' || user.value?.is_staff === true)
  const isTeamLeader = computed(() => user.value?.role === 'TEAM_LEADER')

  const login = async (email, password) => {
    const response = await apiLogin(email, password)
    token.value = response.data.token
    user.value = response.data.user
    localStorage.setItem('token', token.value)
    localStorage.setItem('user', JSON.stringify(response.data.user))
    return response.data
  }

  const logout = () => {
    user.value = null
    token.value = null
    localStorage.removeItem('token')
    localStorage.removeItem('user')
  }

  const setTeamFilter = (team) => {
    teamFilter.value = team
  }

  return {
    user, token, isAuthenticated, isAdmin, isTeamLeader,
    teamFilter, login, logout, setTeamFilter
  }
})
