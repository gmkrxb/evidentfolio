<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, ref, watch } from 'vue'
import { Check, ExternalLink, File as FileIcon, Folder, FolderOpen, Search, UploadCloud, X } from 'lucide-vue-next'
import { adminApi } from '@/api/admin'
import LoadingState from '@/components/ui/LoadingState.vue'
import type { Asset, AssetFolder } from '@/types'

const props = withDefaults(defineProps<{
  open: boolean; assets?: Asset[]; folders?: AssetFolder[]; selected: string[]
  multiple?: boolean; accept?: string; title?: string; exclude?: string[]; confirmLabel?: string; busy?: boolean
}>(), { multiple: true, accept: '*/*', title: '从资源库选择', assets: () => [], folders: () => [], exclude: () => [], confirmLabel: '确认选择' })
const emit = defineEmits<{ close: []; confirm: [uuids: string[], assets: Asset[]]; uploaded: [assets: Asset[]] }>()
const dialog = ref<HTMLDialogElement>()
const uploadInput = ref<HTMLInputElement>()
const library = ref<Asset[]>([])
const directories = ref<AssetFolder[]>([])
const query = ref('')
const type = ref('all')
const draft = ref<string[]>([])
const currentFolder = ref('all')
const loading = ref(false)
const uploading = ref(false)
const uploadLabel = ref('')
const error = ref('')
let generation = 0
let previousOverflow: string | null = null

function matchesAccept(asset: { mime_type: string; extension: string }) {
  return props.accept.split(',').some((raw) => {
    const value = raw.trim().toLowerCase()
    return value === '*/*' || !value || (value.startsWith('.') ? asset.extension.toLowerCase() === value
      : value.endsWith('/*') ? asset.mime_type.startsWith(value.slice(0, -1)) : asset.mime_type === value)
  })
}
const eligible = computed(() => library.value.filter((asset) => !props.exclude.includes(asset.uuid) && matchesAccept(asset)))
const fileType = (asset: Asset) => asset.mime_type.split('/')[0] === 'image' ? 'image' : asset.mime_type === 'application/pdf' ? 'pdf' : asset.mime_type.startsWith('video/') ? 'video' : asset.mime_type.startsWith('audio/') ? 'audio' : 'file'
const typeOptions = computed(() => [['all', '全部类型'], ['image', '图片'], ['video', '视频'], ['audio', '音频'], ['pdf', 'PDF'], ['file', '其他']].filter(([value]) => value === 'all' || eligible.value.some((asset) => fileType(asset) === value)))
const folderRows = computed(() => [...directories.value].sort((a, b) => a.path.map(p => p.name).join('/').localeCompare(b.path.map(p => p.name).join('/'))))
const folderName = computed(() => currentFolder.value === 'all' ? '全部资源' : currentFolder.value === 'unfiled' ? '未分类' : directories.value.find(folder => folder.uuid === currentFolder.value)?.path.map(p => p.name).join(' / ') || '资源库')
const filtered = computed(() => eligible.value.filter((asset) => {
  const keyword = query.value.trim().toLowerCase()
  return (type.value === 'all' || fileType(asset) === type.value)
    && (keyword || currentFolder.value === 'all' || (asset.folder?.uuid || 'unfiled') === currentFolder.value)
    && (!keyword || `${asset.display_name} ${asset.original_name} ${asset.extension}`.toLowerCase().includes(keyword))
}))
const selectedAssets = computed(() => draft.value.map(uuid => eligible.value.find(asset => asset.uuid === uuid)).filter((asset): asset is Asset => Boolean(asset)))
async function load() {
  const current = ++generation
  loading.value = true; error.value = ''
  try {
    const [assets, folders] = await Promise.all([adminApi.allAssets(), adminApi.assetFolders()])
    if (current !== generation) return
    library.value = assets.items; directories.value = folders.items
    draft.value = draft.value.filter(uuid => eligible.value.some(asset => asset.uuid === uuid))
  } catch (cause) { if (current === generation) error.value = cause instanceof Error ? cause.message : '资源库加载失败' }
  finally { if (current === generation) loading.value = false }
}
function unlock() { if (previousOverflow !== null) { document.body.style.overflow = previousOverflow; previousOverflow = null } }
watch(() => props.open, async (open) => {
  if (!open) { generation++; dialog.value?.close(); unlock(); return }
  draft.value = props.multiple ? [...props.selected] : props.selected.slice(0, 1)
  query.value = ''; type.value = 'all'; currentFolder.value = 'all'
  library.value = props.assets; directories.value = props.folders
  await nextTick()
  if (!props.open) return
  previousOverflow = document.body.style.overflow; document.body.style.overflow = 'hidden'
  dialog.value?.showModal()
  void load()
}, { immediate: true })
onBeforeUnmount(() => { generation++; unlock() })
function toggle(uuid: string) { if (!props.busy) draft.value = props.multiple ? draft.value.includes(uuid) ? draft.value.filter(item => item !== uuid) : [...draft.value, uuid] : [uuid] }
function selectVisible() { if (!props.busy) draft.value = [...new Set([...draft.value, ...filtered.value.map(asset => asset.uuid)])] }
function fileSize(size: number) { return size < 1024 ? `${size} B` : size < 1024 * 1024 ? `${(size / 1024).toFixed(0)} KB` : `${(size / 1024 / 1024).toFixed(1)} MB` }
function close() { if (!uploading.value && !props.busy) emit('close') }
async function upload(event: Event) {
  const input = event.target as HTMLInputElement
  const files = Array.from(input.files || [])
  input.value = ''
  if (!files.length || uploading.value || props.busy) return
  uploading.value = true; error.value = ''
  const created: Asset[] = []
  try {
    for (const [index, file] of files.entries()) {
      const extension = '.' + file.name.split('.').pop()?.toLowerCase()
      if (!matchesAccept({ mime_type: file.type, extension })) throw new Error(`文件类型不匹配：${file.name}`)
      uploadLabel.value = `上传中 ${index + 1}/${files.length}`
      const asset = await adminApi.uploadAsset(file, true, '', ['all', 'unfiled'].includes(currentFolder.value) ? '' : currentFolder.value)
      library.value = [asset, ...library.value.filter(item => item.uuid !== asset.uuid)]
      created.push(asset)
      draft.value = props.multiple ? [...new Set([...draft.value, asset.uuid])] : [asset.uuid]
    }
    query.value = ''; type.value = 'all'
  } catch (cause) { error.value = cause instanceof Error ? cause.message : '上传失败，可重试未完成的文件' }
  finally { uploading.value = false; if (created.length) emit('uploaded', created) }
}
</script>

