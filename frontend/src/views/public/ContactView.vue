<script setup lang="ts">
import { computed } from 'vue'
import { ArrowUpRight } from 'lucide-vue-next'
import ConfiguredIcon from '@/components/icons/ConfiguredIcon.vue'
import { track, usePageAnalytics } from '@/composables/useAnalytics'
import { useMeta } from '@/composables/useMeta'
import { useSiteStore } from '@/stores/site'
import { useLocaleStore } from '@/stores/locale'

const site = useSiteStore()
const locale = useLocaleStore()
const pageContent = computed(() => site.settings.page_content?.contact || {
  eyebrow: 'Contact',
  title: locale.t('contact'),
  description: '',
})
const contacts = computed(() => site.settings.contact_methods || [])
usePageAnalytics('contact')
useMeta({
  title: computed(() => `${pageContent.value.title}｜${site.settings.person_name || site.settings.site_name || 'Portfolio'}`),
  description: computed(() => pageContent.value.description),
})
</script>

<template>
  <section class="page-hero page-hero--contact">
    <div class="container">
      <span class="eyebrow">{{ pageContent.eyebrow }}</span>
      <h1>{{ pageContent.title }}</h1>
      <p>{{ pageContent.description }}</p>
    </div>
  </section>
  <section class="contact-page">
    <div class="container contact-grid">
      <div class="contact-intro" v-reveal>
        <span class="eyebrow">{{ locale.t('availability') }}</span>
        <h2>{{ site.settings.current_identity || site.settings.site_name }}</h2>
        <p>{{ site.settings.bio }}</p>
      </div>
      <div class="contact-methods">
        <component
          :is="item.url ? 'a' : 'div'"
          v-for="(item, index) in contacts"
          :key="`${item.type}:${item.value}`"
          v-reveal="index * 70"
          :href="item.url || undefined"
          :target="item.url?.startsWith('http') ? '_blank' : undefined"
          :rel="item.url?.startsWith('http') ? 'noopener noreferrer' : undefined"
          @click="item.url && track({ event_type: 'contact_click', page_type: 'contact', event_data: { type: item.type } }, true)"
        >
          <span class="contact-method__icon">
            <ConfiguredIcon
              :image-uuid="item.icon_asset_uuid"
              :icon-name="item.icon_name"
              :icon-svg="item.icon_svg"
              :size="22"
            />
          </span>
          <span><small>{{ item.label }}</small><strong>{{ item.value }}</strong><em>{{ item.description }}</em></span>
          <ArrowUpRight v-if="item.url" :size="18" />
        </component>
      </div>
    </div>
  </section>
</template>
