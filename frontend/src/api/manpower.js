import client from './client'

export const listManpower = (params = {}) => client.get('/manpower/people/', { params })
export const createManpower = (data) => client.post('/manpower/people/', data)
export const updateManpower = (id, data) => client.patch(`/manpower/people/${id}/`, data)
export const deleteManpower = (id) => client.delete(`/manpower/people/${id}/`)
export const geocodeManpower = (id) => client.post(`/manpower/people/${id}/geocode/`)
export const geocodeAllManpower = (onlyMissing = true) =>
  client.post('/manpower/people/geocode_all/', { only_missing: onlyMissing })
export const importManpowerXlsx = (file) => {
  const fd = new FormData()
  fd.append('file', file)
  return client.post('/manpower/people/import_xlsx/', fd, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}
export const syncManpowerSheet = (url) =>
  client.post('/manpower/people/sync_sheet/', { url })
export const fetchManpowerSheet = () => client.get('/manpower/people/sheet/')
export const nearbyManpower = (lat, lon, radius_m = 3000) =>
  client.get('/manpower/people/nearby/', { params: { lat, lon, radius_m } })
