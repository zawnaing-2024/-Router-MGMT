import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/login',
      name: 'login',
      component: () => import('@/views/LoginView.vue')
    },
    {
      path: '/',
      redirect: '/dashboard'
    },
    {
      path: '/dashboard',
      name: 'dashboard',
      component: () => import('@/views/DashboardView.vue'),
      meta: { requiresAuth: true }
    },
    {
      path: '/routers',
      name: 'routers',
      component: () => import('@/views/RoutersView.vue'),
      meta: { requiresAuth: true }
    },
    {
      path: '/routers/:id',
      name: 'router-detail',
      component: () => import('@/views/RouterDetailView.vue'),
      meta: { requiresAuth: true }
    },
    {
      path: '/backups',
      name: 'backups',
      component: () => import('@/views/BackupsView.vue'),
      meta: { requiresAuth: true }
    },
    {
      path: '/templates',
      name: 'templates',
      component: () => import('@/views/TemplatesView.vue'),
      meta: { requiresAuth: true }
    },
    {
      path: '/jobs',
      name: 'jobs',
      component: () => import('@/views/JobsView.vue'),
      meta: { requiresAuth: true }
    },
    {
      path: '/terminal',
      name: 'terminal-select',
      component: () => import('@/views/TerminalSelectView.vue'),
      meta: { requiresAuth: true }
    },
    {
      path: '/terminal/:routerId',
      name: 'terminal',
      component: () => import('@/views/TerminalView.vue'),
      meta: { requiresAuth: true }
    },
    {
      path: '/groups',
      name: 'groups',
      component: () => import('@/views/GroupsView.vue'),
      meta: { requiresAuth: true }
    },
    {
      path: '/batch',
      name: 'batch',
      component: () => import('@/views/BatchView.vue'),
      meta: { requiresAuth: true }
    },
    {
      path: '/reports',
      name: 'reports',
      component: () => import('@/views/ReportsView.vue'),
      meta: { requiresAuth: true }
    },
    {
      path: '/audit',
      name: 'audit',
      component: () => import('@/views/AuditView.vue'),
      meta: { requiresAuth: true }
    },
    {
      path: '/logs',
      name: 'logs',
      component: () => import('@/views/LogsView.vue'),
      meta: { requiresAuth: true }
    },
    {
      path: '/notifications',
      name: 'notifications',
      component: () => import('@/views/NotificationsView.vue'),
      meta: { requiresAuth: true }
    },
    {
      path: '/remediation',
      name: 'remediation',
      component: () => import('@/views/RemediationView.vue'),
      meta: { requiresAuth: true }
    },
    {
      path: '/settings',
      name: 'settings',
      component: () => import('@/views/SettingsView.vue'),
      meta: { requiresAuth: true }
    }
  ]
})

router.beforeEach((to, from, next) => {
  const token = localStorage.getItem('token')
  if (to.meta.requiresAuth && !token) {
    next('/login')
  } else if (to.path === '/login' && token) {
    next('/dashboard')
  } else {
    next()
  }
})

export default router
