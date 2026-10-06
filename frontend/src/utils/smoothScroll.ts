/**
 * 轻量惯性滚动：拦截鼠标滚轮，以指数缓动驱动原生滚动位置。
 * 仍使用原生 window 滚动，因此 sticky、IntersectionObserver 与键盘 / 滚动条均保持可用。
 */

type Listener = (y: number) => void

let target = 0
let current = 0
let lastSet = -1
let frame = 0
let last = 0
let active = false
let installed = 0
let tween: { from: number; to: number; start: number; duration: number } | null = null
const listeners = new Set<Listener>()

const maxScroll = () => Math.max(0, document.documentElement.scrollHeight - window.innerHeight)
const clamp = (value: number) => Math.min(maxScroll(), Math.max(0, value))
const easeInOut = (t: number) => (t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2)

function canScroll(element: Element | null, delta: number, horizontal: boolean): boolean {
  let node = element
  while (node && node !== document.body && node !== document.documentElement) {
    if (node instanceof HTMLElement) {
      if (node.dataset.nativeScroll !== undefined) return true
      const style = getComputedStyle(node)
      const overflow = horizontal ? style.overflowX : style.overflowY
      if (/(auto|scroll|overlay)/.test(overflow)) {
        const size = horizontal ? node.scrollWidth - node.clientWidth : node.scrollHeight - node.clientHeight
        const position = horizontal ? node.scrollLeft : node.scrollTop
        if (size > 1 && ((delta > 0 && position < size - 1) || (delta < 0 && position > 0))) return true
      }
    }
    node = node.parentElement
  }
  return false
}

function hasModal() {
  try { return Boolean(document.querySelector('dialog:modal')) } catch { return Boolean(document.querySelector('dialog[open]')) }
}

function write(y: number) {
  lastSet = Math.round(y)
  window.scrollTo(0, y)
  listeners.forEach((listener) => listener(y))
}

function loop(now: number) {
  frame = 0
  const dt = Math.min(0.05, (now - (last || now)) / 1000) || 1 / 60
  last = now
  if (tween) {
    const t = Math.min(1, (now - tween.start) / tween.duration)
    current = tween.from + (tween.to - tween.from) * easeInOut(t)
    target = current
    write(current)
    if (t >= 1) { tween = null; active = false; last = 0; return }
  } else {
    current += (target - current) * (1 - Math.exp(-dt * 10))
    if (Math.abs(target - current) < 0.4) {
      current = target
      write(current)
      active = false
      last = 0
      return
    }
    write(current)
  }
  frame = requestAnimationFrame(loop)
}

function start() {
  active = true
  if (!frame) frame = requestAnimationFrame(loop)
}

function stop() {
  cancelAnimationFrame(frame)
  frame = 0
  active = false
  tween = null
  last = 0
  target = current = window.scrollY
}

function onWheel(event: WheelEvent) {
  if (event.defaultPrevented || event.ctrlKey || event.metaKey) return
  if (document.body.classList.contains('is-locked') || hasModal()) return
  const unit = event.deltaMode === 1 ? 16 : event.deltaMode === 2 ? window.innerHeight : 1
  const dx = event.deltaX * unit
  const dy = event.deltaY * unit
  if (Math.abs(dx) > Math.abs(dy)) return
  if (canScroll(event.target as Element, dy, false)) return
  event.preventDefault()
  if (!active) { current = window.scrollY; target = current }
  tween = null
  target = clamp(target + dy)
  start()
}

function onScroll() {
  // 键盘、滚动条或程序跳转改变了位置：放弃当前动画并同步。
  if (Math.abs(window.scrollY - lastSet) > 2) {
    if (active) stop()
    current = target = window.scrollY
  }
}

function onKey(event: KeyboardEvent) {
  if (active && ['ArrowUp', 'ArrowDown', 'PageUp', 'PageDown', 'Home', 'End', ' '].includes(event.key)) stop()
}

export function smoothScrollEnabled() {
  return installed > 0
}

export function scrollToY(y: number, duration?: number) {
  const destination = clamp(y)
  if (!installed || window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
    window.scrollTo({ top: destination, behavior: 'smooth' })
    return
  }
  current = window.scrollY
  const distance = Math.abs(destination - current)
  tween = { from: current, to: destination, start: performance.now(), duration: duration ?? Math.min(1600, 520 + distance * 0.35) }
  start()
}

export function onSmoothScroll(listener: Listener) {
  listeners.add(listener)
  return () => listeners.delete(listener)
}

export function installSmoothScroll() {
  const query = window.matchMedia('(pointer: fine) and (hover: hover) and (prefers-reduced-motion: no-preference)')
  if (!query.matches) return () => undefined
  installed += 1
  if (installed === 1) {
    current = target = window.scrollY
    window.addEventListener('wheel', onWheel, { passive: false })
    window.addEventListener('scroll', onScroll, { passive: true })
    window.addEventListener('keydown', onKey, { passive: true })
    document.documentElement.classList.add('has-smooth-scroll')
  }
  return () => {
    installed = Math.max(0, installed - 1)
    if (installed) return
    stop()
    window.removeEventListener('wheel', onWheel)
    window.removeEventListener('scroll', onScroll)
    window.removeEventListener('keydown', onKey)
    document.documentElement.classList.remove('has-smooth-scroll')
  }
}
