<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { Menu, X } from 'lucide-vue-next'
import { useRoute, useRouter } from 'vue-router'
import { useSiteStore } from '@/stores/site'
import { useLocaleStore } from '@/stores/locale'

const site = useSiteStore()
const route = useRoute()
const router = useRouter()
const locale = useLocaleStore()
const open = ref(false)
const navigation = computed(() => site.settings.navigation_items || [])
watch(() => route.fullPath, () => (open.value = false))
function localizedRoute(path: string) {
  return locale.publicPath(path)
}
async function switchLanguage() {
  const path = route.fullPath
  const target = locale.isEnglish
    ? (path.replace(/^\/en(?=\/|$)/, '') || '/')
    : `/en${path === '/' ? '' : path}`
  locale.setLanguage(locale.isEnglish ? 'zh-CN' : 'en')
  await router.push(target)
  await site.load(true)
}
</script>

<template>
  <header class="public-header">
    <div class="container public-header__inner">
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
      <button class="icon-button public-menu" :aria-expanded="open" :aria-label="locale.t('menuToggle')" @click="open = !open">
        <X v-if="open" :size="20" />
        <Menu v-else :size="20" />
      </button>
      <nav class="public-nav" :class="{ 'is-open': open }" :aria-label="locale.t('mainNavigation')">
        <template v-for="item in navigation" :key="`${item.kind}:${item.to}`">
          <RouterLink v-if="item.kind === 'route'" :to="localizedRoute(item.to)">{{ item.label }}</RouterLink>
          <a v-else :href="item.to" target="_blank" rel="noopener noreferrer">{{ item.label }}</a>
        </template>
        <button type="button" class="public-language-switch" @click="switchLanguage">{{ locale.isEnglish ? '中文' : 'EN' }}</button>
      </nav>
    </div>
  </header>
</template>
