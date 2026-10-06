type TextState = { text: string; top: number; left: number }
export type LocaleTextSnapshot = Map<HTMLElement, TextState>

function textOf(element: HTMLElement) {
  if (element.hasAttribute('data-locale-text')) return element.textContent?.trim() || ''
  return [...element.childNodes].filter(node => node.nodeType === Node.TEXT_NODE).map(node => node.textContent).join('').trim()
}

export function captureLocaleText(root: HTMLElement): LocaleTextSnapshot {
  const snapshot: LocaleTextSnapshot = new Map()
  for (const element of root.querySelectorAll<HTMLElement>('h1,h2,h3,h4,p,span,strong,small,dt,dd,figcaption,a,button,li,[data-locale-text]')) {
    if (element.closest('[inert], [data-locale-static], .theme-control, .public-language-switch')) continue
    const owner = element.closest('[data-locale-text]')
    if (owner && owner !== element) continue
    if (element.querySelector('img,svg,canvas,video,iframe')) continue
    const rect = element.getBoundingClientRect(), text = textOf(element)
    if (!text || !rect.width || !rect.height || rect.bottom < 0 || rect.top > innerHeight) continue
    snapshot.set(element, { text, top: rect.top, left: rect.left })
  }
  return snapshot
}

export function animateLocaleText(before: LocaleTextSnapshot): Promise<void> {
  if (document.hidden || matchMedia('(prefers-reduced-motion: reduce)').matches) return Promise.resolve()
  const animations: Promise<unknown>[] = []
  for (const [element, previous] of before) {
    if (!element.isConnected || previous.text === textOf(element) || !element.animate) continue
    const rect = element.getBoundingClientRect()
    if (!rect.width || !rect.height || rect.bottom < 0 || rect.top > innerHeight) continue
    // 不动背景、图片和未改变的文字，也不让标题整体消失。
    const y = Math.max(-18, Math.min(18, previous.top - rect.top)) + 3
    const animation = element.animate([
      { opacity: .55, translate: `0 ${y}px`, filter: 'blur(.8px)' },
      { opacity: 1, translate: '0 0', filter: 'blur(0)' },
    ], { duration: 340, easing: 'cubic-bezier(.18,.72,.2,1)' })
    animation.id = 'locale-text'
    animations.push(animation.finished.catch(() => undefined))
  }
  return Promise.all(animations).then(() => undefined)
}
