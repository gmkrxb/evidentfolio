<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { Download, Eye, File, Folder, FolderPlus, Image, MoveRight, Pencil, RefreshCw, Search, Trash2, UploadCloud, Video, X } from 'lucide-vue-next'
import EmptyState from '@/components/ui/EmptyState.vue'
import ErrorState from '@/components/ui/ErrorState.vue'
import LoadingState from '@/components/ui/LoadingState.vue'
import { adminApi, type AssetDependencies, type AssetFolderDependencies } from '@/api/admin'
import { api } from '@/api/client'
import { useAsyncState } from '@/composables/useAsync'
import { useToastStore } from '@/stores/toast'
import type { Asset, AssetFolder } from '@/types'
import { uploadStatusLabel } from '@/utils/labels'

interface UploadItem {
  id: string
  file: File
  progress: number
  status: 'queued' | 'uploading' | 'success' | 'error'
  error: string
}

const state = useAsyncState<{ items: Asset[]; pagination: { total: number } }>()
const toast = useToastStore()
const q = ref('')
const category = ref('')
const dragging = ref(false)
const uploadPublic = ref(false)
const queue = ref<UploadItem[]>([])
const folders = ref<AssetFolder[]>([])
const activeFolder = ref('')
const selectedAssets = ref<string[]>([])
const moveTarget = ref('')
const folderDialogOpen = ref(false)
const moveDialogOpen = ref(false)
const folderMoveDialogOpen = ref(false)
const moveBrowseParent = ref<string | null>(null)
const folderEditing = ref<AssetFolder | null>(null)
const movingFolder = ref<AssetFolder | null>(null)
const deleteReview = ref<AssetDependencies | null>(null)
const deletingAsset = ref<Asset | null>(null)
const folderDeleteReview = ref<AssetFolderDependencies | null>(null)
const folderForm = reactive({ name: '', description: '', sort_order: 0, parent_uuid: null as string | null })
const editing = ref<Asset | null>(null)
const editForm = reactive({ display_name: '', description: '', logical_group: '', is_public: false, folder_uuid: null as string | null, translations: {} as Record<string, Record<string, string>> })
const assetEditLocale = ref<'zh-CN' | 'en'>('zh-CN')
const assetEnglish = reactive({ display_name: '', description: '' })
const activeUploads = ref(0)
const maxConcurrent = 3
const hasUploads = computed(() => queue.value.length > 0)
const rootFolders = computed(() => folders.value.filter((folder) => !folder.parent_uuid))
const activeFolderData = computed(() => folders.value.find((folder) => folder.uuid === activeFolder.value) || null)
const activeChildren = computed(() => folders.value.filter((folder) =>
  folder.parent_uuid === (activeFolderData.value?.uuid || null),
))
const moveChildren = computed(() => folders.value.filter((folder) => folder.parent_uuid === moveBrowseParent.value))
const folderMoveChildren = computed(() => moveChildren.value.filter(isFolderMoveCandidate))
const moveBreadcrumbs = computed(() =>
  moveBrowseParent.value
    ? folders.value.find((folder) => folder.uuid === moveBrowseParent.value)?.path || []
    : [],
)

