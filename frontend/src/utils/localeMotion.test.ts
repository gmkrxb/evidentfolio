import { afterEach, expect, test, vi } from 'vitest'
import { animateLocaleText, captureLocaleText } from './localeMotion'

const originalAnimate = Object.getOwnPropertyDescriptor(HTMLElement.prototype, 'animate')
afterEach(() => {
  document.body.innerHTML = ''; vi.restoreAllMocks(); vi.unstubAllGlobals()
  if (originalAnimate) Object.defineProperty(HTMLElement.prototype, 'animate', originalAnimate)
  else Reflect.deleteProperty(HTMLElement.prototype, 'animate')
})

test('只过渡变化的文字，原有图片、背景和相同文案保持不动', async () => {
  vi.stubGlobal('matchMedia', () => ({ matches: false }))
  vi.spyOn(HTMLElement.prototype, 'getBoundingClientRect').mockReturnValue({ top: 120, bottom: 160, left: 20, right: 220, width: 200, height: 40 } as DOMRect)
  const animate = vi.fn(() => ({ finished: Promise.resolve() }))
  Object.defineProperty(HTMLElement.prototype, 'animate', { value: animate, configurable: true })
  document.body.innerHTML = '<main><h1>从思考，到实现。</h1><p>Python</p><img src="/cover.png"><div data-locale-text><span>项目</span><span>标题</span></div></main>'
  const before = captureLocaleText(document.body)
  document.querySelector('h1')!.textContent = 'From thought to outcome.'
  await animateLocaleText(before)
  expect(animate).toHaveBeenCalledTimes(1)
  expect(animate.mock.instances[0]).toBe(document.querySelector('h1'))
  expect(document.querySelector('main')!.style.opacity).toBe('')
  expect(document.querySelector('p')!.textContent).toBe('Python')
  expect([...before.keys()].filter(element => element.closest('[data-locale-text]'))).toHaveLength(1)
})

test('减少动态效果时不启动文字动画', async () => {
  vi.stubGlobal('matchMedia', () => ({ matches: true }))
  const element = document.createElement('h1')
  element.textContent = 'English'
  const animate = vi.fn()
  element.animate = animate
  document.body.append(element)
  await animateLocaleText(new Map([[element, { text: '中文', top: 0, left: 0 }]]))
  expect(animate).not.toHaveBeenCalled()
})
