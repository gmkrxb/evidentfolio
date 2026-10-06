<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { Pause, Play } from 'lucide-vue-next'
import { useLocaleStore } from '@/stores/locale'

/**
 * 多智能体协作：规划、感知、检索、推理、校验、执行六个智能体围绕一项任务协作。
 * 消息沿连线传递，右侧终端实时记录工具调用；点击智能体会向其余智能体广播心跳，悬停查看职责与工具。
 */
type AgentId = 'planner' | 'perception' | 'retriever' | 'reasoner' | 'verifier' | 'operator' | 'task'
interface Agent { id: AgentId; zh: string; en: string; roleZh: string; roleEn: string; tools: string[]; glyph: string }
interface Step { from: AgentId; to: AgentId; zh: string; en: string; tone?: 'reject' | 'accept' }

const locale = useLocaleStore()
const en = computed(() => locale.isEnglish)
const AGENTS: Agent[] = [
  { id: 'planner', zh: '规划', en: 'Planner', roleZh: '拆解任务，分派子目标，决定何时结束', roleEn: 'Decomposes the task and decides when it is done', tools: ['plan()', 'delegate()', 'stop()'], glyph: '◇' },
  { id: 'perception', zh: '感知', en: 'Perception', roleZh: '订阅物联网传感器流，切窗与降噪', roleEn: 'Subscribes to IoT streams, windows and denoises', tools: ['mqtt.subscribe', 'fft', 'patchify'], glyph: '◉' },
  { id: 'retriever', zh: '检索', en: 'Retriever', roleZh: '在规范、历史病害与文献中检索证据', roleEn: 'Retrieves codes, past defects and literature', tools: ['vector.search', 'bm25', 'rerank'], glyph: '⌕' },
  { id: 'reasoner', zh: '推理', en: 'Reasoner', roleZh: '大语言模型在证据约束下给出诊断', roleEn: 'An LLM that diagnoses under evidence constraints', tools: ['llm.generate', 'cot', 'json_schema'], glyph: '∴' },
  { id: 'verifier', zh: '校验', en: 'Verifier', roleZh: '回到原始时间轴核验每一条结论', roleEn: 'Checks every claim against the raw timeline', tools: ['iou()', 'replay()', 'unit_test'], glyph: '✓' },
  { id: 'operator', zh: '执行', en: 'Operator', roleZh: '生成报告，派发运维工单', roleEn: 'Writes the report and dispatches maintenance', tools: ['report.pdf', 'ticket.create', 'notify'], glyph: '⚙' },
]
const SCRIPT: Step[] = [
  { from: 'task', to: 'planner', zh: 'task · 诊断 CH-07 夜间异常', en: 'task · diagnose CH-07 night anomaly' },
  { from: 'planner', to: 'perception', zh: 'subscribe(bridge/A3/acc, 20 Hz)', en: 'subscribe(bridge/A3/acc, 20 Hz)' },
  { from: 'perception', to: 'planner', zh: 'window ready · 72,000 pts', en: 'window ready · 72,000 pts' },
  { from: 'planner', to: 'retriever', zh: 'query(钢箱梁 · 加速度 · 方波)', en: 'query(steel box girder · accel · square)' },
  { from: 'retriever', to: 'reasoner', zh: 'context · 8 docs · 3 cases', en: 'context · 8 docs · 3 cases' },
  { from: 'perception', to: 'reasoner', zh: 'tokens · 6 × patch', en: 'tokens · 6 × patch' },
  { from: 'reasoner', to: 'verifier', zh: 'claim · square @ 01:12–01:19', en: 'claim · square @ 01:12–01:19' },
  { from: 'verifier', to: 'reasoner', zh: 'reject · IoU 0.41 < 0.50', en: 'reject · IoU 0.41 < 0.50', tone: 'reject' },
  { from: 'reasoner', to: 'verifier', zh: 'claim · square @ 01:13–01:17', en: 'claim · square @ 01:13–01:17' },
  { from: 'verifier', to: 'operator', zh: 'accept · IoU 0.92 · evidence ✓', en: 'accept · IoU 0.92 · evidence ✓', tone: 'accept' },
  { from: 'operator', to: 'task', zh: 'report.pdf · ticket #1005', en: 'report.pdf · ticket #1005' },
]

