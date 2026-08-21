<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ArrowDown, ArrowUp, Languages, Plus, Save, Trash2 } from 'lucide-vue-next'
import ErrorState from '@/components/ui/ErrorState.vue'
import LoadingState from '@/components/ui/LoadingState.vue'
import { adminApi } from '@/api/admin'
import { useSiteStore } from '@/stores/site'
import { useToastStore } from '@/stores/toast'
import type { Asset, SiteSettings } from '@/types'
import IconPicker from '@/components/icons/IconPicker.vue'
import { clonePlain } from '@/utils/clone'
import { readSse } from '@/utils/sse'

const loading = ref(false)
const saving = ref(false)
const translating = ref(false)
const error = ref('')
const settingsLocale = ref<'zh-CN' | 'en'>('zh-CN')
const site = useSiteStore()
const toast = useToastStore()
const directions = ref('')
const assets = ref<Asset[]>([])
const navigation = ref<Array<{ label: string; to: string; kind: 'route' | 'external' }>>([])
const homeStats = ref<Array<{ value: string; label: string }>>([])
const capabilities = ref<Array<{ title: string; description: string }>>([])
const contacts = ref<Array<{
  type: string
  label: string
  value: string
  url: string
  description: string
  icon_asset_uuid: string
  icon_name: string
  icon_svg: string
}>>([])
const pageContent = reactive<Record<string, { eyebrow: string; title: string; description: string }>>({
  projects: { eyebrow: '', title: '', description: '' },
  resumes: { eyebrow: '', title: '', description: '' },
  certificates: { eyebrow: '', title: '', description: '' },
  contact: { eyebrow: '', title: '', description: '' },
})
const homeCopy = reactive<Record<string, string>>({
  projects_eyebrow: '', projects_title: '', projects_description: '',
  capabilities_eyebrow: '', capabilities_title: '', capabilities_description: '',
  categories_eyebrow: '', categories_title: '', contact_eyebrow: '', contact_description: '',
})
const pageLabels: Record<string, string> = {
  projects: '项目页',
  resumes: '简历页',
  certificates: '证书页',
  contact: '联系页',
}
const form = reactive<SiteSettings>({
  site_name: '', person_name: '', headline: '', bio: '', current_identity: '', research_directions: [],
  email: '', github_url: '', gitee_url: '', location: '', footer_text: '', footer_eyebrow: '',
  footer_heading: '', hero_eyebrow: '', hero_focus_label: '', hero_focus_value: '',
  default_seo_title: '', default_seo_description: '', analytics_enabled: true,
  analytics_retention_days: 365, analytics_notice_enabled: true, featured_project_count: 3,
})
const englishSettings = reactive<SiteSettings>({
  site_name: '', person_name: '', headline: '', bio: '', current_identity: '', research_directions: [],
  location: '', footer_text: '', footer_eyebrow: '', footer_heading: '', hero_eyebrow: '',
  hero_focus_label: '', hero_focus_value: '', default_seo_title: '', default_seo_description: '',
})
const englishDirections = ref('')
const englishNavigation = ref<Array<{ label: string; to: string; kind: 'route' | 'external' }>>([])
const englishHomeStats = ref<Array<{ value: string; label: string }>>([])
const englishCapabilities = ref<Array<{ title: string; description: string }>>([])
const englishContacts = ref<typeof contacts.value>([])
const englishPageContent = reactive<Record<string, { eyebrow: string; title: string; description: string }>>({
  projects: { eyebrow: '', title: '', description: '' }, resumes: { eyebrow: '', title: '', description: '' },
  certificates: { eyebrow: '', title: '', description: '' }, contact: { eyebrow: '', title: '', description: '' },
})
const englishHomeCopy = reactive<Record<string, string>>({})
async function load() {
  loading.value = true
  error.value = ''
  try {
    const [settings, assetResult] = await Promise.all([
      adminApi.settings(),
      adminApi.assets({ category: 'images', page_size: 100 }),
    ])
    Object.assign(form, settings)
    Object.assign(englishSettings, clonePlain(settings.translations?.en || {}))
    assets.value = assetResult.items
    directions.value = (form.research_directions || []).join('\n')
    navigation.value = clonePlain(form.navigation_items || [])
    homeStats.value = clonePlain(form.home_stats || [])
    capabilities.value = clonePlain(form.home_capabilities || [])
    contacts.value = clonePlain(form.contact_methods || [])
    Object.assign(pageContent, clonePlain(form.page_content || {}))
    Object.assign(homeCopy, clonePlain(form.home_copy || {}))
    englishDirections.value = (englishSettings.research_directions || form.research_directions || []).join('\n')
    englishNavigation.value = clonePlain(englishSettings.navigation_items || navigation.value)
    englishHomeStats.value = clonePlain(englishSettings.home_stats || homeStats.value)
    englishCapabilities.value = clonePlain(englishSettings.home_capabilities || capabilities.value)
    englishContacts.value = clonePlain(englishSettings.contact_methods || contacts.value)
    Object.assign(englishPageContent, clonePlain(englishSettings.page_content || pageContent))
    Object.assign(englishHomeCopy, clonePlain(englishSettings.home_copy || homeCopy))
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : '设置加载失败'
  } finally {
    loading.value = false
  }
}
async function save() {
  saving.value = true
  error.value = ''
  try {
    form.research_directions = directions.value.split('\n').map((item) => item.trim()).filter(Boolean)
    form.navigation_items = clonePlain(navigation.value)
    form.home_stats = clonePlain(homeStats.value)
    form.home_capabilities = clonePlain(capabilities.value)
    contacts.value = contacts.value.map((item) => ({
      ...item,
      url: item.url.trim() || automaticContactUrl(item.type, item.value),
    }))
    form.contact_methods = clonePlain(contacts.value)
    form.page_content = clonePlain(pageContent)
    form.home_copy = clonePlain(homeCopy)
    englishSettings.research_directions = englishDirections.value.split('\n').map((item) => item.trim()).filter(Boolean)
    englishSettings.navigation_items = clonePlain(englishNavigation.value)
    englishSettings.home_stats = clonePlain(englishHomeStats.value)
    englishSettings.home_capabilities = clonePlain(englishCapabilities.value)
    englishSettings.contact_methods = clonePlain(englishContacts.value)
    englishSettings.page_content = clonePlain(englishPageContent)
    englishSettings.home_copy = clonePlain(englishHomeCopy)
    form.translations = { ...(form.translations || {}), en: clonePlain(englishSettings) }
    await adminApi.updateSettings(clonePlain(form))
    await site.load(true)
    toast.show('网站设置已保存', 'success')
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : '保存失败'
  } finally {
    saving.value = false
  }
}

