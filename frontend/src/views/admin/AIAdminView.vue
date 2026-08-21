<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { Bot, CheckCircle2, FileSearch, KeyRound, Languages, Play, Save } from 'lucide-vue-next'
import { adminApi } from '@/api/admin'
import BaseSelect from '@/components/ui/BaseSelect.vue'
import ErrorState from '@/components/ui/ErrorState.vue'
import LoadingState from '@/components/ui/LoadingState.vue'
import { useToastStore } from '@/stores/toast'
import type { Asset } from '@/types'

const toast = useToastStore()
const loading = ref(true)
const running = ref(false)
const error = ref('')
const models = ref<Array<{ id: string; owned_by: string }>>([])
const pdfAssets = ref<Asset[]>([])
const selectedResume = ref('')
const streamText = ref('')
const reasoningText = ref('')
const parsedResult = ref<Record<string, unknown> | null>(null)
const config = reactive({ base_url: '', api_key: '', model: '', enabled: true, has_api_key: false })
const modelOptions = computed(() => models.value.map((item) => ({ value: item.id, label: item.id, description: item.owned_by })))
const resumeOptions = computed(() => pdfAssets.value.map((item) => ({ value: item.uuid, label: item.display_name, description: `${Math.ceil(item.size / 1024)} KB` })))

async function load() {
  loading.value = true
  try {
    const [saved, assets] = await Promise.all([adminApi.aiConfig(), adminApi.assets({ category: 'documents', page_size: 1000 })])
    Object.assign(config, saved, { api_key: '' })
    pdfAssets.value = assets.items.filter((item) => item.mime_type === 'application/pdf')
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : 'AI 配置加载失败'
  } finally { loading.value = false }
}
async function fetchModels() {
  error.value = ''
  try {
    const result = await adminApi.aiModels({ base_url: config.base_url, api_key: config.api_key })
    models.value = result.items
    if (!config.model && models.value.length) config.model = models.value[0].id
    toast.show(`已读取 ${models.value.length} 个模型`, 'success')
  } catch (cause) { error.value = cause instanceof Error ? cause.message : '模型列表读取失败' }
}
async function saveConfig() {
  try {
    await adminApi.updateAiConfig(config)
    config.has_api_key ||= Boolean(config.api_key)
    config.api_key = ''
    toast.show('AI 配置已保存', 'success')
  } catch (cause) { error.value = cause instanceof Error ? cause.message : '保存失败' }
}
async function consume(response: Response) {
  const reader = response.body?.getReader()
  if (!reader) throw new Error('浏览器不支持流式读取')
  const decoder = new TextDecoder()
  let buffer = ''
  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    const events = buffer.split('\n\n')
    buffer = events.pop() || ''
    for (const event of events) {
      const line = event.split('\n').find((item) => item.startsWith('data:'))
      if (!line) continue
      const payload = JSON.parse(line.slice(5).trim()) as { type: string; content?: string; message?: string; data?: Record<string, unknown> }
      if (payload.type === 'reasoning') reasoningText.value += payload.content || ''
      if (payload.type === 'content') streamText.value += payload.content || ''
      if (payload.type === 'result') parsedResult.value = payload.data || null
      if (payload.type === 'error') throw new Error(payload.message || 'AI 处理失败')
    }
  }
}
async function parseResume() {
  if (!selectedResume.value) return
  running.value = true; error.value = ''; streamText.value = ''; reasoningText.value = ''; parsedResult.value = null
  try { await consume(await adminApi.aiStream('resume/parse', { asset_uuid: selectedResume.value, source_locale: 'zh-CN' })) }
  catch (cause) { error.value = cause instanceof Error ? cause.message : '简历解析失败' }
  finally { running.value = false }
}
async function applyResume() {
  if (!parsedResult.value) return
  try {
    const result = await adminApi.applyAiResume(parsedResult.value)
    toast.show(`已创建 ${result.projects_created} 个项目草稿、${result.certificates_created} 条证书草稿`, 'success')
  } catch (cause) { error.value = cause instanceof Error ? cause.message : '导入失败' }
}
onMounted(load)
</script>

<template>
  <div class="admin-page ai-admin-page">
    <header class="admin-page-heading"><div><span class="eyebrow">AI workspace</span><h1>AI 内容助手</h1><p>OpenAI 兼容接口、流式简历解析与双向结构化翻译。</p></div></header>
    <LoadingState v-if="loading" :rows="8" />
    <template v-else>
      <ErrorState v-if="error" :message="error" @retry="error = ''" />
      <section class="form-section">
        <div class="form-section__heading"><KeyRound :size="22" /><div><h2>模型配置</h2><p>API Key 加密保存在数据库中，接口不会回传明文。</p></div></div>
        <div class="form-grid">
          <label class="span-2">OpenAI 兼容 API URL<input v-model="config.base_url" type="url" placeholder="https://api.example.com/v1" /></label>
          <label class="span-2">API Key<input v-model="config.api_key" type="password" :placeholder="config.has_api_key ? '已保存；留空表示不更换' : 'sk-...'" autocomplete="new-password" /></label>
          <label class="span-2">模型<BaseSelect v-model="config.model" label="模型" :options="modelOptions" placeholder="先拉取模型列表" /></label>
          <label class="check-row"><input v-model="config.enabled" type="checkbox" />启用 AI 功能</label>
        </div>
        <div class="editor-actions"><button class="button button--outline" type="button" @click="fetchModels"><Bot :size="16" />拉取模型</button><button class="button button--dark" type="button" @click="saveConfig"><Save :size="16" />保存配置</button></div>
      </section>
      <section class="form-section">
        <div class="form-section__heading"><FileSearch :size="22" /><div><h2>导入简历</h2><p>选择资源库中的 PDF，先流式解析并预览，确认后仅创建可编辑草稿。</p></div></div>
        <BaseSelect v-model="selectedResume" label="PDF 简历" :options="resumeOptions" placeholder="选择一份 PDF 简历" />
        <button class="button button--dark" type="button" :disabled="running || !selectedResume" @click="parseResume"><Play :size="16" />{{ running ? '正在流式解析…' : '开始解析' }}</button>
        <div v-if="running || streamText" class="ai-stream-panel">
          <div><span>模型输出</span><strong>{{ streamText.length }} 字符</strong></div>
          <pre>{{ streamText || '等待模型输出…' }}</pre>
          <details v-if="reasoningText"><summary>模型思考过程</summary><pre>{{ reasoningText }}</pre></details>
        </div>
        <div v-if="parsedResult" class="ai-result-panel">
          <div><CheckCircle2 :size="20" /><strong>结构化草稿已生成</strong></div>
          <pre>{{ JSON.stringify(parsedResult, null, 2) }}</pre>
          <button class="button button--dark" type="button" @click="applyResume">确认导入为草稿</button>
        </div>
      </section>
      <section class="form-section ai-note"><Languages :size="22" /><div><h2>双向翻译</h2><p>项目编辑器中的“AI 翻译”会使用同一模型，保留 Markdown、指标、链接与字段结构。</p></div></section>
    </template>
  </div>
</template>
