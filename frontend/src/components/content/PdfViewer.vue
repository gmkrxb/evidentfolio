<script setup lang="ts">
import '@/utils/pdfPolyfills'
import { computed, nextTick, onBeforeUnmount, onMounted, ref, shallowRef, watch } from 'vue'
import {
  ChevronLeft,
  ChevronRight,
  Download,
  Expand,
  ListTree,
  Minus,
  Plus,
  Shrink,
} from 'lucide-vue-next'
import {
  PDFWorker,
  getDocument,
  type PDFDocumentLoadingTask,
  type PDFDocumentProxy,
  type PDFPageProxy,
} from 'pdfjs-dist'
import { useLocaleStore } from '@/stores/locale'
import type { Asset } from '@/types'
import { protectedBytes } from '@/utils/protectedAsset'

const locale = useLocaleStore()
const text = (zh: string, en: string) => locale.isEnglish ? en : zh

// 每个阅读器使用独立的解析线程：切换简历时旧文档的销毁不会波及新文档
//（共用同一个 Worker 时，新文档会拿到“正在销毁”的线程而永远不开始加载）。
let pdfWorker: PDFWorker | null = null
let workerThread: Worker | null = null
function ensureWorker() {
  if (pdfWorker && !pdfWorker.destroyed) return pdfWorker
  workerThread = new Worker(new URL('../../utils/pdfWorker.ts', import.meta.url), { type: 'module' })
  pdfWorker = new PDFWorker({ port: workerThread } as unknown as ConstructorParameters<typeof PDFWorker>[0])
  return pdfWorker
}
function releaseWorker() {
  pdfWorker?.destroy()
  workerThread?.terminate()
  pdfWorker = null
  workerThread = null
}

interface OutlineItem {
  title: string
  dest: string | unknown[] | null
  items?: OutlineItem[]
}

const props = defineProps<{
  src: string
  title: string
  meta?: string
  /** 仅可查看的资源：经加密票据取回并在内存中解密，隐藏下载入口 */
  protectedAsset?: (Pick<Asset, 'uuid' | 'sha256' | 'mime_type' | 'content_url'> & { protected?: boolean }) | null
}>()
const isProtected = computed(() => Boolean(props.protectedAsset?.protected))
const emit = defineEmits<{ download: [] }>()
const root = ref<HTMLElement | null>(null)
const scroller = ref<HTMLElement | null>(null)
// PDF.js 实例需保留原生私有字段，避免深层响应式代理。
const documentProxy = shallowRef<PDFDocumentProxy | null>(null)
const loadingTask = shallowRef<PDFDocumentLoadingTask | null>(null)
const pages = shallowRef<PDFPageProxy[]>([])
const canvases = new Map<number, HTMLCanvasElement>()
const pageElements = new Map<number, HTMLElement>()
const pageCount = ref(0)
const currentPage = ref(1)
const pageInput = ref(1)
const zoom = ref(100)
const renderedZoom = ref(100)
const outline = ref<OutlineItem[]>([])
const sidebarOpen = ref(false)
const loading = ref(true)
const error = ref('')
const rendering = ref(false)
const pagesReady = ref(false)
const loadedBytes = ref(0)
const totalBytes = ref(0)
const renderedPageCount = ref(0)
const fullscreen = ref(false)
const dragging = ref(false)
const dragOrigin = { x: 0, y: 0, left: 0, top: 0 }
let renderTimer: number | undefined
let renderGeneration = 0
let documentGeneration = 0
let intersectionObserver: IntersectionObserver | null = null

const visualScale = computed(() => zoom.value / renderedZoom.value)
const documentStyle = computed(() => ({
  transform: `scale(${visualScale.value})`,
  transformOrigin: 'top center',
}))
const loadPercent = computed(() =>
  totalBytes.value > 0 ? Math.min(100, Math.round((loadedBytes.value / totalBytes.value) * 100)) : 0,
)
const renderPercent = computed(() =>
  pageCount.value > 0 ? Math.round((renderedPageCount.value / pageCount.value) * 100) : 0,
)

function setCanvas(element: unknown, pageNumber: number) {
  if (element instanceof HTMLCanvasElement) canvases.set(pageNumber, element)
}
function setPageElement(element: unknown, pageNumber: number) {
  if (element instanceof HTMLElement) pageElements.set(pageNumber, element)
}
function flattenOutline(items: OutlineItem[], depth = 0): Array<OutlineItem & { depth: number }> {
  return items.flatMap((item) => [
    { ...item, depth },
    ...flattenOutline(item.items || [], depth + 1),
  ])
}
const outlineItems = computed(() => flattenOutline(outline.value))

