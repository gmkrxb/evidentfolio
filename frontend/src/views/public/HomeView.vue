<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { ArrowDown, ArrowRight, ArrowUpRight, Award, BrainCircuit, FileText, Layers3 } from 'lucide-vue-next'
import ProjectCard from '@/components/public/ProjectCard.vue'
import VibeCodeBackdrop from '@/components/public/VibeCodeBackdrop.vue'
import LoadingState from '@/components/ui/LoadingState.vue'
import ErrorState from '@/components/ui/ErrorState.vue'
import { publicApi } from '@/api/public'
import { useAsyncState } from '@/composables/useAsync'
import { usePageAnalytics, track } from '@/composables/useAnalytics'
import { useMeta } from '@/composables/useMeta'
import { useSiteStore } from '@/stores/site'
import { useLocaleStore } from '@/stores/locale'
import type { Project } from '@/types'

const site = useSiteStore()
const locale = useLocaleStore()
const featured = useAsyncState<{ items: Project[] }>()
const settings = computed(() => site.settings)
const projects = computed(() => featured.data.value?.items || [])
const homeStats = computed(() => settings.value.home_stats || [])
const homeCopy = computed(() => settings.value.home_copy || {})
const capabilities = computed(() => settings.value.home_capabilities || [])
const title = computed(() => String(settings.value.default_seo_title || settings.value.site_name || 'Portfolio'))
const description = computed(() => String(settings.value.default_seo_description || settings.value.bio || ''))

async function load() {
  await Promise.all([
    site.load().catch(() => undefined),
    featured.run(async (signal) => {
      const result = await publicApi.projects({ featured: true, page_size: 4 }, signal)
      return { items: result.items }
    }),
  ])
}
onMounted(load)
usePageAnalytics('home')
useMeta({ title, description })
</script>

<template>
  <div class="home">
    <section class="hero">
      <VibeCodeBackdrop />
      <div class="container hero__grid">
        <div class="hero__content">
          <span class="eyebrow hero__eyebrow">{{ settings.hero_eyebrow }}</span>
          <h1>
            {{ settings.person_name || settings.site_name }}
            <span>{{ settings.headline }}</span>
          </h1>
          <p class="hero__bio">{{ settings.bio }}</p>
          <div class="hero__actions">
            <RouterLink class="button button--dark" :to="locale.publicPath('/projects')">
              {{ locale.t('featuredProjects') }} <ArrowUpRight :size="17" />
            </RouterLink>
            <RouterLink
              class="button button--ghost"
              :to="locale.publicPath('/resumes')"
              @click="track({ event_type: 'resume_view', page_type: 'home' })"
            >
              <FileText :size="17" /> {{ locale.t('onlineResume') }}
            </RouterLink>
          </div>
          <a class="hero__scroll" href="#featured">
            <ArrowDown :size="16" /> {{ locale.t('scrollExplore') }}
          </a>
        </div>
        <div class="hero__signal" :aria-label="locale.t('researchOverview')">
          <div class="signal-orbit signal-orbit--one" />
          <div class="signal-orbit signal-orbit--two" />
          <div class="signal-core">
            <span>{{ settings.hero_focus_label }}</span>
            <strong>{{ settings.hero_focus_value }}</strong>
          </div>
          <div
            v-for="(direction, index) in (settings.research_directions || [])"
            :key="String(direction)"
            class="signal-label"
            :class="`signal-label--${index + 1}`"
          >
            {{ direction }}
          </div>
        </div>
      </div>
      <div v-if="homeStats.length" class="container hero__facts" :style="{ '--stat-count': homeStats.length }">
        <div v-for="item in homeStats" :key="`${item.value}:${item.label}`">
          <strong>{{ item.value }}</strong><span>{{ item.label }}</span>
        </div>
      </div>
    </section>

    <section id="featured" class="section section--projects">
      <div class="container">
        <div class="section-heading">
          <div>
            <span class="eyebrow">{{ homeCopy.projects_eyebrow }}</span>
            <h2>{{ homeCopy.projects_title }}</h2>
          </div>
          <p>{{ homeCopy.projects_description }}</p>
        </div>
        <LoadingState v-if="featured.loading.value" :rows="5" />
        <ErrorState v-else-if="featured.error.value" :message="featured.error.value" @retry="load" />
        <div v-else class="featured-grid">
          <ProjectCard v-for="project in projects" :key="project.uuid" :project="project" />
        </div>
        <div class="section-action">
          <RouterLink class="text-link text-link--large" :to="locale.publicPath('/projects')">
            {{ locale.t('allProjects') }} <ArrowRight :size="18" />
          </RouterLink>
        </div>
      </div>
    </section>

    <section class="section capability-section">
      <div class="container capability-grid">
        <div class="section-heading section-heading--vertical">
          <span class="eyebrow">{{ homeCopy.capabilities_eyebrow }}</span>
          <h2>{{ homeCopy.capabilities_title }}</h2>
          <p>{{ homeCopy.capabilities_description }}</p>
        </div>
        <div class="capability-list">
          <article v-for="(item, index) in capabilities" :key="item.title" v-reveal="index * 70">
            <span>{{ String(index + 1).padStart(2, '0') }}</span>
            <BrainCircuit v-if="index === 0" :size="24" />
            <Layers3 v-else-if="index === 1" :size="24" />
            <Award v-else :size="24" />
            <div>
              <h3>{{ item.title }}</h3>
              <p>{{ item.description }}</p>
            </div>
          </article>
        </div>
      </div>
    </section>

    <section class="section category-section">
      <div class="container">
        <div class="section-heading">
          <div>
            <span class="eyebrow">{{ homeCopy.categories_eyebrow }}</span>
            <h2>{{ homeCopy.categories_title }}</h2>
          </div>
        </div>
        <div class="category-links">
          <RouterLink
            v-for="(category, index) in site.categories"
            :key="category.uuid"
            :to="{ path: locale.publicPath('/projects'), query: { category: category.uuid } }"
          >
            <span>{{ String(index + 1).padStart(2, '0') }}</span>
            <strong>{{ category.name }}</strong>
            <small>{{ category.description }}</small>
            <ArrowUpRight :size="20" />
          </RouterLink>
        </div>
      </div>
    </section>

    <section class="section cta-section">
      <div class="container cta-panel">
        <div>
          <span class="eyebrow">{{ homeCopy.contact_eyebrow }}</span>
          <h2>{{ settings.current_identity }}</h2>
        </div>
        <div>
          <p>{{ homeCopy.contact_description }}</p>
          <RouterLink class="button button--light" :to="locale.publicPath('/contact')">{{ locale.t('contactMe') }} <ArrowUpRight :size="17" /></RouterLink>
        </div>
      </div>
    </section>
  </div>
</template>
