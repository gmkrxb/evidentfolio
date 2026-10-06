<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { ArrowLeft, ArrowUpRight, BadgeCheck, CalendarDays, Download, ExternalLink, Eye, FileText, Maximize2, X } from 'lucide-vue-next'
import { useRoute } from 'vue-router'
import ConfiguredIcon from '@/components/icons/ConfiguredIcon.vue'
import ImageLightbox from '@/components/content/ImageLightbox.vue'
import PdfViewer from '@/components/content/PdfViewer.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import ErrorState from '@/components/ui/ErrorState.vue'
import LoadingState from '@/components/ui/LoadingState.vue'
import { publicApi } from '@/api/public'
import { useAsyncState } from '@/composables/useAsync'
import { useLocaleReload } from '@/composables/useLocaleReload'
import { track, usePageAnalytics } from '@/composables/useAnalytics'
import { useMeta } from '@/composables/useMeta'
import { useSiteStore } from '@/stores/site'
import { useLocaleStore } from '@/stores/locale'
import type { ProjectAsset } from '@/types'
import { certificateTypeLabel } from '@/utils/labels'
import AssetMedia from '@/components/content/AssetMedia.vue'
import { downloadAsset } from '@/utils/protectedAsset'

const route = useRoute()
const site = useSiteStore()
const locale = useLocaleStore()
const state = useAsyncState<Awaited<ReturnType<typeof publicApi.certificate>>>({ keepPreviousData: true })
const lightboxOpen = ref(false)
const pdfOpen = ref(false)
const pdfDialog = ref<HTMLElement>()
let pdfTrigger: HTMLElement | null = null
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
const assetProtected = computed(() => Boolean(state.data.value?.asset?.protected))
async function downloadCertificate() {
  const asset = state.data.value?.asset
  if (asset && !asset.protected) await downloadAsset(asset).catch(() => undefined)
}
watch(() => route.params.uuid, load)
watch(pdfOpen, async (value) => {
  document.body.classList.toggle('is-locked', value)
  if (value) {
    pdfTrigger = document.activeElement as HTMLElement | null
    await nextTick()
    pdfDialog.value?.querySelector<HTMLElement>('.certificate-pdf-modal__close')?.focus()
  } else if (pdfTrigger?.isConnected) pdfTrigger.focus({ preventScroll: true })
})
function pdfKeys(event: KeyboardEvent) {
  if (!pdfOpen.value) return
  if (event.key === 'Escape') { event.preventDefault(); pdfOpen.value = false; return }
  if (event.key !== 'Tab') return
  const items = [...(pdfDialog.value?.querySelectorAll<HTMLElement>('button:not(:disabled),a[href],input:not(:disabled),select:not(:disabled),[tabindex="0"]') || [])].filter(element => element.getClientRects().length)
  const first = items[0], last = items.at(-1)
  if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last?.focus() }
  else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first?.focus() }
}
useLocaleReload(load)
onMounted(() => { void load(); window.addEventListener('keydown', pdfKeys) })
usePageAnalytics('certificate_detail', String(route.params.uuid))
onBeforeUnmount(() => { document.body.classList.remove('is-locked'); window.removeEventListener('keydown', pdfKeys) })
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
        <header v-if="state.data.value.asset && (isPdf || lightboxItems.length)" class="certificate-preview-heading">
          <span class="certificate-preview-heading__file"><i>{{ isPdf ? 'PDF' : (state.data.value.asset.extension || '').replace('.', '').toUpperCase() || 'IMG' }}</i>{{ state.data.value.asset.display_name || state.data.value.name }}</span>
          <span class="certificate-preview-heading__actions">
            <button class="button button--dark button--small" type="button" @click="isPdf ? pdfOpen = true : lightboxOpen = true">
              <Maximize2 :size="15" />{{ isPdf ? locale.t('openFullPdf') : locale.t('clickEnlarge') }}
            </button>
            <span v-if="assetProtected" class="asset-view-only asset-view-only--small"><Eye :size="14" />{{ locale.isEnglish ? 'View only' : '仅可查看' }}</span>
            <button v-else class="button button--outline button--small" type="button" :aria-label="locale.t('downloadOriginal')" @click="downloadCertificate">
              <Download :size="15" /><span class="certificate-preview-heading__label">{{ locale.t('downloadOriginal') }}</span>
            </button>
          </span>
        </header>
        <button
          v-if="lightboxItems.length"
          type="button"
          class="certificate-preview-image"
          :aria-label="locale.t('enlargeCertificate')"
          @click="lightboxOpen = true"
        >
          <AssetMedia
            v-if="state.data.value.asset"
            :asset="state.data.value.asset"
            kind="image"
            :alt="`${state.data.value.name} ${locale.t('certificatePreview')}`"
          />
        </button>
        <button
          v-else-if="isPdf && state.data.value.asset"
          type="button"
          class="certificate-preview-image"
          :class="{ 'certificate-preview-image--empty': !state.data.value.asset.thumbnail_url }"
          :aria-label="locale.t('openFullPdf')"
          @click="pdfOpen = true"
        >
          <img
            v-if="state.data.value.asset.thumbnail_url"
            :src="state.data.value.asset.thumbnail_url"
            :alt="`${state.data.value.name} ${locale.t('pdfFirstPage')}`"
          />
          <FileText v-else :size="58" />
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
        <div v-if="pdfOpen && state.data.value.asset" ref="pdfDialog" class="certificate-pdf-modal" role="dialog" :aria-modal="pdfOpen" :inert="!pdfOpen" :aria-label="state.data.value.name" @click.self="pdfOpen = false">
          <button class="icon-button icon-button--light certificate-pdf-modal__close" :aria-label="locale.t('closePdf')" @click="pdfOpen = false">
            <X :size="22" />
          </button>
          <PdfViewer
            :src="state.data.value.asset.content_url"
            :protected-asset="state.data.value.asset.protected ? state.data.value.asset : null"
            :title="state.data.value.name"
            :meta="state.data.value.issuer"
            @download="downloadCertificate"
          />
        </div>
      </Transition>
    </Teleport>
  </article>
</template>
