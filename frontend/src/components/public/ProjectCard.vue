<script setup lang="ts">
import { ArrowUpRight, CircleDot, Code2, ExternalLink } from 'lucide-vue-next'
import type { Project } from '@/types'
import { useLocaleStore } from '@/stores/locale'

defineProps<{ project: Project; compact?: boolean }>()
const locale = useLocaleStore()
</script>

<template>
  <article v-reveal class="project-card" :class="{ 'project-card--compact': compact }">
    <RouterLink class="project-card__visual" :to="locale.publicPath(`/projects/${project.uuid}`)" :aria-label="project.title">
      <img
        v-if="project.cover_asset?.thumbnail_url"
        :src="project.cover_asset.thumbnail_url"
        :alt="project.cover_asset.description || `${project.title} ${locale.t('cover')}`"
        loading="lazy"
      />
      <div
        v-else-if="project.auto_cover_assets?.length"
        class="project-card__collage"
        :class="`project-card__collage--${Math.min(project.auto_cover_assets.length, 4)}`"
      >
        <img
          v-for="asset in project.auto_cover_assets.slice(0, 4)"
          :key="asset.uuid"
          :src="asset.thumbnail_url || asset.content_url"
          :alt="asset.description || asset.display_name"
          loading="lazy"
        />
        <span>{{ locale.t('autoCover') }}</span>
      </div>
      <div v-else class="project-card__placeholder">
        <span>{{ project.category?.name || 'PROJECT' }}</span>
        <strong>{{ project.title.slice(0, 2) }}</strong>
      </div>
    </RouterLink>
    <div class="project-card__body">
      <div class="project-card__meta">
        <span>{{ project.category?.name || locale.t('uncategorized') }}</span>
        <span>{{ project.start_date }}{{ project.end_date ? ` — ${project.end_date}` : '' }}</span>
      </div>
      <RouterLink :to="locale.publicPath(`/projects/${project.uuid}`)">
        <h3>{{ project.title }}</h3>
      </RouterLink>
      <p>{{ project.summary }}</p>
      <div class="project-card__details">
        <span><CircleDot :size="14" />{{ project.role }}</span>
        <span v-if="project.is_open_source"><Code2 :size="14" />{{ locale.t('openSource') }}</span>
        <span v-if="project.links.some((item) => item.link_type === 'demo')"><ExternalLink :size="14" />{{ locale.t('liveDemo') }}</span>
      </div>
      <div class="tag-row">
        <span v-for="tag in project.tags.slice(0, 4)" :key="tag.uuid" class="tag">{{ tag.name }}</span>
      </div>
      <RouterLink class="text-link" :to="locale.publicPath(`/projects/${project.uuid}`)">
        {{ locale.t('viewCase') }} <ArrowUpRight :size="16" />
      </RouterLink>
    </div>
  </article>
</template>
