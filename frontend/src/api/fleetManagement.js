import client from './client'

const VM = '/vehicle'

export const fetchFleetSite = (params = {}) =>
  client.get(`${VM}/fleet-site/`, { params })

export const createFleetReplacement = (payload) =>
  client.post(`${VM}/fleet-site/replacement/`, payload)

export const uploadFleetBulkData = (formData, params = {}) =>
  client.post(`${VM}/fleet-site/bulk-import/`, formData, {
    params,
    headers: { 'Content-Type': 'multipart/form-data' },
  })

export const createFleetVehicle = (payload) =>
  client.post(`${VM}/vehicles/fleet-create/`, payload)

export const updateFleetVehicleInfo = (vehicleId, payload) =>
  client.patch(`${VM}/vehicles/${vehicleId}/fleet-info/`, payload)

export const updateFleetVehicleStatus = (vehicleId, payload) =>
  client.patch(`${VM}/vehicles/${vehicleId}/status/`, payload)

export const deleteFleetVehicle = (vehicleId) =>
  client.delete(`${VM}/vehicles/${vehicleId}/fleet-delete/`)

export const updateFleetRecord = (recordId, payload) =>
  client.patch(`${VM}/fleet-records/${recordId}/`, payload)

export const updateFleetRecordStatus = (recordId, payload) =>
  client.patch(`${VM}/fleet-records/${recordId}/status/`, payload)

export const createFleetDocument = (payload) =>
  client.post(`${VM}/fleet-documents/`, payload)

export const updateFleetDocument = (documentId, payload) =>
  client.patch(`${VM}/fleet-documents/${documentId}/`, payload)

export const deleteFleetDocument = (documentId) =>
  client.delete(`${VM}/fleet-documents/${documentId}/`)

export const createFleetSubscription = (payload) =>
  client.post(`${VM}/fleet-subscriptions/`, payload)

export const updateFleetSubscription = (subscriptionId, payload) =>
  client.patch(`${VM}/fleet-subscriptions/${subscriptionId}/`, payload)

export const fetchFleetMonthlyBilling = (params = {}) =>
  client.get(`${VM}/fleet-subscriptions/monthly-billing/`, { params })

export const downloadFleetMonthlyBilling = (params = {}) =>
  client.get(`${VM}/fleet-subscriptions/monthly-billing-export/`, {
    params,
    responseType: 'blob',
  })

export const createFleetReturn = (payload) =>
  client.post(`${VM}/fleet-returns/`, payload)

export const updateFleetReturn = (returnId, payload) =>
  client.patch(`${VM}/fleet-returns/${returnId}/`, payload)

export const uploadFleetReturnPhoto = (returnId, formData) =>
  client.post(`${VM}/fleet-returns/${returnId}/photos/`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })

export const createFleetInsurance = (payload) =>
  client.post(`${VM}/fleet-insurances/`, payload)

export const updateFleetInsurance = (insuranceId, payload) =>
  client.patch(`${VM}/fleet-insurances/${insuranceId}/`, payload)

export const deleteFleetInsurance = (insuranceId) =>
  client.delete(`${VM}/fleet-insurances/${insuranceId}/`)

export const createFleetInspection = (payload) =>
  client.post(`${VM}/fleet-inspections/`, payload)

export const updateFleetInspection = (inspectionId, payload) =>
  client.patch(`${VM}/fleet-inspections/${inspectionId}/`, payload)

export const deleteFleetInspection = (inspectionId) =>
  client.delete(`${VM}/fleet-inspections/${inspectionId}/`)

export const updateFleetAccident = (accidentId, payload) =>
  client.patch(`${VM}/fleet-accidents/${accidentId}/`, payload)

export const uploadFleetAccidentHistory = (formData, params = {}) =>
  client.post(`${VM}/fleet-accidents/upload-history/`, formData, {
    params,
    headers: { 'Content-Type': 'multipart/form-data' },
  })

export const downloadFleetAccidentTemplate = (params = {}) =>
  client.get(`${VM}/fleet-accidents/upload-template/`, {
    params,
    responseType: 'blob',
  })

export const createFleetProfitAdjustment = (payload) =>
  client.post(`${VM}/fleet-profit-adjustments/`, payload)

export const updateFleetProfitAdjustment = (adjustmentId, payload) =>
  client.patch(`${VM}/fleet-profit-adjustments/${adjustmentId}/`, payload)

export const deleteFleetProfitAdjustment = (adjustmentId) =>
  client.delete(`${VM}/fleet-profit-adjustments/${adjustmentId}/`)

export const recalculateFleetProfit = (payload = {}) =>
  client.post(`${VM}/fleet-profit-snapshots/recalculate/`, payload)

export const closeFleetMonth = (payload = {}) =>
  client.post(`${VM}/fleet-monthly-closes/close/`, payload)

export const reopenFleetMonth = (payload = {}) =>
  client.post(`${VM}/fleet-monthly-closes/reopen/`, payload)