const W = 640, H = 540, CX = 320, CY = 270, RING = 205
const positions = computed(() => {
  const map = {} as Record<AgentId, { x: number; y: number }>
  AGENTS.forEach((agent, index) => {
    const a = -Math.PI / 2 + (index / AGENTS.length) * Math.PI * 2
    map[agent.id] = { x: CX + Math.cos(a) * RING, y: CY + Math.sin(a) * RING * 0.86 }
  })
  map.task = { x: CX, y: CY }
  return map
})
const mesh = computed(() => {
  const lines: Array<{ d: string; key: string }> = []
  AGENTS.forEach((a, i) => AGENTS.forEach((b, j) => { if (i < j) lines.push({ key: `${a.id}-${b.id}`, d: curve(a.id, b.id) }) }))
  return lines
})
function curve(from: AgentId, to: AgentId) {
  const a = positions.value[from], b = positions.value[to]
  const mx = (a.x + b.x) / 2, my = (a.y + b.y) / 2
  const pull = from === 'task' || to === 'task' ? 0 : 0.28
  const cx = mx + (CX - mx) * pull, cy = my + (CY - my) * pull
  return `M${a.x.toFixed(1)} ${a.y.toFixed(1)}Q${cx.toFixed(1)} ${cy.toFixed(1)} ${b.x.toFixed(1)} ${b.y.toFixed(1)}`
}
function pointOn(from: AgentId, to: AgentId, t: number) {
  const a = positions.value[from], b = positions.value[to]
  const mx = (a.x + b.x) / 2, my = (a.y + b.y) / 2
  const pull = from === 'task' || to === 'task' ? 0 : 0.28
  const cx = mx + (CX - mx) * pull, cy = my + (CY - my) * pull
  const u = 1 - t
  return { x: u * u * a.x + 2 * u * t * cx + t * t * b.x, y: u * u * a.y + 2 * u * t * cy + t * t * b.y }
}

const compact = ref(false)
const stepIndex = ref(0)
const progress = ref(0)
const playing = ref(true)
const hovered = ref<AgentId | null>(null)
const pinned = ref<AgentId | null>(null)
const log = ref<Array<{ id: number; time: string; from: AgentId; to: AgentId; text: string; tone?: string }>>([])
const broadcasts = ref<Array<{ id: number; from: AgentId; t: number }>>([])
const received = ref<Record<string, number>>({})
let logId = 0
let frame = 0
let last = 0
let visible = false
let observer: IntersectionObserver | undefined
const root = ref<HTMLElement | null>(null)
const clock = ref(new Date(2026, 9, 5, 1, 20, 0))

const step = computed(() => SCRIPT[stepIndex.value % SCRIPT.length]!)
const packet = computed(() => (progress.value <= 1 ? pointOn(step.value.from, step.value.to, easeInOut(progress.value)) : null))
const activeEdge = computed(() => curve(step.value.from, step.value.to))
const focus = computed(() => pinned.value || hovered.value)
const focusAgent = computed(() => AGENTS.find((agent) => agent.id === focus.value) || null)
const name = (id: AgentId) => (id === 'task' ? (en.value ? 'Task' : '任务') : (en.value ? AGENTS.find((a) => a.id === id)!.en : AGENTS.find((a) => a.id === id)!.zh))
function easeInOut(t: number) { return t < 0.5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2 }

