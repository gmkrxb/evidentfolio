<script setup lang="ts">
import { ArrowLeft } from 'lucide-vue-next'
</script>

<template>
  <main class="not-found">
    <span>404</span>
    <h1>这一页不在作品集中。</h1>
    <p>地址可能已经变化，或内容尚未公开。</p>
    <RouterLink class="button button--dark" to="/"><ArrowLeft :size="17" /> 返回首页</RouterLink>
  </main>
</template>

