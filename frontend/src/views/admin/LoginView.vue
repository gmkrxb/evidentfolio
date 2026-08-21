<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ArrowRight, KeyRound, ShieldCheck } from 'lucide-vue-next'
import { useRoute, useRouter } from 'vue-router'
import { authApi } from '@/api/admin'
import { useAuthStore } from '@/stores/auth'
import { useSiteStore } from '@/stores/site'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const site = useSiteStore()
const setupRequired = ref(false)
const checking = ref(true)
const error = ref('')
const loginForm = reactive({ username: '', password: '' })
const setupForm = reactive({
  username: 'admin',
  password: '',
  display_name: '',
  site_name: '',
  person_name: '',
  primary_language: 'zh-CN',
})
const heading = computed(() => setupRequired.value ? '首次初始化' : '管理后台登录')

onMounted(async () => {
  try {
    const [result] = await Promise.all([
      authApi.setupStatus(),
      site.load().catch(() => undefined),
    ])
    setupRequired.value = result.required
    setupForm.site_name = String(site.settings.site_name || '')
    setupForm.person_name = String(site.settings.person_name || '')
    setupForm.display_name = String(site.settings.person_name || '')
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : '无法检查系统状态'
  } finally {
    checking.value = false
  }
})
async function submit() {
  error.value = ''
  try {
    if (setupRequired.value) await auth.initialize({ ...setupForm })
    else await auth.login(loginForm.username, loginForm.password)
    await router.replace(String(route.query.redirect || '/admin/dashboard'))
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : '操作失败'
  }
}
</script>

<template>
  <main class="login-page">
    <section class="login-brand-panel">
      <RouterLink to="/" class="public-brand public-brand--light">
        <span class="public-brand__mark">{{ site.settings.brand_mark_text || 'P' }}</span>
        <span class="public-brand__text">{{ site.settings.site_name || 'Portfolio' }}</span>
      </RouterLink>
      <div>
        <span class="eyebrow">Private control room</span>
        <h1>管理作品，<br />观察真实关注。</h1>
        <p>内容、文件、简历和匿名访问行为都由你自己管理。</p>
      </div>
      <ul>
        <li><ShieldCheck :size="18" />HttpOnly 会话与操作审计</li>
        <li><KeyRound :size="18" />初始化完成后入口自动关闭</li>
      </ul>
    </section>
    <section class="login-form-panel">
      <form class="auth-form" @submit.prevent="submit">
        <span class="eyebrow">{{ setupRequired ? 'One-time setup' : 'Welcome back' }}</span>
        <h2>{{ heading }}</h2>
        <p v-if="checking">正在检查系统状态…</p>
        <template v-else-if="setupRequired">
          <label>管理员账号<input v-model.trim="setupForm.username" required minlength="3" autocomplete="username" /></label>
          <label>管理员显示名<input v-model.trim="setupForm.display_name" required /></label>
          <label>网站名称<input v-model.trim="setupForm.site_name" required /></label>
          <label>个人姓名<input v-model.trim="setupForm.person_name" required /></label>
          <label>网站第一语言<select v-model="setupForm.primary_language"><option value="zh-CN">中文</option><option value="en">English</option></select></label>
          <label>
            管理员密码
            <input v-model="setupForm.password" required minlength="12" type="password" autocomplete="new-password" />
            <small>至少 12 位；建议使用密码管理器生成。</small>
          </label>
        </template>
        <template v-else>
          <label>管理员账号<input v-model.trim="loginForm.username" required autocomplete="username" /></label>
          <label>密码<input v-model="loginForm.password" required type="password" autocomplete="current-password" /></label>
        </template>
        <div v-if="error" class="form-error" role="alert">{{ error }}</div>
        <button class="button button--dark button--wide" :disabled="auth.loading || checking">
          {{ auth.loading ? '处理中…' : setupRequired ? '完成初始化' : '安全登录' }}
          <ArrowRight :size="17" />
        </button>
        <p class="auth-form__hint">登录凭证保存在安全 Cookie 中，不写入 LocalStorage。</p>
      </form>
    </section>
  </main>
</template>
