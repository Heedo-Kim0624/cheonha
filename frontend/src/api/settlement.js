import client from './client'

export const fetchSettlements = (filters = {}) => {
  return client.get('/settlement/settlements', { params: filters })
}

export const getSettlement = (id) => {
  return client.get(`/settlement/settlements/${id}`)
}

export const createSettlement = (settlementData) => {
  return client.post('/settlement/settlements', settlementData)
}

export const getSettlementDetails = (id) => {
  return client.get('/settlement/details', { params: { settlement_id: id } })
}

export const exportSettlement = (id) => {
  return client.get(`/settlement/settlements/${id}/export`, { responseType: 'blob' })
}

export const fetchSettlementWebOverview = (params = {}) => {
  return client.get('/settlement/settlements/web_overview/', { params })
}

export const fetchSettlementDetailGroups = (id) => {
  return client.get(`/settlement/settlements/${id}/web-detail-groups/`)
}

export const fetchSettlementCrewHistory = (params = {}) => {
  return client.get('/settlement/settlements/web-crew-history/', { params })
}

export const updateSettlementDetail = (id, data = {}) => {
  return client.patch(`/settlement/details/${id}`, data)
}

export const recalcSettlement = (id) => {
  return client.post(`/settlement/settlements/${id}/recalc/`)
}
