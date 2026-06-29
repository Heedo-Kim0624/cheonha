import client from './client'

export const fetchPointItems = () =>
  client.get('/points/items/')

export const createPointItem = (payload) =>
  client.post('/points/items/', payload)

export const updatePointItem = (itemId, payload) =>
  client.patch(`/points/items/${itemId}/`, payload)

export const deletePointItem = (itemId) =>
  client.delete(`/points/items/${itemId}/`)

export const fetchPointSummaries = (params = {}) =>
  client.get('/points/summaries/', { params })

export const fetchCrewPointDetail = (crewId) =>
  client.get(`/points/crew/${crewId}/`)

export const setCrewPointBalance = (crewId, payload) =>
  client.post(`/points/crew/${crewId}/set-balance/`, payload)

export const confirmPointRedemption = (redemptionId) =>
  client.post(`/points/redemptions/${redemptionId}/confirm/`)

export const cancelPointRedemption = (redemptionId, payload = {}) =>
  client.post(`/points/redemptions/${redemptionId}/cancel/`, payload)
