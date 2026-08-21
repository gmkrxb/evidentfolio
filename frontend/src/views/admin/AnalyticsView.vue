<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { Activity, Clock3, Eye, FileDown, GitBranch, Monitor, MousePointerClick, Play, RotateCcw, Search, UsersRound, X } from 'lucide-vue-next'
import ErrorState from '@/components/ui/ErrorState.vue'
import LoadingState from '@/components/ui/LoadingState.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import { adminApi } from '@/api/admin'
import { useAsyncState } from '@/composables/useAsync'
import { useToastStore } from '@/stores/toast'

const overviewState = useAsyncState<Record<string, unknown>>()
const visitorState = useAsyncState<{ items: Array<Record<string, unknown>> }>()
const sessionState = useAsyncState<Record<string, unknown>>()
const toast = useToastStore()
const selectedSession = ref<string | null>(null)
const eventCounts = computed(() => (overviewState.data.value?.event_counts || {}) as Record<string, number>)
const stats = computed(() => [
  { label: '今日访问', value: Number(overviewState.data.value?.today_views || 0), icon: Activity },
  { label: '总访问量', value: Number(overviewState.data.value?.total_views || 0), icon: Eye },
  { label: '独立访客', value: Number(overviewState.data.value?.unique_visitors || 0), icon: UsersRound },
  { label: '回访访客', value: Number(overviewState.data.value?.returning_visitors || 0), icon: RotateCcw },
  { label: '简历下载', value: Number(eventCounts.value.resume_download || 0), icon: FileDown },
  { label: '代码仓库点击', value: Number(eventCounts.value.repository_click || 0), icon: GitBranch },
  { label: '在线演示点击', value: Number(eventCounts.value.demo_click || 0), icon: MousePointerClick },
  { label: '视频播放', value: Number(eventCounts.value.video_start || 0), icon: Play },
])
const trend = computed(() => (overviewState.data.value?.trend || []) as Array<{ date: string; views: number }>)
const maxTrend = computed(() => Math.max(...trend.value.map((item) => item.views), 1))
const distributions = computed(() => (overviewState.data.value?.distributions || {}) as Record<string, Array<{ name: string; value: number }>>)
const projectRanking = computed(() => (overviewState.data.value?.project_ranking || []) as Array<{ project_uuid: string; project_title: string; views: number }>)
const sessionDetails = computed(() => sessionState.data.value as { session?: Record<string, unknown>; events?: Array<Record<string, unknown>> } | null)

async function load() {
  await Promise.all([
    overviewState.run(() => adminApi.analyticsOverview()),
    visitorState.run(() => adminApi.visitors()),
  ])
}
async function openSession(uuid: string) {
  selectedSession.value = uuid
  await sessionState.run(() => adminApi.session(uuid))
}
async function cleanup() {
  const value = window.prompt('删除多少天以前的分析数据？', '365')
  if (value === null) return
  const days = Number(value)
  if (!Number.isFinite(days) || days < 0 || !window.confirm(`确定删除 ${days} 天以前的匿名访问数据吗？`)) return
  await adminApi.cleanupAnalytics(days)
  toast.show('历史分析数据已清理', 'success')
  await load()
}
function eventLabel(value: unknown) {
  const labels: Record<string, string> = {
    page_view: '页面访问', home_view: '首页访问', project_list_view: '项目列表',
    project_view: '查看项目', project_dwell: '项目停留', image_view: '查看图片',
    video_start: '播放视频', video_progress: '视频进度', document_preview: '预览文档',
    document_download: '下载文档', resume_view: '查看简历', resume_download: '下载简历',
    demo_click: '打开演示', repository_click: '打开代码仓库', contact_click: '点击联系',
    filter_use: '使用筛选', search: '搜索', page_exit: '离开页面',
  }
  return labels[String(value)] || String(value)
}
function deviceLabel(value: unknown) {
  const labels: Record<string, string> = {
    desktop: '桌面电脑',
    mobile: '手机',
    tablet: '平板电脑',
    bot: '自动程序',
    unknown: '未知设备',
  }
  return labels[String(value).toLowerCase()] || String(value || '未知设备')
}
onMounted(load)
</script>

