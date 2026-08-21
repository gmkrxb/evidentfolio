<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { Check, ExternalLink, File, Folder, Search, UploadCloud, X } from 'lucide-vue-next'
import type { Asset, AssetFolder } from '@/types'

const props = withDefaults(defineProps<{
  open: boolean
  assets: Asset[]
  folders?: AssetFolder[]
  selected: string[]
  multiple?: boolean
  accept?: string
  title?: string
  uploading?: boolean
}>(), {
  multiple: true,
  accept: '*/*',
  title: '从资源库选择',
  folders: () => [],
})
const emit = defineEmits<{
  close: []
  confirm: [uuids: string[]]
  upload: [files: File[], folderUuid: string | null]
}>()

const query = ref('')
const type = ref('all')
const draft = ref<string[]>([])
const currentFolder = ref<string | null>(null)

watch(() => props.open, (open) => {
  if (open) {
    draft.value = [...props.selected]
    query.value = ''
    type.value = 'all'
    currentFolder.value = null
  }
})

const typeOptions = computed(() => {
  const available = new Set<string>(props.assets.map((asset) => {
    if (asset.mime_type.startsWith('image/')) return 'image'
    if (asset.mime_type.startsWith('video/')) return 'video'
    if (asset.mime_type.startsWith('audio/')) return 'audio'
    if (asset.mime_type === 'application/pdf') return 'pdf'
    return 'file'
  }))
  return [
    ['all', '全部'],
    ['image', '图片'],
    ['video', '视频'],
    ['audio', '音频'],
    ['pdf', 'PDF'],
    ['file', '其他文件'],
  ].filter(([value]) => value === 'all' || available.has(value))
})

const filtered = computed(() => {
  const keyword = query.value.trim().toLowerCase()
  return props.assets.filter((asset) => {
    const assetType = asset.mime_type.startsWith('image/') ? 'image'
      : asset.mime_type.startsWith('video/') ? 'video'
        : asset.mime_type.startsWith('audio/') ? 'audio'
          : asset.mime_type === 'application/pdf' ? 'pdf' : 'file'
    return (type.value === 'all' || type.value === assetType)
      && (keyword || (asset.folder?.uuid || null) === currentFolder.value)
      && (!keyword || `${asset.display_name} ${asset.original_name} ${asset.extension}`.toLowerCase().includes(keyword))
  })
})
const childFolders = computed(() =>
  props.folders.filter((folder) => folder.parent_uuid === currentFolder.value),
)
const breadcrumbs = computed(() =>
  currentFolder.value
    ? props.folders.find((folder) => folder.uuid === currentFolder.value)?.path || []
    : [],
)

function toggle(uuid: string) {
  if (!props.multiple) {
    draft.value = [uuid]
    return
  }
  draft.value = draft.value.includes(uuid)
    ? draft.value.filter((item) => item !== uuid)
    : [...draft.value, uuid]
}
function fileSize(size: number) {
  if (size < 1024) return `${size} B`
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`
  return `${(size / 1024 / 1024).toFixed(1)} MB`
}
function upload(event: Event) {
  const input = event.target as HTMLInputElement
  const files = Array.from(input.files || [])
  if (files.length) emit('upload', files, currentFolder.value)
  input.value = ''
}
</script>

<template>
  <Teleport to="body">
    <Transition name="modal">
      <div v-if="open" class="resource-modal" role="dialog" aria-modal="true" :aria-label="title" @click.self="emit('close')">
        <div class="resource-modal__panel">
          <header>
            <div>
              <span class="eyebrow">Asset library</span>
              <h2>{{ title }}</h2>
              <p>{{ multiple ? '可选择多个资源' : '该展示方式只允许选择一个资源' }}，上传的新文件也会保存到系统资源库。</p>
            </div>
            <button type="button" class="icon-button" aria-label="关闭" @click="emit('close')"><X :size="20" /></button>
          </header>
          <div class="resource-modal__toolbar">
            <label class="search-field">
              <Search :size="17" />
              <input v-model="query" type="search" placeholder="搜索文件名称、类型或扩展名" />
            </label>
            <div class="resource-modal__types">
              <button
                v-for="[value, label] in typeOptions"
                :key="value"
                type="button"
                :class="{ active: type === value }"
                @click="type = value"
              >{{ label }}</button>
            </div>
            <label class="button button--outline button--small">
              <UploadCloud :size="15" />{{ uploading ? '上传中…' : '上传到资源库' }}
              <input type="file" :accept="accept" :multiple="multiple" :disabled="uploading" @change="upload" />
            </label>
          </div>
          <div v-if="folders.length" class="resource-modal__folders">
            <nav class="asset-breadcrumbs">
              <button @click="currentFolder = null">全部目录</button>
              <template v-for="part in breadcrumbs" :key="part.uuid">
                <span>/</span><button @click="currentFolder = part.uuid">{{ part.name }}</button>
              </template>
              <small v-if="query">正在全局搜索，结果不受当前文件夹限制</small>
            </nav>
            <div v-if="childFolders.length && !query" class="resource-modal__folder-grid">
              <button v-for="folder in childFolders" :key="folder.uuid" @click="currentFolder = folder.uuid">
                <Folder :size="19" /><span>{{ folder.name }}</span><small>{{ folder.asset_count }}</small>
              </button>
            </div>
          </div>
          <div v-if="filtered.length" class="resource-modal__grid">
            <article
              v-for="asset in filtered"
              :key="asset.uuid"
              :class="{ selected: draft.includes(asset.uuid) }"
              @click="toggle(asset.uuid)"
            >
              <div class="resource-modal__preview">
                <img v-if="asset.thumbnail_url" :src="asset.thumbnail_url" :alt="asset.display_name" loading="lazy" />
                <File v-else :size="34" />
                <span v-if="draft.includes(asset.uuid)" class="resource-modal__check"><Check :size="15" /></span>
              </div>
              <div class="resource-modal__meta">
                <strong :title="asset.display_name">{{ asset.display_name }}</strong>
                <span>{{ asset.extension.replace('.', '').toUpperCase() || asset.mime_type }} · {{ fileSize(asset.size) }}</span>
              </div>
              <RouterLink
                class="icon-button"
                :to="`/assets/${asset.uuid}`"
                target="_blank"
                aria-label="在线预览"
                @click.stop
              ><ExternalLink :size="16" /></RouterLink>
            </article>
          </div>
          <div v-else class="inline-empty">资源库中没有符合当前条件的文件。</div>
          <footer>
            <span>已选择 {{ draft.length }} 项</span>
            <div>
              <button type="button" class="button button--outline" @click="emit('close')">取消</button>
              <button type="button" class="button button--dark" @click="emit('confirm', draft)">确认选择</button>
            </div>
          </footer>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>
