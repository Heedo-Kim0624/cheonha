import client from './client'

const VM = '/vehicle'

// ── Companies ────────────────────────────────────────────────────────────────
export const fetchCompanies = () => client.get(`${VM}/companies/`)

// ── Vehicles (전체 차량현황) ────────────────────────────────────────────────
export const fetchVehicles = (params = {}) =>
  client.get(`${VM}/vehicles/`, { params })

export const fetchVehicleStats = (params = {}) =>
  client.get(`${VM}/vehicles/stats/`, { params })

export const createVehicle = (data) => client.post(`${VM}/vehicles/`, data)
export const updateVehicle = (id, data) => client.patch(`${VM}/vehicles/${id}/`, data)
export const deleteVehicle = (id) => client.delete(`${VM}/vehicles/${id}/`)
export const uploadVehicleRegistrationCertificate = (id, file) => {
  const formData = new FormData()
  formData.append('file', file)
  return client.post(`${VM}/vehicles/${id}/registration-certificate/`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}
export const deleteVehicleRegistrationCertificate = (id) =>
  client.delete(`${VM}/vehicles/${id}/registration-certificate/`)

export const fetchVehicleEvdash = (id) =>
  client.get(`${VM}/vehicles/${id}/evdash/`)

// ── Pit Records (피트 차량현황) ─────────────────────────────────────────────
export const fetchPitRecords = (params = {}) =>
  client.get(`${VM}/pit-records/`, { params })

export const createPitRecord = (data) => client.post(`${VM}/pit-records/`, data)
export const updatePitRecord = (id, data) => client.patch(`${VM}/pit-records/${id}/`, data)
export const deletePitRecord = (id) => client.delete(`${VM}/pit-records/${id}/`)

// ── Calendar (통합 일정) ────────────────────────────────────────────────────
export const fetchCalendarEvents = (params = {}) =>
  client.get(`${VM}/calendar/`, { params })

export const createCalendarEvent = (data) => client.post(`${VM}/calendar/`, data)
export const updateCalendarEvent = (id, data) => client.patch(`${VM}/calendar/${id}/`, data)
export const deleteCalendarEvent = (id) => client.delete(`${VM}/calendar/${id}/`)

// ── Subscription Requests (구독 요청) ───────────────────────────────────────
export const fetchSubscriptions = (params = {}) =>
  client.get(`${VM}/subscriptions/`, { params })

export const fetchSubscription = (id) => client.get(`${VM}/subscriptions/${id}/`)

export const approveSubscription = (id) =>
  client.post(`${VM}/subscriptions/${id}/approve/`)

export const rejectSubscription = (id, payload = {}) =>
  client.post(`${VM}/subscriptions/${id}/reject/`, payload)

export const assignSubscriptionVehicles = (id, vehicleIds) =>
  client.post(`${VM}/subscriptions/${id}/assign/`, { vehicle_ids: vehicleIds })

export const completeSubscription = (id) =>
  client.post(`${VM}/subscriptions/${id}/complete/`)

// ── Return Requests (구독 반납) ─────────────────────────────────────────────
export const fetchReturns = (params = {}) =>
  client.get(`${VM}/returns/`, { params })

export const fetchReturn = (id) => client.get(`${VM}/returns/${id}/`)

export const confirmReturn = (id, payload) =>
  client.post(`${VM}/returns/${id}/confirm/`, payload)

export const adjustReturn = (id, payload) =>
  client.post(`${VM}/returns/${id}/adjust/`, payload)

// ── A/S Requests ────────────────────────────────────────────────────────────
export const fetchASRequests = (params = {}) =>
  client.get(`${VM}/as-requests/`, { params })

export const fetchASRequest = (id) => client.get(`${VM}/as-requests/${id}/`)

export const completeASRequest = (id, payload) =>
  client.post(`${VM}/as-requests/${id}/complete/`, payload)