function pushLog(item: Step | { from: AgentId; to: AgentId; zh: string; en: string; tone?: string }) {
  clock.value = new Date(clock.value.getTime() + 1000 + Math.round(Math.random() * 2500))
  const time = clock.value.toTimeString().slice(0, 8)
  log.value = [...log.value, { id: ++logId, time, from: item.from, to: item.to, text: en.value ? item.en : item.zh, tone: item.tone }].slice(-12)
  received.value = { ...received.value, [item.to]: performance.now() }
}
function tick(now: number) {
  frame = requestAnimationFrame(tick)
  const dt = Math.min(0.05, (now - (last || now)) / 1000)
  last = now
  if (!visible) return
  if (playing.value) {
    const before = progress.value
    progress.value += dt / 1.05
    if (before < 1 && progress.value >= 1) pushLog(step.value)
    if (progress.value > 1.55) { progress.value = 0; stepIndex.value = (stepIndex.value + 1) % SCRIPT.length }
  }
  if (broadcasts.value.length) {
    broadcasts.value = broadcasts.value.map((b) => ({ ...b, t: b.t + dt / 0.9 })).filter((b) => b.t < 1.05)
  }
}
function broadcast(id: AgentId) {
  pinned.value = pinned.value === id ? null : id
  broadcasts.value = [...broadcasts.value, { id: ++logId, from: id, t: 0 }]
  pushLog({ from: id, to: 'task', zh: `heartbeat · 广播至 ${AGENTS.length - 1} 个智能体`, en: `heartbeat · broadcast to ${AGENTS.length - 1} agents` })
  window.dispatchEvent(new CustomEvent('portfolio:chime', { detail: { kind: 'broadcast' } }))
}
function isRecent(id: AgentId) { return (performance.now() - (received.value[id] || -9999)) < 900 }

let compactQuery: MediaQueryList | undefined
const syncCompact = () => { compact.value = Boolean(compactQuery?.matches) }
onMounted(() => {
  compactQuery = window.matchMedia('(max-width: 600px)')
  syncCompact()
  compactQuery.addEventListener('change', syncCompact)
  if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
    playing.value = false
    SCRIPT.forEach((s) => pushLog(s))
    progress.value = 2
    return
  }
  // 先放入上一轮的最后几条记录，终端不至于空着。
  SCRIPT.slice(-9).forEach((s) => pushLog(s))
  observer = new IntersectionObserver(([entry]) => { visible = Boolean(entry?.isIntersecting) }, { threshold: 0.1 })
  if (root.value) observer.observe(root.value)
  frame = requestAnimationFrame(tick)
})
onBeforeUnmount(() => { cancelAnimationFrame(frame); observer?.disconnect(); compactQuery?.removeEventListener('change', syncCompact) })
</script>

