<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import type { Asset } from '@/types'
import { coverImageUrl, coverLayout } from '@/utils/projectCover'

const props = defineProps<{ assets: Asset[]; eager?: boolean }>()
const root = ref<HTMLElement>()
const aspect = ref(1.6)
const measured = ref<Record<string, { width: number; height: number }>>({})
let observer: ResizeObserver | undefined
const layout = computed(() => coverLayout(props.assets.map(asset => measured.value[asset.uuid] || asset), aspect.value))
function measureImage(asset: Asset, event: Event) {
  if (asset.width && asset.height) return
  const image = event.target as HTMLImageElement
  if (image.naturalWidth && image.naturalHeight) measured.value[asset.uuid] = { width: image.naturalWidth, height: image.naturalHeight }
}
onMounted(() => {
  observer = new ResizeObserver(([entry]) => {
    if (entry && entry.contentRect.width && entry.contentRect.height) aspect.value = Math.round(entry.contentRect.width / entry.contentRect.height * 100) / 100
  })
  if (root.value) observer.observe(root.value)
})
onBeforeUnmount(() => observer?.disconnect())
</script>

<template>
  <div ref="root" class="project-cover" :data-image-count="assets.length">
    <div v-for="tile in layout" :key="assets[tile.index]!.uuid" class="project-cover__tile" :style="{ left: `calc(${tile.x * 100}% + ${tile.x ? 1 : 0}px)`, top: `calc(${tile.y * 100}% + ${tile.y ? 1 : 0}px)`, width: `calc(${tile.width * 100}% - ${tile.x ? 1 : 0}px)`, height: `calc(${tile.height * 100}% - ${tile.y ? 1 : 0}px)` }">
      <img :src="coverImageUrl(assets[tile.index]!)" alt="" :loading="eager ? 'eager' : 'lazy'" :fetchpriority="eager && tile.index === 0 ? 'high' : 'auto'" decoding="async" @load="measureImage(assets[tile.index]!, $event)" />
    </div>
  </div>
</template>

<style scoped>
.project-cover { position: absolute; inset: 0; overflow: hidden; }
.project-cover__tile { position: absolute; overflow: hidden; }
.project-cover .project-cover__tile>img { display: block; width: 100%; height: 100%; padding: 0; object-fit: cover; object-position: center; animation: none; translate: none; scale: none; transform: none; transition: transform .7s cubic-bezier(.2,.65,.25,1); }
@media(hover:hover) and (prefers-reduced-motion:no-preference) {
  :global(.project-card__visual:hover .project-cover .project-cover__tile>img), :global(.showcase-project:hover .project-cover .project-cover__tile>img) { transform: scale(1.055); }
}
:global(.project-card__visual:focus-visible .project-cover), :global(.showcase-project:focus-visible .project-cover) { outline: 2px solid var(--color-accent-ink); outline-offset: -3px; }
@media(prefers-reduced-motion:reduce) { .project-cover__tile>img { transition: none; } }
</style>
