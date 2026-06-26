import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { COMPANY_APP_LIST, getCompanyApp } from '@/utils/companyApp'

const portalRoutes = [
  { path: '/', name: 'CleverPortal', component: () => import('@/views/CleverPortalAdminView.vue'), meta: { requiresAuth: false, portalTab: 'operations' } },
  { path: '/portal/operations', name: 'CleverPortalOperations', component: () => import('@/views/CleverPortalAdminView.vue'), meta: { requiresAuth: false, portalTab: 'operations' } },
  { path: '/portal/revenue', name: 'CleverPortalRevenue', component: () => import('@/views/CleverPortalAdminView.vue'), meta: { requiresAuth: false, portalTab: 'revenue' } },
  { path: '/portal/companies', name: 'CleverPortalCompanies', component: () => import('@/views/CleverPortalAdminView.vue'), meta: { requiresAuth: false, portalTab: 'companies' } },
  { path: '/portal/work', redirect: '/portal/work/live' },
  { path: '/portal/work/live', name: 'CleverPortalWorkLive', component: () => import('@/views/CleverPortalAdminView.vue'), meta: { requiresAuth: false, portalTab: 'work', portalSubtab: 'live' } },
  { path: '/portal/work/csv', name: 'CleverPortalWorkCsv', component: () => import('@/views/CleverPortalAdminView.vue'), meta: { requiresAuth: false, portalTab: 'work', portalSubtab: 'csv' } },
  { path: '/portal/work/legal-consents', name: 'CleverPortalWorkLegalConsents', component: () => import('@/views/CleverPortalAdminView.vue'), meta: { requiresAuth: false, portalTab: 'work', portalSubtab: 'legal-consents' } },
  { path: '/portal/tracking', redirect: '/portal/work/csv' },
  { path: '/portal/points', redirect: '/portal/points/summary' },
  { path: '/portal/points/summary', name: 'CleverPortalPointsSummary', component: () => import('@/views/CleverPortalAdminView.vue'), meta: { requiresAuth: false, portalTab: 'points', portalSubtab: 'summary' } },
  { path: '/portal/points/shop', name: 'CleverPortalPointsShop', component: () => import('@/views/CleverPortalAdminView.vue'), meta: { requiresAuth: false, portalTab: 'points', portalSubtab: 'shop' } },
  { path: '/portal/app', redirect: '/portal/app/messages' },
  { path: '/portal/app/messages', name: 'CleverPortalAppMessages', component: () => import('@/views/CleverPortalAdminView.vue'), meta: { requiresAuth: false, portalTab: 'app', portalSubtab: 'messages' } },
  { path: '/portal/vehicle', redirect: '/portal/vehicle/dashboard' },
  { path: '/portal/vehicle/dashboard', name: 'CleverPortalVehicleDashboard', component: () => import('@/views/FleetManagementView.vue'), meta: { requiresAuth: true, adminOnly: true, fleetTab: 'dashboard' } },
  { path: '/portal/vehicle/status', redirect: '/portal/vehicle/vehicles' },
  { path: '/portal/vehicle/vehicles', name: 'CleverPortalVehicleVehicles', component: () => import('@/views/FleetManagementView.vue'), meta: { requiresAuth: true, adminOnly: true, fleetTab: 'vehicles' } },
  { path: '/portal/vehicle/subscriptions', name: 'CleverPortalVehicleSubscriptions', component: () => import('@/views/FleetManagementView.vue'), meta: { requiresAuth: true, adminOnly: true, fleetTab: 'subscriptions' } },
  { path: '/portal/vehicle/subscription', redirect: '/portal/vehicle/subscriptions' },
  { path: '/portal/vehicle/returns', name: 'CleverPortalVehicleReturns', component: () => import('@/views/FleetManagementView.vue'), meta: { requiresAuth: true, adminOnly: true, fleetTab: 'returns' } },
  { path: '/portal/vehicle/insurance', name: 'CleverPortalVehicleInsurance', component: () => import('@/views/FleetManagementView.vue'), meta: { requiresAuth: true, adminOnly: true, fleetTab: 'insurance' } },
  { path: '/portal/vehicle/accidents', name: 'CleverPortalVehicleAccidents', component: () => import('@/views/FleetManagementView.vue'), meta: { requiresAuth: true, adminOnly: true, fleetTab: 'accidents' } },
  { path: '/portal/vehicle/upload', name: 'CleverPortalVehicleUpload', component: () => import('@/views/FleetManagementView.vue'), meta: { requiresAuth: true, adminOnly: true, fleetTab: 'upload' } },
  { path: '/portal/vehicle/calendar', redirect: '/portal/vehicle/dashboard' },
  { path: '/portal/vehicle/pit', redirect: '/portal/pit/status' },
  { path: '/portal/vehicle/as', redirect: '/portal/pit/as' },
  { path: '/portal/pit', redirect: '/portal/pit/status' },
  { path: '/portal/pit/status', name: 'CleverPortalPitStatus', component: () => import('@/views/CleverPortalAdminView.vue'), meta: { requiresAuth: false, portalTab: 'pit', portalSubtab: 'status' } },
  { path: '/portal/pit/calendar', name: 'CleverPortalPitCalendar', component: () => import('@/views/CleverPortalAdminView.vue'), meta: { requiresAuth: false, portalTab: 'pit', portalSubtab: 'calendar' } },
  { path: '/portal/pit/assignment', name: 'CleverPortalPitAssignment', component: () => import('@/views/CleverPortalAdminView.vue'), meta: { requiresAuth: false, portalTab: 'pit', portalSubtab: 'assignment' } },
  { path: '/portal/pit/as', name: 'CleverPortalPitAS', component: () => import('@/views/CleverPortalAdminView.vue'), meta: { requiresAuth: false, portalTab: 'pit', portalSubtab: 'as' } },
]

