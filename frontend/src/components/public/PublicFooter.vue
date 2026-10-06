<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { ArrowUp, ArrowUpRight } from 'lucide-vue-next'
import { privacy } from '@/stores/privacy'
import ConfiguredIcon from '@/components/icons/ConfiguredIcon.vue'
import FooterHorizon from '@/components/public/FooterHorizon.vue'
import { useSiteStore } from '@/stores/site'
import { track } from '@/composables/useAnalytics'
import { useLocaleStore } from '@/stores/locale'
import { scrollToY } from '@/utils/smoothScroll'

withDefaults(defineProps<{ showContact?: boolean }>(), { showContact: true })

const site = useSiteStore()
const locale = useLocaleStore()
const settings = computed(() => site.settings)
const name = computed(() => settings.value.person_name || settings.value.site_name || 'Portfolio')
const quote = computed(() => settings.value.home_copy?.footer_quote || (locale.isEnglish ? 'All things have their pattern; structure is the shape it takes.' : '万物皆有其理，结构是理的形状。'))
const contacts = computed(() => settings.value.contact_methods || [])
const clock = ref('')
const progress = ref(0)
let timer = 0
let frame = 0

function tick() {
  clock.value = new Intl.DateTimeFormat(locale.isEnglish ? 'en-GB' : 'zh-CN', { hour: '2-digit', minute: '2-digit', hour12: false }).format(new Date())
}
function measure() {
  frame = 0
  const max = document.documentElement.scrollHeight - window.innerHeight
  progress.value = max > 0 ? Math.min(1, window.scrollY / max) : 0
}
function schedule() { if (!frame) frame = requestAnimationFrame(measure) }
function toTop() { scrollToY(0, 1600) }
onMounted(() => {
  tick()
  timer = window.setInterval(tick, 15000)
  window.addEventListener('scroll', schedule, { passive: true })
  measure()
})
onBeforeUnmount(() => { window.clearInterval(timer); window.removeEventListener('scroll', schedule); cancelAnimationFrame(frame) })
</script>

<template>
  <footer class="public-footer colophon" :class="{ 'colophon--compact': !showContact }">
    <div v-if="showContact" class="container colophon__top">
      <div class="colophon__lead">
        <span class="eyebrow">{{ settings.footer_eyebrow || (locale.isEnglish ? 'Correspondence' : '来信') }}</span>
        <h2>{{ settings.footer_heading || (locale.isEnglish ? 'Let us build what can be proven.' : '一起建造，可以被证明的未来。') }}</h2>
      </div>
      <nav v-if="contacts.length" class="colophon__contacts" :aria-label="locale.isEnglish ? 'Contact' : '联系方式'">
        <component
          :is="item.url ? 'a' : 'span'"
          v-for="item in contacts"
          :key="`${item.type}:${item.value}`"
          class="colophon__contact"
          :href="item.url || undefined"
          :target="item.url?.startsWith('http') ? '_blank' : undefined"
          :rel="item.url?.startsWith('http') ? 'noopener noreferrer' : undefined"
          @click="item.url && track({ event_type: 'contact_click', page_type: 'footer', event_data: { type: item.type } })"
        >
          <span class="colophon__icon"><ConfiguredIcon :image-uuid="item.icon_asset_uuid" :icon-name="item.icon_name" :icon-svg="item.icon_svg" :size="16" /></span>
          <span class="colophon__contact-text"><small>{{ item.label || item.type }}</small><strong>{{ item.value }}</strong></span>
          <ArrowUpRight v-if="item.url" class="colophon__arrow" :size="18" />
        </component>
      </nav>
    </div>

    <FooterHorizon class="colophon__horizon" />

    <p class="container colophon__quote">{{ quote }}</p>

    <div class="container footer-wordmark" aria-hidden="true"><span>{{ name }}</span></div>

    <div class="container colophon__bottom">
      <span>© {{ new Date().getFullYear() }} {{ name }}</span>
      <span v-if="settings.footer_text">{{ settings.footer_text }}</span>
      <span class="colophon__clock"><i />{{ settings.location ? `${settings.location} · ` : '' }}{{ clock }}</span>
      <span class="colophon__links">
        <button type="button" @click="privacy.open = true">{{ locale.isEnglish ? 'Privacy' : '隐私设置' }}</button>
        <RouterLink to="/admin/login">{{ locale.t('admin') }}</RouterLink>
      </span>
      <button v-magnetic="0.35" type="button" class="colophon__top-button" :aria-label="locale.isEnglish ? 'Back to top' : '回到顶部'" @click="toTop">
        <svg class="colophon__ring" viewBox="0 0 48 48" aria-hidden="true"><circle cx="24" cy="24" r="22" class="ring-track" /><circle cx="24" cy="24" r="22" class="ring-value" :style="{ strokeDashoffset: 1 - progress }" pathLength="1" /></svg>
        <ArrowUp :size="16" />
      </button>
    </div>
  </footer>
</template>
