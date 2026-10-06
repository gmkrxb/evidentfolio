import { afterEach, expect, test, vi } from 'vitest'
import { initialScroll, isLocaleNavigation, restoreReadingPosition, SHOWCASE_RESTORE_EVENT, trackPageLoad, waitForPageContent, withoutLocale } from './pageNavigation'

afterEach(() => { document.body.innerHTML = ''; vi.restoreAllMocks() })

test('刷新忽略浏览器旧位置，历史返回保留位置，显式锚点仍可定位', () => {
  const saved = { left: 0, top: 1680 }
  expect(initialScroll(true, '', saved)).toEqual({ left: 0, top: 0 })
  expect(initialScroll(false, '', saved)).toEqual(saved)
  expect(initialScroll(true, '#overview', null)).toBeNull()
})

test('只把同一页面的语言变化识别为切换', () => {
  expect(withoutLocale('/en')).toBe('/')
  expect(withoutLocale('/en/projects/123')).toBe('/projects/123')
  expect(withoutLocale('/engineering')).toBe('/engineering')
  expect(isLocaleNavigation('/en/projects/123', '/projects/123')).toBe(true)
  expect(isLocaleNavigation('/en/contact', '/projects')).toBe(false)
})

test('页面完成异步内容后再恢复阅读位置', async () => {
  let resolve!: () => void
  let ready = false
  const task = trackPageLoad(new Promise<void>((done) => { resolve = done }))
  const waiting = waitForPageContent().then(() => { ready = true })
  await Promise.resolve()
  expect(ready).toBe(false)
  resolve()
  await Promise.all([task, waiting])
  expect(ready).toBe(true)
})

test('语言切换保留作品 UUID，并按新页面高度恢复滚动进度', () => {
  document.body.innerHTML = '<header class="public-header"></header><section class="showcase-scene is-pinned"><a data-showcase-project="first"></a><a data-showcase-project="second"></a></section>'
  const scene = document.querySelector('section')!
  Object.defineProperty(scene, 'offsetHeight', { value: 1900 })
  Object.defineProperty(scene, 'offsetTop', { value: 72 })
  Object.defineProperty(document.querySelector('header'), 'offsetHeight', { value: 72 })
  const scroll = vi.spyOn(window, 'scrollTo').mockImplementation(() => {})
  const restored = vi.fn()
  window.addEventListener(SHOWCASE_RESTORE_EVENT, restored, { once: true })
  restoreReadingPosition({ top: 480, offset: 0, key: undefined, id: '', showcase: { uuid: 'second', pinned: true, progress: .6, offset: 100 } })
  expect(restored.mock.calls[0][0].detail).toBe('second')
  expect(scroll).toHaveBeenCalledWith({ top: (1900 - (innerHeight - 72)) * .6, behavior: 'instant' })
  restoreReadingPosition({ top: 0, offset: 0, key: undefined, id: '', showcase: { uuid: 'second', pinned: false, progress: 0, offset: 100 } })
  expect(scroll).toHaveBeenLastCalledWith({ top: 1900 - (innerHeight - 72), behavior: 'instant' })
})

test('标题刚收起时按首屏底部恢复位置，避免译文高度变化让小标题消失', () => {
  document.body.innerHTML = '<header class="case-hero"></header>'
  const hero = document.querySelector<HTMLElement>('.case-hero')!
  Object.defineProperty(hero, 'offsetTop', { value: 73 })
  Object.defineProperty(hero, 'offsetHeight', { value: 600 })
  const scroll = vi.spyOn(window, 'scrollTo').mockImplementation(() => {})
  restoreReadingPosition({ top: 300, offset: 0, key: undefined, id: '', showcase: null, heroEndOffset: 120 })
  expect(scroll).toHaveBeenCalledWith({ top: 553, behavior: 'instant' })
})