function companyMeta(companyCode, extra = {}) {
  const company = getCompanyApp(companyCode)
  return {
    companyApp: company.code,
    companyBase: company.routeBase,
    companyLoginPath: company.loginPath,
    ...extra,
  }
}

function createCompanyRoutes(companyCode) {
  const company = getCompanyApp(companyCode)
  const suffix = company.code === 'cheonha' ? '' : `-${company.code}`
  return [
    { path: company.routeBase, redirect: company.dashboardPath },
    { path: company.loginPath, name: `Login${suffix}`, component: () => import('@/views/LoginView.vue'), meta: companyMeta(company.code, { requiresAuth: false }) },
    { path: `${company.routeBase}/signup`, name: `CompanyUserSignup${suffix}`, component: () => import('@/views/CompanyUserSignupView.vue'), meta: companyMeta(company.code, { requiresAuth: false }) },
    { path: `${company.routeBase}/dashboard`, name: `Home${suffix}`, component: () => import('@/views/HomeView.vue'), meta: companyMeta(company.code, { requiresAuth: true, adminOnly: true }) },
    { path: `${company.routeBase}/dispatch`, name: `Dispatch${suffix}`, component: () => import('@/views/DispatchView.vue'), meta: companyMeta(company.code, { requiresAuth: true }) },
    { path: `${company.routeBase}/workflow`, name: `Workflow${suffix}`, component: () => import('@/views/WorkflowView.vue'), meta: companyMeta(company.code, { requiresAuth: false, adminOnly: false }) },
    { path: `${company.routeBase}/crew`, name: `Crew${suffix}`, component: () => import('@/views/CrewView.vue'), meta: companyMeta(company.code, { requiresAuth: true }) },
    { path: `${company.routeBase}/settlement`, name: `Settlement${suffix}`, component: () => import('@/views/SettlementView.vue'), meta: companyMeta(company.code, { requiresAuth: true, adminOnly: true }) },
    { path: `${company.routeBase}/operations`, name: `Operations${suffix}`, component: () => import('@/views/OperationsView.vue'), meta: companyMeta(company.code, { requiresAuth: true }) },
    { path: `${company.routeBase}/inquiry`, name: `Inquiry${suffix}`, component: () => import('@/views/InquiryView.vue'), meta: companyMeta(company.code, { requiresAuth: true, adminOnly: true }) },
    { path: `${company.routeBase}/region`, name: `Region${suffix}`, component: () => import('@/views/RegionView.vue'), meta: companyMeta(company.code, { requiresAuth: true, adminOnly: true }) },
    { path: `${company.routeBase}/tracking`, name: `Tracking${suffix}`, component: () => import('@/views/TrackingView.vue'), meta: companyMeta(company.code, { requiresAuth: true }) },
    { path: `${company.routeBase}/territory`, redirect: `${company.routeBase}/tracking` },
    { path: `${company.routeBase}/manpower`, name: `Manpower${suffix}`, component: () => import('@/views/ManpowerView.vue'), meta: companyMeta(company.code, { requiresAuth: true }) },
  ]
}

