import client from './client'

export const COMPANY_TAB_OPTIONS = [
  { key: 'dashboard', label: '대시보드' },
  { key: 'operations', label: '운영현황' },
  { key: 'settlement', label: '정산처리' },
  { key: 'inquiry', label: '정산문의' },
  { key: 'tracking', label: '권역관리' },
  { key: 'manpower', label: '인력풀' },
]

export const DEFAULT_COMPANY_TABS = ['dispatch', 'crew', 'region']

export const DEFAULT_SHIPPER_CODES = ['kurly']

export const fetchCompanyApps = () =>
  client.get('/accounts/company-apps/')

export const fetchShippers = () =>
  client.get('/accounts/shippers/')

export const createShipper = (payload) =>
  client.post('/accounts/shippers/', payload)

export const updateShipper = (id, payload) =>
  client.patch(`/accounts/shippers/${id}/`, payload)

export const deleteShipper = (id) =>
  client.delete(`/accounts/shippers/${id}/`)

export const fetchPublicCompanyApps = () =>
  client.get('/accounts/company-apps/public/')

export const fetchPublicCompanyApp = (code) =>
  client.get(`/accounts/company-app-public/${encodeURIComponent(code)}/`)

export const createCompanyApp = (payload) =>
  client.post('/accounts/company-apps/', payload)

export const updateCompanyApp = (id, payload) =>
  client.patch(`/accounts/company-apps/${id}/`, payload)

export const approveCompanyApp = (id) =>
  client.post(`/accounts/company-apps/${id}/approve/`)

export const rejectCompanyApp = (id) =>
  client.post(`/accounts/company-apps/${id}/reject/`)

export const deleteCompanyApp = (id) =>
  client.delete(`/accounts/company-apps/${id}/`)

export const permanentlyDeleteCompanyApp = (id) =>
  client.delete(`/accounts/company-apps/${id}/permanent-delete/`)

export const restoreCompanyApp = (id) =>
  client.post(`/accounts/company-apps/${id}/restore/`)

export const rotateCompanySignupToken = (id) =>
  client.post(`/accounts/company-apps/${id}/rotate-signup-token/`)

export const fetchCompanySignup = (token) =>
  client.get(`/accounts/company-app-signup/${encodeURIComponent(token)}/`)

export const submitCompanySignup = (token, payload) =>
  client.post(`/accounts/company-app-signup/${encodeURIComponent(token)}/`, payload)

export const fetchCompanyUserSignup = (code) =>
  client.get(`/accounts/company-user-signup/${encodeURIComponent(code)}/`)

export const submitCompanyUserSignup = (code, payload) =>
  client.post(`/accounts/company-user-signup/${encodeURIComponent(code)}/`, payload)

export const fetchPendingCompanyUserSignups = () =>
  client.get('/accounts/company-user-signup-requests/')

export const approveCompanyUserSignup = (id) =>
  client.post(`/accounts/company-user-signup-requests/${id}/approve/`)

export const rejectCompanyUserSignup = (id) =>
  client.post(`/accounts/company-user-signup-requests/${id}/reject/`)
