import { nextTick } from 'vue'

const pending = new Set<Promise<unknown>>()
export const SHOWCASE_RESTORE_EVENT = 'portfolio:restore-showcase'
export const PAGE_LAYOUT_EVENT = 'portfolio:page-layout'

export function trackPageLoad<T>(task: Promise<T>): Promise<T> {
  pending.add(task)
  void task.finally(() => pending.delete(task)).catch(() => undefined)
  return task
}

export async function waitForPageContent(waitForLayout = true) {
  await nextTick()
  while (pending.size) {
    await Promise.allSettled([...pending])
    await nextTick()
  }
  // 等待自适应布局和尺寸观察器完成，避免恢复到旧的固定高度。
  if (waitForLayout && typeof requestAnimationFrame === 'function') {
    await new Promise<void>((resolve) => requestAnimationFrame(() => requestAnimationFrame(() => resolve())))
    await nextTick()
  }
}

export function withoutLocale(path: string) {
  return path.replace(/^\/en(?=\/|$)/, '') || '/'
}

export function isLocaleNavigation(to: string, from: string) {
  return to !== from && withoutLocale(to) === withoutLocale(from)
}

export function initialScroll(initial: boolean, hash: string, saved: { left: number; top: number } | null) {
  // 刷新从顶部开始，前进后退才恢复历史位置。
  if (initial && !hash) return { left: 0, top: 0 }
  return saved
}

function layoutTop(element: HTMLElement) {
  let top = 0
  let current: HTMLElement | null = element
  while (current) { top += current.offsetTop; current = current.offsetParent as HTMLElement | null }
  return top
}

export function captureReadingPosition() {
  const scene = document.querySelector<HTMLElement>('.showcase-scene')
  const active = scene?.querySelector<HTMLElement>('.showcase-project.is-active')
  const rect = scene?.getBoundingClientRect()
  const showcase = active && rect && rect.top < window.innerHeight && rect.bottom > 100 ? {
    uuid: active.dataset.showcaseProject,
    progress: Number(scene?.style.getPropertyValue('--scene-progress')) || 0,
    pinned: scene?.classList.contains('is-pinned'),
    offset: active.getBoundingClientRect().top,
  } : null
  const elements = [...document.querySelectorAll<HTMLElement>('main [data-scroll-key], main section[id]')]
  const anchor = elements.filter((element) => (element.offsetHeight || element.offsetWidth) && layoutTop(element) - window.scrollY <= 140)
    .sort((a, b) => layoutTop(b) - layoutTop(a))[0]
  const hero = document.querySelector<HTMLElement>('.case-hero')
  const heroEnd = !anchor && hero && document.querySelector('.project-reading-bar.is-visible') ? { heroEndOffset: hero.getBoundingClientRect().bottom } : {}
  return { top: window.scrollY, key: anchor?.dataset.scrollKey, id: anchor?.id, offset: anchor ? layoutTop(anchor) - window.scrollY : 0, showcase, ...heroEnd }
}

export function restoreReadingPosition(position: ReturnType<typeof captureReadingPosition>) {
  if (position.showcase?.uuid) {
    const scene = document.querySelector<HTMLElement>('.showcase-scene')
    const cards = [...document.querySelectorAll<HTMLElement>('[data-showcase-project]')]
    const index = cards.findIndex((card) => card.dataset.showcaseProject === position.showcase?.uuid)
    if (scene && index >= 0) {
      window.dispatchEvent(new CustomEvent(SHOWCASE_RESTORE_EVENT, { detail: position.showcase.uuid }))
      const inset = document.querySelector<HTMLElement>('.public-header')?.offsetHeight || 72
      const progress = position.showcase.pinned ? position.showcase.progress : index / Math.max(1, cards.length - 1)
      const pinned = scene.classList.contains('is-pinned')
      const top = position.top < 2 && (!pinned || index === 0) ? 0 : pinned
        ? layoutTop(scene) - inset + (scene.offsetHeight - (window.innerHeight - inset)) * progress
        : layoutTop(cards[index]) - Math.max(inset + 20, position.showcase.offset)
      window.scrollTo({ top: Math.max(0, top), behavior: 'instant' })
      return
    }
  }
  const anchor = position.key
    ? [...document.querySelectorAll<HTMLElement>('main [data-scroll-key]')].find((element) => element.dataset.scrollKey === position.key)
    : position.id ? document.getElementById(position.id) : null
  if (typeof position.heroEndOffset === 'number') {
    const hero = document.querySelector<HTMLElement>('.case-hero')
    if (hero) { window.scrollTo({ top: Math.max(0, layoutTop(hero) + hero.offsetHeight - position.heroEndOffset), behavior: 'instant' }); return }
  }
  window.scrollTo({ top: anchor ? layoutTop(anchor) - position.offset : position.top, behavior: 'instant' })
}
