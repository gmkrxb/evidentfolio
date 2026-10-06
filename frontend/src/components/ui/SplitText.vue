<script setup lang="ts">
import { computed } from 'vue'

/**
 * 将文字拆分为词 / 字，供入场与滚动“着墨”动画使用。
 * intro：加载后逐词浮现；fill：由祖先元素的 --fill 变量（0–1）驱动，从浅墨到浓墨。
 */
const props = withDefaults(defineProps<{ text: string; mode?: 'intro' | 'fill'; delay?: number; step?: number }>(), {
  mode: 'intro',
  delay: 0,
  step: 38,
})

function segment(text: string) {
  if (typeof Intl !== 'undefined' && typeof Intl.Segmenter === 'function') {
    return [...new Intl.Segmenter(undefined, { granularity: 'word' }).segment(text)].map((part) => part.segment)
  }
  return text.split(/(\s+)/)
}

const lines = computed(() => {
  let index = 0
  return props.text.split(/\n+/).filter((line) => line.trim()).map((line) => segment(line.trim()).map((word) => ({ word, index: /^\s+$/.test(word) ? index : index++ })))
})
const total = computed(() => Math.max(1, lines.value.reduce((sum, line) => sum + line.filter((item) => item.word.trim()).length, 0)))
</script>

<template>
  <span class="split-text" :class="`split-text--${mode}`" :style="{ '--count': total }" data-locale-text>
    <span class="sr-only">{{ text }}</span>
    <span v-for="(line, row) in lines" :key="row" class="split-text__line" aria-hidden="true">
      <template v-for="(item, column) in line" :key="column">
        <span v-if="!item.word.trim()" class="split-text__space">{{ item.word }}</span>
        <span v-else class="split-text__word" :style="{ '--i': item.index, '--delay': `${delay + item.index * step}ms` }">{{ item.word }}</span>
      </template>
    </span>
  </span>
</template>
