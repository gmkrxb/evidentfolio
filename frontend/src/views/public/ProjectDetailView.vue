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
import AssetMedia from '@/components/content/AssetMedia.vue'
import { publicApi } from '@/api/public'
import { useAsyncState } from '@/composables/useAsync'
import { useLocaleReload } from '@/composables/useLocaleReload'
import { track, usePageAnalytics } from '@/composables/useAnalytics'
import { privacy } from '@/stores/privacy'
import { useMeta } from '@/composables/useMeta'
import { useSiteStore } from '@/stores/site'
import { useLocaleStore } from '@/stores/locale'
import type { Asset, ProjectAlbum, ProjectAsset, ProjectSection } from '@/types'
import ConfiguredIcon from '@/components/icons/ConfiguredIcon.vue'
import ProjectReadingBar from '@/components/public/ProjectReadingBar.vue'
import { certificateTypeLabel, projectStateLabel } from '@/utils/labels'
import ProjectCover from '@/components/public/ProjectCover.vue'
import ProjectArt from '@/components/public/ProjectArt.vue'
import { projectCoverAssets } from '@/utils/projectCover'
import { usePinProgress } from '@/composables/usePinProgress'

const route = useRoute()
const site = useSiteStore()
const locale = useLocaleStore()
const state = useAsyncState<Awaited<ReturnType<typeof publicApi.project>>>({ keepPreviousData: true })
const lightboxIndex = ref<number | null>(null)
const hero = ref<HTMLElement | null>(null)
const started = ref(performance.now())
let recordedProject = ''
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
  await state.run((signal) => publicApi.project(String(route.params.uuid), signal))

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
  if (layoutEntry(key)?.visible === false || !state.data.value) return false
  const project = state.data.value
  const content: Record<string, unknown> = {
    overview: project.summary || project.content,
    problem: project.background || project.problem || project.solution,
    architecture: project.architecture || project.technologies.length,
    contribution: project.contributions.length,
    outcomes: project.outcomes.length,
    media: hasMedia.value,
    credentials: project.certificates?.length,
  }
  if (key in content) return Boolean(content[key])
  const section = project.sections.find((item) => `custom:${item.client_key}` === key)
  return Boolean(section?.is_visible && (section.title || section.body || sectionAssets(section).length))
}
function blockOrder(key: string, fallback: number) {
  return layoutEntry(key)?.sort_order ?? fallback
}
function blockNumber(key: string, _fallback: number) {
  const keys = ['overview', 'problem', 'architecture', 'contribution', 'outcomes', 'media', 'credentials', ...(state.data.value?.sections || []).map((item) => `custom:${item.client_key}`)]
  const visible = keys.map((key, index) => ({ key, order: blockOrder(key, index) })).filter((item) => blockVisible(item.key)).sort((a, b) => a.order - b.order)
  return String(Math.max(0, visible.findIndex((item) => item.key === key)) + 1).padStart(2, '0')
}
const cover = ref<HTMLElement | null>(null)
usePinProgress(cover, { mode: 'pass' })
const coverAssets = computed(() => (state.data.value ? projectCoverAssets(state.data.value) : []))
const tocItems = computed(() => {
  const project = state.data.value
  if (!project) return []
  const builtins = (['overview', 'problem', 'architecture', 'contribution', 'outcomes', 'media', 'credentials'] as const)
    .map((key, index) => ({ key, id: key, label: locale.t(key), order: blockOrder(key, index) }))
  const custom = project.sections.map((section, index) => ({
    key: `custom:${section.client_key}`,
    id: sectionAnchor(section),
    label: section.title,
    order: blockOrder(`custom:${section.client_key}`, index + 7),
  }))
  return [...builtins, ...custom].filter((item) => item.label && blockVisible(item.key)).sort((a, b) => a.order - b.order)
})
function sectionAnchor(section: ProjectSection) {
  return `section-${String(section.client_key || section.uuid || section.sort_order).replace(/[^\w-]/g, '')}`
}
const activeSection = ref('')
let tocFrame = 0
function trackSection() {
  tocFrame = 0
  const line = window.innerHeight * 0.35
  let current = ''
  for (const item of tocItems.value) {
    const element = document.getElementById(item.id)
    if (element && element.offsetParent !== null && element.getBoundingClientRect().top <= line) current = item.id
  }
  activeSection.value = current || tocItems.value[0]?.id || ''
}
function scheduleTrack() { if (!tocFrame) tocFrame = requestAnimationFrame(trackSection) }
onMounted(() => window.addEventListener('scroll', scheduleTrack, { passive: true }))
onBeforeUnmount(() => { window.removeEventListener('scroll', scheduleTrack); cancelAnimationFrame(tocFrame) })
watch(tocItems, scheduleTrack, { flush: 'post' })
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
  if (!state.data.value || !recordedProject) return
  track({
    event_type: 'project_dwell',
    page_type: 'project_detail',
    project_uuid: state.data.value.uuid,
    event_data: { seconds: Math.round((performance.now() - started.value) / 1000) },
  }, true)
}
watch([() => privacy.ready && privacy.analytics, () => state.data.value?.uuid], ([allowed, uuid]) => {
  if (!allowed || !uuid) { recordedProject = ''; return }
  if (recordedProject === uuid) return
  recordedProject = String(uuid); started.value = performance.now()
  track({ event_type: 'project_view', page_type: 'project_detail', project_uuid: String(uuid) })
})
watch(() => route.params.uuid, load)
useLocaleReload(load)
onMounted(load)
usePageAnalytics('project_detail', String(route.params.uuid))
onBeforeUnmount(recordDwell)
useMeta({ title, description })
</script>

