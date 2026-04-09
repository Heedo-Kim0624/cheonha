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
