<script setup lang="ts">
import ThemeControl from '@/components/ui/ThemeControl.vue'
import SoundToggle from '@/components/public/SoundToggle.vue'
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { Menu, X } from 'lucide-vue-next'
import { useRoute, useRouter } from 'vue-router'
import { useSiteStore } from '@/stores/site'
import { useLocaleStore } from '@/stores/locale'
import { useToastStore } from '@/stores/toast'
import { prepareLocalePage } from '@/api/public'
import { captureReadingPosition, restoreReadingPosition, waitForPageContent, withoutLocale, PAGE_LAYOUT_EVENT } from '@/utils/pageNavigation'
import { captureLocaleText, animateLocaleText } from '@/utils/localeMotion'

const site = useSiteStore()
const route = useRoute()
const router = useRouter()
const locale = useLocaleStore()
const toast = useToastStore()
const open = ref(false)
const destination = ref<boolean | null>(null)
const headerInner = ref<HTMLElement | null>(null)
const preferences = ref<HTMLElement | null>(null)
const controlsInMenu = ref(false)
const scrolled = ref(false)
function updateScrolled() { scrolled.value = window.scrollY > 8 }
let headerSizes: ResizeObserver | undefined
const navigation = computed(() => site.settings.navigation_items || [])
watch(() => route.fullPath, () => (open.value = false))
function measureControls() {
  const inner = headerInner.value, controls = preferences.value
  if (!inner || !controls) return
  if (!matchMedia('(max-width: 820px)').matches) { controlsInMenu.value = false; return }
  // 手机上把主题与语言收进菜单，顶栏只留品牌与菜单按钮。
  if (matchMedia('(max-width: 560px)').matches) { controlsInMenu.value = true; return }
  const brand = inner.querySelector<HTMLElement>('.public-brand')
  const label = brand?.querySelector<HTMLElement>('.public-brand__text')
  const mark = brand?.querySelector<HTMLElement>('.public-brand__mark, .public-brand__image')
  const menu = inner.querySelector<HTMLElement>('.public-menu')
  if (!brand || !label || !mark || !menu) return
  const brandWidth = label.scrollWidth + mark.offsetWidth + (parseFloat(getComputedStyle(brand).columnGap) || 0)
  const gaps = (parseFloat(getComputedStyle(inner).columnGap) || 0) * 2
  controlsInMenu.value = brandWidth + controls.scrollWidth + menu.offsetWidth + gaps > inner.clientWidth
}
onMounted(async () => {
  await nextTick()
  headerSizes = new ResizeObserver(measureControls)
  for (const element of [headerInner.value, preferences.value, headerInner.value?.querySelector('.public-brand__text')]) {
    if (element) headerSizes.observe(element)
  }
  window.addEventListener('resize', measureControls, { passive: true })
  window.addEventListener('scroll', updateScrolled, { passive: true })
  updateScrolled()
  measureControls()
})
onBeforeUnmount(() => { headerSizes?.disconnect(); window.removeEventListener('resize', measureControls); window.removeEventListener('scroll', updateScrolled) })
function localizedRoute(path: string) {
  return locale.publicPath(path)
}
async function switchLanguage(nextEnglish: boolean) {
  if (locale.switching || nextEnglish === locale.isEnglish) return
  const originalPath = route.fullPath
  const base = withoutLocale(route.path)
  const path = nextEnglish ? `/en${base === '/' ? '' : base}` : base
  locale.switching = true
  destination.value = nextEnglish
  try {
    await prepareLocalePage(base, route.query, nextEnglish ? 'en' : 'zh-CN')
    if (route.fullPath !== originalPath) return
    const position = captureReadingPosition()
    const text = captureLocaleText(document.querySelector<HTMLElement>('.site-shell') || document.body)
    document.documentElement.dataset.localeDirection = nextEnglish ? 'en' : 'zh'
    await router.push({ path, query: route.query, hash: route.hash })
    await site.load()
    await waitForPageContent(false)
    window.dispatchEvent(new Event(PAGE_LAYOUT_EVENT))
    await nextTick()
    restoreReadingPosition(position)
    window.dispatchEvent(new Event(PAGE_LAYOUT_EVENT))
    await nextTick()
    await animateLocaleText(text)
  } catch {
    toast.show(locale.isEnglish ? 'Some content could not be loaded. Please refresh to retry.' : '部分内容加载失败，请刷新重试', 'error')
  } finally {
    locale.switching = false
    destination.value = null
    delete document.documentElement.dataset.localeDirection
  }
}
</script>

<template>
  <header class="public-header" :class="{ 'is-scrolled': scrolled, 'is-menu-open': open }">
    <div ref="headerInner" class="container public-header__inner" :class="{ 'preferences-in-menu': controlsInMenu }">
      <RouterLink :to="locale.publicPath('/')" class="public-brand" :aria-label="`${site.settings.site_name || 'Portfolio'} ${locale.t('home')}`">
        <img
          v-if="site.settings.brand_icon_asset_uuid"
          class="public-brand__image"
          :src="`/api/v1/public/assets/${site.settings.brand_icon_asset_uuid}/thumbnail`"
          alt=""
        />
        <span v-else class="public-brand__mark">{{ site.settings.brand_mark_text || 'P' }}</span>
        <span class="public-brand__text">{{ site.settings.person_name || site.settings.site_name || 'Portfolio' }}</span>
      </RouterLink>
      <nav class="public-nav" :class="{ 'is-open': open }" :aria-label="locale.t('mainNavigation')">
        <template v-for="item in navigation" :key="`${item.kind}:${item.to}`">
          <RouterLink v-if="item.kind === 'route'" :to="localizedRoute(item.to)">{{ item.label }}</RouterLink>
          <a v-else :href="item.to" target="_blank" rel="noopener noreferrer">{{ item.label }}</a>
        </template>
        <div id="menu-preferences" />
      </nav>
      <div id="header-preferences" />
      <SoundToggle v-if="site.settings.music_enabled !== false" class="public-sound" />
      <button class="icon-button public-menu" :aria-expanded="open" :aria-label="locale.t('menuToggle')" @click="open = !open">
        <X v-if="open" :size="20" />
        <Menu v-else :size="20" />
      </button>
      <Teleport defer :to="controlsInMenu ? '#menu-preferences' : '#header-preferences'">
        <div ref="preferences" class="public-preferences">
          <ThemeControl />
          <div class="public-language-switch" :class="{ 'is-english': destination ?? locale.isEnglish }" role="group" aria-label="Language / 语言" :aria-busy="locale.switching"><button type="button" :disabled="locale.switching" :aria-pressed="!locale.isEnglish" aria-label="切换为中文" @click="switchLanguage(false)">中</button><button type="button" :disabled="locale.switching" :aria-pressed="locale.isEnglish" aria-label="Switch to English" @click="switchLanguage(true)">EN</button></div>
        </div>
      </Teleport>
    </div>
    <div id="public-reading-slot" class="public-reading-slot" />
  </header>
</template>
