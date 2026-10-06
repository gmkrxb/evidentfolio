<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { FieldRenderer } from '@/utils/fieldRenderer'
import { withoutLocale } from '@/utils/pageNavigation'

const route = useRoute()
const field = ref<HTMLCanvasElement | null>(null)
const network = ref<HTMLCanvasElement | null>(null)
const scene = ref<HTMLCanvasElement | null>(null)
const SECTIONS = [['intro', 'introduction'], ['manifesto', 'manifesto'], ['capabilities', 'capabilities'], ['agents', 'agents'], ['overview', 'overview'], ['featured', 'featured'], ['directions', 'directions'], ['connect', 'connect']] as const

// 每个章节在视口中所占比例，决定三维场景里对应元素的出现程度。
function sectionWeights(viewport: number) {
  const weights = { intro: 0, manifesto: 0, capabilities: 0, agents: 0, overview: 0, featured: 0, directions: 0, connect: 0 }
  for (const [key, id] of SECTIONS) {
    const rect = document.getElementById(id)?.getBoundingClientRect()
    if (!rect) continue
    const overlap = (Math.min(rect.bottom, viewport) - Math.max(rect.top, 0)) / viewport
    weights[key] = Math.min(1, Math.max(0, overlap * 1.6 - 0.12))
  }
  return weights
}
const ready = ref(false)
let renderer: FieldRenderer | null = null
let frame = 0

const isHome = () => withoutLocale(route.path) === '/'

let currentSection = ''
function announce(section: string) {
  if (section === currentSection) return
  currentSection = section
  document.documentElement.dataset.section = section
  window.dispatchEvent(new CustomEvent('portfolio:section', { detail: section }))
}
function pageSection() {
  const path = withoutLocale(route.path)
  if (path.startsWith('/projects/')) return 'detail'
  return path.split('/')[1] || 'intro'
}
function sync() {
  frame = 0
  if (!renderer) return
  const viewport = window.innerHeight || 1
  const y = window.scrollY
  if (isHome()) {
    renderer.options.intensity = Math.max(0.3, 0.72 - Math.max(0, y - viewport * 0.35) / (viewport * 1.1) * 0.42)
    renderer.options.crosshair = y < viewport * 0.75
    renderer.options.order = Math.min(1, y / (viewport * 2.6))
    const weights = sectionWeights(viewport)
    renderer.options.scene = weights
    const dominant = (Object.entries(weights) as Array<[string, number]>).sort((a, b) => b[1] - a[1])[0]
    if (dominant && dominant[1] > 0.3) announce(dominant[0])
    renderer.options.network = 0.45
  } else {
    renderer.options.scene = null
    renderer.options.network = 1
    announce(pageSection())
    renderer.options.intensity = 0.4
    renderer.options.crosshair = false
    renderer.options.order = 0.55
  }
  renderer.touch()
}
function schedule() { if (!frame) frame = requestAnimationFrame(sync) }
function move(event: PointerEvent) { renderer?.pointer(event.clientX, event.clientY) }
function up(event: PointerEvent) { if (event.pointerType !== 'mouse') renderer?.leave() }
function down(event: PointerEvent) { renderer?.ripple(event.clientX, event.clientY) }
function out(event: PointerEvent) { if (!event.relatedTarget) renderer?.leave() }
function resize() { renderer?.resize(); schedule() }
function theme() { requestAnimationFrame(() => renderer?.readTheme()) }
function visibility() { if (document.hidden) renderer?.stopLoop(); else renderer?.startLoop() }

onMounted(() => {
  if (!field.value || !network.value) return
  renderer = new FieldRenderer(field.value, network.value)
  renderer.attachScene(scene.value)
  sync()
  window.setTimeout(schedule, 300)
  window.setTimeout(schedule, 1200)
  renderer.startLoop()
  ready.value = true
  window.addEventListener('pointermove', move, { passive: true })
  window.addEventListener('pointerup', up, { passive: true })
  window.addEventListener('pointerdown', down, { passive: true })
  document.addEventListener('pointerout', out, { passive: true })
  window.addEventListener('scroll', schedule, { passive: true })
  window.addEventListener('resize', resize, { passive: true })
  window.addEventListener('portfolio:theme-change', theme)
  document.addEventListener('visibilitychange', visibility)
})
watch(() => route.path, () => { schedule(); window.setTimeout(schedule, 400); window.setTimeout(schedule, 1200) })
onBeforeUnmount(() => {
  window.removeEventListener('pointermove', move)
  window.removeEventListener('pointerup', up)
  window.removeEventListener('pointerdown', down)
  document.removeEventListener('pointerout', out)
  window.removeEventListener('scroll', schedule)
  window.removeEventListener('resize', resize)
  window.removeEventListener('portfolio:theme-change', theme)
  document.removeEventListener('visibilitychange', visibility)
  cancelAnimationFrame(frame)
  renderer?.destroy()
  renderer = null
})
</script>

<template>
  <div class="field-backdrop" :class="{ 'is-ready': ready }" aria-hidden="true">
    <canvas ref="field" class="field-backdrop__field" />
    <canvas ref="scene" class="field-backdrop__scene" />
    <canvas ref="network" class="field-backdrop__network" />
    <div class="field-backdrop__grain" />
  </div>
</template>

<style scoped>
.field-backdrop { position: fixed; inset: 0; z-index: 0; pointer-events: none; opacity: 0; transition: opacity 1.6s cubic-bezier(.16,1,.3,1); }
.field-backdrop.is-ready { opacity: 1; }
.field-backdrop canvas { position: absolute; inset: 0; width: 100%; height: 100%; display: block; }
.field-backdrop__grain { position: absolute; inset: -50%; opacity: var(--grain-opacity, .05); background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='160' height='160'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='.9' numOctaves='2' stitchTiles='stitch'/%3E%3CfeColorMatrix values='0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 .55 0'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E"); }
</style>
