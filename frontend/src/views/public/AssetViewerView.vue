<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ArrowLeft, Download, Eye, FileQuestion, FileSpreadsheet, PackageOpen } from 'lucide-vue-next'
import { useRoute, useRouter } from 'vue-router'
import MarkdownContent from '@/components/content/MarkdownContent.vue'
import PdfViewer from '@/components/content/PdfViewer.vue'
import AssetMedia from '@/components/content/AssetMedia.vue'
import { downloadAsset, protectedText } from '@/utils/protectedAsset'
import LoadingState from '@/components/ui/LoadingState.vue'
import ErrorState from '@/components/ui/ErrorState.vue'
import { publicApi } from '@/api/public'
import { useAsyncState } from '@/composables/useAsync'
import { useLocaleReload } from '@/composables/useLocaleReload'
import { track, usePageAnalytics } from '@/composables/useAnalytics'
import { useMeta } from '@/composables/useMeta'
import { useSiteStore } from '@/stores/site'
import { useLocaleStore } from '@/stores/locale'

const route = useRoute()
const locale = useLocaleStore()
const site = useSiteStore()
const state = useAsyncState<Awaited<ReturnType<typeof publicApi.asset>>>({ keepPreviousData: true })
const text = useAsyncState<string>({ keepPreviousData: true })
const structuredPreview = useAsyncState<Awaited<ReturnType<typeof publicApi.assetPreview>>>({ keepPreviousData: true })
const isText = computed(() => {
  const asset = state.data.value
  return asset ? asset.mime_type.startsWith('text/') || ['.json', '.yaml', '.yml', '.csv', '.md'].includes(asset.extension) : false
})
const isProtected = computed(() => Boolean(state.data.value?.protected))
const downloadError = ref('')
const isMarkdown = computed(() => ['.md', '.markdown'].includes(state.data.value?.extension || ''))
const hasStructuredPreview = computed(() =>
  ['.zip', '.docx', '.xlsx', '.pptx'].includes(state.data.value?.extension || ''),
)

async function load() {
  await state.run((signal) => publicApi.asset(String(route.params.uuid), signal))
  if (state.data.value && isText.value) {
    await text.run(async (signal) => {
      const asset = state.data.value!
      if (asset.protected) return (await protectedText(asset, signal)).slice(0, 2_000_000)
      const response = await fetch(asset.content_url, { credentials: 'include', signal })
      if (!response.ok) throw new Error(locale.t('textLoadFailed'))
      const content = await response.text()
      return content.slice(0, 2_000_000)
    })
  }
  if (state.data.value && hasStructuredPreview.value) {
    await structuredPreview.run((signal) => publicApi.assetPreview(state.data.value!.uuid, signal))
  }
  if (state.data.value) {
    track({ event_type: 'document_preview', page_type: 'asset', asset_uuid: state.data.value.uuid })
  }
}
const router = useRouter()
// 从项目详情点进来时，返回原页面并恢复阅读位置；直接打开链接时回到项目列表。
function goBack(event: MouseEvent) {
  if (window.history.state?.back) { event.preventDefault(); router.back() }
}
async function download() {
  const asset = state.data.value
  if (!asset || asset.protected) return
  track({ event_type: 'document_download', page_type: 'asset', asset_uuid: asset.uuid }, true)
  downloadError.value = ''
  try { await downloadAsset(asset) } catch (error) { downloadError.value = error instanceof Error ? error.message : String(error) }
}
useLocaleReload(load)
onMounted(load)
usePageAnalytics('asset', String(route.params.uuid))
useMeta({
  title: computed(() => `${state.data.value?.display_name || locale.t('assetPreview')}｜${site.settings.site_name || 'Portfolio'}`),
  description: computed(() => state.data.value?.description || locale.t('assetPreviewDescription')),
})
</script>

