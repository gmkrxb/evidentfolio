<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { Download, Eye, FilePlus2, Pencil, Star, Trash2, X } from 'lucide-vue-next'
import EmptyState from '@/components/ui/EmptyState.vue'
import ErrorState from '@/components/ui/ErrorState.vue'
import LoadingState from '@/components/ui/LoadingState.vue'
import { adminApi } from '@/api/admin'
import { useAsyncState } from '@/composables/useAsync'
import { useToastStore } from '@/stores/toast'
import type { Asset, ResumeVersion } from '@/types'
import { languageLabel, resumeTypeLabel } from '@/utils/labels'

const state = useAsyncState<{ items: ResumeVersion[] }>()
const assets = ref<Asset[]>([])
const toast = useToastStore()
const editing = ref<ResumeVersion | 'new' | null>(null)
const form = reactive({
  name: '', language: 'zh-CN', resume_type: 'technical', asset_uuid: '', is_default: false, is_public: true, version: '1.0',
})

async function load() {
  await Promise.all([
    state.run(() => adminApi.resumes()),
    adminApi.assets({ page_size: 100 }).then((result) => (assets.value = result.items.filter((item) => item.mime_type === 'application/pdf'))),
  ])
}
function open(item?: ResumeVersion) {
  editing.value = item || 'new'
  Object.assign(form, item ? {
    name: item.name, language: item.language, resume_type: item.resume_type, asset_uuid: item.asset.uuid,
    is_default: item.is_default, is_public: item.is_public, version: item.version,
  } : { name: '', language: 'zh-CN', resume_type: 'technical', asset_uuid: '', is_default: false, is_public: true, version: '1.0' })
}
async function save() {
  if (!editing.value) return
  if (editing.value === 'new') await adminApi.createResume(form)
  else await adminApi.updateResume(editing.value.uuid, form)
  editing.value = null
  toast.show('简历版本已保存', 'success')
  await load()
}
async function remove(item: ResumeVersion) {
  if (!window.confirm(`删除简历版本“${item.name}”？原始 PDF 资源会保留。`)) return
  await adminApi.deleteResume(item.uuid)
  toast.show('简历版本已删除', 'success')
  await load()
}
onMounted(load)
</script>

<template>
  <div class="admin-page">
    <header class="admin-page-heading">
      <div><span class="eyebrow">Resume versions</span><h1>简历管理</h1><p>维护多个语言和方向版本，控制默认与公开状态。</p></div>
      <button class="button button--dark" @click="open()"><FilePlus2 :size="17" />创建简历版本</button>
    </header>
    <div class="info-banner">请先在资源库上传 PDF，再在此创建简历版本；替换 PDF 时可以创建新版本并保留历史记录。</div>
    <LoadingState v-if="state.loading.value" :rows="7" />
    <ErrorState v-else-if="state.error.value" :message="state.error.value" @retry="load" />
    <EmptyState v-else-if="!state.data.value?.items.length" title="还没有简历版本" description="上传 PDF 后创建中文、英文、学术或技术简历。">
      <RouterLink class="button button--outline button--small" to="/admin/assets">前往资源库</RouterLink>
    </EmptyState>
    <div v-else class="resume-admin-grid">
      <article v-for="item in state.data.value.items" :key="item.uuid">
        <div class="resume-admin-preview">
          <img v-if="item.asset.thumbnail_url" :src="item.asset.thumbnail_url" :alt="`${item.name} 预览`" />
          <Star v-if="item.is_default" class="resume-default-star" :size="20" fill="currentColor" />
        </div>
        <div>
          <span class="eyebrow">{{ languageLabel(item.language) }} · {{ resumeTypeLabel(item.resume_type) }}</span>
          <h2>{{ item.name }}</h2>
          <p>版本 {{ item.version }} · {{ item.is_public ? '公开' : '私有' }}</p>
          <dl><div><dt>查看</dt><dd>{{ item.view_count }}</dd></div><div><dt>下载</dt><dd>{{ item.download_count }}</dd></div></dl>
          <div class="card-actions">
            <RouterLink :to="`/assets/${item.asset.uuid}`" target="_blank"><Eye :size="16" />预览</RouterLink>
            <a :href="item.asset.download_url"><Download :size="16" />下载</a>
            <button @click="open(item)"><Pencil :size="16" />编辑</button>
            <button class="danger-text" @click="remove(item)"><Trash2 :size="16" />删除</button>
          </div>
        </div>
      </article>
    </div>
    <Teleport to="body">
      <div v-if="editing" class="modal-backdrop" @click.self="editing = null">
        <form class="modal-card" @submit.prevent="save">
          <header><div><span class="eyebrow">Resume version</span><h2>{{ editing === 'new' ? '创建版本' : '编辑版本' }}</h2></div><button class="icon-button" type="button" aria-label="关闭" @click="editing = null"><X :size="19" /></button></header>
          <label>版本名称<input v-model="form.name" required placeholder="大模型算法实习简历" /></label>
          <div class="form-grid">
            <label>语言<select v-model="form.language"><option value="zh-CN">中文</option><option value="en">English</option></select></label>
            <label>类型<select v-model="form.resume_type"><option value="technical">技术简历</option><option value="academic">学术简历</option><option value="general">通用简历</option></select></label>
          </div>
          <label>PDF 资源<select v-model="form.asset_uuid" required><option value="" disabled>请选择 PDF</option><option v-for="asset in assets" :key="asset.uuid" :value="asset.uuid">{{ asset.display_name }}</option></select></label>
          <label>版本号<input v-model="form.version" required /></label>
          <label class="check-label"><input v-model="form.is_default" type="checkbox" />设为默认简历</label>
          <label class="check-label"><input v-model="form.is_public" type="checkbox" />允许公开查看和下载</label>
          <footer><button type="button" class="button button--outline" @click="editing = null">取消</button><button class="button button--dark">保存</button></footer>
        </form>
      </div>
    </Teleport>
  </div>
</template>
