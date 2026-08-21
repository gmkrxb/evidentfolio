<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import {
  ArrowLeft,
  Eye,
  FileArchive,
  FileText,
  FolderOpen,
  GripVertical,
  ImagePlus,
  Images,
  Music2,
  Languages,
  Pencil,
  Plus,
  Save,
  Trash2,
  UploadCloud,
  Video,
  X,
} from 'lucide-vue-next'
import { onBeforeRouteLeave, useRoute, useRouter } from 'vue-router'
import ErrorState from '@/components/ui/ErrorState.vue'
import LoadingState from '@/components/ui/LoadingState.vue'
import MarkdownContent from '@/components/content/MarkdownContent.vue'
import BaseSelect from '@/components/ui/BaseSelect.vue'
import ResourcePickerModal from '@/components/admin/ResourcePickerModal.vue'
import { adminApi } from '@/api/admin'
import { useToastStore } from '@/stores/toast'
import type { Asset, AssetFolder, Certificate, Project, ProjectAlbum, ProjectContentLayoutItem, ProjectPayload, ProjectSection, TaxonomyItem } from '@/types'
import { clonePlain } from '@/utils/clone'
import { readSse } from '@/utils/sse'

const route = useRoute()
const router = useRouter()
const toast = useToastStore()
const isNew = computed(() => route.name === 'admin-project-new')
const loading = ref(false)
const saving = ref(false)
const translating = ref(false)
const error = ref('')
const dirty = ref(false)
const categories = ref<TaxonomyItem[]>([])
const tags = ref<TaxonomyItem[]>([])
const assets = ref<Asset[]>([])
const assetFolders = ref<AssetFolder[]>([])
const existingProjectImages = ref<Asset[]>([])
const certificates = ref<Certificate[]>([])
const uploadingTarget = ref('')
const previewSections = ref<Set<number>>(new Set())
const pickerOpen = ref(false)
const pickerSectionIndex = ref<number | null>(null)
const albumPickerOpen = ref(false)
const albumPickerIndex = ref<number | null>(null)
const sortModalOpen = ref(false)
const draggedLayoutIndex = ref<number | null>(null)
const editLocale = ref<'zh-CN' | 'en'>('zh-CN')
const listFields = reactive({ technologies: '', contributions: '', outcomes: '' })
const englishProject = reactive({
  title: '', subtitle: '', summary: '', content: '', background: '', problem: '', solution: '', architecture: '',
  role: '', seo_title: '', seo_description: '', contributions: '', outcomes: '',
})
const form = reactive<ProjectPayload>({
  title: '', subtitle: '', summary: '', content: '', background: '', problem: '', solution: '', architecture: '',
  contributions: [], technologies: [], outcomes: [], start_date: '', end_date: '', role: '', team_size: null,
  status: 'draft', project_state: 'completed', is_featured: false, is_open_source: false, sort_order: 0,
  category_uuid: null, tag_uuids: [], cover_asset_uuid: null, seo_title: '', seo_description: '', links: [], sections: [],
  certificate_uuids: [], albums: [],
  translations: {}, content_language_mode: 'bilingual',
  content_layout: [
    { key: 'overview', kind: 'builtin', visible: true, sort_order: 0 },
    { key: 'problem', kind: 'builtin', visible: true, sort_order: 1 },
    { key: 'architecture', kind: 'builtin', visible: true, sort_order: 2 },
    { key: 'contribution', kind: 'builtin', visible: true, sort_order: 3 },
    { key: 'outcomes', kind: 'builtin', visible: true, sort_order: 4 },
    { key: 'media', kind: 'builtin', visible: true, sort_order: 5 },
    { key: 'credentials', kind: 'builtin', visible: true, sort_order: 6 },
  ],
})
const builtinLabels: Record<string, string> = {
  overview: '项目概览',
  problem: '问题与方案',
  architecture: '系统架构与技术路线',
  contribution: '我的具体贡献',
  outcomes: '关键成果',
  media: '项目截图、视频与文档',
  credentials: '关联证书与荣誉',
}
const sectionModeOptions = [
  { value: 'text', label: '文字 / Markdown', description: '仅展示结构化文字内容' },
  { value: 'single', label: '单张图片', description: '突出展示一张关键图像' },
  { value: 'gallery', label: '多图画廊', description: '响应式网格并支持灯箱' },
  { value: 'carousel', label: '横向轮播', description: '适合连续截图或过程图' },
  { value: 'album', label: '引用相册', description: '复用项目内已经维护的相册' },
  { value: 'video', label: '视频内容', description: '在线播放一个或多个演示视频' },
  { value: 'audio', label: '音频内容', description: '在线播放访谈、讲解或录音' },
  { value: 'attachments', label: '文档与附件', description: 'PDF、Office、文本或 ZIP 附件' },
  { value: 'mixed', label: '混合媒体', description: '在同一区块组合不同类型资源' },
]
const albumModeOptions = [
  { value: 'grid', label: '网格画廊' },
  { value: 'carousel', label: '横向轮播' },
]
const imageAssets = computed(() => assets.value.filter((asset) => asset.mime_type.startsWith('image/')))
const albumOptions = computed(() => form.albums.map((album) => ({
  value: album.uuid || '',
  label: album.title || '未命名相册',
  description: `${album.asset_uuids?.length || 0} 张图片`,
})))
const autoCoverPreview = computed(() => {
  const uuids = new Set<string>()
  for (const section of form.sections) {
    section.asset_uuids.forEach((uuid) => uuids.add(uuid))
  }
  for (const album of form.albums) {
    album.asset_uuids?.forEach((uuid) => uuids.add(uuid))
  }
  const current = imageAssets.value.filter((asset) => uuids.has(asset.uuid))
  for (const asset of existingProjectImages.value) {
    if (!current.some((item) => item.uuid === asset.uuid)) current.push(asset)
  }
  return current.slice(0, 4)
})
const pickerSection = computed(() =>
  pickerSectionIndex.value === null ? null : form.sections[pickerSectionIndex.value],
)
const pickerAssets = computed(() => pickerSection.value ? sectionAssetOptions(pickerSection.value) : assets.value)
const pickerMultiple = computed(() => pickerSection.value?.display_mode !== 'single')
const pickerAlbum = computed(() =>
  albumPickerIndex.value === null ? null : form.albums[albumPickerIndex.value],
)
const orderedSectionEntries = computed(() => form.sections
  .map((section, index) => ({
    section,
    index,
    order: form.content_layout.find(
      (item) => item.key === `custom:${section.client_key}`,
    )?.sort_order ?? index + 100,
  }))
  .sort((left, right) => left.order - right.order))

