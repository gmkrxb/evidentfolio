<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'

/**
 * 工程线描：桁架受荷（结构）、注意力网络（智能）、监测信号（信息）、剖面与日照（建筑）。
 * 静态线条由 --draw 控制描线进度；live 时以 rAF 驱动荷载移动、信号流动与波形扫描。
 */
const props = withDefaults(defineProps<{ variant: number; live?: boolean }>(), { live: false })

type Mark = { d: string; accent?: boolean; thin?: boolean }
type Dot = { x: number; y: number; r: number; accent?: boolean }
type Label = { x: number; y: number; text: string; anchor?: 'start' | 'middle' | 'end' }

const kind = computed(() => Math.abs(props.variant) % 4)
const root = ref<SVGSVGElement | null>(null)
const time = ref(1.2)
let frame = 0
let start = 0
let observer: IntersectionObserver | undefined

// —— 静态构件 ——
// —— 斜拉桥立面 ——
const DECK = 148
const TOWERS = [118, 282]
const TOWER_TOP = 34
const WATER = 204
const CABLES = TOWERS.flatMap((tower, t) => Array.from({ length: 12 }, (_, k) => {
  const side = k < 6 ? -1 : 1
  const order = k % 6
  return { id: t * 12 + k, tx: tower + side * 2.5, ty: TOWER_TOP + 10 + order * 6, dx: tower + side * (22 + order * 14.5) }
}))
const SENSORS = [52, 150, 200, 250, 348]

function bridge() {
  const marks: Mark[] = [], dots: Dot[] = [], labels: Label[] = []
  marks.push({ d: `M6 ${DECK}H394M6 ${DECK + 6}H394` })
  let segments = ''
  for (let x = 14; x < 394; x += 16) segments += `M${x} ${DECK}v6`
  marks.push({ d: segments, thin: true })
  for (const x of TOWERS) {
    marks.push({ d: `M${x - 5} 226L${x - 3} ${TOWER_TOP}H${x + 3}L${x + 5} 226M${x - 4} ${DECK + 10}H${x + 4}M${x - 3.6} 70H${x + 3.6}` })
    marks.push({ d: `M${x - 14} 226H${x + 14}V238H${x - 14}Z`, thin: true })
  }
  marks.push({ d: CABLES.map((cable) => `M${cable.tx} ${cable.ty}L${cable.dx} ${DECK}`).join(''), thin: true })
  marks.push({ d: `M0 ${DECK + 6}L6 ${DECK + 6}L6 226M394 ${DECK + 6}V226`, thin: true })
  marks.push({ d: `M0 ${WATER}H400`, thin: true })
  SENSORS.forEach((x, index) => { dots.push({ x, y: DECK + 3, r: 2.4 }); labels.push({ x, y: DECK + 22, text: `A${index + 1}`, anchor: 'middle' }) })
  labels.push({ x: 200, y: 252, text: '164 m + 164 m', anchor: 'middle' })
  return { marks, dots, labels }
}

// —— Transformer：补丁 token、三层注意力 / 前馈、类别分布 ——
const TOKENS = ['P₁', 'P₂', 'P₃', 'P₄', 'P₅', '[Q]']
const TOKEN_X = TOKENS.map((_, index) => 52 + index * 59.2)
const LAYER_Y = [174, 138, 102]
const CLASSES = ['normal', 'outlier', 'drift', 'missing']

function transformer() {
  const marks: Mark[] = [], dots: Dot[] = [], labels: Label[] = []
  marks.push({ d: TOKEN_X.map((x) => `M${x - 20} 206H${x + 20}V226H${x - 20}Z`).join('') })
  marks.push({ d: TOKEN_X.map((x) => `M${x} 206V84`).join(''), thin: true })
  LAYER_Y.forEach((y, index) => {
    marks.push({ d: `M20 ${y - 13}H380V${y + 13}H20Z`, thin: true })
    labels.push({ x: 384, y: y + 4, text: `L${index + 1}`, anchor: 'start' })
  })
  marks.push({ d: CLASSES.map((_, index) => `M${70 + index * 82} 58H${130 + index * 82}`).join(''), thin: true })
  TOKENS.forEach((token, index) => labels.push({ x: TOKEN_X[index]!, y: 220, text: token, anchor: 'middle' }))
  CLASSES.forEach((name, index) => labels.push({ x: 100 + index * 82, y: 74, text: name, anchor: 'middle' }))
  labels.push({ x: 20, y: 248, text: '72,000 pts → 6 tokens', anchor: 'start' }, { x: 20, y: 22, text: 'p(y | x)', anchor: 'start' })
  return { marks, dots, labels }
}

