import client from './client'

export const fetchPartners = () => {
  return client.get('/partner')
}

export const getPartner = (id) => {
  return client.get(`/partner/${id}`)
}

export const createPartner = (partnerData) => {
  return client.post('/partner', partnerData)
}

export const updatePartner = (id, partnerData) => {
  return client.put(`/partner/${id}`, partnerData)
}

export const deletePartner = (id) => {
  return client.delete(`/partner/${id}`)
}
