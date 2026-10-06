<script setup lang="ts">
import { computed } from 'vue'
import { useLocaleStore } from '@/stores/locale'
const props = withDefaults(defineProps<{ rows?: number; label?: string; variant?: 'lines' | 'card' }>(), { rows: 3, label: '', variant: 'lines' })
const locale = useLocaleStore()
const labelText = computed(() => props.label || locale.t('loading'))
</script>

<template>
  <div class="loading-state" :class="{ 'loading-state--card': variant === 'card' }" role="status" :aria-label="labelText">
    <div v-if="variant === 'card'" class="skeleton-media" />
    <span v-for="row in props.rows" :key="row" class="skeleton-line" :style="{ width: `${Math.max(35, 100 - (row - 1) * 13)}%` }" />
  </div>
</template>
