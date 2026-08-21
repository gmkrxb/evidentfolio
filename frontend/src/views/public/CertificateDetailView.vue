<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { ArrowLeft, ArrowUpRight, BadgeCheck, CalendarDays, ExternalLink, FileText, Maximize2, X } from 'lucide-vue-next'
import { useRoute } from 'vue-router'
import ConfiguredIcon from '@/components/icons/ConfiguredIcon.vue'
import ImageLightbox from '@/components/content/ImageLightbox.vue'
import PdfViewer from '@/components/content/PdfViewer.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import ErrorState from '@/components/ui/ErrorState.vue'
import LoadingState from '@/components/ui/LoadingState.vue'
import { publicApi } from '@/api/public'
import { useAsyncState } from '@/composables/useAsync'
import { track } from '@/composables/useAnalytics'
import { useMeta } from '@/composables/useMeta'
import { useSiteStore } from '@/stores/site'
import { useLocaleStore } from '@/stores/locale'
import type { ProjectAsset } from '@/types'
import { certificateTypeLabel } from '@/utils/labels'

const route = useRoute()
const site = useSiteStore()
const locale = useLocaleStore()
const state = useAsyncState<Awaited<ReturnType<typeof publicApi.certificate>>>()
const lightboxOpen = ref(false)
const pdfOpen = ref(false)
const title = computed(() => `${state.data.value?.name || locale.t('credentials')}｜${site.settings.site_name || 'Portfolio'}`)
const description = computed(() => state.data.value?.description || '')
const lightboxItems = computed<ProjectAsset[]>(() => {
  const asset = state.data.value?.asset
  if (!asset?.mime_type.startsWith('image/')) return []
  return [{
    uuid: `certificate-${state.data.value?.uuid}`,
    usage: 'certificate',
    caption: state.data.value?.name || asset.display_name,
    sort_order: 0,
    asset,
  }]
})
const isPdf = computed(() => state.data.value?.asset?.mime_type === 'application/pdf')

async function load() {
  await state.run((signal) => publicApi.certificate(String(route.params.uuid), signal))
  if (state.data.value) {
    track({
      event_type: 'document_preview',
      page_type: 'certificate_detail',
      page_uuid: state.data.value.uuid,
      asset_uuid: state.data.value.asset?.uuid,
    })
  }
}
function downloadCertificate() {
  const asset = state.data.value?.asset
  if (asset) window.location.href = asset.download_url
}
watch(() => route.params.uuid, load)
watch(pdfOpen, (value) => document.body.classList.toggle('is-locked', value))
onMounted(load)
onBeforeUnmount(() => document.body.classList.remove('is-locked'))
useMeta({ title, description })
</script>

