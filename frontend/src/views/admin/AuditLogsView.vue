<script setup lang="ts">
import { onMounted } from 'vue'
import { ShieldCheck } from 'lucide-vue-next'
import EmptyState from '@/components/ui/EmptyState.vue'
import ErrorState from '@/components/ui/ErrorState.vue'
import LoadingState from '@/components/ui/LoadingState.vue'
import { adminApi } from '@/api/admin'
import { useAsyncState } from '@/composables/useAsync'

const state = useAsyncState<{ items: Array<Record<string, unknown>> }>()
function load() {
  return state.run(() => adminApi.auditLogs())
}
onMounted(load)
</script>

<template>
  <div class="admin-page">
    <header class="admin-page-heading">
      <div><span class="eyebrow">Security trail</span><h1>审计日志</h1><p>登录、内容修改、文件删除、设置和数据清理操作记录。</p></div>
      <ShieldCheck :size="28" />
    </header>
    <LoadingState v-if="state.loading.value" :rows="8" />
    <ErrorState v-else-if="state.error.value" :message="state.error.value" @retry="load" />
    <EmptyState v-else-if="!state.data.value?.items.length" title="暂无审计记录" description="管理员执行操作后会自动记录。" />
    <div v-else class="admin-table-wrap">
      <table class="admin-table">
        <thead><tr><th>时间</th><th>操作</th><th>实体</th><th>实体 UUID</th><th>管理员</th><th>详情</th></tr></thead>
        <tbody>
          <tr v-for="item in state.data.value.items" :key="String(item.uuid)">
            <td data-label="时间">{{ new Date(String(item.created_at)).toLocaleString() }}</td>
            <td data-label="操作"><strong>{{ item.action }}</strong></td>
            <td data-label="实体">{{ item.entity_type || '—' }}</td>
            <td data-label="实体 UUID"><code>{{ item.entity_uuid || '—' }}</code></td>
            <td data-label="管理员"><code>{{ item.admin_user_uuid ? String(item.admin_user_uuid).slice(0, 8) : 'system' }}</code></td>
            <td data-label="详情"><code>{{ JSON.stringify(item.details) }}</code></td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

