<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import {
  ArrowLeft,
  ArrowUpRight,
  CheckCircle2,
  Clock3,
  Code2,
  ExternalLink,
  FileArchive,
  Layers3,
  Music2,
  UserRound,
} from 'lucide-vue-next'
import { useRoute } from 'vue-router'
import ErrorState from '@/components/ui/ErrorState.vue'
import LoadingState from '@/components/ui/LoadingState.vue'
import MarkdownContent from '@/components/content/MarkdownContent.vue'
import ImageLightbox from '@/components/content/ImageLightbox.vue'
import { publicApi } from '@/api/public'
import { useAsyncState } from '@/composables/useAsync'
import { track } from '@/composables/useAnalytics'
import { useMeta } from '@/composables/useMeta'
import { useSiteStore } from '@/stores/site'
import { useLocaleStore } from '@/stores/locale'
import type { Asset, ProjectAlbum, ProjectAsset, ProjectSection } from '@/types'
import ConfiguredIcon from '@/components/icons/ConfiguredIcon.vue'
import { certificateTypeLabel, projectStateLabel } from '@/utils/labels'

const route = useRoute()
const site = useSiteStore()
const locale = useLocaleStore()
const state = useAsyncState<Awaited<ReturnType<typeof publicApi.project>>>()
const lightboxIndex = ref<number | null>(null)
const started = ref(performance.now())
const standaloneAssets = computed(() => state.data.value?.assets.filter((item) => item.usage !== 'album') || [])
const images = computed(() => standaloneAssets.value.filter((item) => item.asset.mime_type.startsWith('image/')))
const lightboxItems = computed<ProjectAsset[]>(() => {
  const collected = [...images.value]
  const seen = new Set(collected.map((item) => item.asset.uuid))
  for (const section of state.data.value?.sections || []) {
    for (const item of sectionMedia(section)) {
      if (!seen.has(item.asset.uuid)) {
        collected.push(item)
        seen.add(item.asset.uuid)
      }
    }
  }
  for (const album of state.data.value?.albums || []) {
    for (const item of album.assets || []) {
      if (!item.asset.mime_type.startsWith('image/') || seen.has(item.asset.uuid)) continue
      collected.push({ ...item, usage: 'album' })
      seen.add(item.asset.uuid)
    }
  }
  return collected
})
const videos = computed(() => standaloneAssets.value.filter((item) => item.asset.mime_type.startsWith('video/')))
const documents = computed(() => standaloneAssets.value.filter((item) => !item.asset.mime_type.startsWith('image/') && !item.asset.mime_type.startsWith('video/')))
const referencedAlbumUuids = computed(() => new Set((state.data.value?.sections || []).filter((section) => section.display_mode === 'album' && section.album_uuid).map((section) => section.album_uuid)))
const standaloneAlbums = computed(() => (state.data.value?.albums || []).filter((album) => !referencedAlbumUuids.value.has(album.uuid || null)))
const hasMedia = computed(() => standaloneAssets.value.length > 0 || standaloneAlbums.value.length > 0)
const title = computed(() => state.data.value?.seo_title || `${state.data.value?.title || locale.t('projectFallback')}｜${site.settings.site_name || 'Portfolio'}`)
const description = computed(() => state.data.value?.seo_description || state.data.value?.summary || '')

