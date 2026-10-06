import type { Directive } from 'vue'
import { PAGE_LAYOUT_EVENT } from '@/utils/pageNavigation'

type Scene = { start: number; end: number; visible: boolean }
const scenes = new Map<HTMLElement, Scene>()
let observer: IntersectionObserver | undefined
let media: MediaQueryList | undefined
let frame = 0

function render() {
  frame = 0
  for (const [element, scene] of scenes) {
    if (!scene.visible && !media?.matches) continue
    const top = element.getBoundingClientRect().top
    const progress = media?.matches ? 1 : Math.min(1, Math.max(0, (innerHeight * scene.start - top) / (innerHeight * (scene.start - scene.end))))
    element.style.setProperty('--scroll-progress', progress.toFixed(4))
  }
}
function schedule() { if (!frame) frame = requestAnimationFrame(render) }
function connect() {
  if (observer) return
  media = matchMedia('(prefers-reduced-motion: reduce)')
  observer = new IntersectionObserver(entries => {
    for (const entry of entries) {
      const element = entry.target as HTMLElement, scene = scenes.get(element)
      if (!scene) continue
      scene.visible = entry.isIntersecting
      if (!scene.visible) element.style.setProperty('--scroll-progress', entry.boundingClientRect.top < 0 ? '1' : '0')
    }
    schedule()
  }, { rootMargin: '15% 0px 15% 0px' })
  window.addEventListener('scroll', schedule, { passive: true })
  window.addEventListener('resize', schedule, { passive: true })
  window.addEventListener(PAGE_LAYOUT_EVENT, schedule)
  media.addEventListener('change', schedule)
}

export const scrollProgress: Directive<HTMLElement> = {
  mounted(element, binding) {
    if (binding.value === false) return
    if (typeof IntersectionObserver === 'undefined') { element.style.setProperty('--scroll-progress', '1'); return }
    connect()
    const options = binding.value || {}
    scenes.set(element, { start: options.start ?? .94, end: options.end ?? .32, visible: true })
    element.dataset.scrollScene = ''
    observer?.observe(element)
    schedule()
  },
  updated() { schedule() },
  unmounted(element) {
    scenes.delete(element)
    observer?.unobserve(element)
    if (scenes.size) return
    observer?.disconnect(); observer = undefined
    window.removeEventListener('scroll', schedule)
    window.removeEventListener('resize', schedule)
    window.removeEventListener(PAGE_LAYOUT_EVENT, schedule)
    media?.removeEventListener('change', schedule)
    cancelAnimationFrame(frame); frame = 0
  },
}
