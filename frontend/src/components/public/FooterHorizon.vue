<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue'

/** 页脚地平线：远山、长桥、水面与一盏缓缓过桥的灯。进入视口时逐笔描出。 */
const root = ref<HTMLElement | null>(null)
const drawn = ref(false)
let observer: IntersectionObserver | undefined

const ridge = (seed: number, base: number, amp: number) => {
  let d = ''
  for (let x = 0; x <= 1440; x += 24) {
    const y = base - Math.sin(x * 0.004 + seed) * amp - Math.sin(x * 0.011 + seed * 2) * amp * 0.45 - Math.max(0, Math.sin(x * 0.0019 + seed)) * amp * 0.8
    d += `${x ? 'L' : 'M'}${x} ${y.toFixed(1)}`
  }
  return d
}
const far = ridge(1.3, 118, 26)
const near = ridge(4.1, 140, 16)
const TOWERS = [540, 900]
const cables = TOWERS.flatMap((x) => Array.from({ length: 14 }, (_, k) => {
  const ty = 32 + k * 4
  return [`M${x} ${ty}L${x - 30 - k * 12.5} 150`, `M${x} ${ty}L${x + 30 + k * 12.5} 150`]
}).flat()).join('')
const piers = [120, 200, 280, 360, 440, 1000, 1080, 1160, 1240, 1320].map((x) => `M${x} 154V186`).join('')
const ripples = Array.from({ length: 5 }, (_, row) => {
  let d = ''
  for (let x = 40 + row * 17; x < 1420; x += 46 + row * 6) d += `M${x} ${194 + row * 6}h${18 - row * 2}`
  return d
}).join('')

onMounted(() => {
  if (typeof IntersectionObserver === 'undefined' || window.matchMedia('(prefers-reduced-motion: reduce)').matches) { drawn.value = true; return }
  observer = new IntersectionObserver(([entry]) => { if (entry?.isIntersecting) { drawn.value = true; observer?.disconnect() } }, { threshold: 0.25 })
  if (root.value) observer.observe(root.value)
})
onBeforeUnmount(() => observer?.disconnect())
</script>

<template>
  <div ref="root" class="horizon" :class="{ 'is-drawn': drawn }" aria-hidden="true">
    <svg viewBox="0 0 1440 230" preserveAspectRatio="xMidYMax meet">
      <circle class="horizon__sun" cx="1180" cy="58" r="16" pathLength="1" />
      <path class="horizon__line horizon__line--far" :d="far" pathLength="1" style="--k: 0" />
      <path class="horizon__line horizon__line--near" :d="near" pathLength="1" style="--k: 1" />
      <path class="horizon__line" d="M60 150H1380M60 155H1380" pathLength="1" style="--k: 2" />
      <path v-for="(x, i) in TOWERS" :key="x" class="horizon__line horizon__line--tower" :d="`M${x - 9} 188L${x} 22L${x + 9} 188M${x - 5} 120H${x + 5}`" pathLength="1" :style="{ '--k': 3 + i }" />
      <path class="horizon__line horizon__line--cable" :d="cables" pathLength="1" style="--k: 5" />
      <path class="horizon__line horizon__line--thin" :d="piers" pathLength="1" style="--k: 6" />
      <path class="horizon__line horizon__line--thin" d="M0 188H1440" pathLength="1" style="--k: 6" />
      <path class="horizon__ripple" :d="ripples" />
      <g class="horizon__lamp"><circle r="3" /><circle class="horizon__lamp-glow" r="10" /></g>
      <g class="horizon__lamp horizon__lamp--reflection"><circle r="2" /></g>
    </svg>
  </div>
</template>

<style scoped>
.horizon { position: relative; width: 100%; color: var(--color-ink); }
.horizon svg { display: block; width: 100%; height: auto; overflow: visible; }
.horizon__line { fill: none; stroke: currentColor; stroke-width: 1; stroke-opacity: .55; stroke-linecap: round; vector-effect: non-scaling-stroke; stroke-dasharray: 1; stroke-dashoffset: 1; transition: stroke-dashoffset 2.6s cubic-bezier(.16,1,.3,1) calc(var(--k) * .18s); }
.horizon__line--far { stroke-opacity: .18; }
.horizon__line--near { stroke-opacity: .3; }
.horizon__line--tower { stroke-opacity: .75; stroke-width: 1.2; }
.horizon__line--cable { stroke-opacity: .28; stroke-width: .7; }
.horizon__line--thin { stroke-opacity: .25; }
.is-drawn .horizon__line { stroke-dashoffset: 0; }
.horizon__sun { fill: none; stroke: var(--color-accent); stroke-width: 1; vector-effect: non-scaling-stroke; stroke-dasharray: 1; stroke-dashoffset: 1; transition: stroke-dashoffset 3s cubic-bezier(.16,1,.3,1) 1s; }
.is-drawn .horizon__sun { stroke-dashoffset: 0; }
.horizon__ripple { fill: none; stroke: currentColor; stroke-opacity: .16; stroke-width: 1; vector-effect: non-scaling-stroke; opacity: 0; transition: opacity 2s 1.4s; animation: horizon-drift 9s linear infinite; }
.is-drawn .horizon__ripple { opacity: 1; }
.horizon__lamp { fill: var(--color-accent); offset-path: path('M60 147H1380'); offset-rotate: 0deg; opacity: 0; animation: horizon-cross 26s linear infinite; transition: opacity 1s 2s; }
.horizon__lamp--reflection { offset-path: path('M60 200H1380'); fill-opacity: .35; }
.horizon__lamp-glow { fill-opacity: .14; }
.is-drawn .horizon__lamp { opacity: 1; }
@keyframes horizon-cross { from { offset-distance: 0%; } to { offset-distance: 100%; } }
@keyframes horizon-drift { to { transform: translateX(-46px); } }
@media (prefers-reduced-motion: reduce) { .horizon__lamp, .horizon__ripple { animation: none; } }
</style>