async function load() {
  started.value = performance.now()
  await state.run((signal) => publicApi.project(String(route.params.uuid), signal))
  if (state.data.value) {
    track({ event_type: 'project_view', page_type: 'project_detail', project_uuid: state.data.value.uuid })
  }
}
function openImage(item: ProjectAsset) {
  lightboxIndex.value = lightboxItems.value.findIndex((image) => image.asset.uuid === item.asset.uuid)
  track({
    event_type: 'image_view',
    page_type: 'project_detail',
    project_uuid: state.data.value?.uuid,
    asset_uuid: item.asset.uuid,
  })
}
function sectionMedia(section: ProjectSection): ProjectAsset[] {
  if (section.display_mode === 'album' && section.album?.assets) {
    return section.album.assets
      .filter((item) => item.asset.mime_type.startsWith('image/'))
      .map((item) => ({ ...item, usage: 'album' }))
  }
  return sectionAssets(section)
    .filter((asset) => asset.mime_type.startsWith('image/'))
    .map((asset, index) => ({
      uuid: `${section.uuid || section.sort_order}-${asset.uuid}`,
      usage: 'section',
      caption: asset.description || asset.display_name,
      sort_order: index,
      asset,
    }))
}
function albumImages(album: ProjectAlbum): ProjectAsset[] {
  return (album.assets || [])
    .filter((item) => item.asset.mime_type.startsWith('image/'))
    .map((item) => ({ ...item, usage: 'album' }))
}
function sectionAssets(section: ProjectSection): Asset[] {
  if (section.display_mode === 'album' && section.album?.assets) {
    return section.album.assets.map((item) => item.asset)
  }
  return section.media_assets || []
}
function sectionVideos(section: ProjectSection) {
  return sectionAssets(section).filter((asset) => asset.mime_type.startsWith('video/'))
}
function sectionAudios(section: ProjectSection) {
  return sectionAssets(section).filter((asset) => asset.mime_type.startsWith('audio/'))
}
function sectionAttachments(section: ProjectSection) {
  return sectionAssets(section).filter((asset) =>
    !asset.mime_type.startsWith('image/')
    && !asset.mime_type.startsWith('video/')
    && !asset.mime_type.startsWith('audio/'),
  )
}
function layoutEntry(key: string) {
  return state.data.value?.content_layout?.find((item) => item.key === key)
}
function blockVisible(key: string) {
  return layoutEntry(key)?.visible !== false
}
function blockOrder(key: string, fallback: number) {
  return layoutEntry(key)?.sort_order ?? fallback
}
function blockNumber(key: string, fallback: number) {
  const order = blockOrder(key, fallback)
  return String(order + 1).padStart(2, '0')
}
function headingTag(section: ProjectSection) {
  return `h${section.heading_level || 2}`
}
function fileSize(size: number) {
  if (size < 1024 * 1024) return `${Math.max(1, Math.round(size / 1024))} KB`
  return `${(size / 1024 / 1024).toFixed(1)} MB`
}
function assetTypeLabel(asset: Asset) {
  if (asset.mime_type.startsWith('image/')) return locale.t('image')
  if (asset.mime_type.startsWith('video/')) return locale.t('video')
  if (asset.mime_type.startsWith('audio/')) return locale.t('audio')
  if (asset.mime_type === 'application/pdf') return 'PDF'
  return asset.extension.replace('.', '').toUpperCase() || locale.t('file')
}
function trackLink(link: { link_type: string; url: string }) {
  track({
    event_type: link.link_type === 'demo' ? 'demo_click' : link.link_type === 'repository' ? 'repository_click' : 'contact_click',
    page_type: 'project_detail',
    project_uuid: state.data.value?.uuid,
    event_data: { url: link.url },
  }, true)
}
function recordDwell() {
  if (!state.data.value) return
  track({
    event_type: 'project_dwell',
    page_type: 'project_detail',
    project_uuid: state.data.value.uuid,
    event_data: { seconds: Math.round((performance.now() - started.value) / 1000) },
  }, true)
}
watch(() => route.params.uuid, load)
onMounted(load)
onBeforeUnmount(recordDwell)
useMeta({ title, description })
</script>

