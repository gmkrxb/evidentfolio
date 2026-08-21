import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useLocaleStore } from '@/stores/locale'
import { authApi } from '@/api/admin'

function publicChildren(prefix = '') {
  return [
    { path: '', name: `${prefix}home`, component: () => import('@/views/public/HomeView.vue') },
    { path: 'projects', name: `${prefix}projects`, component: () => import('@/views/public/ProjectsView.vue') },
    { path: 'projects/:uuid', name: `${prefix}project-detail`, component: () => import('@/views/public/ProjectDetailView.vue') },
    { path: 'resumes', name: `${prefix}resumes`, component: () => import('@/views/public/ResumesView.vue') },
    { path: 'certificates', name: `${prefix}certificates`, component: () => import('@/views/public/CertificatesView.vue') },
    { path: 'certificates/:uuid', name: `${prefix}certificate-detail`, component: () => import('@/views/public/CertificateDetailView.vue') },
    { path: 'contact', name: `${prefix}contact`, component: () => import('@/views/public/ContactView.vue') },
    { path: 'assets/:uuid', name: `${prefix}asset-viewer`, component: () => import('@/views/public/AssetViewerView.vue') },
  ]
}

const router = createRouter({
  history: createWebHistory(),
  scrollBehavior(to, from, savedPosition) {
    if (savedPosition) return savedPosition
    if (to.hash) return { el: to.hash, top: 90, behavior: 'smooth' }
    if (to.path !== from.path) return { top: 0 }
  },
  routes: [
    {
      path: '/',
      component: () => import('@/layouts/PublicLayout.vue'),
      meta: { layoutKey: 'public' },
      children: publicChildren(),
    },
    {
      path: '/en',
      component: () => import('@/layouts/PublicLayout.vue'),
      meta: { layoutKey: 'public', locale: 'en' },
      children: publicChildren('en-'),
    },
    {
      path: '/admin/login',
      name: 'admin-login',
      component: () => import('@/views/admin/LoginView.vue'),
      meta: { guestOnly: true },
    },
    {
      path: '/admin',
      component: () => import('@/layouts/AdminLayout.vue'),
      meta: { requiresAuth: true, layoutKey: 'admin' },
      children: [
        { path: '', redirect: '/admin/dashboard' },
        { path: 'dashboard', name: 'admin-dashboard', component: () => import('@/views/admin/DashboardView.vue') },
        { path: 'projects', name: 'admin-projects', component: () => import('@/views/admin/ProjectsAdminView.vue') },
        { path: 'projects/new', name: 'admin-project-new', component: () => import('@/views/admin/ProjectEditorView.vue') },
        {
          path: 'projects/:uuid',
          name: 'admin-project-edit',
          component: () => import('@/views/admin/ProjectEditorView.vue'),
        },
        { path: 'categories', name: 'admin-categories', component: () => import('@/views/admin/TaxonomyView.vue'), props: { mode: 'categories' } },
        { path: 'tags', name: 'admin-tags', component: () => import('@/views/admin/TaxonomyView.vue'), props: { mode: 'tags' } },
        { path: 'assets', name: 'admin-assets', component: () => import('@/views/admin/AssetsAdminView.vue') },
        { path: 'resumes', name: 'admin-resumes', component: () => import('@/views/admin/ResumesAdminView.vue') },
        { path: 'certificates', name: 'admin-certificates', component: () => import('@/views/admin/CertificatesAdminView.vue') },
        { path: 'analytics', name: 'admin-analytics', component: () => import('@/views/admin/AnalyticsView.vue') },
        { path: 'ai', name: 'admin-ai', component: () => import('@/views/admin/AIAdminView.vue') },
        { path: 'settings', name: 'admin-settings', component: () => import('@/views/admin/SettingsView.vue') },
        { path: 'audit-logs', name: 'admin-audit', component: () => import('@/views/admin/AuditLogsView.vue') },
      ],
    },
    { path: '/:pathMatch(.*)*', name: 'not-found', component: () => import('@/views/NotFoundView.vue') },
  ],
})

router.beforeEach(async (to) => {
  if (!to.path.startsWith('/admin') && !localStorage.getItem('evidentfolio_setup_complete')) {
    try {
      const setup = await authApi.setupStatus()
      if (setup.required) return { name: 'admin-login', query: { setup: '1' } }
      localStorage.setItem('evidentfolio_setup_complete', '1')
    } catch {
      // Public error states handle an unavailable API without trapping navigation.
    }
  }
  const locale = useLocaleStore()
  if (!to.path.startsWith('/admin')) {
    if (to.path === '/' && !localStorage.getItem('portfolio_locale') && !navigator.language.toLowerCase().startsWith('zh')) {
      return '/en'
    }
    locale.syncPath(to.path)
  }
  const auth = useAuthStore()
  if (to.meta.requiresAuth) {
    const authenticated = await auth.check()
    if (!authenticated) return { name: 'admin-login', query: { redirect: to.fullPath } }
  }
  if (to.meta.guestOnly) {
    const authenticated = await auth.check()
    if (authenticated) return { name: 'admin-dashboard' }
  }
})

export default router