async function loadDocument() {
  const currentDocument = ++documentGeneration
  window.clearTimeout(renderTimer)
  loading.value = true
  pagesReady.value = false
  error.value = ''
  renderGeneration += 1
  await loadingTask.value?.destroy().catch(() => undefined)
  if (currentDocument !== documentGeneration) return
  documentProxy.value = null
  pages.value = []
  renderedPageCount.value = 0
  loadedBytes.value = 0
  totalBytes.value = 0
  canvases.clear()
  pageElements.clear()
  try {
    const source = isProtected.value
      ? { data: (await protectedBytes(props.protectedAsset!)).slice() }
      : { url: props.src }
    if (currentDocument !== documentGeneration) return
    const task = getDocument({
      ...source,
      worker: ensureWorker(),
      withCredentials: true,
      cMapUrl: '/pdfjs/cmaps/',
      cMapPacked: true,
      standardFontDataUrl: '/pdfjs/standard_fonts/',
      wasmUrl: '/pdfjs/wasm/',
      useSystemFonts: true,
    })
    task.onProgress = ({ loaded, total }: { loaded: number; total: number }) => {
      if (currentDocument !== documentGeneration) return
      loadedBytes.value = loaded
      totalBytes.value = total || totalBytes.value
    }
    loadingTask.value = task
    const pdf = await task.promise
    if (currentDocument !== documentGeneration) return
    documentProxy.value = pdf
    pageCount.value = pdf.numPages
    currentPage.value = 1
    pageInput.value = 1
    zoom.value = 100
    renderedZoom.value = 100
    void pdf.getOutline().then((items) => {
      if (currentDocument !== documentGeneration) return
      outline.value = (items || []) as OutlineItem[]
    }).catch(() => {
      if (currentDocument === documentGeneration) outline.value = []
    })
    // 首屏先展示，后续页面逐页加载。
    loading.value = false
    rendering.value = true
    const generation = renderGeneration
    let initialZoom = 100
    for (let pageNumber = 1; pageNumber <= pdf.numPages; pageNumber += 1) {
      if (generation !== renderGeneration) return
      const page = await pdf.getPage(pageNumber)
      if (currentDocument !== documentGeneration) return
      if (pageNumber === 1) {
        await nextTick()
        const scrollStyle = scroller.value ? getComputedStyle(scroller.value) : null
        const padding = scrollStyle ? parseFloat(scrollStyle.paddingLeft) + parseFloat(scrollStyle.paddingRight) : 32
        const available = (scroller.value?.clientWidth || 680) - padding
        initialZoom = Math.max(25, Math.min(100, Math.floor(available / page.getViewport({ scale: 1 }).width * 100)))
        zoom.value = initialZoom
        renderedZoom.value = initialZoom
      }
      pages.value = [...pages.value, page]
      await nextTick()
      setNaturalPageSize(page)
      await renderPage(page, initialZoom, generation)
      renderedPageCount.value = pageNumber
      const element = pageElements.get(pageNumber)
      if (element && intersectionObserver) intersectionObserver.observe(element)
    }
    renderedZoom.value = initialZoom
    rendering.value = false
    pagesReady.value = true
    observePages()
  } catch (cause) {
    if (currentDocument !== documentGeneration) return
    if (loadingTask.value) {
      error.value = cause instanceof Error ? cause.message : text('PDF 加载失败', 'Could not load PDF')
    }
    loading.value = false
    rendering.value = false
  }
}

function setNaturalPageSize(page: PDFPageProxy) {
  const element = pageElements.get(page.pageNumber)
  if (!element) return
  const viewport = page.getViewport({ scale: zoom.value / 100 })
  element.style.minWidth = `${viewport.width}px`
  element.style.minHeight = `${viewport.height}px`
}

async function renderPage(page: PDFPageProxy, targetZoom: number, generation: number) {
  const visible = canvases.get(page.pageNumber)
  if (!visible) return
  const viewport = page.getViewport({ scale: targetZoom / 100 })
  const outputScale = Math.min(window.devicePixelRatio || 1, 2)
  const buffer = document.createElement('canvas')
  buffer.width = Math.ceil(viewport.width * outputScale)
  buffer.height = Math.ceil(viewport.height * outputScale)
  const context = buffer.getContext('2d', { alpha: false })
  if (!context) return
  await page.render({
    canvas: buffer,
    canvasContext: context,
    viewport,
    transform: outputScale === 1 ? undefined : [outputScale, 0, 0, outputScale, 0, 0],
  }).promise
  if (generation !== renderGeneration) return
  visible.width = buffer.width
  visible.height = buffer.height
  visible.style.width = `${viewport.width}px`
  visible.style.height = `${viewport.height}px`
  const element = pageElements.get(page.pageNumber)
  if (element) { element.style.minWidth = `${viewport.width}px`; element.style.minHeight = `${viewport.height}px` }
  visible.getContext('2d', { alpha: false })?.drawImage(buffer, 0, 0)
}

