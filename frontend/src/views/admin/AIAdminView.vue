<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { Bot, CheckCircle2, FileSearch, KeyRound, Languages, Play, Save } from 'lucide-vue-next'
import { adminApi } from '@/api/admin'
import BaseSelect from '@/components/ui/BaseSelect.vue'
import AssetPickerField from '@/components/admin/AssetPickerField.vue'
import ErrorState from '@/components/ui/ErrorState.vue'
import LoadingState from '@/components/ui/LoadingState.vue'
import { useToastStore } from '@/stores/toast'
import BatchTranslationModal from '@/components/admin/BatchTranslationModal.vue'
import { useAiTask } from '@/composables/useAiTask'
import AiProgressPanel from '@/components/admin/AiProgressPanel.vue'
import type { Asset } from '@/types'

const batch = ref<InstanceType<typeof BatchTranslationModal>>()
const toast = useToastStore()
const loading = ref(true)
const ai = useAiTask()
const running = computed(() => ai.state.running)
const error = ref('')
const models = ref<Array<{ id: string; owned_by: string }>>([])
const pdfAssets = ref<Asset[]>([])
const selectedResume = ref('')
const parsedResult = computed(() => ai.state.result)
const savingConfig = ref(false)
const fetchingModels = ref(false)
const applying = ref(false)
const applied = ref(false)
const config = reactive({ base_url: '', api_key: '', model: '', enabled: true, has_api_key: false, max_context_chars: 32000 })
const modelOptions = computed(() => {
  const options = models.value.map((item) => ({ value: item.id, label: item.id, description: item.owned_by }))
  if (config.model && !options.some((item) => item.value === config.model)) options.unshift({ value: config.model, label: config.model, description: '当前配置' })
  return options
})

async function load() {
  loading.value = true
  try {
    const [saved, assets] = await Promise.all([adminApi.aiConfig(), adminApi.allAssets({ category: 'documents' })])
    Object.assign(config, saved, { api_key: '' })
    pdfAssets.value = assets.items.filter((item) => item.mime_type === 'application/pdf')
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : 'AI 配置加载失败'
  } finally { loading.value = false }
}
async function fetchModels() {
  if (fetchingModels.value) return
  fetchingModels.value = true
  error.value = ''
  try {
    const result = await adminApi.aiModels({ base_url: config.base_url, api_key: config.api_key })
    models.value = result.items
    if (!config.model && models.value.length) config.model = models.value[0].id
    toast.show(`已读取 ${models.value.length} 个模型`, 'success')
  } catch (cause) { error.value = cause instanceof Error ? cause.message : '模型列表读取失败' }
  finally { fetchingModels.value = false }
}
async function saveConfig() {
  if (savingConfig.value) return
  if (!Number.isInteger(config.max_context_chars) || config.max_context_chars < 4000 || config.max_context_chars > 200000) { error.value = '上下文窗口需为 4,000 至 200,000 字符'; return }
  savingConfig.value = true
  try {
    await adminApi.updateAiConfig(config)
    config.has_api_key ||= Boolean(config.api_key)
    config.api_key = ''
    toast.show('AI 配置已保存', 'success')
  } catch (cause) { error.value = cause instanceof Error ? cause.message : '保存失败' }
  finally { savingConfig.value = false }
}
async function parseResume() {
  if (!selectedResume.value) return
  error.value = ''; applied.value = false
  try { await ai.run('resume/parse', { asset_uuid: selectedResume.value, source_locale: 'zh-CN' }) }
  catch (cause) { error.value = cause instanceof Error ? cause.message : '简历解析失败' }
}
async function applyResume() {
  if (!parsedResult.value || applying.value || applied.value) return
  applying.value = true
  try {
    const result = await adminApi.applyAiResume(parsedResult.value)
    applied.value = true
    toast.show(`已创建 ${result.projects_created} 个项目草稿、${result.certificates_created} 条证书草稿`, 'success')
  } catch (cause) { error.value = cause instanceof Error ? cause.message : '导入失败' }
  finally { applying.value = false }
}
onMounted(load)
</script>

