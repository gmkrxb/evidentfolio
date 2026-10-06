import type { Directive } from 'vue'

/** 磁吸：精细指针悬停时，按钮被光标轻轻吸引。 */
type MagneticElement = HTMLElement & { __magnetic?: { move: (event: PointerEvent) => void; leave: () => void } }
const enabled = () => typeof window !== 'undefined' && window.matchMedia('(pointer: fine) and (prefers-reduced-motion: no-preference)').matches

export const magnetic: Directive<MagneticElement, number | undefined> = {
  mounted(element, binding) {
    if (!enabled()) return
    const strength = binding.value ?? 0.28
    const move = (event: PointerEvent) => {
      const rect = element.getBoundingClientRect()
      const x = (event.clientX - rect.left - rect.width / 2) * strength
      const y = (event.clientY - rect.top - rect.height / 2) * strength
      element.style.transition = 'transform .25s cubic-bezier(.16,1,.3,1)'
      element.style.transform = `translate3d(${x.toFixed(1)}px, ${y.toFixed(1)}px, 0)`
    }
    const leave = () => {
      element.style.transition = 'transform .9s cubic-bezier(.16,1,.3,1)'
      element.style.transform = ''
    }
    element.__magnetic = { move, leave }
    element.addEventListener('pointermove', move)
    element.addEventListener('pointerleave', leave)
  },
  unmounted(element) {
    if (!element.__magnetic) return
    element.removeEventListener('pointermove', element.__magnetic.move)
    element.removeEventListener('pointerleave', element.__magnetic.leave)
  },
}
