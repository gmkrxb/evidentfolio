<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { Award, Eye, FileBadge, Languages, Pencil, Plus, Trash2, X } from 'lucide-vue-next'
import EmptyState from '@/components/ui/EmptyState.vue'
import ErrorState from '@/components/ui/ErrorState.vue'
import LoadingState from '@/components/ui/LoadingState.vue'
import { adminApi } from '@/api/admin'
import { useAsyncState } from '@/composables/useAsync'
import { useToastStore } from '@/stores/toast'
import type { Asset, Certificate } from '@/types'
import IconPicker from '@/components/icons/IconPicker.vue'
import { certificateTypeLabel } from '@/utils/labels'
import { readSse } from '@/utils/sse'

const state = useAsyncState<{ items: Certificate[] }>()
const assets = ref<Asset[]>([])
const images = ref<Asset[]>([])
const editing = ref<Certificate | 'new' | null>(null)
const toast = useToastStore()
const editLocale = ref<'zh-CN' | 'en'>('zh-CN')
const translating = ref(false)
const form = reactive({
  name: '', issuer: '', certificate_type: 'competition', issued_at: '', description: '',
  credential_no: '', credential_url: '', asset_uuid: '', icon_asset_uuid: '', is_public: true, sort_order: 0,
  icon_name: '', icon_svg: '',
  translations: {} as Record<string, Record<string, string>>, content_language_mode: 'bilingual',
})
const english = reactive({ name: '', issuer: '', description: '' })

async function load() {
  await Promise.all([
    state.run(() => adminApi.certificates()),
    adminApi.assets({ page_size: 100 }).then((result) => {
      assets.value = result.items.filter((item) => item.mime_type === 'application/pdf' || item.mime_type.startsWith('image/'))
      images.value = result.items.filter((item) => item.mime_type.startsWith('image/'))
    }),
  ])
}
function open(item?: Certificate) {
  editing.value = item || 'new'
  Object.assign(form, item ? {
    name: item.name, issuer: item.issuer, certificate_type: item.certificate_type, issued_at: item.issued_at,
    description: item.description, credential_no: item.credential_no, credential_url: item.credential_url,
    asset_uuid: item.asset?.uuid || '', icon_asset_uuid: item.icon_asset?.uuid || '',
    icon_name: item.icon_name || '', icon_svg: item.icon_svg || '',
    is_public: item.is_public, sort_order: item.sort_order,
    translations: item.translations || {}, content_language_mode: item.content_language_mode || 'bilingual',
  } : {
    name: '', issuer: '', certificate_type: 'competition', issued_at: '', description: '',
    credential_no: '', credential_url: '', asset_uuid: '', icon_asset_uuid: '', icon_name: '', icon_svg: '', is_public: true, sort_order: 0,
    translations: {}, content_language_mode: 'bilingual',
  })
  Object.assign(english, form.translations.en || { name: '', issuer: '', description: '' })
}
async function save() {
  if (!editing.value) return
  const payload = {
    ...form,
    translations: { ...form.translations, en: { ...english } },
    asset_uuid: form.asset_uuid || null,
    icon_asset_uuid: form.icon_asset_uuid || null,
  }
  if (editing.value === 'new') await adminApi.createCertificate(payload)
  else await adminApi.updateCertificate(editing.value.uuid, payload)
  editing.value = null
  toast.show('证书已保存', 'success')
  await load()
}
async function translateCertificate() {
  translating.value = true
  try {
    const fromEnglish = editLocale.value === 'en'
    const content = fromEnglish ? english : { name: form.name, issuer: form.issuer, description: form.description }
    let result: Record<string, unknown> | null = null
    await readSse(await adminApi.aiStream('translate', { source_locale: fromEnglish ? 'en' : 'zh-CN', target_locale: fromEnglish ? 'zh-CN' : 'en', entity_type: 'certificate', content }), (event) => {
      if (event.type === 'result') result = event.data || null
    })
    if (!result) throw new Error('AI 未返回翻译结果')
    if (fromEnglish) Object.assign(form, result)
    else Object.assign(english, result)
    editLocale.value = fromEnglish ? 'zh-CN' : 'en'
    toast.show('翻译已生成，请检查后保存', 'success')
  } catch (cause) { toast.show(cause instanceof Error ? cause.message : '翻译失败', 'error') }
  finally { translating.value = false }
}
async function remove(item: Certificate) {
  if (!window.confirm(`确定删除“${item.name}”吗？关联项目存在时系统会阻止删除。`)) return
  try {
    await adminApi.deleteCertificate(item.uuid)
    toast.show('证书记录已删除', 'success')
    await load()
  } catch (cause) {
    toast.show(cause instanceof Error ? cause.message : '删除失败', 'error')
  }
}
onMounted(load)
</script>

