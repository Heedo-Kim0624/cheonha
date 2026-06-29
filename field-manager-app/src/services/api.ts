import Constants from 'expo-constants'
import * as SecureStore from 'expo-secure-store'

const RAW_BASE: string =
  (Constants.expoConfig?.extra as any)?.apiBaseUrl ||
  'http://43.201.160.163/api/v1'

const BASE = RAW_BASE.replace(/\/+$/, '')
const TOKEN_KEY = 'fm_token'
const IDENTITY_KEY = 'fm_identity'
const DEFAULT_PIN = '2580'
const FETCH_TIMEOUT_MS = 15000
const REQUEST_TIMEOUT_MESSAGE = '\uC11C\uBC84 \uC751\uB2F5 \uC2DC\uAC04\uC774 \uCD08\uACFC\uB418\uC5C8\uC2B5\uB2C8\uB2E4. \uC11C\uBC84 \uC8FC\uC18C\uC640 \uB124\uD2B8\uC6CC\uD06C \uC0C1\uD0DC\uB97C \uD655\uC778\uD574\uC8FC\uC138\uC694.'

let cachedToken: string | null = null
let cachedIdentity: Identity | null = null

export interface Identity {
  company_code: 'YUHAN' | 'CHEONHA' | 'PERSONAL'
  team_code: string
  phone: string
}

export interface LocalImageFile {
  uri: string
  name?: string
  type?: string
}

export interface RequestHistoryResponse {
  subscription_requests: Array<{
    id: number
    requested_date: string
    quantity: number
    status: string
    status_display: string
    reject_reason: string
    created_at: string
    updated_at: string
  }>
  return_requests: Array<{
    id: number
    vehicle_number: string
    reason: string
    hope_date: string
    hope_time: string
    status: string
    status_display: string
    block_reason: string
    available_dates: string
    confirmed_date: string | null
    confirmed_time: string | null
    photo_count: number
    created_at: string
    updated_at: string
  }>
  as_requests: Array<{
    id: number
    vehicle_number: string
    owner_name: string
    owner_phone: string
    reason: string
    status: string
    status_display: string
    admin_comment: string
    created_at: string
    updated_at: string
  }>
}

export async function saveSession(token: string, identity: Identity) {
  cachedToken = token
  cachedIdentity = identity
  await SecureStore.setItemAsync(TOKEN_KEY, token)
  await SecureStore.setItemAsync(IDENTITY_KEY, JSON.stringify(identity))
}

export async function getToken(): Promise<string | null> {
  if (cachedToken) {
    return cachedToken
  }
  const token = await SecureStore.getItemAsync(TOKEN_KEY)
  cachedToken = token
  return token
}

export async function getIdentity(): Promise<Identity | null> {
  if (cachedIdentity) {
    return cachedIdentity
  }
  const value = await SecureStore.getItemAsync(IDENTITY_KEY)
  cachedIdentity = value ? JSON.parse(value) : null
  return cachedIdentity
}

export async function clearSession() {
  cachedToken = null
  cachedIdentity = null
  await SecureStore.deleteItemAsync(TOKEN_KEY)
  await SecureStore.deleteItemAsync(IDENTITY_KEY)
}

export async function hasStoredSession(): Promise<boolean> {
  const [token, identity] = await Promise.all([getToken(), getIdentity()])
  return Boolean(token && identity)
}

function buildUrl(path: string, query?: Record<string, string>) {
  const search = query
    ? `?${Object.entries(query)
        .map(([key, value]) => `${encodeURIComponent(key)}=${encodeURIComponent(value)}`)
        .join('&')}`
    : ''
  return `${BASE}${path}${search}`
}