function signal() {
  const marks: Mark[] = [], dots: Dot[] = [], labels: Label[] = []
  marks.push({ d: 'M20 130H380M20 36V222', thin: true })
  marks.push({ d: 'M20 82H380M20 178H380', thin: true })
  let ticks = ''
  for (let x = 20; x <= 380; x += 36) ticks += `M${x} 222v5`
  marks.push({ d: ticks, thin: true })
  labels.push({ x: 26, y: 76, text: '+3σ', anchor: 'start' }, { x: 26, y: 192, text: '−3σ', anchor: 'start' }, { x: 380, y: 246, text: 't / s', anchor: 'end' })
  return { marks, dots, labels }
}

function section() {
  const marks: Mark[] = [], dots: Dot[] = [], labels: Label[] = []
  marks.push({ d: 'M20 220H380', thin: true })
  marks.push({ d: 'M90 220V60H250V220M250 110H330V220' })
  let floors = ''
  for (let y = 92; y < 220; y += 32) floors += `M90 ${y}H250`
  for (let y = 142; y < 220; y += 26) floors += `M250 ${y}H330`
  marks.push({ d: floors, thin: true })
  marks.push({ d: 'M90 60A160 160 0 0 1 250 220', accent: true })
  marks.push({ d: 'M60 60V220M54 60H66M54 220H66', thin: true })
  for (const x of [90, 170, 250, 330]) dots.push({ x, y: 220, r: 2.4 })
  labels.push({ x: 48, y: 144, text: 'H', anchor: 'end' }, { x: 170, y: 246, text: 'φ = 1.618', anchor: 'middle' })
  return { marks, dots, labels }
}

const drawing = computed(() => [bridge, transformer, signal, section][kind.value]!())

// —— 动态部分 ——
// —— 监测信号：在“信号坐标”里生成，保证同一段数据形状始终不变 ——
const EVENT_PERIOD = 360
const EVENT_OFFSET = 300
const ANOMALIES = [
  { type: 'outlier', width: 26 },
  { type: 'square', width: 44 },
  { type: 'missing', width: 46 },
  { type: 'minor', width: 58 },
  { type: 'drift', width: 76 },
] as const
function noise(k: number) {
  const value = Math.sin(k * 127.1 + 311.7) * 43758.5453
  return value - Math.floor(value) - 0.5
}
function anomalyEvent(n: number) {
  const kind = ANOMALIES[n % ANOMALIES.length]!
  return { ...kind, center: EVENT_OFFSET + n * EVENT_PERIOD, confidence: 0.86 + ((n * 37) % 12) / 100 }
}
function signalAt(u: number, k: number) {
  const base = Math.sin(u * 0.105) * 15 + Math.sin(u * 0.24 + 1) * 5 + Math.sin(u * 0.031) * 9 + noise(k) * 4
  const n = Math.round((u - EVENT_OFFSET) / EVENT_PERIOD)
  if (n >= 0) {
    const event = anomalyEvent(n)
    const d = u - event.center
    const inside = Math.abs(d) <= event.width / 2
    if (event.type === 'outlier') return { y: 130 + base - 86 * Math.exp(-((d / 2.6) ** 2)), missing: false }
    if (inside && event.type === 'square') return { y: 74 + noise(k) * 2, missing: false }
    if (inside && event.type === 'missing') return { y: 130, missing: true }
    if (inside && event.type === 'minor') return { y: 130 + base * 0.12, missing: false }
    if (event.type === 'drift' && d > -event.width / 2) return { y: 130 + base - Math.min(1, (d + event.width / 2) / event.width) * 52 * Math.max(0, 1 - Math.max(0, d - event.width / 2) / 60), missing: false }
  }
  return { y: 130 + base, missing: false }
}

