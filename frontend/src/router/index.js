import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const routes = [
  { path: '/login', name: 'Login', component: () => import('@/views/LoginView.vue'), meta: { requiresAuth: false } },
  { path: '/privacy', name: 'Privacy', component: () => import('@/views/PrivacyView.vue'), meta: { requiresAuth: false } },
  { path: '/', name: 'Home', component: () => import('@/views/HomeView.vue'), meta: { requiresAuth: true, adminOnly: true } },
  { path: '/dispatch', name: 'Dispatch', component: () => import('@/views/DispatchView.vue'), meta: { requiresAuth: true } },
  { path: '/crew', name: 'Crew', component: () => import('@/views/CrewView.vue'), meta: { requiresAuth: true } },
  { path: '/settlement', name: 'Settlement', component: () => import('@/views/SettlementView.vue'), meta: { requiresAuth: true, adminOnly: true } },
  { path: '/operations', name: 'Operations', component: () => import('@/views/OperationsView.vue'), meta: { requiresAuth: true } },
  { path: '/region', name: 'Region', component: () => import('@/views/RegionView.vue'), meta: { requiresAuth: true, adminOnly: true } },
  { path: '/:pathMatch(.*)*', redirect: '/' }
]

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes
})

router.beforeEach((to, from, next) => {
  const authStore = useAuthStore()

  if (to.meta.requiresAuth && !authStore.isAuthenticated) {
    next('/login')
  } else if (to.path === '/login' && authStore.isAuthenticated) {
    next(authStore.isAdmin ? '/' : '/dispatch')
  } else if (to.meta.adminOnly && !authStore.isAdmin) {
    next('/dispatch')
  } else {
    next()
  }
})

export default router
