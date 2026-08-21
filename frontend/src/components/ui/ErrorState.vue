<script setup lang="ts">
import { CircleAlert, RefreshCw } from 'lucide-vue-next'
import { useLocaleStore } from '@/stores/locale'
defineProps<{ message: string }>()
defineEmits<{ retry: [] }>()
const locale = useLocaleStore()
</script>

<template>
  <div class="error-state" role="alert">
    <CircleAlert :size="28" aria-hidden="true" />
    <h3>{{ locale.t('loadFailed') }}</h3>
    <p>{{ message }}</p>
    <button class="button button--outline button--small" type="button" @click="$emit('retry')">
      <RefreshCw :size="16" />{{ locale.t('retry') }}
    </button>
  </div>
</template>
