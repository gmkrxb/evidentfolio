<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { Activity, ArrowUpRight, BriefcaseBusiness, Eye, FileText, FolderArchive, UsersRound } from 'lucide-vue-next'
import LoadingState from '@/components/ui/LoadingState.vue'
import ErrorState from '@/components/ui/ErrorState.vue'
import { adminApi } from '@/api/admin'
import { useAsyncState } from '@/composables/useAsync'

const state = useAsyncState<Record<string, unknown>>()
const analytics = computed(() => (state.data.value?.analytics || {}) as Record<string, unknown>)
const eventCounts = computed(() => (analytics.value.event_counts || {}) as Record<string, number>)
const stats = computed(() => [
  { label: '项目总数', value: Number(state.data.value?.projects || 0), icon: BriefcaseBusiness, link: '/admin/projects' },
  { label: '公开项目', value: Number(state.data.value?.published_projects || 0), icon: Eye, link: '/admin/projects?status=published' },
  { label: '资源文件', value: Number(state.data.value?.assets || 0), icon: FolderArchive, link: '/admin/assets' },
  { label: '简历版本', value: Number(state.data.value?.resumes || 0), icon: FileText, link: '/admin/resumes' },
])
const engagement = computed(() => [
  { label: '总页面访问', value: Number(analytics.value.total_views || 0) },
  { label: '独立访客', value: Number(analytics.value.unique_visitors || 0) },
  { label: '回访访客', value: Number(analytics.value.returning_visitors || 0) },
  { label: '项目查看', value: Number(eventCounts.value.project_view || 0) },
  { label: '简历查看', value: Number(eventCounts.value.resume_view || 0) },
  { label: '简历下载', value: Number(eventCounts.value.resume_download || 0) },
])
const trend = computed(() => (analytics.value.trend || []) as Array<{ date: string; views: number }>)
const maxTrend = computed(() => Math.max(...trend.value.map((item) => item.views), 1))

function load() {
  return state.run(() => adminApi.dashboard())
}
onMounted(load)
</script>

<template>
  <div class="admin-page">
    <header class="admin-page-heading">
      <div><span class="eyebrow">Overview</span><h1>作品集总览</h1><p>内容状态与访问关注信号，集中在一个页面。</p></div>
      <RouterLink class="button button--dark" to="/admin/projects/new">新建项目 <ArrowUpRight :size="17" /></RouterLink>
    </header>
    <LoadingState v-if="state.loading.value" :rows="8" />
    <ErrorState v-else-if="state.error.value" :message="state.error.value" @retry="load" />
    <template v-else-if="state.data.value">
      <section class="admin-stat-grid">
        <RouterLink v-for="item in stats" :key="item.label" :to="item.link" class="admin-stat">
          <component :is="item.icon" :size="20" />
          <span>{{ item.label }}</span>
          <strong>{{ item.value }}</strong>
          <ArrowUpRight :size="16" />
        </RouterLink>
      </section>
      <div class="dashboard-grid">
        <section class="admin-panel admin-panel--wide">
          <div class="admin-panel__heading">
            <div><span class="eyebrow">Last 30 days</span><h2>访问趋势</h2></div>
            <RouterLink to="/admin/analytics">查看完整分析</RouterLink>
          </div>
          <div v-if="trend.length" class="trend-chart">
            <div v-for="item in trend" :key="item.date" class="trend-bar">
              <span :style="{ height: `${Math.max(5, (item.views / maxTrend) * 100)}%` }" />
              <small>{{ item.date.slice(5) }}</small>
              <em>{{ item.views }}</em>
            </div>
          </div>
          <div v-else class="chart-empty">还没有访问趋势数据</div>
        </section>
        <section class="admin-panel">
          <div class="admin-panel__heading"><div><span class="eyebrow">Signals</span><h2>关注行为</h2></div><Activity :size="20" /></div>
          <dl class="metric-list">
            <div v-for="item in engagement" :key="item.label"><dt>{{ item.label }}</dt><dd>{{ item.value }}</dd></div>
          </dl>
        </section>
        <section class="admin-panel">
          <div class="admin-panel__heading"><div><span class="eyebrow">Today</span><h2>今日摘要</h2></div><UsersRound :size="20" /></div>
          <div class="today-metric"><strong>{{ Number(analytics.today_views || 0) }}</strong><span>页面访问</span></div>
          <p class="panel-note">访问分析只生成匿名的关注度信号，不识别访客真实身份，也不推断录用意向。</p>
        </section>
      </div>
    </template>
  </div>
</template>

