<script setup lang="ts">
import { onBeforeUnmount, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import PublicHeader from '@/components/public/PublicHeader.vue'
import PublicFooter from '@/components/public/PublicFooter.vue'
import { useSiteStore } from '@/stores/site'
import PrivacyConsent from '@/components/public/PrivacyConsent.vue'
import FieldBackdrop from '@/components/public/FieldBackdrop.vue'
import { useLocaleStore } from '@/stores/locale'
import { withoutLocale } from '@/utils/pageNavigation'
import { installSmoothScroll } from '@/utils/smoothScroll'
import { ambient } from '@/utils/ambientMusic'

const site = useSiteStore()
const locale = useLocaleStore()
const route = useRoute()
let uninstall: (() => void) | undefined
onMounted(() => {
  document.documentElement.dataset.surface = 'public'
  window.dispatchEvent(new Event('portfolio:theme-change'))
  uninstall = installSmoothScroll()
  ambient.install()
  site.load().catch(() => undefined)
})
onBeforeUnmount(() => {
  uninstall?.()
  ambient.setActive(false)
  delete document.documentElement.dataset.surface
})
watch(() => route.path.startsWith('/en'), () => site.load().catch(() => undefined))
// 管理员可在后台关闭全站音乐；站点信息加载前不发声。
watch(() => Boolean(site.data) && site.settings.music_enabled !== false, (allowed) => ambient.setAllowed(allowed), { immediate: true })
</script>

<template>
  <div class="site-shell" :class="{ 'is-home': withoutLocale(route.path) === '/' }">
    <FieldBackdrop />
    <PublicHeader />
    <main id="main-content" :aria-busy="locale.switching" :class="{ 'is-language-changing': locale.switching }">
      <RouterView v-slot="{ Component }">
        <!-- 不使用 out-in 过渡：浏览器前进 / 后退时新页面立即挂载，滚动恢复与内容加载不会被离场动画阻塞。 -->
        <div :key="withoutLocale(route.path)" class="atelier-view"><component :is="Component" /></div>
      </RouterView>
    </main>
    <PublicFooter :show-contact="withoutLocale(route.path).replace(/\/$/, '') !== '/contact'" />
    <PrivacyConsent />
  </div>
</template>
