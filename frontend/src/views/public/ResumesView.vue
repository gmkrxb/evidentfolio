<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { FileText } from 'lucide-vue-next'
import PdfViewer from '@/components/content/PdfViewer.vue'
import LoadingState from '@/components/ui/LoadingState.vue'
import ErrorState from '@/components/ui/ErrorState.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import { publicApi } from '@/api/public'
import { useAsyncState } from '@/composables/useAsync'
import { track, usePageAnalytics } from '@/composables/useAnalytics'
import { useMeta } from '@/composables/useMeta'
import { useSiteStore } from '@/stores/site'
import { useLocaleStore } from '@/stores/locale'
import type { ResumeVersion } from '@/types'

const state = useAsyncState<{ items: ResumeVersion[] }>()
const site = useSiteStore()
const locale = useLocaleStore()
const selected = ref<ResumeVersion | null>(null)
const pageContent = computed(() => site.settings.page_content?.resumes || {
  eyebrow: 'Resume',
  title: locale.t('resumes'),
  description: '',
})

async function load() {
  await state.run((signal) => publicApi.resumes(signal))
  selected.value = state.data.value?.items.find((item) => item.is_default) || state.data.value?.items[0] || null
  if (selected.value) {
    track({ event_type: 'resume_view', page_type: 'resume', page_uuid: selected.value.uuid, asset_uuid: selected.value.asset.uuid })
  }
}
function selectResume(item: ResumeVersion) {
  selected.value = item
  track({ event_type: 'resume_view', page_type: 'resume', page_uuid: item.uuid, asset_uuid: item.asset.uuid })
}
function download() {
  if (!selected.value) return
  track({ event_type: 'resume_download', page_type: 'resume', page_uuid: selected.value.uuid, asset_uuid: selected.value.asset.uuid }, true)
  window.location.href = selected.value.asset.download_url
}
function formatBytes(value: number) {
  return value < 1024 * 1024 ? `${(value / 1024).toFixed(0)} KB` : `${(value / 1024 / 1024).toFixed(1)} MB`
}
onMounted(load)
usePageAnalytics('resume')
useMeta({
  title: computed(() => `${pageContent.value.title}｜${site.settings.site_name || 'Portfolio'}`),
  description: computed(() => pageContent.value.description),
})
</script>

<template>
  <section class="page-hero page-hero--resume">
    <div class="container">
      <span class="eyebrow">{{ pageContent.eyebrow }}</span>
      <h1>{{ pageContent.title }}</h1>
      <p>{{ pageContent.description }}</p>
    </div>
  </section>
  <section class="resume-page">
    <div class="container">
      <LoadingState v-if="state.loading.value" :rows="8" />
      <ErrorState v-else-if="state.error.value" :message="state.error.value" @retry="load" />
      <EmptyState
        v-else-if="!state.data.value?.items.length"
        :title="locale.t('noResumes')"
        :description="locale.t('noResumesDescription')"
      />
      <div v-else class="resume-workspace">
        <aside class="resume-list">
          <span class="eyebrow">{{ locale.t('availableVersions') }}</span>
          <button
            v-for="item in state.data.value.items"
            :key="item.uuid"
            type="button"
            :class="{ active: selected?.uuid === item.uuid }"
            @click="selectResume(item)"
          >
            <FileText :size="19" />
            <span><strong>{{ item.name }}</strong><small>{{ item.language }} · {{ item.version }}</small></span>
            <em v-if="item.is_default">{{ locale.t('defaultLabel') }}</em>
          </button>
        </aside>
        <PdfViewer
          v-if="selected"
          :key="selected.uuid"
          :src="selected.asset.content_url"
          :title="selected.name"
          :meta="`${formatBytes(selected.asset.size)} · ${locale.t('updatedAt')} ${new Date(selected.updated_at).toLocaleDateString(locale.language)}`"
          @download="download"
        />
      </div>
    </div>
  </section>
</template>
