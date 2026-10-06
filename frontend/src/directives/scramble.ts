import type { Directive } from 'vue'

/**
 * 信息解码：元素进入视口时，文字先以符号乱码出现，再从左到右「解码」为原文。
 */
const GLYPHS = '01∑∫∂∇λσΔ≈∞▚▞░▒/\\<>{}[]#'
const observer = typeof window !== 'undefined' && 'IntersectionObserver' in window
  ? new IntersectionObserver((entries) => {
      for (const entry of entries) {
        if (!entry.isIntersecting) continue
        observer?.unobserve(entry.target)
        run(entry.target as HTMLElement)
      }
    }, { threshold: 0.6 })
  : null

function run(element: HTMLElement) {
  const final = element.dataset.scrambleText || element.textContent || ''
  const chars = Array.from(final)
  const start = performance.now()
  const duration = Math.min(1100, 380 + chars.length * 28)
  const step = (now: number) => {
    const t = Math.min(1, (now - start) / duration)
    const resolved = Math.floor(t * chars.length)
    element.textContent = chars.map((char, index) => (index < resolved || char === ' ' ? char : GLYPHS[Math.floor(Math.random() * GLYPHS.length)])).join('')
    if (t < 1) requestAnimationFrame(step)
    else element.textContent = final
  }
  requestAnimationFrame(step)
}

export const scramble: Directive<HTMLElement, string | undefined> = {
  mounted(element, binding) {
    const text = binding.value ?? element.textContent ?? ''
    element.dataset.scrambleText = text
    element.setAttribute('aria-label', text)
    if (!observer || window.matchMedia('(prefers-reduced-motion: reduce)').matches) return
    observer.observe(element)
  },
  updated(element, binding) {
    const text = binding.value ?? ''
    if (text && text !== element.dataset.scrambleText) {
      element.dataset.scrambleText = text
      element.setAttribute('aria-label', text)
      element.textContent = text
    }
  },
  unmounted(element) { observer?.unobserve(element) },
}