<template>
  <LoadingState v-if="state.loading.value" class="container page-loading" :rows="8" />
  <ErrorState v-else-if="state.error.value" class="container page-loading" :message="state.error.value" @retry="load" />
  <article v-else-if="state.data.value" class="certificate-detail">
    <header class="page-hero page-hero--certificate-detail">
      <div class="container">
        <RouterLink class="back-link" :to="locale.publicPath('/certificates')"><ArrowLeft :size="16" />{{ locale.t('backCredentials') }}</RouterLink>
        <span class="eyebrow">{{ certificateTypeLabel(state.data.value.certificate_type) }} · {{ state.data.value.issued_at || locale.t('notProvided') }}</span>
        <h1>{{ state.data.value.name }}</h1>
        <p>{{ state.data.value.description }}</p>
      </div>
    </header>
    <div class="container certificate-detail__grid">
      <section class="certificate-detail__visual">
        <button
          v-if="lightboxItems.length"
          type="button"
          :aria-label="locale.t('enlargeCertificate')"
          @click="lightboxOpen = true"
        >
          <img
            :src="state.data.value.asset?.content_url"
            :alt="`${state.data.value.name} ${locale.t('certificatePreview')}`"
          />
          <span><Maximize2 :size="17" />{{ locale.t('clickEnlarge') }}</span>
        </button>
        <button
          v-else-if="isPdf && state.data.value.asset"
          type="button"
          class="certificate-pdf-trigger"
          :aria-label="locale.t('openFullPdf')"
          @click="pdfOpen = true"
        >
          <img
            v-if="state.data.value.asset.thumbnail_url"
            :src="state.data.value.asset.thumbnail_url"
            :alt="`${state.data.value.name} ${locale.t('pdfFirstPage')}`"
          />
          <FileText v-else :size="58" />
          <strong>{{ state.data.value.asset.display_name }}</strong>
          <span><Maximize2 :size="17" />{{ locale.t('openFullPdf') }}</span>
        </button>
        <RouterLink
          v-else-if="state.data.value.asset"
          class="certificate-file-preview"
          :to="locale.publicPath(`/assets/${state.data.value.asset.uuid}`)"
        >
          <BadgeCheck :size="42" />
          <strong>{{ state.data.value.asset.display_name }}</strong>
          <span>{{ locale.t('openCertificateFile') }} <ArrowUpRight :size="15" /></span>
        </RouterLink>
        <div v-else class="certificate-file-preview">
          <ConfiguredIcon
            :image-uuid="state.data.value.icon_asset?.uuid"
            :icon-name="state.data.value.icon_name || 'Medal'"
            :icon-svg="state.data.value.icon_svg"
            :size="54"
          />
          <strong>{{ state.data.value.name }}</strong>
        </div>
      </section>
      <aside class="certificate-detail__meta">
        <span class="eyebrow">{{ locale.t('credentialInformation') }}</span>
        <dl>
          <div><dt>{{ locale.t('issuer') }}</dt><dd>{{ state.data.value.issuer || '—' }}</dd></div>
          <div><dt>{{ locale.t('issuedAt') }}</dt><dd><CalendarDays :size="15" />{{ state.data.value.issued_at || '—' }}</dd></div>
          <div v-if="state.data.value.credential_no"><dt>{{ locale.t('credentialNumber') }}</dt><dd>{{ state.data.value.credential_no }}</dd></div>
        </dl>
        <a
          v-if="state.data.value.credential_url"
          class="button button--outline"
          :href="state.data.value.credential_url"
          target="_blank"
          rel="noopener noreferrer"
        >
          <ExternalLink :size="16" />{{ locale.t('verifyCertificate') }}
        </a>
      </aside>
    </div>
    <section class="certificate-related">
      <div class="container">
        <div class="section-heading">
          <div><span class="eyebrow">{{ locale.t('relatedCaseStudies') }}</span><h2>{{ locale.t('relatedCaseStudies') }}</h2></div>
          <p>{{ locale.t('relatedCaseStudiesDescription') }}</p>
        </div>
        <div v-if="state.data.value.projects?.length" class="certificate-related__grid">
          <RouterLink
            v-for="project in state.data.value.projects"
            :key="project.uuid"
            :to="locale.publicPath(`/projects/${project.uuid}`)"
          >
            <span>{{ project.start_date }} — {{ project.end_date }}</span>
            <h3>{{ project.title }}</h3>
            <p>{{ project.summary }}</p>
            <small>{{ project.role }} <ArrowUpRight :size="15" /></small>
          </RouterLink>
        </div>
        <EmptyState v-else :title="locale.t('noRelatedProjects')" :description="locale.t('noRelatedProjectsDescription')" />
      </div>
    </section>
    <ImageLightbox
      :items="lightboxItems"
      :index="lightboxOpen ? 0 : null"
      @close="lightboxOpen = false"
    />
    <Teleport to="body">
      <Transition name="lightbox">
        <div v-if="pdfOpen && state.data.value.asset" class="certificate-pdf-modal" @click.self="pdfOpen = false">
          <button class="icon-button icon-button--light certificate-pdf-modal__close" :aria-label="locale.t('closePdf')" @click="pdfOpen = false">
            <X :size="22" />
          </button>
          <PdfViewer
            :src="state.data.value.asset.content_url"
            :title="state.data.value.name"
            :meta="state.data.value.issuer"
            @download="downloadCertificate"
          />
        </div>
      </Transition>
    </Teleport>
  </article>
</template>