<template>
  <div class="admin-page">
    <header class="admin-page-heading">
      <div><span class="eyebrow">Credentials</span><h1>证书与荣誉</h1><p>管理奖学金证书、竞赛获奖、专利和课程认证，并关联项目展示。</p></div>
      <button class="button button--dark" @click="open()"><Plus :size="17" />新建证书</button>
    </header>
    <div class="info-banner">证书扫描件或照片先上传到资源库；创建证书后，可在项目编辑页选择关联。</div>
    <LoadingState v-if="state.loading.value" :rows="8" />
    <ErrorState v-else-if="state.error.value" :message="state.error.value" @retry="load" />
    <EmptyState v-else-if="!state.data.value?.items.length" title="还没有证书记录" description="支持奖学金、竞赛、专利、课程认证和其他荣誉。" />
    <div v-else class="credential-admin-grid">
      <article v-for="item in state.data.value.items" :key="item.uuid">
        <div class="credential-admin-icon">
          <img v-if="item.icon_asset?.thumbnail_url" :src="item.icon_asset.thumbnail_url" alt="" />
          <FileBadge v-else :size="30" />
        </div>
        <div>
          <span class="eyebrow">{{ certificateTypeLabel(item.certificate_type) }} · {{ item.issued_at || '时间未填写' }}</span>
          <h2>{{ item.name }}</h2>
          <p>{{ item.issuer }} · {{ item.project_count }} 个关联项目 · {{ item.is_public ? '公开' : '私有' }}</p>
        </div>
        <RouterLink v-if="item.asset" :to="`/assets/${item.asset.uuid}`" target="_blank" title="预览"><Eye :size="17" /></RouterLink>
        <button class="icon-button" title="编辑" @click="open(item)"><Pencil :size="16" /></button>
        <button class="icon-button danger-text" title="删除" @click="remove(item)"><Trash2 :size="16" /></button>
      </article>
    </div>
    <Teleport to="body">
      <div v-if="editing" class="modal-backdrop" @click.self="editing = null">
        <form class="modal-card modal-card--large" @submit.prevent="save">
          <header><div><span class="eyebrow">Credential record</span><h2>{{ editing === 'new' ? '新建证书' : '编辑证书' }}</h2></div><button class="icon-button" type="button" @click="editing = null"><X :size="19" /></button></header>
          <div class="editor-language-bar">
            <div class="language-tabs"><button type="button" :class="{ active: editLocale === 'zh-CN' }" @click="editLocale = 'zh-CN'">中文</button><button type="button" :class="{ active: editLocale === 'en' }" @click="editLocale = 'en'">English</button></div>
            <label>内容语言<select v-model="form.content_language_mode"><option value="bilingual">中英双语</option><option value="single_zh">仅中文</option><option value="single_en">English only</option></select></label>
            <button type="button" class="button button--outline" :disabled="translating" @click="translateCertificate"><Languages :size="16" />{{ translating ? '翻译中…' : editLocale === 'en' ? '翻译为中文' : '翻译为英文' }}</button>
          </div>
          <div class="form-grid">
            <label class="span-2">{{ editLocale === 'en' ? 'Credential / honor name' : '证书 / 荣誉名称' }}<input v-if="editLocale === 'zh-CN'" v-model="form.name" required /><input v-else v-model="english.name" /></label>
            <label>{{ editLocale === 'en' ? 'Issuer' : '颁发机构' }}<input v-if="editLocale === 'zh-CN'" v-model="form.issuer" /><input v-else v-model="english.issuer" /></label>
            <label>颁发时间<input v-model="form.issued_at" placeholder="2025.06" /></label>
            <label>类型<select v-model="form.certificate_type"><option value="competition">竞赛获奖</option><option value="scholarship">奖学金</option><option value="patent">专利</option><option value="course">课程认证</option><option value="other">其他</option></select></label>
            <label>排序值<input v-model.number="form.sort_order" type="number" /></label>
            <label class="span-2">{{ editLocale === 'en' ? 'Description' : '说明' }}<textarea v-if="editLocale === 'zh-CN'" v-model="form.description" rows="4" /><textarea v-else v-model="english.description" rows="4" /></label>
            <label>证书编号<input v-model="form.credential_no" /></label>
            <label>验证地址<input v-model="form.credential_url" type="url" /></label>
            <label>证书文件 / 图片<select v-model="form.asset_uuid"><option value="">不关联文件</option><option v-for="asset in assets" :key="asset.uuid" :value="asset.uuid">{{ asset.display_name }}</option></select></label>
            <div class="span-2">
              <IconPicker
                v-model:icon-name="form.icon_name"
                v-model:icon-svg="form.icon_svg"
                v-model:image-uuid="form.icon_asset_uuid"
                :assets="images"
              />
            </div>
          </div>
          <label class="check-label"><input v-model="form.is_public" type="checkbox" />允许公开展示</label>
          <footer><button type="button" class="button button--outline" @click="editing = null">取消</button><button class="button button--dark">保存证书</button></footer>
        </form>
      </div>
    </Teleport>
  </div>
</template>
