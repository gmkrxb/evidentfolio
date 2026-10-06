<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue'

/** 词汇带：土木、信息、智能与诗的词语在两条方向相反的轨道上流动，速度随滚动加快。 */
const WORDS = [['结构', 'Structure'], ['信息', 'Information'], ['智能', 'Intelligence'], ['诗', 'Poetry'], ['理', 'Reason'], ['证据', 'Evidence']]
const TERMS = ['Load', 'Stress', 'Strain', 'Signal', 'Token', 'Attention', 'Gradient', 'Evidence', 'Span', 'Section', 'Order', 'Time', 'Silence', 'Meaning']
const root = ref<HTMLElement | null>(null)
const upper = ref<HTMLElement | null>(null)
const lower = ref<HTMLElement | null>(null)
let frame = 0
let last = 0
let offset = 0
let velocity = 0
let lastScroll = 0
let visible = false
let observer: IntersectionObserver | undefined
const reduced = typeof window !== 'undefined' && window.matchMedia('(prefers-reduced-motion: reduce)').matches

function loop(now: number) {
  frame = requestAnimationFrame(loop)
  const dt = Math.min(0.05, (now - (last || now)) / 1000)
  last = now
  const scroll = window.scrollY
  const delta = scroll - lastScroll
  lastScroll = scroll
  velocity += (delta - velocity) * 0.12
  const speed = 38 + Math.min(900, Math.abs(velocity) * 22)
  offset += speed * dt * (velocity < -0.5 ? -1 : 1)
  const skew = Math.max(-8, Math.min(8, velocity * 0.35))
  for (const [track, direction] of [[upper.value, 1], [lower.value, -1]] as const) {
    if (!track) continue
    const half = track.scrollWidth / 2 || 1
    const shift = ((offset * (direction === 1 ? 1 : 0.7)) % half + half) % half
    track.style.transform = `translate3d(${direction === 1 ? -shift : shift - half}px,0,0) skewX(${(-skew * direction).toFixed(2)}deg)`
  }
}
onMounted(() => {
  if (reduced || !root.value) return
  lastScroll = window.scrollY
  observer = new IntersectionObserver(([entry]) => {
    visible = Boolean(entry?.isIntersecting)
    if (visible && !frame) { last = 0; frame = requestAnimationFrame(loop) }
    if (!visible) { cancelAnimationFrame(frame); frame = 0 }
  }, { rootMargin: '10% 0px' })
  observer.observe(root.value)
})
onBeforeUnmount(() => { observer?.disconnect(); cancelAnimationFrame(frame) })
</script>

<template>
  <section ref="root" class="lexicon" aria-hidden="true">
    <div ref="upper" class="lexicon__track lexicon__track--words">
      <template v-for="copy in 2" :key="copy">
        <span v-for="([zh, en], index) in WORDS" :key="`${copy}-${index}`" class="lexicon__word"><b>{{ zh }}</b><em>{{ en }}</em><i>✦</i></span>
      </template>
    </div>
    <div ref="lower" class="lexicon__track lexicon__track--terms">
      <template v-for="copy in 2" :key="copy">
        <span v-for="(term, index) in TERMS" :key="`${copy}-${index}`">{{ term }}<i>/</i></span>
      </template>
    </div>
  </section>
</template>

<style scoped>
.lexicon { position: relative; z-index: 1; overflow: hidden; padding: clamp(36px, 7vh, 80px) 0; border-block: 1px solid var(--color-line); background: color-mix(in srgb, var(--color-bg) 55%, transparent); backdrop-filter: blur(4px); }
.lexicon__track { display: flex; width: max-content; will-change: transform; }
.lexicon__word { display: inline-flex; align-items: baseline; gap: .28em; padding-right: .5em; font-family: var(--font-display); font-size: clamp(64px, 10vw, 168px); line-height: 1.02; letter-spacing: -.04em; white-space: nowrap; }
.lexicon__word b { font-weight: 400; color: var(--color-ink); }
.lexicon__word em { font-style: italic; color: transparent; -webkit-text-stroke: 1px color-mix(in srgb, var(--color-ink) 55%, transparent); }
.lexicon__word:nth-child(3n + 2) em { -webkit-text-stroke-color: var(--color-accent); }
.lexicon__word i { font-style: normal; font-size: .3em; color: var(--color-accent); transform: translateY(-.9em); }
.lexicon__track--terms { margin-top: clamp(14px, 2.4vh, 28px); }
.lexicon__track--terms span { display: inline-flex; align-items: center; gap: 22px; padding-right: 22px; font-family: var(--font-mono); font-size: clamp(12px, 1.1vw, 15px); letter-spacing: .22em; text-transform: uppercase; color: var(--color-muted); white-space: nowrap; }
.lexicon__track--terms i { font-style: normal; color: var(--color-accent); }
</style>
