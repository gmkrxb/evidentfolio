import type { Directive } from 'vue'

const observer = typeof window !== 'undefined' && 'IntersectionObserver' in window
  ? new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add('is-revealed')
            observer?.unobserve(entry.target)
          }
        })
      },
      { rootMargin: '0px 0px -32px 0px', threshold: 0.06 },
    )
  : null

export const reveal: Directive<HTMLElement> = {
  mounted(element, binding) {
    if (binding.value === false) return
    element.classList.add('reveal-item')
    const options = typeof binding.value === 'object' && binding.value ? binding.value : { delay: binding.value }
    element.dataset.reveal = options.kind || 'rise'
    const delay = Math.max(0, Math.min(260, Number(options.delay) || 0))
    element.style.setProperty('--reveal-delay', `${delay}ms`)
    const alreadyInView = document.documentElement.dataset.localeDirection && element.getBoundingClientRect().top < window.innerHeight
    if (alreadyInView || window.matchMedia('(prefers-reduced-motion: reduce)').matches || !observer) {
      element.dataset.revealImmediate = 'true'
      element.classList.add('is-revealed')
    } else {
      observer.observe(element)
    }
  },
  unmounted(element) {
    observer?.unobserve(element)
  },
}