async function translateSettings() {
  translating.value = true; error.value = ''
  try {
    const content = {
      site_name: form.site_name, person_name: form.person_name, headline: form.headline, bio: form.bio,
      current_identity: form.current_identity, research_directions: directions.value.split('\n').filter(Boolean),
      location: form.location, footer_text: form.footer_text, footer_eyebrow: form.footer_eyebrow,
      footer_heading: form.footer_heading, hero_eyebrow: form.hero_eyebrow, hero_focus_label: form.hero_focus_label,
      hero_focus_value: form.hero_focus_value, default_seo_title: form.default_seo_title,
      default_seo_description: form.default_seo_description, navigation_items: navigation.value,
      home_stats: homeStats.value, home_capabilities: capabilities.value, contact_methods: contacts.value,
      page_content: pageContent, home_copy: homeCopy,
    }
    let result: Record<string, any> | null = null
    await readSse(await adminApi.aiStream('translate', { source_locale: 'zh-CN', target_locale: 'en', entity_type: 'site_settings', content }), (event) => {
      if (event.type === 'result') result = event.data || null
    })
    if (!result) throw new Error('AI 未返回翻译结果')
    const translated = result as Record<string, any>
    Object.assign(englishSettings, translated)
    englishDirections.value = Array.isArray(translated.research_directions) ? translated.research_directions.join('\n') : ''
    englishNavigation.value = clonePlain(translated.navigation_items || [])
    englishHomeStats.value = clonePlain(translated.home_stats || [])
    englishCapabilities.value = clonePlain(translated.home_capabilities || [])
    englishContacts.value = clonePlain(translated.contact_methods || [])
    Object.assign(englishPageContent, clonePlain(translated.page_content || {}))
    Object.assign(englishHomeCopy, clonePlain(translated.home_copy || {}))
    settingsLocale.value = 'en'
    toast.show('英文网站内容已生成，请检查后保存', 'success')
  } catch (cause) { error.value = cause instanceof Error ? cause.message : 'AI 翻译失败' }
  finally { translating.value = false }
}