function lines(value: string) {
  return value.split('\n').map((item) => item.trim()).filter(Boolean)
}
function sectionEn(section: ProjectSection): Record<string, string> {
  section.translations ||= {}
  section.translations.en ||= {}
  return section.translations.en as Record<string, string>
}
function albumEn(album: ProjectAlbum): Record<string, string> {
  album.translations ||= {}
  album.translations.en ||= {}
  return album.translations.en as Record<string, string>
}
async function translateProject() {
  translating.value = true
  error.value = ''
  try {
    const fromEnglish = editLocale.value === 'en'
    const content = fromEnglish ? {
      ...clonePlain(englishProject), contributions: lines(englishProject.contributions), outcomes: lines(englishProject.outcomes),
      sections: form.sections.map((section) => ({ client_key: section.client_key, ...sectionEn(section) })),
      albums: form.albums.map((album) => ({ uuid: album.uuid, ...albumEn(album) })),
    } : {
      title: form.title, subtitle: form.subtitle, summary: form.summary, content: form.content,
      background: form.background, problem: form.problem, solution: form.solution, architecture: form.architecture,
      role: form.role, contributions: lines(listFields.contributions), outcomes: lines(listFields.outcomes),
      seo_title: form.seo_title, seo_description: form.seo_description,
      sections: form.sections.map((section) => ({ client_key: section.client_key, title: section.title, body: section.body })),
      albums: form.albums.map((album) => ({ uuid: album.uuid, title: album.title, description: album.description })),
    }
    let result: Record<string, unknown> | null = null
    await readSse(await adminApi.aiStream('translate', { source_locale: fromEnglish ? 'en' : 'zh-CN', target_locale: fromEnglish ? 'zh-CN' : 'en', entity_type: 'project', content }), (event) => {
      if (event.type === 'result') result = event.data || null
    })
    if (!result) throw new Error('AI 未返回翻译结果')
    const translated = result as Record<string, any>
    if (fromEnglish) {
      for (const key of ['title', 'subtitle', 'summary', 'content', 'background', 'problem', 'solution', 'architecture', 'role', 'seo_title', 'seo_description'] as const) {
        form[key] = String(translated[key] || '')
      }
      listFields.contributions = Array.isArray(translated.contributions) ? translated.contributions.join('\n') : ''
      listFields.outcomes = Array.isArray(translated.outcomes) ? translated.outcomes.join('\n') : ''
    } else {
      for (const key of Object.keys(englishProject) as Array<keyof typeof englishProject>) {
        const value = translated[key]
        englishProject[key] = Array.isArray(value) ? value.join('\n') : String(value || '')
      }
    }
    for (const item of Array.isArray(translated.sections) ? translated.sections : []) {
      const target = form.sections.find((section) => section.client_key === item.client_key)
      if (target) {
        if (fromEnglish) Object.assign(target, { title: item.title || '', body: item.body || '' })
        else Object.assign(sectionEn(target), { title: item.title || '', body: item.body || '' })
      }
    }
    for (const [index, item] of (Array.isArray(translated.albums) ? translated.albums : []).entries()) {
      const target = form.albums.find((album) => album.uuid && album.uuid === item.uuid) || form.albums[index]
      if (target) {
        if (fromEnglish) Object.assign(target, { title: item.title || '', description: item.description || '' })
        else Object.assign(albumEn(target), { title: item.title || '', description: item.description || '' })
      }
    }
    editLocale.value = fromEnglish ? 'zh-CN' : 'en'
    dirty.value = true
    toast.show(fromEnglish ? '中文内容已生成，请检查后保存' : '英文内容已生成，请检查后保存', 'success')
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : 'AI 翻译失败'
  } finally { translating.value = false }
}
function assignProject(item: Project) {
  Object.assign(form, {
    ...item,
    category_uuid: item.category?.uuid || null,
    tag_uuids: item.tags.map((tag) => tag.uuid),
    certificate_uuids: item.certificates.map((certificate) => certificate.uuid),
    cover_asset_uuid: item.cover_asset?.uuid || null,
    links: item.links.map(({ label, url, link_type, sort_order }) => ({ label, url, link_type, sort_order })),
    sections: item.sections.map((section) => ({
      client_key: section.client_key || section.uuid || crypto.randomUUID(),
      title: section.title,
      body: section.body,
      section_type: section.section_type,
      display_mode: section.display_mode || 'text',
      asset_uuids: [...(section.asset_uuids || [])],
      album_uuid: section.album_uuid || null,
      heading_level: section.heading_level || 2,
      is_visible: section.is_visible !== false,
      sort_order: section.sort_order,
      translations: clonePlain(section.translations || {}),
    })),
    albums: item.albums.map((album) => ({
      uuid: album.uuid,
      title: album.title,
      description: album.description,
      display_mode: album.display_mode,
      asset_uuids: album.assets?.map((relation) => relation.asset.uuid) || [],
      sort_order: album.sort_order,
      translations: clonePlain(album.translations || {}),
    })),
    content_layout: normalizeLayout(item.content_layout || [], item.sections),
  })
  existingProjectImages.value = item.assets
    .map((relation) => relation.asset)
    .filter((asset) => asset.mime_type.startsWith('image/'))
  listFields.technologies = item.technologies.join('\n')
  listFields.contributions = item.contributions.join('\n')
  listFields.outcomes = item.outcomes.join('\n')
  const en = (item.translations?.en || {}) as Record<string, unknown>
  for (const key of Object.keys(englishProject) as Array<keyof typeof englishProject>) {
    const value = en[key]
    englishProject[key] = Array.isArray(value) ? value.join('\n') : String(value || '')
  }
}
async function load() {
  loading.value = true
  error.value = ''
  try {
    const [categoryData, tagData, assetData, folderData, certificateData] = await Promise.all([
      adminApi.categories(), adminApi.tags(), adminApi.assets({ page_size: 1000 }), adminApi.assetFolders(), adminApi.certificates(),
    ])
    categories.value = categoryData.items
    tags.value = tagData.items
    assets.value = assetData.items
    assetFolders.value = folderData.items
    certificates.value = certificateData.items
    if (!isNew.value) assignProject(await adminApi.project(String(route.params.uuid)))
    dirty.value = false
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : '项目加载失败'
  } finally {
    loading.value = false
  }
}
function addLink() {
  form.links.push({ label: '', url: '', link_type: 'other', sort_order: form.links.length })
  dirty.value = true
}
function addSection() {
  const clientKey = crypto.randomUUID()
  form.sections.push({
    client_key: clientKey,
    title: '',
    body: '',
    section_type: 'markdown',
    display_mode: 'text',
    asset_uuids: [],
    album_uuid: null,
    heading_level: 2,
    is_visible: true,
    sort_order: form.sections.length,
    translations: {},
  })
  form.content_layout.push({
    key: `custom:${clientKey}`,
    kind: 'custom',
    visible: true,
    sort_order: form.content_layout.length,
  })
  dirty.value = true
}
function buildDefaultLayout(sections: ProjectSection[]): ProjectContentLayoutItem[] {
  const builtins = Object.keys(builtinLabels).map((key, index) => ({
    key,
    kind: 'builtin' as const,
    visible: true,
    sort_order: index,
  }))
  return [
    ...builtins,
    ...sections.map((section, index) => ({
      key: `custom:${section.client_key || section.uuid || index}`,
      kind: 'custom' as const,
      visible: section.is_visible !== false,
      sort_order: builtins.length + index,
    })),
  ]
}
function normalizeLayout(layout: ProjectContentLayoutItem[], sections: ProjectSection[]) {
  const result = layout.map((entry) => ({ ...entry }))
  const existing = new Set(result.map((entry) => entry.key))
  for (const [index, key] of Object.keys(builtinLabels).entries()) {
    if (!existing.has(key)) result.push({ key, kind: 'builtin', visible: true, sort_order: index })
  }
  for (const [index, section] of sections.entries()) {
    const key = `custom:${section.client_key || section.uuid || index}`
    if (!existing.has(key)) {
      result.push({ key, kind: 'custom', visible: section.is_visible !== false, sort_order: result.length })
    }
  }
  return result.sort((left, right) => left.sort_order - right.sort_order)
}
function layoutLabel(item: ProjectContentLayoutItem) {
  if (item.kind === 'builtin') return builtinLabels[item.key] || item.key
  const section = form.sections.find((entry) => `custom:${entry.client_key}` === item.key)
  return section?.title || '未命名自定义章节'
}
function syncLayout() {
  const customKeys = new Set(form.sections.map((section) => `custom:${section.client_key}`))
  form.content_layout = form.content_layout.filter((entry) => entry.kind === 'builtin' || customKeys.has(entry.key))
  form.content_layout.forEach((entry, index) => {
    entry.sort_order = index
    if (entry.kind === 'custom') {
      const section = form.sections.find((item) => `custom:${item.client_key}` === entry.key)
      if (section) {
        section.sort_order = index
        section.is_visible = entry.visible
      }
    }
  })
  dirty.value = true
}
function dropLayout(targetIndex: number) {
  const sourceIndex = draggedLayoutIndex.value
  if (sourceIndex === null || sourceIndex === targetIndex) return
  const [entry] = form.content_layout.splice(sourceIndex, 1)
  form.content_layout.splice(targetIndex, 0, entry)
  draggedLayoutIndex.value = null
  syncLayout()
}
function removeSection(index: number) {
  const [section] = form.sections.splice(index, 1)
  form.content_layout = form.content_layout.filter((entry) => entry.key !== `custom:${section.client_key}`)
  syncLayout()
}
function openSectionPicker(index: number) {
  pickerSectionIndex.value = index
  pickerOpen.value = true
}
function confirmSectionAssets(uuids: string[]) {
  if (pickerSection.value) {
    const unique = [...new Set(uuids)]
    pickerSection.value.asset_uuids = pickerMultiple.value ? unique : unique.slice(0, 1)
  }
  pickerOpen.value = false
  dirty.value = true
}
function openAlbumPicker(index: number) {
  albumPickerIndex.value = index
  albumPickerOpen.value = true
}
function confirmAlbumAssets(uuids: string[]) {
  if (pickerAlbum.value) pickerAlbum.value.asset_uuids = [...new Set(uuids)]
  albumPickerOpen.value = false
  dirty.value = true
}
async function uploadFromAlbumPicker(files: File[], folderUuid: string | null = null) {
  if (!pickerAlbum.value || !files.length) return
  uploadingTarget.value = 'album-picker'
  try {
    for (const file of files) {
      if (!file.type.startsWith('image/')) throw new Error('项目相册只能上传图片')
      const asset = await adminApi.uploadAsset(file, true, 'project-album', folderUuid || '')
      if (!assets.value.some((item) => item.uuid === asset.uuid)) assets.value.unshift(asset)
      const selected = pickerAlbum.value.asset_uuids || (pickerAlbum.value.asset_uuids = [])
      if (!selected.includes(asset.uuid)) {
        selected.push(asset.uuid)
      }
    }
    toast.show(`${files.length} 个图片已上传到资源库并加入相册`, 'success')
    dirty.value = true
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : '相册图片上传失败'
  } finally {
    uploadingTarget.value = ''
  }
}
async function uploadFromPicker(files: File[], folderUuid: string | null = null) {
  if (!pickerSection.value || !files.length) return
  uploadingTarget.value = 'resource-picker'
  try {
    for (const file of files) {
      const asset = await adminApi.uploadAsset(file, true, 'project-content', folderUuid || '')
      if (!assets.value.some((item) => item.uuid === asset.uuid)) assets.value.unshift(asset)
      if (pickerMultiple.value) {
        if (!pickerSection.value.asset_uuids.includes(asset.uuid)) pickerSection.value.asset_uuids.push(asset.uuid)
      } else {
        pickerSection.value.asset_uuids = [asset.uuid]
      }
    }
    toast.show(`${files.length} 个文件已上传到资源库并选中`, 'success')
    dirty.value = true
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : '文件上传失败'
  } finally {
    uploadingTarget.value = ''
  }
}
function fileSize(size: number) {
  if (size < 1024 * 1024) return `${Math.max(1, Math.round(size / 1024))} KB`
  return `${(size / 1024 / 1024).toFixed(1)} MB`
}
function addAlbum() {
  form.albums.push({
    uuid: crypto.randomUUID(),
    title: `相册 ${form.albums.length + 1}`,
    description: '',
    display_mode: 'grid',
    asset_uuids: [],
    sort_order: form.albums.length,
    translations: {},
  })
  dirty.value = true
}
function toggleSectionPreview(index: number) {
  const next = new Set(previewSections.value)
  if (next.has(index)) next.delete(index)
  else next.add(index)
  previewSections.value = next
}
function mediaSelection(section: ProjectSection) {
  return section.asset_uuids || (section.asset_uuids = [])
}
function sectionAssetOptions(section: ProjectSection) {
  if (['single', 'gallery', 'carousel'].includes(section.display_mode)) return imageAssets.value
  if (section.display_mode === 'video') return assets.value.filter((asset) => asset.mime_type.startsWith('video/'))
  if (section.display_mode === 'audio') return assets.value.filter((asset) => asset.mime_type.startsWith('audio/'))
  if (section.display_mode === 'attachments') {
    return assets.value.filter((asset) =>
      !asset.mime_type.startsWith('image/')
      && !asset.mime_type.startsWith('video/')
      && !asset.mime_type.startsWith('audio/'),
    )
  }
  return assets.value
}
function selectedAssets(section: ProjectSection) {
  return sectionAssetOptions(section).filter((asset) => mediaSelection(section).includes(asset.uuid))
}
function sectionAccept(section: ProjectSection) {
  if (['single', 'gallery', 'carousel'].includes(section.display_mode)) return 'image/*'
  if (section.display_mode === 'video') return 'video/*'
  if (section.display_mode === 'audio') return 'audio/*'
  if (section.display_mode === 'attachments') return '.pdf,.docx,.xlsx,.pptx,.txt,.md,.json,.csv,.yaml,.yml,.zip'
  return 'image/*,video/*,audio/*,.pdf,.docx,.xlsx,.pptx,.txt,.md,.json,.csv,.yaml,.yml,.zip'
}
function assetTypeLabel(asset: Asset) {
  if (asset.mime_type.startsWith('video/')) return '视频'
  if (asset.mime_type.startsWith('audio/')) return '音频'
  if (asset.extension === '.zip') return '压缩附件'
  return asset.extension.replace('.', '').toUpperCase() || '文件'
}
async function uploadFiles(
  event: Event,
  target: ProjectSection | ProjectAlbum,
  targetKey: string,
  imagesOnly = false,
) {
  const input = event.target as HTMLInputElement
  const files = Array.from(input.files || [])
  if (!files.length) return
  if (imagesOnly && files.some((file) => !file.type.startsWith('image/'))) {
    error.value = '项目相册只接收图片；其他媒体请添加到内容区块'
    input.value = ''
    return
  }
  uploadingTarget.value = targetKey
  try {
    const targetUuids = 'asset_uuids' in target
      ? (target.asset_uuids || (target.asset_uuids = []))
      : []
    for (const file of files) {
      const asset = await adminApi.uploadAsset(file, true, 'project-content')
      if (!assets.value.some((item) => item.uuid === asset.uuid)) assets.value.unshift(asset)
      if (!targetUuids.includes(asset.uuid)) targetUuids.push(asset.uuid)
    }
    dirty.value = true
    toast.show(`${files.length} 个文件已上传并加入内容`, 'success')
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : '文件上传失败'
  } finally {
    uploadingTarget.value = ''
    input.value = ''
  }
}
async function save(status?: Project['status']) {
  saving.value = true
  error.value = ''
  try {
    if (status) form.status = status
    syncLayout()
    form.technologies = lines(listFields.technologies)
    form.contributions = lines(listFields.contributions)
    form.outcomes = lines(listFields.outcomes)
    form.translations = {
      ...(form.translations || {}),
      en: {
        title: englishProject.title, subtitle: englishProject.subtitle, summary: englishProject.summary,
        content: englishProject.content, background: englishProject.background, problem: englishProject.problem,
        solution: englishProject.solution, architecture: englishProject.architecture, role: englishProject.role,
        seo_title: englishProject.seo_title, seo_description: englishProject.seo_description,
        contributions: lines(englishProject.contributions), outcomes: lines(englishProject.outcomes),
      },
    }
    const payload = clonePlain(form)
    const project = isNew.value
      ? await adminApi.createProject(payload)
      : await adminApi.updateProject(String(route.params.uuid), payload)
    dirty.value = false
    toast.show(status === 'published' ? '项目已发布' : '项目已保存', 'success')
    if (isNew.value) await router.replace(`/admin/projects/${project.uuid}`)
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : '保存失败'
  } finally {
    saving.value = false
  }
}
onBeforeRouteLeave(() => !dirty.value || window.confirm('有尚未保存的修改，确定离开吗？'))
onMounted(load)
</script>

