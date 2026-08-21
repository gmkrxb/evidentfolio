<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { Grid2X2, List, Search, SlidersHorizontal, X } from 'lucide-vue-next'
import { useRoute, useRouter } from 'vue-router'
import ProjectCard from '@/components/public/ProjectCard.vue'
import LoadingState from '@/components/ui/LoadingState.vue'
import ErrorState from '@/components/ui/ErrorState.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import BaseSelect from '@/components/ui/BaseSelect.vue'
import { publicApi } from '@/api/public'
import { useAsyncState } from '@/composables/useAsync'
import { track, usePageAnalytics } from '@/composables/useAnalytics'
import { useMeta } from '@/composables/useMeta'
import { useSiteStore } from '@/stores/site'
import { useLocaleStore } from '@/stores/locale'
import type { Project } from '@/types'

const route = useRoute()
const router = useRouter()
const site = useSiteStore()
const locale = useLocaleStore()
const state = useAsyncState<{ items: Project[]; total: number }>()
const q = ref(String(route.query.q || ''))
const category = ref(String(route.query.category || ''))
const selectedTags = ref<string[]>(
  Array.isArray(route.query.tags) ? route.query.tags.map(String) : route.query.tags ? [String(route.query.tags)] : [],
)
const sort = ref(String(route.query.sort || 'featured'))
const mode = ref<'grid' | 'list'>((localStorage.getItem('project-view-mode') as 'grid' | 'list') || 'grid')
const pageContent = computed(() => site.settings.page_content?.projects || {
  eyebrow: 'Projects',
  title: locale.t('projects'),
  description: '',
})
const categoryOptions = computed(() => [
  { value: '', label: locale.t('allCategories') },
  ...site.categories.map((item) => ({ value: item.uuid, label: item.name, description: item.description })),
])
const sortOptions = computed(() => [
  { value: 'featured', label: locale.t('featuredFirst') },
  { value: 'latest', label: locale.t('latestFirst') },
  { value: 'oldest', label: locale.t('oldestFirst') },
  { value: 'title', label: locale.t('titleSort') },
])
let debounce = 0

async function load() {
  await site.load().catch(() => undefined)
  await state.run(async (signal) => {
    const result = await publicApi.projects(
      { q: q.value || undefined, category: category.value || undefined, tags: selectedTags.value, sort: sort.value, page_size: 50 },
      signal,
    )
    return { items: result.items, total: result.pagination.total }
  })
}
function syncQuery() {
  router.replace({
    query: {
      ...(q.value ? { q: q.value } : {}),
      ...(category.value ? { category: category.value } : {}),
      ...(selectedTags.value.length ? { tags: selectedTags.value } : {}),
      ...(sort.value !== 'featured' ? { sort: sort.value } : {}),
    },
  })
  window.clearTimeout(debounce)
  debounce = window.setTimeout(() => {
    track({
      event_type: q.value ? 'search' : 'filter_use',
      page_type: 'project_list',
      event_data: { q: q.value, category: category.value, tags: selectedTags.value, sort: sort.value },
    })
    load()
  }, 250)
}
function toggleTag(uuid: string) {
  selectedTags.value = selectedTags.value.includes(uuid)
    ? selectedTags.value.filter((item) => item !== uuid)
    : [...selectedTags.value, uuid]
}
function clearFilters() {
  q.value = ''
  category.value = ''
  selectedTags.value = []
  sort.value = 'featured'
}
function setMode(next: 'grid' | 'list') {
  mode.value = next
  localStorage.setItem('project-view-mode', next)
}
watch([category, selectedTags, sort], syncQuery, { deep: true })
watch(q, syncQuery)
onMounted(load)
usePageAnalytics('project_list')
useMeta({
  title: computed(() => `${pageContent.value.title}｜${site.settings.site_name || 'Portfolio'}`),
  description: computed(() => pageContent.value.description),
})
</script>

<template>
  <section class="page-hero page-hero--projects">
    <div class="container">
      <span class="eyebrow">{{ pageContent.eyebrow }}</span>
      <h1>{{ pageContent.title }}</h1>
      <p>{{ pageContent.description }}</p>
    </div>
  </section>
  <section class="projects-browser">
    <div class="container">
      <div class="filter-bar">
        <label class="search-field">
          <Search :size="18" aria-hidden="true" />
          <span class="sr-only">{{ locale.t('searchProjects') }}</span>
          <input v-model="q" type="search" :placeholder="locale.t('searchProjects')" />
          <button v-if="q" type="button" :aria-label="locale.t('clearSearch')" @click="q = ''"><X :size="15" /></button>
        </label>
        <BaseSelect v-model="category" :label="locale.t('allCategories')" :options="categoryOptions" />
        <BaseSelect v-model="sort" :label="locale.t('titleSort')" :options="sortOptions" />
        <div class="view-switch" role="group">
          <button :class="{ active: mode === 'grid' }" :aria-label="locale.t('gridView')" @click="setMode('grid')"><Grid2X2 :size="17" /></button>
          <button :class="{ active: mode === 'list' }" :aria-label="locale.t('listView')" @click="setMode('list')"><List :size="18" /></button>
        </div>
      </div>
      <div class="filter-tags">
        <span><SlidersHorizontal :size="15" /> {{ locale.t('technologyTags') }}</span>
        <button
          v-for="tag in site.tags"
          :key="tag.uuid"
          type="button"
          :class="{ active: selectedTags.includes(tag.uuid) }"
          @click="toggleTag(tag.uuid)"
        >
          {{ tag.name }}
        </button>
      </div>
      <div class="results-bar">
        <span>{{ state.data.value?.total || 0 }} {{ locale.t('projectCount') }}</span>
        <button v-if="q || category || selectedTags.length || sort !== 'featured'" type="button" @click="clearFilters">
          {{ locale.t('clearFilters') }}
        </button>
      </div>
      <LoadingState v-if="state.loading.value" :rows="7" />
      <ErrorState v-else-if="state.error.value" :message="state.error.value" @retry="load" />
      <EmptyState
        v-else-if="!state.data.value?.items.length"
        :title="locale.t('noProjects')"
        :description="locale.t('noProjectsDescription')"
      >
        <button class="button button--outline button--small" @click="clearFilters">{{ locale.t('clearFilters') }}</button>
      </EmptyState>
      <div v-else class="projects-grid" :class="{ 'projects-grid--list': mode === 'list' }">
        <ProjectCard
          v-for="project in state.data.value.items"
          :key="project.uuid"
          :project="project"
          :compact="mode === 'list'"
        />
      </div>
    </div>
  </section>
</template>
