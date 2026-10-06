import { onBeforeUnmount, onMounted, ref, watch, type Ref } from 'vue'
import { PAGE_LAYOUT_EVENT } from '@/utils/pageNavigation'

export interface PinOptions {
  /** 'pin'：元素高于视口、内部 sticky 时，从顶端贴合到底端离开为 0→1；
   *  'pass'：元素从视口底部进入到顶部离开为 0→1。 */
  mode?: 'pin' | 'pass'
  /** 进度写入的 CSS 变量名 */
  variable?: string
  onUpdate?: (progress: number) => void
}

const motionQuery = typeof window !== 'undefined' ? window.matchMedia('(prefers-reduced-motion: reduce)') : null

/**
 * 将元素的滚动进度写入 CSS 变量，动画完全由样式中的 calc() 驱动，不触发 Vue 重新渲染。
 */
export function usePinProgress(element: Ref<HTMLElement | null>, options: PinOptions = {}) {
  const progress = ref(0)
  const visible = ref(false)
  const variable = options.variable || '--p'
  let frame = 0
  let observer: IntersectionObserver | undefined
  let sizes: ResizeObserver | undefined

  function measure() {
    frame = 0
    const node = element.value
    if (!node) return
    const rect = node.getBoundingClientRect()
    const viewport = window.innerHeight || 1
    let value: number
    if (motionQuery?.matches) value = options.mode === 'pass' ? 0.5 : 1
    else if (options.mode === 'pass') value = (viewport - rect.top) / (viewport + rect.height)
    else value = -rect.top / Math.max(1, rect.height - viewport)
    value = Math.min(1, Math.max(0, value))
    if (Math.abs(value - progress.value) < 0.0004 && node.style.getPropertyValue(variable)) return
    progress.value = value
    node.style.setProperty(variable, value.toFixed(4))
    options.onUpdate?.(value)
  }
  function schedule() { if (!frame && visible.value) frame = requestAnimationFrame(measure) }
  function force() { visible.value = true; cancelAnimationFrame(frame); frame = 0; measure() }

  onMounted(() => {
    window.addEventListener('scroll', schedule, { passive: true })
    window.addEventListener('resize', force, { passive: true })
    window.addEventListener(PAGE_LAYOUT_EVENT, force)
    observer = new IntersectionObserver(([entry]) => {
      visible.value = Boolean(entry?.isIntersecting)
      if (visible.value) schedule()
      else measure()
    }, { rootMargin: '20% 0px 20% 0px' })
    sizes = new ResizeObserver(force)
    attach(element.value, null)
  })
  function attach(next: HTMLElement | null, previous: HTMLElement | null) {
    if (previous) { observer?.unobserve(previous); sizes?.unobserve(previous) }
    if (next) { observer?.observe(next); sizes?.observe(next); force() }
  }
  // 元素可能在数据加载后才出现（v-if），需要在出现时重新绑定。
  watch(element, (next, previous) => { if (observer) attach(next, previous) }, { flush: 'post' })
  onBeforeUnmount(() => {
    window.removeEventListener('scroll', schedule)
    window.removeEventListener('resize', force)
    window.removeEventListener(PAGE_LAYOUT_EVENT, force)
    observer?.disconnect()
    sizes?.disconnect()
    cancelAnimationFrame(frame)
  })
  return { progress, visible, refresh: force }
}
