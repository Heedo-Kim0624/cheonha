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

export const getCrewMonthlySettlement = (id, params = {}) => {
  return client.get(`/crew/members/${id}/monthly-settlement`, { params })
}

export const setCrewInsurancePercent = (id, data = {}) => {
  return client.post(`/crew/members/${id}/set-insurance-percent`, data)
}

export const fetchYongchaSummary = (params = {}) => {
  return client.get('/crew/members/yongcha_summary', { params })
}

export const getYongchaDaily = (id, params = {}) => {
  return client.get(`/crew/members/${id}/yongcha_daily`, { params })
}

export const convertToRegular = (id, data = {}) => {
  return client.post(`/crew/members/${id}/convert_to_regular`, data)
}

export const convertToYongcha = (id, data = {}) => {
  return client.post(`/crew/members/${id}/convert_to_yongcha`, data)
}

export const setRoundYongcha = (id, data = {}) => {
  return client.post(`/crew/members/${id}/set_round_yongcha`, data)
}

export const setRegularFixedPay = (id, data = {}) => {
  return client.post(`/crew/members/${id}/set_regular_fixed_pay`, data)
}

export const setYongchaPayGroup = (id, data = {}) => {
  return client.post(`/crew/members/${id}/set_yongcha_pay_group`, data)
}

export const bulkSetYongchaPayGroup = (data = {}) => {
  return client.post('/crew/members/bulk-set-yongcha-pay-group/', data)
}

export const fetchYongchaPayGroups = (params = {}) => {
  return client.get('/crew/yongcha-pay-groups', { params })
}

export const createYongchaPayGroup = (data = {}) => {
  return client.post('/crew/yongcha-pay-groups', data)
}

export const updateYongchaPayGroup = (id, data = {}) => {
  return client.patch(`/crew/yongcha-pay-groups/${id}`, data)
}

export const deleteYongchaPayGroup = (id) => {
  return client.delete(`/crew/yongcha-pay-groups/${id}`)
}

export const getYongchaPayGroupSettlementSummary = (id, params = {}) => {
  return client.get(`/crew/yongcha-pay-groups/${id}/settlement-summary/`, { params })
}