<template>
  <div class="admin-page">
    <header class="admin-page-heading">
      <div><span class="eyebrow">Privacy-aware signals</span><h1>访问分析</h1><p>用匿名行为信号理解项目关注点，不识别访客身份，不推断录用意向。</p></div>
      <button class="button button--outline" @click="cleanup">清理历史数据</button>
    </header>
    <LoadingState v-if="overviewState.loading.value" :rows="8" />
    <ErrorState v-else-if="overviewState.error.value" :message="overviewState.error.value" @retry="load" />
    <template v-else>
      <section class="analytics-stat-grid">
        <article v-for="item in stats" :key="item.label"><component :is="item.icon" :size="19" /><span>{{ item.label }}</span><strong>{{ item.value }}</strong></article>
      </section>
      <div class="analytics-grid">
        <section class="admin-panel admin-panel--wide">
          <div class="admin-panel__heading"><div><span class="eyebrow">Timeline</span><h2>30 天访问趋势</h2></div></div>
          <div v-if="trend.length" class="trend-chart trend-chart--large">
            <div v-for="item in trend" :key="item.date" class="trend-bar">
              <span :style="{ height: `${Math.max(4, (item.views / maxTrend) * 100)}%` }" /><small>{{ item.date.slice(5) }}</small><em>{{ item.views }}</em>
            </div>
          </div>
          <div v-else class="chart-empty">暂无趋势数据</div>
        </section>
        <section class="admin-panel">
          <div class="admin-panel__heading"><div><span class="eyebrow">Projects</span><h2>项目访问排行</h2></div></div>
          <ol v-if="projectRanking.length" class="ranking-list">
            <li v-for="item in projectRanking" :key="item.project_uuid">
              <span><b>{{ item.project_title }}</b><small>{{ item.project_uuid.slice(0, 8) }}</small></span>
              <strong>{{ item.views }}</strong>
            </li>
          </ol>
          <div v-else class="chart-empty">暂无项目查看数据</div>
        </section>
        <section class="admin-panel">
          <div class="admin-panel__heading"><div><span class="eyebrow">Devices</span><h2>设备分布</h2></div><Monitor :size="20" /></div>
          <div class="distribution-list">
            <div v-for="item in distributions.devices || []" :key="item.name"><span>{{ deviceLabel(item.name) }}</span><strong>{{ item.value }}</strong></div>
          </div>
        </section>
        <section class="admin-panel">
          <div class="admin-panel__heading"><div><span class="eyebrow">Browsers</span><h2>浏览器分布</h2></div></div>
          <div class="distribution-list">
            <div v-for="item in distributions.browsers || []" :key="item.name"><span>{{ item.name }}</span><strong>{{ item.value }}</strong></div>
          </div>
        </section>
        <section class="admin-panel">
          <div class="admin-panel__heading"><div><span class="eyebrow">Sources</span><h2>UTM 来源</h2></div></div>
          <div class="distribution-list">
            <div v-for="item in distributions.sources || []" :key="item.name"><span>{{ item.name }}</span><strong>{{ item.value }}</strong></div>
          </div>
        </section>
        <section class="admin-panel">
          <div class="admin-panel__heading"><div><span class="eyebrow">Locations</span><h2>访问地区</h2></div></div>
          <div class="distribution-list">
            <div v-for="item in distributions.locations || []" :key="item.name"><span>{{ item.name }}</span><strong>{{ item.value }}</strong></div>
          </div>
        </section>
      </div>
      <section class="admin-panel session-panel">
        <div class="admin-panel__heading"><div><span class="eyebrow">Recent sessions</span><h2>最近匿名访问路径</h2></div></div>
        <EmptyState v-if="!visitorState.data.value?.items.length" title="暂无访问会话" description="公开站产生访问事件后，会在此显示匿名路径。" />
        <div v-else class="session-list">
          <button v-for="item in visitorState.data.value.items" :key="String(item.uuid)" @click="openSession(String(item.uuid))">
            <span class="score-ring" :style="{ '--score': Number(item.attention_score || 0) }">{{ item.attention_score }}</span>
            <span>
              <strong>匿名访客 {{ String(item.visitor_uuid).slice(0, 8) }}</strong>
              <small>{{ [item.country, item.region, item.city].filter(Boolean).join(' · ') || '未知地区' }} · {{ deviceLabel(item.device_type) }} · {{ item.browser }} · {{ new Date(String(item.started_at)).toLocaleString() }}</small>
            </span>
            <span>{{ item.visit_count }} 次访问</span>
            <Activity :size="17" />
          </button>
        </div>
      </section>
    </template>
    <Teleport to="body">
      <div v-if="selectedSession" class="modal-backdrop" @click.self="selectedSession = null">
        <section class="modal-card modal-card--large">
          <header><div><span class="eyebrow">Anonymous journey</span><h2>访问路径与关注评分</h2></div><button class="icon-button" @click="selectedSession = null"><X :size="19" /></button></header>
          <LoadingState v-if="sessionState.loading.value" :rows="8" />
          <ErrorState v-else-if="sessionState.error.value" :message="sessionState.error.value" @retry="openSession(selectedSession)" />
          <template v-else-if="sessionDetails?.session">
            <div class="session-score-summary">
              <strong>{{ sessionDetails.session.attention_score }}</strong>
              <div><h3>高关注会话评分</h3><p>这是可解释的行为分数，不代表真实身份或录用意向。</p></div>
            </div>
            <div class="score-reasons">
              <span v-for="reason in (sessionDetails.session.score_reasons as Array<Record<string, unknown>> || [])" :key="String(reason.rule)">{{ reason.rule }} · +{{ reason.points }}</span>
            </div>
            <ol class="journey-timeline">
              <li v-for="event in sessionDetails.events" :key="String(event.uuid)">
                <span><Clock3 :size="15" /></span>
                <div><strong>{{ eventLabel(event.event_type) }}</strong><small>{{ new Date(String(event.timestamp)).toLocaleString() }}</small><code v-if="event.project_uuid">项目 {{ event.project_title || String(event.project_uuid).slice(0, 8) }}</code></div>
              </li>
            </ol>
          </template>
        </section>
      </div>
    </Teleport>
  </div>
</template>