function moveContact(index: number, offset: -1 | 1) {
  const target = index + offset
  if (target < 0 || target >= contacts.value.length) return
  const [item] = contacts.value.splice(index, 1)
  contacts.value.splice(target, 0, item)
}

function contactUrlPlaceholder(type: string) {
  if (type === 'phone') return 'tel:+86...'
  if (type === 'email') return 'mailto:name@example.com'
  if (type === 'location') return '地图地址或留空'
  return 'https://...'
}

function automaticContactUrl(type: string, value: string) {
  const normalized = value.trim()
  if (type === 'phone' && normalized) return `tel:${normalized.replace(/[^\d+]/g, '')}`
  if (type === 'email' && normalized) return `mailto:${normalized}`
  return ''
}
onMounted(load)
</script>

<template>
  <div class="admin-page">
    <header class="admin-page-heading">
      <div><span class="eyebrow">Site configuration</span><h1>网站设置</h1><p>公开端身份信息、SEO、分析与内容展示策略。</p></div>
      <button class="button button--dark" :disabled="saving" @click="save"><Save :size="17" />{{ saving ? '保存中…' : '保存设置' }}</button>
    </header>
    <LoadingState v-if="loading" :rows="10" />
    <ErrorState v-else-if="error && !form.site_name" :message="error" @retry="load" />
    <form v-else class="settings-grid" @submit.prevent="save">
      <section class="editor-language-bar settings-language-bar">
        <div class="language-tabs"><button type="button" :class="{ active: settingsLocale === 'zh-CN' }" @click="settingsLocale = 'zh-CN'">中文设置</button><button type="button" :class="{ active: settingsLocale === 'en' }" @click="settingsLocale = 'en'">English settings</button></div>
        <label>网站第一语言<select v-model="form.primary_language"><option value="zh-CN">中文</option><option value="en">English</option></select></label>
        <button type="button" class="button button--outline" :disabled="translating" @click="translateSettings"><Languages :size="16" />{{ translating ? '翻译中…' : 'AI 生成英文设置' }}</button>
      </section>
      <section v-if="settingsLocale === 'en'" class="form-section form-section--translation">
        <div class="form-section__heading"><span>EN</span><div><h2>English public content</h2><p>English fields override the primary content under /en; blank fields fall back safely.</p></div></div>
        <div class="form-grid">
          <label>Site name<input v-model="englishSettings.site_name" /></label><label>Person name<input v-model="englishSettings.person_name" /></label>
          <label class="span-2">Hero statement<textarea v-model="englishSettings.headline" rows="3" /></label>
          <label class="span-2">Biography<textarea v-model="englishSettings.bio" rows="5" /></label>
          <label class="span-2">Current identity<input v-model="englishSettings.current_identity" /></label>
          <label class="span-2">Research directions (one per line)<textarea v-model="englishDirections" rows="6" /></label>
          <label>Location<input v-model="englishSettings.location" /></label><label>Hero eyebrow<input v-model="englishSettings.hero_eyebrow" /></label>
          <label>Focus label<input v-model="englishSettings.hero_focus_label" /></label><label>Focus value<input v-model="englishSettings.hero_focus_value" /></label>
          <label>Footer eyebrow<input v-model="englishSettings.footer_eyebrow" /></label><label>Footer text<input v-model="englishSettings.footer_text" /></label>
          <label class="span-2">Footer heading<input v-model="englishSettings.footer_heading" /></label>
          <label>SEO title<input v-model="englishSettings.default_seo_title" /></label><label>SEO description<textarea v-model="englishSettings.default_seo_description" rows="3" /></label>
        </div>
        <div class="repeat-list-heading"><strong>English navigation</strong></div>
        <div v-for="(item, index) in englishNavigation" :key="index" class="repeat-row repeat-row--nav"><input v-model="item.label" placeholder="Label" /><input v-model="item.to" /><select v-model="item.kind"><option value="route">Route</option><option value="external">External</option></select></div>
        <div class="repeat-list-heading"><strong>English home metrics</strong></div>
        <div v-for="(item, index) in englishHomeStats" :key="index" class="repeat-row repeat-row--stat"><input v-model="item.value" placeholder="Value" /><input v-model="item.label" placeholder="Label" /></div>
        <div class="repeat-list-heading"><strong>English capabilities</strong></div>
        <div v-for="(item, index) in englishCapabilities" :key="index" class="repeat-section repeat-section--compact"><div><input v-model="item.title" placeholder="Title" /></div><textarea v-model="item.description" rows="2" placeholder="Description" /></div>
        <div class="repeat-list-heading"><strong>English page headers</strong></div>
        <div v-for="key in ['projects', 'resumes', 'certificates', 'contact']" :key="key" class="page-copy-editor"><strong>{{ key }}</strong><div class="form-grid"><label>Eyebrow<input v-model="englishPageContent[key].eyebrow" /></label><label>Title<input v-model="englishPageContent[key].title" /></label><label class="span-2">Description<textarea v-model="englishPageContent[key].description" rows="2" /></label></div></div>
      </section>
      <template v-if="settingsLocale === 'zh-CN'">
      <section class="form-section">
        <div class="form-section__heading"><span>01</span><div><h2>个人与网站</h2><p>首页首屏、联系区与页脚会实时使用这些内容。</p></div></div>
        <div class="form-grid">
          <label>网站名称<input v-model="form.site_name" required /></label>
          <label>个人姓名<input v-model="form.person_name" required /></label>
          <label class="span-2">首屏主张<textarea v-model="form.headline" rows="3" /></label>
          <label class="span-2">个人简介<textarea v-model="form.bio" rows="5" /></label>
          <label class="span-2">当前身份<input v-model="form.current_identity" /></label>
          <label class="span-2">研究方向（每行一项）<textarea v-model="directions" rows="5" /></label>
          <label>邮箱<input v-model="form.email" type="email" /></label>
          <label>所在地<input v-model="form.location" /></label>
          <label>GitHub 地址<input v-model="form.github_url" type="url" /></label>
          <label>Gitee 地址<input v-model="form.gitee_url" type="url" /></label>
          <label class="span-2">首屏眉题<input v-model="form.hero_eyebrow" /></label>
          <label>焦点标签<input v-model="form.hero_focus_label" /></label>
          <label>焦点内容<input v-model="form.hero_focus_value" /></label>
          <label>页脚眉题<input v-model="form.footer_eyebrow" /></label>
          <label class="span-2">页脚文字<input v-model="form.footer_text" /></label>
          <label class="span-2">页脚主标题<input v-model="form.footer_heading" /></label>
        </div>
      </section>
      <section class="form-section">
        <div class="form-section__heading"><span>02</span><div><h2>品牌与导航</h2><p>不在代码中绑定姓名、缩写或导航项，开源部署可直接替换。</p></div></div>
        <div class="form-grid">
          <label>品牌文字<input v-model="form.brand_mark_text" maxlength="8" placeholder="例如 GMK" /></label>
          <label>品牌图标
            <select v-model="form.brand_icon_asset_uuid">
              <option value="">使用品牌文字</option>
              <option v-for="asset in assets" :key="asset.uuid" :value="asset.uuid">{{ asset.display_name }}</option>
            </select>
          </label>
        </div>
        <div class="repeat-list-heading"><strong>导航项目</strong><button type="button" class="button button--outline button--small" @click="navigation.push({ label: '', to: '/', kind: 'route' })"><Plus :size="15" />添加</button></div>
        <div v-for="(item, index) in navigation" :key="index" class="repeat-row repeat-row--nav">
          <input v-model="item.label" placeholder="名称" />
          <input v-model="item.to" placeholder="/route 或 https://..." />
          <select v-model="item.kind"><option value="route">站内路由</option><option value="external">外部链接</option></select>
          <button type="button" class="icon-button danger-text" @click="navigation.splice(index, 1)"><Trash2 :size="16" /></button>
        </div>
      </section>
      <section class="form-section">
        <div class="form-section__heading"><span>03</span><div><h2>首页指标与介绍</h2><p>首页数据、段落标题和能力介绍均由后台维护。</p></div></div>
        <div class="repeat-list-heading"><strong>首屏指标</strong><button type="button" class="button button--outline button--small" @click="homeStats.push({ value: '', label: '' })"><Plus :size="15" />添加</button></div>
        <div v-for="(item, index) in homeStats" :key="index" class="repeat-row repeat-row--stat">
          <input v-model="item.value" placeholder="数值" />
          <input v-model="item.label" placeholder="指标说明" />
          <button type="button" class="icon-button danger-text" @click="homeStats.splice(index, 1)"><Trash2 :size="16" /></button>
        </div>
        <div class="form-grid">
          <label>项目区眉题<input v-model="homeCopy.projects_eyebrow" /></label>
          <label>项目区标题<input v-model="homeCopy.projects_title" /></label>
          <label class="span-2">项目区说明<textarea v-model="homeCopy.projects_description" rows="3" /></label>
          <label>能力区眉题<input v-model="homeCopy.capabilities_eyebrow" /></label>
          <label>能力区标题<input v-model="homeCopy.capabilities_title" /></label>
          <label class="span-2">能力区说明<textarea v-model="homeCopy.capabilities_description" rows="3" /></label>
          <label>分类区眉题<input v-model="homeCopy.categories_eyebrow" /></label>
          <label>分类区标题<input v-model="homeCopy.categories_title" /></label>
          <label>联系区眉题<input v-model="homeCopy.contact_eyebrow" /></label>
          <label class="span-2">联系区说明<textarea v-model="homeCopy.contact_description" rows="3" /></label>
        </div>
        <div class="repeat-list-heading"><strong>能力介绍</strong><button type="button" class="button button--outline button--small" @click="capabilities.push({ title: '', description: '' })"><Plus :size="15" />添加</button></div>
        <div v-for="(item, index) in capabilities" :key="index" class="repeat-section repeat-section--compact">
          <div><input v-model="item.title" placeholder="能力标题" /><button type="button" class="icon-button danger-text" @click="capabilities.splice(index, 1)"><Trash2 :size="16" /></button></div>
          <textarea v-model="item.description" rows="2" placeholder="能力说明" />
        </div>
      </section>
      <section class="form-section">
        <div class="form-section__heading"><span>04</span><div><h2>页面首屏文案</h2><p>控制项目、简历、证书和联系页面顶部的眉题、标题与说明。</p></div></div>
        <div v-for="key in ['projects', 'resumes', 'certificates', 'contact']" :key="key" class="page-copy-editor">
          <strong>{{ pageLabels[key] }}</strong>
          <div class="form-grid">
            <label>眉题<input v-model="pageContent[key].eyebrow" /></label>
            <label>标题<input v-model="pageContent[key].title" /></label>
            <label class="span-2">说明<textarea v-model="pageContent[key].description" rows="2" /></label>
          </div>
        </div>
      </section>
      <section class="form-section">
        <div class="form-section__heading"><span>05</span><div><h2>联系方式</h2><p>联系页与页脚共享；每项可选择上传的自定义图标。</p></div></div>
        <div class="repeat-list-heading"><strong>联系项目</strong><button type="button" class="button button--outline button--small" @click="contacts.push({ type: 'other', label: '', value: '', url: '', description: '', icon_asset_uuid: '', icon_name: '', icon_svg: '' })"><Plus :size="15" />添加</button></div>
        <div v-for="(item, index) in contacts" :key="index" class="repeat-section contact-setting-item">
          <div class="contact-setting-item__heading">
            <span class="contact-setting-item__index">{{ String(index + 1).padStart(2, '0') }}</span>
            <input v-model="item.label" placeholder="名称，例如：电话、工作邮箱" />
            <div class="contact-setting-item__order">
              <button type="button" class="icon-button" :disabled="index === 0" aria-label="上移联系方式" @click="moveContact(index, -1)"><ArrowUp :size="16" /></button>
              <button type="button" class="icon-button" :disabled="index === contacts.length - 1" aria-label="下移联系方式" @click="moveContact(index, 1)"><ArrowDown :size="16" /></button>
              <button type="button" class="icon-button danger-text" aria-label="删除联系方式" @click="contacts.splice(index, 1)"><Trash2 :size="16" /></button>
            </div>
          </div>
          <div class="form-grid contact-setting-item__fields">
            <label>类型<select v-model="item.type"><option value="email">邮箱</option><option value="phone">电话</option><option value="github">GitHub</option><option value="location">地址</option><option value="message">即时通信</option><option value="other">其他</option></select></label>
            <label class="contact-setting-item__value">展示值<input v-model="item.value" :type="item.type === 'phone' ? 'tel' : 'text'" placeholder="公开页面显示的完整内容" /></label>
            <label class="contact-setting-item__url">链接地址<input v-model="item.url" :placeholder="contactUrlPlaceholder(item.type)" /></label>
            <label class="span-2">说明<input v-model="item.description" /></label>
            <div class="span-2">
              <IconPicker
                v-model:icon-name="item.icon_name"
                v-model:icon-svg="item.icon_svg"
                v-model:image-uuid="item.icon_asset_uuid"
                :assets="assets"
              />
            </div>
          </div>
        </div>
      </section>
      <section class="form-section">
        <div class="form-section__heading"><span>06</span><div><h2>SEO 与首页</h2><p>页面可单独覆盖，以下作为默认值。</p></div></div>
        <div class="form-grid">
          <label class="span-2">默认 SEO 标题<input v-model="form.default_seo_title" /></label>
          <label class="span-2">默认 SEO 描述<textarea v-model="form.default_seo_description" rows="4" /></label>
          <label>首页推荐项目数量<input v-model.number="form.featured_project_count" type="number" min="1" max="12" /></label>
        </div>
      </section>
      <section class="form-section">
        <div class="form-section__heading"><span>07</span><div><h2>访问分析与隐私</h2><p>只生成关注度信号，不进行侵入式浏览器指纹。</p></div></div>
        <label class="check-label"><input v-model="form.analytics_enabled" type="checkbox" />开启访问分析</label>
        <label class="check-label"><input v-model="form.analytics_notice_enabled" type="checkbox" />公开端显示分析说明</label>
        <label>数据保留天数<input v-model.number="form.analytics_retention_days" type="number" min="0" max="3650" /></label>
        <p class="panel-note">运行级的允许文件类型、上传大小和可信代理由挂载的 Python 配置文件管理，网站内容设置不会覆盖安全边界。</p>
      </section>
      </template>
      <div v-if="error" class="form-error">{{ error }}</div>
      <button class="button button--dark settings-save" :disabled="saving"><Save :size="17" />保存全部设置</button>
    </form>
  </div>
</template>