<template>
  <section class="asset-viewer-page">
    <div class="container">
      <RouterLink class="back-link" :to="locale.publicPath('/projects')" @click="goBack"><ArrowLeft :size="16" /> {{ locale.t('backProjects') }}</RouterLink>
      <LoadingState v-if="state.loading.value" :rows="8" />
      <ErrorState v-else-if="state.error.value" :message="state.error.value" @retry="load" />
      <div v-else-if="state.data.value" class="asset-viewer">
        <header>
          <div>
            <span class="eyebrow">{{ state.data.value.extension.toUpperCase() }} · {{ (state.data.value.size / 1024 / 1024).toFixed(2) }} MB</span>
            <h1>{{ state.data.value.display_name }}</h1>
            <p>{{ state.data.value.description }}</p>
          </div>
          <span v-if="isProtected" class="asset-view-only"><Eye :size="15" /> {{ locale.isEnglish ? 'View only · encrypted' : '仅可查看 · 加密传输' }}</span>
          <button v-else-if="state.data.value.mime_type !== 'application/pdf'" class="button button--dark" @click="download"><Download :size="17" /> {{ locale.t('downloadOriginal') }}</button>
          <p v-if="downloadError" class="asset-download-error" role="alert">{{ downloadError }}</p>
        </header>
        <div class="asset-preview" :class="{ 'asset-preview--pdf': state.data.value.mime_type === 'application/pdf', 'asset-preview--document': isMarkdown }">
          <AssetMedia
            v-if="['image/', 'video/', 'audio/'].some((prefix) => state.data.value!.mime_type.startsWith(prefix))"
            :asset="state.data.value"
            :alt="state.data.value.description || state.data.value.display_name"
          />
          <PdfViewer
            v-else-if="state.data.value.mime_type === 'application/pdf'"
            :src="state.data.value.content_url"
            :protected-asset="state.data.value.protected ? state.data.value : null"
            :title="state.data.value.display_name"
            :meta="`${(state.data.value.size / 1024 / 1024).toFixed(2)} MB`"
            @download="download"
          />
          <LoadingState v-else-if="hasStructuredPreview && structuredPreview.loading.value" :rows="8" />
          <ErrorState
            v-else-if="hasStructuredPreview && structuredPreview.error.value"
            :message="structuredPreview.error.value"
            @retry="load"
          />
          <div
            v-else-if="structuredPreview.data.value?.kind === 'office'"
            class="office-preview"
          >
            <header><FileSpreadsheet :size="26" /><div><strong>{{ locale.t('safeDocumentPreview') }}</strong><span>{{ locale.t('safeDocumentDescription') }}</span></div></header>
            <section v-for="section in structuredPreview.data.value.sections || []" :key="section.title">
              <h2>{{ section.title }}</h2>
              <p v-for="(line, index) in section.lines" :key="`${index}-${line}`">{{ line }}</p>
              <span v-if="!section.lines.length">{{ locale.t('noExtractedText') }}</span>
            </section>
          </div>
          <div
            v-else-if="structuredPreview.data.value?.kind === 'archive'"
            class="archive-preview"
          >
            <header>
              <PackageOpen :size="28" />
              <div><strong>{{ locale.t('archiveContents') }}</strong><span>{{ structuredPreview.data.value.entry_count }} {{ locale.t('entries') }} · {{ locale.t('archiveDescription') }}</span></div>
            </header>
            <ol>
              <li v-for="entry in structuredPreview.data.value.entries || []" :key="entry.name">
                <span>{{ entry.name }}</span>
                <small>{{ entry.is_directory ? locale.t('directory') : `${(entry.size / 1024).toFixed(1)} KB` }}</small>
              </li>
            </ol>
            <p v-if="structuredPreview.data.value.truncated">{{ locale.t('archiveTruncated') }}</p>
          </div>
          <LoadingState v-else-if="isText && text.loading.value" :rows="8" />
          <MarkdownContent v-else-if="isMarkdown && text.data.value" v-protect="isProtected" :source="text.data.value" />
          <pre v-else-if="isText && text.data.value" v-protect="isProtected"><code>{{ text.data.value }}</code></pre>
          <div v-else class="unsupported-preview">
            <FileQuestion :size="36" />
            <h2>{{ locale.t('unsupportedPreview') }}</h2>
            <p>{{ locale.t('unsupportedPreviewDescription') }}</p>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>
