import client from './client'

export const fetchLiveWorkStatuses = (params = {}) =>
  client.get('/tracking/live-status/', { params })

export const fetchTrackingUsageOverview = (params = {}) =>
  client.get('/tracking/usage-overview/', { params })

export const fetchLegalConsentMatrix = (params = {}) =>
  client.get('/tracking/legal-consent-matrix/', { params })

export const fetchTrackingSessions = (params = {}) =>
  client.get('/tracking/sessions/', { params })

export const fetchTrackingSession = (id) =>
  client.get(`/tracking/sessions/${id}/`)

export const fetchSessionPoints = (id) =>
  client.get(`/tracking/sessions/${id}/points/`)

export const fetchSessionCaptures = (id) =>
  client.get(`/tracking/sessions/${id}/captures/`)

export const fetchSessionCycles = (id) =>
  client.get(`/tracking/sessions/${id}/cycles/`)

export const downloadTrackingCsv = (id) =>
  client.get(`/tracking/sessions/${id}/download_csv/`, { responseType: 'blob' })

export const fetchAvailableDates = (params = {}) =>
  client.get('/tracking/sessions/available_dates/', { params })

export const deleteTrackingSession = (id) =>
  client.delete(`/tracking/sessions/${id}/`)

export const bulkDeleteTrackingSessions = (params = {}) =>
  client.delete('/tracking/sessions/bulk_delete/', { params })
