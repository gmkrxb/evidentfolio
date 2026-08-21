<script setup lang="ts">
import { computed } from 'vue'
import DOMPurify from 'dompurify'
import MarkdownIt from 'markdown-it'

const props = defineProps<{ source: string }>()
const markdown = new MarkdownIt({ html: false, linkify: true, typographer: true })
const rendered = computed(() =>
  DOMPurify.sanitize(markdown.render(props.source || ''), {
    USE_PROFILES: { html: true },
    FORBID_TAGS: ['style', 'iframe', 'object', 'embed', 'script'],
  }),
)
</script>

<template>
  <div class="rich-content" v-html="rendered" />
</template>

