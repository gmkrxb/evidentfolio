<script setup lang="ts">
import { storeToRefs } from 'pinia'
import { useToastStore } from '@/stores/toast'
import { onBeforeUnmount, onMounted, watch } from 'vue'
import { useSiteStore } from '@/stores/site'
import { applySiteIcon, applyThemeColor } from '@/utils/siteIcon'

const toast = useToastStore()
const { message, tone } = storeToRefs(toast)
const site = useSiteStore()
// 后台设置的品牌图标即站点 favicon；地址栏颜色跟随主题。
watch(() => [site.settings.brand_icon_asset_uuid, site.settings.brand_mark_text, site.settings.person_name], () => {
  applySiteIcon({ iconUuid: site.settings.brand_icon_asset_uuid, mark: site.settings.brand_mark_text || site.settings.person_name || site.settings.site_name })
}, { immediate: true })
function syncThemeColor() { requestAnimationFrame(applyThemeColor) }
onMounted(() => { window.addEventListener('portfolio:theme-change', syncThemeColor); syncThemeColor() })
onBeforeUnmount(() => window.removeEventListener('portfolio:theme-change', syncThemeColor))
</script>

<template>
  <RouterView v-slot="{ Component, route }">
    <Transition name="page" mode="out-in">
      <component :is="Component" :key="route.meta.layoutKey || route.fullPath" />
    </Transition>
  </RouterView>
  <Transition name="toast">
    <div v-if="message" class="toast" :class="`toast--${tone}`" role="status" aria-live="polite">
      {{ message }}
    </div>
  </Transition>
</template>

