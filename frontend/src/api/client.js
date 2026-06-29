import axios from 'axios'
import { useAuthStore } from '@/stores/auth'
import { publishWorkflowEvent } from '@/lib/workflowChannel'
import {
  inferCompanyAppCodeFromPath,
  getCompanyApp,
  getSelectedCompanyAppCode,
} from '@/utils/companyApp'

const baseURL = import.meta.env.VITE_API_BASE_URL || '/api/v1'
let workflowRequestSequence = 0

const client = axios.create({
  baseURL,
  headers: {
    'Content-Type': 'application/json',
  },
})

function resolveCompanyAppCodeForRequest() {
  if (typeof window === 'undefined') return 'cheonha'
  const path = window.location.pathname || ''
  if (path === '/' || path.startsWith('/portal')) {
    return getSelectedCompanyAppCode()
  }
  return inferCompanyAppCodeFromPath(path)
}

function normalizeRequestUrl(config) {
  try {
    const target = new URL(config.url, `${config.baseURL || baseURL}/`)
    return {
      fullUrl: target.toString(),
      path: target.pathname,
      query: target.search.replace(/^\?/, ''),
    }
  } catch (_error) {
    return {
      fullUrl: config.url || '',
      path: config.url || '',
      query: '',
    }
  }
}

function createWorkflowRequestId() {
  workflowRequestSequence += 1
  return `wf-${Date.now()}-${workflowRequestSequence}`
}

client.interceptors.request.use(
  (config) => {
    if (config.url && !config.url.endsWith('/') && !config.url.includes('?')) {
      config.url = `${config.url}/`
    }
    const authStore = useAuthStore()
    if (authStore.token) {
      config.headers.Authorization = `Bearer ${authStore.token}`
    }

    config.headers['X-Company-App'] = resolveCompanyAppCodeForRequest()

    const startedAt = Date.now()
    const workflowId = createWorkflowRequestId()
    const { fullUrl, path, query } = normalizeRequestUrl(config)
    config.metadata = {
      workflowId,
      startedAt,
      path,
      query,
      fullUrl,
    }

    publishWorkflowEvent({
      type: 'request-start',
      id: workflowId,
      method: String(config.method || 'GET').toUpperCase(),
      path,
      query,
      fullUrl,
      startedAt,
    })

    return config
  },
  (error) => Promise.reject(error),
)

client.interceptors.response.use(
  (response) => {
    const metadata = response.config?.metadata
    if (metadata) {
      publishWorkflowEvent({
        type: 'request-end',
        id: metadata.workflowId,
        method: String(response.config?.method || 'GET').toUpperCase(),
        path: metadata.path,
        query: metadata.query,
        fullUrl: metadata.fullUrl,
        startedAt: metadata.startedAt,
        endedAt: Date.now(),
        durationMs: Date.now() - metadata.startedAt,
        statusCode: response.status,
        ok: response.status < 400,
      })
    }
    return response
  },
  (error) => {
    const config = error.config || {}
    const metadata = config.metadata
    if (metadata) {
      publishWorkflowEvent({
        type: 'request-end',
        id: metadata.workflowId,
        method: String(config.method || 'GET').toUpperCase(),
        path: metadata.path,
        query: metadata.query,
        fullUrl: metadata.fullUrl,
        startedAt: metadata.startedAt,
        endedAt: Date.now(),
        durationMs: Date.now() - metadata.startedAt,
        statusCode: error.response?.status || 0,
        ok: false,
        errorText: error.message || 'Request failed',
      })
    }

    if (error.response?.status === 401) {
      const authStore = useAuthStore()
      authStore.logout()
      const companyCode = inferCompanyAppCodeFromPath(window.location.pathname)
      const companyApp = getCompanyApp(companyCode)
      window.location.href = window.location.pathname.startsWith('/portal') || window.location.pathname === '/'
        ? '/'
        : companyApp.loginPath
    }
    return Promise.reject(error)
  },
)

export default client
