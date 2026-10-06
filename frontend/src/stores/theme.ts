import { computed, ref } from 'vue'
import { readPreference, writePreference } from '@/utils/storage'
export type ThemePreference = 'system' | 'light' | 'dark'
const saved = readPreference('portfolio_theme')
const preference = ref<ThemePreference>(saved === 'light' || saved === 'dark' ? saved : 'system')
const media = window.matchMedia('(prefers-color-scheme: dark)')
const systemDark = ref(media.matches)
const resolved = computed(() => preference.value === 'system' ? (systemDark.value ? 'dark' : 'light') : preference.value)
let transitionTimer: ReturnType<typeof setTimeout> | undefined
type ViewTransitionDocument = Document & { startViewTransition?: (update: () => void) => { finished: Promise<void> } }
function commit() {
  const root = document.documentElement
  root.dataset.theme = resolved.value
  root.style.colorScheme = resolved.value
  window.dispatchEvent(new Event('portfolio:theme-change'))
}
/**
 * 主题切换：支持视图过渡的浏览器由合成器完成一次圆形揭示（从点击处展开），
 * 页面只重绘一次，不再逐元素过渡颜色；其余浏览器退化为短暂的颜色过渡。
 */
function apply(animate = false, origin?: { x: number; y: number }) {
  const root = document.documentElement
  const changed = root.dataset.theme !== resolved.value
  if (!animate || !changed || window.matchMedia('(prefers-reduced-motion: reduce)').matches) { commit(); return }
  const transition = (document as ViewTransitionDocument).startViewTransition
  if (transition) {
    const x = origin?.x ?? window.innerWidth - 80
    const y = origin?.y ?? 32
    root.style.setProperty('--theme-x', `${x}px`)
    root.style.setProperty('--theme-y', `${y}px`)
    root.style.setProperty('--theme-r', `${Math.hypot(Math.max(x, window.innerWidth - x), Math.max(y, window.innerHeight - y))}px`)
    root.classList.add('theme-view-transition')
    transition.call(document, commit).finished.finally(() => root.classList.remove('theme-view-transition'))
    return
  }
  clearTimeout(transitionTimer)
  root.classList.add('theme-transition')
  commit()
  transitionTimer = setTimeout(() => root.classList.remove('theme-transition'), 420)
}
export function setTheme(value: ThemePreference, event?: MouseEvent) {
  preference.value = value
  writePreference('portfolio_theme', value)
  apply(true, event && event.clientX ? { x: event.clientX, y: event.clientY } : undefined)
}
export function initializeTheme() {
  apply()
  media.addEventListener('change', event => { systemDark.value = event.matches; if (preference.value === 'system') apply(true) })
  window.addEventListener('storage', event => {
    if (event.key !== 'portfolio_theme') return
    preference.value = event.newValue === 'dark' || event.newValue === 'light' ? event.newValue : 'system'
    apply(true)
  })
}
export function useTheme() { return { preference, resolved, setTheme } }