function load() {
  return state.run(() => adminApi.assets({
    q: q.value || undefined,
    category: category.value || undefined,
    folder: activeFolder.value || undefined,
    page_size: 100,
  }))
}
async function loadFolders() {
  folders.value = (await adminApi.assetFolders()).items
}
async function loadAll() {
  await Promise.all([load(), loadFolders()])
}
function chooseFiles(event: Event) {
  const input = event.target as HTMLInputElement
  if (input.files) addFiles([...input.files])
  input.value = ''
}
function drop(event: DragEvent) {
  dragging.value = false
  if (event.dataTransfer?.files) addFiles([...event.dataTransfer.files])
}
function addFiles(files: File[]) {
  queue.value.push(...files.map((file) => ({ id: crypto.randomUUID(), file, progress: 0, status: 'queued' as const, error: '' })))
  pumpQueue()
}
function pumpQueue() {
  while (activeUploads.value < maxConcurrent) {
    const next = queue.value.find((item) => item.status === 'queued')
    if (!next) return
    void upload(next)
  }
}
async function upload(item: UploadItem) {
  item.status = 'uploading'
  activeUploads.value += 1
  const form = new FormData()
  form.append('file', item.file)
  form.append('is_public', String(uploadPublic.value))
  form.append('folder_uuid', activeFolder.value === 'unfiled' ? '' : activeFolder.value)
  try {
    await api.upload<Asset>('/admin/assets/upload', form, (event) => {
      if (event.total) item.progress = Math.round((event.loaded / event.total) * 100)
    })
    item.status = 'success'
    item.progress = 100
  } catch (cause) {
    item.status = 'error'
    item.error = cause instanceof Error ? cause.message : '上传失败'
  } finally {
    activeUploads.value -= 1
    pumpQueue()
    if (!queue.value.some((entry) => entry.status === 'queued' || entry.status === 'uploading')) await loadAll()
  }
}
function retry(item: UploadItem) {
  item.status = 'queued'
  item.error = ''
  item.progress = 0
  pumpQueue()
}
function openEdit(asset: Asset) {
  editing.value = asset
  Object.assign(editForm, {
    display_name: asset.display_name,
    description: asset.description,
    logical_group: asset.logical_group,
    is_public: asset.is_public,
    folder_uuid: asset.folder?.uuid || null,
    translations: asset.translations || {},
  })
  Object.assign(assetEnglish, asset.translations?.en || { display_name: '', description: '' })
}
function openFolderDialog(folder: AssetFolder | null = null) {
  folderEditing.value = folder
  Object.assign(folderForm, folder
    ? {
        name: folder.name,
        description: folder.description,
        sort_order: folder.sort_order,
        parent_uuid: folder.parent_uuid,
      }
    : {
        name: '',
        description: '',
        sort_order: folders.value.length,
        parent_uuid: activeFolder.value && activeFolder.value !== 'unfiled' ? activeFolder.value : null,
      })
  folderDialogOpen.value = true
}
async function saveFolder() {
  if (folderEditing.value) {
    await adminApi.updateAssetFolder(folderEditing.value.uuid, folderForm)
  } else {
    await adminApi.createAssetFolder(folderForm)
  }
  folderDialogOpen.value = false
  toast.show('文件夹已保存', 'success')
  await loadFolders()
}
async function removeFolder(folder: AssetFolder) {
  folderDeleteReview.value = await adminApi.assetFolderDependencies(folder.uuid)
}
async function confirmFolderDelete() {
  const review = folderDeleteReview.value
  if (!review || review.has_dependencies) return
  await adminApi.deleteAssetFolder(review.folder.uuid, true)
  if (activeFolder.value === review.folder.uuid) activeFolder.value = ''
  folderDeleteReview.value = null
  toast.show('文件夹、其中资源和物理文件均已删除', 'success')
  await loadAll()
}
async function moveSelected() {
  if (!selectedAssets.value.length) return
  await adminApi.batchMoveAssets(selectedAssets.value, moveTarget.value || null)
  toast.show(`${selectedAssets.value.length} 个资源已移动，UUID 与引用保持不变`, 'success')
  selectedAssets.value = []
  await loadAll()
}
function openMoveDialog() {
  moveBrowseParent.value = null
  moveTarget.value = ''
  moveDialogOpen.value = true
}
function isFolderMoveCandidate(folder: AssetFolder) {
  const moving = movingFolder.value
  if (!moving) return true
  return folder.uuid !== moving.uuid
    && !folder.path.some((part) => part.uuid === moving.uuid)
}
function openFolderMoveDialog(folder: AssetFolder) {
  movingFolder.value = folder
  moveBrowseParent.value = folder.parent_uuid
  moveTarget.value = folder.parent_uuid || ''
  folderMoveDialogOpen.value = true
}
async function confirmFolderMove() {
  const folder = movingFolder.value
  if (!folder) return
  await adminApi.updateAssetFolder(folder.uuid, {
    name: folder.name,
    description: folder.description,
    sort_order: folder.sort_order,
    parent_uuid: moveTarget.value || null,
  })
  toast.show('文件夹已移动，内部资源 UUID 与所有引用保持不变', 'success')
  folderMoveDialogOpen.value = false
  movingFolder.value = null
  await loadFolders()
}
async function confirmMove() {
  await moveSelected()
  moveDialogOpen.value = false
}
function selectFolder(uuid: string) {
  activeFolder.value = uuid
  selectedAssets.value = []
  void load()
}
async function saveEdit() {
  if (!editing.value) return
  editForm.translations = { ...editForm.translations, en: { ...assetEnglish } }
  await adminApi.updateAsset(editing.value.uuid, editForm)
  editing.value = null
  toast.show('资源信息已保存，UUID 地址保持不变', 'success')
  await loadAll()
}
async function remove(asset: Asset) {
  try {
    deletingAsset.value = asset
    deleteReview.value = await adminApi.assetDependencies(asset.uuid)
  } catch (cause) {
    deletingAsset.value = null
    toast.show(cause instanceof Error ? cause.message : '依赖检查失败', 'error')
  }
}
async function confirmAssetDelete() {
  if (!deletingAsset.value || deleteReview.value?.has_dependencies) return
  try {
    await adminApi.deleteAsset(deletingAsset.value.uuid)
    toast.show('资源数据库记录、原文件和缩略图均已删除', 'success')
    deletingAsset.value = null
    deleteReview.value = null
    await loadAll()
  } catch (cause) {
    toast.show(cause instanceof Error ? cause.message : '删除失败', 'error')
  }
}
function iconFor(asset: Asset) {
  if (asset.mime_type.startsWith('image/')) return Image
  if (asset.mime_type.startsWith('video/')) return Video
  return File
}
function formatBytes(size: number) {
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(0)} KB`
  return `${(size / 1024 / 1024).toFixed(1)} MB`
}
onMounted(loadAll)
</script>

<template>
  <div class="admin-page">
    <header class="admin-page-heading">
      <div><span class="eyebrow">Media library</span><h1>文件与资源</h1><p>安全上传、预览、重命名和管理稳定 UUID 资源地址。</p></div>
      <label class="button button--dark file-button"><UploadCloud :size="17" />选择文件<input type="file" multiple @change="chooseFiles" /></label>
    </header>
    <section
      class="drop-zone"
      :class="{ 'is-dragging': dragging }"
      @dragenter.prevent="dragging = true"
      @dragover.prevent
      @dragleave.prevent="dragging = false"
      @drop.prevent="drop"
    >
      <UploadCloud :size="30" />
      <div><strong>拖拽多个文件到这里上传</strong><span>系统会校验扩展名、MIME、内容、大小和 SHA-256。</span></div>
      <label class="check-label"><input v-model="uploadPublic" type="checkbox" />上传后立即公开</label>
    </section>
    <section v-if="hasUploads" class="upload-queue">
      <div class="admin-panel__heading"><div><span class="eyebrow">Upload queue</span><h2>上传队列</h2></div><button @click="queue = queue.filter((item) => item.status === 'uploading')">清除已完成</button></div>
      <article v-for="item in queue" :key="item.id">
        <File :size="18" />
        <div><strong>{{ item.file.name }}</strong><span>{{ formatBytes(item.file.size) }} · {{ uploadStatusLabel(item.status) }}</span><div class="progress"><span :style="{ width: `${item.progress}%` }" /></div><small v-if="item.error">{{ item.error }}</small></div>
        <button v-if="item.status === 'error'" class="icon-button" aria-label="重试上传" @click="retry(item)"><RefreshCw :size="17" /></button>
      </article>
    </section>
    <div class="resource-library-layout">
      <aside class="asset-folder-sidebar">
        <div class="asset-folder-sidebar__heading">
          <strong>资源文件夹</strong>
          <button type="button" class="icon-button" aria-label="新建文件夹" @click="openFolderDialog()"><FolderPlus :size="17" /></button>
        </div>
        <button :class="{ active: activeFolder === '' }" @click="selectFolder('')"><Folder :size="16" /><span>全部资源</span><small>{{ state.data.value?.pagination.total || 0 }}</small></button>
        <button :class="{ active: activeFolder === 'unfiled' }" @click="selectFolder('unfiled')"><Folder :size="16" /><span>未分类</span></button>
        <div v-for="folder in rootFolders" :key="folder.uuid" class="asset-folder-row" :class="{ active: activeFolder === folder.uuid }">
          <button @click="selectFolder(folder.uuid)"><Folder :size="16" /><span>{{ folder.name }}</span><small>{{ folder.asset_count }}</small></button>
          <button class="asset-folder-row__move" title="移动文件夹" @click="openFolderMoveDialog(folder)"><MoveRight :size="13" /></button>
          <button class="asset-folder-row__edit" title="编辑文件夹" @click="openFolderDialog(folder)"><Pencil :size="13" /></button>
          <button class="asset-folder-row__delete danger-text" title="删除文件夹" @click="removeFolder(folder)"><Trash2 :size="13" /></button>
        </div>
      </aside>
      <main class="asset-library-main">
    <nav v-if="activeFolderData" class="asset-breadcrumbs" aria-label="资源文件夹路径">
      <button @click="selectFolder('')">全部资源</button>
      <template v-for="part in activeFolderData.path" :key="part.uuid">
        <span>/</span><button @click="selectFolder(part.uuid)">{{ part.name }}</button>
      </template>
      <span class="asset-breadcrumbs__actions">
        <button type="button" @click="openFolderMoveDialog(activeFolderData)"><MoveRight :size="14" />移动当前文件夹</button>
        <button type="button" @click="openFolderDialog(activeFolderData)"><Pencil :size="14" />编辑</button>
        <button type="button" class="danger-text" @click="removeFolder(activeFolderData)"><Trash2 :size="14" />删除</button>
      </span>
    </nav>
    <div v-if="activeChildren.length && !q" class="asset-child-folders">
      <button v-for="folder in activeChildren" :key="folder.uuid" @click="selectFolder(folder.uuid)">
        <Folder :size="22" /><span><strong>{{ folder.name }}</strong><small>{{ folder.asset_count }} 个资源 · {{ folder.child_count }} 个子目录</small></span>
      </button>
    </div>
    <div class="admin-toolbar">
      <label class="search-field"><Search :size="17" /><span class="sr-only">搜索资源</span><input v-model="q" placeholder="全局搜索名称、原始文件名、描述或分组" @keyup.enter="load" /></label>
      <select v-model="category" aria-label="文件分类" @change="load"><option value="">全部文件</option><option value="images">图片</option><option value="videos">视频</option><option value="documents">文档</option><option value="resumes">简历</option><option value="text">文本</option></select>
      <button class="button button--outline button--small" @click="load">查询</button>
      <span class="toolbar-count">共 {{ state.data.value?.pagination.total || 0 }} 项</span>
    </div>
    <div v-if="selectedAssets.length" class="asset-batch-bar">
      <strong>已选择 {{ selectedAssets.length }} 项</strong>
      <button type="button" class="button button--dark button--small" @click="openMoveDialog"><MoveRight :size="15" />选择目标文件夹</button>
      <button type="button" class="button button--outline button--small" @click="selectedAssets = []">取消选择</button>
    </div>
    <LoadingState v-if="state.loading.value" :rows="8" />
    <ErrorState v-else-if="state.error.value" :message="state.error.value" @retry="load" />
    <EmptyState v-else-if="!state.data.value?.items.length" title="资源库为空" description="上传项目截图、演示视频、PDF 或安全文本文件。" />
    <div v-else class="asset-grid">
      <article v-for="asset in state.data.value.items" :key="asset.uuid" class="asset-card">
        <div class="asset-card__preview">
          <label class="asset-card__select" aria-label="选择资源"><input v-model="selectedAssets" type="checkbox" :value="asset.uuid" /></label>
          <img v-if="asset.thumbnail_url" :src="asset.thumbnail_url" :alt="asset.description || asset.display_name" loading="lazy" />
          <component :is="iconFor(asset)" v-else :size="30" />
          <span :class="{ public: asset.is_public }">{{ asset.is_public ? '公开' : '私有' }}</span>
        </div>
        <div class="asset-card__body">
          <strong :title="asset.display_name">{{ asset.display_name }}</strong>
          <span>{{ asset.extension.toUpperCase() }} · {{ formatBytes(asset.size) }}</span>
          <small :title="asset.original_name">原名：{{ asset.original_name }}</small>
          <small v-if="asset.folder">文件夹：{{ asset.folder.name }}</small>
          <div>
            <RouterLink :to="`/assets/${asset.uuid}`" target="_blank" title="预览"><Eye :size="17" /></RouterLink>
            <a :href="asset.download_url" title="下载"><Download :size="17" /></a>
            <button title="编辑信息" @click="openEdit(asset)"><Pencil :size="16" /></button>
            <button class="danger-text" title="删除" @click="remove(asset)"><Trash2 :size="16" /></button>
          </div>
        </div>
      </article>
    </div>
      </main>
    </div>
    <Teleport to="body">
      <div v-if="editing" class="modal-backdrop" @click.self="editing = null">
        <form class="modal-card" @submit.prevent="saveEdit">
          <header><div><span class="eyebrow">Edit asset</span><h2>资源信息</h2></div><button class="icon-button" type="button" aria-label="关闭" @click="editing = null"><X :size="19" /></button></header>
          <div class="language-tabs"><button type="button" :class="{ active: assetEditLocale === 'zh-CN' }" @click="assetEditLocale = 'zh-CN'">中文</button><button type="button" :class="{ active: assetEditLocale === 'en' }" @click="assetEditLocale = 'en'">English</button></div>
          <label>{{ assetEditLocale === 'en' ? 'Display name' : '展示名称' }}<input v-if="assetEditLocale === 'zh-CN'" v-model="editForm.display_name" required /><input v-else v-model="assetEnglish.display_name" /></label>
          <label>逻辑分组<input v-model="editForm.logical_group" placeholder="例如：研究论文 / 架构图" /></label>
          <label>资源文件夹
            <select v-model="editForm.folder_uuid">
              <option :value="null">未分类</option>
              <option v-for="folder in folders" :key="folder.uuid" :value="folder.uuid">{{ folder.name }}</option>
            </select>
          </label>
          <label>{{ assetEditLocale === 'en' ? 'Description' : '描述' }}<textarea v-if="assetEditLocale === 'zh-CN'" v-model="editForm.description" rows="5" /><textarea v-else v-model="assetEnglish.description" rows="5" /></label>
          <label class="check-label"><input v-model="editForm.is_public" type="checkbox" />允许公开访问</label>
          <p class="panel-note">修改展示名称不会改变内部 storage_name，也不会使 UUID 地址失效。</p>
          <footer><button type="button" class="button button--outline" @click="editing = null">取消</button><button class="button button--dark">保存</button></footer>
        </form>
      </div>
    </Teleport>
    <Teleport to="body">
      <div v-if="folderDialogOpen" class="modal-backdrop" @click.self="folderDialogOpen = false">
        <form class="modal-card" @submit.prevent="saveFolder">
          <header><div><span class="eyebrow">Asset folder</span><h2>{{ folderEditing ? '编辑文件夹' : '新建文件夹' }}</h2></div><button class="icon-button" type="button" aria-label="关闭" @click="folderDialogOpen = false"><X :size="19" /></button></header>
          <label>文件夹名称<input v-model="folderForm.name" required maxlength="160" placeholder="例如：论文插图" /></label>
          <label>说明<textarea v-model="folderForm.description" rows="3" /></label>
          <label>排序值<input v-model.number="folderForm.sort_order" type="number" /></label>
          <label>上级文件夹
            <select v-model="folderForm.parent_uuid">
              <option :value="null">根目录</option>
              <option v-for="folder in folders.filter((item) => item.uuid !== folderEditing?.uuid)" :key="folder.uuid" :value="folder.uuid">{{ folder.path.map((item) => item.name).join(' / ') }}</option>
            </select>
          </label>
          <footer><button type="button" class="button button--outline" @click="folderDialogOpen = false">取消</button><button class="button button--dark">保存文件夹</button></footer>
        </form>
      </div>
    </Teleport>
    <Teleport to="body">
      <div v-if="moveDialogOpen" class="modal-backdrop" @click.self="moveDialogOpen = false">
        <div class="modal-card folder-browser-modal">
          <header><div><span class="eyebrow">Move assets</span><h2>移动到文件夹</h2></div><button class="icon-button" type="button" aria-label="关闭" @click="moveDialogOpen = false"><X :size="19" /></button></header>
          <nav class="asset-breadcrumbs">
            <button @click="moveBrowseParent = null; moveTarget = ''">根目录</button>
            <template v-for="part in moveBreadcrumbs" :key="part.uuid">
              <span>/</span><button @click="moveBrowseParent = part.uuid; moveTarget = part.uuid">{{ part.name }}</button>
            </template>
          </nav>
          <div class="folder-browser-list">
            <button :class="{ active: moveTarget === (moveBrowseParent || '') }" @click="moveTarget = moveBrowseParent || ''">
              <Folder :size="20" /><span>选择当前目录</span>
            </button>
            <button v-for="folder in moveChildren" :key="folder.uuid" @dblclick="moveBrowseParent = folder.uuid; moveTarget = folder.uuid" @click="moveTarget = folder.uuid">
              <Folder :size="20" /><span>{{ folder.name }}</span><small>双击进入</small>
            </button>
          </div>
          <footer><button class="button button--outline" @click="moveDialogOpen = false">取消</button><button class="button button--dark" @click="confirmMove">移动 {{ selectedAssets.length }} 个资源</button></footer>
        </div>
      </div>
    </Teleport>
    <Teleport to="body">
      <div v-if="folderMoveDialogOpen && movingFolder" class="modal-backdrop" @click.self="folderMoveDialogOpen = false">
        <div class="modal-card folder-browser-modal">
          <header><div><span class="eyebrow">Move folder</span><h2>移动“{{ movingFolder.name }}”</h2></div><button class="icon-button" type="button" aria-label="关闭" @click="folderMoveDialogOpen = false"><X :size="19" /></button></header>
          <p class="panel-note">选择新的上级目录。系统已隐藏当前文件夹及其全部子目录，防止产生循环嵌套。</p>
          <nav class="asset-breadcrumbs">
            <button @click="moveBrowseParent = null; moveTarget = ''">根目录</button>
            <template v-for="part in moveBreadcrumbs.filter((item) => item.uuid !== movingFolder?.uuid)" :key="part.uuid">
              <span>/</span><button @click="moveBrowseParent = part.uuid; moveTarget = part.uuid">{{ part.name }}</button>
            </template>
          </nav>
          <div class="folder-browser-list">
            <button :class="{ active: moveTarget === (moveBrowseParent || '') }" @click="moveTarget = moveBrowseParent || ''">
              <Folder :size="20" /><span>选择当前目录</span>
            </button>
            <button v-for="folder in folderMoveChildren" :key="folder.uuid" @dblclick="moveBrowseParent = folder.uuid; moveTarget = folder.uuid" @click="moveTarget = folder.uuid">
              <Folder :size="20" /><span>{{ folder.name }}</span><small>双击进入</small>
            </button>
          </div>
          <footer><button class="button button--outline" @click="folderMoveDialogOpen = false">取消</button><button class="button button--dark" @click="confirmFolderMove">确认移动文件夹</button></footer>
        </div>
      </div>
    </Teleport>
    <Teleport to="body">
      <div v-if="deletingAsset && deleteReview" class="modal-backdrop" @click.self="deletingAsset = null; deleteReview = null">
        <div class="modal-card dependency-review-modal">
          <header><div><span class="eyebrow">Dependency check</span><h2>删除前依赖检查</h2></div><button class="icon-button" aria-label="关闭" @click="deletingAsset = null; deleteReview = null"><X :size="19" /></button></header>
          <p>资源：<strong>{{ deletingAsset.display_name }}</strong></p>
          <div v-if="deleteReview.has_dependencies" class="dependency-review__warning">该资源正在使用中，暂时不能删除。请先进入下列内容解除关联。</div>
          <div v-else class="dependency-review__safe">未发现任何引用。确认后会同时删除数据库记录、原始文件和缩略图，此操作不可恢复。</div>
          <section v-if="deleteReview.projects.length">
            <h3>使用项目（{{ deleteReview.projects.length }}）</h3>
            <RouterLink v-for="project in deleteReview.projects" :key="project.uuid" :to="`/admin/projects/${project.uuid}`" target="_blank">
              <span>{{ project.title }}</span><small>使用 {{ project.usage_count }} 处</small>
            </RouterLink>
          </section>
          <section v-if="deleteReview.certificates.length">
            <h3>关联证书（{{ deleteReview.certificates.length }}）</h3>
            <RouterLink v-for="certificate in deleteReview.certificates" :key="certificate.uuid" to="/admin/certificates" target="_blank">{{ certificate.name }}</RouterLink>
          </section>
          <section v-if="deleteReview.resumes.length">
            <h3>关联简历（{{ deleteReview.resumes.length }}）</h3>
            <RouterLink v-for="resume in deleteReview.resumes" :key="resume.uuid" to="/admin/resumes" target="_blank">{{ resume.name }}</RouterLink>
          </section>
          <section v-if="deleteReview.site_uses.length">
            <h3>网站设置</h3><span v-for="item in deleteReview.site_uses" :key="item">{{ item }}</span>
          </section>
          <footer><button class="button button--outline" @click="deletingAsset = null; deleteReview = null">取消</button><button class="button button--danger" :disabled="deleteReview.has_dependencies" @click="confirmAssetDelete">永久删除资源</button></footer>
        </div>
      </div>
    </Teleport>
    <Teleport to="body">
      <div v-if="folderDeleteReview" class="modal-backdrop" @click.self="folderDeleteReview = null">
        <div class="modal-card dependency-review-modal">
          <header><div><span class="eyebrow">Folder dependency check</span><h2>删除文件夹前检查</h2></div><button class="icon-button" aria-label="关闭" @click="folderDeleteReview = null"><X :size="19" /></button></header>
          <p><strong>{{ folderDeleteReview.folder.name }}</strong>：包含 {{ folderDeleteReview.asset_count }} 个资源。</p>
          <div v-if="folderDeleteReview.has_dependencies" class="dependency-review__warning">文件夹内存在被项目、证书、简历或设置使用的资源，不能删除。</div>
          <div v-else class="dependency-review__safe">未发现外部引用。确认后将递归删除子文件夹、数据库资源记录、原文件与缩略图。</div>
          <section v-if="folderDeleteReview.projects.length">
            <h3>使用项目（{{ folderDeleteReview.projects.length }}）</h3>
            <RouterLink v-for="project in folderDeleteReview.projects" :key="project.uuid" :to="`/admin/projects/${project.uuid}`" target="_blank"><span>{{ project.title }}</span><small>使用 {{ project.usage_count }} 处</small></RouterLink>
          </section>
          <section v-if="folderDeleteReview.certificates.length"><h3>关联证书</h3><RouterLink v-for="item in folderDeleteReview.certificates" :key="item.uuid" to="/admin/certificates" target="_blank">{{ item.name }}</RouterLink></section>
          <section v-if="folderDeleteReview.resumes.length"><h3>关联简历</h3><RouterLink v-for="item in folderDeleteReview.resumes" :key="item.uuid" to="/admin/resumes" target="_blank">{{ item.name }}</RouterLink></section>
          <footer><button class="button button--outline" @click="folderDeleteReview = null">取消</button><button class="button button--danger" :disabled="folderDeleteReview.has_dependencies" @click="confirmFolderDelete">永久删除文件夹及内容</button></footer>
        </div>
      </div>
    </Teleport>
  </div>
</template>
