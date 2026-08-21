<script setup lang="ts">
import { Inbox } from 'lucide-vue-next'
import { computed } from 'vue'
import { useLocaleStore } from '@/stores/locale'
const props = withDefaults(defineProps<{ title?: string; description?: string }>(), { title: '', description: '' })
const locale = useLocaleStore()
const titleText = computed(() => props.title || locale.t('emptyTitle'))
const descriptionText = computed(() => props.description || locale.t('emptyDescription'))
</script>

<template>
  <div class="empty-state">
    <Inbox :size="28" aria-hidden="true" />
    <h3>{{ titleText }}</h3>
    <p>{{ descriptionText }}</p>
    <slot />
  </div>
</template>
