import client from './client'

export const listTerritories = (params = {}) => client.get('/territory/territories/', { params })
export const createTerritory = (data) => client.post('/territory/territories/', data)
export const updateTerritory = (id, data) => client.patch(`/territory/territories/${id}/`, data)
export const deleteTerritory = (id) => client.delete(`/territory/territories/${id}/`)
export const importTerritoryGeoJSON = (fileOrPayload) => {
  if (fileOrPayload instanceof File) {
    const fd = new FormData()
    fd.append('file', fileOrPayload)
    return client.post('/territory/territories/import_geojson/', fd, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  }
  return client.post('/territory/territories/import_geojson/', fileOrPayload)
}
export const territoryBoxSeries = (id) => client.get(`/territory/territories/${id}/box_series/`)
export const setTerritoryBoxes = (id, payload) => client.post(`/territory/territories/${id}/box_set/`, payload)
export const territoryCyclesInside = (id) => client.get(`/territory/territories/${id}/cycles_inside/`)
export const territoryNearbyManpower = (id, radius_m = 3000) =>
  client.get(`/territory/territories/${id}/nearby_manpower/`, { params: { radius_m } })
