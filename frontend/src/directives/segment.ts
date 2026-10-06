import type { Directive } from 'vue'

/**
 * 分段控件的滑块：在容器内放一块随选中项移动、伸缩的底色。
 * 选中项由 .active / [aria-pressed="true"] / [aria-selected="true"] 标记，切换时以弹性曲线滑动。
 */
type SegmentElement = HTMLElement & { __segment?: { indicator: HTMLSpanElement; mutation: MutationObserver; resize: ResizeObserver; frame: number } }
const ACTIVE = ':scope > .active, :scope > [aria-pressed="true"], :scope > [aria-selected="true"]'

function update(element: SegmentElement) {
  const state = element.__segment
  if (!state) return
  cancelAnimationFrame(state.frame)
  state.frame = requestAnimationFrame(() => {
    const active = element.querySelector<HTMLElement>(ACTIVE)
    const indicator = state.indicator
    if (!active) { indicator.style.opacity = '0'; return }
    const first = !indicator.dataset.ready
    if (first) indicator.style.transition = 'none'
    indicator.style.opacity = '1'
    indicator.style.width = `${active.offsetWidth}px`
    indicator.style.height = `${active.offsetHeight}px`
    indicator.style.transform = `translate3d(${active.offsetLeft}px, ${active.offsetTop}px, 0)`
    if (first) { indicator.dataset.ready = '1'; void indicator.offsetWidth; indicator.style.transition = '' }
  })
}

export const segment: Directive<SegmentElement> = {
  mounted(element) {
    const indicator = document.createElement('span')
    indicator.className = 'segment-indicator'
    indicator.setAttribute('aria-hidden', 'true')
    element.classList.add('has-segment')
    element.prepend(indicator)
    const mutation = new MutationObserver(() => update(element))
    mutation.observe(element, { subtree: true, childList: true, attributes: true, attributeFilter: ['class', 'aria-pressed', 'aria-selected'] })
    const resize = new ResizeObserver(() => update(element))
    resize.observe(element)
    element.__segment = { indicator, mutation, resize, frame: 0 }
    update(element)
  },
  updated(element) { update(element) },
  unmounted(element) {
    const state = element.__segment
    if (!state) return
    state.mutation.disconnect()
    state.resize.disconnect()
    cancelAnimationFrame(state.frame)
  },
}
