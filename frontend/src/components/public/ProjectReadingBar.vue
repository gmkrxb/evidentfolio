<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { ArrowLeft, ArrowUp } from 'lucide-vue-next'
import { useLocaleStore } from '@/stores/locale'
import { PAGE_LAYOUT_EVENT } from '@/utils/pageNavigation'
import { readingProgress } from '@/utils/readingProgress'

const props = defineProps<{ hero: HTMLElement | null; title: string }>()
const locale = useLocaleStore()
const bar = ref<HTMLElement>()
const visible = ref(false)
const percentage = ref(0)
let frame = 0
let sizes: ResizeObserver | undefined
function render() {
  frame = 0
  if (!props.hero || !bar.value) return
  const inset = document.querySelector<HTMLElement>('.public-header')?.getBoundingClientRect().bottom || 72
  const bottom = props.hero.getBoundingClientRect().bottom
  const progress = Math.min(1, Math.max(0, (inset + 108 - bottom) / 96))
  const article = props.hero.closest('article')
  const content = article?.querySelector('.case-content')?.getBoundingClientRect()
  const read = content ? readingProgress(scrollY, content.top + scrollY, content.bottom + scrollY, innerHeight, inset + bar.value.offsetHeight + 24) : 0
  bar.value.style.setProperty('--reading-collapse', String(progress))
  bar.value.style.setProperty('--reading-progress', String(read))
  article?.style.setProperty('--reading-top', `${inset}px`)
  props.hero.style.setProperty('--title-collapse', String(progress))
  percentage.value = Math.round(read * 100)
  if (!progress && bar.value.contains(document.activeElement)) focusTitle()
  visible.value = progress > 0
}
function schedule() { if (!frame) frame = requestAnimationFrame(render) }
function focusTitle() { props.hero?.querySelector<HTMLElement>('h1')?.focus({ preventScroll: true }) }
function backToTop() {
  focusTitle()
  window.scrollTo({ top: 0, behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'instant' : 'smooth' })
}
watch(() => props.hero, (hero, previous) => {
  if (previous) sizes?.unobserve(previous)
  if (hero) sizes?.observe(hero)
  schedule()
}, { flush: 'post' })
onMounted(() => {
  window.addEventListener('scroll', schedule, { passive: true })
  window.addEventListener('resize', schedule, { passive: true })
  window.addEventListener(PAGE_LAYOUT_EVENT, render)
  sizes = new ResizeObserver(schedule)
  if (props.hero) sizes.observe(props.hero)
  const content = props.hero?.closest('article')?.querySelector('.case-content')
  if (content) sizes.observe(content)
  const header = document.querySelector('.public-header')
  if (header) sizes.observe(header)
  schedule()
})
onBeforeUnmount(() => { window.removeEventListener('scroll', schedule); window.removeEventListener('resize', schedule); window.removeEventListener(PAGE_LAYOUT_EVENT, render); sizes?.disconnect(); cancelAnimationFrame(frame) })
</script>

<template>
  <Teleport to="#public-reading-slot">
  <div ref="bar" class="project-reading-bar" :class="{ 'is-visible': visible }" :inert="!visible">
    <div class="container project-reading-bar__inner">
      <RouterLink :to="locale.publicPath('/projects')" :aria-label="locale.t('backProjects')"><ArrowLeft :size="17" /></RouterLink>
      <strong :title="title">{{ title }}</strong>
      <button class="reading-top" type="button" @click="backToTop" :aria-label="locale.isEnglish ? 'Back to project title' : '返回项目标题'"><span>{{ locale.isEnglish ? 'Top' : '顶部' }}</span><i><ArrowUp :size="15" /></i></button>
    </div>
    <div class="project-reading-bar__progress" role="progressbar" :aria-label="locale.isEnglish ? 'Reading progress' : '阅读进度'" :aria-valuenow="percentage" :aria-valuemin="0" :aria-valuemax="100"><span /></div>
  </div>
  </Teleport>
</template>
