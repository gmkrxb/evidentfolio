<script setup lang="ts">
import { storeToRefs } from 'pinia'
import { useToastStore } from '@/stores/toast'

const toast = useToastStore()
const { message, tone } = storeToRefs(toast)
</script>

<template>
  <RouterView v-slot="{ Component, route }">
    <Transition name="page" mode="out-in">
      <component :is="Component" :key="route.meta.layoutKey || route.fullPath" />
    </Transition>
  </RouterView>
  <Transition name="toast">
    <div v-if="message" class="toast" :class="`toast--${tone}`" role="status" aria-live="polite">
      {{ message }}
    </div>
  </Transition>
</template>

