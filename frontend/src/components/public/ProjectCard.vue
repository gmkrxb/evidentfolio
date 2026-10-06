<script setup lang="ts">
import { ArrowUpRight, CircleDot, Code2, ExternalLink } from 'lucide-vue-next'
import { computed } from 'vue'
import type { Project } from '@/types'
import { useLocaleStore } from '@/stores/locale'
import ScrollText from '@/components/ui/ScrollText.vue'
import ProjectCover from '@/components/public/ProjectCover.vue'
import ProjectArt from '@/components/public/ProjectArt.vue'
import { projectCoverAssets } from '@/utils/projectCover'

const props = defineProps<{ project: Project; compact?: boolean; revealDelay?: number; story?: boolean; sequence?: number }>()
const locale = useLocaleStore()
const coverAssets = computed(() => projectCoverAssets(props.project))
const hasDetails = computed(() => props.project.role || props.project.is_open_source || props.project.links.some((item) => item.link_type === 'demo'))
</script>

<template>
  <article v-reveal="story ? false : { delay: revealDelay || 0, kind: 'card' }" v-scroll-progress="story ? { start: .96, end: .16 } : false" class="project-card" :class="{ 'project-card--compact': compact, 'project-card--story': story }" :data-scroll-key="project.uuid">
    <RouterLink class="project-card__visual" :to="locale.publicPath(`/projects/${project.uuid}`)" :aria-label="project.title">
      <ProjectCover v-if="coverAssets.length" :assets="coverAssets" />
      <ProjectArt v-else :seed="project.uuid" :index="sequence" />
    </RouterLink>
    <div class="project-card__body">
      <span v-if="story" class="project-card__sequence" data-locale-static>{{ String((sequence || 0) + 1).padStart(2, '0') }}</span>
      <div class="project-card__meta">
        <span>{{ project.category?.name || locale.t('uncategorized') }}</span>
        <span v-if="project.start_date || project.end_date">{{ [project.start_date, project.end_date].filter(Boolean).join(' — ') }}</span>
      </div>
      <RouterLink :to="locale.publicPath(`/projects/${project.uuid}`)">
        <ScrollText v-if="story" as="h3" :text="project.title" />
        <h3 v-else>{{ project.title }}</h3>
      </RouterLink>
      <p v-if="project.summary">{{ project.summary }}</p>
      <div v-if="hasDetails" class="project-card__details">
        <span v-if="project.role"><CircleDot :size="14" />{{ project.role }}</span>
        <span v-if="project.is_open_source"><Code2 :size="14" />{{ locale.t('openSource') }}</span>
        <span v-if="project.links.some((item) => item.link_type === 'demo')"><ExternalLink :size="14" />{{ locale.t('liveDemo') }}</span>
      </div>
      <div v-if="project.tags.length" class="tag-row">
        <span v-for="tag in project.tags.slice(0, 4)" :key="tag.uuid" class="tag">{{ tag.name }}</span>
      </div>
      <RouterLink class="text-link" :to="locale.publicPath(`/projects/${project.uuid}`)">
        {{ locale.t('viewCase') }} <ArrowUpRight :size="16" />
      </RouterLink>
    </div>
  </article>
</template>
