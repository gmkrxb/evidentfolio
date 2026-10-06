<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
const props = defineProps<{ points: Array<{ date: string; views: number }> }>()
const days = ref(30)
const selected = ref(-1)
const canvas = ref<HTMLCanvasElement>()
const container = ref<HTMLElement>()
const data = computed(() => props.points.slice(-days.value))
const total = computed(() => data.value.reduce((sum, item) => sum + item.views, 0))
const active = computed(() => data.value[selected.value])
let observer: ResizeObserver | undefined
let width = 600
const height = 230
const left = 42, right = 18, top = 20, bottom = 32
function draw() {
  const el = canvas.value
  if (!el) return
  width = container.value?.clientWidth || 600
  const dpr = Math.min(window.devicePixelRatio || 1, 3)
  el.width = width * dpr; el.height = height * dpr
  const ctx = el.getContext('2d')
  if (!ctx) return
  ctx.scale(dpr, dpr)
  const palette = getComputedStyle(el)
  const brand = palette.getPropertyValue('--color-accent-ink').trim() || palette.getPropertyValue('--color-brand').trim()
  const line = palette.getPropertyValue('--color-line').trim()
  const muted = palette.getPropertyValue('--color-muted').trim()
  const maximum = Math.max(4, Math.ceil(Math.max(...data.value.map((point) => point.views), 0) / 4) * 4)
  const plotHeight = height - top - bottom
  const x = (index: number) => left + index / Math.max(1, data.value.length - 1) * (width - left - right)
  const y = (views: number) => top + plotHeight * (1 - views / maximum)
  ctx.font = '11px system-ui'; ctx.lineWidth = 1
  for (let i = 0; i <= 4; i++) {
    const ordinate = top + i / 4 * plotHeight
    ctx.strokeStyle = line; ctx.beginPath(); ctx.moveTo(left, ordinate); ctx.lineTo(width - right, ordinate); ctx.stroke()
    ctx.fillStyle = muted; ctx.textAlign = 'right'; ctx.fillText(String(maximum * (1 - i / 4)), left - 10, ordinate + 4)
  }
  if (data.value.length) {
    ctx.beginPath(); ctx.moveTo(x(0), y(0))
    data.value.forEach((point, index) => ctx.lineTo(x(index), y(point.views)))
    ctx.lineTo(x(data.value.length - 1), y(0)); ctx.closePath()
    const gradient = ctx.createLinearGradient(0, top, 0, height - bottom)
    gradient.addColorStop(0, brand); gradient.addColorStop(1, 'transparent'); ctx.fillStyle = gradient; ctx.globalAlpha = .18; ctx.fill(); ctx.globalAlpha = 1
    ctx.beginPath(); data.value.forEach((point, index) => index ? ctx.lineTo(x(index), y(point.views)) : ctx.moveTo(x(index), y(point.views)))
    ctx.strokeStyle = brand; ctx.lineWidth = 2.5; ctx.lineJoin = 'round'; ctx.stroke()
    const labels = [...new Set([0, Math.floor((data.value.length - 1) / 2), data.value.length - 1])]
    ctx.fillStyle = muted
    labels.forEach((index) => { ctx.textAlign = index === 0 ? 'left' : index === data.value.length - 1 ? 'right' : 'center'; ctx.fillText(data.value[index].date.slice(5), x(index), height - 8) })
    if (active.value) {
      const cx = x(selected.value), cy = y(active.value.views)
      ctx.beginPath(); ctx.moveTo(cx, top); ctx.lineTo(cx, height - bottom); ctx.setLineDash([4, 4]); ctx.strokeStyle = muted; ctx.lineWidth = 1; ctx.stroke(); ctx.setLineDash([])
      ctx.beginPath(); ctx.arc(cx, cy, 5, 0, Math.PI * 2); ctx.fillStyle = brand; ctx.fill(); ctx.strokeStyle = '#fff'; ctx.lineWidth = 2; ctx.stroke()
    }
  }
}
function move(event: PointerEvent) {
  const rect = canvas.value!.getBoundingClientRect()
  selected.value = Math.max(0, Math.min(data.value.length - 1, Math.round((event.clientX - rect.left - left) / (width - left - right) * (data.value.length - 1))))
}
function keyboard(event: KeyboardEvent) {
  if (!['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) return
  event.preventDefault()
  selected.value = event.key === 'Home' ? 0 : event.key === 'End' ? data.value.length - 1 : Math.max(0, Math.min(data.value.length - 1, selected.value + (event.key === 'ArrowRight' ? 1 : -1)))
}
watch([data, selected], draw, { flush: 'post' })
watch(days, () => { selected.value = -1 })
onMounted(() => { observer = new ResizeObserver(draw); if (container.value) observer.observe(container.value); window.addEventListener('portfolio:theme-change', draw); draw() })
onBeforeUnmount(() => { observer?.disconnect(); window.removeEventListener('portfolio:theme-change', draw) })
</script>
<template>
  <div class="visit-chart">
    <div class="visit-chart__toolbar"><span><strong>{{ total.toLocaleString() }}</strong> 次页面访问 <small>UTC</small></span><div class="language-tabs"><button v-for="count in [7,30]" :key="count" :class="{ active: days === count }" :aria-pressed="days === count" @click="days = count">{{ count }} 天</button></div></div>
    <div ref="container" class="visit-chart__canvas"><canvas ref="canvas" tabindex="0" role="img" aria-label="页面访问趋势，左右方向键查看每日数据，下方可展开数据表" @pointermove="move" @pointerleave="selected = -1" @keydown="keyboard" @focus="selected = data.length - 1" @blur="selected = -1" /></div>
    <div class="visit-chart__caption" aria-live="polite">{{ active ? `${active.date} · ${active.views} 次页面访问` : total ? '移动指针或使用方向键查看每日访问' : '本时段暂无已获同意的访问记录' }}</div>
    <details><summary>查看每日数据</summary><div class="visit-chart__table"><table><thead><tr><th>日期（UTC）</th><th>页面访问</th></tr></thead><tbody><tr v-for="point in data" :key="point.date"><td>{{ point.date }}</td><td>{{ point.views }}</td></tr></tbody></table></div></details>
  </div>
</template>
<style scoped>
.visit-chart__toolbar{display:flex;align-items:center;justify-content:space-between;gap:16px;margin-bottom:14px;font-size:12px;color:var(--color-ink-soft)}.visit-chart__toolbar strong{font-size:30px;color:var(--color-ink);letter-spacing:-.04em;margin-right:6px}.visit-chart__canvas{width:100%;min-width:0}.visit-chart canvas{width:100%;height:230px;display:block;touch-action:pan-y;border-radius:10px}.visit-chart__caption{min-height:28px;text-align:center;font-size:12px;color:var(--color-muted)}.visit-chart details{font-size:12px;color:var(--color-muted)}.visit-chart summary{cursor:pointer}.visit-chart__table{max-height:210px;overflow:auto;margin-top:12px}.visit-chart table{width:100%}.visit-chart td,.visit-chart th{padding:7px;text-align:left;border-bottom:1px solid var(--color-line)}
</style>