<template>
  <LoadingState v-if="state.loading.value" class="container page-loading" :rows="9" />
  <ErrorState v-else-if="state.error.value" class="container page-loading" :message="state.error.value" @retry="load" />
  <article v-else-if="state.data.value" class="case-study">
    <ProjectReadingBar :hero="hero" :title="state.data.value.title" />
    <header ref="hero" class="case-hero">
      <div class="container">
        <RouterLink class="back-link" :to="locale.publicPath('/projects')"><ArrowLeft :size="16" /> {{ locale.t('backProjects') }}</RouterLink>
        <div class="case-hero__grid">
          <div>
            <span class="eyebrow">{{ state.data.value.category?.name || (locale.isEnglish ? 'Project / Case study' : '项目 / 案例研究') }}</span>
            <h1 tabindex="-1">{{ state.data.value.title }}</h1>
            <p>{{ state.data.value.subtitle || state.data.value.summary }}</p>
            <div v-if="state.data.value.links.length" class="case-hero__links">
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
            <div v-if="state.data.value.role"><dt><UserRound :size="16" />{{ locale.t('role') }}</dt><dd>{{ state.data.value.role }}</dd></div>
            <div v-if="state.data.value.start_date || state.data.value.end_date"><dt><Clock3 :size="16" />{{ locale.t('time') }}</dt><dd>{{ [state.data.value.start_date, state.data.value.end_date].filter(Boolean).join(' — ') }}</dd></div>
            <div><dt><Layers3 :size="16" />{{ locale.t('status') }}</dt><dd>{{ locale.isEnglish ? ({ active: 'In progress', completed: 'Completed', research: 'Research' }[state.data.value.project_state] || state.data.value.project_state) : projectStateLabel(state.data.value.project_state) }}</dd></div>
          </dl>
        </div>
        <div ref="cover" class="case-cover">
          <ProjectCover v-if="coverAssets.length" :assets="coverAssets" eager />
          <ProjectArt v-else :seed="state.data.value.uuid" :label="state.data.value.title" />
        </div>
      </div>
    </header>

    <div class="container case-body">
      <aside class="case-toc">
        <span class="eyebrow">{{ locale.t('page') }}</span>
        <a v-for="item in tocItems" :key="item.id" :href="`#${item.id}`" :class="{ 'is-active': activeSection === item.id }" :aria-current="activeSection === item.id ? 'location' : undefined">{{ item.label }}</a>
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
            <div v-if="state.data.value.background">
              <h3>{{ locale.t('backgroundConstraints') }}</h3>
              <p>{{ state.data.value.background }}</p>
            </div>
            <div v-if="state.data.value.problem">
              <h3>{{ locale.t('coreProblem') }}</h3>
              <p>{{ state.data.value.problem }}</p>
            </div>
            <div v-if="state.data.value.solution" class="case-split__wide">
              <h3>{{ locale.t('solution') }}</h3>
              <p>{{ state.data.value.solution }}</p>
            </div>
          </div>
        </section>
        <section v-show="blockVisible('architecture')" id="architecture" class="case-section" :style="{ order: blockOrder('architecture', 2) }">
          <span class="section-number">{{ blockNumber('architecture', 2) }}</span>
          <div>
            <h2>{{ locale.t('architecture') }}</h2>
            <p v-if="state.data.value.architecture" class="architecture-line">{{ state.data.value.architecture }}</p>
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
                  <AssetMedia :asset="item.asset" kind="image" thumbnail :alt="item.caption || item.asset.description || item.asset.display_name" loading="lazy" />
                  <span>{{ item.caption || item.asset.display_name }}</span>
                </button>
              </div>
            </section>
            <div v-if="images.length" class="gallery-grid">
              <button v-for="item in images" :key="item.uuid" type="button" @click="openImage(item)">
                <AssetMedia :asset="item.asset" kind="image" thumbnail :alt="item.caption || item.asset.description || item.asset.display_name" loading="lazy" />
                <span>{{ item.caption || item.asset.display_name }}</span>
              </button>
            </div>
            <div v-if="videos.length" class="video-grid">
              <figure v-for="item in videos" :key="item.uuid">
                <AssetMedia
                  :asset="item.asset"
                  kind="video"
                  @play="track({ event_type: 'video_start', page_type: 'project_detail', project_uuid: state.data.value?.uuid, asset_uuid: item.asset.uuid })"
                  @ended="track({ event_type: 'video_progress', page_type: 'project_detail', project_uuid: state.data.value?.uuid, asset_uuid: item.asset.uuid, event_data: { progress: 1 } })"
                />
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
          :id="sectionAnchor(section)"
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
                <AssetMedia
                  :asset="item.asset"
                  kind="image"
                  thumbnail
                  :alt="item.caption || item.asset.display_name"
                  loading="lazy"
                />
                <span>{{ item.caption || item.asset.display_name }}</span>
              </button>
            </div>
            <div v-if="sectionVideos(section).length" class="section-video-grid">
              <figure v-for="asset in sectionVideos(section)" :key="asset.uuid">
                <AssetMedia
                  :asset="asset"
                  kind="video"
                  @play="track({ event_type: 'video_start', page_type: 'project_detail', project_uuid: state.data.value?.uuid, asset_uuid: asset.uuid })"
                  @ended="track({ event_type: 'video_progress', page_type: 'project_detail', project_uuid: state.data.value?.uuid, asset_uuid: asset.uuid, event_data: { progress: 1 } })"
                />
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
                <AssetMedia :asset="asset" kind="audio" />
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
