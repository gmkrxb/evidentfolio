<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useLocaleStore } from '@/stores/locale'

/** 首屏的「推理窗」：一个被证据约束的语言模型，在结构与诗之间作答。 */
const locale = useLocaleStore()
const DIALOGUES = {
  zh: [
    ['桥为什么会沉默？', '因为它把所有的力，都安静地交还给了大地。'],
    ['什么是证据？', '是一条别人可以重新走一遍的路。'],
    ['模型会写诗吗？', '它学会了押韵；而诗，是它学不会的停顿。'],
    ['结构与语言有何相同？', '二者都在约束之中，寻找自由。'],
    ['裂缝意味着什么？', '是材料在说话，只是声音很轻。'],
  ],
  en: [
    ['Why is a bridge silent?', 'Because it quietly returns every force to the earth.'],
    ['What is evidence?', 'A path that someone else can walk again.'],
    ['Can a model write poetry?', 'It learns the rhyme; the pause is what it cannot learn.'],
    ['What do structure and language share?', 'Both look for freedom within constraint.'],
    ['What does a crack mean?', 'The material is speaking — only very softly.'],
  ],
}
const dialogues = computed(() => (locale.isEnglish ? DIALOGUES.en : DIALOGUES.zh))
const index = ref(0)
const shown = ref(0)
const bars = ref<number[]>([])
const attention = ref<number[]>([])
const latency = ref('0.0')
const answer = computed(() => dialogues.value[index.value % dialogues.value.length]![1])
const question = computed(() => dialogues.value[index.value % dialogues.value.length]![0])
const tokens = computed(() => Array.from(answer.value))
const questionChars = computed(() => Array.from(question.value))
const typed = computed(() => tokens.value.slice(0, shown.value).join(''))
const done = computed(() => shown.value >= tokens.value.length)
const root = ref<HTMLElement | null>(null)
let timer = 0
let visible = true
let observer: IntersectionObserver | undefined
let started = 0

function schedule(delay: number) {
  window.clearTimeout(timer)
  timer = window.setTimeout(step, delay)
}
function step() {
  if (!visible || document.hidden) { schedule(600); return }
  if (!done.value) {
    // 以不规则的步长输出，像真实的 token 流。
    shown.value = Math.min(tokens.value.length, shown.value + 1 + Math.floor(Math.random() * (locale.isEnglish ? 4 : 2)))
    bars.value = [...bars.value, 0.55 + Math.random() * 0.45].slice(-28)
    // 每生成一个 token，重新分配对问题的注意力：少数几个字被高亮。
    const focus = Math.floor(Math.random() * questionChars.value.length)
    attention.value = questionChars.value.map((_, i) => Math.max(0.04, Math.exp(-((i - focus) ** 2) / 3) * (0.6 + Math.random() * 0.4)))
    latency.value = ((performance.now() - started) / 1000).toFixed(1)
    schedule(done.value ? 3600 : 45 + Math.random() * 70)
    return
  }
  index.value = (index.value + 1) % dialogues.value.length
  shown.value = 0
  bars.value = []
  attention.value = []
  started = performance.now()
  schedule(700)
}
watch(() => locale.isEnglish, () => { shown.value = 0; bars.value = []; started = performance.now(); schedule(400) })
onMounted(() => {
  if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) { shown.value = tokens.value.length; return }
  observer = new IntersectionObserver(([entry]) => { visible = Boolean(entry?.isIntersecting) })
  if (root.value) observer.observe(root.value)
  started = performance.now()
  schedule(1600)
})
onBeforeUnmount(() => { window.clearTimeout(timer); observer?.disconnect() })
</script>

<template>
  <aside ref="root" class="inference" :aria-label="locale.isEnglish ? 'A model reasoning under evidence' : '在证据约束下推理的模型'">
    <header class="inference__head">
      <span><i :class="{ 'is-busy': !done }" />{{ locale.isEnglish ? 'reasoning' : '推理中' }}</span>
      <span>evidence-bound · T=0.2</span>
    </header>
    <p class="inference__prompt"><b>›</b><span :aria-label="question"><i v-for="(char, k) in questionChars" :key="k" aria-hidden="true" :style="{ '--a': done ? 0 : (attention[k] || 0) }">{{ char }}</i></span></p>
    <p class="inference__answer" aria-live="off">{{ typed }}<span class="inference__caret" :class="{ 'is-done': done }" /></p>
    <footer class="inference__foot">
      <div class="inference__bars" aria-hidden="true"><i v-for="(bar, k) in bars" :key="k" :style="{ '--h': bar }" /></div>
      <span>{{ shown }} tok · {{ latency }}s</span>
    </footer>
  </aside>
</template>

<style scoped>
.inference { width: 340px; padding: 16px 18px 14px; border: 1px solid color-mix(in srgb, var(--color-ink) 12%, transparent); border-radius: 16px; background: color-mix(in srgb, var(--color-surface-strong) 72%, transparent); backdrop-filter: blur(14px) saturate(1.2); -webkit-backdrop-filter: blur(14px) saturate(1.2); box-shadow: 0 30px 70px -40px rgb(30 20 10 / 40%); font-family: var(--font-mono); color: var(--color-ink); }
.inference__head { display: flex; justify-content: space-between; gap: 12px; padding-bottom: 10px; border-bottom: 1px dashed var(--color-line-strong); font-size: 10px; letter-spacing: .1em; text-transform: uppercase; color: var(--color-muted); }
.inference__head span:first-child { display: inline-flex; align-items: center; gap: 8px; color: var(--color-ink-soft); }
.inference__head i { width: 6px; height: 6px; border-radius: 50%; background: var(--color-success, #4f7a5b); }
.inference__head i.is-busy { background: var(--color-accent); animation: inference-blink .9s steps(2) infinite; }
.inference__prompt { display: flex; gap: 8px; margin: 12px 0 0; font-size: 12px; line-height: 1.6; color: var(--color-muted); }
.inference__prompt b { color: var(--color-accent-ink); font-weight: 500; }
.inference__prompt i { font-style: normal; white-space: pre; border-radius: 2px; background: color-mix(in srgb, var(--color-accent) calc(var(--a, 0) * 45%), transparent); color: color-mix(in srgb, var(--color-ink) calc(40% + var(--a, 0) * 60%), var(--color-muted)); transition: background .25s, color .25s; }
.inference__answer { min-height: 3.2em; margin: 8px 0 0; font-family: var(--font-display); font-size: 17px; line-height: 1.6; letter-spacing: -.01em; color: var(--color-ink); }
.inference__caret { display: inline-block; width: 7px; height: 1.05em; margin-left: 3px; vertical-align: -.15em; background: var(--color-accent); animation: inference-blink 1s steps(2) infinite; }
.inference__caret.is-done { opacity: .35; }
.inference__foot { display: flex; align-items: flex-end; justify-content: space-between; gap: 14px; margin-top: 12px; font-size: 10px; letter-spacing: .06em; color: var(--color-muted); }
.inference__bars { display: flex; align-items: flex-end; gap: 2px; height: 18px; flex: 1; }
.inference__bars i { width: 3px; height: calc(var(--h) * 100%); border-radius: 1px; background: var(--color-accent); opacity: calc(var(--h) * .9); }
@keyframes inference-blink { 50% { opacity: 0; } }
@media (prefers-reduced-motion: reduce) { .inference__caret, .inference__head i.is-busy { animation: none; } }
</style>
