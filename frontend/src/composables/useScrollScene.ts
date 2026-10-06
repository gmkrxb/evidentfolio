import { onBeforeUnmount, onMounted, ref, type Ref } from 'vue'
import { PAGE_LAYOUT_EVENT } from '@/utils/pageNavigation'

export function useScrollScene(root: Ref<HTMLElement | null>) {
  let frame = 0
  let observer: IntersectionObserver | undefined
  let sizeObserver: ResizeObserver | undefined
  let visible = true
  const motion = window.matchMedia('(min-width: 1001px) and (min-height: 690px) and (prefers-reduced-motion: no-preference)')
  const progress = ref(0)
  const enabled = ref(false)
  const headerHeight = () => document.querySelector<HTMLElement>('.public-header')?.offsetHeight || 72
  function measure() {
    const stage = root.value?.querySelector<HTMLElement>('.showcase-stage')
    const content = root.value?.querySelector<HTMLElement>('.showcase-grid')
    if (!stage || !content || !root.value) return
    const styles = getComputedStyle(stage)
    const inset = headerHeight()
    const available = window.innerHeight - inset
    const height = content.offsetHeight + parseFloat(styles.paddingTop) + parseFloat(styles.paddingBottom)
    // 内容完整放得下时才固定，长文与缩放场景保持自然布局。
    enabled.value = motion.matches && height <= available - 2
    root.value.style.setProperty('--scene-top', `${inset}px`)
    root.value.style.setProperty('--scene-height', `${available}px`)
    schedule()
  }
  function render() {
    frame = 0
    if (!root.value) return
    const rect = root.value.getBoundingClientRect()
    const inset = headerHeight()
    progress.value = enabled.value ? Math.min(1, Math.max(0, (inset - rect.top) / Math.max(1, rect.height - (window.innerHeight - inset)))) : 0
    root.value.style.setProperty('--scene-progress', String(progress.value))
  }
  function schedule() { if (visible && !frame) frame = requestAnimationFrame(render) }
  onMounted(() => {
    window.addEventListener('scroll', schedule, { passive: true })
    window.addEventListener('resize', measure, { passive: true })
    window.addEventListener(PAGE_LAYOUT_EVENT, measure)
    motion.addEventListener('change', measure)
    observer = new IntersectionObserver(([entry]) => { visible = entry.isIntersecting; if (visible) schedule() })
    if (root.value) observer.observe(root.value)
    sizeObserver = new ResizeObserver(measure)
    const content = root.value?.querySelector('.showcase-grid')
    if (content) sizeObserver.observe(content)
    const header = document.querySelector('.public-header')
    if (header) sizeObserver.observe(header)
    measure()
  })
  onBeforeUnmount(() => {
    window.removeEventListener('scroll', schedule); window.removeEventListener('resize', measure)
    window.removeEventListener(PAGE_LAYOUT_EVENT, measure)
    motion.removeEventListener('change', measure); observer?.disconnect(); sizeObserver?.disconnect(); cancelAnimationFrame(frame)
  })
  return { progress, enabled, refresh: measure }
}
