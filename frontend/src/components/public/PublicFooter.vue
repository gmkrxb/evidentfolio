<script setup lang="ts">
import ConfiguredIcon from '@/components/icons/ConfiguredIcon.vue'
import { useSiteStore } from '@/stores/site'
import { track } from '@/composables/useAnalytics'
import { useLocaleStore } from '@/stores/locale'

const site = useSiteStore()
const locale = useLocaleStore()
</script>

<template>
  <footer class="public-footer">
    <div class="container footer-grid">
      <div>
        <span class="eyebrow">{{ site.settings.footer_eyebrow }}</span>
        <h2>{{ site.settings.footer_heading }}</h2>
      </div>
      <div class="footer-contact">
        <component
          :is="item.url ? 'a' : 'span'"
          v-for="item in site.settings.contact_methods || []"
          :key="`${item.type}:${item.value}`"
          :href="item.url || undefined"
          :target="item.url?.startsWith('http') ? '_blank' : undefined"
          :rel="item.url?.startsWith('http') ? 'noopener noreferrer' : undefined"
          @click="item.url && track({ event_type: 'contact_click', page_type: 'footer', event_data: { type: item.type } })"
        >
          <ConfiguredIcon
            :image-uuid="item.icon_asset_uuid"
            :icon-name="item.icon_name"
            :icon-svg="item.icon_svg"
            :size="18"
          />
          {{ item.value }}
        </component>
      </div>
    </div>
    <div class="container footer-bottom">
      <span>© {{ new Date().getFullYear() }} {{ site.settings.person_name || site.settings.site_name || 'Portfolio' }}</span>
      <span>{{ site.settings.footer_text }}</span>
      <RouterLink to="/admin/login">{{ locale.t('admin') }}</RouterLink>
    </div>
  </footer>
</template>
