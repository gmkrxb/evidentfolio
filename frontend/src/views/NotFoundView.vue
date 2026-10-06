<script setup lang="ts">
import { ArrowLeft } from 'lucide-vue-next'
import { useLocaleStore } from '@/stores/locale'
import { useMeta } from '@/composables/useMeta'
import { computed } from 'vue'

const locale = useLocaleStore()
const text = (zh: string, en: string) => (locale.isEnglish ? en : zh)
useMeta({ title: computed(() => text('未找到页面', 'Page not found')), description: computed(() => '') })
</script>

<template>
  <section class="lost">
    <div class="container lost__inner">
      <span class="ah-mono ah-label">404 — {{ text('此跨未建', 'Span not built') }}</span>
      <svg class="lost__bridge" viewBox="0 0 640 200" aria-hidden="true">
        <path class="lost__line" pathLength="1" d="M10 120H250M390 120H630M10 126H250M390 126H630" />
        <path class="lost__line" pathLength="1" d="M150 120V20M490 120V20M150 30L60 120M150 30L240 120M150 50L90 120M150 50L210 120M490 30L400 120M490 30L580 120M490 50L430 120M490 50L550 120" />
        <path class="lost__line lost__line--thin" pathLength="1" d="M0 170H640M150 126V170M490 126V170M10 126V170M630 126V170" />
        <path class="lost__gap" d="M250 123H390" />
        <circle class="lost__dot" cx="250" cy="123" r="4" /><circle class="lost__dot" cx="390" cy="123" r="4" />
        <text x="320" y="108" text-anchor="middle" class="lost__note">Δ = ∞</text>
      </svg>
      <h1>{{ text('这一跨，尚未建成。', 'This span has not been built yet.') }}</h1>
      <p>{{ text('地址可能已经变化，或这一页还没有公开。', 'The address may have changed, or this page is not public yet.') }}</p>
      <RouterLink v-magnetic class="ah-button ah-button--solid" :to="locale.publicPath('/')"><ArrowLeft :size="17" />{{ text('回到首页', 'Back to home') }}</RouterLink>
    </div>
  </section>
</template>

<style scoped>
.lost { display: grid; min-height: calc(100vh - var(--header-h)); place-items: center; padding: 60px 0 100px; }
.lost__inner { display: flex; flex-direction: column; align-items: center; text-align: center; }
.lost__bridge { width: min(640px, 100%); margin: 40px 0 28px; overflow: visible; }
.lost__line { fill: none; stroke: var(--color-ink); stroke-width: 1.2; vector-effect: non-scaling-stroke; stroke-dasharray: 1; stroke-dashoffset: 1; animation: lost-draw 2.4s cubic-bezier(.16,1,.3,1) forwards; }
.lost__line--thin { stroke-opacity: .4; animation-delay: .4s; }
.lost__gap { fill: none; stroke: var(--color-accent); stroke-width: 1.2; stroke-dasharray: 3 6; vector-effect: non-scaling-stroke; animation: lost-march 1.2s linear infinite; }
.lost__dot { fill: var(--color-accent); }
.lost__note { fill: var(--color-accent-ink); font-family: var(--font-mono); font-size: 12px; }
.lost h1 { margin: 0; font-size: clamp(36px, 5.4vw, 76px); line-height: 1.08; letter-spacing: -.04em; text-wrap: balance; }
.lost p { margin: 20px 0 34px; color: var(--color-ink-soft); }
@keyframes lost-draw { to { stroke-dashoffset: 0; } }
@keyframes lost-march { to { stroke-dashoffset: -9; } }
@media (prefers-reduced-motion: reduce) { .lost__line { animation: none; stroke-dashoffset: 0; } .lost__gap { animation: none; } }
</style>