const live = computed(() => {
  const t = time.value
  if (kind.value === 0) {
    // 两辆车相向而行；桥面挠度、受力最大的斜拉索与经过的传感器随之响应。
    const cars = [{ x: 6 + ((t * 38) % 420) - 14, dir: 1 }, { x: 394 - ((t * 27 + 170) % 420) + 14, dir: -1 }]
    const deflect = (x: number) => cars.reduce((sum, car) => {
      const towerRelief = TOWERS.reduce((r, tower) => r * (1 - Math.exp(-(((x - tower) / 18) ** 2))), 1)
      return sum + 9 * Math.exp(-(((x - car.x) / 46) ** 2)) * towerRelief
    }, 0)
    let deck = ''
    for (let x = 6; x <= 394; x += 6) deck += `${x === 6 ? 'M' : 'L'}${x} ${(DECK + 3 + deflect(x) * 1.6).toFixed(1)}`
    const paths: Array<{ d: string; accent?: boolean; thin?: boolean }> = [{ d: deck, accent: true }]
    let loaded = ''
    let maxTension = 0
    for (const cable of CABLES) {
      const load = cars.reduce((sum, car) => sum + Math.exp(-(((cable.dx - car.x) / 26) ** 2)), 0)
      maxTension = Math.max(maxTension, load)
      if (load > 0.35) loaded += `M${cable.tx} ${cable.ty}L${cable.dx} ${DECK}`
    }
    if (loaded) paths.push({ d: loaded, accent: true })
    for (const car of cars) {
      if (car.x < 0 || car.x > 400) continue
      paths.push({ d: `M${(car.x - 8).toFixed(1)} ${DECK - 1}v-6h${car.dir > 0 ? 11 : 16}v-3h5v9Z` })
    }
    const dots: Dot[] = []
    SENSORS.forEach((x) => {
      const near = cars.reduce((m, car) => Math.max(m, Math.exp(-(((x - car.x) / 30) ** 2))), 0)
      if (near > 0.2) {
        const phase = (t * 1.8 + x * 0.01) % 1
        dots.push({ x, y: DECK + 3, r: 3 + phase * 12 * near, accent: false })
      }
    })
    let ripple = ''
    for (let row = 0; row < 3; row++) {
      for (let x = 10 + ((t * 9 + row * 23) % 26); x < 390; x += 26) ripple += `M${x.toFixed(1)} ${WATER + 6 + row * 7}h${10 - row * 2}`
    }
    paths.push({ d: ripple, thin: true })
    return {
      paths,
      dots,
      labels: [
        { x: 394, y: 18, text: `δmax = ${(Math.max(...[60, 150, 200, 250, 340].map(deflect)) * 1.37).toFixed(1)} mm`, anchor: 'end' as const },
        { x: 394, y: 30, text: `Tmax = ${(1640 + maxTension * 420).toFixed(0)} kN`, anchor: 'end' as const },
      ],
    }
  }
  if (kind.value === 1) {
    // 查询 token 依次聚焦；注意力弧线宽度即权重，激活沿残差流上行，顶部类别分布随之收敛。
    const query = Math.floor(t * 0.6) % TOKENS.length
    const local = (t * 0.6) % 1
    const weights = TOKEN_X.map((_, index) => {
      const raw = Math.exp(Math.sin(index * 2.1 + query * 1.3 + 0.7) * 1.6)
      return raw
    })
    const total = weights.reduce((sum, value) => sum + value, 0)
    const paths: Array<{ d: string; accent?: boolean; thin?: boolean }> = []
    const dots: Dot[] = []
    const labels: Array<{ x: number; y: number; text: string; anchor: 'start' | 'middle' | 'end' }> = []
    const qx = TOKEN_X[query]!
    let strong = ''
    weights.forEach((weight, index) => {
      if (index === query) return
      const x = TOKEN_X[index]!
      const share = weight / total
      const lift = 18 + Math.abs(x - qx) * 0.16
      const arc = `M${qx} 204Q${(qx + x) / 2} ${204 - lift * 2} ${x} 204`
      if (share > 0.17) strong += arc
      else paths.push({ d: arc, thin: true })
    })
    if (strong) paths.push({ d: strong, accent: true })
    paths.push({ d: `M${qx - 20} 206H${qx + 20}V226H${qx - 20}Z`, accent: true })
    TOKEN_X.forEach((x, index) => {
      const travel = (t * 0.9 + index * 0.23) % 1
      dots.push({ x, y: 204 - travel * 134, r: 1.8 + (index === query ? 1 : 0), accent: true })
    })
    LAYER_Y.forEach((y, layer) => {
      const head = (query + layer) % TOKENS.length
      paths.push({ d: `M${TOKEN_X[head]! - 16} ${y - 8}h32v16h-32Z`, accent: true })
    })
    const settle = 0.5 + 0.5 * Math.sin(local * Math.PI)
    const probabilities = [0.18, 0.56, 0.16, 0.1].map((value, index) => value + Math.sin(t * 1.3 + index * 1.7) * 0.06 * (1 - settle * 0.5))
    const sum = probabilities.reduce((a, b) => a + b, 0)
    const best = probabilities.indexOf(Math.max(...probabilities))
    probabilities.forEach((value, index) => {
      const height = (value / sum) * 64
      paths.push({ d: `M${76 + index * 82} 56V${(56 - height).toFixed(1)}H${124 + index * 82}V56Z`, accent: index === best, thin: index !== best })
      labels.push({ x: 100 + index * 82, y: Math.max(14, 50 - height), text: (value / sum).toFixed(2), anchor: 'middle' })
    })
    return { paths, dots, labels }
  }
  if (kind.value === 2) {
    // 实时监测：数据从右侧流入、向左流动；采样点随信号一起移动，波形不再抖动。
    // 异常按真实 SHM 类别轮换（离群 / 方波 / 缺失 / 微弱 / 漂移），完整进入窗口后被识别并标注证据区间。
    const speed = 30
    const shift = t * speed
    const step = 3
    const first = Math.floor((shift + 20) / step)
    const points: string[] = []
    const missing: string[] = []
    for (let k = first; ; k++) {
      const u = k * step
      const x = u - shift
      if (x > 380) break
      if (x < 20) continue
      const sample = signalAt(u, k)
      if (sample.missing) missing.push(`${x.toFixed(1)} 130`)
      points.push(`${points.length ? 'L' : 'M'}${x.toFixed(1)} ${sample.y.toFixed(1)}`)
    }
    const paths: Array<{ d: string; accent?: boolean; thin?: boolean }> = [{ d: points.join('') }]
    const dots: Dot[] = []
    const labels: Array<{ x: number; y: number; text: string; anchor: 'start' | 'middle' | 'end' }> = []
    // 右侧是当前推理窗口。
    paths.push({ d: 'M318 36H380V222H318Z', thin: true })
    labels.push({ x: 349, y: 30, text: 'infer', anchor: 'middle' }, { x: 22, y: 246, text: 'CH-07 · 20 Hz', anchor: 'start' })
    const lastEvent = Math.floor((shift + 380 - EVENT_OFFSET) / EVENT_PERIOD)
    for (let n = lastEvent; n >= lastEvent - 2; n--) {
      if (n < 0) continue
      const event = anomalyEvent(n)
      const left = event.center - event.width / 2 - shift
      const right = event.center + event.width / 2 - shift
      if (right < 20 || left > 316) continue
      // 刚离开推理窗口时，识别框从中心展开。
      const age = Math.min(1, Math.max(0, (316 - right) / 26))
      if (age <= 0) continue
      const half = ((right - left) / 2) * (0.35 + 0.65 * age)
      const middle = (left + right) / 2
      const x1 = Math.max(20, middle - half), x2 = Math.min(316, middle + half)
      if (x2 - x1 < 2) continue
      const box = `M${x1.toFixed(1)} 42H${x2.toFixed(1)}V214H${x1.toFixed(1)}Z`
      paths.push({ d: box, accent: true })
      if (middle > 20) dots.push({ x: middle, y: 42, r: 3, accent: true })
      labels.push({ x: Math.max(24, Math.min(312, middle)), y: 34, text: `${event.type} · p ${event.confidence.toFixed(2)}`, anchor: middle < 90 ? 'start' : middle > 250 ? 'end' : 'middle' })
    }
    if (missing.length) paths.push({ d: `M${missing.join('L')}`, thin: true })
    return { paths, dots, labels }
  }
  // 剖面：太阳沿黄金弧运行，光线穿过楼层，窗格依次亮起。
  const s = 0.5 + 0.5 * Math.sin(t * 0.45)
  const angle = Math.PI - s * Math.PI / 2
  const sun = { x: 250 + 160 * Math.cos(angle), y: 60 + 160 * Math.sin(angle) }
  const lit = Array.from({ length: 4 }, (_, k) => ({ d: `M${100 + k * 38} ${96 + ((Math.floor(t * 1.2) + k) % 4) * 32}h22v18h-22Z`, accent: true }))
  return {
    paths: [{ d: `M${sun.x} ${sun.y}L330 220`, thin: true }, ...lit],
    dots: [{ x: sun.x, y: sun.y, r: 5, accent: true }],
    labels: [{ x: 390, y: 30, text: `α = ${(s * 90).toFixed(0)}°`, anchor: 'end' as const }],
  }
})

