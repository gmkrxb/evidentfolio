<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ArrowUpRight, Award, BookOpenCheck, FileBadge, Medal } from 'lucide-vue-next'
import EmptyState from '@/components/ui/EmptyState.vue'
import ErrorState from '@/components/ui/ErrorState.vue'
import LoadingState from '@/components/ui/LoadingState.vue'
import { publicApi } from '@/api/public'
import { useAsyncState } from '@/composables/useAsync'
import { usePageAnalytics } from '@/composables/useAnalytics'
import { useMeta } from '@/composables/useMeta'
import { useSiteStore } from '@/stores/site'
import { useLocaleStore } from '@/stores/locale'
import type { Certificate } from '@/types'
import ConfiguredIcon from '@/components/icons/ConfiguredIcon.vue'
import { certificateTypeLabel } from '@/utils/labels'

const site = useSiteStore()
const locale = useLocaleStore()
const state = useAsyncState<{ items: Certificate[] }>()
const filter = ref('')
const pageContent = computed(() => site.settings.page_content?.certificates || {
  eyebrow: 'Credentials',
  title: locale.t('certificates'),
  description: '',
})
const types = computed(() => [
  { value: '', label: locale.t('all'), count: state.data.value?.items.length || 0 },
  ...['competition', 'scholarship', 'patent', 'course', 'other'].map((value) => ({
    value,
    label: certificateTypeLabel(value),
    count: state.data.value?.items.filter((item) => item.certificate_type === value).length || 0,
  })).filter((item) => item.count),
])
const items = computed(() => state.data.value?.items.filter((item) => !filter.value || item.certificate_type === filter.value) || [])

function typeIcon(type: string) {
  return type === 'competition' ? Medal : type === 'scholarship' ? Award : type === 'course' ? BookOpenCheck : FileBadge
}
function load() {
  return state.run((signal) => publicApi.certificates(signal))
}
onMounted(load)
usePageAnalytics('certificates')
useMeta({
  title: computed(() => `${pageContent.value.title}｜${site.settings.person_name || site.settings.site_name || 'Portfolio'}`),
  description: computed(() => pageContent.value.description),
})
</script>

<template>
  <section class="page-hero page-hero--certificates">
    <div class="container">
      <span class="eyebrow">{{ pageContent.eyebrow }}</span>
      <h1>{{ pageContent.title }}</h1>
      <p>{{ pageContent.description }}</p>
    </div>
  </section>
  <section class="certificates-page">
    <div class="container">
      <LoadingState v-if="state.loading.value" :rows="8" />
      <ErrorState v-else-if="state.error.value" :message="state.error.value" @retry="load" />
      <EmptyState v-else-if="!state.data.value?.items.length" :title="locale.t('noCertificates')" :description="locale.t('noCertificatesDescription')" />
      <template v-else>
        <nav class="certificate-filters" :aria-label="locale.t('certificateFilters')">
          <button v-for="item in types" :key="item.value" :class="{ active: filter === item.value }" @click="filter = item.value">
            {{ item.label }} <span>{{ item.count }}</span>
          </button>
        </nav>
        <div class="certificate-grid">
          <article v-for="(item, index) in items" :key="item.uuid" v-reveal="(index % 3) * 70">
            <div class="certificate-card__visual">
              <img v-if="item.asset?.thumbnail_url" :src="item.asset.thumbnail_url" :alt="`${item.name} ${locale.t('certificatePreview')}`" loading="lazy" />
              <span v-else-if="item.icon_asset || item.icon_name || item.icon_svg" class="certificate-card__icon">
                <ConfiguredIcon
                  :image-uuid="item.icon_asset?.uuid"
                  :icon-name="item.icon_name"
                  :icon-svg="item.icon_svg"
                  :size="42"
                />
              </span>
              <component :is="typeIcon(item.certificate_type)" v-else :size="42" />
              <span>{{ certificateTypeLabel(item.certificate_type) }}</span>
            </div>
            <div class="certificate-card__body">
              <span class="eyebrow">{{ item.issued_at }} · {{ item.issuer }}</span>
              <h2>{{ item.name }}</h2>
              <p>{{ item.description }}</p>
              <small v-if="item.credential_no">{{ locale.t('credentialNumber') }} {{ item.credential_no }}</small>
              <div>
                <RouterLink class="text-link" :to="locale.publicPath(`/certificates/${item.uuid}`)">
                  {{ locale.t('viewDetails') }} <ArrowUpRight :size="15" />
                </RouterLink>
                <a v-if="item.credential_url" class="text-link" :href="item.credential_url" target="_blank" rel="noopener noreferrer">
                  {{ locale.t('verifyAddress') }} <ArrowUpRight :size="15" />
                </a>
              </div>
            </div>
          </article>
        </div>
      </template>
    </div>
  </section>
</template>
