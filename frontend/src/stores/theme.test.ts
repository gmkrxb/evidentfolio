import { afterEach, expect, test, vi } from 'vitest'

afterEach(() => { vi.useRealTimers(); vi.unstubAllGlobals(); document.documentElement.className = ''; localStorage.clear() })

test('自动跟随系统并过渡，手动选择覆盖系统偏好，减少动态效果时直接切换', async () => {
  let systemChange: (event: { matches: boolean }) => void = () => {}
  let reduce = false
  vi.stubGlobal('matchMedia', (query: string) => ({ matches: query.includes('reduce') ? reduce : false, addEventListener: (_: string, callback: typeof systemChange) => { systemChange = callback } }))
  vi.useFakeTimers()
  const theme = await import('./theme')
  theme.initializeTheme()
  expect(document.documentElement.dataset.theme).toBe('light')
  systemChange({ matches: true })
  expect(document.documentElement.dataset.theme).toBe('dark')
  expect(document.documentElement.classList.contains('theme-transition')).toBe(true)
  vi.advanceTimersByTime(420)
  expect(document.documentElement.classList.contains('theme-transition')).toBe(false)
  theme.setTheme('light')
  systemChange({ matches: true })
  expect(document.documentElement.dataset.theme).toBe('light')
  expect(localStorage.getItem('portfolio_theme')).toBe('light')
  vi.advanceTimersByTime(420)
  reduce = true
  theme.setTheme('system')
  expect(document.documentElement.dataset.theme).toBe('dark')
  expect(document.documentElement.classList.contains('theme-transition')).toBe(false)
})