async function performRequest<T = any>(
  method: 'GET' | 'POST',
  path: string,
  body?: any,
  query?: Record<string, string>,
  token?: string | null,
): Promise<{ data?: T; error?: string; status: number }> {
  const controller = typeof AbortController !== 'undefined' ? new AbortController() : null
  const timeoutId = controller ? setTimeout(() => controller.abort(), FETCH_TIMEOUT_MS) : null

  try {
    const isFormData = typeof FormData !== 'undefined' && body instanceof FormData
    const response = await fetch(buildUrl(path, query), {
      method,
      signal: controller?.signal,
      headers: {
        ...(isFormData ? {} : { 'Content-Type': 'application/json' }),
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: body ? (isFormData ? body : JSON.stringify(body)) : undefined,
    })
    let data: any = null
    try {
      data = await response.json()
    } catch {
      data = null
    }
    if (!response.ok) {
      const detail = data?.detail || (data ? Object.values(data)[0] : null) || `HTTP ${response.status}`
      return {
        error: typeof detail === 'string' ? detail : JSON.stringify(detail),
        status: response.status,
      }
    }
    return { data, status: response.status }
  } catch (error: any) {
    if (error?.name === 'AbortError') {
      return {
        error: REQUEST_TIMEOUT_MESSAGE,
        status: 0,
      }
    }
    if (error?.name === 'AbortError') {
      return {
        error: '서버 응답 시간이 초과되었습니다. 서버 주소와 네트워크 상태를 확인해주세요.',
        status: 0,
      }
    }
    const message = error?.message || '네트워크 연결 오류'
    return {
      error: `${message}. 서버 주소와 네트워크 상태를 확인해주세요.`,
      status: 0,
    }
  } finally {
    if (timeoutId) {
      clearTimeout(timeoutId)
    }
  }
}

async function refreshSessionToken(): Promise<string | null> {
  const identity = await getIdentity()
  if (!identity) {
    return null
  }

  const response = await performRequest<{ token: string; identity: Identity }>(
    'POST',
    '/field-manager/login/',
    {
      company_code: identity.company_code,
      team_code: identity.team_code,
      phone: identity.phone,
      pin: DEFAULT_PIN,
    },
  )

  if (!response.data?.token || !response.data.identity) {
    return null
  }

  await saveSession(response.data.token, response.data.identity)
  return response.data.token
}

async function request<T = any>(
  method: 'GET' | 'POST',
  path: string,
  body?: any,
  query?: Record<string, string>,
  triedRefresh = false,
): Promise<{ data?: T; error?: string; status: number }> {
  let token = await getToken()
  if (!token) {
    token = await refreshSessionToken()
  }

  if (!token) {
    return {
      error: '인증 정보가 없습니다. 다시 로그인해주세요.',
      status: 401,
    }
  }

  const response = await performRequest<T>(method, path, body, query, token)
  if (response.status !== 401 || triedRefresh) {
    return response
  }

  const refreshedToken = await refreshSessionToken()
  if (!refreshedToken) {
    return response
  }

  return request<T>(method, path, body, query, true)
}

export const api = {
  async login(company_code: string, team_code: string, phone: string, pin: string) {
    return performRequest<{ token: string; identity: Identity }>(
      'POST',
      '/field-manager/login/',
      { company_code, team_code, phone, pin },
    )
  },

  async createSubscriptionRequest(payload: {
    company_code: string
    team_code: string
    phone: string
    requested_date: string
    quantity: number
  }) {
    return request('POST', '/field-manager/subscription-requests/', payload)
  },

  async createReturnRequest(payload: {
    company_code: string
    team_code: string
    phone: string
    vehicle_number: string
    reason: string
    hope_date: string
    hope_time: string
    photos: {
      front: LocalImageFile
      rear: LocalImageFile
      left: LocalImageFile
      right: LocalImageFile
      dashboard: LocalImageFile
    }
  }) {
    const formData = new FormData()
    formData.append('company_code', payload.company_code)
    formData.append('team_code', payload.team_code)
    formData.append('phone', payload.phone)
    formData.append('vehicle_number', payload.vehicle_number)
    formData.append('reason', payload.reason)
    formData.append('hope_date', payload.hope_date)
    formData.append('hope_time', payload.hope_time)
    const appendPhoto = (fieldName: string, file: LocalImageFile) => {
      formData.append(fieldName, {
        uri: file.uri,
        name: file.name || `${fieldName}.jpg`,
        type: file.type || 'image/jpeg',
      } as any)
    }
    appendPhoto('front_photo', payload.photos.front)
    appendPhoto('rear_photo', payload.photos.rear)
    appendPhoto('left_photo', payload.photos.left)
    appendPhoto('right_photo', payload.photos.right)
    appendPhoto('dashboard_photo', payload.photos.dashboard)
    return request('POST', '/field-manager/return-requests/', formData)
  },

  async createASRequest(payload: {
    company_code: string
    team_code: string
    phone: string
    vehicle_number: string
    owner_name: string
    owner_phone: string
    reason: string
  }) {
    return request('POST', '/field-manager/as-requests/', payload)
  },

  async getBlockedDates(company_code: string, date_from?: string, date_to?: string) {
    const query: Record<string, string> = { company_code }
    if (date_from) query.date_from = date_from
    if (date_to) query.date_to = date_to
    return request<{ blocked_dates: string[] }>('GET', '/field-manager/blocked-dates/', undefined, query)
  },

  async getRequestHistory() {
    return request<RequestHistoryResponse>('GET', '/field-manager/request-history/')
  },
}
