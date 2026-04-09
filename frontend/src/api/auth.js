import client from './client'

export const login = (email, password) => {
  return client.post('/auth/login/', { email, password })
}

export const logout = () => {
  return client.post('/auth/logout/')
}

export const refreshToken = () => {
  return client.post('/auth/refresh/')
}

export const getProfile = () => {
  return client.get('/auth/profile/')
}
