export const DEFAULT_COMPANY_TABS = ['dispatch', 'crew', 'region']
export const OPTIONAL_COMPANY_TABS = ['dashboard', 'operations', 'settlement', 'inquiry', 'tracking', 'manpower']
export const ALL_COMPANY_TABS = [...DEFAULT_COMPANY_TABS, ...OPTIONAL_COMPANY_TABS]

export const COMPANY_APPS = {
  cheonha: {
    code: 'cheonha',
    routeBase: '/cheonha',
    loginPath: '/cheonha/login',
    dashboardPath: '/cheonha/dashboard',
    dispatchPath: '/cheonha/dispatch',
    displayName: '천하운수',
    dashboardTitle: 'CLEVER 천하운수 정산관리 대시보드',
    portalLinkLabel: '천하운수 페이지',
    mark: 'CH',
    enabledTabs: ALL_COMPANY_TABS,
    isStatic: true,
  },
  abc: {
    code: 'abc',
    routeBase: '/ABC',
    loginPath: '/ABC/login',
    dashboardPath: '/ABC/dashboard',
    dispatchPath: '/ABC/dispatch',
    displayName: 'ABC',
    dashboardTitle: 'CLEVER ABC 정산관리 대시보드',
    portalLinkLabel: 'ABC 페이지',
    mark: 'AB',
    enabledTabs: ALL_COMPANY_TABS,
    isStatic: true,
  },
}

const runtimeCompanyApps = {}

export const COMPANY_APP_LIST = Object.values(COMPANY_APPS)
export const COMPANY_APP_STORAGE_KEY = 'clever:selected-company-app'

export function normalizeCompanyAppCode(code = 'cheonha') {
  return String(code || '').trim().toLowerCase() || 'cheonha'
}

export function makeDynamicCompanyRouteBase(code) {
  return `/company/${encodeURIComponent(normalizeCompanyAppCode(code))}`
}

export function buildCompanyApp(config = {}) {
  const code = normalizeCompanyAppCode(config.code)
  const staticApp = COMPANY_APPS[code]
  if (staticApp) {
    return {
      ...staticApp,
      displayName: config.name || staticApp.displayName,
      enabledTabs: config.enabled_tabs || config.enabledTabs || staticApp.enabledTabs,
      enabledShippers: config.enabled_shippers || config.enabledShippers || ['kurly'],
      enabledShipperTabs: config.enabled_shipper_tabs || config.enabledShipperTabs || {},
      status: config.status || staticApp.status || 'ACTIVE',
    }
  }

  const routeBase = makeDynamicCompanyRouteBase(code)
  const displayName = config.name || code.toUpperCase()
  return {
    code,
    routeBase,
    loginPath: `${routeBase}/login`,
    dashboardPath: `${routeBase}/dashboard`,
    dispatchPath: `${routeBase}/dispatch`,
    displayName,
    dashboardTitle: `CLEVER ${displayName} 정산관리 대시보드`,
    portalLinkLabel: `${displayName} 페이지`,
    mark: String(displayName || code).slice(0, 2).toUpperCase(),
    enabledTabs: config.enabled_tabs || config.enabledTabs || DEFAULT_COMPANY_TABS,
    enabledShippers: config.enabled_shippers || config.enabledShippers || ['kurly'],
    enabledShipperTabs: config.enabled_shipper_tabs || config.enabledShipperTabs || {},
    status: config.status || 'ACTIVE',
    isStatic: false,
  }
}

export function setRuntimeCompanyApps(companies = []) {
  for (const company of companies || []) {
    if (!company?.code) continue
    runtimeCompanyApps[normalizeCompanyAppCode(company.code)] = buildCompanyApp(company)
  }
}

export function setRuntimeCompanyApp(company) {
  if (!company?.code) return
  runtimeCompanyApps[normalizeCompanyAppCode(company.code)] = buildCompanyApp(company)
}

export function getCompanyApp(code = 'cheonha') {
  const normalized = normalizeCompanyAppCode(code)
  return runtimeCompanyApps[normalized] || COMPANY_APPS[normalized] || buildCompanyApp({ code: normalized })
}

export function inferCompanyAppCodeFromPath(path = '') {
  const value = String(path || '')
  const dynamicMatch = value.match(/^\/company\/([^/]+)/)
  if (dynamicMatch?.[1]) return normalizeCompanyAppCode(decodeURIComponent(dynamicMatch[1]))
  if (value.startsWith('/ABC')) return 'abc'
  return 'cheonha'
}

export function getCompanyAppFromRoute(route) {
  return getCompanyApp(route?.params?.companyCode || route?.meta?.companyApp || inferCompanyAppCodeFromPath(route?.path))
}

export function getSelectedCompanyAppCode() {
  if (typeof window === 'undefined') return 'cheonha'
  return getCompanyApp(localStorage.getItem(COMPANY_APP_STORAGE_KEY) || 'cheonha').code
}

export function setSelectedCompanyAppCode(code) {
  if (typeof window === 'undefined') return
  localStorage.setItem(COMPANY_APP_STORAGE_KEY, getCompanyApp(code).code)
}