function createDynamicCompanyRoutes() {
  return [
    { path: '/company/:companyCode', redirect: (to) => `/company/${to.params.companyCode}/dispatch` },
    { path: '/company/:companyCode/login', name: 'Login-dynamic', component: () => import('@/views/LoginView.vue'), meta: { requiresAuth: false, dynamicCompanyApp: true } },
    { path: '/company/:companyCode/signup', name: 'CompanyUserSignup-dynamic', component: () => import('@/views/CompanyUserSignupView.vue'), meta: { requiresAuth: false, dynamicCompanyApp: true } },
    { path: '/company/:companyCode/dashboard', name: 'Home-dynamic', component: () => import('@/views/HomeView.vue'), meta: { requiresAuth: true, adminOnly: true, dynamicCompanyApp: true } },
    { path: '/company/:companyCode/dispatch', name: 'Dispatch-dynamic', component: () => import('@/views/DispatchView.vue'), meta: { requiresAuth: true, dynamicCompanyApp: true } },
    { path: '/company/:companyCode/workflow', name: 'Workflow-dynamic', component: () => import('@/views/WorkflowView.vue'), meta: { requiresAuth: false, adminOnly: false, dynamicCompanyApp: true } },
    { path: '/company/:companyCode/crew', name: 'Crew-dynamic', component: () => import('@/views/CrewView.vue'), meta: { requiresAuth: true, dynamicCompanyApp: true } },
    { path: '/company/:companyCode/settlement', name: 'Settlement-dynamic', component: () => import('@/views/SettlementView.vue'), meta: { requiresAuth: true, adminOnly: true, dynamicCompanyApp: true } },
    { path: '/company/:companyCode/operations', name: 'Operations-dynamic', component: () => import('@/views/OperationsView.vue'), meta: { requiresAuth: true, dynamicCompanyApp: true } },
    { path: '/company/:companyCode/inquiry', name: 'Inquiry-dynamic', component: () => import('@/views/InquiryView.vue'), meta: { requiresAuth: true, adminOnly: true, dynamicCompanyApp: true } },
    { path: '/company/:companyCode/region', name: 'Region-dynamic', component: () => import('@/views/RegionView.vue'), meta: { requiresAuth: true, adminOnly: true, dynamicCompanyApp: true } },
    { path: '/company/:companyCode/tracking', name: 'Tracking-dynamic', component: () => import('@/views/TrackingView.vue'), meta: { requiresAuth: true, dynamicCompanyApp: true } },
    { path: '/company/:companyCode/territory', redirect: (to) => `/company/${to.params.companyCode}/tracking` },
    { path: '/company/:companyCode/manpower', name: 'Manpower-dynamic', component: () => import('@/views/ManpowerView.vue'), meta: { requiresAuth: true, dynamicCompanyApp: true } },
  ]
}

