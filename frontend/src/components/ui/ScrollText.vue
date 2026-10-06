<script setup lang="ts">
import { computed } from 'vue'

const props = withDefaults(defineProps<{ text: string; as?: string }>(), { as: 'h2' })
const segments = computed(() => {
  if (typeof Intl.Segmenter === 'function') return [...new Intl.Segmenter(undefined, { granularity: 'word' }).segment(props.text)].map(part => part.segment)
  return Array.from(props.text)
})
</script>

<template>
  <component :is="as" v-scroll-progress="{ start: .98, end: .52 }" class="scroll-text" data-locale-text :aria-label="text" :style="{ '--word-count': segments.length }"><span v-for="(word, index) in segments" :key="index" aria-hidden="true" :style="{ '--word-index': index }">{{ word }}</span></component>
</template>
