import client from './client'

export const uploadOneFiles = (files = [], params = {}) => {
  const formData = new FormData()
  for (const file of files) formData.append('files', file)
  return client.post('/one/uploads/', formData, {
    params,
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}

export const fetchOneUploads = (params = {}) => {
  return client.get('/one/uploads/', { params })
}

export const deleteOneUpload = (uploadId, params = {}) => {
  return client.delete(`/one/uploads/${uploadId}/`, { params })
}

export const fetchOneSummary = (params = {}) => {
  return client.get('/one/summary/', { params })
}

export const fetchOneCollection = (params = {}) => {
  return client.get('/one/summary/collection/', { params })
}

export const downloadOneCollectionExcel = (params = {}) => {
  return client.get('/one/summary/collection-export/', { params, responseType: 'blob' })
}

export const fetchOneDrivers = (params = {}) => {
  return client.get('/one/drivers/', { params })
}

export const fetchOneDriverStatement = (driverId, params = {}) => {
  return client.get(`/one/drivers/${driverId}/statement/`, { params })
}

export const updateOneStatement = (statementId, payload = {}, params = {}) => {
  return client.patch(`/one/statements/${statementId}/`, payload, { params })
}

export const downloadOneStatementExcel = (statementId, params = {}) => {
  return client.get(`/one/statements/${statementId}/export.xlsx/`, { params, responseType: 'blob' })
}

export const downloadOneStatementPdf = (statementId, params = {}) => {
  return client.get(`/one/statements/${statementId}/export.pdf/`, { params, responseType: 'blob' })
}
