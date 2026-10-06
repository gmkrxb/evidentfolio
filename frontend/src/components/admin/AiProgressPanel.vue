<script setup lang="ts">
import { nextTick, ref, watch } from 'vue'
import { Sparkles, Square, X } from 'lucide-vue-next'
const props = defineProps<{ task: { running: boolean; reasoning: string; error: string; visible: boolean; context?: { chars: number; limit: number; references: number } | null; completed?: number; total?: number; fields?: Array<{path: string; label: string; text: string; done: boolean}> }; body: string }>()
const emit = defineEmits<{ cancel: []; close: [] }>()
const reasoningBox = ref<HTMLElement>()
const bodyBox = ref<HTMLElement>()
const followReasoning = ref(true)
const followBody = ref(true)
function atBottom(event: Event) {
  const el = event.target as HTMLElement
  return el.scrollHeight - el.scrollTop - el.clientHeight < 45
}
watch(() => [props.task.reasoning, props.body], async () => {
  await nextTick()
  if (followReasoning.value && reasoningBox.value) reasoningBox.value.scrollTop = reasoningBox.value.scrollHeight
  if (followBody.value && bodyBox.value) bodyBox.value.scrollTop = bodyBox.value.scrollHeight
})
watch(() => props.task.running, (running) => { if (running) { followReasoning.value = true; followBody.value = true } })
</script>
<template>
  <section v-if="task.visible" class="ai-progress" aria-label="AI 处理进度" :aria-busy="task.running">
    <header><span><Sparkles :size="18" />{{ task.running ? 'AI 正在处理' : task.error ? '任务已停止' : '生成完成，请检查后保存' }}</span><button v-if="task.running" type="button" class="button button--outline" @click="emit('cancel')"><Square :size="13" />停止</button><button v-else type="button" class="icon-button" aria-label="收起进度" @click="emit('close')"><X :size="16" /></button></header>
    <p v-if="task.context" class="ai-context">参考 {{ task.context.references }} 条已有译文 · 上下文 {{ task.context.chars.toLocaleString() }} / {{ task.context.limit.toLocaleString() }} 字符</p>
    <div v-if="task.total" class="ai-field-progress"><progress :value="task.completed || 0" :max="task.total" /><span>{{ task.completed }} / {{ task.total }} 个字段</span></div>
    <div class="ai-progress__columns">
      <div><h3>思考过程 <small>模型返回的推理信息</small></h3><div ref="reasoningBox" class="ai-progress__scroll" tabindex="0" @scroll="followReasoning = atBottom($event)">{{ task.reasoning || (task.running ? '等待模型响应…' : '此模型未提供思考过程') }}</div></div>
      <div><h3>正文 <small>{{ task.running ? '正在生成' : '可在表单中继续编辑' }}</small></h3><div ref="bodyBox" class="ai-progress__scroll" tabindex="0" @scroll="followBody = atBottom($event)"><template v-if="task.fields?.length"><article v-for="field in task.fields" :key="field.path" class="ai-field"><small>{{ field.label }} · {{ field.done ? '已接收' : '生成中' }}</small><p>{{ field.text }}</p></article></template><template v-else>{{ body || '正文将在这里逐步显示…' }}</template></div></div>
    </div>
    <p v-if="task.error" class="form-error" role="alert">{{ task.error }}</p>
  </section>
</template>
<style scoped>
.ai-context{font-size:11px;color:var(--color-muted);padding:10px 20px;margin:0}.ai-field-progress{display:flex;gap:15px;align-items:center;padding:10px 20px;font-size:12px}.ai-field-progress progress{flex:1;accent-color:var(--color-brand);height:5px}.ai-field{white-space:normal;border-bottom:1px solid var(--color-line);padding:0 0 12px;margin-bottom:12px}.ai-field p{white-space:pre-wrap;margin:4px 0}.ai-progress{border:1px solid var(--color-line);border-radius:18px;background:var(--color-surface-strong);overflow:hidden;margin:16px 0;grid-column:1 / -1}.ai-progress>header{display:flex;align-items:center;justify-content:space-between;gap:12px;padding:14px 20px;background:var(--color-bg)}header>span{display:flex;align-items:center;gap:10px;font-weight:600}.ai-progress__columns{display:grid;grid-template-columns:1fr 1.4fr;gap:1px;background:var(--color-line)}.ai-progress__columns>div{background:var(--color-surface-strong);padding:16px}h3{font-size:13px;margin:0 0 12px}small{font-weight:400;color:var(--color-muted);margin-left:8px}.ai-progress__scroll{height:200px;overflow:auto;white-space:pre-wrap;overflow-wrap:anywhere;font-size:13px;line-height:1.85;overscroll-behavior:contain}.form-error{padding:0 20px}@media(max-width:700px){.ai-progress__columns{grid-template-columns:1fr}.ai-progress__scroll{height:150px}}
</style>
