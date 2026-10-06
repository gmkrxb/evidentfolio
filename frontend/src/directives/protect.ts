import type { Directive } from 'vue'

/**
 * v-protect：仅可查看的内容禁止选择、复制、拖拽、右键另存与打印。
 * 页面上存在受保护内容时，同时拦截 Ctrl/⌘ + C / S / P。
 */
let active = 0
const block = (event: Event) => event.preventDefault()
function keys(event: KeyboardEvent) {
  if (!(event.metaKey || event.ctrlKey)) return
  const key = event.key.toLowerCase()
  if (key === 's' || key === 'p' || (key === 'c' && !(event.target as HTMLElement | null)?.closest?.('input, textarea, [contenteditable="true"]'))) event.preventDefault()
}
const events = ['copy', 'cut', 'contextmenu', 'dragstart', 'selectstart'] as const

function enable(el: HTMLElement) {
  // 组件重新渲染 class 时会覆盖手动添加的类名，因此每次都补上
  el.classList.add('is-protected')
  if (el.dataset.protected === '1') return
  el.dataset.protected = '1'
  events.forEach((name) => el.addEventListener(name, block))
  if (active++ === 0) {
    document.addEventListener('keydown', keys, true)
    document.documentElement.classList.add('has-protected-content')
  }
}
function disable(el: HTMLElement) {
  if (el.dataset.protected !== '1') return
  delete el.dataset.protected
  el.classList.remove('is-protected')
  events.forEach((name) => el.removeEventListener(name, block))
  if (--active === 0) {
    document.removeEventListener('keydown', keys, true)
    document.documentElement.classList.remove('has-protected-content')
  }
}

export const protect: Directive<HTMLElement, boolean | undefined> = {
  mounted(el, binding) { if (binding.value !== false) enable(el) },
  updated(el, binding) { if (binding.value === false) disable(el); else enable(el) },
  beforeUnmount(el) { disable(el) },
}