<template>
  <BatchTranslationModal ref="batch" :default-context-chars="config.max_context_chars" />
  <div class="admin-page ai-admin-page">
    <header class="admin-page-heading"><div><span class="eyebrow">AI workspace</span><h1>AI 内容助手</h1><p>OpenAI 兼容接口、流式简历解析与双向结构化翻译。</p></div><button class="button button--dark" @click="batch?.open()"><Languages :size="17" />全系统翻译</button></header>
    <LoadingState v-if="loading" :rows="8" />
    <template v-else>
      <ErrorState v-if="error" :message="error" @retry="error = ''" />
      <section class="form-section">
        <div class="form-section__heading"><KeyRound :size="22" /><div><h2>模型配置</h2><p>API Key 加密保存在数据库中，接口不会回传明文。</p></div></div>
        <div class="form-grid">
          <label class="span-2">OpenAI 兼容 API URL<input v-model="config.base_url" type="url" placeholder="https://api.example.com/v1" /></label>
          <label class="span-2">API Key<input v-model="config.api_key" type="password" :placeholder="config.has_api_key ? '已保存；留空表示不更换' : 'sk-...'" autocomplete="new-password" /></label>
          <label class="span-2">模型<BaseSelect v-model="config.model" label="模型" :options="modelOptions" placeholder="先拉取模型列表" /></label>
          <label class="span-2">模型 ID<input v-model="config.model" placeholder="可手动填写服务商提供的模型 ID" /></label>
          <label class="span-2">最大输入上下文（字符）<input v-model.number="config.max_context_chars" type="number" min="4000" max="200000" step="1000" /><small>包含当前正文、提示词与参考译文。窗口滚动保留相关和最近完成的内容，自动移出较旧参考；字符数不是模型 token 数。</small></label>
          <label class="check-row"><input v-model="config.enabled" type="checkbox" />启用 AI 功能</label>
        </div>
        <div class="editor-actions"><button class="button button--outline" type="button" :disabled="fetchingModels" @click="fetchModels"><Bot :size="16" />拉取模型</button><button class="button button--dark" type="button" :disabled="savingConfig" @click="saveConfig"><Save :size="16" />保存配置</button></div>
      </section>
      <section class="form-section">
        <div class="form-section__heading"><FileSearch :size="22" /><div><h2>导入简历</h2><p>选择资源库中的 PDF，先流式解析并预览，确认后仅创建可编辑草稿。</p></div></div>
        <label>PDF 简历<AssetPickerField v-model="selectedResume" :assets="pdfAssets" accept="application/pdf" title="选择要解析的简历" /></label>
        <button class="button button--dark" type="button" :disabled="running || !selectedResume" @click="parseResume"><Play :size="16" />{{ running ? '正在流式解析…' : '开始解析' }}</button>
        <AiProgressPanel :task="ai.state" :body="ai.body.value" @cancel="ai.cancel" @close="ai.state.visible = false" />
        <div v-if="parsedResult" class="ai-result-panel">
          <div><CheckCircle2 :size="20" /><strong>结构化草稿已生成</strong></div>

          <button class="button button--dark" type="button" :disabled="applying || applied" @click="applyResume">{{ applied ? "已导入" : applying ? "导入中…" : "确认导入为草稿" }}</button>
        </div>
      </section>
      <section class="form-section ai-note"><Languages :size="22" /><div><h2>双向翻译</h2><p>在各内容编辑页使用 AI 翻译，生成后检查并保存。</p><div class="editor-actions"><RouterLink to="/admin/projects">项目内容</RouterLink><RouterLink to="/admin/settings">网站文案</RouterLink><RouterLink to="/admin/certificates">证书</RouterLink><RouterLink to="/admin/categories">分类</RouterLink><RouterLink to="/admin/tags">标签</RouterLink><RouterLink to="/admin/assets">附件信息</RouterLink></div></div></section>
    </template>
  </div>
</template>