<template>
  <div ref="root" class="swarm">
    <figure class="swarm__stage">
      <svg :viewBox="compact ? '78 34 484 500' : `0 0 ${W} ${H}`" role="img" :aria-label="en ? 'Six agents collaborating on one task' : '六个智能体围绕一项任务协作'">
        <defs>
          <radialGradient id="swarm-core" cx="50%" cy="50%" r="50%"><stop offset="0%" class="swarm__core-glow" /><stop offset="100%" stop-opacity="0" class="swarm__core-glow" /></radialGradient>
        </defs>
        <ellipse :cx="CX" :cy="CY" :rx="RING" :ry="RING * 0.86" class="swarm__orbit" />
        <ellipse :cx="CX" :cy="CY" :rx="RING * 0.55" :ry="RING * 0.47" class="swarm__orbit swarm__orbit--inner" />
        <path v-for="line in mesh" :key="line.key" :d="line.d" class="swarm__mesh" :class="{ 'is-focus': focus && line.key.includes(focus) }" />
        <path v-for="agent in AGENTS" :key="`spoke-${agent.id}`" :d="`M${CX} ${CY}L${positions[agent.id].x} ${positions[agent.id].y}`" class="swarm__spoke" />
        <path :d="activeEdge" class="swarm__active" :class="step.tone ? `is-${step.tone}` : ''" />
        <!-- 广播：从被点击的智能体向其余智能体扩散 -->
        <g v-for="b in broadcasts" :key="b.id">
          <circle v-for="agent in AGENTS.filter((a) => a.id !== b.from)" :key="agent.id" r="3" class="swarm__packet" :cx="pointOn(b.from, agent.id, b.t).x" :cy="pointOn(b.from, agent.id, b.t).y" />
        </g>
        <circle v-if="packet" :cx="packet.x" :cy="packet.y" r="5" class="swarm__packet swarm__packet--main" :class="step.tone ? `is-${step.tone}` : ''" />
        <circle v-if="packet" :cx="packet.x" :cy="packet.y" r="12" class="swarm__packet-halo" />
        <!-- 任务核心 -->
        <circle :cx="CX" :cy="CY" r="70" fill="url(#swarm-core)" />
        <circle :cx="CX" :cy="CY" r="34" class="swarm__core" :class="{ 'is-recent': isRecent('task') }" />
        <text :x="CX" :y="CY - 2" class="swarm__core-title">{{ en ? 'TASK' : '任务' }}</text>
        <text :x="CX" :y="CY + 14" class="swarm__core-sub">CH-07</text>
        <!-- 智能体 -->
        <g v-for="agent in AGENTS" :key="agent.id" class="swarm__agent"
          :class="{ 'is-active': step.from === agent.id || step.to === agent.id, 'is-recent': isRecent(agent.id), 'is-focus': focus === agent.id }"
          :transform="`translate(${positions[agent.id].x} ${positions[agent.id].y})`" tabindex="0" role="button"
          :aria-label="`${en ? agent.en : agent.zh} — ${en ? agent.roleEn : agent.roleZh}`"
          @pointerenter="hovered = agent.id" @pointerleave="hovered = null" @focus="hovered = agent.id" @blur="hovered = null"
          @click="broadcast(agent.id)" @keydown.enter.prevent="broadcast(agent.id)">
          <circle r="46" class="swarm__hit" />
          <circle r="30" class="swarm__ring" />
          <circle r="22" class="swarm__node" />
          <g v-if="step.from === agent.id && progress < 1" class="swarm__thinking">
            <circle v-for="n in 3" :key="n" r="2.2" :cx="Math.cos(progress * 12 + n * 2.1) * 30" :cy="Math.sin(progress * 12 + n * 2.1) * 30" />
          </g>
          <text y="6" class="swarm__glyph">{{ agent.glyph }}</text>
          <text y="50" class="swarm__name">{{ en ? agent.en : agent.zh }}</text>
          <text y="64" class="swarm__alt">{{ en ? agent.zh : agent.en }}</text>
        </g>
      </svg>
      <figcaption class="swarm__caption">
        <template v-if="focusAgent">
          <strong>{{ en ? focusAgent.en : focusAgent.zh }}</strong>
          <span>{{ en ? focusAgent.roleEn : focusAgent.roleZh }}</span>
          <code v-for="tool in focusAgent.tools" :key="tool">{{ tool }}</code>
        </template>
        <span v-else class="swarm__hint">{{ en ? 'Hover an agent to see its tools · click to broadcast' : '悬停查看智能体的工具 · 点击向其余智能体广播' }}</span>
      </figcaption>
    </figure>
    <aside class="swarm__terminal" :aria-label="en ? 'Message log' : '消息日志'">
      <header>
        <span><i />agents.log</span>
        <button type="button" :aria-label="playing ? (en ? 'Pause' : '暂停') : (en ? 'Play' : '播放')" @click="playing = !playing">
          <Pause v-if="playing" :size="14" /><Play v-else :size="14" />
        </button>
      </header>
      <TransitionGroup tag="ol" name="swarm-log">
        <li v-for="line in log" :key="line.id" :class="line.tone ? `is-${line.tone}` : ''">
          <time>{{ line.time }}</time>
          <span class="swarm__route">{{ name(line.from) }} <b>→</b> {{ name(line.to) }}</span>
          <span class="swarm__text">{{ line.text }}</span>
        </li>
      </TransitionGroup>
      <footer>
        <span>{{ en ? 'step' : '步骤' }} {{ String(stepIndex + 1).padStart(2, '0') }} / {{ String(SCRIPT.length).padStart(2, '0') }}</span>
        <span>{{ en ? 'protocol · evidence-first' : '协议 · 证据优先' }}</span>
      </footer>
    </aside>
  </div>
</template>

