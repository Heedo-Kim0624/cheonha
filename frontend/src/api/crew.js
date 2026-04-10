import client from './client'

export const fetchCrewMembers = (params = {}) => {
  return client.get('/crew/members', { params })
}

export const getCrewMember = (id) => {
  return client.get(`/crew/members/${id}`)
}

export const createCrewMember = (data) => {
  return client.post('/crew/members', data)
}

export const updateCrewMember = (id, data) => {
  return client.patch(`/crew/members/${id}`, data)
}

export const deleteCrewMember = (id) => {
  return client.delete(`/crew/members/${id}`)
}

export const getNewMembers = () => {
  return client.get('/crew/members/new_members')
}

export const markRegistered = (id) => {
  return client.post(`/crew/members/${id}/mark_registered`)
}

// 배송원별 정산 내역 조회
export const getSettlementHistory = (id) => {
  return client.get(`/crew/members/${id}/settlement_history`)
}
