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
      { rootMargin: '0px 0px -7% 0px', threshold: 0.08 },
    )
  : null

export const reveal: Directive<HTMLElement> = {
  mounted(element, binding) {
    element.classList.add('reveal-item')
    if (binding.value) element.style.setProperty('--reveal-delay', `${Number(binding.value)}ms`)
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches || !observer) {
      element.classList.add('is-revealed')
    } else {
      observer.observe(element)
    }
  },
  unmounted(element) {
    observer?.unobserve(element)
  },
}
