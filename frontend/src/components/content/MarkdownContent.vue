<script setup lang="ts">
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import DOMPurify from 'dompurify'
import MarkdownIt from 'markdown-it'
import { headingSlug } from '@/utils/headingSlug'
import { scrollToY } from '@/utils/smoothScroll'
import { protectedObjectUrl } from '@/utils/protectedAsset'

const props = defineProps<{ source: string }>()
const root = ref<HTMLElement | null>(null)
const markdown = new MarkdownIt({ html: false, linkify: true, typographer: true })

// 标题生成与 GitHub / Typora 目录一致的锚点，文档里的“[5. 接口设计](#5-接口设计)”可以直接跳转。
markdown.core.ruler.push('heading_anchors', (state) => {
  const used = new Map<string, number>()
  state.tokens.forEach((token, index) => {
    if (token.type !== 'heading_open') return
    const inline = state.tokens[index + 1]
    const text = inline?.children?.filter((child) => child.type === 'text' || child.type === 'code_inline').map((child) => child.content).join('') || inline?.content || ''
    const base = headingSlug(text) || 'section'
    const count = used.get(base) || 0
    used.set(base, count + 1)
    token.attrSet('id', count ? `${base}-${count}` : base)
  })
})
// 外链在新窗口打开。
const defaultLink = markdown.renderer.rules.link_open || ((tokens, index, options, _env, self) => self.renderToken(tokens, index, options))
markdown.renderer.rules.link_open = (tokens, index, options, env, self) => {
  const href = tokens[index]!.attrGet('href') || ''
  if (/^https?:\/\//i.test(href)) {
    tokens[index]!.attrSet('target', '_blank')
    tokens[index]!.attrSet('rel', 'noopener noreferrer')
  }
  return defaultLink(tokens, index, options, env, self)
}

const rendered = computed(() =>
  DOMPurify.sanitize(markdown.render(props.source || ''), {
    USE_PROFILES: { html: true },
    ADD_ATTR: ['target'],
    FORBID_TAGS: ['style', 'iframe', 'object', 'embed', 'script'],
  }),
)

function target(hash: string) {
  let id = hash.replace(/^#/, '')
  try { id = decodeURIComponent(id) } catch { /* 保留原样 */ }
  return root.value?.querySelector<HTMLElement>(`[id="${CSS.escape(id)}"]`) || null
}
function jump(element: HTMLElement, smooth = true) {
  const header = document.querySelector<HTMLElement>('.public-header')?.offsetHeight || 64
  const reading = document.querySelector<HTMLElement>('.project-reading-bar.is-visible')?.offsetHeight || 0
  const y = element.getBoundingClientRect().top + window.scrollY - header - reading - 24
  if (smooth) scrollToY(y, 900)
  else window.scrollTo({ top: y, behavior: 'instant' })
  element.classList.remove('is-target')
  void element.offsetWidth
  element.classList.add('is-target')
}
function onClick(event: MouseEvent) {
  const link = (event.target as HTMLElement).closest<HTMLAnchorElement>('a[href^="#"]')
  if (!link || event.metaKey || event.ctrlKey) return
  const element = target(link.getAttribute('href') || '')
  if (!element) return
  event.preventDefault()
  history.replaceState(history.state, '', link.getAttribute('href'))
  jump(element)
}
// 正文里引用的“仅可查看”图片：原始地址会被拒绝，改为经加密票据取回。
function protectImages() {
  root.value?.querySelectorAll<HTMLImageElement>('img[src*="/public/assets/"]').forEach((image) => {
    const match = image.getAttribute('src')?.match(/\/public\/assets\/([0-9a-f-]{36})\/content/i)
    if (!match || image.dataset.guarded) return
    image.dataset.guarded = '1'
    image.addEventListener('error', () => {
      void protectedObjectUrl({ uuid: match[1]!, sha256: '', mime_type: 'image/*', content_url: '', protected: true })
        .then((url) => { image.src = url; image.draggable = false; image.addEventListener('contextmenu', (event) => event.preventDefault()) })
        .catch(() => undefined)
    }, { once: true })
  })
}
async function followLocationHash() {
  if (!location.hash) return
  await nextTick()
  const element = target(location.hash)
  if (element) requestAnimationFrame(() => jump(element, false))
}
onMounted(() => { protectImages(); void followLocationHash() })
watch(rendered, async () => { await nextTick(); protectImages(); void followLocationHash() })
</script>

<template>
  <div ref="root" class="rich-content" @click="onClick" v-html="rendered" />
</template>