function tick(now: number) {
  if (!start) start = now - time.value * 1000
  time.value = (now - start) / 1000
  frame = requestAnimationFrame(tick)
}
function play() { if (!frame && props.live) frame = requestAnimationFrame(tick) }
function pause() { cancelAnimationFrame(frame); frame = 0; start = 0 }

onMounted(() => {
  if (!props.live || window.matchMedia('(prefers-reduced-motion: reduce)').matches || typeof IntersectionObserver === 'undefined') return
  observer = new IntersectionObserver(([entry]) => (entry?.isIntersecting ? play() : pause()), { rootMargin: '10% 0px' })
  if (root.value) observer.observe(root.value)
})
onBeforeUnmount(() => { observer?.disconnect(); pause() })
</script>

<template>
  <svg ref="root" class="line-art" viewBox="0 0 400 260" fill="none" aria-hidden="true">
    <path v-for="(mark, index) in drawing.marks" :key="`m${index}`" :d="mark.d" pathLength="1" class="line-art__stroke" :class="{ 'is-accent': mark.accent, 'is-thin': mark.thin }" :style="{ '--k': index }" />
    <circle v-for="(dot, index) in drawing.dots" :key="`d${index}`" :cx="dot.x" :cy="dot.y" :r="dot.r" class="line-art__dot" :class="{ 'is-accent': dot.accent }" :style="{ '--k': index }" />
    <text v-for="(label, index) in drawing.labels" :key="`l${index}`" :x="label.x" :y="label.y" :text-anchor="label.anchor || 'start'" class="line-art__label">{{ label.text }}</text>
    <g class="line-art__live">
      <path v-for="(path, index) in live.paths" :key="`lp${index}`" :d="path.d" class="line-art__live-path" :class="{ 'is-accent': 'accent' in path && path.accent, 'is-thin': 'thin' in path && path.thin }" />
      <circle v-for="(dot, index) in live.dots" :key="`ld${index}`" :cx="dot.x" :cy="dot.y" :r="dot.r" class="line-art__live-dot" :class="{ 'is-accent': dot.accent }" />
      <text v-for="(label, index) in live.labels" :key="`ll${index}`" :x="label.x" :y="label.y" :text-anchor="label.anchor" class="line-art__label line-art__label--live">{{ label.text }}</text>
    </g>
  </svg>
</template>