<template>
  <Teleport to="body">
    <dialog v-if="open" ref="dialog" class="library-dialog" :aria-label="title" @cancel.prevent="close" @click="($event.target === dialog) && close()">
      <header class="library-heading"><div><span class="eyebrow">资源库</span><h2>{{ title }}</h2><p>{{ multiple ? '可跨文件夹多选，确认后统一关联。' : '选择一个文件；也可以先上传，再确认使用。' }}</p></div><button type="button" class="icon-button" :disabled="uploading || busy" aria-label="关闭资源库" @click="close"><X :size="20" /></button></header>
      <div class="library-workspace">
        <aside class="library-folders" aria-label="资源目录">
          <button type="button" :class="{ active: currentFolder === 'all' }" @click="currentFolder = 'all'"><FolderOpen :size="17" />全部资源<span>{{ eligible.length }}</span></button>
          <button type="button" :class="{ active: currentFolder === 'unfiled' }" @click="currentFolder = 'unfiled'"><Folder :size="17" />未分类</button>
          <button v-for="folder in folderRows" :key="folder.uuid" type="button" :class="{ active: currentFolder === folder.uuid }" :style="{ paddingLeft: `${12 + Math.min(4, folder.path.length - 1) * 12}px` }" @click="currentFolder = folder.uuid"><Folder :size="16" /><strong>{{ folder.name }}</strong><span>{{ folder.asset_count }}</span></button>
        </aside>
        <section class="library-content">
          <div class="library-toolbar"><label class="search-field"><Search :size="17" /><input v-model="query" aria-label="搜索资源库" placeholder="搜索全部文件" type="search" /></label><select v-model="type" aria-label="文件类型"><option v-for="[value,label] in typeOptions" :key="value" :value="value">{{ label }}</option></select><button type="button" class="button button--dark button--small" :disabled="uploading || busy" @click="uploadInput?.click()"><UploadCloud :size="16" />{{ uploading ? uploadLabel : '上传文件' }}</button><input ref="uploadInput" hidden type="file" :accept="accept" :multiple="multiple" :disabled="uploading || busy" @change="upload" /></div>
          <div class="library-location"><span>{{ query ? '全部资源中的搜索结果' : folderName }} · {{ filtered.length }} 项</span><button v-if="multiple && filtered.length" type="button" @click="selectVisible">选择当前结果</button></div>
          <p v-if="error" class="form-error" role="alert">{{ error }} <button v-if="!uploading" type="button" @click="load">重试加载</button></p>
          <LoadingState v-if="loading" :rows="6" />
          <div v-else-if="filtered.length" class="library-grid">
            <article v-for="asset in filtered" :key="asset.uuid" :class="{ selected: draft.includes(asset.uuid) }">
              <button type="button" class="library-file" :aria-pressed="draft.includes(asset.uuid)" :aria-label="`选择 ${asset.display_name}`" @click="toggle(asset.uuid)"><span class="library-preview"><img v-if="asset.thumbnail_url || asset.mime_type.startsWith('image/')" :src="asset.thumbnail_url || asset.content_url" :alt="asset.display_name" loading="lazy" /><FileIcon v-else :size="36" /><span v-if="draft.includes(asset.uuid)" class="library-check"><Check :size="16" /></span></span><strong :title="asset.display_name">{{ asset.display_name }}</strong><small>{{ asset.extension.replace('.', '').toUpperCase() }} · {{ fileSize(asset.size) }} · {{ asset.is_public ? '公开' : '私有' }}</small></button>
              <RouterLink class="library-preview-link" :to="`/assets/${asset.uuid}`" target="_blank" :aria-label="`预览 ${asset.display_name}`"><ExternalLink :size="14" /></RouterLink>
            </article>
          </div>
          <div v-else class="library-empty"><FolderOpen :size="36" /><strong>暂无符合条件的文件</strong><span>切换目录、修改搜索条件，或上传新文件。</span></div>
        </section>
      </div>
      <footer class="library-footer"><div><strong>已选 {{ selectedAssets.length }} 项</strong><button v-if="draft.length" type="button" @click="!busy && (draft = [])">清空选择</button><span v-if="selectedAssets.length === 1">{{ selectedAssets[0].display_name }}</span></div><div><button type="button" class="button button--outline" :disabled="uploading || busy" @click="close">取消</button><button type="button" class="button button--dark" :disabled="busy || loading || uploading || (!multiple && !selectedAssets.length)" @click="emit('confirm', selectedAssets.map(asset => asset.uuid), selectedAssets)">{{ confirmLabel }}</button></div></footer>
    </dialog>
  </Teleport>
</template>
