<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { Pencil, Plus, Trash2, X } from 'lucide-vue-next'
import EmptyState from '@/components/ui/EmptyState.vue'
import ErrorState from '@/components/ui/ErrorState.vue'
import LoadingState from '@/components/ui/LoadingState.vue'
import { adminApi } from '@/api/admin'
import { useAsyncState } from '@/composables/useAsync'
import { useToastStore } from '@/stores/toast'
import type { TaxonomyItem } from '@/types'

const props = defineProps<{ mode: 'categories' | 'tags' }>()
const state = useAsyncState<{ items: TaxonomyItem[] }>()
const toast = useToastStore()
const editing = ref<TaxonomyItem | 'new' | null>(null)
const form = reactive({ name: '', slug: '', description: '', sort_order: 0, color: '#315b4f', translations: {} as Record<string, Record<string, string>> })
const editLocale = ref<'zh-CN' | 'en'>('zh-CN')
const english = reactive({ name: '', description: '' })
const title = computed(() => props.mode === 'categories' ? '项目分类' : '技术标签')
const description = computed(() => props.mode === 'categories' ? '控制项目分类入口与显示顺序。' : '维护可组合筛选的技术标签与视觉颜色。')

async function load() {
  await state.run(() => props.mode === 'categories' ? adminApi.categories() : adminApi.tags())
}
function open(item?: TaxonomyItem) {
  editing.value = item || 'new'
  Object.assign(form, item ? { ...item, description: item.description || '', sort_order: item.sort_order || 0, color: item.color || '#315b4f', translations: item.translations || {} } : { name: '', slug: '', description: '', sort_order: 0, color: '#315b4f', translations: {} })
  Object.assign(english, form.translations.en || { name: '', description: '' })
}
async function save() {
  if (!editing.value) return
  const current = editing.value
  form.translations = { ...form.translations, en: { ...english } }
  if (current === 'new') {
    if (props.mode === 'categories') await adminApi.createCategory(form)
    else await adminApi.createTag(form)
  } else {
    if (props.mode === 'categories') await adminApi.updateCategory(current.uuid, form)
    else await adminApi.updateTag(current.uuid, form)
  }
  editing.value = null
  toast.show(`${props.mode === 'categories' ? '分类' : '标签'}已保存`, 'success')
  await load()
}
async function remove(item: TaxonomyItem) {
  if (!window.confirm(`确定删除“${item.name}”吗？有关联项目时系统会阻止删除。`)) return
  try {
    if (props.mode === 'categories') await adminApi.deleteCategory(item.uuid)
    else await adminApi.deleteTag(item.uuid)
    toast.show('已删除', 'success')
    await load()
  } catch (cause) {
    toast.show(cause instanceof Error ? cause.message : '删除失败', 'error')
  }
}
watch(() => props.mode, load)
onMounted(load)
</script>

<template>
  <div class="admin-page">
    <header class="admin-page-heading">
      <div><span class="eyebrow">Taxonomy</span><h1>{{ title }}</h1><p>{{ description }}</p></div>
      <button class="button button--dark" @click="open()"><Plus :size="17" />新建{{ mode === 'categories' ? '分类' : '标签' }}</button>
    </header>
    <LoadingState v-if="state.loading.value" :rows="7" />
    <ErrorState v-else-if="state.error.value" :message="state.error.value" @retry="load" />
    <EmptyState v-else-if="!state.data.value?.items.length" :title="`还没有${title}`" description="创建后即可在项目编辑和公开筛选中使用。" />
    <div v-else class="taxonomy-list">
      <article v-for="item in state.data.value.items" :key="item.uuid">
        <span v-if="mode === 'tags'" class="taxonomy-color" :style="{ backgroundColor: item.color }" />
        <div><strong>{{ item.name }}</strong><small>{{ item.slug }}</small></div>
        <p v-if="mode === 'categories'">{{ item.description || '暂无说明' }}</p>
        <span>{{ item.project_count || 0 }} 个关联项目</span>
        <span v-if="mode === 'categories'">排序 {{ item.sort_order || 0 }}</span>
        <button class="icon-button" aria-label="编辑" @click="open(item)"><Pencil :size="16" /></button>
        <button class="icon-button danger-text" aria-label="删除" @click="remove(item)"><Trash2 :size="16" /></button>
      </article>
    </div>
    <Teleport to="body">
      <div v-if="editing" class="modal-backdrop" @click.self="editing = null">
        <form class="modal-card" @submit.prevent="save">
          <header><div><span class="eyebrow">Taxonomy item</span><h2>{{ editing === 'new' ? '新建' : '编辑' }}{{ mode === 'categories' ? '分类' : '标签' }}</h2></div><button class="icon-button" type="button" @click="editing = null"><X :size="19" /></button></header>
          <div class="language-tabs"><button type="button" :class="{ active: editLocale === 'zh-CN' }" @click="editLocale = 'zh-CN'">中文</button><button type="button" :class="{ active: editLocale === 'en' }" @click="editLocale = 'en'">English</button></div>
          <label>{{ editLocale === 'en' ? 'Name' : '名称' }}<input v-if="editLocale === 'zh-CN'" v-model="form.name" required /><input v-else v-model="english.name" /></label>
          <label>URL 标识<input v-model="form.slug" placeholder="留空自动生成" /></label>
          <template v-if="mode === 'categories'">
            <label>{{ editLocale === 'en' ? 'Description' : '说明' }}<textarea v-if="editLocale === 'zh-CN'" v-model="form.description" rows="4" /><textarea v-else v-model="english.description" rows="4" /></label>
            <label>排序值<input v-model.number="form.sort_order" type="number" /></label>
          </template>
          <label v-else>视觉颜色<input v-model="form.color" type="color" /></label>
          <footer><button type="button" class="button button--outline" @click="editing = null">取消</button><button class="button button--dark">保存</button></footer>
        </form>
      </div>
    </Teleport>
  </div>
</template>
