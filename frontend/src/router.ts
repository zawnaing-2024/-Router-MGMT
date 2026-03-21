import { createRouter, createWebHistory } from 'vue-router'
const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      redirect: '/dashboard'
    },
    {
      path: '/dashboard',
      name: 'dashboard',
      component: () => import('@/views/DashboardView.vue')
    },
    {
      path: '/routers',
      name: 'routers',
      component: () => import('@/views/RoutersView.vue')
    },
    {
      path: '/routers/:id',
      name: 'router-detail',
      component: () => import('@/views/RouterDetailView.vue')
    },
    {
      path: '/backups',
      name: 'backups',
      component: () => import('@/views/BackupsView.vue')
    },
    {
      path: '/templates',
      name: 'templates',
      component: () => import('@/views/TemplatesView.vue')
    },
    {
      path: '/jobs',
      name: 'jobs',
      component: () => import('@/views/JobsView.vue')
    },
    {
      path: '/terminal',
      name: 'terminal-select',
      component: () => import('@/views/TerminalSelectView.vue')
    },
    {
      path: '/terminal/:routerId',
      name: 'terminal',
      component: () => import('@/views/TerminalView.vue')
    },
    {
      path: '/groups',
      name: 'groups',
      component: () => import('@/views/GroupsView.vue')
    },
    {
      path: '/batch',
      name: 'batch',
      component: () => import('@/views/BatchView.vue')
    },
    {
      path: '/reports',
      name: 'reports',
      component: () => import('@/views/ReportsView.vue')
    },
    {
      path: '/audit',
      name: 'audit',
      component: () => import('@/views/AuditView.vue')
    },
    {
      path: '/logs',
      name: 'logs',
      component: () => import('@/views/LogsView.vue')
    },
    {
      path: '/notifications',
      name: 'notifications',
      component: () => import('@/views/NotificationsView.vue')
    },
    {
      path: '/remediation',
      name: 'remediation',
      component: () => import('@/views/RemediationView.vue')
    },
    {
      path: '/settings',
      name: 'settings',
      component: () => import('@/views/SettingsView.vue')
    }
  ]
})
export default router