<template>
  <LoadingState v-if="state.loading.value" class="container page-loading" :rows="9" />
  <ErrorState v-else-if="state.error.value" class="container page-loading" :message="state.error.value" @retry="load" />
  <article v-else-if="state.data.value" class="case-study">
    <header class="case-hero">
      <div class="container">
        <RouterLink class="back-link" :to="locale.publicPath('/projects')"><ArrowLeft :size="16" /> {{ locale.t('backProjects') }}</RouterLink>
        <div class="case-hero__grid">
          <div>
            <span class="eyebrow">{{ state.data.value.category?.name }} · {{ state.data.value.start_date }} — {{ state.data.value.end_date }}</span>
            <h1>{{ state.data.value.title }}</h1>
            <p>{{ state.data.value.subtitle || state.data.value.summary }}</p>
            <div class="case-hero__links">
              <a
                v-for="link in state.data.value.links"
                :key="link.uuid"
                class="button"
                :class="link.link_type === 'demo' ? 'button--dark' : 'button--outline'"
                :href="link.url"
                target="_blank"
                rel="noopener noreferrer"
                @click="trackLink(link)"
              >
                <ExternalLink v-if="link.link_type === 'demo'" :size="16" />
                <Code2 v-else :size="16" />
                {{ link.label }}
              </a>
            </div>
          </div>
          <dl class="case-facts">
            <div><dt><UserRound :size="16" />{{ locale.t('role') }}</dt><dd>{{ state.data.value.role }}</dd></div>
            <div><dt><Clock3 :size="16" />{{ locale.t('time') }}</dt><dd>{{ state.data.value.start_date }} — {{ state.data.value.end_date }}</dd></div>
            <div><dt><Layers3 :size="16" />{{ locale.t('status') }}</dt><dd>{{ locale.isEnglish ? state.data.value.project_state : projectStateLabel(state.data.value.project_state) }}</dd></div>
          </dl>
        </div>
      </div>
    </header>

    <div class="container case-body">
      <aside class="case-toc">
        <span class="eyebrow">{{ locale.t('page') }}</span>
        <a href="#overview">{{ locale.t('overview') }}</a>
        <a href="#problem">{{ locale.t('problem') }}</a>
        <a href="#architecture">{{ locale.t('architecture') }}</a>
        <a href="#contribution">{{ locale.t('contribution') }}</a>
        <a href="#outcomes">{{ locale.t('outcomes') }}</a>
        <a v-if="hasMedia" href="#media">{{ locale.t('media') }}</a>
      </aside>
      <div class="case-content">
        <section v-show="blockVisible('overview')" id="overview" class="case-section case-lead" :style="{ order: blockOrder('overview', 0) }">
          <span class="section-number">{{ blockNumber('overview', 0) }}</span>
          <div>
            <h2>{{ locale.t('overview') }}</h2>
            <p>{{ state.data.value.summary }}</p>
            <MarkdownContent v-if="state.data.value.content" :source="state.data.value.content" />
          </div>
        </section>
        <section v-show="blockVisible('problem')" id="problem" class="case-section" :style="{ order: blockOrder('problem', 1) }">
          <span class="section-number">{{ blockNumber('problem', 1) }}</span>
          <div class="case-split">
            <div>
              <h3>{{ locale.t('backgroundConstraints') }}</h3>
              <p>{{ state.data.value.background }}</p>
            </div>
            <div>
              <h3>{{ locale.t('coreProblem') }}</h3>
              <p>{{ state.data.value.problem }}</p>
            </div>
            <div class="case-split__wide">
              <h3>{{ locale.t('solution') }}</h3>
              <p>{{ state.data.value.solution }}</p>
            </div>
          </div>
        </section>
        <section v-show="blockVisible('architecture')" id="architecture" class="case-section" :style="{ order: blockOrder('architecture', 2) }">
          <span class="section-number">{{ blockNumber('architecture', 2) }}</span>
          <div>
            <h2>{{ locale.t('architecture') }}</h2>
            <p class="architecture-line">{{ state.data.value.architecture }}</p>
            <div class="tech-grid">
              <span v-for="tech in state.data.value.technologies" :key="tech">{{ tech }}</span>
            </div>
          </div>
        </section>
        <section v-show="blockVisible('contribution')" id="contribution" class="case-section" :style="{ order: blockOrder('contribution', 3) }">
          <span class="section-number">{{ blockNumber('contribution', 3) }}</span>
          <div>
            <h2>{{ locale.t('contribution') }}</h2>
            <ul class="evidence-list">
              <li v-for="item in state.data.value.contributions" :key="item">
                <CheckCircle2 :size="18" aria-hidden="true" />{{ item }}
              </li>
            </ul>
          </div>
        </section>
        <section v-show="blockVisible('outcomes')" id="outcomes" class="case-section case-outcomes" :style="{ order: blockOrder('outcomes', 4) }">
          <span class="section-number">{{ blockNumber('outcomes', 4) }}</span>
          <div>
            <h2>{{ locale.t('outcomes') }}</h2>
            <div class="outcome-grid">
              <article v-for="(item, index) in state.data.value.outcomes" :key="item">
                <span>{{ String(index + 1).padStart(2, '0') }}</span>
                <p>{{ item }}</p>
              </article>
            </div>
          </div>
        </section>
        <section v-if="hasMedia" v-show="blockVisible('media')" id="media" class="case-section" :style="{ order: blockOrder('media', 5) }">
          <span class="section-number">{{ blockNumber('media', 5) }}</span>
          <div>
            <h2>{{ locale.t('media') }}</h2>
            <section v-for="album in standaloneAlbums" :key="album.uuid" class="project-album">
              <header class="project-album__header">
                <h3>{{ album.title }}</h3>
                <p v-if="album.description">{{ album.description }}</p>
              </header>
              <div
                v-if="albumImages(album).length"
                class="gallery-grid"
                :class="{ 'gallery-grid--carousel': album.display_mode === 'carousel' }"
              >
                <button v-for="item in albumImages(album)" :key="item.uuid" type="button" @click="openImage(item)">
                  <img :src="item.asset.thumbnail_url || item.asset.content_url" :alt="item.caption || item.asset.description || item.asset.display_name" loading="lazy" />
                  <span>{{ item.caption || item.asset.display_name }}</span>
                </button>
              </div>
            </section>
            <div v-if="images.length" class="gallery-grid">
              <button v-for="item in images" :key="item.uuid" type="button" @click="openImage(item)">
                <img :src="item.asset.thumbnail_url || item.asset.content_url" :alt="item.caption || item.asset.description || item.asset.display_name" loading="lazy" />
                <span>{{ item.caption || item.asset.display_name }}</span>
              </button>
            </div>
            <div v-if="videos.length" class="video-grid">
              <figure v-for="item in videos" :key="item.uuid">
                <video
                  controls
                  preload="metadata"
                  playsinline
                  :poster="item.asset.thumbnail_url || undefined"
                  @play="track({ event_type: 'video_start', page_type: 'project_detail', project_uuid: state.data.value?.uuid, asset_uuid: item.asset.uuid })"
                  @ended="track({ event_type: 'video_progress', page_type: 'project_detail', project_uuid: state.data.value?.uuid, asset_uuid: item.asset.uuid, event_data: { progress: 1 } })"
                >
                  <source :src="item.asset.content_url" :type="item.asset.mime_type" />
                </video>
                <figcaption>
                  <strong>{{ item.caption || item.asset.display_name }}</strong>
                  <small>{{ assetTypeLabel(item.asset) }} · {{ fileSize(item.asset.size) }}</small>
                </figcaption>
              </figure>
            </div>
            <div v-if="documents.length" class="document-list">
              <RouterLink
                v-for="item in documents"
                :key="item.uuid"
                :to="locale.publicPath(`/assets/${item.asset.uuid}`)"
                @click="track({ event_type: 'document_preview', page_type: 'project_detail', project_uuid: state.data.value?.uuid, asset_uuid: item.asset.uuid })"
              >
                <span>{{ item.asset.extension.toUpperCase() }}</span>
                <strong>{{ item.caption || item.asset.display_name }}</strong>
                <small>{{ assetTypeLabel(item.asset) }} · {{ fileSize(item.asset.size) }}</small>
                <ArrowUpRight :size="18" />
              </RouterLink>
            </div>
          </div>
        </section>
        <section v-if="state.data.value.certificates.length" v-show="blockVisible('credentials')" id="credentials" class="case-section" :style="{ order: blockOrder('credentials', 6) }">
          <span class="section-number">{{ blockNumber('credentials', 6) }}</span>
          <div>
            <h2>{{ locale.t('credentials') }}</h2>
            <div class="certificate-strip">
              <article v-for="certificate in state.data.value.certificates" :key="certificate.uuid">
                <ConfiguredIcon
                  :image-uuid="certificate.icon_asset?.uuid"
                  :icon-name="certificate.icon_name || 'Medal'"
                  :icon-svg="certificate.icon_svg"
                  :size="24"
                />
                <div>
                  <span>{{ certificateTypeLabel(certificate.certificate_type) }} · {{ certificate.issued_at || locale.t('notProvided') }}</span>
                  <strong>{{ certificate.name }}</strong>
                  <small>{{ certificate.issuer }}</small>
                </div>
                <RouterLink :to="locale.publicPath(`/certificates/${certificate.uuid}`)">
                  {{ locale.t('viewDetails') }} <ArrowUpRight :size="15" />
                </RouterLink>
              </article>
            </div>
          </div>
        </section>
        <section
          v-for="(section, index) in state.data.value.sections"
          :key="section.uuid"
          class="case-section"
          v-show="section.is_visible && blockVisible(`custom:${section.client_key}`)"
          :style="{ order: blockOrder(`custom:${section.client_key}`, index + 7) }"
        >
          <span class="section-number">{{ blockNumber(`custom:${section.client_key}`, index + 7) }}</span>
          <div>
            <component :is="headingTag(section)" class="custom-section-title">{{ section.title }}</component>
            <MarkdownContent v-if="section.body" :source="section.body" />
            <header v-if="section.display_mode === 'album' && section.album" class="project-album__header">
              <h3>{{ section.album.title }}</h3>
              <p v-if="section.album.description">{{ section.album.description }}</p>
            </header>
            <div
              v-if="sectionMedia(section).length"
              class="section-media"
              :class="`section-media--${section.display_mode === 'album' ? section.album?.display_mode || 'grid' : section.display_mode}`"
            >
              <button
                v-for="item in sectionMedia(section)"
                :key="item.uuid"
                type="button"
                @click="openImage(item)"
              >
                <img
                  :src="item.asset.thumbnail_url || item.asset.content_url"
                  :alt="item.caption || item.asset.display_name"
                  loading="lazy"
                />
                <span>{{ item.caption || item.asset.display_name }}</span>
              </button>
            </div>
            <div v-if="sectionVideos(section).length" class="section-video-grid">
              <figure v-for="asset in sectionVideos(section)" :key="asset.uuid">
                <video
                  controls
                  playsinline
                  preload="metadata"
                  :poster="asset.thumbnail_url || undefined"
                  @play="track({ event_type: 'video_start', page_type: 'project_detail', project_uuid: state.data.value?.uuid, asset_uuid: asset.uuid })"
                  @ended="track({ event_type: 'video_progress', page_type: 'project_detail', project_uuid: state.data.value?.uuid, asset_uuid: asset.uuid, event_data: { progress: 1 } })"
                >
                  <source :src="asset.content_url" :type="asset.mime_type" />
                </video>
                <figcaption>
                  <strong>{{ asset.description || asset.display_name }}</strong>
                  <small>{{ assetTypeLabel(asset) }} · {{ fileSize(asset.size) }}</small>
                </figcaption>
              </figure>
            </div>
            <div v-if="sectionAudios(section).length" class="section-audio-list">
              <article v-for="asset in sectionAudios(section)" :key="asset.uuid">
                <Music2 :size="20" />
                <div><strong>{{ asset.display_name }}</strong><small>{{ asset.description || locale.t('audioResource') }}</small></div>
                <audio controls preload="metadata">
                  <source :src="asset.content_url" :type="asset.mime_type" />
                </audio>
              </article>
            </div>
            <div v-if="sectionAttachments(section).length" class="document-list section-attachments">
              <RouterLink
                v-for="asset in sectionAttachments(section)"
                :key="asset.uuid"
                :to="locale.publicPath(`/assets/${asset.uuid}`)"
                @click="track({ event_type: 'document_preview', page_type: 'project_detail', project_uuid: state.data.value?.uuid, asset_uuid: asset.uuid })"
              >
                <span><FileArchive v-if="asset.extension === '.zip'" :size="18" />{{ asset.extension.replace('.', '').toUpperCase() }}</span>
                <strong>{{ asset.description || asset.display_name }}</strong>
                <small>{{ asset.extension.replace('.', '').toUpperCase() || asset.mime_type }} · {{ fileSize(asset.size) }}</small>
                <ArrowUpRight :size="18" />
              </RouterLink>
            </div>
          </div>
        </section>
        <div class="case-next" style="order: 999">
          <span class="eyebrow">{{ locale.t('continue') }}</span>
          <RouterLink :to="locale.publicPath('/projects')">{{ locale.t('otherProjects') }} <ArrowUpRight :size="20" /></RouterLink>
        </div>
      </div>
    </div>
    <ImageLightbox :items="lightboxItems" :index="lightboxIndex" @close="lightboxIndex = null" @change="lightboxIndex = $event" />
  </article>
</template>
