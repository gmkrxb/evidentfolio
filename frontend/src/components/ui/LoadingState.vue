<script setup lang="ts">
import { computed } from 'vue'
import { useLocaleStore } from '@/stores/locale'
const props = withDefaults(defineProps<{ rows?: number; label?: string }>(), { rows: 3, label: '' })
const locale = useLocaleStore()
const labelText = computed(() => props.label || locale.t('loading'))
</script>

<template>
  <div class="loading-state" role="status" :aria-label="labelText">
    <span v-for="row in props.rows" :key="row" class="skeleton-line" :style="{ width: `${100 - (row - 1) * 13}%` }" />
  </div>
</template>
