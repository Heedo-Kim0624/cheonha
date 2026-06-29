import client from './client'

export const fetchMobileAppConfig = () =>
  client.get('/mobile/admin/app-config/')

export const updateMobileAppConfig = (payload) =>
  client.put('/mobile/admin/app-config/', payload)