<template>
  <div class="admin-page project-editor">
    <header class="admin-page-heading admin-page-heading--sticky">
      <div>
        <RouterLink class="back-link" to="/admin/projects"><ArrowLeft :size="16" />项目列表</RouterLink>
        <h1>{{ isNew ? '新建项目' : '编辑项目' }}</h1>
      </div>
      <div class="editor-actions">
        <button type="button" class="button button--outline" @click="sortModalOpen = true"><GripVertical :size="16" />排序</button>
        <RouterLink v-if="!isNew" class="button button--outline" :to="`/projects/${route.params.uuid}`" target="_blank"><Eye :size="16" />预览</RouterLink>
        <button class="button button--outline" :disabled="saving" @click="save()">保存草稿</button>
        <button class="button button--dark" :disabled="saving" @click="save('published')"><Save :size="16" />{{ saving ? '保存中…' : '保存并发布' }}</button>
      </div>
    </header>
    <LoadingState v-if="loading" :rows="10" />
    <ErrorState v-else-if="error && !form.title" :message="error" @retry="load" />
    <form v-else class="editor-grid" @change="dirty = true" @submit.prevent="save()">
      <div class="editor-main">
        <section class="editor-language-bar">
          <div class="language-tabs" role="tablist" aria-label="内容编辑语言">
            <button type="button" :class="{ active: editLocale === 'zh-CN' }" @click="editLocale = 'zh-CN'">中文内容</button>
            <button type="button" :class="{ active: editLocale === 'en' }" @click="editLocale = 'en'">English</button>
          </div>
          <label>内容语言
            <select v-model="form.content_language_mode">
              <option value="bilingual">中英双语</option>
              <option value="single_zh">仅中文</option>
              <option value="single_en">English only</option>
            </select>
          </label>
          <button type="button" class="button button--outline" :disabled="translating" @click="translateProject"><Languages :size="16" />{{ translating ? '翻译中…' : editLocale === 'en' ? 'AI 翻译为中文' : 'AI 翻译为英文' }}</button>
        </section>
        <section v-if="editLocale === 'zh-CN'" class="form-section">
          <div class="form-section__heading"><span>01</span><div><h2>基本信息</h2><p>用于项目列表和详情页首屏。</p></div></div>
          <div class="form-grid">
            <label class="span-2">项目名称<input v-model="form.title" required maxlength="180" /></label>
            <label class="span-2">副标题<input v-model="form.subtitle" maxlength="240" /></label>
            <label class="span-2">一句话摘要<textarea v-model="form.summary" required rows="3" /></label>
            <label>开始时间<input v-model="form.start_date" placeholder="2025.10" /></label>
            <label>结束时间<input v-model="form.end_date" placeholder="至今" /></label>
            <label class="span-2">我的角色<input v-model="form.role" /></label>
            <label>团队规模<input v-model.number="form.team_size" type="number" min="1" /></label>
            <label>项目进展<select v-model="form.project_state"><option value="active">进行中</option><option value="completed">已完成</option><option value="research">研究中</option></select></label>
          </div>
        </section>
        <section v-if="editLocale === 'zh-CN'" class="form-section">
          <div class="form-section__heading"><span>02</span><div><h2>案例研究</h2><p>说明为什么做、如何做和做成了什么。</p></div></div>
          <div class="form-grid">
            <label class="span-2">项目背景<textarea v-model="form.background" rows="5" /></label>
            <label class="span-2">需要解决的问题<textarea v-model="form.problem" rows="5" /></label>
            <label class="span-2">解决方案<textarea v-model="form.solution" rows="6" /></label>
            <label class="span-2">系统架构 / 技术路线<textarea v-model="form.architecture" rows="5" /></label>
            <label class="span-2">完整介绍（Markdown）<textarea v-model="form.content" rows="9" /></label>
          </div>
        </section>
        <section v-if="editLocale === 'zh-CN'" class="form-section">
          <div class="form-section__heading"><span>03</span><div><h2>证据与结果</h2><p>每行一项，公开端会按结构展示。</p></div></div>
          <div class="form-grid">
            <label>技术栈<textarea v-model="listFields.technologies" rows="8" placeholder="PyTorch&#10;Transformer" /></label>
            <label>我的贡献<textarea v-model="listFields.contributions" rows="8" /></label>
            <label class="span-2">关键成果<textarea v-model="listFields.outcomes" rows="7" /></label>
          </div>
        </section>
        <section v-else class="form-section form-section--translation">
          <div class="form-section__heading"><span>EN</span><div><h2>English content</h2><p>English pages use these fields and fall back to the primary content when empty.</p></div></div>
          <div class="form-grid">
            <label class="span-2">Project title<input v-model="englishProject.title" maxlength="180" /></label>
            <label class="span-2">Subtitle<input v-model="englishProject.subtitle" maxlength="240" /></label>
            <label class="span-2">Summary<textarea v-model="englishProject.summary" rows="3" /></label>
            <label class="span-2">Role<input v-model="englishProject.role" /></label>
            <label class="span-2">Background<textarea v-model="englishProject.background" rows="5" /></label>
            <label class="span-2">Problem<textarea v-model="englishProject.problem" rows="5" /></label>
            <label class="span-2">Solution<textarea v-model="englishProject.solution" rows="6" /></label>
            <label class="span-2">Architecture<textarea v-model="englishProject.architecture" rows="5" /></label>
            <label class="span-2">Full description (Markdown)<textarea v-model="englishProject.content" rows="9" /></label>
            <label>Contributions (one per line)<textarea v-model="englishProject.contributions" rows="7" /></label>
            <label>Outcomes (one per line)<textarea v-model="englishProject.outcomes" rows="7" /></label>
            <label>SEO title<input v-model="englishProject.seo_title" /></label>
            <label>SEO description<textarea v-model="englishProject.seo_description" rows="3" /></label>
          </div>
        </section>
        <section class="form-section">
          <div class="form-section__heading"><span>04</span><div><h2>外部链接</h2><p>在线演示、代码仓库和其他相关页面。</p></div><button type="button" class="button button--outline button--small" @click="addLink"><Plus :size="15" />添加链接</button></div>
          <div v-if="!form.links.length" class="inline-empty">尚未添加链接</div>
          <div v-for="(link, index) in form.links" :key="index" class="repeat-row repeat-row--link">
            <input v-model="link.label" required placeholder="链接名称" />
            <input v-model="link.url" required type="url" placeholder="https://..." />
            <select v-model="link.link_type"><option value="demo">在线演示</option><option value="repository">代码仓库</option><option value="document">文档</option><option value="other">其他</option></select>
            <button type="button" class="icon-button danger-text" aria-label="删除链接" @click="form.links.splice(index, 1)"><Trash2 :size="17" /></button>
          </div>
        </section>
        <section class="form-section">
          <div class="form-section__heading">
            <span>05</span>
            <div><h2>自定义章节</h2><p>使用安全 Markdown 扩展案例研究。</p></div>
            <div class="form-section__actions">
              <button type="button" class="button button--outline button--small" @click="addSection"><Plus :size="15" />添加章节</button>
            </div>
          </div>
          <div v-if="!form.sections.length" class="inline-empty">尚未添加自定义章节</div>
          <div v-for="{ section, index } in orderedSectionEntries" :key="section.client_key" class="repeat-section content-block-editor">
            <div class="content-block-editor__heading">
              <input v-if="editLocale === 'zh-CN'" v-model="section.title" required placeholder="章节标题" />
              <input v-else v-model="sectionEn(section).title" placeholder="Section title" />
              <button type="button" class="button button--outline button--small" @click="toggleSectionPreview(index)">
                <Pencil v-if="previewSections.has(index)" :size="15" />
                <Eye v-else :size="15" />
                {{ previewSections.has(index) ? '继续编辑' : '区块预览' }}
              </button>
              <button type="button" class="icon-button danger-text" aria-label="删除章节" @click="removeSection(index)"><Trash2 :size="17" /></button>
            </div>
            <div v-if="previewSections.has(index)" class="content-block-preview">
              <MarkdownContent v-if="section.body" :source="section.body" />
              <div
                v-if="selectedAssets(section).some((asset) => asset.mime_type.startsWith('image/'))"
                class="content-block-preview__media"
                :class="`is-${section.display_mode}`"
              >
                <img
                  v-for="asset in selectedAssets(section).filter((item) => item.mime_type.startsWith('image/'))"
                  :key="asset.uuid"
                  :src="asset.thumbnail_url || asset.content_url"
                  :alt="asset.display_name"
                />
              </div>
              <div
                v-if="selectedAssets(section).some((asset) => !asset.mime_type.startsWith('image/'))"
                class="content-block-preview__files"
              >
                <span
                  v-for="asset in selectedAssets(section).filter((item) => !item.mime_type.startsWith('image/'))"
                  :key="asset.uuid"
                >
                  <Video v-if="asset.mime_type.startsWith('video/')" :size="16" />
                  <Music2 v-else-if="asset.mime_type.startsWith('audio/')" :size="16" />
                  <FileArchive v-else-if="asset.extension === '.zip'" :size="16" />
                  <FileText v-else :size="16" />
                  {{ asset.display_name }} · {{ assetTypeLabel(asset) }}
                </span>
              </div>
              <div v-if="selectedAssets(section).some((asset) => asset.mime_type.startsWith('video/'))" class="section-video-grid">
                <video
                  v-for="asset in selectedAssets(section).filter((item) => item.mime_type.startsWith('video/'))"
                  :key="asset.uuid"
                  controls
                  preload="metadata"
                  :poster="asset.thumbnail_url || undefined"
                ><source :src="asset.content_url" :type="asset.mime_type" /></video>
              </div>
              <div v-if="selectedAssets(section).some((asset) => asset.mime_type.startsWith('audio/'))" class="section-audio-list">
                <article v-for="asset in selectedAssets(section).filter((item) => item.mime_type.startsWith('audio/'))" :key="asset.uuid">
                  <strong>{{ asset.display_name }}</strong>
                  <audio controls preload="metadata"><source :src="asset.content_url" :type="asset.mime_type" /></audio>
                </article>
              </div>
              <div v-if="section.display_mode === 'album'" class="inline-empty">
                将引用“{{ form.albums.find((album) => album.uuid === section.album_uuid)?.title || '未选择相册' }}”
              </div>
            </div>
            <template v-else>
              <textarea v-if="editLocale === 'zh-CN'" v-model="section.body" rows="8" placeholder="Markdown 内容，可与下方图片组合展示" />
              <textarea v-else v-model="sectionEn(section).body" rows="8" placeholder="English Markdown content" />
              <label class="field-stack">
                <span>区块展示方式</span>
                <BaseSelect
                  v-model="section.display_mode"
                  label="区块展示方式"
                  :options="sectionModeOptions"
                />
              </label>
              <label class="field-stack">
                <span>章节标题层级</span>
                <select v-model.number="section.heading_level">
                  <option :value="2">二级标题（主要章节）</option>
                  <option :value="3">三级标题（子章节）</option>
                  <option :value="4">四级标题（小节）</option>
                </select>
              </label>
              <label v-if="section.display_mode === 'album'" class="field-stack">
                <span>引用相册</span>
                <BaseSelect
                  v-model="section.album_uuid"
                  label="引用相册"
                  :options="albumOptions"
                  placeholder="请选择相册"
                />
              </label>
              <div v-if="section.display_mode !== 'text' && section.display_mode !== 'album'" class="section-resource-summary">
                <div class="inline-media-picker__actions">
                  <span>已关联 {{ section.asset_uuids.length }} 个资源</span>
                  <button type="button" class="button button--outline button--small" @click="openSectionPicker(index)">
                    <FolderOpen :size="15" />从资源库选择或上传
                  </button>
                </div>
                <div v-if="selectedAssets(section).length" class="selected-resource-list">
                  <article v-for="asset in selectedAssets(section)" :key="asset.uuid">
                    <img v-if="asset.thumbnail_url" :src="asset.thumbnail_url" :alt="asset.display_name" />
                    <FileText v-else :size="24" />
                    <div><strong>{{ asset.display_name }}</strong><span>{{ assetTypeLabel(asset) }} · {{ fileSize(asset.size) }}</span></div>
                    <RouterLink :to="`/assets/${asset.uuid}`" target="_blank">在线预览</RouterLink>
                    <button type="button" class="icon-button" aria-label="移除资源" @click="section.asset_uuids = section.asset_uuids.filter((uuid) => uuid !== asset.uuid)"><X :size="15" /></button>
                  </article>
                </div>
                <div v-else class="inline-empty">尚未关联资源。可从附件库选择，或直接上传新文件。</div>
              </div>
              <div v-else-if="section.display_mode !== 'text'" class="inline-media-picker inline-media-picker--legacy">
                <div class="inline-media-picker__actions">
                  <span>选择资源，或从这里批量上传</span>
                  <label class="button button--outline button--small">
                    <UploadCloud :size="15" />
                    {{ uploadingTarget === `section-${index}` ? '上传中…' : '批量上传' }}
                    <input
                      type="file"
                      :accept="sectionAccept(section)"
                      multiple
                      :disabled="Boolean(uploadingTarget)"
                      @change="uploadFiles($event, section, `section-${index}`)"
                    />
                  </label>
                </div>
                <div class="media-choice-grid">
                  <label v-for="asset in sectionAssetOptions(section)" :key="asset.uuid" :class="{ selected: mediaSelection(section).includes(asset.uuid) }">
                    <input v-model="section.asset_uuids" type="checkbox" :value="asset.uuid" />
                    <img v-if="asset.mime_type.startsWith('image/')" :src="asset.thumbnail_url || asset.content_url" :alt="asset.display_name" />
                    <span v-else class="media-choice-grid__file">
                      <Video v-if="asset.mime_type.startsWith('video/')" :size="24" />
                      <Music2 v-else-if="asset.mime_type.startsWith('audio/')" :size="24" />
                      <FileArchive v-else-if="asset.extension === '.zip'" :size="24" />
                      <FileText v-else :size="24" />
                      <small>{{ assetTypeLabel(asset) }}</small>
                    </span>
                    <span>{{ asset.display_name }}</span>
                  </label>
                </div>
              </div>
            </template>
          </div>
        </section>
        <section class="form-section">
          <div class="form-section__heading">
            <span>06</span>
            <div><h2>项目相册</h2><p>创建可复用相册，在任意内容区块中以网格或轮播方式引用。</p></div>
            <button type="button" class="button button--outline button--small" @click="addAlbum"><Images :size="15" />新建相册</button>
          </div>
          <div v-if="!form.albums.length" class="inline-empty">尚未创建项目相册</div>
          <div v-for="(album, index) in form.albums" :key="album.uuid" class="album-editor">
            <div class="album-editor__heading">
              <ImagePlus :size="20" />
              <input v-if="editLocale === 'zh-CN'" v-model="album.title" required placeholder="相册名称" />
              <input v-else v-model="albumEn(album).title" placeholder="Album title" />
              <button type="button" class="icon-button danger-text" aria-label="删除相册" @click="form.albums.splice(index, 1)"><Trash2 :size="17" /></button>
            </div>
            <textarea v-if="editLocale === 'zh-CN'" v-model="album.description" rows="2" placeholder="相册说明（可选）" />
            <textarea v-else v-model="albumEn(album).description" rows="2" placeholder="Album description (optional)" />
            <BaseSelect
              v-model="album.display_mode"
              label="相册展示方式"
              :options="albumModeOptions"
            />
            <div class="inline-media-picker__actions">
              <span>相册图片（{{ album.asset_uuids?.length || 0 }}）</span>
              <button type="button" class="button button--outline button--small" @click="openAlbumPicker(index)">
                <FolderOpen :size="15" />从资源库选择或上传
              </button>
            </div>
            <div v-if="album.asset_uuids?.length" class="selected-resource-list selected-resource-list--images">
              <article v-for="asset in imageAssets.filter((item) => album.asset_uuids?.includes(item.uuid))" :key="asset.uuid">
                <img :src="asset.thumbnail_url || asset.content_url" :alt="asset.display_name" />
                <div><strong>{{ asset.display_name }}</strong><span>{{ fileSize(asset.size) }}</span></div>
                <RouterLink :to="`/assets/${asset.uuid}`" target="_blank">预览</RouterLink>
                <button type="button" class="icon-button" aria-label="移出相册" @click="album.asset_uuids = album.asset_uuids?.filter((uuid) => uuid !== asset.uuid) || []"><X :size="15" /></button>
              </article>
            </div>
            <div v-else class="inline-empty">相册中尚未选择图片</div>
          </div>
        </section>
      </div>
      <aside class="editor-side">
        <section class="form-section">
          <h2>发布设置</h2>
          <label>状态<select v-model="form.status"><option value="draft">草稿</option><option value="published">已发布</option><option value="hidden">隐藏</option><option value="archived">归档</option></select></label>
          <label>分类<select v-model="form.category_uuid"><option :value="null">未分类</option><option v-for="item in categories" :key="item.uuid" :value="item.uuid">{{ item.name }}</option></select></label>
          <label>排序值<input v-model.number="form.sort_order" type="number" /></label>
          <label class="check-label"><input v-model="form.is_featured" type="checkbox" />设为推荐项目</label>
          <label class="check-label"><input v-model="form.is_open_source" type="checkbox" />这是开源项目</label>
        </section>
        <section class="form-section">
          <h2>项目封面</h2>
          <select v-model="form.cover_asset_uuid"><option :value="null">自动组合项目媒体</option><option v-for="asset in imageAssets" :key="asset.uuid" :value="asset.uuid">{{ asset.display_name }}</option></select>
          <img v-if="form.cover_asset_uuid" class="cover-preview" :src="assets.find((item) => item.uuid === form.cover_asset_uuid)?.thumbnail_url || ''" alt="当前项目封面预览" />
          <div v-else-if="autoCoverPreview.length" class="cover-collage-preview">
            <img v-for="asset in autoCoverPreview" :key="asset.uuid" :src="asset.thumbnail_url || asset.content_url" :alt="asset.display_name" />
            <span>系统将实时组合当前项目图片</span>
          </div>
          <p v-else class="form-hint">未设置固定封面。上传并关联图片后，系统会自动生成动态组合封面。</p>
          <RouterLink class="text-link" to="/admin/assets">前往资源库上传</RouterLink>
        </section>
        <section class="form-section">
          <h2>标签</h2>
          <div class="check-grid"><label v-for="tag in tags" :key="tag.uuid"><input v-model="form.tag_uuids" type="checkbox" :value="tag.uuid" />{{ tag.name }}</label></div>
        </section>
        <section class="form-section">
          <h2>关联证书与荣誉</h2>
          <div v-if="certificates.length" class="check-grid">
            <label v-for="certificate in certificates" :key="certificate.uuid">
              <input v-model="form.certificate_uuids" type="checkbox" :value="certificate.uuid" />
              {{ certificate.name }}
            </label>
          </div>
          <div v-else class="inline-empty">尚未创建证书</div>
          <RouterLink class="text-link" to="/admin/certificates">管理证书</RouterLink>
        </section>
        <section class="form-section">
          <h2>SEO</h2>
          <label>SEO 标题<input v-model="form.seo_title" maxlength="180" /></label>
          <label>SEO 描述<textarea v-model="form.seo_description" rows="5" maxlength="320" /></label>
        </section>
      </aside>
      <div v-if="error" class="form-error editor-error">{{ error }}</div>
    </form>
    <ResourcePickerModal
      :open="pickerOpen"
      :assets="pickerAssets"
      :folders="assetFolders"
      :selected="pickerSection?.asset_uuids || []"
      :multiple="pickerMultiple"
      :accept="pickerSection ? sectionAccept(pickerSection) : '*/*'"
      :uploading="uploadingTarget === 'resource-picker'"
      title="选择章节资源"
      @close="pickerOpen = false"
      @confirm="confirmSectionAssets"
      @upload="uploadFromPicker"
    />
    <ResourcePickerModal
      :open="albumPickerOpen"
      :assets="imageAssets"
      :folders="assetFolders"
      :selected="pickerAlbum?.asset_uuids || []"
      multiple
      accept="image/*"
      :uploading="uploadingTarget === 'album-picker'"
      title="选择相册图片"
      @close="albumPickerOpen = false"
      @confirm="confirmAlbumAssets"
      @upload="uploadFromAlbumPicker"
    />
    <Teleport to="body">
      <Transition name="modal">
        <div v-if="sortModalOpen" class="resource-modal content-sort-modal" role="dialog" aria-modal="true" aria-label="项目内容排序" @click.self="sortModalOpen = false">
          <div class="resource-modal__panel">
            <header>
              <div>
                <span class="eyebrow">Content outline</span>
                <h2>项目内容排序</h2>
                <p>拖动统一调整内置区块和自定义章节顺序；隐藏后公开页面不会展示。</p>
              </div>
              <button type="button" class="icon-button" aria-label="关闭排序" @click="sortModalOpen = false"><X :size="20" /></button>
            </header>
            <div class="content-outline-editor">
              <div class="content-outline-editor__intro">
                <div><strong>页面内容目录</strong><span>排序会同时应用到项目页面和编辑区块列表。</span></div>
                <small>{{ form.content_layout.filter((item) => item.visible).length }} 个区块公开展示</small>
              </div>
              <div class="content-outline-editor__list">
                <div
                  v-for="(item, layoutIndex) in form.content_layout"
                  :key="item.key"
                  class="content-outline-item"
                  :class="{ 'is-hidden': !item.visible }"
                  draggable="true"
                  @dragstart="draggedLayoutIndex = layoutIndex"
                  @dragover.prevent
                  @drop="dropLayout(layoutIndex)"
                >
                  <GripVertical :size="18" />
                  <span class="content-outline-item__number">{{ String(layoutIndex + 1).padStart(2, '0') }}</span>
                  <div><strong>{{ layoutLabel(item) }}</strong><small>{{ item.kind === 'builtin' ? '内置区块' : '自定义章节' }}</small></div>
                  <label class="switch-label"><input v-model="item.visible" type="checkbox" @change="syncLayout" /><span>{{ item.visible ? '显示' : '隐藏' }}</span></label>
                </div>
              </div>
            </div>
            <footer>
              <span>关闭后仍需点击“保存项目”写入数据库</span>
              <button type="button" class="button button--dark" @click="syncLayout(); sortModalOpen = false">完成排序</button>
            </footer>
          </div>
        </div>
      </Transition>
    </Teleport>
  </div>
</template>