async function renderPages(targetZoom: number) {
  const generation = ++renderGeneration
  rendering.value = true
  renderedPageCount.value = 0
  try {
    const prioritized = [...pages.value].sort(
      (left, right) =>
        Math.abs(left.pageNumber - currentPage.value)
        - Math.abs(right.pageNumber - currentPage.value),
    )
    for (const page of prioritized) {
      if (generation !== renderGeneration) return
      await renderPage(page, targetZoom, generation)
      renderedPageCount.value += 1
    }
    renderedZoom.value = targetZoom
  } catch (cause) {
    if (generation === renderGeneration && !(cause instanceof Error && cause.name === 'RenderingCancelledException')) {
      error.value = cause instanceof Error ? cause.message : text('PDF 页面渲染失败', 'Could not render PDF')
    }
  } finally {
    if (generation === renderGeneration) rendering.value = false
  }
}

function scheduleRender() {
  window.clearTimeout(renderTimer)
  renderTimer = window.setTimeout(() => void renderPages(zoom.value), 180)
}
function setZoom(value: number) {
  if (!pagesReady.value) return
  zoom.value = Math.min(220, Math.max(25, value))
  scheduleRender()
}
function goToPage(value: number) {
  const next = Math.max(1, Math.min(pages.value.length, Math.max(1, Math.round(value || 1))))
  pageInput.value = next
  currentPage.value = next
  pageElements.get(next)?.scrollIntoView({ behavior: window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth', block: 'start' })
}
async function goToDestination(destination: string | unknown[] | null) {
  const pdf = documentProxy.value
  if (!pdf || !destination) return
  const resolved = typeof destination === 'string'
    ? await pdf.getDestination(destination)
    : destination
  const reference = resolved?.[0]
  if (reference == null) return
  const pageIndex = typeof reference === 'object'
    ? await pdf.getPageIndex(reference as { num: number; gen: number })
    : Number(reference)
  goToPage(pageIndex + 1)
  if (window.innerWidth < 900) sidebarOpen.value = false
}
function observePages() {
  intersectionObserver?.disconnect()
  if (!scroller.value) return
  intersectionObserver = new IntersectionObserver(
    (entries) => {
      const visible = entries
        .filter((entry) => entry.isIntersecting)
        .sort((a, b) => b.intersectionRatio - a.intersectionRatio)[0]
      if (!visible) return
      const number = Number((visible.target as HTMLElement).dataset.page)
      if (number) {
        currentPage.value = number
        pageInput.value = number
      }
    },
    { root: scroller.value, threshold: [0.25, 0.5, 0.75] },
  )
  for (const element of pageElements.values()) intersectionObserver.observe(element)
}
function startDrag(event: PointerEvent) {
  if (event.pointerType !== 'mouse' || event.button !== 0) return
  if (!scroller.value || (event.target as HTMLElement).closest('button, input, a')) return
  dragging.value = true
  dragOrigin.x = event.clientX
  dragOrigin.y = event.clientY
  dragOrigin.left = scroller.value.scrollLeft
  dragOrigin.top = scroller.value.scrollTop
  scroller.value.setPointerCapture(event.pointerId)
}
function drag(event: PointerEvent) {
  if (!dragging.value || !scroller.value) return
  scroller.value.scrollLeft = dragOrigin.left - (event.clientX - dragOrigin.x)
  scroller.value.scrollTop = dragOrigin.top - (event.clientY - dragOrigin.y)
}
function stopDrag() {
  dragging.value = false
}
async function toggleFullscreen() {
  if (!root.value) return
  try {
    if (document.fullscreenElement) await document.exitFullscreen()
    else await root.value.requestFullscreen()
  } catch { /* 浏览器不支持时保留当前预览。 */ }
}
function syncFullscreen() {
  fullscreen.value = document.fullscreenElement === root.value
}

watch(() => [props.src, props.protectedAsset?.uuid, isProtected.value], loadDocument)
onMounted(() => {
  document.addEventListener('fullscreenchange', syncFullscreen)
  void loadDocument()
})
onBeforeUnmount(() => {
  window.clearTimeout(renderTimer)
  renderGeneration += 1
  documentGeneration += 1
  intersectionObserver?.disconnect()
  document.removeEventListener('fullscreenchange', syncFullscreen)
  const task = loadingTask.value
  loadingTask.value = null
  void (task?.destroy() || Promise.resolve()).catch(() => undefined).finally(releaseWorker)
})
</script>

<template>
  <div ref="root" v-protect="isProtected" class="pdf-viewer" :class="{ 'is-fullscreen': fullscreen, 'has-sidebar': sidebarOpen }">
    <div class="pdf-toolbar">
      <div class="pdf-toolbar__identity">
        <strong>{{ title }}</strong>
        <span>{{ meta }}</span>
      </div>
      <span v-if="isProtected" class="pdf-protected-badge">{{ text('仅可查看', 'View only') }}</span>
      <button v-if="!isProtected" class="button button--dark button--small pdf-download pdf-download--compact" :aria-label="text('下载', 'Download')" @click="emit('download')">
        <Download :size="16" /><span>{{ text('下载', 'Download') }}</span>
      </button>
      <div class="pdf-controls">
        <button
          :aria-label="text('切换 PDF 目录', 'Toggle PDF outline')"
          :class="{ active: sidebarOpen }"
          :disabled="!pagesReady || !outlineItems.length"
          @click="sidebarOpen = !sidebarOpen"
        >
          <ListTree :size="17" />
        </button>
        <button :aria-label="text('上一页', 'Previous page')" :disabled="currentPage <= 1" @click="goToPage(currentPage - 1)">
          <ChevronLeft :size="17" />
        </button>
        <label>
          <span class="pdf-controls__page-label">{{ text('页码', 'Page') }}</span>
          <input
            v-model.number="pageInput"
            type="number"
            min="1"
            :max="pages.length || 1"
            :aria-label="text('PDF 页码', 'PDF page number')"
            @change="goToPage(pageInput)"
            @keyup.enter="goToPage(pageInput)"
          />
          <span>/ {{ pageCount || '—' }}</span>
        </label>
        <button :aria-label="text('下一页', 'Next page')" :disabled="currentPage >= pages.length" @click="goToPage(currentPage + 1)"><ChevronRight :size="17" /></button>
        <button :disabled="!pagesReady" :aria-label="text('缩小', 'Zoom out')" @click="setZoom(zoom - 10)"><Minus :size="17" /></button>
        <input
          class="pdf-zoom-range"
          :disabled="!pagesReady"
          :value="zoom"
          type="range"
          min="25"
          max="220"
          step="5"
          :aria-label="text('PDF 缩放比例', 'PDF zoom level')"
          @input="setZoom(Number(($event.target as HTMLInputElement).value))"
        />
        <span class="pdf-zoom-value">{{ zoom }}%</span>
        <button :disabled="!pagesReady" :aria-label="text('放大', 'Zoom in')" @click="setZoom(zoom + 10)"><Plus :size="17" /></button>
        <button :aria-label="fullscreen ? text('退出全屏', 'Exit fullscreen') : text('全屏预览', 'Fullscreen')" @click="toggleFullscreen">
          <Shrink v-if="fullscreen" :size="17" />
          <Expand v-else :size="17" />
        </button>
        <button v-if="!isProtected" class="button button--dark button--small pdf-download pdf-download--wide" @click="emit('download')">
          <Download :size="16" />{{ text('下载', 'Download') }}
        </button>
      </div>
    </div>
    <div class="pdf-viewer__body">
      <aside v-if="sidebarOpen" class="pdf-outline" :aria-label="text('PDF 目录', 'PDF outline')">
        <span class="eyebrow">Document outline</span>
        <button
          v-for="(item, index) in outlineItems"
          :key="`${item.title}-${index}`"
          :style="{ paddingLeft: `${14 + item.depth * 14}px` }"
          @click="goToDestination(item.dest)"
        >
          {{ item.title }}
        </button>
        <p v-if="!outlineItems.length">{{ text('该文件没有内置目录。', 'No outline is included in this file.') }}</p>
      </aside>
      <div
        ref="scroller"
        class="pdf-document-scroll"
        :class="{ 'is-dragging': dragging }"
        @pointerdown="startDrag"
        @pointermove="drag"
        @pointerup="stopDrag"
        @pointercancel="stopDrag"
      >
        <div v-if="loading" class="pdf-viewer__state">
          <strong>{{ text('正在加载 PDF…', 'Loading PDF…') }}</strong>
          <span>{{ loadPercent ? `${loadPercent}%` : text('正在连接文件', 'Connecting to file') }}</span>
          <div class="pdf-load-progress"><i :style="{ width: `${loadPercent}%` }" /></div>
        </div>
        <div v-else-if="error" class="pdf-viewer__state pdf-viewer__state--error">{{ error }}</div>
        <div v-else class="pdf-document-stage" :style="documentStyle">
          <section
            v-for="pageItem in pages"
            :key="pageItem.pageNumber"
            :ref="(element) => setPageElement(element, pageItem.pageNumber)"
            class="pdf-page"
            :data-page="pageItem.pageNumber"
          >
            <canvas :ref="(element) => setCanvas(element, pageItem.pageNumber)" />
            <span>{{ pageItem.pageNumber }}</span>
          </section>
        </div>
        <span v-if="rendering && !loading" class="pdf-render-indicator">
          {{ text('正在逐页渲染', 'Rendering pages') }} {{ renderedPageCount }} / {{ pageCount }}（{{ renderPercent }}%）
        </span>
      </div>
    </div>
  </div>
</template>