const companyRoutes = COMPANY_APP_LIST.flatMap((company) => createCompanyRoutes(company.code))

const routes = [
  ...portalRoutes,
  { path: '/login', redirect: getCompanyApp('cheonha').loginPath },
  { path: '/privacy', name: 'Privacy', component: () => import('@/views/PrivacyView.vue'), meta: { requiresAuth: false } },
  { path: '/privacy-policy', redirect: '/privacy', meta: { requiresAuth: false } },
  { path: '/terms', name: 'Terms', component: () => import('@/views/TermsView.vue'), meta: { requiresAuth: false } },
  { path: '/driver-terms', name: 'DriverTerms', component: () => import('@/views/DriverTermsView.vue'), meta: { requiresAuth: false } },
  { path: '/location-terms', name: 'LocationTerms', component: () => import('@/views/LocationTermsView.vue'), meta: { requiresAuth: false } },
  { path: '/data-processing', name: 'DataProcessing', component: () => import('@/views/DataProcessingView.vue'), meta: { requiresAuth: false } },
  { path: '/marketing-consent', name: 'MarketingConsent', component: () => import('@/views/MarketingConsentView.vue'), meta: { requiresAuth: false } },
  { path: '/company-signup/:token', name: 'CompanySignup', component: () => import('@/views/CompanySignupView.vue'), meta: { requiresAuth: false } },
  { path: '/account-deletion', name: 'AccountDeletion', component: () => import('@/views/AccountDeletionView.vue'), meta: { requiresAuth: false } },
  ...companyRoutes,
  ...createDynamicCompanyRoutes(),
  { path: '/dashboard', redirect: getCompanyApp('cheonha').dashboardPath },
  { path: '/dispatch', redirect: `${getCompanyApp('cheonha').routeBase}/dispatch` },
  { path: '/workflow', redirect: `${getCompanyApp('cheonha').routeBase}/workflow` },
  { path: '/crew', redirect: `${getCompanyApp('cheonha').routeBase}/crew` },
  { path: '/settlement', redirect: `${getCompanyApp('cheonha').routeBase}/settlement` },
  { path: '/operations', redirect: `${getCompanyApp('cheonha').routeBase}/operations` },
  { path: '/inquiry', redirect: `${getCompanyApp('cheonha').routeBase}/inquiry` },
  { path: '/region', redirect: `${getCompanyApp('cheonha').routeBase}/region` },
  { path: '/tracking', redirect: `${getCompanyApp('cheonha').routeBase}/tracking` },
  { path: '/territory', redirect: `${getCompanyApp('cheonha').routeBase}/tracking` },
  { path: '/manpower', redirect: `${getCompanyApp('cheonha').routeBase}/manpower` },
  { path: '/:pathMatch(.*)*', redirect: '/' },
]

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes,
  scrollBehavior(to, from, savedPosition) {
    if (savedPosition) return savedPosition
    if (to.hash) {
      return new Promise((resolve) => {
        setTimeout(() => {
          resolve({
            el: decodeURIComponent(to.hash),
            top: 24,
            behavior: 'smooth',
          })
        }, 120)
      })
    }
    return { top: 0 }
  },
})

router.beforeEach((to, from, next) => {
  const authStore = useAuthStore()
  const company = getCompanyApp(to.params.companyCode || to.meta.companyApp || 'cheonha')

  if (to.meta.requiresAuth && !authStore.isAuthenticated) {
    next(company.loginPath)
    return
  }

  if (to.path === company.loginPath && authStore.isAuthenticated) {
    const adminLandingPath = company.enabledTabs?.includes('dashboard') ? company.dashboardPath : company.dispatchPath
    next(authStore.isAdmin ? adminLandingPath : company.dispatchPath)
    return
  }

  if (to.meta.adminOnly && !authStore.isAdmin) {
    next(company.dispatchPath)
    return
  }

  next()
})

export default router
