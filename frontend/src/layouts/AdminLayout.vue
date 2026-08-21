<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  Activity,
  Archive,
  BriefcaseBusiness,
  ChevronLeft,
  FileText,
  Award,
  FolderOpen,
  LayoutDashboard,
  LogOut,
  Menu,
  Settings,
  Sparkles,
  Tags,
  X,
} from 'lucide-vue-next'
import { useAuthStore } from '@/stores/auth'
import { useSiteStore } from '@/stores/site'
import { useLocaleStore } from '@/stores/locale'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const site = useSiteStore()
const locale = useLocaleStore()
const mobileOpen = ref(false)
const nav = computed(() => [
  { to: '/admin/dashboard', label: locale.t('dashboard'), icon: LayoutDashboard },
  { to: '/admin/projects', label: locale.t('projects'), icon: BriefcaseBusiness },
  { to: '/admin/categories', label: locale.t('categoriesAdmin'), icon: FolderOpen },
  { to: '/admin/tags', label: locale.t('tagsAdmin'), icon: Tags },
  { to: '/admin/assets', label: locale.t('assetsAdmin'), icon: Archive },
  { to: '/admin/resumes', label: locale.t('resumes'), icon: FileText },
  { to: '/admin/certificates', label: locale.t('certificates'), icon: Award },
  { to: '/admin/analytics', label: locale.t('analyticsAdmin'), icon: Activity },
  { to: '/admin/ai', label: locale.t('aiAdmin'), icon: Sparkles },
  { to: '/admin/settings', label: locale.t('settingsAdmin'), icon: Settings },
])
const currentLabel = computed(() => nav.value.find((item) => route.path.startsWith(item.to))?.label || locale.t('adminPanel'))

async function logout() {
  await auth.logout()
  await router.replace('/admin/login')
}
function switchLanguage() {
  locale.setLanguage(locale.isEnglish ? 'zh-CN' : 'en')
}
</script>

<template>
  <div class="admin-shell">
    <aside class="admin-sidebar" :class="{ 'is-open': mobileOpen }">
      <div class="admin-brand">
        <RouterLink to="/" class="admin-brand__mark" aria-label="返回公开网站">{{ site.settings.brand_mark_text || 'P' }}</RouterLink>
        <button class="icon-button admin-sidebar__close" aria-label="关闭菜单" @click="mobileOpen = false">
          <X :size="19" />
        </button>
      </div>
      <nav class="admin-nav" aria-label="管理导航">
        <RouterLink
          v-for="item in nav"
          :key="item.to"
          :to="item.to"
          @click="mobileOpen = false"
        >
          <component :is="item.icon" :size="18" aria-hidden="true" />
          <span>{{ item.label }}</span>
        </RouterLink>
      </nav>
      <div class="admin-sidebar__footer">
        <RouterLink to="/admin/audit-logs">
          <Archive :size="17" aria-hidden="true" />
          {{ locale.t('auditAdmin') }}
        </RouterLink>
        <RouterLink :to="locale.publicPath('/')" target="_blank">
          <ChevronLeft :size="17" aria-hidden="true" />
          {{ locale.t('publicSite') }}
        </RouterLink>
        <button type="button" @click="logout">
          <LogOut :size="17" aria-hidden="true" />
          {{ locale.t('logout') }}
        </button>
      </div>
    </aside>
    <button
      v-if="mobileOpen"
      class="admin-backdrop"
      aria-label="关闭菜单"
      @click="mobileOpen = false"
    />
    <section class="admin-main">
      <header class="admin-topbar">
        <button class="icon-button admin-menu-button" aria-label="打开管理菜单" @click="mobileOpen = true">
          <Menu :size="21" />
        </button>
        <div>
          <span class="eyebrow">Portfolio Control</span>
          <strong>{{ currentLabel }}</strong>
        </div>
        <div class="admin-user">
          <button type="button" class="public-language-switch" @click="switchLanguage">{{ locale.isEnglish ? '中文' : 'EN' }}</button>
          <span>{{ auth.user?.display_name }}</span>
          <span class="admin-avatar">{{ auth.user?.display_name?.slice(0, 1) }}</span>
        </div>
      </header>
      <main class="admin-content">
        <RouterView />
      </main>
    </section>
  </div>
</template>