<style scoped>
.swarm { display: grid; grid-template-columns: minmax(0, 1.25fr) minmax(280px, .75fr); gap: clamp(20px, 3vw, 48px); align-items: center; }
.swarm__stage { margin: 0; }
.swarm svg { display: block; width: 100%; height: auto; overflow: visible; }
.swarm__orbit { fill: none; stroke: var(--color-line-strong); stroke-width: 1; stroke-dasharray: 2 6; animation: swarm-spin 60s linear infinite; transform-origin: 320px 270px; }
.swarm__orbit--inner { stroke: color-mix(in srgb, var(--color-accent) 40%, transparent); animation-duration: 40s; animation-direction: reverse; }
.swarm__mesh { fill: none; stroke: var(--color-ink); stroke-opacity: .08; stroke-width: 1; transition: stroke-opacity .4s, stroke .4s; }
.swarm__mesh.is-focus { stroke: var(--color-accent); stroke-opacity: .45; }
.swarm__spoke { stroke: var(--color-ink); stroke-opacity: .07; stroke-dasharray: 1 5; }
.swarm__active { fill: none; stroke: var(--color-accent); stroke-width: 1.6; stroke-opacity: .75; }
.swarm__active.is-reject { stroke: var(--color-ink); stroke-dasharray: 4 4; }
.swarm__packet { fill: var(--color-accent); }
.swarm__packet--main.is-reject { fill: var(--color-ink); }
.swarm__packet-halo { fill: var(--color-accent); fill-opacity: .14; }
.swarm__core-glow { stop-color: var(--color-accent); stop-opacity: .1; }
.swarm__core { fill: var(--color-surface-strong); stroke: var(--color-ink); stroke-width: 1.2; transition: stroke .3s; }
.swarm__core.is-recent { stroke: var(--color-accent); stroke-width: 2; }
.swarm__core-title { fill: var(--color-ink); font-family: var(--font-display); font-size: 15px; text-anchor: middle; }
.swarm__core-sub { fill: var(--color-muted); font-family: var(--font-mono); font-size: 9px; letter-spacing: .1em; text-anchor: middle; }
.swarm__agent { cursor: pointer; outline: none; }
.swarm__hit { fill: transparent; }
.swarm__ring { fill: none; stroke: var(--color-line-strong); stroke-width: 1; transition: stroke .3s, r .5s cubic-bezier(.34,1.36,.5,1); }
.swarm__node { fill: var(--color-surface-strong); stroke: var(--color-ink); stroke-width: 1.2; transition: fill .35s, stroke .35s, r .5s cubic-bezier(.34,1.36,.5,1); }
.swarm__glyph { fill: var(--color-ink); font-size: 17px; text-anchor: middle; pointer-events: none; transition: fill .35s; }
.swarm__name { fill: var(--color-ink); font-family: var(--font-display); font-size: 15px; text-anchor: middle; }
.swarm__alt { fill: var(--color-muted); font-family: var(--font-mono); font-size: 9px; letter-spacing: .1em; text-anchor: middle; text-transform: uppercase; }
.swarm__agent.is-active .swarm__ring { stroke: var(--color-accent); }
.swarm__agent.is-recent .swarm__node, .swarm__agent.is-focus .swarm__node { fill: var(--color-ink); r: 25; }
.swarm__agent.is-recent .swarm__glyph, .swarm__agent.is-focus .swarm__glyph { fill: var(--color-inverse); }
.swarm__agent.is-focus .swarm__ring { r: 36; stroke: var(--color-accent); }
.swarm__agent:focus-visible .swarm__ring { stroke: var(--color-accent); stroke-width: 2; }
.swarm__thinking circle { fill: var(--color-accent); }
.swarm__caption { display: flex; flex-wrap: wrap; align-items: center; justify-content: center; gap: 8px 10px; min-height: 40px; margin-top: 4px; font-size: 14px; color: var(--color-ink-soft); text-align: center; }
.swarm__caption strong { font-family: var(--font-display); font-weight: 400; font-size: 17px; color: var(--color-ink); }
.swarm__caption code { padding: 2px 8px; border: 1px solid var(--color-line); border-radius: 999px; font-family: var(--font-mono); font-size: 11px; color: var(--color-accent-ink); }
.swarm__hint { font-family: var(--font-mono); font-size: 11px; letter-spacing: .06em; color: var(--color-muted); }
.swarm__terminal {
  --t-bg: color-mix(in srgb, var(--color-surface-strong) 88%, var(--color-accent) 3%);
  --t-fg: var(--color-ink);
  --t-soft: var(--color-ink-soft);
  --t-dim: var(--color-muted);
  --t-line: var(--color-line);
  --t-accent: var(--color-accent-ink);
  --t-reject: #b0532e;
  --t-accept: #4d7a3c;
  overflow: hidden; border: 1px solid var(--t-line); border-radius: 16px; background: var(--t-bg); color: var(--t-fg); font-family: var(--font-mono); font-size: 12px;
  box-shadow: 0 30px 80px -46px rgb(60 40 20 / 35%), inset 0 1px 0 rgb(255 255 255 / 60%);
  -webkit-backdrop-filter: blur(10px); backdrop-filter: blur(10px);
}
:root[data-theme='dark'] .swarm__terminal {
  --t-bg: #0f0e0c; --t-fg: #e9e2d6; --t-soft: rgb(233 226 214 / 66%); --t-dim: rgb(233 226 214 / 42%);
  --t-line: rgb(255 255 255 / 9%); --t-accent: #e08a64; --t-reject: #d9a07a; --t-accept: #b9d6a6;
  box-shadow: 0 30px 80px -40px rgb(0 0 0 / 80%), inset 0 1px 0 rgb(255 255 255 / 4%);
}
.swarm__terminal header, .swarm__terminal footer { display: flex; align-items: center; justify-content: space-between; gap: 12px; padding: 10px 14px; border-bottom: 1px solid var(--t-line); color: var(--t-dim); font-size: 11px; letter-spacing: .06em; }
.swarm__terminal footer { border-top: 1px solid var(--t-line); border-bottom: 0; }
.swarm__terminal header span { display: inline-flex; align-items: center; gap: 8px; color: var(--t-soft); }
.swarm__terminal header i { width: 7px; height: 7px; border-radius: 50%; background: var(--t-accent); box-shadow: 0 0 0 4px color-mix(in srgb, var(--t-accent) 18%, transparent); animation: swarm-blink 1.6s steps(2) infinite; }
.swarm__terminal header button { display: grid; width: 28px; height: 28px; padding: 0; place-items: center; border: 1px solid var(--t-line); border-radius: 50%; background: transparent; color: var(--t-soft); cursor: pointer; transition: background .3s, border-color .3s; }
.swarm__terminal header button:hover { border-color: var(--t-fg); background: color-mix(in srgb, var(--t-fg) 8%, transparent); }
.swarm__terminal ol { position: relative; display: flex; flex-direction: column; justify-content: flex-end; height: 300px; margin: 0; padding: 12px 14px; overflow: hidden; list-style: none; -webkit-mask-image: linear-gradient(to bottom, transparent 0, #000 26%); mask-image: linear-gradient(to bottom, transparent 0, #000 26%); }
.swarm__terminal li { flex: none; display: grid; grid-template-columns: auto 1fr; gap: 2px 10px; padding: 6px 0; border-bottom: 1px dashed var(--t-line); line-height: 1.5; }
.swarm__terminal time { grid-row: span 2; color: var(--t-dim); }
.swarm__route { color: var(--t-fg); }
.swarm__route b { color: var(--t-accent); font-weight: 400; }
.swarm__text { color: var(--t-soft); overflow-wrap: anywhere; }
.swarm__terminal li.is-reject .swarm__text { color: var(--t-reject); text-decoration: line-through color-mix(in srgb, var(--t-reject) 45%, transparent); }
.swarm__terminal li.is-accept .swarm__text { color: var(--t-accept); }
.swarm-log-enter-active { transition: opacity .7s ease .12s, transform .7s cubic-bezier(.22,1,.36,1); }
.swarm-log-enter-from { opacity: 0; transform: translateY(100%); }
.swarm-log-leave-active { display: none; }
.swarm-log-move { transition: transform .7s cubic-bezier(.22,1,.36,1); }
@keyframes swarm-spin { to { transform: rotate(360deg); } }
@keyframes swarm-blink { 50% { opacity: .3; } }
@media (max-width: 900px) {
  .swarm { grid-template-columns: minmax(0, 1fr); }
  .swarm__terminal ol { height: 236px; }
}
@media (max-width: 600px) {
  .swarm__name { font-size: 19px; }
  .swarm__alt { font-size: 11px; }
  .swarm__glyph { font-size: 20px; }
  .swarm__core-title { font-size: 18px; }
  .swarm__terminal { font-size: 11.5px; }
}
@media (prefers-reduced-motion: reduce) { .swarm__orbit, .swarm__terminal header i { animation: none; } }
</style>
