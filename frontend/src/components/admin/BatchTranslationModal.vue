<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, ref } from 'vue'
import { Languages, X, Check, LoaderCircle, AlertCircle, Square, RotateCcw } from 'lucide-vue-next'
import { api } from '@/api/client'
import { readSse, type StreamEvent } from '@/utils/sse'
import { useSiteStore } from '@/stores/site'

const props = defineProps<{ defaultContextChars?: number }>()
const maxContextChars = ref(32000)
type Status = 'waiting' | 'running' | 'saved' | 'failed' | 'stopped'
interface Task { id: string; module: string; title: string; total: number; completed: number; status: Status; error: string; fields: NonNullable<StreamEvent['fields']>; reasoning: string; context?: { chars: number; limit: number; references: number } }
const dialog = ref<HTMLDialogElement>()
const source = ref('zh-CN')
const overwrite = ref(false)
const tasks = ref<Task[]>([])
const planning = ref(false)
const running = ref(false)
const error = ref('')
const selected = ref('')
const planSignature = ref('')
const reasoningBox = ref<HTMLElement>()
const contentBox = ref<HTMLElement>()
const followReasoning = ref(true)
const followContent = ref(true)
const site = useSiteStore()
let controller: AbortController | null = null
const current = computed(() => tasks.value.find((item) => item.id === selected.value))
const modules = computed(() => [...new Set(tasks.value.map((item) => item.module))])
const fieldsTotal = computed(() => tasks.value.reduce((sum, item) => sum + item.total, 0))
const processed = computed(() => tasks.value.reduce((sum, item) => sum + (item.status === 'saved' || item.status === 'failed' ? item.total : item.completed), 0))
const percent = computed(() => fieldsTotal.value ? Math.round(processed.value / fieldsTotal.value * 100) : 0)
const saved = computed(() => tasks.value.filter((item) => item.status === 'saved').length)
const failed = computed(() => tasks.value.filter((item) => item.status === 'failed' || item.status === 'stopped'))
const labels: Record<Status,string> = { waiting: '等待', running: '翻译中', saved: '已保存', failed: '失败', stopped: '已停止' }
function signature() { return `${source.value}:${overwrite.value}` }
function payload(only?: string[]) { return { source_locale: source.value, max_context_chars: maxContextChars.value, overwrite: overwrite.value, ...(only ? { only } : {}) } }
async function plan() {
  planning.value = true; error.value = ''; tasks.value = []
  try {
    const result = await api.post<{items: Array<{ id: string; module: string; title: string; total: number }>}>('/admin/ai/translate/plan', payload())
    tasks.value = result.items.map((item) => ({ ...item, completed: 0, status: 'waiting', error: '', fields: [], reasoning: '' }))
    selected.value = tasks.value[0]?.id || ''; planSignature.value = signature()
  } catch (cause) { error.value = cause instanceof Error ? cause.message : '无法读取翻译内容' }
  finally { planning.value = false }
}
async function open() { maxContextChars.value = props.defaultContextChars || 32000; dialog.value?.showModal(); await plan() }
function close() { if (!running.value) dialog.value?.close() }
function atBottom(event: Event) { const el = event.target as HTMLElement; return el.scrollHeight - el.scrollTop - el.clientHeight < 50 }
async function scroll() {
  await nextTick()
  if (followReasoning.value && reasoningBox.value) reasoningBox.value.scrollTop = reasoningBox.value.scrollHeight
  if (followContent.value && contentBox.value) contentBox.value.scrollTop = contentBox.value.scrollHeight
}
async function start(retry = false) {
  if (running.value || planning.value) return
  if (!Number.isInteger(maxContextChars.value) || maxContextChars.value < 4000 || maxContextChars.value > 200000) { error.value = '上下文窗口需为 4,000 至 200,000 字符'; return }
  if (planSignature.value !== signature()) { await plan(); if (error.value) return }
  if (!tasks.value.length) return
  const only = retry ? tasks.value.filter((item) => item.status !== 'saved').map((item) => item.id) : tasks.value.map((item) => item.id)
  if (!only.length) return
  controller = new AbortController(); running.value = true; error.value = ''
  let activeId = ''
  try {
    await readSse(await api.stream('/admin/ai/translate/batch/stream', payload(only), controller.signal), (event) => {
      if (event.type === 'plan') {
        const planned = new Set(event.items?.map((item) => item.id))
        tasks.value = tasks.value.filter((item) => item.status === 'saved' || planned.has(item.id))
        for (const item of event.items || []) {
          const task = tasks.value.find((task) => task.id === item.id)
          if (task) Object.assign(task, item, { completed: 0, status: 'waiting', error: '', fields: [], reasoning: '' })
        }
      }
      if (event.type === 'task_started') {
        activeId = event.id || ''; selected.value = activeId; followReasoning.value = true; followContent.value = true
      }
      const task = tasks.value.find((item) => item.id === (event.id || activeId))
      if (!task) return
      if (event.type === 'task_started') task.status = 'running'
      if (event.type === 'context') task.context = { chars: event.chars || 0, limit: event.limit || 0, references: event.references || 0 }
      if (event.type === 'reasoning') task.reasoning += event.content || ''
      if (event.type === 'fields') { task.fields = event.fields || []; task.completed = event.completed || 0 }
      if (event.type === 'task_done') { task.status = 'saved'; task.completed = task.total }
      if (event.type === 'task_error') { task.status = 'failed'; task.error = event.message || '翻译失败' }
      void scroll()
    })
  } catch (cause) {
    error.value = controller.signal.aborted ? '已停止。已保存的内容保留，其余项目可以继续。' : cause instanceof Error ? cause.message : '连接失败'
    tasks.value.filter((item) => item.status === 'running').forEach((item) => { item.status = 'stopped' })
  } finally { running.value = false; controller = null; void site.load(true).catch(() => undefined) }
}
function cancel() { controller?.abort() }
function beforeUnload(event: BeforeUnloadEvent) { if (running.value) event.preventDefault() }
window.addEventListener('beforeunload', beforeUnload)
onBeforeUnmount(() => { cancel(); window.removeEventListener('beforeunload', beforeUnload) })
defineExpose({ open })
</script>
<template>
  <Teleport to="body">
    <dialog ref="dialog" class="batch-dialog" aria-labelledby="batch-title" @cancel.prevent="close">
      <header class="batch-heading"><div><span class="eyebrow">TRANSLATION WORKSPACE</span><h2 id="batch-title"><Languages :size="24" />全系统翻译</h2><p>逐模块翻译并自动保存。参考已有译文与最近完成的内容，保持术语一致；附件原文件保持原样。</p></div><button class="icon-button" :disabled="running" aria-label="关闭全系统翻译" @click="close"><X :size="22" /></button></header>
      <div class="batch-options"><label>翻译方向<select v-model="source" :disabled="running || planning" @change="plan"><option value="zh-CN">中文 → English</option><option value="en">English → 中文</option></select></label><label class="batch-context-input">上下文上限（字符）<input v-model.number="maxContextChars" type="number" min="4000" max="200000" step="1000" :disabled="running || planning" /></label><label class="check-label"><input v-model="overwrite" type="checkbox" :disabled="running || planning" @change="plan" />重新翻译已有译文</label><span>{{ overwrite ? '完成后覆盖目标语言内容' : '仅补全缺失译文，保留已有内容' }}</span></div>
      <div class="batch-summary"><div><strong>{{ percent }}<small>%</small></strong><span>{{ saved }} / {{ tasks.length }} 项已保存<span v-if="failed.length"> · {{ failed.length }} 项需处理</span></span></div><progress :value="processed" :max="fieldsTotal || 1" /><small>{{ processed }} / {{ fieldsTotal }} 字段已处理 · 按模型 JSON 字段实时识别</small></div>
      <p v-if="error" class="form-error batch-error" role="alert">{{ error }}</p>
      <div v-if="planning" class="batch-empty">正在读取各模块内容…</div>
      <div v-else-if="!tasks.length" class="batch-empty">{{ error ? '请检查模型配置后重试。' : '当前方向没有待翻译内容，或译文已齐全。' }}<button class="button button--outline" @click="plan">重新检查</button></div>
      <div v-else class="batch-workspace">
        <nav class="batch-modules" aria-label="翻译模块"><section v-for="module in modules" :key="module"><h3>{{ module }} <small>{{ tasks.filter((item) => item.module === module && item.status === 'saved').length }}/{{ tasks.filter((item) => item.module === module).length }}</small></h3><button v-for="task in tasks.filter((item) => item.module === module)" :key="task.id" :class="{ active: selected === task.id }" @click="selected = task.id"><Check v-if="task.status === 'saved'" :size="15" /><AlertCircle v-else-if="['failed','stopped'].includes(task.status)" :size="15" /><LoaderCircle v-else-if="task.status === 'running'" :size="15" class="batch-spin" /><span v-else class="batch-dot" /><span>{{ task.title }}<small>{{ labels[task.status] }} · {{ task.completed }}/{{ task.total }} 字段</small></span></button></section></nav>
        <section v-if="current" class="batch-detail"><header><span class="eyebrow">{{ current.module }}</span><h3>{{ current.title }}</h3><p v-if="current.context" class="batch-context">参考 {{ current.context.references }} 条译文 · 滚动上下文 {{ current.context.chars.toLocaleString() }} / {{ current.context.limit.toLocaleString() }} 字符</p><p v-if="current.error" class="form-error">{{ current.error }}</p></header><div class="batch-streams"><section><h4>思考过程</h4><div ref="reasoningBox" class="batch-scroll" tabindex="0" @scroll="followReasoning = atBottom($event)">{{ current.reasoning || '模型提供的思考过程将在这里实时显示。' }}</div></section><section><h4>翻译正文 <span>{{ current.completed }}/{{ current.total }}</span></h4><div ref="contentBox" class="batch-scroll" tabindex="0" @scroll="followContent = atBottom($event)"><article v-for="field in current.fields" :key="field.path"><small>{{ field.label }} · {{ field.done ? '已接收' : '生成中' }}</small><p>{{ field.text }}</p></article><p v-if="!current.fields.length">等待正文内容…</p></div></section></div></section>
      </div>
      <footer><span>{{ running ? '正在流式翻译，完成一个项目后自动保存' : '可查看各模块结果；失败项可单独重试' }}</span><button v-if="running" class="button button--outline" @click="cancel"><Square :size="14" />停止</button><template v-else><button class="button button--outline" :disabled="planning" @click="plan"><RotateCcw :size="15" />刷新清单</button><button v-if="saved || failed.length" class="button button--dark" :disabled="!tasks.some((item) => item.status !== 'saved')" @click="start(true)">继续未完成项</button><button v-else class="button button--dark" :disabled="planning || !tasks.length" @click="start()">开始全部翻译</button></template></footer>
    </dialog>
  </Teleport>
