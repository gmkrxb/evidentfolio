<script setup lang="ts">
import { onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import PublicHeader from '@/components/public/PublicHeader.vue'
import PublicFooter from '@/components/public/PublicFooter.vue'
import { useSiteStore } from '@/stores/site'
import InteractiveBackdrop from '@/components/public/InteractiveBackdrop.vue'

const site = useSiteStore()
const route = useRoute()
onMounted(() => site.load().catch(() => undefined))
watch(() => route.path.startsWith('/en'), () => site.load(true).catch(() => undefined))
</script>

<template>
  <div class="site-shell">
    <InteractiveBackdrop />
    <PublicHeader />
    <main id="main-content">
      <RouterView />
    </main>
    <PublicFooter />
  </div>
</template>
