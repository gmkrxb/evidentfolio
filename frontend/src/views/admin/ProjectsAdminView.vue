<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { Copy, Eye, MoreHorizontal, Plus, Search, Trash2 } from 'lucide-vue-next'
import EmptyState from '@/components/ui/EmptyState.vue'
import ErrorState from '@/components/ui/ErrorState.vue'
import LoadingState from '@/components/ui/LoadingState.vue'
import { adminApi } from '@/api/admin'
import { useAsyncState } from '@/composables/useAsync'
import { useToastStore } from '@/stores/toast'
import type { Project } from '@/types'
import { projectStatusLabel } from '@/utils/labels'

const state = useAsyncState<{ items: Project[]; pagination: { total: number } }>()
const toast = useToastStore()
const q = ref('')
const status = ref('')
const selected = ref<string[]>([])
const allSelected = computed(() => Boolean(state.data.value?.items.length) && selected.value.length === state.data.value?.items.length)

async function load() {
  await state.run(() => adminApi.projects({ q: q.value || undefined, status: status.value || undefined, page_size: 100 }))
  selected.value = []
}
function toggleAll() {
  selected.value = allSelected.value ? [] : state.data.value?.items.map((item) => item.uuid) || []
}
async function duplicate(item: Project) {
  await adminApi.duplicateProject(item.uuid)
  toast.show('项目副本已创建', 'success')
  await load()
}
async function remove(item: Project) {
  if (!window.confirm(`确定删除“${item.title}”吗？此操作会写入审计日志。`)) return
  await adminApi.deleteProject(item.uuid)
  toast.show('项目已删除', 'success')
  await load()
}
async function batch(action: string) {
  if (!selected.value.length) return
  if (action === 'delete' && !window.confirm(`确定删除选中的 ${selected.value.length} 个项目吗？`)) return
  await adminApi.batchProjects(selected.value, action)
  toast.show('批量操作已完成', 'success')
  await load()
}
onMounted(load)
</script>

<template>
  <div class="admin-page">
    <header class="admin-page-heading">
      <div><span class="eyebrow">Content</span><h1>项目管理</h1><p>编辑、发布、复制、归档和批量维护项目。</p></div>
      <RouterLink class="button button--dark" to="/admin/projects/new"><Plus :size="17" />新建项目</RouterLink>
    </header>
    <div class="admin-toolbar">
      <label class="search-field"><Search :size="17" /><span class="sr-only">搜索项目</span><input v-model="q" placeholder="搜索项目" @keyup.enter="load" /></label>
      <select v-model="status" aria-label="项目状态" @change="load">
        <option value="">全部状态</option><option value="draft">草稿</option><option value="published">已发布</option><option value="hidden">隐藏</option><option value="archived">归档</option>
      </select>
      <button class="button button--outline button--small" @click="load">查询</button>
      <div v-if="selected.length" class="batch-actions">
        <span>已选 {{ selected.length }} 项</span>
        <button @click="batch('published')">发布</button>
        <button @click="batch('draft')">转草稿</button>
        <button @click="batch('archived')">归档</button>
        <button class="danger-text" @click="batch('delete')">删除</button>
      </div>
    </div>
    <LoadingState v-if="state.loading.value" :rows="8" />
    <ErrorState v-else-if="state.error.value" :message="state.error.value" @retry="load" />
    <EmptyState v-else-if="!state.data.value?.items.length" title="还没有项目" description="创建第一个项目，公开端会在发布后自动显示。">
      <RouterLink class="button button--dark button--small" to="/admin/projects/new">新建项目</RouterLink>
    </EmptyState>
    <div v-else class="admin-table-wrap">
      <table class="admin-table">
        <thead><tr><th><input type="checkbox" :checked="allSelected" aria-label="全选" @change="toggleAll" /></th><th>项目</th><th>分类</th><th>状态</th><th>时间</th><th>排序</th><th class="table-actions">操作</th></tr></thead>
        <tbody>
          <tr v-for="item in state.data.value.items" :key="item.uuid">
            <td><input v-model="selected" type="checkbox" :value="item.uuid" :aria-label="`选择${item.title}`" /></td>
            <td data-label="项目"><strong>{{ item.title }}</strong><small>{{ item.role }}</small></td>
            <td data-label="分类">{{ item.category?.name || '未分类' }}</td>
            <td data-label="状态"><span class="status-pill" :class="`status-pill--${item.status}`">{{ projectStatusLabel(item.status) }}</span></td>
            <td data-label="时间">{{ item.start_date }} — {{ item.end_date }}</td>
            <td data-label="排序">{{ item.sort_order }}</td>
            <td class="table-actions" data-label="操作">
              <RouterLink :to="`/projects/${item.uuid}`" target="_blank" title="预览"><Eye :size="17" /></RouterLink>
              <button title="复制" @click="duplicate(item)"><Copy :size="17" /></button>
              <RouterLink :to="`/admin/projects/${item.uuid}`" title="编辑"><MoreHorizontal :size="19" /></RouterLink>
              <button class="danger-text" title="删除" @click="remove(item)"><Trash2 :size="17" /></button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>