</template>
<style scoped>
.batch-context-input{display:flex;align-items:center;gap:8px}.batch-context-input input{width:105px;padding:8px}.batch-context{font-size:11px;color:var(--color-muted);margin:0 0 12px}.batch-dialog{position:fixed;inset:0;width:min(1180px,calc(100vw - 36px));height:min(850px,calc(100dvh - 36px));padding:0;border:1px solid var(--color-line);border-radius:16px;box-shadow:0 30px 120px rgb(23 32 29 / 20%);background:var(--color-bg);color:var(--color-ink);margin:auto;overflow:hidden}.batch-dialog[open]{display:flex;flex-direction:column}.batch-dialog::backdrop{background:rgb(23 32 29 / 50%);backdrop-filter:blur(12px)}.batch-heading{line-height:1.4;display:flex;justify-content:space-between;padding:18px 24px 10px;gap:20px}.batch-heading h2{display:flex;align-items:center;gap:12px;font-size:23px;margin:4px 0}.batch-heading p{font-size:12px;color:var(--color-ink-soft);margin:6px 0}.batch-options{display:flex;gap:24px;align-items:center;padding:0 28px 18px;font-size:12px;flex-wrap:wrap}.batch-options>label:first-child{display:flex;align-items:center;gap:10px}.batch-options select{padding:8px 14px}.batch-options>span{color:var(--color-muted)}.batch-summary{padding:12px 24px;background:var(--color-surface-strong);border-block:1px solid var(--color-line)}.batch-summary>div{display:flex;align-items:baseline;gap:20px}.batch-summary strong{font-size:28px;line-height:1.2;letter-spacing:-.04em;font-variant-numeric:tabular-nums}.batch-summary strong small{font-size:16px}.batch-summary span,.batch-summary>small{font-size:12px;color:var(--color-ink-soft)}.batch-summary progress{display:block;width:100%;height:6px;accent-color:var(--color-brand);margin:12px 0 8px}.batch-workspace{min-height:0;flex:1;display:grid;grid-template-columns:260px 1fr}.batch-modules{overflow:auto;border-right:1px solid var(--color-line);padding:16px}.batch-modules h3{font-size:11px;color:var(--color-muted);margin:14px 10px 8px;display:flex;justify-content:space-between}.batch-modules button{border:0;background:transparent;display:flex;align-items:center;gap:10px;text-align:left;width:100%;padding:12px;border-radius:10px;font-size:12px}.batch-modules button:hover{background:var(--color-surface)}.batch-modules button.active{background:#e4eae2;color:var(--color-brand)}.batch-modules button>span:last-child{min-width:0;overflow-wrap:anywhere}.batch-modules small{display:block;font-size:10px;color:var(--color-muted);margin-top:4px}.batch-dot{width:6px;height:6px;background:var(--color-line-strong);border-radius:50%;margin:4px;flex-shrink:0}.batch-detail{display:flex;flex-direction:column;min-height:0;min-width:0;padding:22px}.batch-detail>header h3{font-size:20px;margin:5px 0 16px;overflow-wrap:anywhere}.batch-streams{min-height:0;flex:1;display:grid;grid-template-columns:1fr 1.3fr;gap:16px}.batch-streams>section{display:flex;flex-direction:column;min-height:0;min-width:0;background:var(--color-surface-strong);border:1px solid var(--color-line);border-radius:14px;overflow:hidden}.batch-streams h4{font-size:12px;padding:12px 16px;border-bottom:1px solid var(--color-line);margin:0}.batch-streams h4 span{float:right;color:var(--color-muted)}.batch-scroll{flex:1;overflow:auto;white-space:pre-wrap;overflow-wrap:anywhere;padding:16px;font-size:13px;line-height:1.8;overscroll-behavior:contain}.batch-scroll article{border-bottom:1px solid var(--color-line);margin-bottom:14px;padding-bottom:14px}.batch-scroll article small{font-size:10px;color:var(--color-brand-2)}.batch-scroll p{margin:5px 0}.batch-dialog footer{display:flex;align-items:center;justify-content:flex-end;gap:12px;padding:12px 24px;border-top:1px solid var(--color-line);background:var(--color-surface-strong)}.batch-dialog footer>span{margin-right:auto;font-size:11px;color:var(--color-muted)}.batch-error{margin:0;padding:8px 28px;font-size:12px}.batch-empty{flex:1;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:20px;color:var(--color-muted)}.batch-spin{animation:batch-spin 1.5s linear infinite;flex-shrink:0}@keyframes batch-spin{to{transform:rotate(360deg)}}@media(prefers-reduced-motion:reduce){.batch-spin{animation:none}}@media(max-width:760px){.batch-dialog{width:100vw;max-width:none;height:100dvh;max-height:none;border-radius:0}.batch-heading{line-height:1.4;padding:16px}.batch-options{padding:0 16px 12px;gap:10px}.batch-summary{padding:12px 16px}.batch-workspace{grid-template-columns:135px 1fr}.batch-modules{padding:6px}.batch-modules button{border:0;background:transparent;padding:9px 6px}.batch-detail{padding:10px}.batch-detail>header h3{font-size:15px}.batch-streams{grid-template-columns:1fr;grid-template-rows:1fr 1.5fr}.batch-dialog footer{padding:12px;flex-wrap:wrap}.batch-dialog footer>span{width:100%}.batch-dialog .button{font-size:12px;padding:10px 15px}}
</style>
