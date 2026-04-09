import client from './client'

export const fetchRegions = () => {
  return client.get('/region')
}

export const getRegion = (id) => {
  return client.get(`/region/${id}`)
}

export const updatePrice = (regionId, priceData) => {
  return client.put(`/region/${regionId}/price`, priceData)
}

export const fetchTeams = () => {
  return client.get('/region/teams')
}

export const getTeam = (id) => {
  return client.get(`/region/teams/${id}`)
}

export const updateTeam = (id, teamData) => {
  return client.put(`/region/teams/${id}`, teamData)
}

export const bulkUpdatePrices = (priceList) => {
  return client.post('/region/bulk-prices', { prices: priceList })
}

export const downloadPriceTemplate = () => {
  return client.get('/region/template/prices', { responseType: 'blob' })
}
