<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, ref, watch } from 'vue'
import { ChevronLeft, ChevronRight, Maximize2, X, ZoomIn, ZoomOut } from 'lucide-vue-next'
import type { ProjectAsset } from '@/types'

const props = defineProps<{ items: ProjectAsset[]; index: number | null }>()
const emit = defineEmits<{ close: []; change: [index: number] }>()
const zoom = ref(1)
const dialog = ref<HTMLElement | null>(null)
const current = computed(() => (props.index === null ? null : props.items[props.index]))

function previous() {
  if (props.index === null) return
  emit('change', (props.index - 1 + props.items.length) % props.items.length)
}
function next() {
  if (props.index === null) return
  emit('change', (props.index + 1) % props.items.length)
}
function keydown(event: KeyboardEvent) {
  if (props.index === null) return
  if (event.key === 'Escape') emit('close')
  if (event.key === 'ArrowLeft') previous()
  if (event.key === 'ArrowRight') next()
}
async function fullscreen() {
  await dialog.value?.requestFullscreen?.()
}
watch(
  () => props.index,
  async (value) => {
    zoom.value = 1
    document.body.classList.toggle('is-locked', value !== null)
    if (value !== null) await nextTick(() => dialog.value?.focus())
  },
  { immediate: true },
)
window.addEventListener('keydown', keydown)
onBeforeUnmount(() => {
  window.removeEventListener('keydown', keydown)
  document.body.classList.remove('is-locked')
})
</script>

<template>
  <Teleport to="body">
    <Transition name="lightbox">
      <div
        v-if="current"
        ref="dialog"
        class="lightbox"
        role="dialog"
        aria-modal="true"
        :aria-label="current.caption || current.asset.display_name"
        tabindex="-1"
        @click.self="$emit('close')"
      >
        <div class="lightbox__toolbar">
          <button class="icon-button icon-button--light" aria-label="缩小" @click="zoom = Math.max(0.5, zoom - 0.25)">
            <ZoomOut :size="20" />
          </button>
          <span>{{ Math.round(zoom * 100) }}%</span>
          <button class="icon-button icon-button--light" aria-label="放大" @click="zoom = Math.min(3, zoom + 0.25)">
            <ZoomIn :size="20" />
          </button>
          <button class="icon-button icon-button--light" aria-label="全屏" @click="fullscreen">
            <Maximize2 :size="20" />
          </button>
          <button class="icon-button icon-button--light" aria-label="关闭" @click="$emit('close')">
            <X :size="22" />
          </button>
        </div>
        <button v-if="items.length > 1" class="lightbox__nav lightbox__nav--prev" aria-label="上一张" @click="previous">
          <ChevronLeft :size="28" />
        </button>
        <figure>
          <img
            :src="current.asset.content_url"
            :alt="current.caption || current.asset.description || current.asset.display_name"
            :style="{ transform: `scale(${zoom})` }"
          />
          <figcaption>{{ current.caption || current.asset.display_name }}</figcaption>
        </figure>
        <button v-if="items.length > 1" class="lightbox__nav lightbox__nav--next" aria-label="下一张" @click="next">
          <ChevronRight :size="28" />
        </button>
      </div>
    </Transition>
  </Teleport>
</template>

